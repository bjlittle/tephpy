# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Gate CONFIG_DEFAULTS against the defaults the plotting path resolves.

``CONFIG_DEFAULTS`` exists so the template generator never re-enters
``IsoplethFamily._resolve``, which every image baseline covers (configfile
spec §3.4). Being a second copy, it drifts unless something holds it in
place; that is this file.
"""

from __future__ import annotations

import dataclasses

import pytest

import tephpy
from tephpy._config import Config
from tephpy._constants import CONFIG_DEFAULTS, CURSOR_FIELDS, DEFAULT_EXTENT
from tephpy.plotting import isopleths

FAMILY_SECTIONS = (
    "isotherms",
    "isobars",
    "dry_adiabats",
    "moist_adiabats",
    "mixing_ratios",
)


def _resolved(name):
    """Resolve a family's options with no kwargs and a pristine config."""
    spec = isopleths._FAMILY_SPECS[name]
    return isopleths.IsoplethFamily(spec, getattr(tephpy.config, name)).options


def _family_cases():
    return [
        (section, option)
        for section in FAMILY_SECTIONS
        for option in CONFIG_DEFAULTS[section]
    ]


def test_config_defaults_covers_exactly_the_config_sections():
    """The gate's own input must not silently empty out."""
    assert set(CONFIG_DEFAULTS) == {field.name for field in dataclasses.fields(Config)}


def test_config_defaults_covers_exactly_each_section_option():
    for field in dataclasses.fields(Config):
        section = getattr(tephpy.config, field.name)
        expected = {option.name for option in dataclasses.fields(section)}
        assert set(CONFIG_DEFAULTS[field.name]) == expected, field.name


def test_the_gate_covers_every_family_option():
    """A parametrised gate over an empty list passes by checking nothing.

    Forty: eight ``FamilyOptions`` each for isotherms, isobars and dry
    adiabats, nine for moist adiabats (plus ``truncation``), and seven for
    mixing ratios (``LineOptions`` plus ``values``, with no ``interval``).
    With ``diagram.extent`` and ``cursor.fields`` below, that is the 42
    options of configfile spec §3.3.
    """
    assert len(_family_cases()) == 40


@pytest.mark.parametrize(("section", "option"), _family_cases())
def test_config_default_matches_the_resolved_default(section, option):
    resolved = _resolved(section)
    assert CONFIG_DEFAULTS[section][option] == getattr(resolved, option)


def test_diagram_and_cursor_defaults():
    """The two non-family sections resolve outside IsoplethFamily."""
    assert CONFIG_DEFAULTS["diagram"]["extent"] == DEFAULT_EXTENT
    assert CONFIG_DEFAULTS["cursor"]["fields"] == CURSOR_FIELDS
