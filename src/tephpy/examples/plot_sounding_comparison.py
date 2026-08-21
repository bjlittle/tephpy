# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Comparing Two Soundings
=======================

Two :term:`soundings <sounding>` from the same station on the same day,
overlaid on a fixed extent so the change between them is the only thing
that moves.

Norman, Oklahoma on 2013-05-20: the 12Z ascent, and the 17Z
:term:`special <special sounding>` released about three hours before the
Moore EF5 tornado. Over those five hours the :term:`cap` erodes from
-271 J/kg to nothing while :term:`CAPE` nearly triples. The extent is closer
than the default view, and both ascents run out of the top of it near
250 hPa. That is deliberate: everything that changed between them lies in
the lower troposphere, far below.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from tephpy import samples

if TYPE_CHECKING:
    from matplotlib.figure import Figure

# sphinx_gallery_tags = ["overlay", "sounding"]

# Both profiles are drawn against this, so neither ascent's own data can
# decide the frame the comparison is read in. It is a quarter narrower
# than the default view and clips both ascents near 250 hPa: the two differ
# in the lower troposphere, and the frame is worth no more than the story
# it carries.
EXTENT = ((950.0, -50.0), (300.0, 5.0))


def main() -> Figure:
    """Overlay the 12Z and 17Z ascents.

    Returns
    -------
    matplotlib.figure.Figure
        The composed figure.
    """
    morning = samples.sounding("norman-12z")
    afternoon = samples.sounding("norman-17z")
    fig, ax = plt.subplots(figsize=(8.0, 4.0), subplot_kw={"projection": "tephigram"})
    ax.set_extent(EXTENT)
    ax.plot_sounding(morning, linestyle="--")
    ax.plot_sounding(afternoon)
    ax.legend()
    return fig


# %%
# Saving the Figure
# -----------------
#
# The diagram is drawn as vectors, so it saves at publication quality:
#
# .. code-block:: python
#
#     fig.savefig("sounding-comparison.pdf")
#
# It is shown rather than run, so that browsing the gallery writes no
# files.

if __name__ == "__main__":
    main()
    plt.show()
