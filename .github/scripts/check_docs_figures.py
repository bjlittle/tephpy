#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that every figure the user documentation publishes is the approved one.

The how-to guides that teach a visual API render their own snippets as figures
through ``matplotlib.sphinxext.plot_directive`` (plots spec §3.1). The snippet
gate of docs spec §3.9 already runs that code on every supported Python, so a
snippet that stops working fails there. What it cannot see is the second failure
a rendered page adds: a snippet that still runs and no longer *shows* what its
prose claims. This gate is that check (plots spec §3.5).

It runs on the documentation side, against the images the build just produced,
because what is worth pinning is the artifact that ships and it exists only in
the build. Re-rendering the same code in the test environment and comparing that
would pin a second render whose agreement with the published one rests on
several settings staying aligned, with nothing checking the alignment.

The expected set is not a glob of the build's ``_images/``. That directory also
holds the browser demo's toolbar icons, and a glob cannot tell a plot from an
icon -- adding one non-plot image would turn this gate red for a file it was
never meant to judge, while a plot silently *not* built is the failure it exists
to catch. The names come instead from the ``:filename-prefix:`` each directive
declares on the page, which makes the page the registry and lets a declared
figure that was never built be reported as missing.

The page is parsed here rather than imported from ``tests/``: the sdist ships
the tests and prunes ``.github``, so this script cannot be a consumer of that
module, and a second implementation of a two-line pattern is the cheaper half of
that trade. It is also the half that catches a bug in the other one.

Three things are checked. Every declared figure was built. Every baseline is
claimed by a declaration, so a renamed section leaves no orphan behind. And each
declared/built pair matches its baseline within tolerance, by matplotlib's own
comparator -- the same RMS measure ``pytest-mpl`` applies to ``tests/baseline``.

An empty declared set fails. A gate that finds nothing to check and exits ``0``
reports a green tick over nothing, which is what docs spec §3.9's own corpus
refusals were written against.

What this does *not* do is judge whether a figure is a good illustration. It
pins what was published against what was approved; a diagram that draws
correctly and teaches nothing is review's to catch.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from pathlib import Path
import re
import sys
import textwrap
from typing import NamedTuple

from matplotlib.image import imread
from matplotlib.testing.compare import compare_images
from matplotlib.testing.exceptions import ImageComparisonFailure

