# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The ``Sounding`` data model (spec §3.4).

A :class:`Sounding` is a frozen dataclass holding one ascent's
pressure/temperature/dewpoint/wind arrays as pint quantities on MetPy's
registry, plus optional station/time metadata and a derived legend label.
Inputs are coerced and validated at construction — bad data fails at
ingest, not mid-plot (spec §6) — and pressure is normalized to decreasing
(surface-first) storage with all arrays reversed together, so downstream
``metpy.calc`` sees one orientation.

The pandas/xarray constructors consume the objects handed to them —
neither library is imported at runtime — so ``import tephpy`` stays
light (spec §10 item 10).
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

import numpy as np

from tephpy._constants import SOUNDING_LABEL_FORMAT
from tephpy._units import as_quantity, check_units_mapping
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    NonMonotonicPressureError,
    TephpyUnitsError,
    TephpyValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pandas as pd
    import pint
    import xarray as xr

__all__ = ["Sounding"]

#: The data fields with their required dimensionalities (spec §5);
#: ``""`` means dimensionless (wind direction is an angle).
_FIELD_DIMENSIONS: Final[dict[str, str]] = {
    "pressure": "[pressure]",
    "temperature": "[temperature]",
    "dewpoint": "[temperature]",
    "wind_speed": "[speed]",
    "wind_direction": "",
}

#: Minimum number of levels in a sounding.
_MIN_LEVELS: Final[int] = 2


