# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Boundary units coercion over MetPy's pint registry (spec §5).

Every public tephpy boundary accepts pint quantities and converts
internally; bare arrays are accepted only with an explicit ``units=``
argument — never silently assumed. At multi-argument boundaries ``units=``
is a mapping keyed by argument or field name, validated by
:func:`check_units_mapping`; each value then passes through
:func:`as_quantity`, the single coercion helper.

tephpy standardizes on MetPy's registry — one registry across tephpy,
MetPy, and user code — so quantities flow into ``metpy.calc`` without
cross-registry errors. MetPy is imported function-locally so that
``import tephpy`` stays light (spec §10 item 10).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from tephpy.exceptions import TephpyUnitsError, TephpyValidationError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    import pint

__all__ = ["as_quantity", "check_units_mapping"]


def check_units_mapping(
    units: Mapping[str, str] | None, *, allowed: Iterable[str]
) -> dict[str, str]:
    """Validate the keys of a boundary's ``units=`` mapping.

    Parameters
    ----------
    units : mapping of str to str or None
        The ``units=`` argument: argument or field names mapped to unit
        strings, or ``None`` when not given.
    allowed : iterable of str
        The argument or field names this boundary accepts.

    Returns
    -------
    dict of str to str
        The validated mapping (empty for ``None``).

    Raises
    ------
    TephpyUnitsError
        If the mapping names an unknown argument or field.
    """
    if units is None:
        return {}
    unknown = set(units) - set(allowed)
    if unknown:
        msg = (
            f"units= names unknown argument(s) {sorted(unknown)!r}; "
            f"expected a mapping keyed by {sorted(allowed)!r}"
        )
        raise TephpyUnitsError(msg)
    return dict(units)


def as_quantity(
    value: object, *, name: str, units: str | None = None, dimension: str
) -> pint.Quantity:
    """Coerce one boundary argument to a MetPy-registry pint quantity.

    A pint quantity (from any registry) is re-wrapped onto MetPy's
    registry; a bare array is wrapped with the required `units`. Either
    way the result is float64 and dimension-checked.

    Parameters
    ----------
    value : object
        The argument value: a pint quantity, or a bare array-like with
        `units` given.
    name : str
        The argument or field name, used in error messages.
    units : str, optional
        The unit for a bare array-like `value` (from the boundary's
        ``units=`` mapping). Must be omitted when `value` is already a
        quantity.
    dimension : str
        The required pint dimensionality, e.g. ``"[pressure]"``;
        ``""`` means dimensionless.

    Returns
    -------
    pint.Quantity
        The float64 quantity on MetPy's registry.

    Raises
    ------
    TephpyUnitsError
        For unit-less input without `units`, the ambiguous
        quantity-plus-`units` case, an unparsable unit string, or the
        wrong dimensionality.
    TephpyValidationError
        If the value holds non-numeric elements (e.g. string
        missing-markers) that cannot coerce to float64.
    """
    # Function-local so `import tephpy` stays light (spec §5, §10 item 10).
    from metpy.units import units as registry  # noqa: PLC0415
    import pint  # noqa: PLC0415

    if isinstance(value, pint.Quantity):
        if units is not None:
            msg = (
                f"{name!r} is already a quantity, but units= names it too: "
                f"drop the units[{name!r}] entry or pass a bare array"
            )
            raise TephpyUnitsError(msg)
        raw: object = value.magnitude
        unit = str(value.units)
    else:
        if units is None:
            msg = (
                f"{name!r} has no units: pass a pint quantity, or add "
                f'units={{"{name}": "<unit>"}}'
            )
            raise TephpyUnitsError(msg)
        raw = value
        unit = units
    try:
        magnitude = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as error:
        msg = f"{name!r} is not numeric and cannot coerce to float64: {error}"
        raise TephpyValidationError(msg) from error
    try:
        quantity = registry.Quantity(magnitude, unit)
    except (pint.PintError, TypeError, ValueError) as error:
        msg = f"{name!r} has an unparsable unit {unit!r}: {error}"
        raise TephpyUnitsError(msg) from error
    if not quantity.check(dimension):
        expected = dimension or "dimensionless"
        msg = (
            f"{name!r} has dimensionality {quantity.dimensionality} "
            f"({quantity.units}); expected {expected}"
        )
        raise TephpyUnitsError(msg)
    return quantity
