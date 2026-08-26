# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the tephigram matplotlib projection (spec §3.1)."""

from __future__ import annotations

import dataclasses
import math

import matplotlib.colors as mcolors
from matplotlib.patches import PathPatch
from matplotlib.path import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoLocator
from metpy.units import units
import numpy as np
import pytest

from tephpy import Sounding, calc, samples, transforms
from tephpy._config import config
from tephpy._constants import (
    BARB_GUTTER_PAD,
    CAPE_COLOR,
    CIN_COLOR,
    CURSOR_FIELD_NAMES,
    DEFAULT_EXTENT,
    EDGE_AXIS_TITLES,
    EDGE_LABEL_GUTTER_PAD,
    INDICES_PANEL_ROWS,
    ISOBAR_COLOR,
    LABEL_FONTSIZE,
    PROFILE_DEWPOINT_COLOR,
    PROFILE_LINEWIDTH,
    PROFILE_TEMPERATURE_COLOR,
    PROFILE_ZORDER,
    SHADING_ALPHA,
    SHADING_ZORDER,
)
from tephpy.exceptions import MissingDataError, TephpyUnitsError, TephpyValidationError
from tephpy.plotting import axes
from tephpy.plotting.axes import TephigramAxes, TephigramTransform
from tephpy.plotting.isopleths import EDGES, IsoplethFamily


def test_the_cursor_registry_and_the_vocabulary_agree():
    """Two independently written tables, made to agree (domain spec §3.2).

    The formatter functions stay in ``plotting.axes``: two import MetPy
    function-locally so that ``import tephpy`` stays light, and every one
    formats a value for display — presentation, not the data ``_constants``
    holds. Only their names are the closed vocabulary the configuration
    loader must validate against, so only the names moved. So the registry
    stays here and the names live there, and this is what stops a sixth
    formatter being unreachable from a configuration file — or a sixth name
    being accepted by the loader and unformattable at the cursor.
    """
    assert set(axes._CURSOR_FORMATTERS) == set(CURSOR_FIELD_NAMES)


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


@pytest.fixture
def tephigram_axes_b():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    yield ax
    plt.close(fig)


@pytest.fixture
def sample_sounding():
    """Build the 17Z Norman ascent -- the one with CAPE (gallery spec §3.1)."""
    return samples.sounding("norman-17z")


@pytest.fixture
def sample_sounding_b():
    """Build the 12Z Norman ascent, a second sounding from the same station day."""
    return samples.sounding("norman-12z")


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
    """Map all four corners of an extent to expected x/y limits.

    Independent of ``axes._limits_from_ranges``: it computes the same four
    corners from scratch rather than calling the implementation under test,
    so a regression there (e.g. back to mapping only the two positionally
    paired corners) is still caught here (framing spec §1, §3.1).
    """
    p0, p1 = extent["pressure"]
    t0, t1 = extent["temperature"]
    pressures = np.array([p0, p0, p1, p1])
    temperatures = np.array([t0, t1, t0, t1])
    thetas = transforms.theta_from_pressure_temperature(pressures, temperatures)
    x, y = transforms.xy_from_temperature_theta(temperatures, thetas)
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
    extent = {"pressure": (1050.0, 700.0), "temperature": (-10.0, 30.0)}
    tephigram_axes.set_extent(**extent)
    (x0, x1), (y0, y1) = _expected_limits(extent)
    assert tephigram_axes.get_xlim() == pytest.approx((x0, x1))
    assert tephigram_axes.get_ylim() == pytest.approx((y0, y1))


def test_set_extent_disables_autoscale_so_overlays_do_not_drift(tephigram_axes):
    tephigram_axes.set_extent(**DEFAULT_EXTENT)
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
    with pytest.raises(ValueError, match="above 0 hPa"):
        tephigram_axes.set_extent(pressure=(0.0, 200.0), temperature=(-40.0, 40.0))
    with pytest.raises(ValueError, match="degenerate"):
        tephigram_axes.set_extent(pressure=(850.0, 850.0), temperature=(10.0, 10.0))


def test_set_extent_takes_keyword_ranges(tephigram_axes):
    """The view is named by a pressure range and a temperature range."""
    tephigram_axes.set_extent(pressure=(900.0, 200.0), temperature=(-65.0, 5.0))
    assert tephigram_axes.get_xlim() == pytest.approx((1545.51, 1831.40), abs=0.01)
    assert tephigram_axes.get_ylim() == pytest.approx((1675.51, 1821.40), abs=0.01)


def test_order_within_a_range_carries_no_meaning(tephigram_axes, tephigram_axes_b):
    """(a, b) and (b, a) name the same window (framing spec §3.1)."""
    tephigram_axes.set_extent(pressure=(900.0, 200.0), temperature=(-65.0, 5.0))
    tephigram_axes_b.set_extent(pressure=(200.0, 900.0), temperature=(5.0, -65.0))
    assert tephigram_axes.get_xlim() == tephigram_axes_b.get_xlim()
    assert tephigram_axes.get_ylim() == tephigram_axes_b.get_ylim()


def test_the_view_contains_the_whole_region_it_names(tephigram_axes):
    """Every corner of the named region falls inside the view.

    The defect this replaces mapped two corners and took the extremes,
    which is the bounding box of two *points* rather than of the region
    they delimit. Measured 2026-08-25, the old code placed
    (1000 hPa, -10 degC) and (900 hPa, 30 degC) outside the view that
    ``((1000, 30), (900, -10))`` asked for -- half the named region
    (framing spec §1).
    """
    tephigram_axes.set_extent(pressure=(1000.0, 900.0), temperature=(30.0, -10.0))
    xlo, xhi = tephigram_axes.get_xlim()
    ylo, yhi = tephigram_axes.get_ylim()
    for p in (1000.0, 900.0):
        for t in (30.0, -10.0):
            theta = transforms.theta_from_pressure_temperature(
                np.array([p]), np.array([t])
            )
            x, y = transforms.xy_from_temperature_theta(np.array([t]), theta)
            assert xlo <= float(x[0]) <= xhi, f"({p}, {t}) outside x"
            assert ylo <= float(y[0]) <= yhi, f"({p}, {t}) outside y"


