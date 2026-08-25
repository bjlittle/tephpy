# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Domain validation of a configuration value that has the right type.

The second stage of ``coerce`` (domain spec §3.1): every case here has already
passed the type check that ``tests/test_configfile.py`` covers.
"""

from __future__ import annotations

import dataclasses
import re
import warnings

import matplotlib.pyplot as plt
from metpy.units import units
import numpy as np
import pytest

import tephpy
from tephpy import Sounding, _configfile
from tephpy._constants import (
    CONFIG_DEFAULTS,
    CURSOR_FIELD_NAMES,
    EDGES,
    EMPHASIS_STYLE_KEYS,
)
from tephpy.exceptions import TephpyConfigWarning

#: A minimal sounding, just to give ``fit`` something to frame: ``margin`` is
#: consumed only there, never at axes creation, so ``_draw_with`` cannot reach
#: it through ``fig.add_subplot`` and ``canvas.draw`` the way ``diagram.extent``
#: and the isopleth options are (framing spec §3.2/§3.3).
_PROBE_SOUNDING = Sounding(
    units.Quantity(np.array([1000.0, 900.0, 800.0]), "hPa"),
    units.Quantity(np.array([20.0, 10.0, 0.0]), "degC"),
)


def _write(tmp_path, text):
    path = tmp_path / "tephpyrc.yaml"
    path.write_text(text, encoding="utf-8")
    return path


#: A 320-digit plain integer: valid YAML, valid Python, and rejected only by
#: ``float()``'s own ``OverflowError`` -- the failure mode ``_as_float`` must
#: catch alongside ``_as_number``'s existing guard, or the emphasis-style
#: numeric path stops ``import tephpy`` outright (configfile spec §5.2).
_HUGE_INT = "9" * 320

#: Eighteen of the domain spec §1 table's nineteen rows -- the gate drops
#: ``color: 'b0b0b0'``, which has its own named test for the ``#`` hint --
#: plus five cases that table does not tabulate: a ``diagram.extent``
#: range with a non-finite temperature rather than a non-finite pressure,
#: an ``emphasis`` member key that is itself non-finite (a member key, not
#: a style key), an ``emphasis`` ``linewidth`` override carrying the huge
#: integer above rather than an ordinary bad number, ``linewidth: 0``,
#: which that table cannot hold because it drew the diagram it was asked
#: for, and a negative ``diagram.margin`` (framing spec §3.3, added after
#: the table). Each is
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
    (
        "isotherms",
        "linewidth",
        "0.0",
        "a positive, finite number, not the number 0.0",
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
        "emphasis",
        '{0.0: {linestyle: ["--"]}}',
        "member 0 'linestyle' to be a linestyle matplotlib knows, not ['--']",
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
        "{pressure: [0.0, 1050.0], temperature: [-80.0, 40.0]}",
        "extent pressures above 0 hPa, not the number 0.0",
    ),
    (
        "diagram",
        "extent",
        "{pressure: [1050.0, 300.0], temperature: [.nan, 40.0]}",
        "finite extent bounds, not the number nan",
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
        "{pressure: [.inf, 300.0], temperature: [-80.0, 40.0]}",
        "extent pressures above 0 hPa, not the number inf",
    ),
    (
        "diagram",
        "margin",
        "-1.0",
        "a finite margin of 0 or more, not the number -1.0",
    ),
]


@pytest.mark.parametrize(("section", "option", "yaml", "tail"), REFUSED)
def test_a_bad_value_warns_keeps_the_default_and_spares_the_file(
    tmp_path, section, option, yaml, tail
):
    """The whole of domain spec §2's rule, in one assertion each.

    Every one of these loaded silently before: most failed at the first draw,
    with tephpy's message or matplotlib's, and the rest drew a diagram that
    was simply not the one the file asked for (domain spec §1). Which case
    falls where is not counted here — ``DRAWS_IN_SILENCE`` below is where
    that split is recorded, and it is checked rather than asserted in prose.

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
    assert len(REFUSED) == 23
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


