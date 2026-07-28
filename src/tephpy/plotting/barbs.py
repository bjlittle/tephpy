# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The wind-barb gutter staff (spec §3.2).

Free geometry builders — bare numpy in diagram-native units, headlessly
testable (the ``isopleths.py``/``shading.py`` pattern) — plus
:class:`BarbStaff`, the zoom-aware artist ``plot_barbs`` installs in the
gutter axes. Each draw places every barb at the y where its level's isobar
meets the diagram's right edge (the printed-form staff convention), thins
the visible levels to the densest subset at least ``BARB_MIN_SEPARATION``
apart, and renders them through matplotlib's barbs machinery with the Met
Office increments (flag 50 kt, full 10 kt, half 5 kt, 5 kt binning).
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._constants import (
    KAPPA,
    KELVIN_ZERO,
    MA,
    P_REF,
)

__all__ = ["select_barbs", "staff_y"]

#: Temperature span (°C) sampled for the g(T) inversion. Deliberately far
#: wider than ``TEMPERATURE_DOMAIN``: an isobar's drawn polyline ends at
#: the domain edge, often inside the view, but its staff crossing is a
#: geometric anchor on the isobar's analytic extension — Poisson's
#: equation is smooth there, and a crossing beyond even this span means
#: the view is nowhere near that level (the barb drops as NaN).
_STAFF_TEMPERATURE_SPAN = (-200.0, 300.0)

#: Sample count for the shared g(T) inversion grid.
_STAFF_SAMPLES = 2048


def staff_y(pressure: npt.ArrayLike, x_edge: float) -> npt.NDArray[np.float64]:
    """Find the y where each pressure's isobar crosses a staff x.

    The tephigram x decomposes along an isobar into a level-independent
    part and a pressure offset: ``x = g(T) + c(p)`` with
    ``g(T) = MA·ln(T + KELVIN_ZERO) + T`` (strictly increasing) and
    ``c(p) = MA·KAPPA·ln(P_REF / p)``, from ``x = MA·ln(theta_K) + T``
    and Poisson's equation. Each level's crossing temperature solves
    ``g(T*) = x_edge - c(p)`` by inverse interpolation on one sampled
    ``g``, and the crossing y then comes from the real transforms at
    ``(T*, p)``.

    Parameters
    ----------
    pressure : ArrayLike
        Level pressures in hPa.
    x_edge : float
        The staff's x in tephigram data space — the diagram's right
        edge.

    Returns
    -------
    numpy.ndarray
        The float64 crossing ys in tephigram data space; NaN where the
        crossing temperature falls outside ``_STAFF_TEMPERATURE_SPAN``
        (or the pressure is not positive and finite).
    """
    p = np.atleast_1d(np.asarray(pressure, dtype=np.float64))
    grid = np.linspace(
        _STAFF_TEMPERATURE_SPAN[0], _STAFF_TEMPERATURE_SPAN[1], _STAFF_SAMPLES
    )
    g = MA * np.log(grid + KELVIN_ZERO) + grid
    with np.errstate(invalid="ignore", divide="ignore"):
        target = np.where(p > 0.0, x_edge - MA * KAPPA * np.log(P_REF / p), np.nan)
    t_star = np.interp(target, g, grid, left=np.nan, right=np.nan)
    theta = transforms.theta_from_pressure_temperature(p, t_star)
    _, y = transforms.xy_from_temperature_theta(t_star, theta)
    return np.asarray(y, dtype=np.float64)


def select_barbs(
    y: npt.ArrayLike, *, minimum_separation: float
) -> npt.NDArray[np.bool_]:
    """Thin barb positions to a minimum vertical separation.

    A greedy scan in input order — surface-first, so the surface barb
    always survives — keeps each position at least `minimum_separation`
    from the last kept one; non-finite positions are dropped. Positions
    and separation share one space (the staff uses display points), so
    zooming in spreads the ys and reveals more levels (spec §3.2).

    Parameters
    ----------
    y : ArrayLike
        Barb positions, ordered surface-first.
    minimum_separation : float
        The minimum spacing between kept positions.

    Returns
    -------
    numpy.ndarray
        Boolean keep-mask over `y`.
    """
    positions = np.atleast_1d(np.asarray(y, dtype=np.float64))
    keep = np.zeros(positions.shape, dtype=np.bool_)
    last = -np.inf
    for index, position in enumerate(positions):
        if not np.isfinite(position):
            continue
        if abs(position - last) >= minimum_separation or last == -np.inf:
            keep[index] = True
            last = position
    return keep
