# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Discovery, parsing and coercion of the configuration file."""

from __future__ import annotations

import dataclasses
import re
import warnings

import pytest

import tephpy
from tephpy import _configfile
from tephpy._constants import CONFIG_DEFAULTS
from tephpy.exceptions import TephpyConfigError, TephpyConfigWarning


def test_cascade_order_without_the_environment_variable(monkeypatch, tmp_path):
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    paths = _configfile.config_paths()
    assert len(paths) == 2
    assert paths[0] == tmp_path / _configfile.CONFIG_FILENAME
    assert paths[1] == _configfile.user_config_path()


def test_environment_variable_leads_the_cascade(monkeypatch, tmp_path):
    named = tmp_path / "elsewhere.yaml"
    monkeypatch.setenv(_configfile.CONFIG_ENV_VAR, str(named))
    paths = _configfile.config_paths()
    assert len(paths) == 3
    assert paths[0] == named


def test_discover_returns_none_when_nothing_exists(monkeypatch, tmp_path):
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        _configfile, "user_config_path", lambda: tmp_path / "absent" / "tephpyrc.yaml"
    )
    assert _configfile.discover() is None


def test_discover_stops_at_the_first_hit(monkeypatch, tmp_path):
    """First hit wins: a later entry must not override a visible one."""
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    later = tmp_path / "later" / "tephpyrc.yaml"
    later.parent.mkdir()
    later.write_text("isotherms: {}\n", encoding="utf-8")
    monkeypatch.setattr(_configfile, "user_config_path", lambda: later)
    here = tmp_path / _configfile.CONFIG_FILENAME
    here.write_text("isotherms: {}\n", encoding="utf-8")
    assert _configfile.discover() == here


def test_missing_environment_variable_target_is_an_error(monkeypatch, tmp_path):
    """Naming a file explicitly and not having it is a mistake, not a fallthrough."""
    monkeypatch.setenv(_configfile.CONFIG_ENV_VAR, str(tmp_path / "absent.yaml"))
    with pytest.raises(TephpyConfigError, match="TEPHPYRC"):
        _configfile.discover()


def test_a_directory_is_not_a_config_file(monkeypatch, tmp_path):
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / _configfile.CONFIG_FILENAME).mkdir()
    monkeypatch.setattr(
        _configfile, "user_config_path", lambda: tmp_path / "absent" / "tephpyrc.yaml"
    )
    assert _configfile.discover() is None


def _write(tmp_path, text):
    path = tmp_path / "tephpyrc.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_wholly_commented_file_is_an_empty_configuration(tmp_path):
    path = _write(tmp_path, "# isotherms:\n#   color: dimgrey\n")
    assert _configfile.read_document(path) == {}


def test_a_null_section_is_an_empty_section(tmp_path):
    """The expected state of every section the user has not touched."""
    path = _write(tmp_path, "isotherms:\ndiagram:\n")
    assert _configfile.read_document(path) == {"isotherms": None, "diagram": None}
    _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    assert tephpy.config.isotherms.color is None


def test_a_null_option_value_warns_and_names_the_quoting_trap(tmp_path):
    """``color: #b0b0b0`` parses as null — the hex is eaten as a comment."""
    path = _write(tmp_path, "isotherms:\n  color: #b0b0b0\n")
    document = _configfile.read_document(path)
    assert document == {"isotherms": {"color": None}}
    with pytest.warns(TephpyConfigWarning, match="quote"):
        _configfile.apply(tephpy.config, document, source=path)
    assert tephpy.config.isotherms.color is None


def test_a_null_non_colour_option_warns_without_the_colour_hint(tmp_path):
    """The template tells the reader to uncomment ``# emphasis:``.

    Doing exactly that leaves a null value, and a hint about quoting hex
    colours is noise for an option that holds no colour.
    """
    path = _write(tmp_path, "isotherms:\n  emphasis:\n")
    with pytest.warns(TephpyConfigWarning, match="isotherms.emphasis") as record:
        _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    assert "quote" not in str(record[0].message)


def test_an_unknown_option_warns_and_is_skipped(tmp_path):
    path = _write(tmp_path, "isotherms:\n  colour: purple\n  color: purple\n")
    with pytest.warns(TephpyConfigWarning, match="colour"):
        _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    assert tephpy.config.isotherms.color == "purple"


def test_a_warning_blames_the_caller_not_tephpy(tmp_path):
    """The user's file is at fault, so the user's own frame is what is named.

    Reached through ``Config.load`` rather than through ``apply`` on
    purpose. A direct ``apply`` call is already one frame from the caller,
    which is what ``stacklevel=2`` gets right, so a test written that way
    passes whatever the warning does and guards nothing
    (configfile spec §5.1).
    """
    path = _write(tmp_path, "isotherms:\n  colour: purple\n")
    with pytest.warns(TephpyConfigWarning, match="colour") as record:
        tephpy.config.load(path)
    assert record[0].filename == __file__


