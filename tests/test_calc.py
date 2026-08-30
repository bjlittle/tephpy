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

import dataclasses

import metpy.calc as mpcalc
from metpy.units import units
import numpy as np
import pytest

import tephpy
from tephpy import Sounding
from tephpy._constants import MOIST_ADIABAT_PRESSURE_STEP
from tephpy.calc import Profile, SoundingIndices, indices, normand_point, parcel_path
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


# A saturated profile with a sharp cold notch inside the mixed-layer depth.
# `mixed_parcel` averages potential temperature linearly and mixing ratio
# nonlinearly, so across this layer the mean mixing ratio outruns the mean
# potential temperature and the mixed parcel comes out supersaturated. It is
# the one route to a parcel start `Sounding` construction cannot reject.
NOTCHED_PRESSURE = Q(np.array([1000.0, 950.0, 900.0, 850.0, 700.0, 500.0]), "hPa")
NOTCHED_TEMPERATURE = Q(np.array([25.0, -15.0, 25.0, 10.0, -5.0, -25.0]), "degC")


def _notched_sounding():
    """Build the saturated, cold-notched sounding (dewpoint at temperature)."""
    return Sounding(NOTCHED_PRESSURE, NOTCHED_TEMPERATURE, dewpoint=NOTCHED_TEMPERATURE)


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


def test_parcel_path_mixed_layer_shallower_than_depth_raises():
    """A mixed-layer parcel needs a sounding spanning its depth (spec §6)."""
    snd = Sounding(PRESSURE[:2], TEMPERATURE[:2], dewpoint=DEWPOINT[:2])
    with pytest.raises(ProfileTooShortError, match="mixed-layer parcel needs"):
        parcel_path(snd, parcel="mixed-layer")


def test_parcel_path_nan_surface_start_raises():
    """A NaN lowest level leaves the surface parcel start undefined (spec §6)."""
    temperature = TEMPERATURE.magnitude.copy()
    dewpoint = DEWPOINT.magnitude.copy()
    temperature[0] = dewpoint[0] = np.nan
    snd = Sounding(PRESSURE, Q(temperature, "degC"), dewpoint=Q(dewpoint, "degC"))
    with pytest.raises(TephpyValidationError, match=r"undefined \(NaN\)") as excinfo:
        parcel_path(snd)
    assert excinfo.value.levels == (0,)


def test_parcel_path_mixed_layer_nan_start_raises():
    """A NaN inside the mixed layer propagates into an undefined start."""
    temperature = TEMPERATURE.magnitude.copy()
    dewpoint = DEWPOINT.magnitude.copy()
    temperature[0] = dewpoint[0] = np.nan
    snd = Sounding(PRESSURE, Q(temperature, "degC"), dewpoint=Q(dewpoint, "degC"))
    with pytest.raises(TephpyValidationError, match=r"undefined \(NaN\)") as excinfo:
        parcel_path(snd, parcel="mixed-layer")
    assert excinfo.value.levels == ()


def test_parcel_path_mixed_layer_dewpoint_above_temperature_raises():
    """Only the mixed parcel can start supersaturated (spec §6).

    `Sounding` rejects dewpoint above temperature level by level, so the
    surface parcel — which starts from a level — can never reach Normand's
    point without one. The mixed-layer parcel is averaged rather than
    selected, and the average is not bound by the per-level invariant, so
    it is the sole route to this error from a constructed sounding.
    """
    snd = _notched_sounding()
    with pytest.raises(
        DewpointExceedsTemperatureError, match="no Normand's point exists"
    ):
        parcel_path(snd, parcel="mixed-layer")
    # The same sounding lifts cleanly from the surface: the overshoot is the
    # averaging's, not the profile's.
    assert parcel_path(snd).parcel == "surface"


# --- indices ---------------------------------------------------------------

# A stable sounding: no positive buoyancy anywhere (zero CAPE).
STABLE_TEMPERATURE = Q(
    np.array([5.0, 4.0, 3.5, 3.0, 2.0, -2.0, -8.0, -16.0, -28.0, -44.0, -58.0]),
    "degC",
)
STABLE_DEWPOINT = Q(
    np.array([-5.0, -6.0, -7.0, -9.0, -12.0, -18.0, -25.0, -35.0, -45.0, -60.0, -75.0]),
    "degC",
)


