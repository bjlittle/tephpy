# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The reference-page rendering of the configuration tables (configfile spec §3.6)."""

from __future__ import annotations

import builtins
from pathlib import Path
import re

import matplotlib.pyplot as plt
import pytest

import tephpy
from tephpy import _configfile
from tephpy._constants import (
    CONFIG_DEFAULTS,
    CURSOR_FIELD_NAMES,
    EDGES,
    EMPHASIS_STYLE_KEYS,
)

#: The how-to the methods section sends the reader to. Read rather than built,
#: because the claim being checked is about that page's contents.
HOWTO = Path(__file__).parents[1] / "docs" / "src" / "howtos" / "configuration.rst"

#: A method the methods section cross-references in its own prose.
CROSS_REFERENCED = re.compile(r":meth:`tephpy\.config\.(\w+)`")

#: Every option ``CONFIG_DETAILS`` is expected to carry. Written out rather than
#: derived, so that both losing a detail and gaining an ungated one are failures
#: (configfile spec §3.4).
EXPECTED_DETAILS = {
    (section, option)
    for section in (
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
    )
    for option in ("labels", "emphasis")
}


def test_details_name_only_real_options():
    """A detail cannot outlive the option it details (configfile spec §3.4)."""
    for section, options in _configfile.CONFIG_DETAILS.items():
        assert section in CONFIG_DEFAULTS, section
        assert set(options) <= set(CONFIG_DEFAULTS[section]), section


def test_the_detail_table_carries_what_it_is_expected_to():
    """The subset gate above passes vacuously over an empty table.

    Pinning membership is what makes it refuse its own empty input.
    """
    detailed = {
        (section, option)
        for section, options in _configfile.CONFIG_DETAILS.items()
        for option in options
    }
    assert detailed == EXPECTED_DETAILS


def test_every_detail_is_prose():
    """Details are sentences the reference page prints, not fragments."""
    for options in _configfile.CONFIG_DETAILS.values():
        for option, detail in options.items():
            assert detail.strip() == detail, option
            assert detail.endswith("."), option
            assert len(detail) > 40, option


#: A word ending in an underscore, which reStructuredText reads as a
#: hyperlink reference rather than prose. A mid-word underscore, as in
#: ``dry_adiabats``, is ordinary text and must not match.
_TRAILING_UNDERSCORE = re.compile(r"\w*_\b")


def test_every_description_carries_no_markup_but_literals():
    """A stray ``*``, ``|`` or ``--`` would render as markup, not prose.

    ``CONFIG_DESCRIPTIONS`` is dual-register: the same string is a plain-text
    YAML comment in the generated template and a paragraph of
    reStructuredText on the options reference page. A character the first
    rendering shows literally is read as markup by the second, so the strings
    carry exactly one construct -- the double-backquoted literal, which
    ``_unmarked`` strips for the template -- and nothing else. A single
    backquote is left over from a literal written wrong, and would reach the
    template as itself (configfile spec §3.4).
    """
    for section, options in _configfile.CONFIG_DESCRIPTIONS.items():
        for option, description in options.items():
            key = f"{section}.{option}"
            for token in ("*", "|", "--"):
                assert token not in description, key
            assert "`" not in _configfile._unmarked(description), key
            assert not _TRAILING_UNDERSCORE.search(description), key


#: A double-backquoted literal, masked out before the prose around it is read.
_LITERAL = re.compile(r"``[^`]+``")


def unliteralled(text):
    """Return the prose with each double-backquoted literal blanked out."""
    return _LITERAL.sub(" ", text)


def test_every_number_in_the_option_prose_is_a_literal():
    """A bound blends into a sentence as readily as a name does.

    The vocabularies are words and so were the visible half of the problem,
    but ``alpha``'s bounds and the ``emphasis`` example's key are values a
    reader types too. Every digit in either table therefore has to sit inside
    a literal. Nothing here counts anything: the option prose spells a count
    as a word, so a bare digit is always a value (configfile spec §3.4).
    """
    for table in (_configfile.CONFIG_DESCRIPTIONS, _configfile.CONFIG_DETAILS):
        for section, options in table.items():
            for option, text in options.items():
                bare = re.findall(r"\S*\d\S*", unliteralled(text))
                assert not bare, f"{section}.{option}: {bare}"


