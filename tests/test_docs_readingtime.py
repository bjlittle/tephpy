# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the reading-time directive and its coverage gate (reading spec §6)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
DOCS = REPO / "docs" / "src"
EXT = DOCS / "_ext"


def _load(name: str):
    """Import an extension module by path; ``_ext`` is not an importable package."""
    path = EXT / f"{name}.py"
    assert path.is_file(), f"the module is missing from {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# `_ext` is a `sys.path` entry at build time rather than a package, so a module
# there resolves its siblings by top-level name and cannot be imported until that
# entry exists (:issue:`92`).
if str(EXT) not in sys.path:
    sys.path.insert(0, str(EXT))

reading = _load("tephpy_reading")


def test_the_default_rate_is_the_one_the_specification_cites():
    """Reading spec §3.4 fixes 150, below Brysbaert's 175 non-fiction floor."""
    assert reading.WPM == 150


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),
        ("one", 1),
        ("one two three", 3),
        # `\w+` splits on punctuation, so a dotted name counts as its parts. The
        # banner and the gate must agree on that, which is why it is pinned.
        ("tephpy.plotting.axes", 3),
        ("hyphen-ated", 2),
        ("   spaced   out   ", 2),
        ("newlines\nare\nwhitespace", 3),
    ],
)
def test_count_words_counts_word_character_runs(text, expected):
    assert reading.count_words(text) == expected


@pytest.mark.parametrize(
    ("words", "wpm", "expected"),
    [
        (0, 150, 1),  # the floor: no page reads in zero minutes
        (1, 150, 1),
        (150, 150, 1),
        (151, 150, 2),  # rounds up, never down
        (300, 150, 2),
        (1500, 150, 10),
        (300, 100, 3),  # the rate is honoured
    ],
)
def test_estimate_minutes_rounds_up_with_a_floor_of_one(words, wpm, expected):
    assert reading.estimate_minutes(words, wpm) == expected


def test_estimate_minutes_defaults_to_the_house_rate():
    assert reading.estimate_minutes(300) == reading.estimate_minutes(300, reading.WPM)


@pytest.mark.parametrize(
    ("argument", "minutes", "wpm"),
    [
        (None, None, 150),  # no argument: count at the house rate
        ("30", 30, 150),  # a literal duration, quoted not counted
        ("1", 1, 150),
        ("200wpm", None, 200),  # a rate override; the count still happens
        ("200WPM", None, 200),  # case-insensitive
        ("90wpm", None, 90),
    ],
)
def test_parse_argument_reads_the_two_documented_shapes(argument, minutes, wpm):
    parsed = reading.parse_argument(argument)
    assert parsed.minutes == minutes
    assert parsed.wpm == wpm


@pytest.mark.parametrize(
    "argument",
    [
        "thirty",  # the prior art computes an estimate here and warns nobody
        "",
        "10 minutes",
        "wpm",
        "0wpm",  # a zero rate would divide by zero
        "0",  # a zero-minute page is not a duration
        "-5",
        "12wpmx",  # anchored at both ends
        "x200wpm",
    ],
)
def test_parse_argument_rejects_anything_else(argument):
    """Reading spec §3.2: an argument the directive cannot read stops the build."""
    with pytest.raises(ValueError, match="readingtime"):
        reading.parse_argument(argument)


RST_PAGE = """\
.. _howto-example:

An Example Page
===============

.. readingtime::

A lead paragraph.

A Section
---------

Body text.
"""

MYST_PAGE = """\
# An Example Specification

```{readingtime}
```

> **Living document.**

(example-spec-1)=
## 1. Purpose

Body text.
"""


def test_the_rst_title_is_the_first_underline():
    assert reading.title_line(RST_PAGE, ".rst") == 4


def test_the_rst_first_section_is_the_second_underline():
    assert reading.first_section_line(RST_PAGE, ".rst") == 11


def test_a_page_with_no_sections_has_no_first_section():
    text = "Only a Title\n============\n\n.. readingtime::\n\nBody.\n"
    assert reading.first_section_line(text, ".rst") is None
    assert reading.carries_reading_time(text, ".rst")


def test_the_myst_title_is_the_first_atx_heading():
    assert reading.title_line(MYST_PAGE, ".md") == 1


def test_the_myst_first_section_is_the_first_level_two_heading():
    assert reading.first_section_line(MYST_PAGE, ".md") == 9