def _direct_indices(pressure, temperature, dewpoint, curve, start):
    """Compute the ten fields by direct metpy.calc delegation (spec §7)."""
    cape, cin = mpcalc.cape_cin(pressure, temperature, dewpoint, curve)
    lfc_pressure, lfc_temperature = mpcalc.lfc(
        pressure, temperature, dewpoint, parcel_temperature_profile=curve
    )
    el_pressure, el_temperature = mpcalc.el(
        pressure, temperature, dewpoint, parcel_temperature_profile=curve
    )
    lifted = mpcalc.lifted_index(pressure, temperature, curve)[0]
    theta_w = mpcalc.wet_bulb_potential_temperature(*start)
    return (
        cape,
        cin,
        lfc_pressure,
        lfc_temperature,
        el_pressure,
        el_temperature,
        lifted,
        theta_w,
    )


def _assert_indices_equal(result, direct, lcl):
    """Assert every SoundingIndices field equals its direct counterpart.

    `assert_array_equal` treats NaN as equal — a NaN LFC/EL must match a
    NaN field (spec §6).
    """
    cape, cin, lfc_p, lfc_t, el_p, el_t, lifted, theta_w = direct
    lcl_pressure, lcl_temperature = lcl
    equal = np.testing.assert_array_equal
    equal(result.cape.m_as("J/kg"), cape.m_as("J/kg"))
    equal(result.cin.m_as("J/kg"), cin.m_as("J/kg"))
    equal(result.lcl_pressure.m_as("hPa"), lcl_pressure.m_as("hPa"))
    equal(result.lcl_temperature.m_as("degC"), lcl_temperature.m_as("degC"))
    equal(result.lfc_pressure.m_as("hPa"), lfc_p.m_as("hPa"))
    equal(result.lfc_temperature.m_as("degC"), lfc_t.m_as("degC"))
    equal(result.el_pressure.m_as("hPa"), el_p.m_as("hPa"))
    equal(result.el_temperature.m_as("degC"), el_t.m_as("degC"))
    equal(result.lifted_index.m_as("delta_degC"), lifted.m_as("delta_degC"))
    equal(result.theta_w.m_as("degC"), theta_w.m_as("degC"))


def test_indices_default_is_plain_surface_parcel_delegation():
    """Every field equals the direct metpy.calc call (spec §7)."""
    result = indices(_sounding())
    curve = mpcalc.parcel_profile(PRESSURE, TEMPERATURE[0], DEWPOINT[0])
    direct = _direct_indices(
        PRESSURE,
        TEMPERATURE,
        DEWPOINT,
        curve,
        (PRESSURE[0], TEMPERATURE[0], DEWPOINT[0]),
    )
    _assert_indices_equal(
        result, direct, mpcalc.lcl(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0])
    )


def test_indices_mixed_layer_delegates_to_the_mixed_parcel():
    result = indices(_sounding(), parcel="mixed-layer")
    start = mpcalc.mixed_parcel(PRESSURE, TEMPERATURE, DEWPOINT)
    curve = mpcalc.parcel_profile(PRESSURE, start[1], start[2])
    direct = _direct_indices(PRESSURE, TEMPERATURE, DEWPOINT, curve, start)
    _assert_indices_equal(result, direct, mpcalc.lcl(*start))


def test_indices_corrected_feeds_the_hand_built_curve():
    """A corrected run feeds the generic functions the corrected curve."""
    correction = Q(-25.0, "hPa")
    result = indices(_sounding(), cloud_base_correction=correction)
    lcl_pressure, _ = mpcalc.lcl(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0])
    corrected_pressure = lcl_pressure + correction
    corrected_temperature = mpcalc.dry_lapse(
        corrected_pressure, TEMPERATURE[0], reference_pressure=PRESSURE[0]
    )
    below = corrected_pressure <= PRESSURE
    curve = np.empty(PRESSURE.size)
    curve[below] = mpcalc.dry_lapse(
        PRESSURE[below], TEMPERATURE[0], reference_pressure=PRESSURE[0]
    ).m_as("degC")
    curve[~below] = mpcalc.moist_lapse(
        PRESSURE[~below],
        corrected_temperature,
        reference_pressure=corrected_pressure,
    ).m_as("degC")
    direct = _direct_indices(
        PRESSURE,
        TEMPERATURE,
        DEWPOINT,
        Q(curve, "degC"),
        (PRESSURE[0], TEMPERATURE[0], DEWPOINT[0]),
    )
    _assert_indices_equal(
        result,
        direct,
        (corrected_pressure.to("hPa"), corrected_temperature.to("degC")),
    )