#: The five options that have no domain rule, and why. A bool is the whole of
#: its own domain, so ``visible`` needs none (domain spec §3.3).
UNDOMAINED = {
    (section, "visible")
    for section, defaults in CONFIG_DEFAULTS.items()
    if "visible" in defaults
}


def test_every_option_bar_the_flags_has_a_domain_rule():
    """An option with no rule must fail here, not go quietly unchecked.

    ``coerce`` returns an option with no entry in ``_DOMAIN_VALIDATORS``
    untouched, exactly as it does for an unrecognised annotation and for the
    same reason: adding an option must not be able to stop an import. So
    nothing else in the suite would notice the gap — the option would simply
    go back to being applied unchecked, which is the defect this work exists
    to close.

    The first two assertions are what stop this gate passing by checking
    nothing, and the count comes from ``CONFIG_DEFAULTS`` rather than being
    written down, so adding an option updates it.
    """
    options = {
        (section, option)
        for section, defaults in CONFIG_DEFAULTS.items()
        for option in defaults
    }
    assert options
    assert len(options) == 43
    assert len(UNDOMAINED) == 5
    missing = sorted(
        key
        for key in options - UNDOMAINED
        if key[1] not in _configfile._DOMAIN_VALIDATORS
    )
    assert missing == []
    assert {option for _, option in options} - set(_configfile._DOMAIN_VALIDATORS) == {
        "visible"
    }


def test_every_emphasis_style_key_has_a_domain_rule():
    """A style key with no rule reaches the draw with no domain check at all.

    ``_domain_emphasis`` accepts any key ``EMPHASIS_STYLE_KEYS`` lists, then hands the
    value to ``_EMPHASIS_STYLE_RULES``. A key present in the first table and absent
    from the second is legal at load time and undomained at the draw -- the same gap
    the top-level completeness gate above closes, one option's rules deep rather than
    across all of them (domain spec §3.3).

    The first assertion is what stops this gate passing by checking nothing.
    """
    assert EMPHASIS_STYLE_KEYS
    assert set(_configfile._EMPHASIS_STYLE_RULES) == set(EMPHASIS_STYLE_KEYS)


def test_no_option_name_carries_two_domains():
    """The assumption behind keying by name rather than by annotation.

    ``_DOMAIN_VALIDATORS`` is keyed by option name, so ``values`` in
    ``isotherms`` and ``values`` in ``mixing_ratios`` get the same rule.
    That is sound today because the two mean the same kind of thing — finite
    numbers, whether the family measures degrees Celsius or g/kg — and it is
    a property of the current ``Config``, not a law (domain spec §3.1).

    An option that ever needs a per-section domain has to be keyed by
    ``(section, option)``, and this is where that shows up. The proxy for
    "same domain" is the declared type: two sections that give one option
    name different types cannot share a rule that runs on the converted
    value.
    """
    annotations: dict[str, set[object]] = {}
    for field in dataclasses.fields(tephpy.config):
        section = getattr(tephpy.config, field.name)
        hints = _configfile._option_hints(type(section))
        for option in dataclasses.fields(section):
            annotations.setdefault(option.name, set()).add(hints[option.name])
    assert annotations
    ambiguous = sorted(name for name, types in annotations.items() if len(types) > 1)
    assert ambiguous == []


