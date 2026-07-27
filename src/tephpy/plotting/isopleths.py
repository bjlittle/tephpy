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
import math
from typing import TYPE_CHECKING, Final, cast

from matplotlib import artist as martist
from matplotlib.collections import LineCollection
from matplotlib.text import Text
import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._constants import (
    DRY_ADIABAT_COLOR,
    DRY_ADIABAT_STEPS,
    DRY_ADIABAT_ZORDER,
    ISOBAR_COLOR,
    ISOBAR_STEPS,
    ISOBAR_ZORDER,
    ISOPLETH_ALPHA,
    ISOPLETH_LINEWIDTH,
    ISOPLETH_SAMPLES,
    ISOTHERM_COLOR,
    ISOTHERM_STEPS,
    ISOTHERM_ZORDER,
    LABEL_BOX_ALPHA,
    LABEL_BOX_COLOR,
    LABEL_BOXSTYLE,
    LABEL_FONTSIZE,
    MIXING_RATIO_COLOR,
    MIXING_RATIO_STRIDES,
    MIXING_RATIO_VALUES,
    MIXING_RATIO_ZORDER,
    MOIST_ADIABAT_COLOR,
    MOIST_ADIABAT_DOMAIN,
    MOIST_ADIABAT_PRESSURE_STEP,
    MOIST_ADIABAT_STEPS,
    MOIST_ADIABAT_TRUNCATION,
    MOIST_ADIABAT_ZORDER,
    P_REF,
    PRESSURE_DOMAIN,
    TEMPERATURE_DOMAIN,
    THETA_DOMAIN,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import SupportsFloat

    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    import matplotlib.transforms as mtransforms

__all__ = [
    "FamilySpec",
    "IsoplethFamily",
    "Member",
    "ResolvedOptions",
    "dry_adiabat_members",
    "isobar_members",
    "isotherm_members",
    "mixing_ratio_members",
    "moist_adiabat_members",
]

#: Options that require rebuilding the cached member geometry when changed.
_GEOMETRY_KEYS: Final[frozenset[str]] = frozenset({"values", "interval", "truncation"})

#: Style and visibility options shared by every family.
_STYLE_KEYS: Final[frozenset[str]] = frozenset(
    {"color", "linewidth", "alpha", "labels", "visible"}
)

#: Options accepted by the interval-based families.
_INTERVAL_KEYS: Final[frozenset[str]] = _STYLE_KEYS | {"values", "interval"}


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
    values : ArrayLike
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
    values : ArrayLike
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
    values : ArrayLike
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
    values : ArrayLike
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
    values : ArrayLike
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


@dataclasses.dataclass(frozen=True)
class ResolvedOptions:
    """A family's fully resolved settings snapshot.

    Resolution precedence: accessor kwargs > ``tephpy.config`` >
    ``_constants`` (spec §3.5). ``values``/``interval`` of ``None`` mean the
    zoom-adaptive default ladder is in force.
    """

    values: tuple[float, ...] | None
    interval: float | None
    truncation: float | None
    color: str
    linewidth: float
    alpha: float
    labels: bool
    visible: bool


@dataclasses.dataclass(frozen=True)
class FamilySpec:
    """Static wiring of one isopleth family: builder plus conventions.

    Exactly one of (``domain`` + ``steps``) for interval families or
    (``values`` + ``strides``) for list families is set.
    """

    name: str
    builder: Callable[[npt.NDArray[np.float64], float | None], list[Member]]
    allowed: frozenset[str]
    color: str
    zorder: float
    domain: tuple[float, float] | None = None
    steps: tuple[tuple[float, float], ...] | None = None
    strides: tuple[tuple[float, int], ...] | None = None
    values: tuple[float, ...] | None = None
    truncation: float | None = None


def _build_isotherms(
    values: npt.NDArray[np.float64], _truncation: float | None
) -> list[Member]:
    """Adapt :func:`isotherm_members` to the uniform builder signature.

    Parameters
    ----------
    values : numpy.ndarray
        Member temperatures in degrees Celsius.
    _truncation : float or None
        Ignored; only meaningful for the moist adiabats.

    Returns
    -------
    list of Member
        The family members.
    """
    return isotherm_members(values)


def _build_dry_adiabats(
    values: npt.NDArray[np.float64], _truncation: float | None
) -> list[Member]:
    """Adapt :func:`dry_adiabat_members` to the uniform builder signature.

    Parameters
    ----------
    values : numpy.ndarray
        Member potential temperatures in degrees Celsius.
    _truncation : float or None
        Ignored; only meaningful for the moist adiabats.

    Returns
    -------
    list of Member
        The family members.
    """
    return dry_adiabat_members(values)


def _build_isobars(
    values: npt.NDArray[np.float64], _truncation: float | None
) -> list[Member]:
    """Adapt :func:`isobar_members` to the uniform builder signature.

    Parameters
    ----------
    values : numpy.ndarray
        Member pressures in hPa.
    _truncation : float or None
        Ignored; only meaningful for the moist adiabats.

    Returns
    -------
    list of Member
        The family members.
    """
    return isobar_members(values)


def _build_moist_adiabats(
    values: npt.NDArray[np.float64], truncation: float | None
) -> list[Member]:
    """Adapt :func:`moist_adiabat_members` to the uniform builder signature.

    Parameters
    ----------
    values : numpy.ndarray
        Member wet-bulb potential temperatures in degrees Celsius.
    truncation : float or None
        Truncation temperature in degrees Celsius; ``None`` selects the
        ``MOIST_ADIABAT_TRUNCATION`` convention.

    Returns
    -------
    list of Member
        The family members.
    """
    resolved = MOIST_ADIABAT_TRUNCATION if truncation is None else truncation
    return moist_adiabat_members(values, resolved)


def _build_mixing_ratios(
    values: npt.NDArray[np.float64], _truncation: float | None
) -> list[Member]:
    """Adapt :func:`mixing_ratio_members` to the uniform builder signature.

    Parameters
    ----------
    values : numpy.ndarray
        Member humidity mixing ratios in g/kg.
    _truncation : float or None
        Ignored; only meaningful for the moist adiabats.

    Returns
    -------
    list of Member
        The family members.
    """
    return mixing_ratio_members(values)


#: The five families, keyed by accessor name (spec §10 item 6).
_FAMILY_SPECS: Final[dict[str, FamilySpec]] = {
    "isotherms": FamilySpec(
        name="isotherms",
        builder=_build_isotherms,
        allowed=_INTERVAL_KEYS,
        color=ISOTHERM_COLOR,
        zorder=ISOTHERM_ZORDER,
        domain=TEMPERATURE_DOMAIN,
        steps=ISOTHERM_STEPS,
    ),
    "dry_adiabats": FamilySpec(
        name="dry_adiabats",
        builder=_build_dry_adiabats,
        allowed=_INTERVAL_KEYS,
        color=DRY_ADIABAT_COLOR,
        zorder=DRY_ADIABAT_ZORDER,
        domain=THETA_DOMAIN,
        steps=DRY_ADIABAT_STEPS,
    ),
    "isobars": FamilySpec(
        name="isobars",
        builder=_build_isobars,
        allowed=_INTERVAL_KEYS,
        color=ISOBAR_COLOR,
        zorder=ISOBAR_ZORDER,
        domain=PRESSURE_DOMAIN,
        steps=ISOBAR_STEPS,
    ),
    "moist_adiabats": FamilySpec(
        name="moist_adiabats",
        builder=_build_moist_adiabats,
        allowed=_INTERVAL_KEYS | {"truncation"},
        color=MOIST_ADIABAT_COLOR,
        zorder=MOIST_ADIABAT_ZORDER,
        domain=MOIST_ADIABAT_DOMAIN,
        steps=MOIST_ADIABAT_STEPS,
        truncation=MOIST_ADIABAT_TRUNCATION,
    ),
    "mixing_ratios": FamilySpec(
        name="mixing_ratios",
        builder=_build_mixing_ratios,
        allowed=_STYLE_KEYS | {"values"},
        color=MIXING_RATIO_COLOR,
        zorder=MIXING_RATIO_ZORDER,
        strides=MIXING_RATIO_STRIDES,
        values=MIXING_RATIO_VALUES,
    ),
}


class IsoplethFamily(martist.Artist):
    """One zoom-aware background isopleth family (spec §3.2).

    Member polylines are built lazily on first draw and cached; each draw
    clips the cache to the current view rectangle, selects the members
    appropriate to the zoom level via the family's convention ladder, and
    re-places the member labels. Settings resolve as accessor kwargs >
    ``tephpy.config`` > ``_constants``, read when the family is created or
    reconfigured (spec §3.5); explicit ``values`` or ``interval`` fixes the
    member set and disables the zoom ladder.

    Parameters
    ----------
    spec : FamilySpec
        The family's static wiring (builder plus convention defaults).
    section : object
        The family's ``tephpy.config`` section, read at creation and on
        :meth:`configure`.
    """

    def __init__(self, spec: FamilySpec, section: object) -> None:
        """Initialise the family and snapshot its resolved options.

        Parameters
        ----------
        spec : FamilySpec
            The family's static wiring (builder plus convention defaults).
        section : object
            The family's ``tephpy.config`` section, read at creation and
            on :meth:`configure`.
        """
        super().__init__()
        self._spec = spec
        self._section = section
        self._overrides: dict[str, object] = {}
        self._members: list[Member] | None = None
        self._member_values: npt.NDArray[np.float64] = np.empty(0)
        self._member_bboxes: npt.NDArray[np.float64] = np.empty((0, 4))
        self._zoom_adaptive = True
        self._lines = LineCollection([])
        self._texts: list[Text] = []
        self._options = self._resolve()
        self.set_zorder(spec.zorder)
        self.set_visible(self._options.visible)

    @property
    def options(self) -> ResolvedOptions:
        """The resolved settings snapshot currently in force.

        Returns
        -------
        ResolvedOptions
            The snapshot (accessor kwargs > ``tephpy.config`` >
            ``_constants``) taken at creation or the last
            :meth:`configure`.
        """
        return self._options

    def configure(self, **kwargs: object) -> None:
        """Reconfigure the family (the accessor-kwargs precedence tier).

        Re-reads ``tephpy.config`` now (spec §3.5 semantics). Passing
        ``None`` for an option removes any prior override so the value
        falls back to ``tephpy.config`` and then ``_constants``. A call
        that raises leaves the family unchanged.

        Parameters
        ----------
        **kwargs : object
            Options to override; the family's accessor documents the
            accepted names.

        Raises
        ------
        TypeError
            If an option name is unknown for this family.
        ValueError
            If an option value is invalid, e.g. a non-positive
            ``interval``.
        """
        unknown = set(kwargs) - self._spec.allowed
        if unknown:
            msg = f"unknown option(s) {sorted(unknown)!r} for {self._spec.name!r}"
            raise TypeError(msg)
        # Stage the update on a copy so a rejected call rolls back cleanly.
        overrides = dict(self._overrides)
        for key, value in kwargs.items():
            if value is None:
                overrides.pop(key, None)
            else:
                # Materialize one-shot iterables (e.g., generators) to tuple
                # so they survive later reconfigures (spec §3.5, §7 item 1).
                if key == "values":
                    override_value: object = tuple(
                        float(v) for v in cast("Iterable[SupportsFloat]", value)
                    )
                else:
                    override_value = value
                overrides[key] = override_value
        prior = self._overrides
        self._overrides = overrides
        try:
            self._options = self._resolve()
        except Exception:
            self._overrides = prior
            raise
        self.set_visible(self._options.visible)
        if _GEOMETRY_KEYS & set(kwargs):
            self._members = None
        self.stale = True

    def set_figure(self, fig: Figure | SubFigure) -> None:
        """Propagate the owning figure to the managed child artists.

        Parameters
        ----------
        fig : matplotlib.figure.Figure or matplotlib.figure.SubFigure
            The figure the family belongs to.
        """
        super().set_figure(fig)
        self._lines.set_figure(fig)
        for text in self._texts:
            text.set_figure(fig)

    @martist.allow_rasterization  # type: ignore[untyped-decorator]
    def draw(self, renderer: RendererBase) -> None:
        """Draw the members visible in the current view.

        Parameters
        ----------
        renderer : matplotlib.backend_bases.RendererBase
            The active renderer.
        """
        if not self.get_visible():
            return
        axes = self.axes
        if axes is None:
            return
        if self._members is None:
            self._build()
        members = self._members if self._members is not None else []
        opts = self._options
        view = axes.viewLim
        mask = self._zoom_mask(view.width) & self._view_mask(view)
        selected = [m for m, keep in zip(members, mask, strict=True) if keep]
        renderer.open_group("isopleth-family", gid=self.get_gid())
        lines = self._lines
        lines.set_segments([m.xy for m in selected])
        lines.set_color(opts.color)
        lines.set_linewidth(opts.linewidth)
        lines.set_alpha(opts.alpha)
        lines.set_transform(axes.transData)
        lines.set_clip_box(axes.bbox)
        lines.draw(renderer)
        if opts.labels:
            self._draw_labels(renderer, selected)
        renderer.close_group("isopleth-family")
        self.stale = False

    def _pick(self, key: str) -> object:
        """Return the highest-precedence non-``None`` value for an option.

        Parameters
        ----------
        key : str
            The option name.

        Returns
        -------
        object
            The override or ``tephpy.config`` value, or ``None`` to fall
            back to the ``_constants`` convention.
        """
        value: object = self._overrides.get(key)
        if value is None:
            value = getattr(self._section, key, None)
        return value

    def _resolve(self) -> ResolvedOptions:
        """Snapshot the resolved options (kwargs > config > constants).

        Returns
        -------
        ResolvedOptions
            The frozen snapshot the family builds and draws from.

        Raises
        ------
        ValueError
            If the resolved ``interval`` is not a positive, finite number.
        """
        spec = self._spec
        pick = self._pick
        raw_values = pick("values")
        values: tuple[float, ...] | None = None
        if raw_values is not None:
            values = tuple(
                float(v) for v in cast("Iterable[SupportsFloat]", raw_values)
            )
        raw_interval = pick("interval")
        interval = (
            None if raw_interval is None else float(cast("SupportsFloat", raw_interval))
        )
        if interval is not None and not (interval > 0 and math.isfinite(interval)):
            msg = (
                f"{spec.name!r} interval must be a positive, finite number: "
                f"{interval!r}"
            )
            raise ValueError(msg)
        raw_truncation = pick("truncation")
        truncation = (
            spec.truncation
            if raw_truncation is None
            else float(cast("SupportsFloat", raw_truncation))
        )
        raw_color = pick("color")
        raw_linewidth = pick("linewidth")
        raw_alpha = pick("alpha")
        raw_labels = pick("labels")
        raw_visible = pick("visible")
        return ResolvedOptions(
            values=values,
            interval=interval,
            truncation=truncation,
            color=spec.color if raw_color is None else str(raw_color),
            linewidth=(
                ISOPLETH_LINEWIDTH
                if raw_linewidth is None
                else float(cast("SupportsFloat", raw_linewidth))
            ),
            alpha=(
                ISOPLETH_ALPHA
                if raw_alpha is None
                else float(cast("SupportsFloat", raw_alpha))
            ),
            labels=True if raw_labels is None else bool(raw_labels),
            visible=True if raw_visible is None else bool(raw_visible),
        )

    def _candidate_values(self) -> npt.NDArray[np.float64]:
        """Return the member values to build, at the finest granularity.

        Returns
        -------
        numpy.ndarray
            Explicit ``values`` if resolved, else interval multiples over
            the family domain (the finest ladder step by default), else
            the family's canonical values list.
        """
        opts = self._options
        spec = self._spec
        if opts.values is not None:
            return np.asarray(opts.values, dtype=np.float64)
        if spec.steps is not None and spec.domain is not None:
            interval = opts.interval if opts.interval is not None else spec.steps[-1][1]
            lo, hi = spec.domain
            start = math.ceil(lo / interval) * interval
            return np.arange(start, hi + 0.5 * interval, interval)
        values = spec.values if spec.values is not None else ()
        return np.asarray(values, dtype=np.float64)

    def _build(self) -> None:
        """Build and cache the member polylines and their bounding boxes."""
        opts = self._options
        members = self._spec.builder(self._candidate_values(), opts.truncation)
        self._members = members
        self._member_values = np.array(
            [member.value for member in members], dtype=np.float64
        )
        if members:
            self._member_bboxes = np.array(
                [
                    (
                        member.xy[:, 0].min(),
                        member.xy[:, 1].min(),
                        member.xy[:, 0].max(),
                        member.xy[:, 1].max(),
                    )
                    for member in members
                ],
                dtype=np.float64,
            )
        else:
            self._member_bboxes = np.empty((0, 4))
        self._zoom_adaptive = opts.values is None and opts.interval is None

    def _zoom_mask(self, width: float) -> npt.NDArray[np.bool_]:
        """Select members for the zoom level via the convention ladder.

        Parameters
        ----------
        width : float
            The current view width in data-space x units.

        Returns
        -------
        numpy.ndarray
            Boolean mask over the cached members.
        """
        count = self._member_values.size
        if not self._zoom_adaptive:
            return np.ones(count, dtype=bool)
        spec = self._spec
        if spec.steps is not None:
            step = spec.steps[-1][1]
            for min_width, ladder_step in spec.steps:
                if width >= min_width:
                    step = ladder_step
                    break
            ratio = self._member_values / step
            return np.asarray(np.abs(ratio - np.round(ratio)) < 1e-6)
        stride = 1
        if spec.strides is not None:
            for min_width, ladder_stride in spec.strides:
                if width >= min_width:
                    stride = ladder_stride
                    break
        return np.asarray((np.arange(count) % stride) == 0)

    def _view_mask(self, view: mtransforms.Bbox) -> npt.NDArray[np.bool_]:
        """Select members whose bounding box overlaps the view rectangle.

        Parameters
        ----------
        view : matplotlib.transforms.Bbox
            The current data-space view rectangle.

        Returns
        -------
        numpy.ndarray
            Boolean mask over the cached members.
        """
        boxes = self._member_bboxes
        if boxes.size == 0:
            return np.zeros(0, dtype=bool)
        return np.asarray(
            (boxes[:, 0] <= view.x1)
            & (boxes[:, 2] >= view.x0)
            & (boxes[:, 1] <= view.y1)
            & (boxes[:, 3] >= view.y0)
        )

    def _make_text(self) -> Text:
        """Create one pooled label with the family label conventions.

        Returns
        -------
        matplotlib.text.Text
            An unattached label owned and drawn by the family.
        """
        text = Text(
            0.0,
            0.0,
            "",
            ha="center",
            va="center",
            fontsize=LABEL_FONTSIZE,
            rotation_mode="anchor",
            bbox={
                "boxstyle": LABEL_BOXSTYLE,
                "facecolor": LABEL_BOX_COLOR,
                "edgecolor": LABEL_BOX_COLOR,
                "alpha": LABEL_BOX_ALPHA,
            },
        )
        figure = self.get_figure(root=False)
        if figure is not None:
            text.set_figure(figure)
        return text

    def _draw_labels(self, renderer: RendererBase, selected: list[Member]) -> None:
        """Place and draw one label per selected member.

        The label anchors at the middle in-view vertex, rotated to the
        local line direction in screen space and folded upright.

        Parameters
        ----------
        renderer : matplotlib.backend_bases.RendererBase
            The active renderer.
        selected : list of Member
            The members drawn this pass.
        """
        axes = self.axes
        if axes is None:
            return
        opts = self._options
        view = axes.viewLim
        while len(self._texts) < len(selected):
            self._texts.append(self._make_text())
        for member, text in zip(selected, self._texts, strict=False):
            xy = member.xy
            inside = (
                (xy[:, 0] >= view.x0)
                & (xy[:, 0] <= view.x1)
                & (xy[:, 1] >= view.y0)
                & (xy[:, 1] <= view.y1)
            )
            indices = np.flatnonzero(inside)
            if indices.size < 2:
                continue
            mid = int(indices[indices.size // 2])
            lo = max(mid - 1, 0)
            hi = min(mid + 1, xy.shape[0] - 1)
            display = axes.transData.transform(xy[[lo, hi]])
            angle = math.degrees(
                math.atan2(display[1, 1] - display[0, 1], display[1, 0] - display[0, 0])
            )
            angle = (angle + 90.0) % 180.0 - 90.0
            text.set_position((float(xy[mid, 0]), float(xy[mid, 1])))
            text.set_text(f"{member.value:g}")
            text.set_color(opts.color)
            text.set_rotation(angle)
            text.set_transform(axes.transData)
            text.set_clip_box(axes.bbox)
            text.set_clip_on(True)
            text.draw(renderer)
