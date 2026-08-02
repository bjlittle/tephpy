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
import numpy as np
import pytest

from tephpy._constants import LOGO_PAD, LOGO_SIZES, LOGO_ZORDER, POINTS_PER_INCH
from tephpy.plotting import add_logo, logo

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


def test_resolve_target_rejects_a_removed_axes():
    """An axes removed from its figure has no parent; say so accurately."""
    figure, axes = plt.subplots()
    axes.remove()
    with pytest.raises(TypeError, match="removed"):
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
    with pytest.raises(TypeError, match="must be a string or a real number"):
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


def test_resolve_theme_auto_composites_a_translucent_axes_over_the_figure():
    """10% black over white reads as nearly white, so the logo needs the light mark.

    Judging the axes on its own channels would score this 0.0 and pick the dark
    mark, which is the low-contrast answer on a background the reader sees as
    near-white (logo spec §3.5).
    """
    figure, axes = plt.subplots()
    axes.set_facecolor((0.0, 0.0, 0.0, 0.1))
    assert logo._resolve_theme("auto", figure, axes) == "light"
    plt.close(figure)


def test_resolve_theme_auto_composites_a_translucent_axes_the_other_way():
    """The same arithmetic must be able to darken, not only lighten."""
    figure, axes = plt.subplots()
    figure.set_facecolor("black")
    axes.set_facecolor((1.0, 1.0, 1.0, 0.1))
    assert logo._resolve_theme("auto", figure, axes) == "dark"
    plt.close(figure)


def test_resolve_theme_auto_composites_a_translucent_figure_over_the_page():
    """Nothing sits under the figure, so it composites over the assumed white page."""
    figure = plt.figure()
    figure.set_facecolor((0.0, 0.0, 0.0, 0.1))
    assert logo._resolve_theme("auto", figure, None) == "light"
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


@pytest.mark.parametrize(
    ("loc", "pad", "expected_offset"),
    [
        ("lower left", 10.0, (10.0, 10.0)),
        ("upper right", 10.0, (-10.0, -10.0)),
        ("lower right", 4.0, (-4.0, 4.0)),
        ("center right", 3.0, (-3.0, 0.0)),
    ],
)
def test_resolve_loc_string_pad_scales_offset(loc, pad, expected_offset):
    """The offset is ``pad * signs``; using a fixed constant would break these."""
    _, _, offset = logo._resolve_loc(loc, pad)
    assert offset == expected_offset


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
    with pytest.raises(TypeError, match=r"unknown option \['bogus'\]"):
        logo._image_options({"bogus": 1})


def test_image_options_names_every_unknown_key():
    with pytest.raises(TypeError, match=r"unknown option \['bogus', 'spurious'\]"):
        logo._image_options({"spurious": 2, "bogus": 1})


def _extent(artist, figure):
    """Return the artist's rendered box in display units, after a draw."""
    figure.canvas.draw()
    return artist.get_window_extent(figure.canvas.get_renderer())


@pytest.mark.parametrize("dpi", [100, 300, 600])
@pytest.mark.parametrize("form", ["icon", "lockup", "stacked"])
@pytest.mark.parametrize("size", ["small", "large"])
def test_rendered_height_is_the_requested_inches_at_any_dpi(dpi, form, size):
    """The whole point of the zoom calculation (logo spec §3.3)."""
    figure, axes = plt.subplots(figsize=(6, 4), dpi=dpi)
    box = _extent(add_logo(axes, form=form, size=size), figure)
    assert box.height / dpi == pytest.approx(LOGO_SIZES[form][size], abs=1e-6)
    plt.close(figure)


def test_annotation_bbox_pad_is_zero():
    """``AnnotationBbox``'s default 0.4 font-size units adds 0.111 in at 10 pt."""
    figure, axes = plt.subplots(figsize=(6, 4), dpi=100)
    box = _extent(add_logo(axes, form="lockup", size="small"), figure)
    assert box.height / 100 == pytest.approx(0.30, abs=1e-6)
    plt.close(figure)


