# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The sounding data tephpy ships (gallery spec §3.1)."""

from __future__ import annotations

import pytest

from tephpy import samples


def test_available_names_every_shipped_ascent():
    """The names are the gallery's, in the order the ascents were measured."""
    assert samples.available() == (
        "norman-12z",
        "norman-17z",
        "camborne-igra-12z",
        "camborne-wyoming-12z",
    )


@pytest.mark.parametrize("name", samples.available())
def test_path_is_a_real_file_beside_the_package(name):
    """An installed tephpy carries it, so it is a path that stays valid."""
    assert samples.path(name).is_file()
    assert samples.path(name).parent == samples.path(name).parent.resolve()


def test_path_takes_the_sample_name():
    """Two formats ship, so there is no file to return without being asked."""
    assert samples.path("camborne-wyoming-12z").suffix == ".csv"
    assert samples.path("camborne-igra-12z").suffix == ".txt"
    assert samples.path("norman-12z").suffix == ".txt"


def test_path_rejects_an_unknown_name_like_sounding_does():
    """One vocabulary for both accessors, and one error when it is missed."""
    with pytest.raises(ValueError, match="norman-12z"):
        samples.path("nowhere")


def test_the_camborne_pair_is_one_ascent_in_two_formats():
    """Two readers, one Sounding -- the reader how-to's whole point."""
    igra = samples.sounding("camborne-igra-12z")
    wyoming = samples.sounding("camborne-wyoming-12z")
    assert igra.time == wyoming.time
    # Same physical ascent through two archives, which thin it differently
    # and disagree in the last significant figure. The surface must agree to
    # about a tenth; the level counts need not agree at all.
    assert igra.pressure[0].m_as("hPa") == pytest.approx(
        wyoming.pressure[0].m_as("hPa"), abs=0.5
    )
    assert igra.temperature[0].m_as("degC") == pytest.approx(
        wyoming.temperature[0].m_as("degC"), abs=0.5
    )


def test_the_camborne_pair_names_its_station_the_way_each_archive_does():
    """Not the same string, and neither reading is wrong.

    IGRA identifies a station by an eleven-character id carrying a country
    and network code; the Wyoming archive uses the bare WMO number, which is
    what the id's last eight characters zero-pad. Coercing one to the other
    here would put an identifier on the data that its source does not use.
    """
    igra = samples.sounding("camborne-igra-12z")
    wyoming = samples.sounding("camborne-wyoming-12z")
    assert igra.station == "UKM00003808"
    assert wyoming.station == "03808"
    assert int(igra.station[3:]) == int(wyoming.station)


def test_every_sample_yields_a_usable_sounding():
    """A sample nothing can read is data that proves nothing."""
    for name in samples.available():
        snd = samples.sounding(name)
        assert snd.pressure.size > 0
        assert snd.temperature.size == snd.pressure.size


def test_sounding_reads_the_named_ascent():
    """The name selects an ascent, not merely the file holding both."""
    morning = samples.sounding("norman-12z")
    afternoon = samples.sounding("norman-17z")
    assert morning.station == afternoon.station
    assert morning.time.hour == 12
    assert afternoon.time.hour == 17


def test_sounding_carries_winds():
    """The barb and hodograph examples need them (gallery spec §3.1)."""
    snd = samples.sounding("norman-12z")
    assert snd.wind_speed is not None
    assert snd.wind_direction is not None


def test_unknown_sample_names_the_alternatives():
    """The message is the user's route out, so it lists what it accepts."""
    with pytest.raises(ValueError, match="norman-12z, norman-17z") as excinfo:
        samples.sounding("lerwick")
    assert "lerwick" in str(excinfo.value)
