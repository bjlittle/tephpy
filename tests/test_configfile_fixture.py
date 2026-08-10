# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Prove every configuration option survives the YAML round trip.

A representative fixture would let a newly added option with a type YAML
cannot express land unnoticed, so this one is complete: the gate below fails
until the fixture covers every option in ``CONFIG_DEFAULTS`` (configfile
spec §6).
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

import tephpy
from tephpy import _configfile
from tephpy._constants import CONFIG_DEFAULTS

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "tephpyrc-complete.yaml"


def _document():
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _annotation(section, option):
    """Return the declared type of an option, for a direct ``coerce`` call."""
    return _configfile._option_hints(type(getattr(tephpy.config, section)))[option]


def test_the_fixture_covers_every_section():
    assert set(_document()) == set(CONFIG_DEFAULTS)


@pytest.mark.parametrize("section", sorted(CONFIG_DEFAULTS))
def test_the_fixture_covers_every_option(section):
    assert set(_document()[section]) == set(CONFIG_DEFAULTS[section])


@pytest.mark.parametrize("section", sorted(CONFIG_DEFAULTS))
def test_no_fixture_value_coincides_with_its_default(section):
    """A fixture equal to the defaults would pass without the loader running."""
    loaded = _document()[section]
    for option, default in CONFIG_DEFAULTS[section].items():
        coerced = _configfile.coerce(
            section, option, loaded[option], _annotation(section, option)
        )
        assert coerced != default, f"{section}.{option}"


def test_loading_the_fixture_reaches_every_option():
    tephpy.config.load(FIXTURE)
    document = _document()
    for section, options in CONFIG_DEFAULTS.items():
        applied = getattr(tephpy.config, section)
        for option in options:
            expected = _configfile.coerce(
                section, option, document[section][option], _annotation(section, option)
            )
            assert getattr(applied, option) == expected, f"{section}.{option}"
