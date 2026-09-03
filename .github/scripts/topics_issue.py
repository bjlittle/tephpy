#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Report topic promotion changes and the coverage matrix (topics spec §3.8).

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from types import ModuleType

REPO = Path(__file__).resolve().parents[2]

MARKER = "topic-coverage"

#: The issue this report keeps. One standing issue, edited in place, in the
#: manner of the floors report's dedupe: a monthly finding that filed a new issue
#: each run would bury the one before it.
TITLE = "Topic coverage"

#: The current promoted set, carried in the body so the next run can say what
#: changed. An HTML comment, so it is invisible to a reader and unambiguous to
#: the parser -- a set recovered by scraping the rendered table would break the
#: moment the table's wording changed.
STATE = re.compile(r"<!-- topics-state: (?P<value>\{.*?\}) -->", re.DOTALL)

#: What each quadrant is called in the rendered matrix. Presentation, not
#: taxonomy -- `tephpy_topics.py`'s `LABELS` makes the same separation for the
#: published index, and this report has its own opinion of the word for the
#: same reason: nothing in the promotion rule cares what a column is titled.
LABELS = {
    "tutorials": "tutorials",
    "howtos": "how-tos",
    "explanation": "explanation",
    "gallery": "gallery",
}

#: The demand-signal issue the matrix's coverage gap complements
#: (topics spec §3.8). Written bare, following `floors_issue.py`'s
#: `SPHINX_CLICK` / `SECOND_FLOOR` precedent: an issue body is not
#: Sphinx-rendered, so an `issue` role would reach the reader as its own
#: source, and the bare form is what GitHub turns into a link.
DEMAND_SIGNAL = 261


def _gh() -> str:
    """Resolve ``gh`` off ``PATH``.

    This script shells out to nothing else, so it carries its own resolver
    rather than importing the pin generator for one function.

    Returns
    -------
    str
        The absolute path to ``gh``.

    Raises
    ------
    RuntimeError
        If ``gh`` is not on ``PATH``.

    """
    found = shutil.which("gh")
    if found is None:
        msg = "gh is not on PATH"
        raise RuntimeError(msg)
    return found


