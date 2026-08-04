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

Side-of-axes layout contract (spec §10 item 7): panels beside the diagram
are appended with ``mpl_toolkits.axes_grid1``'s axes divider, which tracks
the equal-aspect box height — right side, inside-out: the wind-barb
gutter, then the indices panel. One divider is created per axes, cached,
and shared by every side-panel method; ``_relayout_side_panels`` rebuilds
the divider's horizontal stack and reassigns every locator whenever a
panel appears, so the inside-out order holds regardless of the order the
panel methods are called in (spec §3.2).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Final, cast, overload
import warnings

from matplotlib.axes import Axes
import matplotlib.colors as mcolors
from matplotlib.figure import FigureBase
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.projections import register_projection
from matplotlib.ticker import AutoLocator, NullLocator, ScalarFormatter
import matplotlib.transforms as mtransforms
from mpl_toolkits.axes_grid1 import axes_size, make_axes_locatable
import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._config import config
from tephpy._constants import (
    BARB_GUTTER_PAD,
    BARB_GUTTER_WIDTH,
    BARB_MIN_SEPARATION,
    BARB_STAFF_POSITION,
    CAPE_COLOR,
    CIN_COLOR,
    CURSOR_FIELDS,
    DEFAULT_EXTENT,
    EDGE_AXIS_TITLES,
    EDGE_LABEL_GUTTER_PAD,
    EDGE_TICK_LENGTH,
    EDGE_TICK_PAD,
    INDICES_PANEL_FONTSIZE,
    INDICES_PANEL_PAD,
    INDICES_PANEL_ROWS,
    INDICES_PANEL_WIDTH,
    LABEL_FONTSIZE,
    PROFILE_DEWPOINT_COLOR,
    PROFILE_LINEWIDTH,
    PROFILE_TEMPERATURE_COLOR,
    PROFILE_ZORDER,
    SHADING_ALPHA,
    SHADING_ZORDER,
)
from tephpy._units import as_quantity, check_units_mapping
from tephpy.exceptions import MissingDataError
from tephpy.plotting import shading
from tephpy.plotting.barbs import BarbStaff
from tephpy.plotting.isopleths import (
    _FAMILY_SPECS,
    EDGES,
    IsoplethFamily,
    _EdgeFormatter,
    _EdgeLocator,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from matplotlib.axes._secondary_axes import SecondaryAxis
    from matplotlib.axis import Axis
    from matplotlib.lines import Line2D
    from mpl_toolkits.axes_grid1.axes_divider import AxesDivider

    from tephpy.calc import Profile, SoundingIndices
    from tephpy.plotting.isopleths import ResolvedOptions
    from tephpy.sounding import Sounding

__all__ = ["TephigramAxes", "TephigramInvertedTransform", "TephigramTransform"]

#: ``Figure.clear``'s frame, recognised so the side-panel teardown can
#: stand down for that caller (see ``TephigramAxes._figure_is_clearing``).
_FIGURE_CLEAR_CODE = FigureBase.clear.__code__


def _cursor_pressure(pressure: float, _temperature: float, _theta: float) -> str:
    """Format the cursor point's pressure (spec §3.2).

    Parameters
    ----------
    pressure : float
        Cursor pressure in hPa.
    _temperature : float
        Ignored; the uniform registry signature.
    _theta : float
        Ignored; the uniform registry signature.

    Returns
    -------
    str
        The pressure readout, whole hPa.
    """
    return f"{pressure:.0f} hPa"


def _cursor_temperature(_pressure: float, temperature: float, _theta: float) -> str:
    """Format the cursor point's temperature (spec §3.2).

    Parameters
    ----------
    _pressure : float
        Ignored; the uniform registry signature.
    temperature : float
        Cursor temperature in degrees Celsius.
    _theta : float
        Ignored; the uniform registry signature.

    Returns
    -------
    str
        The temperature readout, one decimal.
    """
    return f"{temperature:.1f} °C"


def _cursor_theta(_pressure: float, _temperature: float, theta: float) -> str:
    """Format the cursor point's potential temperature (spec §3.2).

    Parameters
    ----------
    _pressure : float
        Ignored; the uniform registry signature.
    _temperature : float
        Ignored; the uniform registry signature.
    theta : float
        Cursor potential temperature in degrees Celsius.

    Returns
    -------
    str
        The potential-temperature readout, one decimal.
    """
    return f"θ {theta:.1f} °C"


def _cursor_mixing_ratio(pressure: float, temperature: float, _theta: float) -> str:
    """Format the saturation mixing ratio through the cursor point (spec §3.2).

    Parameters
    ----------
    pressure : float
        Cursor pressure in hPa.
    temperature : float
        Cursor temperature in degrees Celsius.
    _theta : float
        Ignored; the uniform registry signature.

    Returns
    -------
    str
        The mixing-ratio readout in g/kg, one decimal, or ``""`` when
        undefined (total pressure is less than the saturation vapour
        pressure at that temperature).

    Notes
    -----
    MetPy is imported on first use; the first call has a small import cost.
    """
    # Function-local so `import tephpy` stays light (spec §10 item 10).
    from metpy.calc import saturation_mixing_ratio  # noqa: PLC0415
    from metpy.units import units as registry  # noqa: PLC0415

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        warnings.simplefilter("ignore", RuntimeWarning)
        ratio = saturation_mixing_ratio(
            registry.Quantity(pressure, "hPa"), registry.Quantity(temperature, "degC")
        ).m_as("g/kg")
    if not math.isfinite(float(ratio)):
        return ""
    return f"{float(ratio):.1f} g/kg"


def _cursor_theta_w(pressure: float, temperature: float, _theta: float) -> str:
    """Format the moist adiabat (θw) through the cursor point (spec §3.2).

    The point is treated as saturated (``dewpoint=temperature``), giving
    the wet-bulb potential temperature of the pseudoadiabat through it —
    the moist-adiabat family's member value (the spec §3.2/§3.3
    one-source-of-truth idiom).

    Parameters
    ----------
    pressure : float
        Cursor pressure in hPa.
    temperature : float
        Cursor temperature in degrees Celsius.
    _theta : float
        Ignored; the uniform registry signature.

    Returns
    -------
    str
        The wet-bulb potential-temperature readout, one decimal, or ``""``
        when undefined (total pressure is less than the saturation vapour
        pressure at that temperature).

    Notes
    -----
    MetPy is imported on first use; the first call has a small import cost.
    ``theta_w`` integrates the pseudoadiabat numerically per event.
    """
    # Function-local so `import tephpy` stays light (spec §10 item 10).
    from metpy.calc import wet_bulb_potential_temperature  # noqa: PLC0415
    from metpy.units import units as registry  # noqa: PLC0415

    quantity = registry.Quantity
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        warnings.simplefilter("ignore", RuntimeWarning)
        theta_w = wet_bulb_potential_temperature(
            quantity(pressure, "hPa"),
            quantity(temperature, "degC"),
            quantity(temperature, "degC"),
        ).m_as("degC")
    if not math.isfinite(float(theta_w)):
        return ""
    return f"θw {float(theta_w):.1f} °C"


#: The cursor readout field registry (spec §3.2): field name to a
#: ``(pressure, temperature, theta) -> str`` formatter.
_CURSOR_FORMATTERS: Final[dict[str, Callable[[float, float, float], str]]] = {
    "pressure": _cursor_pressure,
    "temperature": _cursor_temperature,
    "theta": _cursor_theta,
    "mixing_ratio": _cursor_mixing_ratio,
    "theta_w": _cursor_theta_w,
}


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
    x/y ticks carry no meteorological meaning and are hidden until
    a family claims an edge for its labels — ``labels=("bottom", "left")``
    turns them into that family's scale (spec §3.2).
    """

    name = "tephigram"

    tephigram_transform: TephigramTransform
    _families: dict[str, IsoplethFamily]
    _indices_panel: Axes | None
    _barb_gutter: Axes | None
    _side_divider: AxesDivider | None
    _edge_owners: dict[str, str]
    _secondary_axes: dict[str, SecondaryAxis]
    _edge_titles: dict[str, str]
    #: The owner and RGBA last applied to each claimed edge's ticks, so a
    #: sync re-applies only what the owning family actually changed.
    #: Survives release, which is what makes a family visibility toggle a
    #: true round trip; the owner is part of the key so a new owner's colour
    #: still lands when it matches the last one's. Only :meth:`clear` empties
    #: it (spec §3.2).
    _edge_tick_colors: dict[str, tuple[str, tuple[float, float, float, float]]]
    #: Re-entrancy guard for ``_sync_edge_labels``; a class default so it is
    #: live before ``Axes.__init__`` reaches :meth:`clear`.
    _edge_sync_busy: bool = False

    def clear(self) -> None:
        """Reset the axes to the tephigram projection defaults.

        Matplotlib calls this during ``Axes.__init__`` and on user
        ``ax.clear()``; both paths recreate the projection-owned state:
        the tephigram transform, equal aspect, hidden native axes, the
        five background isopleth families, any edges they claim for their
        labels, and the default extent
        (``tephpy.config`` diagram extent, else ``DEFAULT_EXTENT``).
        Side panels — the barb gutter and the indices panel — are
        removed with the diagram they annotated, except when the figure
        is clearing itself: it removes every axes anyway, and it is
        iterating a snapshot this one must not delete from.

        Raises
        ------
        TypeError
            If ``tephpy.config`` gives one diagram edge to two families, or
            names an unknown label placement, or carries a malformed family
            ``emphasis`` — a non-mapping, a member value that will not convert
            to float, a style that is not a mapping, or an unknown style key
            (spec §3.2).
        ValueError
            If a ``tephpy.config`` family ``emphasis`` keys a member value
            that is not finite, or gives a ``linewidth`` that is not positive
            and finite, or an ``alpha`` outside ``[0, 1]``, or a family
            ``interval`` is not positive and finite.
        """
        super().clear()
        self.tephigram_transform = TephigramTransform()
        self.set_aspect(1.0, adjustable="box")
        self.xaxis.set_visible(False)
        self.yaxis.set_visible(False)
        # Presentation is stamped once, here, and never re-asserted, so it is
        # the user's from a claim onwards (spec §3.2).
        self._style_edge_axis(self.xaxis)
        self._style_edge_axis(self.yaxis)
        # The classic style mirrors ticks onto the opposite edge, which would
        # collide with that edge's own family. Pinned on the concrete
        # ``XAxis``/``YAxis``, whose ``set_ticks_position`` take different
        # values, rather than through the ``Axis``-typed helper above.
        self.xaxis.set_ticks_position("bottom")
        self.yaxis.set_ticks_position("left")
        slots = ("_barb_gutter", "_indices_panel")
        panels = [getattr(self, name, None) for name in slots]
        if any(panel is not None for panel in panels):
            if not self._figure_is_clearing():
                for panel in panels:
                    if panel is not None:
                        panel.remove()
            # The stub demands a callable, but None resets the locator
            # (the documented matplotlib behaviour).
            self.set_axes_locator(None)  # type: ignore[arg-type]
        self._indices_panel = None
        self._barb_gutter = None
        self._side_divider = None
        self._edge_owners = {}
        self._secondary_axes = {}
        self._edge_titles = {}
        self._edge_tick_colors = {}
        self._families = {}
        for name, spec in _FAMILY_SPECS.items():
            # The families arm their ``on_change`` only once constructed, so
            # this loop builds all five before the first sync sees any.
            family = IsoplethFamily(
                spec,
                getattr(config, name),
                validate=self._check_label_edges,
                on_change=self._sync_edge_labels,
            )
            self.add_artist(family)
            self._families[name] = family
        self._sync_edge_labels()
        extent = config.diagram.extent
        self.set_extent(DEFAULT_EXTENT if extent is None else extent)

    def _figure_is_clearing(self) -> bool:
        """Whether the enclosing figure is the caller of :meth:`clear`.

        ``Figure.clear`` clears and deletes each entry of a snapshot of
        ``figure.axes``, so an axes that removes a sibling from inside
        its own ``clear`` orphans an entry matplotlib is still about to
        visit — the panel is then cleared and deleted with no figure,
        raising deep in matplotlib. The side panels are the diagram's to
        remove on a direct ``ax.clear()``; on a figure clear they are the
        figure's, so the teardown stands down (spec §3.2). Recognising
        the caller by its frame is the only signal: the figure's state is
        identical either way.

        Returns
        -------
        bool
            Whether a ``Figure.clear`` of this axes' figure is running.
        """
        figure = self.get_figure(root=False)
        if figure is None:
            return False
        # Function-local so `import tephpy` stays light (spec §10 item 10).
        import inspect  # noqa: PLC0415

        frame = inspect.currentframe()
        while frame is not None:
            if (
                frame.f_code is _FIGURE_CLEAR_CODE
                and frame.f_locals.get("self") is figure
            ):
                return True
            frame = frame.f_back
        return False

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

    def format_coord(self, x: float, y: float) -> str:
        """Report diagram-meaningful values for the cursor position (spec §3.2).

        The navigation toolbar's readout: the data-space cursor position
        inverts to (temperature, theta), pressure derives via Poisson's
        equation, and the configured fields render in listed order, e.g.
        ``850 hPa, -4.2 °C, θ 8.6 °C``. Fields resolve as instance
        assignment > ``tephpy.config`` > ``_constants``: assigning
        ``ax.format_coord = fn`` (stock matplotlib) shadows this method
        entirely, and ``config.cursor.fields`` is read live on every call,
        so a ``config.context(cursor={"fields": ...})`` override applies to
        existing axes for its duration (spec §3.5). Fields whose value is
        undefined at the point are omitted from the readout.

        Parameters
        ----------
        x : float
            Cursor x in tephigram data space.
        y : float
            Cursor y in tephigram data space.

        Returns
        -------
        str
            The formatted readout, or ``""`` when the position is
            unphysical (e.g. left of the -273.15 °C isotherm).

        Raises
        ------
        TypeError
            If ``config.cursor.fields`` is a bare string rather than a
            tuple of field names, or names an unknown field.
        """
        fields = config.cursor.fields
        if fields is None:
            fields = CURSOR_FIELDS
        _fields_obj: object = fields
        if isinstance(_fields_obj, str):
            msg = (
                f"cursor fields must be a tuple of field names, not a bare string: "
                f"pass ({_fields_obj!r},)"
            )
            raise TypeError(msg)
        unknown = set(fields) - set(_CURSOR_FORMATTERS)
        if unknown:
            msg = (
                f"unknown cursor field(s) {sorted(unknown)!r}; "
                f"expected {sorted(_CURSOR_FORMATTERS)!r}"
            )
            raise TypeError(msg)
        temperature, theta = transforms.temperature_theta_from_xy(x, y)
        pressure = transforms.pressure_from_temperature_theta(temperature, theta)
        p, t, th = float(pressure), float(temperature), float(theta)
        finite = math.isfinite(p) and math.isfinite(t) and math.isfinite(th)
        if not (finite and p > 0.0):
            return ""
        return ", ".join(
            part
            for part in (_CURSOR_FORMATTERS[name](p, t, th) for name in fields)
            if part
        )

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

    def _append_side_axes(
        self,
        *,
        width: str,
        pad: float,
        **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
    ) -> Axes:
        """Append one side panel through the shared, cached divider.

        The divider is created on first use and reused by every
        side-panel method — a second ``make_axes_locatable`` call would
        build a fresh divider and detach the earlier panel (spec §3.2).
        The caller stores the returned axes on its slot attribute and
        must call :meth:`_relayout_side_panels` afterwards.

        Parameters
        ----------
        width : str
            The panel width, as an ``axes_grid1`` size (e.g. ``"35%"``).
        pad : float
            The panel padding from the diagram, in inches.
        **kwargs : Any
            Passed through to the axes constructor (e.g. ``sharey=``).

        Returns
        -------
        matplotlib.axes.Axes
            The appended plain axes.
        """
        if self._side_divider is None:
            self._side_divider = make_axes_locatable(self)
        return cast(
            "Axes",
            self._side_divider.append_axes(
                "right", size=width, pad=pad, axes_class=Axes, **kwargs
            ),
        )

    def _relayout_side_panels(self) -> None:
        """Rebuild the divider stack in the contracted inside-out order.

        ``append_axes`` stacks panels in call order; this rebuilds the
        divider's horizontal sizes as diagram, barb gutter, indices
        panel — skipping absent panels — and reassigns every locator, so
        the spec §3.2 order holds regardless of the order the panel
        methods were called in. The panel nearest the diagram takes
        ``EDGE_LABEL_GUTTER_PAD`` in place of its own pad while the right
        edge carries isopleth ticks, which are wider than the 0.1 in
        conventions (spec §3.2).
        """
        divider = self._side_divider
        if divider is None:
            return
        horizontal = [axes_size.AxesX(self)]
        slots: list[tuple[Axes, int]] = []
        panels: tuple[tuple[Axes | None, float, str], ...] = (
            (self._barb_gutter, BARB_GUTTER_PAD, BARB_GUTTER_WIDTH),
            (self._indices_panel, INDICES_PANEL_PAD, INDICES_PANEL_WIDTH),
        )
        right_labelled = "right" in self._edge_owners
        for panel, pad, width in panels:
            if panel is None:
                continue
            # The first panel abuts the diagram, so it is the one the right
            # edge's tick labels would land on (spec §3.2).
            gap = EDGE_LABEL_GUTTER_PAD if right_labelled and not slots else pad
            horizontal.append(axes_size.Fixed(gap))
            horizontal.append(axes_size.from_any(width, fraction_ref=horizontal[0]))
            slots.append((panel, len(horizontal) - 1))
        divider.set_horizontal(horizontal)
        self.set_axes_locator(divider.new_locator(nx=0, ny=0))
        for panel, nx in slots:
            panel.set_axes_locator(divider.new_locator(nx=nx, ny=0))

    def edge_axis(self, edge: str) -> Axis:
        """Return the matplotlib axis drawing one diagram edge's ticks.

        The uniform handle on all four edges (spec §3.2), keyed by the same
        names the ``labels`` option takes. Bottom and left are the axes' own
        ``xaxis``/``yaxis``; top and right belong to a secondary axes that
        has no other public handle. tephpy stamps its tick conventions on an
        edge axis once, when that axis is created, so everything stock
        matplotlib offers is the caller's from the claim onwards — e.g.
        ``ax.edge_axis("top").set_tick_params(labelsize=12)``, or
        ``set_label_text("")`` to keep the ticks and drop the axis title.
        The only thing tephpy changes afterwards is the tick colour, and
        only when the owning family's own colour or alpha changes, or
        another family takes the edge.

        Parameters
        ----------
        edge : str
            The edge, one of ``EDGES``.

        Returns
        -------
        matplotlib.axis.Axis
            The axis drawing that edge's ticks.

        Raises
        ------
        TypeError
            If `edge` is not one of ``EDGES``.
        ValueError
            If no family labels that edge. An unclaimed edge renders
            nothing to style — bottom and left are hidden, and top and
            right have no axis yet — and probing one must not build a
            secondary axes nothing is using.
        """
        if edge not in EDGES:
            msg = f"unknown edge {edge!r}; expected one of {list(EDGES)!r}"
            raise TypeError(msg)
        if edge not in self._edge_owners:
            msg = (
                f"the {edge!r} edge carries no isopleth labels; claim it "
                f'first, e.g. ax.isobars(labels="{edge}") (spec §3.2)'
            )
            raise ValueError(msg)
        return self._edge_axis(edge)

    def _check_label_edges(self, name: str, options: ResolvedOptions) -> None:
        """Reject an edge claim another family already holds.

        The axes owns all five families, so it is the only place that can see
        a collision; handing this to each family as its validator puts the
        rejection inside ``IsoplethFamily.configure``'s rollback, and running
        it during family creation surfaces a ``tephpy.config`` conflict at
        axes creation rather than at first draw (spec §3.2).

        Parameters
        ----------
        name : str
            The family the candidate options belong to.
        options : ResolvedOptions
            The candidate options, not yet in force.

        Raises
        ------
        TypeError
            If another family already claims one of the candidate's edges.
        """
        claimed = set(options.label_edges)
        if not claimed:
            return
        for other_name, other in self._families.items():
            if other_name == name:
                continue
            clash = claimed & set(other.options.label_edges)
            if clash:
                msg = (
                    f"the {min(clash)!r} edge is already labelled by "
                    f"{other_name!r}: one family per edge, so release it "
                    f"before {name!r} can claim it (spec §3.2)"
                )
                raise TypeError(msg)

    def _style_edge_axis(self, axis: Axis) -> None:
        """Stamp the tephigram tick conventions on one edge axis.

        Applied once, when the axis comes into existence — :meth:`clear` for
        the axes' own ``xaxis``/``yaxis``, the lazy build in
        :meth:`_edge_axis` for a top or right secondary — and never
        re-applied, so a user's ``tick_params`` on a claimed edge survives
        every later family resolve (spec §3.2). Matplotlib offers no
        provenance on ``set_tick_params``, so *when* is the only guard
        available. The conventions replay onto the tick artists matplotlib
        rebuilds when a claim swaps the locator, because they live in the
        axis' ``_major_tick_kw``.

        Parameters
        ----------
        axis : matplotlib.axis.Axis
            The axis that draws one diagram edge's ticks.
        """
        axis.set_tick_params(
            labelsize=LABEL_FONTSIZE,
            length=EDGE_TICK_LENGTH,
            pad=EDGE_TICK_PAD,
        )
        # Lines of constant data-space x or y mean nothing on a tephigram: the
        # ticks are the crossings, not a scale to rule off. Suppressing here
        # lands after ``Axes.clear`` has read ``rcParams["axes.grid"]``, which
        # several styles set, so a style cannot smuggle them in — while an
        # explicit later ``ax.grid(True)`` is the user's call (spec §3.2).
        axis.grid(visible=False, which="both")

    def _edge_axis(self, edge: str) -> Axis:
        """Return the axis that draws one diagram edge's ticks.

        Bottom and left reclaim the axes' own hidden ``xaxis``/``yaxis``
        (spec §3.1); top and right take a secondary axis, created on first
        demand and cached. The identity transform keeps the secondary axis in
        the parent's data coordinates, which is what the crossings are in.

        Parameters
        ----------
        edge : str
            The edge, one of ``EDGES``.

        Returns
        -------
        matplotlib.axis.Axis
            The axis to point a locator and formatter at.
        """
        if edge == "bottom":
            return self.xaxis
        if edge == "left":
            return self.yaxis
        secondary = self._secondary_axes.get(edge)
        if secondary is None:
            identity = mtransforms.IdentityTransform()
            secondary = (
                self.secondary_xaxis("top", functions=identity)
                if edge == "top"
                else self.secondary_yaxis("right", functions=identity)
            )
            self._secondary_axes[edge] = secondary
            self._style_edge_axis(secondary.xaxis if edge == "top" else secondary.yaxis)
        return secondary.xaxis if edge == "top" else secondary.yaxis

    def _claim_edge(self, edge: str, name: str, *, first: bool) -> None:
        """Point one edge's ticks at a family. Idempotent.

        Identity only — locator, formatter, visibility, colour and title.
        How the ticks look is stamped once by :meth:`_style_edge_axis` when
        the edge axis is created and is the user's thereafter (spec §3.2).

        Parameters
        ----------
        edge : str
            The edge to claim, one of ``EDGES``.
        name : str
            The claiming family's accessor name, which keys both the axis
            titles and ``self._families``.
        first : bool
            Whether this claim is the edge's first under this owner — the
            edge was unowned, or another family held it and has just been
            released. Identity is installed only then; a repeat claim
            re-applies nothing but a changed colour (spec §3.2).
        """
        family = self._families[name]
        axis = self._edge_axis(edge)
        if first:
            locator = _EdgeLocator(family, edge)
            axis.set_major_locator(locator)
            axis.set_major_formatter(_EdgeFormatter(locator))
            # Crossings are exact positions; a minor tick between them means
            # nothing. NullLocator is also matplotlib's linear-axis default, so
            # release restores it.
            axis.set_minor_locator(NullLocator())
            # Visibility is identity, so a claim restores it on both paths:
            # the ``Axis`` on every edge, and for top or right the secondary
            # axes that hid with it, spine included. Showing the container
            # alone would leave an ``Axis`` the user had hidden drawing no
            # ticks on an edge that has just been claimed (spec §3.2).
            axis.set_visible(True)
            secondary = self._secondary_axes.get(edge)
            if secondary is not None:
                secondary.set_visible(True)
            if not axis.get_label_text():
                title = EDGE_AXIS_TITLES[name]
                axis.set_label_text(title)
                self._edge_titles[edge] = title
        # ``set_tick_params`` takes no alpha, and per-``Tick`` alpha would not
        # survive matplotlib rebuilding the tick artists on a locator change,
        # so the family's alpha is baked into the tick RGBA instead.
        # The memory is keyed by owner as well as RGBA: it survives release,
        # so a bare colour comparison would suppress a new owner's claim
        # whenever its colour matched the last owner's, leaving the ticks in
        # a colour that now ties them to nothing.
        rgba = mcolors.to_rgba(family.options.color, family.options.alpha)
        if self._edge_tick_colors.get(edge) != (name, rgba):
            axis.set_tick_params(color=rgba, labelcolor=rgba)
            self._edge_tick_colors[edge] = (name, rgba)

    def _release_edge(self, edge: str) -> None:
        """Return one edge to its unclaimed state.

        Teardown only: the locator and formatter go back to matplotlib's
        linear-axis defaults, tephpy's own axis title is cleared and
        forgotten, and the edge hides. Presentation is left exactly as it
        is — it belongs to the user, and the hidden axis renders none of it
        (spec §3.2).

        Parameters
        ----------
        edge : str
            The edge to release, one of ``EDGES``.
        """
        title = self._edge_titles.pop(edge, None)
        secondary = self._secondary_axes.get(edge)
        if secondary is None and edge in {"top", "right"}:
            # Never claimed, so there is no secondary axes to return; the
            # early exit also keeps ``_edge_axis`` below from building one.
            return
        axis = self._edge_axis(edge)
        if title is not None and axis.get_label_text() == title:
            axis.set_label_text("")
        axis.set_major_locator(AutoLocator())
        axis.set_major_formatter(ScalarFormatter())
        axis.set_minor_locator(NullLocator())
        if secondary is None:
            axis.set_visible(False)
        else:
            # The whole secondary axes hides, not merely its ``Axis``, or the
            # spine it owns would keep drawing. It is kept, not removed, so a
            # handle held across a release stays live and its ticks and title
            # survive the reclaim exactly as bottom and left do (spec §3.2).
            secondary.set_visible(False)

    def _sync_edge_labels(self) -> None:
        """Match the claimed edges to what the five families now ask for.

        Every successful family resolve lands here — the accessors, a direct
        :meth:`~tephpy.plotting.isopleths.IsoplethFamily.configure`, an
        ``Artist.set_visible`` — plus the end of :meth:`clear`. Ownership
        conflicts were already rejected by :meth:`_check_label_edges`, so this
        only applies the outcome. A change on the right edge also relayouts the
        side panels, whose pad widens to clear the tick labels (spec §3.2).

        Nothing on this path resolves a family's options, so a nested call
        would have nothing new to apply; the guard makes that structural rather
        than a standing assumption about matplotlib's axis internals.
        """
        if self._edge_sync_busy:
            return
        self._edge_sync_busy = True
        try:
            claims: dict[str, str] = {}
            for name, family in self._families.items():
                for edge in family.options.label_edges:
                    claims[edge] = name
            had_right = "right" in self._edge_owners
            for edge in EDGES:
                owner = claims.get(edge)
                previous = self._edge_owners.get(edge)
                if previous not in (None, owner):
                    self._release_edge(edge)
                if owner is None:
                    self._edge_owners.pop(edge, None)
                else:
                    self._edge_owners[edge] = owner
                    self._claim_edge(edge, owner, first=previous != owner)
            if had_right != ("right" in self._edge_owners):
                self._relayout_side_panels()
        finally:
            self._edge_sync_busy = False

    def plot_barbs(
        self,
        snd: Sounding,
        *,
        x: float | None = None,
        minimum_separation: float | None = None,
        **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
    ) -> BarbStaff:
        """Plot the sounding's wind barbs on the gutter staff (spec §3.2).

        The barbs draw on a right-hand gutter appended with the shared
        divider, each level at the y where its isobar meets the
        diagram's right edge (the printed-form staff convention),
        thinned per draw to a minimum vertical separation — zooming in
        reveals more levels. Met Office symbology: flag 50 kt, full barb
        10 kt, half barb 5 kt, speeds rounded to 5 kt bins; calm levels
        render as matplotlib's small circle. Each call draws one staff:
        overlay soundings by calling again with another `x`,
        `minimum_separation`, and colour.

        Parameters
        ----------
        snd : Sounding
            The sounding to plot; must carry wind.
        x : float, optional
            The staff position as a fraction across the gutter
            (default ``BARB_STAFF_POSITION``).
        minimum_separation : float, optional
            The minimum vertical separation between drawn barbs, in
            points (default ``BARB_MIN_SEPARATION``) — a longer
            ``length=`` glyph wants a wider separation.
        **kwargs : Any
            Passed through to :class:`matplotlib.quiver.Barbs`, over
            the ``_constants`` conventions (increments, rounding,
            length).

        Returns
        -------
        BarbStaff
            The zoom-aware staff artist; its ``barbs`` property is the
            underlying matplotlib collection.

        Raises
        ------
        MissingDataError
            If the sounding has no wind (spec §6).
        """
        if snd.wind_speed is None or snd.wind_direction is None:
            msg = "plot_barbs() needs wind: this sounding has none (spec §3.4)"
            raise MissingDataError(msg)
        # Function-local so `import tephpy` stays light (spec §10 item 10).
        from metpy.calc import wind_components  # noqa: PLC0415

        u, v = wind_components(snd.wind_speed, snd.wind_direction)
        if self._barb_gutter is None:
            gutter = self._append_side_axes(
                width=BARB_GUTTER_WIDTH, pad=BARB_GUTTER_PAD, sharey=self
            )
            gutter.set_xlim(0.0, 1.0)
            gutter.set_axis_off()
            self._barb_gutter = gutter
            self._relayout_side_panels()
        staff = BarbStaff(
            self,
            snd.pressure.m_as("hPa"),
            np.asarray(u.m_as("knots"), dtype=np.float64),
            np.asarray(v.m_as("knots"), dtype=np.float64),
            x=BARB_STAFF_POSITION if x is None else float(x),
            minimum_separation=(
                BARB_MIN_SEPARATION
                if minimum_separation is None
                else float(minimum_separation)
            ),
            **kwargs,
        )
        self._barb_gutter.add_artist(staff)
        return staff

    def annotate_indices(self, indices: SoundingIndices) -> Axes:
        """Display derived parameters in a panel beside the diagram.

        The first consumer of the side-of-axes contract (spec §3.2):
        the panel is appended with the ``axes_grid1`` divider, one
        formatted line per ``SoundingIndices`` field, NaN rendered as an
        em dash. Calling it again updates the panel in place rather than
        stacking a second one, and the side-panel layout is rebuilt
        inside-out (barb gutter, then this panel) whichever order the
        panel methods are called in (spec §3.2).

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
            self._indices_panel = self._append_side_axes(
                width=INDICES_PANEL_WIDTH, pad=INDICES_PANEL_PAD
            )
            self._relayout_side_panels()
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

        The family's own ``on_change`` runs :meth:`_sync_edge_labels`, so a
        claim made here reaches the edges by the same route a direct
        ``family.configure(...)`` takes (spec §3.2).

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

        Raises
        ------
        TypeError
            If an option name or ``labels`` placement is unknown, or if another
            family already claims a requested edge.
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
        labels: bool | str | tuple[str, ...] | None = None,
        emphasis: Mapping[float, Mapping[str, object]] | None = None,
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
        labels : bool or str or tuple of str, optional
            Where member values are labelled: ``True`` (every member inline —
            the default), ``False`` (none), or the diagram edge names
            ``"bottom"``, ``"top"``, ``"left"`` and ``"right"``, singly or as a
            tuple. Listed edges label the members that reach them; every member
            left over is labelled inline. One family per edge. An edge crowded
            by closely spaced members is thinned with ``interval=``; edge
            labelling never drops a member's label itself.
        emphasis : mapping of float to mapping, optional
            Members to distinguish, keyed by member value in degrees Celsius.
            Each value is a mapping of style overrides — ``color``,
            ``linewidth``, ``linestyle``, ``alpha`` — and an omitted key falls
            back to the family's own style, so ``{0.0: {}}`` draws that member
            at ``EMPHASIS_LINEWIDTH`` in the family's own colour. An emphasised
            member is always drawn, whatever the zoom ladder would select, so a
            value the interval never lands on still appears. An empty mapping
            emphasises nothing.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The isotherm family artist.

        Raises
        ------
        TypeError
            If ``labels`` names an unknown placement, ``emphasis`` is malformed,
            or an edge another family already claims.
        ValueError
            If an ``emphasis`` member value is not finite, a ``linewidth`` is
            not positive and finite, an ``alpha`` falls outside ``[0, 1]``, or
            ``interval`` is not positive and finite.
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
                "emphasis": emphasis,
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
        labels: bool | str | tuple[str, ...] | None = None,
        emphasis: Mapping[float, Mapping[str, object]] | None = None,
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
        labels : bool or str or tuple of str, optional
            Where member values are labelled: ``True`` (every member inline —
            the default), ``False`` (none), or the diagram edge names
            ``"bottom"``, ``"top"``, ``"left"`` and ``"right"``, singly or as a
            tuple. Listed edges label the members that reach them; every member
            left over is labelled inline. One family per edge. An edge crowded
            by closely spaced members is thinned with ``interval=``; edge
            labelling never drops a member's label itself.
        emphasis : mapping of float to mapping, optional
            Members to distinguish, keyed by member value in hPa.
            Each value is a mapping of style overrides — ``color``,
            ``linewidth``, ``linestyle``, ``alpha`` — and an omitted key falls
            back to the family's own style, so ``{500.0: {}}`` draws that member
            at ``EMPHASIS_LINEWIDTH`` in the family's own colour. An emphasised
            member is always drawn, whatever the zoom ladder would select, so a
            value the interval never lands on still appears. An empty mapping
            emphasises nothing.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The isobar family artist.

        Raises
        ------
        TypeError
            If ``labels`` names an unknown placement, ``emphasis`` is malformed,
            or an edge another family already claims.
        ValueError
            If an ``emphasis`` member value is not finite, a ``linewidth`` is
            not positive and finite, an ``alpha`` falls outside ``[0, 1]``, or
            ``interval`` is not positive and finite.
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
                "emphasis": emphasis,
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
        labels: bool | str | tuple[str, ...] | None = None,
        emphasis: Mapping[float, Mapping[str, object]] | None = None,
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
        labels : bool or str or tuple of str, optional
            Where member values are labelled: ``True`` (every member inline —
            the default), ``False`` (none), or the diagram edge names
            ``"bottom"``, ``"top"``, ``"left"`` and ``"right"``, singly or as a
            tuple. Listed edges label the members that reach them; every member
            left over is labelled inline. One family per edge. An edge crowded
            by closely spaced members is thinned with ``interval=``; edge
            labelling never drops a member's label itself.
        emphasis : mapping of float to mapping, optional
            Members to distinguish, keyed by member value in degrees Celsius.
            Each value is a mapping of style overrides — ``color``,
            ``linewidth``, ``linestyle``, ``alpha`` — and an omitted key falls
            back to the family's own style, so ``{0.0: {}}`` draws that member
            at ``EMPHASIS_LINEWIDTH`` in the family's own colour. An emphasised
            member is always drawn, whatever the zoom ladder would select, so a
            value the interval never lands on still appears. An empty mapping
            emphasises nothing.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The dry-adiabat family artist.

        Raises
        ------
        TypeError
            If ``labels`` names an unknown placement, ``emphasis`` is malformed,
            or an edge another family already claims.
        ValueError
            If an ``emphasis`` member value is not finite, a ``linewidth`` is
            not positive and finite, an ``alpha`` falls outside ``[0, 1]``, or
            ``interval`` is not positive and finite.
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
                "emphasis": emphasis,
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
        labels: bool | str | tuple[str, ...] | None = None,
        emphasis: Mapping[float, Mapping[str, object]] | None = None,
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
        labels : bool or str or tuple of str, optional
            Where member values are labelled: ``True`` (every member inline —
            the default), ``False`` (none), or the diagram edge names
            ``"bottom"``, ``"top"``, ``"left"`` and ``"right"``, singly or as a
            tuple. Listed edges label the members that reach them; every member
            left over is labelled inline. One family per edge. An edge crowded
            by closely spaced members is thinned with ``interval=``; edge
            labelling never drops a member's label itself.
        emphasis : mapping of float to mapping, optional
            Members to distinguish, keyed by member value in degrees Celsius.
            Each value is a mapping of style overrides — ``color``,
            ``linewidth``, ``linestyle``, ``alpha`` — and an omitted key falls
            back to the family's own style, so ``{0.0: {}}`` draws that member
            at ``EMPHASIS_LINEWIDTH`` in the family's own colour. An emphasised
            member is always drawn, whatever the zoom ladder would select, so a
            value the interval never lands on still appears. An empty mapping
            emphasises nothing.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The moist-adiabat family artist.

        Raises
        ------
        TypeError
            If ``labels`` names an unknown placement, ``emphasis`` is malformed,
            or an edge another family already claims.
        ValueError
            If an ``emphasis`` member value is not finite, a ``linewidth`` is
            not positive and finite, an ``alpha`` falls outside ``[0, 1]``, or
            ``interval`` is not positive and finite.
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
                "emphasis": emphasis,
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
        labels: bool | str | tuple[str, ...] | None = None,
        emphasis: Mapping[float, Mapping[str, object]] | None = None,
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
        labels : bool or str or tuple of str, optional
            Where member values are labelled: ``True`` (every member inline —
            the default), ``False`` (none), or the diagram edge names
            ``"bottom"``, ``"top"``, ``"left"`` and ``"right"``, singly or as a
            tuple. Listed edges label the members that reach them; every member
            left over is labelled inline. One family per edge. An edge crowded
            by a large member set is thinned with ``values=``; edge labelling
            never drops a member's label itself.
        emphasis : mapping of float to mapping, optional
            Members to distinguish, keyed by member value in g/kg.
            Each value is a mapping of style overrides — ``color``,
            ``linewidth``, ``linestyle``, ``alpha`` — and an omitted key falls
            back to the family's own style, so ``{5.0: {}}`` draws that member
            at ``EMPHASIS_LINEWIDTH`` in the family's own colour. An emphasised
            member is always drawn, whatever the zoom ladder would select, so a
            value the ladder never selects still appears. An empty mapping
            emphasises nothing.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The mixing-ratio family artist.

        Raises
        ------
        TypeError
            If ``labels`` names an unknown placement, ``emphasis`` is malformed,
            or an edge another family already claims.
        ValueError
            If an ``emphasis`` member value is not finite, a ``linewidth`` is
            not positive and finite, or an ``alpha`` falls outside ``[0, 1]``.
        """
        return self._configure_family(
            "mixing_ratios",
            {
                "values": values,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "labels": labels,
                "emphasis": emphasis,
                "visible": visible,
            },
        )


register_projection(TephigramAxes)
