# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The tephigram matplotlib projection.

``TephigramAxes`` (registered as the ``"tephigram"`` projection, Task 5)
uses the native rotated x-y plane as its data space, with the
temperature/theta mapping exposed as an invertible matplotlib transform.
Plan 3 extends this class in place with the isopleth machinery.
"""

from __future__ import annotations

import matplotlib.transforms as mtransforms
import numpy as np
import numpy.typing as npt

from tephpy import transforms

__all__ = ["TephigramInvertedTransform", "TephigramTransform"]


class TephigramTransform(mtransforms.Transform):
    """Map ``(temperature, theta)`` pairs to tephigram ``(x, y)`` pairs.

    A thin, invertible matplotlib wrapper over
    :func:`tephpy.transforms.xy_from_temperature_theta`; operates on
    ``(N, 2)`` arrays in diagram-native units (degrees Celsius).
    """

    input_dims = 2
    output_dims = 2
    is_separable = False
    has_inverse = True

    def transform_non_affine(self, values: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Transform ``(N, 2)`` (temperature, theta) columns to (x, y).

        Parameters
        ----------
        values : array_like
            Array-like of shape ``(N, 2)``: temperature, theta in degrees
            Celsius.

        Returns
        -------
        numpy.ndarray
            Array of shape ``(N, 2)``: the x, y display coordinates.
        """
        arr = np.asarray(values, dtype=np.float64)
        x, y = transforms.xy_from_temperature_theta(arr[:, 0], arr[:, 1])
        return np.column_stack([x, y])

    def inverted(self) -> TephigramInvertedTransform:
        """Return the inverse (x, y) -> (temperature, theta) transform.

        Returns
        -------
        TephigramInvertedTransform
            The inverse transform.
        """
        return TephigramInvertedTransform()


class TephigramInvertedTransform(mtransforms.Transform):
    """Map tephigram ``(x, y)`` pairs back to ``(temperature, theta)``."""

    input_dims = 2
    output_dims = 2
    is_separable = False
    has_inverse = True

    def transform_non_affine(self, values: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Transform ``(N, 2)`` (x, y) columns to (temperature, theta).

        Parameters
        ----------
        values : array_like
            Array-like of shape ``(N, 2)``: x, y display coordinates.

        Returns
        -------
        numpy.ndarray
            Array of shape ``(N, 2)``: temperature, theta in degrees
            Celsius.
        """
        arr = np.asarray(values, dtype=np.float64)
        t, theta = transforms.temperature_theta_from_xy(arr[:, 0], arr[:, 1])
        return np.column_stack([t, theta])

    def inverted(self) -> TephigramTransform:
        """Return the forward (temperature, theta) -> (x, y) transform.

        Returns
        -------
        TephigramTransform
            The forward transform.
        """
        return TephigramTransform()
