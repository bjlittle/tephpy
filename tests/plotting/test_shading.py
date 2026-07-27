# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the CAPE/CIN shading builders (spec §3.2).

Headless geometry tests against an analytic fixture: an isothermal 0 °C
environment and a piecewise-linear (in ln p) parcel curve, whose buoyancy
sign-change crossings have closed-form pressures.
"""

from __future__ import annotations

import numpy as np

from tephpy import transforms
from tephpy.plotting.shading import cape_polygons, cin_polygons

ENV_PRESSURE = np.array([1000.0, 800.0, 500.0, 300.0])
ENV_TEMPERATURE = np.zeros(4)
PARCEL_TEMPERATURE = np.array([-4.0, 6.0, 6.0, -6.0])

#: Buoyancy crossings of the fixture, exact in ln p: the -4 → +6 segment
#: crosses zero at 0.4 of ln(1000/800); the +6 → -6 segment at its ln-p
#: midpoint.
CROSS_LOW = 1000.0 * np.exp(-0.4 * np.log(1000.0 / 800.0))
CROSS_HIGH = np.sqrt(500.0 * 300.0)


def _cape(lcl_pressure, parcel_temperature=PARCEL_TEMPERATURE):
    return cape_polygons(
        ENV_PRESSURE,
        ENV_TEMPERATURE,
        ENV_PRESSURE,
        parcel_temperature,
        lcl_pressure=lcl_pressure,
    )


def _cin(lcl_pressure, parcel_temperature=PARCEL_TEMPERATURE):
    return cin_polygons(
        ENV_PRESSURE,
        ENV_TEMPERATURE,
        ENV_PRESSURE,
        parcel_temperature,
        lcl_pressure=lcl_pressure,
    )


def _vertex_pressures(polygon):
    """Recover each polygon vertex's pressure from (T, theta) space."""
    return transforms.pressure_from_temperature_theta(polygon[:, 0], polygon[:, 1])


def test_cape_region_bounded_by_the_interpolated_crossings():
    """Crossings are located by linear interpolation in ln p (spec §3.2)."""
    (polygon,) = _cape(lcl_pressure=950.0)
    pressures = _vertex_pressures(polygon)
    np.testing.assert_allclose(pressures.max(), CROSS_LOW, rtol=1e-9)
    np.testing.assert_allclose(pressures.min(), CROSS_HIGH, rtol=1e-9)


def test_cape_region_clipped_at_the_lcl():
    """Positive buoyancy below the LCL never counts towards CAPE."""
    (polygon,) = _cape(lcl_pressure=900.0)
    pressures = _vertex_pressures(polygon)
    np.testing.assert_allclose(pressures.max(), 900.0, rtol=1e-9)
    np.testing.assert_allclose(pressures.min(), CROSS_HIGH, rtol=1e-9)


def test_cape_polygon_closes_on_the_drawn_curves():
    """Up the parcel curve, back down the isothermal environment."""
    (polygon,) = _cape(lcl_pressure=950.0)
    half = polygon.shape[0] // 2
    environment_branch = polygon[half:, 0]
    np.testing.assert_allclose(environment_branch, 0.0, atol=1e-12)
    # The branches meet exactly at the crossings: parcel == environment.
    np.testing.assert_allclose(polygon[0, 0], 0.0, atol=1e-12)
    np.testing.assert_allclose(polygon[half - 1, 0], 0.0, atol=1e-12)


def test_cin_region_spans_start_to_the_lfc():
    """CIN runs from the parcel start up to the LFC crossing."""
    (polygon,) = _cin(lcl_pressure=950.0)
    pressures = _vertex_pressures(polygon)
    np.testing.assert_allclose(pressures.max(), 1000.0, rtol=1e-9)
    np.testing.assert_allclose(pressures.min(), CROSS_LOW, rtol=1e-9)


def test_interrupted_cape_yields_plural_polygons():
    """An embedded stable layer splits the region (spec §3.2)."""
    pressure = np.array([1000.0, 900.0, 800.0, 600.0, 300.0])
    environment = np.zeros(5)
    parcel = np.array([-4.0, 5.0, -3.0, 4.0, -6.0])
    polygons = cape_polygons(
        pressure, environment, pressure, parcel, lcl_pressure=980.0
    )
    assert len(polygons) == 2
    lower, upper = polygons
    assert _vertex_pressures(lower).min() > _vertex_pressures(upper).max()


def test_no_positive_buoyancy_yields_no_regions():
    """With no LFC there is neither CAPE nor CIN (cape_cin's zeros)."""
    colder = np.full(4, -5.0)
    assert _cape(lcl_pressure=950.0, parcel_temperature=colder) == []
    assert _cin(lcl_pressure=950.0, parcel_temperature=colder) == []


def test_positive_buoyancy_only_below_the_lcl_is_not_cape():
    """A superadiabatic surface layer is no LFC (spec §3.2)."""
    parcel = np.array([2.0, -2.0, -4.0, -8.0])
    assert _cape(lcl_pressure=700.0, parcel_temperature=parcel) == []
    assert _cin(lcl_pressure=700.0, parcel_temperature=parcel) == []


def test_nan_gap_breaks_the_region():
    """NaN environment gaps are data; the region stops at the gap."""
    environment = np.array([0.0, 0.0, np.nan, 0.0])
    (polygon,) = cape_polygons(
        ENV_PRESSURE,
        environment,
        ENV_PRESSURE,
        PARCEL_TEMPERATURE,
        lcl_pressure=950.0,
    )
    pressures = _vertex_pressures(polygon)
    np.testing.assert_allclose(pressures.max(), CROSS_LOW, rtol=1e-9)
    np.testing.assert_allclose(pressures.min(), 800.0, rtol=1e-9)
