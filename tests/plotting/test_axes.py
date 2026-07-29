# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the tephigram matplotlib projection (spec §3.1)."""

from __future__ import annotations

import matplotlib.colors as mcolors
from matplotlib.patches import PathPatch
from matplotlib.path import Path
import matplotlib.pyplot as plt
from metpy.units import units
import numpy as np
import pytest

from tephpy import Sounding, calc, transforms
from tephpy._config import config
from tephpy._constants import (
    CAPE_COLOR,
    CIN_COLOR,
    DEFAULT_EXTENT,
    INDICES_PANEL_ROWS,
    PROFILE_DEWPOINT_COLOR,
    PROFILE_LINEWIDTH,
    PROFILE_TEMPERATURE_COLOR,
    PROFILE_ZORDER,
    SHADING_ALPHA,
    SHADING_ZORDER,
)
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


def _cursor_xy(pressure, temperature):
    """Map a (pressure, temperature) point into cursor data-space (x, y)."""
    theta = transforms.theta_from_pressure_temperature(pressure, temperature)
    x, y = transforms.xy_from_temperature_theta(temperature, theta)
    return float(x), float(y)


def test_format_coord_default_trio(tephigram_axes):
    """The toolbar readout renders p, T, theta — not raw data-space (x, y)."""
    x, y = _cursor_xy(850.0, -4.2)
    assert tephigram_axes.format_coord(x, y) == "850 hPa, -4.2 °C, θ 8.6 °C"


def test_format_coord_config_fields_read_live(tephigram_axes):
    """config.cursor.fields reorders/selects, live on an existing axes (§3.5)."""
    x, y = _cursor_xy(850.0, -4.2)
    with config.context(cursor={"fields": ("theta", "pressure")}):
        assert tephigram_axes.format_coord(x, y) == "θ 8.6 °C, 850 hPa"
    assert tephigram_axes.format_coord(x, y) == "850 hPa, -4.2 °C, θ 8.6 °C"


def test_format_coord_out_of_domain_blank(tephigram_axes):
    """Left of the -273.15 °C isotherm the pressure is NaN: blank readout."""
    assert tephigram_axes.format_coord(-300.0, 300.0) == ""


def test_format_coord_instance_assignment_wins(tephigram_axes):
    """Stock matplotlib full-custom path: assignment shadows the method (§3.2)."""

    def custom(_x, _y):
        return "custom"

    tephigram_axes.format_coord = custom
    assert tephigram_axes.format_coord(1.0, 2.0) == "custom"


def test_format_coord_metpy_fields(tephigram_axes):
    """Opt-in fields: saturation mixing ratio and the moist adiabat (θw)."""
    x, y = _cursor_xy(850.0, -4.2)
    with config.context(cursor={"fields": ("mixing_ratio", "theta_w")}):
        assert tephigram_axes.format_coord(x, y) == "3.3 g/kg, θw 4.0 °C"


def test_format_coord_unknown_field_raises(tephigram_axes):
    with (
        config.context(cursor={"fields": ("bogus",)}),
        pytest.raises(TypeError, match="unknown cursor field"),
    ):
        tephigram_axes.format_coord(0.0, 0.0)


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
PROFILE_DEWPOINT = units.Quantity(np.array([15.0, 8.0, np.nan, -30.0]), "degC")


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


def _sounding(**kwargs):
    """Build the module's reference sounding with metadata overrides."""
    return Sounding(
        PROFILE_PRESSURE, PROFILE_TEMPERATURE, dewpoint=PROFILE_DEWPOINT, **kwargs
    )


def test_plot_sounding_conventional_colours_and_zorder(tephigram_axes):
    temperature_line, dewpoint_line = tephigram_axes.plot_sounding(_sounding())
    assert temperature_line.get_color() == PROFILE_TEMPERATURE_COLOR
    assert dewpoint_line.get_color() == PROFILE_DEWPOINT_COLOR
    assert temperature_line.get_linewidth() == PROFILE_LINEWIDTH
    for line in (temperature_line, dewpoint_line):
        assert line.get_zorder() == PROFILE_ZORDER
        assert line.get_zorder() > max(
            family.get_zorder() for family in tephigram_axes._families.values()
        )


