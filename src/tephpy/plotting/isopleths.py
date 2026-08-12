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

from collections.abc import Iterable, Mapping
import dataclasses
import math
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, cast, override

from matplotlib import artist as martist
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgba
from matplotlib.text import Text
from matplotlib.ticker import Formatter, Locator
import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._constants import (
    DRY_ADIABAT_COLOR,
    DRY_ADIABAT_STEPS,
    DRY_ADIABAT_ZORDER,
    EMPHASIS_LINEWIDTH,
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
from tephpy._constants import (
    EDGES as _EDGES,
)
from tephpy._constants import (
    EMPHASIS_STYLE_KEYS as _EMPHASIS_STYLE_KEYS,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import SupportsFloat

    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    import matplotlib.transforms as mtransforms

__all__ = [
    "EDGES",
    "FamilySpec",
    "IsoplethFamily",
    "Member",
    "ResolvedOptions",
    "dry_adiabat_members",
    "edge_crossings",
    "isobar_members",
    "isotherm_members",
    "mixing_ratio_members",
    "moist_adiabat_members",
]

#: Options that require rebuilding the cached member geometry when changed.
#: Every name is also a :class:`ResolvedOptions` field, because
#: :meth:`IsoplethFamily.configure` decides whether to rebuild by comparing the
#: resolved values rather than by inspecting which keywords a caller passed.
#: ``emphasis`` is here as well as in the style keys because an emphasised value
#: the zoom ladder would never select is added to the build (spec §3.2).
_GEOMETRY_KEYS: Final[frozenset[str]] = frozenset(
    {"values", "interval", "truncation", "emphasis"}
)

#: Style and visibility options shared by every family.
_STYLE_KEYS: Final[frozenset[str]] = frozenset(
    {"color", "linewidth", "alpha", "labels", "visible", "emphasis"}
)

#: Options accepted by the interval-based families.
_INTERVAL_KEYS: Final[frozenset[str]] = _STYLE_KEYS | {"values", "interval"}

#: The diagram edges an isopleth family may claim for its labels (spec §3.2).
#: The tuple itself lives in ``tephpy._constants``, below the
#: configfile spec §3 dependency arrow, so the configuration loader can check a
#: ``labels`` value against it (domain spec §3.2). Re-bound here, rather than
#: left as a bare import, because it is public API: it is in ``__all__``, and
#: other docstrings in this module reference it as :data:`EDGES`. autoapi is a
#: static parser and does not render imported names, so an import alone would
#: drop the attribute from the API page and break those references under
#: ``nitpicky``. It is the same object, not a copy.
EDGES: Final[tuple[str, ...]] = _EDGES

#: Tolerance for matching a member value against an emphasis key. ``abs_tol``
#: carries the 0 °C case, where a relative tolerance alone matches nothing.
_EMPHASIS_RTOL: Final[float] = 1e-9
_EMPHASIS_ATOL: Final[float] = 1e-9

#: The linestyle a member draws with unless an emphasis override says otherwise.
#: A family has no family-level ``linestyle`` (spec §3.2), so this is the
#: ``LineCollection`` default rather than a convention a caller can set.
#: Bare ``Final`` so the value narrows to ``Literal["solid"]``, which is what
#: ``Collection.set_linestyle`` accepts.
_DEFAULT_LINESTYLE: Final = "solid"

#: The resolved ``emphasis`` when nothing is emphasised. Shared, and a proxy
#: like every other resolved ``emphasis``, so a caller cannot write a member
#: into the snapshot of a family that has none.
_NO_EMPHASIS: Final[Mapping[float, Mapping[str, object]]] = MappingProxyType({})


def edge_crossings(
    xy: npt.NDArray[np.float64], edge: str, view: mtransforms.Bbox
) -> npt.NDArray[np.float64]:
    """Return where a member polyline meets one edge of the view.

    Pure numpy over the cached member geometry: each segment that straddles
    the edge's level contributes one linearly interpolated crossing, kept
    only when it falls within the edge's own span. A vertex lying exactly on
    the edge counts once — attributed to the segment it starts, or to the
    segment it ends when it is the polyline's last vertex; a segment with a
    non-finite endpoint never counts. A member may cross the
    same edge more than once — a curved isobar leaving and re-entering the
    view — and every crossing is returned (spec §3.2).

    Parameters
    ----------
    xy : numpy.ndarray
        The member polyline, shape ``(n, 2)`` in tephigram data space.
    edge : str
        The edge to intersect, one of :data:`EDGES`.
    view : matplotlib.transforms.Bbox
        The current data-space view rectangle.

    Returns
    -------
    numpy.ndarray
        The along-edge coordinates of the crossings — x for ``"bottom"``
        and ``"top"``, y for ``"left"`` and ``"right"`` — in polyline
        order; empty when the member does not reach the edge.

    Raises
    ------
    TypeError
        If `edge` is not one of :data:`EDGES`.
    """
    if edge not in EDGES:
        msg = f"unknown edge {edge!r}; expected one of {list(EDGES)!r}"
        raise TypeError(msg)
    if xy.shape[0] < 2:
        return np.empty(0, dtype=np.float64)
    if edge in {"bottom", "top"}:
        across, along = xy[:, 1], xy[:, 0]
        level = view.y0 if edge == "bottom" else view.y1
        lo, hi = view.x0, view.x1
    else:
        across, along = xy[:, 0], xy[:, 1]
        level = view.x0 if edge == "left" else view.x1
        lo, hi = view.y0, view.y1
    delta = across - level
    start, end = delta[:-1], delta[1:]
    # A segment with a non-finite endpoint never counts. NaN drops out of the
    # tests below on its own, but ``np.sign`` maps +/-inf to +/-1, so an
    # infinite endpoint would otherwise fake a sign change (and opposing
    # infinities divide inf by inf); mask both explicitly.
    finite = np.isfinite(start) & np.isfinite(end)
    hit = finite & ((start == 0.0) | (np.sign(start) * np.sign(end) < 0.0))
    # A vertex exactly on the edge is attributed to the segment it starts, so
    # it counts once. The polyline's final vertex starts no segment, so the
    # final segment claims it instead — the interpolation below, with
    # ``end == 0``, lands exactly on that vertex.
    hit[-1] |= finite[-1] & (end[-1] == 0.0)
    if not hit.any():
        return np.empty(0, dtype=np.float64)
    start, end = start[hit], end[hit]
    first, second = along[:-1][hit], along[1:][hit]
    span = end - start
    fraction = np.where(span == 0.0, 0.0, -start / np.where(span == 0.0, 1.0, span))
    positions = first + fraction * (second - first)
    return np.asarray(positions[(positions >= lo) & (positions <= hi)])


def _normalize_labels(value: object, name: str) -> tuple[bool, tuple[str, ...]]:
    """Split a raw ``labels`` option into a flag and the edges it claims.

    ``True``/``None`` mean every member is labelled inline, ``False`` means
    none is, and one or more edge names claim those edges — a bare string
    and a one-tuple are identical, and duplicates collapse in first-seen
    order (spec §3.2). The bare-string case is handled before the iterable
    case so ``"bottom"`` is never iterated character by character.

    Parameters
    ----------
    value : object
        The resolved ``labels`` option, from any precedence tier.
    name : str
        The family name, for the error message.

    Returns
    -------
    tuple of (bool, tuple of str)
        Whether the family labels anything, and the edges it claims.

    Raises
    ------
    TypeError
        If `value` is neither a bool nor edge name(s) from :data:`EDGES`.
    """
    if value is None or isinstance(value, bool):
        return (True if value is None else value), ()
    placements: tuple[object, ...]
    if isinstance(value, str):
        placements = (value,)
    elif isinstance(value, Iterable):
        placements = tuple(cast("Iterable[object]", value))
    else:
        placements = (value,)
    edges: list[str] = []
    for placement in placements:
        if not isinstance(placement, str) or placement not in EDGES:
            msg = (
                f"unknown {name!r} label placement {placement!r}; expected "
                f"True, False, or edge name(s) from {list(EDGES)!r}"
            )
            raise TypeError(msg)
        if placement not in edges:
            edges.append(placement)
    return bool(edges), tuple(edges)


def _emphasis_number(value: object, key: str, name: str, member: float) -> float:
    """Validate one numeric style override on an emphasised member.

    Parameters
    ----------
    value : object
        The resolved override value.
    key : str
        The style key, ``"linewidth"`` or ``"alpha"``.
    name : str
        The family name, for the error message.
    member : float
        The member value the style belongs to, for the error message.

    Returns
    -------
    float
        The validated number.

    Raises
    ------
    TypeError
        If `value` is not a number.
    ValueError
        If a ``linewidth`` is not positive and finite, or an ``alpha`` falls
        outside ``[0, 1]``.
    """
    try:
        number = float(cast("SupportsFloat", value))
    except (TypeError, ValueError) as err:
        msg = (
            f"{name!r} emphasis {key!r} for member {member:g} must be a "
            f"number: {value!r}"
        )
        raise TypeError(msg) from err
    if key == "linewidth":
        valid = number > 0.0 and math.isfinite(number)
        expected = "a positive, finite number"
    else:
        valid = 0.0 <= number <= 1.0
        expected = "between 0 and 1"
    if not valid:
        msg = (
            f"{name!r} emphasis {key!r} for member {member:g} must be "
            f"{expected}: {number!r}"
        )
        raise ValueError(msg)
    return number


def _normalize_emphasis(
    value: object, name: str
) -> Mapping[float, Mapping[str, object]]:
    """Validate and copy a raw ``emphasis`` option (spec §3.2).

    Keys become floats and each style mapping is copied into a fresh dict, so
    the family's snapshot never aliases a mapping the caller can still mutate --
    the same reason ``values`` materialises a generator to a tuple. Both levels
    are then wrapped in a read-only proxy, because the result is reachable
    through the public :attr:`IsoplethFamily.options`: a write there would enter
    a member that skipped this validation and that the member cache was never
    invalidated for, so the family would advertise a style it does not draw.
    ``color`` and ``linestyle`` are left to matplotlib to validate at draw time,
    exactly as the family-level ``color`` already is.

    Parameters
    ----------
    value : object
        The resolved ``emphasis`` option, from any precedence tier.
    name : str
        The family name, for the error messages.

    Returns
    -------
    Mapping of float to Mapping of str to object
        Member value mapped to its validated style overrides, read-only at
        both levels; empty when nothing is emphasised.

    Raises
    ------
    TypeError
        If `value` is not a mapping, a key is not a number, a style is not a
        mapping, or a style names a key outside :data:`_EMPHASIS_STYLE_KEYS`.
    ValueError
        If a member value is not finite, or a ``linewidth`` or ``alpha``
        override is out of range.
    """
    if not isinstance(value, Mapping):
        msg = (
            f"{name!r} emphasis must be a mapping of member value to style "
            f"overrides, not {type(value).__name__}"
        )
        raise TypeError(msg)
    emphasis: dict[float, Mapping[str, object]] = {}
    for raw_member, raw_style in cast("Mapping[object, object]", value).items():
        try:
            member = float(cast("SupportsFloat", raw_member))
        except (TypeError, ValueError) as err:
            msg = f"{name!r} emphasis member value must be a number: {raw_member!r}"
            raise TypeError(msg) from err
        if not math.isfinite(member):
            # A non-finite key would build a full NaN polyline that the view
            # mask silently drops, so it is rejected here alongside the
            # ``linewidth``, ``alpha`` and ``interval`` finiteness checks.
            msg = f"{name!r} emphasis member value must be a finite number: {member!r}"
            raise ValueError(msg)
        if not isinstance(raw_style, Mapping):
            msg = (
                f"{name!r} emphasis style for member {member:g} must be a mapping "
                f"of style overrides, not {type(raw_style).__name__}"
            )
            raise TypeError(msg)
        style = dict(cast("Mapping[str, object]", raw_style))
        unknown = set(style) - set(_EMPHASIS_STYLE_KEYS)
        if unknown:
            msg = (
                f"unknown {name!r} emphasis style key(s) {sorted(unknown)!r} for "
                f"member {member:g}; expected {list(_EMPHASIS_STYLE_KEYS)!r}"
            )
            raise TypeError(msg)
        for key in ("linewidth", "alpha"):
            if key in style:
                style[key] = _emphasis_number(style[key], key, name, member)
        emphasis[member] = MappingProxyType(style)
    return MappingProxyType(emphasis)


def _close_index(
    values: npt.NDArray[np.float64], targets: npt.NDArray[np.float64]
) -> npt.NDArray[np.int64]:
    """Match each value against a target list within the emphasis tolerance.

    Member values are floats built by arithmetic over a ladder interval, and
    emphasis keys are floats a user typed, so the two are compared with a
    tolerance rather than for equality.

    Parameters
    ----------
    values : numpy.ndarray
        The values to match, shape ``(n,)``.
    targets : numpy.ndarray
        The values to match against, shape ``(m,)``.

    Returns
    -------
    numpy.ndarray
        Shape ``(n,)`` of int64: the index into `targets` of the first match
        for each value, or ``-1`` where there is none.
    """
    if values.size == 0 or targets.size == 0:
        return np.full(values.size, -1, dtype=np.int64)
    close = np.isclose(
        values[:, None], targets[None, :], rtol=_EMPHASIS_RTOL, atol=_EMPHASIS_ATOL
    )
    return np.asarray(
        np.where(close.any(axis=1), close.argmax(axis=1), -1), dtype=np.int64
    )


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
    zoom-adaptive default ladder is in force. An empty `label_edges` means
    the family labels inline only, and an empty `emphasis` means no member is
    distinguished. The snapshot is immutable throughout: the class is frozen
    against rebinding, and `emphasis` -- its one field with any container
    depth -- is a read-only proxy at both levels over dicts the family copied
    for itself when it resolved.
    """

    values: tuple[float, ...] | None
    interval: float | None
    truncation: float | None
    color: str
    linewidth: float
    alpha: float
    labels: bool
    label_edges: tuple[str, ...]
    visible: bool
    emphasis: Mapping[float, Mapping[str, object]]


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
    validate : callable, optional
        Called with ``(family name, candidate options)`` whenever the
        options resolve; raising rejects the change. The owning axes
        passes its one-family-per-edge check here so the rejection
        lands inside this class's rollback (spec §3.2).
    on_change : callable, optional
        Called with no arguments after the options resolve successfully,
        whichever entry point resolved them. The owning axes passes its
        edge-ownership sync here so a direct :meth:`configure` or
        :meth:`set_visible` reaches it too (spec §3.2).
    """

    def __init__(
        self,
        spec: FamilySpec,
        section: object,
        validate: Callable[[str, ResolvedOptions], None] | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        """Initialise the family and snapshot its resolved options.

        Parameters
        ----------
        spec : FamilySpec
            The family's static wiring (builder plus convention defaults).
        section : object
            The family's ``tephpy.config`` section, read at creation and
            on :meth:`configure`.
        validate : callable, optional
            Called with ``(family name, candidate options)`` whenever the
            options resolve; raising rejects the change. The owning axes
            passes its one-family-per-edge check here so the rejection
            lands inside this class's rollback (spec §3.2).
        on_change : callable, optional
            Called with no arguments after the options resolve
            successfully, whichever entry point resolved them. The owning
            axes passes its edge-ownership sync here so a direct
            :meth:`configure` or :meth:`set_visible` reaches it too
            (spec §3.2).
        """
        super().__init__()
        self._spec = spec
        self._section = section
        self._validate = validate
        # Armed at the end of construction: the owner builds all five
        # families before its first sync, and a half-built one calling back
        # into that sync would find itself missing (spec §3.2).
        self._on_change: Callable[[], None] | None = None
        self._overrides: dict[str, object] = {}
        self._members: list[Member] | None = None
        self._member_values: npt.NDArray[np.float64] = np.empty(0)
        self._member_bboxes: npt.NDArray[np.float64] = np.empty((0, 4))
        self._member_extra: npt.NDArray[np.bool_] = np.empty(0, dtype=bool)
        self._zoom_adaptive = True
        self._lines = LineCollection([])
        self._texts: list[Text] = []
        self._options = self._resolve_validated()
        self.set_zorder(spec.zorder)
        # Artist.set_visible, not this class's override: the options are
        # already resolved, and nothing may call back yet.
        super().set_visible(self._options.visible)
        self._on_change = on_change

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

        Re-reads ``tephpy.config`` now (spec §3.5 semantics), so any tier
        may move — a geometry option changed there takes effect on the next
        call whether or not that call mentions it, and the cached members
        are rebuilt whenever the resolved geometry differs. Passing
        ``None`` for an option removes any prior override so the value
        falls back to ``tephpy.config`` and then ``_constants``. A call
        that raises leaves the family unchanged, and only a call that
        succeeds notifies the owner's ``on_change`` — which is how an edge
        claimed or released here reaches the diagram (spec §3.2).

        Parameters
        ----------
        **kwargs : object
            Options to override; the family's accessor documents the
            accepted names.

        Raises
        ------
        TypeError
            If an option name is unknown for this family, if ``labels`` names
            an unknown placement, or if the owning axes rejects an edge claim
            already held by another family, or if ``emphasis`` is malformed.
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
                # so they survive later reconfigures (spec §3.5, §7 item 1),
                # and copy an emphasis mapping for the same reason.
                if key == "values":
                    override_value: object = tuple(
                        float(v) for v in cast("Iterable[SupportsFloat]", value)
                    )
                elif key == "emphasis":
                    override_value = _normalize_emphasis(value, self._spec.name)
                else:
                    override_value = value
                overrides[key] = override_value
        prior = self._overrides
        previous = self._options
        self._overrides = overrides
        try:
            self._options = self._resolve_validated()
        except Exception:
            self._overrides = prior
            raise
        # Artist.set_visible, not this class's override: the visibility is
        # already resolved, and the notify below covers it.
        super().set_visible(self._options.visible)
        # Compare what the geometry resolved to, not which keywords arrived.
        # The resolve above re-reads every tier, so a geometry option changed
        # in ``tephpy.config`` lands in the snapshot whatever this call was
        # about -- keying off ``kwargs`` left the cache stale, and the family
        # advertised a geometry it did not draw. It also spared a rebuild when
        # a caller re-passes a value the family already has.
        if any(
            getattr(previous, key) != getattr(self._options, key)
            for key in _GEOMETRY_KEYS
        ):
            self._members = None
        self.stale = True
        if self._on_change is not None:
            self._on_change()

    @override
    def set_visible(self, b: bool) -> None:
        """Show or hide the family, resolving its options as it goes.

        The inherited ``Artist.set_visible`` only flips a flag; an isopleth
        family's visibility is one of its resolved options, and an invisible
        family draws nothing so it holds no edge (spec §3.2). Hiding is
        therefore ``configure(visible=False)``, which releases any claimed
        edge, and showing is ``configure(visible=True)``, which reclaims it.
        Setting the value the family already has changes nothing, exactly as
        the base class does.

        Parameters
        ----------
        b : bool
            Whether the family is drawn.

        Raises
        ------
        TypeError
            If showing the family would reclaim an edge another family took
            while it was hidden; the family stays hidden (see
            :meth:`configure`).
        """
        if bool(b) == bool(self.get_visible()):
            super().set_visible(b)
            return
        self.configure(visible=bool(b))

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
            # A hidden family holds nothing: it gives its pooled labels up on
            # the same terms as its claimed edge (spec §3.2).
            self._texts.clear()
            return
        axes = self.axes
        if axes is None:
            return
        opts = self._options
        selected = self._order_members(self._selected_members())
        renderer.open_group("isopleth-family", gid=self.get_gid())
        lines = self._lines
        lines.set_segments([m.xy for m in selected])
        # Only a family with something emphasised pays for per-segment state;
        # with nothing emphasised the collection takes one scalar colour,
        # linewidth and alpha, exactly as it did before emphasis existed, so a
        # diagram with no ``emphasis`` renders identically -- including in
        # vector output, where per-path stroke state would otherwise be emitted
        # for every member.  ``_order_members`` is gated the same way (spec §3.2).
        if selected and opts.emphasis:
            styles = [self._member_style(m.value) for m in selected]
            # Bake alpha into the RGBA colour rather than calling set_alpha with
            # a per-segment list.  LineCollection.set_color calls
            # to_rgba_array(c, self._alpha) immediately; if self._alpha were a
            # per-segment array from the previous draw and the segment count
            # changed (zoom), the shapes would mismatch and raise.  Keeping
            # self._alpha as None throughout this path avoids the conflict.
            lines.set_alpha(None)  # clear any scalar from a prior else-branch draw
            lines.set_color(
                [
                    to_rgba(cast("str", s["color"]), cast("float", s["alpha"]))
                    for s in styles
                ]
            )
            lines.set_linewidth([cast("float", s["linewidth"]) for s in styles])
            lines.set_linestyle(
                [cast("str", s["linestyle"]) for s in styles]  # type: ignore[misc]
            )
        else:
            lines.set_color(opts.color)
            lines.set_linewidth(opts.linewidth)
            # Back to the collection's own default, not just left alone: a
            # per-segment list from an earlier emphasised draw would otherwise
            # survive clearing ``emphasis`` and keep dashing a member.
            lines.set_linestyle(_DEFAULT_LINESTYLE)
            lines.set_alpha(opts.alpha)
        lines.set_transform(axes.transData)
        lines.set_clip_box(axes.bbox)
        lines.draw(renderer)
        if opts.labels:
            self._draw_labels(renderer, selected)
        else:
            # ``_draw_labels`` owns the trim, so labelling switched off after a
            # labelled draw would otherwise strand the whole pool here.
            self._texts.clear()
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
            If the resolved ``interval`` is not a positive, finite number, or
            the resolved ``emphasis`` gives a non-finite member value, a
            ``linewidth`` that is not positive and finite, or an ``alpha``
            outside ``[0, 1]``.
        TypeError
            If the resolved ``labels`` names an unknown placement, or
            ``emphasis`` is malformed.
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
        labels, label_edges = _normalize_labels(raw_labels, spec.name)
        raw_visible = pick("visible")
        visible = True if raw_visible is None else bool(raw_visible)
        raw_emphasis = pick("emphasis")
        emphasis = (
            _NO_EMPHASIS
            if raw_emphasis is None
            else _normalize_emphasis(raw_emphasis, spec.name)
        )
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
            labels=labels,
            # An invisible family draws nothing, so it holds no edge (spec §3.2).
            label_edges=label_edges if visible else (),
            visible=visible,
            emphasis=emphasis,
        )

    def _resolve_validated(self) -> ResolvedOptions:
        """Resolve the options and put them past the owner's validator.

        Returns
        -------
        ResolvedOptions
            The accepted snapshot.

        Raises
        ------
        TypeError
            If the owner's validator rejects the candidate options.
        ValueError
            If an option value is invalid (see :meth:`_resolve`).
        """
        options = self._resolve()
        if self._validate is not None:
            self._validate(self._spec.name, options)
        return options

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
        """Build and cache the member polylines, boxes and emphasis marks.

        Emphasised values the canonical set does not already carry are appended
        to the build, so a member the zoom ladder would never select still
        exists to be forced in by :meth:`_zoom_mask` (spec §3.2). Which members
        those are is recorded, because a list family strides by member index and
        an addition must not shift that phase.
        """
        opts = self._options
        canonical = self._candidate_values()
        keys = np.asarray(sorted(opts.emphasis), dtype=np.float64)
        extra = keys[_close_index(keys, canonical) < 0]
        members = self._spec.builder(
            np.concatenate([canonical, extra]), opts.truncation
        )
        self._members = members
        self._member_values = np.array(
            [member.value for member in members], dtype=np.float64
        )
        # By value, not by build position: a builder may drop members (the moist
        # adiabats truncate), so positions do not survive the round trip.
        self._member_extra = np.asarray(_close_index(self._member_values, extra) >= 0)
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

        An emphasised member is always selected, whatever the ladder would pick
        — that is what lets emphasis mark a reference isopleth the interval
        never lands on (spec §3.2). A list family strides by member index, so
        the stride runs over the canonical members by their canonical position
        and an emphasis-only addition cannot shift its phase.

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
        extra = self._member_extra
        if extra.size != count:
            extra = np.zeros(count, dtype=bool)
        keys = np.asarray(sorted(self._options.emphasis), dtype=np.float64)
        forced = np.asarray(_close_index(self._member_values, keys) >= 0)
        spec = self._spec
        if spec.steps is not None:
            step = spec.steps[-1][1]
            for min_width, ladder_step in spec.steps:
                if width >= min_width:
                    step = ladder_step
                    break
            ratio = self._member_values / step
            mask = np.asarray(np.abs(ratio - np.round(ratio)) < 1e-6)
            return np.asarray(mask | forced)
        stride = 1
        if spec.strides is not None:
            for min_width, ladder_stride in spec.strides:
                if width >= min_width:
                    stride = ladder_stride
                    break
        # Position among the canonical members, so an emphasis-only addition
        # never shifts which members the stride picks.
        position = np.cumsum(~extra) - 1
        mask = np.asarray((position % stride) == 0) & ~extra
        return np.asarray(mask | forced)

    def _emphasis_style(self, value: float) -> Mapping[str, object] | None:
        """Return the emphasis overrides for one member value.

        Parameters
        ----------
        value : float
            The member's isopleth value in the family's native units.

        Returns
        -------
        Mapping of str to object or None
            The member's style overrides -- read-only, straight out of the
            snapshot -- or ``None`` when it is not emphasised.
        """
        emphasis = self._options.emphasis
        if not emphasis:
            return None
        for key, style in emphasis.items():
            if math.isclose(key, value, rel_tol=_EMPHASIS_RTOL, abs_tol=_EMPHASIS_ATOL):
                return style
        return None

    def _member_style(self, value: float) -> dict[str, object]:
        """Return the style one member draws with.

        The family's own resolved style, with an emphasised member's overrides
        applied over it. Emphasis with no overrides still thickens the line to
        ``EMPHASIS_LINEWIDTH`` — the monochrome printed-chart idiom of same ink,
        heavier line (spec §3.2).

        Parameters
        ----------
        value : float
            The member's isopleth value in the family's native units.

        Returns
        -------
        dict of str to object
            Keys ``color``, ``linewidth``, ``linestyle`` and ``alpha``.
        """
        opts = self._options
        style: dict[str, object] = {
            "color": opts.color,
            "linewidth": opts.linewidth,
            "linestyle": _DEFAULT_LINESTYLE,
            "alpha": opts.alpha,
        }
        override = self._emphasis_style(value)
        if override is not None:
            style["linewidth"] = EMPHASIS_LINEWIDTH
            style.update(override)
        return style

    def _order_members(self, selected: list[Member]) -> list[Member]:
        """Order the drawn members plain first, emphasised last.

        Draw order stays inside the family: an emphasised member wins against
        its own family's neighbours, while the families drawn above this one
        still cross it (spec §3.2).

        Parameters
        ----------
        selected : list of Member
            The members the view and zoom ladder selected, in build order.

        Returns
        -------
        list of Member
            The same members, emphasised ones moved to the end in build order.
        """
        if not self._options.emphasis:
            return selected
        plain = [m for m in selected if self._emphasis_style(m.value) is None]
        emphasised = [m for m in selected if self._emphasis_style(m.value) is not None]
        return plain + emphasised

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

    def _selected_members(self) -> list[Member]:
        """Return the members the current view and zoom ladder select.

        Building lazily on first use, this is the single definition of "what
        this family shows right now" — shared by :meth:`draw` and by the edge
        tick locator, which matplotlib calls outside the draw path.

        Returns
        -------
        list of Member
            The selected members in build order; empty until the family has
            an axes.
        """
        axes = self.axes
        if axes is None:
            return []
        if self._members is None:
            self._build()
        members = self._members if self._members is not None else []
        view = axes.viewLim
        mask = self._zoom_mask(view.width) & self._view_mask(view)
        return [m for m, keep in zip(members, mask, strict=True) if keep]

    def _inline_members(
        self, view: mtransforms.Bbox, selected: list[Member]
    ) -> list[Member]:
        """Return the selected members no claimed edge already labels.

        The automatic remainder of spec §3.2: listed edges label the members
        that reach them, and every member left over is labelled inline. With
        no claimed edge every selected member is inline, which is the default.
        The crossings are recomputed here rather than shared with the locator
        because tick location and artist drawing have no guaranteed ordering.

        Parameters
        ----------
        view : matplotlib.transforms.Bbox
            The current data-space view rectangle.
        selected : list of Member
            The members drawn this pass.

        Returns
        -------
        list of Member
            The members to label inline.
        """
        edges = self._options.label_edges
        if not edges:
            return selected
        return [
            member
            for member in selected
            if not any(edge_crossings(member.xy, edge, view).size for edge in edges)
        ]

    def _draw_labels(self, renderer: RendererBase, selected: list[Member]) -> None:
        """Place and draw one label per selected member.

        The label anchors at the middle in-view vertex, rotated to the
        local line direction in screen space and folded upright. Members
        a claimed edge already ticks are dropped first (spec §3.2). An
        emphasised member's label takes the emphasis colour and alpha.

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
        view = axes.viewLim
        labelled = self._inline_members(view, selected)
        while len(self._texts) < len(labelled):
            self._texts.append(self._make_text())
        # ... and give the surplus back when the labelled set shrinks -- a zoom
        # out, or an edge claiming the members it now ticks.  The pool is a
        # cache sized to the current draw, not a high-water mark: nothing but
        # this list holds a pooled label, so dropping it is the whole release.
        del self._texts[len(labelled) :]
        # The grow-then-trim above makes these two exactly equal in length, so
        # ``strict=True`` would pass today and is what the rest of the codebase
        # uses -- this is deliberately the one exception.  The zip runs inside
        # ``draw``, where raising costs the caller the whole figure; a future
        # desync should cost one label instead, and the pool-length tests are
        # what catch it.
        for member, text in zip(labelled, self._texts, strict=False):
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
            style = self._member_style(member.value)
            text.set_color(cast("str", style["color"]))
            text.set_alpha(cast("float", style["alpha"]))
            text.set_rotation(angle)
            text.set_transform(axes.transData)
            text.set_clip_box(axes.bbox)
            text.set_clip_on(True)
            text.draw(renderer)


class _EdgeLocator(Locator):
    """Locate one family's crossings of one diagram edge as ticks.

    Matplotlib calls the locator on every draw, so pan, zoom, resize and
    ``set_extent`` stay correct with no refresh machinery (spec §3.2). Each
    call caches the member value beside each position for
    :class:`_EdgeFormatter`, which is why the formatter needs no inverse
    math and works identically for all five families.

    Parameters
    ----------
    family : IsoplethFamily
        The family that claimed the edge.
    edge : str
        The claimed edge, one of :data:`EDGES`.
    """

    def __init__(self, family: IsoplethFamily, edge: str) -> None:
        """Initialise the locator with empty caches.

        Parameters
        ----------
        family : IsoplethFamily
            The family that claimed the edge.
        edge : str
            The claimed edge, one of :data:`EDGES`.
        """
        super().__init__()
        self.family = family
        self.edge = edge
        self.positions: list[float] = []
        self.values: list[float] = []

    def __call__(self) -> list[float]:
        """Return the tick positions, refreshing the caches.

        Returns
        -------
        list of float
            The along-edge crossing coordinates, in member order; empty
            while the family has no axes.
        """
        positions: list[float] = []
        values: list[float] = []
        axes = self.family.axes
        if axes is not None:
            view = axes.viewLim
            # The locator is the family's own machinery, one module away
            # from a method it has no reason to publish.
            for member in self.family._selected_members():  # noqa: SLF001
                for position in edge_crossings(member.xy, self.edge, view):
                    positions.append(float(position))
                    values.append(member.value)
        self.positions = positions
        self.values = values
        return positions

    def tick_values(self, vmin: float, vmax: float) -> list[float]:
        """Return the tick positions, ignoring the requested interval.

        Parameters
        ----------
        vmin : float
            Ignored; the crossings define their own interval.
        vmax : float
            Ignored; the crossings define their own interval.

        Returns
        -------
        list of float
            The same positions :meth:`__call__` returns.
        """
        del vmin, vmax
        return self()


class _EdgeFormatter(Formatter):
    """Label an edge tick with the member value that produced it.

    Parameters
    ----------
    locator : _EdgeLocator
        The locator whose caches supply the values; matplotlib runs it
        immediately before this formatter within a draw, so the two agree.
    """

    def __init__(self, locator: _EdgeLocator) -> None:
        """Bind the formatter to its locator's caches.

        Parameters
        ----------
        locator : _EdgeLocator
            The locator whose caches supply the values.
        """
        super().__init__()
        self.locator = locator

    def __call__(self, x: float, pos: int | None = None) -> str:
        """Format one tick.

        Parameters
        ----------
        x : float
            The tick position, in along-edge data coordinates.
        pos : int, optional
            Ignored; the registry signature matplotlib calls with.

        Returns
        -------
        str
            The member value formatted ``"{value:g}"``, as inline labels
            already are, or ``""`` for a position this locator did not
            produce.
        """
        del pos
        locator = self.locator
        for position, value in zip(locator.positions, locator.values, strict=True):
            if math.isclose(position, x, rel_tol=1e-9, abs_tol=1e-9):
                return f"{value:g}"
        return ""
