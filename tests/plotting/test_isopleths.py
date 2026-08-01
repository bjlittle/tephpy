# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the isopleth geometry builders and family artist (spec §3.2/§7)."""

from __future__ import annotations

import math
import subprocess
import sys
import warnings

from hypothesis import given
from hypothesis import strategies as st
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from metpy.calc import saturation_mixing_ratio, wet_bulb_potential_temperature
from metpy.units import units
import numpy as np
import pytest

from tephpy import transforms
from tephpy._config import config
from tephpy._constants import (
    EMPHASIS_LINEWIDTH,
    ISOPLETH_ALPHA,
    ISOPLETH_LINEWIDTH,
    ISOPLETH_SAMPLES,
    ISOTHERM_COLOR,
    MIXING_RATIO_VALUES,
    MOIST_ADIABAT_TRUNCATION,
)
from tephpy.plotting import isopleths


def _max_chord_deviation(xy):
    """Maximum perpendicular deviation of vertices from the end-to-end chord."""
    chord = xy[-1] - xy[0]
    chord = chord / np.linalg.norm(chord)
    relative = xy - xy[0]
    cross = relative[:, 0] * chord[1] - relative[:, 1] * chord[0]
    return float(np.max(np.abs(cross)))


def test_isotherm_members_are_straight():
    """Isotherms are exactly straight lines in the tephigram plane."""
    members = isopleths.isotherm_members([-40.0, 0.0, 40.0])
    assert [member.value for member in members] == [-40.0, 0.0, 40.0]
    for member in members:
        assert member.xy.shape == (ISOPLETH_SAMPLES, 2)
        assert member.xy.dtype == np.float64
        assert np.isfinite(member.xy).all()
        assert _max_chord_deviation(member.xy) < 1e-9


def test_dry_adiabat_members_are_straight():
    """Dry adiabats are exactly straight lines in the tephigram plane."""
    members = isopleths.dry_adiabat_members([0.0, 40.0, 100.0])
    assert [member.value for member in members] == [0.0, 40.0, 100.0]
    for member in members:
        assert member.xy.shape == (ISOPLETH_SAMPLES, 2)
        assert np.isfinite(member.xy).all()
        assert _max_chord_deviation(member.xy) < 1e-9


def test_isotherm_perpendicular_to_dry_adiabat():
    """The defining tephigram invariant holds for the built geometry."""
    (isotherm,) = isopleths.isotherm_members([10.0])
    (adiabat,) = isopleths.dry_adiabat_members([40.0])
    v1 = isotherm.xy[-1] - isotherm.xy[0]
    v2 = adiabat.xy[-1] - adiabat.xy[0]
    cosine = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    assert cosine == pytest.approx(0.0, abs=1e-12)


def test_isobar_members_satisfy_poisson():
    """Every isobar vertex maps back to its pressure via the transforms."""
    members = isopleths.isobar_members([1000.0, 850.0, 500.0])
    for member in members:
        t, theta = transforms.temperature_theta_from_xy(
            member.xy[:, 0], member.xy[:, 1]
        )
        pressure = transforms.pressure_from_temperature_theta(t, theta)
        np.testing.assert_allclose(pressure, member.value, rtol=1e-9)


@given(pressure=st.floats(min_value=60.0, max_value=1040.0))
def test_isobar_round_trip_property(pressure):
    """(p) -> isobar polyline -> (p) is the identity across the domain."""
    (member,) = isopleths.isobar_members([pressure])
    t, theta = transforms.temperature_theta_from_xy(member.xy[:, 0], member.xy[:, 1])
    back = transforms.pressure_from_temperature_theta(t, theta)
    np.testing.assert_allclose(back, pressure, rtol=1e-8)


def test_scalar_values_accepted():
    """Builders accept a bare scalar as well as a sequence."""
    (member,) = isopleths.isotherm_members(15.0)
    assert member.value == 15.0


def _pressure_temperature(member):
    """Recover (pressure, temperature) vertices from a member's x-y polyline."""
    t, theta = transforms.temperature_theta_from_xy(member.xy[:, 0], member.xy[:, 1])
    pressure = transforms.pressure_from_temperature_theta(t, theta)
    return pressure, t


def test_moist_adiabat_crosses_reference_at_its_value():
    """theta_w labels the curve: T at 1000 hPa equals the member value."""
    (member,) = isopleths.moist_adiabat_members([20.0])
    pressure, temperature = _pressure_temperature(member)
    index = int(np.argmin(np.abs(pressure - 1000.0)))
    assert pressure[index] == pytest.approx(1000.0, abs=1e-6)
    assert temperature[index] == pytest.approx(20.0, abs=1e-6)


def test_moist_adiabat_matches_metpy_wet_bulb_potential_temperature():
    """Cross-check the pseudoadiabat against MetPy's own theta-w function.

    Along the theta_w = 20 pseudoadiabat, the wet-bulb potential
    temperature of a saturated parcel recovers 20 °C. Tolerance 0.2 °C
    covers the documented formulation difference between moist_lapse
    (pseudoadiabat ODE integration) and wet_bulb_potential_temperature
    (Davies-Jones 2008 approximation); measured offsets on metpy 1.7.1
    were +0.02 to +0.15 °C.
    """
    (member,) = isopleths.moist_adiabat_members([20.0])
    pressure, temperature = _pressure_temperature(member)
    for target in (850.0, 700.0, 500.0, 300.0):
        index = int(np.argmin(np.abs(pressure - target)))
        t_q = units.Quantity(temperature[index], "degC")
        theta_w = wet_bulb_potential_temperature(
            units.Quantity(pressure[index], "hPa"), t_q, t_q
        ).m_as("degC")
        assert theta_w == pytest.approx(20.0, abs=0.2)


def test_moist_adiabat_truncation():
    """Curves stop at the truncation temperature (default and overridden)."""
    (member,) = isopleths.moist_adiabat_members([20.0])
    _, temperature = _pressure_temperature(member)
    assert temperature.min() >= MOIST_ADIABAT_TRUNCATION - 1e-6
    (shorter,) = isopleths.moist_adiabat_members([20.0], truncation=-30.0)
    assert shorter.xy.shape[0] < member.xy.shape[0]
    _, t_short = _pressure_temperature(shorter)
    assert t_short.min() >= -30.0 - 1e-6