def test_indices_zero_cape_is_zero_not_nan():
    """Zero CAPE/CIN is 0 J/kg — never NaN (spec §6, item 11)."""
    snd = Sounding(PRESSURE, STABLE_TEMPERATURE, dewpoint=STABLE_DEWPOINT)
    result = indices(snd)
    assert result.cape.m_as("J/kg") == 0.0
    assert result.cin.m_as("J/kg") == 0.0
    assert np.isnan(result.lfc_pressure.magnitude)
    assert np.isnan(result.el_pressure.magnitude)
    assert np.isfinite(result.lcl_pressure.magnitude)


def test_indices_el_nan_while_cape_positive():
    """The parcel can still be buoyant at the profile top (spec §6)."""
    snd = Sounding(
        Q([1000.0, 900.0, 800.0, 700.0], "hPa"),
        Q([30.0, 19.0, 10.0, 0.0], "degC"),
        dewpoint=Q([24.0, 15.0, 5.0, -5.0], "degC"),
    )
    result = indices(snd)
    assert result.cape.m_as("J/kg") > 0.0
    assert np.isnan(result.el_pressure.magnitude)


def test_indices_lifted_index_nan_below_500():
    """A profile topping out below 500 hPa reports NaN.

    The MetPy warning is suppressed at the call site — the suite runs
    ``filterwarnings = ["error"]``, so this test passing proves it.
    """
    snd = Sounding(
        PRESSURE[:6], TEMPERATURE[:6], dewpoint=DEWPOINT[:6]
    )  # tops at 700 hPa
    result = indices(snd)
    assert np.isnan(result.lifted_index.magnitude)
    assert result.cape.m_as("J/kg") > 0.0


def test_indices_interior_nan_gaps_pass_through():
    """NaN gaps in temperature/dewpoint are data, tolerated by MetPy."""
    temperature = TEMPERATURE.copy()
    temperature[3] = Q(np.nan, "degC")
    dewpoint = DEWPOINT.copy()
    dewpoint[5] = Q(np.nan, "degC")
    snd = Sounding(PRESSURE, temperature, dewpoint=dewpoint)
    result = indices(snd)
    assert np.isfinite(result.cape.magnitude)


def test_indices_missing_dewpoint_raises():
    with pytest.raises(MissingDataError, match="needs dewpoint"):
        indices(Sounding(PRESSURE, TEMPERATURE))


def test_indices_profile_too_short_raises():
    snd = Sounding(PRESSURE[:2], TEMPERATURE[:2], dewpoint=DEWPOINT[:2])
    with pytest.raises(ProfileTooShortError, match="no moist ascent"):
        indices(snd)


def test_indices_mixed_layer_shallower_than_depth_raises():
    """The mixed-layer depth guard also fronts ``indices`` (spec §6)."""
    snd = Sounding(PRESSURE[:2], TEMPERATURE[:2], dewpoint=DEWPOINT[:2])
    with pytest.raises(ProfileTooShortError, match="mixed-layer parcel needs"):
        indices(snd, parcel="mixed-layer")


def test_indices_nan_surface_start_raises():
    """The undefined-start guard also fronts ``indices`` (spec §6)."""
    temperature = TEMPERATURE.magnitude.copy()
    dewpoint = DEWPOINT.magnitude.copy()
    temperature[0] = dewpoint[0] = np.nan
    snd = Sounding(PRESSURE, Q(temperature, "degC"), dewpoint=Q(dewpoint, "degC"))
    with pytest.raises(TephpyValidationError, match=r"undefined \(NaN\)") as excinfo:
        indices(snd)
    assert excinfo.value.levels == (0,)