#: Values every rule must accept: the legitimate lookalikes. A validator that
#: refuses a value the draw would have accepted is worse than no validator,
#: and no other gate here can see it -- every refusal test passes just as
#: well against a rule that is too strict (domain spec §5).
ACCEPTED = [
    ("isotherms", "color", "C0"),
    ("isotherms", "color", "'xkcd:sky blue'"),
    ("isotherms", "color", "'0.5'"),
    ("isotherms", "color", "'#b0b0b0'"),
    ("isotherms", "linewidth", "0.5"),
    ("isotherms", "alpha", "0"),
    ("isotherms", "alpha", "1"),
    ("isotherms", "labels", "true"),
    ("isotherms", "labels", "false"),
    ("isotherms", "labels", "bottom"),
    ("isotherms", "labels", "[bottom, left]"),
    ("isotherms", "values", "[]"),
    ("isotherms", "values", "[0, 10]"),
    ("isotherms", "visible", "false"),
    ("isotherms", "emphasis", "{}"),
    ("isotherms", "emphasis", "{850.0: {}}"),
    ("isotherms", "emphasis", "{850.0: {linestyle: '--'}}"),
    ("isotherms", "emphasis", "{850.0: {linestyle: dashed}}"),
    ("isotherms", "emphasis", "{850.0: {linestyle: none}}"),
    ("isotherms", "emphasis", "{850.0: {linewidth: 2}}"),
    ("isotherms", "emphasis", "{850.0: {alpha: 1}}"),
    ("isotherms", "emphasis", "{850.0: {color: red, linewidth: 2.0, alpha: 1.0}}"),
    ("isobars", "interval", "10.0"),
    ("moist_adiabats", "truncation", "-40"),
    ("diagram", "extent", "{pressure: [1050.0, 300.0], temperature: [-80.0, 40.0]}"),
    ("diagram", "margin", "0"),
    ("cursor", "fields", "[pressure, theta_w]"),
]


@pytest.mark.parametrize(("section", "option", "yaml"), ACCEPTED)
def test_a_legitimate_value_is_not_refused(tmp_path, section, option, yaml):
    """Each rule's lookalikes, loaded through the file (domain spec §5).

    ``C0``, ``xkcd:sky blue`` and ``0.5`` are all colours and none of them
    looks like one. ``alpha: 0`` and ``alpha: 1`` are the inclusive bounds.
    ``labels: bottom`` is the bare-string arm and ``[bottom, left]`` the list
    arm. ``truncation: -40`` is the negative number the one invented rule
    must not read as out of range. The three ``emphasis`` overrides written
    as integers are the case that drove ``_as_float``: a style value is
    annotated ``object`` and so arrives unconverted, so a rule testing for
    ``float`` would refuse ``linewidth: 2`` where ``linewidth: 2.0`` passes
    (domain spec §3.3).
    """
    path = _write(tmp_path, f"{section}:\n  {option}: {yaml}\n")
    with warnings.catch_warnings():
        warnings.simplefilter("error", TephpyConfigWarning)
        tephpy.config.load(path)
    assert getattr(getattr(tephpy.config, section), option) is not None


def test_the_accepted_table_reaches_every_rule():
    """An emptied table would pass the gate above having checked nothing."""
    assert len(ACCEPTED) == 27
    assert {option for _, option, _ in ACCEPTED} == set(
        _configfile._DOMAIN_VALIDATORS
    ) | {"visible"}


