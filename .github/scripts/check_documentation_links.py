#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that every documentation link in tracked source resolves in the build.

A few tracked files reach the documentation by absolute URL, because they are not
sources of the Sphinx project and have no role to write instead: ``README.md`` is
the repository's landing page, and a script that fails a contributor sends them to
the page that explains why. Nothing in the build sees those links -- ``nitpicky``
checks the references Sphinx itself resolved, and the rendered-citation gate reads
only pages the build produced. Meanwhile a glossary anchor is derived from the term
-- Sphinx keeps the case and collapses each run of non-alphanumeric characters to a
single hyphen, so ``Normand's point`` becomes ``term-Normand-s-point`` -- which
makes renaming a term a silent way to break the landing page, and moving a page
another.

This gate closes that gap from the outside. ``SOURCES`` names the files it reads:
an explicit list rather than a sweep of the repository, because a sweep would judge
whatever happened to be quoted in a test fixture or a frozen implementation plan,
and a plan is meant to go on naming the URL it named. Each URL is looked up in the
HTML the build has just produced: the page must exist, and a fragment must name an
``id`` on it. Nothing here reproduces the slug rule, because the ids are read off
the built page rather than derived. A normalisation of our own would be one more
thing able to drift from Sphinx, which is the drift this gate exists to catch.

Only the canonical ``en/latest`` URL can be looked up that way, so a link onto a
documentation host of this project written any other way is reported rather than
skipped in silence. A per-pull-request preview is where a documentation change is
verified and the wrong place to link from tracked source, because Read the Docs
deletes it when the pull request closes; and ``latest`` is the only version this
project publishes.

A listed source carrying no documentation link at all fails too. A check is worth
what it covers, and a rewrite that dropped every link from one source would
otherwise pass in silence while that source quietly left the check behind.

Three things are deliberately not checked. That a link points at the *right* page
is a question about meaning, not resolution, and no gate can answer it. An
``en/latest`` URL is checked against the working tree's own build, which is the
only build available -- a link correct here is wrong on the published site until
this branch merges, and that is the ordinary lag of source that names a moving
target. And a URL on a documentation host of this project whose path never says
``.html`` is passed over rather than judged: it is how the Read the Docs badge,
which points at the base with a query string, stays out of the report, and it lets
through a directory-style URL, which Read the Docs does resolve and which carries
no page or anchor to look up.

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

