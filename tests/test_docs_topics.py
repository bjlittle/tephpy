# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The topic taxonomy, its corpus and its promotion rule (topics spec §6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tephpy import examples
from tests.ext_modules import load

topics = load("tephpy_topics_data")


def test_the_vocabulary_is_the_seventeen_terms_the_specification_defines():
    """Topics spec §3.3 is a closed vocabulary with a definition per term."""
    assert len(topics.VOCABULARY) == 17
    assert "sounding" in topics.VOCABULARY
    assert "data-input" in topics.VOCABULARY


def test_the_bounds_are_the_gallery_specification_s_own():
    assert topics.MIN_TAGS == 2
    assert topics.MAX_TAGS == 4
    assert topics.MIN_QUADRANTS == 2


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("units, sounding", ["units", "sounding"]),
        ("units,sounding", ["units", "sounding"]),
        ("  units ,  sounding  ", ["units", "sounding"]),
        ("units", ["units"]),
        ("", []),
        ("units, , sounding", ["units", "sounding"]),
    ],
)
def test_split_tags_reads_a_comma_separated_field_body(value, expected):
    """`env.metadata` hands the adapter the field body as one string."""
    assert topics.split_tags(value) == expected


def test_read_page_tags_reads_a_field_list_at_the_head_of_the_file():
    """Measured: only a field list preceding all other markup reaches metadata."""
    source = (
        ":tags: units, sounding\n\n.. _howto-units:\n\nWork With Units\n"
        "===============\n"
    )
    assert topics.read_page_tags(source) == ["units", "sounding"]


def test_read_page_tags_rejects_a_field_list_under_the_title():
    """The position topics spec §3.2 originally proposed, which does not work.

    Measured in a build: a field list under the title is left in the doctree and
    renders as a visible definition list, and `env.metadata` stays empty. The
    reader is as strict as Sphinx so that the gate fails the page rather than the
    reader silently finding no tags on a page that appears to declare them.
    """
    source = "Work With Units\n===============\n\n:tags: units, sounding\n"
    assert topics.read_page_tags(source) == []


def test_read_page_tags_finds_nothing_on_an_untagged_page():
    assert topics.read_page_tags(".. _howto-units:\n\nWork With Units\n") == []


def test_read_gallery_tags_reads_the_flag_sphinx_gallery_reads():
    source = '"""Doc."""\n# sphinx_gallery_tags = ["metpy", "barbs", "sounding"]\n'
    assert topics.read_gallery_tags(source) == ["metpy", "barbs", "sounding"]


def test_read_gallery_tags_rejects_a_misspelled_flag():
    """sphinx-gallery discards `sphinx_gallery_tag` in silence, so the gate must not."""
    source = '"""Doc."""\n# sphinx_gallery_tag = ["metpy", "barbs"]\n'
    assert topics.read_gallery_tags(source) == []


#: A corpus in which every term sits on a documented side of both thresholds.
#: Six items, so "fewer than half" is "fewer than three".
FIXTURE = {
    "a": ("tutorials", ["spanning", "narrow", "broad"]),
    "b": ("howtos", ["spanning", "broad"]),
    "c": ("tutorials", ["narrow", "broad"]),
    "d": ("explanation", ["halved", "broad"]),
    "e": ("gallery", ["halved", "broad"]),
    "f": ("gallery", ["halved", "solo"]),
}


def test_a_term_in_exactly_two_quadrants_promotes():
    """The lower boundary of the first condition (topics spec §3.4)."""
    assert "spanning" in topics.promote(FIXTURE)


def test_a_term_in_one_quadrant_is_held_back():
    """`barbs` is the live example: two gallery examples, no narrative page."""
    assert "narrow" not in topics.promote(FIXTURE)
    assert "solo" not in topics.promote(FIXTURE)


def test_a_term_selecting_exactly_half_the_corpus_is_held_back():
    """Reads "fewer than half" strictly: three of six does not promote."""
    assert len(FIXTURE) == 6
    assert sum("halved" in tags for _, tags in FIXTURE.values()) == 3
    assert "halved" not in topics.promote(FIXTURE)


def test_a_term_selecting_more_than_half_the_corpus_is_held_back():
    """`sounding` is the live example: twelve of nineteen items."""
    assert "broad" not in topics.promote(FIXTURE)


