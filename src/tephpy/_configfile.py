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

from collections.abc import Callable, Mapping
import dataclasses
import os
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, get_type_hints
import warnings

import platformdirs
import yaml

from tephpy._constants import CONFIG_DEFAULTS
from tephpy.exceptions import TephpyConfigError, TephpyConfigWarning

if TYPE_CHECKING:
    from tephpy._config import Config

__all__ = [
    "CONFIG_DESCRIPTIONS",
    "CONFIG_ENV_VAR",
    "CONFIG_FILENAME",
    "apply",
    "coerce",
    "config_paths",
    "discover",
    "read_document",
    "render_template",
    "user_config_path",
    "write_config",
    "write_template",
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

    Raises
    ------
    TephpyConfigError
        If the current working directory no longer exists, so the failure
        surfaces the same way every other unreadable-configuration case
        does, instead of an uncontained ``FileNotFoundError`` reaching
        ``import tephpy`` (configfile spec §5).
    """
    paths: list[Path] = []
    named = os.environ.get(CONFIG_ENV_VAR)
    if named:
        paths.append(Path(named))
    try:
        cwd = Path.cwd()
    except FileNotFoundError as exc:
        msg = f"cannot read the working directory to look for {CONFIG_FILENAME}: {exc}"
        raise TephpyConfigError(msg) from exc
    paths.append(cwd / CONFIG_FILENAME)
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


#: Options whose value is a colour, and so can be swallowed by YAML's comment
#: syntax when written as an unquoted hex triplet (configfile spec §5). Only
#: these earn the quoting hint on a null value: the template instructs the
#: reader to uncomment ``# emphasis:``, ``# values:`` and ``# interval:``, and
#: a hint about colour quoting is noise for all three.
_COLOR_OPTIONS: Final[frozenset[str]] = frozenset({"color"})


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
        If the file cannot be read, is not valid YAML, holds a scalar
        PyYAML cannot construct, or holds anything other than a mapping at
        the top level.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        msg = f"{path}: cannot read the configuration file: {exc}"
        raise TephpyConfigError(msg) from exc
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        msg = f"{path}: not valid YAML: {exc}"
        raise TephpyConfigError(msg) from exc
    except ValueError as exc:
        # PyYAML builds Python objects while parsing, and a resolver can
        # match a scalar its constructor then rejects: `2026-13-01` is a
        # timestamp right up until datetime.date sees the month. That is a
        # ValueError, not a YAMLError, so it would otherwise escape every
        # guard and stop the import (configfile spec §5).
        msg = f"{path}: cannot make sense of a value: {exc}"
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


class _MismatchError(Exception):
    """A configuration value does not match the type its option declares.

    Carries no message of its own. The section, the option and the expected
    type are known to :func:`coerce` and not to the converter that raises,
    so composing the text here would mean threading all three through every
    converter (configfile spec §5.2).
    """


def _as_string(value: object) -> str:
    """Check a value is a string.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    str
        The value, unchanged.

    Raises
    ------
    _MismatchError
        If the value is not a string.
    """
    if not isinstance(value, str):
        raise _MismatchError
    return value


def _as_number(value: object) -> float:
    """Check a value is a number, and convert it to a float.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    float
        The value as a float, so ``linewidth: 1`` and ``linewidth: 1.0``
        reach the configuration as the same thing.

    Raises
    ------
    _MismatchError
        If the value is not a number. ``bool`` is excluded explicitly:
        ``isinstance(True, int)`` is ``True`` in Python, which is how
        ``linewidth: true`` came to draw a 1 pt line (configfile spec §5.2).
    """
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _MismatchError
    return float(value)


def _as_flag(value: object) -> bool:
    """Check a value is a boolean.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    bool
        The value, unchanged.

    Raises
    ------
    _MismatchError
        If the value is not a boolean. YAML 1.1 spells more things
        ``bool`` than Python does: ``yes``, ``no``, ``on`` and ``off``
        all arrive here already converted.
    """
    if not isinstance(value, bool):
        raise _MismatchError
    return value


def _as_string_tuple(value: object) -> tuple[str, ...]:
    """Check a value is a list of strings, and convert it to a tuple.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    tuple of str
        The list as a tuple (configfile spec §3.3).

    Raises
    ------
    _MismatchError
        If the value is not a list, or any entry is not a string.
    """
    if not isinstance(value, list) or not all(
        isinstance(entry, str) for entry in value
    ):
        raise _MismatchError
    return tuple(value)


def _as_labels(value: object) -> bool | str | tuple[str, ...]:
    """Check a value is a labels setting, and convert any list to a tuple.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    bool or str or tuple of str
        The value, with a list of edge names as a tuple.

    Raises
    ------
    _MismatchError
        If the value is neither a boolean, nor a string, nor a list of
        strings.
    """
    if isinstance(value, bool | str):
        return value
    return _as_string_tuple(value)


def _as_number_tuple(value: object) -> tuple[float, ...]:
    """Check a value is a list of numbers, and convert it to a tuple of floats.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    tuple of float
        The list as a tuple of floats (configfile spec §3.3).

    Raises
    ------
    _MismatchError
        If the value is not a list, or any entry is not a number. A bare
        string is the case worth naming: iterating it would otherwise
        yield one member per character.
    """
    if not isinstance(value, list):
        raise _MismatchError
    return tuple(_as_number(entry) for entry in value)


def _as_corner(value: object) -> tuple[float, float]:
    """Check a value is one [pressure, temperature] corner.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    tuple of float
        The corner as a two-tuple of floats.

    Raises
    ------
    _MismatchError
        If the value is not a list of exactly two numbers.
    """
    if not isinstance(value, list) or len(value) != 2:
        raise _MismatchError
    first, second = value
    return (_as_number(first), _as_number(second))


def _as_extent(value: object) -> tuple[tuple[float, float], tuple[float, float]]:
    """Check a value is two [pressure, temperature] corners.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    tuple of tuple of float
        The extent as nested tuples of floats (configfile spec §3.3).

    Raises
    ------
    _MismatchError
        If the value is not a list of exactly two corners.
    """
    if not isinstance(value, list) or len(value) != 2:
        raise _MismatchError
    first, second = value
    return (_as_corner(first), _as_corner(second))


def _as_emphasis(value: object) -> dict[float, dict[str, object]]:
    """Check a value is an emphasis mapping, and convert its keys to floats.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    dict
        Member value to style overrides, keyed by float so ``850`` and
        ``850.0`` are not two different members (configfile spec §3.3).

    Raises
    ------
    _MismatchError
        If the value is not a mapping, or a member is not a number, or a
        style is not a mapping keyed by strings. The style *values* are
        annotated ``object`` and so are not checked at all
        (configfile spec §5.2).
    """
    if not isinstance(value, Mapping):
        raise _MismatchError
    emphasis: dict[float, dict[str, object]] = {}
    for member, style in value.items():
        if not isinstance(style, Mapping) or not all(
            isinstance(key, str) for key in style
        ):
            raise _MismatchError
        emphasis[_as_number(member)] = dict(style)
    return emphasis


#: One ``(description, converter)`` per distinct annotation in ``Config``:
#: eight entries covering all 42 options. The keys are evaluated
#: annotations, which compare equal to the ones ``typing.get_type_hints``
#: returns for ``_config``'s dataclasses — so the expected types are read
#: from the declarations rather than written out a second time. Each
#: converter both checks and converts, which makes it the natural home for the
#: configfile spec §3.3 coercions rather than a second pass over the same value
#: (configfile spec §5.2).
_TYPE_VALIDATORS: Final[Mapping[object, tuple[str, Callable[[object], object]]]] = (
    MappingProxyType(
        {
            str | None: ("a string", _as_string),
            float | None: ("a number", _as_number),
            bool | None: ("true or false", _as_flag),
            bool | str | tuple[str, ...] | None: (
                "true, false, an edge name, or a list of edge names",
                _as_labels,
            ),
            tuple[float, ...] | None: ("a list of numbers", _as_number_tuple),
            tuple[str, ...] | None: ("a list of strings", _as_string_tuple),
            tuple[tuple[float, float], tuple[float, float]] | None: (
                "two [pressure, temperature] corners",
                _as_extent,
            ),
            Mapping[float, Mapping[str, object]] | None: (
                "a mapping of member value to style overrides",
                _as_emphasis,
            ),
        }
    )
)


def _describe(value: object) -> str:
    """Name a value as the reader of the file would.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    str
        The value described in the vocabulary of the YAML file being
        edited rather than of the annotation behind it — the reader has
        never seen ``float`` (configfile spec §5.2). ``bool`` is tested
        first because it is also an ``int``.
    """
    if isinstance(value, bool):
        return f"the boolean {str(value).lower()}"
    if isinstance(value, str):
        return f"the string {value!r}"
    if isinstance(value, int | float):
        return f"the number {value!r}"
    return repr(value)


def _option_hints(section_type: type[object]) -> Mapping[str, object]:
    """Return each option's declared type for a configuration section.

    Parameters
    ----------
    section_type : type
        A section dataclass, as ``type(config.isotherms)`` gives it.

    Returns
    -------
    mapping
        Option name to the annotation ``_config`` declares for it.
        ``get_type_hints`` evaluates the strings that ``from __future__
        import annotations`` leaves behind, in the namespace of the module
        that defined the class — which is how this module reads
        ``_config``'s types without importing it and reversing the
        dependency arrow (configfile spec §3).
    """
    return MappingProxyType(get_type_hints(section_type))


def coerce(section: str, option: str, value: object, annotation: object) -> object:
    """Check a parsed YAML value against its declared type, and convert it.

    Parameters
    ----------
    section : str
        The configuration section the option belongs to.
    option : str
        The option name.
    value : object
        The value as ``yaml.safe_load`` produced it.
    annotation : object
        The type ``_config`` declares for the option, as
        :func:`_option_hints` returns it.

    Returns
    -------
    object
        The value in the type ``tephpy.config`` holds (configfile spec §3.3). An
        annotation with no validator is returned untouched rather than rejected:
        adding an option must not be able to stop an import, and the
        completeness gate in ``tests/test_configfile.py`` is what reports the
        gap instead (configfile spec §5.2).

    Raises
    ------
    TephpyConfigError
        If the value does not match the declared type. The message is a
        noun phrase — ``isotherms.linewidth, which expects a number, not
        the string 'thick'`` — so that :func:`apply` can lead with the
        file and the word "ignoring" and have the whole read as one
        sentence.
    """
    validator = _TYPE_VALIDATORS.get(annotation)
    if validator is None:
        return value
    description, convert = validator
    try:
        return convert(value)
    except _MismatchError:
        msg = f"{section}.{option}, which expects {description}, not {_describe(value)}"
        raise TephpyConfigError(msg) from None


#: Every file in the tephpy package, with the trailing separator that stops
#: the prefix also matching a sibling ``tephpy_extras`` — matching is a plain
#: string compare (configfile spec §5.1).
_PACKAGE_ROOT: Final[str] = str(Path(__file__).parent) + os.sep


def _warn_from_caller(message: str) -> None:
    """Warn about the configuration file, blaming the user's own frame.

    ``skip_file_prefixes`` walks outwards to the first frame outside the
    tephpy package, so the warning names the user's ``config.load(...)`` or
    ``import tephpy`` line however deep inside tephpy it was raised.
    ``stacklevel`` cannot: ``apply`` is reached at four different depths,
    and the import path sits behind importlib's frozen bootstrap frames,
    which no fixed count reaches (configfile spec §5.1).

    Parameters
    ----------
    message : str
        The warning text.

    Warns
    -----
    TephpyConfigWarning
        Always. The caller has already decided the situation warrants it.
    """
    warnings.warn(message, TephpyConfigWarning, skip_file_prefixes=(_PACKAGE_ROOT,))


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
        If an option is unknown, its value is an explicit null, or its
        value does not match the type the option declares.
    """
    prefix = f"{source}: " if source is not None else ""
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
        hints = _option_hints(type(section))
        for option, value in options.items():
            if option not in valid:
                _warn_from_caller(
                    f"{prefix}ignoring unknown option {option!r} in "
                    f"configuration section {name!r}; expected one of "
                    f"{sorted(valid)}"
                )
                continue
            if value is None:
                hint = (
                    "; an unquoted '#' colour is read as a comment, so quote "
                    "it as '#b0b0b0' if that is what happened"
                    if option in _COLOR_OPTIONS
                    else ""
                )
                _warn_from_caller(
                    f"{prefix}ignoring {name}.{option}, whose value is null{hint}"
                )
                continue
            try:
                setattr(section, option, coerce(name, option, value, hints[option]))
            except TephpyConfigError as exc:
                _warn_from_caller(f"{prefix}ignoring {exc}")
    config._source = source  # noqa: SLF001 -- the property behind Config.source


#: Prose shared by the ``color``, ``linewidth``, ``alpha``, ``labels`` and
#: ``visible`` options, which mean the same thing for every isopleth family.
_LINE_DESCRIPTIONS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "color": "Matplotlib colour for the lines and their labels.",
        "linewidth": "Line width in points.",
        "alpha": "Line and label opacity, 0 to 1.",
        "labels": (
            "true, false, or the diagram edges to label - bottom, top, "
            "left, right - singly or as a list."
        ),
        "visible": "Whether the family is drawn at all.",
    }
)

