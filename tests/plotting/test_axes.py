# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the tephigram matplotlib projection (spec §3.1)."""

from __future__ import annotations

import matplotlib.pyplot as plt
from metpy.units import units
import numpy as np
import pytest

from tephpy import transforms
from tephpy._config import config
from tephpy._constants import DEFAULT_EXTENT
from tephpy.exceptions import TephpyUnitsError
from tephpy.plotting.axes import TephigramAxes, TephigramTransform
from tephpy.plotting.isopleths import IsoplethFamily


def test_transform_matches_functions():
    """The matplotlib Transform delegates to the transforms module exactly."""
    tr = TephigramTransform()
    points = np.array([[15.0, 15.0], [-40.0, 20.0], [0.0, 100.0]])
    out = tr.transform(points)
    x, y = transforms.xy_from_temperature_theta(points[:, 0], points[:, 1])
    np.testing.assert_allclose(out, np.column_stack([x, y]), rtol=1e-12)


def test_transform_round_trip_via_inverted():
    """Transform followed by its inverse is the identity (invertibility)."""
    tr = TephigramTransform()
    points = np.array([[15.0, 15.0], [-40.0, 20.0], [30.0, 250.0]])
    back = tr.inverted().transform(tr.transform(points))
    np.testing.assert_allclose(back, points, rtol=1e-9, atol=1e-9)


def test_transform_non_affine_accepts_1d_point():
    """A length-2 1-D input returns a shape (2,) result (base-class contract)."""
    tr = TephigramTransform()
    out = tr.transform_non_affine(np.array([15.0, 15.0]))
    assert out.shape == (2,)
    assert out.dtype == np.float64
    x, y = transforms.xy_from_temperature_theta(15.0, 15.0)
    np.testing.assert_allclose(out, [x, y], rtol=1e-12)
    points = np.array([[15.0, 15.0], [-40.0, 20.0], [0.0, 100.0]])
    xs, ys = transforms.xy_from_temperature_theta(points[:, 0], points[:, 1])
    np.testing.assert_allclose(
        tr.transform_non_affine(points), np.column_stack([xs, ys]), rtol=1e-12
    )


def test_inverted_transform_non_affine_accepts_1d_point():
    """The inverse also honours the 1-D form, shape-preserving both ways."""
    tr = TephigramTransform().inverted()
    out = tr.transform_non_affine(np.array([0.5, 200.0]))
    assert out.shape == (2,)
    assert out.dtype == np.float64
    t1, theta1 = transforms.temperature_theta_from_xy(0.5, 200.0)
    np.testing.assert_allclose(out, [t1, theta1], rtol=1e-12)
    points = np.array([[15.0, 15.0], [-40.0, 20.0], [0.0, 100.0]])
    t, theta = transforms.temperature_theta_from_xy(points[:, 0], points[:, 1])
    np.testing.assert_allclose(
        tr.transform_non_affine(points), np.column_stack([t, theta]), rtol=1e-12
    )


def test_transform_dimensions():
    """2-in, 2-out, non-separable, declared invertible."""
    tr = TephigramTransform()
    assert tr.input_dims == 2
    assert tr.output_dims == 2
    assert not tr.is_separable
    assert tr.has_inverse


@pytest.fixture
def tephigram_axes():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    yield ax
    plt.close(fig)


def test_projection_registered_by_package_import(tephigram_axes):
    """`import tephpy` registers the projection for stock matplotlib idioms."""
    assert isinstance(tephigram_axes, TephigramAxes)
    assert tephigram_axes.name == "tephigram"


def test_axes_defaults(tephigram_axes):
    """Equal aspect, hidden native ticks, finite default extents."""
    assert tephigram_axes.get_aspect() == 1.0
    assert not tephigram_axes.xaxis.get_visible()
    assert not tephigram_axes.yaxis.get_visible()
    x0, x1 = tephigram_axes.get_xlim()
    y0, y1 = tephigram_axes.get_ylim()
    assert np.isfinite([x0, x1, y0, y1]).all()
    assert x0 < x1
    assert y0 < y1


def test_axes_exposes_invertible_tephigram_transform(tephigram_axes):
    """The (T, theta) mapping is available for artists and later plans."""
    composed = tephigram_axes.tephigram_transform + tephigram_axes.transData
    points = np.array([[15.0, 15.0], [-40.0, 20.0]])
    display = composed.transform(points)
    assert np.isfinite(display).all()
    back = tephigram_axes.tephigram_transform.inverted().transform(
        tephigram_axes.tephigram_transform.transform(points)
    )
    np.testing.assert_allclose(back, points, rtol=1e-9)


