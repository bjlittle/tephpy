# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the logo artist and its bundled brand masters (logo spec §6)."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

REPO = Path(__file__).parents[2]
STATIC = REPO / "src" / "tephpy" / "plotting" / "_static"
BUNDLE = REPO / "docs" / "src" / "_static" / "brand" / "assets" / "logo-bundle.zip"

MASTERS = (
    "icon-512-light.png",
    "icon-512-dark.png",
    "lockup-716-light.png",
    "lockup-716-dark.png",
    "stacked-512-light.png",
    "stacked-512-dark.png",
)


def test_static_holds_exactly_the_masters():
    """No stragglers: the packaged directory is the six masters and nothing else."""
    assert sorted(p.name for p in STATIC.iterdir()) == sorted(MASTERS)


@pytest.mark.parametrize("name", MASTERS)
def test_master_matches_the_bundle(name):
    """The bundle is the source of truth; a copy that drifts is a silent rebrand."""
    with zipfile.ZipFile(BUNDLE) as archive:
        expected = hashlib.sha256(archive.read(f"bundle/png/{name}")).hexdigest()
    assert hashlib.sha256((STATIC / name).read_bytes()).hexdigest() == expected


def test_masters_ship_in_the_wheel(tmp_path):
    """A source-tree copy nobody packaged is the failure tests cannot see."""
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(tmp_path),
            str(REPO),
        ],
        check=True,
        capture_output=True,
    )
    (wheel,) = tmp_path.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        packaged = {
            Path(name).name
            for name in archive.namelist()
            if name.startswith("tephpy/plotting/_static/")
        }
    assert packaged == set(MASTERS)
