# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""A Hodograph beside a Tephigram
==============================

tephpy draws tephigrams and leaves hodographs to MetPy, so the two go side
by side in one figure, from one :class:`Sounding <tephpy.sounding.Sounding>`.

A tephigram shows the thermodynamic profile and a hodograph the wind
profile, and a forecaster reads them together.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
from metpy.calc import wind_components
from metpy.plots import Hodograph

from tephpy import samples

if TYPE_CHECKING:
    from matplotlib.figure import Figure

# sphinx_gallery_tags = ["metpy", "barbs", "sounding"]


def main() -> Figure:
    """Draw a tephigram and a hodograph from one sounding.

    Returns
    -------
    matplotlib.figure.Figure
        The composed figure.
    """
    snd = samples.sounding("norman-12z")
    fig = plt.figure(figsize=(8.0, 4.0))
    ax = fig.add_subplot(1, 2, 1, projection="tephigram")
    ax.plot_sounding(snd)
    ax.plot_barbs(snd)
    hodograph = Hodograph(fig.add_subplot(1, 2, 2), component_range=40.0)
    hodograph.add_grid(increment=10.0)
    hodograph.plot(*wind_components(snd.wind_speed, snd.wind_direction))
    return fig


if __name__ == "__main__":
    main()
    plt.show()