def test_a_category_filter_silences_an_explicit_load(tmp_path):
    """The axis this change left working, and the one the how-to shows.

    Filtering by module stopped matching once the warning moved to the
    caller's frame; filtering by category never depended on where the
    warning was raised. The second block is the control — without it an
    empty ``record`` would prove nothing, since a load that failed to warn
    for any other reason would satisfy it too (configfile spec §5.1).
    """
    path = _write(tmp_path, "isotherms:\n  colour: purple\n")
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        warnings.filterwarnings("ignore", category=TephpyConfigWarning)
        tephpy.config.load(path)
    assert record == []
    with warnings.catch_warnings(record=True) as control:
        warnings.simplefilter("always")
        tephpy.config.load(path)
    assert len(control) == 1


def test_an_unknown_section_raises(tmp_path):
    path = _write(tmp_path, "isotherm:\n  color: purple\n")
    with pytest.raises(TephpyConfigError, match="isotherm"):
        _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)


def test_a_non_mapping_section_raises(tmp_path):
    path = _write(tmp_path, "isotherms:\n  - purple\n")
    with pytest.raises(TephpyConfigError, match="mapping of options"):
        _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)


def test_malformed_yaml_raises(tmp_path):
    path = _write(tmp_path, "isotherms:\n  color: [unclosed\n")
    with pytest.raises(TephpyConfigError, match="not valid YAML"):
        _configfile.read_document(path)


def test_an_unconstructable_scalar_raises(tmp_path):
    """PyYAML can reject a scalar with a ValueError, not a YAMLError.

    ``2026-13-01`` matches the timestamp resolver and then fails in
    ``datetime.date``. Catching only ``yaml.YAMLError`` lets that escape as
    a bare ``ValueError``, which is the one thing ``read_document`` exists
    to prevent.
    """
    path = _write(tmp_path, "isotherms:\n  color: 2026-13-01\n")
    with pytest.raises(TephpyConfigError, match="cannot make sense of a value"):
        _configfile.read_document(path)


def test_a_non_utf8_file_raises(tmp_path):
    """A cp1252-saved comment must not raise an uncontained UnicodeDecodeError."""
    path = tmp_path / "tephpyrc.yaml"
    path.write_bytes("isotherms:\n  color: purple  # r\xe9sum\xe9\n".encode("cp1252"))
    with pytest.raises(TephpyConfigError, match="cannot read"):
        _configfile.read_document(path)


def test_a_deleted_working_directory_raises(monkeypatch):
    """``Path.cwd()`` raising must not escape as an uncontained FileNotFoundError."""

    def _no_such_directory():
        msg = "no such file or directory"
        raise FileNotFoundError(msg)

    monkeypatch.setattr(_configfile.Path, "cwd", _no_such_directory)
    with pytest.raises(TephpyConfigError, match="working directory"):
        _configfile.config_paths()


def test_a_non_mapping_document_raises(tmp_path):
    path = _write(tmp_path, "- isotherms\n")
    with pytest.raises(TephpyConfigError, match="mapping of sections"):
        _configfile.read_document(path)


def _annotation(section, option):
    """Return the declared type of an option, for a direct ``coerce`` call."""
    return _configfile._option_hints(type(getattr(tephpy.config, section)))[option]


@pytest.mark.parametrize(
    ("section", "option", "value", "expected"),
    [
        ("isotherms", "color", "purple", "purple"),
        ("isotherms", "linewidth", 0.5, 0.5),
        ("isotherms", "linewidth", 1, 1.0),
        ("isotherms", "visible", False, False),
        ("isotherms", "labels", True, True),
        ("isotherms", "labels", "bottom", "bottom"),
        ("isotherms", "labels", ["bottom", "right"], ("bottom", "right")),
        ("isotherms", "values", [0, 10], (0.0, 10.0)),
        ("isotherms", "emphasis", {0: {"color": "red"}}, {0.0: {"color": "red"}}),
        ("cursor", "fields", ["pressure"], ("pressure",)),
        (
            "diagram",
            "extent",
            [[1000, -30], [300, 30]],
            ((1000.0, -30.0), (300.0, 30.0)),
        ),
        ("moist_adiabats", "truncation", -30.0, -30.0),
    ],
)
def test_a_well_typed_value_is_accepted(section, option, value, expected):
    """One accepted case per annotation shape, plus the two YAML forces.

    ``linewidth: 1`` is an ``int`` where a ``float`` is declared and must
    be accepted and converted; ``labels`` covers three of its four arms.
    The type assertion guards the scalar and container-shape rows: ``1 ==
    1.0`` and ``False == 0`` in Python, so an equality-only test would
    pass with no conversion happening at all (configfile spec §5.2). It
    does not guard the inner element coercion for ``values``, ``extent``
    or ``emphasis``, whose outer ``tuple``/``dict`` type is the same
    either way; ``test_values_members_coerce_to_float``,
    ``test_extent_corners_coerce_to_float`` and the pre-existing
    ``test_emphasis_keys_coerce_to_float`` pin those separately.
    """
    coerced = _configfile.coerce(section, option, value, _annotation(section, option))
    assert coerced == expected
    assert type(coerced) is type(expected)


