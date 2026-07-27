# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""CAPE/CIN shading geometry for the tephigram (spec §3.2).

Free builders in the ``isopleths`` pattern: pure functions over bare numpy
arrays in diagram-native units (hPa, °C — the spec §5 exemption) that
return closed polygons in (temperature, theta) space, headlessly testable.
``TephigramAxes.shade_cape``/``shade_cin`` draw them through the tephigram
transform as one compound-path ``PathPatch`` per call.

Both curves are interpolated onto their merged pressure grid (linear in
ln p) with the exact buoyancy sign-change crossings inserted, and the
regions are bounded as :func:`metpy.calc.cape_cin` integrates (its
``which_lfc="bottom"``/``which_el="top"`` defaults): CAPE is the
positive-buoyancy region between the LFC — the bottom of the lowest
positive run at or above the LCL — and the EL — the top of the highest
such run, which is the profile top while the parcel is still buoyant
there; CIN is the negative-buoyancy region between the parcel start and
the LFC. With no LFC there is neither region (``cape_cin`` returns
``0 J/kg`` for both). Two documented divergences from the *numbers*:
``cape_cin`` finds its bounds on virtual-temperature profiles and
integrates the net virtual-temperature difference (Doswell & Rasmussen
1994), neither of which the plotted temperature curves can show — the
shading is the drawn-curve region between the same rules' bounds, and the
annotated J/kg number remains the quantitative truth.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from tephpy import transforms

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["cape_polygons", "cin_polygons"]


def cape_polygons(
    pressure: npt.ArrayLike,
    temperature: npt.ArrayLike,
    parcel_pressure: npt.ArrayLike,
    parcel_temperature: npt.ArrayLike,
    *,
    lcl_pressure: float,
) -> list[npt.NDArray[np.float64]]:
    """Build the CAPE region's closed polygons (spec §3.2).

    Parameters
    ----------
    pressure : array_like
        Environment pressures in hPa, strictly decreasing.
    temperature : array_like
        Environment temperatures in degrees Celsius; NaN gaps break the
        region.
    parcel_pressure : array_like
        Parcel-path pressures in hPa, strictly decreasing.
    parcel_temperature : array_like
        Parcel-path temperatures in degrees Celsius.
    lcl_pressure : float
        Pressure of the LCL the parcel uses, in hPa; buoyancy below it
        never counts towards CAPE.

    Returns
    -------
    list of numpy.ndarray
        One ``(N, 2)`` closed polygon in (temperature, theta) space per
        uninterrupted positive-buoyancy run — plural when the region is
        interrupted, empty when there is no CAPE (0 is an answer, not an
        error; spec §6).
    """
    p, env, parcel = _merged_curves(
        pressure, temperature, parcel_pressure, parcel_temperature
    )
    regions = [
        (lo, hi)
        for lo, hi in _regions(p, parcel - env, positive=True)
        if p[hi - 1] < lcl_pressure
    ]
    polygons = []
    for lo, hi in regions:
        clipped = _clip_pressure_span(
            p[lo:hi], env[lo:hi], parcel[lo:hi], bottom=lcl_pressure
        )
        if clipped is not None:
            polygons.append(_polygon(*clipped))
    return polygons


def cin_polygons(
    pressure: npt.ArrayLike,
    temperature: npt.ArrayLike,
    parcel_pressure: npt.ArrayLike,
    parcel_temperature: npt.ArrayLike,
    *,
    lcl_pressure: float,
) -> list[npt.NDArray[np.float64]]:
    """Build the CIN region's closed polygons (spec §3.2).

    Parameters
    ----------
    pressure : array_like
        Environment pressures in hPa, strictly decreasing.
    temperature : array_like
        Environment temperatures in degrees Celsius; NaN gaps break the
        region.
    parcel_pressure : array_like
        Parcel-path pressures in hPa, strictly decreasing.
    parcel_temperature : array_like
        Parcel-path temperatures in degrees Celsius.
    lcl_pressure : float
        Pressure of the LCL the parcel uses, in hPa; it locates the LFC
        that bounds the region.

    Returns
    -------
    list of numpy.ndarray
        One ``(N, 2)`` closed polygon in (temperature, theta) space per
        uninterrupted negative-buoyancy run between the parcel start and
        the LFC — empty when there is no LFC (``cape_cin`` reports both
        CAPE and CIN as zero then) or no inhibition below it.
    """
    p, env, parcel = _merged_curves(
        pressure, temperature, parcel_pressure, parcel_temperature
    )
    diff = parcel - env
    lfc_pressure = _lfc(p, diff, lcl_pressure)
    if lfc_pressure is None:
        return []
    regions = [
        (lo, hi) for lo, hi in _regions(p, diff, positive=False) if p[lo] > lfc_pressure
    ]
    polygons = []
    for lo, hi in regions:
        clipped = _clip_pressure_span(
            p[lo:hi], env[lo:hi], parcel[lo:hi], top=lfc_pressure
        )
        if clipped is not None:
            polygons.append(_polygon(*clipped))
    return polygons


