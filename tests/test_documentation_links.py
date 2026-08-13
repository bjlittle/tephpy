# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the documentation-link gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_documentation_links.py"

# As in `test_rendered_citations.py`: `MANIFEST.in` prunes `.github`, so an sdist
# ships these tests without the gate they exercise. The guard sits on the module
# and not inside the tests, because an unconditional import would break
# collection there rather than skip.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="not a checkout of the repository"
)

GLOSSARY = "reference/glossary.html"
SPECS = "developer/specs/index.html"
STYLE = "developer/docs-style.html"
PREVIEW = "https://tephpy--99.org.readthedocs.build/en/99/reference/glossary.html"


def _load():
    """Import the gate by path; ``.github`` is not an importable package."""
    assert SCRIPT.is_file(), f"the documentation link gate is missing from {SCRIPT}"
    spec = importlib.util.spec_from_file_location("check_documentation_links", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load() if SCRIPT.is_file() else None


def url(page, anchor=""):
    """Build the published URL of ``page``, naming ``anchor`` when given."""
    return gate.BASE + page + (f"#{anchor}" if anchor else "")


def terms(*names: str):
    """Render a glossary page carrying ``names`` as its term anchors."""
    entries = "".join(f'<dt id="{name}">{name}</dt>' for name in names)
    return f"<html><body><dl>{entries}</dl></body></html>"


def build(tmp_path, pages):
    """Write ``{relative page: html}`` under ``tmp_path`` and return the root."""
    root = tmp_path / "html"
    root.mkdir(parents=True, exist_ok=True)
    for relative, html in pages.items():
        page = root / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(html, encoding="utf-8")
    return root


def readme(tmp_path, text):
    """Write a README under ``tmp_path`` and return its path."""
    path = tmp_path / "README.md"
    path.write_text(text, encoding="utf-8")
    return path


def script(tmp_path, *targets: str):
    """Write a Python source naming each target the way a script does."""
    path = tmp_path / "changelog.py"
    body = "".join(f'URL = "{gate.BASE}{target}"\n' for target in targets)
    path.write_text(body, encoding="utf-8")
    return path


def run(monkeypatch, capsys, root, *paths: Path):
    """Run the gate over ``root`` and ``paths``; return its code and output."""
    argv = ["check_documentation_links.py", str(root), *(str(path) for path in paths)]
    monkeypatch.setattr(gate.sys, "argv", argv)
    code = gate.main()
    return code, capsys.readouterr().out


def flat(out):
    """Undo the wrapping, so an assertion can name a phrase and not a line.

    The report wraps its advice to a terminal width. Asserting on a substring of
    the wrapped text would pin where the line breaks fall, and break on a wording
    change that moved nothing but a word onto the next line.
    """
    return " ".join(out.split())


def test_resolving_links_pass(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE", "term-parcel-ascent")})
    path = readme(
        tmp_path,
        f"[CAPE]({url(GLOSSARY, 'term-CAPE')}) and "
        f"[ascent]({url(GLOSSARY, 'term-parcel-ascent')})",
    )
    code, out = run(monkeypatch, capsys, root, path)
    assert code == 0
    assert "2 checked across 1 source, 2 naming an anchor" in out


def test_the_success_line_counts_anchors_and_pages(tmp_path, monkeypatch, capsys):
    root = build(
        tmp_path,
        {GLOSSARY: terms("term-CAPE"), SPECS: "<html><body><p>specs</p></body></html>"},
    )
    path = readme(
        tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')}) and [design]({url(SPECS)})"
    )
    code, out = run(monkeypatch, capsys, root, path)
    # On the success path that line is the whole report. A count that stops
    # distinguishing an anchored link from a bare page link, or that names the
    # wrong number of pages, describes a check other than the one that ran.
    assert code == 0
    assert "2 checked across 1 source, 1 naming an anchor, across 2 pages" in out


def test_one_anchor_broken_twice_is_reported_once(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    link = url(GLOSSARY, "term-parcel-ascent")
    path = readme(tmp_path, f"[ascent]({link}) and again [ascent]({link})")
    code, out = run(monkeypatch, capsys, root, path)
    # One anchor named twice is one thing to fix. Counting the mentions instead
    # would inflate the report and send an author looking for a second break that
    # the README does not have.
    assert code == 1
    assert "Missing anchors (1)" in out
    assert flat(out).count("term-parcel-ascent") == 1


def test_missing_anchor_is_reported(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, f"[ascent]({url(GLOSSARY, 'term-parcel-ascent')})")
    code, out = run(monkeypatch, capsys, root, path)
    assert code == 1
    assert "Missing anchors (1)" in out
    assert f"{GLOSSARY}#term-parcel-ascent" in out
    # The two failures need different fixes, so advice written for the other one
    # sends an author to look for a page that is sitting right where it belongs.
    assert "renaming a term moves its anchor" in flat(out)
    assert "Missing pages" not in out


def test_missing_page_is_reported(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, f"[specs]({url(SPECS, 'term-CAPE')})")
    code, out = run(monkeypatch, capsys, root, path)
    assert code == 1
    assert "Missing pages (1)" in out
    assert "developer/specs/index.html" in out
    assert "answers with a 404" in flat(out)
    # An absent page carries no ids, so it must not also be read as a broken
    # anchor: one cause, reported once, or the count overstates the damage.
    assert "Missing anchors" not in out


def test_every_missing_anchor_is_listed(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(
        tmp_path,
        f"[a]({url(GLOSSARY, 'term-CIN')}) [b]({url(GLOSSARY, 'term-LCL')}) "
        f"[c]({url(GLOSSARY, 'term-CAPE')})",
    )
    code, out = run(monkeypatch, capsys, root, path)
    assert code == 1
    # Reporting the first and stopping would send an author round the build once
    # per broken link, with a green tick promised at the end of every pass.
    assert "Missing anchors (2)" in out
    assert "term-CIN" in out
    assert "term-LCL" in out


def test_the_report_says_what_it_did_not_list(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(
        tmp_path,
        " ".join(f"[{n}]({url(GLOSSARY, f'term-{n}')})" for n in range(10)),
    )
    code, out = run(monkeypatch, capsys, root, path)
    # The header counts every offender, so a listing that quietly stops short
    # invites the reader to conclude the rest were fine.
    assert code == 1
    assert "Missing anchors (10)" in out
    assert "and 4 more" in out


def test_a_preview_host_url_is_not_canonical(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(
        tmp_path,
        f"[CAPE]({url(GLOSSARY, 'term-CAPE')})\n\n[preview]: {PREVIEW}#term-CAPE\n",
    )
    code, out = run(monkeypatch, capsys, root, path)
    # A preview URL resolves for as long as its pull request is open, which is
    # exactly why one gets pasted: the rot arrives later, when nobody is looking.
    assert code == 1
    assert "Non-canonical URLs (1)" in out
    assert f"{PREVIEW}#term-CAPE" in out
    assert "deletes the preview when the pull request closes" in flat(out)
    # The canonical link beside it resolved, and must not be swept in.
    assert "Missing anchors" not in out


def test_an_unpublished_version_is_not_canonical(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    stable = gate.BASE.replace("latest", "stable") + f"{GLOSSARY}#term-CAPE"
    bare = gate.BASE.replace("en/latest/", "") + f"{GLOSSARY}#term-CAPE"
    path = readme(
        tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')}) [s]({stable}) [b]({bare})"
    )
    code, out = run(monkeypatch, capsys, root, path)
    # Both resolve only in an author's head: there is no 'stable' until the
    # project releases, and a path that drops the version names no version.
    assert code == 1
    assert "Non-canonical URLs (2)" in out
    assert stable in out
    assert bare in out
    assert "there is no 'stable' until the project releases" in flat(out)


def test_text_after_the_page_is_not_canonical(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    good = url(GLOSSARY, "term-CAPE")
    stale = f"{url(GLOSSARY)}.bak"
    typo = f"{gate.BASE}reference/glossary.htmlx"
    deeper = f"{url(GLOSSARY)}/extra"
    text = f"[CAPE]({good}) [s]({stale}) [t]({typo}) [d]({deeper})"
    path = readme(tmp_path, text)
    code, out = run(monkeypatch, capsys, root, path)
    # Every one of these begins with a page the build did produce, so a matcher
    # allowed to settle for a prefix reads them as `reference/glossary.html` and
    # discards the trailing text -- which is the whole of what makes them 404.
    assert gate.links(text) == [(GLOSSARY, "term-CAPE")]
    assert code == 1
    assert "Non-canonical URLs (3)" in out
    assert stale in out
    assert typo in out
    assert deeper in out
    assert "text after '.html' names a file the build never produced" in flat(out)


def test_an_http_url_is_not_canonical(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    plain = url(GLOSSARY, "term-CAPE").replace("https://", "http://")
    path = readme(tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')}) [p]({plain})")
    code, out = run(monkeypatch, capsys, root, path)
    # Read the Docs redirects this one to https, so it works today and rots only
    # if that courtesy ends. Matching the host on https alone would hide it from
    # both halves of the check at once: not canonical, and not reported either.
    assert code == 1
    assert "Non-canonical URLs (1)" in out
    assert plain in out
    assert "the scheme is 'https'" in flat(out)


def test_a_quoted_url_is_a_link(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {STYLE: "<html><body></body></html>"})
    text = f'URL = "{gate.BASE}{STYLE}"\n'
    source = tmp_path / "changelog.py"
    source.write_text(text, encoding="utf-8")
    code, out = run(monkeypatch, capsys, root, source)
    # A URL in a script ends at the closing quote, not at a Markdown ")" or "]".
    # Leave the quote out of the terminator set and it is swallowed into the URL,
    # so the page path stops matching and a good link is reported non-canonical --
    # the gate crying wolf at the one kind of source it is being extended to cover.
    assert gate.links(text) == [(STYLE, "")]
    assert gate.strays(text) == []
    assert code == 0
    assert "1 checked" in out


def test_a_directory_url_is_passed_over(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(
        tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')}) [ref]({gate.BASE}reference/)"
    )
    code, out = run(monkeypatch, capsys, root, path)
    # A directory URL resolves on Read the Docs and names no page and no anchor,
    # so there is nothing to look up and nothing to be wrong about.
    assert code == 0
    assert "1 checked" in out


def test_a_source_with_no_links_fails(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, "# tephpy\n\nNo links here.\n")
    code, out = run(monkeypatch, capsys, root, path)
    # A source that has lost its links is a search this gate no longer makes, and
    # a check that passes on an empty search is a green tick over nothing. It is
    # named, because with several sources "nowhere" does not say which one.
    assert code == 1
    assert "README.md links into the documentation nowhere" in out
    assert "Remove it from SOURCES, or restore the link" in flat(out)
    # Every other way of failing says where the rule is written down; this one is
    # about SOURCES, which is the part of the rule that section documents.
    assert "docs-style.rst" in out


def test_a_stray_only_source_is_not_blind(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, f"[preview]({PREVIEW}#term-CAPE)")
    code, out = run(monkeypatch, capsys, root, path)
    # A source linking only non-canonically does link into the documentation, so
    # it is told what is wrong with those links rather than that it has none:
    # calling it blind sends the reader looking for a link that is right there.
    assert code == 1
    assert "Non-canonical URLs (1)" in out
    assert f"{PREVIEW}#term-CAPE" in out
    assert "links into the documentation nowhere" not in out


def test_badge_url_is_not_a_page(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(
        tmp_path,
        "[![RTD](https://app.readthedocs.org/projects/tephpy/badge/?version=latest)]"
        "(https://tephpy.readthedocs.io/en/latest/?badge=latest)\n"
        f"[CAPE]({url(GLOSSARY, 'term-CAPE')})",
    )
    code, out = run(monkeypatch, capsys, root, path)
    # The badge names no page. Reading it as one would fail a good README, and
    # the gate that cries wolf is the gate somebody deletes.
    assert code == 0
    assert "1 checked" in out


def test_usage_is_reported(monkeypatch, capsys):
    monkeypatch.setattr(gate.sys, "argv", ["check_documentation_links.py"])
    assert gate.main() == 1
    assert "usage: check_documentation_links.py" in capsys.readouterr().out


def test_two_sources_are_both_checked(tmp_path, monkeypatch, capsys):
    root = build(
        tmp_path,
        {GLOSSARY: terms("term-CAPE"), STYLE: "<html><body></body></html>"},
    )
    first = readme(tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')})")
    second = script(tmp_path, STYLE)
    code, out = run(monkeypatch, capsys, root, first, second)
    # The counts are of the whole check, not of whichever source came last.
    assert code == 0
    assert "2 checked across 2 sources, 1 naming an anchor, across 2 pages" in out


def test_two_sources_naming_one_page_count_it_once(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    first = readme(tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')})")
    second = script(tmp_path, GLOSSARY)
    code, out = run(monkeypatch, capsys, root, first, second)
    # The page count is a union across sources, not a sum: two sources naming one
    # page have one page between them, and a report that says two is counting
    # links while calling them pages.
    assert code == 0
    assert "2 checked across 2 sources, 1 naming an anchor, across 1 page" in out


def test_a_failure_names_its_source(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    first = readme(tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')})")
    second = script(tmp_path, SPECS)
    code, out = run(monkeypatch, capsys, root, first, second)
    # With more than one source checked, a bare page path does not say which file
    # to open, and the reader is sent hunting through every source for the URL.
    assert code == 1
    assert "Missing pages (1)" in out
    assert f"{SPECS} (" in out
    assert "changelog.py)" in out


def test_one_source_is_not_attributed(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, f"[specs]({url(SPECS)})")
    code, out = run(monkeypatch, capsys, root, path)
    # One source names itself in the invocation, so attributing its entries to it
    # is noise on every line of the report.
    assert code == 1
    assert f"{SPECS}\n" in out
    assert f"{SPECS} (" not in out


def test_a_single_page_is_singular(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')})")
    code, out = run(monkeypatch, capsys, root, path)
    # "across 1 pages" reads as a line nobody has looked at, which is an odd thing
    # for a report whose whole job is to be believed.
    assert code == 0
    assert "1 checked across 1 source, 1 naming an anchor, across 1 page" in out
    assert "1 pages" not in out


def test_the_defaults_come_from_sources(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    monkeypatch.setattr(gate, "SOURCES", ("nowhere/missing.md",))
    code, out = run(monkeypatch, capsys, root)
    # With no source named on the command line the gate checks SOURCES. Were it to
    # fall back to the README instead, adding a file to that list would change
    # nothing and no run would say so.
    assert code == 1
    assert "no such file" in out
    assert "nowhere/missing.md" in out


def test_sources_resolve_against_the_repository_not_the_cwd(
    tmp_path, monkeypatch, capsys
):
    text = (REPO / "README.md").read_text(encoding="utf-8")
    found = gate.links(text)
    # Without a link in it the README is found and then read for nothing, and the
    # run below would pass on having located the file alone.
    assert found, "README.md carries no documentation link for this test to resolve"
    pages = {page: set() for page, _ in found}
    for page, anchor in found:
        if anchor:
            pages[page].add(anchor)
    root = build(
        tmp_path, {page: terms(*sorted(names)) for page, names in pages.items()}
    )
    monkeypatch.setattr(gate, "SOURCES", ("README.md",))
    # Run from somewhere holding no README, which is what the anchoring is for: a
    # SOURCES entry is documented as relative to the repository root, and nothing
    # else here ever leaves it, since every other case names its source on the
    # command line -- the branch that deliberately does not anchor.
    monkeypatch.chdir(tmp_path)
    code, out = run(monkeypatch, capsys, root)
    # Resolved against the working directory instead, every entry becomes "no such
    # file": an exit 1 that reads as a broken link and is a broken invocation, and
    # a run from a pixi task, a hook or `docs/` would meet it rather than CI.
    assert "no such file" not in out
    assert code == 0
    assert f"{len(found)} checked across 1 source" in out


def test_every_listed_source_exists():
    # SOURCES names files by path. A rename that misses this list turns the check
    # into "no such file" on the next run -- a failure, but not the one anyone is
    # looking for, and one that hides whatever the run was meant to catch.
    missing = [name for name in gate.SOURCES if not (REPO / name).is_file()]
    assert missing == []


def test_sources_names_the_deliverables_of_this_gate():
    # Membership, not equality: a later PR adding a source must not break this
    # test, but reverting this branch -- dropping README.md back to being the
    # only source, or losing the script it added -- must.
    assert "README.md" in gate.SOURCES
    assert ".github/scripts/changelog.py" in gate.SOURCES


def test_an_empty_sources_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gate, "SOURCES", ())
    code, out = run(monkeypatch, capsys, tmp_path)
    # With no source named on the command line and none left in SOURCES, the gate
    # has nothing to read. A search of nothing finds nothing wrong, and the
    # success line would print having checked nothing at all.
    assert code == 1
    assert "checked across" not in out
    assert "SOURCES lists no source to check" in out
    assert "a green tick over nothing" in flat(out)
    assert "docs-style.rst" in out
