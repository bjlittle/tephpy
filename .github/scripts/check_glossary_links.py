#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that a page links a glossary term on its first mention (:issue:`209`).

docs-style's glossary rule asks for the *first* mention of a glossary term on a
page to be cross-referenced with ``:term:``, "in narrative prose only -- never
in titles, code blocks, API signatures, or admonition labels". The
fail-on-warning build already catches a ``:term:`` whose entry does not exist.
Nothing caught the link nobody wrote, so a page could name every term in the
glossary in plain text and build perfectly green -- which four pages written to
follow the rule did, sixteen times between them.

This gate reads source rather than the built HTML, so it needs no build and
fails on the commit that introduces the defect. That is the same footing as
``check_citations.py`` and ``check_github_references.py``.

**Aliases are why the work is done by group.** ``CAPE`` and ``convective
available potential energy`` are one glossary entry, so linking either
satisfies the rule; a scan that treated them as separate terms would report the
unlinked spelling as missing while the rule was already met.

**The exclusions are the engineering**, because each is a reading of "narrative
prose only". Four, each earning its place against the real corpus:

- A directive's options and its indented body are code, not prose. This is what
  keeps ``$ bufr_dump -p sounding.bufr`` in a ``console`` block from reading as
  a mention of *sounding*.
- The line above a section underline is a title.
- A role's target and an inline literal are API signatures or names. This is
  what keeps ``:class:`Sounding``` and a ``dewpoint_C`` column name out.
- An emphasis span quotes a page title -- *Parcel Ascent and Normand's Point* --
  rather than using the concept.

That last one is the judgement call, and it is deliberate: it would hide a
mention someone wrote as ``*sounding*`` for stress. Measured over this corpus
that costs nothing, and without it two page-title citations are permanent false
positives. Revisit it if a real mention is ever missed.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs" / "src"
#: The Diátaxis quadrants written for users. The reference quadrant is excluded
#: because the glossary lives there and an entry naming another term is the
#: rule's own exception; the developer section, because it is written for
#: contributors who are not the audience the glossary serves.
QUADRANTS = ("howtos", "tutorials", "explanation")

#: A term line in the ``glossary`` directive: one indent, no trailing colon,
#: and no markup. Consecutive matches share the definition that follows them,
#: which is what makes them aliases of one entry.
TERM = re.compile(r"^    ([A-Za-z][A-Za-z0-9 '-]*)$")
#: The definition body under a term line, which closes an alias run.
DEFINITION = re.compile(r"^        \S")
#: A cross-reference to a glossary entry, with the explicit target that wins
#: over the display text when one is written.
XREF = re.compile(r":term:`([^`<]+?)(?:\s*<([^>]+)>)?`")
#: A directive, whose options and indented body are not prose.
DIRECTIVE = re.compile(r"^\s*\.\.\s+\S+::")
#: A section underline; the line above it is a title.
UNDERLINE = re.compile(r"^[=\-~^\"'`#*+]{3,}\s*$")
#: Spans that are not narrative prose, stripped before a line is searched.
NOT_PROSE = (
    re.compile(r":[a-z:]+:`[^`]*`"),  # any role, display text and target
    re.compile(r"``[^`]*``"),  # inline literal
    re.compile(r"`[^`]*`_+"),  # hyperlink display text
    re.compile(r"(?<!\*)\*[^*\n]+\*(?!\*)"),  # emphasis: a quoted page title
)


def alias_map(glossary: str) -> dict[str, str]:
    """Map every term and alias to the canonical name of its entry.

    Parameters
    ----------
    glossary : str
        The source of the glossary page.

    Returns
    -------
    dict of str to str
        Each spelling, mapped to the first term of the run it belongs to.

    """
    groups: list[list[str]] = []
    run: list[str] = []
    for line in glossary.splitlines():
        term = TERM.match(line)
        if term:
            run.append(term.group(1).strip())
        elif run and DEFINITION.match(line):
            groups.append(run)
            run = []
    return {spelling: group[0] for group in groups for spelling in group}