def _merged_curves(
    pressure: npt.ArrayLike,
    temperature: npt.ArrayLike,
    parcel_pressure: npt.ArrayLike,
    parcel_temperature: npt.ArrayLike,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Interpolate both curves onto their merged pressure grid.

    Both curves are interpolated linearly in ln p onto the union of their
    pressure levels over the overlapping span, and the exact buoyancy
    sign-change crossings are inserted so every run of one buoyancy sign
    starts and ends on a zero-difference vertex (or a span end).

    Parameters
    ----------
    pressure : array_like
        Environment pressures in hPa, strictly decreasing.
    temperature : array_like
        Environment temperatures in degrees Celsius.
    parcel_pressure : array_like
        Parcel-path pressures in hPa, strictly decreasing.
    parcel_temperature : array_like
        Parcel-path temperatures in degrees Celsius.

    Returns
    -------
    tuple of numpy.ndarray
        ``(pressure, temperature, parcel_temperature)`` on the merged,
        crossing-augmented grid, pressure strictly decreasing.
    """
    env_p = np.asarray(pressure, dtype=np.float64)
    env_t = np.asarray(temperature, dtype=np.float64)
    path_p = np.asarray(parcel_pressure, dtype=np.float64)
    path_t = np.asarray(parcel_temperature, dtype=np.float64)
    top = max(env_p.min(), path_p.min())
    bottom = min(env_p.max(), path_p.max())
    grid = np.unique(np.concatenate([env_p, path_p]))
    grid = grid[(grid >= top) & (grid <= bottom)][::-1]
    # Interpolate linearly in ln p; -ln p is increasing for np.interp.
    x = -np.log(grid)
    env = np.interp(x, -np.log(env_p), env_t)
    parcel = np.interp(x, -np.log(path_p), path_t)
    diff = parcel - env
    crossing = np.flatnonzero(diff[:-1] * diff[1:] < 0.0)
    if crossing.size:
        fraction = diff[crossing] / (diff[crossing] - diff[crossing + 1])
        x_cross = x[crossing] + fraction * (x[crossing + 1] - x[crossing])
        t_cross = np.interp(x_cross, x, env)
        grid = np.insert(grid, crossing + 1, np.exp(-x_cross))
        env = np.insert(env, crossing + 1, t_cross)
        parcel = np.insert(parcel, crossing + 1, t_cross)
    return grid, env, parcel


def _regions(
    pressure: npt.NDArray[np.float64],
    diff: npt.NDArray[np.float64],
    *,
    positive: bool,
) -> Iterator[tuple[int, int]]:
    """Locate the uninterrupted runs of one buoyancy sign.

    Each run is widened to the adjacent zero-difference crossing vertices
    so its polygon closes exactly on the drawn curves; runs too short to
    enclose area are dropped.

    Parameters
    ----------
    pressure : numpy.ndarray
        The merged, crossing-augmented pressure grid.
    diff : numpy.ndarray
        Parcel minus environment temperature on that grid.
    positive : bool
        Select positive-buoyancy runs (CAPE) or negative ones (CIN).

    Yields
    ------
    tuple of int
        Half-open ``(start, stop)`` index bounds of one region.
    """
    mask = diff > 0.0 if positive else diff < 0.0
    padded = np.concatenate([[False], mask, [False]])
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    for start, stop in zip(edges[::2], edges[1::2], strict=True):
        lo = int(start)
        hi = int(stop)
        if lo > 0 and diff[lo - 1] == 0.0:
            lo -= 1
        if hi < diff.size and diff[hi] == 0.0:
            hi += 1
        if hi - lo >= 2 and pressure[lo] > pressure[hi - 1]:
            yield lo, hi


def _lfc(
    pressure: npt.NDArray[np.float64],
    diff: npt.NDArray[np.float64],
    lcl_pressure: float,
) -> float | None:
    """Locate the LFC bound the way ``cape_cin`` does (spec §3.2).

    The bottom of the lowest positive-buoyancy run reaching above the
    LCL, clamped to the LCL itself when that run starts below it
    (``which_lfc="bottom"`` semantics on the drawn curves).

    Parameters
    ----------
    pressure : numpy.ndarray
        The merged, crossing-augmented pressure grid.
    diff : numpy.ndarray
        Parcel minus environment temperature on that grid.
    lcl_pressure : float
        Pressure of the LCL the parcel uses, in hPa.

    Returns
    -------
    float or None
        The LFC pressure in hPa, or ``None`` when the parcel never
        becomes positively buoyant at or above the LCL.
    """
    for lo, hi in _regions(pressure, diff, positive=True):
        if pressure[hi - 1] < lcl_pressure:
            return min(float(pressure[lo]), lcl_pressure)
    return None


def _clip_pressure_span(
    pressure: npt.NDArray[np.float64],
    temperature: npt.NDArray[np.float64],
    parcel_temperature: npt.NDArray[np.float64],
    *,
    bottom: float | None = None,
    top: float | None = None,
) -> (
    tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]]
    | None
):
    """Trim one region to a pressure span, keeping the cut level exact.

    Parameters
    ----------
    pressure : numpy.ndarray
        The region's pressures, strictly decreasing.
    temperature : numpy.ndarray
        Environment temperatures on those levels.
    parcel_temperature : numpy.ndarray
        Parcel temperatures on those levels.
    bottom : float, optional
        Keep only ``pressure <= bottom``, inserting the exact cut level
        (the CAPE clip at the LCL).
    top : float, optional
        Keep only ``pressure >= top``, inserting the exact cut level
        (the CIN clip at the LFC).

    Returns
    -------
    tuple of numpy.ndarray or None
        The clipped ``(pressure, temperature, parcel_temperature)``, or
        ``None`` when fewer than two levels survive.
    """
    p, env, parcel = pressure, temperature, parcel_temperature
    if bottom is not None and p[0] > bottom:
        keep = p <= bottom
        cut = _interpolated_level(p, env, parcel, bottom)
        p = np.concatenate([[bottom], p[keep]])
        env = np.concatenate([[cut[0]], env[keep]])
        parcel = np.concatenate([[cut[1]], parcel[keep]])
    if top is not None and p[-1] < top:
        keep = p >= top
        cut = _interpolated_level(p, env, parcel, top)
        p = np.concatenate([p[keep], [top]])
        env = np.concatenate([env[keep], [cut[0]]])
        parcel = np.concatenate([parcel[keep], [cut[1]]])
    if p.size < 2 or p[0] <= p[-1]:
        return None
    return p, env, parcel


def _interpolated_level(
    pressure: npt.NDArray[np.float64],
    temperature: npt.NDArray[np.float64],
    parcel_temperature: npt.NDArray[np.float64],
    level: float,
) -> tuple[float, float]:
    """Interpolate both curves at one pressure level (linear in ln p).

    Parameters
    ----------
    pressure : numpy.ndarray
        The region's pressures, strictly decreasing.
    temperature : numpy.ndarray
        Environment temperatures on those levels.
    parcel_temperature : numpy.ndarray
        Parcel temperatures on those levels.
    level : float
        The pressure to interpolate at, in hPa.

    Returns
    -------
    tuple of float
        The ``(environment, parcel)`` temperatures at `level`.
    """
    x = -np.log(pressure)
    at = -np.log(level)
    return (
        float(np.interp(at, x, temperature)),
        float(np.interp(at, x, parcel_temperature)),
    )


def _polygon(
    pressure: npt.NDArray[np.float64],
    temperature: npt.NDArray[np.float64],
    parcel_temperature: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    """Close one region into a (temperature, theta) polygon.

    Up the parcel curve, then back down the environment curve; the
    vertices are ready for the tephigram transform (no duplicate closing
    vertex — the drawing side appends ``CLOSEPOLY``).

    Parameters
    ----------
    pressure : numpy.ndarray
        The region's pressures, strictly decreasing.
    temperature : numpy.ndarray
        Environment temperatures on those levels.
    parcel_temperature : numpy.ndarray
        Parcel temperatures on those levels.

    Returns
    -------
    numpy.ndarray
        The closed ``(N, 2)`` polygon in (temperature, theta) space.
    """
    parcel_theta = transforms.theta_from_pressure_temperature(
        pressure, parcel_temperature
    )
    env_theta = transforms.theta_from_pressure_temperature(pressure, temperature)
    vertices_t = np.concatenate([parcel_temperature, temperature[::-1]])
    vertices_theta = np.concatenate([parcel_theta, env_theta[::-1]])
    return np.column_stack([vertices_t, vertices_theta])