def test_moist_adiabat_monotonic_cooling_with_height():
    """Along a pseudoadiabat, temperature falls as pressure falls."""
    (member,) = isopleths.moist_adiabat_members([20.0])
    pressure, temperature = _pressure_temperature(member)
    order = np.argsort(pressure)
    assert np.all(np.diff(temperature[order]) > 0)


def test_mixing_ratio_members_match_metpy_saturation_mixing_ratio():
    """Each vertex is the dew point where saturation mixing ratio equals w.

    Tolerance 1e-2: metpy's dewpoint (a Bolton-formula inversion) is not
    the exact inverse of the saturation vapour pressure inside
    saturation_mixing_ratio, and the mismatch grows at cold dew points —
    measured on metpy 1.7.1 at rel 6.5e-3 for w = 1 g/kg at the 50 hPa
    domain edge (and up to 5e-2 for w = 0.05, deliberately not asserted
    here).
    """
    members = isopleths.mixing_ratio_members([1.0, 10.0, 40.0])
    for member in members:
        pressure, dew = _pressure_temperature(member)
        w = saturation_mixing_ratio(
            units.Quantity(pressure, "hPa"), units.Quantity(dew, "degC")
        ).m_as("g/kg")
        np.testing.assert_allclose(w, member.value, rtol=1e-2)


def test_mixing_ratio_default_values_all_build():
    members = isopleths.mixing_ratio_members(MIXING_RATIO_VALUES)
    assert [member.value for member in members] == list(MIXING_RATIO_VALUES)
    for member in members:
        assert np.isfinite(member.xy).all()


def test_import_tephpy_does_not_import_metpy():
    """Importing tephpy must not import metpy (spec §3.2/§10 item 10).

    metpy loads on the first isopleth build instead. Run in a subprocess
    so the check is independent of what this session already imported.
    """
    code = "import sys, tephpy; raise SystemExit(1 if 'metpy' in sys.modules else 0)"
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603


@pytest.fixture
def plain_axes():
    """Provide a stock Axes framed on the tephigram default view.

    IsoplethFamily only needs `axes.viewLim`/`transData`, so testing on a
    plain Axes proves the artist stands alone before it is wired into
    TephigramAxes.
    """
    fig, ax = plt.subplots()
    ax.set(xlim=(1591.0, 1902.0), ylim=(1671.0, 1822.0))
    yield ax
    plt.close(fig)


def _make_family(name):
    spec = isopleths._FAMILY_SPECS[name]
    return isopleths.IsoplethFamily(spec, getattr(config, name))


def test_family_specs_cover_the_five_families():
    assert set(isopleths._FAMILY_SPECS) == {
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
    }


def test_family_builds_lazily_and_draws(plain_axes):
    family = _make_family("isobars")
    plain_axes.add_artist(family)
    assert family._members is None
    plain_axes.figure.canvas.draw()
    assert family._members is not None
    assert len(family._lines.get_segments()) > 0


def test_every_family_draws_on_the_default_view(plain_axes):
    for name in isopleths._FAMILY_SPECS:
        plain_axes.add_artist(_make_family(name))
    plain_axes.figure.canvas.draw()
    for artist in plain_axes.get_children():
        if isinstance(artist, isopleths.IsoplethFamily):
            assert len(artist._lines.get_segments()) > 0


def _geometry_probe(family):
    """Summarize the built geometry, in the terms every geometry option moves.

    ``values``, ``interval`` and ``emphasis`` change which members exist;
    ``truncation`` leaves the member list alone and shortens the polylines,
    which the bounding boxes carry.
    """
    return family._member_values.copy(), family._member_bboxes.copy()


@pytest.mark.parametrize(
    ("name", "option", "value"),
    [
        ("isotherms", "values", (0.0, 10.0)),
        ("isotherms", "interval", 2.0),
        ("moist_adiabats", "truncation", -30.0),
        ("isotherms", "emphasis", {-12.0: {}}),
    ],
)
def test_config_tier_geometry_change_rebuilds_members(name, option, value):
    """A geometry change rebuilds whichever tier it came from (:issue:`63`).

    ``configure`` re-reads ``tephpy.config`` on every call, so a geometry
    option changed there lands in the snapshot even when the call is about
    something else entirely. Deciding whether to rebuild from the keyword
    names left the cache stale, and the family then advertised a geometry
    through ``options`` that its members did not carry.
    """
    family = _make_family(name)
    family._build()
    before_values, before_bboxes = _geometry_probe(family)
    with config.context(**{name: {option: value}}):
        family.configure(color="red")
        assert getattr(family.options, option) == value
        assert family._members is None
        family._build()
        after_values, after_bboxes = _geometry_probe(family)
    assert not (
        np.array_equal(before_values, after_values)
        and np.array_equal(before_bboxes, after_bboxes)
    )


def test_configure_keeps_members_when_the_geometry_is_unchanged():
    """Re-passing a value the family already has must not force a rebuild.

    The old keyword-name test threw the cache away on every ``interval``
    keyword, whatever it resolved to.
    """
    family = _make_family("isotherms")
    family.configure(interval=2.0)
    family._build()
    members = family._members
    family.configure(interval=2.0, color="red")
    assert family._members is members


def test_family_does_not_participate_in_autoscale(plain_axes):
    family = _make_family("isobars")
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    assert not np.isfinite(plain_axes.dataLim.x0)