def prose(text: str) -> list[tuple[int, str]]:
    """Select the narrative lines of a page, with their 1-based numbers.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    list of tuple
        ``(number, line)`` for each line of narrative prose.

    """
    lines = text.splitlines()
    found: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if DIRECTIVE.match(line) or re.match(r"^\s*\.\.\s", line):
            # The directive, its options and its body, to the first line that
            # is neither blank nor indented.
            index += 1
            while index < len(lines) and (
                not lines[index].strip() or lines[index].startswith(("    ", "\t"))
            ):
                index += 1
            continue
        if UNDERLINE.match(line) and found and found[-1][0] == index - 1:
            # The line above was a title rather than prose.
            found.pop()
            index += 1
            continue
        found.append((index, line))
        index += 1
    return [(number + 1, line) for number, line in found]


def narrative(line: str) -> str:
    """Strip the spans of a line that are not narrative prose.

    Parameters
    ----------
    line : str
        One line of a page.

    Returns
    -------
    str
        The line with roles, literals, links and emphasis blanked out.

    """
    for pattern in NOT_PROSE:
        line = pattern.sub(" ", line)
    return line


def unlinked(text: str, terms: dict[str, str]) -> list[tuple[int, str, str]]:
    """Report each glossary entry a page names in prose and never links.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.
    terms : dict of str to str
        The alias map from :func:`alias_map`.

    Returns
    -------
    list of tuple
        ``(number, term, line)`` per entry, in document order, naming the
        first mention and the spelling that matched.

    """
    targets = {(target or display).strip() for display, target in XREF.findall(text)}
    linked = {terms.get(name, name) for name in targets}
    found: dict[str, tuple[int, str, str]] = {}
    for number, line in prose(text):
        text_only = narrative(line)
        for spelling, entry in terms.items():
            if entry in linked or entry in found:
                continue
            # A trailing "s" is the same mention; a leading word character is
            # a different word, so `resounding` is not `sounding`.
            if re.search(
                rf"(?<![\w-]){re.escape(spelling)}s?\b", text_only, re.IGNORECASE
            ):
                found[entry] = (number, spelling, line.strip())
    return sorted(found.values())


def corpus() -> list[Path]:
    """Select the pages this gate reads.

    Returns
    -------
    list of Path
        Every ``.rst`` under the user quadrants, quadrant by quadrant.

    """
    found: list[Path] = []
    for quadrant in QUADRANTS:
        found.extend(sorted((DOCS / quadrant).rglob("*.rst")))
    return found


def main() -> int:
    """Report every unlinked first mention in the user quadrants.

    Returns
    -------
    int
        ``0`` when every page links the terms it names, ``1`` otherwise.

    """
    glossary = DOCS / "reference" / "glossary.rst"
    if not glossary.is_file():
        print(f"no glossary found at {glossary.relative_to(REPO)}")
        return 1
    terms = alias_map(glossary.read_text(encoding="utf-8"))
    if not terms:
        print(f"{glossary.relative_to(REPO)} defines no terms to check against")
        return 1
    pages = corpus()
    if not pages:
        print(f"no pages found under {DOCS.relative_to(REPO)} in {QUADRANTS}")
        return 1

    offenders = [
        (page, number, spelling, line)
        for page in pages
        for number, spelling, line in unlinked(page.read_text(encoding="utf-8"), terms)
    ]
    if not offenders:
        print(
            f"glossary links ok: {len(terms)} spellings, {len(pages)} pages "
            "(docs-style, glossary rule)"
        )
        return 0

    print(f"Unlinked glossary terms ({len(offenders)}):")
    for page, number, spelling, line in offenders:
        print(f"  {page.relative_to(REPO)}:{number}: {spelling!r} is not linked")
        print(f"      {line[:88]}")
    print(
        "\nCross-reference the *first* mention of a term on a page with "
        "`:term:`, in narrative prose. An alias counts: linking `CAPE` "
        "satisfies `convective available potential energy` too. See the "
        "glossary rule in docs/src/developer/docs-style.rst."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