def test_explicit_height_in_inches_is_honoured():
    figure, axes = plt.subplots(figsize=(6, 4), dpi=100)
    box = _extent(add_logo(axes, size=1.25), figure)
    assert box.height / 100 == pytest.approx(1.25, abs=1e-6)
    plt.close(figure)


@pytest.mark.parametrize(("dpi", "figsize"), [(100, (6, 4)), (300, (4.5, 6))])
@pytest.mark.parametrize("loc", sorted(logo._LOC))
def test_every_placement_lands_where_its_table_row_says(loc, dpi, figsize):
    """One arithmetic check per row, so a transposed sign cannot hide.

    Two dpi and two aspect ratios, because the gap is in points and the anchor
    is a fraction — either could be right at one shape and wrong at the other.
    """
    figure, axes = plt.subplots(figsize=figsize, dpi=dpi)
    box = _extent(add_logo(axes, loc=loc, pad=LOGO_PAD), figure)
    target = axes.get_window_extent()
    scale = dpi / POINTS_PER_INCH
    anchor, alignment, signs = logo._LOC[loc]
    x = target.x0 + anchor[0] * target.width + signs[0] * LOGO_PAD * scale
    y = target.y0 + anchor[1] * target.height + signs[1] * LOGO_PAD * scale
    assert box.x0 == pytest.approx(x - alignment[0] * box.width, abs=0.01)
    assert box.y0 == pytest.approx(y - alignment[1] * box.height, abs=0.01)
    plt.close(figure)


def test_a_pair_places_the_lower_left_corner_and_ignores_pad():
    figure, axes = plt.subplots(figsize=(6, 4), dpi=100)
    box = _extent(add_logo(axes, loc=(0.35, 0.2), pad=50.0), figure)
    target = axes.get_window_extent()
    assert box.x0 == pytest.approx(target.x0 + 0.35 * target.width, abs=0.01)
    assert box.y0 == pytest.approx(target.y0 + 0.2 * target.height, abs=0.01)
    plt.close(figure)


def test_a_figure_target_anchors_to_the_figure_not_the_axes():
    """The distinguishing property: the figure box is strictly outside the axes box."""
    figure, axes = plt.subplots(figsize=(6, 4), dpi=100)
    on_figure = _extent(add_logo(figure, loc="lower left"), figure)
    on_axes = _extent(add_logo(axes, loc="lower left"), figure)
    assert on_figure.x0 < on_axes.x0
    assert on_figure.y0 < on_axes.y0
    assert on_figure.x0 == pytest.approx(LOGO_PAD * 100 / POINTS_PER_INCH, abs=0.01)
    plt.close(figure)


def test_the_artist_is_returned_attached_and_removable():
    """The caller can restyle or drop it — the reason it is returned at all."""
    figure, axes = plt.subplots()
    artist = add_logo(axes)
    assert artist in axes.artists
    assert artist.get_zorder() == LOGO_ZORDER
    artist.remove()
    assert artist not in axes.artists
    plt.close(figure)


def test_image_options_reach_the_offsetimage():
    figure, axes = plt.subplots()
    artist = add_logo(axes, alpha=0.5)
    assert artist.offsetbox.get_children()[0].get_alpha() == 0.5
    plt.close(figure)


def test_dark_theme_draws_the_dark_master():
    """``add_logo(ax, theme='dark')`` on a white figure must draw the dark artwork.

    A default (white) figure resolves to ``'light'`` under ``theme='auto'``, so
    explicit ``theme='dark'`` is the sharpest case: it cannot be satisfied by
    accident. If the artwork call ignores ``variant`` this assertion fails.
    """
    figure, axes = plt.subplots()
    artist = add_logo(axes, theme="dark")
    array = artist.offsetbox.get_children()[0].get_array()
    np.testing.assert_array_equal(array, logo._load_master("lockup", "dark"))
    plt.close(figure)


