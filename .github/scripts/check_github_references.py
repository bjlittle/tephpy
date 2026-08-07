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

Detection is wider than validation, deliberately, and the two are separate patterns
rather than one. A ``#`` is matched whether or not a space follows it, and a URL
under this repository is matched whatever path it names; only then is the form
compared against what a role produces. A single pattern doing both jobs could not
report a near-miss, because a form it failed to match would be neither judged nor
mentioned: a ``# 65`` written with a space and a ``pulls/65`` typo would each read
as compliance rather than as something to look at. Both are reported, each with the
reason it is not the form the rule asks for.

Widening the first pattern has a cost, and it is paid where a number sign does not
mean a reference at all. A number sign that opens a line is a Markdown heading or a
whole-line comment -- ``# 360 degrees at 4.1 m/s`` in the IGRA tests -- and is not
judged for that reason. One that follows something on the line is judged, and a
trailing comment whose first word is a number would be reported as a near-miss it
is not. Nothing distinguishes the two: ``see # 65`` and ``x = 1  # 3 files`` put the
same characters in the same places, and only the sentence around them says which is
which. The trade is deliberate -- a form nobody can see is worse than one somebody
rewords -- and the report names both readings so that rewording is the obvious out.

Three things are not references, and each is blanked before a line is judged --
blanked rather than dropped, so that what remains keeps the columns a reader will
find it at. Fenced code blocks, skipped by the shared reader for the reason that
docs spec §3.6 gives: the specification passage stating this rule quotes the bare
form it forbids. Inline code spans, and quoted hexadecimal colours -- the ones in
the logo tests whose six digits would otherwise read as an issue number. And link
text, so that a number already carrying a link is not reported as carrying none.

The colour exemption is written as a colour and not as a quoted string, which is the
wider form it began as. A quote mark is also an apostrophe, so a pair of them spans
the words between: ``It's #103, and don't regress it`` holds a real reference inside
a span that would have blanked it, and a one-line docstring holds one between its
own delimiters. Docs spec §3.8 puts a docstring in scope.

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
#: A hexadecimal colour, which is the one quoted string a reference can be confused
#: with: the all-digit ones such as ``"#101820"`` in the logo tests are a number sign
#: followed by digits, and only the quotes say otherwise. The quoting is not itself
#: the exemption, because the quote character is also the apostrophe: the pair in
#: ``It's #103, and don't regress it`` spans the words between them, and the
#: reference inside would be blanked rather than judged. A docstring's own
#: delimiters read the same way, and docs spec §3.8 puts docstrings in scope.
COLOUR = re.compile(r"[\"']#[0-9A-Fa-f]{3,8}[\"']")
#: What the unlinked assertion does not judge: an inline literal or a
#: reStructuredText hyperlink, a quoted colour, and Markdown link text -- recognised
#: by the parenthesis that follows it, which is what separates a link from an
#: ordinary bracket.
UNLINKED_EXEMPT = re.compile(
    f"{SPAN.format(name='literal')}|{COLOUR.pattern}|" + r"\[[^\]\n]*\](?=\()"
)
#: What the hardcoded assertion does not judge: an inline literal, and not a
#: reStructuredText hyperlink -- the trailing underscore says its URL is real.
HARDCODED_EXEMPT = re.compile(SPAN.format(name="literal") + r"(?!__?)")
#: A ``#`` and the digits that follow it, with or without the space that a near-miss
#: leaves between them. The preceding character is excluded from the word characters
#: and from the solidus, ampersand and number sign, so that a URL fragment, an HTML
#: entity and a nested Markdown heading are not read as one.
BARE = re.compile(r"(?<![\w&/#-])#(?P<gap>[ \t]*)(?P<number>\d+)\b")
#: Any URL under this repository that names something by number. The path is captured
#: rather than spelt out, so that a misspelling of one reaches the check.
URL = re.compile(
    r"https://github\.com/bjlittle/tephpy/(?P<path>[a-z]+)/(?P<number>\d+)"
)
#: The paths GitHub serves a single issue or pull request at, and the role each is
#: written with instead.
ROLE = {"issues": "issue", "pull": "pull"}
#: How each path is misspelt, which is the other one's number: GitHub lists issues at
#: ``issues`` and pull requests at ``pulls``, but serves one item at ``issues/N`` and
#: ``pull/N``, so the plural that is right for the list is wrong for the item and the
#: singular that is right for the item is wrong for the list. A URL under a misspelt
#: path resolves to no page, and is reported as broken rather than as hardcoded. Any
#: other path -- a discussion, a release, a commit -- names no issue or pull request,
#: has no role to be written with, and is left alone.
MISSPELT = {"pulls": "pull", "issue": "issues"}


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
                if match["gap"]:
                    if not line[: match.start()].strip():
                        # A number sign opening a line is a Markdown heading or a
                        # whole-line comment, not a reference that lost its digits.
                        continue
                    detail = (
                        f"a space separates {found} from its number sign, so no role "
                        f"produced it and none can be read from it"
                    )
                else:
                    detail = f"reference to {found} links to nothing"
                violations.append(
                    Violation(
                        path,
                        number,
                        f"{detail}; {advice(found, 'issue')} -- or the pull role, "
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
                where, found = match["path"], match["number"]
                if where in ROLE:
                    detail = f"hardcoded link to {found}"
                elif where in MISSPELT:
                    where = MISSPELT[where]
                    detail = (
                        f"link to {found} under a path GitHub serves no page at; "
                        f"one item is /{where}/"
                    )
                else:
                    continue
                violations.append(
                    Violation(path, number, f"{detail}; {advice(found, ROLE[where])}")
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
