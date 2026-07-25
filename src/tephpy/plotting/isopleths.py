# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Isopleth families for the tephigram projection (spec §3.2).

Each of the five background families — isotherms, isobars, dry adiabats,
moist adiabats, and humidity mixing-ratio lines — is drawn by one
zoom-aware :class:`IsoplethFamily` artist. Member polylines are precomputed
as bare numpy arrays over a generous physical domain (the ``_constants``
domains), mapped once into the tephigram x-y data space, and cached on the
artist; every draw selects the members appropriate to the current view and
zoom ladder and re-places the family's labels. The curved families delegate
their moist thermodynamics to MetPy behind function-local imports so that
``import tephpy`` stays light (spec §10 item 10). The design is derived
from the published tephigram construction with tephi as a corroborating
oracle, not ported from tephi (spec §3.1/§10 item 5).

Units are diagram-native (spec §5 exemption): pressure in hPa, temperatures
and potential temperatures in degrees Celsius, mixing ratios in g/kg.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._constants import (
    ISOPLETH_SAMPLES,
    MOIST_ADIABAT_PRESSURE_STEP,
    MOIST_ADIABAT_TRUNCATION,
    P_REF,
    PRESSURE_DOMAIN,
    TEMPERATURE_DOMAIN,
    THETA_DOMAIN,
)

__all__ = [
    "Member",
    "dry_adiabat_members",
    "isobar_members",
    "isotherm_members",
    "mixing_ratio_members",
    "moist_adiabat_members",
]


@dataclasses.dataclass(frozen=True)
class Member:
    """One isopleth polyline in tephigram x-y data space.

    ``value`` is the member's isopleth value in the family's native units
    (°C, hPa, or g/kg); ``xy`` is the ``(N, 2)`` float64 polyline.
    """

    value: float
    xy: npt.NDArray[np.float64]


def _member(
    value: float,
    temperature: npt.NDArray[np.float64],
    theta: npt.NDArray[np.float64],
) -> Member:
    """Map a (temperature, theta) polyline into a data-space member.

    Parameters
    ----------
    value : float
        The member's isopleth value in its native units.
    temperature : numpy.ndarray
        Vertex temperatures in degrees Celsius.
    theta : numpy.ndarray
        Vertex potential temperatures in degrees Celsius.

    Returns
    -------
    Member
        The member with its polyline in tephigram x-y data space.
    """
    x, y = transforms.xy_from_temperature_theta(temperature, theta)
    return Member(value=float(value), xy=np.column_stack([x, y]))


def isotherm_members(values: npt.ArrayLike) -> list[Member]:
    """Build isotherm polylines (lines of constant temperature).

    Isotherms are exactly straight in the tephigram plane; each member
    spans ``THETA_DOMAIN`` at its constant temperature.

    Parameters
    ----------
    values : array_like
        Member temperatures in degrees Celsius.

    Returns
    -------
    list of Member
        One member per value, in input order.
    """
    theta = np.linspace(THETA_DOMAIN[0], THETA_DOMAIN[1], ISOPLETH_SAMPLES)
    vals = np.atleast_1d(np.asarray(values, dtype=np.float64))
    return [_member(v, np.full_like(theta, v), theta) for v in vals]


def dry_adiabat_members(values: npt.ArrayLike) -> list[Member]:
    """Build dry-adiabat polylines (lines of constant potential temperature).

    Dry adiabats are exactly straight in the tephigram plane, perpendicular
    to the isotherms; each member spans ``TEMPERATURE_DOMAIN`` at its
    constant potential temperature.

    Parameters
    ----------
    values : array_like
        Member potential temperatures in degrees Celsius.

    Returns
    -------
    list of Member
        One member per value, in input order.
    """
    temperature = np.linspace(
        TEMPERATURE_DOMAIN[0], TEMPERATURE_DOMAIN[1], ISOPLETH_SAMPLES
    )
    vals = np.atleast_1d(np.asarray(values, dtype=np.float64))
    return [_member(v, temperature, np.full_like(temperature, v)) for v in vals]


