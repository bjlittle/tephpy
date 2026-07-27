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

from tephpy._units import as_quantity, check_units_mapping
from tephpy.exceptions import (
    TephpyValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pint

__all__ = ["Profile", "SoundingIndices"]

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
