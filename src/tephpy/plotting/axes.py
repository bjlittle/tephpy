# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The tephigram matplotlib projection.

``TephigramAxes`` (registered as the ``"tephigram"`` projection) uses the
native rotated x-y plane as its data space, with the temperature/theta
mapping exposed as an invertible matplotlib transform and the five
background isopleth families drawn by default as zoom-aware artists
(spec §3.2).

Side-of-axes layout contract (spec §10 item 7 — decided here, built by the
consuming plans): panels beside the diagram are appended with
``mpl_toolkits.axes_grid1``'s axes divider, which tracks the equal-aspect
box height — right side, inside-out: the wind-barb gutter (Plan 6), then
the indices panel (Plan 5). Panel widths join ``_constants`` with their
plans. No layout code ships in this release.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, cast, overload

from matplotlib.axes import Axes
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.projections import register_projection
import matplotlib.transforms as mtransforms
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._config import config
from tephpy._constants import (
    CAPE_COLOR,
    CIN_COLOR,
    DEFAULT_EXTENT,
    INDICES_PANEL_FONTSIZE,
    INDICES_PANEL_PAD,
    INDICES_PANEL_ROWS,
    INDICES_PANEL_WIDTH,
    PROFILE_DEWPOINT_COLOR,
    PROFILE_LINEWIDTH,
    PROFILE_TEMPERATURE_COLOR,
    PROFILE_ZORDER,
    SHADING_ALPHA,
    SHADING_ZORDER,
)
from tephpy._units import as_quantity, check_units_mapping
from tephpy.plotting import shading
from tephpy.plotting.isopleths import _FAMILY_SPECS, IsoplethFamily

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from matplotlib.lines import Line2D

    from tephpy.calc import Profile, SoundingIndices
    from tephpy.sounding import Sounding

__all__ = ["TephigramAxes", "TephigramInvertedTransform", "TephigramTransform"]


