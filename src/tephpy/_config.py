# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Runtime configuration for tephpy (spec §3.5).

``tephpy.config`` is the mutable, typed runtime layer over the
``_constants`` conventions. Precedence: accessor kwargs > ``tephpy.config``
> ``_constants``. A ``None`` field means "fall through to the next tier".
Configuration is read when an isopleth family is created or reconfigured;
changing it does not retroactively restyle existing axes (matplotlib
rcParams semantics).
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
import dataclasses
from pathlib import Path
from typing import TYPE_CHECKING, Final

from tephpy import _configfile

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = [
    "Config",
    "CursorOptions",
    "DiagramOptions",
    "FamilyOptions",
    "LineOptions",
    "MixingRatioOptions",
    "MoistAdiabatOptions",
    "config",
]

#: A diagram extent: pressure and temperature ranges in hPa / degrees
#: Celsius, keyed ``"pressure"`` and ``"temperature"`` (framing spec §3.4).
Extent = Mapping[str, tuple[float, float]]


@dataclasses.dataclass
class LineOptions:
    """Style and visibility options common to every isopleth family.

    A ``None`` field falls through to the ``_constants`` convention default.
    """

    #: Matplotlib colour for the family's lines and labels.
    color: str | None = None

    #: Line width in points.
    linewidth: float | None = None

    #: Line and label alpha.
    alpha: float | None = None

    #: Whether member values are labelled, and where: ``True`` (every member
    #: labelled inline — the default), ``False`` (none), or the diagram edge
    #: names ``"bottom"``, ``"top"``, ``"left"`` and ``"right"``, singly as a
    #: bare string or together as a tuple. What each choice draws is
    #: specified in spec §3.2 and published from
    #: ``_configfile.CONFIG_DETAILS["<family>"]["labels"]`` (configfile spec §3.6).
    labels: bool | str | tuple[str, ...] | None = None

    #: Whether the family is drawn at all.
    visible: bool | None = None

    #: Members drawn with a distinguishing style, keyed by member value in the
    #: family's native units, each value a mapping of style overrides. An
    #: omitted key falls back to the family's own style, so an empty mapping
    #: draws the member at ``EMPHASIS_LINEWIDTH`` in the family's own colour,
    #: while a ``linewidth`` override replaces it. An emphasised member is
    #: always drawn, whatever the zoom-adaptive ladder would otherwise select.
    #: Spec §3.2 specifies the behaviour;
    #: ``_configfile.CONFIG_DETAILS["<family>"]["emphasis"]`` publishes it
    #: (configfile spec §3.6).
    emphasis: Mapping[float, Mapping[str, object]] | None = None


@dataclasses.dataclass
class FamilyOptions(LineOptions):
    """Options for an interval-based isopleth family.

    Setting `values` or `interval` fixes the member set explicitly and
    disables the zoom-adaptive selection ladder.
    """

    #: Explicit member values (diagram-native units).
    values: tuple[float, ...] | None = None

    #: Member value interval (diagram-native units).
    interval: float | None = None


@dataclasses.dataclass
class MixingRatioOptions(LineOptions):
    """Options for the humidity mixing-ratio family (values ladder only)."""

    #: Explicit member values in g/kg.
    values: tuple[float, ...] | None = None


@dataclasses.dataclass
class MoistAdiabatOptions(FamilyOptions):
    """Options for the moist-adiabat family."""

    #: Temperature (°C) below which moist adiabats are truncated.
    truncation: float | None = None


@dataclasses.dataclass
class DiagramOptions:
    """Diagram-wide options."""

    #: Default view extent applied to new tephigram axes.
    extent: Extent | None = None
    #: Default ``fit`` margin, as a fraction of the fitted span
    #: (framing spec §3.3).
    margin: float | None = None


@dataclasses.dataclass
class CursorOptions:
    """Options for the interactive cursor readout (spec §3.2)."""

    #: Readout fields in display order, naming entries in the
    #: ``TephigramAxes.format_coord`` registry; ``None`` falls through to
    #: the ``_constants.CURSOR_FIELDS`` convention.
    fields: tuple[str, ...] | None = None


