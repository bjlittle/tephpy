#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that the documentation's tooltips were generated, and stayed scoped.

Tooltips are presentation, and this project gates the correctness of content
rather than its presentation, so nothing here judges how a tooltip looks: not its
palette, its placement, its size, nor whether its text wrapped well. What it
checks is the small set of properties whose regression would be *silent* and
would reach the reader as something worse than no tooltip at all
(tooltip spec §3.6).

Four of them. Every ``:term:`` link on a published page has a tip, and there is at
least one -- the positive assertion, without which a build where the extension
produced nothing passes the other three most completely. No gallery example link
is tipped, because sphinx-gallery already puts a tooltip on those thumbnails and
two of them fire on one hover (tooltip spec §3.4). No page loads the tooltip
runtime from a third party, because ``tippy_js`` is one deleted line away from its
unpkg default and nothing else would say so (tooltip spec §3.2). And the emitted
payload still carries ``interactive: false`` and ``sd-stretched-link``: the first
keeps 781 dead in-tip fragment links unreachable (tooltip spec §3.5), the second
keeps the landing page's four cards from raising a tooltip that buries a third of
the viewport (tooltip spec §3.3). Neither fails a build when it is lost.

The check for the runtime looks for a *script element* whose source is absolute,
not for the string ``unpkg.com``. This gate's own specification is a published
page and names that host in prose, so a sweep for the text would fail on the
document that asked for the gate.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

#: Where the extension writes one JavaScript payload per page, named with a
#: ``uuid4`` -- so the file is found by glob and never by name.
TIPPY = Path("_static") / "tippy"
#: The uuid the extension appends, stripped back to the docname it belongs to.
STAMP = re.compile(r"\.[0-9a-f-]{36}\.js$")
#: A payload's first line, which is the selector map. The rest of the file is the
#: loader, and `json` reads the map once the assignment is removed.
ASSIGNED = re.compile(r"^\s*selector_to_html\s*=\s*")
#: One ``a[href="…"]`` selector, which is the only shape the map's keys take here.
SELECTOR = re.compile(r'a\[href="(.*)"\]$')
#: Links inside the article container -- the same scope `tippy_anchor_parent_selector`
#: gives the extension, so the two agree about which links are in question.
ARTICLE = re.compile(r'<article class="bd-article">(.*?)</article>', re.DOTALL)
#: An anchor's href within that scope.
HREF = re.compile(r'<a\b[^>]*\bhref="([^"]*)"')
#: A glossary term link, by the anchor Sphinx derives from the term.
TERM = re.compile(r"glossary\.html#term-")
#: A gallery example page, bare from the gallery index and dotted from elsewhere.
GALLERY = re.compile(r"(\.\./)*(gallery/)?plot_\w+\.html")
#: A script element and the source it loads.
SCRIPT = re.compile(r'<script\b[^>]*\bsrc="([^"]*)"')
#: The runtime this gate is about, by the file each URL ends in.
RUNTIME = re.compile(r"(tippy|popper)", re.IGNORECASE)
#: A URL that leaves this site.
ABSOLUTE = re.compile(r"^[a-z][a-z0-9+.-]*:|^//", re.IGNORECASE)
#: The two guards of tooltip spec §3.3 and tooltip spec §3.5, as the payload
#: spells them.
GUARDS = ("interactive: false", "sd-stretched-link")


def pages(root: Path) -> list[Path]:
    """Return every published HTML page under ``root``.

    Parameters
    ----------
    root : Path
        The build directory.

    Returns
    -------
    list of Path
        The pages, sorted. The staged browser application is not documentation
        this build wrote, and is passed over.

    """
    return sorted(p for p in root.rglob("*.html") if "browser" not in p.parts)


def payloads(root: Path) -> dict[str, dict[str, str]]:
    """Return each page's selector map, keyed by docname.

    Parameters
    ----------
    root : Path
        The build directory.

    Returns
    -------
    dict
        ``{docname: {selector: tip html}}``.

    """
    found = {}
    for js in (root / TIPPY).rglob("*.js"):
        docname = STAMP.sub("", js.relative_to(root / TIPPY).as_posix())
        first = js.read_text(encoding="utf-8").splitlines()[0]
        found[docname] = json.loads(ASSIGNED.sub("", first).strip().rstrip(";"))
    return found