#: The six values the draw accepts in silence. Four are domain spec §1
#: rows, and each draws a diagram that is simply not the one the file
#: asked for, which is the worst outcome available and the reason this work
#: exists. Their rules are lifted from the *emphasis* checks on the same
#: quantities, not from a check the family-level option reaches, so the load
#: refuses what the draw does not -- and this set is where that asymmetry is
#: written down rather than assumed.
#:
#: All three ``linewidth`` values are here for one reason: the family-level
#: option is not range-checked anywhere in the draw, so each reaches
#: matplotlib. -1.0 and .inf produce a line width that is not the one asked
#: for; the infinity was measured, not assumed -- it emits two numpy
#: RuntimeWarnings from a scalar multiply and draws. 0.0 is the fifth value
#: and the odd one out: matplotlib reads it as *draw no line*, so it is a
#: working configuration the load stage refuses anyway (domain spec §3.3),
#: which is why domain spec §1 has no row for it. ``visible: false`` is the
#: supported spelling, and the warning names the option rather than
#: dropping it in silence. The sixth, a negative ``diagram.margin``, is
#: outside domain spec §1 entirely -- ``margin`` postdates that table
#: (framing spec §3.3) -- and it draws because ``fit`` applies the padding
#: with no range check of its own, halving or inverting the fitted span
#: instead of refusing it.
#:
#: A list, and a separate one, rather than an exemption set consulted by
#: membership: seven of the refused values below are dicts, which are
#: unhashable, and two are NaN, which is not equal to itself -- so
#: ``(section, option, value) in a_set`` neither runs nor means anything
#: here. Which list a row is written in carries the split, and no value is
#: ever compared.
DRAWS_IN_SILENCE = [
    ("isotherms", "linewidth", -1.0),
    ("isotherms", "linewidth", 0.0),
    ("isotherms", "linewidth", float("inf")),
    ("isotherms", "values", (0.0, float("nan"))),
    ("moist_adiabats", "truncation", float("nan")),
    ("diagram", "margin", -1.0),
]

#: The seventeen the draw refuses loudly, in one of the three exception types
#: the gate below accepts.
RAISES_AT_THE_DRAW = [
    ("isotherms", "color", "notacolour"),
    ("isotherms", "alpha", 5.0),
    ("isotherms", "emphasis", {0.0: {"color": "notacolour"}}),
    ("isotherms", "emphasis", {0.0: {"linestyle": "notaline"}}),
    ("isotherms", "emphasis", {0.0: {"linestyle": ["--"]}}),
    ("isotherms", "labels", ("botom",)),
    ("isobars", "interval", 0.0),
    ("isobars", "interval", float("inf")),
    ("diagram", "extent", {"pressure": (0.0, 1050.0), "temperature": (-80.0, 40.0)}),
    (
        "diagram",
        "extent",
        {"pressure": (1050.0, 300.0), "temperature": (float("nan"), 40.0)},
    ),
    (
        "diagram",
        "extent",
        {"pressure": (float("inf"), 300.0), "temperature": (-80.0, 40.0)},
    ),
    ("isotherms", "emphasis", {700.0: {"lw": 2.0}}),
    ("isotherms", "emphasis", {0.0: {"linewidth": "thick"}}),
    ("isotherms", "emphasis", {0.0: {"alpha": 5.0}}),
    ("isotherms", "emphasis", {float("nan"): {}}),
    ("isotherms", "emphasis", {850.0: {"linewidth": int("9" * 400)}}),
    ("cursor", "fields", ("nonsuch",)),
]

#: What the draw does with a refused value, as a parametrisation label:
#: strings rather than booleans so a failing case names its own expectation.
DRAWS, RAISES = "draws", "raises"

#: Every refused value again, as the Python objects ``coerce`` would have
#: produced, for the draw to be asked about directly. Written out rather than
#: derived from ``REFUSED`` because ``coerce`` refuses these -- deriving them
#: would mean running the stage under test to build the input to its own gate.
REFUSED_AT_THE_DRAW = [
    (section, option, value, DRAWS) for section, option, value in DRAWS_IN_SILENCE
] + [(section, option, value, RAISES) for section, option, value in RAISES_AT_THE_DRAW]


def _draw_with(section, option, value):
    """Set an option through the Python API and exercise everything that reads it.

    Three actions, because "the draw" is not one thing: ``diagram.extent``
    is consumed when the axes are built, the isopleth options when the
    canvas is drawn, and ``cursor.fields`` only on mouse motion — which is
    why its mistake reaches an interactive user and nobody else
    (domain spec §1).

    A fourth action just for ``diagram.margin``: it is read only by ``fit``,
    never by axes creation or the canvas draw, so nothing above would ever
    consume it (framing spec §3.3) -- the call is added here rather than
    given its own helper so this one function stays the single place "the
    draw" is defined.

    The draw itself runs with ``RuntimeWarning`` suppressed: the
    ``isotherms.linewidth: .inf`` row in ``DRAWS_IN_SILENCE`` emits two from
    a numpy scalar multiply during the render, and the suite's
    ``filterwarnings = ["error"]`` would otherwise turn the one row whose
    whole point is that the draw *succeeds* into a failure. Nothing else is
    suppressed.
    """
    with tephpy.config.context(**{section: {option: value}}):
        fig = plt.figure()
        try:
            ax = fig.add_subplot(projection="tephigram")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                fig.canvas.draw()
                ax.format_coord(0.0, 0.0)
                if (section, option) == ("diagram", "margin"):
                    ax.fit(_PROBE_SOUNDING)
        finally:
            plt.close(fig)


