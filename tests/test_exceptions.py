# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the public exception hierarchy (spec §6)."""

from __future__ import annotations

import pytest

from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    NonMonotonicPressureError,
    TephpyError,
    TephpyUnitsError,
    TephpyValidationError,
)


def test_hierarchy():
    """Every tephpy exception is catchable as TephpyError."""
    assert issubclass(TephpyUnitsError, TephpyError)
    assert issubclass(TephpyValidationError, TephpyError)
    assert issubclass(NonMonotonicPressureError, TephpyValidationError)
    assert issubclass(DewpointExceedsTemperatureError, TephpyValidationError)
    assert issubclass(TephpyError, Exception)


def test_validation_error_carries_levels():
    error = TephpyValidationError("bad levels", levels=(2, 5))
    assert error.levels == (2, 5)
    assert str(error) == "bad levels"


def test_validation_error_levels_default_empty():
    assert TephpyValidationError("nothing specific").levels == ()


@pytest.mark.parametrize(
    "exception", [NonMonotonicPressureError, DewpointExceedsTemperatureError]
)
def test_subclasses_carry_levels(exception):
    error = exception("boom", levels=(1,))
    assert error.levels == (1,)
    with pytest.raises(TephpyError):
        raise error
