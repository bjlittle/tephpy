# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The sounding data tephpy ships (gallery spec §3.1)."""

from __future__ import annotations

import pytest

from tephpy import samples


def test_available_names_both_ascents():
    """The names are the gallery's, in the order the ascents were measured."""
    assert samples.available() == ("norman-12z", "norman-17z")


def test_path_is_a_real_file_beside_the_package():
    """An installed tephpy carries it, so it is a path that stays valid."""
    assert samples.path().is_file()
    assert samples.path().parent == samples.path().parent.resolve()


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
        samples.sounding("camborne")
    assert "camborne" in str(excinfo.value)
