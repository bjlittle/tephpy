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

from matplotlib.axes import Axes
from matplotlib.projections import register_projection
import matplotlib.transforms as mtransforms
import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._constants import DEFAULT_ANCHOR

__all__ = ["TephigramAxes", "TephigramInvertedTransform", "TephigramTransform"]


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


class TephigramAxes(Axes):
    """Matplotlib axes for the ``"tephigram"`` projection.

    The data space is the native rotated x-y plane (dimensionless), with
    equal aspect so the isotherm/dry-adiabat grid stays exactly
    perpendicular on screen. The temperature/theta mapping is exposed as
    :attr:`tephigram_transform`; artists plot in (temperature, theta)
    space via ``transform=ax.tephigram_transform + ax.transData``. Native
    x/y ticks carry no meteorological meaning and are hidden — meaningful
    labelling arrives with the Plan 3 isopleths.

    Parameters
    ----------
    *args : object
        Positional arguments forwarded to :class:`matplotlib.axes.Axes`.
    **kwargs : object
        Keyword arguments forwarded to :class:`matplotlib.axes.Axes`.
    """

    name = "tephigram"

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise the axes and apply the tephigram view defaults.

        Parameters
        ----------
        *args : object
            Positional arguments forwarded to :class:`matplotlib.axes.Axes`.
        **kwargs : object
            Keyword arguments forwarded to :class:`matplotlib.axes.Axes`.
        """
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.tephigram_transform = TephigramTransform()
        self.set_aspect(1.0, adjustable="box")
        self.xaxis.set_visible(False)
        self.yaxis.set_visible(False)
        self._set_default_extent()

    def _set_default_extent(self) -> None:
        """Frame the default view from the ``DEFAULT_ANCHOR`` corners."""
        (p_bottom, t_left), (p_top, t_right) = DEFAULT_ANCHOR
        corner_pressures = np.array([p_bottom, p_top])
        corner_temperatures = np.array([t_left, t_right])
        thetas = transforms.theta_from_pressure_temperature(
            corner_pressures, corner_temperatures
        )
        x, y = transforms.xy_from_temperature_theta(corner_temperatures, thetas)
        self.set_xlim(float(np.min(x)), float(np.max(x)))
        self.set_ylim(float(np.min(y)), float(np.max(y)))


register_projection(TephigramAxes)
