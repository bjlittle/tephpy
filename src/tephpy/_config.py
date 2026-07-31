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
from typing import TYPE_CHECKING, Final

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

#: A diagram extent: ((pressure, temperature), (pressure, temperature))
#: corners in hPa / degrees Celsius.
Extent = tuple[tuple[float, float], tuple[float, float]]


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
    #: bare string or together as a tuple. Listed edges label the members that
    #: reach them; every member left over is labelled inline (spec §3.2).
    labels: bool | str | tuple[str, ...] | None = None

    #: Whether the family is drawn at all.
    visible: bool | None = None

    #: Members drawn with a distinguishing style, keyed by member value in the
    #: family's native units. Each value is a mapping of style overrides --
    #: ``color``, ``linewidth``, ``linestyle`` and ``alpha`` -- and an omitted
    #: key falls back to the family's own style, so ``{0.0: {}}`` is the 0 °C
    #: member at ``EMPHASIS_LINEWIDTH`` in the family's own colour. An emphasised
    #: member is always drawn, whatever the zoom ladder would select. An empty
    #: mapping emphasises nothing (spec §3.2).
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
