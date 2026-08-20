# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""A Sounding
============

Temperature and dewpoint profiles, with the ascent's wind barbs on the
gutter staff to the right of the diagram.

The sounding is Norman, Oklahoma at 12Z on 2013-05-20.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from tephpy import samples

if TYPE_CHECKING:
    from matplotlib.figure import Figure

# sphinx_gallery_tags = ["sounding", "barbs"]


def main() -> Figure:
    """Draw a sounding and its wind barbs.

    Returns
    -------
    matplotlib.figure.Figure
        The composed figure.
    """
    snd = samples.sounding("norman-12z")
    fig, ax = plt.subplots(figsize=(8.0, 4.0), subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(snd)
    ax.plot_barbs(snd)
    ax.legend()
    return fig


if __name__ == "__main__":
    main()
    plt.show()