@pytest.mark.parametrize(("section", "option", "value", "outcome"), REFUSED_AT_THE_DRAW)
def test_what_the_load_refuses_the_draw_refuses_too(section, option, value, outcome):
    """Makes "lifted, not invented" a checked property (domain spec §5).

    The Python API is unguarded by design (domain spec §2), so setting the
    value there and drawing asks the draw-time rule directly. Seventeen of these
    raise; the five in ``DRAWS_IN_SILENCE`` do not, and pinning that silence
    is the point — a later change that makes one of them raise is a change to
    a diagram a user already has, and this is where it surfaces.

    ``OverflowError`` is in the tuple for the huge-integer row alone. It is
    not a ``ValueError`` — it descends from ``ArithmeticError`` — so leaving
    it out would let that row pass this gate by raising something the gate
    never asked about. It is the draw-time counterpart of the rule that keeps
    such a value from stopping an import (configfile spec §5.2).
    """
    if outcome == DRAWS:
        _draw_with(section, option, value)
        return
    with pytest.raises((TypeError, ValueError, OverflowError)):
        _draw_with(section, option, value)


@pytest.mark.parametrize(("section", "option", "yaml"), ACCEPTED)
def test_what_the_load_accepts_the_draw_accepts_too(tmp_path, section, option, yaml):
    """The half that has no exceptions, and the false-positive gate's teeth.

    A rule that is too strict refuses a diagram that would have drawn. Here
    the value goes in through the file — so the whole pipeline runs — and
    then the diagram is drawn from the configuration it produced.
    """
    path = _write(tmp_path, f"{section}:\n  {option}: {yaml}\n")
    with warnings.catch_warnings():
        warnings.simplefilter("error", TephpyConfigWarning)
        tephpy.config.load(path)
    _draw_with(section, option, getattr(getattr(tephpy.config, section), option))


def test_the_draw_table_covers_every_refusal():
    """``REFUSED_AT_THE_DRAW`` is hand-written, so nothing else keeps it in step.

    It is deliberately not derived from ``REFUSED`` — deriving it would mean
    running the stage under test to build the input to its own gate — and the
    price of writing it out is that a row added to one table and forgotten in
    the other goes unnoticed. The refusal would keep its own test and quietly
    stop being asked whether the draw agrees, which is the property this
    module exists to check.

    Compared by ``(section, option)`` rather than by value: the two tables
    hold the same cases in different forms, YAML text on one side and the
    Python objects ``coerce`` would have produced on the other.
    """
    assert len(REFUSED_AT_THE_DRAW) == len(REFUSED)
    refused = sorted((section, option) for section, option, _, _ in REFUSED)
    drawn = sorted((section, option) for section, option, _, _ in REFUSED_AT_THE_DRAW)
    assert drawn == refused
    # The split, not just the total. Both halves are quoted as words — in the
    # docstring above and in domain spec §5 — and a row moved from one table to
    # the other keeps the total that the assertion above checks. That is how the
    # docstring came to say sixteen and four of a table that had held seventeen
    # and five since the pull request introducing both (:pull:`126`).
    assert len(RAISES_AT_THE_DRAW) == 17
    assert len(DRAWS_IN_SILENCE) == 6
