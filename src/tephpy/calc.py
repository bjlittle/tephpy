# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tephigram-native thermodynamic analysis over ``metpy.calc`` (spec §3.3).

Physics is delegated to MetPy; only tephigram-native compositions live
here, and everything returns pint quantities on the shared registry
(spec §5). Sounding-level functions take a :class:`~tephpy.sounding.Sounding`
— constructing one already validates units, monotonic pressure, and
dewpoint ≤ temperature — while :func:`normand_point` is the one
quantity-level function. MetPy stays behind function-local imports so that
``import tephpy`` stays light (spec §10 item 10).

Analysis results distinguish "does not exist" from "zero" (spec §6):
``metpy.calc`` returns NaN quantities for a missing LFC/EL and ``0 J/kg``
— never NaN — for zero CAPE/CIN, and tephpy passes both through,
documented per :class:`SoundingIndices` field.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Final, Literal

import numpy as np

from tephpy._constants import MOIST_ADIABAT_PRESSURE_STEP
from tephpy._units import as_quantity, check_units_mapping
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    MissingDataError,
    ProfileTooShortError,
    TephpyValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pint

    from tephpy.sounding import Sounding

__all__ = ["Profile", "SoundingIndices", "normand_point", "parcel_path"]

#: The parcel-selection options (spec §3.3).
_PARCELS: Final[tuple[str, ...]] = ("surface", "mixed-layer")

#: The ``Profile`` data fields with their required dimensionalities (spec §5).
_PROFILE_DIMENSIONS: Final[dict[str, str]] = {
    "pressure": "[pressure]",
    "temperature": "[temperature]",
    "lcl_pressure": "[pressure]",
    "lcl_temperature": "[temperature]",
}

#: The ``SoundingIndices`` fields with their required dimensionalities
#: (spec §5). CAPE/CIN are specific energies (J/kg); the lifted index is a
#: temperature difference, so its pint dimensionality is a temperature.
_INDEX_DIMENSIONS: Final[dict[str, str]] = {
    "cape": "[energy] / [mass]",
    "cin": "[energy] / [mass]",
    "lcl_pressure": "[pressure]",
    "lcl_temperature": "[temperature]",
    "lfc_pressure": "[pressure]",
    "lfc_temperature": "[temperature]",
    "el_pressure": "[pressure]",
    "el_temperature": "[temperature]",
    "theta_w": "[temperature]",
    "lifted_index": "[temperature]",
}


