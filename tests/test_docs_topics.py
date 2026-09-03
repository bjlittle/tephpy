# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The topic taxonomy, its corpus and its promotion rule (topics spec §6)."""

from __future__ import annotations

import pytest

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
