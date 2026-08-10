# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Prove the import-time auto-load actually runs.

``tephpy`` is already imported by the time any in-process test runs, so this
seam is invisible from inside the suite and has to be exercised in a fresh
interpreter (configfile spec §6).
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import matplotlib as mpl

PROBE = textwrap.dedent(
    """
    import tephpy

    print(tephpy.config.isotherms.color)
    print(tephpy.config.source)
    """
)


def _run(tmp_path, **env_extra):
    """Import tephpy in a fresh interpreter under a controlled environment.

    ``HOME`` and ``XDG_CONFIG_HOME`` both move, which empties the user
    configuration directory on linux — where CI runs — and on macOS.
    Windows resolves it from ``%LOCALAPPDATA%``, which neither variable
    touches, so a developer running these there with a user configuration
    file of their own would still see it. ``MPLCONFIGDIR`` keeps pointing
    at this process's matplotlib cache, so the relocated ``HOME`` does not
    trigger a font-cache rebuild.
    """
    env = dict(os.environ)
    env.pop("TEPHPYRC", None)
    env["HOME"] = str(tmp_path)
    env["XDG_CONFIG_HOME"] = str(tmp_path / "config")
    env["MPLCONFIGDIR"] = mpl.get_configdir()
    env.update(env_extra)
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", PROBE],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
        env=env,
    )


def test_autoload_applies_the_named_file(tmp_path):
    named = tmp_path / "named.yaml"
    named.write_text("isotherms:\n  color: purple\n", encoding="utf-8")
    result = _run(tmp_path, TEPHPYRC=str(named))
    colour, source = result.stdout.splitlines()
    assert colour == "purple"
    assert source == str(named)


def test_autoload_finds_the_working_directory_file(tmp_path):
    (tmp_path / "tephpyrc.yaml").write_text(
        "isotherms:\n  color: purple\n", encoding="utf-8"
    )
    result = _run(tmp_path)
    colour, _ = result.stdout.splitlines()
    assert colour == "purple"


def test_autoload_finds_nothing_without_a_file(tmp_path):
    result = _run(tmp_path)
    colour, source = result.stdout.splitlines()
    assert colour == "None"
    assert source == "None"


def test_a_broken_file_warns_and_does_not_stop_the_import(tmp_path):
    """``check=True`` is the assertion: a raising import would exit non-zero."""
    broken = tmp_path / "broken.yaml"
    broken.write_text("isotherms:\n  color: [unclosed\n", encoding="utf-8")
    result = _run(tmp_path, TEPHPYRC=str(broken))
    assert "TephpyConfigWarning" in result.stderr
    colour, source = result.stdout.splitlines()
    assert colour == "None"
    assert source == "None"


def test_a_non_utf8_file_warns_and_does_not_stop_the_import(tmp_path):
    """A cp1252-saved comment must not make ``tephpy`` unimportable."""
    broken = tmp_path / "broken.yaml"
    broken.write_bytes("isotherms:\n  color: purple  # r\xe9sum\xe9\n".encode("cp1252"))
    result = _run(tmp_path, TEPHPYRC=str(broken))
    assert "TephpyConfigWarning" in result.stderr
    colour, source = result.stdout.splitlines()
    assert colour == "None"
    assert source == "None"


def test_an_unconstructable_scalar_does_not_stop_the_import(tmp_path):
    """A YAML scalar can fail to build without ever being a YAMLError.

    ``2026-13-01`` parses as a timestamp and then raises ``ValueError`` in
    ``datetime.date``. Uncontained, it takes out the import and
    ``tephpy config path`` with it — the failure mode the whole warn-and-
    continue guarantee exists to prevent.
    """
    month = tmp_path / "month.yaml"
    month.write_text("isotherms:\n  color: 2026-13-01\n", encoding="utf-8")
    result = _run(tmp_path, TEPHPYRC=str(month))
    assert "TephpyConfigWarning" in result.stderr
    colour, source = result.stdout.splitlines()
    assert colour == "None"
    assert source == "None"


def test_warnings_as_errors_does_not_stop_the_import(tmp_path):
    """``-W error`` turns a warning into an exception, including ours.

    A typo'd option key is the likeliest configuration mistake there is,
    and under ``PYTHONWARNINGS=error`` the warning about it would kill the
    import — and with it ``tephpy config path``, the tool for finding out
    which file is at fault. ``check=True`` is half the assertion.
    """
    typo = tmp_path / "typo.yaml"
    typo.write_text("isotherms:\n  colour: purple\n", encoding="utf-8")
    result = _run(tmp_path, TEPHPYRC=str(typo), PYTHONWARNINGS="error")
    assert "TephpyConfigWarning" in result.stderr
    assert "colour" in result.stderr
    colour, source = result.stdout.splitlines()
    assert colour == "None"
    assert source == str(typo)


def test_warnings_as_errors_survives_an_unreadable_file(tmp_path):
    """The failure path warns from ``_autoload_config``, not from ``apply``.

    A typo'd key warns from inside ``apply``, which ``config.load`` is
    already wrapped for; a file that cannot be parsed at all warns from the
    ``except`` clause afterwards. Only that second warning is pinned by
    this test, so narrowing ``catch_warnings`` to ``config.load`` alone
    would fail here and nowhere else.
    """
    broken = tmp_path / "broken.yaml"
    broken.write_text("isotherms:\n  color: [unclosed\n", encoding="utf-8")
    result = _run(tmp_path, TEPHPYRC=str(broken), PYTHONWARNINGS="error")
    assert "TephpyConfigWarning" in result.stderr
    colour, source = result.stdout.splitlines()
    assert colour == "None"
    assert source == "None"


def test_a_partially_applied_file_still_resets(tmp_path):
    """``apply`` can set an earlier section before raising on a later one.

    Without ``config.reset()`` on the failure path, ``isotherms.color``
    would still read ``chartreuse`` here, even though the file as a whole
    was rejected.
    """
    partial = tmp_path / "partial.yaml"
    partial.write_text(
        "isotherms:\n  color: chartreuse\nbogus:\n  color: red\n", encoding="utf-8"
    )
    result = _run(tmp_path, TEPHPYRC=str(partial))
    assert "TephpyConfigWarning" in result.stderr
    colour, source = result.stdout.splitlines()
    assert colour == "None"
    assert source == "None"