def _topics_data() -> ModuleType:
    """Import the topic taxonomy module by path (topics spec §3.5).

    ``docs/src/_ext`` is a ``sys.path`` entry at Sphinx build time rather than a
    package (:issue:`92`), and this script runs outside that build -- so it
    loads the module the same way `tests/ext_modules.py` does for the test
    suite, rather than depending on a test helper from a script the sdist does
    not ship.

    Returns
    -------
    module
        The executed `tephpy_topics_data` module.

    """
    path = REPO / "docs" / "src" / "_ext" / "tephpy_topics_data.py"
    spec = importlib.util.spec_from_file_location("tephpy_topics_data", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


topics = _topics_data()


def narrative_pages(docs: Path) -> list[Path]:
    """Every hand-written page of the three narrative quadrants.

    Parameters
    ----------
    docs : Path
        The documentation source root.

    Returns
    -------
    list of Path
        The quadrants' pages, sorted, without their landing pages.

    """
    found: list[Path] = []
    for quadrant in topics.NARRATIVE:
        found.extend(
            path
            for path in sorted((docs / quadrant).rglob("*.rst"))
            if path.name != "index.rst"
        )
    return found


def corpus(repo: Path) -> dict[str, tuple[str, list[str]]]:
    """Return the tagged corpus of topics spec §3.1.

    Reads the same three quadrants and the same example directory the gate does,
    through the same two readers (`read_page_tags`, `read_gallery_tags`), so the
    two assemblies describe the same corpus -- asserted directly by
    `test_the_corpus_matches_the_gate_s`.

    Parameters
    ----------
    repo : Path
        The repository root.

    Returns
    -------
    dict
        ``"<quadrant>/<stem>"`` to ``(quadrant, tags)``.

    """
    docs = repo / "docs" / "src"
    examples = repo / "src" / "tephpy" / "examples"
    found = {
        f"{page.parent.name}/{page.stem}": (
            page.parent.name,
            topics.read_page_tags(page.read_text(encoding="utf-8")),
        )
        for page in narrative_pages(docs)
    }
    found.update(
        {
            f"gallery/{path.stem}": (
                "gallery",
                topics.read_gallery_tags(path.read_text(encoding="utf-8")),
            )
            for path in sorted(examples.glob("plot_*.py"))
        }
    )
    return found


def matrix(items: Mapping[str, tuple[str, Sequence[str]]]) -> str:
    """Render the coverage matrix (topics spec §3.8).

    One row per term the corpus actually uses, one column per quadrant.
    Every quadrant gets a column even where a term appears in none of them,
    because an empty cell is the report's entire second job: the gap is what
    a reader is here to see, and omitting the column would omit the finding.

    Parameters
    ----------
    items : mapping
        Item name to ``(quadrant, tags)``, as `corpus` returns.

    Returns
    -------
    str
        A GitHub-flavoured Markdown table.

    """
    covered = topics.coverage(items)
    header = "| term | " + " | ".join(LABELS[q] for q in topics.QUADRANTS) + " |"
    rule = "|---|" + "---|" * len(topics.QUADRANTS)
    rows = [
        f"| `{term}` | "
        + " | ".join(
            "✓" if quadrant in covered[term] else "—" for quadrant in topics.QUADRANTS
        )
        + " |"
        for term in sorted(covered)
    ]
    return "\n".join([header, rule, *rows])


def _state_line(promoted: frozenset[str]) -> str:
    """Return the `STATE` marker carrying `promoted`, for the end of the body."""
    payload = json.dumps({"promoted": sorted(promoted)})
    return f"<!-- topics-state: {payload} -->"


def read_state(text: str) -> frozenset[str]:
    """Return the promoted set the previous run's body carried.

    This round trip is the report's one real failure mode (topics spec §3.8): a
    marker that cannot be read makes every month report every term as newly
    promoted, and the report would look like it was working -- it would be full
    of findings. So a body with no marker is refused rather than read as "there
    was no previous promoted set".

    Parameters
    ----------
    text : str
        The issue body, as read back from GitHub.

    Returns
    -------
    frozenset of str
        The promoted set the marker carries.

    Raises
    ------
    ValueError
        If no `STATE` marker is found in `text`.

    """
    match = STATE.search(text)
    if match is None:
        msg = "no topics-state marker found in the issue body"
        raise ValueError(msg)
    payload = json.loads(match.group("value"))
    return frozenset(payload["promoted"])


def changes(previous: frozenset[str], promoted: frozenset[str]) -> str | None:
    """Return a short paragraph naming what changed, or None if nothing did.

    Parameters
    ----------
    previous : frozenset of str
        The promoted set the last run reported, read back with `read_state`.
    promoted : frozenset of str
        This run's promoted set.

    Returns
    -------
    str or None
        GitHub-flavoured Markdown naming the terms newly promoted and the terms
        newly held back, or None when the two sets are equal -- the month this
        report says nothing, and posts no comment (topics spec §3.8, decision 1).

    """
    if previous == promoted:
        return None
    gained = sorted(promoted - previous)
    lost = sorted(previous - promoted)
    lines = []
    if gained:
        named = ", ".join(f"`{term}`" for term in gained)
        lines.append(f"Newly promoted: {named}.")
    if lost:
        named = ", ".join(f"`{term}`" for term in lost)
        lines.append(f"Newly held back: {named}.")
    return "\n".join(lines)


def body(
    items: Mapping[str, tuple[str, Sequence[str]]],
    promoted: frozenset[str],
    run_url: str,
) -> str:
    """Return the issue body (topics spec §3.8).

    The dashboard half of the report: the current picture, rewritten every run.
    What changed since the last run is never said here -- that is `changes`'
    job, posted as a comment and only where something moved.

    Parameters
    ----------
    items : mapping
        The corpus, as `corpus` returns.
    promoted : frozenset of str
        The terms that currently earn a filter button.
    run_url : str
        A link to the workflow run.

    Returns
    -------
    str
        GitHub-flavoured Markdown, ending in the `STATE` marker.

    """
    named = ", ".join(f"`{term}`" for term in sorted(promoted))
    lines = [
        (
            "The standing coverage report of topics spec §3.8. This body is the "
            "dashboard -- the current picture, rewritten every run -- and never "
            "the notification. What changed is posted as a comment on this "
            "issue, and only in a month the promoted set actually moved."
        ),
        "",
        f"## Promoted terms ({len(promoted)} of {len(topics.VOCABULARY)})",
        "",
        named or "None currently promoted.",
        "",
        "## Coverage matrix",
        "",
        matrix(items),
        "",
        ("An empty cell is a candidate for editorial judgement, not a defect."),
        (
            "The matrix can only see gaps between subjects already written "
            "about: the vocabulary is closed, so a topic nobody has documented "
            f"carries no term and appears nowhere here. #{DEMAND_SIGNAL} tracks "
            "the complementary demand signal, Read the Docs search analytics."
        ),
        "",
        f"**Run:** {run_url}",
        "",
        _state_line(promoted),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _standing_issue() -> tuple[str, str] | None:
    """Return the number and body of the standing issue, or None if none exists."""
    out = subprocess.run(  # noqa: S603 -- fixed argv, gh resolved off PATH
        [
            _gh(),
            "issue",
            "list",
            "--label",
            MARKER,
            "--state",
            "open",
            "--json",
            "number,body",
            "--limit",
            "1",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    found = json.loads(out)
    if not found:
        return None
    return str(found[0]["number"]), found[0]["body"] or ""


def main() -> int:
    """File or update the standing coverage issue.

    Returns
    -------
    int
        The process exit status.

    """
    parser = argparse.ArgumentParser(description="Report topic coverage.")
    parser.add_argument("--run-url", required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the body and exit, touching no network",
    )
    args = parser.parse_args()

    # `promote` raises on an empty corpus, and that is let through rather than
    # caught: a report that files successfully having read nothing is worse
    # than one that fails (topics spec §3.4).
    items = corpus(REPO)
    promoted = topics.promote(items)
    text = body(items, promoted, args.run_url)

    if args.dry_run:
        print(text)
        return 0

    found = _standing_issue()
    if found is None:
        try:
            subprocess.run(  # noqa: S603 -- fixed argv, gh resolved off PATH
                [
                    _gh(),
                    "issue",
                    "create",
                    "--title",
                    TITLE,
                    "--body",
                    text,
                    "--label",
                    MARKER,
                ],
                check=True,
            )
        except subprocess.CalledProcessError:
            # `gh issue create --label` fails on a label that does not exist,
            # and it is not this script's call to create one on the live
            # repository -- that is an outward-facing change and somebody's
            # deliberate decision. Comprehensible over a bare traceback: say
            # what the likely cause is and how to see the report anyway.
            print(
                f"error: could not create the standing issue. If the "
                f"'{MARKER}' label does not exist in this repository yet, "
                "create it by hand (gh label create) and re-run -- or run "
                "with --dry-run to read the report without filing anything.",
                file=sys.stderr,
            )
            return 1
        return 0

    number, previous_body = found
    # A body the marker cannot be read from is let raise (topics spec §3.8):
    # treating it as "nothing was promoted before" would report every term as
    # newly promoted, which looks like a working report and is not one.
    delta = changes(read_state(previous_body), promoted)
    subprocess.run(  # noqa: S603 -- fixed argv, gh resolved off PATH
        [_gh(), "issue", "edit", number, "--body", text], check=True
    )
    if delta is not None:
        subprocess.run(  # noqa: S603 -- fixed argv, gh resolved off PATH
            [_gh(), "issue", "comment", number, "--body", delta], check=True
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