def test_isobar_zoom_ladder_masks():
    """The ladder picks 100/50/20/10 hPa members by view width, value-anchored."""
    family = _make_family("isobars")
    family._build()
    wide = family._member_values[family._zoom_mask(600.0)]
    mid = family._member_values[family._zoom_mask(300.0)]
    fine = family._member_values[family._zoom_mask(100.0)]
    finest = family._member_values[family._zoom_mask(50.0)]
    np.testing.assert_array_equal(wide, np.arange(100.0, 1001.0, 100.0))
    np.testing.assert_array_equal(mid, np.arange(50.0, 1051.0, 50.0))
    np.testing.assert_array_equal(fine, np.arange(60.0, 1041.0, 20.0))
    np.testing.assert_array_equal(finest, np.arange(50.0, 1051.0, 10.0))


def test_mixing_ratio_stride_masks():
    """List families stride from index 0, so panning never shifts members."""
    family = _make_family("mixing_ratios")
    family._build()
    wide = family._member_values[family._zoom_mask(600.0)]
    fine = family._member_values[family._zoom_mask(100.0)]
    np.testing.assert_allclose(wide, MIXING_RATIO_VALUES[::4])
    np.testing.assert_allclose(fine, MIXING_RATIO_VALUES)


def test_view_mask_selects_overlapping_bboxes():
    family = _make_family("isotherms")
    family._member_values = np.array([0.0, 1.0])
    family._member_bboxes = np.array([[0.0, 0.0, 1.0, 1.0], [5.0, 5.0, 6.0, 6.0]])
    view = mtransforms.Bbox.from_extents(0.5, 0.5, 2.0, 2.0)
    np.testing.assert_array_equal(family._view_mask(view), [True, False])


def test_zoom_changes_the_drawn_subset(plain_axes):
    """Zooming in switches the isobar ladder from 50 hPa to 20 hPa members."""
    family = _make_family("isobars")
    plain_axes.add_artist(family)
    fig = plain_axes.figure
    fig.canvas.draw()
    wide_count = len(family._lines.get_segments())
    plain_axes.set(xlim=(1700.0, 1800.0), ylim=(1700.0, 1800.0))
    fig.canvas.draw()
    fine_count = len(family._lines.get_segments())
    assert fine_count > 0
    assert fine_count != wide_count


def test_configure_values_override_disables_ladder(plain_axes):
    family = _make_family("isotherms")
    plain_axes.add_artist(family)
    family.configure(values=(0.0, 10.0), color="red")
    plain_axes.figure.canvas.draw()
    assert family.options.color == "red"
    assert family.options.values == (0.0, 10.0)
    assert len(family._lines.get_segments()) <= 2


def test_configure_unknown_option_raises():
    with pytest.raises(TypeError, match="unknown option"):
        _make_family("isotherms").configure(bogus=1)
    with pytest.raises(TypeError, match="unknown option"):
        _make_family("mixing_ratios").configure(interval=5.0)
    with pytest.raises(TypeError, match="unknown option"):
        _make_family("isotherms").configure(truncation=-30.0)


def test_configure_none_resets_override():
    family = _make_family("isotherms")
    family.configure(color="red")
    assert family.options.color == "red"
    family.configure(color=None)
    assert family.options.color == ISOTHERM_COLOR


def test_config_precedence_and_snapshot_semantics():
    """Verify kwargs > config > constants and the snapshot semantics."""
    with config.context(isotherms={"color": "purple", "interval": 20.0}):
        family = _make_family("isotherms")
        assert family.options.color == "purple"
        assert family.options.interval == 20.0
        family.configure(color="black")
        assert family.options.color == "black"
        assert family.options.interval == 20.0
    # Exiting the context must not restyle the existing snapshot (spec §3.5).
    assert family.options.interval == 20.0
    assert family.options.color == "black"


def test_visible_option_maps_to_artist_visibility():
    family = _make_family("isobars")
    assert family.get_visible()
    family.configure(visible=False)
    assert not family.get_visible()
    assert family.options.visible is False


def test_configure_values_iterator_materialized():
    """A one-shot iterator for values must survive later reconfigures."""
    family = _make_family("isotherms")
    family.configure(values=iter([0.0, 10.0]))
    assert family.options.values == (0.0, 10.0)
    family.configure(color="red")
    assert family.options.values == (0.0, 10.0)


def test_labels_drawn_and_upright(plain_axes):
    family = _make_family("isobars")
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    labelled = [text for text in family._texts if text.get_text()]
    assert labelled
    for text in labelled:
        rotation = text.get_rotation()  # normalised to [0, 360)
        assert rotation <= 90.0 or rotation >= 270.0


def test_label_pool_does_not_outgrow_the_labelled_set(plain_axes):
    """The pool tracks what is labelled, in both directions (spec §3.2).

    ``_draw_labels`` grows the pool to fit, and a zoom that promotes a finer
    ladder step grows it further. Zooming back out must give the surplus up
    again: the pool is a cache sized to the current draw, not a high-water
    mark held until ``ax.clear()``. The surplus is never drawn — the draw
    loop's ``zip(..., strict=False)`` stops at the shorter sequence — so
    nothing but the pool length can catch this.
    """
    family = _make_family("isobars")
    plain_axes.add_artist(family)
    figure = plain_axes.figure

    def labelled():
        selected = family._order_members(family._selected_members())
        return len(family._inline_members(plain_axes.viewLim, selected))

    figure.canvas.draw()
    assert len(family._texts) == labelled()
    # Zoom in far enough for the convention ladder to promote a finer step,
    # which is what grows the pool beyond the wide-view count.
    plain_axes.set(xlim=(1700.0, 1750.0), ylim=(1700.0, 1750.0))
    figure.canvas.draw()
    zoomed = len(family._texts)
    assert zoomed == labelled()
    plain_axes.set(xlim=(1591.0, 1902.0), ylim=(1671.0, 1822.0))
    figure.canvas.draw()
    assert zoomed > labelled()
    assert len(family._texts) == labelled()


def test_labels_disabled(plain_axes):
    family = _make_family("isobars")
    family.configure(labels=False)
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    assert family._texts == []


def test_moist_adiabat_truncation_configurable():
    family = _make_family("moist_adiabats")
    family.configure(truncation=-30.0)
    assert family.options.truncation == -30.0


def test_configure_zero_interval_raises():
    family = _make_family("isotherms")
    with pytest.raises(ValueError, match="positive"):
        family.configure(interval=0.0)


