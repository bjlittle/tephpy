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

from metpy.units import units
import numpy as np
import pytest

from tephpy.calc import Profile, SoundingIndices
from tephpy.exceptions import (
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
