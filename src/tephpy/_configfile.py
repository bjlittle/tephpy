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
import datetime
import inspect
import os
from pathlib import Path
import textwrap
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, cast, get_type_hints
import warnings

import platformdirs
import yaml

from tephpy._constants import CONFIG_DEFAULTS
from tephpy.exceptions import TephpyConfigError, TephpyConfigWarning

if TYPE_CHECKING:
    from tephpy._config import Config

__all__ = [
    "CONFIG_DESCRIPTIONS",
    "CONFIG_DETAILS",
    "CONFIG_ENV_VAR",
    "CONFIG_FILENAME",
    "apply",
    "coerce",
    "config_paths",
    "discover",
    "read_document",
    "render_reference",
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


def _named_path() -> Path | None:
    """Return the path ``$TEPHPYRC`` names, if it names one.

    Returns
    -------
    pathlib.Path or None
        The path the environment variable names, or ``None`` when it is unset
        or empty. Both entry points to the discovery cascade take their answer
        from here, so the environment is read once per call: the file
        ``discover`` checks for existence is then necessarily the file it
        returns (configfile spec §3.2).
    """
    named = os.environ.get(CONFIG_ENV_VAR)
    return Path(named) if named else None


def _cascade(named: Path | None) -> tuple[Path, ...]:
    """Build the discovery cascade around an already-resolved ``$TEPHPYRC``.

    Parameters
    ----------
    named : pathlib.Path or None
        The path ``$TEPHPYRC`` names, as :func:`_named_path` resolved it, or
        ``None`` when it names none.

    Returns
    -------
    tuple of pathlib.Path
        The named path when there is one, then the working directory, then the
        user configuration directory. The entries need not exist: a caller
        reporting the search shows the absent ones too, so nothing here rejects
        a path for not being a file.

    Raises
    ------
    TephpyConfigError
        If the current working directory no longer exists, so the failure
        surfaces the same way every other unreadable-configuration case does,
        instead of an uncontained ``FileNotFoundError`` reaching
        ``import tephpy`` (configfile spec §5).
    """
    paths: list[Path] = []
    if named is not None:
        paths.append(named)
    try:
        cwd = Path.cwd()
    except FileNotFoundError as exc:
        msg = f"cannot read the working directory to look for {CONFIG_FILENAME}: {exc}"
        raise TephpyConfigError(msg) from exc
    paths.append(cwd / CONFIG_FILENAME)
    paths.append(user_config_path())
    return tuple(paths)


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
    return _cascade(_named_path())


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
    named = _named_path()
    if named is not None and not named.is_file():
        msg = (
            f"{CONFIG_ENV_VAR} names {str(named)!r}, which is not a file; unset "
            f"{CONFIG_ENV_VAR} to fall back to the {CONFIG_FILENAME} search"
        )
        raise TephpyConfigError(msg)
    for path in _cascade(named):
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

    Usually carries no message of its own. The section, the option and the
    expected type are known to :func:`coerce` and not to the converter that
    raises, so composing the text here would mean threading all three
    through every converter (configfile spec §5.2). The exception is a
    converter that knows something :func:`_describe` cannot see — an
    integer with no float to convert to is still a number, so describing it
    would say "expects a number, not the number" and print all 401 digits.
    Such a converter passes the noun phrase as the sole argument, and
    :func:`coerce` uses it in place of the description of the value.
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
        If the value is not a number, or is an integer with no float to
        convert to. ``bool`` is excluded explicitly: ``isinstance(True,
        int)`` is ``True`` in Python, which is how ``linewidth: true`` came
        to draw a 1 pt line (configfile spec §5.2).
    """
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _MismatchError
    try:
        return float(value)
    except OverflowError:
        # An integer of 309 or more digits is valid YAML and a valid Python
        # int, and only fails at the conversion. OverflowError is caught by
        # neither coerce nor apply nor the auto-load, so letting it escape
        # would make a typo'd zero stop `import tephpy` -- the one thing a
        # value check must never do (configfile spec §5.2).
        msg = "a number that large; the largest tephpy can hold is about 1.8e308"
        raise _MismatchError(msg) from None


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
        first because it is also an ``int``, and ``datetime.datetime`` is
        covered by the ``datetime.date`` arm because it is also a
        ``date``. What is left — a list or a mapping — a ``repr`` already
        renders as the file itself spells it.
    """
    if isinstance(value, bool):
        return f"the boolean {str(value).lower()}"
    if isinstance(value, str):
        return f"the string {value!r}"
    if isinstance(value, int | float):
        return f"the number {value!r}"
    if isinstance(value, datetime.date):
        # An unquoted `2026-01-01` matches YAML's timestamp resolver, so
        # `safe_load` hands over a date rather than a string; `str` spells
        # it the way the file did, where a `repr` would say
        # `datetime.date(2026, 1, 1)`.
        return f"the timestamp {value}"
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
    except _MismatchError as exc:
        found = str(exc) or _describe(value)
        msg = f"{section}.{option}, which expects {description}, not {found}"
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
        If a section is unknown or is not a mapping. The message leads with
        the file, as the option-level warnings do — a section-level problem
        discards the whole file, so it is the outcome that most needs to say
        which file (configfile spec §5.2).

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
                f"{prefix}unknown configuration section {name!r}; expected one of "
                f"{sorted(sections)}"
            )
            raise TephpyConfigError(msg)
        if options is None:
            # Every option commented out: the untouched state of a section
            # in a generated template (configfile spec §5).
            continue
        if not isinstance(options, Mapping):
            msg = (
                f"{prefix}configuration section {name!r} must hold a mapping of "
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

#: Detail shared by the ``labels`` and ``emphasis`` options, which behave the
#: same way for every isopleth family, as ``_LINE_DESCRIPTIONS`` above is.
#: Unlike the descriptions, this prose is unit-neutral: ``LineOptions`` is the
#: base for isobars in hPa and mixing ratios in g/kg as well as the temperature
#: families, so no example here names a unit.
_LINE_DETAILS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "labels": (
            "Listed edges label the members that reach them, and every member "
            "left over is labelled inline. ``true`` labels every member "
            "inline; ``false`` labels none."
        ),
        "emphasis": (
            "Each value is a mapping of style overrides -- ``color``, "
            "``linewidth``, ``linestyle`` and ``alpha`` -- and an omitted key "
            "falls back to the family's own style, so ``{20.0: {}}`` is the "
            "member at 20 in the family's own units, drawn at the emphasis "
            "line width in the family's own colour. An emphasised member is "
            "always drawn, whatever the zoom-adaptive ladder would otherwise "
            "select. An empty mapping emphasises nothing."
        ),
    }
)