#: One line of prose per option, rendered above it in the generated template
#: (configfile spec §3.4). Gated for completeness against ``CONFIG_DEFAULTS``
#: by ``tests/test_configfile_template.py``.
#:
#: ``color``, ``linewidth``, ``alpha``, ``labels`` and ``visible`` mean the
#: same thing for every isopleth family, so ``_LINE_DESCRIPTIONS`` supplies
#: each of those five strings once. ``emphasis``, ``values`` and ``interval``
#: are not shared: the units differ per family -- hPa for isobars, degrees
#: Celsius for the temperature families, g/kg for mixing ratios -- so each
#: family spells its own out.
CONFIG_DESCRIPTIONS: Final[Mapping[str, Mapping[str, str]]] = MappingProxyType(
    {
        "isotherms": MappingProxyType(
            {
                **_LINE_DESCRIPTIONS,
                "emphasis": (
                    "Members drawn with a distinguishing style, keyed by "
                    "temperature in degrees Celsius."
                ),
                "values": (
                    "Explicit member temperatures in degrees Celsius. Unset, "
                    "the zoom-adaptive ladder selects them."
                ),
                "interval": (
                    "Member spacing in degrees Celsius. Unset, the "
                    "zoom-adaptive ladder selects it."
                ),
            }
        ),
        "isobars": MappingProxyType(
            {
                **_LINE_DESCRIPTIONS,
                "emphasis": (
                    "Members drawn with a distinguishing style, keyed by "
                    "pressure in hPa."
                ),
                "values": (
                    "Explicit member pressures in hPa. Unset, the "
                    "zoom-adaptive ladder selects them."
                ),
                "interval": (
                    "Member spacing in hPa. Unset, the zoom-adaptive ladder selects it."
                ),
            }
        ),
        "dry_adiabats": MappingProxyType(
            {
                **_LINE_DESCRIPTIONS,
                "emphasis": (
                    "Members drawn with a distinguishing style, keyed by "
                    "potential temperature in degrees Celsius."
                ),
                "values": (
                    "Explicit member potential temperatures in degrees "
                    "Celsius. Unset, the zoom-adaptive ladder selects them."
                ),
                "interval": (
                    "Member spacing in degrees Celsius. Unset, the "
                    "zoom-adaptive ladder selects it."
                ),
            }
        ),
        "moist_adiabats": MappingProxyType(
            {
                **_LINE_DESCRIPTIONS,
                "emphasis": (
                    "Members drawn with a distinguishing style, keyed by "
                    "wet-bulb potential temperature in degrees Celsius."
                ),
                "values": (
                    "Explicit member wet-bulb potential temperatures in "
                    "degrees Celsius. Unset, the zoom-adaptive ladder "
                    "selects them."
                ),
                "interval": (
                    "Member spacing in degrees Celsius. Unset, the "
                    "zoom-adaptive ladder selects it."
                ),
                "truncation": (
                    "Temperature in degrees Celsius below which a moist "
                    "adiabat stops being drawn."
                ),
            }
        ),
        "mixing_ratios": MappingProxyType(
            {
                **_LINE_DESCRIPTIONS,
                "emphasis": (
                    "Members drawn with a distinguishing style, keyed by "
                    "mixing ratio in g/kg."
                ),
                "values": (
                    "Explicit member mixing ratios in g/kg. Unset, the "
                    "zoom-adaptive ladder selects them."
                ),
            }
        ),
        "diagram": MappingProxyType(
            {
                "extent": (
                    "Default view corners as [[pressure, temperature], "
                    "[pressure, temperature]], in hPa and degrees Celsius."
                ),
            }
        ),
        "cursor": MappingProxyType(
            {
                "fields": "Cursor readout fields, in display order.",
            }
        ),
    }
)


