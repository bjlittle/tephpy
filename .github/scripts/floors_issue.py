#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Compose and dedupe dependency floor issues (floors spec §3.6).

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

MARKER = "dependency-floors"

#: The two declaration sites of floors spec §3.1, by tier.
SITES = {
    "core": ("[tool.pixi.dependencies]", "requirements/pypi-core.txt"),
    "test": (
        "[tool.pixi.feature.test.dependencies]",
        "requirements/pypi-optional-test.txt",
    ),
    "docs": (
        "[tool.pixi.feature.docs.dependencies]",
        "requirements/pypi-optional-docs.txt",
    ),
    "devs": (
        "[tool.pixi.feature.devs.dependencies]",
        "requirements/pypi-optional-devs.txt",
    ),
}

#: The order halves are reported in, so a two-half issue reads the same each
#: week whatever order the artifacts happened to download in.
HALVES = ("conda", "pypi")

#: Stands in for the package in the key and the title when nothing attributed.
#: The two must agree: `_open_issues` rebuilds each key from the title of an
#: issue already open, so a key that does not round-trip matches nothing and
#: the weekly run files another issue instead of commenting on the first.
UNATTRIBUTED = "unattributed"

#: The precedent floors spec §3.5 cites, interpolated rather than written out.
#: This text is posted as an issue body, which is not Sphinx-rendered: the
#: `issue` role would reach the reader as its own source, and the bare form is
#: the one GitHub turns into a link -- so the rule the reference gate enforces
#: is met at this text's destination, by the form that gate reads as breaking
#: it. `changelog.py` composes its pull-request links the same way.
SPHINX_CLICK = 109

CAVEAT = (
    "What the scan reports is the *lowest version that passes what tephpy "
    "runs*, which is a weaker claim than the lowest version that is correct. "
    "`sphinx-click 6.0.0` resolved, built the documentation clean under "
    "`--fail-on-warning` with both output gates green, and still rendered a "
    f"page differently from the pinned version (#{SPHINX_CLICK}). Read this "
    "as a starting point, not an answer."
)


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


def key(finding: dict) -> str:
    """Return the dedupe key: tier and package, never the half.

    Parameters
    ----------
    finding : dict
        One finding artifact.

    Returns
    -------
    str
        The key both halves of one floor share.

    """
    return f"{finding['tier']}/{finding['package'] or UNATTRIBUTED}"


def title(finding: dict) -> str:
    """Return the issue title.

    Parameters
    ----------
    finding : dict
        One finding artifact.

    Returns
    -------
    str
        A title carrying the dedupe key.

    """
    return f"Dependency floor: {finding['tier']} / {finding['package'] or UNATTRIBUTED}"


def outcome(finding: dict) -> str:
    """Say in one line what one half's scan established.

    Parameters
    ----------
    finding : dict
        One finding artifact.

    Returns
    -------
    str
        A phrase that reads both after ``The scan found`` and after a list
        item's label, so the two callers below need no wording of their own.

    """
    if finding["package"] is None:
        return "**no attribution was reached**"
    tried = len(finding["scanned"])
    if finding["lowest"] is None:
        return f"no version at or above the floor that passes, of {tried} tried"
    return f"**{finding['lowest']}**, the lowest that passes, of {tried} tried"


