# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the tephigram matplotlib projection (spec §3.1)."""

from __future__ import annotations

import numpy as np

from tephpy import transforms
from tephpy.plotting.axes import TephigramTransform


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
