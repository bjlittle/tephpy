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

The exemptions below are narrower than that skip set, which is why a citation in
a raw block, in an API signature, or in a page title -- stripped of its anchor
both by Sphinx copying the title into ``<title>`` and by the theme repeating it
in the breadcrumb -- is reported here. Those are failures, not false positives:
the citation reaches the reader as plain text in every one of them. Exempting
them would mean recognising the transform's node classes in the rendered HTML,
so the rule is stated for authors in the documentation style guide instead, and
the failure below names it.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import sys

CITATION = re.compile(r"§\s*\d+(?:\.\d+)*")
#: Text inside these is never linked, by design (docs spec §3.7).
EXEMPT = {"code", "pre", "script", "style"}
#: ``viewcode`` renders verbatim source; its section signs are Python, not prose.
SKIP_PAGES = ("_modules/",)
#: Elements that never close, so must never be pushed onto the stack.
VOID = {"br", "col", "hr", "img", "input", "link", "meta", "source", "wbr"}


class Scan(HTMLParser):
    """Collect every citation in one page, classified by where it sits."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.linked = 0
        self.exempt = 0
        self.bare: list[str] = []
        self.nested: list[str] = []

    # The unused overrides take underscored names so ruff reads them as
    # deliberate: ``HTMLParser`` calls these positionally, so the names are ours.
    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        """Push ``tag`` unless it is void."""
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(
        self, _tag: str, _attrs: list[tuple[str, str | None]]
    ) -> None:
        """Ignore a self-closing tag; it encloses nothing."""

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
            self.bare.extend(hits)


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
    unlinked: dict[str, list[str]] = {}
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
            f"no citation became a link across {pages} pages -- is 'citation_xrefs' "
            "still first in conf.py's extensions?"
        )
        return 1
    if not unlinked and not nested:
        print(
            f"rendered citations ok: {linked} linked, {exempt} literal, "
            f"{pages} pages (docs spec §3.7)"
        )
        return 0
    for heading, offenders in (("Unlinked", unlinked), ("Nested in a link", nested)):
        if offenders:
            total = sum(len(hits) for hits in offenders.values())
            print(f"{heading} ({total}):")
            for relative, hits in sorted(offenders.items()):
                print(f"  {relative}: {', '.join(hits[:8])}")
    if unlinked:
        print(
            "\nA citation is left plain in a page title, a raw HTML block and an "
            "API signature,\nand reaches the reader as text in each -- cite the "
            "section in body prose instead.\nSee 'Specification Citations' in "
            "docs/src/developer/docs-style.rst."
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
