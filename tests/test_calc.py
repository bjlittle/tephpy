# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the thermodynamic analysis layer (spec §3.3/§6/§7).

Composition, not thermodynamics: ``indices()`` fields are asserted equal
to direct ``metpy.calc`` calls on the same profile, and the parcel path is
asserted to pass through Normand's point and follow the MetPy adiabats it
composes.
"""

from __future__ import annotations

import metpy.calc as mpcalc
from metpy.units import units
import numpy as np
import pytest

import tephpy
from tephpy import Sounding
from tephpy._constants import MOIST_ADIABAT_PRESSURE_STEP
from tephpy.calc import Profile, SoundingIndices, normand_point, parcel_path
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    MissingDataError,
    ProfileTooShortError,
    TephpyUnitsError,
    TephpyValidationError,
)

Q = units.Quantity

# A plausible convective mid-latitude sounding (one uninterrupted CAPE
# region; CIN zero).
PRESSURE = Q(
    np.array(
        [1000.0, 950.0, 900.0, 850.0, 800.0, 700.0, 600.0, 500.0, 400.0, 300.0, 200.0]
    ),
    "hPa",
)
TEMPERATURE = Q(
    np.array([30.0, 25.0, 21.0, 18.0, 15.0, 8.0, -1.0, -12.0, -25.0, -42.0, -55.0]),
    "degC",
)
DEWPOINT = Q(
    np.array([21.0, 19.0, 17.0, 14.0, 10.0, 2.0, -8.0, -20.0, -35.0, -55.0, -70.0]),
    "degC",
)


# --- Profile ---------------------------------------------------------------


def test_profile_construction_from_bare_arrays_with_units():
    profile = Profile(
        [1000.0, 900.0, 800.0],
        [20.0, 12.0, 5.0],
        950.0,
        16.0,
        units={
            "pressure": "hPa",
            "temperature": "degC",
            "lcl_pressure": "hPa",
            "lcl_temperature": "degC",
        },
    )
    assert profile.pressure.check("[pressure]")
    assert profile.parcel == "surface"
    assert profile.label is None


def test_profile_requires_strictly_decreasing_pressure():
    with pytest.raises(TephpyValidationError, match="strictly decreasing") as info:
        Profile(
            Q([1000.0, 900.0, 950.0], "hPa"),
            Q([20.0, 12.0, 5.0], "degC"),
            Q(975.0, "hPa"),
            Q(18.0, "degC"),
        )
    assert info.value.levels == (2,)


def test_profile_rejects_increasing_pressure():
    """A Profile is stored surface-first; increasing input is not normalized."""
    with pytest.raises(TephpyValidationError, match="strictly decreasing"):
        Profile(
            Q([800.0, 900.0, 1000.0], "hPa"),
            Q([5.0, 12.0, 20.0], "degC"),
            Q(950.0, "hPa"),
            Q(16.0, "degC"),
        )


def test_profile_length_mismatch_raises():
    with pytest.raises(TephpyValidationError, match="equal length"):
        Profile(
            Q([1000.0, 900.0, 800.0], "hPa"),
            Q([20.0, 12.0], "degC"),
            Q(950.0, "hPa"),
            Q(16.0, "degC"),
        )


def test_profile_too_few_levels_raises():
    with pytest.raises(TephpyValidationError, match="at least 2 levels"):
        Profile(
            Q([1000.0], "hPa"), Q([20.0], "degC"), Q(1000.0, "hPa"), Q(20.0, "degC")
        )


def test_profile_non_1d_raises():
    with pytest.raises(TephpyValidationError, match="must be 1-D"):
        Profile(
            Q([[1000.0, 900.0]], "hPa"),
            Q([[20.0, 12.0]], "degC"),
            Q(950.0, "hPa"),
            Q(16.0, "degC"),
        )


def test_profile_lcl_must_be_scalar():
    with pytest.raises(TephpyValidationError, match="'lcl_pressure' must be a scalar"):
        Profile(
            Q([1000.0, 900.0], "hPa"),
            Q([20.0, 12.0], "degC"),
            Q([950.0], "hPa"),
            Q(16.0, "degC"),
        )


def test_profile_lcl_outside_span_raises():
    with pytest.raises(TephpyValidationError, match="inside the path's pressure span"):
        Profile(
            Q([1000.0, 900.0], "hPa"),
            Q([20.0, 12.0], "degC"),
            Q(850.0, "hPa"),
            Q(8.0, "degC"),
        )


def test_profile_nan_lcl_raises():
    with pytest.raises(TephpyValidationError, match="inside the path's pressure span"):
        Profile(
            Q([1000.0, 900.0], "hPa"),
            Q([20.0, 12.0], "degC"),
            Q(np.nan, "hPa"),
            Q(16.0, "degC"),
        )


def test_profile_unknown_parcel_raises():
    with pytest.raises(ValueError, match="parcel must be one of"):
        Profile(
            Q([1000.0, 900.0], "hPa"),
            Q([20.0, 12.0], "degC"),
            Q(950.0, "hPa"),
            Q(16.0, "degC"),
            parcel="bogus",
        )


# --- SoundingIndices -------------------------------------------------------


def _indices_kwargs(**overrides):
    """Scalar quantity values for every SoundingIndices field."""
    values = {
        "cape": Q(1500.0, "J/kg"),
        "cin": Q(-50.0, "J/kg"),
        "lcl_pressure": Q(900.0, "hPa"),
        "lcl_temperature": Q(15.0, "degC"),
        "lfc_pressure": Q(800.0, "hPa"),
        "lfc_temperature": Q(8.0, "degC"),
        "el_pressure": Q(250.0, "hPa"),
        "el_temperature": Q(-45.0, "degC"),
        "theta_w": Q(18.0, "degC"),
        "lifted_index": Q(-5.0, "delta_degC"),
    }
    values.update(overrides)
    return values


def test_sounding_indices_dimension_checked():
    with pytest.raises(TephpyUnitsError, match="'cape' has dimensionality"):
        SoundingIndices(**_indices_kwargs(cape=Q(1500.0, "hPa")))


def test_sounding_indices_requires_scalars():
    with pytest.raises(TephpyValidationError, match="'cape' must be a scalar"):
        SoundingIndices(**_indices_kwargs(cape=Q([1500.0], "J/kg")))


def test_sounding_indices_nan_fields_are_answers():
    """No cross-field validation: NaN LFC/EL fields construct fine."""
    result = SoundingIndices(
        **_indices_kwargs(
            lfc_pressure=Q(np.nan, "hPa"), lfc_temperature=Q(np.nan, "degC")
        )
    )
    assert np.isnan(result.lfc_pressure.magnitude)


def test_sounding_indices_bare_values_take_units_mapping():
    result = SoundingIndices(
        **{name: value.magnitude for name, value in _indices_kwargs().items()},
        units={
            "cape": "J/kg",
            "cin": "J/kg",
            "lcl_pressure": "hPa",
            "lcl_temperature": "degC",
            "lfc_pressure": "hPa",
            "lfc_temperature": "degC",
            "el_pressure": "hPa",
            "el_temperature": "degC",
            "theta_w": "degC",
            "lifted_index": "delta_degC",
        },
    )
    assert result.cape.m_as("J/kg") == 1500.0


def test_sounding_indices_bare_value_without_units_raises():
    with pytest.raises(TephpyUnitsError, match="'cape' has no units"):
        SoundingIndices(**_indices_kwargs(cape=1500.0))


# --- normand_point ---------------------------------------------------------


def test_normand_point_is_the_metpy_lcl():
    result = normand_point(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0])
    expected = mpcalc.lcl(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0])
    assert result[0].m_as("hPa") == expected[0].m_as("hPa")
    assert result[1].m_as("degC") == pytest.approx(expected[1].m_as("degC"))
    assert result[0].units == units.hPa
    assert result[1].units == units.degC


def test_normand_point_bare_values_with_units():
    result = normand_point(
        1000.0,
        30.0,
        21.0,
        units={"pressure": "hPa", "temperature": "degC", "dewpoint": "degC"},
    )
    expected = normand_point(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0])
    assert result[0].m_as("hPa") == pytest.approx(expected[0].m_as("hPa"))


def test_normand_point_bare_values_without_units_raise():
    with pytest.raises(TephpyUnitsError, match="'pressure' has no units"):
        normand_point(1000.0, TEMPERATURE[0], DEWPOINT[0])


def test_normand_point_unknown_units_key_raises():
    with pytest.raises(TephpyUnitsError, match="unknown argument"):
        normand_point(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0], units={"bogus": "hPa"})


def test_normand_point_wrong_dimension_raises():
    with pytest.raises(TephpyUnitsError, match="'pressure' has dimensionality"):
        normand_point(TEMPERATURE[0], PRESSURE[0], DEWPOINT[0])


def test_normand_point_non_scalar_raises():
    with pytest.raises(TephpyValidationError, match="must be a scalar"):
        normand_point(PRESSURE, TEMPERATURE[0], DEWPOINT[0])


def test_normand_point_dewpoint_above_temperature_raises():
    with pytest.raises(DewpointExceedsTemperatureError):
        normand_point(PRESSURE[0], TEMPERATURE[0], Q(31.0, "degC"))


def test_normand_point_saturation_is_the_parcel():
    """At saturation the Normand's point is the parcel itself."""
    pressure, temperature = normand_point(PRESSURE[0], TEMPERATURE[0], TEMPERATURE[0])
    assert pressure.m_as("hPa") == pytest.approx(1000.0)
    assert temperature.m_as("degC") == pytest.approx(30.0)


