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

__all__ = ["fetch", "parse"]

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
        The WMO station identifier, e.g. ``"72357"``.
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
    TypeError
        If `time` is neither a datetime nor a string.
    ValueError
        If a `time` string is not ISO 8601.
    """
    when = coerce_time(time)
    from urllib.parse import quote  # noqa: PLC0415 -- spec §3.4 idiom

    url = WYOMING_URL.format(
        datetime=quote(f"{when:%Y-%m-%d %H:%M:%S}"), station=quote(station)
    )
    text = _request(url, WYOMING_TIMEOUT if timeout is None else timeout)
    return parse(text, station=station, time=when)


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
    from http.client import HTTPException  # noqa: PLC0415
    from urllib.error import HTTPError  # noqa: PLC0415
    from urllib.request import urlopen  # noqa: PLC0415

    try:
        # The URL derives from the https-scheme WYOMING_URL constant.
        with urlopen(url, timeout=timeout) as response:  # noqa: S310
            return str(response.read().decode("utf-8", errors="replace"))
    except HTTPError as error:
        try:
            with error:
                body = error.read().decode("utf-8", errors="replace").strip()
        except (OSError, HTTPException):
            # A truncated or reset error body must not mask the status.
            body = ""
        summary = body.splitlines()[0] if body else str(error.reason)
        msg = f"the Wyoming archive returned HTTP {error.code}: {summary}"
        raise TephpyIOError(msg) from error
    except (OSError, HTTPException) as error:
        # `URLError` and `TimeoutError` are `OSError`s; `HTTPException`
        # adds the http.client failures urlopen does not wrap, e.g. a
        # truncated body (`IncompleteRead`) or a malformed status line.
        msg = f"could not reach the Wyoming archive: {error}"
        raise TephpyIOError(msg) from error


def parse(
    text: str, *, station: str | None = None, time: datetime | str | None = None
) -> Sounding:
    """Read one ``TEXT:CSV`` archive body into a sounding.

    The route :func:`fetch` cannot serve: a body the caller already has.
    A response cached against a rate limit, one pulled through a proxy that
    this package's ``urlopen`` call cannot reach, or a bulk archive dump
    someone else downloaded -- each is the same text over the same format,
    with only the retrieval differing, and :func:`fetch` is retrieval. The
    two share this parser rather than agreeing by inspection, so a body read
    here and a body fetched become the same ``Sounding``.

    `station` and `time` are metadata rather than parsing input: the archive
    body carries neither the identifier that was asked for nor the nominal
    hour it was asked for, so a caller who knows them says so and gets the
    legend label derived (spec §3.4). A caller who does not gets a sounding
    without one, which is a sounding all the same.

    Blank cells read as NaN (NaN gaps are data, spec §3.4); rows whose
    pressure does not strictly decrease on the running minimum are
    dropped keeping the first occurrence, so the dense BUFR-era ascents
    satisfy ``Sounding``'s strict monotonicity; an optional field that
    is entirely NaN is treated as absent — and the wind pair as a unit,
    so a one-sided wind column passes as absent rather than tripping
    ``Sounding``'s pairing rule — keeping the missing-data errors
    meaningful downstream (spec §6).

    The archive's CSV is rectangular, so a row with fewer cells than
    the header is a truncated reply rather than a gap: it is rejected
    naming the row (the header is row 1). Trailing cells beyond the
    header are ignored — every carried column is located by its header
    index.

    Parameters
    ----------
    text : str
        The response body.
    station : str, optional
        The WMO station identifier, carried as metadata; omitted, no
        legend label derives.
    time : datetime.datetime or str, optional
        The nominal launch time, carried as metadata; a string is read
        the way :func:`fetch` reads one, so the two do not diverge.
        Omitted, no legend label derives.

    Returns
    -------
    Sounding
        The validated sounding.

    Raises
    ------
    TephpyIOError
        If the body is not readable as CSV at all, expected columns are
        missing, a row is shorter than the header, the header carries no
        data rows, or a cell is not numeric.
    TypeError
        If `time` is neither a datetime nor a string.
    ValueError
        If a `time` string is not ISO 8601.
    """
    when = None if time is None else coerce_time(time)
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as error:
        # A 200 body that is not CSV at all — a proxy page, a binary blob.
        msg = f"unexpected Wyoming response format: {error}"
        raise TephpyIOError(msg) from error
    if not rows:
        msg = "unexpected Wyoming response format: the body is empty"
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
    for number, row in enumerate(rows[1:], start=2):
        if not row:
            continue
        if len(row) < len(header):
            msg = (
                f"unexpected Wyoming response format: row {number} has "
                f"{len(row)} cell(s), expected at least {len(header)}"
            )
            raise TephpyIOError(msg)
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
    if not data["pressure"]:
        # A header carrying no records is a mangled reply, not a sounding
        # with too few levels (spec §3.4).
        msg = "unexpected Wyoming response format: no data rows after the header"
        raise TephpyIOError(msg)
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
    # The wind pair goes together: one wholly-missing component retires
    # both, so the failure downstream is the meaningful MissingDataError
    # from `plot_barbs`, not a `Sounding` pairing error here (spec §6).
    if fields["wind_speed"] is None or fields["wind_direction"] is None:
        fields["wind_speed"] = fields["wind_direction"] = None
    return Sounding(
        fields["pressure"],
        fields["temperature"],
        dewpoint=fields["dewpoint"],
        wind_speed=fields["wind_speed"],
        wind_direction=fields["wind_direction"],
        units=dict(_COLUMNS.values()),
        station=station,
        time=when,
    )
