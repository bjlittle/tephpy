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
from typing import TYPE_CHECKING, Final

import matplotlib.image as mimage

if TYPE_CHECKING:
    from typing import Any

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


@cache
def _load_master(form: str, variant: str) -> npt.NDArray[np.floating[Any]]:
    """Read one packaged master, decoded once and shared thereafter.

    The array is marked read-only because every figure drawing that variant
    holds the same object (logo spec §3.6).

    Parameters
    ----------
    form : str
        Which mark: a key of the first element of ``_MASTERS``.
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
