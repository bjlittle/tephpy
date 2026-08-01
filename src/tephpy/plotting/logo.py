# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Place the tephpy logo on a figure or an axes.

The masters under ``_static`` are byte-identical copies of the published brand
bundle (logo spec §3.2), kept that way by a drift guard in
``tests/plotting/test_logo.py``. Sizing is a height in inches and is
dpi-independent (logo spec §3.3); placement follows the ``legend`` vocabulary
(logo spec §3.4).
"""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from io import BytesIO
import math
from typing import TYPE_CHECKING, Any, Final

from matplotlib.axes import Axes
import matplotlib.colors as mcolors
from matplotlib.figure import Figure
import matplotlib.image as mimage
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

from tephpy._constants import (
    LOGO_LUMINANCE_THRESHOLD,
    LOGO_LUMINANCE_WEIGHTS,
    LOGO_PAD,
    LOGO_SIZES,
    LOGO_ZORDER,
    POINTS_PER_INCH,
)

__all__ = ["add_logo"]

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

_MASTERS: Final[dict[tuple[str, str], str]] = {
    ("icon", "light"): "icon-512-light.png",
    ("icon", "dark"): "icon-512-dark.png",
    ("lockup", "light"): "lockup-716-light.png",
    ("lockup", "dark"): "lockup-716-dark.png",
    ("stacked", "light"): "stacked-512-light.png",
    ("stacked", "dark"): "stacked-512-dark.png",
}

#: Placement string to ``(anchor, box_alignment, offset signs)``. The anchor is a
#: point in the target's fraction coordinates, the alignment names which corner
#: of the logo lands on it, and the signs turn ``pad`` into an inward offset in
#: points (logo spec §3.4). ``right`` aliases ``center right``, as in ``legend``.
_LOC: Final[
    dict[str, tuple[tuple[float, float], tuple[float, float], tuple[float, float]]]
] = {
    "upper right": ((1.0, 1.0), (1.0, 1.0), (-1.0, -1.0)),
    "upper left": ((0.0, 1.0), (0.0, 1.0), (1.0, -1.0)),
    "lower left": ((0.0, 0.0), (0.0, 0.0), (1.0, 1.0)),
    "lower right": ((1.0, 0.0), (1.0, 0.0), (-1.0, 1.0)),
    "right": ((1.0, 0.5), (1.0, 0.5), (-1.0, 0.0)),
    "center left": ((0.0, 0.5), (0.0, 0.5), (1.0, 0.0)),
    "center right": ((1.0, 0.5), (1.0, 0.5), (-1.0, 0.0)),
    "lower center": ((0.5, 0.0), (0.5, 0.0), (0.0, 1.0)),
    "upper center": ((0.5, 1.0), (0.5, 1.0), (0.0, -1.0)),
    "center": ((0.5, 0.5), (0.5, 0.5), (0.0, 0.0)),
}

#: The ``OffsetImage`` options ``add_logo`` forwards. Anything else is a typo
#: worth naming, because ``OffsetImage`` reports it as an ``AttributeError``
#: raised by ``BboxImage.set`` (logo spec §5).
_IMAGE_KEYS: Final[frozenset[str]] = frozenset(
    {"alpha", "filternorm", "filterrad", "interpolation", "resample"}
)


def _resolve_target(target: Figure | Axes | None) -> tuple[Figure, Axes | None]:
    """Split the target into the figure that owns it and the axes, if any.

    Parameters
    ----------
    target : matplotlib.figure.Figure or matplotlib.axes.Axes or None
        What to brand. ``None`` takes the current figure.

    Returns
    -------
    tuple of (matplotlib.figure.Figure, matplotlib.axes.Axes or None)
        The owning figure, and the axes when one was given.

    Raises
    ------
    TypeError
        If `target` is neither a figure nor an axes, is an axes belonging to
        a :class:`matplotlib.figure.SubFigure`, or is an axes that has been
        removed from its figure.
    """
    if target is None:
        # Local: keeps pyplot out of ``import tephpy`` (logo spec §3.2).
        import matplotlib.pyplot as plt  # noqa: PLC0415

        target = plt.gcf()
    # Widened so the guard below stays reachable under mypy's ``warn_unreachable``
    # for a caller who ignores the annotation — which is the caller it protects
    # against. Narrow it back and mypy calls the final ``raise`` dead code.
    resolved: object = target
    if isinstance(resolved, Axes):
        # ``get_figure(root=False)`` returns the direct parent (added in 3.10);
        # ``.figure`` resolved to the root Figure at the floor, hiding the
        # SubFigure guard, and at 3.10 without an explicit ``root`` argument it
        # emits a deprecation warning that ``filterwarnings = ["error"]`` makes
        # fatal.  ``root=False`` is the safe spelling across the support range.
        figure = resolved.get_figure(root=False)
        if figure is None:
            msg = "target axes has been removed from its figure."
            raise TypeError(msg)
        if not isinstance(figure, Figure):
            msg = "target axes must belong to a Figure, not a SubFigure."
            raise TypeError(msg)
        return figure, resolved
    if isinstance(resolved, Figure):
        return resolved, None
    msg = f"target must be a Figure or an Axes, got {type(resolved).__name__}."
    raise TypeError(msg)


def _resolve_size(size: str | float, form: str) -> float:
    """Turn a preset name or an explicit height into a height in inches.

    Parameters
    ----------
    size : str or float
        A key of the `form`'s ``LOGO_SIZES`` entry, or a height in inches.
    form : str
        Which mark, which selects the preset table.

    Returns
    -------
    float
        The logo height in inches.

    Raises
    ------
    TypeError
        If `size` is not a string or a real number.
    ValueError
        If `form` names no mark, if `size` names no preset, or if `size` is not
        a positive finite height.
    """
    presets = LOGO_SIZES.get(form)
    if presets is None:
        valid = ", ".join(sorted(LOGO_SIZES))
        msg = f"unknown form {form!r}, expected one of: {valid}."
        raise ValueError(msg)
    if isinstance(size, str):
        height = presets.get(size)
        if height is None:
            valid = ", ".join(sorted(presets))
            msg = (
                f"unknown size {size!r}, expected one of: {valid}, "
                "or a height in inches."
            )
            raise ValueError(msg)
        return height
    height = float(size)
    if not math.isfinite(height) or height <= 0.0:
        msg = f"size must be a positive finite height in inches, got {size!r}."
        raise ValueError(msg)
    return height


def _resolve_theme(theme: str, figure: Figure, axes: Axes | None) -> str:
    """Choose the light or dark variant, reading the background when asked to.

    ``"auto"`` measures the sRGB relative luminance of the first opaque
    facecolor among the axes and then the figure, so a transparent axes defers
    to the figure showing through it (logo spec §3.5).

    Parameters
    ----------
    theme : str
        ``"auto"``, ``"light"`` or ``"dark"``, naming the *background*.
    figure : matplotlib.figure.Figure
        The owning figure, measured when the axes is absent or transparent.
    axes : matplotlib.axes.Axes or None
        The target axes, measured first when there is one.

    Returns
    -------
    str
        ``"light"`` or ``"dark"``.

    Raises
    ------
    ValueError
        If `theme` is none of the three accepted names.
    """
    if theme in {"dark", "light"}:
        return theme
    if theme != "auto":
        msg = f"unknown theme {theme!r}, expected one of: auto, dark, light."
        raise ValueError(msg)
    for artist in (axes, figure):
        if artist is None:
            continue
        red, green, blue, alpha = mcolors.to_rgba(artist.get_facecolor())
        if alpha == 0.0:
            continue
        weight_red, weight_green, weight_blue = LOGO_LUMINANCE_WEIGHTS
        luminance = weight_red * red + weight_green * green + weight_blue * blue
        return "dark" if luminance < LOGO_LUMINANCE_THRESHOLD else "light"
    return "light"


def _resolve_loc(
    loc: str | tuple[float, float], pad: float
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """Turn a placement into an anchor, a box alignment and an offset in points.

    A pair places the logo's lower-left corner at those fraction coordinates and
    ignores `pad`, because the caller has already said exactly where they want
    it (logo spec §3.4).

    Parameters
    ----------
    loc : str or tuple of float
        A key of ``_LOC``, or an ``(x, y)`` pair in fraction coordinates.
    pad : float
        Points between the logo and the target's edge, for the string form.

    Returns
    -------
    tuple of (tuple of float, tuple of float, tuple of float)
        The anchor, the box alignment, and the offset in points.

    Raises
    ------
    TypeError
        If `loc` is neither a string nor a pair of floats.
    ValueError
        If `loc` names no placement, or holds a non-finite coordinate.
    """
    if isinstance(loc, str):
        placement = _LOC.get(loc)
        if placement is None:
            valid = ", ".join(sorted(_LOC))
            detail = (
                "loc='best' is unsupported: add_logo performs no collision detection"
                if loc == "best"
                else f"unknown loc {loc!r}"
            )
            msg = f"{detail}, expected one of: {valid}, or an (x, y) pair."
            raise ValueError(msg)
        anchor, alignment, signs = placement
        return anchor, alignment, (signs[0] * pad, signs[1] * pad)
    try:
        x, y = (float(value) for value in loc)
    except (TypeError, ValueError) as err:
        msg = (
            f"loc must be a placement string or an (x, y) pair of floats, got {loc!r}."
        )
        raise TypeError(msg) from err
    if not (math.isfinite(x) and math.isfinite(y)):
        msg = f"loc coordinates must be finite, got {loc!r}."
        raise ValueError(msg)
    return (x, y), (0.0, 0.0), (0.0, 0.0)


def _image_options(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Check the forwarded keywords against what ``OffsetImage`` accepts.

    Parameters
    ----------
    kwargs : dict
        The caller's surplus keyword arguments.

    Returns
    -------
    dict
        `kwargs` unchanged, once every key is known.

    Raises
    ------
    TypeError
        If any key is not an ``OffsetImage`` option.
    """
    unknown = sorted(set(kwargs) - _IMAGE_KEYS)
    if unknown:
        valid = ", ".join(sorted(_IMAGE_KEYS))
        msg = f"unknown option {', '.join(unknown)}; expected one of: {valid}."
        raise TypeError(msg)
    return kwargs