#: The published documentation, which each listed source links into.
BASE = "https://tephpy.readthedocs.io/en/latest/"
#: The tracked files this gate reads, relative to the repository root. A file earns
#: a place here by writing an absolute documentation URL somewhere no Sphinx build
#: can see it. Keep the list short and deliberate: it is the statement of which
#: links the project means to keep working, and everything not on it is unchecked.
SOURCES = ("README.md", ".github/scripts/changelog.py")
#: A link into a documentation page, with the fragment it names, if any. Only a
#: path ending in ``.html`` is a page: the Read the Docs badge points at the base
#: with a query string and no path, and names nothing this gate can look up.
LINK = re.compile(re.escape(BASE) + r"([\w./-]+\.html)(?:#([\w.:-]+))?")
#: Any URL onto a documentation host of this project -- the published site, or a
#: per-pull-request Read the Docs preview. The match stops before whitespace, ``)``,
#: ``]`` and either quote, which is where a URL ends in the two kinds of source
#: checked here: a Markdown inline link or reference definition, and a string
#: literal in a script. A character missing from this set is swallowed into the
#: URL, which turns a good link into a reported one. Either scheme matches,
#: deliberately: this pattern decides what gets *judged*, so narrowing it to
#: ``https`` would make a plaintext link invisible to the gate instead of
#: non-canonical.
DOCS = re.compile(
    r"https?://(?:tephpy\.readthedocs\.io"
    r"|tephpy--[\w.-]+?\.org\.readthedocs\.build)[^\s)\]'\"]*"
)
#: An ``id`` attribute in the built HTML, which is what a fragment must name.
ID = re.compile(r'\bid="([^"]+)"')
#: How many offenders of one kind to name before counting the rest.
SHOWN = 6
#: What to do about a link naming a page the build did not produce.
MISSING_PAGE = (
    "The build produced no such page. A page that is renamed or moved leaves the "
    "source pointing at a URL Read the Docs answers with a 404, and the build "
    "cannot notice, because the source is not one of its inputs. Update the link "
    "to the path the page now has, or restore the page under the path the source "
    "names."
)
#: What to do about a link naming a fragment its page does not carry.
MISSING_ANCHOR = (
    "The page renders, but nothing on it carries that id. A glossary anchor is "
    "derived from the term: Sphinx keeps the case and collapses each run of "
    "non-alphanumeric characters to a single hyphen, so renaming a term moves its "
    "anchor and the source goes on naming where it used to be. Copy the id out of "
    "the built page rather than deriving it by hand."
)
#: What to do about a link into the documentation written some other way.
NOT_CANONICAL = (
    "Only 'https://tephpy.readthedocs.io/en/latest/<page>.html' is checked here, "
    "and it is the only form that goes on working. A per-pull-request preview "
    "host ('tephpy--<pr>.org.readthedocs.build') is where a documentation change "
    "is verified, not where a link belongs: Read the Docs deletes the preview "
    "when the pull request closes. And 'latest' is the only version published -- "
    "there is no 'stable' until the project releases -- so a URL naming another "
    "version, or naming none at all, is a 404 waiting to be clicked. The form is "
    "exact in its two quieter parts as well: the scheme is 'https', because "
    "'http' arrives only by a redirect Read the Docs is under no obligation to "
    "keep offering, and the path stops at the page, because text after '.html' "
    "names a file the build never produced. Rewrite the URL in the canonical form."
)
#: What to do about SOURCES with no source left in it.
EMPTY_SOURCES = (
    "SOURCES is empty, so the gate has nothing to read, and a search of nothing "
    "finds nothing wrong. The list is the statement of which links the project "
    "means to keep working; a gate that passes on an empty one is a green tick "
    "over nothing. Restore the entry that was removed."
)
#: What to do about a listed source that links into the documentation nowhere.
BLIND = (
    "A source with no documentation link is not one this check can check, so it "
    "fails rather than passing on an empty search. Each source is listed because "
    "it writes a documentation URL where no Sphinx build can see it; one that no "
    "longer does has nothing left to go wrong and no reason to stay listed. "
    "Remove it from SOURCES, or restore the link."
)


class Report(NamedTuple):
    """What one checked source's documentation links came to."""

    found: list[tuple[str, str]]
    absent: list[str]
    broken: list[str]
    stray: list[str]
    pages: set[str]


def links(text: str) -> list[tuple[str, str]]:
    """Find every canonically written documentation link in one source.

    Parameters
    ----------
    text : str
        The source file's text.

    Returns
    -------
    list of tuple of str
        The page path and fragment of each canonical link, in the order they
        were written, with ``""`` for a link naming no fragment.

    Notes
    -----
    Each URL is taken whole and then matched, rather than searched for a
    canonical form somewhere inside it. Searching would settle for a prefix:
    the page pattern is greedy but backtracks to the last ``.html`` it can end
    on, so ``glossary.html.bak`` would read as the page ``glossary.html`` --
    which the build does produce. That records a resolving link and throws away
    the very text that makes the URL a 404.

    """
    canonical = (LINK.fullmatch(url) for url in DOCS.findall(text))
    return [
        (match.group(1), match.group(2) or "")
        for match in canonical
        if match is not None
    ]


def path(url: str) -> str:
    """Take the path out of a URL, dropping any fragment and query string.

    Parameters
    ----------
    url : str
        A documentation URL, as a source writes it.

    Returns
    -------
    str
        Everything the URL says before the first ``#`` or ``?``.

    """
    return url.split("#", 1)[0].split("?", 1)[0]