@dataclasses.dataclass(frozen=True, eq=False)
class Profile:
    """One computed parcel ascent, ready to plot (spec §3.3).

    Plain plottable data: ``plot_profile`` draws it and the shading
    builders consume it, and neither re-derives the LCL. Construction
    mirrors ``Sounding``: bare arrays take the ``units=`` mapping, fields
    are dimension-checked quantities on the shared registry, and
    validation happens at construction.

    Attributes
    ----------
    pressure : pint.Quantity
        Path pressures, surface-first (strictly decreasing), at least two
        levels.
    temperature : pint.Quantity
        Parcel temperatures along the path.
    lcl_pressure : pint.Quantity
        Scalar pressure of the Normand's point the path actually uses —
        the corrected one when a correction was requested — inside the
        path's pressure span.
    lcl_temperature : pint.Quantity
        Scalar temperature at that point.
    parcel : str
        The lifted parcel: ``"surface"`` or ``"mixed-layer"``.
    label : str or None
        Legend text; ``None`` means no legend entry.
    units : mapping of str to str, optional
        Construction-only (not stored): unit strings for bare-array
        fields, keyed by field name (spec §5).
    """

    pressure: pint.Quantity
    temperature: pint.Quantity
    lcl_pressure: pint.Quantity
    lcl_temperature: pint.Quantity
    parcel: Literal["surface", "mixed-layer"] = "surface"
    label: str | None = None
    units: dataclasses.InitVar[Mapping[str, str] | None] = None

    def __post_init__(self, units: Mapping[str, str] | None) -> None:
        """Coerce and validate the constructed profile.

        Parameters
        ----------
        units : mapping of str to str or None
            The ``units=`` mapping for bare-array fields.
        """
        mapping = check_units_mapping(units, allowed=_PROFILE_DIMENSIONS)
        for name, dimension in _PROFILE_DIMENSIONS.items():
            quantity = as_quantity(
                getattr(self, name),
                name=name,
                units=mapping.get(name),
                dimension=dimension,
            )
            object.__setattr__(self, name, quantity)
        self._validate_arrays()
        self._validate_lcl()
        if self.parcel not in _PARCELS:
            msg = f"parcel must be one of {_PARCELS!r}, got {self.parcel!r}"
            raise ValueError(msg)

    def _validate_arrays(self) -> None:
        """Require 1-D equal-length arrays with strictly decreasing pressure."""
        pressure = self.pressure.magnitude
        temperature = self.temperature.magnitude
        for name, magnitude in (("pressure", pressure), ("temperature", temperature)):
            if magnitude.ndim != 1:
                msg = f"{name!r} must be 1-D, got {magnitude.ndim}-D"
                raise TephpyValidationError(msg)
        if pressure.size != temperature.size:
            msg = (
                "pressure and temperature must be equal length, got "
                f"{pressure.size} and {temperature.size}"
            )
            raise TephpyValidationError(msg)
        if pressure.size < 2:
            msg = f"a profile needs at least 2 levels, got {pressure.size}"
            raise TephpyValidationError(msg)
        offending = np.flatnonzero(~(np.diff(pressure) < 0.0)) + 1
        if offending.size:
            levels = tuple(int(index) for index in offending)
            msg = (
                "profile pressure must be strictly decreasing "
                f"(surface-first); offending levels {levels}"
            )
            raise TephpyValidationError(msg, levels=levels)

    def _validate_lcl(self) -> None:
        """Require a scalar LCL inside the path's pressure span."""
        for name in ("lcl_pressure", "lcl_temperature"):
            magnitude = getattr(self, name).magnitude
            if magnitude.ndim != 0:
                msg = f"{name!r} must be a scalar, got shape {magnitude.shape}"
                raise TephpyValidationError(msg)
        pressure = self.pressure.m_as("hPa")
        lcl = float(self.lcl_pressure.m_as("hPa"))
        if not pressure[-1] <= lcl <= pressure[0]:
            msg = (
                f"lcl_pressure ({lcl:g} hPa) must lie inside the path's "
                f"pressure span [{pressure[-1]:g}, {pressure[0]:g}] hPa"
            )
            raise TephpyValidationError(msg)


@dataclasses.dataclass(frozen=True, eq=False)
class SoundingIndices:
    """Derived thermodynamic parameters for one sounding (spec §3.3).

    Ten scalar quantity fields, each dimension-checked at construction.
    There is no cross-field validation: NaN fields are answers, not
    errors — analysis results distinguish "does not exist" (NaN) from
    "zero" (spec §6).

    Attributes
    ----------
    cape : pint.Quantity
        Convective available potential energy (J/kg); ``0 J/kg`` — never
        NaN — when the parcel has no positive-buoyancy region.
    cin : pint.Quantity
        Convective inhibition (J/kg, non-positive); ``0 J/kg`` when there
        is no LFC or no negative-buoyancy region below it.
    lcl_pressure : pint.Quantity
        Pressure of the lifting condensation level the parcel uses (the
        corrected one when a correction was requested); always defined.
    lcl_temperature : pint.Quantity
        Temperature at that level; always defined.
    lfc_pressure : pint.Quantity
        Pressure of the level of free convection; NaN when the parcel
        never becomes positively buoyant.
    lfc_temperature : pint.Quantity
        Temperature at that level; NaN with `lfc_pressure`.
    el_pressure : pint.Quantity
        Pressure of the equilibrium level; NaN when it does not exist —
        including while ``cape > 0`` with the parcel still buoyant at the
        profile top.
    el_temperature : pint.Quantity
        Temperature at that level; NaN with `el_pressure`.
    theta_w : pint.Quantity
        Wet-bulb potential temperature of the lifted parcel, evaluated at
        the parcel start, so it follows the ``parcel=`` option; always
        defined.
    lifted_index : pint.Quantity
        Lifted index (a temperature difference at 500 hPa); NaN when the
        profile tops out below 500 hPa.
    units : mapping of str to str, optional
        Construction-only (not stored): unit strings for bare scalar
        fields, keyed by field name (spec §5).
    """

    cape: pint.Quantity
    cin: pint.Quantity
    lcl_pressure: pint.Quantity
    lcl_temperature: pint.Quantity
    lfc_pressure: pint.Quantity
    lfc_temperature: pint.Quantity
    el_pressure: pint.Quantity
    el_temperature: pint.Quantity
    theta_w: pint.Quantity
    lifted_index: pint.Quantity
    units: dataclasses.InitVar[Mapping[str, str] | None] = None

    def __post_init__(self, units: Mapping[str, str] | None) -> None:
        """Coerce and dimension-check the constructed indices.

        Parameters
        ----------
        units : mapping of str to str or None
            The ``units=`` mapping for bare scalar fields.
        """
        mapping = check_units_mapping(units, allowed=_INDEX_DIMENSIONS)
        for name, dimension in _INDEX_DIMENSIONS.items():
            quantity = as_quantity(
                getattr(self, name),
                name=name,
                units=mapping.get(name),
                dimension=dimension,
            )
            if quantity.magnitude.ndim != 0:
                msg = f"{name!r} must be a scalar, got shape {quantity.magnitude.shape}"
                raise TephpyValidationError(msg)
            object.__setattr__(self, name, quantity)


