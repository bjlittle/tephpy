# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Integrated Global Radiosonde Archive (IGRA) version 2 reader (spec §3.4).

:func:`read` takes one ascent from an IGRA v2 per-station file — the
as-distributed ``.zip`` or the extracted ``.txt``, sniffed with
``zipfile.is_zipfile`` rather than by suffix — parsing the fixed-width
records per NCEI's ``igra2-data-format.txt``: pressure in Pa, temperature
and dewpoint depression in tenths of °C, wind in degrees and tenths of
m s⁻¹, with the missing-value sentinels reading as NaN and dewpoint
derived as temperature minus depression. Unreadable, malformed, or
ambiguous input raises :class:`~tephpy.exceptions.TephpyIOError`; the
returned sounding passes the ordinary ingest validation (spec §6).
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import numpy as np

from tephpy._constants import IGRA_MISSING
from tephpy.exceptions import TephpyIOError
from tephpy.io._util import coerce_time, strictly_decreasing
from tephpy.sounding import Sounding

if TYPE_CHECKING:
    import os

__all__ = ["read"]

#: The nominal-hour sentinel for an ascent with no nominal hour.
_MISSING_HOUR = 99

#: Data-record slices (0-based) per NCEI ``igra2-data-format.txt``, with
#: the value scale to the sounding's unit.
_FIELDS: dict[str, tuple[slice, float, str]] = {
    "pressure": (slice(9, 15), 0.01, "hPa"),
    "temperature": (slice(22, 27), 0.1, "degC"),
    "dewpoint_depression": (slice(34, 39), 0.1, "delta_degC"),
    "wind_direction": (slice(40, 45), 1.0, "degree"),
    "wind_speed": (slice(46, 51), 0.1, "m/s"),
}


@dataclasses.dataclass(frozen=True)
class _Header:
    """One ascent's header record.

    ``line`` is the header's line index, ``levels`` its record count,
    ``station`` the 11-character IGRA identifier, and ``when`` the
    nominal UTC time — ``None`` when the nominal hour is missing.
    """

    line: int
    levels: int
    station: str
    when: datetime | None


def read(
    path: str | os.PathLike[str], *, time: datetime | str | None = None
) -> Sounding:
    """Read one sounding from an IGRA v2 per-station file.

    Parameters
    ----------
    path : str or os.PathLike
        The station file: the as-distributed ``.zip`` or the extracted
        ``.txt``.
    time : datetime.datetime or str, optional
        The nominal launch time selecting the ascent; a string is read
        with :meth:`datetime.datetime.fromisoformat`, and a naive value
        is read as UTC. May be omitted only when the file holds exactly
        one sounding (trimmed research subsets, fixtures).

    Returns
    -------
    Sounding
        The validated sounding, with the IGRA station identifier and
        the nominal time as metadata.

    Raises
    ------
    TephpyIOError
        For an unreadable or malformed file, a `time` matching no
        ascent (the nearest nominal times are reported), or an
        ambiguous read — several soundings with no ``time=`` selector
        (the file's count and span are reported).
    ValueError
        If a `time` string is not ISO 8601.
    """
    lines = _text(path).splitlines()
    headers = _headers(lines)
    if not headers:
        msg = f"{path!s} holds no IGRA v2 header records"
        raise TephpyIOError(msg)
    return _sounding(lines, _select(headers, time, path))


def _text(path: str | os.PathLike[str]) -> str:
    """Return a station file's text, transparently opening the zip form.

    Parameters
    ----------
    path : str or os.PathLike
        The station file path.

    Returns
    -------
    str
        The decoded file text.

    Raises
    ------
    TephpyIOError
        If the file is unreadable, or a zip without exactly one member.
    """
    # Function-local so `import tephpy` stays light (spec §3.4, §10 item 10).
    import zipfile  # noqa: PLC0415

    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != 1:
                    msg = (
                        f"{path!s} is not an IGRA v2 station file: expected "
                        f"one archive member, found {names!r}"
                    )
                    raise TephpyIOError(msg)
                return archive.read(names[0]).decode("ascii", errors="replace")
        with open(path, encoding="ascii", errors="replace") as handle:  # noqa: PTH123
            return handle.read()
    except OSError as error:
        msg = f"could not read {path!s}: {error}"
        raise TephpyIOError(msg) from error


