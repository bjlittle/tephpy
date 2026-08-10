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


@pytest.fixture
def user_config(monkeypatch, tmp_path):
    """Relocate the user configuration file under ``tmp_path``.

    Every command here enumerates or writes the cascade, whose last entry is
    the real user configuration directory. Relocating it keeps the suite off
    the developer's own file, in either direction.

    Returns
    -------
    pathlib.Path
        The relocated file. Neither it nor its parent directory exists.
    """
    path = tmp_path / "user" / _configfile.CONFIG_FILENAME
    monkeypatch.setattr(_configfile, "user_config_path", lambda: path)
    return path


def test_bare_config_reports_the_path(runner, monkeypatch, tmp_path, user_config):
    """``tephpy config`` defaults to ``path``, which can never write a file."""
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(_cli.main, ["config"])
    assert result.exit_code == 0
    assert "tephpyrc.yaml" in result.output
    assert not user_config.exists()


def test_path_reports_every_cascade_entry(runner, monkeypatch, tmp_path, user_config):
    """A user reaching for this is asking why their file is ignored."""
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 0
    assert result.output.count("tephpyrc.yaml") >= 2
    assert str(user_config) in result.output


def test_path_marks_the_active_file(runner, monkeypatch, tmp_path, user_config):
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tephpyrc.yaml").write_text("isotherms: {}\n", encoding="utf-8")
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 0
    assert "in force" in result.output
    assert not user_config.exists()


def test_path_marks_a_shadowed_file(runner, monkeypatch, tmp_path, user_config):
    """The state the command exists to diagnose: present, but overridden.

    "absent" and "in force" both leave a user none the wiser about the file
    they are actually editing.
    """
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tephpyrc.yaml").write_text("isotherms: {}\n", encoding="utf-8")
    user_config.parent.mkdir(parents=True)
    user_config.write_text("isotherms: {}\n", encoding="utf-8")
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 0
    assert f"{tmp_path / 'tephpyrc.yaml'}  [in force]" in result.output
    assert f"{user_config}  [shadowed]" in result.output


def test_path_marks_a_rejected_file(runner, monkeypatch, tmp_path, user_config):
    """The cascade picking a file is not the same as tephpy using it.

    A malformed file is picked and then rejected, so tephpy runs on its
    defaults. Reporting it "in force" answers "why is my file ignored?"
    with "it isn't" — the one wrong answer this command can give.
    """
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tephpyrc.yaml").write_text(
        "isotherms:\n  color: [unclosed\n", encoding="utf-8"
    )
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 0
    assert f"{tmp_path / 'tephpyrc.yaml'}  [rejected]" in result.output
    assert f"{user_config}  [absent]" in result.output
    assert "in force" not in result.output
    assert "using its defaults" in result.output


def test_path_marks_a_file_with_an_unknown_option_in_force(
    runner, monkeypatch, tmp_path, user_config
):
    """A guard against ``_applies``' warning suppression going away.

    An unknown option warns and is skipped, but the rest of the file still
    applies (configfile spec §2), so it must be reported ``[in force]``, not
    ``[rejected]``. Without the suppression this warning would escape
    ``_applies`` — and under ``filterwarnings = ["error"]`` it would raise,
    turning a working file into a non-zero exit (configfile spec §5.1).
    """
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tephpyrc.yaml").write_text(
        "isotherms:\n  colour: purple\n", encoding="utf-8"
    )
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 0
    assert f"{tmp_path / 'tephpyrc.yaml'}  [in force]" in result.output
    assert not user_config.exists()


def test_path_marks_a_directory_as_not_a_file(
    runner, monkeypatch, tmp_path, user_config
):
    """``discover()`` skips a directory on ``is_file``, so this must agree.

    Calling it "shadowed" contradicts the "no configuration file found"
    line printed directly underneath; calling it "absent" denies something
    the user can see is there.
    """
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tephpyrc.yaml").mkdir()
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 0
    assert f"{tmp_path / 'tephpyrc.yaml'}  [not a file]" in result.output
    assert f"{user_config}  [absent]" in result.output
    assert "shadowed" not in result.output
    assert "No configuration file found" in result.output


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


def test_generate_defaults_to_the_user_config_file(runner, user_config):
    """``tephpy config generate``, bare, is the spec's headline invocation.

    With no ``-o`` the target is the user configuration file, whose parent
    directory need not exist yet; the second run proves the clobber refusal
    resolves the same default.
    """
    assert not user_config.parent.exists()
    result = runner.invoke(_cli.main, ["config", "generate"])
    assert result.exit_code == 0
    assert f"Wrote {user_config}" in result.output
    assert "# color:" in user_config.read_text(encoding="utf-8")
    again = runner.invoke(_cli.main, ["config", "generate"])
    assert again.exit_code == 1
    assert "--force" in again.output


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