def test_configure_negative_interval_raises():
    family = _make_family("isotherms")
    with pytest.raises(ValueError, match="positive"):
        family.configure(interval=-10.0)


def test_config_sourced_invalid_interval_raises_at_creation():
    """A bad config-tier interval must fail at creation, not at draw."""
    with (
        config.context(isotherms={"interval": 0.0}),
        pytest.raises(ValueError, match="positive"),
    ):
        _make_family("isotherms")


def test_configure_interval_must_be_finite():
    family = _make_family("isotherms")
    with pytest.raises(ValueError, match="positive"):
        family.configure(interval=math.inf)


def test_configure_failure_leaves_family_unchanged():
    """A rejected configure() rolls back, so later calls are unaffected."""
    family = _make_family("isotherms")
    with pytest.raises(ValueError, match="positive"):
        family.configure(interval=0.0)
    family.configure(color="red")
    assert family.options.color == "red"
    assert family.options.interval is None


VIEW = mtransforms.Bbox.from_extents(1591.0, 1671.0, 1902.0, 1822.0)


def test_edge_crossings_isotherm_bottom_is_analytic():
    """An isotherm x - y = 2T meets y = y0 at exactly x = y0 + 2T."""
    (member,) = isopleths.isotherm_members([20.0])
    crossings = isopleths.edge_crossings(member.xy, "bottom", VIEW)
    np.testing.assert_allclose(crossings, [VIEW.y0 + 40.0], rtol=1e-12)


def test_edge_crossings_isotherm_left_is_analytic():
    """An isotherm x - y = 2T meets x = x0 at exactly y = x0 - 2T."""
    (member,) = isopleths.isotherm_members([-50.0])
    crossings = isopleths.edge_crossings(member.xy, "left", VIEW)
    np.testing.assert_allclose(crossings, [VIEW.x0 + 100.0], rtol=1e-12)


def test_edge_crossings_outside_the_edge_span_are_dropped():
    """A crossing of the infinite line beyond the edge segment is not a hit."""
    tiny = mtransforms.Bbox.from_extents(1591.0, 1671.0, 1600.0, 1822.0)
    (member,) = isopleths.isotherm_members([20.0])
    assert isopleths.edge_crossings(member.xy, "bottom", tiny).size == 0


def test_edge_crossings_vertex_on_the_edge_counts_once():
    """A vertex sitting exactly on the edge yields one crossing, not two."""
    xy = np.array([[1700.0, 1600.0], [1700.0, 1671.0], [1700.0, 1750.0]])
    crossings = isopleths.edge_crossings(xy, "bottom", VIEW)
    np.testing.assert_allclose(crossings, [1700.0])


def test_edge_crossings_terminal_vertex_on_the_edge_counts():
    """The last vertex starts no segment, but still lies on the edge.

    The same geometric vertex must give the same answer wherever it sits in
    the polyline, so this is pinned against the interior placement above.
    """
    terminal = np.array([[1700.0, 1750.0], [1700.0, 1671.0]])
    np.testing.assert_allclose(
        isopleths.edge_crossings(terminal, "bottom", VIEW), [1700.0]
    )
    leading = np.array([[1700.0, 1671.0], [1700.0, 1750.0]])
    np.testing.assert_allclose(
        isopleths.edge_crossings(leading, "bottom", VIEW), [1700.0]
    )


def test_edge_crossings_ignores_non_finite_segments():
    """Truncated members carry NaN vertices; those segments never hit."""
    xy = np.array([[1700.0, 1600.0], [np.nan, np.nan], [1700.0, 1750.0]])
    assert isopleths.edge_crossings(xy, "bottom", VIEW).size == 0


@pytest.mark.parametrize("infinity", [np.inf, -np.inf])
def test_edge_crossings_ignores_infinite_endpoints(infinity):
    """``np.sign`` maps +/-inf to +/-1, which would fake a sign change.

    ``-inf`` is the dangerous one: it used to return a finite, wholly
    fictitious crossing rather than nothing at all.
    """
    xy = np.array([[1700.0, 1750.0], [1750.0, infinity]])
    assert isopleths.edge_crossings(xy, "bottom", VIEW).size == 0


def test_edge_crossings_opposing_infinities_are_silent():
    """Opposing infinities divide inf by inf; mask before doing the maths."""
    xy = np.array([[1700.0, -np.inf], [1750.0, np.inf]])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert isopleths.edge_crossings(xy, "bottom", VIEW).size == 0


def test_edge_crossings_needs_two_vertices():
    """A degenerate polyline has no segments to intersect."""
    xy = np.array([[1700.0, 1671.0]])
    assert isopleths.edge_crossings(xy, "bottom", VIEW).size == 0


def test_edge_crossings_rejects_an_unknown_edge():
    """Fail loud on an unknown edge name (spec §6)."""
    (member,) = isopleths.isotherm_members([0.0])
    with pytest.raises(TypeError, match=r"unknown edge 'middle'.*bottom"):
        isopleths.edge_crossings(member.xy, "middle", VIEW)


def test_edges_are_the_four_diagram_edges():
    assert isopleths.EDGES == ("bottom", "top", "left", "right")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, (True, ())),
        (True, (True, ())),
        (False, (False, ())),
        ("bottom", (True, ("bottom",))),
        (("bottom", "left"), (True, ("bottom", "left"))),
        (("left", "bottom"), (True, ("left", "bottom"))),
        (("bottom", "bottom"), (True, ("bottom",))),
        ((), (False, ())),
    ],
)
def test_normalize_labels(raw, expected):
    """A bare string and a one-tuple are identical; duplicates collapse."""
    assert isopleths._normalize_labels(raw, "isobars") == expected


@pytest.mark.parametrize("raw", ["middle", ("bottom", "middle"), (0,), 3.5])
def test_normalize_labels_rejects_unknown_placements(raw):
    """Fail loud, naming the placement and the valid set (spec §6)."""
    with pytest.raises(TypeError, match=r"'isobars' label placement"):
        isopleths._normalize_labels(raw, "isobars")