def strays(text: str) -> list[str]:
    """Find every documentation link one source writes non-canonically.

    Parameters
    ----------
    text : str
        The source file's text.

    Returns
    -------
    list of str
        Each URL onto a documentation host of this project whose path says
        ``.html`` and which is not the canonical form, sorted, and once each:
        the same wrong URL written twice is one thing to fix. A URL whose path
        never says ``.html`` is passed over -- it is how the Read the Docs
        badge stays out of the report, and a directory-style URL resolves while
        carrying nothing to look up.

    Notes
    -----
    The path has to *say* ``.html`` rather than end in it, so that a URL going
    on past the page -- ``glossary.html.bak``, ``glossary.html/extra`` -- is
    judged here instead of being waved through as a directory. Nothing follows
    a page on this site, so text after ``.html`` is a 404, not a folder.

    """
    return sorted(
        {
            url
            for url in DOCS.findall(text)
            if not LINK.fullmatch(url) and ".html" in path(url)
        }
    )


def anchors(page: Path) -> set[str]:
    """Collect every id one built page carries.

    Parameters
    ----------
    page : pathlib.Path
        A page of the built HTML.

    Returns
    -------
    set of str
        Its ``id`` attributes, which are the fragments it can answer.

    """
    return set(ID.findall(page.read_text(encoding="utf-8")))


def listed(found: list[str]) -> str:
    """Name the first few offenders, and say how many are not named.

    Parameters
    ----------
    found : list of str
        The offenders of one kind.

    Returns
    -------
    str
        The listing. A report that bounds what it shows says what it dropped;
        a count quietly smaller than the total reads as a smaller problem.

    """
    rest = len(found) - SHOWN
    listing = ", ".join(found[:SHOWN])
    return f"{listing} and {rest} more" if rest > 0 else listing


def scan(text: str, root: Path) -> Report:
    """Look every documentation link in one source up in the built HTML.

    Parameters
    ----------
    text : str
        The source file's text.
    root : pathlib.Path
        The root of the HTML the build produced.

    Returns
    -------
    Report
        What that source's links came to, with the pages named rather than
        counted, so several sources naming one page count it once.

    """
    found = links(text)
    ids: dict[str, set[str] | None] = {}
    for page, _ in found:
        if page not in ids:
            built = root / page
            ids[page] = anchors(built) if built.is_file() else None
    return Report(
        found=found,
        absent=sorted(page for page, carried in ids.items() if carried is None),
        # Keyed by page and fragment together, so one broken anchor named twice in
        # one source is one thing to fix and is reported as one.
        broken=sorted(
            {
                f"{page}#{anchor}"
                for page, anchor in found
                # An absent page carries no ids to miss; it is reported as absent.
                if anchor and ids[page] is not None and anchor not in ids[page]
            }
        ),
        stray=strays(text),
        pages=set(ids),
    )


def plural(count: int, noun: str) -> str:
    """Give ``noun`` the ending ``count`` calls for.

    Parameters
    ----------
    count : int
        How many of the thing there are.
    noun : str
        Its singular form.

    Returns
    -------
    str
        ``noun`` written for that count. A report that says "1 pages" reads as one
        nobody has looked at, which invites the reader to distrust the number
        beside it.

    """
    return noun if count == 1 else f"{noun}s"


def gathered(picked: dict[str, list[str]], *, tagged: bool) -> list[str]:
    """Collect one kind of offender from every source, once each.

    Parameters
    ----------
    picked : dict of (str, list of str)
        The offenders of one kind, keyed by the source they were found in, named
        as it was given.
    tagged : bool
        Whether to name the source each offender came from.

    Returns
    -------
    list of str
        The offenders, sorted and once each. Every list a Report carries is
        already unique -- absent comes from dict keys, broken and stray are
        already sets -- so nothing passed in here can repeat; the set below is
        defence against that guarantee lapsing later, not a duplicate this
        function has ever had to resolve.

    """
    return sorted(
        {
            f"{entry} ({name})" if tagged else entry
            for name, entries in picked.items()
            for entry in entries
        }
    )