@dataclasses.dataclass(frozen=True, eq=False)
class Sounding:
    """One sounding: quantified profile arrays plus metadata (spec §3.4).

    Pressure and temperature are required; dewpoint and wind are optional,
    and the two wind fields must arrive together. Bare arrays need the
    ``units=`` mapping; a constructed Sounding always holds pint
    quantities on MetPy's registry, with pressure stored decreasing
    (surface-first). NaN gaps are data everywhere except pressure.

    Attributes
    ----------
    pressure : pint.Quantity
        Level pressures; required, finite, and strictly monotonic (either
        direction accepted, normalized to decreasing).
    temperature : pint.Quantity
        Level temperatures; required.
    dewpoint : pint.Quantity or None
        Level dewpoints; where dewpoint and temperature are both non-NaN,
        dewpoint above temperature is rejected (equality — saturation —
        is physical).
    wind_speed : pint.Quantity or None
        Level wind speeds; requires `wind_direction`.
    wind_direction : pint.Quantity or None
        Level wind directions (degrees from north); requires `wind_speed`.
    station : str or None
        Station identifier, e.g. ``"72357"``.
    time : datetime.datetime or None
        Launch time; ``numpy.datetime64`` input is accepted, naive
        datetimes are read as UTC, and aware ones are converted to UTC.
    label : str or None
        Legend text. When not given it derives as e.g.
        ``"72357 2013-05-20 12Z"`` if both `station` and `time` are
        present, else ``None`` — and ``None`` means no legend entry.
    units : mapping of str to str, optional
        Construction-only (not stored): unit strings for bare-array
        fields, keyed by field name, e.g. ``units={"pressure": "hPa",
        "temperature": "degC"}`` (spec §5).
    """

    pressure: pint.Quantity
    temperature: pint.Quantity
    dewpoint: pint.Quantity | None = None
    wind_speed: pint.Quantity | None = None
    wind_direction: pint.Quantity | None = None
    station: str | None = None
    time: datetime | None = None
    label: str | None = None
    units: dataclasses.InitVar[Mapping[str, str] | None] = None

    def __post_init__(self, units: Mapping[str, str] | None) -> None:
        """Coerce, validate, and normalize the constructed sounding.

        Parameters
        ----------
        units : mapping of str to str or None
            The ``units=`` mapping for bare-array fields.
        """
        for name in ("pressure", "temperature"):
            if getattr(self, name) is None:
                msg = f"pressure and temperature are required: {name!r} is None"
                raise TypeError(msg)
        mapping = check_units_mapping(units, allowed=_FIELD_DIMENSIONS)
        for name, dimension in _FIELD_DIMENSIONS.items():
            value = getattr(self, name)
            if value is None:
                continue
            quantity = as_quantity(
                value, name=name, units=mapping.get(name), dimension=dimension
            )
            object.__setattr__(self, name, quantity)
        self._validate_shapes()
        self._validate_wind_pairing()
        self._validate_dewpoint()
        self._normalize_pressure()
        self._normalize_time()
        self._derive_label()

    def _fields_present(self) -> dict[str, pint.Quantity]:
        """Collect the data fields provided to this sounding.

        Returns
        -------
        dict of str to pint.Quantity
            Field name to coerced quantity, in field order.
        """
        present = {}
        for name in _FIELD_DIMENSIONS:
            value = getattr(self, name)
            if value is not None:
                present[name] = value
        return present

    def _validate_shapes(self) -> None:
        """Require 1-D equal-length arrays of at least two levels."""
        lengths = {}
        for name, quantity in self._fields_present().items():
            if quantity.magnitude.ndim != 1:
                msg = f"{name!r} must be 1-D, got {quantity.magnitude.ndim}-D"
                raise TephpyValidationError(msg)
            lengths[name] = quantity.magnitude.size
        if len(set(lengths.values())) > 1:
            msg = f"fields must be equal length, got {lengths!r}"
            raise TephpyValidationError(msg)
        if min(lengths.values()) < _MIN_LEVELS:
            msg = f"a sounding needs at least {_MIN_LEVELS} levels, got {lengths!r}"
            raise TephpyValidationError(msg)

    def _validate_wind_pairing(self) -> None:
        """Require wind speed and direction to arrive together."""
        if (self.wind_speed is None) != (self.wind_direction is None):
            missing = "wind_direction" if self.wind_direction is None else "wind_speed"
            msg = (
                "wind_speed and wind_direction must arrive together: "
                f"{missing!r} is missing"
            )
            raise TephpyValidationError(msg)

    def _normalize_pressure(self) -> None:
        """Require finite, strictly monotonic pressure; store it decreasing.

        Increasing input is accepted and reversed — with every data array
        reversed together — so storage is always surface-first.
        """
        pressure = self.pressure.magnitude
        bad = np.flatnonzero(~np.isfinite(pressure))
        if bad.size:
            levels = tuple(int(index) for index in bad)
            msg = f"pressure must be finite at every level; offending levels {levels}"
            raise TephpyValidationError(msg, levels=levels)
        diffs = np.diff(pressure)
        if np.all(diffs < 0.0):
            return
        if np.all(diffs > 0.0):
            for name, quantity in self._fields_present().items():
                object.__setattr__(self, name, quantity[::-1])
            return
        direction = 1.0 if pressure[-1] > pressure[0] else -1.0
        offending = np.flatnonzero(diffs * direction <= 0.0) + 1
        levels = tuple(int(index) for index in offending)
        msg = (
            "pressure must be strictly monotonic; "
            f"offending levels {levels} of the {pressure.size}-level profile"
        )
        raise NonMonotonicPressureError(msg, levels=levels)

    def _validate_dewpoint(self) -> None:
        """Reject dewpoint above temperature where both are non-NaN.

        Runs before pressure normalization, so ``levels`` index the
        caller's input arrays — the same frame as the pressure errors.
        """
        if self.dewpoint is None:
            return
        temperature = self.temperature.m_as("degC")
        dewpoint = self.dewpoint.m_as("degC")
        both = np.isfinite(temperature) & np.isfinite(dewpoint)
        bad = np.flatnonzero(both & (dewpoint > temperature))
        if bad.size:
            levels = tuple(int(index) for index in bad)
            msg = (
                "dewpoint exceeds temperature (equality is saturation and "
                f"accepted); offending levels {levels}"
            )
            raise DewpointExceedsTemperatureError(msg, levels=levels)

    def _normalize_time(self) -> None:
        """Read naive times as UTC and convert aware ones to UTC."""
        # Typed `object`: the field annotation says datetime, but the
        # boundary also accepts numpy.datetime64 and rejects the rest.
        time: object = self.time
        if time is None:
            return
        if isinstance(time, np.datetime64):
            if np.isnat(time):
                msg = "time is NaT (not-a-time): pass a real launch time, or None"
                raise TypeError(msg)
            time = time.astype("datetime64[us]").item()
        if not isinstance(time, datetime):
            msg = f"time must be a datetime or numpy.datetime64, got {type(time)!r}"
            raise TypeError(msg)
        time = time.replace(tzinfo=UTC) if time.tzinfo is None else time.astimezone(UTC)
        object.__setattr__(self, "time", time)

    def _derive_label(self) -> None:
        """Derive the legend label when not explicitly given (spec §3.4)."""
        if self.label is None and self.station is not None and self.time is not None:
            label = SOUNDING_LABEL_FORMAT.format(station=self.station, time=self.time)
            object.__setattr__(self, "label", label)

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        *,
        units: Mapping[str, str] | None = None,
        station: str | None = None,
        time: datetime | None = None,
        label: str | None = None,
        **column_map: str,
    ) -> Sounding:
        """Build a sounding from a pandas DataFrame (spec §3.4).

        Column names default to the field names; `column_map` overrides
        per field (e.g. ``dewpoint="dwpt"``). Columns are bare arrays, so
        the present fields need the ``units=`` mapping.

        Parameters
        ----------
        df : pandas.DataFrame
            The profile table; must contain pressure and temperature
            columns.
        units : mapping of str to str, optional
            Unit strings keyed by field name (spec §5).
        station : str, optional
            Station identifier.
        time : datetime.datetime, optional
            Launch time; ``pandas.Timestamp`` and ``numpy.datetime64``
            are accepted.
        label : str, optional
            Legend text override.
        **column_map : str
            Field names mapped to their column names in `df`.

        Returns
        -------
        Sounding
            The validated sounding.

        Raises
        ------
        KeyError
            If a required or explicitly mapped column is missing.
        TypeError
            If `column_map` names an unknown field.
        """
        cls._check_field_map(column_map)
        data: dict[str, np.ndarray] = {}
        for name in _FIELD_DIMENSIONS:
            column = column_map.get(name, name)
            if column in df.columns:
                data[name] = df[column].to_numpy()
            elif name in column_map or name in ("pressure", "temperature"):
                msg = f"column {column!r} (field {name!r}) is not in the DataFrame"
                raise KeyError(msg)
        return cls(units=units, station=station, time=time, label=label, **data)

    @classmethod
    def from_dataset(
        cls,
        ds: xr.Dataset,
        *,
        units: Mapping[str, str] | None = None,
        station: str | None = None,
        time: datetime | None = None,
        label: str | None = None,
        **var_map: str,
    ) -> Sounding:
        """Build a sounding from an xarray Dataset (spec §3.4).

        Variable names default to the field names; `var_map` overrides per
        field. Units are read from each variable's ``attrs["units"]`` (the
        xarray/CF convention); the ``units=`` mapping is the explicit
        override.

        Parameters
        ----------
        ds : xarray.Dataset
            The profile dataset; must contain pressure and temperature
            variables.
        units : mapping of str to str, optional
            Unit strings keyed by field name, overriding
            ``attrs["units"]``.
        station : str, optional
            Station identifier.
        time : datetime.datetime, optional
            Launch time; ``pandas.Timestamp`` and ``numpy.datetime64``
            are accepted.
        label : str, optional
            Legend text override.
        **var_map : str
            Field names mapped to their variable names in `ds`.

        Returns
        -------
        Sounding
            The validated sounding.

        Raises
        ------
        KeyError
            If a required or explicitly mapped variable is missing.
        TephpyUnitsError
            If a field has neither ``attrs["units"]`` nor a ``units=``
            entry.
        TypeError
            If `var_map` names an unknown field.
        """
        cls._check_field_map(var_map)
        mapping = check_units_mapping(units, allowed=_FIELD_DIMENSIONS)
        data: dict[str, np.ndarray] = {}
        resolved: dict[str, str] = {}
        for name in _FIELD_DIMENSIONS:
            variable = var_map.get(name, name)
            if variable not in ds.variables:
                if name in var_map or name in ("pressure", "temperature"):
                    msg = f"variable {variable!r} (field {name!r}) not in the Dataset"
                    raise KeyError(msg)
                continue
            unit = mapping.get(name) or ds[variable].attrs.get("units")
            if not unit:
                msg = (
                    f"{name!r} (variable {variable!r}) has no attrs['units'] "
                    f'and no override: add units={{"{name}": "<unit>"}}'
                )
                raise TephpyUnitsError(msg)
            data[name] = ds[variable].to_numpy()
            resolved[name] = unit
        return cls(units=resolved, station=station, time=time, label=label, **data)

    @staticmethod
    def _check_field_map(field_map: Mapping[str, str]) -> None:
        """Reject unknown field names in a constructor's field mapping.

        Parameters
        ----------
        field_map : mapping of str to str
            Field names mapped to column or variable names.

        Raises
        ------
        TypeError
            If the mapping names an unknown field.
        """
        unknown = set(field_map) - set(_FIELD_DIMENSIONS)
        if unknown:
            msg = (
                f"unknown field(s) {sorted(unknown)!r}; "
                f"expected {sorted(_FIELD_DIMENSIONS)!r}"
            )
            raise TypeError(msg)