def test_resolved_label_edges_and_invisibility():
    """An invisible family labels nothing and holds no edge (spec §3.2)."""
    spec = isopleths._FAMILY_SPECS["isobars"]
    family = isopleths.IsoplethFamily(spec, config.isobars)
    assert family.options.labels is True
    assert family.options.label_edges == ()
    family.configure(labels=("bottom", "left"))
    assert family.options.label_edges == ("bottom", "left")
    family.configure(visible=False)
    assert family.options.label_edges == ()
    family.configure(visible=True)
    assert family.options.label_edges == ("bottom", "left")
    family.configure(labels=True)
    assert family.options.label_edges == ()


def test_validator_rejection_rolls_the_family_back():
    """A validator veto leaves the family exactly as it was."""

    def veto(name, options):
        if options.label_edges:
            msg = f"{name} may not claim an edge"
            raise TypeError(msg)

    spec = isopleths._FAMILY_SPECS["isobars"]
    family = isopleths.IsoplethFamily(spec, config.isobars, validate=veto)
    family.configure(color="red")
    with pytest.raises(TypeError, match="may not claim an edge"):
        family.configure(labels="left", color="blue")
    assert family.options.label_edges == ()
    assert family.options.color == "red"


def test_on_change_fires_once_per_successful_resolve():
    """Every resolve notifies the owner; a rejected one must not."""

    def veto(name, options):
        if "right" in options.label_edges:
            msg = f"{name} may not claim the right edge"
            raise TypeError(msg)

    calls = []

    def notify():
        calls.append(None)

    spec = isopleths._FAMILY_SPECS["isobars"]
    family = isopleths.IsoplethFamily(
        spec, config.isobars, validate=veto, on_change=notify
    )
    # Creation resolves before the owner can hold the family, so it is silent.
    assert calls == []
    family.configure(labels="left")
    assert len(calls) == 1
    with pytest.raises(TypeError, match="may not claim the right edge"):
        family.configure(labels="right")
    assert len(calls) == 1
    assert family.options.label_edges == ("left",)
    family.configure(labels=True)
    assert len(calls) == 2


def test_set_visible_resolves_and_notifies_only_on_a_change():
    """``set_visible`` is the visibility resolve, and it does not recurse."""
    calls = []

    def notify():
        calls.append(None)

    spec = isopleths._FAMILY_SPECS["isobars"]
    family = isopleths.IsoplethFamily(spec, config.isobars, on_change=notify)
    family.configure(labels=("bottom", "left"))
    assert len(calls) == 1
    family.set_visible(False)
    assert len(calls) == 2
    assert family.get_visible() is False
    assert family.options.visible is False
    assert family.options.label_edges == ()
    family.set_visible(False)
    assert len(calls) == 2
    family.set_visible(True)
    assert len(calls) == 3
    assert family.get_visible() is True
    assert family.options.label_edges == ("bottom", "left")
    assert family.stale is True


def test_selected_and_inline_members_at_the_default_extent():
    """Spec §3.2's coverage table, exercised through the family."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        view = ax.viewLim

        isobars = ax.isobars(labels=("bottom", "left"))
        selected = isobars._selected_members()
        assert [member.value for member in selected][:3] == [150.0, 200.0, 250.0]
        assert len(selected) == 19
        assert isobars._inline_members(view, selected) == []

        # Release the edges before the isotherms take them: Task 5 makes a
        # second claimant an error, and this test must keep passing.
        ax.isobars(labels=True)
        isotherms = ax.isotherms(labels=("bottom", "left"))
        selected = isotherms._selected_members()
        assert len(selected) == 19
        remainder = isotherms._inline_members(view, selected)
        assert [member.value for member in remainder] == [-120.0]

        adiabats = ax.dry_adiabats()
        selected = adiabats._selected_members()
        assert adiabats._inline_members(view, selected) == selected
    finally:
        plt.close(fig)


def test_edge_locator_matches_the_coverage_table():
    """Spec §3.2's measured coverage, through the locator (spec §7)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        locator = isopleths._EdgeLocator(ax.isobars(), "left")
        positions = locator()
        assert len(positions) == 18
        assert locator.values == [float(p) for p in range(150, 1050, 50)]
        assert locator.positions == positions

        locator = isopleths._EdgeLocator(ax.mixing_ratios(), "top")
        locator()
        assert locator.values == [0.05, 0.2, 1.0, 2.0, 4.0, 7.0, 14.0, 28.0]

        locator = isopleths._EdgeLocator(ax.isotherms(), "bottom")
        locator()
        assert locator.values == [float(t) for t in range(-40, 70, 10)]
    finally:
        plt.close(fig)


def test_edge_locator_ticks_every_crossing():
    """200 hPa leaves and re-enters the view across the top edge."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        locator = isopleths._EdgeLocator(ax.isobars(), "top")
        locator()
        assert locator.values == [150.0, 200.0, 200.0]
    finally:
        plt.close(fig)


def test_edge_locator_tracks_the_view():
    """Matplotlib calls the locator every draw, so zoom needs no plumbing."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        locator = isopleths._EdgeLocator(ax.isobars(), "left")
        wide = locator()
        ax.set_extent(((900.0, -10.0), (500.0, 20.0)))
        fig.canvas.draw()
        zoomed = locator()
        assert zoomed != wide
        # Two separate reasons the ticks reach below the 500 hPa the extent
        # names.  The zoom ladder promotes the isobar step to 20 hPa at this
        # view width, which is what puts 460 and 480 in the family at all;
        # and the left edge is a vertical line in (x, y) space rather than a
        # constant-pressure line, so it sweeps down to ~457 hPa at the
        # top-left corner and those two members genuinely cross it.  The
        # curvature is why the 450 bound cannot be read off the corner
        # pressures; the ladder is why these particular members exist.
        assert all(450.0 <= value <= 900.0 for value in locator.values)
        # ``tick_values`` must ignore the interval matplotlib hands it and
        # return the crossings.  Compared against the snapshot above, never
        # against ``locator.positions``: ``__call__`` returns the very list
        # it assigns there, so ``tick_values(...) == locator.positions`` is
        # an identity comparison that cannot fail.
        ticks = locator.tick_values(0.0, 1.0)
        assert ticks is not zoomed
        assert ticks == zoomed
    finally:
        plt.close(fig)


