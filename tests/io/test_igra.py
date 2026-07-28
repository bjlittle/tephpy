# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the IGRA v2 reader (spec §3.4, §7).

The recorded fixture holds the Camborne 2026-07-21 00Z and 12Z ascents as
byte-faithful blocks (see ``tests/fixtures/io/README.md``); the 12Z ascent
is the same physical launch as the Wyoming fixture, so the surface values
cross-validate the two readers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import zipfile

import numpy as np
import pytest

from tephpy.exceptions import TephpyIOError
from tephpy.io import igra

FIXTURE = Path(__file__).parents[1] / "fixtures" / "io" / "UKM00003808-data-trimmed.txt"
WHEN = datetime(2026, 7, 21, 12, tzinfo=UTC)


def test_read_carries_the_fixture_profile():
    snd = igra.read(FIXTURE, time=WHEN)
    assert snd.station == "UKM00003808"
    assert snd.time == WHEN
    assert snd.label == "UKM00003808 2026-07-21 12Z"
    # The surface record: 101900 Pa, 19.6 degC, 3.7 degC depression,
    # 360 degrees at 4.1 m/s — the same launch as the Wyoming fixture
    # (19.7 degC surface), released 11:17 UTC.
    assert snd.pressure[0].m_as("hPa") == pytest.approx(1019.0)
    assert snd.temperature[0].m_as("degC") == pytest.approx(19.6)
    assert snd.dewpoint[0].m_as("degC") == pytest.approx(19.6 - 3.7)
    assert snd.wind_direction[0].m_as("degree") == pytest.approx(360.0)
    assert snd.wind_speed[0].m_as("m/s") == pytest.approx(4.1)


def test_read_sentinels_become_nan_gaps():
    snd = igra.read(FIXTURE, time=WHEN)
    # The second surviving record has -9999 wind fields.
    assert np.isnan(snd.wind_speed.magnitude).any()
    assert np.isnan(snd.dewpoint.magnitude).any()
    assert not np.isnan(snd.pressure.magnitude).any()


def test_read_accepts_the_distributed_zip_form(tmp_path):
    bundle = tmp_path / "UKM00003808-data.txt.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("UKM00003808-data.txt", FIXTURE.read_text())
    snd = igra.read(bundle, time="2026-07-21 12:00")
    assert snd.pressure[0].m_as("hPa") == pytest.approx(1019.0)


def test_read_without_time_is_ambiguous_for_several_soundings():
    with pytest.raises(
        TephpyIOError,
        match=r"holds 2 soundings spanning 2026-07-21 00Z to 2026-07-21 12Z",
    ):
        igra.read(FIXTURE)


def test_read_without_time_reads_a_single_sounding_file(tmp_path):
    lines = FIXTURE.read_text().splitlines()
    second = [i for i, line in enumerate(lines) if line.startswith("#")][1]
    single = tmp_path / "single.txt"
    single.write_text("\n".join(lines[:second]) + "\n")
    snd = igra.read(single)
    assert snd.time == datetime(2026, 7, 21, 0, tzinfo=UTC)


def test_read_unmatched_time_reports_the_nearest_ascents():
    with pytest.raises(TephpyIOError, match=r"nearest: 2026-07-21 12Z"):
        igra.read(FIXTURE, time="2026-07-21 13:00")


def test_read_rejects_a_file_without_headers(tmp_path):
    path = tmp_path / "noise.txt"
    path.write_text("this is not an IGRA station file\n")
    with pytest.raises(TephpyIOError, match="holds no IGRA v2 header records"):
        igra.read(path)


def test_read_rejects_a_truncated_block(tmp_path):
    lines = FIXTURE.read_text().splitlines()
    path = tmp_path / "truncated.txt"
    path.write_text("\n".join(lines[:10]) + "\n")
    with pytest.raises(TephpyIOError, match=r"declares .* levels but the file ends"):
        igra.read(path)


def test_read_rejects_a_malformed_data_record(tmp_path):
    lines = FIXTURE.read_text().splitlines()
    lines[1] = lines[1][:9] + "oopsie" + lines[1][15:]
    path = tmp_path / "malformed.txt"
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(TephpyIOError, match="malformed IGRA v2 data record on line 2"):
        igra.read(path, time="2026-07-21 00:00")


def test_read_rejects_a_multi_member_zip(tmp_path):
    bundle = tmp_path / "two.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("a.txt", "x")
        archive.writestr("b.txt", "y")
    with pytest.raises(TephpyIOError, match="expected one archive member"):
        igra.read(bundle)


def test_read_maps_unreadable_paths(tmp_path):
    with pytest.raises(TephpyIOError, match="could not read"):
        igra.read(tmp_path / "absent.txt")


def test_read_rejects_a_non_iso_time_string():
    with pytest.raises(ValueError, match="Invalid isoformat"):
        igra.read(FIXTURE, time="21/07/2026")