def test_indices_mixed_layer_dewpoint_above_temperature_raises():
    """The supersaturated mixed-parcel guard also fronts ``indices`` (spec §6)."""
    with pytest.raises(
        DewpointExceedsTemperatureError, match="no Normand's point exists"
    ):
        indices(_notched_sounding(), parcel="mixed-layer")


def test_indices_theta_w_follows_the_parcel_option():
    surface = indices(_sounding())
    mixed = indices(_sounding(), parcel="mixed-layer")
    start = mpcalc.mixed_parcel(PRESSURE, TEMPERATURE, DEWPOINT)
    expected = mpcalc.wet_bulb_potential_temperature(*start)
    assert mixed.theta_w.m_as("degC") == expected.m_as("degC")
    assert mixed.theta_w.m_as("degC") != surface.theta_w.m_as("degC")


# --- the published worked example (spec §7, §10 item 13) -------------------

# Stull, R., 2017: "Practical Meteorology: An Algebra-based Survey of
# Atmospheric Science", version 1.02b, CC BY-NC-SA 4.0, ch. 14 p. 496
# (https://www.eoas.ubc.ca/books/Practical_Meteorology/): the sample
# application sounding — P (kPa) 100, 96, 80, 70, 50, 30, 20; T (°C) 30,
# 25, 10, 15, -10, -35, -35; surface Td 20 °C — with published
# thermo-diagram answers P_LCL = 87 kPa, P_LFC = 60 kPa, P_EL = 24 kPa.
# Values transcribed from the chapter PDF on 2026-07-26: a handful of
# numeric facts, reproduced with citation. The environment dewpoints above
# the surface are not published; the placeholders below enter only
# cape_cin's virtual-temperature correction, not the LCL/LFC/EL
# comparisons.
STULL_PRESSURE = Q(np.array([1000.0, 960.0, 800.0, 700.0, 500.0, 300.0, 200.0]), "hPa")
STULL_TEMPERATURE = Q(np.array([30.0, 25.0, 10.0, 15.0, -10.0, -35.0, -35.0]), "degC")
STULL_DEWPOINT = Q(np.array([20.0, 15.0, 0.0, -5.0, -25.0, -50.0, -60.0]), "degC")


def test_worked_example_stull_ch14():
    """Integration: the published Stull ch. 14 parcel-ascent answers."""
    snd = Sounding(STULL_PRESSURE, STULL_TEMPERATURE, dewpoint=STULL_DEWPOINT)
    result = indices(snd)
    # Stull reads 870 and 600 off a full-size skew-T; his own Sample
    # Applications carry a "slightly different answer if you used a
    # different thermo diagram... is normal" caveat.
    assert result.lcl_pressure.m_as("hPa") == pytest.approx(870.0, abs=10.0)
    assert result.lfc_pressure.m_as("hPa") == pytest.approx(600.0, abs=5.0)
    # The published EL (240 hPa) sits in the isothermal -35 °C layer,
    # where the crossing is hypersensitive to the moist-adiabat
    # formulation: metpy 1.7.1 places it at 275 hPa. Divergence
    # documented, not forced to zero (spec §7).
    assert 240.0 <= result.el_pressure.m_as("hPa") <= 300.0
    assert result.cin.m_as("J/kg") == 0.0


def test_worked_example_cape_against_stull_equation_14_5():
    """CAPE agrees with Stull's published pressure-integral, eq. (14.5).

    CAPE = Rd * sum((T_parcel - T_env) * ln(p_bottom / p_top)) over the
    area between the LFC and the EL — evaluated here on a fine ln-p grid
    over MetPy's own parcel curve. cape_cin integrates the same area in
    *virtual* temperature (the Doswell & Rasmussen correction), which
    inflates it — by 14% for this moist parcel over its dry mid-level
    environment (1182 vs 1033 J/kg, metpy 1.7.1). The check pins the
    magnitude and the direction of that documented divergence: a
    composition bug (wrong units, wrong curve, wrong bounds) lands far
    outside it.
    """
    snd = Sounding(STULL_PRESSURE, STULL_TEMPERATURE, dewpoint=STULL_DEWPOINT)
    result = indices(snd)
    curve = mpcalc.parcel_profile(
        STULL_PRESSURE, STULL_TEMPERATURE[0], STULL_DEWPOINT[0]
    )
    # cape_cin's integration bounds: its LFC ("bottom") is the LCL here —
    # the parcel is buoyant from the LCL up — and its EL is the reported
    # one.
    bottom = result.lcl_pressure.m_as("hPa")
    top = result.el_pressure.m_as("hPa")
    grid = np.geomspace(bottom, top, 4001)
    x = -np.log(STULL_PRESSURE.m_as("hPa"))
    environment = np.interp(-np.log(grid), x, STULL_TEMPERATURE.m_as("degC"))
    parcel = np.interp(-np.log(grid), x, curve.m_as("degC"))
    rd = 287.053
    cape_stull = rd * np.trapezoid(parcel - environment, -np.log(grid))
    cape = result.cape.m_as("J/kg")
    assert cape >= cape_stull
    assert cape == pytest.approx(cape_stull, rel=0.2)


