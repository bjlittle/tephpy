# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the shared ingest helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import numpy as np
import pytest

from tephpy.io._util import coerce_time, strictly_decreasing


def test_coerce_time_naive_string_reads_as_utc():
    assert coerce_time("2026-07-21 12:00") == datetime(2026, 7, 21, 12, tzinfo=UTC)


def test_coerce_time_aware_input_converts_to_utc():
    plus_two = timezone(timedelta(hours=2))
    when = coerce_time(datetime(2026, 7, 21, 14, tzinfo=plus_two))
    assert when == datetime(2026, 7, 21, 12, tzinfo=UTC)
    assert when.tzinfo == UTC


def test_coerce_time_rejects_non_iso_string():
    with pytest.raises(ValueError, match="Invalid isoformat"):
        coerce_time("21/07/2026 12Z")


def test_coerce_time_rejects_wrong_type():
    with pytest.raises(TypeError, match="datetime or an ISO 8601 string"):
        coerce_time(20260721)


def test_strictly_decreasing_passes_monotonic_input():
    pressure = np.array([1000.0, 850.0, 700.0])
    np.testing.assert_array_equal(strictly_decreasing(pressure), [True, True, True])


def test_strictly_decreasing_drops_duplicates_keeping_first():
    pressure = np.array([1000.0, 1000.0, 850.0, 850.0, 700.0])
    np.testing.assert_array_equal(
        strictly_decreasing(pressure), [True, False, True, False, True]
    )


def test_strictly_decreasing_drops_rises_against_the_running_minimum():
    pressure = np.array([1000.0, 900.0, 950.0, 850.0])
    np.testing.assert_array_equal(
        strictly_decreasing(pressure), [True, True, False, True]
    )


def test_strictly_decreasing_drops_non_finite_rows():
    pressure = np.array([np.nan, 1000.0, np.nan, 850.0])
    np.testing.assert_array_equal(
        strictly_decreasing(pressure), [False, True, False, True]
    )