def test_a_directive_in_the_lead_satisfies_the_rule():
    assert reading.carries_reading_time(RST_PAGE, ".rst")
    assert reading.carries_reading_time(MYST_PAGE, ".md")


def test_a_page_without_the_directive_does_not():
    without = RST_PAGE.replace(".. readingtime::\n", "")
    assert not reading.carries_reading_time(without, ".rst")


def test_a_directive_after_the_first_section_does_not_satisfy_the_rule():
    """Reading spec §3.6, decision 5: the banner is for a reader who hasn't scrolled."""
    moved = RST_PAGE.replace(".. readingtime::\n\n", "").replace(
        "Body text.\n", ".. readingtime::\n\nBody text.\n"
    )
    assert reading.directive_lines(moved, ".rst")
    assert not reading.carries_reading_time(moved, ".rst")


def test_an_indented_directive_is_a_demonstration_and_does_not_count():
    """What lets `docs-style.rst` show the directive and carry a live one."""
    shown = RST_PAGE.replace(".. readingtime::", ".. code::\n\n       .. readingtime::")
    assert reading.directive_lines(shown, ".rst") == []
    assert not reading.carries_reading_time(shown, ".rst")


def test_an_rst_directive_glued_to_trailing_text_does_not_count():
    """Important 1: `.. readingtime::junk` at column 0 is a comment to docutils.

    `RST_DIRECTIVE` used to match on prefix alone, so the gate would credit the
    page with a directive that renders no banner at all.
    """
    text = RST_PAGE.replace(".. readingtime::", ".. readingtime::junk")
    assert reading.directive_lines(text, ".rst") == []
    assert not reading.carries_reading_time(text, ".rst")


def test_the_myst_directive_is_found_although_it_is_itself_a_fence():
    """Reading spec §3.6: a fence-skipping reader cannot see the opening rail."""
    assert reading.directive_lines(MYST_PAGE, ".md") == [3]


@pytest.mark.parametrize(
    "info",
    ["{readingtime}", "{readingtime} 45", "{readingtime} 200wpm"],
    ids=["bare", "minutes", "wpm"],
)
def test_a_myst_directive_carrying_an_argument_is_still_found(info):
    """Important 1: the MyST half must match a directive that takes an argument.

    `directive_lines` used to compare the whole info string against
    `MYST_DIRECTIVE` with `==`, so `` ```{readingtime} 45 `` -- a documented
    override, reading spec §3.2 -- was invisible to the gate: an author using
    either override would be told by the coverage test to add a directive they
    had already added.
    """
    text = MYST_PAGE.replace("```{readingtime}", f"```{info}")
    assert reading.directive_lines(text, ".md") == [3]
    assert reading.carries_reading_time(text, ".md")


def test_a_different_myst_directive_is_not_found():
    """The token match must not widen into a substring or prefix match."""
    text = MYST_PAGE.replace("```{readingtime}", "```{note}")
    assert reading.directive_lines(text, ".md") == []


def test_a_directive_quoted_inside_a_myst_fence_does_not_count():
    quoted = MYST_PAGE.replace(
        "Body text.\n",
        "````\n```{readingtime}\n```\n````\n",
    )
    assert reading.directive_lines(quoted, ".md") == [3]


def test_a_heading_inside_a_myst_fence_is_not_a_section():
    """The defect `tephpy_citations.read_lines` documents, in the other direction."""
    fenced = MYST_PAGE.replace("Body text.\n", "```\n## Not a heading\n```\n")
    assert reading.first_section_line(fenced, ".md") == 9


def test_the_myst_scanner_keeps_the_rail_discipline():
    """A four-backtick block may quote a three-backtick one without closing."""
    text = "# Title\n\n````\n```\n## quoted\n```\n````\n\n## 1. Real\n"
    assert reading.first_section_line(text, ".md") == 9


#: Trees that carry no hand-written page, so no author could add the directive to
#: them. This is a different thing from an exemption (reading spec §3.6): `EXEMPT`
#: below is for pages somebody could have written it on and should not.
EXCLUDED_DIRS = (
    "_static",  # Sphinx excludes `html_static_path` from document discovery
    "developer/plans",  # tracked but unpublished (docs spec §3.1)
    "gallery",  # generated by sphinx-gallery, and untracked
    "reference/generated",  # generated by autoapi
)