def _as_sequences(value: object) -> object:
    """Rebuild a configuration value in the types ``yaml.safe_dump`` knows.

    Parameters
    ----------
    value : object
        A configuration value, possibly nesting mappings and tuples.

    Returns
    -------
    object
        The same value as plain ``dict`` and ``list`` throughout. Of the
        containers, PyYAML's safe representer knows ``dict``, ``list`` and
        ``tuple`` and nothing else, so any other mapping — ``emphasis`` is
        annotated ``Mapping``, and ``extent`` nests two deep — would reach
        ``RepresenterError``. The ``tuple`` arm is therefore not redundant:
        it is what recurses into a tuple's entries, where such a mapping
        could sit.
    """
    if isinstance(value, tuple | list):
        return [_as_sequences(entry) for entry in value]
    if isinstance(value, Mapping):
        return {key: _as_sequences(entry) for key, entry in value.items()}
    return value


def _format_default(value: object) -> str:
    """Render a default as the YAML a user can uncomment.

    Parameters
    ----------
    value : object
        The default from ``CONFIG_DEFAULTS``.

    Returns
    -------
    str
        The value in YAML flow style, or the empty string for an option
        with no default and for an empty ``emphasis`` mapping.
    """
    if value is None or value == {}:
        return ""
    rendered = yaml.safe_dump(_as_sequences(value), default_flow_style=True).strip()
    # A scalar document is dumped with an explicit "..." end marker.
    if rendered.endswith("..."):
        rendered = rendered[: -len("...")].strip()
    return rendered


