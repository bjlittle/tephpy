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

#: The two declaration sites of floors spec §3.1, by tier. pixi takes a floor
#: from either of two manifest tables, and both pair with the one requirements
#: file, so the pixi table named is the one the culprit is declared in and not
#: the one its tier declares most of its floors in (:issue:`151`).
SITES = {
    "core": {
        "dependencies": "[tool.pixi.dependencies]",
        "pypi-dependencies": "[tool.pixi.pypi-dependencies]",
        "requirements": "requirements/pypi-core.txt",
    },
    "test": {
        "dependencies": "[tool.pixi.feature.test.dependencies]",
        "pypi-dependencies": "[tool.pixi.feature.test.pypi-dependencies]",
        "requirements": "requirements/pypi-optional-test.txt",
    },
    "docs": {
        "dependencies": "[tool.pixi.feature.docs.dependencies]",
        "pypi-dependencies": "[tool.pixi.feature.docs.pypi-dependencies]",
        "requirements": "requirements/pypi-optional-docs.txt",
    },
    "devs": {
        "dependencies": "[tool.pixi.feature.devs.dependencies]",
        "pypi-dependencies": "[tool.pixi.feature.devs.pypi-dependencies]",
        "requirements": "requirements/pypi-optional-devs.txt",
    },
}

#: The order halves are reported in, so a two-half issue reads the same each
#: week whatever order the artifacts happened to download in.
HALVES = ("conda", "pypi")

#: Stands in for the package in the key and the title when nothing attributed.
#: The two must agree: `_open_issues` rebuilds each key from the title of an
#: issue already open, so a key that does not round-trip matches nothing and
#: the weekly run files another issue instead of commenting on the first.
UNATTRIBUTED = "unattributed"

#: How far the diagnosis got, as `floors_diagnose.attribute` records it. Three
#: of its four returns carry no package, and this is what tells them apart: the
#: verdict is the same at all three, but what ran to reach it is not, and every
#: unattributed issue used to be described as the relaxation loop running and
#: finding nothing -- true of one of the three (:issue:`188`).
#:
#: Deliberately *not* in the dedupe key, which is tier and package
#: (floors spec §3.6). A tier that fails to solve one week and fails its
#: exercise the next is one broken thing and belongs in one issue; keying on the
#: stage would file a second the week its failure changed shape.
#:
#: The same three words are declared in `floors_diagnose.py`, and
#: `tests/test_floors.py` holds the two lists together. A stage added there and
#: unhandled here does not go missing from the body -- it takes the wrong
#: sentence, which is the defect this field was added to fix.
STAGE_SOLVE = "solve"
STAGE_EXERCISE = "exercise"
STAGE_UNREPRODUCED = "unreproduced"
STAGES = (STAGE_SOLVE, STAGE_EXERCISE, STAGE_UNREPRODUCED)

#: What a stage this composer does not recognise reads as, and what a two-half
#: issue whose halves got different distances reads as. Every table below
#: carries an entry for it, so each lookup is total and the filing job cannot
#: die composing prose. The entries say nothing about what ran: a confident
#: wrong sentence is the thing being fixed here, and a vaguer true one is
#: strictly better than the wrong one it would otherwise inherit.
STAGE_UNKNOWN = ""

#: The precedent floors spec §3.5 cites, interpolated rather than written out.
#: This text is posted as an issue body, which is not Sphinx-rendered: the
#: `issue` role would reach the reader as its own source, and the bare form is
#: the one GitHub turns into a link -- so the rule the reference gate enforces
#: is met at this text's destination, by the form that gate reads as breaking
#: it. `changelog.py` composes its pull-request links the same way.
SPHINX_CLICK = 109

#: The other precedent, cited the same bare way as `SPHINX_CLICK` above.
#: :issue:`145` reported no passing `sphinx-design` of three tried, of a package whose
#: 0.6.1 is sound: every candidate was failing on `sphinx-autoapi`, which the
#: relaxed resolve had left at a version that cannot drive `astroid 4`.
SECOND_FLOOR = 145

ASYMMETRY = (
    "Attribution and the scan ask different questions, so *attributed a "
    "package, and no version of it passes* is a verdict rather than a "
    "contradiction. A relaxation is asked only whether the tier **resolves**; "
    "a scanned version has to resolve **and** pass that tier's exercise. Where "
    "the scan runs out, the reason is usually a second floor the relaxed "
    f"resolve left broken, and the trace below is where it is named (#{SECOND_FLOOR})."
)

CAVEAT = (
    "What the scan reports is the *lowest version that passes what tephpy "
    "runs*, which is a weaker claim than the lowest version that is correct. "
    "`sphinx-click 6.0.0` resolved, built the documentation clean under "
    "`--fail-on-warning` with both output gates green, and still rendered a "
    f"page differently from the pinned version (#{SPHINX_CLICK}). Read this "
    "as a starting point, not an answer."
)