def test_plot_sounding_without_dewpoint(tephigram_axes):
    snd = Sounding(PROFILE_PRESSURE, PROFILE_TEMPERATURE)
    temperature_line, dewpoint_line = tephigram_axes.plot_sounding(snd)
    assert temperature_line is not None
    assert dewpoint_line is None


def test_plot_sounding_label_precedence(tephigram_axes):
    """label= argument > snd.label > no legend entry (spec §3.2)."""
    labelled = _sounding(label="observed")
    temperature_line, _ = tephigram_axes.plot_sounding(labelled)
    assert temperature_line.get_label() == "observed"
    overridden, _ = tephigram_axes.plot_sounding(labelled, label="forecast")
    assert overridden.get_label() == "forecast"
    anonymous, _ = tephigram_axes.plot_sounding(_sounding())
    assert anonymous.get_label().startswith("_")


def test_plot_sounding_one_legend_entry_per_sounding(tephigram_axes):
    """The dewpoint line is _nolegend_; unlabelled soundings add nothing."""
    _, dewpoint_line = tephigram_axes.plot_sounding(_sounding(label="obs"))
    assert dewpoint_line.get_label() == "_nolegend_"
    tephigram_axes.plot_sounding(_sounding())
    legend = tephigram_axes.legend()
    assert [text.get_text() for text in legend.get_texts()] == ["obs"]


def test_plot_sounding_overlay_with_distinguishable_styles(tephigram_axes):
    """Two soundings overlay with per-call styles and legend entries."""
    first, _ = tephigram_axes.plot_sounding(_sounding(label="00Z"))
    second, _ = tephigram_axes.plot_sounding(
        _sounding(label="12Z"), linestyle="--", alpha=0.6
    )
    assert second.get_linestyle() == "--"
    assert second.get_alpha() == 0.6
    assert first.get_linestyle() == "-"
    legend = tephigram_axes.legend()
    assert [text.get_text() for text in legend.get_texts()] == ["00Z", "12Z"]


def test_plot_sounding_kwargs_override_convention_colours(tephigram_axes):
    temperature_line, dewpoint_line = tephigram_axes.plot_sounding(
        _sounding(), color="purple"
    )
    assert temperature_line.get_color() == "purple"
    assert dewpoint_line.get_color() == "purple"


# --- Profile plotting, shading, and the indices panel (spec §3.2/§3.3) ----

CAPPED_PRESSURE = units.Quantity(
    np.array([1000.0, 950.0, 900.0, 850.0, 700.0, 500.0, 300.0, 200.0]), "hPa"
)
CAPPED_TEMPERATURE = units.Quantity(
    np.array([26.0, 24.0, 23.0, 21.0, 10.0, -12.0, -40.0, -55.0]), "degC"
)
CAPPED_DEWPOINT = units.Quantity(
    np.array([20.0, 17.0, 14.0, 10.0, 2.0, -15.0, -45.0, -60.0]), "degC"
)


def _capped_sounding():
    """Build a capped convective sounding with both CAPE and CIN."""
    return Sounding(CAPPED_PRESSURE, CAPPED_TEMPERATURE, dewpoint=CAPPED_DEWPOINT)


def test_plot_profile_accepts_a_parcel_profile(tephigram_axes):
    """The Profile form plots the path through the transform machinery."""
    parcel = calc.parcel_path(_capped_sounding(), label="surface parcel")
    line = tephigram_axes.plot_profile(parcel, color="black", linestyle="--")
    np.testing.assert_allclose(line.get_xdata(), parcel.temperature.m_as("degC"))
    expected_theta = transforms.theta_from_pressure_temperature(
        parcel.pressure.m_as("hPa"), parcel.temperature.m_as("degC")
    )
    np.testing.assert_allclose(line.get_ydata(), expected_theta)
    assert line.get_label() == "surface parcel"
    assert line.get_color() == "black"


def test_plot_profile_profile_label_precedence(tephigram_axes):
    """label= argument > profile.label > no legend entry (spec §3.2)."""
    labelled = calc.parcel_path(_capped_sounding(), label="from the profile")
    assert tephigram_axes.plot_profile(labelled).get_label() == "from the profile"
    overridden = tephigram_axes.plot_profile(labelled, label="argument wins")
    assert overridden.get_label() == "argument wins"
    anonymous = tephigram_axes.plot_profile(calc.parcel_path(_capped_sounding()))
    assert anonymous.get_label().startswith("_")