#: The Diátaxis quadrants written for users, which are the pages that may publish
#: a figure (plots spec §3.2).
QUADRANTS = ("howtos", "tutorials", "explanation")
#: The pages known to publish figures. Membership, not a count: a count is a
#: figure that has to be re-measured to stay true. This is what fails when the
#: declaration pattern stops matching, instead of the gate finding nothing and
#: reporting that nothing was wrong.
PUBLISHES = (
    "explanation/parcel-ascent.rst",
    "explanation/rotated-axes.rst",
    "howtos/emphasis.rst",
    "howtos/framing.rst",
    "howtos/logo.rst",
    "howtos/temp-and-bufr.rst",
    "tutorials/analyse-a-sounding.rst",
    "tutorials/first-tephigram.rst",
)
#: A figure declaration: the ``:filename-prefix:`` option of a ``.. plot::``. The
#: directive line is matched too, so an option of that name under some other
#: directive is not read as a figure this project publishes.
DECLARATION = re.compile(
    r"^[ ]*\.\.[ ]+plot::.*$(?:\n^[ ]*:[\w-]+:.*$)*?"
    r"\n^[ ]*:filename-prefix:[ ]*(?P<prefix>[\w.-]+)[ ]*$",
    re.MULTILINE,
)
#: The same shape as :data:`DECLARATION`, widened rather than narrowed: any
#: indentation character (a tab as well as a space), a value captured whole
#: rather than restricted to word characters, dots and dashes, and the option
#: name read without regard to case -- docutils lowercases a directive's
#: option names, so ``:Filename-Prefix:`` is a real declaration and not a
#: typo. ``DECLARATION`` stays case-sensitive: widening it would make this
#: gate *accept* the variant sight unseen rather than report it. What this
#: still matches and :data:`DECLARATION` does not is a declaration invisible
#: to the strict pattern -- a fail-open it alone cannot report. The sibling
#: gate on these same pages carries a near-miss detector of its own, on the
#: same principle: detection wider than validation (plots spec §3.4).
CANDIDATE = re.compile(
    r"^[ \t]*\.\.[ ]+plot::.*$(?:\n^[ \t]*:[\w-]+:.*$)*?"
    r"\n^[ \t]*:filename-prefix:[ \t]*(?P<prefix>.*)$",
    re.MULTILINE | re.IGNORECASE,
)
#: Where the build collects the images a page references. Sphinx puts only
#: referenced images here, so a ``:nofigs:`` block's render never arrives and
#: cannot be mistaken for a published figure.
IMAGES = "_images"
#: The extension the sole configured output format produces (plots spec §3.1).
SUFFIX = ".png"
#: The RMS difference tolerated between a published figure and its baseline,
#: which is ``pytest-mpl``'s default and so the figure the rest of this project's
#: image comparison already uses.
TOLERANCE = 2
#: How many offenders of one kind to name before counting the rest.
SHOWN = 6
#: What to do about a figure a page declares and the build did not produce.
MISSING = (
    "The page declares this figure and the build produced no such image. Sphinx "
    "collects into '_images' only what a page references, so the usual cause is "
    "a directive carrying both ':filename-prefix:' and ':nofigs:' -- it renders "
    "an image the page never shows, under a name this gate then looks for. The "
    "other cause is a block that leaves two figures open: matplotlib then "
    "numbers them '<prefix>_00.png' and '<prefix>_01.png' instead of writing "
    "the bare name, so the declaration goes unbuilt while both numbered images "
    "are published and pinned by nothing. Either drop the ':nofigs:' and "
    "publish the figure, close the surplus figure so exactly one remains, or "
    "drop the name."
)
#: What to do about a baseline no page claims.
ORPHANED = (
    "No page declares this figure, so nothing compares against this baseline. A "
    "renamed ':filename-prefix:' leaves the old baseline behind, where it goes "
    "on being shipped and never again being read. Delete it, or restore the "
    "declaration that named it."
)
#: What to do about a figure with no baseline at all.
UNAPPROVED = (
    "The page declares this figure and no baseline exists to compare it "
    "against, so what it publishes has never been approved. Run 'pixi run "
    "docs-figures' to bless the build's output, then read the diff before "
    "committing it: that command approves whatever was rendered, including a "
    "regression."
)
#: What to do about a figure that no longer matches its baseline.
CHANGED = (
    "The published figure has drifted from the one that was approved. This is "
    "the failure this gate exists to catch: the snippet still runs, and no "
    "longer draws what the page's prose describes. A pixel-size change is "
    "reported above with both sizes and writes no diff to open; anything else "
    "has a '-failed-diff.png' written beside the built image. If the change is "
    "wrong, fix the code or the snippet; if it is intended, run 'pixi run "
    "docs-figures' to re-bless it and commit the new baseline with the change "
    "that caused it."
)
#: What to do about a documentation tree that declares no figure anywhere.
EMPTY = (
    "No page declares a figure, so this gate has nothing to compare and a "
    "search of nothing finds nothing wrong. Either the pages stopped publishing "
    "figures -- in which case remove this gate rather than leaving it green -- "
    "or the declaration pattern has stopped matching them."
)
#: What to do about a page that is supposed to publish figures and does not.
UNRECOGNISED = (
    "This page is listed in PUBLISHES and declares no figure. The list names "
    "the pages whose figures are meant to be pinned; a page missing from the "
    "scan is not reported by any other check here, because every check reads "
    "the declarations. Restore the page's declarations, or remove it from "
    "PUBLISHES if it deliberately stopped publishing."
)
#: What to do about something that looks like a declaration and is not read
#: as one.
MALFORMED = (
    "This looks like a ':filename-prefix:' declaration and is not read as "
    "one, which is worse than declaring nothing: the page appears to publish "
    "the figure, and no baseline is ever compared against it. The three "
    "shapes this misses are a value that contains whitespace, a line indented "
    "with a tab rather than spaces, and an option name spelled in some other "
    "case, such as ':Filename-Prefix:'. Rewrite the value as one run of "
    "letters, digits, dots and dashes, indent every line of the block with "
    "spaces only, and spell the option name in lowercase."
)