#: What one half's diagnosis did to reach its verdict, by the stage it got that
#: far at. Floors spec §3.4 puts all three here by design and the verdict is
#: honest at each, but only `STAGE_SOLVE` is the relaxation loop running and
#: finding nothing. `{outcome}` is filled from `outcome` below, so the phrase a
#: reader meets is the same one either shape of this section uses.
#:
#: Per half rather than per issue, because the two halves are diagnosed
#: separately and can get different distances -- so this is what a two-half
#: issue puts on each of its two lines, and what a one-half issue opens with.
#: What is *not* here is anything that reads across the whole issue: that is
#: `UNATTRIBUTED_MEANS` below, said once or not at all.
UNATTRIBUTED_AT = {
    STAGE_SOLVE: "Relaxing each declared floor in turn resolved nothing, so {outcome}.",
    STAGE_EXERCISE: (
        "The declared floors resolved and the tier's exercise then failed, so "
        "no floor was relaxed at all and {outcome}."
    ),
    STAGE_UNREPRODUCED: (
        "The declared floors resolved and the tier's exercise then passed when "
        "re-run here, so no floor was relaxed and {outcome}."
    ),
    STAGE_UNKNOWN: (
        "The diagnosis reports that {outcome}, and did not record how far it "
        "got before saying so."
    ),
}

#: What the stage above means for the reader, and what the blocks quoted under
#: it hold. Split from `UNATTRIBUTED_AT` because it is about the stage and not
#: about one half's verdict: a two-half issue says it once where both halves got
#: the same distance, and where they did not it says nothing rather than
#: asserting of both what is true of one. Kept out of the per-half lines for the
#: same reason it is not repeated in a one-half issue -- twice is once too many,
#: and every sentence here names what is *below*, which is both halves' blocks.
UNATTRIBUTED_MEANS = {
    STAGE_SOLVE: "The solver output is below verbatim.",
    STAGE_EXERCISE: (
        "Relaxation attributes a *solve* failure, and this tier solved. What is "
        "quoted below is that exercise, not a solver conflict, and where the "
        "floors resolve the trace usually names the culprit on its own."
    ),
    STAGE_UNREPRODUCED: (
        "This diagnosis reproduced nothing: the failing step is one it does not "
        "run, and what is quoted below is a solve that succeeded."
    ),
    STAGE_UNKNOWN: "What is below is whatever the diagnosis kept.",
}

#: Where to start, for the sentence that says no declaration site is named.
#: Read from the whole group rather than from one finding: the two halves are
#: diagnosed separately and can get different distances, so one issue can carry
#: a solver conflict from one half and a pytest traceback from the other, and
#: neither name fits both. The `STAGE_UNREPRODUCED` entry sends the reader out
#: of the issue entirely, because what is quoted under it is a probe that
#: reproduced nothing -- said once, here, and not also in the sentence above,
#: which has already said what is quoted.
QUOTED = {
    STAGE_SOLVE: "the solver output below",
    STAGE_EXERCISE: "the trace below",
    STAGE_UNREPRODUCED: "the run log",
    STAGE_UNKNOWN: "the output quoted below",
}

#: How each quoted block is labelled. `failure at the declared floors` is true
#: of all three in the sense that those were the floors in force, but it reads
#: as the *solve* having failed -- and which of the three it was is the thing a
#: reader most needs and could not get (:issue:`188`). An attributed finding is
#: always `STAGE_SOLVE`, so its label is the one that has always been there.
SUMMARY = {
    STAGE_SOLVE: "failure at the declared floors",
    STAGE_EXERCISE: "exercise failure at the declared floors",
    STAGE_UNREPRODUCED: "the declared floors, which resolved and passed here",
    STAGE_UNKNOWN: "failure at the declared floors",
}


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


def stage(finding: dict) -> str:
    """Return how far the diagnosis of one finding got.

    Parameters
    ----------
    finding : dict
        One finding artifact.

    Returns
    -------
    str
        One of `STAGES`, or `STAGE_UNKNOWN` where this composer does not
        recognise what was recorded. A finding carrying no stage at all reads
        as `STAGE_SOLVE`: that is what every issue said before there was a
        stage to read, so an artifact from before then keeps the wording it
        was written under (:issue:`188`).

    """
    found = finding.get("stage") or STAGE_SOLVE
    return found if found in STAGES else STAGE_UNKNOWN


def agreed(group: Sequence[dict]) -> str | None:
    """Return the stage a whole group got to, or None where its halves differ.

    Parameters
    ----------
    group : sequence of dict
        Every finding this issue reports, the primary half first.

    Returns
    -------
    str or None
        The one stage of `STAGES`, or `STAGE_UNKNOWN`, that every finding
        reached; None where they reached more than one. The halves are
        diagnosed separately and can stop at different stages, so anything
        this issue says once about all of them has to ask first (:issue:`188`).

    """
    stages = {stage(item) for item in group}
    return stages.pop() if len(stages) == 1 else None


def _quoted(group: Sequence[dict]) -> str:
    """Name what the quoted blocks hold, as the stages of a whole group have it."""
    shared = agreed(group)
    return QUOTED[STAGE_UNKNOWN if shared is None else shared]


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