# --- Unit independence (spec §5) -------------------------------------------

#: Pressure units a caller may plausibly hold a profile in, spanning the two
#: pint defines as a height of a fluid column (:issue:`214`). Every existing
#: test in this module builds in hPa, so nothing here pinned that the analysis
#: path is independent of the unit the sounding arrived in.
PRESSURE_UNITS = (
    "hPa",
    "Pa",
    "kPa",
    "mbar",
    "bar",
    "atm",
    "psi",
    "torr",
    "inHg",
    "mmHg",
)

#: Levels the parcel curve is compared at, well inside the profile so the
#: comparison never extrapolates.
_SAMPLE_HPA = np.array([950.0, 800.0, 600.0, 400.0])


def _sounding_in(unit):
    """Build the reference sounding with its pressure expressed in `unit`."""
    return Sounding(PRESSURE.to(unit), TEMPERATURE, dewpoint=DEWPOINT)


def _curve_at_samples(profile):
    """Sample the parcel temperature at `_SAMPLE_HPA`, in °C.

    Sampled rather than compared element-wise: the parcel grid is built by
    ``np.arange`` from the start pressure, so a unit round-trip can shift the
    grid by one level without the physics differing at all.
    """
    pressure = profile.pressure.m_as("hPa")
    temperature = profile.temperature.m_as("degC")
    return np.interp(_SAMPLE_HPA, pressure[::-1], temperature[::-1])


@pytest.mark.parametrize("unit", PRESSURE_UNITS)
def test_parcel_path_is_independent_of_the_pressure_unit(unit):
    """The ascent is the same atmosphere however the pressure was spelled."""
    baseline = _curve_at_samples(parcel_path(_sounding()))
    np.testing.assert_allclose(
        _curve_at_samples(parcel_path(_sounding_in(unit))), baseline, atol=1e-6
    )


@pytest.mark.parametrize("unit", PRESSURE_UNITS)
def test_indices_are_independent_of_the_pressure_unit(unit):
    """Every field of the panel agrees, not merely the call not raising."""
    baseline = indices(_sounding())
    result = indices(_sounding_in(unit))
    for field in dataclasses.fields(SoundingIndices):
        expected = getattr(baseline, field.name)
        actual = getattr(result, field.name).to(expected.units)
        np.testing.assert_allclose(
            actual.magnitude, expected.magnitude, rtol=1e-6, err_msg=field.name
        )


@pytest.mark.parametrize("unit", PRESSURE_UNITS)
def test_a_corrected_cloud_base_is_independent_of_the_pressure_unit(unit):
    """The corrected path takes a different branch, and needs its own case.

    Without ``cloud_base_correction`` the parcel curve is delegated whole to
    ``metpy.calc.parcel_profile``; the correction is what routes it through
    tephpy's own dry and moist legs (:issue:`214`).
    """
    correction = Q(10.0, "hPa")
    baseline = indices(_sounding(), cloud_base_correction=correction)
    result = indices(_sounding_in(unit), cloud_base_correction=correction)
    for field in dataclasses.fields(SoundingIndices):
        expected = getattr(baseline, field.name)
        actual = getattr(result, field.name).to(expected.units)
        np.testing.assert_allclose(
            actual.magnitude, expected.magnitude, rtol=1e-6, err_msg=field.name
        )
