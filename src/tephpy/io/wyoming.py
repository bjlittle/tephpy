# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""University of Wyoming sounding archive reader (spec §3.4).

:func:`fetch` requests one ascent from the archive's post-2024 wsgi
interface in its machine-readable ``TEXT:CSV`` form — bare, self-describing
CSV (verified 2026-07-27) — over stdlib ``urllib`` behind a function-local
import, and hands the body to a pure, transport-free parser. Network
failures, HTTP errors, and the archive's "no data" replies raise
:class:`~tephpy.exceptions.TephpyIOError` summarising the upstream
response; the parsed sounding passes the ordinary ingest validation
(spec §6).
"""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING

import numpy as np

from tephpy._constants import WYOMING_TIMEOUT, WYOMING_URL
from tephpy.exceptions import TephpyIOError
from tephpy.io._util import coerce_time, strictly_decreasing
from tephpy.sounding import Sounding

if TYPE_CHECKING:
    from datetime import datetime

    import numpy.typing as npt

__all__ = ["fetch"]

#: Archive CSV column → (sounding field, pint unit) for the carried fields.
_COLUMNS: dict[str, tuple[str, str]] = {
    "pressure_hPa": ("pressure", "hPa"),
    "temperature_C": ("temperature", "degC"),
    "dew point temperature_C": ("dewpoint", "degC"),
    "wind direction_degree": ("wind_direction", "degree"),
    "wind speed_m/s": ("wind_speed", "m/s"),
}


def fetch(
    station: str, time: datetime | str, *, timeout: float | None = None
) -> Sounding:
    """Fetch one sounding from the University of Wyoming archive.

    Parameters
    ----------
    station : str
        The WMO station identifier, e.g. ``"03808"``.
    time : datetime.datetime or str
        The nominal launch time; a string is read with
        :meth:`datetime.datetime.fromisoformat`, and a naive value is
        read as UTC (the ``Sounding`` convention).
    timeout : float, optional
        The request timeout in seconds (default ``WYOMING_TIMEOUT``).

    Returns
    -------
    Sounding
        The validated sounding, with `station` and `time` as metadata —
        so the legend label derives for free (spec §3.4).

    Raises
    ------
    TephpyIOError
        For network failures, HTTP errors (including the archive's "no
        data at that time" and "unknown station" replies), or a response
        the parser does not recognise.
    ValueError
        If a `time` string is not ISO 8601.
    """
    when = coerce_time(time)
    from urllib.parse import quote  # noqa: PLC0415 -- spec §3.4 idiom

    url = WYOMING_URL.format(
        datetime=quote(f"{when:%Y-%m-%d %H:%M:%S}"), station=quote(station)
    )
    text = _request(url, WYOMING_TIMEOUT if timeout is None else timeout)
    return _parse(text, station=station, time=when)


def _request(url: str, timeout: float) -> str:
    """Perform the archive request, mapping failures to `TephpyIOError`.

    Parameters
    ----------
    url : str
        The request URL (the formatted ``WYOMING_URL``).
    timeout : float
        The request timeout in seconds.

    Returns
    -------
    str
        The decoded response body.

    Raises
    ------
    TephpyIOError
        For HTTP error statuses (summarising the archive's reply) or
        any transport failure.
    """
    # Function-local so `import tephpy` stays light (spec §3.4, §10 item 10).
    from urllib.error import HTTPError, URLError  # noqa: PLC0415
    from urllib.request import urlopen  # noqa: PLC0415

    try:
        # The URL derives from the https-scheme WYOMING_URL constant.
        with urlopen(url, timeout=timeout) as response:  # noqa: S310
            return str(response.read().decode("utf-8", errors="replace"))
    except HTTPError as error:
        with error:
            body = error.read().decode("utf-8", errors="replace").strip()
        summary = body.splitlines()[0] if body else str(error.reason)
        msg = f"the Wyoming archive returned HTTP {error.code}: {summary}"
        raise TephpyIOError(msg) from error
    except (TimeoutError, URLError, OSError) as error:
        msg = f"could not reach the Wyoming archive: {error}"
        raise TephpyIOError(msg) from error


def _parse(text: str, *, station: str, time: datetime) -> Sounding:
    """Parse one ``TEXT:CSV`` archive body into a sounding.

    Blank cells read as NaN (NaN gaps are data, spec §3.4); rows whose
    pressure does not strictly decrease on the running minimum are
    dropped keeping the first occurrence, so the dense BUFR-era ascents
    satisfy ``Sounding``'s strict monotonicity; an optional field that
    is entirely NaN is treated as absent, so the missing-data errors
    stay meaningful downstream (spec §6).

    Parameters
    ----------
    text : str
        The response body.
    station : str
        The WMO station identifier, carried as metadata.
    time : datetime.datetime
        The nominal launch time, carried as metadata.

    Returns
    -------
    Sounding
        The validated sounding.

    Raises
    ------
    TephpyIOError
        If the body is not the archive's CSV form, expected columns are
        missing, or a cell is not numeric.
    """
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        msg = "the Wyoming archive returned an empty response"
        raise TephpyIOError(msg)
    header = [column.strip() for column in rows[0]]
    missing = sorted(set(_COLUMNS) - set(header))
    if missing:
        msg = (
            f"unexpected Wyoming response format: column(s) {missing!r} "
            f"not in header {header!r}"
        )
        raise TephpyIOError(msg)
    indices = {column: header.index(column) for column in _COLUMNS}
    data: dict[str, list[float]] = {field: [] for field, _ in _COLUMNS.values()}
    for row in rows[1:]:
        if not row:
            continue
        for column, (field, _) in _COLUMNS.items():
            cell = row[indices[column]].strip()
            try:
                data[field].append(float(cell) if cell else np.nan)
            except ValueError as error:
                msg = (
                    f"unexpected Wyoming response format: {column!r} "
                    f"cell {cell!r} is not numeric"
                )
                raise TephpyIOError(msg) from error
    arrays = {
        field: np.asarray(values, dtype=np.float64) for field, values in data.items()
    }
    keep = strictly_decreasing(arrays["pressure"])
    arrays = {field: values[keep] for field, values in arrays.items()}
    fields: dict[str, npt.NDArray[np.float64] | None] = {}
    for field, _ in _COLUMNS.values():
        values = arrays[field]
        optional = field not in ("pressure", "temperature")
        fields[field] = None if optional and bool(np.all(np.isnan(values))) else values
    return Sounding(
        fields["pressure"],
        fields["temperature"],
        dewpoint=fields["dewpoint"],
        wind_speed=fields["wind_speed"],
        wind_direction=fields["wind_direction"],
        units=dict(_COLUMNS.values()),
        station=station,
        time=time,
    )