def body(finding: dict, run_url: str, others: Sequence[dict] = ()) -> str:
    """Return the issue body.

    Parameters
    ----------
    finding : dict
        The finding the title and the declared floor are taken from.
    run_url : str
        A link to the workflow run.
    others : sequence of dict, optional
        The same floor's findings from the other half. One floor is one
        issue, but a package can be at a different version in the conda
        channel and the package index, so each half reports its own scan
        (floors spec §3.5, §3.6).

    Returns
    -------
    str
        GitHub-flavoured Markdown.

    """
    # The declaring table, not the tier that failed: core is resolved into every
    # tier, so a `test` run can attribute to a package declared in the core
    # table, whose two declaration sites are a different pair (floors spec §3.1).
    table, requirements = SITES[finding.get("site") or finding["tier"]]
    group = [finding, *others]
    if others:
        named = " and ".join(item["half"] for item in group)
        where = f"{named} halves"
    else:
        where = f"{finding['half']} half"
    lines = [
        f"The `{finding['tier']}` tier failed at its declared floors ({where}).",
        "",
        f"- **package:** `{finding['package'] or UNATTRIBUTED}`",
        f"- **declared:** `{finding['declared'] or 'n/a'}`",
        f"- **run:** {run_url}",
        "",
    ]
    if others:
        lines += [
            (
                "Both halves failed, and they are one fix, so this is one "
                "issue. Each half scanned its own source:"
            ),
            "",
            *[f"- **{item['half']}:** {outcome(item)}" for item in group],
            "",
        ]
    elif finding["package"] is None:
        lines += [
            (
                "Relaxing each declared floor in turn resolved nothing, so "
                f"{outcome(finding)}. The solver output is below verbatim."
            ),
            "",
        ]
    else:
        lines += [f"The scan found {outcome(finding)}.", ""]
    lines += [
        (
            "Both declaration sites need the same edit — a fix that changes "
            "one and not the other leaves the two sides disagreeing:"
        ),
        "",
        f"- `pyproject.toml`, `{table}`",
        f"- `{requirements}`",
        "",
        CAVEAT,
        "",
    ]
    for item in group:
        lines += [
            f"<details><summary>failure ({item['half']})</summary>",
            "",
            "```text",
            item["failure"],
            "```",
            "",
            "</details>",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def _open_issues() -> dict[str, str]:
    """Map the dedupe key of every open marker-labelled issue to its number."""
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
            "number,title",
            "--limit",
            "200",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    found = {}
    for issue in json.loads(out):
        prefix = "Dependency floor: "
        if issue["title"].startswith(prefix):
            found[issue["title"].removeprefix(prefix).replace(" / ", "/")] = str(
                issue["number"]
            )
    return found


def group(findings: Sequence[dict]) -> dict[str, list[dict]]:
    """Collect findings by dedupe key, each group in a stable half order.

    Parameters
    ----------
    findings : sequence of dict
        Every finding artifact this run produced.

    Returns
    -------
    dict
        Dedupe key to the findings sharing it.

    """
    grouped: dict[str, list[dict]] = {}
    for finding in findings:
        grouped.setdefault(key(finding), []).append(finding)
    order = {half: index for index, half in enumerate(HALVES)}
    for entries in grouped.values():
        entries.sort(key=lambda item: order.get(item["half"], len(order)))
    return grouped


def main() -> int:
    """File or comment on one issue per floor, both halves together.

    Returns
    -------
    int
        The process exit status.

    """
    parser = argparse.ArgumentParser(description="File dependency floor issues.")
    parser.add_argument("artifacts", type=Path, nargs="+")
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()

    paths = [path for path in args.artifacts if path.is_file()]
    if not paths:
        # This job runs only when a tier failed, so nothing to read means the
        # diagnosis never wrote its artifact -- and an unmatched shell glob
        # arrives here as a path that does not exist. Exiting 0 would be
        # indistinguishable from a run that found nothing to file.
        print(
            f"error: no finding artifacts among {[str(p) for p in args.artifacts]}",
            file=sys.stderr,
        )
        return 1

    findings = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    existing = _open_issues()
    for name, entries in group(findings).items():
        primary, others = entries[0], entries[1:]
        text = body(primary, args.run_url, others)
        number = existing.get(name)
        if number is None:
            subprocess.run(  # noqa: S603 -- fixed argv, gh resolved off PATH
                [
                    _gh(),
                    "issue",
                    "create",
                    "--title",
                    title(primary),
                    "--body",
                    text,
                    "--label",
                    MARKER,
                    "--label",
                    "type: dependencies",
                ],
                check=True,
            )
        else:
            subprocess.run(  # noqa: S603 -- fixed argv, gh resolved off PATH
                [_gh(), "issue", "comment", number, "--body", text], check=True
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
