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
from metpy.calc import saturation_mixing_ratio, wet_bulb_potential_temperature
from metpy.units import units
import numpy as np
import pytest

from tephpy import transforms
from tephpy._constants import (
    ISOPLETH_SAMPLES,
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
