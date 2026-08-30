# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the reading-time directive and its coverage gate (reading spec §6)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
DOCS = REPO / "docs" / "src"
EXT = DOCS / "_ext"


def _load(name: str):
    """Import an extension module by path; ``_ext`` is not an importable package."""
    path = EXT / f"{name}.py"
    assert path.is_file(), f"the module is missing from {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# `_ext` is a `sys.path` entry at build time rather than a package, so a module
# there resolves its siblings by top-level name and cannot be imported until that
# entry exists (:issue:`92`).
if str(EXT) not in sys.path:
    sys.path.insert(0, str(EXT))

reading = _load("tephpy_reading")


def test_the_default_rate_is_the_one_the_specification_cites():
    """Reading spec §3.4 fixes 150, below Brysbaert's 175 non-fiction floor."""
    assert reading.WPM == 150


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),
        ("one", 1),
        ("one two three", 3),
        # `\w+` splits on punctuation, so a dotted name counts as its parts. The
        # banner and the gate must agree on that, which is why it is pinned.
        ("tephpy.plotting.axes", 3),
        ("hyphen-ated", 2),
        ("   spaced   out   ", 2),
        ("newlines\nare\nwhitespace", 3),
    ],
)
def test_count_words_counts_word_character_runs(text, expected):
    assert reading.count_words(text) == expected


@pytest.mark.parametrize(
    ("words", "wpm", "expected"),
    [
        (0, 150, 1),  # the floor: no page reads in zero minutes
        (1, 150, 1),
        (150, 150, 1),
        (151, 150, 2),  # rounds up, never down
        (300, 150, 2),
        (1500, 150, 10),
        (300, 100, 3),  # the rate is honoured
    ],
)
def test_estimate_minutes_rounds_up_with_a_floor_of_one(words, wpm, expected):
    assert reading.estimate_minutes(words, wpm) == expected


def test_estimate_minutes_defaults_to_the_house_rate():
    assert reading.estimate_minutes(300) == reading.estimate_minutes(300, reading.WPM)


@pytest.mark.parametrize(
    ("argument", "minutes", "wpm"),
    [
        (None, None, 150),  # no argument: count at the house rate
        ("30", 30, 150),  # a literal duration, quoted not counted
        ("1", 1, 150),
        ("200wpm", None, 200),  # a rate override; the count still happens
        ("200WPM", None, 200),  # case-insensitive
        ("90wpm", None, 90),
    ],
)
def test_parse_argument_reads_the_two_documented_shapes(argument, minutes, wpm):
    parsed = reading.parse_argument(argument)
    assert parsed.minutes == minutes
    assert parsed.wpm == wpm


@pytest.mark.parametrize(
    "argument",
    [
        "thirty",  # the prior art computes an estimate here and warns nobody
        "",
        "10 minutes",
        "wpm",
        "0wpm",  # a zero rate would divide by zero
        "0",  # a zero-minute page is not a duration
        "-5",
        "12wpmx",  # anchored at both ends
        "x200wpm",
    ],
)
def test_parse_argument_rejects_anything_else(argument):
    """Reading spec §3.2: an argument the directive cannot read stops the build."""
    with pytest.raises(ValueError, match="readingtime"):
        reading.parse_argument(argument)
