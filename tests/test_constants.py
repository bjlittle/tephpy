# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the diagram convention constants (spec §3.5)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import numpy as np
import pytest

from tephpy import _constants as constants
from tephpy.calc import SoundingIndices
from tephpy.plotting import isopleths

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
        station="72357", time=datetime(2013, 5, 20, 12, tzinfo=UTC)
    )
    assert label == "72357 2013-05-20 12Z"


def test_cursor_fields():
    """The default cursor readout trio, in display order (spec §3.2)."""
    assert constants.CURSOR_FIELDS == ("pressure", "temperature", "theta")


def test_cursor_field_names_cover_the_default_trio():
    """The vocabulary and the default are different facts (domain spec §3.2).

    ``CURSOR_FIELDS`` is what a user gets without asking;
    ``CURSOR_FIELD_NAMES`` is everything they may ask for. A default naming a
    field outside the vocabulary would be a readout that raises on the first
    mouse move.
    """
    assert set(constants.CURSOR_FIELDS) <= set(constants.CURSOR_FIELD_NAMES)
    assert constants.CURSOR_FIELDS != constants.CURSOR_FIELD_NAMES


def test_cursor_field_names_are_sorted():
    """The unknown-field message lists them, and ``format_coord`` sorts.

    ``plotting.axes.format_coord`` says ``expected
    sorted(_CURSOR_FORMATTERS)``, so a vocabulary in registry order would make
    the load-time warning and the draw-time error name the same five fields in
    two different orders (domain spec §4).
    """
    assert list(constants.CURSOR_FIELD_NAMES) == sorted(constants.CURSOR_FIELD_NAMES)


def test_the_isopleth_vocabularies_are_the_objects_plotting_uses():
    """A copy would be two tables a test has to keep in step (domain spec §3.2).

    Identity, not equality: the move is a change of address, and equality
    would pass just as well against a second tuple that has since drifted.
    """
    assert isopleths.EDGES is constants.EDGES
    assert isopleths._EMPHASIS_STYLE_KEYS is constants.EMPHASIS_STYLE_KEYS


def test_shading_conventions():
    """Shading draws between the families and the profile lines."""
    family_zorders = (
        constants.ISOTHERM_ZORDER,
        constants.DRY_ADIABAT_ZORDER,
        constants.ISOBAR_ZORDER,
        constants.MIXING_RATIO_ZORDER,
        constants.MOIST_ADIABAT_ZORDER,
    )
    assert max(family_zorders) < constants.SHADING_ZORDER < constants.PROFILE_ZORDER
    # Also strictly below Matplotlib's default Line2D zorder of 2, so a parcel
    # path drawn through plot_profile (which sets no zorder) stays above the
    # shading rather than tying with it and being painted over.
    assert constants.SHADING_ZORDER < 2.0
    assert constants.CAPE_COLOR != constants.CIN_COLOR
    assert 0.0 < constants.SHADING_ALPHA < 1.0


def test_cloud_base_correction_is_the_operational_value():
    """The operational correction raises the LCL by 25 mb (spec §1/§3.3)."""
    assert constants.CLOUD_BASE_CORRECTION == -25.0


def test_indices_panel_rows_cover_every_field():
    """One panel row per SoundingIndices field, in field order."""
    fields = [field.name for field in dataclasses.fields(SoundingIndices)]
    assert [row[0] for row in constants.INDICES_PANEL_ROWS] == fields


def test_barb_conventions():
    """Met Office symbology, a sane staff, and knot-calibrated increments."""
    assert constants.BARB_INCREMENTS == {"half": 5.0, "full": 10.0, "flag": 50.0}
    assert constants.BARB_GUTTER_WIDTH.endswith("%")
    assert constants.BARB_GUTTER_PAD > 0.0
    assert 0.0 < constants.BARB_STAFF_POSITION < 1.0
    assert constants.BARB_MIN_SEPARATION > 0.0
    assert constants.BARB_LENGTH > 0.0


def test_io_conventions():
    """The Wyoming request is https with both placeholders; sane sentinels."""
    assert constants.WYOMING_URL.startswith("https://weather.uwyo.edu/")
    assert "{datetime}" in constants.WYOMING_URL
    assert "{station}" in constants.WYOMING_URL
    assert "TEXT:CSV" in constants.WYOMING_URL
    assert constants.WYOMING_TIMEOUT > 0.0
    assert constants.IGRA_MISSING == (-9999, -8888)


def test_edge_axis_titles_cover_every_family():
    """One axis title per family accessor, in the accessor's own units."""
    assert set(constants.EDGE_AXIS_TITLES) == {
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
    }
    assert constants.EDGE_AXIS_TITLES["isobars"] == "Pressure (hPa)"
    assert all(title.strip() for title in constants.EDGE_AXIS_TITLES.values())


def test_edge_label_gutter_pad_clears_a_tick_label():
    """The substituted pad is wider than the panel pads it replaces."""
    assert constants.EDGE_LABEL_GUTTER_PAD > constants.BARB_GUTTER_PAD
    assert constants.EDGE_LABEL_GUTTER_PAD > constants.INDICES_PANEL_PAD
    assert constants.EDGE_TICK_LENGTH > 0.0
    assert constants.EDGE_TICK_PAD >= 0.0


def test_logo_conventions():
    """Every form has both presets, ordered, and the luminance weights are Rec. 709."""
    assert constants.POINTS_PER_INCH == 72.0
    assert set(constants.LOGO_SIZES) == {"icon", "lockup", "stacked"}
    for presets in constants.LOGO_SIZES.values():
        assert set(presets) == {"small", "large"}
        assert 0.0 < presets["small"] < presets["large"]
    assert constants.LOGO_PAD > 0.0
    assert constants.LOGO_ZORDER > 5.0
    assert 0.0 < constants.LOGO_LUMINANCE_THRESHOLD < 1.0
    assert constants.LOGO_LUMINANCE_WEIGHTS == (0.2126, 0.7152, 0.0722)
    assert sum(constants.LOGO_LUMINANCE_WEIGHTS) == pytest.approx(1.0)
