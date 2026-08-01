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

import matplotlib.pyplot as plt
import pytest

from tephpy._constants import LOGO_SIZES
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


def test_resolve_target_axes_returns_its_figure():
    figure, axes = plt.subplots()
    assert logo._resolve_target(axes) == (figure, axes)
    plt.close(figure)


def test_resolve_target_figure_has_no_axes():
    figure = plt.figure()
    assert logo._resolve_target(figure) == (figure, None)
    plt.close(figure)


def test_resolve_target_none_takes_the_current_figure():
    figure = plt.figure()
    assert logo._resolve_target(None) == (figure, None)
    plt.close(figure)


def test_resolve_target_rejects_anything_else():
    with pytest.raises(TypeError, match="Figure or an Axes"):
        logo._resolve_target("figure")


def test_resolve_target_rejects_a_subfigure_axes():
    """``SubFigure`` is out of scope (logo spec §8); say so rather than lie about it."""
    figure = plt.figure()
    axes = figure.subfigures(1, 1).subplots()
    with pytest.raises(TypeError, match="not a SubFigure"):
        logo._resolve_target(axes)
    plt.close(figure)


@pytest.mark.parametrize("form", ["icon", "lockup", "stacked"])
@pytest.mark.parametrize("size", ["small", "large"])
def test_resolve_size_preset(form, size):
    assert logo._resolve_size(size, form) == LOGO_SIZES[form][size]


def test_resolve_size_explicit_height():
    assert logo._resolve_size(1.25, "lockup") == 1.25


def test_resolve_size_rejects_an_unknown_form():
    with pytest.raises(ValueError, match="unknown form 'wordmark'"):
        logo._resolve_size("small", "wordmark")


def test_resolve_size_rejects_an_unknown_preset():
    with pytest.raises(ValueError, match="unknown size 'medium'"):
        logo._resolve_size("medium", "lockup")


@pytest.mark.parametrize("size", [-1.0, 0.0, float("nan"), float("inf")])
def test_resolve_size_rejects_a_nonpositive_or_nonfinite_height(size):
    with pytest.raises(ValueError, match="positive finite"):
        logo._resolve_size(size, "lockup")


def test_resolve_size_rejects_a_sequence():
    with pytest.raises(TypeError):
        logo._resolve_size([1.0, 2.0], "lockup")


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_resolve_theme_explicit_is_taken_as_given(theme):
    figure, axes = plt.subplots()
    axes.set_facecolor("black" if theme == "light" else "white")
    assert logo._resolve_theme(theme, figure, axes) == theme
    plt.close(figure)


def test_resolve_theme_auto_on_a_default_figure():
    figure, axes = plt.subplots()
    assert logo._resolve_theme("auto", figure, axes) == "light"
    plt.close(figure)


def test_resolve_theme_auto_reads_the_axes_first():
    """The axes is the background the logo actually sits on."""
    figure, axes = plt.subplots()
    axes.set_facecolor("#101820")
    assert logo._resolve_theme("auto", figure, axes) == "dark"
    plt.close(figure)


def test_resolve_theme_auto_falls_through_a_transparent_axes():
    """A transparent axes shows the figure, so the figure is what to measure."""
    figure, axes = plt.subplots()
    axes.set_facecolor("none")
    figure.set_facecolor("black")
    assert logo._resolve_theme("auto", figure, axes) == "dark"
    plt.close(figure)


def test_resolve_theme_auto_under_the_dark_background_style():
    with plt.style.context("dark_background"):
        figure, axes = plt.subplots()
        assert logo._resolve_theme("auto", figure, axes) == "dark"
        plt.close(figure)


def test_resolve_theme_auto_with_nothing_opaque_assumes_light():
    """Nothing to measure: print is the default medium, and print is white."""
    figure = plt.figure()
    figure.set_facecolor("none")
    assert logo._resolve_theme("auto", figure, None) == "light"
    plt.close(figure)