#: sphinx-gallery writes one beside each gallery it builds, including at the root.
GENERATED_PAGES = ("sg_execution_times.rst",)

#: The pages that are navigated rather than read (reading spec §3.7). Each entry
#: states why, because a list with a silent escape hatch is what decision 3 exists
#: to prevent.
EXEMPT = (
    "index.rst",  # the site landing page: a card grid and a toctree
    "tutorials/index.rst",  # quadrant landing page
    "howtos/index.rst",  # quadrant landing page
    "explanation/index.rst",  # quadrant landing page
    "reference/index.rst",  # quadrant landing page
    "developer/index.rst",  # section landing page: a heading and a toctree
    "developer/specs/index.rst",  # the specification toctree and prefix table
    "reference/changelog.rst",  # the page is a `sphinx_changelog` directive
    "reference/cli.rst",  # the body is generated by `sphinx-click`
    "reference/config.rst",  # the body is generated by `tephpy-config-options`
    "reference/references.rst",  # the body is generated by a `bibliography` directive
    "reference/glossary.rst",  # a lookup table, not read in order
)


def published_pages(docs: Path = DOCS) -> list[Path]:
    """Every hand-written page Sphinx publishes.

    Derived rather than declared (reading spec §3.6), so a page is governed from
    the day it lands.

    Parameters
    ----------
    docs : Path, optional
        The documentation source root. It defaults to this repository's, which is
        what the gate reads; a test passes a tree of its own.

    Returns
    -------
    list of Path
        The `.rst` and `.md` sources, sorted.

    """
    found: list[Path] = []
    for path in sorted([*docs.rglob("*.rst"), *docs.rglob("*.md")]):
        relative = path.relative_to(docs).as_posix()
        if any(relative.startswith(f"{name}/") for name in EXCLUDED_DIRS):
            continue
        if path.name in GENERATED_PAGES:
            continue
        found.append(path)
    return found


def identify(page: Path) -> str:
    """Name a page for a parametrised test id."""
    return page.relative_to(DOCS).as_posix()


def test_the_corpus_is_not_empty():
    """A gate that finds nothing passes by never having looked."""
    assert len(published_pages()) > 30


def test_the_corpus_holds_a_member_of_every_quadrant_it_governs():
    """Membership, not a count: a count is a figure that must be re-measured."""
    found = {identify(page) for page in published_pages()}
    for member in (
        "howtos/logo.rst",
        "tutorials/first-tephigram.rst",
        "explanation/rotated-axes.rst",
        "developer/docs-style.rst",
        "developer/specs/2026-08-31-reading-time-design.md",
    ):
        assert member in found, f"{member} is missing from the corpus"


def test_the_corpus_excludes_the_generated_and_unpublished_trees():
    found = {identify(page) for page in published_pages()}
    assert not any(name.startswith("developer/plans/") for name in found)
    assert not any(name.startswith("gallery/") for name in found)
    assert not any(name.startswith("_static/") for name in found)
    assert "sg_execution_times.rst" not in found


@pytest.mark.parametrize("name", EXCLUDED_DIRS)
def test_every_excluded_tree_exists(name):
    """An exclusion naming nothing is an exclusion that stopped excluding.

    The skip is conditioned on the tree's actual absence, not on a hardcoded set of
    names expected to be absent -- the earlier version skipped `gallery` and
    `reference/generated` unconditionally, so it never checked either even in a
    workspace (this one, most of the time) where a docs build has already populated
    them. The name itself is checked regardless of whether the tree exists: a leading
    or trailing slash would make `published_pages`'s ``str.startswith(f"{name}/")``
    prefix match silently exclude nothing.
    """
    assert not name.startswith("/"), f"{name} has a leading slash"
    assert not name.endswith("/"), f"{name} has a trailing slash"
    if not (DOCS / name).is_dir():
        pytest.skip(f"{name} exists only after a docs build")


@pytest.mark.parametrize("name", ["_static", "developer/plans"])
def test_every_tracked_excluded_tree_exists_unconditionally(name):
    """`_static` and `developer/plans` may not skip.

    Unlike `gallery` and `reference/generated`, they are tracked, so their existence
    never depends on a docs build having run. The CI test matrix carries no Sphinx and
    never runs one (reading spec decision 4).
    """
    assert (DOCS / name).is_dir(), f"{name} is not a directory under {DOCS}"


