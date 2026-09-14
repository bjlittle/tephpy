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
