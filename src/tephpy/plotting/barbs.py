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

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from matplotlib import artist as martist
from matplotlib.quiver import Barbs
import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._constants import (
    BARB_INCREMENTS,
    BARB_LENGTH,
    BARB_STAFF_POSITION,
    KAPPA,
    KELVIN_ZERO,
    MA,
    P_REF,
    POINTS_PER_INCH,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure

__all__ = ["BarbStaff", "select_barbs", "staff_y"]

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

    Notes
    -----
    .. versionadded:: 0.1.0

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

    Notes
    -----
    .. versionadded:: 0.1.0

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


class BarbStaff(martist.Artist):
    """One sounding's wind barbs on the gutter staff (spec §3.2).

    A zoom-aware artist (the ``IsoplethFamily`` refresh pattern) that
    manages a :class:`matplotlib.quiver.Barbs` child. Each draw reads the
    main axes' view, places every level at its isobar's staff crossing
    (:func:`staff_y`), masks the levels outside the view or closer than
    the minimum separation (:func:`select_barbs`), and hands the child
    the same-length masked arrays — matplotlib's barbs machinery skips
    masked points, so the member count never changes.

    Parameters
    ----------
    main_axes : matplotlib.axes.Axes
        The tephigram axes the staff annotates.
    pressure : numpy.ndarray
        Level pressures in hPa, surface-first.
    u, v : numpy.ndarray
        Wind components in knots (the barb-increment units).
    x : float
        The staff position as a fraction across the gutter.
    minimum_separation : float
        Minimum vertical separation between drawn barbs, in points.
    **kwargs : Any
        Passed through to :class:`matplotlib.quiver.Barbs`, over the
        ``_constants`` conventions (increments, rounding, length).

    Notes
    -----
    .. versionadded:: 0.1.0

    """

    def __init__(  # noqa: PLR0913 -- the staff's full geometry contract
        self,
        main_axes: Axes,
        pressure: npt.NDArray[np.float64],
        u: npt.NDArray[np.float64],
        v: npt.NDArray[np.float64],
        *,
        x: float = BARB_STAFF_POSITION,
        minimum_separation: float,
        **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
    ) -> None:
        """Wire the staff and its managed barbs child.

        Parameters
        ----------
        main_axes : matplotlib.axes.Axes
            The tephigram axes the staff annotates.
        pressure : numpy.ndarray
            Level pressures in hPa, surface-first.
        u, v : numpy.ndarray
            Wind components in knots.
        x : float
            The staff position as a fraction across the gutter.
        minimum_separation : float
            Minimum vertical separation between drawn barbs, in points.
        **kwargs : Any
            Passed through to :class:`matplotlib.quiver.Barbs`.
        """
        super().__init__()
        self._main_axes = main_axes
        self._pressure = np.asarray(pressure, dtype=np.float64)
        self._u = np.asarray(u, dtype=np.float64)
        self._v = np.asarray(v, dtype=np.float64)
        self._x = float(x)
        self._minimum_separation = float(minimum_separation)
        self._kwargs = {
            "barb_increments": dict(BARB_INCREMENTS),
            "rounding": True,
            "length": BARB_LENGTH,
            **kwargs,
        }
        self._barbs: Barbs | None = None

    @property
    def barbs(self) -> Barbs | None:
        """The managed matplotlib barbs collection.

        Returns
        -------
        matplotlib.quiver.Barbs or None
            The child collection, or ``None`` before the first draw.

        Notes
        -----
        .. versionadded:: 0.1.0

        """
        return self._barbs

    def set_figure(self, fig: Figure | SubFigure) -> None:
        """Propagate the owning figure to the managed child.

        Parameters
        ----------
        fig : matplotlib.figure.Figure or matplotlib.figure.SubFigure
            The figure the staff belongs to.

        Notes
        -----
        .. versionadded:: 0.1.0

        """
        super().set_figure(fig)
        if self._barbs is not None:
            self._barbs.set_figure(fig)

    @martist.allow_rasterization  # type: ignore[untyped-decorator]
    def draw(self, renderer: RendererBase) -> None:
        """Draw the barbs visible in the current view.

        Parameters
        ----------
        renderer : matplotlib.backend_bases.RendererBase
            The active renderer.

        Notes
        -----
        .. versionadded:: 0.1.0

        """
        if not self.get_visible():
            return
        figure = self.get_figure(root=True)
        if self.axes is None or figure is None or self._pressure.size == 0:
            return
        gutter = cast("Axes", self.axes)
        main = self._main_axes
        y = staff_y(self._pressure, main.get_xlim()[1])
        y0, y1 = sorted(main.get_ylim())
        candidate = (
            np.isfinite(y)
            & (y >= y0)
            & (y <= y1)
            & np.isfinite(self._u)
            & np.isfinite(self._v)
        )
        keep = np.zeros(y.shape, dtype=np.bool_)
        indices = np.flatnonzero(candidate)
        if indices.size:
            offsets = np.column_stack([np.full(indices.size, self._x), y[indices]])
            separation = self._minimum_separation * figure.dpi / POINTS_PER_INCH
            display = gutter.transData.transform(offsets)[:, 1]
            keep[indices] = select_barbs(display, minimum_separation=separation)
        if self._barbs is None:
            self._barbs = Barbs(
                gutter,
                np.full(y.shape, self._x),
                np.where(keep, y, 0.0),
                np.ma.masked_array(self._u, mask=~keep),
                np.ma.masked_array(self._v, mask=~keep),
                **self._kwargs,
            )
            self._barbs.set_figure(figure)
        else:
            self._barbs.set_offsets(
                np.column_stack([np.full(y.shape, self._x), np.where(keep, y, 0.0)])
            )
            self._barbs.set_UVC(
                np.ma.masked_array(self._u, mask=~keep),
                np.ma.masked_array(self._v, mask=~keep),
            )
        renderer.open_group("barb-staff", gid=self.get_gid())
        self._barbs.set_clip_box(gutter.bbox)
        self._barbs.draw(renderer)
        renderer.close_group("barb-staff")
        self.stale = False