class Figure(NamedTuple):
    """One declared figure, and where its three files are."""

    #: The ``:filename-prefix:`` the page declared.
    name: str
    #: The page that declared it, relative to the documentation source root.
    page: str
    #: The image the build produced, which may not exist.
    built: Path
    #: The approved image, which may not exist.
    baseline: Path


def declarations(text: str) -> list[str]:
    """Read the figure names a page declares.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    list of str
        The ``:filename-prefix:`` values, in document order.

    """
    return [match["prefix"] for match in DECLARATION.finditer(text)]


def malformed(text: str) -> list[str]:
    """Read every ``:filename-prefix:`` that :data:`DECLARATION` fails to accept.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    list of str
        The raw value of each such declaration, in document order.

    """
    strict = {match.start() for match in DECLARATION.finditer(text)}
    return [
        match["prefix"].strip()
        for match in CANDIDATE.finditer(text)
        if match.start() not in strict
    ]


def collect(source: Path, images: Path, baselines: Path) -> list[Figure]:
    """Gather every figure the user documentation declares.

    Parameters
    ----------
    source : Path
        The documentation source root holding the quadrant directories.
    images : Path
        The built ``_images`` directory.
    baselines : Path
        The directory holding the approved images.

    Returns
    -------
    list of Figure
        One entry per declaration, quadrant by quadrant and sorted within each.

    """
    found: list[Figure] = []
    for quadrant in QUADRANTS:
        for page in sorted((source / quadrant).rglob("*.rst")):
            text = page.read_text(encoding="utf-8")
            found.extend(
                Figure(
                    name=name,
                    page=page.relative_to(source).as_posix(),
                    built=images / f"{name}{SUFFIX}",
                    baseline=baselines / f"{name}{SUFFIX}",
                )
                for name in declarations(text)
            )
    return found


def offenders(title: str, lines: list[str], advice: str) -> bool:
    """Report one kind of failure, truncated to :data:`SHOWN`.

    Parameters
    ----------
    title : str
        The headline, naming what went wrong.
    lines : list of str
        One line per offender, already formatted.
    advice : str
        What to do about it.

    Returns
    -------
    bool
        Whether anything was reported.

    """
    if not lines:
        return False
    print(f"{title}:")
    for line in lines[:SHOWN]:
        print(f"  {line}")
    if len(lines) > SHOWN:
        print(f"  ... and {len(lines) - SHOWN} more")
    print(f"\n{textwrap.fill(advice)}\n")
    return True


def unreadable(source: Path, figures: list[Figure]) -> bool:
    """Report every declaration this scan failed to read.

    Both commands stop here rather than act on a set of figures known to be
    short, because nothing downstream can tell a declaration that went unread
    from one that was renamed away. To this gate the figure's baseline is an
    orphan, and :data:`ORPHANED` advises deleting it; to the blessing command
    it is an orphan too, and that command deletes it. Either way the figure
    ends up published and pinned by nothing -- the very failure the near-miss
    detector exists to report, reached through the remedy for it.

    Parameters
    ----------
    source : Path
        The documentation source root holding the quadrant directories.
    figures : list of Figure
        Every declaration read from that root.

    Returns
    -------
    bool
        Whether anything was reported.

    """
    garbled = []
    for quadrant in QUADRANTS:
        for page in sorted((source / quadrant).rglob("*.rst")):
            text = page.read_text(encoding="utf-8")
            relative = page.relative_to(source).as_posix()
            garbled.extend(f"{value!r} ({relative})" for value in malformed(text))
    garbled.sort()
    # The near miss is reported first because it is the cause: a page whose
    # every declaration is malformed declares nothing, so it reports under both
    # headings, and only this one says which character to fix.
    failed = offenders(
        "these look like declarations and are not read", garbled, MALFORMED
    )
    silent = sorted(set(PUBLISHES) - {figure.page for figure in figures})
    failed |= offenders("these pages declare no figure", silent, UNRECOGNISED)
    return failed