def test_the_prose_the_number_gate_reads_still_carries_numbers():
    """The gate above passes over prose that mentions no number at all.

    Both numbers are pinned where they are written, so dropping either --
    rewording the bounds away, or the worked ``emphasis`` key -- fails here
    rather than quietly emptying the gate's input.
    """
    assert "``0`` to ``1``" in _configfile.CONFIG_DESCRIPTIONS["isotherms"]["alpha"]
    assert "at ``20`` in" in _configfile.CONFIG_DETAILS["isotherms"]["emphasis"]


#: A dotted or bare Python name inside rendered type text.
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")


def rendered():
    """Return the reference page as ``render_reference`` renders it."""
    return _configfile.render_reference(tephpy.config)


def test_the_reference_names_every_option_and_no_others():
    """The page and the template render the same table (configfile spec §3.6)."""
    prefix = ".. py:attribute:: "
    emitted = {
        line.removeprefix(prefix)
        for line in rendered().splitlines()
        if line.startswith(prefix)
    }
    assert emitted == {
        f"tephpy.config.{section}.{option}"
        for section, options in CONFIG_DEFAULTS.items()
        for option in options
    }


def test_the_option_set_the_page_is_gated_against_is_not_empty():
    """Forty-two, so the gate above cannot pass by rendering nothing."""
    assert sum(len(options) for options in CONFIG_DEFAULTS.values()) == 42


def test_every_rendered_type_is_resolvable_text():
    """``str()`` of an annotation naming a class yields ``<class '...'>``.

    That reaches the page as neither valid type text nor a resolvable target,
    and the docs build is where it would surface — a build ``pixi run tests``
    never runs (configfile spec §3.4).
    """
    prefix = "   :type: "
    types = [
        line.removeprefix(prefix)
        for line in rendered().splitlines()
        if line.startswith(prefix)
    ]
    assert len(types) == 42
    for text in types:
        assert "<" not in text, text
        for name in NAME.findall(text):
            assert "." in name or hasattr(builtins, name), f"{name!r} in {text!r}"


def test_every_method_is_given_a_target():
    """Prose cross-references the methods; the page is where they resolve."""
    emitted = [
        line for line in rendered().splitlines() if line.startswith(".. py:method:: ")
    ]
    assert emitted == [
        ".. py:method:: tephpy.config.load(path=None)",
        ".. py:method:: tephpy.config.save(path=None)",
        ".. py:method:: tephpy.config.reset()",
        ".. py:method:: tephpy.config.context(**overrides)",
    ]


def test_the_how_to_covers_the_methods_the_page_sends_readers_to():
    """A page's promise about another page is otherwise nobody's to keep.

    The methods section names the how-to and the methods it covers. Neither
    file imports the other, so the claim can go stale from either end: a
    method dropped from the how-to, or one added to it and not said here.
    Equality catches both (configfile spec §3.6).
    """
    text = rendered()
    preamble = text[text.index("Methods\n-------") : text.index(".. py:method:: ")]
    named = set(CROSS_REFERENCED.findall(preamble))
    assert named, (
        "the methods section sends the reader to the how-to for no method, so "
        "this gate reads a sentence that no longer makes the claim it checks"
    )
    howto = HOWTO.read_text(encoding="utf-8")
    covered = {
        name
        for name in _configfile._REFERENCE_METHODS
        if f"tephpy.config.{name}" in howto
    }
    assert named == covered, (
        f"the methods section sends readers to {HOWTO.name} for {sorted(named)}, "
        f"but that page names {sorted(covered)}"
    )


def test_every_method_carries_an_example():
    """A method listed without one would render an empty literal block.

    Equality, not a subset: the page is the only documentation ``reset`` and
    ``context`` have, so a method reaching ``_REFERENCE_METHODS`` without an
    example is the case worth failing on (configfile spec §3.6).
    """
    assert set(_configfile._REFERENCE_EXAMPLES) == set(_configfile._REFERENCE_METHODS)