def verdict(reports: dict[str, Report]) -> int:
    """Print what every source's links came to, and say whether the run passed.

    Split out of ``main`` so that a run reaching this point -- every source
    read, none of them blind -- has one way out instead of adding another
    return statement to a function that already has one for every earlier way
    a run can fail.

    Parameters
    ----------
    reports : dict of (str, Report)
        Each checked source's report, keyed by the name it was given.

    Returns
    -------
    int
        ``0`` when every link resolves, ``1`` otherwise.

    """
    # One source names itself in the invocation, so attributing every entry to it
    # is noise; more than one, and a bare page path does not say which file to open.
    tagged = len(reports) > 1
    absent = gathered(
        {name: report.absent for name, report in reports.items()}, tagged=tagged
    )
    broken = gathered(
        {name: report.broken for name, report in reports.items()}, tagged=tagged
    )
    stray = gathered(
        {name: report.stray for name, report in reports.items()}, tagged=tagged
    )

    if not absent and not broken and not stray:
        checked = sum(len(report.found) for report in reports.values())
        anchored = sum(
            1 for report in reports.values() for _, anchor in report.found if anchor
        )
        pages = {page for report in reports.values() for page in report.pages}
        print(
            f"Documentation links ok: {checked} checked across "
            f"{len(reports)} {plural(len(reports), 'source')}, "
            f"{anchored} naming an anchor, across "
            f"{len(pages)} {plural(len(pages), 'page')}"
        )
        return 0
    if absent:
        print(f"Missing pages ({len(absent)}):")
        print(f"  {listed(absent)}")
        print(f"\n{textwrap.fill(MISSING_PAGE)}")
    if broken:
        print(f"\nMissing anchors ({len(broken)}):")
        print(f"  {listed(broken)}")
        print(f"\n{textwrap.fill(MISSING_ANCHOR)}")
    if stray:
        print(f"\nNon-canonical URLs ({len(stray)}):")
        print(f"  {listed(stray)}")
        print(f"\n{textwrap.fill(NOT_CANONICAL)}")
    print("\nSee 'Documentation Links' in docs/src/developer/docs-style.rst.")
    return 1


def main() -> int:
    """Check each source's documentation links against the built HTML.

    Returns
    -------
    int
        ``0`` when every link resolves, ``1`` otherwise.

    """
    if len(sys.argv) < 2:
        print("usage: check_documentation_links.py <html-root> [source ...]")
        return 1
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"no such directory: {root}")
        return 1
    repo = Path(__file__).parents[2]
    # Named as given, so a listed source is reported by the path that finds it in
    # the repository rather than by a basename two sources could share.
    named = [(name, Path(name)) for name in sys.argv[2:]]
    sources = named or [(name, repo / name) for name in SOURCES]
    # Reachable only through SOURCES: sources named on the command line are never
    # empty, since an empty sys.argv[2:] is exactly what falls back to SOURCES.
    if not sources:
        print("SOURCES lists no source to check")
        print(f"\n{textwrap.fill(EMPTY_SOURCES)}")
        print("\nSee 'Documentation Links' in docs/src/developer/docs-style.rst.")
        return 1

    reports: dict[str, Report] = {}
    for name, source in sources:
        if not source.is_file():
            print(f"no such file: {source}")
            return 1
        reports[name] = scan(source.read_text(encoding="utf-8"), root)

    # A source linking only non-canonically does link into the documentation, so
    # it is told what is wrong with those links rather than that it has none.
    blind = [
        name
        for name, report in reports.items()
        if not report.found and not report.stray
    ]
    if blind:
        for name in blind:
            print(f"{name} links into the documentation nowhere")
        print(f"\n{textwrap.fill(BLIND)}")
        print("\nSee 'Documentation Links' in docs/src/developer/docs-style.rst.")
        return 1

    return verdict(reports)


if __name__ == "__main__":
    sys.exit(main())
