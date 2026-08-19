# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Read the colour of the canvas a diagram is drawn on.

One definition of "what colour is the background", shared by the two places
that need it: ``logo.add_logo`` thresholds it to choose a light or dark brand
master (logo spec §3.5), and ``isopleths.IsoplethFamily`` takes it directly to
tint its inline label boxes, so a label masks the lines behind it on a dark
canvas as well as on a white one (spec §3.2).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.colors as mcolors

if TYPE_CHECKING:
    from typing import Protocol

    from matplotlib.typing import ColorType

    class Background(Protocol):
        """Anything that paints a background: a figure, a subfigure, an axes.

        Narrower than ``Artist``, which does not promise a facecolor, and
        wider than the three concrete classes — ``Artist.axes`` is typed
        ``_AxesBase``, and this helper has no business naming a private
        matplotlib class to say "something with a background colour".
        """

        def get_facecolor(self) -> ColorType:
            """Return the background colour.

            Returns
            -------
            matplotlib.typing.ColorType
                Any colour matplotlib accepts, with or without an alpha.
            """


__all__ = ["canvas_rgb"]


def canvas_rgb(*layers: Background | None) -> tuple[float, float, float]:
    """Composite the given backgrounds over an assumed white page.

    The layers are alpha-composited back to front — the page, then each
    layer in turn — so a translucent background is judged on what the reader
    actually sees rather than on its own channels: 10% black over white is
    near-white, not black. An alpha of 0 leaves the accumulator untouched,
    which is how a transparent axes defers to the figure under it and a
    transparent figure falls back to the page (logo spec §3.5).

    Parameters
    ----------
    *layers : Background or None
        The backgrounds, furthest from the reader first — typically a figure
        and then the axes over it — each read through its ``get_facecolor``.
        A ``None`` layer is skipped, so a caller with no axes may pass one
        without a guard of its own.

    Returns
    -------
    tuple of float
        The composited ``(red, green, blue)`` in ``[0, 1]``, always opaque.
    """
    red = green = blue = 1.0
    for layer in layers:
        if layer is None:
            continue
        over_red, over_green, over_blue, alpha = mcolors.to_rgba(layer.get_facecolor())
        red = alpha * over_red + (1.0 - alpha) * red
        green = alpha * over_green + (1.0 - alpha) * green
        blue = alpha * over_blue + (1.0 - alpha) * blue
    return red, green, blue