def _headers(lines: list[str]) -> list[_Header]:
    """Collect the header records from a station file's lines.

    Parameters
    ----------
    lines : list of str
        The file's lines.

    Returns
    -------
    list of _Header
        One entry per ascent, in file order.

    Raises
    ------
    TephpyIOError
        If a header record does not parse.
    """
    headers = []
    for index, line in enumerate(lines):
        if not line.startswith("#"):
            continue
        try:
            year, month, day = int(line[13:17]), int(line[18:20]), int(line[21:23])
            hour = int(line[24:26])
            when = (
                None
                if hour == _MISSING_HOUR
                else datetime(year, month, day, hour, tzinfo=UTC)
            )
            headers.append(
                _Header(
                    line=index,
                    levels=int(line[32:36]),
                    station=line[1:12].strip(),
                    when=when,
                )
            )
        except ValueError as error:
            msg = f"malformed IGRA v2 header record on line {index + 1}: {line!r}"
            raise TephpyIOError(msg) from error
    return headers


def _select(
    headers: list[_Header],
    time: datetime | str | None,
    path: str | os.PathLike[str],
) -> _Header:
    """Select the requested ascent from a file's headers.

    Parameters
    ----------
    headers : list of _Header
        The file's ascents, in file order.
    time : datetime.datetime or str or None
        The nominal launch time, or ``None`` for the sole ascent.
    path : str or os.PathLike
        The station file path, for error messages.

    Returns
    -------
    _Header
        The selected ascent.

    Raises
    ------
    TephpyIOError
        For an ambiguous read (no `time` with several ascents) or a
        `time` matching no ascent.
    """
    if time is None:
        if len(headers) == 1:
            return headers[0]
        stamped = [header.when for header in headers if header.when is not None]
        span = (
            f" spanning {min(stamped):%Y-%m-%d %H}Z to {max(stamped):%Y-%m-%d %H}Z"
            if stamped
            else ""
        )
        msg = f"{path!s} holds {len(headers)} soundings{span}: pass time= to select one"
        raise TephpyIOError(msg)
    when = coerce_time(time)
    for header in headers:
        if header.when == when:
            return header
    nearest = sorted(
        (header.when for header in headers if header.when is not None),
        key=lambda stamp: abs(stamp - when),
    )[:3]
    listed = ", ".join(f"{stamp:%Y-%m-%d %H}Z" for stamp in nearest)
    msg = f"{path!s} has no sounding at {when:%Y-%m-%d %H:%M}Z (nearest: {listed})"
    raise TephpyIOError(msg)


def _sounding(lines: list[str], header: _Header) -> Sounding:
    """Parse one ascent's records into a sounding.

    Records without a pressure value are dropped (`Sounding` requires
    finite pressure), the sentinels read as NaN, dewpoint derives as
    temperature minus dewpoint depression, and rows whose pressure does
    not strictly undercut the running minimum drop keeping the first
    occurrence. An optional field that is entirely NaN is treated as
    absent, so the missing-data errors stay meaningful downstream
    (spec §6).

    Parameters
    ----------
    lines : list of str
        The file's lines.
    header : _Header
        The selected ascent.

    Returns
    -------
    Sounding
        The validated sounding.

    Raises
    ------
    TephpyIOError
        If a data record does not parse.
    """
    start = header.line + 1
    block = lines[start : start + header.levels]
    if len(block) < header.levels:
        msg = (
            f"IGRA v2 header on line {header.line + 1} declares "
            f"{header.levels} levels but the file ends after {len(block)}"
        )
        raise TephpyIOError(msg)
    columns: dict[str, list[float]] = {field: [] for field in _FIELDS}
    for offset, line in enumerate(block):
        for field, (chars, scale, _) in _FIELDS.items():
            cell = line[chars].strip()
            try:
                raw = int(cell)
            except ValueError as error:
                msg = (
                    f"malformed IGRA v2 data record on line "
                    f"{start + offset + 1}: {line!r}"
                )
                raise TephpyIOError(msg) from error
            columns[field].append(np.nan if raw in IGRA_MISSING else raw * scale)
    arrays = {
        field: np.asarray(values, dtype=np.float64) for field, values in columns.items()
    }
    keep = strictly_decreasing(arrays["pressure"])
    arrays = {field: values[keep] for field, values in arrays.items()}
    dewpoint = arrays["temperature"] - arrays.pop("dewpoint_depression")
    wind = ("wind_direction", "wind_speed")
    wind_absent = all(bool(np.all(np.isnan(arrays[field]))) for field in wind)
    return Sounding(
        arrays["pressure"],
        arrays["temperature"],
        dewpoint=None if bool(np.all(np.isnan(dewpoint))) else dewpoint,
        wind_speed=None if wind_absent else arrays["wind_speed"],
        wind_direction=None if wind_absent else arrays["wind_direction"],
        units={
            "pressure": "hPa",
            "temperature": "degC",
            "dewpoint": "degC",
            "wind_direction": "degree",
            "wind_speed": "m/s",
        },
        station=header.station,
        time=header.when,
    )
