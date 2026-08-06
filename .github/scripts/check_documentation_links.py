#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that every documentation link in ``README.md`` resolves in the build.

The README is the repository's landing page and is not a source of the Sphinx
project, so it reaches the documentation by absolute URL. Nothing in the build
sees those links: ``nitpicky`` checks the references Sphinx itself resolved, and
the rendered-citation gate reads only pages the build produced. Meanwhile a
glossary anchor is derived from the term -- Sphinx keeps the case and collapses
each run of non-alphanumeric characters to a single hyphen, so ``Normand's
point`` becomes ``term-Normand-s-point`` -- which makes renaming a term a silent
way to break the landing page, and moving a page another.

This gate closes that gap from the outside. It reads the URLs out of the README
and looks each one up in the HTML the build has just produced: the page must
exist, and a fragment must name an ``id`` on it. Nothing here reproduces the slug
rule, because the ids are read off the built page rather than derived. A
normalisation of our own would be one more thing able to drift from Sphinx, which
is the drift this gate exists to catch.

Only the canonical ``en/latest`` URL can be looked up that way, so a link onto a
documentation host of this project written any other way is reported rather than
skipped in silence. A per-pull-request preview is where a documentation change is
verified and the wrong place to link from the landing page, because Read the Docs
deletes it when the pull request closes; and ``latest`` is the only version this
project publishes.

A README carrying no documentation link at all fails too. A check is worth what it
covers, and a rewrite that dropped every link would otherwise pass in silence.

Three things are deliberately not checked. That a link points at the *right* page
is a question about meaning, not resolution, and no gate can answer it. An
``en/latest`` URL is checked against the working tree's own build, which is the
only build available -- a link correct here is wrong on the published site until
this branch merges, and that is the ordinary lag of a landing page that names a
moving target. And a URL on a documentation host of this project whose path never
says ``.html`` is passed over rather than judged: it is how the Read the Docs
badge, which points at the base with a query string, stays out of the report, and
it lets through a directory-style URL, which Read the Docs does resolve and which
carries no page or anchor to look up.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from pathlib import Path
import re
import sys
import textwrap

#: The published documentation, which is what the README links into.
BASE = "https://tephpy.readthedocs.io/en/latest/"
#: A link into a documentation page, with the fragment it names, if any. Only a
#: path ending in ``.html`` is a page: the Read the Docs badge points at the base
#: with a query string and no path, and names nothing this gate can look up.
LINK = re.compile(re.escape(BASE) + r"([\w./-]+\.html)(?:#([\w.:-]+))?")
#: Any URL onto a documentation host of this project -- the published site, or a
#: per-pull-request Read the Docs preview. The match stops before whitespace,
#: ``)`` and ``]``, so a Markdown inline link and a reference definition both
#: terminate cleanly. Either scheme matches, deliberately: this pattern decides
#: what gets *judged*, so narrowing it to ``https`` would make a plaintext link
#: invisible to the gate instead of non-canonical.
DOCS = re.compile(
    r"https?://(?:tephpy\.readthedocs\.io"
    r"|tephpy--[\w.-]+?\.org\.readthedocs\.build)[^\s)\]]*"
)
#: An ``id`` attribute in the built HTML, which is what a fragment must name.
ID = re.compile(r'\bid="([^"]+)"')
#: How many offenders of one kind to name before counting the rest.
SHOWN = 6
#: What to do about a link naming a page the build did not produce.
MISSING_PAGE = (
    "The build produced no such page. A page that is renamed or moved leaves the "
    "README pointing at a URL Read the Docs answers with a 404, and the build "
    "cannot notice, because the README is not one of its sources. Update the link "
    "to the path the page now has, or restore the page under the path the README "
    "names."
)
#: What to do about a link naming a fragment its page does not carry.
MISSING_ANCHOR = (
    "The page renders, but nothing on it carries that id. A glossary anchor is "
    "derived from the term: Sphinx keeps the case and collapses each run of "
    "non-alphanumeric characters to a single hyphen, so renaming a term moves its "
    "anchor and the README goes on naming where it used to be. Copy the id out of "
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
#: What to do about a README that links into the documentation nowhere.
BLIND = (
    "A README with no documentation link is not one this check can check, so it "
    "fails rather than passing on an empty search. If the landing page really "
    "should carry none, retire this check along with them: leaving it is a green "
    "tick standing for nothing."
)


def links(text: str) -> list[tuple[str, str]]:
    """Find every canonically written documentation link in the README.

    Parameters
    ----------
    text : str
        The README, as Markdown.

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
        A documentation URL, as the README writes it.

    Returns
    -------
    str
        Everything the URL says before the first ``#`` or ``?``.

    """
    return url.split("#", 1)[0].split("?", 1)[0]


def strays(text: str) -> list[str]:
    """Find every documentation link the README writes non-canonically.

    Parameters
    ----------
    text : str
        The README, as Markdown.

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


def main() -> int:
    """Check the README's documentation links against the built HTML.

    Returns
    -------
    int
        ``0`` when every link resolves, ``1`` otherwise.

    """
    if not 2 <= len(sys.argv) <= 3:
        print("usage: check_documentation_links.py <html-root> [readme]")
        return 1
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"no such directory: {root}")
        return 1
    default = Path(__file__).parents[2] / "README.md"
    readme = Path(sys.argv[2]) if len(sys.argv) == 3 else default
    if not readme.is_file():
        print(f"no such file: {readme}")
        return 1

    text = readme.read_text(encoding="utf-8")
    found = links(text)
    # A README linking only non-canonically does link into the documentation, so
    # it is told what is wrong with those links rather than that it has none.
    stray = strays(text)
    if not found and not stray:
        print(f"{readme.name} links into the documentation nowhere")
        print(f"\n{textwrap.fill(BLIND)}")
        return 1

    pages: dict[str, set[str] | None] = {}
    for page, _ in found:
        if page not in pages:
            built = root / page
            pages[page] = anchors(built) if built.is_file() else None

    absent = sorted(page for page, ids in pages.items() if ids is None)
    # Keyed by page and fragment together, so one broken anchor named twice in
    # the README is one thing to fix and is reported as one.
    broken = sorted(
        {
            f"{page}#{anchor}"
            for page, anchor in found
            # An absent page carries no ids to miss; it is already reported above.
            if anchor and pages[page] is not None and anchor not in pages[page]
        }
    )
    if not absent and not broken and not stray:
        named = sum(1 for _, anchor in found if anchor)
        print(
            f"README links ok: {len(found)} checked, {named} naming an anchor, "
            f"across {len(pages)} pages"
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
    print("\nSee 'Landing Page Links' in docs/src/developer/docs-style.rst.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
