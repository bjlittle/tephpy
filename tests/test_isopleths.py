# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the isopleth geometry builders and family artist (spec §3.2/§7)."""

from __future__ import annotations

import subprocess
import sys

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