def tipped(payload: dict[str, str]) -> set[str]:
    """Return the hrefs a payload generates a tip for.

    Parameters
    ----------
    payload : dict
        One page's selector map.

    Returns
    -------
    set of str
        The hrefs, with the selector syntax removed.

    """
    return {m[1] for selector in payload if (m := SELECTOR.match(selector))}


def article_links(html: str) -> list[str]:
    """Return every href inside the article container of ``html``.

    Parameters
    ----------
    html : str
        A rendered page.

    Returns
    -------
    list of str
        The hrefs, in document order. Empty when the page has no article.

    """
    body = ARTICLE.search(html)
    return HREF.findall(body[1]) if body else []


def check_glossary(root: Path) -> list[str]:
    """Report every glossary link with no tip, and a build with no link at all."""
    found, seen = [], 0
    maps = payloads(root)
    for page in pages(root):
        docname = page.relative_to(root).with_suffix("").as_posix()
        has = tipped(maps.get(docname, {}))
        for href in article_links(page.read_text(encoding="utf-8")):
            if not TERM.search(href):
                continue
            seen += 1
            if href not in has:
                found.append(f"{docname}: no tip for the glossary link {href}")
    if not seen:
        found.append(
            "no glossary link was found in the build, so nothing was checked; "
            "a gate that passes on an empty search is a green tick over nothing"
        )
    return found


def check_gallery(root: Path) -> list[str]:
    """Report every gallery example link that carries a tip (tooltip spec §3.4)."""
    found = []
    for docname, payload in payloads(root).items():
        found.extend(
            f"{docname}: {href} is tipped, and sphinx-gallery already puts a "
            f"tooltip on that thumbnail"
            for href in sorted(tipped(payload))
            if GALLERY.fullmatch(href.split("#")[0])
        )
    return found


def check_vendored(root: Path) -> list[str]:
    """Report every page loading the tooltip runtime from off-site."""
    found = []
    for page in pages(root):
        text = page.read_text(encoding="utf-8")
        found.extend(
            f"{page.relative_to(root)}: loads the tooltip runtime from "
            f"{src}; tippy_js must name the vendored bundles"
            for src in SCRIPT.findall(text)
            if RUNTIME.search(src) and ABSOLUTE.match(src)
        )
    return found


def check_guards(root: Path) -> list[str]:
    """Report every payload that lost one of the two runtime guards."""
    found = []
    maps = payloads(root)
    if not maps:
        return ["the build wrote no tooltip payload at all"]
    for js in sorted((root / TIPPY).rglob("*.js")):
        text = js.read_text(encoding="utf-8")
        found.extend(
            f"{js.relative_to(root)}: the payload no longer carries {guard!r}"
            for guard in GUARDS
            if guard not in text
        )
    return found


def main() -> int:
    """Run the four checks over a build.

    Returns
    -------
    int
        ``0`` when all four hold, ``1`` otherwise.

    """
    if len(sys.argv) != 2:
        print("usage: check_tooltips.py <build directory>")
        return 1
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"{root} is not a directory")
        return 1
    groups = {
        "Glossary links with no tooltip": check_glossary(root),
        "Gallery links that were tipped": check_gallery(root),
        "Pages loading the runtime off-site": check_vendored(root),
        "Payloads missing a runtime guard": check_guards(root),
    }
    total = sum(len(found) for found in groups.values())
    if total == 0:
        counted = sum(len(tipped(p)) for p in payloads(root).values())
        print(
            f"tooltips ok: {counted} tips across {len(payloads(root))} pages "
            f"(tooltip spec §3.6)"
        )
        return 0
    for heading, found in groups.items():
        if found:
            print(f"{heading} ({len(found)}):")
            for violation in found:
                print(f"  {violation}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
