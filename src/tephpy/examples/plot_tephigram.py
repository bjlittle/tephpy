# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The Tephigram
==============

The bare diagram: five isopleth families on a coordinate system rotated so
that isotherms and dry adiabats cross at right angles.

The projection is registered by importing tephpy, and the extent is given
as two (pressure, temperature) corners.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

import tephpy  # registers the "tephigram" projection

if TYPE_CHECKING:
    from matplotlib.figure import Figure

# sphinx_gallery_tags = ["diagram", "isopleths"]


def main() -> Figure:
    """Draw a tephigram over a chosen extent.

    Returns
    -------
    matplotlib.figure.Figure
        The composed figure.
    """
    fig, ax = plt.subplots(figsize=(8.0, 4.0), subplot_kw={"projection": "tephigram"})
    ax.set_extent(((1050.0, -40.0), (200.0, 40.0)))
    ax.set_title("Tephigram")
    return fig


if __name__ == "__main__":
    main()
    plt.show()
