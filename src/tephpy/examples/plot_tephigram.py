# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The Tephigram
=============

The bare diagram: the five :term:`isopleth` families of a :term:`tephigram`,
on a coordinate system rotated so that :term:`isotherms <isotherm>` and
:term:`dry adiabats <dry adiabat>` cross at right angles.

The :term:`projection` is registered by importing tephpy, and the extent is
given as a pressure range and a temperature range.
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
    # The ranges the diagram already frames itself with, restated so the
    # example shows how to reframe it. `tests/examples` pins them to the
    # default, so a change to that default cannot leave this figure behind.
    ax.set_extent(pressure=(900.0, 200.0), temperature=(-65.0, 5.0))
    ax.set_title("Tephigram")
    return fig


if __name__ == "__main__":
    main()
    plt.show()