def main() -> int:
    """Check the built figures against their baselines.

    Returns
    -------
    int
        ``0`` when every published figure matches, ``1`` otherwise.

    """
    if len(sys.argv) < 2:
        print("usage: check_docs_figures.py <html-root> [source-root] [baselines]")
        return 1
    root = Path(sys.argv[1])
    repo = Path(__file__).parents[2]
    source = Path(sys.argv[2]) if len(sys.argv) > 2 else repo / "docs" / "src"
    baselines = Path(sys.argv[3]) if len(sys.argv) > 3 else repo / "docs" / "baseline"
    for directory in (root, source):
        if not directory.is_dir():
            print(f"no such directory: {directory}")
            return 1

    figures = collect(source, root / IMAGES, baselines)
    if not figures:
        print("no page declares a figure")
        print(f"\n{textwrap.fill(EMPTY)}")
        print("\nSee 'Published Figures' in docs/src/developer/docs-style.rst.")
        return 1

    # Every check below reads this set, so an unread declaration makes all of
    # them judge a short one -- where a live baseline is indistinguishable from
    # an orphan. Report that and stop, rather than add advice to delete it.
    if unreadable(source, figures):
        print("See 'Published Figures' in docs/src/developer/docs-style.rst.")
        return 1

    missing, unapproved, changed = [], [], []
    for figure in sorted(figures):
        if not figure.built.is_file():
            missing.append(f"{figure.name} ({figure.page})")
        elif not figure.baseline.is_file():
            unapproved.append(f"{figure.name} ({figure.page})")
        else:
            try:
                # `in_decorator=True` is what returns the measurement as a
                # mapping; the default returns a formatted string, whose RMS
                # could only be recovered by parsing prose matplotlib is free
                # to reword.
                result = compare_images(
                    str(figure.baseline),
                    str(figure.built),
                    TOLERANCE,
                    in_decorator=True,
                )
            except ImageComparisonFailure:
                # Raised rather than returned when the two images differ in
                # pixel size -- `plot_rcparams`'s figure size is one config
                # change away from breaking every baseline this way, so this
                # is not hypothetical. There is no RMS to report, since there
                # is no pixel-for-pixel comparison to make; each image's own
                # size, read independently, stands in for it rather than the
                # raised message, which matplotlib is as free to reword as the
                # string form `in_decorator=False` returns.
                changed.append(
                    f"{figure.name} (size {imread(figure.built).shape[:2]} != "
                    f"baseline {imread(figure.baseline).shape[:2]})"
                )
            else:
                if result is not None:
                    changed.append(
                        f"{figure.name} (RMS {result['rms']:.2f}, "
                        f"tolerance {result['tol']})"
                    )

    claimed = {figure.baseline for figure in figures}
    orphaned = sorted(
        path.name for path in baselines.glob(f"*{SUFFIX}") if path not in claimed
    )

    failed = offenders("these declared figures were not built", missing, MISSING)
    failed |= offenders("these figures have no baseline", unapproved, UNAPPROVED)
    failed |= offenders("these figures no longer match", changed, CHANGED)
    failed |= offenders("these baselines are claimed by no page", orphaned, ORPHANED)
    if failed:
        print("See 'Published Figures' in docs/src/developer/docs-style.rst.")
        return 1

    pages = len({figure.page for figure in figures})
    print(
        f"published figures ok: {len(figures)} compared within RMS {TOLERANCE}, "
        f"across {pages} page{'' if pages == 1 else 's'} (plots spec §3.5)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
