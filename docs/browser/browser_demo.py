# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""CSV parsing for the documentation's in-browser tephigram demo."""

from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
from io import StringIO
import math

from tephpy import Sounding

REQUIRED_COLUMNS = ("pressure_hPa", "temperature_C")
OPTIONAL_COLUMNS = (
    "dewpoint_C",
    "wind_speed_m_s",
    "wind_direction_degree",
)
WIND_COLUMNS = ("wind_speed_m_s", "wind_direction_degree")

_FIELD_UNITS = {
    "pressure": "hPa",
    "temperature": "degC",
    "dewpoint": "degC",
    "wind_speed": "m/s",
    "wind_direction": "degree",
}


class DemoCSVError(ValueError):
    """A readable violation of the browser demo's CSV contract."""


@dataclass(frozen=True)
class ParsedSounding:
    """Numeric columns parsed from one demo CSV file."""

    pressure: tuple[float, ...]
    temperature: tuple[float, ...]
    dewpoint: tuple[float, ...] | None = None
    wind_speed: tuple[float, ...] | None = None
    wind_direction: tuple[float, ...] | None = None

    def to_sounding(self, *, label: str) -> Sounding:
        """Construct the validated tephpy sounding represented by these columns.

        Parameters
        ----------
        label : str
            Label attached to the sounding, normally the uploaded filename.

        Returns
        -------
        Sounding
            A quantified and physically validated sounding.
        """
        values: dict[str, tuple[float, ...]] = {
            "pressure": self.pressure,
            "temperature": self.temperature,
        }
        for field in ("dewpoint", "wind_speed", "wind_direction"):
            value = getattr(self, field)
            if value is not None:
                values[field] = value
        units = {field: _FIELD_UNITS[field] for field in values}
        return Sounding(**values, label=label, units=units)


def _headers(row: list[str]) -> tuple[str, ...]:
    """Validate and normalize a CSV header row."""
    headers = tuple(cell.strip() for cell in row)
    if not headers or not any(headers) or "" in headers:
        msg = "the CSV header contains a missing column name"
        raise DemoCSVError(msg)
    duplicates = sorted(name for name, count in Counter(headers).items() if count > 1)
    if duplicates:
        msg = f"duplicate CSV header(s): {', '.join(duplicates)}"
        raise DemoCSVError(msg)
    missing = [name for name in REQUIRED_COLUMNS if name not in headers]
    if missing:
        msg = f"missing required CSV header(s): {', '.join(missing)}"
        raise DemoCSVError(msg)
    wind_present = [name in headers for name in WIND_COLUMNS]
    if wind_present[0] != wind_present[1]:
        missing_wind = WIND_COLUMNS[wind_present.index(False)]
        msg = (
            "wind columns must be supplied together; "
            f"missing CSV header: {missing_wind}"
        )
        raise DemoCSVError(msg)
    return headers


def _number(value: str, *, column: str, line: int) -> float:
    """Parse one numeric cell, mapping blank cells to NaN."""
    stripped = value.strip()
    if not stripped:
        return math.nan
    try:
        return float(stripped)
    except ValueError as exc:
        msg = f"line {line}, column {column}: expected a number, got {value!r}"
        raise DemoCSVError(msg) from exc


def parse_sounding_csv(text: str) -> ParsedSounding:
    """Parse the browser demo's deliberately small sounding CSV format.

    Parameters
    ----------
    text : str
        CSV text with the documented required and optional headers.

    Returns
    -------
    ParsedSounding
        Parsed numeric columns. Blank cells are NaN and absent optional
        columns are ``None``.

    Raises
    ------
    DemoCSVError
        If the CSV structure, headers, or numeric cells violate the demo
        contract. Physical validation is deliberately left to `Sounding`.
    """
    reader = csv.reader(StringIO(text), strict=True)
    try:
        header_row = next(reader)
    except StopIteration as exc:
        msg = "the CSV is empty; expected a header row"
        raise DemoCSVError(msg) from exc
    except csv.Error as exc:
        msg = f"could not read the CSV header: {exc}"
        raise DemoCSVError(msg) from exc

    if header_row:
        header_row[0] = header_row[0].removeprefix("\N{BYTE ORDER MARK}")
    headers = _headers(header_row)
    indices = {name: index for index, name in enumerate(headers)}
    present_columns = tuple(
        column for column in (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS) if column in indices
    )
    columns: dict[str, list[float]] = {name: [] for name in present_columns}

    try:
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) > len(headers):
                msg = (
                    f"line {reader.line_num}: found {len(row)} cells for "
                    f"{len(headers)} headers"
                )
                raise DemoCSVError(msg)
            padded = [*row, *([""] * (len(headers) - len(row)))]
            for column in present_columns:
                columns[column].append(
                    _number(
                        padded[indices[column]],
                        column=column,
                        line=reader.line_num,
                    )
                )
    except csv.Error as exc:
        msg = f"could not read CSV line {reader.line_num}: {exc}"
        raise DemoCSVError(msg) from exc

    if not columns[REQUIRED_COLUMNS[0]]:
        msg = "the CSV contains no data rows"
        raise DemoCSVError(msg)

    return ParsedSounding(
        pressure=tuple(columns["pressure_hPa"]),
        temperature=tuple(columns["temperature_C"]),
        dewpoint=(tuple(columns["dewpoint_C"]) if "dewpoint_C" in columns else None),
        wind_speed=(
            tuple(columns["wind_speed_m_s"]) if "wind_speed_m_s" in columns else None
        ),
        wind_direction=(
            tuple(columns["wind_direction_degree"])
            if "wind_direction_degree" in columns
            else None
        ),
    )
