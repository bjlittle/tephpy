# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Persistence for ``tephpy.config`` (configfile spec §3).

Discovery, parsing and rendering of the YAML configuration file. This module
owns everything about the file; ``_config`` owns only the shape of the
configuration and its lifecycle. Nothing here imports ``tephpy.plotting``, so
reading a configuration file cannot pull in matplotlib figure machinery.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

import platformdirs

from tephpy.exceptions import TephpyConfigError

__all__ = [
    "CONFIG_ENV_VAR",
    "CONFIG_FILENAME",
    "config_paths",
    "discover",
    "user_config_path",
]

#: The configuration file's name in the working directory and the user
#: configuration directory (configfile spec §3.2).
CONFIG_FILENAME: Final[str] = "tephpyrc.yaml"

#: The environment variable naming a configuration file outright.
CONFIG_ENV_VAR: Final[str] = "TEPHPYRC"


def user_config_path() -> Path:
    """Return the configuration file in the user's configuration directory.

    Returns
    -------
    pathlib.Path
        The platform's user configuration directory for tephpy, with the
        configuration file name appended. The directory need not exist.
    """
    return Path(platformdirs.user_config_dir("tephpy")) / CONFIG_FILENAME


def config_paths() -> tuple[Path, ...]:
    """Return the discovery cascade, in precedence order (configfile spec §3.2).

    Returns
    -------
    tuple of pathlib.Path
        ``$TEPHPYRC`` when set, then the working directory, then the user
        configuration directory. The entries need not exist.
    """
    paths: list[Path] = []
    named = os.environ.get(CONFIG_ENV_VAR)
    if named:
        paths.append(Path(named))
    paths.append(Path.cwd() / CONFIG_FILENAME)
    paths.append(user_config_path())
    return tuple(paths)


def discover() -> Path | None:
    """Find the configuration file in force.

    Returns
    -------
    pathlib.Path or None
        The first cascade entry that is a file, or ``None`` when there is
        none — running on the hardwired conventions is normal, not an error.

    Raises
    ------
    TephpyConfigError
        If ``$TEPHPYRC`` is set but does not name a file. Falling through
        would silently ignore an explicit instruction.
    """
    named = os.environ.get(CONFIG_ENV_VAR)
    if named and not Path(named).is_file():
        msg = (
            f"{CONFIG_ENV_VAR} names {named!r}, which is not a file; unset "
            f"{CONFIG_ENV_VAR} to fall back to the {CONFIG_FILENAME} search"
        )
        raise TephpyConfigError(msg)
    for path in config_paths():
        if path.is_file():
            return path
    return None