def test_promotion_needs_both_conditions_and_the_fixture_proves_each_alone():
    """Neither condition alone would give this answer.

    `narrow` passes the breadth cap and fails the span; `halved` passes the span
    and fails the cap. A rule that dropped either condition would promote one of
    them, so this asserts the conjunction rather than the result.
    """
    assert topics.promote(FIXTURE) == frozenset({"spanning"})


def test_promotion_over_an_empty_corpus_is_an_error():
    """A rule that returns an empty set over nothing reports "no buttons" twice.

    Once for a corpus with no spanning term, and once for a corpus the caller
    failed to assemble -- and those need different fixes.
    """
    with pytest.raises(ValueError, match="corpus"):
        topics.promote({})


def test_coverage_reports_the_quadrants_each_term_appears_in():
    """The matrix of topics spec §3.8, and what `promote` counts its span from."""
    found = topics.coverage(FIXTURE)
    assert found["spanning"] == frozenset({"tutorials", "howtos"})
    assert found["solo"] == frozenset({"gallery"})
    assert set(found) == {"spanning", "narrow", "broad", "halved", "solo"}


REPO = Path(__file__).parents[1]
DOCS = REPO / "docs" / "src"
EXAMPLES = Path(examples.__file__).parent


def narrative_pages(docs: Path = DOCS) -> list[Path]:
    """Every hand-written page of the three narrative quadrants.

    Discovered rather than listed (topics spec §3.1), so a page added tomorrow
    fails this gate until it declares tags. A hand-maintained list is one a new
    page silently misses.

    Parameters
    ----------
    docs : Path, optional
        The documentation source root. It defaults to this repository's; a test
        passes a tree of its own.

    Returns
    -------
    list of Path
        The quadrants' pages, sorted, without their landing pages.

    """
    found: list[Path] = []
    for quadrant in topics.NARRATIVE:
        found.extend(
            path
            for path in sorted((docs / quadrant).rglob("*.rst"))
            if path.name != "index.rst"
        )
    return found


def narrative_corpus(docs: Path = DOCS) -> dict[str, tuple[str, list[str]]]:
    """Return the narrative half of the corpus, keyed as Sphinx names it.

    The quadrant is the page's **top-level** directory under `docs`, not its
    immediate parent, and the key is its whole relative path without the suffix.
    For a page sitting directly in a quadrant the two are the same string; for
    `howtos/advanced/tuning.rst` they are not, and `page.parent.name` would call
    the quadrant `advanced` -- a name the vocabulary has never heard of.

    Parameters
    ----------
    docs : Path, optional
        The documentation source root.

    Returns
    -------
    dict
        Docname to ``(quadrant, tags)``.

    """
    found: dict[str, tuple[str, list[str]]] = {}
    for page in narrative_pages(docs):
        relative = page.relative_to(docs)
        found[relative.with_suffix("").as_posix()] = (
            relative.parts[0],
            topics.read_page_tags(page.read_text(encoding="utf-8")),
        )
    return found


def corpus() -> dict[str, tuple[str, list[str]]]:
    """Return the tagged corpus of topics spec §3.1.

    Returns
    -------
    dict
        Docname to ``(quadrant, tags)``, the docname being what Sphinx calls the
        page and so what the extension keys by.

    """
    found = narrative_corpus()
    found.update(
        {
            f"gallery/{path.stem}": (
                "gallery",
                topics.read_gallery_tags(path.read_text(encoding="utf-8")),
            )
            for path in sorted(EXAMPLES.glob("plot_*.py"))
        }
    )
    return found


def test_the_corpus_is_not_empty():
    """A gate that finds nothing passes by never having looked."""
    assert len(corpus()) > 15


def test_the_corpus_holds_a_member_of_every_quadrant_it_governs():
    """Membership, not a count: a count is a figure that must be re-measured."""
    found = corpus()
    for member in (
        "tutorials/first-tephigram",
        "howtos/units",
        "explanation/rotated-axes",
        "gallery/plot_tephigram",
    ):
        assert member in found, f"{member} is missing from the corpus"


def test_the_corpus_excludes_the_quadrant_landing_pages():
    """A landing page is a toctree, and tagging one files the toctree."""
    assert not any(name.endswith("/index") for name in corpus())