def test_resolve_theme_rejects_an_unknown_name():
    figure = plt.figure()
    with pytest.raises(ValueError, match="unknown theme 'sepia'"):
        logo._resolve_theme("sepia", figure, None)
    plt.close(figure)


def test_loc_table_covers_the_legend_vocabulary():
    """Ten strings, nine positions — ``right`` is ``center right``, as in ``legend``."""
    assert set(logo._LOC) == {
        "upper right",
        "upper left",
        "lower left",
        "lower right",
        "right",
        "center left",
        "center right",
        "lower center",
        "upper center",
        "center",
    }
    assert logo._LOC["right"] == logo._LOC["center right"]


@pytest.mark.parametrize(
    ("loc", "anchor", "alignment", "offset"),
    [
        ("lower left", (0.0, 0.0), (0.0, 0.0), (6.0, 6.0)),
        ("lower right", (1.0, 0.0), (1.0, 0.0), (-6.0, 6.0)),
        ("upper left", (0.0, 1.0), (0.0, 1.0), (6.0, -6.0)),
        ("upper right", (1.0, 1.0), (1.0, 1.0), (-6.0, -6.0)),
        ("lower center", (0.5, 0.0), (0.5, 0.0), (0.0, 6.0)),
        ("upper center", (0.5, 1.0), (0.5, 1.0), (0.0, -6.0)),
        ("center left", (0.0, 0.5), (0.0, 0.5), (6.0, 0.0)),
        ("center right", (1.0, 0.5), (1.0, 0.5), (-6.0, 0.0)),
        ("center", (0.5, 0.5), (0.5, 0.5), (0.0, 0.0)),
    ],
)
def test_resolve_loc_string(loc, anchor, alignment, offset):
    """The pad pushes inward from whichever edge the anchor sits on."""
    assert logo._resolve_loc(loc, 6.0) == (anchor, alignment, offset)


def test_resolve_loc_pair_places_the_lower_left_corner_and_ignores_pad():
    assert logo._resolve_loc((0.35, 0.2), 50.0) == ((0.35, 0.2), (0.0, 0.0), (0.0, 0.0))


def test_resolve_loc_pair_allows_coordinates_outside_the_box():
    """``annotation_clip=False`` renders these, and ``legend`` permits them too."""
    anchor, _alignment, _offset = logo._resolve_loc((-0.1, 1.4), 6.0)
    assert anchor == (-0.1, 1.4)


def test_resolve_loc_rejects_best_by_name():
    with pytest.raises(ValueError, match="no collision detection"):
        logo._resolve_loc("best", 6.0)


def test_resolve_loc_rejects_an_unknown_string():
    with pytest.raises(ValueError, match="unknown loc 'middle'"):
        logo._resolve_loc("middle", 6.0)


@pytest.mark.parametrize("loc", [(0.1, 0.2, 0.3), ("a", 0.1), 0.5])
def test_resolve_loc_rejects_a_malformed_pair(loc):
    with pytest.raises(TypeError, match=r"\(x, y\) pair"):
        logo._resolve_loc(loc, 6.0)


@pytest.mark.parametrize("loc", [(float("nan"), 0.1), (0.1, float("inf"))])
def test_resolve_loc_rejects_a_nonfinite_coordinate(loc):
    with pytest.raises(ValueError, match="must be finite"):
        logo._resolve_loc(loc, 6.0)


def test_image_options_passes_known_keys_through():
    options = {"alpha": 0.5, "interpolation": "nearest"}
    assert logo._image_options(options) == options


def test_image_options_rejects_an_unknown_key():
    """``OffsetImage`` would raise ``AttributeError`` from deep inside; be clearer."""
    with pytest.raises(TypeError, match="unknown option bogus"):
        logo._image_options({"bogus": 1})


def test_image_options_names_every_unknown_key():
    with pytest.raises(TypeError, match="unknown option bogus, spurious"):
        logo._image_options({"spurious": 2, "bogus": 1})
