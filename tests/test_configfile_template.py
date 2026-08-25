# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Template rendering and the values-only save."""

from __future__ import annotations

import dataclasses
from types import MappingProxyType

import numpy as np
import pytest
import yaml

import tephpy
from tephpy import _configfile
from tephpy._config import Config
from tephpy._constants import CONFIG_DEFAULTS, CURSOR_FIELD_NAMES, EDGES
from tephpy.exceptions import TephpyConfigError


def _description_cases():
    return [
        (section, option)
        for section in CONFIG_DEFAULTS
        for option in CONFIG_DEFAULTS[section]
    ]


def test_the_description_gate_covers_every_option():
    """A gate over an empty list passes by checking nothing.

    Forty-two, the option count of configfile spec §3.3.
    """
    assert len(_description_cases()) == 42


def test_descriptions_cover_exactly_the_config_sections():
    assert set(_configfile.CONFIG_DESCRIPTIONS) == set(CONFIG_DEFAULTS)


@pytest.mark.parametrize("section", sorted(CONFIG_DEFAULTS))
def test_descriptions_cover_exactly_each_section_option(section):
    assert set(_configfile.CONFIG_DESCRIPTIONS[section]) == set(
        CONFIG_DEFAULTS[section]
    )


@pytest.mark.parametrize(("section", "option"), _description_cases())
def test_every_description_is_prose(section, option):
    description = _configfile.CONFIG_DESCRIPTIONS[section][option]
    assert isinstance(description, str)
    assert description.strip()


def test_the_template_shows_its_vocabularies_as_plain_text():
    """The reference page's literal markup does not reach the file.

    The descriptions are dual-register (configfile spec §3.4): a value the
    reader types is a reStructuredText literal on the options reference
    page, and has to be bare prose in the YAML comment above the option it
    describes. Both halves are asserted -- that no backquote survives, and
    that the vocabulary itself does -- because stripping the markup by
    dropping the whole phrase would pass the first alone. The surviving
    vocabulary is checked on the stripped description rather than on the
    rendered file, where an 88-column wrap can fall mid-run.
    """
    assert "`" not in _configfile.render_template()
    for section, option, vocabulary in (
        ("isotherms", "labels", EDGES),
        ("cursor", "fields", CURSOR_FIELD_NAMES),
    ):
        description = _configfile.CONFIG_DESCRIPTIONS[section][option]
        assert ", ".join(vocabulary) in _configfile._unmarked(description)


def test_the_template_is_an_empty_configuration_as_generated():
    """Every option commented out, so an untouched template changes nothing."""
    document = yaml.safe_load(_configfile.render_template())
    assert set(document) == set(CONFIG_DEFAULTS)
    assert all(value is None for value in document.values())


def test_the_template_names_every_option_in_a_comment():
    text = _configfile.render_template()
    for section, options in CONFIG_DEFAULTS.items():
        assert f"\n{section}:" in text
        for option in options:
            assert f"# {option}:" in text, f"{section}.{option}"


def test_the_template_prints_no_number_for_the_ladder_options():
    """``interval`` and ``values`` have no default; a number disables the ladder."""
    for line in _configfile.render_template().splitlines():
        stripped = line.strip()
        if stripped.startswith(("# interval:", "# values:")):
            assert stripped in {"# interval:", "# values:"}, line


def test_an_untouched_template_loads_as_no_configuration(tmp_path):
    path = tmp_path / "tephpyrc.yaml"
    _configfile.write_template(path)
    tephpy.config.load(path)
    for field in dataclasses.fields(Config):
        section = getattr(tephpy.config, field.name)
        for option in dataclasses.fields(section):
            assert getattr(section, option.name) is None, f"{field.name}.{option.name}"


def test_write_template_refuses_to_clobber(tmp_path):
    path = tmp_path / "tephpyrc.yaml"
    path.write_text("isotherms: {}\n", encoding="utf-8")
    with pytest.raises(TephpyConfigError, match="--force"):
        _configfile.write_template(path)
    assert path.read_text(encoding="utf-8") == "isotherms: {}\n"


def test_write_template_overwrites_with_force(tmp_path):
    path = tmp_path / "tephpyrc.yaml"
    path.write_text("isotherms: {}\n", encoding="utf-8")
    _configfile.write_template(path, force=True)
    assert "# color:" in path.read_text(encoding="utf-8")


def test_save_writes_only_what_was_set(tmp_path):
    path = tmp_path / "saved.yaml"
    tephpy.config.isotherms.color = "purple"
    tephpy.config.save(path)
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == {
        "isotherms": {"color": "purple"}
    }


def test_save_round_trips_the_tuple_valued_options(tmp_path):
    """PyYAML has no tuple representer; extent nests a tuple inside a mapping."""
    path = tmp_path / "saved.yaml"
    tephpy.config.cursor.fields = ("pressure",)
    tephpy.config.diagram.extent = {
        "pressure": (1000.0, 300.0),
        "temperature": (-30.0, 30.0),
    }
    tephpy.config.save(path)
    tephpy.config.reset()
    tephpy.config.load(path)
    assert tephpy.config.cursor.fields == ("pressure",)
    assert tephpy.config.diagram.extent == {
        "pressure": (1000.0, 300.0),
        "temperature": (-30.0, 30.0),
    }


def test_save_normalises_a_non_dict_emphasis_mapping(tmp_path):
    """``emphasis`` is annotated ``Mapping``; only ``dict`` is dumpable.

    PyYAML's safe representer covers ``dict``, ``list`` and ``tuple``, and
    nothing else. A read-only mapping — the idiom ``_constants`` itself uses
    for shared tables, so the obvious one to reach for when sharing an
    emphasis table between scripts — would otherwise reach
    ``RepresenterError``, at both levels of the nesting.
    """
    path = tmp_path / "saved.yaml"
    tephpy.config.isotherms.emphasis = MappingProxyType(
        {0.0: MappingProxyType({"color": "red"})}
    )
    tephpy.config.save(path)
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert document["isotherms"]["emphasis"] == {0.0: {"color": "red"}}


def test_save_reports_a_value_it_cannot_serialise(tmp_path):
    """A numpy scalar is an ordinary way for an interval to arrive.

    ``safe_dump`` runs outside ``_write``'s guard, so its
    ``RepresenterError`` would otherwise escape the ``TephpyConfigError``
    the docstring promises. Nothing is written either.
    """
    path = tmp_path / "saved.yaml"
    tephpy.config.isobars.interval = np.float64(25.0)
    with pytest.raises(TephpyConfigError, match="cannot serialise"):
        tephpy.config.save(path)
    assert not path.exists()


def test_save_reports_an_unwritable_path(tmp_path):
    """A filesystem refusal is a configuration error, as three docstrings say."""
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory\n", encoding="utf-8")
    with pytest.raises(TephpyConfigError, match="cannot write"):
        tephpy.config.save(blocker / _configfile.CONFIG_FILENAME)


def test_save_returns_the_path_written(tmp_path):
    path = tmp_path / "saved.yaml"
    assert tephpy.config.save(path) == path


def test_no_generated_template_line_exceeds_the_source_width():
    """The template is held to the width ruff holds the sources to.

    88 is written here as a literal rather than imported from ``_configfile``,
    so that raising the renderer's width cannot silently carry the gate up with
    it (configfile spec §3.4).
    """
    over = [
        line for line in _configfile.render_template().splitlines() if len(line) > 88
    ]
    assert over == []
