# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the boundary units coercion helpers (spec §5)."""

from __future__ import annotations

import subprocess
import sys

from metpy.units import units
import numpy as np
import pint
import pytest

from tephpy._units import as_quantity, check_units_mapping
from tephpy.exceptions import TephpyUnitsError


def test_quantity_passes_through():
    quantity = units.Quantity(np.array([1000.0, 850.0]), "hPa")
    result = as_quantity(quantity, name="pressure", dimension="[pressure]")
    np.testing.assert_array_equal(result.magnitude, [1000.0, 850.0])
    assert result.units == units.hPa


def test_foreign_registry_quantity_rewrapped():
    """A quantity from another pint registry lands on MetPy's registry."""
    foreign = pint.UnitRegistry()
    quantity = foreign.Quantity(np.array([1000.0]), "hPa")
    result = as_quantity(quantity, name="pressure", dimension="[pressure]")
    assert result._REGISTRY is not foreign
    assert result.m_as("Pa") == pytest.approx(100000.0)


def test_bare_array_with_units():
    result = as_quantity(
        [20.0, 10.0], name="temperature", units="degC", dimension="[temperature]"
    )
    assert result.magnitude.dtype == np.float64
    assert result.m_as("K")[0] == pytest.approx(293.15)


def test_integer_input_coerced_to_float64():
    result = as_quantity(
        np.array([1000, 850]), name="pressure", units="hPa", dimension="[pressure]"
    )
    assert result.magnitude.dtype == np.float64


def test_bare_array_without_units_raises():
    with pytest.raises(TephpyUnitsError, match=r"'pressure' has no units"):
        as_quantity([1000.0], name="pressure", dimension="[pressure]")


def test_quantity_plus_units_is_ambiguous():
    quantity = units.Quantity([1000.0], "hPa")
    with pytest.raises(TephpyUnitsError, match="already a quantity"):
        as_quantity(quantity, name="pressure", units="hPa", dimension="[pressure]")


def test_wrong_dimensionality_raises():
    quantity = units.Quantity([20.0], "degC")
    with pytest.raises(TephpyUnitsError, match="expected \\[pressure\\]"):
        as_quantity(quantity, name="pressure", dimension="[pressure]")


def test_unparsable_unit_raises():
    with pytest.raises(TephpyUnitsError, match="unparsable unit"):
        as_quantity([1.0], name="pressure", units="bogons", dimension="[pressure]")


def test_dimensionless_dimension():
    """The empty dimension string means dimensionless (e.g. wind direction)."""
    result = as_quantity([270.0], name="wind_direction", units="deg", dimension="")
    assert result.dimensionless
    with pytest.raises(TephpyUnitsError, match="expected dimensionless"):
        as_quantity([270.0], name="wind_direction", units="hPa", dimension="")


def test_check_units_mapping():
    allowed = ("pressure", "temperature")
    assert check_units_mapping(None, allowed=allowed) == {}
    mapping = {"pressure": "hPa"}
    assert check_units_mapping(mapping, allowed=allowed) == mapping
    with pytest.raises(TephpyUnitsError, match="unknown argument"):
        check_units_mapping({"bogus": "hPa"}, allowed=allowed)


def test_import_tephpy_does_not_import_heavy_dependencies():
    """`import tephpy` must not import metpy, pandas, or xarray (item 10).

    MetPy loads on first use (as_quantity); pandas and xarray are never
    imported by tephpy at runtime at all; the readers keep their
    network/archive imports (urllib.request, zipfile) function-local
    (spec §3.4). Run in a subprocess so the check is independent of what
    this session already imported.
    """
    code = (
        "import sys, tephpy; raise SystemExit("
        "1 if {'metpy', 'pandas', 'xarray', 'urllib.request', 'zipfile'}"
        " & set(sys.modules) else 0)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603