def test_plot_profile_profile_form_sets_no_style_defaults(tephigram_axes):
    """The low-level primitive: matplotlib defaults, not conventions."""
    line = tephigram_axes.plot_profile(calc.parcel_path(_capped_sounding()))
    assert line.get_linewidth() == plt.rcParams["lines.linewidth"]
    assert line.get_zorder() == 2


def test_plot_profile_wrong_combinations_are_type_errors(tephigram_axes):
    """Bad argument shapes are TypeErrors, never units errors (spec §3.2)."""
    snd = _capped_sounding()
    parcel = calc.parcel_path(snd)
    with pytest.raises(TypeError, match="no separate temperature"):
        tephigram_axes.plot_profile(parcel, CAPPED_TEMPERATURE)
    with pytest.raises(TypeError, match="no units="):
        tephigram_axes.plot_profile(parcel, units={"pressure": "hPa"})
    with pytest.raises(TypeError, match="needs pressure and temperature"):
        tephigram_axes.plot_profile(CAPPED_PRESSURE)
    with pytest.raises(TypeError, match="needs pressure and temperature"):
        tephigram_axes.plot_profile(snd)


def _stable_sounding():
    """Build a stable sounding: no positive buoyancy anywhere."""
    return Sounding(
        units.Quantity(np.array([1000.0, 850.0, 700.0, 500.0, 300.0]), "hPa"),
        units.Quantity(np.array([5.0, 3.0, 0.0, -14.0, -40.0]), "degC"),
        dewpoint=units.Quantity(np.array([-5.0, -10.0, -15.0, -30.0, -55.0]), "degC"),
    )


def test_shade_cape_draws_one_compound_patch(tephigram_axes):
    snd = _capped_sounding()
    parcel = calc.parcel_path(snd)
    patch = tephigram_axes.shade_cape(snd, parcel)
    assert isinstance(patch, PathPatch)
    assert patch in tephigram_axes.patches
    expected = tephigram_axes.tephigram_transform + tephigram_axes.transData
    assert patch.get_data_transform() == expected
    np.testing.assert_allclose(
        patch.get_facecolor(), mcolors.to_rgba(CAPE_COLOR, SHADING_ALPHA)
    )
    assert (patch.get_path().codes == Path.MOVETO).sum() == 1


def test_shade_cin_draws_below_the_lfc(tephigram_axes):
    snd = _capped_sounding()
    parcel = calc.parcel_path(snd)
    patch = tephigram_axes.shade_cin(snd, parcel)
    assert isinstance(patch, PathPatch)
    np.testing.assert_allclose(
        patch.get_facecolor(), mcolors.to_rgba(CIN_COLOR, SHADING_ALPHA)
    )


def test_shading_zorder_between_families_and_profiles(tephigram_axes):
    snd = _capped_sounding()
    parcel = calc.parcel_path(snd)
    parcel_line = tephigram_axes.plot_profile(parcel)
    patch = tephigram_axes.shade_cape(snd, parcel)
    family_zorders = [
        family.get_zorder() for family in tephigram_axes._families.values()
    ]
    assert max(family_zorders) < patch.get_zorder() == SHADING_ZORDER
    # A parcel path drawn through plot_profile sets no zorder, so it sits at
    # Matplotlib's default; the shading must still render strictly below it
    # (and below the PROFILE_ZORDER sounding lines).
    assert patch.get_zorder() < parcel_line.get_zorder() < PROFILE_ZORDER


def test_shade_kwargs_override_the_conventions(tephigram_axes):
    snd = _capped_sounding()
    patch = tephigram_axes.shade_cape(
        snd, calc.parcel_path(snd), facecolor="purple", alpha=0.5
    )
    np.testing.assert_allclose(patch.get_facecolor(), mcolors.to_rgba("purple", 0.5))


def test_shade_zero_area_returns_none(tephigram_axes):
    """0 is an answer, not an error (spec §6)."""
    snd = _stable_sounding()
    parcel = calc.parcel_path(snd)
    assert tephigram_axes.shade_cape(snd, parcel) is None
    assert tephigram_axes.shade_cin(snd, parcel) is None