#: The longer prose the options reference page has room for and the generated
#: template does not (configfile spec §3.6). Sparse: an option with nothing
#: more to say than its ``CONFIG_DESCRIPTIONS`` line is absent, and the gate in
#: ``tests/test_configfile_reference.py`` is a subset check against
#: ``CONFIG_DEFAULTS`` with its own membership pinned, not a completeness check.
CONFIG_DETAILS: Final[Mapping[str, Mapping[str, str]]] = MappingProxyType(
    {
        "isotherms": MappingProxyType(dict(_LINE_DETAILS)),
        "isobars": MappingProxyType(dict(_LINE_DETAILS)),
        "dry_adiabats": MappingProxyType(dict(_LINE_DETAILS)),
        "moist_adiabats": MappingProxyType(dict(_LINE_DETAILS)),
        "mixing_ratios": MappingProxyType(dict(_LINE_DETAILS)),
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


#: Width the generated template's comment lines are wrapped to, matching the
#: line length ruff holds this repository's own sources to. Value lines are not
#: wrapped: a wrapped YAML value would no longer be uncommentable, which is the
#: whole point of the template (configfile spec §3.6).
_TEMPLATE_WIDTH: Final[int] = 88


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
            lines.extend(
                textwrap.fill(
                    CONFIG_DESCRIPTIONS[section][option],
                    width=_TEMPLATE_WIDTH,
                    initial_indent="  # ",
                    subsequent_indent="  # ",
                ).splitlines()
            )
            lines.append(f"  # {option}: {_format_default(default)}".rstrip())
    return "\n".join(lines) + "\n"


#: Methods of ``tephpy.config`` given a target on the options reference page,
#: in the order a reader meets them. Thinner than the docstrings ``Config``
#: carries: numpydoc's docstring processing is an autodoc hook, and this
#: project renders its API with autoapi, so a full rendering here would be a
#: second, hand-maintained one (configfile spec §3.6, §9).
_REFERENCE_METHODS: Final[tuple[str, ...]] = ("load", "save", "reset", "context")


def _reference_signature(method: object) -> str:
    """Spell a method's parameters as the reference page shows them.

    Parameters
    ----------
    method : object
        An unbound method of ``Config``.

    Returns
    -------
    str
        The parameter list without enclosing parentheses, ``self`` dropped and
        annotations omitted. ``inspect.signature`` renders resolved annotations
        as quoted strings, which is noise on a page whose types come from
        elsewhere; name and default are what the reader needs.
    """
    signature = inspect.signature(cast("Callable[..., object]", method))
    parameters = list(signature.parameters.values())[1:]
    rendered = []
    for parameter in parameters:
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            rendered.append(f"**{parameter.name}")
        elif parameter.default is inspect.Parameter.empty:
            rendered.append(parameter.name)
        else:
            rendered.append(f"{parameter.name}={parameter.default!r}")
    return ", ".join(rendered)


def _reference_default(value: object) -> str:
    """Render a default as the reference page shows it.

    Parameters
    ----------
    value : object
        The default from ``CONFIG_DEFAULTS``.

    Returns
    -------
    str
        The value as inline literal YAML, or the word ``unset`` for an option
        with no default. ``_format_default`` renders both ``None`` and an empty
        mapping as the empty string, because the template needs a line a reader
        can uncomment; the page has no such constraint and distinguishes them.
    """
    if value is None:
        return "unset"
    return f"``{_format_default(value) or '{}'}``"


def render_reference(config: Config) -> str:
    """Render the options reference page as reStructuredText.

    Parameters
    ----------
    config : Config
        The live configuration, supplying each section's dataclass so the
        annotations can be evaluated. It is a parameter rather than an import
        because ``_config`` imports this module at module scope: passing the
        instance in is what keeps that arrow one-way (configfile spec §3.6).

    Returns
    -------
    str
        A section per configuration section, a ``py:attribute`` target per
        option and a ``py:method`` target per method in
        ``_REFERENCE_METHODS`` — the second rendering of the same tables the
        configuration template is rendered from, so a new option reaches both
        or neither.
    """
    lines = [
        ".. Generated by tephpy._configfile.render_reference from the tables in",
        ".. _configfile.py. Edit those, not this output (configfile spec §3.6).",
        "",
    ]
    for section, options in CONFIG_DEFAULTS.items():
        hints = _option_hints(type(getattr(config, section)))
        lines.append(section)
        lines.append("-" * len(section))
        lines.append("")
        for option, default in options.items():
            lines.append(f".. py:attribute:: tephpy.config.{section}.{option}")
            lines.append(f"   :type: {hints[option]!s}")
            lines.append("")
            lines.append(f"   {CONFIG_DESCRIPTIONS[section][option]}")
            detail = CONFIG_DETAILS.get(section, {}).get(option)
            if detail is not None:
                lines.append("")
                lines.append(f"   {detail}")
            lines.append("")
            lines.append(f"   Default: {_reference_default(default)}")
            lines.append("")
    lines.append("Methods")
    lines.append("-------")
    lines.append("")
    lines.append(
        "These entries exist so that prose can cross-reference them; "
        ":ref:`configure-from-a-file` is the how-to that explains when to reach "
        "for each."
    )
    lines.append("")
    for name in _REFERENCE_METHODS:
        method = getattr(type(config), name)
        lines.append(
            f".. py:method:: tephpy.config.{name}({_reference_signature(method)})"
        )
        lines.append("")
        lines.append(f"   {cast('str', inspect.getdoc(method)).splitlines()[0]}")
        lines.append("")
    return "\n".join(lines)


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