def test_the_old_corner_call_is_now_unwritable(tephigram_axes):
    """The transposition of framing spec §1 cannot be expressed."""
    with pytest.raises(TypeError):
        tephigram_axes.set_extent(((900.0, -65.0), (200.0, 5.0)))


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"pressure": (0.0, 200.0), "temperature": (-65.0, 5.0)}, "pressure"),
        ({"pressure": (-5.0, 200.0), "temperature": (-65.0, 5.0)}, "pressure"),
        ({"pressure": (float("nan"), 200.0), "temperature": (-65.0, 5.0)}, "pressure"),
        ({"pressure": (900.0, 900.0), "temperature": (-65.0, 5.0)}, "pressure"),
        (
            {"pressure": (900.0, 200.0), "temperature": (float("inf"), 5.0)},
            "temperature",
        ),
        ({"pressure": (900.0, 200.0), "temperature": (5.0, 5.0)}, "temperature"),
    ],
)
def test_an_unusable_range_is_refused_by_name(tephigram_axes, kwargs, expected):
    """The message names the offending keyword, not a nested tuple."""
    with pytest.raises(ValueError, match=expected):
        tephigram_axes.set_extent(**kwargs)


def test_set_extent_disables_autoscaling(tephigram_axes):
    """A caller who fixed a window meant it (framing spec §3.5)."""
    tephigram_axes.set_extent(pressure=(900.0, 200.0), temperature=(-65.0, 5.0))
    assert tephigram_axes.get_autoscale_on() is False


# --- fit (framing spec §3.2, §3.3, §3.5) -----------------------------------


def test_fit_frames_one_sounding(tephigram_axes, sample_sounding):
    """Every finite datum falls inside the fitted view."""
    tephigram_axes.fit(sample_sounding, margin=0.0)
    xlo, xhi = tephigram_axes.get_xlim()
    ylo, yhi = tephigram_axes.get_ylim()
    p = sample_sounding.pressure.to("hPa").magnitude
    t = sample_sounding.temperature.to("degC").magnitude
    theta = transforms.theta_from_pressure_temperature(p, t)
    x, y = transforms.xy_from_temperature_theta(t, theta)
    assert xlo <= float(np.nanmin(x))
    assert float(np.nanmax(x)) <= xhi
    assert ylo <= float(np.nanmin(y))
    assert float(np.nanmax(y)) <= yhi


def test_fit_without_the_parcel_clips_the_path_it_is_read_against(
    tephigram_axes, tephigram_axes_b, sample_sounding
):
    """The defect ``fit`` exists to prevent (framing spec §3.2).

    A parcel is warmer than its environment through the CAPE region, so
    fitting the sounding alone can clip the very path the parcel analysis
    is drawn to show. Passing the parcel is what dissolves it.
    """
    parcel = calc.parcel_path(sample_sounding)
    tephigram_axes.fit(sample_sounding, margin=0.0)
    tephigram_axes_b.fit(sample_sounding, parcel, margin=0.0)
    without = tephigram_axes.get_xlim()
    with_parcel = tephigram_axes_b.get_xlim()
    assert with_parcel[1] > without[1] or with_parcel[0] < without[0]


def test_fit_takes_several_soundings(
    tephigram_axes, sample_sounding, sample_sounding_b
):
    """A station's day, framed alike."""
    tephigram_axes.fit(sample_sounding, sample_sounding_b, margin=0.0)
    xlo, xhi = tephigram_axes.get_xlim()
    for snd in (sample_sounding, sample_sounding_b):
        p = snd.pressure.to("hPa").magnitude
        t = snd.temperature.to("degC").magnitude
        theta = transforms.theta_from_pressure_temperature(p, t)
        x, _ = transforms.xy_from_temperature_theta(t, theta)
        assert xlo <= float(np.nanmin(x))
        assert float(np.nanmax(x)) <= xhi


def test_a_nan_dewpoint_bounds_nothing_and_poisons_nothing(
    tephigram_axes, sample_sounding
):
    """NaN gaps are data everywhere except pressure (spec §3.4)."""
    dewpoint = sample_sounding.dewpoint.magnitude.copy()
    dewpoint[1] = float("nan")
    gapped = dataclasses.replace(
        sample_sounding,
        dewpoint=dewpoint * sample_sounding.dewpoint.units,
    )
    tephigram_axes.fit(gapped, margin=0.0)
    assert all(
        math.isfinite(v)
        for v in (*tephigram_axes.get_xlim(), *tephigram_axes.get_ylim())
    )


def test_fit_needs_something_to_frame(tephigram_axes):
    with pytest.raises(TephpyValidationError, match="at least one"):
        tephigram_axes.fit()


def test_fit_refuses_what_it_cannot_frame(tephigram_axes):
    with pytest.raises(TephpyValidationError, match="Sounding or Profile"):
        tephigram_axes.fit(object())


def test_margin_resolves_keyword_over_config_over_constant(
    tephigram_axes, tephigram_axes_b, sample_sounding
):
    """The resolution order every tunable here uses (framing spec §3.3)."""
    tephigram_axes.fit(sample_sounding, margin=0.0)
    tight = tephigram_axes.get_xlim()
    with config.context(diagram={"margin": 0.5}):
        tephigram_axes_b.fit(sample_sounding)
    loose = tephigram_axes_b.get_xlim()
    assert loose[1] - loose[0] > tight[1] - tight[0]


def test_fit_disables_autoscaling(tephigram_axes, sample_sounding):
    tephigram_axes.fit(sample_sounding)
    assert tephigram_axes.get_autoscale_on() is False


def test_a_pressure_clamp_sets_the_pressure_range(tephigram_axes, sample_sounding):
    """The clamp names the layer; temperature is fitted inside it."""
    tephigram_axes.fit(sample_sounding, pressure=(950.0, 300.0), margin=0.0)
    # Measured directly from the norman-17z sample_sounding fixture between
    # 950 and 300 hPa (temperature and dewpoint combined); not the brief's
    # (-58.7, 24.1), whose 24.1 turns out to be norman-12z's max in that
    # band rather than norman-17z's 22.8.
    (xlo, xhi), (ylo, yhi) = _expected_limits(
        {"pressure": (950.0, 300.0), "temperature": (-58.7, 22.8)}
    )
    assert tephigram_axes.get_xlim() == pytest.approx((xlo, xhi), abs=0.5)
    assert tephigram_axes.get_ylim() == pytest.approx((ylo, yhi), abs=0.5)


def test_a_pressure_clamp_narrows_the_view(
    tephigram_axes, tephigram_axes_b, sample_sounding
):
    """The defect this parameter exists to fix (framing spec §3.2).

    A radiosonde ascent does not stop at the tropopause; the shipped
    samples reach about 10 hPa. Framing all of that gives a view whose
    span is dominated by the stratosphere.
    """
    tephigram_axes.fit(sample_sounding, margin=0.0)
    tephigram_axes_b.fit(sample_sounding, pressure=(950.0, 300.0), margin=0.0)
    unclamped = tephigram_axes.get_xlim()
    clamped = tephigram_axes_b.get_xlim()
    assert (clamped[1] - clamped[0]) < 0.6 * (unclamped[1] - unclamped[0])