def _write(path: Path, text: str) -> None:
    """Write text to a file, creating its parent directory.

    Parameters
    ----------
    path : pathlib.Path
        The file to write.
    text : str
        The content.

    Raises
    ------
    TephpyConfigError
        If the file cannot be written.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        msg = f"{path}: cannot write the configuration file: {exc}"
        raise TephpyConfigError(msg) from exc


def render_template() -> str:
    """Render the fully-commented configuration template.

    Returns
    -------
    str
        A YAML document whose section headers are live and whose every
        option is commented out, so an untouched template parses to an
        empty configuration (configfile spec §5).
    """
    lines = [
        "# tephpy configuration file.",
        "#",
        "# Every option below is commented out and shows the default in force.",
        "# Uncomment a line and edit it to change that option; leave the rest",
        "# alone. Quote any colour written as a hex triplet - an unquoted",
        "# '#b0b0b0' is read as a comment, not a colour.",
        "#",
        "# Discovery, first match wins: $TEPHPYRC, then ./tephpyrc.yaml, then",
        "# the user configuration directory. 'tephpy config path' reports the",
        "# whole search, and which file is in force.",
    ]
    for section, options in CONFIG_DEFAULTS.items():
        lines.append("")
        lines.append(f"{section}:")
        for option, default in options.items():
            lines.append(f"  # {CONFIG_DESCRIPTIONS[section][option]}")
            lines.append(f"  # {option}: {_format_default(default)}".rstrip())
    return "\n".join(lines) + "\n"


def write_template(path: Path, *, force: bool = False) -> None:
    """Write the configuration template.

    Parameters
    ----------
    path : pathlib.Path
        The file to write. Its parent directory is created if absent.
    force : bool, optional
        Overwrite an existing file. Default is ``False``.

    Raises
    ------
    TephpyConfigError
        If the file exists and `force` is false, or it cannot be written.
    """
    if path.exists() and not force:
        msg = f"{path} already exists; pass --force to overwrite it"
        raise TephpyConfigError(msg)
    _write(path, render_template())


def write_config(config: Config, path: Path) -> None:
    """Write a configuration's set options to a file.

    Parameters
    ----------
    config : Config
        The configuration to serialise.
    path : pathlib.Path
        The file to write. Its parent directory is created if absent.

    Raises
    ------
    TephpyConfigError
        If a value cannot be serialised, or the file cannot be written.
        Nothing is written in the first case: the value has to survive
        ``yaml.safe_dump`` before any existing file is touched.
    """
    document: dict[str, object] = {}
    for field in dataclasses.fields(config):
        section = getattr(config, field.name)
        options = {
            option.name: _as_sequences(getattr(section, option.name))
            for option in dataclasses.fields(section)
            if getattr(section, option.name) is not None
        }
        if options:
            document[field.name] = options
    try:
        text = yaml.safe_dump(document, default_flow_style=False, sort_keys=False)
    except yaml.YAMLError as exc:
        # A numpy scalar is the likely arrival: config values come out of
        # arrays as readily as out of literals, and the safe representer
        # covers only the builtin types.
        msg = f"{path}: cannot serialise the configuration: {exc}"
        raise TephpyConfigError(msg) from exc
    _write(path, text)
