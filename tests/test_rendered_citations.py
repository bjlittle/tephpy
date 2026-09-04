# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the rendered-citation gate (docs spec §3.7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.by_path import load_script

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_rendered_citations.py"

# As in `test_citations.py`: the suite runs from a checkout, and a tree without
# `.github` has no gate to exercise. The guard sits on the module and not
# inside the tests, because an unconditional import would break collection
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


crc = load_script("check_rendered_citations") if SCRIPT.is_file() else None


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


def flat(out):
    """Undo the wrapping, so an assertion can name a phrase and not a line.

    The report wraps its advice to a terminal width. Asserting on a substring of
    the wrapped text would pin where the line breaks fall, and break on a wording
    change that moved nothing but a word onto the next line.
    """
    return " ".join(out.split())


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
    assert found.bare == [(cite("@3.2"), "")]
    assert (found.linked, found.exempt) == (0, 0)


def test_a_citation_in_a_page_title_is_unlinked():
    """The heading links; the copies Sphinx makes of it do not.

    A title is emitted again in ``<title>`` with its markup stripped, and again by
    the theme's breadcrumb without the anchor, so the citation reaches the reader
    as plain text in the browser tab and above the page. Reporting it is what
    docs spec §3.7 asks for, and this pins that against a later exemption.
    """
    assert scan("<head><title>3. Rendering, per spec @3.2</title></head>").bare == [
        (cite("@3.2"), "title")
    ]
    breadcrumb = scan('<nav><li><span class="std std-ref">spec @3.2</span></li></nav>')
    assert breadcrumb.bare == [(cite("@3.2"), "nav")]


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
    assert raw.bare == [(cite("@3.2"), "")]
    assert signature.bare == [(cite("@3.2"), "dt")]


def test_a_citation_in_a_toctree_caption_is_unlinked():
    """The fourth placement, and the one an author is least likely to expect.

    A ``:caption:`` is a directive option rather than a node the transform can
    reach, so it is never rewritten. It renders twice: once where the toctree
    sits, as an ordinary paragraph indistinguishable from prose, and once in the
    theme's sidebar, which is navigation. Both are reported.
    """
    body = scan('<p class="caption" role="heading"><span>Reading spec @3.2</span></p>')
    sidebar = scan(
        '<nav class="bd-docs-nav"><p class="caption"><span class="caption-text">'
        "Reading spec @3.2</span></p></nav>"
    )
    assert body.bare == [(cite("@3.2"), "")]
    assert sidebar.bare == [(cite("@3.2"), "nav")]


def test_the_outermost_placement_wins():
    """Two candidates on the stack at once, where the outer one is the answer.

    A definition list inside a sidebar is navigation, not an API signature. What
    an author is told to do about a citation follows from how the text reached the
    page, and here navigation put it there — the inner element only says what it
    was dressed as on arrival. The nesting cannot run the other way.
    """
    found = scan("<nav><dl><dt>spec @3.2</dt></dl></nav>")
    assert found.bare == [(cite("@3.2"), "nav")]


def test_a_citation_nested_in_two_links_is_reported():
    """One anchor inside another is invalid HTML, so it is called out separately.

    The markup is a build's, not an invention: a ``.. contents::`` directive runs
    at a lower priority than the citation transform, so it wraps a heading whose
    citation has already become a link. Neither the transform's skip set nor
    ``--fail-on-warning`` can see it, which is why this bucket exists.
    """
    found = scan(
        '<h2><a class="toc-backref" href="#id1" role="doc-backlink">Heading, per '
        '<a class="reference internal" href="design.html#spec-3-2">'
        '<span class="std std-ref">spec @3.2</span></a></a></h2>'
    )
    assert found.nested == [cite("@3.2")]
    assert (found.linked, found.bare) == (0, [])


def test_a_citation_an_author_linked_is_counted_as_linked():
    """The same collision from the other side, which is not an error.

    ``nodes.reference`` is on the transform's skip set, so a citation written
    inside a link stays plain text and the author's anchor is the only one. The
    gate counts one and passes it. Pinning the direction matters because the two
    read alike in prose and oppositely to the scanner (docs spec §3.7).
    """
    found = scan(
        '<p>An author link: <a class="reference external" '
        'href="https://example.com/">see spec @3.2</a> in prose.</p>'
    )
    assert (found.linked, found.nested, found.bare) == (1, [], [])


def test_an_unclosed_element_does_not_corrupt_the_stack():
    """A tag closed past an element left open must not strand it on the stack.

    ``</div>`` pops the ``<p>`` with it. Were the pop to stop at the first
    mismatch, the ``<p>`` would sit on the stack for the rest of the page —
    harmless here, but the same slip with a ``<code>`` reclassifies every later
    citation as exempt and the gate prints "ok" with a quietly smaller count.
    """
    found = scan('<div><p>spec @3.1</div><a href="#x">spec @3.2</a>')
    assert found.bare == [(cite("@3.1"), "")]
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
    assert found.bare == [(cite("@3.1"), "")]
    assert found.stack == []
    assert scan("<br><p>spec @3.2</p>").stack == []


def test_a_self_closing_tag_encloses_nothing():
    """``<a … />`` opens no link, so what follows it is not inside one."""
    found = scan('<p><a href="#x"/>spec @3.2</p>')
    assert found.bare == [(cite("@3.2"), "")]
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
    out = flat(capsys.readouterr().out)
    assert "Unlinked (1)" in out
    assert "guide/style.html" in out
    # The advice has to fit the failure in hand. This one is the ordinary miss --
    # prose that should have linked and did not -- so it is told where to look,
    # and not told about placements it was nowhere near.
    assert "body text" in out
    assert "still first in conf.py's extensions" in out
    assert "browser tab" not in out
    assert "API signature" not in out