# --- parcel_path -----------------------------------------------------------


def _sounding(**kwargs):
    """Build the module's reference convective sounding."""
    return Sounding(PRESSURE, TEMPERATURE, dewpoint=DEWPOINT, **kwargs)


def test_calc_reexports_eagerly():
    """`tephpy.calc.parcel_path` works after `import tephpy` (spec §4)."""
    assert tephpy.calc.parcel_path is parcel_path
    assert tephpy.calc.Profile is Profile


def test_parcel_path_passes_through_normand_point():
    """The LCL vertex is spliced into the path exactly (spec §3.3/§7)."""
    profile = parcel_path(_sounding())
    lcl_pressure, lcl_temperature = normand_point(
        PRESSURE[0], TEMPERATURE[0], DEWPOINT[0]
    )
    assert profile.lcl_pressure.m_as("hPa") == lcl_pressure.m_as("hPa")
    position = np.flatnonzero(profile.pressure.m_as("hPa") == lcl_pressure.m_as("hPa"))
    assert position.size == 1
    assert profile.temperature.m_as("degC")[position[0]] == pytest.approx(
        lcl_temperature.m_as("degC")
    )


def test_parcel_path_spans_start_to_top():
    profile = parcel_path(_sounding())
    pressure = profile.pressure.m_as("hPa")
    assert pressure[0] == PRESSURE[0].m_as("hPa")
    assert pressure[-1] == PRESSURE[-1].m_as("hPa")
    assert np.all(np.diff(pressure) < 0.0)


