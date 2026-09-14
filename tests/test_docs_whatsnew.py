# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The what's new section, and the changelog hooks it reads (whatsnew spec §4)."""

from __future__ import annotations

from pathlib import Path
import re
from types import SimpleNamespace

from jinja2 import Template
from packaging.version import Version
import pytest

import tephpy
from tests.by_path import load_path

REPO = Path(__file__).parents[1]
TEMPLATE = REPO / "changelog" / "template.rst"


def _rendered(version: str = "9.9.9", date: str = "2099-01-01") -> str:
    """Render the towncrier template with a context towncrier would give it.

    In memory rather than through `towncrier build`: the assembly writes
    `CHANGELOG.rst`, deletes every fragment, and fails the container census
    (:issue:`318`). Rendering the template is what this is about anyway.
    """
    return Template(TEMPLATE.read_text(encoding="utf-8")).render(
        versiondata=SimpleNamespace(version=version, date=date),
        render_title=True,
        top_underline="=",
        underlines=["^", "-"],
        sections={"": {}},
        definitions={},
    )


def test_the_template_anchors_each_release_by_version():
    # A whatsnew page links this anchor. Keyed on version rather than
    # geovista's date, for the legibility reason of `whatsnew spec §2`
    # decision 2: `changelog-v0.1.0` can be guessed and checked against the
    # page it sits on.
    assert ".. _changelog-v9.9.9:" in _rendered()


def test_the_template_titles_each_release():
    # Without this the assembled changelog has no version headings at all --
    # one release hides it, and from the second the file is an undivided run
    # of entries (`whatsnew spec §3.3`).
    rendered = _rendered()
    assert "v9.9.9 (2099-01-01)" in rendered
    assert "=" * len("v9.9.9 (2099-01-01)") in rendered


CONF = REPO / "docs" / "src" / "conf.py"

#: What `conf.py` must define for the pages to use. Two names in one tuple, so
#: renaming one and not the other fails here rather than rendering a raw
#: `|tp_version|` into the published page (`whatsnew spec §3.2`).
SUBSTITUTIONS = ("tp_version", "build_date")


def _defined_substitutions() -> set[str]:
    """Return the substitution names `conf.py`'s ``rst_epilog`` actually defines.

    Executes `conf.py` and reads the `rst_epilog` it builds, rather than
    regex-scanning the file's text for the same pattern: a text scan matches
    wherever the pattern sits -- a comment, a docstring, an unreachable branch
    -- so it would pass on a substitution that is documented but never built,
    and it would fail on a `rst_epilog` still correct at build time but
    written a different way (indented, or joined together from parts instead
    of a triple-quoted literal). Reading the value checks what Sphinx would
    actually substitute.
    """
    conf = load_path("tephpy_docs_conf", CONF)
    return set(re.findall(r"^\.\. \|(\w+)\| replace::", conf.rst_epilog, re.MULTILINE))


def test_conf_declares_the_substitutions_the_pages_use():
    assert set(SUBSTITUTIONS) <= _defined_substitutions()


CHANGELOG_PAGE = REPO / "docs" / "src" / "reference" / "changelog.rst"

#: The label `latest.rst` links. It sits immediately above the directive, so it
#: resolves to the top of the changelog -- the newest release -- whichever
#: release that is (`whatsnew spec §3.4`).
LATEST_ANCHOR = "changelog-latest"


def test_the_changelog_page_anchors_its_newest_release():
    assert f".. _{LATEST_ANCHOR}:" in CHANGELOG_PAGE.read_text(encoding="utf-8")


WHATSNEW = REPO / "docs" / "src" / "reference" / "whatsnew"
INDEX = WHATSNEW / "index.rst"
LATEST = WHATSNEW / "latest.rst"
TEMPLATE_PAGE = WHATSNEW / "latest.rst.template"


def _pages() -> set[str]:
    """Return every page in the section, by stem. The seed is not a page.

    The section index is the toctree's host, not one of its entries -- the
    same way a quadrant landing page's own table never names itself -- so it
    is excluded here rather than by the glob.
    """
    return {path.stem for path in WHATSNEW.glob("*.rst")} - {INDEX.stem}


def _toctree_entries() -> list[str]:
    """Return the section index's toctree entries, in order."""
    body = INDEX.read_text(encoding="utf-8").split(".. toctree::", 1)[1]
    return [
        line.strip()
        for line in body.splitlines()
        if line.startswith("    ") and line.strip() and not line.strip().startswith(":")
    ]


def test_the_toctree_lists_every_page_in_the_section():
    # A page the toctree does not name builds clean and is unreachable from the
    # section it belongs to -- the rule `narrative spec §3.9` gives the quadrant
    # landing pages, borrowed here (`whatsnew spec §4`). The include is a
    # convenience that always duplicates one entry and is never a page's only
    # route, so the toctree alone is what this reads.
    assert set(_toctree_entries()) == _pages()


def test_the_section_index_includes_a_page_the_toctree_names():
    # The body a reader meets is the newest *released* highlights -- decision 5
    # of `whatsnew spec §2` -- so whatever it includes must be a real page.
    (included,) = re.findall(
        r"^\.\. include:: (\S+)$", INDEX.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert included.removesuffix(".rst") in _pages()


def test_the_seed_is_not_a_page():
    # `latest.rst.template` is copied into place at release time and is not
    # itself published; `.glob("*.rst")` must not collect it.
    assert TEMPLATE_PAGE.is_file()
    assert "latest.rst" not in _pages()


#: The first release. The placeholder gate below is one-sided against this for
#: the reason `start spec §3.7` records having to become one-sided: the release
#: signal moves when the repository is tagged, and the page is edited on a
#: different commit over the same tree.
FIRST_RELEASE = Version("0.1.0")

#: What the seed carries until a release manager writes over it.
PLACEHOLDER = "``TBD`` prior to release."


def _frozen() -> list[Path]:
    """Return the frozen release pages -- every page but `latest.rst`."""
    return sorted(p for p in WHATSNEW.glob("*.rst") if p.name != "latest.rst")


def test_no_frozen_page_carries_the_substitutions():
    # A frozen page stays in the toctree for the life of the project. Left
    # substituted it would render with whatever version the *next* build is --
    # a page about 0.1 announcing 0.2 (`whatsnew spec §3.2`). Freezing replaces
    # them with literal text, and forgetting that is invisible until the next
    # release, which is why this reads the pages rather than trusting the step.
    offenders = {
        path.name: name
        for path in _frozen()
        for name in SUBSTITUTIONS
        if f"|{name}|" in path.read_text(encoding="utf-8")
    }
    assert offenders == {}


def test_the_accumulating_page_is_written_before_a_release():
    # One-sided: released forbids the placeholder, unreleased does not require
    # its absence. Shipping `TBD` as the highlights of a release is the one
    # failure here that reaches every reader.
    if Version(tephpy.__version__) < FIRST_RELEASE:
        pytest.skip(f"{tephpy.__version__} predates the first release")
    assert PLACEHOLDER not in LATEST.read_text(encoding="utf-8")