def said(finding: dict) -> str:
    """Say what one half's diagnosis did, and what it established by doing it.

    Parameters
    ----------
    finding : dict
        One finding artifact.

    Returns
    -------
    str
        `outcome` below where a culprit was attributed, the scan being the
        whole of what that half did that the reader needs. Where none was, the
        `UNATTRIBUTED_AT` sentence for the stage that half reached: the verdict
        alone is the same at all three and so says nothing about which of them
        ran, which is what a two-half issue used to leave the reader to guess
        at (:issue:`188`).

    """
    if finding["package"] is not None:
        return outcome(finding)
    return UNATTRIBUTED_AT[stage(finding)].format(outcome=outcome(finding))


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
        # A scan needs a culprit to scan, so an unattributed group ran none --
        # and "each half scanned its own source" over two lines that both say
        # nothing was attributed is the same assertion of work that never ran
        # this stage exists to stop making (:issue:`188`).
        each = (
            "Each half was diagnosed against its own source:"
            if finding["package"] is None
            else "Each half scanned its own source:"
        )
        lines += [
            f"Both halves failed, and they are one fix, so this is one issue. {each}",
            "",
            *[f"- **{item['half']}:** {said(item)}" for item in group],
            "",
        ]
        # Said once for the group, and only where the group agrees: every
        # sentence in it is about the stage rather than about one half, and
        # names what is quoted *below*, which is both halves' blocks. Where the
        # halves got different distances there is no such sentence to say, and
        # the per-half lines above have already said what each of them did.
        shared = agreed(group) if finding["package"] is None else None
        if shared is not None:
            lines += [UNATTRIBUTED_MEANS[shared], ""]
    elif finding["package"] is None:
        lines += [f"{said(finding)} {UNATTRIBUTED_MEANS[stage(finding)]}", ""]
    else:
        lines += [f"The scan found {outcome(finding)}.", ""]
    if any(item["lowest"] is None and item.get("blocked") for item in group):
        # Under the verdict it explains, ahead of what to do about it. Read
        # without this, "attributed X, and no version of X passes" says X has
        # no good version, and :issue:`145` was read that way about a package
        # whose 0.6.1 is fine. The two steps ask different questions, and the
        # gap between them is where a second broken floor hides. Said only
        # where a trace is quoted below, the text ending in a pointer to one:
        # a scan with no candidate to try ran out for another reason and has
        # nothing to show.
        lines += [ASYMMETRY, ""]
    if finding["package"] is None:
        # No package means no declaration to name. The tier that failed is not
        # it: core resolves into every tier (floors spec §3.1), so the tier's
        # own pair is a guess, and one that reads as established -- it would
        # send the reader to two files that need not declare anything to do
        # with the failure. The `test` tier is expected to produce a finding of
        # exactly this shape on the first run.
        lines += [
            (
                "No declaration site is named, because nothing was attributed "
                "and the tier that failed is not necessarily where the culprit "
                "is declared — the core table resolves into every tier. Start "
                f"from {_quoted(group)}."
            ),
            "",
        ]
    else:
        # The declaring table, not the tier that failed: core is resolved into
        # every tier, so a `test` run can attribute to a package declared in the
        # core table, whose two sites are a different pair (floors spec §3.1).
        site = SITES[finding.get("site") or finding["tier"]]
        table = site[finding.get("table") or "dependencies"]
        # The requirements file the floor is declared in, which is not always
        # the one the pixi table's tier pairs with: `setuptools_scm` is a `test`
        # requirement and a core declaration in the manifest. The diagnosis
        # answers this for both halves, so a missing key is a finding from
        # before it did; an empty one is an answer, and says there is no such
        # line -- `make` is declared for pixi alone.
        requirements = finding.get("requirements", site["requirements"])
        # And the name, which is not always the same at the two sites either.
        # The issue is keyed and titled on the manifest's spelling, so a reader
        # sent to the requirements file with only that would find no such line:
        # `matplotlib-base` is `matplotlib` there, `python-build` is `build`.
        alias = finding.get("alias")
        named = f" — declared there as `{alias}`" if alias else ""
        if requirements:
            lines += [
                (
                    "Both declaration sites need the same edit — a fix that "
                    "changes one and not the other leaves the two sides "
                    "disagreeing:"
                ),
                "",
                f"- `pyproject.toml`, `{table}`",
                f"- `{requirements}`{named}",
                "",
            ]
        else:
            lines += [
                (
                    f"Declared for pixi alone, in `pyproject.toml`, `{table}`. "
                    "The pip requirements carry no counterpart to edit, so this "
                    "is one line and not the usual two."
                ),
                "",
            ]
        lines += [CAVEAT, ""]
    for item in group:
        lines += [
            f"<details><summary>{SUMMARY[stage(item)]} ({item['half']})</summary>",
            "",
            "```text",
            item["failure"],
            "```",
            "",
            "</details>",
            "",
        ]
        if item.get("blocked"):
            lines += [
                (
                    f"<details><summary>{item['scanned'][-1]}, the highest "
                    "version tried, and what it failed on "
                    f"({item['half']})</summary>"
                ),
                "",
                "```text",
                item["blocked"],
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