def isobar_members(values: npt.ArrayLike) -> list[Member]:
    """Build isobar polylines (lines of constant pressure).

    Pressure is a derived curve on the tephigram, not an axis: each member
    traces Poisson's equation across ``TEMPERATURE_DOMAIN`` at its constant
    pressure.

    Parameters
    ----------
    values : array_like
        Member pressures in hPa.

    Returns
    -------
    list of Member
        One member per value, in input order.
    """
    temperature = np.linspace(
        TEMPERATURE_DOMAIN[0], TEMPERATURE_DOMAIN[1], ISOPLETH_SAMPLES
    )
    vals = np.atleast_1d(np.asarray(values, dtype=np.float64))
    members = []
    for v in vals:
        theta = transforms.theta_from_pressure_temperature(v, temperature)
        members.append(_member(v, temperature, theta))
    return members


def moist_adiabat_members(
    values: npt.ArrayLike, truncation: float = MOIST_ADIABAT_TRUNCATION
) -> list[Member]:
    """Build moist-adiabat (pseudoadiabat) polylines.

    Each member is labelled by its wet-bulb potential temperature — the
    temperature where the curve crosses ``P_REF`` — and is integrated over
    ``PRESSURE_DOMAIN`` with :func:`metpy.calc.moist_lapse` in a single
    vectorized call, then truncated where the temperature falls below
    `truncation` (the curves converge onto the dry adiabats; Met Office
    Factsheet 13 convention). Members with fewer than two remaining
    vertices are dropped.

    Parameters
    ----------
    values : array_like
        Member wet-bulb potential temperatures in degrees Celsius.
    truncation : float, default: MOIST_ADIABAT_TRUNCATION
        Temperature (°C) below which the curves are truncated.

    Returns
    -------
    list of Member
        One member per surviving value, in input order.
    """
    # Function-local so `import tephpy` stays light (spec §3.2, §10 item 10).
    from metpy.calc import moist_lapse  # noqa: PLC0415
    from metpy.units import units  # noqa: PLC0415

    vals = np.atleast_1d(np.asarray(values, dtype=np.float64))
    lo, hi = PRESSURE_DOMAIN
    step = MOIST_ADIABAT_PRESSURE_STEP
    pressure = np.arange(hi, lo - step, -step)
    temperature = np.atleast_2d(
        moist_lapse(
            units.Quantity(pressure, "hPa"),
            units.Quantity(vals, "degC"),
            reference_pressure=units.Quantity(P_REF, "hPa"),
        ).m_as("degC")
    )
    members = []
    for value, row in zip(vals, temperature, strict=True):
        keep = row >= truncation
        if np.count_nonzero(keep) < 2:
            continue
        theta = transforms.theta_from_pressure_temperature(pressure[keep], row[keep])
        members.append(_member(value, row[keep], theta))
    return members


def mixing_ratio_members(values: npt.ArrayLike) -> list[Member]:
    """Build humidity mixing-ratio polylines (isohumes).

    For a mixing ratio ``w`` the member traces the dew-point temperature at
    which the saturation mixing ratio equals ``w``, sampled across
    ``PRESSURE_DOMAIN``: ``Td = dewpoint(vapor_pressure(p, w))`` via MetPy.

    Parameters
    ----------
    values : array_like
        Member humidity mixing ratios in g/kg.

    Returns
    -------
    list of Member
        One member per value, in input order.
    """
    # Function-local so `import tephpy` stays light (spec §3.2, §10 item 10).
    from metpy.calc import dewpoint, vapor_pressure  # noqa: PLC0415
    from metpy.units import units  # noqa: PLC0415

    vals = np.atleast_1d(np.asarray(values, dtype=np.float64))
    lo, hi = PRESSURE_DOMAIN
    pressure = np.linspace(lo, hi, ISOPLETH_SAMPLES)
    pressure_q = units.Quantity(pressure, "hPa")
    members = []
    for w in vals:
        dew = dewpoint(vapor_pressure(pressure_q, units.Quantity(w, "g/kg")))
        td = np.asarray(dew.m_as("degC"), dtype=np.float64)
        theta = transforms.theta_from_pressure_temperature(pressure, td)
        members.append(_member(w, td, theta))
    return members