def test_parcel_path_samples_the_background_step():
    """Both legs sample the moist-adiabat family's 5 hPa step (spec §3.3)."""
    profile = parcel_path(_sounding())
    pressure = profile.pressure.m_as("hPa")
    lcl = profile.lcl_pressure.m_as("hPa")
    dry = pressure[pressure > lcl]
    moist = pressure[pressure < lcl]
    np.testing.assert_allclose(np.diff(dry), -MOIST_ADIABAT_PRESSURE_STEP)
    np.testing.assert_allclose(np.diff(moist)[:-1], -MOIST_ADIABAT_PRESSURE_STEP)


def test_parcel_path_dry_leg_follows_the_dry_adiabat():
    profile = parcel_path(_sounding())
    pressure = profile.pressure.m_as("hPa")
    lcl = profile.lcl_pressure.m_as("hPa")
    dry = pressure > lcl
    expected = mpcalc.dry_lapse(
        Q(pressure[dry], "hPa"), TEMPERATURE[0], reference_pressure=PRESSURE[0]
    )
    np.testing.assert_allclose(
        profile.temperature.m_as("degC")[dry], expected.m_as("degC")
    )


def test_parcel_path_moist_leg_is_anchored_at_the_lcl():
    """The moist leg is moist_lapse(..., reference_pressure=p_lcl) (spec §3.3)."""
    profile = parcel_path(_sounding())
    pressure = profile.pressure.m_as("hPa")
    lcl = profile.lcl_pressure.m_as("hPa")
    moist = pressure < lcl
    expected = mpcalc.moist_lapse(
        Q(pressure[moist], "hPa"),
        profile.lcl_temperature,
        reference_pressure=profile.lcl_pressure,
    )
    np.testing.assert_allclose(
        profile.temperature.m_as("degC")[moist], expected.m_as("degC")
    )