def normand_point(
    pressure: object,
    temperature: object,
    dewpoint: object,
    *,
    units: Mapping[str, str] | None = None,
) -> tuple[pint.Quantity, pint.Quantity]:
    """Construct Normand's point — the LCL — for one parcel (spec §3.3).

    The geometric construction: the dry adiabat through (`pressure`,
    `temperature`) meets the humidity mixing-ratio line through
    (`pressure`, `dewpoint`) at the lifting condensation level. This is
    always the uncorrected construction; the operational cloud-base
    correction is :func:`parcel_path`'s concern.

    Parameters
    ----------
    pressure : pint.Quantity or float
        Scalar parcel pressure; a bare value takes the ``units=`` mapping.
    temperature : pint.Quantity or float
        Scalar parcel temperature.
    dewpoint : pint.Quantity or float
        Scalar parcel dewpoint; must not exceed `temperature` (equality —
        saturation — is physical, and puts Normand's point at the parcel).
    units : mapping of str to str, optional
        Unit strings for bare values, keyed by argument name, e.g.
        ``units={"pressure": "hPa", "temperature": "degC"}`` (spec §5).

    Returns
    -------
    tuple of pint.Quantity
        The scalar ``(pressure, temperature)`` of Normand's point, in
        hPa and degrees Celsius.

    Raises
    ------
    TephpyUnitsError
        For unit-less bare values, ambiguous or unparsable units, or the
        wrong dimensionality.
    DewpointExceedsTemperatureError
        If `dewpoint` exceeds `temperature`.
    TephpyValidationError
        If an argument is not a scalar.
    """
    mapping = check_units_mapping(
        units, allowed=("pressure", "temperature", "dewpoint")
    )
    p = _scalar_quantity(pressure, "pressure", mapping, "[pressure]")
    t = _scalar_quantity(temperature, "temperature", mapping, "[temperature]")
    td = _scalar_quantity(dewpoint, "dewpoint", mapping, "[temperature]")
    if float(td.m_as("degC")) > float(t.m_as("degC")):
        msg = (
            "dewpoint exceeds temperature (equality is saturation and "
            "accepted); no Normand's point exists"
        )
        raise DewpointExceedsTemperatureError(msg)
    # Function-local so `import tephpy` stays light (spec §3.3, §10 item 10).
    from metpy.calc import lcl  # noqa: PLC0415

    lcl_pressure, lcl_temperature = lcl(p, t, td)
    return lcl_pressure.to("hPa"), lcl_temperature.to("degC")


def _scalar_quantity(
    value: object, name: str, mapping: Mapping[str, str], dimension: str
) -> pint.Quantity:
    """Coerce one scalar boundary argument (spec §5).

    Parameters
    ----------
    value : object
        The argument value: a pint quantity, or a bare value with a
        `mapping` entry.
    name : str
        The argument name, used in error messages.
    mapping : mapping of str to str
        The boundary's validated ``units=`` mapping.
    dimension : str
        The required pint dimensionality.

    Returns
    -------
    pint.Quantity
        The scalar quantity on MetPy's registry.

    Raises
    ------
    TephpyUnitsError
        For unit-less bare values, ambiguous or unparsable units, or the
        wrong dimensionality.
    TephpyValidationError
        If the value is not a scalar.
    """
    quantity = as_quantity(
        value, name=name, units=mapping.get(name), dimension=dimension
    )
    if quantity.magnitude.ndim != 0:
        msg = f"{name!r} must be a scalar, got shape {quantity.magnitude.shape}"
        raise TephpyValidationError(msg)
    return quantity