def test_a_clamp_excludes_data_outside_it(
    tephigram_axes, tephigram_axes_b, sample_sounding
):
    """Levels outside the band do not bound the view."""
    tephigram_axes.fit(sample_sounding, pressure=(950.0, 300.0), margin=0.0)
    narrow = tephigram_axes.get_ylim()
    tephigram_axes_b.fit(sample_sounding, pressure=(950.0, 100.0), margin=0.0)
    wide = tephigram_axes_b.get_ylim()
    assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])


def test_a_clamp_order_carries_no_meaning(
    tephigram_axes, tephigram_axes_b, sample_sounding
):
    tephigram_axes.fit(sample_sounding, pressure=(950.0, 300.0), margin=0.0)
    tephigram_axes_b.fit(sample_sounding, pressure=(300.0, 950.0), margin=0.0)
    assert tephigram_axes.get_xlim() == tephigram_axes_b.get_xlim()
    assert tephigram_axes.get_ylim() == tephigram_axes_b.get_ylim()


def test_a_clamp_containing_no_data_raises(tephigram_axes, sample_sounding):
    with pytest.raises(MissingDataError, match="no finite data"):
        tephigram_axes.fit(sample_sounding, pressure=(5.0, 1.0))


def test_an_unusable_clamp_is_refused(tephigram_axes, sample_sounding):
    with pytest.raises(ValueError, match="pressure"):
        tephigram_axes.fit(sample_sounding, pressure=(0.0, 300.0))


def test_a_clamp_masks_each_object_by_its_own_levels(
    tephigram_axes, sample_sounding, sample_sounding_b
):
    """The two samples have different level counts (framing spec §3.2).

    Pins correct per-object masking. The most literal way to get this
    wrong -- a mask built once and reused across both objects -- would
    raise ``IndexError`` here rather than pass quietly, since the two
    samples' level counts (71 and 68) differ. What this guards against is
    a subtler regression that stays index-valid, such as truncating every
    object's temperature array to the shorter object's length before
    masking.
    """
    band = (950.0, 300.0)
    tephigram_axes.fit(sample_sounding, sample_sounding_b, pressure=band, margin=0.0)
    both = tephigram_axes.get_ylim()

    lo, hi = sorted(band)
    expected_lo, expected_hi = math.inf, -math.inf
    for snd in (sample_sounding, sample_sounding_b):
        levels = snd.pressure.to("hPa").magnitude
        inside = (levels >= lo) & (levels <= hi)
        for field in (snd.temperature, snd.dewpoint):
            if field is None:
                continue
            values = field.to("degC").magnitude[inside]
            values = values[np.isfinite(values)]
            if values.size:
                expected_lo = min(expected_lo, float(values.min()))
                expected_hi = max(expected_hi, float(values.max()))

    (_, _), (ylo, yhi) = _expected_limits(
        {"pressure": band, "temperature": (expected_lo, expected_hi)}
    )
    assert both == pytest.approx((ylo, yhi), abs=0.5)


def test_an_argument_with_no_finite_data_raises_naming_it(
    tephigram_axes, sample_sounding
):
    """Per-argument, before any clamp (framing spec §3.2).

    An argument carrying no finite data at all is a caller error distinct
    from data that merely falls outside a clamp -- checked here with no
    ``pressure=`` in play at all, so the clamp cannot be what triggers it.
    """
    nan_temperature = np.full_like(sample_sounding.temperature.magnitude, float("nan"))
    empty = dataclasses.replace(
        sample_sounding,
        temperature=nan_temperature * sample_sounding.temperature.units,
        dewpoint=None,
    )
    with pytest.raises(MissingDataError, match="argument 2"):
        tephigram_axes.fit(sample_sounding, empty)


def test_an_argument_entirely_outside_the_clamp_contributes_nothing(
    tephigram_axes, tephigram_axes_b, sample_sounding
):
    """The defect ``fit`` exists to prevent, from the other side (framing spec §3.2).

    Finite data that simply falls outside the ``pressure=`` clamp is not a
    caller error: a stratospheric profile passed alongside a
    tropospheric sounding contributes nothing to a lower-troposphere
    frame, silently, and the frame is identical to fitting the sounding
    alone.
    """
    stratospheric = calc.Profile(
        [150.0, 100.0],
        [-60.0, -70.0],
        125.0,
        -65.0,
        units={
            "pressure": "hPa",
            "temperature": "degC",
            "lcl_pressure": "hPa",
            "lcl_temperature": "degC",
        },
    )
    band = (950.0, 300.0)
    tephigram_axes.fit(sample_sounding, pressure=band, margin=0.0)
    tephigram_axes_b.fit(sample_sounding, stratospheric, pressure=band, margin=0.0)
    assert tephigram_axes.get_xlim() == tephigram_axes_b.get_xlim()
    assert tephigram_axes.get_ylim() == tephigram_axes_b.get_ylim()


def test_fit_raises_when_nothing_survives_the_clamp_across_every_argument(
    tephigram_axes, sample_sounding, sample_sounding_b
):
    """The aggregate check still holds with several arguments (framing spec §3.2).

    Both soundings carry finite data -- neither is the per-argument
    caller error of the test above -- but a clamp outside every level of
    both still leaves nothing to frame.
    """
    with pytest.raises(MissingDataError, match="no finite data"):
        tephigram_axes.fit(sample_sounding, sample_sounding_b, pressure=(5.0, 1.0))


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
    """config.cursor.fields reorders/selects, live on an existing axes (spec §3.5)."""
    x, y = _cursor_xy(850.0, -4.2)
    with config.context(cursor={"fields": ("theta", "pressure")}):
        assert tephigram_axes.format_coord(x, y) == "θ 8.6 °C, 850 hPa"
    assert tephigram_axes.format_coord(x, y) == "850 hPa, -4.2 °C, θ 8.6 °C"


def test_format_coord_out_of_domain_blank(tephigram_axes):
    """Left of the -273.15 °C isotherm the pressure is NaN: blank readout."""
    assert tephigram_axes.format_coord(-300.0, 300.0) == ""


def test_format_coord_instance_assignment_wins(tephigram_axes):
    """Stock matplotlib full-custom path: assignment shadows the method (spec §3.2)."""

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


def test_format_coord_supersaturated_skips_metpy_fields(tephigram_axes):
    """Supersaturated points omit undefined fields, not render nan (spec §3.2).

    At ~1000 hPa / 120 °C, saturation vapour pressure exceeds total pressure,
    making mixing_ratio and theta_w mathematically undefined.  The readout
    must omit those fields rather than showing nan and must not emit any
    warning (filterwarnings=error enforces this).
    """
    x, y = _cursor_xy(1000.0, 120.0)
    with config.context(
        cursor={"fields": ("pressure", "temperature", "mixing_ratio", "theta_w")}
    ):
        result = tephigram_axes.format_coord(x, y)
    assert result == "1000 hPa, 120.0 °C"


