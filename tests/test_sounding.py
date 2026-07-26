# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the Sounding data model (spec §3.4/§6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from hypothesis import given
from hypothesis import strategies as st
from metpy.units import units
import numpy as np
import pytest

import tephpy
from tephpy import Sounding
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    NonMonotonicPressureError,
    TephpyUnitsError,
    TephpyValidationError,
)

PRESSURE = units.Quantity(np.array([1000.0, 850.0, 700.0, 500.0]), "hPa")
TEMPERATURE = units.Quantity(np.array([20.0, 12.0, 4.0, -12.0]), "degC")
DEWPOINT = units.Quantity(np.array([15.0, 8.0, np.nan, -30.0]), "degC")


def test_sounding_reexported_at_top_level():
    """`from tephpy import Sounding` works (spec §10 item 10)."""
    assert tephpy.Sounding is Sounding


def test_construction_from_quantities():
    snd = Sounding(PRESSURE, TEMPERATURE, dewpoint=DEWPOINT)
    np.testing.assert_array_equal(snd.pressure.m_as("hPa"), PRESSURE.magnitude)
    np.testing.assert_array_equal(snd.temperature.m_as("degC"), TEMPERATURE.magnitude)
    assert snd.station is None
    assert snd.time is None
    assert snd.label is None


def test_construction_from_bare_arrays_with_units():
    snd = Sounding(
        [1000.0, 850.0],
        [20.0, 12.0],
        units={"pressure": "hPa", "temperature": "degC"},
    )
    assert snd.pressure.check("[pressure]")
    assert snd.temperature.check("[temperature]")


def test_kelvin_and_pascal_just_work():
    """Any pressure/temperature units convert on use (spec §5)."""
    snd = Sounding(
        units.Quantity(np.array([100000.0, 85000.0]), "Pa"),
        units.Quantity(np.array([293.15, 285.15]), "K"),
    )
    np.testing.assert_allclose(snd.pressure.m_as("hPa"), [1000.0, 850.0])
    np.testing.assert_allclose(snd.temperature.m_as("degC"), [20.0, 12.0])


def test_bare_arrays_without_units_raise():
    with pytest.raises(TephpyUnitsError, match="'pressure' has no units"):
        Sounding([1000.0, 850.0], TEMPERATURE[:2])


def test_unknown_units_key_raises():
    with pytest.raises(TephpyUnitsError, match="unknown argument"):
        Sounding(PRESSURE[:2], TEMPERATURE[:2], units={"bogus": "hPa"})


def test_swapped_dimensions_raise():
    with pytest.raises(TephpyUnitsError, match="'pressure' has dimensionality"):
        Sounding(TEMPERATURE, PRESSURE)


def test_too_few_levels_raises():
    with pytest.raises(TephpyValidationError, match="at least 2 levels"):
        Sounding(PRESSURE[:1], TEMPERATURE[:1])


def test_length_mismatch_raises():
    with pytest.raises(TephpyValidationError, match="equal length"):
        Sounding(PRESSURE[:3], TEMPERATURE)


def test_non_1d_raises():
    pressure = units.Quantity(np.array([[1000.0, 850.0]]), "hPa")
    temperature = units.Quantity(np.array([[20.0, 12.0]]), "degC")
    with pytest.raises(TephpyValidationError, match="must be 1-D"):
        Sounding(pressure, temperature)


def test_wind_fields_must_arrive_together():
    speed = units.Quantity(np.full(4, 15.0), "knots")
    direction = units.Quantity(np.full(4, 270.0), "deg")
    with pytest.raises(TephpyValidationError, match="arrive together"):
        Sounding(PRESSURE, TEMPERATURE, wind_speed=speed)
    with pytest.raises(TephpyValidationError, match="arrive together"):
        Sounding(PRESSURE, TEMPERATURE, wind_direction=direction)
    snd = Sounding(PRESSURE, TEMPERATURE, wind_speed=speed, wind_direction=direction)
    assert snd.wind_speed is not None
    assert snd.wind_direction is not None


def test_increasing_pressure_normalized_with_all_arrays_reversed():
    """Either monotonic direction is accepted; storage is surface-first."""
    speed = units.Quantity(np.array([5.0, 10.0, 20.0, 40.0]), "knots")
    direction = units.Quantity(np.array([180.0, 200.0, 240.0, 270.0]), "deg")
    snd = Sounding(
        PRESSURE[::-1],
        TEMPERATURE[::-1],
        dewpoint=DEWPOINT[::-1],
        wind_speed=speed[::-1],
        wind_direction=direction[::-1],
    )
    np.testing.assert_array_equal(snd.pressure.magnitude, PRESSURE.magnitude)
    np.testing.assert_array_equal(snd.temperature.magnitude, TEMPERATURE.magnitude)
    np.testing.assert_array_equal(snd.dewpoint.magnitude, DEWPOINT.magnitude)
    np.testing.assert_array_equal(snd.wind_speed.magnitude, speed.magnitude)
    np.testing.assert_array_equal(snd.wind_direction.magnitude, direction.magnitude)


