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
from tephpy._constants import CPD, KAPPA, KELVIN_ZERO, MA, P_REF, RD

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


THETAS = st.floats(min_value=-100.0, max_value=300.0, allow_nan=False)


def test_xy_known_value_recomputed_independently():
    """Spot value recomputed with the math module, not the numpy code path.

    Derivation: for T = 15 °C, theta = 15 °C (a surface point at P_REF),
    ln(theta_K) = ln(288.15), so x = 300 ln(288.15) + 15, y = 300 ln(288.15) - 15.
    """
    ln_theta = math.log(15.0 + KELVIN_ZERO)
    x, y = transforms.xy_from_temperature_theta(15.0, 15.0)
    assert float(x) == pytest.approx(MA * ln_theta + 15.0, rel=1e-12)
    assert float(y) == pytest.approx(MA * ln_theta - 15.0, rel=1e-12)


@given(temperature=TEMPERATURES, theta=THETAS)
def test_xy_round_trip(temperature, theta):
    """(T, theta) -> (x, y) -> (T, theta) is the identity."""
    x, y = transforms.xy_from_temperature_theta(temperature, theta)
    t_back, theta_back = transforms.temperature_theta_from_xy(x, y)
    assert float(t_back) == pytest.approx(temperature, rel=1e-9, abs=1e-9)
    assert float(theta_back) == pytest.approx(theta, rel=1e-9, abs=1e-9)


@given(pressure=PRESSURES, temperature=TEMPERATURES)
def test_full_round_trip_pressure_temperature(pressure, temperature):
    """(p, T) -> (T, theta) -> (x, y) and back reproduces (p, T) — spec §7."""
    theta = transforms.theta_from_pressure_temperature(pressure, temperature)
    x, y = transforms.xy_from_temperature_theta(temperature, theta)
    t_back, theta_back = transforms.temperature_theta_from_xy(x, y)
    p_back = transforms.pressure_from_temperature_theta(t_back, theta_back)
    assert float(p_back) == pytest.approx(pressure, rel=1e-8)
    assert float(t_back) == pytest.approx(temperature, rel=1e-9, abs=1e-9)


def test_isotherm_perpendicular_to_dry_adiabat():
    """The defining tephigram invariant, asserted in display space (spec §7).

    Along an isotherm (T fixed, theta varies) the direction is
    d(x, y) = (MA dln(theta), MA dln(theta)) ∝ (1, 1); along a dry adiabat
    (theta fixed, T varies) it is (dT, -dT) ∝ (1, -1). Their dot product is
    exactly zero. Verified numerically from function output alone.
    """
    t0, theta0, eps = 10.0, 40.0, 1e-6
    x0, y0 = transforms.xy_from_temperature_theta(t0, theta0)
    # Direction along the isotherm through (t0, theta0).
    x1, y1 = transforms.xy_from_temperature_theta(t0, theta0 + eps)
    isotherm = np.array([float(x1 - x0), float(y1 - y0)])
    # Direction along the dry adiabat through (t0, theta0).
    x2, y2 = transforms.xy_from_temperature_theta(t0 + eps, theta0)
    adiabat = np.array([float(x2 - x0), float(y2 - y0)])
    cosine = np.dot(isotherm, adiabat) / (
        np.linalg.norm(isotherm) * np.linalg.norm(adiabat)
    )
    assert cosine == pytest.approx(0.0, abs=1e-9)


def test_xy_out_of_domain_is_nan():
    """Theta at or below absolute zero has no ln(theta_K): NaN, silently."""
    x, y = transforms.xy_from_temperature_theta(0.0, -KELVIN_ZERO - 1.0)
    assert np.isnan(x)
    assert np.isnan(y)


def test_xy_domain_boundary_exactly_at_absolute_zero():
    """The domain guard flips exactly at theta = absolute zero: still NaN."""
    x, y = transforms.xy_from_temperature_theta(0.0, -KELVIN_ZERO)
    assert np.isnan(x)
    assert np.isnan(y)


def test_inverse_extreme_input_is_silent():
    """Hostile x/y returns silently — no RuntimeWarning escapes (spec §3.1).

    The suite's ``filterwarnings = ["error"]`` promotes any unsilenced
    numpy warning to a failure, so returning at all proves silence.
    Regression: ``np.exp`` overflow and ``inf + -inf`` previously escaped
    from ``temperature_theta_from_xy``.
    """
    temperature, theta = transforms.temperature_theta_from_xy(3e5, 3e5)
    assert float(temperature) == 0.0
    assert np.isposinf(theta)
    temperature, theta = transforms.temperature_theta_from_xy(np.inf, -np.inf)
    assert np.isposinf(temperature)
    assert np.isnan(theta)


def test_xy_vectorized_shapes():
    """Array inputs broadcast; scalar inputs give 0-d float64 arrays."""
    x, y = transforms.xy_from_temperature_theta(
        np.array([15.0, -40.0]), np.array([15.0, 20.0])
    )
    t_back, theta_back = transforms.temperature_theta_from_xy(x, y)
    for result in (x, y, t_back, theta_back):
        assert result.shape == (2,)
        assert result.dtype == np.float64
    x_scalar, y_scalar = transforms.xy_from_temperature_theta(15.0, 15.0)
    t_scalar, theta_scalar = transforms.temperature_theta_from_xy(x_scalar, y_scalar)
    for result in (x_scalar, y_scalar, t_scalar, theta_scalar):
        assert result.shape == ()