def test_narrative_pages_discovers_a_synthetic_tree_of_its_own(tmp_path):
    """The discovery is exercised directly, not only against this repository.

    Against the real tree every assertion about exclusion passes whether or not
    the rule is applied, because the tree happens not to contain the thing being
    excluded. A tree built here always does.
    """
    for relative in (
        "tutorials/index.rst",
        "tutorials/a-lesson.rst",
        "howtos/index.rst",
        "howtos/a-recipe.rst",
        "explanation/index.rst",
        "explanation/some-background.rst",
        "reference/glossary.rst",
    ):
        page = tmp_path / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("Title\n=====\n", encoding="utf-8")

    found = {
        path.relative_to(tmp_path).as_posix() for path in narrative_pages(tmp_path)
    }
    assert found == {
        "tutorials/a-lesson.rst",
        "howtos/a-recipe.rst",
        "explanation/some-background.rst",
    }


def test_a_nested_page_keeps_its_top_level_quadrant(tmp_path):
    """Discovery is recursive, so the quadrant is the top directory, not the parent.

    `page.parent.name` is the same string only for a page sitting directly in a
    quadrant. For `howtos/advanced/tuning.rst` it yields `advanced` -- a quadrant
    the vocabulary has never heard of, which would enter the promotion rule's span
    count and the monthly matrix as a fifth column, while the extension, keying by
    Sphinx docname, would call the same page `howtos`. The published page and the
    gate would then describe different corpora.

    Nothing else catches it. The gate and the report share this construction, so
    `test_the_corpus_matches_the_gate_s` compares two readers that are wrong in
    the same way and passes -- which is why the invariant is pinned here, against
    a tree built for it, rather than left to the equivalence test.
    """
    for relative in (
        "howtos/index.rst",
        "howtos/units.rst",
        "howtos/advanced/tuning.rst",
    ):
        page = tmp_path / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(":tags: units, sounding\n\nTitle\n=====\n", encoding="utf-8")

    found = narrative_corpus(tmp_path)
    assert set(found) == {"howtos/units", "howtos/advanced/tuning"}
    assert found["howtos/advanced/tuning"][0] == "howtos"
    assert all(quadrant in topics.QUADRANTS for quadrant, _ in found.values())


@pytest.mark.parametrize("item", sorted(corpus()))
def test_every_item_declares_two_to_four_tags(item):
    """Topics spec §3.7, assertion 1, over a discovered corpus (assertion 4).

    An untagged narrative page fails here from the day it lands, which is the
    whole reason the corpus is discovered rather than listed.
    """
    _, tags = corpus()[item]
    assert tags, (
        f"{item} declares no tags: put `:tags: <two to four terms>` on the FIRST "
        f"line of the file, above the `.. _label:` target, followed by a blank "
        f"line. Sphinx reads a field list into page metadata only where it "
        f"precedes all other markup; under the title it renders at the reader "
        f"instead (topics spec §3.2)."
    )
    assert topics.MIN_TAGS <= len(tags) <= topics.MAX_TAGS, (
        f"{item} declares {len(tags)} tags: {tags}"
    )


@pytest.mark.parametrize("item", sorted(corpus()))
def test_every_declared_tag_is_in_the_vocabulary(item):
    """Topics spec §3.7, assertion 2, and the growth mechanism of topics spec §3.3.

    An unknown term fails here, and the fix is to add it to `VOCABULARY` *and* to
    the covers/not table together -- a term with no stated edge is one two people
    apply differently, and nothing here can see that.
    """
    _, tags = corpus()[item]
    unknown = sorted(set(tags) - topics.VOCABULARY)
    assert not unknown, (
        f"{item} declares {unknown}, which is not in the vocabulary of topics "
        f"spec §3.3. Add the term to VOCABULARY in "
        f"docs/src/_ext/tephpy_topics_data.py and its covers/not definition to "
        f"that table, in the same change."
    )


def test_every_vocabulary_term_is_used():
    """Topics spec §3.7, assertion 3: an unused term is a typo or a residue.

    It is the direction the per-item tests cannot check. A term nothing declares
    survives every one of them, and is either a misspelling of a term that is used
    or what a deleted page left behind.
    """
    used = set(topics.coverage(corpus()))
    unused = sorted(topics.VOCABULARY - used)
    assert not unused, f"no item declares {unused}"
