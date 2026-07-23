# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Coordinate transforms for the tephigram projection.

Pure numpy functions between the three coordinate frames of the tephigram
(spec §3.1): pressure/temperature (p, T), temperature/potential-temperature
(T, theta), and the rotated display plane (x, y), where

    x = MA * ln(theta_K) + T        y = MA * ln(theta_K) - T

with MA = 300 and theta_K the potential temperature in Kelvin. The
construction is derived from Met Office Factsheet 13 and Stull,
*Practical Meteorology* ch. 5, and cross-validated against tephi as an
oracle (``tests/test_oracle.py``) — not ported from it.

This module is the documented exemption to the pint units policy (spec §5):
bare ``float64`` arrays in diagram-native units — pressure in hPa,
temperatures in degrees Celsius, x/y dimensionless. Out-of-domain input
(non-positive pressure, temperatures at or below absolute zero) propagates
NaN; exception-carrying validation lives at the quantified boundaries
above this module (spec §6).
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from tephpy._constants import KAPPA, KELVIN_ZERO, MA, P_REF

__all__ = [
    "pressure_from_temperature_theta",
    "temperature_theta_from_xy",
    "theta_from_pressure_temperature",
    "xy_from_temperature_theta",
]


def theta_from_pressure_temperature(
    pressure: npt.ArrayLike, temperature: npt.ArrayLike
) -> npt.NDArray[np.float64]:
    """Convert pressure and temperature to potential temperature.

    Poisson's equation: ``theta_K = T_K * (P_REF / p) ** kappa``.

    Parameters
    ----------
    pressure : array_like
        Pressure in hPa. Non-positive values yield NaN.
    temperature : array_like
        Temperature in degrees Celsius.

    Returns
    -------
    numpy.ndarray
        Potential temperature in degrees Celsius, ``float64``, broadcast
        over the inputs.
    """
    p = np.asarray(pressure, dtype=np.float64)
    t = np.asarray(temperature, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        p_valid = np.where(p > 0.0, p, np.nan)
        theta_k = (t + KELVIN_ZERO) * (P_REF / p_valid) ** KAPPA
    return np.asarray(theta_k - KELVIN_ZERO, dtype=np.float64)


def pressure_from_temperature_theta(
    temperature: npt.ArrayLike, theta: npt.ArrayLike
) -> npt.NDArray[np.float64]:
    """Convert temperature and potential temperature to pressure.

    Inverse of :func:`theta_from_pressure_temperature`:
    ``p = P_REF * (T_K / theta_K) ** (1 / kappa)``.

    Parameters
    ----------
    temperature : array_like
        Temperature in degrees Celsius.
    theta : array_like
        Potential temperature in degrees Celsius. Values at or below
        absolute zero yield NaN.

    Returns
    -------
    numpy.ndarray
        Pressure in hPa, ``float64``, broadcast over the inputs.
    """
    t = np.asarray(temperature, dtype=np.float64)
    th = np.asarray(theta, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        theta_k = np.where(th + KELVIN_ZERO > 0.0, th + KELVIN_ZERO, np.nan)
        p = P_REF * ((t + KELVIN_ZERO) / theta_k) ** (1.0 / KAPPA)
    return np.asarray(p, dtype=np.float64)


def xy_from_temperature_theta(
    temperature: npt.ArrayLike, theta: npt.ArrayLike
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Convert temperature and potential temperature to display coordinates.

    The rotated tephigram mapping: ``x = MA * ln(theta_K) + T`` and
    ``y = MA * ln(theta_K) - T``, which renders isotherms and dry adiabats
    as exactly perpendicular straight lines.

    Parameters
    ----------
    temperature : array_like
        Temperature in degrees Celsius.
    theta : array_like
        Potential temperature in degrees Celsius. Values at or below
        absolute zero yield NaN.

    Returns
    -------
    tuple of numpy.ndarray
        The ``(x, y)`` display coordinates, ``float64``, broadcast over
        the inputs.
    """
    t = np.asarray(temperature, dtype=np.float64)
    th = np.asarray(theta, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        theta_k = np.where(th + KELVIN_ZERO > 0.0, th + KELVIN_ZERO, np.nan)
        scaled = MA * np.log(theta_k)
    return (
        np.asarray(scaled + t, dtype=np.float64),
        np.asarray(scaled - t, dtype=np.float64),
    )


def temperature_theta_from_xy(
    x: npt.ArrayLike, y: npt.ArrayLike
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Convert display coordinates back to temperature and theta.

    Inverse of :func:`xy_from_temperature_theta`: ``T = (x - y) / 2`` and
    ``theta_K = exp((x + y) / (2 * MA))``.

    Parameters
    ----------
    x : array_like
        Display x coordinate (dimensionless).
    y : array_like
        Display y coordinate (dimensionless).

    Returns
    -------
    tuple of numpy.ndarray
        ``(temperature, theta)`` in degrees Celsius, ``float64``,
        broadcast over the inputs.
    """
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    temperature = (x_arr - y_arr) / 2.0
    theta = np.exp((x_arr + y_arr) / (2.0 * MA)) - KELVIN_ZERO
    return (
        np.asarray(temperature, dtype=np.float64),
        np.asarray(theta, dtype=np.float64),
    )
