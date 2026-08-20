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

Asked about one artist rather than handed a list of layers, because the layers
are the part that is easy to get wrong: a subfigure paints nothing by default,
so an axes inside one is over the root figure through two invisible sheets, and
a caller passing what it happened to have would leave the root out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.colors as mcolors

if TYPE_CHECKING:
    from collections.abc import Iterator
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

        def get_figure(self, *, root: bool = ...) -> Background | None:
            """Return what this is drawn on, one step out.

            Parameters
            ----------
            root : bool, optional
                Passed ``False``, so the answer is the direct parent rather
                than the figure at the top of the tree. Keyword-only here
                because that is the only way this is ever called, and a
                positional flag reads as nothing at the call site.

            Returns
            -------
            Background or None
                The enclosing figure or subfigure. A root figure answers
                itself and a detached artist answers ``None``, which is how
                :func:`_backgrounds` knows the walk is over.
            """


__all__ = ["canvas_rgb"]


def _backgrounds(artist: Background) -> Iterator[Background]:
    """Walk out from `artist` to the root figure, yielding back to front.

    Parameters
    ----------
    artist : Background
        Where to start, nearest the reader — typically an axes.

    Yields
    ------
    Background
        `artist` and every figure enclosing it, furthest from the reader
        first, so the caller can composite them in painting order.
    """
    stack = []
    node: Background | None = artist
    while node is not None:
        stack.append(node)
        parent = node.get_figure(root=False)
        # A root figure is its own ``root=False`` parent, which is what ends
        # the walk; an artist detached from its figure answers ``None``.
        node = None if parent is node else parent
    yield from reversed(stack)


def canvas_rgb(artist: Background) -> tuple[float, float, float]:
    """Composite everything behind `artist` over an assumed white page.

    The backgrounds are alpha-composited back to front — the page, then the
    root figure, then each subfigure on the way in, then `artist` itself — so
    a translucent background is judged on what the reader actually sees
    rather than on its own channels: 10% black over white is near-white, not
    black. An alpha of 0 leaves the accumulator untouched, which is how a
    transparent axes defers to the figure under it and a transparent figure
    falls back to the page (logo spec §3.5).

    The whole stack, rather than `artist` and its direct parent, because a
    subfigure is transparent by default: an axes in one shows the root figure
    through two invisible layers, and stopping at the first would answer
    white for a canvas the reader sees as black.

    Parameters
    ----------
    artist : Background
        The layer nearest the reader — an axes, or a figure where there is no
        axes to read. What encloses it is found from it, so there is no way
        to ask this about half a stack.

    Returns
    -------
    tuple of float
        The composited ``(red, green, blue)`` in ``[0, 1]``, always opaque.
    """
    red = green = blue = 1.0
    for layer in _backgrounds(artist):
        over_red, over_green, over_blue, alpha = mcolors.to_rgba(layer.get_facecolor())
        red = alpha * over_red + (1.0 - alpha) * red
        green = alpha * over_green + (1.0 - alpha) * green
        blue = alpha * over_blue + (1.0 - alpha) * blue
    return red, green, blue