def test_every_example_reaches_the_page_as_a_literal_block():
    """Indented four short of the directive and the block silently ends early."""
    text = rendered()
    for name, example in _configfile._REFERENCE_EXAMPLES.items():
        first, last = example.splitlines()[0], example.splitlines()[-1]
        assert "   .. code-block:: python\n\n      " + first in text, name
        assert f"      {last}" in text, name


@pytest.mark.parametrize("name", _configfile._REFERENCE_METHODS)
def test_the_example_runs(name, monkeypatch, tmp_path):
    """The page's only hand-written content, and so its only content that drifts.

    ``tests/test_docs_snippets.py`` excludes the reference quadrant because a
    generated page cannot drift -- true of everything else here, and not of
    these. Run against the live API, an example that names a method that has
    been renamed, or passes an argument that no longer exists, fails here
    rather than reaching a reader (configfile spec §3.6, §6).

    The working directory is a ``tmp_path`` and ``$TEPHPYRC`` is cleared, so
    the two examples naming a file cannot reach the developer's own
    configuration. The autouse ``_pristine_config`` fixture restores the
    singleton the examples mutate.
    """
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        _configfile, "user_config_path", lambda: tmp_path / "absent" / "tephpyrc.yaml"
    )
    # `load` needs the file its example names to exist; running the example
    # under the conditions its prose describes is the point of running it.
    (tmp_path / "tephpyrc.yaml").write_text(
        "isobars:\n  interval: 25.0\n", encoding="utf-8"
    )
    try:
        exec(_configfile._REFERENCE_EXAMPLES[name], {"__name__": "__main__"})  # noqa: S102
    finally:
        plt.close("all")


def test_a_default_is_rendered_by_its_kind():
    """Three branches, where the template's renderer has two.

    ``_format_default`` renders both ``None`` and an empty mapping as the empty
    string, because the template needs a line the reader can uncomment. The
    page has no such constraint: an absent default and an empty one are
    different facts and are printed differently (configfile spec §3.6).
    """
    text = rendered()
    assert "Default: unset" in text
    assert "Default: ``None``" not in text
    assert "Default: ``{}``" in text
    assert "Default: ``dimgrey``" in text
    assert "Default: ``[[900.0, -65.0], [200.0, 5.0]]``" in text


@pytest.mark.parametrize(
    ("section", "option", "vocabulary"),
    [
        ("isotherms", "labels", EDGES),
        ("cursor", "fields", CURSOR_FIELD_NAMES),
    ],
)
def test_a_description_lists_its_whole_closed_vocabulary(section, option, vocabulary):
    """The page cannot document a legal set the loader rejects.

    The joined names are asserted as one run, not member by member, so a
    name added to the constant and not to the prose fails here — which is
    the only way to tell a derived string from a hand-written one that
    happens to agree today (domain spec §6). Each name is asserted as a
    literal, since a value the reader types has to stand out from the prose
    around it rather than blend into it (configfile spec §3.4).
    """
    description = _configfile.CONFIG_DESCRIPTIONS[section][option]
    assert ", ".join(f"``{name}``" for name in vocabulary) in description


def test_the_emphasis_detail_names_every_style_key():
    """The other closed vocabulary, in the prose that documents overrides.

    The whole ``and``-list as one run, for the same reason: a key added to
    the constant and left out of the prose has to fail somewhere.
    """
    keys = ", ".join(f"``{key}``" for key in EMPHASIS_STYLE_KEYS[:-1])
    detail = _configfile.CONFIG_DETAILS["isotherms"]["emphasis"]
    assert f"{keys} and ``{EMPHASIS_STYLE_KEYS[-1]}``" in detail


def test_the_page_carries_the_vocabularies_it_documents():
    """The descriptions above reach the rendered page, not just the table.

    As literals, which is the whole point of writing them as literals: the
    page is where the markup renders, and the reader who has to pick a value
    out of a sentence is the reader of this page (configfile spec §3.4).
    """
    page = rendered()
    assert ", ".join(f"``{name}``" for name in EDGES) in page
    assert ", ".join(f"``{name}``" for name in CURSOR_FIELD_NAMES) in page
