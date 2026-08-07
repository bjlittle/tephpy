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


def _autoload_config() -> None:
    """Apply the discovered configuration file, if there is one.

    A configuration file that cannot be read must not stop the import: that
    would also take out ``tephpy config path``, which is the tool for
    finding out which file is at fault. Any failure therefore warns and
    leaves the configuration pristine (configfile spec §5).
    """
    import warnings  # noqa: PLC0415 -- avoids a public tephpy.warnings attribute

    try:
        config.load()
    except exceptions.TephpyConfigError as exc:
        config.reset()
        warnings.warn(
            f"ignoring the configuration file: {exc}",
            exceptions.TephpyConfigWarning,
            stacklevel=2,
        )


_autoload_config()
