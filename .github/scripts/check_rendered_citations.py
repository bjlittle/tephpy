#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that every rendered citation became a link (docs spec §3.7).

This is the converse of the pre-commit gate of docs spec §3.6. That one asserts
every citation in the *source* resolves to an anchor; this one asserts every
citation in the *output* became a link. Each is blind where the other sees: the
input gate cannot tell whether the extension ran at all, and the output gate
cannot tell a right target from a wrong one.

The pattern below is deliberately looser than the shared grammar, and shares no
code with it. A check that asked the grammar what to look for would go blind in
the same instant the grammar did, and pass by finding nothing.

One limitation follows from that independence and is accepted rather than fixed:
a citation sitting inside an *unrelated* hyperlink counts as linked, because this
gate counts ``<a>`` ancestors and cannot tell a citation cross-reference from any
other anchor. The transform leaves such a citation plain on purpose —
``nodes.reference`` is in its skip set, so that one anchor is never nested inside
another — so the case reads here as a pass. Distinguishing it would mean matching
the transform's output classes, which is exactly the coupling this gate exists to
avoid.

A second limitation runs the other way, and matters more: an ``<a>`` a theme
template leaves unclosed survives on the stack only until an ancestor's end tag
pops past it, because ``handle_endtag`` pops the whole run down to the tag it
matches and takes the stray ``<a>`` with it. Every bare citation inside that window
counts as linked instead of bare — the pattern finds them and the count buckets
them wrong, so the gate passes on an empty bare list rather than on anything
really being linked. The inverse, an ``<a>`` nested inside an
``<a>``, fails closed. Sphinx output is well-formed, so this is theoretical today;
a theme upgrade is the change that would introduce it.

The nested bucket below is the same collision arrived at from the other side, and
is not the unrelated-hyperlink limitation. A skip set can only decline to rewrite
text that is *already* inside a link; it cannot stop a later transform from
wrapping one the transform made. Docutils' ``contents`` transform does precisely
that, at a lower priority than the citation transform, linking each heading it
lists both in the list and in the heading itself — so a citation written in a
heading is rewritten first and enclosed second, and the page really does carry one
anchor inside another. Sphinx reports nothing, and ``--fail-on-warning`` sees a
clean build. Reading the finished HTML is what catches it, which is the case for
this gate that neither the transform nor the input gate can make.

The exemptions below are narrower than that skip set, which is why a citation in
a raw block, in an API signature, in a toctree caption, or in a page title --
stripped of its anchor by Sphinx copying the title into ``<title>``, and again by
the theme repeating it in the breadcrumb -- is reported here. Those are failures,
not false positives: the citation reaches the reader as plain text in every one
of them. Exempting them would mean recognising the transform's node classes in
the rendered HTML, so the rule is stated for authors in the documentation style
guide instead, and the failure below names it.

What a failure *says* is a different matter from whether it fails, and the
placements are told apart for the report alone. That distinction is what makes
it safe: a wrong label costs a confusing message, where a wrong exemption would
cost this gate its sight. The labels are read off element names for the same
reason -- ``<title>``, ``<nav>`` and ``<dt>`` are HTML, whereas the classes that
would separate a breadcrumb from any other navigation are one theme's private
presentation contract.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import textwrap

CITATION = re.compile(r"§\s*\d+(?:\.\d+)*")
#: Text inside these is never linked, by design (docs spec §3.7).
EXEMPT = {"code", "pre", "script", "style"}
#: ``viewcode`` renders verbatim source; its section signs are Python, not prose.
SKIP_PAGES = ("_modules/",)
#: Elements that never close, so must never be pushed onto the stack.
VOID = {"br", "col", "hr", "img", "input", "link", "meta", "source", "wbr"}
#: How many citations of one placement to name on one page before counting them.
SHOWN = 4
#: Ancestors that say where an unlinked citation sat, tried in this order so the
#: outermost distinction wins. Diagnostic only: this decides what the failure
#: says, never whether it fails.
PLACEMENT = ("title", "nav", "dt")
#: How each of those is named in the report, with ``""`` for everything else.
WHERE = {
    "title": "the page title",
    "nav": "navigation chrome",
    "dt": "an API signature",
    "": "body text",
}
#: What to do about each, keyed the same way.
TITLE = (
    "A citation in a page title is a link in the heading itself, but not in the "
    "copy Sphinx makes of it for the browser tab, which is the title stripped of "
    "its markup. Name the section in the prose under the heading instead."
)
NAVIGATION = (
    "Navigation repeats text written elsewhere and drops the markup with it: the "
    "breadcrumb repeats the page title, and the sidebar repeats a toctree "
    "':caption:'. Neither copy can carry a link of its own, so the citation "
    "belongs in the prose of the page that owns it."
)
SIGNATURE = (
    "An API signature is on the transform's skip set, so a citation in one -- in "
    "a parameter's default value, say -- is never rewritten into a link. Cite the "
    "section in the docstring's prose instead."
)
BODY = (
    "Body text is where a citation that simply failed to link comes out. Check "
    "that 'tephpy_citation_xrefs' is still first in conf.py's extensions and "
    "that the section named exists; failing that, the citation is in a "
    "'.. raw:: html' block or a toctree ':caption:', neither of which the "
    "transform rewrites."
)
ADVICE = {"title": TITLE, "nav": NAVIGATION, "dt": SIGNATURE, "": BODY}
#: The other bucket, which is nobody's authoring mistake and everybody's puzzle.
NESTED = (
    "Two anchors around one citation is invalid HTML, and a browser restructures "
    "it silently, so neither link reliably goes where it reads as going. It "
    "happens when something wraps a heading after the citation inside it became a "
    "link: a '.. contents::' directive does exactly that, to the heading and to "
    "its own list entry alike. Nothing in the source looks wrong, so name the "
    "section in the prose under the heading instead. A citation an author wrote "
    "inside a link runs the other way -- the transform leaves it plain, one anchor "
    "encloses it, and it is counted as linked rather than reported here."
)


