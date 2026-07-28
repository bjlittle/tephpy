# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Plot and analyse tephigrams.

``tephpy`` renders tephigrams on a rotated temperature-entropy coordinate
system and delegates thermodynamic analysis to MetPy.
"""

from __future__ import annotations

try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

from tephpy import calc, exceptions, io, plotting, transforms
from tephpy._config import config
from tephpy.sounding import Sounding

__all__ = [
    "Sounding",
    "__version__",
    "calc",
    "config",
    "exceptions",
    "io",
    "plotting",
    "transforms",
]