def test_values_members_coerce_to_float():
    """``[0, 10]``'s ``int`` members must not survive as ints inside the tuple."""
    coerced = _configfile.coerce(
        "isotherms", "values", [0, 10], _annotation("isotherms", "values")
    )
    assert coerced == (0.0, 10.0)
    assert all(isinstance(member, float) for member in coerced)


def test_extent_corners_coerce_to_float():
    """Each corner's numbers must not survive as the ints the YAML wrote."""
    coerced = _configfile.coerce(
        "diagram",
        "extent",
        [[1000, -30], [300, 30]],
        _annotation("diagram", "extent"),
    )
    assert coerced == ((1000.0, -30.0), (300.0, 30.0))
    assert all(isinstance(number, float) for corner in coerced for number in corner)


@pytest.mark.parametrize(
    ("section", "option", "value", "match"),
    [
        ("isotherms", "linewidth", "thick", "expects a number, not the string 'thick'"),
        ("isotherms", "linewidth", True, "expects a number, not the boolean true"),
        ("isotherms", "color", 3, "expects a string, not the number 3"),
        ("isotherms", "visible", "maybe", "expects true or false"),
        ("isotherms", "values", "notalist", "expects a list of numbers"),
        ("isotherms", "values", [0, "ten"], "expects a list of numbers"),
        ("isotherms", "labels", 3, "expects true, false, an edge name"),
        ("isotherms", "emphasis", [0], "expects a mapping of member value"),
        ("cursor", "fields", "notalist", "expects a list of strings"),
        ("cursor", "fields", [1], "expects a list of strings"),
        ("diagram", "extent", 5, "expects two [pressure, temperature] corners"),
        ("diagram", "extent", [1, 2], "expects two [pressure, temperature] corners"),
        (
            "diagram",
            "extent",
            [[1000, -30], [300, "warm"]],
            "expects two [pressure, temperature] corners",
        ),
    ],
)
def test_a_wrong_typed_value_is_rejected(section, option, value, match):
    """Every measured case from the configfile spec §5.2 table, and then some.

    ``linewidth: true`` is the one that drove the design: it drew a 1 pt
    line, because ``isinstance(True, int)`` is ``True``. ``values:
    notalist`` and ``fields: notalist`` are the strings that would
    otherwise be iterated one character per member.
    """
    with pytest.raises(TephpyConfigError, match=re.escape(match)):
        _configfile.coerce(section, option, value, _annotation(section, option))


def test_every_option_has_a_validator():
    """An option whose type has no validator must fail here, not in silence.

    ``coerce`` returns an unrecognised annotation's value untouched, so that adding
    an option can never stop an import — which means nothing else in the suite would
    notice the gap. The option would simply go back to being applied unchecked,
    which is the defect configfile spec §5.2 exists to close.

    The first two assertions are what stop this gate passing by checking
    nothing, and the count is taken from ``CONFIG_DEFAULTS`` rather than
    written down, so adding an option updates it.
    """
    annotations = {}
    for field in dataclasses.fields(tephpy.config):
        section = getattr(tephpy.config, field.name)
        hints = _configfile._option_hints(type(section))
        for option in dataclasses.fields(section):
            annotations[field.name, option.name] = hints[option.name]
    assert annotations
    assert len(annotations) == sum(len(options) for options in CONFIG_DEFAULTS.values())
    missing = [
        key
        for key, annotation in sorted(annotations.items())
        if annotation not in _configfile._TYPE_VALIDATORS
    ]
    assert missing == []
    assert set(_configfile._TYPE_VALIDATORS) - set(annotations.values()) == set()


@pytest.mark.parametrize(
    ("text", "section", "option", "expected"),
    [
        (
            "isotherms:\n  labels: [bottom, right]\n",
            "isotherms",
            "labels",
            ("bottom", "right"),
        ),
        ("isotherms:\n  labels: bottom\n", "isotherms", "labels", "bottom"),
        ("isotherms:\n  values: [0, 10]\n", "isotherms", "values", (0.0, 10.0)),
        ("cursor:\n  fields: [pressure]\n", "cursor", "fields", ("pressure",)),
        (
            "diagram:\n  extent: [[1000, -30], [300, 30]]\n",
            "diagram",
            "extent",
            ((1000.0, -30.0), (300.0, 30.0)),
        ),
    ],
)
def test_sequences_coerce_to_tuples(tmp_path, text, section, option, expected):
    path = _write(tmp_path, text)
    _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    assert getattr(getattr(tephpy.config, section), option) == expected


