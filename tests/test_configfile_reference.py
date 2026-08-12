# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The reference-page rendering of the configuration tables (configfile spec §3.6)."""

from __future__ import annotations

from tephpy import _configfile
from tephpy._constants import CONFIG_DEFAULTS

#: Every option ``CONFIG_DETAILS`` is expected to carry. Written out rather than
#: derived, so that both losing a detail and gaining an ungated one are failures
#: (configfile spec §3.4).
EXPECTED_DETAILS = {
    (section, option)
    for section in (
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
    )
    for option in ("labels", "emphasis")
}


def test_details_name_only_real_options():
    """A detail cannot outlive the option it details (configfile spec §3.4)."""
    for section, options in _configfile.CONFIG_DETAILS.items():
        assert section in CONFIG_DEFAULTS, section
        assert set(options) <= set(CONFIG_DEFAULTS[section]), section


def test_the_detail_table_carries_what_it_is_expected_to():
    """The subset gate above passes vacuously over an empty table.

    Pinning membership is what makes it refuse its own empty input.
    """
    detailed = {
        (section, option)
        for section, options in _configfile.CONFIG_DETAILS.items()
        for option in options
    }
    assert detailed == EXPECTED_DETAILS


def test_every_detail_is_prose():
    """Details are sentences the reference page prints, not fragments."""
    for options in _configfile.CONFIG_DETAILS.values():
        for option, detail in options.items():
            assert detail.strip() == detail, option
            assert detail.endswith("."), option
            assert len(detail) > 40, option
