# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the shared canvas-colour helper (logo spec §3.5)."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from tephpy.plotting import _theme


def test_canvas_rgb_on_a_default_figure():
    """The default canvas is the white page, which is what it has always been."""
    figure, axes = plt.subplots()
    assert _theme.canvas_rgb(axes) == (1.0, 1.0, 1.0)
    plt.close(figure)


def test_canvas_rgb_reads_the_axes_over_the_figure():
    """An opaque axes hides the figure under it."""
    figure, axes = plt.subplots()
    axes.set_facecolor("black")
    assert _theme.canvas_rgb(axes) == (0.0, 0.0, 0.0)
    plt.close(figure)


def test_canvas_rgb_falls_through_a_transparent_axes():
    """A transparent axes shows the figure, so the figure is what shows."""
    figure, axes = plt.subplots()
    axes.set_facecolor("none")
    figure.set_facecolor("black")
    assert _theme.canvas_rgb(axes) == (0.0, 0.0, 0.0)
    plt.close(figure)


def test_canvas_rgb_composites_a_translucent_axes_over_the_figure():
    """10% black over a white figure is near-white, not black.

    Reading the axes' own channels would answer black for a background the
    reader sees as near-white (logo spec §3.5).
    """
    figure, axes = plt.subplots()
    axes.set_facecolor((0.0, 0.0, 0.0, 0.1))
    assert _theme.canvas_rgb(axes) == pytest.approx((0.9, 0.9, 0.9))
    plt.close(figure)


def test_canvas_rgb_composites_a_translucent_figure_over_the_page():
    """Nothing sits under the figure, so it composites over the assumed page."""
    figure = plt.figure()
    figure.set_facecolor((0.0, 0.0, 0.0, 0.1))
    assert _theme.canvas_rgb(figure) == pytest.approx((0.9, 0.9, 0.9))
    plt.close(figure)


def test_canvas_rgb_with_nothing_opaque_is_the_assumed_white_page():
    """Nothing to measure: print is the default medium, and print is white."""
    figure = plt.figure()
    figure.set_facecolor("none")
    assert _theme.canvas_rgb(figure) == (1.0, 1.0, 1.0)
    plt.close(figure)


def test_canvas_rgb_composites_the_other_way_too():
    """The same arithmetic must darken as well as lighten."""
    figure, axes = plt.subplots()
    figure.set_facecolor("black")
    axes.set_facecolor((1.0, 1.0, 1.0, 0.1))
    assert _theme.canvas_rgb(axes) == pytest.approx((0.1, 0.1, 0.1))
    plt.close(figure)


def test_canvas_rgb_reads_the_root_figure_through_a_subfigure():
    """A subfigure is transparent by default, so the root figure is the canvas.

    Stopping at the axes' direct parent answers white for a canvas the reader
    sees as black, which is the defect of :issue:`173` all over again.
    """
    figure = plt.figure(facecolor="black")
    subfigure = figure.subfigures()
    axes = subfigure.add_subplot()
    axes.set_facecolor("none")
    assert _theme.canvas_rgb(axes) == (0.0, 0.0, 0.0)
    plt.close(figure)


def test_canvas_rgb_stops_at_the_nearest_opaque_subfigure():
    """Every subfigure in the chain is composited, nearest the reader last.

    Red, because white is what a walk that never leaves the axes answers and
    black is what one that runs to the root answers: only a walk that reads
    each subfigure on the way past can say red.
    """
    figure = plt.figure(facecolor="black")
    outer = figure.subfigures()
    outer.set_facecolor("red")
    inner = outer.subfigures()
    axes = inner.add_subplot()
    axes.set_facecolor("none")
    assert _theme.canvas_rgb(axes) == (1.0, 0.0, 0.0)
    plt.close(figure)
