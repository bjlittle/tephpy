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
two of them fire on one hover (tooltip spec §3.4). The vendored runtime is there,
and only there (tooltip spec §3.2): no page loads it from a third party, a page
carrying a tippy payload always references at least one local runtime script,
and every script it references resolves to a file under the build root --
because ``tippy_js`` is one deleted line away from its unpkg default, a stripped
``<script>`` tag is otherwise silent, and Sphinx does not warn on a missing
static asset either. And the emitted payload still carries ``interactive: false`` and
``sd-stretched-link``: the first keeps about 790 dead in-tip fragment links
unreachable (tooltip spec §3.5), the second keeps the landing page's four cards
from raising a tooltip that buries a third of the viewport (tooltip spec §3.3).
None of the four fails a build when it is lost.

The off-site half of the runtime check looks for a *script element* whose source
is absolute, not for the string ``unpkg.com``. This gate's own specification is a
published page and names that host in prose, so a sweep for the text would fail
on the document that asked for the gate.

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
#: The runtime this gate is about, by the file each URL ends in. Also matches the
#: per-page payload loader `TIPPY` names, which sits under a directory also
#: named "tippy" -- `TIPPY_PREFIX` below tells the two apart.
RUNTIME = re.compile(r"(tippy|popper)", re.IGNORECASE)
#: The payload loader's directory, as the prefix a matched `RUNTIME` source is
#: excluded on: it is Sphinx-emitted and already read by `payloads()`, not one
#: of the two vendored bundles this check is about.
TIPPY_PREFIX = f"{TIPPY.as_posix()}/"
#: A URL that leaves this site. Also excludes intersphinx glossary links from
#: check 1: tooltip spec §7 records that external and intersphinx links carry no
#: tooltip by design, so a bare ``:term:`` resolving off-site is not this
#: project's glossary and is not counted against it.
ABSOLUTE = re.compile(r"^[a-z][a-z0-9+.-]*:|^//", re.IGNORECASE)
#: Pages Sphinx's builder generates rather than renders from a source document --
#: the extension processes the document set it builds from, writes no payload for
#: any of these three, and a general index lists every glossary term, so
#: `genindex` alone would otherwise supply 50 links check 1 could never satisfy.
#: Matched against the full posix docname, not a basename, so a nested page that
#: happens to share one of these three names -- `reference/search`, say -- is
#: not this exclusion and is still checked.
GENERATED = {"genindex", "search", "py-modindex"}
#: The two guards of tooltip spec §3.3 and tooltip spec §3.5, as the payload
#: spells them.
GUARDS = ("interactive: false", "sd-stretched-link")
#: The line carrying tooltip spec §3.3's guard, matched on its own so a payload
#: that merely quotes the class name inside copied tip HTML -- one of the 65
#: does, this specification's own prose -- does not pass check 4 on that
#: content instead of on the setting itself.
SKIP_CLASSES = re.compile(r"^\s*skip_classes\s*=.*$", re.MULTILINE)


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
        if docname in GENERATED:
            continue
        has = tipped(maps.get(docname, {}))
        for href in article_links(page.read_text(encoding="utf-8")):
            if not TERM.search(href) or ABSOLUTE.match(href):
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
    """Report the runtime loading off-site, missing outright, or not there.

    Three things are checked, and each catches a regression the others cannot.
    An off-site source is the vendoring reverted. A payload with no local runtime
    script at all is the same silent failure with the ``<script>`` tag stripped
    instead of pointed off-site -- the purely negative off-site check alone is
    satisfied most completely by a page that loads nothing. And a local source
    naming a file that is not there is a bundle renamed or deleted at either
    end: neither absent nor off-site, so it passes both of the others, and
    Sphinx does not warn on it either -- ``_file_checksum_inner`` swallows the
    ``FileNotFoundError`` a missing static asset raises.
    """
    found = []
    maps = payloads(root)
    for page in pages(root):
        docname = page.relative_to(root).with_suffix("").as_posix()
        text = page.read_text(encoding="utf-8")
        #: The two vendored bundles this check is about, excluding the payload
        #: loader `TIPPY_PREFIX` names -- it also matches `RUNTIME` on its
        #: filename, but it is not the runtime `tippy_js` vendors.
        runtime = [
            src
            for src in SCRIPT.findall(text)
            if RUNTIME.search(src) and TIPPY_PREFIX not in src
        ]
        found.extend(
            f"{page.relative_to(root)}: an off-site script src names {src}, "
            f"matching the tooltip runtime pattern"
            for src in runtime
            if ABSOLUTE.match(src)
        )
        local = [src for src in runtime if not ABSOLUTE.match(src)]
        if docname in maps and not local:
            found.append(
                f"{page.relative_to(root)}: carries a tippy payload but "
                f"references no vendored runtime script"
            )
        for src in local:
            #: Sphinx appends a cache-busting `?v=...` query; strip it before
            #: resolving, and resolve relative to the page, not the root --
            #: every non-index page's `src` is written relative to itself.
            target = (page.parent / src.split("?", 1)[0]).resolve()
            if not target.is_file():
                found.append(
                    f"{page.relative_to(root)}: references the runtime file "
                    f"{src}, which does not exist under the build root"
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
        skip_line = SKIP_CLASSES.search(text)
        #: `interactive: false` is read from the whole payload -- it is
        #: emitted once, in the `tippy(...)` call, and nothing else in a
        #: copied tip could plausibly quote it. `sd-stretched-link` is read
        #: from the `skip_classes` line alone, because that string *can*
        #: appear inside copied tip HTML (tooltip spec §3.2's own page does),
        #: and a hit there would pass on the wrong evidence.
        haystacks = {
            "interactive: false": text,
            "sd-stretched-link": skip_line[0] if skip_line else "",
        }
        found.extend(
            f"{js.relative_to(root)}: the payload no longer carries {guard!r}"
            for guard in GUARDS
            if guard not in haystacks[guard]
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
        "The vendored runtime, not delivered as configured": check_vendored(root),
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