def test_edge_formatter_reads_the_cached_values():
    """No inverse math: the formatter reads the value beside the position."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        locator = isopleths._EdgeLocator(ax.mixing_ratios(), "top")
        formatter = isopleths._EdgeFormatter(locator)
        positions = locator()
        assert formatter(positions[0]) == "0.05"
        assert formatter(positions[-1]) == "28"
        assert formatter(positions[0] + 1.0) == ""
    finally:
        plt.close(fig)


def test_edge_locator_without_axes_is_empty():
    """A detached family has no view to intersect."""
    spec = isopleths._FAMILY_SPECS["isobars"]
    locator = isopleths._EdgeLocator(
        isopleths.IsoplethFamily(spec, config.isobars), "left"
    )
    assert locator() == []
    assert locator.values == []


def test_emphasis_defaults_to_empty():
    """A family emphasises nothing until asked (spec §3.2)."""
    family = _make_family("isotherms")
    assert family.options.emphasis == {}


def test_emphasis_normalizes_keys_to_float():
    family = _make_family("isotherms")
    family.configure(emphasis={0: {}, -20: {"color": "tab:cyan"}})
    assert family.options.emphasis == {0.0: {}, -20.0: {"color": "tab:cyan"}}
    assert all(isinstance(key, float) for key in family.options.emphasis)


def test_emphasis_accepts_every_style_key():
    family = _make_family("isotherms")
    style = {
        "color": "tab:cyan",
        "linewidth": 2.0,
        "linestyle": "--",
        "alpha": 0.5,
    }
    family.configure(emphasis={0.0: style})
    assert family.options.emphasis[0.0] == style


def test_emphasis_snapshot_does_not_alias_the_caller():
    """Mutating the caller's mapping afterwards must not reach the family."""
    family = _make_family("isotherms")
    style = {"color": "tab:cyan"}
    emphasis = {0.0: style}
    family.configure(emphasis=emphasis)
    emphasis[10.0] = {"color": "red"}
    style["color"] = "red"
    assert family.options.emphasis == {0.0: {"color": "tab:cyan"}}


def test_emphasis_snapshot_rejects_mutation():
    """The caller cannot write into the snapshot either (the other direction).

    ``options`` is public, and a write there would enter a member that never
    went through ``_normalize_emphasis`` and that the member cache was never
    invalidated for. Both levels are proxies, so both writes raise: before
    this, ``emphasis[0.0]["linewidth"] = -5.0`` put a negative linewidth
    straight onto the collection.
    """
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"color": "tab:cyan"}})
    emphasis = family.options.emphasis
    with pytest.raises(TypeError, match="mappingproxy"):
        emphasis[-12.0] = {}  # type: ignore[index]
    with pytest.raises(TypeError, match="mappingproxy"):
        emphasis[0.0]["linewidth"] = -5.0  # type: ignore[index]
    with pytest.raises(TypeError, match="mappingproxy"):
        del emphasis[0.0]  # type: ignore[attr-defined]
    assert family.options.emphasis == {0.0: {"color": "tab:cyan"}}


def test_emphasis_empty_snapshot_rejects_mutation():
    """A family with nothing emphasised shares one read-only empty snapshot."""
    family = _make_family("isotherms")
    other = _make_family("isobars")
    with pytest.raises(TypeError, match="mappingproxy"):
        family.options.emphasis[0.0] = {}  # type: ignore[index]
    assert family.options.emphasis == {}
    assert other.options.emphasis == {}


def test_emphasis_none_resets_to_config():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {}})
    family.configure(emphasis=None)
    assert family.options.emphasis == {}


def test_emphasis_empty_mapping_clears_config():
    """An empty mapping is how an accessor clears a config-tier emphasis."""
    with config.context(isotherms={"emphasis": {0.0: {"color": "tab:cyan"}}}):
        family = _make_family("isotherms")
        assert family.options.emphasis == {0.0: {"color": "tab:cyan"}}
        family.configure(emphasis={})
        assert family.options.emphasis == {}


def test_emphasis_config_tier_resolves():
    with config.context(isotherms={"emphasis": {0.0: {"color": "tab:cyan"}}}):
        family = _make_family("isotherms")
        assert family.options.emphasis == {0.0: {"color": "tab:cyan"}}


def test_emphasis_not_a_mapping_raises():
    family = _make_family("isotherms")
    with pytest.raises(TypeError, match="'isotherms' emphasis must be a mapping"):
        family.configure(emphasis=[0.0])


def test_emphasis_non_numeric_key_raises():
    family = _make_family("isotherms")
    with pytest.raises(TypeError, match="member value must be a number"):
        family.configure(emphasis={None: {}})


@pytest.mark.parametrize("member", [float("nan"), float("inf"), float("-inf")])
def test_emphasis_non_finite_key_raises(member):
    """A non-finite member key builds a NaN polyline the view mask hides.

    Rejected up front instead, alongside the ``linewidth``, ``alpha`` and
    ``interval`` finiteness checks (spec §3.2).
    """
    family = _make_family("isotherms")
    with pytest.raises(ValueError, match="member value must be a finite number"):
        family.configure(emphasis={member: {}})


def test_emphasis_style_not_a_mapping_raises():
    family = _make_family("isotherms")
    with pytest.raises(TypeError, match="must be a mapping of style overrides"):
        family.configure(emphasis={0.0: "tab:cyan"})


def test_emphasis_unknown_style_key_raises():
    family = _make_family("isotherms")
    with pytest.raises(TypeError, match=r"unknown 'isotherms' emphasis style key"):
        family.configure(emphasis={0.0: {"colour": "tab:cyan"}})