@pytest.mark.parametrize(
    ("text", "section", "option", "match"),
    [
        (
            "diagram:\n  extent: [[1000, -30], [300, warm]]\n",
            "diagram",
            "extent",
            "diagram.extent",
        ),
        (
            "isotherms:\n  emphasis: [0]\n",
            "isotherms",
            "emphasis",
            "isotherms.emphasis",
        ),
        ("isotherms:\n  values: [0, ten]\n", "isotherms", "values", "isotherms.values"),
    ],
    ids=["extent", "emphasis", "values"],
)
def test_a_wrong_typed_value_warns_and_keeps_the_default(
    tmp_path, text, section, option, match
):
    """The three cases that used to cost the reader the whole file.

    Each is an option-level problem, so it warns and is skipped like an
    unknown option and a null value, and the option keeps its default
    (configfile spec §5.2). Before this change all three raised
    ``TephpyConfigError`` out of ``apply``, which under the auto-load left
    every other option in the file unapplied.
    """
    path = _write(tmp_path, text)
    with pytest.warns(TephpyConfigWarning, match=match):
        _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    assert getattr(getattr(tephpy.config, section), option) is None


def test_a_wrong_typed_value_does_not_cost_the_rest_of_the_file(tmp_path):
    """'The rest of the file still applies' is otherwise a claim about nothing.

    One bad option beside a good one, in one file, reached through
    ``Config.load`` so the rollback is in play: the good option must
    survive, and ``source`` must be set — a rejected file leaves it
    ``None`` (configfile spec §5.2).
    """
    path = _write(tmp_path, "isotherms:\n  linewidth: thick\n  color: purple\n")
    with pytest.warns(TephpyConfigWarning, match="expects a number"):
        tephpy.config.load(path)
    assert tephpy.config.isotherms.linewidth is None
    assert tephpy.config.isotherms.color == "purple"
    assert tephpy.config.source == path


def test_every_option_level_warning_names_the_file(tmp_path):
    """With three cascade entries, a warning naming no file is half an answer.

    All three option-level warnings — unknown option, null value,
    wrong-typed value — lead with the path, as the file-level errors
    already do (configfile spec §5.2).
    """
    path = _write(
        tmp_path,
        "isotherms:\n  colour: purple\n  alpha:\n  linewidth: thick\n",
    )
    with pytest.warns(TephpyConfigWarning) as record:
        tephpy.config.load(path)
    assert len(record) == 3
    assert all(str(entry.message).startswith(f"{path}: ") for entry in record)


def test_emphasis_keys_coerce_to_float(tmp_path):
    """``850`` and ``850.0`` must not be two different members."""
    path = _write(tmp_path, "isotherms:\n  emphasis:\n    0: {color: red}\n")
    _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    keys = list(tephpy.config.isotherms.emphasis)
    assert keys == [0.0]
    assert isinstance(keys[0], float)


def test_load_sets_the_source(tmp_path):
    path = _write(tmp_path, "isotherms:\n  color: purple\n")
    tephpy.config.load(path)
    assert tephpy.config.source == path
    assert tephpy.config.isotherms.color == "purple"


def test_a_rejected_file_leaves_the_configuration_as_it_was(tmp_path):
    """``apply`` writes section by section, so a late raise can half-apply.

    ``load`` has to undo whatever the rejected file managed to set, and
    only that: a ``reset()`` here would take ``isobars.linewidth`` — set in
    Python, never mentioned by the file — down with it.
    """
    tephpy.config.isobars.linewidth = 3.0
    path = _write(tmp_path, "isotherms:\n  color: chartreuse\nbogus:\n  color: red\n")
    with pytest.raises(TephpyConfigError, match="bogus"):
        tephpy.config.load(path)
    assert tephpy.config.isotherms.color is None
    assert tephpy.config.isobars.linewidth == 3.0
    assert tephpy.config.source is None


def test_a_rejected_file_rolls_back_under_warnings_as_errors(tmp_path):
    """The raise that undoes a load need not be a ``TephpyConfigError``.

    A caller who filters ``TephpyConfigWarning`` to an error gets that
    class raised from ``apply`` instead, out of the same half-applied
    state. Rolling back only on ``TephpyConfigError`` would let
    ``chartreuse`` survive a file the caller saw rejected.
    """
    path = _write(tmp_path, "isotherms:\n  color: chartreuse\n  colour: purple\n")
    with warnings.catch_warnings():
        warnings.simplefilter("error", TephpyConfigWarning)
        with pytest.raises(TephpyConfigWarning, match="colour"):
            tephpy.config.load(path)
    assert tephpy.config.isotherms.color is None
    assert tephpy.config.source is None
