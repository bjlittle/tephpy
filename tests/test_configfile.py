# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Discovery, parsing and coercion of the configuration file."""

from __future__ import annotations

import pytest

import tephpy
from tephpy import _configfile
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


def test_an_unknown_option_warns_and_is_skipped(tmp_path):
    path = _write(tmp_path, "isotherms:\n  colour: purple\n  color: purple\n")
    with pytest.warns(TephpyConfigWarning, match="colour"):
        _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    assert tephpy.config.isotherms.color == "purple"


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


def test_a_non_mapping_document_raises(tmp_path):
    path = _write(tmp_path, "- isotherms\n")
    with pytest.raises(TephpyConfigError, match="mapping of sections"):
        _configfile.read_document(path)


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