def test_the_failure_says_where_each_unlinked_citation_sat(
    monkeypatch, capsys, tmp_path
):
    """Which is the whole of the difference between a report and a puzzle.

    Every one of these fails; naming the placement decides only what the author
    is told to do about it. A page title and a breadcrumb are one mistake with two
    symptoms, so a build showing both is not told twice.
    """
    root = build(
        tmp_path,
        {
            "index.html": '<p><a href="#spec-3-2">spec @3.2</a></p>',
            "title.html": (
                "<head><title>Rendering, per spec @3.1</title></head>"
                "<nav><li><span>Rendering, per spec @3.1</span></li></nav>"
            ),
            "api.html": '<dt class="sig"><span>@3.3</span></dt>',
        },
    )
    assert run(monkeypatch, root) == 1
    out = flat(capsys.readouterr().out)
    assert cite("title.html: @3.1 in the page title") in out
    assert cite("title.html: @3.1 in navigation chrome") in out
    assert cite("api.html: @3.3 in an API signature") in out
    assert out.count("browser tab") == 1
    assert "docstring's prose" in out


def test_every_advised_placement_has_a_visible_offender(monkeypatch, capsys, tmp_path):
    """Advice without an example is a report about a page the author cannot find.

    The listing is grouped by placement rather than truncated at a flat count, so
    the two cannot come apart: a placement is advised on because a line naming it
    was just printed. A page long enough to push a rare placement past a flat cut
    is what makes the difference visible, so that is what this builds.
    """
    prose = "".join(f"<p>spec @3.{n} in prose</p>" for n in range(1, 10))
    root = build(
        tmp_path,
        {
            "index.html": '<p><a href="#spec-3-2">spec @3.2</a></p>',
            "big.html": prose + '<dt class="sig"><span>@9.9</span></dt>',
        },
    )
    assert run(monkeypatch, root) == 1
    out = flat(capsys.readouterr().out)
    assert "docstring's prose" in out, "the signature placement was advised on"
    assert cite("@9.9") in out, "and must therefore have been shown"


def test_the_report_says_what_it_did_not_list(monkeypatch, capsys, tmp_path):
    """A listing that quietly stops reads as a smaller problem than it is.

    The header counts every citation, so a listing shorter than the header without
    saying so invites the reader to conclude the rest were fine.
    """
    prose = "".join(f"<p>spec @3.{n} in prose</p>" for n in range(1, 10))
    root = build(
        tmp_path,
        {
            "index.html": '<p><a href="#spec-3-2">spec @3.2</a></p>',
            "big.html": prose,
        },
    )
    assert run(monkeypatch, root) == 1
    out = flat(capsys.readouterr().out)
    assert "Unlinked (9)" in out
    assert "and 5 more" in out


def test_a_long_run_of_nested_citations_is_summarised_too(
    monkeypatch, capsys, tmp_path
):
    """The other bucket truncates on the same rule, and says so on the same terms."""
    nest = "".join(
        f'<a href="#a"><a href="#b">spec @4.{n}</a></a>' for n in range(1, 8)
    )
    root = build(
        tmp_path,
        {"index.html": '<p><a href="#spec-3-2">spec @3.2</a></p>', "toc.html": nest},
    )
    assert run(monkeypatch, root) == 1
    out = flat(capsys.readouterr().out)
    assert "Nested in a link (7)" in out
    assert "and 3 more" in out


def test_a_nested_citation_is_explained_and_not_merely_counted(
    monkeypatch, capsys, tmp_path
):
    """The bucket had no guidance of its own, and is the harder one to diagnose.

    Nothing in the source looks wrong: the citation is written as every other one
    is, and the link around it was put there by a ``.. contents::`` directive or
    by an author linking a whole sentence. Reporting the count alone leaves that
    to be rediscovered.
    """
    root = build(
        tmp_path,
        {
            "index.html": '<p><a href="#spec-3-2">spec @3.2</a></p>',
            "guide/style.html": '<a href="#x"><a href="#y">spec @3.1</a></a>',
        },
    )
    assert run(monkeypatch, root) == 1
    out = flat(capsys.readouterr().out)
    assert "Nested in a link (1)" in out
    assert "contents::" in out
    # Two anchors is what lands here and one is what passes, so advice written the
    # other way round sends an author after the case that never reaches it.
    assert "Two anchors" in out
    assert "counted as linked" in out
    # The other bucket is empty, so none of its advice belongs here.
    assert "Unlinked" not in out


def test_the_gate_fails_when_no_citation_became_a_link(monkeypatch, capsys, tmp_path):
    """Total blindness — the extension unloaded — is reported as its own failure.

    The implementation plan for docs spec §3.7,
    ``docs/src/developer/plans/2026-08-04-tephpy-citation-crossrefs.md``, states
    that this branch "is the one no fixture test can supply". That is wrong, and
    the correction belongs here because a plan is a frozen point-in-time record
    (docs spec §3.4). The branch is unreachable only against the real build;
    against a ``tmp_path`` tree of pages carrying citations and no links it fires
    directly, which is what this test does. Left uncorrected, the document a
    maintainer reads to understand the gate argues for a coverage hole that does
    not exist — in the one branch that catches the extension being dropped from
    ``conf.py``.
    """
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