class TephigramTransform(mtransforms.Transform):
    """Map ``(temperature, theta)`` pairs to tephigram ``(x, y)`` pairs.

    A thin, invertible matplotlib wrapper over
    :func:`tephpy.transforms.xy_from_temperature_theta`; operates on
    ``(N, 2)`` arrays in diagram-native units (degrees Celsius).
    """

    input_dims = 2
    output_dims = 2
    is_separable = False
    has_inverse = True

    def transform_non_affine(self, values: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Transform (temperature, theta) pairs to (x, y).

        Parameters
        ----------
        values : ArrayLike
            Array-like of shape ``(N, 2)`` or length ``2``: temperature,
            theta in degrees Celsius.

        Returns
        -------
        numpy.ndarray
            The tephigram x, y coordinates (the axes' data space), with
            the input's dimensionality preserved: shape ``(N, 2)`` for
            ``(N, 2)`` input, shape ``(2,)`` for length-2 input.
        """
        arr = np.asarray(values, dtype=np.float64)
        ndim = arr.ndim
        arr = np.atleast_2d(arr)
        x, y = transforms.xy_from_temperature_theta(arr[:, 0], arr[:, 1])
        out = np.column_stack([x, y])
        return out if ndim > 1 else out.reshape(-1)

    def inverted(self) -> TephigramInvertedTransform:
        """Return the inverse (x, y) -> (temperature, theta) transform.

        Returns
        -------
        TephigramInvertedTransform
            The inverse transform.
        """
        return TephigramInvertedTransform()


class TephigramInvertedTransform(mtransforms.Transform):
    """Map tephigram ``(x, y)`` pairs back to ``(temperature, theta)``."""

    input_dims = 2
    output_dims = 2
    is_separable = False
    has_inverse = True

    def transform_non_affine(self, values: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Transform (x, y) pairs to (temperature, theta).

        Parameters
        ----------
        values : ArrayLike
            Array-like of shape ``(N, 2)`` or length ``2``: tephigram
            x, y coordinates (the axes' data space).

        Returns
        -------
        numpy.ndarray
            Temperature, theta in degrees Celsius, with the input's
            dimensionality preserved: shape ``(N, 2)`` for ``(N, 2)``
            input, shape ``(2,)`` for length-2 input.
        """
        arr = np.asarray(values, dtype=np.float64)
        ndim = arr.ndim
        arr = np.atleast_2d(arr)
        t, theta = transforms.temperature_theta_from_xy(arr[:, 0], arr[:, 1])
        out = np.column_stack([t, theta])
        return out if ndim > 1 else out.reshape(-1)

    def inverted(self) -> TephigramTransform:
        """Return the forward (temperature, theta) -> (x, y) transform.

        Returns
        -------
        TephigramTransform
            The forward transform.
        """
        return TephigramTransform()


class TephigramAxes(Axes):
    """Matplotlib axes for the ``"tephigram"`` projection.

    The data space is the native rotated x-y plane (dimensionless), with
    equal aspect so the isotherm/dry-adiabat grid stays exactly
    perpendicular on screen. The five background isopleth families are
    drawn by default as zoom-aware artists and reconfigured through the
    accessor methods (:meth:`isotherms`, :meth:`isobars`,
    :meth:`dry_adiabats`, :meth:`moist_adiabats`, :meth:`mixing_ratios`).
    The temperature/theta mapping is exposed as
    :attr:`tephigram_transform`; artists plot in (temperature, theta)
    space via ``transform=ax.tephigram_transform + ax.transData``. Native
    x/y ticks carry no meteorological meaning and are hidden.
    """

    name = "tephigram"

    tephigram_transform: TephigramTransform
    _families: dict[str, IsoplethFamily]
    _indices_panel: Axes | None

    def clear(self) -> None:
        """Reset the axes to the tephigram projection defaults.

        Matplotlib calls this during ``Axes.__init__`` and on user
        ``ax.clear()``; both paths recreate the projection-owned state:
        the tephigram transform, equal aspect, hidden native axes, the
        five background isopleth families, and the default extent
        (``tephpy.config`` diagram extent, else ``DEFAULT_EXTENT``).
        An indices panel is removed with the diagram it annotated.
        """
        super().clear()
        self.tephigram_transform = TephigramTransform()
        self.set_aspect(1.0, adjustable="box")
        self.xaxis.set_visible(False)
        self.yaxis.set_visible(False)
        panel = getattr(self, "_indices_panel", None)
        if panel is not None:
            panel.remove()
            # The stub demands a callable, but None resets the locator
            # (the documented matplotlib behaviour).
            self.set_axes_locator(None)  # type: ignore[arg-type]
        self._indices_panel = None
        self._families = {}
        for name, spec in _FAMILY_SPECS.items():
            family = IsoplethFamily(spec, getattr(config, name))
            self.add_artist(family)
            self._families[name] = family
        extent = config.diagram.extent
        self.set_extent(DEFAULT_EXTENT if extent is None else extent)

    def set_extent(
        self, extent: tuple[tuple[float, float], tuple[float, float]]
    ) -> None:
        """Fix the view from ((pressure, temperature), ...) corners.

        The cartopy-style idiom for directly comparable figures
        (spec §3.2): the two corners are mapped through the tephigram
        transforms to x/y limits, and autoscaling is disabled so later
        overlays never drift the window.

        Parameters
        ----------
        extent : tuple
            ``((pressure, temperature), (pressure, temperature))``
            bottom-left and top-right corners in hPa / degrees Celsius.

        Raises
        ------
        ValueError
            If a corner is unphysical (non-positive pressure) or the
            corners are degenerate.
        """
        (p0, t0), (p1, t1) = extent
        pressures = np.array([p0, p1], dtype=np.float64)
        temperatures = np.array([t0, t1], dtype=np.float64)
        thetas = transforms.theta_from_pressure_temperature(pressures, temperatures)
        x, y = transforms.xy_from_temperature_theta(temperatures, thetas)
        if not (np.isfinite(x).all() and np.isfinite(y).all()):
            msg = f"extent corners must be physical (pressure > 0 hPa): {extent!r}"
            raise ValueError(msg)
        if x[0] == x[1] or y[0] == y[1]:
            msg = f"extent corners must span a non-degenerate view: {extent!r}"
            raise ValueError(msg)
        self.set_xlim(float(np.min(x)), float(np.max(x)))
        self.set_ylim(float(np.min(y)), float(np.max(y)))
        self.set_autoscale_on(False)

    @overload
    def plot_profile(  # numpydoc ignore=GL08
        self,
        pressure: Profile,
        *,
        label: str | None = None,
        **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
    ) -> Line2D: ...

    @overload
    def plot_profile(  # numpydoc ignore=GL08
        self,
        pressure: object,
        temperature: object,
        *,
        units: Mapping[str, str] | None = None,
        label: str | None = None,
        **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
    ) -> Line2D: ...

    def plot_profile(
        self,
        pressure: object,
        temperature: object | None = None,
        *,
        units: Mapping[str, str] | None = None,
        label: str | None = None,
        **kwargs: Any,
    ) -> Line2D:
        """Plot one profile of temperature against pressure (spec §3.2).

        Both arrays are pint quantities — or bare arrays with the
        ``units=`` mapping (spec §5) — converted to diagram-native units
        and plotted through the tephigram transform machinery. Matplotlib
        keywords pass through untouched, and out-of-domain values
        (pressure <= 0 hPa) propagate NaN, breaking the line (spec §3.1).

        The same signature also accepts a ``calc.Profile`` (e.g. the
        return of ``calc.parcel_path``) as its only positional argument;
        dispatch is duck-typed on the ``Profile`` shape — `temperature`
        omitted and ``pressure``/``temperature``/``lcl_pressure``
        attributes present. Label precedence in that form: `label`
        argument > ``profile.label`` > no entry. In both forms no style
        defaults are set — this is the low-level primitive (spec §4
        styles parcel paths explicitly at the call site).

        Parameters
        ----------
        pressure : pint.Quantity, ArrayLike, or Profile
            Level pressures, or the profile to plot.
        temperature : pint.Quantity or ArrayLike, optional
            Level temperatures; omitted in the ``Profile`` form.
        units : mapping of str to str, optional
            Unit strings for bare arrays, keyed by argument name, e.g.
            ``units={"pressure": "hPa", "temperature": "degC"}``; not
            accepted in the ``Profile`` form.
        label : str, optional
            Legend label for the line.
        **kwargs : Any
            Passed through to :meth:`matplotlib.axes.Axes.plot`.

        Returns
        -------
        matplotlib.lines.Line2D
            The profile line.

        Raises
        ------
        TephpyUnitsError
            For unit-less bare arrays, ambiguous or unparsable units, or
            the wrong dimensionality.
        TypeError
            For wrong argument combinations: a ``Profile`` together with
            `temperature` or ``units=``, or `temperature` omitted when
            the sole argument is not ``Profile``-shaped (a bare pressure
            array, or a ``Sounding`` passed by mistake).
        """
        profile_shaped = all(
            hasattr(pressure, attr)
            for attr in ("pressure", "temperature", "lcl_pressure")
        )
        if profile_shaped:
            if temperature is not None:
                msg = "plot_profile() takes no separate temperature with a Profile"
                raise TypeError(msg)
            if units is not None:
                msg = "plot_profile() takes no units= with a Profile"
                raise TypeError(msg)
            profile = cast("Profile", pressure)
            pressure = profile.pressure
            temperature = profile.temperature
            if label is None:
                label = profile.label
        elif temperature is None:
            msg = (
                "plot_profile() needs pressure and temperature, or a single "
                "Profile as its only positional argument"
            )
            raise TypeError(msg)
        mapping = check_units_mapping(units, allowed=("pressure", "temperature"))
        p = as_quantity(
            pressure,
            name="pressure",
            units=mapping.get("pressure"),
            dimension="[pressure]",
        )
        t = as_quantity(
            temperature,
            name="temperature",
            units=mapping.get("temperature"),
            dimension="[temperature]",
        )
        pressure_hpa = p.m_as("hPa")
        temperature_c = t.m_as("degC")
        theta = transforms.theta_from_pressure_temperature(pressure_hpa, temperature_c)
        (line,) = self.plot(
            temperature_c,
            theta,
            transform=self.tephigram_transform + self.transData,
            label=label,
            **kwargs,
        )
        return line

    def plot_sounding(
        self,
        snd: Sounding,
        *,
        label: str | None = None,
        **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
    ) -> tuple[Line2D, Line2D | None]:
        """Plot a sounding's temperature and dewpoint profiles (spec §3.2).

        Temperature and dewpoint-when-present draw as two profile lines in
        the conventional colours (temperature red, dewpoint green), with
        one legend entry per sounding attached to the temperature line.
        Label precedence: `label` argument > ``snd.label`` > no entry.
        Matplotlib keywords pass through to both lines, overriding the
        convention defaults; legends stay stock matplotlib — call
        ``ax.legend()``.

        Parameters
        ----------
        snd : Sounding
            The sounding to plot.
        label : str, optional
            Legend label override.
        **kwargs : Any
            Passed through to :meth:`matplotlib.axes.Axes.plot` for both
            lines.

        Returns
        -------
        tuple of matplotlib.lines.Line2D
            ``(temperature_line, dewpoint_line)``; the dewpoint line is
            ``None`` when the sounding has no dewpoint.
        """
        resolved = label if label is not None else snd.label
        defaults: dict[str, object] = {
            "linewidth": PROFILE_LINEWIDTH,
            "zorder": PROFILE_ZORDER,
        }
        temperature_line = self.plot_profile(
            snd.pressure,
            snd.temperature,
            label=resolved,
            **{"color": PROFILE_TEMPERATURE_COLOR, **defaults, **kwargs},
        )
        dewpoint_line = None
        if snd.dewpoint is not None:
            dewpoint_line = self.plot_profile(
                snd.pressure,
                snd.dewpoint,
                label="_nolegend_",
                **{"color": PROFILE_DEWPOINT_COLOR, **defaults, **kwargs},
            )
        return temperature_line, dewpoint_line

    def shade_cape(
        self,
        snd: Sounding,
        parcel: Profile,
        **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
    ) -> PathPatch | None:
        """Shade the CAPE area between the sounding and a parcel path.

        The positive-buoyancy region between the environment temperature
        and the parcel path, bounded as :func:`metpy.calc.cape_cin`
        integrates — from the LFC to the EL, to the profile top when the
        parcel is still buoyant there — so the shading matches the
        annotated numbers (spec §3.2). Drawn as one compound-path patch;
        interrupted regions become multiple polygons in the same patch.

        Parameters
        ----------
        snd : Sounding
            The environment sounding.
        parcel : Profile
            The parcel path, e.g. from ``calc.parcel_path``.
        **kwargs : Any
            Passed through to :class:`matplotlib.patches.PathPatch`,
            overriding the ``_constants`` conventions.

        Returns
        -------
        matplotlib.patches.PathPatch or None
            The shaded patch, or ``None`` for zero area — 0 is an
            answer, not an error (spec §6).
        """
        return self._shade(snd, parcel, shading.cape_polygons, CAPE_COLOR, kwargs)

    def shade_cin(
        self,
        snd: Sounding,
        parcel: Profile,
        **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
    ) -> PathPatch | None:
        """Shade the CIN area between the sounding and a parcel path.

        The negative-buoyancy region between the environment temperature
        and the parcel path, bounded as :func:`metpy.calc.cape_cin`
        integrates — from the parcel start to the LFC — so the shading
        matches the annotated numbers (spec §3.2). Drawn as one
        compound-path patch; with no LFC there is no CIN region.

        Parameters
        ----------
        snd : Sounding
            The environment sounding.
        parcel : Profile
            The parcel path, e.g. from ``calc.parcel_path``.
        **kwargs : Any
            Passed through to :class:`matplotlib.patches.PathPatch`,
            overriding the ``_constants`` conventions.

        Returns
        -------
        matplotlib.patches.PathPatch or None
            The shaded patch, or ``None`` for zero area — 0 is an
            answer, not an error (spec §6).
        """
        return self._shade(snd, parcel, shading.cin_polygons, CIN_COLOR, kwargs)

    def _shade(
        self,
        snd: Sounding,
        parcel: Profile,
        builder: Callable[..., list[npt.NDArray[np.float64]]],
        facecolor: str,
        kwargs: dict[str, Any],
    ) -> PathPatch | None:
        """Build one shading region and draw it as a compound-path patch.

        Parameters
        ----------
        snd : Sounding
            The environment sounding.
        parcel : Profile
            The parcel path.
        builder : callable
            The ``plotting.shading`` polygon builder to delegate to.
        facecolor : str
            The region's conventional fill colour.
        kwargs : dict
            User overrides, passed through to the patch.

        Returns
        -------
        matplotlib.patches.PathPatch or None
            The shaded patch, or ``None`` for zero area.
        """
        polygons = builder(
            snd.pressure.m_as("hPa"),
            snd.temperature.m_as("degC"),
            parcel.pressure.m_as("hPa"),
            parcel.temperature.m_as("degC"),
            lcl_pressure=float(parcel.lcl_pressure.m_as("hPa")),
        )
        if not polygons:
            return None
        vertices = []
        codes = []
        for polygon in polygons:
            count = polygon.shape[0]
            vertices.append(np.vstack([polygon, polygon[:1]]))
            codes.append(
                np.concatenate(
                    [[Path.MOVETO], np.full(count - 1, Path.LINETO), [Path.CLOSEPOLY]]
                )
            )
        path = Path(np.vstack(vertices), np.concatenate(codes))
        patch = PathPatch(
            path,
            **{
                "facecolor": facecolor,
                "edgecolor": "none",
                "alpha": SHADING_ALPHA,
                "zorder": SHADING_ZORDER,
                "transform": self.tephigram_transform + self.transData,
                **kwargs,
            },
        )
        self.add_patch(patch)
        return patch

    def annotate_indices(self, indices: SoundingIndices) -> Axes:
        """Display derived parameters in a panel beside the diagram.

        The first consumer of the side-of-axes contract (spec §3.2):
        the panel is appended with the ``axes_grid1`` divider, one
        formatted line per ``SoundingIndices`` field, NaN rendered as an
        em dash. Calling it again updates the panel in place rather than
        stacking a second one. With ``axes_grid1``, append order is
        position order: once the wind-barb gutter exists (a later
        release), ``plot_barbs`` must be called before this method for
        the contracted inside-out order.

        Parameters
        ----------
        indices : SoundingIndices
            The derived parameters, e.g. from ``calc.indices``.

        Returns
        -------
        matplotlib.axes.Axes
            The panel axes, for restyling.
        """
        if self._indices_panel is None:
            divider = make_axes_locatable(self)
            self._indices_panel = divider.append_axes(
                "right",
                size=INDICES_PANEL_WIDTH,
                pad=INDICES_PANEL_PAD,
                axes_class=Axes,
            )
        panel = self._indices_panel
        panel.clear()
        panel.set_axis_off()
        rows = len(INDICES_PANEL_ROWS)
        for row, (field, label, unit, display, spec) in enumerate(INDICES_PANEL_ROWS):
            value = float(getattr(indices, field).m_as(unit))
            text = "—" if math.isnan(value) else f"{value:{spec}} {display}"
            y = 1.0 - (row + 0.5) / rows
            panel.text(
                0.04,
                y,
                label,
                fontsize=INDICES_PANEL_FONTSIZE,
                ha="left",
                va="center",
                transform=panel.transAxes,
            )
            panel.text(
                0.96,
                y,
                text,
                fontsize=INDICES_PANEL_FONTSIZE,
                ha="right",
                va="center",
                transform=panel.transAxes,
            )
        return panel

    def _configure_family(self, name: str, kwargs: dict[str, object]) -> IsoplethFamily:
        """Apply non-``None`` accessor kwargs to a family and return it.

        Parameters
        ----------
        name : str
            The family key in ``_families``.
        kwargs : dict
            The accessor's keyword arguments; ``None`` values mean "not
            passed" and are dropped.

        Returns
        -------
        IsoplethFamily
            The (possibly reconfigured) family artist.
        """
        family = self._families[name]
        provided = {key: value for key, value in kwargs.items() if value is not None}
        if provided:
            family.configure(**provided)
        return family

    # The accessors deliberately mirror their config sections as wide
    # keyword-only signatures (spec §3.2/§3.5): PLR0913 is suppressed on
    # each rather than restructured away.
    def isotherms(  # noqa: PLR0913
        self,
        *,
        values: Iterable[float] | None = None,
        interval: float | None = None,
        color: str | None = None,
        linewidth: float | None = None,
        alpha: float | None = None,
        labels: bool | None = None,
        visible: bool | None = None,
    ) -> IsoplethFamily:
        """Return (and optionally reconfigure) the isotherm family.

        With no arguments this returns the family artist unchanged; any
        keyword given reconfigures it first (spec §3.2). Values are in
        degrees Celsius.

        Parameters
        ----------
        values : iterable of float, optional
            Explicit member temperatures; disables the zoom ladder.
        interval : float, optional
            Member interval; disables the zoom ladder.
        color : str, optional
            Line and label colour.
        linewidth : float, optional
            Line width in points.
        alpha : float, optional
            Line and label alpha.
        labels : bool, optional
            Whether member values are labelled.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The isotherm family artist.
        """
        return self._configure_family(
            "isotherms",
            {
                "values": values,
                "interval": interval,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "labels": labels,
                "visible": visible,
            },
        )

    def isobars(  # noqa: PLR0913
        self,
        *,
        values: Iterable[float] | None = None,
        interval: float | None = None,
        color: str | None = None,
        linewidth: float | None = None,
        alpha: float | None = None,
        labels: bool | None = None,
        visible: bool | None = None,
    ) -> IsoplethFamily:
        """Return (and optionally reconfigure) the isobar family.

        With no arguments this returns the family artist unchanged; any
        keyword given reconfigures it first (spec §3.2). Values are in
        hPa.

        Parameters
        ----------
        values : iterable of float, optional
            Explicit member pressures; disables the zoom ladder.
        interval : float, optional
            Member interval; disables the zoom ladder.
        color : str, optional
            Line and label colour.
        linewidth : float, optional
            Line width in points.
        alpha : float, optional
            Line and label alpha.
        labels : bool, optional
            Whether member values are labelled.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The isobar family artist.
        """
        return self._configure_family(
            "isobars",
            {
                "values": values,
                "interval": interval,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "labels": labels,
                "visible": visible,
            },
        )

    def dry_adiabats(  # noqa: PLR0913
        self,
        *,
        values: Iterable[float] | None = None,
        interval: float | None = None,
        color: str | None = None,
        linewidth: float | None = None,
        alpha: float | None = None,
        labels: bool | None = None,
        visible: bool | None = None,
    ) -> IsoplethFamily:
        """Return (and optionally reconfigure) the dry-adiabat family.

        With no arguments this returns the family artist unchanged; any
        keyword given reconfigures it first (spec §3.2). Values are
        potential temperatures in degrees Celsius.

        Parameters
        ----------
        values : iterable of float, optional
            Explicit member potential temperatures; disables the zoom
            ladder.
        interval : float, optional
            Member interval; disables the zoom ladder.
        color : str, optional
            Line and label colour.
        linewidth : float, optional
            Line width in points.
        alpha : float, optional
            Line and label alpha.
        labels : bool, optional
            Whether member values are labelled.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The dry-adiabat family artist.
        """
        return self._configure_family(
            "dry_adiabats",
            {
                "values": values,
                "interval": interval,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "labels": labels,
                "visible": visible,
            },
        )

    def moist_adiabats(  # noqa: PLR0913
        self,
        *,
        values: Iterable[float] | None = None,
        interval: float | None = None,
        truncation: float | None = None,
        color: str | None = None,
        linewidth: float | None = None,
        alpha: float | None = None,
        labels: bool | None = None,
        visible: bool | None = None,
    ) -> IsoplethFamily:
        """Return (and optionally reconfigure) the moist-adiabat family.

        With no arguments this returns the family artist unchanged; any
        keyword given reconfigures it first (spec §3.2). Values are
        wet-bulb potential temperatures in degrees Celsius.

        Parameters
        ----------
        values : iterable of float, optional
            Explicit member wet-bulb potential temperatures; disables the
            zoom ladder.
        interval : float, optional
            Member interval; disables the zoom ladder.
        truncation : float, optional
            Temperature (°C) below which the curves are truncated.
        color : str, optional
            Line and label colour.
        linewidth : float, optional
            Line width in points.
        alpha : float, optional
            Line and label alpha.
        labels : bool, optional
            Whether member values are labelled.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The moist-adiabat family artist.
        """
        return self._configure_family(
            "moist_adiabats",
            {
                "values": values,
                "interval": interval,
                "truncation": truncation,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "labels": labels,
                "visible": visible,
            },
        )

    def mixing_ratios(  # noqa: PLR0913
        self,
        *,
        values: Iterable[float] | None = None,
        color: str | None = None,
        linewidth: float | None = None,
        alpha: float | None = None,
        labels: bool | None = None,
        visible: bool | None = None,
    ) -> IsoplethFamily:
        """Return (and optionally reconfigure) the mixing-ratio family.

        With no arguments this returns the family artist unchanged; any
        keyword given reconfigures it first (spec §3.2). Values are
        humidity mixing ratios in g/kg; this family has no ``interval``
        (its members come from the ``MIXING_RATIO_VALUES`` ladder).

        Parameters
        ----------
        values : iterable of float, optional
            Explicit member mixing ratios; disables the zoom ladder.
        color : str, optional
            Line and label colour.
        linewidth : float, optional
            Line width in points.
        alpha : float, optional
            Line and label alpha.
        labels : bool, optional
            Whether member values are labelled.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The mixing-ratio family artist.
        """
        return self._configure_family(
            "mixing_ratios",
            {
                "values": values,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "labels": labels,
                "visible": visible,
            },
        )


register_projection(TephigramAxes)
