# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the tephigram coordinate transforms (spec §3.1/§7)."""

from __future__ import annotations

import math

from hypothesis import given
from hypothesis import strategies as st
import numpy as np
import pytest

from tephpy import transforms
from tephpy._constants import CPD, KAPPA, KELVIN_ZERO, P_REF, RD

# Physical domains for property tests: pressures from the stratosphere to
# below sea level, temperatures well past any atmospheric extreme.
PRESSURES = st.floats(min_value=1.0, max_value=1100.0, allow_nan=False)
TEMPERATURES = st.floats(min_value=-150.0, max_value=100.0, allow_nan=False)


def test_kappa_is_dry_air_ratio():
    """Kappa is R_d / c_pd, approximately the 2/7 of Poisson's equation."""
    assert KAPPA == RD / CPD
    assert pytest.approx(2.0 / 7.0, rel=2e-3) == KAPPA


def test_theta_identity_at_reference_pressure():
    """At p = P_REF exactly, theta equals temperature — no arithmetic at all.

    Derivation: theta_K = T_K * (P_REF / P_REF)**kappa = T_K.
    """
    temperatures = np.array([-80.0, -40.0, 0.0, 15.0, 40.0])
    result = transforms.theta_from_pressure_temperature(P_REF, temperatures)
    np.testing.assert_allclose(result, temperatures, rtol=0, atol=1e-12)


def test_theta_known_value_recomputed_independently():
    """Spot value recomputed with the math module, not the numpy code path.

    Derivation (Poisson's equation, Stull ch. 5): for p = 850 hPa, T = 20 °C,
    theta_K = (20 + 273.15) * (1000 / 850)**kappa.
    """
    expected = (20.0 + KELVIN_ZERO) * math.pow(P_REF / 850.0, KAPPA) - KELVIN_ZERO
    result = transforms.theta_from_pressure_temperature(850.0, 20.0)
    assert float(result) == pytest.approx(expected, rel=1e-12)
    # And the independently known ballpark: lifting 850->1000 hPa warms the
    # potential temperature by roughly 13-14 K for this profile.
    assert 33.0 < expected < 35.0


def test_theta_monotonic_decreasing_in_pressure():
    """At fixed T, theta decreases as pressure increases (less lift needed)."""
    pressures = np.array([300.0, 500.0, 700.0, 850.0, 1000.0])
    thetas = transforms.theta_from_pressure_temperature(pressures, 0.0)
    assert np.all(np.diff(thetas) < 0)


@given(pressure=PRESSURES, temperature=TEMPERATURES)
def test_pressure_theta_round_trip(pressure, temperature):
    """(p, T) -> theta -> p is the identity across the physical domain."""
    theta = transforms.theta_from_pressure_temperature(pressure, temperature)
    back = transforms.pressure_from_temperature_theta(temperature, theta)
    assert float(back) == pytest.approx(pressure, rel=1e-9)


def test_theta_out_of_domain_is_nan():
    """Non-positive pressure or sub-absolute-zero theta yields NaN, silently."""
    assert np.isnan(transforms.theta_from_pressure_temperature(0.0, 15.0))
    assert np.isnan(transforms.theta_from_pressure_temperature(-10.0, 15.0))
    assert np.isnan(
        transforms.pressure_from_temperature_theta(15.0, -KELVIN_ZERO - 1.0)
    )


def test_theta_vectorized_shapes():
    """Array inputs broadcast; scalar inputs give 0-d float64 arrays."""
    result = transforms.theta_from_pressure_temperature(
        np.array([1000.0, 850.0]), np.array([15.0, 20.0])
    )
    assert result.shape == (2,)
    assert result.dtype == np.float64
    scalar = transforms.theta_from_pressure_temperature(850.0, 20.0)
    assert scalar.shape == ()
