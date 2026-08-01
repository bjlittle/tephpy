# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the logo artist and its bundled brand masters (logo spec §6)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

import pytest

from tephpy.plotting import logo

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
    # Export the committed tree; untracked files are invisible to git-archive,
    # so the test genuinely fails if a master was never committed (logo spec §2).
    src_tar = tmp_path / "src.tar"
    subprocess.run(  # noqa: S603
        ["git", "archive", "--format=tar", f"--output={src_tar}", "HEAD"],  # noqa: S607
        check=True,
        capture_output=True,
        cwd=REPO,
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    with tarfile.open(src_tar) as tar:
        tar.extractall(src_dir, filter="data")
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(tmp_path),
            str(src_dir),
        ],
        check=True,
        capture_output=True,
        env={**os.environ, "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TEPHPY": "0.0.0"},
    )
    (wheel,) = tmp_path.glob("*.whl")
    with zipfile.ZipFile(wheel) as whl:
        packaged = {
            Path(name).name
            for name in whl.namelist()
            if name.startswith("tephpy/plotting/_static/")
        }
    assert packaged == set(MASTERS)


@pytest.mark.parametrize(
    ("form", "variant", "shape"),
    [
        ("icon", "light", (512, 512)),
        ("icon", "dark", (512, 512)),
        ("lockup", "light", (256, 716)),
        ("lockup", "dark", (256, 716)),
        ("stacked", "light", (720, 512)),
        ("stacked", "dark", (720, 512)),
    ],
)
def test_load_master_shape(form, variant, shape):
    """Height first: the zoom calculation divides by ``shape[0]`` (logo spec §3.3)."""
    image = logo._load_master(form, variant)
    assert image.shape == (*shape, 4)


def test_load_master_is_read_only():
    """One shared array per variant; a caller mutating it would poison every figure."""
    with pytest.raises(ValueError, match="read-only"):
        logo._load_master("icon", "light")[0, 0, 0] = 1.0


def test_load_master_caches():
    """Decoding a 512x720 PNG per call would cost more than drawing the figure."""
    assert logo._load_master("stacked", "dark") is logo._load_master("stacked", "dark")


def test_masters_table_covers_every_shipped_file():
    """The table and the packaged directory must not drift apart."""
    assert sorted(logo._MASTERS.values()) == sorted(MASTERS)


def test_importing_reads_no_asset():
    """A logo nobody asked for costs nothing (logo spec §3.6)."""
    code = (
        "from tephpy.plotting import logo;"
        " info = logo._load_master.cache_info();"
        " raise SystemExit(0 if info.hits == 0 and info.currsize == 0 else 1)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603


def test_import_tephpy_does_not_import_pyplot():
    """``pyplot`` is an interactive-session import, not a library one.

    See logo spec §3.2.
    """
    code = (
        "import sys, tephpy;"
        " raise SystemExit(1 if 'matplotlib.pyplot' in sys.modules else 0)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603
