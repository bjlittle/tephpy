# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The reference-page rendering of the configuration tables (configfile spec §3.6)."""

from __future__ import annotations

import builtins
import re

import tephpy
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


#: A dotted or bare Python name inside rendered type text.
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")


def rendered():
    """Return the reference page as ``render_reference`` renders it."""
    return _configfile.render_reference(tephpy.config)


def test_the_reference_names_every_option_and_no_others():
    """The page and the template render the same table (configfile spec §3.6)."""
    prefix = ".. py:attribute:: "
    emitted = {
        line.removeprefix(prefix)
        for line in rendered().splitlines()
        if line.startswith(prefix)
    }
    assert emitted == {
        f"tephpy.config.{section}.{option}"
        for section, options in CONFIG_DEFAULTS.items()
        for option in options
    }


def test_the_option_set_the_page_is_gated_against_is_not_empty():
    """Forty-two, so the gate above cannot pass by rendering nothing."""
    assert sum(len(options) for options in CONFIG_DEFAULTS.values()) == 42


def test_every_rendered_type_is_resolvable_text():
    """``str()`` of an annotation naming a class yields ``<class '...'>``.

    That reaches the page as neither valid type text nor a resolvable target,
    and the docs build is where it would surface — a build ``pixi run tests``
    never runs (configfile spec §3.4).
    """
    prefix = "   :type: "
    types = [
        line.removeprefix(prefix)
        for line in rendered().splitlines()
        if line.startswith(prefix)
    ]
    assert len(types) == 42
    for text in types:
        assert "<" not in text, text
        for name in NAME.findall(text):
            assert "." in name or hasattr(builtins, name), f"{name!r} in {text!r}"


def test_every_method_is_given_a_target():
    """Prose cross-references the methods; the page is where they resolve."""
    emitted = [
        line for line in rendered().splitlines() if line.startswith(".. py:method:: ")
    ]
    assert emitted == [
        ".. py:method:: tephpy.config.load(path=None)",
        ".. py:method:: tephpy.config.save(path=None)",
        ".. py:method:: tephpy.config.reset()",
        ".. py:method:: tephpy.config.context(**overrides)",
    ]


def test_a_default_is_rendered_by_its_kind():
    """Three branches, where the template's renderer has two.

    ``_format_default`` renders both ``None`` and an empty mapping as the empty
    string, because the template needs a line the reader can uncomment. The
    page has no such constraint: an absent default and an empty one are
    different facts and are printed differently (configfile spec §3.6).
    """
    text = rendered()
    assert "Default: unset" in text
    assert "Default: ``None``" not in text
    assert "Default: ``{}``" in text
    assert "Default: ``dimgrey``" in text
    assert "Default: ``[[1050.0, -40.0], [200.0, 40.0]]``" in text
