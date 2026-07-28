# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the wind-barb gutter staff (spec §3.2)."""

from __future__ import annotations

import numpy as np
import pytest

from tephpy import transforms
from tephpy.plotting.barbs import select_barbs, staff_y
from tephpy.plotting.isopleths import isobar_members


def test_staff_y_points_lie_on_their_isobars():
    """Inverting a crossing recovers a point at exactly that pressure."""
    pressure = np.array([1000.0, 850.0, 500.0, 300.0])
    x_edge = 1800.0
    y = staff_y(pressure, x_edge)
    assert np.isfinite(y).all()
    temperature, theta = transforms.temperature_theta_from_xy(
        np.full(y.shape, x_edge), y
    )
    expected = transforms.theta_from_pressure_temperature(pressure, temperature)
    np.testing.assert_allclose(theta, expected, rtol=1e-6)


def test_staff_y_matches_the_drawn_isobar_polyline():
    """Where the crossing lies inside the drawn domain, the polyline agrees."""
    (member,) = isobar_members([500.0])
    inside = member.xy[member.xy[:, 0] <= member.xy[-1, 0] - 1.0]
    x_edge = float(inside[len(inside) // 2, 0])
    y_polyline = np.interp(x_edge, member.xy[:, 0], member.xy[:, 1])
    assert staff_y([500.0], x_edge)[0] == pytest.approx(y_polyline, abs=1e-2)


def test_staff_y_extends_beyond_the_drawn_temperature_domain():
    """A crossing past TEMPERATURE_DOMAIN stays finite (spec placement rule)."""
    (member,) = isobar_members([850.0])
    beyond = float(member.xy[-1, 0]) + 10.0
    assert np.isfinite(staff_y([850.0], beyond)[0])


def test_staff_y_nan_for_unphysical_or_unreachable_input():
    y = staff_y([-10.0, 0.0, 850.0], 1e9)
    assert np.isnan(y).all()


def test_select_barbs_keeps_the_first_and_spaced_positions():
    y = np.array([0.0, 10.0, 25.0, 30.0, 55.0])
    np.testing.assert_array_equal(
        select_barbs(y, minimum_separation=20.0),
        [True, False, True, False, True],
    )


def test_select_barbs_boundary_separation_is_kept():
    y = np.array([0.0, 20.0])
    np.testing.assert_array_equal(
        select_barbs(y, minimum_separation=20.0), [True, True]
    )


def test_select_barbs_drops_non_finite_positions():
    y = np.array([np.nan, 5.0, np.inf, 50.0])
    np.testing.assert_array_equal(
        select_barbs(y, minimum_separation=20.0), [False, True, False, True]
    )
