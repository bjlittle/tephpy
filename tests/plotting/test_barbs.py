# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the wind-barb gutter staff (spec §3.2)."""

from __future__ import annotations

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytest

from tephpy import Sounding, calc, transforms
from tephpy._constants import (
    BARB_MIN_SEPARATION,
    BARB_STAFF_POSITION,
)
from tephpy.exceptions import MissingDataError
from tephpy.plotting.barbs import BarbStaff, select_barbs, staff_y
from tephpy.plotting.isopleths import isobar_members

N = 30
PRESSURE = np.linspace(1000.0, 200.0, N)
TEMPERATURE = np.linspace(20.0, -55.0, N)
WIND_SPEED = np.linspace(5.0, 80.0, N)
WIND_DIRECTION = np.linspace(200.0, 320.0, N) % 360.0
UNITS = {
    "pressure": "hPa",
    "temperature": "degC",
    "wind_speed": "knots",
    "wind_direction": "degree",
}


def _sounding(**kwargs):
    """Build the module's reference wind-carrying sounding."""
    return Sounding(
        PRESSURE,
        TEMPERATURE,
        wind_speed=WIND_SPEED,
        wind_direction=WIND_DIRECTION,
        units=UNITS,
        **kwargs,
    )


def _indices():
    """Build a plausible SoundingIndices for the panel-layout tests."""
    values = {
        "cape": 250.0,
        "cin": -20.0,
        "lcl_pressure": 900.0,
        "lcl_temperature": 12.0,
        "lfc_pressure": 850.0,
        "lfc_temperature": 10.0,
        "el_pressure": 300.0,
        "el_temperature": -45.0,
        "theta_w": 15.0,
        "lifted_index": -2.0,
    }
    units = {
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
    }
    return calc.SoundingIndices(units=units, **values)


@pytest.fixture
def tephigram_axes():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    yield ax
    plt.close(fig)


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


def test_plot_barbs_requires_wind(tephigram_axes):
    snd = Sounding(
        PRESSURE,
        TEMPERATURE,
        units={"pressure": "hPa", "temperature": "degC"},
    )
    with pytest.raises(MissingDataError, match="needs wind"):
        tephigram_axes.plot_barbs(snd)


def test_plot_barbs_returns_a_staff_in_the_gutter(tephigram_axes):
    staff = tephigram_axes.plot_barbs(_sounding())
    assert isinstance(staff, BarbStaff)
    gutter = tephigram_axes._barb_gutter
    assert staff.axes is gutter
    assert staff.barbs is None
    tephigram_axes.figure.canvas.draw()
    assert staff.barbs is not None
    assert len(staff.barbs.get_paths()) > 0


def test_plot_barbs_draws_the_selected_levels(tephigram_axes):
    """The drawn count equals the headless geometry pipeline's count."""
    staff = tephigram_axes.plot_barbs(_sounding())
    fig = tephigram_axes.figure
    fig.canvas.draw()
    gutter = tephigram_axes._barb_gutter
    y = staff_y(PRESSURE, tephigram_axes.get_xlim()[1])
    y0, y1 = sorted(tephigram_axes.get_ylim())
    visible = np.isfinite(y) & (y >= y0) & (y <= y1)
    offsets = np.column_stack([np.full(N, BARB_STAFF_POSITION), y])
    display = gutter.transData.transform(offsets)[:, 1]
    display[~visible] = np.nan
    expected = select_barbs(
        display, minimum_separation=BARB_MIN_SEPARATION * fig.dpi / 72.0
    )
    assert len(staff.barbs.get_paths()) == int(expected.sum())


def test_plot_barbs_zoom_changes_the_drawn_levels(tephigram_axes):
    staff = tephigram_axes.plot_barbs(_sounding())
    tephigram_axes.figure.canvas.draw()
    default_count = len(staff.barbs.get_paths())
    tephigram_axes.set_extent(pressure=(1000.0, 850.0), temperature=(-20.0, 30.0))
    tephigram_axes.figure.canvas.draw()
    zoomed_count = len(staff.barbs.get_paths())
    assert zoomed_count != default_count


def test_plot_barbs_minimum_separation_thins_the_drawn_levels(tephigram_axes):
    """A per-call separation wider than the convention keeps fewer levels."""
    default = tephigram_axes.plot_barbs(_sounding())
    sparse = tephigram_axes.plot_barbs(
        _sounding(), x=0.8, minimum_separation=BARB_MIN_SEPARATION * 3.0
    )
    tephigram_axes.figure.canvas.draw()
    assert default._minimum_separation == BARB_MIN_SEPARATION
    assert sparse._minimum_separation == BARB_MIN_SEPARATION * 3.0
    assert len(sparse.barbs.get_paths()) < len(default.barbs.get_paths())