class Scan(HTMLParser):
    """Collect every citation in one page, classified by where it sits."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.linked = 0
        self.exempt = 0
        self.bare: list[tuple[str, str]] = []
        self.nested: list[str] = []

    def placement(self) -> str:
        """Name the ancestor that explains where the current text sits."""
        return next((tag for tag in PLACEMENT if tag in self.stack), "")

    # The unused overrides take underscored names so ruff reads them as
    # deliberate: ``HTMLParser`` calls these positionally, so the names are ours.
    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        """Push ``tag`` unless it is void."""
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(
        self, _tag: str, _attrs: list[tuple[str, str | None]]
    ) -> None:
        """Ignore a self-closing tag; it encloses nothing.

        Defensive, not load-bearing: deleting this leaves every test in
        ``tests/test_rendered_citations.py`` passing, because ``HTMLParser``
        defaults to ``handle_starttag`` then ``handle_endtag``, which is
        net-neutral for a stack-and-pop model. The test pins the behaviour, not
        the override, and no test can distinguish the two. It stops being
        redundant the moment the classification stops being stack-and-pop.
        """

    def handle_endtag(self, tag: str) -> None:
        """Pop back to ``tag``, tolerating elements left unclosed."""
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass

    def handle_data(self, data: str) -> None:
        """Classify each citation in a run of text."""
        hits = CITATION.findall(data)
        if not hits:
            return
        anchors = self.stack.count("a")
        if any(tag in EXEMPT for tag in self.stack):
            self.exempt += len(hits)
        elif anchors > 1:
            self.nested.extend(hits)
        elif anchors == 1:
            self.linked += len(hits)
        else:
            where = self.placement()
            self.bare.extend((hit, where) for hit in hits)


def grouped(hits: list[tuple[str, str]]) -> dict[str, list[str]]:
    """Gather one page's citations by placement, in the order they were found.

    One line per placement is what keeps the advice honest: every placement the
    report advises on is a placement it has just shown an offender for, by
    construction rather than by the listing happening to be long enough.

    Parameters
    ----------
    hits : list of tuple of str
        The citation and its placement, as :class:`Scan` collected them.

    Returns
    -------
    dict
        The citations of each placement, keyed as :data:`WHERE` is.

    """
    out: dict[str, list[str]] = {}
    for hit, where in hits:
        out.setdefault(where, []).append(hit)
    return out


def listed(hits: list[str]) -> str:
    """Name the first few citations, and say how many are not named.

    Parameters
    ----------
    hits : list of str
        The citations of one placement on one page.

    Returns
    -------
    str
        The listing. A report that bounds what it shows says what it dropped;
        a count quietly smaller than the total reads as a smaller problem.

    """
    rest = len(hits) - SHOWN
    listing = ", ".join(hits[:SHOWN])
    return f"{listing} and {rest} more" if rest > 0 else listing


def main() -> int:
    """Scan the built HTML.

    Returns
    -------
    int
        ``0`` when every rendered citation is a link, ``1`` otherwise.

    """
    if len(sys.argv) != 2:
        print("usage: check_rendered_citations.py <html-root>")
        return 1
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"no such directory: {root}")
        return 1

    linked = exempt = pages = 0
    unlinked: dict[str, list[tuple[str, str]]] = {}
    nested: dict[str, list[str]] = {}
    for page in sorted(root.rglob("*.html")):
        relative = page.relative_to(root).as_posix()
        if relative.startswith(SKIP_PAGES):
            continue
        pages += 1
        scan = Scan()
        scan.feed(page.read_text(encoding="utf-8"))
        linked += scan.linked
        exempt += scan.exempt
        if scan.bare:
            unlinked[relative] = scan.bare
        if scan.nested:
            nested[relative] = scan.nested

    if not pages:
        print(f"no HTML pages under {root}")
        return 1
    if not linked:
        print(
            f"no citation became a link across {pages} pages -- is "
            "'tephpy_citation_xrefs' still first in conf.py's extensions?"
        )
        return 1
    if not unlinked and not nested:
        print(
            f"rendered citations ok: {linked} linked, {exempt} literal, "
            f"{pages} pages (docs spec §3.7)"
        )
        return 0
    if unlinked:
        print(f"Unlinked ({sum(len(hits) for hits in unlinked.values())}):")
        placements = []
        for relative, hits in sorted(unlinked.items()):
            for where, found in grouped(hits).items():
                print(f"  {relative}: {listed(found)} in {WHERE[where]}")
                placements.append(where)
        # Deduplicated by advice and not by placement, so a page title reported
        # from both `<title>` and the breadcrumb is explained once.
        for advice in dict.fromkeys(ADVICE[where] for where in placements):
            print(f"\n{textwrap.fill(advice)}")
    if nested:
        print(f"\nNested in a link ({sum(len(hits) for hits in nested.values())}):")
        for relative, hits in sorted(nested.items()):
            print(f"  {relative}: {listed(hits)}")
        print(f"\n{textwrap.fill(NESTED)}")
    print("\nSee 'Specification Citations' in docs/src/developer/docs-style.rst.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