def test_shading_does_not_drift_the_view(tephigram_axes):
    """Patches never autoscale the fixed extent (spec §3.2)."""
    before = (tephigram_axes.get_xlim(), tephigram_axes.get_ylim())
    snd = _capped_sounding()
    parcel = calc.parcel_path(snd)
    tephigram_axes.shade_cape(snd, parcel)
    tephigram_axes.shade_cin(snd, parcel)
    tephigram_axes.figure.canvas.draw()
    assert (tephigram_axes.get_xlim(), tephigram_axes.get_ylim()) == before


def test_annotate_indices_returns_a_side_panel(tephigram_axes):
    result = calc.indices(_capped_sounding())
    panel = tephigram_axes.annotate_indices(result)
    assert panel in tephigram_axes.figure.axes
    assert not isinstance(panel, TephigramAxes)
    assert not panel.axison
    texts = [text.get_text() for text in panel.texts]
    assert len(texts) == 2 * len(INDICES_PANEL_ROWS)
    assert "CAPE" in texts
    assert any(text.endswith("J/kg") for text in texts)


def test_annotate_indices_updates_in_place(tephigram_axes):
    """Calling it again updates the panel, never stacks a second one."""
    result = calc.indices(_capped_sounding())
    panel = tephigram_axes.annotate_indices(result)
    count = len(tephigram_axes.figure.axes)
    assert tephigram_axes.annotate_indices(result) is panel
    assert len(tephigram_axes.figure.axes) == count
    assert len(panel.texts) == 2 * len(INDICES_PANEL_ROWS)


def test_annotate_indices_renders_nan_as_em_dash(tephigram_axes):
    """A stable sounding has no LFC/EL: those rows show an em dash."""
    panel = tephigram_axes.annotate_indices(calc.indices(_stable_sounding()))
    texts = [text.get_text() for text in panel.texts]
    assert "—" in texts


def test_clear_removes_the_indices_panel(tephigram_axes):
    tephigram_axes.annotate_indices(calc.indices(_capped_sounding()))
    assert len(tephigram_axes.figure.axes) == 2
    tephigram_axes.clear()
    assert len(tephigram_axes.figure.axes) == 1
    assert tephigram_axes.get_axes_locator() is None


def test_figure_clear_with_a_side_panel(tephigram_axes):
    """The figure deletes the panel itself: the diagram must not race it."""
    fig = tephigram_axes.figure
    tephigram_axes.annotate_indices(calc.indices(_capped_sounding()))
    fig.canvas.draw()
    fig.clear()
    assert fig.axes == []
    assert tephigram_axes._indices_panel is None
    assert tephigram_axes._side_divider is None


def test_figure_clear_is_reusable_after_a_side_panel(tephigram_axes):
    """A cleared figure takes a fresh diagram and panel, and draws."""
    fig = tephigram_axes.figure
    tephigram_axes.annotate_indices(calc.indices(_capped_sounding()))
    fig.canvas.draw()
    fig.clear()
    axes = fig.add_subplot(projection="tephigram")
    panel = axes.annotate_indices(calc.indices(_capped_sounding()))
    fig.canvas.draw()
    assert panel in fig.axes
    assert len(fig.axes) == 2


def test_subfigure_clear_with_a_side_panel():
    """The clearing figure is the *enclosing* one, not the root of the tree."""
    fig = plt.figure()
    subfig = fig.subfigures()
    axes = subfig.add_subplot(projection="tephigram")
    try:
        panel = axes.annotate_indices(calc.indices(_capped_sounding()))
        assert panel in subfig.axes
        fig.canvas.draw()
        subfig.clear()
        assert subfig.axes == []
        assert axes._indices_panel is None
    finally:
        plt.close(fig)


def test_canonical_usage_composes(tephigram_axes):
    """The spec §4 sequence works end to end (minus barbs, a later plan)."""
    snd = _capped_sounding()
    tephigram_axes.plot_sounding(snd)
    parcel = calc.parcel_path(snd)
    tephigram_axes.plot_profile(parcel, color="k", linestyle="--")
    assert tephigram_axes.shade_cape(snd, parcel) is not None
    assert tephigram_axes.shade_cin(snd, parcel) is not None
    panel = tephigram_axes.annotate_indices(calc.indices(snd))
    assert panel in tephigram_axes.figure.axes
