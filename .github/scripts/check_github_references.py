#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that every GitHub reference is written as a link (docs spec §3.8).

A reference to an issue or pull request is written with the ``issue`` or ``pull``
extlink role, so that the URL is stated once in ``docs/src/conf.py`` and the caption
is generated from the same value that builds the link. Two forms are therefore
errors, and this gate asserts both over the corpus ``check_citations.py`` derives:

1. **Unlinked.** A bare reference that no role produced, which reaches a reader of
   the published page as plain text.
2. **Hardcoded.** A hand-written ``github.com/bjlittle/tephpy`` issue or
   pull-request URL, which restates what the configuration already holds.

The two partition the failures rather than overlapping. A number that is already the
display text of a link is left to the second assertion, which reports it once if the
link is this repository's and not at all if it is another project's -- the roles are
scoped here, so an issue elsewhere stays an ordinary link with its own URL.

Detection is wider than validation, deliberately. The patterns look for any ``#``
followed by digits, and any URL under this repository's ``issues/`` or ``pull/``
path, rather than for the exact forms the rule forbids. One pattern doing both jobs
could not report a near-miss: a form it failed to match would be neither judged nor
mentioned, so a ``# 65`` written with a space, or a ``pulls/65`` typo, would read as
compliance rather than as something to look at.

Three things are not references, and each is blanked before a line is judged --
blanked rather than dropped, so that what remains keeps the columns a reader will
find it at. Fenced code blocks, skipped by the shared reader for the reason that
docs spec §3.6 gives: the specification passage stating this rule quotes the bare
form it forbids. Inline code spans and quoted string literals, which is where a
hexadecimal colour is written -- mid grey in the add_logo specification, and the
ones in the logo tests whose six digits would otherwise read as an issue number.
And link text, so that a number already carrying a link is not reported as
carrying none.

One exemption differs between the two assertions, and it is reStructuredText's
hyperlink. It is delimited by backticks like an inline literal, and only the trailing
underscore tells them apart. The first assertion blanks it, because the number in it
is link text; the second does not, because the URL in it is real and hardcoded. A
literal with no underscore is blanked by both, which is what lets the specification
and the style guide quote a forbidden URL as an example of one.

**What this cannot catch.** A reference written with the wrong role of the two, where
the number is a pull request and the ``issue`` role names it, is well formed, renders
identically, and resolves -- GitHub redirects between the two paths, so the reader
still arrives where they should, and only the source misnames the kind. Settling it
would mean asking GitHub which each number is, and a hook that needs the network
fails offline and is rate-limited in CI. Review is what narrows that one.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    import types

REPO = Path(__file__).resolve().parents[2]
CITATIONS = REPO / ".github" / "scripts" / "check_citations.py"


def _citations() -> types.ModuleType:
    """Load the citation gate, for the corpus and the reporting it already derives.

    The corpus is a derived list -- every tracked text file, less the plans, as
    docs spec §3.6 requires -- and its docstring records that a glob once left a
    citation-bearing README outside the check. Restating that reasoning here would
    give it a second place to drift from.

    Returns
    -------
    module
        The loaded ``check_citations`` module.

    Raises
    ------
    SystemExit
        When the citation gate is not where this script expects it.

    """
    if not CITATIONS.is_file():
        print(f"cannot load the citation gate from {CITATIONS}")
        raise SystemExit(1)
    spec = importlib.util.spec_from_file_location("check_citations", CITATIONS)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _citations()

corpus = gate.corpus
display = gate.display
Violation = gate.Violation
source_lines = gate.citations.source_lines

