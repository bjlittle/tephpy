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

from collections.abc import Mapping
import dataclasses
import os
from pathlib import Path
from typing import TYPE_CHECKING, Final
import warnings

import platformdirs
import yaml

from tephpy.exceptions import TephpyConfigError, TephpyConfigWarning

if TYPE_CHECKING:
    from tephpy._config import Config

__all__ = [
    "CONFIG_ENV_VAR",
    "CONFIG_FILENAME",
    "apply",
    "coerce",
    "config_paths",
    "discover",
    "read_document",
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


#: Options whose YAML sequence becomes a tuple of strings.
_STRING_TUPLES: Final[frozenset[str]] = frozenset({"labels", "fields"})

#: Options whose YAML sequence becomes a tuple of floats.
_FLOAT_TUPLES: Final[frozenset[str]] = frozenset({"values"})


def read_document(path: Path) -> dict[str, object]:
    """Parse a configuration file into a mapping of sections.

    Parameters
    ----------
    path : pathlib.Path
        The file to read.

    Returns
    -------
    dict
        The document's top-level mapping. A file that is empty or wholly
        commented out yields ``{}`` — that is how a freshly generated
        template reads, and it is an empty configuration, not an error
        (configfile spec §5).

    Raises
    ------
    TephpyConfigError
        If the file cannot be read, is not valid YAML, or holds anything
        other than a mapping at the top level.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"{path}: cannot read the configuration file: {exc}"
        raise TephpyConfigError(msg) from exc
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        msg = f"{path}: not valid YAML: {exc}"
        raise TephpyConfigError(msg) from exc
    if document is None:
        return {}
    if not isinstance(document, Mapping):
        msg = (
            f"{path}: a configuration file must hold a mapping of sections, "
            f"not {type(document).__name__}"
        )
        raise TephpyConfigError(msg)
    return dict(document)


def coerce(section: str, option: str, value: object) -> object:
    """Convert a parsed YAML value to what the configuration expects.

    Parameters
    ----------
    section : str
        The configuration section the option belongs to.
    option : str
        The option name.
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    object
        The value in the type ``tephpy.config`` holds
        (configfile spec §3.3).

    Raises
    ------
    TephpyConfigError
        If the value's shape cannot be converted.
    """
    try:
        if option == "extent":
            return tuple(
                tuple(float(number) for number in corner)
                for corner in value  # type: ignore[attr-defined]
            )
        if option == "emphasis":
            return {
                float(member): dict(style)
                for member, style in value.items()  # type: ignore[attr-defined]
            }
        if option in _FLOAT_TUPLES and isinstance(value, list):
            return tuple(float(number) for number in value)
        if option in _STRING_TUPLES and isinstance(value, list):
            return tuple(str(entry) for entry in value)
    except (AttributeError, TypeError, ValueError) as exc:
        msg = f"{section}.{option}: cannot make sense of {value!r}: {exc}"
        raise TephpyConfigError(msg) from exc
    return value


def apply(config: Config, document: Mapping[str, object], source: Path | None) -> None:
    """Apply a parsed configuration document to a configuration.

    Parameters
    ----------
    config : Config
        The configuration to write into, in place.
    document : mapping
        The parsed document, as :func:`read_document` returns it.
    source : pathlib.Path or None
        The file the document came from, recorded as ``config.source``.

    Raises
    ------
    TephpyConfigError
        If a section is unknown or is not a mapping.

    Warns
    -----
    TephpyConfigWarning
        If an option is unknown, or its value is an explicit null.
    """
    sections = {field.name for field in dataclasses.fields(config)}
    for name, options in document.items():
        if name not in sections:
            msg = (
                f"unknown configuration section {name!r}; expected one of "
                f"{sorted(sections)}"
            )
            raise TephpyConfigError(msg)
        if options is None:
            # Every option commented out: the untouched state of a section
            # in a generated template (configfile spec §5).
            continue
        if not isinstance(options, Mapping):
            msg = (
                f"configuration section {name!r} must hold a mapping of "
                f"options, not {type(options).__name__}"
            )
            raise TephpyConfigError(msg)
        section = getattr(config, name)
        valid = {field.name for field in dataclasses.fields(section)}
        for option, value in options.items():
            if option not in valid:
                warnings.warn(
                    f"ignoring unknown option {option!r} in configuration "
                    f"section {name!r}; expected one of {sorted(valid)}",
                    TephpyConfigWarning,
                    stacklevel=2,
                )
                continue
            if value is None:
                warnings.warn(
                    f"ignoring {name}.{option}, whose value is null; an "
                    f"unquoted '#' colour is read as a comment, so quote it "
                    f"as '#b0b0b0' if that is what happened",
                    TephpyConfigWarning,
                    stacklevel=2,
                )
                continue
            setattr(section, option, coerce(name, option, value))
    config._source = source  # noqa: SLF001 -- the property behind Config.source