def test_format_coord_bare_string_fields_raises(tephigram_axes):
    """A bare-string cursor fields value raises a clear TypeError (spec §3.2)."""
    x, y = _cursor_xy(850.0, -4.2)
    with (
        config.context(cursor={"fields": "pressure"}),
        pytest.raises(TypeError, match="cursor fields must be a tuple"),
    ):
        tephigram_axes.format_coord(x, y)


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
    extent = {"pressure": (1000.0, 500.0), "temperature": (-20.0, 20.0)}
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


# --- Edge ownership (spec §3.2) -------------------------------------------


def _ticks(axis):
    """Return the rendered tick label strings of an axis."""
    return [text.get_text() for text in axis.get_ticklabels()]


def test_no_edge_is_claimed_by_default():
    """Today's default stands: hidden native axes, no secondary axes."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        assert ax._edge_owners == {}
        assert ax.child_axes == []
        assert not ax.xaxis.get_visible()
        assert not ax.yaxis.get_visible()
    finally:
        plt.close(fig)


def test_isobars_claim_bottom_and_left():
    """The printed chart's pressure scale, from one call (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels=("bottom", "left"))
        fig.canvas.draw()
        assert ax._edge_owners == {"bottom": "isobars", "left": "isobars"}
        assert ax.xaxis.get_visible()
        assert _ticks(ax.xaxis) == ["900", "950", "1000", "1050"]
        assert _ticks(ax.yaxis)[:2] == ["200", "250"]
        assert len(_ticks(ax.yaxis)) == 14
        assert ax.get_xlabel() == EDGE_AXIS_TITLES["isobars"]
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
    finally:
        plt.close(fig)


def test_a_user_axis_title_wins_either_way():
    """The convention title only fills an empty axis label (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.set_xlabel("Mine")
        ax.isobars(labels="bottom")
        assert ax.get_xlabel() == "Mine"
        ax.set_xlabel("Still mine")
        ax.isobars(labels=True)
        assert ax.get_xlabel() == "Still mine"
        # Third leg: auto title applied → user replaces it → release must not
        # clear the user's replacement.  A weakened guard (`if title is not
        # None:` without `== title`) would clear the user's text here.
        ax.isobars(labels="left")
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
        ax.set_ylabel("User's ylabel")
        ax.isobars(labels=True)
        assert ax.get_ylabel() == "User's ylabel"
    finally:
        plt.close(fig)


def test_top_and_right_use_lazily_created_secondary_axes():
    """Claiming creates one child axes; releasing hides it; clear reaps (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        assert len(ax.child_axes) == 1
        assert _ticks(ax._secondary_axes["top"].xaxis) == [
            "0.05",
            "0.2",
            "1",
            "2",
            "4",
            "7",
            "14",
            "28",
        ]
        ax.mixing_ratios(labels=True)
        fig.canvas.draw()
        assert len(ax.child_axes) == 1
        assert not ax.child_axes[0].get_visible()
        assert set(ax._secondary_axes) == {"top"}
        # `clear` is the reset: it drops the cache, and matplotlib reaps the
        # child axes with it, so a hidden secondary cannot outlive a clear.
        ax.clear()
        assert ax.child_axes == []
        assert ax._secondary_axes == {}
    finally:
        plt.close(fig)


def test_a_family_can_move_its_own_edge():
    """Top to right in one resolve: a release and a claim in the same sync.

    One of the two transitions that release one secondary axes and build
    another inside a single ``_sync_edge_labels``; the ``right`` to ``top``
    mirror is ``test_a_family_can_move_its_own_edge_the_other_way``, which
    claims before it releases because ``EDGES`` visits ``top`` first.
    The released edge must come away fully unclaimed — hidden, untitled and
    back on matplotlib's linear-axis defaults — while the claimed edge comes
    up ticked and titled (spec §3.2).
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="top")
        fig.canvas.draw()
        top = ax.edge_axis("top")
        assert _ticks(top) == ["150"]
        ax.isobars(labels="right")
        fig.canvas.draw()
        assert ax._edge_owners == {"right": "isobars"}
        # The top secondary hides rather than being destroyed, so the handle
        # taken before the move is still the live axis afterwards.
        assert ax._secondary_axes["top"].xaxis is top
        assert not ax._secondary_axes["top"].get_visible()
        assert top.get_label_text() == ""
        # Not just hidden: the locator goes back to matplotlib's default, so
        # the released edge no longer holds the family through an
        # ``_EdgeLocator``.
        assert isinstance(top.get_major_locator(), AutoLocator)
        right = ax.edge_axis("right")
        assert ax._secondary_axes["right"].get_visible()
        assert right.get_label_text() == EDGE_AXIS_TITLES["isobars"]
        assert _ticks(right) == [str(hpa) for hpa in range(200, 750, 50)]
        assert ax._edge_titles == {"right": EDGE_AXIS_TITLES["isobars"]}
        assert len(ax.child_axes) == 2
    finally:
        plt.close(fig)


def test_a_family_can_move_its_own_edge_the_other_way():
    """The mirror of ``test_a_family_can_move_its_own_edge``: right to top.

    The harder ordering of the two. ``_sync_edge_labels`` releases per edge
    from inside its ``EDGES`` loop, which visits ``top`` before ``right``, so
    this direction *claims* the new edge and only then releases the old one —
    and for the rest of that loop ``_edge_owners`` transiently holds both
    edges for the same family, which the forward direction never does. The
    outcome must be the same either way: one edge fully unclaimed, the other
    ticked and titled (spec §3.2).
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="right")
        fig.canvas.draw()
        right = ax.edge_axis("right")
        assert _ticks(right) == [str(hpa) for hpa in range(200, 750, 50)]
        ax.isobars(labels="top")
        fig.canvas.draw()
        # The transient is gone by the time the sync returns: one owner, on
        # the edge just claimed.
        assert ax._edge_owners == {"top": "isobars"}
        # The right secondary hides rather than being destroyed, so the handle
        # taken before the move is still the live axis afterwards.
        assert ax._secondary_axes["right"].yaxis is right
        assert not ax._secondary_axes["right"].get_visible()
        assert right.get_label_text() == ""
        # Not just hidden: the locator goes back to matplotlib's default, so
        # the released edge no longer holds the family through an
        # ``_EdgeLocator``.
        assert isinstance(right.get_major_locator(), AutoLocator)
        top = ax.edge_axis("top")
        assert ax._secondary_axes["top"].get_visible()
        assert top.get_label_text() == EDGE_AXIS_TITLES["isobars"]
        assert _ticks(top) == ["150"]
        assert ax._edge_titles == {"top": EDGE_AXIS_TITLES["isobars"]}
        assert len(ax.child_axes) == 2
    finally:
        plt.close(fig)


