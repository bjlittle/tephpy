# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Discovery, parsing and coercion of the configuration file."""

from __future__ import annotations

import pytest

from tephpy import _configfile
from tephpy.exceptions import TephpyConfigError


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