@given(
    pressures=st.lists(
        st.floats(min_value=10.0, max_value=1050.0),
        min_size=2,
        max_size=30,
        unique=True,
    ),
    increasing=st.booleans(),
)
def test_any_strictly_monotonic_pressure_stores_decreasing(pressures, increasing):
    """Property: monotonic input of either direction stores decreasing."""
    ordered = np.sort(np.asarray(pressures, dtype=np.float64))
    if not increasing:
        ordered = ordered[::-1]
    temperature = np.linspace(20.0, -40.0, ordered.size)
    snd = Sounding(
        ordered,
        temperature,
        units={"pressure": "hPa", "temperature": "degC"},
    )
    assert np.all(np.diff(snd.pressure.magnitude) < 0.0)


def test_non_monotonic_pressure_raises_with_levels():
    pressure = units.Quantity(np.array([1000.0, 850.0, 900.0, 800.0]), "hPa")
    with pytest.raises(NonMonotonicPressureError, match="strictly monotonic") as info:
        Sounding(pressure, TEMPERATURE)
    assert info.value.levels == (2,)


def test_nan_pressure_raises_with_levels():
    """NaN gaps are data everywhere except pressure (spec §3.4)."""
    pressure = units.Quantity(np.array([1000.0, np.nan, 700.0, 500.0]), "hPa")
    with pytest.raises(TephpyValidationError, match="finite") as info:
        Sounding(pressure, TEMPERATURE)
    assert info.value.levels == (1,)


def test_nan_temperature_and_dewpoint_are_data():
    temperature = units.Quantity(np.array([20.0, np.nan, 4.0, -12.0]), "degC")
    snd = Sounding(PRESSURE, temperature, dewpoint=DEWPOINT)
    assert np.isnan(snd.temperature.magnitude[1])


def test_dewpoint_above_temperature_raises_with_levels():
    dewpoint = units.Quantity(np.array([25.0, 8.0, np.nan, -10.0]), "degC")
    with pytest.raises(DewpointExceedsTemperatureError) as info:
        Sounding(PRESSURE, TEMPERATURE, dewpoint=dewpoint)
    assert info.value.levels == (0, 3)


def test_dewpoint_levels_index_the_input_order():
    """Levels index the caller's arrays, not the normalized storage."""
    pressure = units.Quantity(np.array([500.0, 700.0, 850.0, 1000.0]), "hPa")
    temperature = units.Quantity(np.array([-12.0, 4.0, 12.0, 20.0]), "degC")
    dewpoint = units.Quantity(np.array([-5.0, 0.0, 8.0, 15.0]), "degC")
    with pytest.raises(DewpointExceedsTemperatureError) as info:
        Sounding(pressure, temperature, dewpoint=dewpoint)
    assert info.value.levels == (0,)


def test_saturation_is_physical():
    """Dewpoint equal to temperature — saturation — is accepted."""
    snd = Sounding(PRESSURE, TEMPERATURE, dewpoint=TEMPERATURE)
    assert snd.dewpoint is not None


def test_dewpoint_comparison_converts_units():
    """The Td > T check compares physical values, not magnitudes."""
    dewpoint_k = units.Quantity(TEMPERATURE.m_as("K") + 1.0, "K")
    with pytest.raises(DewpointExceedsTemperatureError):
        Sounding(PRESSURE, TEMPERATURE, dewpoint=dewpoint_k)


def test_label_derives_from_station_and_time():
    snd = Sounding(
        PRESSURE, TEMPERATURE, station="03808", time=datetime(2026, 7, 21, 12)
    )
    assert snd.label == "03808 2026-07-21 12Z"


def test_label_requires_both_station_and_time():
    assert Sounding(PRESSURE, TEMPERATURE, station="03808").label is None
    assert Sounding(PRESSURE, TEMPERATURE, time=datetime(2026, 7, 21, 12)).label is None


def test_explicit_label_wins():
    snd = Sounding(
        PRESSURE,
        TEMPERATURE,
        station="03808",
        time=datetime(2026, 7, 21, 12),
        label="forecast",
    )
    assert snd.label == "forecast"


def test_naive_time_read_as_utc_aware_converted():
    """Naive datetimes are UTC; aware ones convert to UTC (spec §3.4)."""
    naive = Sounding(PRESSURE, TEMPERATURE, station="X", time=datetime(2026, 7, 21, 12))
    assert naive.time == datetime(2026, 7, 21, 12, tzinfo=UTC)
    plus_two = timezone(timedelta(hours=2))
    aware = Sounding(
        PRESSURE,
        TEMPERATURE,
        station="X",
        time=datetime(2026, 7, 21, 14, tzinfo=plus_two),
    )
    assert aware.time == datetime(2026, 7, 21, 12, tzinfo=UTC)
    assert aware.label == "X 2026-07-21 12Z"


def test_datetime64_time_accepted():
    snd = Sounding(
        PRESSURE, TEMPERATURE, station="X", time=np.datetime64("2026-07-21T12:00")
    )
    assert snd.time == datetime(2026, 7, 21, 12, tzinfo=UTC)


def test_bad_time_type_raises():
    with pytest.raises(TypeError, match="time must be"):
        Sounding(PRESSURE, TEMPERATURE, time="2026-07-21")
