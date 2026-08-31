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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

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


FENCE = re.compile(r"\A(?P<rail>`{3,}|~{3,})(?P<info>.*)\Z")
"""A MyST fence at column 0. Indented fences are content, not page structure."""

UNDERLINE = re.compile(r"""\A(?P<char>[=\-~^"'`#*+:.])(?P=char){2,}[ \t]*\Z""")
"""A reStructuredText section underline at column 0, three characters or more."""

RST_DIRECTIVE = re.compile(r"\A\.\. readingtime::(?=\s|\Z)")
"""The directive at column 0. Indented, it is a demonstration (reading spec §3.6).

The lookahead requires the directive name to end at whitespace or line end, so
``.. readingtime::junk`` does not match: docutils parses that as a comment, not
the directive, and a prefix match would tell the gate the page carries a banner
that never renders.
"""

MYST_DIRECTIVE = "{readingtime}"
"""The info string of the fence that opens the directive in MyST."""

MYST_HEADING = "## "
"""The first section heading in a specification, whose title is a single ``#``."""


def myst_scan(text: str) -> Iterator[tuple[int, str, str | None]]:
    """Yield the column-0 lines of ``text`` that sit outside a fenced block.

    A MyST directive *is* a fence, and its opening rail carries the info string
    naming it -- so unlike ``tephpy_citations.read_lines``, which skips a fence
    whole, this reader yields the opening rail and reports its info string. A
    reader that skipped it could not see the thing the gate looks for.

    The rail discipline is the one that module documents: a block opened with
    four backticks may quote a three-backtick block, so a fence closes only on a
    rail of the same character, at least as long, carrying no info string.

    Parameters
    ----------
    text : str
        The file contents.

    Yields
    ------
    tuple of (int, str, str or None)
        The 1-indexed line number, the line, and -- when the line opens a fence
        -- its stripped info string.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    rail: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        fence = FENCE.match(line)
        if fence is not None:
            found, info = fence["rail"], fence["info"].strip()
            if rail is None:
                rail = found
                yield number, line, info
                continue
            if found[0] == rail[0] and len(found) >= len(rail) and not info:
                rail = None
                continue
        if rail is None:
            yield number, line, None


def _underlines(text: str) -> list[int]:
    """Return the 1-indexed lines that underline a title or section heading."""
    lines = text.splitlines()
    found: list[int] = []
    for number, line in enumerate(lines, start=1):
        if UNDERLINE.match(line) is None:
            continue
        # A transition -- four dashes on their own -- underlines nothing. A real
        # underline sits under text and is at least as long as it.
        above = lines[number - 2].rstrip() if number >= 2 else ""
        if above and len(line.rstrip()) >= len(above):
            found.append(number)
    return found


def title_line(text: str, suffix: str) -> int | None:
    """Return the 1-indexed line of the page title.

    Parameters
    ----------
    text : str
        The page source.
    suffix : str
        ``".rst"`` or ``".md"``.

    Returns
    -------
    int or None
        The title underline for reStructuredText, the ``# `` heading for MyST,
        or ``None`` for a page with no title.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    if suffix == ".md":
        for number, line, _ in myst_scan(text):
            if line.startswith("# "):
                return number
        return None
    underlines = _underlines(text)
    return underlines[0] if underlines else None


def first_section_line(text: str, suffix: str) -> int | None:
    """Return the 1-indexed line of the first section heading below the title.

    Parameters
    ----------
    text : str
        The page source.
    suffix : str
        ``".rst"`` or ``".md"``.

    Returns
    -------
    int or None
        ``None`` when the page has a title and no sections, in which case the
        whole page is its lead.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    if suffix == ".md":
        for number, line, _ in myst_scan(text):
            if line.startswith(MYST_HEADING):
                return number
        return None
    underlines = _underlines(text)
    return underlines[1] if len(underlines) > 1 else None


def directive_lines(text: str, suffix: str) -> list[int]:
    """Return the 1-indexed lines carrying the directive at column 0.

    Parameters
    ----------
    text : str
        The page source.
    suffix : str
        ``".rst"`` or ``".md"``.

    Returns
    -------
    list of int
        Every occurrence, in document order. Column 0 is what excludes a
        demonstration inside a literal block (reading spec §3.6).

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    if suffix == ".md":
        # `info` carries the whole fence info string, which for a directive that
        # takes an argument is `"{readingtime} 45"` or `"{readingtime} 200wpm"`
        # (reading spec §3.2) -- so the directive name is only the first token,
        # not the whole string. An exact match would miss both overrides.
        return [
            number
            for number, _, info in myst_scan(text)
            if info is not None and info.split()[:1] == [MYST_DIRECTIVE]
        ]
    return [
        number
        for number, line in enumerate(text.splitlines(), start=1)
        if RST_DIRECTIVE.match(line) is not None
    ]


def carries_reading_time(text: str, suffix: str) -> bool:
    """Report whether the page carries the directive in its lead.

    Parameters
    ----------
    text : str
        The page source.
    suffix : str
        ``".rst"`` or ``".md"``.

    Returns
    -------
    bool
        ``True`` when at least one column-0 directive sits after the title and
        before the first section heading.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    title = title_line(text, suffix)
    if title is None:
        return False
    section = first_section_line(text, suffix)
    return any(
        number > title and (section is None or number < section)
        for number in directive_lines(text, suffix)
    )
