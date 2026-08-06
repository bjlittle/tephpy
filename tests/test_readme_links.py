# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the README documentation-link gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_readme_links.py"

# As in `test_rendered_citations.py`: `MANIFEST.in` prunes `.github`, so an sdist
# ships these tests without the gate they exercise. The guard sits on the module
# and not inside the tests, because an unconditional import would break
# collection there rather than skip.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="not a checkout of the repository"
)

GLOSSARY = "reference/glossary.html"
SPECS = "developer/specs/index.html"
PREVIEW = "https://tephpy--99.org.readthedocs.build/en/99/reference/glossary.html"


def _load():
    """Import the gate by path; ``.github`` is not an importable package."""
    assert SCRIPT.is_file(), f"the README link gate is missing from {SCRIPT}"
    spec = importlib.util.spec_from_file_location("check_readme_links", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


crl = _load() if SCRIPT.is_file() else None


def url(page, anchor=""):
    """Build the published URL of ``page``, naming ``anchor`` when given."""
    return crl.BASE + page + (f"#{anchor}" if anchor else "")


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


def run(monkeypatch, capsys, root, path):
    """Run the gate over ``root`` and ``path``; return its code and output."""
    monkeypatch.setattr(
        crl.sys, "argv", ["check_readme_links.py", str(root), str(path)]
    )
    code = crl.main()
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
    assert "2 checked, 2 naming an anchor" in out


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
    assert "2 checked, 1 naming an anchor, across 2 pages" in out


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
    path = readme(tmp_path, f"[specs]({url('developer/specs/index.html')})")
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
    stable = crl.BASE.replace("latest", "stable") + f"{GLOSSARY}#term-CAPE"
    bare = crl.BASE.replace("en/latest/", "") + f"{GLOSSARY}#term-CAPE"
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


def test_a_directory_url_is_passed_over(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(
        tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')}) [ref]({crl.BASE}reference/)"
    )
    code, out = run(monkeypatch, capsys, root, path)
    # A directory URL resolves on Read the Docs and names no page and no anchor,
    # so there is nothing to look up and nothing to be wrong about.
    assert code == 0
    assert "1 checked" in out


def test_readme_with_no_links_fails(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, "Plot and analyse tephigrams.")
    code, out = run(monkeypatch, capsys, root, path)
    # A gate is worth what it covers. A rewrite that dropped every link would
    # otherwise turn this into a green tick over an empty search.
    assert code == 1
    assert "links into the documentation nowhere" in out
    assert "green tick standing for nothing" in flat(out)


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
    monkeypatch.setattr(crl.sys, "argv", ["check_readme_links.py"])
    assert crl.main() == 1
    assert "usage: check_readme_links.py" in capsys.readouterr().out
