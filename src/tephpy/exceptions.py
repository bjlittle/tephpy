# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The public tephpy exception hierarchy (spec §6).

Every exception tephpy raises for user-correctable input derives from
:class:`TephpyError`, so ``except TephpyError`` catches them all. Units
problems raise :class:`TephpyUnitsError`; physically impossible data raises
a :class:`TephpyValidationError` subclass carrying the offending level
indices. Validation happens at ingest (``Sounding`` construction), not
mid-plot.

Configuration-file problems are the one place tephpy also warns:
:class:`TephpyConfigWarning` is a ``UserWarning``, not a
:class:`TephpyError`, because an unusable configuration file degrades to
the hardwired defaults instead of stopping the import (configfile spec §5).
"""

from __future__ import annotations

__all__ = [
    "DewpointExceedsTemperatureError",
    "MissingDataError",
    "NonMonotonicPressureError",
    "ProfileTooShortError",
    "TephpyConfigError",
    "TephpyConfigWarning",
    "TephpyError",
    "TephpyIOError",
    "TephpyUnitsError",
    "TephpyValidationError",
]


class TephpyError(Exception):
    """Root of the tephpy exception hierarchy."""


class TephpyUnitsError(TephpyError):
    """Missing, ambiguous, unparsable, or wrong-dimension units (spec §5)."""


class TephpyValidationError(TephpyError):
    """Physically impossible input, identified by level indices (spec §6).

    Parameters
    ----------
    message : str
        Description of the failed validation.
    levels : tuple of int, optional
        Zero-based indices of the offending levels, when the failure is
        attributable to specific levels.

    Attributes
    ----------
    levels : tuple of int
        Zero-based indices of the offending levels; empty when the failure
        is not attributable to specific levels.
    """

    def __init__(self, message: str, *, levels: tuple[int, ...] = ()) -> None:
        """Store the message and the offending level indices.

        Parameters
        ----------
        message : str
            Description of the failed validation.
        levels : tuple of int, optional
            Zero-based indices of the offending levels.
        """
        super().__init__(message)
        self.levels = levels


class NonMonotonicPressureError(TephpyValidationError):
    """Pressure is not strictly monotonic (spec §3.4)."""


class DewpointExceedsTemperatureError(TephpyValidationError):
    """Dewpoint exceeds temperature at one or more levels (spec §3.4).

    Equality — saturation — is physical and accepted; only strict excess
    is rejected.
    """


class MissingDataError(TephpyValidationError):
    """The sounding lacks a field the requested operation needs (spec §6).

    Raised at the operation's boundary — the earliest point the need is
    knowable — e.g. parcel analysis without dewpoint, or (in a later
    release) wind barbs without wind.
    """


class TephpyIOError(TephpyError):
    """A reader could not fetch or make sense of its source (spec §6).

    Network failures, HTTP errors, the archive's "no data" replies, a
    malformed or unrecognisable file, and an ambiguous read (an IGRA
    station file holding many soundings with no ``time=`` selector) all
    raise this, summarising the upstream response or file state.
    """


class ProfileTooShortError(TephpyValidationError):
    """The profile tops out at or below the parcel's LCL (spec §6).

    No moist ascent exists, so every parcel-derived quantity would be
    meaningless; ``calc.parcel_path`` and ``calc.indices`` both raise
    this. The LCL tested is the one the path would use — the corrected
    one when a cloud-base correction is requested.
    """


class TephpyConfigError(TephpyError):
    """A configuration file could not be read or made sense of.

    A malformed YAML document, a top-level entry that is not a mapping, an
    unknown configuration section, and a ``$TEPHPYRC`` naming a file that
    does not exist all raise this. Raised only when the file was asked for
    explicitly; the import-time auto-load warns instead
    (configfile spec §5).
    """


class TephpyConfigWarning(UserWarning):
    """A configuration file was used, but something in it was ignored.

    An unknown option, an option whose value is an explicit null, and any
    failure during the import-time auto-load warn rather than raise, so a
    typo in a configuration file cannot make ``tephpy`` unimportable
    (configfile spec §5).
    """
