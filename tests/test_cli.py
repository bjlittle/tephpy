# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The tephpy console script (configfile spec §4)."""

from __future__ import annotations

from click.testing import CliRunner
import pytest
import yaml

from tephpy import _cli, _configfile


@pytest.fixture
def runner():
    return CliRunner()


def test_bare_config_reports_the_path(runner, monkeypatch, tmp_path):
    """``tephpy config`` defaults to ``path``, which can never write a file."""
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(_cli.main, ["config"])
    assert result.exit_code == 0
    assert "tephpyrc.yaml" in result.output


def test_path_reports_every_cascade_entry(runner, monkeypatch, tmp_path):
    """A user reaching for this is asking why their file is ignored."""
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 0
    assert result.output.count("tephpyrc.yaml") >= 2


def test_path_marks_the_active_file(runner, monkeypatch, tmp_path):
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tephpyrc.yaml").write_text("isotherms: {}\n", encoding="utf-8")
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 0
    assert "in force" in result.output


def test_path_reports_a_broken_environment_variable(runner, monkeypatch, tmp_path):
    monkeypatch.setenv(_configfile.CONFIG_ENV_VAR, str(tmp_path / "absent.yaml"))
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 1
    assert "TEPHPYRC" in result.output


def test_generate_writes_a_template(runner, tmp_path):
    target = tmp_path / "generated.yaml"
    result = runner.invoke(_cli.main, ["config", "generate", "-o", str(target)])
    assert result.exit_code == 0
    assert set(yaml.safe_load(target.read_text(encoding="utf-8"))) == {
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
        "diagram",
        "cursor",
    }


def test_generate_refuses_to_clobber(runner, tmp_path):
    target = tmp_path / "generated.yaml"
    target.write_text("isotherms: {}\n", encoding="utf-8")
    result = runner.invoke(_cli.main, ["config", "generate", "-o", str(target)])
    assert result.exit_code == 1
    assert "--force" in result.output
    assert target.read_text(encoding="utf-8") == "isotherms: {}\n"


def test_generate_force_overwrites(runner, tmp_path):
    target = tmp_path / "generated.yaml"
    target.write_text("isotherms: {}\n", encoding="utf-8")
    result = runner.invoke(
        _cli.main, ["config", "generate", "-o", str(target), "--force"]
    )
    assert result.exit_code == 0
    assert "# color:" in target.read_text(encoding="utf-8")


def test_generate_to_stdout_writes_no_file(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(_cli.main, ["config", "generate", "-o", "-"])
    assert result.exit_code == 0
    assert "# color:" in result.output
    assert list(tmp_path.iterdir()) == []


def test_help_lists_both_subcommands(runner):
    result = runner.invoke(_cli.main, ["config", "--help"])
    assert result.exit_code == 0
    assert "generate" in result.output
    assert "path" in result.output