def test_one_family_per_edge():
    """Two claimants raise, naming both and the edge (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        with pytest.raises(TypeError, match=r"'left'.*'isobars'.*'isotherms'"):
            ax.isotherms(labels=("bottom", "left"))
        assert ax._edge_owners == {"left": "isobars"}
        assert ax.isotherms().options.label_edges == ()
    finally:
        plt.close(fig)


def test_a_config_conflict_surfaces_at_axes_creation():
    """Not at first draw: the axes funnels the creation path too."""
    fig = plt.figure()
    try:
        with (
            config.context(
                isotherms={"labels": "bottom"}, isobars={"labels": "bottom"}
            ),
            pytest.raises(TypeError, match="'bottom'"),
        ):
            fig.add_subplot(projection="tephigram")
    finally:
        plt.close(fig)


def test_unknown_placement_is_rejected():
    """Fail loud, naming the placement and the valid set (spec §6)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        with pytest.raises(TypeError, match=r"label placement 'middle'"):
            ax.isobars(labels="middle")
        assert ax._edge_owners == {}
    finally:
        plt.close(fig)


def test_family_alpha_reaches_both_label_routes():
    """``alpha`` is documented for lines *and* labels, inline or on an edge.

    ``set_tick_params`` takes no alpha, so the edge ticks carry it in their
    RGBA; the two routes must still agree.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left", alpha=0.4)
        ax.isotherms(alpha=0.4)
        fig.canvas.draw()
        # A member with fewer than two in-view vertices is skipped before its
        # pooled Text is placed, so only the rendered labels carry the style.
        placed = [text for text in ax._families["isotherms"]._texts if text.get_text()]
        assert len(placed) > 1
        assert all(text.get_alpha() == pytest.approx(0.4) for text in placed)
        expected = mcolors.to_rgba(ISOBAR_COLOR, 0.4)
        assert mcolors.to_rgba(ax.yaxis.get_ticklabels()[0].get_color()) == (
            pytest.approx(expected)
        )
        assert mcolors.to_rgba(ax.yaxis.get_ticklines()[0].get_color()) == (
            pytest.approx(expected)
        )
    finally:
        plt.close(fig)


def test_an_invisible_family_releases_its_edge():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        assert ax._edge_owners == {"left": "isobars"}
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
        ax.isobars(visible=False)
        assert ax._edge_owners == {}
        assert not ax.yaxis.get_visible()
        # Release clears the auto-title it set (spec §3.2).  That it clears
        # *only* its own title and never a user's is a separate clause, and
        # is pinned by the third leg of
        # ``test_a_user_axis_title_wins_either_way`` — not by this assertion,
        # which passes either way.
        assert ax.get_ylabel() == ""
        ax.isotherms(labels="left")
        assert ax._edge_owners == {"left": "isotherms"}
    finally:
        plt.close(fig)


def test_clear_drops_every_edge_claim():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels=("bottom", "left"))
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        ax.clear()
        fig.canvas.draw()
        assert ax._edge_owners == {}
        assert ax._secondary_axes == {}
        assert ax.child_axes == []
        assert not ax.xaxis.get_visible()
        assert ax.get_xlabel() == ""
    finally:
        plt.close(fig)


def _barb_sounding():
    """Return a minimal sounding carrying wind, for a barb gutter."""
    return Sounding(
        pressure=np.array([1000.0, 900.0, 800.0]) * units.hPa,
        temperature=np.array([20.0, 14.0, 8.0]) * units.degC,
        wind_speed=np.array([10.0, 20.0, 30.0]) * units.knots,
        wind_direction=np.array([180.0, 200.0, 220.0]) * units.deg,
    )


def _gutter_pad(ax):
    """Return the gap in pixels between the diagram and the barb gutter."""
    return ax._barb_gutter.get_window_extent().x0 - ax.get_window_extent().x1


def test_right_edge_labels_widen_the_gutter_pad():
    """The relayout helper substitutes the wider pad (spec §3.2)."""
    snd = _barb_sounding()
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.plot_barbs(snd)
        fig.canvas.draw()
        narrow = _gutter_pad(ax)
        # Pinned, not merely ordered.  The load-bearing half of this test is
        # that an unclaimed right edge leaves the layout exactly as it was
        # before edges could be labelled at all; an inequality against
        # ``wide`` would still pass if the unlabelled pad drifted.
        assert narrow == pytest.approx(BARB_GUTTER_PAD * fig.dpi, abs=1.0)
        ax.isobars(labels="right")
        fig.canvas.draw()
        wide = _gutter_pad(ax)
        assert wide == pytest.approx(EDGE_LABEL_GUTTER_PAD * fig.dpi, abs=1.0)
        assert wide > narrow
    finally:
        plt.close(fig)


@pytest.mark.parametrize(
    ("labels", "expected_owners"),
    [("top", {"top": "isobars"}), (False, {})],
    ids=["moved-to-top", "dropped"],
)
def test_releasing_the_right_edge_narrows_the_gutter_pad_back(labels, expected_owners):
    """``_relayout_side_panels`` runs on the release flip too (spec §3.2).

    ``_sync_edge_labels`` relayouts whenever ``had_right`` changes in
    *either* direction, and the widening half is pinned by
    ``test_right_edge_labels_widen_the_gutter_pad``. Both routes here give
    the right edge up, but reach the relayout by different paths through the
    ``EDGES`` loop: moving the claim to ``top`` claims before it releases,
    while dropping labels altogether claims nothing at all. Either way the
    pad must come back to ``BARB_GUTTER_PAD`` exactly, not merely narrow.

    ``labels=False`` is the drop, not ``labels=None``: an accessor reads
    ``None`` as "not passed" and never reconfigures the family at all.
    """
    snd = _barb_sounding()
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.plot_barbs(snd)
        ax.isobars(labels="right")
        fig.canvas.draw()
        assert _gutter_pad(ax) == pytest.approx(
            EDGE_LABEL_GUTTER_PAD * fig.dpi, abs=1.0
        )
        ax.isobars(labels=labels)
        fig.canvas.draw()
        assert ax._edge_owners == expected_owners
        assert _gutter_pad(ax) == pytest.approx(BARB_GUTTER_PAD * fig.dpi, abs=1.0)
    finally:
        plt.close(fig)


def test_a_no_op_labels_argument_leaves_the_gutter_pad_alone():
    """``labels=None`` means "not passed" on an accessor, so nothing moves.

    The accessors drop ``None`` kwargs before reaching
    ``IsoplethFamily.configure`` (spec §3.5), so this cannot be the route
    that gives an edge up — a claimed right edge, and the widened pad that
    goes with it, both survive the call untouched. Passing ``None`` straight
    to ``configure`` *does* release, by removing the override so ``labels``
    falls back through the tiers; that tier behaviour belongs to
    ``test_configure_none_resets_override`` in
    ``tests/plotting/test_isopleths.py``, not to this module.
    """
    snd = _barb_sounding()
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.plot_barbs(snd)
        ax.isobars(labels="right")
        fig.canvas.draw()
        ax.isobars(labels=None)
        fig.canvas.draw()
        assert ax._edge_owners == {"right": "isobars"}
        assert _gutter_pad(ax) == pytest.approx(
            EDGE_LABEL_GUTTER_PAD * fig.dpi, abs=1.0
        )
    finally:
        plt.close(fig)


def test_edge_ticks_follow_set_extent():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        fig.canvas.draw()
        wide = _ticks(ax.yaxis)
        ax.set_extent(pressure=(900.0, 500.0), temperature=(-10.0, 20.0))
        fig.canvas.draw()
        zoomed = _ticks(ax.yaxis)
        assert zoomed != wide
        # The left edge is a vertical line in (x, y) tephigram data space, not
        # a constant-pressure line.  At the top-left corner (P=500, T=-10) the
        # left edge sweeps down to ~457 hPa, so isobars in the 460-480 hPa band
        # genuinely cross it; a naive 500-900 hPa guard would be wrong.
        assert zoomed == [str(v) for v in range(460, 900, 20)]
    finally:
        plt.close(fig)


def test_every_edge_can_be_claimed_at_once():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels=("bottom", "left"))
        ax.mixing_ratios(labels="top")
        ax.isotherms(labels="right")
        fig.canvas.draw()
        assert set(ax._edge_owners) == set(EDGES)
        assert len(ax.child_axes) == 2
    finally:
        plt.close(fig)


def test_family_configure_claims_and_releases_an_edge():
    """The family's own ``configure`` reaches the ownership layer too.

    ``IsoplethFamily.configure`` is public and is what every accessor
    returns, so a claim made through it must light up the edge exactly as
    ``ax.isobars(labels=...)`` does — and dropping the claim must put the
    inline labels back without leaving the edge ticked (spec §3.2).
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        family = ax.isobars()
        family.configure(labels="left")
        fig.canvas.draw()
        assert ax._edge_owners == {"left": "isobars"}
        assert ax.yaxis.get_visible()
        assert _ticks(ax.yaxis)[:2] == ["200", "250"]
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
        selected = family._selected_members()
        assert len(family._inline_members(ax.viewLim, selected)) == 5
        family.configure(labels=True)
        fig.canvas.draw()
        assert ax._edge_owners == {}
        assert not ax.yaxis.get_visible()
        assert ax.get_ylabel() == ""
        assert family._inline_members(ax.viewLim, selected) == selected
    finally:
        plt.close(fig)


