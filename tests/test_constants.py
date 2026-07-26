# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the diagram convention constants (spec §3.5)."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np

from tephpy import _constants as constants

INTERVAL_LADDERS = (
    constants.ISOTHERM_STEPS,
    constants.DRY_ADIABAT_STEPS,
    constants.ISOBAR_STEPS,
    constants.MOIST_ADIABAT_STEPS,
)


def test_default_extent_orientation():
    """Bottom-left has the higher pressure; temperatures increase rightward."""
    (p0, t0), (p1, t1) = constants.DEFAULT_EXTENT
    assert p0 > p1 > 0.0
    assert t0 < t1


def test_domains_are_ordered():
    for lo, hi in (
        constants.PRESSURE_DOMAIN,
        constants.TEMPERATURE_DOMAIN,
        constants.THETA_DOMAIN,
        constants.MOIST_ADIABAT_DOMAIN,
    ):
        assert lo < hi


def test_zoom_ladders_are_well_formed():
    """Widest first, terminated by a catch-all (0.0, finest) pair."""
    for ladder in (*INTERVAL_LADDERS, constants.MIXING_RATIO_STRIDES):
        widths = [width for width, _ in ladder]
        steps = [step for _, step in ladder]
        assert widths == sorted(widths, reverse=True)
        assert widths[-1] == 0.0
        assert steps == sorted(steps, reverse=True)
        assert all(step > 0 for step in steps)


def test_coarser_steps_are_multiples_of_the_finest():
    """Members are built at the finest step; coarser rungs must select a subset.

    Every rung must divide evenly by the finest.
    """
    for ladder in INTERVAL_LADDERS:
        finest = ladder[-1][1]
        for _, step in ladder:
            assert step / finest == np.round(step / finest)


def test_mixing_ratio_values_sorted_and_positive():
    values = np.asarray(constants.MIXING_RATIO_VALUES)
    assert (values > 0.0).all()
    assert (np.diff(values) > 0.0).all()


def test_truncation_below_moist_adiabat_domain():
    """Truncation must bite: below every labelled theta_w start value."""
    assert constants.MOIST_ADIABAT_DOMAIN[0] > constants.MOIST_ADIABAT_TRUNCATION


def test_profile_conventions():
    """Profiles draw above every family and matplotlib's default lines."""
    family_zorders = (
        constants.ISOTHERM_ZORDER,
        constants.DRY_ADIABAT_ZORDER,
        constants.ISOBAR_ZORDER,
        constants.MIXING_RATIO_ZORDER,
        constants.MOIST_ADIABAT_ZORDER,
    )
    assert max(family_zorders) < constants.PROFILE_ZORDER
    assert constants.PROFILE_ZORDER > 2.0
    assert constants.PROFILE_TEMPERATURE_COLOR != constants.PROFILE_DEWPOINT_COLOR
    assert constants.PROFILE_LINEWIDTH > constants.ISOPLETH_LINEWIDTH


def test_sounding_label_format():
    """The derived-label convention renders as station then UTC time."""
    label = constants.SOUNDING_LABEL_FORMAT.format(
        station="03808", time=datetime(2026, 7, 21, 12, tzinfo=UTC)
    )
    assert label == "03808 2026-07-21 12Z"
