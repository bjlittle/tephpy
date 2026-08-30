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

Both curves are sampled onto their merged pressure grid along the drawn
polylines — the straight segments in tephigram (x, y) space that
matplotlib draws between profile levels — with a vertex inserted at each
exact segment intersection, so the fill closes on the plotted lines at
every scale (any other interpolation bows away from the drawn chords
between levels). The regions are bounded as :func:`metpy.calc.cape_cin`
integrates (its ``which_lfc="bottom"``/``which_el="top"`` defaults): CAPE is the
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

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._constants import KAPPA, KELVIN_ZERO, MA, P_REF

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
    pressure : ArrayLike
        Environment pressures in hPa, strictly decreasing.
    temperature : ArrayLike
        Environment temperatures in degrees Celsius; NaN gaps break the
        region.
    parcel_pressure : ArrayLike
        Parcel-path pressures in hPa, strictly decreasing.
    parcel_temperature : ArrayLike
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

    Notes
    -----
    .. versionadded:: 0.1.0

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
    pressure : ArrayLike
        Environment pressures in hPa, strictly decreasing.
    temperature : ArrayLike
        Environment temperatures in degrees Celsius; NaN gaps break the
        region.
    parcel_pressure : ArrayLike
        Parcel-path pressures in hPa, strictly decreasing.
    parcel_temperature : ArrayLike
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

    Notes
    -----
    .. versionadded:: 0.1.0

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
    """Sample both curves onto their merged pressure grid.

    Both curves are sampled along their drawn polylines (straight
    segments in tephigram (x, y) space between profile levels) onto the
    union of their pressure levels over the overlapping span, and a
    vertex is inserted at each exact intersection of the drawn segments
    so every run of one buoyancy sign starts and ends on a
    zero-difference vertex (or a span end; or its own grid vertices for
    a pathological sign flip whose segments never cross).

    Parameters
    ----------
    pressure : ArrayLike
        Environment pressures in hPa, strictly decreasing.
    temperature : ArrayLike
        Environment temperatures in degrees Celsius.
    parcel_pressure : ArrayLike
        Parcel-path pressures in hPa, strictly decreasing.
    parcel_temperature : ArrayLike
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
    env = _polyline_interpolate(env_p, env_t, grid)
    parcel = _polyline_interpolate(path_p, path_t, grid)
    diff = parcel - env
    crossing = np.flatnonzero(diff[:-1] * diff[1:] < 0.0)
    if crossing.size:
        crossing, p_cross, t_cross = _segment_intersections(grid, env, parcel, crossing)
    if crossing.size:
        grid = np.insert(grid, crossing + 1, p_cross)
        env = np.insert(env, crossing + 1, t_cross)
        parcel = np.insert(parcel, crossing + 1, t_cross)
    return grid, env, parcel


def _polyline_interpolate(
    pressure: npt.NDArray[np.float64],
    temperature: npt.NDArray[np.float64],
    targets: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    """Temperature at target pressures on a curve's drawn polyline.

    The drawn curve is straight in tephigram (x, y) space between profile
    levels, so temperature and ln theta_K are both linear along a segment
    while pressure varies nonlinearly; the point at a target pressure is
    located by bisection on ``ln T_K(s) - ln theta_K(s) = kappa ln (p /
    P_REF)``, which is concave in the segment parameter and bracketed by
    the endpoints. Targets that hit a profile level exactly return that
    level's temperature (NaN levels propagate to their segments only, as
    ``np.interp`` did).

    Parameters
    ----------
    pressure : numpy.ndarray
        The curve's pressures in hPa, strictly decreasing.
    temperature : numpy.ndarray
        The curve's temperatures in degrees Celsius.
    targets : numpy.ndarray
        Pressures to sample at, in hPa, within the curve's span.

    Returns
    -------
    numpy.ndarray
        Temperatures in degrees Celsius on the drawn polyline.
    """
    u = -np.log(pressure)
    u_targets = -np.log(np.asarray(targets, dtype=np.float64))
    theta = transforms.theta_from_pressure_temperature(pressure, temperature)
    ln_theta_k = np.log(theta + KELVIN_ZERO)
    segment = np.clip(np.searchsorted(u, u_targets, side="right") - 1, 0, u.size - 2)
    t0 = temperature[segment] + KELVIN_ZERO
    t1 = temperature[segment + 1] + KELVIN_ZERO
    l0 = ln_theta_k[segment]
    l1 = ln_theta_k[segment + 1]
    goal = -KAPPA * (u_targets + np.log(P_REF))
    low = np.zeros_like(goal)
    high = np.ones_like(goal)
    with np.errstate(invalid="ignore", divide="ignore"):
        for _ in range(60):
            mid = 0.5 * (low + high)
            above = np.log(t0 + mid * (t1 - t0)) - (l0 + mid * (l1 - l0)) >= goal
            low = np.where(above, mid, low)
            high = np.where(above, high, mid)
        s = 0.5 * (low + high)
        result = t0 + s * (t1 - t0) - KELVIN_ZERO
    # Exact level hits stay exact, whatever their neighbours.
    index = np.minimum(np.searchsorted(u, u_targets), u.size - 1)
    hit = u[index] == u_targets
    return np.asarray(np.where(hit, temperature[index], result), dtype=np.float64)


def _segment_intersections(
    pressure: npt.NDArray[np.float64],
    temperature: npt.NDArray[np.float64],
    parcel_temperature: npt.NDArray[np.float64],
    crossing: npt.NDArray[np.intp],
) -> tuple[npt.NDArray[np.intp], npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Intersect the drawn curves over each sign-change grid cell.

    Within one merged-grid cell both curves are straight segments in
    tephigram (x, y) space, and a buoyancy sign change across the cell
    means they cross inside it whenever pressure is monotone along both
    chords — the physical case; the intersection point then lies on both
    drawn polylines. A pathological chord (an extreme temperature swing
    over a near-isobaric step) can flip the sign at equal pressures
    while the segments stay disjoint, so a cell is kept only when the
    intersection sits within both segments — fabricating a vertex there
    would put it on neither polyline and break the strictly-decreasing
    grid. Skipped cells leave their run ending on grid vertices instead
    of a pinch.

    Parameters
    ----------
    pressure : numpy.ndarray
        The merged pressure grid, strictly decreasing.
    temperature : numpy.ndarray
        Environment temperatures on that grid.
    parcel_temperature : numpy.ndarray
        Parcel temperatures on that grid.
    crossing : numpy.ndarray
        Indices of the cells whose buoyancy difference changes sign.

    Returns
    -------
    tuple of numpy.ndarray
        The kept cell indices and the ``(pressure, temperature)`` of
        one intersection per kept cell.
    """
    env_xy = np.column_stack(
        transforms.xy_from_temperature_theta(
            temperature,
            transforms.theta_from_pressure_temperature(pressure, temperature),
        )
    )
    parcel_xy = np.column_stack(
        transforms.xy_from_temperature_theta(
            parcel_temperature,
            transforms.theta_from_pressure_temperature(pressure, parcel_temperature),
        )
    )
    env_span = env_xy[crossing + 1] - env_xy[crossing]
    parcel_span = parcel_xy[crossing + 1] - parcel_xy[crossing]
    gap = parcel_xy[crossing] - env_xy[crossing]
    with np.errstate(invalid="ignore", divide="ignore"):
        # 2D cross products: the segment parameters of the intersection.
        determinant = (
            env_span[:, 0] * parcel_span[:, 1] - env_span[:, 1] * parcel_span[:, 0]
        )
        s = (
            gap[:, 0] * parcel_span[:, 1] - gap[:, 1] * parcel_span[:, 0]
        ) / determinant
        u = (gap[:, 0] * env_span[:, 1] - gap[:, 1] * env_span[:, 0]) / determinant
        inside = np.isfinite(s) & np.isfinite(u)
        tolerance = 1e-9
        for parameter in (s, u):
            inside &= (parameter >= -tolerance) & (parameter <= 1.0 + tolerance)
        kept = crossing[inside]
        s = np.clip(s[inside], 0.0, 1.0)
        point = env_xy[kept] + s[:, None] * env_span[inside]
        t_cross = (point[:, 0] - point[:, 1]) / 2.0
        ln_theta_k = (point[:, 0] + point[:, 1]) / (2.0 * MA)
        p_cross = P_REF * np.exp((np.log(t_cross + KELVIN_ZERO) - ln_theta_k) / KAPPA)
    p_cross = np.clip(p_cross, pressure[kept + 1], pressure[kept])
    return kept, p_cross, t_cross


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
    """Interpolate both curves at one pressure level, on the drawn chords.

    The region's grid points already lie on the drawn polylines, and
    consecutive points share a drawn segment, so sampling between them
    stays on the plotted curves.

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
    at = np.array([level], dtype=np.float64)
    return (
        float(_polyline_interpolate(pressure, temperature, at)[0]),
        float(_polyline_interpolate(pressure, parcel_temperature, at)[0]),
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