@dataclasses.dataclass
class Config:
    """The ``tephpy.config`` runtime configuration singleton (spec §3.5).

    One typed section per isopleth family plus diagram-wide and cursor sections,
    e.g. ``config.isobars.interval``, ``config.diagram.extent``, or
    ``config.cursor.fields``. Use :meth:`context` for temporary overrides.
    """

    isotherms: FamilyOptions = dataclasses.field(default_factory=FamilyOptions)
    isobars: FamilyOptions = dataclasses.field(default_factory=FamilyOptions)
    dry_adiabats: FamilyOptions = dataclasses.field(default_factory=FamilyOptions)
    moist_adiabats: MoistAdiabatOptions = dataclasses.field(
        default_factory=MoistAdiabatOptions
    )
    mixing_ratios: MixingRatioOptions = dataclasses.field(
        default_factory=MixingRatioOptions
    )
    diagram: DiagramOptions = dataclasses.field(default_factory=DiagramOptions)
    cursor: CursorOptions = dataclasses.field(default_factory=CursorOptions)

    def __post_init__(self) -> None:
        """Initialise the state that is deliberately not a field.

        Notes
        -----
        ``_source`` is set here rather than declared as a class attribute
        because an annotated class attribute becomes a dataclass field, and
        :meth:`context` enumerates the configuration sections with
        ``dataclasses.fields`` — a field here would present ``source`` as an
        eighth section (configfile spec §3.1).
        """
        self._source: Path | None = None

    @property
    def source(self) -> Path | None:
        """The configuration file in force.

        Returns
        -------
        pathlib.Path or None
            The file this configuration was last *successfully* loaded from,
            or ``None`` if none has been. A failed :meth:`load` leaves this
            alone, along with the options it rolled back, so a rejected
            replacement leaves the file it replaced still named here.
            :meth:`reset` clears it.
        """
        return self._source

    def reset(self) -> None:
        """Restore the pristine, hardwired configuration.

        Every option in every section returns to ``None`` — falling through
        to the ``_constants`` conventions — and :attr:`source` becomes
        ``None``. The section objects are cleared in place rather than
        rebound, because an
        :class:`~tephpy.plotting.isopleths.IsoplethFamily` keeps a reference
        to the section it was created with.

        Notes
        -----
        .. versionadded:: 0.1.0

        """
        pristine = Config()
        for field in dataclasses.fields(self):
            section = getattr(self, field.name)
            fresh = getattr(pristine, field.name)
            for option in dataclasses.fields(fresh):
                setattr(section, option.name, getattr(fresh, option.name))
        self._source = None

    def load(self, path: str | Path | None = None) -> None:
        """Load a configuration file over this configuration.

        A file is applied all or nothing. ``_configfile.apply`` writes
        section by section and raises on the first unknown section, so a
        rejected file can otherwise leave options from its earlier sections
        behind; this method snapshots every section first and puts it back
        if the load raises. What is restored is the configuration as the
        caller had it, not the pristine one — anything set in Python before
        the call survives a rejected file (configfile spec §5).

        Parameters
        ----------
        path : str or pathlib.Path, optional
            The file to read. When omitted, the discovery cascade selects
            it, and nothing happens if the cascade finds no file.

        Raises
        ------
        TephpyConfigError
            If the file cannot be read, is not valid YAML, or names an
            unknown configuration section. An option-level problem — an
            unknown option, a null value, or a value of the wrong type —
            warns and is skipped instead (configfile spec §2, §5.2).
            :attr:`source` is left as it was, along with every section.

        Warns
        -----
        TephpyConfigWarning
            If an option is unknown, its value is an explicit null, or its
            value does not match the type the option declares. A caller who
            has filtered this category to an error gets that exception
            instead, and the same all-or-nothing restore.

        Notes
        -----
        .. versionadded:: 0.1.0

        """
        chosen = _configfile.discover() if path is None else Path(path)
        if chosen is None:
            return
        snapshots = {
            field.name: dataclasses.replace(getattr(self, field.name))
            for field in dataclasses.fields(self)
        }
        applied = False
        try:
            _configfile.apply(self, _configfile.read_document(chosen), source=chosen)
            applied = True
        finally:
            # Not `except TephpyConfigError`: under a filter that turns
            # TephpyConfigWarning into an error, an unknown option raises
            # the warning class instead, which is not a TephpyConfigError
            # and would carry an earlier valid option's mutation past this
            # handler. All-or-nothing has to mean every raise, not an
            # enumerated few.
            if not applied:
                for section_name, snapshot in snapshots.items():
                    section = getattr(self, section_name)
                    for field in dataclasses.fields(snapshot):
                        setattr(section, field.name, getattr(snapshot, field.name))

    def save(self, path: str | Path | None = None) -> Path:
        """Write the options set on this configuration to a file.

        Only options that were actually set are written; everything still
        falling through to the conventions is left out. Comments and key
        order in an existing file are **not** preserved — use
        ``tephpy config generate`` for the commented template
        (configfile spec §3.5).

        Parameters
        ----------
        path : str or pathlib.Path, optional
            Where to write. Defaults to the file in the user's
            configuration directory.

        Returns
        -------
        pathlib.Path
            The file written.

        Raises
        ------
        TephpyConfigError
            If a value cannot be serialised, or the file cannot be written.

        Notes
        -----
        .. versionadded:: 0.1.0

        """
        chosen = _configfile.user_config_path() if path is None else Path(path)
        _configfile.write_config(self, chosen)
        return chosen

    @contextmanager
    def context(self, **overrides: Mapping[str, object]) -> Iterator[Config]:
        """Temporarily override configuration sections.

        Parameters
        ----------
        **overrides : mapping of str to object
            Section names mapped to ``{option: value}`` overrides, e.g.
            ``config.context(isobars={"interval": 25.0})``.

        Yields
        ------
        Config
            This configuration, with the overrides applied; prior values
            are restored on exit, including on error.

        Raises
        ------
        TypeError
            If a section or option name is unknown, or if a section
            override is not a mapping.

        Notes
        -----
        .. versionadded:: 0.1.0

        """
        section_names = {field.name for field in dataclasses.fields(self)}
        snapshots: dict[str, object] = {}
        try:
            for section_name, options in overrides.items():
                if section_name not in section_names:
                    msg = f"unknown config section {section_name!r}"
                    raise TypeError(msg)
                if not isinstance(options, Mapping):
                    # The annotation promises a mapping, but unchecked
                    # callers can still pass anything (hence the guard).
                    msg = (  # type: ignore[unreachable]
                        f"override for config section {section_name!r} must "
                        "be a mapping of option names to values"
                    )
                    raise TypeError(msg)
                section = getattr(self, section_name)
                valid = {field.name for field in dataclasses.fields(section)}
                snapshots[section_name] = dataclasses.replace(section)
                for key, value in options.items():
                    if key not in valid:
                        msg = (
                            f"unknown option {key!r} for config section "
                            f"{section_name!r}"
                        )
                        raise TypeError(msg)
                    setattr(section, key, value)
            yield self
        finally:
            for section_name, snapshot in snapshots.items():
                section = getattr(self, section_name)
                for field in dataclasses.fields(snapshot):  # type: ignore[arg-type]
                    setattr(section, field.name, getattr(snapshot, field.name))


#: The singleton read by the isopleth families (spec §3.5).
config: Final[Config] = Config()