def test_claiming_an_edge_gives_up_the_inline_label_artists():
    """A claim shrinks the pool, it does not just stop drawing from it.

    The edge takes over the members that reach it, so the inline remainder
    collapses (spec §3.2) — and the ``Text`` artists for the members the
    edge now labels are the family's to release. They are never drawn
    again, but they still carry a figure reference, so a pool that only
    ever grows pins them for the life of the axes.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        family = ax.isobars()
        fig.canvas.draw()
        inline = len(family._inline_members(ax.viewLim, family._selected_members()))
        assert len(family._texts) == inline
        family.configure(labels="left")
        fig.canvas.draw()
        claimed = len(family._inline_members(ax.viewLim, family._selected_members()))
        assert claimed < inline
        assert len(family._texts) == claimed
    finally:
        plt.close(fig)


def test_set_visible_releases_and_reclaims_an_edge():
    """``Artist.set_visible`` is a resolve too: hiding drops the edge.

    An invisible family draws nothing, so it holds no edge (spec §3.2) —
    unconditionally, not only for the ``visible`` accessor option.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        family = ax.isobars(labels="left")
        fig.canvas.draw()
        family.set_visible(False)
        fig.canvas.draw()
        assert ax._edge_owners == {}
        assert not ax.yaxis.get_visible()
        assert ax.get_ylabel() == ""
        assert _ticks(ax.yaxis)[:2] != ["200", "250"]
        family.set_visible(True)
        fig.canvas.draw()
        assert ax._edge_owners == {"left": "isobars"}
        assert ax.yaxis.get_visible()
        assert _ticks(ax.yaxis)[:2] == ["200", "250"]
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
    finally:
        plt.close(fig)


def test_a_claimed_edge_draws_no_gridlines():
    """Constant-x gridlines mean nothing on a tephigram (spec §3.2).

    ``rcParams["axes.grid"]`` is set by several common styles, and the
    native axes are hidden precisely because their scale is meaningless;
    claiming an edge must not smuggle that scale back in as gridlines.
    Suppression happens once, when the edge axis is created, which is after
    ``Axes.clear`` reads the rcParam — so a style still cannot smuggle them
    in, and an explicit ``ax.grid(True)`` is honoured (spec §3.2).
    """
    with plt.rc_context({"axes.grid": True}):
        fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
        try:
            ax.isobars(labels="bottom")
            fig.canvas.draw()
            assert ax.xaxis.get_visible()
            assert ax.xaxis.get_gridlines()
            assert not any(line.get_visible() for line in ax.xaxis.get_gridlines())
            # Presentation is the user's after the claim: an explicit
            # ``ax.grid(True)`` is honoured, and an unrelated family's
            # resolve no longer wipes it (spec §3.2).
            ax.grid(visible=True)
            ax.isotherms(color="grey")
            fig.canvas.draw()
            gridlines = ax.xaxis.get_gridlines()
            assert gridlines
            assert all(line.get_visible() for line in gridlines)
        finally:
            plt.close(fig)


