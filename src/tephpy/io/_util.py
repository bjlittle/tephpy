# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Helpers shared by the ingest readers (spec §3.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import numpy.typing as npt

__all__ = ["coerce_time", "strictly_decreasing"]


def coerce_time(time: datetime | str) -> datetime:
    """Read a launch time as a UTC datetime.

    Parameters
    ----------
    time : datetime.datetime or str
        The nominal launch time; a string is read with
        :meth:`datetime.datetime.fromisoformat`.

    Returns
    -------
    datetime.datetime
        The UTC time: naive input read as UTC, aware input converted.

    Raises
    ------
    TypeError
        If `time` is neither a datetime nor a string.
    ValueError
        If a `time` string is not ISO 8601.
    """
    # Typed `object`: the annotation says datetime or str, but the boundary
    # also rejects the rest at runtime (the Sounding._normalize_time idiom).
    value: object = time
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        msg = f"time must be a datetime or an ISO 8601 string, got {type(value)!r}"
        raise TypeError(msg)
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def strictly_decreasing(pressure: npt.NDArray[np.float64]) -> npt.NDArray[np.bool_]:
    """Keep the rows whose pressure strictly undercuts the running minimum.

    Parameters
    ----------
    pressure : numpy.ndarray
        Row pressures in file order (surface-first).

    Returns
    -------
    numpy.ndarray
        Boolean keep-mask: the first occurrence wins; non-finite
        pressures drop.
    """
    with np.errstate(invalid="ignore"):
        floor = np.minimum.accumulate(np.where(np.isfinite(pressure), pressure, np.inf))
    keep: npt.NDArray[np.bool_] = np.empty(pressure.shape, dtype=np.bool_)
    keep[0:1] = np.isfinite(pressure[0:1])
    keep[1:] = np.isfinite(pressure[1:]) & (pressure[1:] < floor[:-1])
    return keep