def test_plot_barbs_view_clear_of_every_level_masks_every_member(tephigram_axes):
    """A view above the profile top leaves no candidate: all members mask."""
    staff = tephigram_axes.plot_barbs(_sounding())
    fig = tephigram_axes.figure
    fig.canvas.draw()
    assert len(staff.barbs.get_paths()) > 0
    tephigram_axes.set_extent(pressure=(150.0, 100.0), temperature=(-80.0, -60.0))
    fig.canvas.draw()
    y = staff_y(PRESSURE, tephigram_axes.get_xlim()[1])
    y0, y1 = sorted(tephigram_axes.get_ylim())
    assert not (np.isfinite(y) & (y >= y0) & (y <= y1)).any()
    assert len(staff.barbs.get_paths()) == 0
    assert staff.barbs.u.size == N
    assert np.ma.getmaskarray(staff.barbs.u).all()
    tephigram_axes.set_extent(pressure=(1000.0, 200.0), temperature=(-50.0, 40.0))
    fig.canvas.draw()
    assert len(staff.barbs.get_paths()) > 0


def test_plot_barbs_builds_a_masked_child_when_nothing_is_in_view(tephigram_axes):
    """The zero-candidate branch also holds on the very first draw."""
    tephigram_axes.set_extent(pressure=(150.0, 100.0), temperature=(-80.0, -60.0))
    staff = tephigram_axes.plot_barbs(_sounding())
    tephigram_axes.figure.canvas.draw()
    assert staff.barbs is not None
    assert len(staff.barbs.get_paths()) == 0
    assert np.ma.getmaskarray(staff.barbs.u).all()


def test_plot_barbs_shares_one_gutter_across_calls(tephigram_axes):
    first = tephigram_axes.plot_barbs(_sounding())
    second = tephigram_axes.plot_barbs(_sounding(), x=0.2)
    assert first.axes is second.axes
    tephigram_axes.figure.canvas.draw()
    assert first.barbs.get_offsets()[0, 0] == pytest.approx(BARB_STAFF_POSITION)
    assert second.barbs.get_offsets()[0, 0] == pytest.approx(0.2)


def test_plot_barbs_kwargs_pass_through(tephigram_axes):
    staff = tephigram_axes.plot_barbs(_sounding(), color="tab:blue")
    tephigram_axes.figure.canvas.draw()
    expected = mcolors.to_rgba("tab:blue")
    assert tuple(staff.barbs.get_facecolor()[0]) == pytest.approx(expected)


def test_plot_barbs_converts_wind_speed_units(tephigram_axes):
    """A m/s sounding feeds the knot-calibrated increments correctly."""
    snd = Sounding(
        PRESSURE,
        TEMPERATURE,
        wind_speed=np.full(N, 10.0),
        wind_direction=np.full(N, 360.0),
        units={**UNITS, "wind_speed": "m/s"},
    )
    staff = tephigram_axes.plot_barbs(snd)
    speed = np.hypot(staff._u, staff._v)
    np.testing.assert_allclose(speed, 10.0 / 0.514444, rtol=1e-4)


def test_plot_barbs_gutter_tracks_the_view(tephigram_axes):
    tephigram_axes.plot_barbs(_sounding())
    tephigram_axes.set_extent(pressure=(1000.0, 850.0), temperature=(-20.0, 30.0))
    assert tephigram_axes._barb_gutter.get_ylim() == tephigram_axes.get_ylim()


def _bounds(axes):
    return axes.get_position().bounds


def test_side_panels_land_inside_out_barbs_first(tephigram_axes):
    snd = _sounding()
    tephigram_axes.plot_barbs(snd)
    panel = tephigram_axes.annotate_indices(_indices())
    tephigram_axes.figure.canvas.draw()
    main, gutter = _bounds(tephigram_axes), _bounds(tephigram_axes._barb_gutter)
    assert main[0] < gutter[0] < _bounds(panel)[0]


def test_side_panels_land_inside_out_indices_first(tephigram_axes):
    """Call order is irrelevant: the layout is rebuilt inside-out (spec §3.2)."""
    snd = _sounding()
    panel = tephigram_axes.annotate_indices(_indices())
    tephigram_axes.plot_barbs(snd)
    tephigram_axes.figure.canvas.draw()
    main, gutter = _bounds(tephigram_axes), _bounds(tephigram_axes._barb_gutter)
    assert main[0] < gutter[0] < _bounds(panel)[0]


def test_side_panels_share_one_divider(tephigram_axes):
    snd = _sounding()
    tephigram_axes.annotate_indices(_indices())
    divider = tephigram_axes._side_divider
    tephigram_axes.plot_barbs(snd)
    assert tephigram_axes._side_divider is divider


def test_clear_removes_the_gutter_and_restores_the_slot(tephigram_axes):
    fig = tephigram_axes.figure
    fig.canvas.draw()
    full = _bounds(tephigram_axes)
    tephigram_axes.plot_barbs(_sounding())
    fig.canvas.draw()
    assert _bounds(tephigram_axes)[2] < full[2]
    tephigram_axes.clear()
    fig.canvas.draw()
    assert tephigram_axes._barb_gutter is None
    assert tephigram_axes._side_divider is None
    assert _bounds(tephigram_axes) == pytest.approx(full)


def test_figure_clear_with_the_gutter_and_a_panel(tephigram_axes):
    """Both panels go with the figure's own teardown, in either order."""
    fig = tephigram_axes.figure
    tephigram_axes.plot_barbs(_sounding())
    tephigram_axes.annotate_indices(_indices())
    fig.canvas.draw()
    fig.clear()
    assert fig.axes == []
    assert tephigram_axes._barb_gutter is None
    assert tephigram_axes._indices_panel is None