def test_user_tick_styling_survives_an_unrelated_family_resolve():
    """Presentation is the user's once the edge is claimed (spec §3.2).

    The first implementation re-asserted ``LABEL_FONTSIZE`` and the tick
    length and pad on every sync, so an *unrelated* family's resolve
    silently reverted a user's ``tick_params``.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        ax.tick_params(axis="y", labelsize=14)
        fig.canvas.draw()
        assert {t.label1.get_fontsize() for t in ax.yaxis.get_major_ticks()} == {14.0}
        ax.isotherms(color="grey")
        fig.canvas.draw()
        assert {t.label1.get_fontsize() for t in ax.yaxis.get_major_ticks()} == {14.0}
        # Nor may the owning family's own restyle revert it.
        ax.isobars(linewidth=2.0)
        fig.canvas.draw()
        assert {t.label1.get_fontsize() for t in ax.yaxis.get_major_ticks()} == {14.0}
    finally:
        plt.close(fig)


def test_clear_restores_the_edge_tick_conventions():
    """``ax.clear()`` is the reset for edge tick presentation (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        ax.tick_params(axis="y", labelsize=14)
        fig.canvas.draw()
        ax.clear()
        ax.isobars(labels="left")
        fig.canvas.draw()
        sizes = {t.label1.get_fontsize() for t in ax.yaxis.get_major_ticks()}
        assert sizes == {LABEL_FONTSIZE}
    finally:
        plt.close(fig)


def test_config_top_claim_takes_effect_at_axes_creation():
    """A config-driven edge claim via the top secondary axis works end-to-end.

    This is the only path that builds a secondary axes from inside
    ``Axes.__init__`` → ``clear``; it verifies the claim is live
    immediately without a separate configure call.
    """
    with config.context(mixing_ratios={"labels": "top"}):
        fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        assert ax._edge_owners["top"] == "mixing_ratios"
        assert "top" in ax._secondary_axes
        assert len(ax.child_axes) == 1
        fig.canvas.draw()
    finally:
        plt.close(fig)


def test_only_a_new_owner_re_points_an_edge():
    """A sync that changes nothing touches nothing (spec §3.2).

    ``_EdgeLocator`` holds a live family reference and recomputes on every
    draw, so re-installing it on each sync is not only wasted work — it is
    the pattern that made unrelated resolves reach into a claimed edge.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        locator = ax.yaxis.get_major_locator()
        ax.isotherms(color="grey")
        ax.isobars(linewidth=2.0)
        assert ax.yaxis.get_major_locator() is locator
        ax.isobars(labels=False)
        ax.isotherms(labels="left")
        assert ax.yaxis.get_major_locator() is not locator
    finally:
        plt.close(fig)


def test_tick_colour_tracks_its_own_family_only():
    """Restyling the owning family restyles its ticks; nothing else does."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        ax.tick_params(axis="y", labelcolor="black")
        fig.canvas.draw()
        black = mcolors.to_rgba("black")
        assert mcolors.to_rgba(
            ax.yaxis.get_ticklabels()[0].get_color()
        ) == pytest.approx(black)
        # An unrelated family, and a non-colour restyle of the owner, leave it.
        ax.isotherms(color="grey")
        ax.isobars(linewidth=2.0)
        fig.canvas.draw()
        assert mcolors.to_rgba(
            ax.yaxis.get_ticklabels()[0].get_color()
        ) == pytest.approx(black)
        # The owner's own colour still reaches its ticks.
        ax.isobars(color="blue")
        fig.canvas.draw()
        assert mcolors.to_rgba(
            ax.yaxis.get_ticklabels()[0].get_color()
        ) == pytest.approx(mcolors.to_rgba("blue"))
    finally:
        plt.close(fig)


def test_a_new_owner_restamps_the_edge_tick_colour():
    """A new owner's colour lands even when it matches the last one's.

    The RGBA memory survives release, so keying it by colour alone would
    suppress this claim and strand the ticks in the user's colour — tied to
    a family that no longer owns the edge (spec §3.2).
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left", color="blue", alpha=1.0)
        fig.canvas.draw()
        ax.edge_axis("left").set_tick_params(color="red", labelcolor="red")
        fig.canvas.draw()
        assert mcolors.to_rgba(
            ax.yaxis.get_ticklabels()[0].get_color()
        ) == pytest.approx(mcolors.to_rgba("red"))
        ax.isobars(labels=False)
        ax.isotherms(labels="left", color="blue", alpha=1.0)
        fig.canvas.draw()
        assert mcolors.to_rgba(
            ax.yaxis.get_ticklabels()[0].get_color()
        ) == pytest.approx(mcolors.to_rgba("blue"))
    finally:
        plt.close(fig)


def test_a_claim_restores_an_edge_axis_the_user_hid():
    """Visibility is identity, so a claim restores it on all four edges.

    Hiding the ``Axis`` alone leaves a top or right secondary axes visible,
    so restoring only the container would give the reclaimed edge no ticks
    while bottom and left came back (spec §3.2).
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.mixing_ratios(labels="top")
        ax.isobars(labels="left")
        fig.canvas.draw()
        ax.edge_axis("top").set_visible(False)
        ax.edge_axis("left").set_visible(False)
        ax.mixing_ratios(labels=False)
        ax.isobars(labels=False)
        ax.mixing_ratios(labels="top")
        ax.isobars(labels="left")
        fig.canvas.draw()
        assert ax.edge_axis("top").get_visible()
        assert ax._secondary_axes["top"].get_visible()
        assert ax.edge_axis("left").get_visible()
        assert _ticks(ax.edge_axis("top"))
        assert _ticks(ax.yaxis)
    finally:
        plt.close(fig)


def test_a_cleared_axis_title_stays_cleared():
    """``set_ylabel("")`` durably means "ticks, no title" (spec §3.2).

    The fill-when-empty guard runs only on a first claim, so no later sync
    looks at the label again; a genuine release forgets tephpy's own title,
    so a reclaim stamps afresh.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
        ax.set_ylabel("")
        ax.isotherms(color="grey")
        ax.isobars(color="blue")
        ax.set_extent(**DEFAULT_EXTENT)
        fig.canvas.draw()
        assert ax.get_ylabel() == ""
        # Dropping the labels and re-adding them is a fresh claim.
        ax.isobars(labels=False)
        ax.isobars(labels="left")
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
    finally:
        plt.close(fig)


def test_a_new_owner_restamps_the_axis_title():
    """Handing an edge to another family retitles it (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
        ax.isobars(labels=False)
        ax.isotherms(labels="left")
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isotherms"]
    finally:
        plt.close(fig)


def test_a_family_visibility_round_trip_preserves_edge_styling():
    """Toggling a family must not discard styling the user did not drop."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        ax.tick_params(axis="y", labelsize=14, labelcolor="black")
        fig.canvas.draw()
        ax.isobars(visible=False)
        ax.isobars(visible=True)
        fig.canvas.draw()
        assert {t.label1.get_fontsize() for t in ax.yaxis.get_major_ticks()} == {14.0}
        assert mcolors.to_rgba(
            ax.yaxis.get_ticklabels()[0].get_color()
        ) == pytest.approx(mcolors.to_rgba("black"))
    finally:
        plt.close(fig)


def test_a_released_secondary_axes_is_hidden_not_destroyed():
    """A held handle must stay live across a release and reclaim (spec §3.2).

    Destroying the secondary axes took its ticks and title with it, so top
    and right could not behave like bottom and left, which are merely
    hidden. An invisible secondary returns ``None`` from ``get_tightbbox``,
    so the persistence costs nothing in layout.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        secondary = ax._secondary_axes["top"]
        axis = secondary.xaxis
        assert len(ax.child_axes) == 1
        ax.mixing_ratios(labels=True)
        fig.canvas.draw()
        assert ax._secondary_axes["top"] is secondary
        assert not secondary.get_visible()
        assert secondary.get_tightbbox() is None
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        assert ax._secondary_axes["top"] is secondary
        assert secondary.xaxis is axis
        assert secondary.get_visible()
        assert _ticks(axis)
    finally:
        plt.close(fig)


def test_edge_axis_returns_each_edge_s_axis():
    """The uniform public handle on all four edges (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels=("bottom", "left"))
        ax.mixing_ratios(labels="top")
        ax.dry_adiabats(labels="right")
        fig.canvas.draw()
        assert ax.edge_axis("bottom") is ax.xaxis
        assert ax.edge_axis("left") is ax.yaxis
        assert ax.edge_axis("top") is ax._secondary_axes["top"].xaxis
        assert ax.edge_axis("right") is ax._secondary_axes["right"].yaxis
    finally:
        plt.close(fig)


def test_edge_axis_rejects_an_unknown_or_unclaimed_edge():
    """An unknown name is a TypeError; an unlabelled edge a ValueError."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        with pytest.raises(TypeError, match="unknown edge 'middle'"):
            ax.edge_axis("middle")
        with pytest.raises(ValueError, match="'top' edge carries no isopleth"):
            ax.edge_axis("top")
        # Probing must not have built a secondary axes nothing is using.
        assert ax._secondary_axes == {}
        assert ax.child_axes == []
    finally:
        plt.close(fig)


def test_edge_axis_styling_reaches_top_and_survives_a_reclaim():
    """Stock matplotlib styling now reaches top and right, and sticks."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        ax.edge_axis("top").set_tick_params(labelsize=12)
        ax.edge_axis("top").set_label_text("W")
        fig.canvas.draw()
        assert {
            t.label2.get_fontsize() for t in ax.edge_axis("top").get_major_ticks()
        } == {12.0}
        ax.mixing_ratios(labels=False)
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        assert ax.edge_axis("top").get_label_text() == "W"
        assert {
            t.label2.get_fontsize() for t in ax.edge_axis("top").get_major_ticks()
        } == {12.0}
    finally:
        plt.close(fig)


def test_accessor_emphasis_reaches_the_family(tephigram_axes):
    family = tephigram_axes.isotherms(emphasis={0.0: {"color": "tab:cyan"}})
    assert family.options.emphasis == {0.0: {"color": "tab:cyan"}}


def test_accessor_emphasis_available_on_every_family(tephigram_axes):
    """Every accessor takes ``emphasis``, and every documented example draws.

    Each family is emphasised at the value its own accessor docstring uses as
    the example, then the figure is drawn and the member is looked for in what
    was drawn. Configuring alone proves nothing: an example whose value warns
    (``filterwarnings = ["error"]``) or falls outside the family's domain, so
    it is built but never shown, is a failure here (spec §3.2).
    """
    examples = {
        "isotherms": 0.0,
        "isobars": 500.0,
        "dry_adiabats": 0.0,
        "moist_adiabats": 0.0,
        "mixing_ratios": 5.0,
    }
    families = {}
    for name, value in examples.items():
        family = getattr(tephigram_axes, name)(emphasis={value: {}})
        assert family.options.emphasis == {value: {}}
        families[name] = family
    tephigram_axes.figure.canvas.draw()
    for name, value in examples.items():
        drawn = [member.value for member in families[name]._selected_members()]
        assert any(np.isclose(drawn, value)), (
            f"{name} emphasis example {value} is documented but never drawn"
        )


def test_accessor_emphasis_error_propagates(tephigram_axes):
    with pytest.raises(TypeError, match="emphasis style key"):
        tephigram_axes.isotherms(emphasis={0.0: {"colour": "red"}})


def test_accessor_emphasis_empty_mapping_clears_config():
    """``ax.isotherms(emphasis={})`` opts one diagram out of a configured emphasis.

    Goes through the accessor rather than ``family.configure``: the accessor
    drops kwargs that are ``None``, not kwargs that are falsey, and an empty
    mapping has to survive that filter for the documented opt-out to work
    (spec §3.2).
    """
    with config.context(isotherms={"emphasis": {0.0: {}}}):
        fig = plt.figure()
        try:
            ax = fig.add_subplot(projection="tephigram")
            assert ax.isotherms().options.emphasis == {0.0: {}}
            assert ax.isotherms(emphasis={}).options.emphasis == {}
        finally:
            plt.close(fig)


def test_config_emphasis_type_error_surfaces_at_axes_creation():
    """A malformed config-tier emphasis fails loud when the axes is built."""
    fig = plt.figure()
    try:
        with (
            config.context(isotherms={"emphasis": {0.0: {"colour": "red"}}}),
            pytest.raises(TypeError, match=r"unknown 'isotherms' emphasis style key"),
        ):
            fig.add_subplot(projection="tephigram")
    finally:
        plt.close(fig)


@pytest.mark.parametrize(
    ("style", "match"),
    [
        ({"linewidth": -1.0}, r"'linewidth' for member 500 must be a positive"),
        ({"alpha": 1.5}, r"'alpha' for member 500 must be between 0 and 1"),
    ],
)
def test_config_emphasis_value_error_surfaces_at_axes_creation(style, match):
    """An out-of-range config-tier emphasis raises ``ValueError`` at creation.

    ``ValueError`` reaches the caller from ``TephigramAxes.clear``, which is
    both the ``Axes.__init__`` path and ``ax.clear()`` (spec §3.2).
    """
    fig = plt.figure()
    try:
        with (
            config.context(isobars={"emphasis": {500.0: style}}),
            pytest.raises(ValueError, match=match),
        ):
            fig.add_subplot(projection="tephigram")
    finally:
        plt.close(fig)


def test_emphasis_forced_member_reaches_the_edge_ticks(tephigram_axes):
    """A forced member is ticked like any other (spec §3.2)."""
    tephigram_axes.isotherms(labels="bottom", emphasis={-12.0: {}})
    tephigram_axes.figure.canvas.draw()
    labels = [text.get_text() for text in tephigram_axes.xaxis.get_ticklabels()]
    assert "-12" in labels
