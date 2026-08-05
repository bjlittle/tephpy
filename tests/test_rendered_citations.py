# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the rendered-citation gate (docs spec §3.7)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_rendered_citations.py"

# As in `test_citations.py`: `MANIFEST.in` prunes `.github`, so an sdist ships
# these tests without the gate they exercise. The guard sits on the module and
# not inside the tests, because an unconditional import would break collection
# there rather than skip.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="not a checkout of the repository"
)

# This file sits inside the corpus the pre-commit gate reads (docs spec §3.6),
# so the fixtures below build the section sign rather than writing it: a literal
# one would be a citation from a file that owns no sections, and the gate would
# be right to reject it. The docstrings cite for real, and stay literal.
SECTION = "\N{SECTION SIGN}"


def cite(text):
    """Read ``@`` in a fixture as a section sign."""
    return text.replace("@", SECTION)


def _load():
    """Import the gate by path; ``.github`` is not an importable package."""
    assert SCRIPT.is_file(), f"the rendered-citation gate is missing from {SCRIPT}"
    spec = importlib.util.spec_from_file_location("check_rendered_citations", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


crc = _load() if SCRIPT.is_file() else None


def scan(html):
    """Return the gate's classification of one fragment of HTML."""
    found = crc.Scan()
    found.feed(cite(html))
    return found


def build(tmp_path, pages):
    """Write ``{relative page: html}`` under ``tmp_path`` and return the root."""
    for relative, html in pages.items():
        page = tmp_path / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(cite(html), encoding="utf-8")
    return tmp_path


def run(monkeypatch, root):
    """Run the gate over ``root`` and return its exit code."""
    monkeypatch.setattr(crc.sys, "argv", ["check_rendered_citations.py", str(root)])
    return crc.main()


def test_a_citation_inside_a_link_is_linked():
    """The property the gate exists to assert (docs spec §3.7)."""
    found = scan('<p>Drawn as described in <a href="#spec-3-2">spec @3.2</a>.</p>')
    assert (found.linked, found.exempt, found.bare, found.nested) == (1, 0, [], [])


def test_every_citation_in_one_run_of_text_is_counted():
    """A compound citation is one text node and two sections."""
    found = scan('<p><a href="#spec-3-1">spec @3.1, @10</a></p>')
    assert found.linked == 2


def test_a_citation_inside_a_literal_is_exempt():
    """Literals and code blocks stay plain by design (docs spec §3.7)."""
    found = scan("<p>Write <code>spec @3.2</code>, never a role.</p>")
    assert (found.linked, found.exempt, found.bare) == (0, 1, [])
    assert scan("<pre>spec @3.2</pre>").exempt == 1


def test_an_exempt_ancestor_counts_at_any_depth():
    """The gate reads the whole stack, not the innermost element."""
    found = scan("<pre><span><em>spec @3.2</em></span></pre>")
    assert (found.exempt, found.bare) == (1, [])


def test_a_citation_in_ordinary_prose_is_unlinked():
    """The failure the gate reports: rendered, and not a link."""
    found = scan("<p>Drawn as described in spec @3.2.</p>")
    assert found.bare == [cite("@3.2")]
    assert (found.linked, found.exempt) == (0, 0)


def test_a_citation_in_a_page_title_is_unlinked():
    """The heading links; the copies Sphinx makes of it do not.

    A title is emitted again in ``<title>`` with its markup stripped, and again by
    the theme's breadcrumb without the anchor, so the citation reaches the reader
    as plain text in the browser tab and above the page. Reporting it is what
    docs spec §3.7 asks for, and this pins that against a later exemption.
    """
    assert scan("<head><title>3. Rendering, per spec @3.2</title></head>").bare == [
        cite("@3.2")
    ]
    breadcrumb = scan('<nav><li><span class="std std-ref">spec @3.2</span></li></nav>')
    assert breadcrumb.bare == [cite("@3.2")]


def test_a_citation_in_a_raw_block_or_a_signature_is_unlinked():
    """Both are on the transform's skip set, and neither is marked in the output.

    A raw block is indistinguishable from prose once rendered, and a signature's
    default value is spans rather than a literal, so the gate reads plain text in
    each -- which is what the page shows. The exemptions are narrower than the
    skip set on purpose (docs spec §3.7).
    """
    raw = scan("<div><p>spec @3.2, written as raw HTML</p></div>")
    signature = scan(
        '<dt class="sig sig-object py"><em class="sig-param">'
        '<span class="default_value"><span class="pre">\'spec</span> '
        '<span class="pre">@3.2\'</span></span></em></dt>'
    )
    assert raw.bare == [cite("@3.2")]
    assert signature.bare == [cite("@3.2")]


def test_a_citation_nested_in_two_links_is_reported():
    """One anchor inside another is invalid HTML, so it is called out separately."""
    found = scan('<a href="#a"><a href="#b">spec @3.2</a></a>')
    assert found.nested == [cite("@3.2")]
    assert (found.linked, found.bare) == (0, [])


def test_an_unclosed_element_does_not_corrupt_the_stack():
    """A tag closed past an element left open must not strand it on the stack.

    ``</div>`` pops the ``<p>`` with it. Were the pop to stop at the first
    mismatch, the ``<p>`` would sit on the stack for the rest of the page —
    harmless here, but the same slip with a ``<code>`` reclassifies every later
    citation as exempt and the gate prints "ok" with a quietly smaller count.
    """
    found = scan('<div><p>spec @3.1</div><a href="#x">spec @3.2</a>')
    assert found.bare == [cite("@3.1")]
    assert found.linked == 1
    assert found.stack == []


def test_a_stray_end_tag_is_ignored():
    """A close with nothing open must not empty the stack under a live element."""
    found = scan('<a href="#x"></span>spec @3.2</a>')
    assert found.linked == 1
    assert found.stack == []


def test_a_void_element_is_never_pushed():
    """``<br>`` never closes, so pushing it would leave the stack growing."""
    found = scan("<p>a line<br>then spec @3.1</p>")
    assert found.bare == [cite("@3.1")]
    assert found.stack == []
    assert scan("<br><p>spec @3.2</p>").stack == []


def test_a_self_closing_tag_encloses_nothing():
    """``<a … />`` opens no link, so what follows it is not inside one."""
    found = scan('<p><a href="#x"/>spec @3.2</p>')
    assert found.bare == [cite("@3.2")]
    assert found.linked == 0


def test_the_gate_passes_a_tree_whose_citations_are_linked(
    monkeypatch, capsys, tmp_path
):
    """The clean case, reported with the figures a reader can check."""
    root = build(
        tmp_path,
        {
            "index.html": '<p><a href="#spec-3-2">spec @3.2</a></p>',
            "guide/style.html": "<p><code>spec @3.2</code></p>",
        },
    )
    assert run(monkeypatch, root) == 0
    assert (
        "rendered citations ok: 1 linked, 1 literal, 2 pages" in capsys.readouterr().out
    )


def test_the_gate_fails_a_page_whose_citation_is_not_a_link(
    monkeypatch, capsys, tmp_path
):
    """One unlinked citation fails the build and names the page."""
    root = build(
        tmp_path,
        {
            "index.html": '<p><a href="#spec-3-2">spec @3.2</a></p>',
            "guide/style.html": "<p>spec @3.1 was missed</p>",
        },
    )
    assert run(monkeypatch, root) == 1
    out = capsys.readouterr().out
    assert "Unlinked (1)" in out
    assert "guide/style.html" in out
    # Naming the page is not enough on its own: the three placements that cannot
    # carry a citation are where an author who did nothing obviously wrong lands.
    assert "cite the section in body prose" in out


def test_the_gate_fails_when_no_citation_became_a_link(monkeypatch, capsys, tmp_path):
    """Total blindness — the extension unloaded — is reported as its own failure."""
    root = build(tmp_path, {"index.html": "<p>spec @3.2 and spec @3.1</p>"})
    assert run(monkeypatch, root) == 1
    assert "no citation became a link across 1 pages" in capsys.readouterr().out


def test_viewcode_listings_are_not_read(monkeypatch, capsys, tmp_path):
    """``_modules/`` renders Python verbatim; its section signs are not prose."""
    root = build(
        tmp_path,
        {
            "index.html": '<p><a href="#spec-3-2">spec @3.2</a></p>',
            "_modules/tephpy/plotting.html": "<p>spec @3.1 unlinked in a listing</p>",
        },
    )
    assert run(monkeypatch, root) == 0
    assert "1 linked, 0 literal, 1 pages" in capsys.readouterr().out


def test_an_empty_tree_is_a_failure(monkeypatch, capsys, tmp_path):
    """Finding no pages at all is the other way to pass by finding nothing."""
    assert run(monkeypatch, tmp_path) == 1
    assert "no HTML pages under" in capsys.readouterr().out