def test_plot_in_temperature_theta_space(tephigram_axes):
    """Plotting through the exposed transform draws within the default view.

    The line is added to the axes and its mapped (x, y) endpoints land
    inside the default xlim/ylim, so it is genuinely in view.
    """
    (line,) = tephigram_axes.plot(
        [0.0, 10.0],
        [10.0, 40.0],
        transform=tephigram_axes.tephigram_transform + tephigram_axes.transData,
    )
    assert line in tephigram_axes.lines
    x, y = transforms.xy_from_temperature_theta(
        np.array([0.0, 10.0]), np.array([10.0, 40.0])
    )
    x0, x1 = tephigram_axes.get_xlim()
    y0, y1 = tephigram_axes.get_ylim()
    assert np.all((x0 <= x) & (x <= x1))
    assert np.all((y0 <= y) & (y <= y1))


FAMILY_NAMES = (
    "isotherms",
    "isobars",
    "dry_adiabats",
    "moist_adiabats",
    "mixing_ratios",
)


def _expected_limits(extent):
    """Map extent corners through the transforms to expected x/y limits."""
    (p0, t0), (p1, t1) = extent
    thetas = transforms.theta_from_pressure_temperature(
        np.array([p0, p1]), np.array([t0, t1])
    )
    x, y = transforms.xy_from_temperature_theta(np.array([t0, t1]), thetas)
    return (float(np.min(x)), float(np.max(x))), (float(np.min(y)), float(np.max(y)))


def test_families_present_and_on_by_default(tephigram_axes):
    families = [
        artist
        for artist in tephigram_axes.get_children()
        if isinstance(artist, IsoplethFamily)
    ]
    assert len(families) == 5
    for name in FAMILY_NAMES:
        family = getattr(tephigram_axes, name)()
        assert isinstance(family, IsoplethFamily)
        assert family in families
        assert family.get_visible()


def test_default_draw_populates_every_family(tephigram_axes):
    tephigram_axes.figure.canvas.draw()
    for name in FAMILY_NAMES:
        family = getattr(tephigram_axes, name)()
        assert len(family._lines.get_segments()) > 0


def test_accessors_reconfigure_and_return(tephigram_axes):
    family = tephigram_axes.isobars(color="black", labels=False)
    assert family is tephigram_axes.isobars()
    assert family.options.color == "black"
    assert family.options.labels is False


def test_accessor_visibility_toggle(tephigram_axes):
    family = tephigram_axes.mixing_ratios(visible=False)
    assert not family.get_visible()


def test_accessor_rejects_unknown_kwarg(tephigram_axes):
    with pytest.raises(TypeError):
        tephigram_axes.isotherms(steps=3)
    with pytest.raises(TypeError):
        tephigram_axes.mixing_ratios(interval=5.0)


def test_moist_adiabats_truncation_kwarg(tephigram_axes):
    family = tephigram_axes.moist_adiabats(truncation=-30.0)
    assert family.options.truncation == -30.0


def test_default_extent_applied(tephigram_axes):
    (x0, x1), (y0, y1) = _expected_limits(DEFAULT_EXTENT)
    assert tephigram_axes.get_xlim() == pytest.approx((x0, x1))
    assert tephigram_axes.get_ylim() == pytest.approx((y0, y1))


def test_set_extent_moves_the_view(tephigram_axes):
    extent = ((1050.0, -10.0), (700.0, 30.0))
    tephigram_axes.set_extent(extent)
    (x0, x1), (y0, y1) = _expected_limits(extent)
    assert tephigram_axes.get_xlim() == pytest.approx((x0, x1))
    assert tephigram_axes.get_ylim() == pytest.approx((y0, y1))


def test_set_extent_disables_autoscale_so_overlays_do_not_drift(tephigram_axes):
    tephigram_axes.set_extent(DEFAULT_EXTENT)
    before = (tephigram_axes.get_xlim(), tephigram_axes.get_ylim())
    assert not tephigram_axes.get_autoscale_on()
    tephigram_axes.plot(
        [0.0, 200.0],
        [10.0, 400.0],
        transform=tephigram_axes.tephigram_transform + tephigram_axes.transData,
    )
    tephigram_axes.figure.canvas.draw()
    assert (tephigram_axes.get_xlim(), tephigram_axes.get_ylim()) == before