def parcel_path(
    snd: Sounding,
    *,
    parcel: Literal["surface", "mixed-layer"] = "surface",
    cloud_base_correction: object = None,
    label: str | None = None,
) -> Profile:
    """Compute a parcel's ascent path over the sounding's span (spec §3.3).

    Dry adiabat from the parcel start to Normand's point, then moist
    adiabat to the profile top. Both legs sample the background moist
    adiabats' 5 hPa step, the moist leg is integrated with
    ``metpy.calc.moist_lapse(..., reference_pressure=lcl_pressure)`` —
    same integrator, same sampling, same anchoring as the background
    family — and the LCL vertex is spliced in exactly.

    Parameters
    ----------
    snd : Sounding
        The environment sounding; must carry dewpoint.
    parcel : str, default: "surface"
        The lifted parcel: ``"surface"`` starts from the lowest level;
        ``"mixed-layer"`` starts from ``metpy.calc.mixed_parcel`` (its
        100 hPa default depth is the operational convention).
    cloud_base_correction : pint.Quantity, optional
        A pressure-dimension correction added to the LCL pressure, applied
        only when explicitly requested; the operational -25 mb value lives
        in ``tephpy._constants.CLOUD_BASE_CORRECTION``. The corrected LCL
        temperature is re-read from the dry adiabat at the corrected
        pressure.
    label : str, optional
        Legend text for the profile; ``None`` means no legend entry.

    Returns
    -------
    Profile
        The parcel path, surface-first, with the LCL it actually uses.

    Raises
    ------
    MissingDataError
        If the sounding has no dewpoint.
    ProfileTooShortError
        If the profile tops out at or below the LCL the path would use
        (the corrected one when a correction is requested).
    TephpyUnitsError
        If `cloud_base_correction` is not a pressure-dimension quantity.
    TephpyValidationError
        If the correction places the LCL below the parcel start.
    ValueError
        If `parcel` is not a known option.
    """
    start_pressure, start_temperature, start_dewpoint = _parcel_start(snd, parcel)
    lcl_pressure, lcl_temperature = _lcl_used(
        start_pressure, start_temperature, start_dewpoint, cloud_base_correction
    )
    _require_moist_ascent(snd, lcl_pressure)
    # Function-local so `import tephpy` stays light (spec §3.3, §10 item 10).
    from metpy.calc import dry_lapse, moist_lapse  # noqa: PLC0415
    from metpy.units import units as registry  # noqa: PLC0415

    p0 = float(start_pressure.m_as("hPa"))
    lcl_hpa = float(lcl_pressure.m_as("hPa"))
    top = float(snd.pressure[-1].m_as("hPa"))
    step = MOIST_ADIABAT_PRESSURE_STEP
    dry_pressure = np.arange(p0, lcl_hpa, -step)
    moist_pressure = np.concatenate([np.arange(lcl_hpa - step, top, -step), [top]])
    if dry_pressure.size:
        dry_temperature = dry_lapse(
            registry.Quantity(dry_pressure, "hPa"),
            start_temperature,
            reference_pressure=start_pressure,
        ).m_as("degC")
    else:  # A saturated parcel: Normand's point is the parcel start.
        dry_temperature = np.empty(0, dtype=np.float64)
    moist_temperature = moist_lapse(
        registry.Quantity(moist_pressure, "hPa"),
        lcl_temperature,
        reference_pressure=lcl_pressure,
    ).m_as("degC")
    pressure = np.concatenate([dry_pressure, [lcl_hpa], moist_pressure])
    temperature = np.concatenate(
        [dry_temperature, [float(lcl_temperature.m_as("degC"))], moist_temperature]
    )
    return Profile(
        pressure=registry.Quantity(pressure, "hPa"),
        temperature=registry.Quantity(temperature, "degC"),
        lcl_pressure=lcl_pressure,
        lcl_temperature=lcl_temperature,
        parcel=parcel,
        label=label,
    )