def test_parcel_path_fields_and_label():
    anonymous = parcel_path(_sounding())
    assert anonymous.parcel == "surface"
    assert anonymous.label is None
    labelled = parcel_path(_sounding(), label="surface parcel")
    assert labelled.label == "surface parcel"


def test_parcel_path_mixed_layer_starts_at_the_mixed_parcel():
    profile = parcel_path(_sounding(), parcel="mixed-layer")
    start_pressure, start_temperature, _ = mpcalc.mixed_parcel(
        PRESSURE, TEMPERATURE, DEWPOINT
    )
    assert profile.parcel == "mixed-layer"
    assert profile.pressure[0].m_as("hPa") == start_pressure.m_as("hPa")
    assert profile.temperature[0].m_as("degC") == pytest.approx(
        start_temperature.m_as("degC")
    )


def test_parcel_path_correction_applied_only_when_requested():
    """The -25 mb correction moves the LCL only when asked (spec §3.3)."""
    plain = parcel_path(_sounding())
    corrected = parcel_path(_sounding(), cloud_base_correction=Q(-25.0, "hPa"))
    assert corrected.lcl_pressure.m_as("hPa") == pytest.approx(
        plain.lcl_pressure.m_as("hPa") - 25.0
    )
    expected_temperature = mpcalc.dry_lapse(
        corrected.lcl_pressure, TEMPERATURE[0], reference_pressure=PRESSURE[0]
    )
    assert corrected.lcl_temperature.m_as("degC") == pytest.approx(
        expected_temperature.m_as("degC")
    )


def test_parcel_path_saturated_parcel_has_no_dry_leg():
    """A saturated surface parcel ascends moist from its start."""
    snd = Sounding(PRESSURE, TEMPERATURE, dewpoint=TEMPERATURE)
    profile = parcel_path(snd)
    assert profile.lcl_pressure.m_as("hPa") == pytest.approx(1000.0)
    assert profile.pressure[0].m_as("hPa") == pytest.approx(1000.0)


def test_parcel_path_missing_dewpoint_raises():
    snd = Sounding(PRESSURE, TEMPERATURE)
    with pytest.raises(MissingDataError, match="needs dewpoint"):
        parcel_path(snd)


def test_parcel_path_unknown_parcel_raises():
    with pytest.raises(ValueError, match="parcel must be one of"):
        parcel_path(_sounding(), parcel="bogus")


def test_parcel_path_profile_too_short_raises():
    """A profile topping out at or below the LCL has no moist ascent."""
    snd = Sounding(PRESSURE[:2], TEMPERATURE[:2], dewpoint=DEWPOINT[:2])
    with pytest.raises(ProfileTooShortError, match="no moist ascent"):
        parcel_path(snd)


def test_parcel_path_corrected_lcl_above_top_raises():
    """The too-short test uses the corrected LCL when one is requested."""
    with pytest.raises(ProfileTooShortError, match="no moist ascent"):
        parcel_path(_sounding(), cloud_base_correction=Q(-700.0, "hPa"))


def test_parcel_path_correction_below_start_raises():
    with pytest.raises(TephpyValidationError, match=r"below the .* parcel start"):
        parcel_path(_sounding(), cloud_base_correction=Q(200.0, "hPa"))


def test_parcel_path_correction_wrong_dimension_raises():
    with pytest.raises(TephpyUnitsError, match="'cloud_base_correction'"):
        parcel_path(_sounding(), cloud_base_correction=Q(-25.0, "degC"))
