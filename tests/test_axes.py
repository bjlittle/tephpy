# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the tephigram matplotlib projection (spec §3.1)."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest

import tephpy
from tephpy import transforms
from tephpy.plotting.axes import TephigramAxes, TephigramTransform


def test_transform_matches_functions():
    """The matplotlib Transform delegates to the transforms module exactly."""
    tr = TephigramTransform()
    points = np.array([[15.0, 15.0], [-40.0, 20.0], [0.0, 100.0]])
    out = tr.transform(points)
    x, y = transforms.xy_from_temperature_theta(points[:, 0], points[:, 1])
    np.testing.assert_allclose(out, np.column_stack([x, y]), rtol=1e-12)


def test_transform_round_trip_via_inverted():
    """Transform followed by its inverse is the identity (invertibility)."""
    tr = TephigramTransform()
    points = np.array([[15.0, 15.0], [-40.0, 20.0], [30.0, 250.0]])
    back = tr.inverted().transform(tr.transform(points))
    np.testing.assert_allclose(back, points, rtol=1e-9, atol=1e-9)


def test_transform_dimensions():
    """2-in, 2-out, non-separable, declared invertible."""
    tr = TephigramTransform()
    assert tr.input_dims == 2
    assert tr.output_dims == 2
    assert not tr.is_separable
    assert tr.has_inverse


@pytest.fixture
def tephigram_axes():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    yield ax
    plt.close(fig)


def test_projection_registered_by_package_import(tephigram_axes):
    """`import tephpy` registers the projection for stock matplotlib idioms."""
    assert isinstance(tephigram_axes, TephigramAxes)
    assert tephigram_axes.name == "tephigram"


def test_axes_defaults(tephigram_axes):
    """Equal aspect, hidden native ticks, finite default extents."""
    assert tephigram_axes.get_aspect() == 1.0
    assert not tephigram_axes.xaxis.get_visible()
    assert not tephigram_axes.yaxis.get_visible()
    x0, x1 = tephigram_axes.get_xlim()
    y0, y1 = tephigram_axes.get_ylim()
    assert np.isfinite([x0, x1, y0, y1]).all()
    assert x0 < x1
    assert y0 < y1


def test_axes_exposes_invertible_tephigram_transform(tephigram_axes):
    """The (T, theta) mapping is available for artists and later plans."""
    composed = tephigram_axes.tephigram_transform + tephigram_axes.transData
    points = np.array([[15.0, 15.0], [-40.0, 20.0]])
    display = composed.transform(points)
    assert np.isfinite(display).all()
    back = tephigram_axes.tephigram_transform.inverted().transform(
        tephigram_axes.tephigram_transform.transform(points)
    )
    np.testing.assert_allclose(back, points, rtol=1e-9)


def test_plot_in_temperature_theta_space(tephigram_axes):
    """Plotting through the exposed transform draws within the default view.

    The line is added to the axes and its mapped (x, y) endpoints land
    inside the default xlim/ylim, so it is genuinely in view.
    """
    (line,) = tephigram_axes.plot(
        [0.0, 10.0],
        [10.0, 40.0],
        transform=tephigram_axes.tephigram_transform + tephigram_axes.transData,
    )
    assert line in tephigram_axes.lines
    x, y = transforms.xy_from_temperature_theta(
        np.array([0.0, 10.0]), np.array([10.0, 40.0])
    )
    x0, x1 = tephigram_axes.get_xlim()
    y0, y1 = tephigram_axes.get_ylim()
    assert np.all((x0 <= x) & (x <= x1))
    assert np.all((y0 <= y) & (y <= y1))


def test_top_level_namespace():
    """Submodules are reachable from the package root (spec §4 idiom)."""
    assert tephpy.transforms is not None
    assert tephpy.plotting is not None
    assert set(tephpy.__all__) == {"__version__", "plotting", "transforms"}