def test_the_plans_are_excluded_by_the_build_and_not_only_by_this_gate():
    """The exclusion tracks `conf.py` rather than restating a claim about it."""
    conf = (DOCS / "conf.py").read_text(encoding="utf-8")
    assert '"developer/plans/**"' in conf


@pytest.mark.parametrize("name", EXEMPT)
def test_every_exempt_page_still_exists(name):
    """A renamed page whose exemption stayed behind would be silently exempt."""
    assert (DOCS / name).is_file(), f"{name} is exempt but is not a page"


def test_the_exempt_pages_are_all_in_the_corpus():
    """An exemption for a page the corpus never had is exempting nothing."""
    found = {identify(page) for page in published_pages()}
    assert set(EXEMPT) <= found


def test_published_pages_excludes_a_synthetic_tree_of_its_own(tmp_path):
    """Every exclusion is pinned regardless of what a docs build has left behind.

    This exercises the `docs` parameter directly. Against the real tree, `gallery/`
    and `reference/generated/` are only ever excluded when a prior docs build happened
    to populate them -- in a fresh checkout neither exists,
    `test_the_corpus_excludes_the_generated_and_unpublished_trees` finds no
    `gallery/*` entries whether or not the rule is even applied, and the assertion
    passes for the wrong reason. A tree built fresh under `tmp_path` for this test
    alone always has both, so the exclusion is checked whether or not this workspace
    has ever run `docs-html`.
    """
    survivors = {
        "index.rst",
        "explanation/example.md",
        # starts with an excluded directory's name, but is a file beside it, not a
        # member of it -- `"gallery.rst".startswith("gallery/")` is `False`.
        "gallery.rst",
    }
    excluded = {
        "_static/tephpy.rst",
        "developer/plans/2099-01-01-example.md",
        "gallery/plot_example.rst",
        "reference/generated/tephpy.rst",
        "sg_execution_times.rst",
        "gallery/sg_execution_times.rst",
    }
    for relative in survivors | excluded:
        page = tmp_path / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("Title\n=====\n", encoding="utf-8")

    found = {
        page.relative_to(tmp_path).as_posix() for page in published_pages(tmp_path)
    }
    assert found == survivors


def carrying_pages() -> list[Path]:
    """Return the published pages a reader reads start to finish (reading spec §3.7)."""
    return [page for page in published_pages() if identify(page) not in EXEMPT]


@pytest.mark.parametrize("page", carrying_pages(), ids=identify)
def test_every_page_a_reader_reads_carries_a_reading_time(page):
    """Reading spec §3.6: absence is a failure, not an omission.

    A page with no banner would otherwise be ambiguous between "short" and
    "nobody got round to it", which is the reason the rule is gated at all.
    """
    text = page.read_text(encoding="utf-8")
    assert reading.carries_reading_time(text, page.suffix), (
        f"{identify(page)} carries no `readingtime` directive in its lead: put one "
        f"after the title and before the first section heading, at column 0, or add "
        f"the page to EXEMPT with the reason it is navigated rather than read"
    )


@pytest.mark.parametrize("page", carrying_pages(), ids=identify)
def test_no_page_carries_more_than_one_reading_time(page):
    """Two banners on one page is a copy-paste, not a decision.

    `docs-style.rst` is the exception the rule allows for: the demonstrations in
    its Reading Time section sit inside literal blocks, indented, so they are not
    directives at column 0 and do not count here.
    """
    text = page.read_text(encoding="utf-8")
    assert len(reading.directive_lines(text, page.suffix)) == 1


@pytest.mark.parametrize("name", EXEMPT)
def test_no_exempt_page_carries_a_reading_time(name):
    """The two tests above enforce reading spec §3.7's list in one direction only.

    `carrying_pages` filters `EXEMPT` out before either runs, so an exempt page
    that grew a banner -- a stale exemption, or a copy-paste -- would pass both
    of them silently.
    """
    text = (DOCS / name).read_text(encoding="utf-8")
    assert not reading.carries_reading_time(text, Path(name).suffix), (
        f"{name} is in EXEMPT and carries a `readingtime` directive: remove the "
        f"directive, or remove the page from EXEMPT if it is read start to finish"
    )