def _parcel_start(
    snd: Sounding, parcel: str
) -> tuple[pint.Quantity, pint.Quantity, pint.Quantity]:
    """Select the lifted parcel's starting point (spec §3.3).

    Parameters
    ----------
    snd : Sounding
        The environment sounding.
    parcel : str
        The parcel option: ``"surface"`` or ``"mixed-layer"``.

    Returns
    -------
    tuple of pint.Quantity
        Scalar ``(pressure, temperature, dewpoint)`` of the parcel start.

    Raises
    ------
    MissingDataError
        If the sounding has no dewpoint.
    ValueError
        If `parcel` is not a known option.
    """
    if parcel not in _PARCELS:
        msg = f"parcel must be one of {_PARCELS!r}, got {parcel!r}"
        raise ValueError(msg)
    if snd.dewpoint is None:
        msg = "parcel analysis needs dewpoint: this sounding has none (spec §3.4)"
        raise MissingDataError(msg)
    if parcel == "mixed-layer":
        # Function-local so `import tephpy` stays light (spec §10 item 10).
        from metpy.calc import mixed_parcel  # noqa: PLC0415

        pressure, temperature, dewpoint = mixed_parcel(
            snd.pressure, snd.temperature, snd.dewpoint
        )
        return pressure.to("hPa"), temperature.to("degC"), dewpoint.to("degC")
    return snd.pressure[0], snd.temperature[0], snd.dewpoint[0]


def _lcl_used(
    start_pressure: pint.Quantity,
    start_temperature: pint.Quantity,
    start_dewpoint: pint.Quantity,
    cloud_base_correction: object,
) -> tuple[pint.Quantity, pint.Quantity]:
    """Locate the LCL the ascent uses, applying any requested correction.

    Parameters
    ----------
    start_pressure : pint.Quantity
        Scalar parcel-start pressure.
    start_temperature : pint.Quantity
        Scalar parcel-start temperature.
    start_dewpoint : pint.Quantity
        Scalar parcel-start dewpoint.
    cloud_base_correction : pint.Quantity or None
        The pressure-dimension correction, or ``None`` for the plain
        Normand's point.

    Returns
    -------
    tuple of pint.Quantity
        The scalar ``(pressure, temperature)`` of the LCL the path uses,
        in hPa and degrees Celsius. The corrected LCL temperature is
        re-read from the dry adiabat at the corrected pressure.

    Raises
    ------
    TephpyUnitsError
        If the correction is not a pressure-dimension quantity.
    TephpyValidationError
        If the correction places the LCL below the parcel start.
    """
    lcl_pressure, lcl_temperature = normand_point(
        start_pressure, start_temperature, start_dewpoint
    )
    if cloud_base_correction is None:
        return lcl_pressure, lcl_temperature
    correction = _scalar_quantity(
        cloud_base_correction, "cloud_base_correction", {}, "[pressure]"
    )
    corrected = (lcl_pressure + correction).to("hPa")
    if float(corrected.m_as("hPa")) > float(start_pressure.m_as("hPa")):
        msg = (
            f"cloud_base_correction ({correction:~P}) places the LCL at "
            f"{corrected:~P}, below the {start_pressure:~P} parcel start"
        )
        raise TephpyValidationError(msg)
    # Function-local so `import tephpy` stays light (spec §10 item 10).
    from metpy.calc import dry_lapse  # noqa: PLC0415

    corrected_temperature = dry_lapse(
        corrected, start_temperature, reference_pressure=start_pressure
    )
    return corrected, corrected_temperature.to("degC")


def _require_moist_ascent(snd: Sounding, lcl_pressure: pint.Quantity) -> None:
    """Require the profile to extend above the LCL the ascent uses.

    Parameters
    ----------
    snd : Sounding
        The environment sounding.
    lcl_pressure : pint.Quantity
        Scalar pressure of the LCL the ascent uses.

    Raises
    ------
    ProfileTooShortError
        If the profile tops out at or below the LCL — no moist ascent
        exists (spec §6).
    """
    top = float(snd.pressure[-1].m_as("hPa"))
    lcl_hpa = float(lcl_pressure.m_as("hPa"))
    if top >= lcl_hpa:
        msg = (
            f"the profile tops out at {top:g} hPa, at or below the parcel's "
            f"{lcl_hpa:g} hPa LCL: no moist ascent exists"
        )
        raise ProfileTooShortError(msg)
