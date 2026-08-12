# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Domain validation of a configuration value that has the right type.

The second stage of ``coerce`` (domain spec §3.1): every case here has already
passed the type check that ``tests/test_configfile.py`` covers.
"""

from __future__ import annotations

import re

import pytest

import tephpy
from tephpy import _configfile
from tephpy._constants import CURSOR_FIELD_NAMES, EDGES, EMPHASIS_STYLE_KEYS
from tephpy.exceptions import TephpyConfigWarning


def _write(tmp_path, text):
    path = tmp_path / "tephpyrc.yaml"
    path.write_text(text, encoding="utf-8")
    return path


#: A 320-digit plain integer: valid YAML, valid Python, and rejected only by
#: ``float()``'s own ``OverflowError`` -- the failure mode ``_as_float`` must
#: catch alongside ``_as_number``'s existing guard, or the emphasis-style
#: numeric path stops ``import tephpy`` outright (configfile spec §5.2).
_HUGE_INT = "9" * 320

#: One case per row of the domain spec §1 table, plus the three parts of
#: ``emphasis`` that table reaches only through a style key. Each is
#: ``(section, option, yaml, expected message tail)``, the tail picking up
#: after "which expects". Where the tail names a closed vocabulary it is
#: built from the constant rather than written out: the message is built
#: from that constant too, so a literal here would only be a second copy to
#: keep in step, and a legitimate new edge or field would fail this test
#: rather than Task 4's, which is the one that owns it.
REFUSED = [
    (
        "isotherms",
        "linewidth",
        "-1.0",
        "a positive, finite number, not the number -1.0",
    ),
    ("isotherms", "values", "[0, .nan]", "finite numbers, not the number nan"),
    ("moist_adiabats", "truncation", ".nan", "a finite number, not the number nan"),
    (
        "isotherms",
        "color",
        "notacolour",
        "a colour matplotlib knows, not the string 'notacolour'",
    ),
    ("isotherms", "alpha", "5.0", "a number between 0 and 1, not the number 5.0"),
    (
        "isotherms",
        "emphasis",
        "{0.0: {color: notacolour}}",
        "member 0 'color' to be a colour matplotlib knows, not the string 'notacolour'",
    ),
    (
        "isotherms",
        "emphasis",
        "{0.0: {linestyle: notaline}}",
        (
            "member 0 'linestyle' to be a linestyle matplotlib knows, "
            "not the string 'notaline'"
        ),
    ),
    (
        "isotherms",
        "labels",
        "[botom]",
        f"true, false, or edge name(s) from {list(EDGES)}, not the string 'botom'",
    ),
    ("isobars", "interval", "0.0", "a positive, finite number, not the number 0.0"),
    (
        "diagram",
        "extent",
        "[[0.0, -80.0], [1050.0, 40.0]]",
        "corner pressures above 0 hPa, not the number 0.0",
    ),
    (
        "diagram",
        "extent",
        "[[1050.0, .nan], [300.0, 40.0]]",
        "finite corner numbers, not the number nan",
    ),
    (
        "isotherms",
        "emphasis",
        "{700.0: {lw: 2.0}}",
        (
            f"member 700 to use style key(s) from {list(EMPHASIS_STYLE_KEYS)}, "
            "not the string 'lw'"
        ),
    ),
    (
        "isotherms",
        "emphasis",
        "{0.0: {linewidth: thick}}",
        "member 0 'linewidth' to be a positive, finite number, not the string 'thick'",
    ),
    (
        "isotherms",
        "emphasis",
        "{0.0: {alpha: 5.0}}",
        "member 0 'alpha' to be a number between 0 and 1, not the number 5.0",
    ),
    ("isotherms", "emphasis", "{.nan: {}}", "finite member values, not the number nan"),
    (
        "cursor",
        "fields",
        "[nonsuch]",
        f"field name(s) from {list(CURSOR_FIELD_NAMES)}, not the string 'nonsuch'",
    ),
    (
        "isotherms",
        "emphasis",
        "{850.0: {linewidth: " + _HUGE_INT + "}}",
        (
            "member 850 'linewidth' to be a positive, finite number, not a "
            "number that large; the largest tephpy can hold is about 1.8e308"
        ),
    ),
    ("isotherms", "linewidth", ".inf", "a positive, finite number, not the number inf"),
    ("isobars", "interval", ".inf", "a positive, finite number, not the number inf"),
    (
        "diagram",
        "extent",
        "[[.inf, -80.0], [300.0, 40.0]]",
        "corner pressures above 0 hPa, not the number inf",
    ),
]


@pytest.mark.parametrize(("section", "option", "yaml", "tail"), REFUSED)
def test_a_bad_value_warns_keeps_the_default_and_spares_the_file(
    tmp_path, section, option, yaml, tail
):
    """The whole of domain spec §2's rule, in one assertion each.

    Every one of these loaded silently before: eight failed at the first
    draw with tephpy's own message, four with matplotlib's, and three drew a
    diagram that was simply not the one the file asked for (domain spec §1).

    The sibling option is what makes "the rest of the file still applies" a
    claim about something. It goes in a second section, so a rule that
    discarded the section rather than the option would fail here too.
    """
    text = f"{section}:\n  {option}: {yaml}\nmixing_ratios:\n  color: purple\n"
    path = _write(tmp_path, text)
    expected = re.escape(f"{section}.{option}, which expects {tail}")
    with pytest.warns(TephpyConfigWarning, match=expected):
        tephpy.config.load(path)
    assert getattr(getattr(tephpy.config, section), option) is None
    assert tephpy.config.mixing_ratios.color == "purple"


def test_the_refused_table_covers_every_rule():
    """The parametrisation above is the gate; an empty table would pass it.

    Pinning the count and the option set is what stops a rule being deleted
    from ``REFUSED`` along with the bug report that motivated it.
    """
    assert len(REFUSED) == 20
    covered = {option for _, option, _, _ in REFUSED}
    assert covered == set(_configfile._DOMAIN_VALIDATORS)


def test_a_hex_colour_missing_its_hash_is_told_so(tmp_path):
    """The mirror image of the trap configfile spec §5 already warns about.

    ``color: #b0b0b0`` parses to null, because YAML eats the unquoted ``#``
    as a comment. ``color: b0b0b0`` is a perfectly good string that is not a
    colour, and lands here. The hint is tested rather than guessed: it is
    offered only because prefixing ``#`` makes ``is_color_like`` true
    (domain spec §4).
    """
    path = _write(tmp_path, "isotherms:\n  color: b0b0b0\n")
    with pytest.warns(TephpyConfigWarning, match=re.escape("did you mean '#b0b0b0'?")):
        tephpy.config.load(path)
    assert tephpy.config.isotherms.color is None


def test_an_ordinary_bad_colour_gets_no_hint(tmp_path):
    """A hint that fires for every bad colour is noise, not a hint."""
    path = _write(tmp_path, "isotherms:\n  color: notacolour\n")
    with pytest.warns(TephpyConfigWarning, match="notacolour") as record:
        tephpy.config.load(path)
    assert "did you mean" not in str(record[0].message)


def test_one_bad_member_skips_the_whole_emphasis_option(tmp_path):
    """Granularity is the option, not the part (domain spec §3.3).

    Not visible from outside, so it is pinned here and documented in the
    configuration how-to. A user told ``emphasis`` was ignored can read
    their own file; one told it was partly applied cannot tell what is in
    force.
    """
    text = "isotherms:\n  emphasis: {850.0: {linewidth: 2.0}, 700.0: {lw: 2.0}}\n"
    path = _write(tmp_path, text)
    with pytest.warns(TephpyConfigWarning, match="isotherms.emphasis"):
        tephpy.config.load(path)
    assert tephpy.config.isotherms.emphasis is None