@pytest.mark.parametrize("linewidth", [0.0, -1.0, float("inf")])
def test_emphasis_bad_linewidth_raises(linewidth):
    family = _make_family("isotherms")
    with pytest.raises(ValueError, match="must be a positive, finite number"):
        family.configure(emphasis={0.0: {"linewidth": linewidth}})


@pytest.mark.parametrize("alpha", [-0.1, 1.1])
def test_emphasis_bad_alpha_raises(alpha):
    family = _make_family("isotherms")
    with pytest.raises(ValueError, match="must be between 0 and 1"):
        family.configure(emphasis={0.0: {"alpha": alpha}})


def test_emphasis_failure_leaves_family_unchanged():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"color": "tab:cyan"}})
    with pytest.raises(TypeError):
        family.configure(emphasis={0.0: {"colour": "red"}})
    assert family.options.emphasis == {0.0: {"color": "tab:cyan"}}


def test_emphasis_is_a_geometry_key():
    """Changing emphasis invalidates the cached member geometry (spec §3.2)."""
    family = _make_family("isotherms")
    family._build()
    assert family._members is not None
    family.configure(emphasis={0.0: {}})
    assert family._members is None


def test_emphasis_accepted_by_every_family():
    for name in (
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
    ):
        family = _make_family(name)
        family.configure(emphasis={0.0: {}})
        assert family.options.emphasis == {0.0: {}}


def test_emphasis_adds_an_off_ladder_member():
    """-12 °C is on no isotherm ladder step, so emphasis must build it."""
    family = _make_family("isotherms")
    family.configure(emphasis={-12.0: {}})
    family._build()
    assert np.any(np.isclose(family._member_values, -12.0))


def test_emphasis_does_not_duplicate_an_existing_member():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {}})
    family._build()
    assert np.count_nonzero(np.isclose(family._member_values, 0.0)) == 1


def test_emphasis_marks_only_the_added_member_as_extra():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {}, -12.0: {}})
    family._build()
    extra = family._member_values[family._member_extra]
    np.testing.assert_allclose(extra, [-12.0])


def test_emphasis_forces_an_off_ladder_member_into_the_zoom_mask():
    family = _make_family("isotherms")
    family.configure(emphasis={-12.0: {}})
    family._build()
    selected = family._member_values[family._zoom_mask(600.0)]
    assert np.any(np.isclose(selected, -12.0))


def test_emphasis_forces_an_on_grid_member_the_ladder_would_drop():
    """5 °C is a canonical member but not a 20 °C ladder step."""
    family = _make_family("isotherms")
    family.configure(emphasis={5.0: {}})
    family._build()
    selected = family._member_values[family._zoom_mask(600.0)]
    assert np.any(np.isclose(selected, 5.0))
    plain = _make_family("isotherms")
    plain._build()
    assert not np.any(np.isclose(plain._member_values[plain._zoom_mask(600.0)], 5.0))


def test_emphasis_does_not_shift_the_mixing_ratio_stride():
    """A list family strides by canonical position, so an addition cannot shift it."""
    plain = _make_family("mixing_ratios")
    plain._build()
    emphasised = _make_family("mixing_ratios")
    emphasised.configure(emphasis={6.0: {}})
    emphasised._build()
    for width in (600.0, 300.0, 100.0):
        expected = plain._member_values[plain._zoom_mask(width)]
        got = emphasised._member_values[emphasised._zoom_mask(width)]
        np.testing.assert_allclose(got[~np.isclose(got, 6.0)], expected)
        assert np.any(np.isclose(got, 6.0))


def test_zoom_mask_strides_by_canonical_position():
    """``_zoom_mask`` strides over canonical positions, not physical indices.

    When an emphasis-only extra sits at physical index 0, the canonical members
    occupy physical indices 1 onward.  The ``cumsum`` phase fix assigns canonical
    position 0 to physical index 1 — so at a stride of 4 (width 600) the member
    at physical index 1 is selected, not the member at physical index 4 (which
    ``np.arange(count) % stride`` would pick instead).

    ``_build`` cannot produce this arrangement today because extras are always
    appended, so the extra always lands at the last index and both
    ``np.arange`` and ``cumsum`` produce the same canonical selection.  This
    test bypasses ``_build`` to guard against a future sorted builder that
    inserts emphasis values mid-list.
    """
    family = _make_family("mixing_ratios")
    # Inject an extra at physical index 0 directly — bypassing _build.
    # cumsum(~extra) - 1 gives canonical positions [-1, 0, 1, 2, 3].
    # At stride 4 (width=600) canonical position 0 → physical index 1 is
    # selected; np.arange would put position 4 at index 4 and pick that instead.
    family._member_values = np.array([99.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    family._member_extra = np.array([True, False, False, False, False])
    family._zoom_adaptive = True
    mask = family._zoom_mask(600.0)
    assert not mask[0], "extra at index 0 must not be selected by the stride"
    assert mask[1], (
        "canonical position 0 (physical index 1) must be selected at stride 4"
    )
    assert not mask[2], "canonical position 1 must not be selected at stride 4"
    assert not mask[3], "canonical position 2 must not be selected at stride 4"
    assert not mask[4], "canonical position 3 must not be selected at stride 4"


def test_emphasis_respects_the_view_mask(plain_axes):
    """A forced-in member that is above the view is still gated by the view mask.

    55 hPa is not a canonical isobar at the plain_axes zoom step (55 / 50 = 1.1
    is rejected by the 50 hPa step ladder at view width 311), so emphasis is the
    sole reason it enters ``_zoom_mask`` via ``forced``.  Its tephigram bounding
    box lies above the plain_axes view (ymin ≈ 1878 > view.y1 = 1822), so
    ``_view_mask`` must still exclude it from ``_selected_members()``.
    """
    family = _make_family("isobars")
    family.configure(emphasis={55.0: {}})
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    view = plain_axes.viewLim
    zoom_selected = family._member_values[family._zoom_mask(view.width)]
    assert np.any(np.isclose(zoom_selected, 55.0)), (
        "emphasis must force 55 hPa into the zoom mask"
    )
    drawn = [m.value for m in family._selected_members()]
    assert not any(math.isclose(value, 55.0) for value in drawn), (
        "view mask must exclude the off-screen member"
    )


def test_emphasis_outside_the_domain_is_a_silent_no_op():
    """``TEMPERATURE_DOMAIN`` ends at 60 °C, so 500 °C is built but never shown.

    500 °C is outside the temperature domain; the skewed tephigram coordinate
    puts its bounding box entirely to the right of the plain-axes view, so it
    passes ``_build`` as an extra member but ``_view_mask`` correctly excludes it.
    """
    family = _make_family("isotherms")
    family.configure(emphasis={500.0: {}})
    family._build()
    assert np.any(np.isclose(family._member_values, 500.0)), (
        "emphasis must force the out-of-domain member into the build"
    )
    view = mtransforms.Bbox.from_extents(1591.0, 1671.0, 1902.0, 1822.0)
    assert not np.any(
        family._view_mask(view) & np.isclose(family._member_values, 500.0)
    )


def test_emphasis_style_lookup_matches_within_tolerance():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"color": "tab:cyan"}})
    assert family._emphasis_style(0.0) == {"color": "tab:cyan"}
    assert family._emphasis_style(1e-12) == {"color": "tab:cyan"}
    assert family._emphasis_style(10.0) is None


