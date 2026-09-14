# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The what's new section, and the changelog hooks it reads (whatsnew spec §4)."""

from __future__ import annotations

from pathlib import Path
import re

from jinja2 import Template

from tests.by_path import load_path
from tests.test_docs_landing_pages import toctree_entries

REPO = Path(__file__).parents[1]
TEMPLATE = REPO / "changelog" / "template.rst"


def _rendered(version: str = "9.9.9", date: str = "2099-01-01") -> str:
    """Render the towncrier template with the context towncrier actually gives it.

    In memory rather than through `towncrier build`: the assembly writes
    `CHANGELOG.rst`, deletes every fragment, and fails the container census
    (:issue:`318`). Rendering the template is what this is about anyway.

    `versiondata` is a plain dict, built by `towncrier/build.py` as
    `{"name": ..., "version": ..., "date": ...}`, not an object -- so this
    builds one too rather than a `SimpleNamespace`. `underlines` is
    `["-", "~"]` here, the two underlines left after towncrier's default
    `("=", "-", "~")` gives its first to `top_underline`. Neither would have
    been caught by the template if wrong: jinja falls back to `__getitem__`
    for attribute lookups on a dict, and `changelog/template.rst` hardcodes
    `"^"` for category underlines rather than reading `underlines` at all --
    but a context that is wrong for reasons the template happens not to
    exercise is still a context this function should not claim to be right.
    """
    return Template(TEMPLATE.read_text(encoding="utf-8")).render(
        versiondata={"name": "Tephpy", "version": version, "date": date},
        render_title=True,
        top_underline="=",
        underlines=["-", "~"],
        sections={"": {}},
        definitions={},
    )


def test_the_template_anchors_each_release_by_version():
    # A whatsnew page links this anchor. Keyed on version rather than
    # geovista's date, for the legibility reason of `whatsnew spec §2`
    # decision 2: `changelog-v0.1.0` can be guessed and checked against the
    # page it sits on.
    assert ".. _changelog-v9.9.9:" in _rendered()


def test_the_release_title_nests_under_the_changelog_page():
    """A release is a section *of* the changelog, not a second page title.

    docutils reads a document's heading levels from the order the underline
    styles first appear. `docs/src/reference/changelog.rst` opens with ``=``, so
    a release title underlined the same way is a *sibling* top-level section
    rather than a subsection -- the page then has two top-level sections, and
    `reference/index.rst`'s toctree lists the newest release beside *Changelog*
    as though it were a page of its own. Observed in the built site
    (:pull:`322`); towncrier's `top_underline` is ``=`` by default, which is why
    this template does not use it.
    """
    rendered = _rendered()
    title = "v9.9.9 (2099-01-01)"
    assert f"{title}\n{'-' * len(title)}" in rendered
    assert f"{title}\n{'=' * len(title)}" not in rendered


def test_the_template_titles_each_release():
    # Without this the assembled changelog has no version headings at all --
    # one release hides it, and from the second the file is an undivided run
    # of entries (`whatsnew spec §3.3`).
    # The underline is the sibling test's subject, not this one's.
    assert "v9.9.9 (2099-01-01)" in _rendered()


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

    Executing it is not free of side effects: it creates
    `docs/_build/plot-scratch/` on disk if the directory is not there already,
    prepends `docs/src/_ext` to `sys.path`, and leaves the module registered in
    `sys.modules` under the name `load_path` is given below. All harmless for a
    test process -- the directory is git-ignored and idempotent to recreate,
    the `sys.path` entry only adds an extension Sphinx would add anyway, and
    nothing else claims that module name -- but real, and worth knowing before
    debugging a test that runs after this one.
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


def test_the_toctree_lists_every_page_in_the_section():
    # A page the toctree does not name builds clean and is unreachable from the
    # section it belongs to -- the rule `narrative spec §3.9` gives the quadrant
    # landing pages, borrowed here (`whatsnew spec §4`). The include is a
    # convenience that always duplicates one entry and is never a page's only
    # route, so the toctree alone is what this reads.
    #
    # `toctree_entries` is `tests/test_docs_landing_pages.py`'s, not a local
    # copy: it stops at the toctree's first unindented line and asserts there
    # is exactly one, rather than taking everything after the directive
    # unbounded.
    source = INDEX.read_text(encoding="utf-8")
    assert set(toctree_entries(source)) == _pages()


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


#: What the seed carries until a release manager writes over it.
PLACEHOLDER = "``TBD`` prior to release."


def _frozen() -> list[Path]:
    """Return the frozen release pages -- every page but `latest.rst`.

    Excludes the section index by stem, the same way `_pages()` does above --
    it hosts the toctree rather than being one of the pages in it, so it is
    not a release page and does not belong in "frozen".
    """
    return sorted(
        p for p in WHATSNEW.glob("*.rst") if p.stem not in {LATEST.stem, INDEX.stem}
    )


def test_no_frozen_page_carries_the_substitutions():
    # A frozen page stays in the toctree for the life of the project. Left
    # substituted it would render with whatever version the *next* build is --
    # a page about 0.1 announcing 0.2 (`whatsnew spec §3.2`). Freezing replaces
    # them with literal text, and forgetting that is invisible until the next
    # release, which is why this reads the pages rather than trusting the step.
    #
    # A set of (page, substitution) pairs rather than a dict keyed on the page
    # name: a page can carry both substitutions, and a dict keyed on the page
    # alone would let the second overwrite the first, reporting only one.
    offenders = {
        (path.name, name)
        for path in _frozen()
        for name in SUBSTITUTIONS
        if f"|{name}|" in path.read_text(encoding="utf-8")
    }
    assert offenders == set()


def test_no_frozen_page_carries_the_placeholder():
    # A frozen release page carrying `TBD` is always wrong (whatsnew spec §4):
    # it needs no comparison against the installed version to be wrong, it is
    # vacuous before the first release since nothing is frozen yet, and it
    # fires on the release pull request that does the freezing rather than at
    # the tag it produces. `latest.rst` is not part of `_frozen()` and carries
    # the placeholder for most of every cycle by design -- `whatsnew spec §3.5`
    # step 3 reseeds it from the template, placeholder and all, after every
    # release.
    #
    # A set of page names rather than a single assertion against one page, the
    # same reporting shape as `test_no_frozen_page_carries_the_substitutions`
    # above: more than one frozen page can carry it.
    offenders = {
        path.name
        for path in _frozen()
        if PLACEHOLDER in path.read_text(encoding="utf-8")
    }
    assert offenders == set()