@cache
def _load_master(form: str, variant: str) -> npt.NDArray[np.floating[Any]]:
    """Read one packaged master, decoded once and shared thereafter.

    The array is marked read-only because every figure drawing that variant
    holds the same object (logo spec §3.6).

    Parameters
    ----------
    form : str
        Which mark: the first element of a ``_MASTERS`` key.
    variant : str
        Which background the mark is drawn on: ``"light"`` or ``"dark"``.

    Returns
    -------
    numpy.ndarray
        A read-only float RGBA array of shape ``(height, width, 4)``.
    """
    resource = files("tephpy.plotting").joinpath("_static", _MASTERS[form, variant])
    # ``read_bytes`` rather than ``open``: ``Traversable.open`` is typed
    # ``IO[bytes]``, which ``imread`` does not accept, and a cast would hide it.
    image = mimage.imread(BytesIO(resource.read_bytes()), format="png")
    image.setflags(write=False)
    return image


def add_logo(  # noqa: PLR0913 -- the placement contract is one flat keyword set
    target: Figure | Axes | None = None,
    *,
    form: str = "lockup",
    size: str | float = "small",
    theme: str = "auto",
    loc: str | tuple[float, float] = "lower left",
    pad: float | None = None,
    zorder: float | None = None,
    **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
) -> AnnotationBbox:
    """Draw the tephpy logo on a figure or an axes.

    The logo is an :class:`matplotlib.offsetbox.AnnotationBbox` anchored in the
    target's own fraction coordinates, so a figure target places it against the
    figure edges and an axes target against the axes edges, exactly as ``legend``
    does (logo spec §3.4). Its rendered height is the number of inches asked for
    whatever the figure dpi (logo spec §3.3).

    Parameters
    ----------
    target : matplotlib.figure.Figure or matplotlib.axes.Axes, optional
        What to brand, and what the position is relative to. ``None`` takes the
        current figure.
    form : str, optional
        Which mark to draw: ``"lockup"``, ``"stacked"`` or ``"icon"``.
    size : str or float, optional
        A preset, ``"small"`` or ``"large"``, or an explicit height in inches.
    theme : str, optional
        Which variant to draw: ``"auto"``, ``"light"`` or ``"dark"``. The name is
        the *background* the logo is drawn on, so ``"dark"`` is the variant for a
        dark background. ``"auto"`` reads the target's facecolor.
    loc : str or tuple of float, optional
        A ``legend`` placement string, or an ``(x, y)`` pair in the target's
        fraction coordinates giving the logo's lower-left corner.
    pad : float, optional
        Points between the logo and the target's edge, ignored when `loc` is a
        pair. ``None`` takes ``LOGO_PAD``.
    zorder : float, optional
        Draw order. ``None`` takes ``LOGO_ZORDER``, which is above lines, text
        and legends.
    **kwargs : Any
        Passed through to :class:`matplotlib.offsetbox.OffsetImage`: ``alpha``,
        ``filternorm``, ``filterrad``, ``interpolation`` and ``resample``.

    Returns
    -------
    matplotlib.offsetbox.AnnotationBbox
        The artist, already added to the target, for restyling or removal.

    Raises
    ------
    TypeError
        If `target` is neither a figure nor an axes, if `loc` is neither a
        placement string nor a pair of floats, or if a keyword is not an
        ``OffsetImage`` option.
    ValueError
        If `form`, `size`, `theme` or `loc` names something that does not exist,
        if `size` is not a positive finite height, or if a `loc` pair holds a
        non-finite coordinate.
    """
    figure, axes = _resolve_target(target)
    height = _resolve_size(size, form)
    variant = _resolve_theme(theme, figure, axes)
    anchor, alignment, offset = _resolve_loc(
        loc, LOGO_PAD if pad is None else float(pad)
    )
    options = _image_options(kwargs)
    image = _load_master(form, variant)
    artist = AnnotationBbox(
        OffsetImage(image, zoom=height * POINTS_PER_INCH / image.shape[0], **options),
        xy=anchor,
        xycoords="axes fraction" if axes is not None else "figure fraction",
        xybox=offset,
        boxcoords="offset points",
        box_alignment=alignment,
        frameon=False,
        # Mandatory: the AnnotationBbox default of 0.4 font-size units adds a
        # constant 0.111 in to the rendered box at the 10 pt default font.
        pad=0.0,
        zorder=LOGO_ZORDER if zorder is None else float(zorder),
        annotation_clip=False,
    )
    owner: Figure | Axes = figure if axes is None else axes
    owner.add_artist(artist)
    return artist
