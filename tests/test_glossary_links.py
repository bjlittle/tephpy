# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The glossary cross-reference gate (:issue:`209`).

docs-style's glossary rule asks that the *first* mention of a glossary term on
a page be cross-referenced with ``:term:``, in narrative prose only. The
fail-on-warning build catches a ``:term:`` whose entry does not exist; nothing
caught the link nobody wrote, so a page could name every term in the glossary
in plain text and build perfectly green.

The exclusions carry the weight here, because each is a reading of "narrative
prose only -- never in titles, code blocks, API signatures, or admonition
labels". They are what the unit cases below pin.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
GATE = REPO / ".github" / "scripts" / "check_glossary_links.py"


def _load():
    """Import the gate, which is a script rather than an installed module."""
    spec = importlib.util.spec_from_file_location("check_glossary_links", GATE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load()

GLOSSARY = """\
Glossary
========

.. glossary::

    sounding
        A vertical profile of atmospheric measurements.

    humidity mixing ratio
    mixing ratio
    isohume
        The mass of water vapour per mass of dry air.
"""


def terms():
    """Build the alias map the unit cases resolve against."""
    return gate.alias_map(GLOSSARY)


def test_alias_map_groups_a_shared_definition():
    """Three spellings, one entry -- linking any of them satisfies the rule."""
    assert terms() == {
        "sounding": "sounding",
        "humidity mixing ratio": "humidity mixing ratio",
        "mixing ratio": "humidity mixing ratio",
        "isohume": "humidity mixing ratio",
    }


def test_an_unlinked_mention_is_reported():
    """The defect itself: prose names a term and no `:term:` targets it."""
    found = gate.unlinked("Draw a sounding on the diagram.\n", terms())
    assert [(number, term) for number, term, _ in found] == [(1, "sounding")]


def test_a_linked_mention_is_not_reported():
    found = gate.unlinked("Draw a :term:`sounding` on the diagram.\n", terms())
    assert found == []


def test_linking_one_alias_satisfies_the_whole_group():
    """`CAPE` and its spelled-out name are one entry; either link will do."""
    text = "The :term:`isohume` family, whose mixing ratio is fixed.\n"
    assert gate.unlinked(text, terms()) == []


def test_an_explicit_target_is_read_rather_than_the_display_text():
    text = "Lines of :term:`constant moisture <mixing ratio>` cross here.\n"
    assert gate.unlinked(text, terms()) == []


def test_only_the_first_mention_is_reported():
    """The rule is first mention per page, so one report, not one per line."""
    text = "A sounding.\n\nAnother sounding.\n\nA third sounding.\n"
    assert len(gate.unlinked(text, terms())) == 1


def test_a_bare_first_mention_is_reported_though_a_later_one_is_linked():
    """Report a bare first mention even where a later one is linked.

    The rule is the *first* mention, so a late link cannot excuse an early bare
    one. Gathering every link on a page before reading its prose passes this
    text, which is the rule inverted.
    """
    text = "A sounding appears.\n\nLater, :term:`sounding`.\n"
    found = gate.unlinked(text, terms())
    assert [(number, term) for number, term, _ in found] == [(1, "sounding")]


def test_a_linked_first_mention_excuses_a_later_bare_one():
    """The converse, which is what the rule permits."""
    text = "A :term:`sounding`.\n\nLater, a sounding.\n"
    assert gate.unlinked(text, terms()) == []


def test_the_two_are_ordered_within_one_line():
    """Same line, bare first: still a bare first mention."""
    text = "A sounding, and then :term:`sounding` again.\n"
    assert [t for _, t, _ in gate.unlinked(text, terms())] == ["sounding"]


def test_a_link_before_a_bare_mention_on_one_line_is_enough():
    text = "A :term:`sounding`, and then a sounding again.\n"
    assert gate.unlinked(text, terms()) == []


def test_a_wrapped_role_is_still_a_link():
    """ReStructuredText lets a role span lines, and one that does is one link."""
    text = "Lines of :term:`humidity mixing ratio\n<mixing ratio>` cross here.\n"
    assert gate.unlinked(text, terms()) == []


def test_a_wrapped_term_is_still_a_mention():
    """A term broken over a line is one mention, which a per-line scan misses."""
    text = "It rises along a humidity mixing\nratio line.\n"
    assert [t for _, t, _ in gate.unlinked(text, terms())] == ["humidity mixing ratio"]


def test_a_title_is_not_prose():
    text = "Draw a Sounding\n===============\n\nNothing else here.\n"
    assert gate.unlinked(text, terms()) == []


def test_a_directive_body_is_not_prose():
    """Caught a real one: `bufr_dump -p sounding.bufr` in a console block."""
    text = ".. code-block:: console\n\n    $ bufr_dump -p sounding.bufr\n"
    assert gate.unlinked(text, terms()) == []


def test_a_directive_option_is_not_prose():
    text = ".. plot::\n    :filename-prefix: read-a-sounding\n\n    value = 1\n"
    assert gate.unlinked(text, terms()) == []


def test_an_inline_literal_is_not_prose():
    """Caught a real one: a ``dewpoint_C`` column name in a table."""
    assert gate.unlinked("The ``sounding`` column.\n", terms()) == []


def test_a_role_target_is_not_prose():
    """`Sounding` the class is an API signature, not a use of the concept."""
    text = "Returns a :class:`Sounding <tephpy.sounding.Sounding>`.\n"
    assert gate.unlinked(text, terms()) == []


def test_emphasis_is_not_prose():
    """Emphasis quotes a page title here -- *Read a Sounding From an Archive*."""
    assert gate.unlinked("See *Draw a Sounding* for that.\n", terms()) == []


def test_a_plural_is_the_same_mention():
    found = gate.unlinked("Two soundings, drawn together.\n", terms())
    assert [term for _, term, _ in found] == ["sounding"]


def test_a_word_that_merely_contains_a_term_is_not_a_mention():
    """`resounding` is not `sounding`, and a substring match would say it was."""
    assert gate.unlinked("A resounding success.\n", terms()) == []


def test_the_report_carries_the_line_and_its_text():
    """A gate that cannot say where is a gate nobody can act on."""
    found = gate.unlinked("Prose.\n\nDraw a sounding here.\n", terms())
    assert found == [(3, "sounding", "Draw a sounding here.")]


def test_the_glossary_parses_into_groups():
    """The real glossary, so a reshape of that file fails here and not silently."""
    real = gate.alias_map((gate.DOCS / "reference" / "glossary.rst").read_text())
    assert real["CAPE"] == real["convective available potential energy"]
    assert real["sounding"] == "sounding"


def test_the_corpus_is_covered():
    """A gate over an empty corpus is a green tick over nothing."""
    assert gate.corpus(), "no pages found in the user quadrants"


@pytest.mark.parametrize("quadrant", gate.QUADRANTS)
def test_every_quadrant_directory_exists(quadrant):
    """A renamed quadrant would empty the corpus without touching this file."""
    assert (gate.DOCS / quadrant).is_dir()


def test_the_user_quadrants_link_their_glossary_terms():
    """The contract: every page links each term it names, on first mention."""
    offenders = [
        f"{page.relative_to(gate.DOCS)}:{number}: {term!r}"
        for page in gate.corpus()
        for number, term, _ in gate.unlinked(
            page.read_text(encoding="utf-8"),
            gate.alias_map((gate.DOCS / "reference" / "glossary.rst").read_text()),
        )
    ]
    assert offenders == [], (
        "these pages name a glossary term in prose and never link it: "
        f"{offenders}. Cross-reference the first mention with `:term:` "
        "(docs-style, glossary rule)"
    )
