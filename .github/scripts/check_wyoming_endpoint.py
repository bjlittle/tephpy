#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that the University of Wyoming archive still answers ``tephpy.io``.

``WYOMING_URL`` is the one external URL this project *calls* rather than links.
``tephpy.io.wyoming.fetch`` formats it, requests it, and parses the reply, so a
change at the far end is not a dead link a reader clicks past -- it is a reader's
traceback. It has moved once already: the constant's own comment records the
classic ``cgi-bin`` ``TEXT:LIST`` endpoint now answering 404.

Nothing else notices. ``tests/io/test_wyoming.py`` runs against byte-faithful
recorded captures, because no test here touches the network (``tests/AGENTS.md``),
and that is the right rule -- a suite that reached Wyoming would fail on their
outage rather than on our defect. The cost of the rule is that the archive can
move on a Tuesday and every gate stays green until somebody reports a bug. This
script is what pays that cost, on a schedule, outside the suite.

**It is deliberately not a link check.** A scanner reading this repository's text
finds the constant unformatted, braces and all::

    https://weather.uwyo.edu/wsgi/sounding?datetime={datetime}&id={station}

which the archive answers **400** while it is perfectly healthy -- measured
2026-09-08, against a formatted request answered 200 the same minute. A generic
checker pointed at ``src/`` therefore reports this URL as broken every run,
forever, and reports nothing at all on the day it truly breaks. ``.lycheeignore``
excludes it for that reason and this script covers it instead.

What it asserts is the invariant rather than a proxy for it: not that the URL
returns 200 -- a redirect to a friendly "we have moved" page returns 200 too --
but that ``fetch`` still comes back with a `Sounding`. That call is the same code
path a user's is, so it cannot drift from what it is checking, and it fails on a
moved endpoint, an HTTP error, and a reply the parser no longer recognises alike.

The ascent it asks for is the one ``tests/fixtures/io/`` recorded: Camborne, 12Z
on 2026-07-21. Asking for the fixtures' own ascent means a passing run also says
the captures remain reproducible from the source they name, which is the
provenance claim their README makes.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from datetime import UTC, datetime
import sys
import textwrap
from urllib.parse import quote

from tephpy._constants import WYOMING_URL
from tephpy.exceptions import TephpyIOError
from tephpy.io import wyoming

#: The ascent to ask for -- the one `tests/fixtures/io/` recorded, so that a
#: passing run also says those captures are still reproducible from the source
#: their README names. A fixed historical sounding, never "now": today's ascent
#: has not been flown at 00:30 UTC, and a probe that failed for that reason would
#: be reporting the clock rather than the archive.
STATION = "03808"
WHEN = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)

#: What to say when the archive does not answer with something readable. The
#: remediation is deliberately not "fix the URL": the endpoint moving is one of
#: several causes and the least likely to be diagnosed correctly from here.
BROKEN = (
    "tephpy.io.wyoming.fetch could not read the University of Wyoming archive. "
    "This is the failure WYOMING_URL's own comment records happening once "
    "already, when the classic cgi-bin TEXT:LIST endpoint began answering 404. "
    "Check by hand whether the archive is down, has moved, or has changed the "
    "reply format: open the URL above in a browser. If it has moved, "
    "WYOMING_URL in src/tephpy/_constants.py is what to update, and the "
    "recorded captures under tests/fixtures/io/ need regenerating with "
    "tests/fixtures/generate_io_fixtures.py against the new endpoint. If the "
    "archive is merely down, close this and let the next run confirm it."
)


def requested() -> str:
    """Build the URL this probe asks for, the way ``fetch`` builds it.

    Returns
    -------
    str
        The formatted request URL.

    Notes
    -----
    Formatted here rather than quoted as a literal, so that the URL a failure
    report tells a maintainer to open is the one the probe actually requested --
    including whatever ``WYOMING_URL`` was changed to since.

    """
    return WYOMING_URL.format(
        datetime=quote(f"{WHEN:%Y-%m-%d %H:%M:%S}"), station=quote(STATION)
    )


def probe() -> tuple[bool, str]:
    """Ask the archive for the fixtures' ascent and say what came back.

    Returns
    -------
    tuple of (bool, str)
        Whether the archive answered with a readable sounding, and the line to
        print about it.

    """
    try:
        sounding = wyoming.fetch(STATION, WHEN)
    except TephpyIOError as exc:
        return False, f"{type(exc).__name__}: {exc}"
    levels = sounding.pressure.magnitude.size
    surface = sounding.pressure.magnitude[0]
    return True, (
        f"{levels} levels, surface {surface:.1f} "
        f"{sounding.pressure.units:~}, label {sounding.label!r} "
        f"(template {WYOMING_URL})"
    )


def main() -> int:
    """Report whether the archive still answers, and say so in one line.

    Returns
    -------
    int
        ``0`` when the archive answered with a readable sounding, ``1``
        otherwise.

    """
    ok, detail = probe()
    if ok:
        print(f"Wyoming endpoint ok: {STATION} at {WHEN:%Y-%m-%d %H:%M} — {detail}")
        return 0
    print(f"Wyoming endpoint unreadable: {STATION} at {WHEN:%Y-%m-%d %H:%M}")
    print(f"  {detail}")
    # The formatted URL, not the template: the remediation says to open it, and a
    # reader who has to fill in the braces themselves is being asked to reproduce
    # the very step whose result is in question.
    print(f"  {requested()}")
    print(f"\n{textwrap.fill(BROKEN)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
