# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the CAPE/CIN shading builders (spec §3.2).

Headless geometry tests against an analytic fixture: an isothermal 0 °C
environment and a parcel curve whose drawn segments (straight in
tephigram (x, y) space) cross it at closed-form pressures.
"""

from __future__ import annotations

import numpy as np

from tephpy import transforms
from tephpy._constants import KELVIN_ZERO
from tephpy.plotting.shading import cape_polygons, cin_polygons

ENV_PRESSURE = np.array([1000.0, 800.0, 500.0, 300.0])
ENV_TEMPERATURE = np.zeros(4)
PARCEL_TEMPERATURE = np.array([-4.0, 6.0, 6.0, -6.0])


def _isotherm_chord_crossing(p0, t0, p1, t1):
    """Locate where a drawn parcel segment meets the 0 °C environment.

    Temperature and ln theta_K are both linear along a drawn segment, so
    the segment meets the isothermal environment at fraction
    ``s = t0 / (t0 - t1)`` with theta_K blended log-linearly; the
    crossing's pressure follows from Poisson's equation.
    """
    fraction = t0 / (t0 - t1)
    theta_k = (
        transforms.theta_from_pressure_temperature(
            np.array([p0, p1]), np.array([t0, t1])
        )
        + KELVIN_ZERO
    )
    blend = theta_k[0] ** (1.0 - fraction) * theta_k[1] ** fraction
    return float(transforms.pressure_from_temperature_theta(0.0, blend - KELVIN_ZERO))


#: Buoyancy crossings of the fixture: where the -4 → +6 and +6 → -6 drawn
#: parcel segments intersect the 0 °C isotherm.
CROSS_LOW = _isotherm_chord_crossing(1000.0, -4.0, 800.0, 6.0)
CROSS_HIGH = _isotherm_chord_crossing(500.0, 6.0, 300.0, -6.0)


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


def test_cape_region_bounded_by_the_drawn_curve_crossings():
    """Crossings sit where the drawn segments intersect (spec §3.2)."""
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


# A sloped environment on a grid offset from the parcel's: the drawn curves
# are straight segments in tephigram (x, y) space between their own vertices,
# and neither is an isotherm, so any other interpolation is off-polyline.
SLOPED_ENV_PRESSURE = np.array([1000.0, 700.0, 400.0])
SLOPED_ENV_TEMPERATURE = np.array([15.0, 0.0, -35.0])
SLOPED_PARCEL_PRESSURE = np.array([1000.0, 900.0, 650.0, 400.0])
SLOPED_PARCEL_TEMPERATURE = np.array([10.0, 9.0, 3.0, -45.0])


def _xy_polyline(pressure, temperature):
    """Build the drawn curve's polyline: one (x, y) vertex per level."""
    theta = transforms.theta_from_pressure_temperature(pressure, temperature)
    x, y = transforms.xy_from_temperature_theta(temperature, theta)
    return np.column_stack([x, y])


def _assert_on_polyline(vertices, pressure, temperature, atol=1e-6):
    """Assert (T, theta) vertices lie on a drawn polyline in (x, y)."""
    line = _xy_polyline(pressure, temperature)
    x, y = transforms.xy_from_temperature_theta(vertices[:, 0], vertices[:, 1])
    points = np.column_stack([x, y])
    tail, head = line[:-1], line[1:]
    span = head - tail
    length = (span * span).sum(axis=1)
    offset = points[:, None, :] - tail[None, :, :]
    fraction = np.clip((offset * span).sum(axis=2) / length, 0.0, 1.0)
    nearest = tail[None, :, :] + fraction[..., None] * span[None, :, :]
    distance = np.sqrt(((points[:, None, :] - nearest) ** 2).sum(axis=2)).min(axis=1)
    np.testing.assert_array_less(distance, atol)


def test_cape_polygon_vertices_lie_on_the_drawn_polylines():
    """Every CAPE vertex sits on a drawn curve — no gap to the profile."""
    (polygon,) = cape_polygons(
        SLOPED_ENV_PRESSURE,
        SLOPED_ENV_TEMPERATURE,
        SLOPED_PARCEL_PRESSURE,
        SLOPED_PARCEL_TEMPERATURE,
        lcl_pressure=680.0,
    )
    half = polygon.shape[0] // 2
    _assert_on_polyline(
        polygon[:half], SLOPED_PARCEL_PRESSURE, SLOPED_PARCEL_TEMPERATURE
    )
    _assert_on_polyline(polygon[half:], SLOPED_ENV_PRESSURE, SLOPED_ENV_TEMPERATURE)


def test_sign_flip_without_segment_intersection_fabricates_nothing():
    """A sign flip whose drawn segments never cross invents no vertex.

    Pressure is not monotone along a near-isobaric chord with an extreme
    temperature swing, so the buoyancy difference can change sign at
    equal pressures while the drawn segments stay disjoint; fabricating
    a crossing there would put a vertex on neither polyline and break
    the strictly-decreasing grid (PR :pull:`43` review).
    """
    pressure = np.array([1000.0, 999.0])
    environment = np.array([0.0, -20.0])
    parcel = np.array([-5.0, -5.1])
    assert (
        cape_polygons(pressure, environment, pressure, parcel, lcl_pressure=1000.0)
        == []
    )
    assert (
        cin_polygons(pressure, environment, pressure, parcel, lcl_pressure=1000.0) == []
    )


def test_cin_polygon_vertices_lie_on_the_drawn_polylines():
    """Every CIN vertex sits on a drawn curve — no gap to the profile."""
    (polygon,) = cin_polygons(
        SLOPED_ENV_PRESSURE,
        SLOPED_ENV_TEMPERATURE,
        SLOPED_PARCEL_PRESSURE,
        SLOPED_PARCEL_TEMPERATURE,
        lcl_pressure=680.0,
    )
    half = polygon.shape[0] // 2
    _assert_on_polyline(
        polygon[:half], SLOPED_PARCEL_PRESSURE, SLOPED_PARCEL_TEMPERATURE
    )
    _assert_on_polyline(polygon[half:], SLOPED_ENV_PRESSURE, SLOPED_ENV_TEMPERATURE)