def test_set_extent_rejects_unphysical_corners(tephigram_axes):
    with pytest.raises(ValueError, match="physical"):
        tephigram_axes.set_extent(((0.0, -40.0), (200.0, 40.0)))
    with pytest.raises(ValueError, match="degenerate"):
        tephigram_axes.set_extent(((850.0, 10.0), (850.0, 10.0)))


def test_clear_restores_projection_defaults(tephigram_axes):
    old_family = tephigram_axes.isobars()
    tephigram_axes.plot([1700.0, 1750.0], [1700.0, 1750.0])
    tephigram_axes.clear()
    assert old_family.axes is None
    fresh = [
        artist
        for artist in tephigram_axes.get_children()
        if isinstance(artist, IsoplethFamily)
    ]
    assert len(fresh) == 5
    assert old_family not in fresh
    assert not tephigram_axes.lines
    assert tephigram_axes.get_aspect() == 1.0
    assert not tephigram_axes.xaxis.get_visible()
    assert not tephigram_axes.yaxis.get_visible()
    (x0, x1), (y0, y1) = _expected_limits(DEFAULT_EXTENT)
    assert tephigram_axes.get_xlim() == pytest.approx((x0, x1))
    assert tephigram_axes.get_ylim() == pytest.approx((y0, y1))


def test_config_diagram_extent_honoured_at_creation():
    extent = ((1000.0, -20.0), (500.0, 20.0))
    with config.context(diagram={"extent": extent}):
        fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        (x0, x1), (y0, y1) = _expected_limits(extent)
        assert ax.get_xlim() == pytest.approx((x0, x1))
        assert ax.get_ylim() == pytest.approx((y0, y1))
    finally:
        plt.close(fig)


PROFILE_PRESSURE = units.Quantity(np.array([1000.0, 850.0, 700.0, 500.0]), "hPa")
PROFILE_TEMPERATURE = units.Quantity(np.array([20.0, 12.0, 4.0, -12.0]), "degC")


def test_plot_profile_maps_through_the_transforms(tephigram_axes):
    line = tephigram_axes.plot_profile(PROFILE_PRESSURE, PROFILE_TEMPERATURE)
    expected_theta = transforms.theta_from_pressure_temperature(
        PROFILE_PRESSURE.m_as("hPa"), PROFILE_TEMPERATURE.m_as("degC")
    )
    np.testing.assert_allclose(line.get_xdata(), PROFILE_TEMPERATURE.m_as("degC"))
    np.testing.assert_allclose(line.get_ydata(), expected_theta)
    expected_transform = tephigram_axes.tephigram_transform + tephigram_axes.transData
    assert line.get_transform() == expected_transform


def test_plot_profile_any_units_just_work(tephigram_axes):
    """K/Pa quantities plot identically to their hPa/degC equivalents."""
    native = tephigram_axes.plot_profile(PROFILE_PRESSURE, PROFILE_TEMPERATURE)
    converted = tephigram_axes.plot_profile(
        PROFILE_PRESSURE.to("Pa"), PROFILE_TEMPERATURE.to("K")
    )
    np.testing.assert_allclose(converted.get_xdata(), native.get_xdata())
    np.testing.assert_allclose(converted.get_ydata(), native.get_ydata())


def test_plot_profile_bare_arrays_with_units(tephigram_axes):
    line = tephigram_axes.plot_profile(
        [1000.0, 850.0],
        [20.0, 12.0],
        units={"pressure": "hPa", "temperature": "degC"},
    )
    np.testing.assert_allclose(line.get_xdata(), [20.0, 12.0])


def test_plot_profile_bare_arrays_without_units_raise(tephigram_axes):
    with pytest.raises(TephpyUnitsError, match="'pressure' has no units"):
        tephigram_axes.plot_profile([1000.0, 850.0], [20.0, 12.0])


def test_plot_profile_kwargs_and_label_pass_through(tephigram_axes):
    line = tephigram_axes.plot_profile(
        PROFILE_PRESSURE,
        PROFILE_TEMPERATURE,
        label="parcel",
        color="black",
        linestyle="--",
    )
    assert line.get_label() == "parcel"
    assert line.get_color() == "black"
    assert line.get_linestyle() == "--"


def test_plot_profile_does_not_drift_the_view(tephigram_axes):
    """Profiles never autoscale the fixed extent (spec §3.2)."""
    before = (tephigram_axes.get_xlim(), tephigram_axes.get_ylim())
    tephigram_axes.plot_profile(PROFILE_PRESSURE, PROFILE_TEMPERATURE)
    tephigram_axes.figure.canvas.draw()
    assert (tephigram_axes.get_xlim(), tephigram_axes.get_ylim()) == before
