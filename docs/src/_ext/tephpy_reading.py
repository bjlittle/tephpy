# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""The reading-time model, shared by the directive and its gate (reading spec §3.1).

One definition of what a word is, what the rate is, and where the directive is
allowed to sit -- shared by the ``readingtime`` directive (reading spec §3.2) and
the coverage gate (reading spec §3.6). Two copies would agree until one of them
was amended, and a gate that counted differently from the banner it polices would
be checking a different page than the one it published.

Nothing here is imported from outside the standard library, so this module runs in
the CI test matrix, which carries no Sphinx.

The ``tephpy_`` prefix claims a top-level name this repository owns, because
``docs/src/_ext`` sits at ``sys.path[0]`` for the whole build (:issue:`92`). It is
not part of the installed package -- nothing under ``docs/`` is.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re

WPM: int = 150
"""Words-per-minute reading rate for technical documentation (reading spec §3.4).

Below the 175 wpm floor Brysbaert (2019) reports for ordinary non-fiction prose,
because these pages alternate argument with code the reader parses line by line.
"""

WORD = re.compile(r"\w+")
"""What counts as a word. Taken from the prior art, and shared rather than better."""

ARGUMENT = re.compile(
    r"\A(?:(?P<wpm>[1-9]\d*)wpm|(?P<minutes>[1-9]\d*))\Z", re.IGNORECASE
)
"""The directive's two argument shapes, anchored at both ends (reading spec §3.2)."""


@dataclass(frozen=True)
class Argument:
    """A parsed ``readingtime`` argument.

    Attributes
    ----------
    minutes : int or None
        A literal duration to quote, or ``None`` to count the page.
    wpm : int
        The rate to count at.

    Notes
    -----
    .. versionadded:: 0.1.0

    """

    minutes: int | None
    wpm: int


def count_words(text: str) -> int:
    """Count the words in ``text``.

    Parameters
    ----------
    text : str
        The text to count.

    Returns
    -------
    int
        The number of word-character runs.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    return len(WORD.findall(text))


def estimate_minutes(words: int, wpm: int = WPM) -> int:
    """Convert a word count to a reading time in minutes.

    Parameters
    ----------
    words : int
        The number of words on the page.
    wpm : int, optional
        The reading rate. It defaults to :data:`WPM`.

    Returns
    -------
    int
        The estimate, rounded up, and never below one: a page a reader has
        opened costs them a minute even when it is a sentence long.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    return max(1, math.ceil(words / wpm))


def parse_argument(argument: str | None) -> Argument:
    """Read the directive's optional argument.

    Parameters
    ----------
    argument : str or None
        ``None`` when the directive was given no argument, ``"30"`` for a
        literal duration in minutes, or ``"200wpm"`` for a rate override.

    Returns
    -------
    Argument
        The duration to quote, if any, and the rate to count at.

    Raises
    ------
    ValueError
        For any other argument. The prior art falls back to computing an
        estimate here, so ``.. readingtime:: thirty`` publishes a number its
        author did not ask for and never sees a warning. The docs build is
        ``--fail-on-warning``, so refusing is what surfaces the mistake.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    if argument is None:
        return Argument(minutes=None, wpm=WPM)
    match = ARGUMENT.match(argument.strip())
    if match is None:
        msg = (
            f"readingtime: expected no argument, a duration in minutes such as "
            f"'30', or a rate such as '200wpm'; got {argument!r}"
        )
        raise ValueError(msg)
    if match["wpm"] is not None:
        return Argument(minutes=None, wpm=int(match["wpm"]))
    return Argument(minutes=int(match["minutes"]), wpm=WPM)
