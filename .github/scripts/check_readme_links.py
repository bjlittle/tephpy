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

A README carrying no documentation link at all fails too. A check is worth what it
covers, and a rewrite that dropped every link would otherwise pass in silence.

Two things are deliberately not checked. That a link points at the *right* page is
a question about meaning, not resolution, and no gate can answer it. And an
``en/latest`` URL is checked against the working tree's own build, which is the
only build available -- a link correct here is wrong on the published site until
this branch merges, and that is the ordinary lag of a landing page that names a
moving target.

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
#: What to do about a README that links into the documentation nowhere.
BLIND = (
    "A README with no documentation link is not one this check can check, so it "
    "fails rather than passing on an empty search. If the landing page really "
    "should carry none, retire this check along with them: leaving it is a green "
    "tick standing for nothing."
)


def links(text: str) -> list[tuple[str, str]]:
    """Find every documentation link in the README.

    Parameters
    ----------
    text : str
        The README, as Markdown.

    Returns
    -------
    list of tuple of str
        The page path and fragment of each link, in the order they were written,
        with ``""`` for a link naming no fragment.

    """
    return [(page, anchor or "") for page, anchor in LINK.findall(text)]


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
        print("usage: check_readme_links.py <html-root> [readme]")
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

    found = links(readme.read_text(encoding="utf-8"))
    if not found:
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
    if not absent and not broken:
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
    print("\nSee 'Landing Page Links' in docs/src/developer/docs-style.rst.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
