# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the tephpy.config runtime configuration layer (spec §3.5)."""

from __future__ import annotations

import dataclasses

import pytest

import tephpy
from tephpy import _config

SECTIONS = (
    "isotherms",
    "isobars",
    "dry_adiabats",
    "moist_adiabats",
    "mixing_ratios",
    "diagram",
)


def test_singleton_identity_and_sections():
    assert tephpy.config is _config.config
    assert isinstance(tephpy.config, _config.Config)
    for section in SECTIONS:
        assert hasattr(tephpy.config, section)


def test_all_defaults_are_none():
    """None means fall through to the `_constants` conventions."""
    for section_field in dataclasses.fields(_config.Config):
        section = getattr(tephpy.config, section_field.name)
        for option in dataclasses.fields(section):
            assert getattr(section, option.name) is None


def test_section_shapes():
    """moist_adiabats gains truncation; mixing_ratios has no interval."""
    assert hasattr(tephpy.config.moist_adiabats, "truncation")
    assert hasattr(tephpy.config.mixing_ratios, "values")
    assert not hasattr(tephpy.config.mixing_ratios, "interval")
    assert hasattr(tephpy.config.diagram, "extent")


def test_context_applies_and_restores():
    with tephpy.config.context(isobars={"interval": 25.0}) as cfg:
        assert cfg is tephpy.config
        assert tephpy.config.isobars.interval == 25.0
    assert tephpy.config.isobars.interval is None


def test_context_restores_on_error():
    msg = "boom"
    with (
        pytest.raises(RuntimeError, match="boom"),
        tephpy.config.context(isobars={"interval": 25.0}),
    ):
        raise RuntimeError(msg)
    assert tephpy.config.isobars.interval is None


def test_context_unknown_section_raises():
    with (
        pytest.raises(TypeError, match="unknown config section"),
        tephpy.config.context(bogus={"interval": 25.0}),
    ):
        pass  # pragma: no cover


def test_context_unknown_option_raises_and_restores_prior_sections():
    """A failure mid-application must roll back what was already applied."""
    with (
        pytest.raises(TypeError, match="unknown option"),
        tephpy.config.context(isobars={"interval": 25.0}, diagram={"bogus": 1}),
    ):
        pass  # pragma: no cover
    assert tephpy.config.isobars.interval is None


def test_context_non_mapping_override_raises():
    with (
        pytest.raises(TypeError, match="mapping"),
        tephpy.config.context(isobars=1),
    ):
        pass  # pragma: no cover


def test_context_non_mapping_override_restores_prior_sections():
    """A non-mapping override must roll back sections already applied."""
    with (
        pytest.raises(TypeError, match="mapping"),
        tephpy.config.context(isotherms={"interval": 25.0}, isobars=1),
    ):
        pass  # pragma: no cover
    assert tephpy.config.isotherms.interval is None