def test_member_style_defaults_to_the_family_style():
    family = _make_family("isotherms")
    style = family._member_style(10.0)
    assert style == {
        "color": ISOTHERM_COLOR,
        "linewidth": ISOPLETH_LINEWIDTH,
        "linestyle": "solid",
        "alpha": ISOPLETH_ALPHA,
    }


def test_member_style_empty_emphasis_only_thickens():
    """`{}` is the printed-chart idiom: same ink, heavier line (spec §3.2)."""
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {}})
    style = family._member_style(0.0)
    assert style["color"] == ISOTHERM_COLOR
    assert style["linewidth"] == EMPHASIS_LINEWIDTH


def test_member_style_overrides_win_over_the_emphasis_default():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"color": "tab:cyan", "linewidth": 3.0}})
    style = family._member_style(0.0)
    assert style["color"] == "tab:cyan"
    assert style["linewidth"] == 3.0


def test_emphasised_member_draws_last(plain_axes):
    """Emphasis wins against its own family's neighbours (spec §3.2)."""
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {}})
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    segments = family._lines.get_segments()
    assert len(segments) > 1
    # The emphasised member draws last; its EMPHASIS_LINEWIDTH identifies it.
    widths = family._lines.get_linewidth()
    assert widths[-1] == EMPHASIS_LINEWIDTH
    assert set(widths[:-1]) == {ISOPLETH_LINEWIDTH}


def test_emphasised_member_gets_per_segment_properties(plain_axes):
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"color": "tab:cyan", "linestyle": "--"}})
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    lines = family._lines
    colors = lines.get_color()
    assert len(colors) == len(lines.get_segments())
    np.testing.assert_allclose(colors[-1], mcolors.to_rgba("tab:cyan"))
    np.testing.assert_allclose(colors[0], mcolors.to_rgba(ISOTHERM_COLOR))
    assert len(lines.get_linestyle()) == len(lines.get_segments())
    assert lines.get_linestyle()[-1] != lines.get_linestyle()[0]


def test_plain_family_still_draws_one_colour(plain_axes):
    """With nothing emphasised the collection is uniform, as before.

    Uniform *and* scalar: the per-segment path is gated on ``emphasis``, so an
    un-emphasised family carries one linewidth and a scalar alpha rather than
    an N-long sequence of each. Pixels are the same either way; vector output
    and the per-draw cost are not (spec §3.2).
    """
    family = _make_family("isotherms")
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    colors = family._lines.get_color()
    assert len({tuple(row) for row in colors}) == 1
    assert set(family._lines.get_linewidth()) == {ISOPLETH_LINEWIDTH}
    assert len(family._lines.get_linewidth()) == 1
    assert family._lines.get_alpha() == ISOPLETH_ALPHA


def test_clearing_emphasis_restores_the_plain_collection(plain_axes):
    """Clearing ``emphasis`` returns every drawn property to its scalar default.

    The per-segment path is gated on ``emphasis``, so the plain path has to
    undo what an earlier emphasised draw left on the collection — a dashed
    linestyle above all, which nothing else would overwrite (spec §3.2).
    """
    family = _make_family("isotherms")
    plain_axes.add_artist(family)
    family.configure(emphasis={0.0: {"color": "tab:cyan", "linestyle": "--"}})
    plain_axes.figure.canvas.draw()
    family.configure(emphasis={})
    plain_axes.figure.canvas.draw()
    lines = family._lines
    assert lines.get_linestyle() == [(0.0, None)]
    assert len({tuple(row) for row in lines.get_color()}) == 1
    np.testing.assert_allclose(lines.get_color()[0], mcolors.to_rgba(ISOTHERM_COLOR))
    assert set(lines.get_linewidth()) == {ISOPLETH_LINEWIDTH}


def test_emphasised_label_takes_the_emphasis_colour(plain_axes):
    """Exactly one label carries the emphasis colour: the emphasised member's."""
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"color": "tab:cyan"}})
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    colors = [mcolors.to_rgba(text.get_color()) for text in family._texts]
    assert colors.count(mcolors.to_rgba("tab:cyan")) == 1


def test_emphasis_alpha_reaches_the_segment_colour_channel(plain_axes):
    """A non-default emphasis alpha is baked into the segment's RGBA channel.

    ``ISOPLETH_ALPHA`` is 1.0, so any test using the default alpha cannot
    distinguish a correct baked-alpha from a missing one.  This test uses
    0.4 to confirm the value reaches the line even though ``ISOPLETH_ALPHA``
    would produce the same pixel.
    """
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"alpha": 0.4}})
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    colors = family._lines.get_color()
    assert colors[-1][3] == pytest.approx(0.4)
    assert colors[0][3] == pytest.approx(ISOPLETH_ALPHA)
