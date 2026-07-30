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
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from metpy.calc import saturation_mixing_ratio, wet_bulb_potential_temperature
from metpy.units import units
import numpy as np
import pytest

from tephpy import transforms
from tephpy._config import config
from tephpy._constants import (
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
