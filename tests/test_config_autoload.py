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

    ``HOME`` and ``XDG_CONFIG_HOME`` both move, so the user configuration
    directory is empty on every platform, not just the linux-64 CI runs.
    ``MPLCONFIGDIR`` keeps pointing at this process's matplotlib cache, so
    the relocated ``HOME`` does not trigger a font-cache rebuild.
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
    colour, source = result.stdout.split()
    assert colour == "purple"
    assert source == str(named)


def test_autoload_finds_the_working_directory_file(tmp_path):
    (tmp_path / "tephpyrc.yaml").write_text(
        "isotherms:\n  color: purple\n", encoding="utf-8"
    )
    result = _run(tmp_path)
    colour, _ = result.stdout.split()
    assert colour == "purple"


def test_autoload_finds_nothing_without_a_file(tmp_path):
    result = _run(tmp_path)
    colour, source = result.stdout.split()
    assert colour == "None"
    assert source == "None"


def test_a_broken_file_warns_and_does_not_stop_the_import(tmp_path):
    """``check=True`` is the assertion: a raising import would exit non-zero."""
    broken = tmp_path / "broken.yaml"
    broken.write_text("isotherms:\n  color: [unclosed\n", encoding="utf-8")
    result = _run(tmp_path, TEPHPYRC=str(broken))
    assert "TephpyConfigWarning" in result.stderr
    colour, source = result.stdout.split()
    assert colour == "None"
    assert source == "None"
