# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Gate CONFIG_DEFAULTS against the defaults the plotting path resolves.

``CONFIG_DEFAULTS`` exists so the template generator never re-enters
``IsoplethFamily._resolve``, which every image baseline covers
(configfile spec §3.4). Being a second copy, it drifts unless something holds
it in place; that is this file.
"""

from __future__ import annotations

import dataclasses

import matplotlib.pyplot as plt
import pytest

import tephpy
from tephpy import transforms
from tephpy._config import Config
from tephpy._constants import CONFIG_DEFAULTS
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


def test_diagram_default_is_the_extent_an_untouched_axes_lands_in():
    """The two non-family sections resolve outside ``IsoplethFamily``.

    ``CONFIG_DEFAULTS["diagram"]["extent"]`` is what the template shows the
    reader; the view a new axes lands in is what the reader gets. Asserting
    the table equals ``DEFAULT_EXTENT`` would compare the definition with
    itself — ``CONFIG_DEFAULTS`` *is* ``{"extent": DEFAULT_EXTENT}`` — so
    this drives the consumer, ``TephigramAxes.__init__`` falling through an
    unset ``config.diagram.extent``, instead.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        untouched = (ax.get_xlim(), ax.get_ylim())
        ax.set_extent(CONFIG_DEFAULTS["diagram"]["extent"])
        assert (ax.get_xlim(), ax.get_ylim()) == untouched
    finally:
        plt.close(fig)


def test_cursor_default_is_the_readout_an_untouched_axes_renders():
    """The same, for the fields ``format_coord`` falls through to.

    ``format_coord`` reads ``config.cursor.fields`` live, so the two halves
    are one call apart.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        x, y = transforms.xy_from_temperature_theta(0.0, 20.0)
        untouched = ax.format_coord(x, y)
        assert untouched
        with tephpy.config.context(
            cursor={"fields": CONFIG_DEFAULTS["cursor"]["fields"]}
        ):
            assert ax.format_coord(x, y) == untouched
    finally:
        plt.close(fig)
