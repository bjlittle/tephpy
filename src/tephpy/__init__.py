# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Plot and analyse tephigrams.

``tephpy`` renders tephigrams on a rotated temperature-entropy coordinate
system and delegates thermodynamic analysis to MetPy.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

from tephpy import calc, exceptions, io, plotting, samples, transforms
from tephpy._config import config
from tephpy._configfile import _warn_from_caller
from tephpy.sounding import Sounding

__all__ = [
    "Sounding",
    "__version__",
    "calc",
    "config",
    "exceptions",
    "io",
    "plotting",
    "samples",
    "transforms",
]


def _autoload_config() -> None:
    """Apply the discovered configuration file, if there is one.

    A configuration file that cannot be read must not stop the import: that
    would also take out ``tephpy config path``, which is the tool for
    finding out which file is at fault. Any failure therefore warns and
    leaves the configuration pristine (configfile spec §5).

    Notes
    -----
    Warning is only half of that guarantee. Under ``-W error`` (or
    ``PYTHONWARNINGS=error``) a warning *is* an exception, so a typo'd
    option key — the likeliest mistake in a configuration file — would kill
    the import just as surely as raising. The ``catch_warnings`` block
    forces tephpy's own configuration warnings to "always" for the duration
    of the auto-load, which makes them shown and never raised, and leaves
    every other warning category on the user's own setting. It has to span
    the ``_warn_from_caller`` call below as well as ``config.load``: that
    call is on the very failure path this function exists to survive.
    """
    import warnings  # noqa: PLC0415 -- avoids a public tephpy.warnings attribute

    with warnings.catch_warnings():
        warnings.filterwarnings("always", category=exceptions.TephpyConfigWarning)
        try:
            config.load()
        except exceptions.TephpyConfigError as exc:
            config.reset()
            _warn_from_caller(f"ignoring the configuration file: {exc}")


_autoload_config()