def test_form_selects_the_correct_master():
    """``add_logo(ax, form='stacked')`` must draw the stacked artwork, not the icon.

    If the artwork call ignores ``form`` this assertion fails.
    """
    figure, axes = plt.subplots()
    artist = add_logo(axes, form="stacked")
    array = artist.offsetbox.get_children()[0].get_array()
    np.testing.assert_array_equal(array, logo._load_master("stacked", "light"))
    plt.close(figure)


def test_no_target_brands_the_current_figure():
    figure = plt.figure(figsize=(6, 4), dpi=100)
    assert add_logo().figure is figure
    plt.close(figure)


@pytest.mark.parametrize(
    ("kwargs", "error", "match"),
    [
        ({"form": "wordmark"}, ValueError, "unknown form"),
        ({"size": "medium"}, ValueError, "unknown size"),
        ({"theme": "sepia"}, ValueError, "unknown theme"),
        ({"loc": "best"}, ValueError, "no collision detection"),
        ({"bogus": 1}, TypeError, "unknown option"),
    ],
)
def test_every_resolver_is_wired_into_the_public_call(kwargs, error, match):
    """Each resolver's rejection must survive the trip through ``add_logo``."""
    figure, axes = plt.subplots()
    with pytest.raises(error, match=match):
        add_logo(axes, **kwargs)
    plt.close(figure)


def test_an_unusable_target_is_rejected():
    with pytest.raises(TypeError, match="Figure or an Axes"):
        add_logo("figure")


def test_explicit_pad_is_forwarded_not_ignored():
    """A non-default pad reaches the offset, visibly moving the logo."""
    figure, axes = plt.subplots(figsize=(6, 4), dpi=100)
    box = _extent(add_logo(axes, loc="lower left", pad=2 * LOGO_PAD), figure)
    target = axes.get_window_extent()
    gap = 2 * LOGO_PAD * 100 / POINTS_PER_INCH
    assert box.x0 == pytest.approx(target.x0 + gap, abs=0.01)
    assert box.y0 == pytest.approx(target.y0 + gap, abs=0.01)
    plt.close(figure)


def test_explicit_zorder_is_forwarded_not_ignored():
    figure, axes = plt.subplots()
    assert add_logo(axes, zorder=7).get_zorder() == 7
    plt.close(figure)


def test_nonfinite_pad_is_rejected():
    figure, axes = plt.subplots()
    with pytest.raises(ValueError, match="pad must be a finite"):
        add_logo(axes, pad=float("nan"))
    plt.close(figure)


def test_string_pad_raises_value_error():
    """A string ``pad`` raises ``ValueError`` naming the parameter (logo spec §5)."""
    figure, axes = plt.subplots()
    with pytest.raises(ValueError, match="pad must be a finite number of points"):
        add_logo(axes, pad="three")
    plt.close(figure)


def test_nonfinite_zorder_is_rejected():
    figure, axes = plt.subplots()
    with pytest.raises(ValueError, match="zorder must be a finite"):
        add_logo(axes, zorder=float("inf"))
    plt.close(figure)


def test_pair_loc_outside_unit_box_places_extent_past_axes_edge():
    """A pair loc outside [0, 1] positions the logo's extent outside the axes."""
    figure, axes = plt.subplots(figsize=(6, 4), dpi=100)
    box = _extent(add_logo(axes, loc=(1.05, 1.05)), figure)
    target = axes.get_window_extent()
    assert box.x0 > target.x1
    assert box.y0 > target.y1
    plt.close(figure)


def test_annotation_clip_false_draws_logo_outside_axes_bounds():
    """``annotation_clip=False`` means a loc outside [0, 1] is actually drawn.

    ``get_window_extent`` is computed unconditionally; only rendered output
    can confirm the artist is drawn.
    """
    figure, axes = plt.subplots(figsize=(6, 4), dpi=100)
    artist = add_logo(axes, loc=(1.05, 1.05))
    figure.canvas.draw()
    drawn = figure.canvas.buffer_rgba().tobytes()  # copy: the buffer is reused
    artist.set_annotation_clip(True)
    figure.canvas.draw()
    assert drawn != figure.canvas.buffer_rgba().tobytes()
    plt.close(figure)