#: A run of backticks and everything up to its matching rail. The rail is remembered
#: rather than counted, for the reason the fence reader gives: a span opened with two
#: backticks may quote a single one, and reStructuredText writes its inline literal
#: with two where Markdown writes one.
SPAN = r"(?P<{name}>`+)(?:(?!(?P={name})).)*(?P={name})"
#: What the unlinked assertion does not judge: an inline literal or a
#: reStructuredText hyperlink, a quoted string literal, and Markdown link text --
#: recognised by the parenthesis that follows it, which is what separates a link from
#: an ordinary bracket.
UNLINKED_EXEMPT = re.compile(
    SPAN.format(name="literal") + r"|\"[^\"]*\"|'[^']*'|\[[^\]\n]*\](?=\()"
)
#: What the hardcoded assertion does not judge: an inline literal, and not a
#: reStructuredText hyperlink -- the trailing underscore says its URL is real.
HARDCODED_EXEMPT = re.compile(SPAN.format(name="literal") + r"(?!__?)")
#: Any ``#`` immediately followed by digits, wherever it is written. The preceding
#: character is excluded from the word characters and from the solidus, ampersand and
#: number sign, so that a URL fragment, an HTML entity and a Markdown heading are not
#: read as one.
BARE = re.compile(r"(?<![\w&/#-])#(?P<number>\d+)\b")
#: Any URL under this repository's issue or pull-request path.
URL = re.compile(
    r"https://github\.com/bjlittle/tephpy/(?P<kind>issues|pull)/(?P<number>\d+)"
)
#: The role each URL path is written with instead.
ROLE = {"issues": "issue", "pull": "pull"}


def blank(match: re.Match[str]) -> str:
    """Replace a matched span with spaces, so the rest of the line keeps its columns.

    Parameters
    ----------
    match : re.Match
        The span to remove.

    Returns
    -------
    str
        As many spaces as the span had characters.

    """
    return " " * len(match.group(0))


def advice(number: str, role: str) -> str:
    """Render the role to write, in both syntaxes.

    Parameters
    ----------
    number : str
        The issue or pull-request number.
    role : str
        The extlink role name, ``issue`` or ``pull``.

    Returns
    -------
    str
        The MyST and reStructuredText forms, as a single phrase.

    """
    return f"write {{{role}}}`{number}` in Markdown, :{role}:`{number}` elsewhere"


def check_unlinked(paths: Iterable[Path]) -> list[Violation]:
    """Assert that no GitHub reference is written as plain text.

    Parameters
    ----------
    paths : iterable of Path
        The files to scan.

    Returns
    -------
    list of Violation
        One entry per reference that links to nothing.

    """
    violations: list[Violation] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for number, line in source_lines(path, text):
            for match in BARE.finditer(UNLINKED_EXEMPT.sub(blank, line)):
                found = match["number"]
                violations.append(
                    Violation(
                        path,
                        number,
                        f"reference to {found} links to nothing; "
                        f"{advice(found, 'issue')} -- or the pull role, "
                        f"if {found} is a pull request",
                    )
                )
    return violations


def check_hardcoded(paths: Iterable[Path]) -> list[Violation]:
    """Assert that no GitHub reference is written as a URL.

    Parameters
    ----------
    paths : iterable of Path
        The files to scan.

    Returns
    -------
    list of Violation
        One entry per hand-written issue or pull-request URL.

    """
    violations: list[Violation] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for number, line in source_lines(path, text):
            for match in URL.finditer(HARDCODED_EXEMPT.sub(blank, line)):
                role = ROLE[match["kind"]]
                violations.append(
                    Violation(
                        path,
                        number,
                        f"hardcoded link to {match['number']}; "
                        f"{advice(match['number'], role)}",
                    )
                )
    return violations


def main() -> int:
    """Run both assertions over the corpus.

    Returns
    -------
    int
        ``0`` when both hold, ``1`` otherwise.

    """
    paths = corpus()
    if not paths:
        print(
            "the corpus is empty, so nothing was checked; a gate that passes on "
            "an empty search is a green tick over nothing (docs spec §3.8)"
        )
        return 1
    groups = {
        "Unlinked references": check_unlinked(paths),
        "Hardcoded links": check_hardcoded(paths),
    }
    total = sum(len(found) for found in groups.values())
    if total == 0:
        print(f"github references ok: {len(paths)} files (docs spec §3.8)")
        return 0
    for heading, found in groups.items():
        if found:
            print(f"{heading} ({len(found)}):")
            for violation in found:
                print(violation)
    return 1


if __name__ == "__main__":
    sys.exit(main())
