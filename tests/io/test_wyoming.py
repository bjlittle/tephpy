# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the University of Wyoming reader (spec §3.4, §7).

The recorded fixture is a thinned but byte-faithful ``TEXT:CSV`` capture
(see ``tests/fixtures/io/README.md``); no test touches the network — the
transport seam (``_request``) is monkeypatched where ``fetch`` itself is
under test.
"""

from __future__ import annotations

from datetime import UTC, datetime
import io as stdlib_io
from pathlib import Path
import urllib.error
import urllib.request

import numpy as np
import pytest

from tephpy.exceptions import TephpyIOError
from tephpy.io import wyoming

FIXTURE = (
    Path(__file__).parents[1] / "fixtures" / "io" / "wyoming-03808-2026-07-21-12Z.csv"
)
WHEN = datetime(2026, 7, 21, 12, tzinfo=UTC)

HEADER = (
    "time,longitude,latitude,pressure_hPa,geopotential height_m,"
    "temperature_C,dew point temperature_C,ice point temperature_C,"
    "relative humidity_%,humidity wrt ice_%,mixing ratio_g/kg,"
    "wind direction_degree,wind speed_m/s"
)


def _parse_fixture():
    return wyoming._parse(FIXTURE.read_text(), station="03808", time=WHEN)


def test_parse_carries_the_fixture_profile():
    snd = _parse_fixture()
    assert snd.pressure.size == 61
    assert snd.pressure[0].m_as("hPa") == pytest.approx(1019.2)
    assert snd.temperature[0].m_as("degC") == pytest.approx(19.7)
    assert snd.dewpoint[0].m_as("degC") == pytest.approx(16.0)
    assert snd.wind_direction[0].m_as("degree") == pytest.approx(360.0)
    assert snd.wind_speed[0].m_as("m/s") == pytest.approx(4.1)


def test_parse_derives_the_label_from_metadata():
    assert _parse_fixture().label == "03808 2026-07-21 12Z"


def test_parse_missing_column_raises():
    text = "time,latitude\n2026-07-21 11:17:10,50.2184\n"
    with pytest.raises(TephpyIOError, match=r"column.*pressure_hPa"):
        wyoming._parse(text, station="03808", time=WHEN)


def test_parse_empty_response_raises():
    with pytest.raises(TephpyIOError, match="empty response"):
        wyoming._parse("", station="03808", time=WHEN)


def test_parse_non_numeric_cell_raises():
    text = f"{HEADER}\n2026,1,2,oops,4,5,6,7,8,9,10,11,12\n"
    with pytest.raises(TephpyIOError, match="'oops' is not numeric"):
        wyoming._parse(text, station="03808", time=WHEN)


def test_parse_blank_cells_read_as_nan_gaps():
    rows = [
        "2026,1,2,1000.0,4,15.0,,7,8,9,10,360,5.0",
        "2026,1,2,900.0,4,10.0,4.0,7,8,9,10,,",
    ]
    snd = wyoming._parse("\n".join([HEADER, *rows]), station=None, time=None)
    assert np.isnan(snd.dewpoint[0].magnitude)
    assert np.isnan(snd.wind_speed[1].magnitude)
    assert np.isnan(snd.wind_direction[1].magnitude)


def test_parse_all_nan_optional_fields_are_absent():
    rows = [
        "2026,1,2,1000.0,4,15.0,,7,8,9,10,,",
        "2026,1,2,900.0,4,10.0,,7,8,9,10,,",
    ]
    snd = wyoming._parse("\n".join([HEADER, *rows]), station=None, time=None)
    assert snd.dewpoint is None
    assert snd.wind_speed is None
    assert snd.wind_direction is None


def test_parse_drops_non_decreasing_pressure_rows():
    rows = [
        "2026,1,2,1000.0,4,15.0,5.0,7,8,9,10,360,5.0",
        "2026,1,2,1000.0,4,14.0,5.0,7,8,9,10,350,6.0",
        "2026,1,2,900.0,4,10.0,4.0,7,8,9,10,340,7.0",
    ]
    snd = wyoming._parse("\n".join([HEADER, *rows]), station=None, time=None)
    np.testing.assert_array_equal(snd.pressure.m_as("hPa"), [1000.0, 900.0])
    np.testing.assert_array_equal(snd.temperature.m_as("degC"), [15.0, 10.0])


def test_fetch_builds_the_documented_url(monkeypatch):
    seen = {}

    def fake_request(url, timeout):
        seen["url"], seen["timeout"] = url, timeout
        return FIXTURE.read_text()

    monkeypatch.setattr(wyoming, "_request", fake_request)
    snd = wyoming.fetch("03808", "2026-07-21 12:00")
    assert seen["url"] == (
        "https://weather.uwyo.edu/wsgi/sounding"
        "?datetime=2026-07-21%2012%3A00%3A00&id=03808&type=TEXT:CSV"
    )
    assert seen["timeout"] == 30.0
    assert snd.label == "03808 2026-07-21 12Z"


def test_fetch_timeout_argument_overrides_the_default(monkeypatch):
    seen = {}

    def fake_request(_url, timeout):
        seen["timeout"] = timeout
        return FIXTURE.read_text()

    monkeypatch.setattr(wyoming, "_request", fake_request)
    wyoming.fetch("03808", WHEN, timeout=5.0)
    assert seen["timeout"] == 5.0


def test_fetch_rejects_a_non_iso_time_string():
    with pytest.raises(ValueError, match="Invalid isoformat"):
        wyoming.fetch("03808", "21/07/2026")


def test_fetch_maps_http_errors_with_the_archive_reply(monkeypatch):
    def fake_urlopen(url, **_kwargs):
        raise urllib.error.HTTPError(
            url,
            400,
            "Bad Request",
            None,
            stdlib_io.BytesIO(b"Unable to retrieve the data for 03808.\n"),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(TephpyIOError, match="HTTP 400: Unable to retrieve the data"):
        wyoming.fetch("03808", WHEN)


def test_fetch_maps_transport_failures(monkeypatch):
    def fake_urlopen(_url, **_kwargs):
        reason = "name resolution failed"
        raise urllib.error.URLError(reason)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(TephpyIOError, match="could not reach the Wyoming archive"):
        wyoming.fetch("03808", WHEN)
