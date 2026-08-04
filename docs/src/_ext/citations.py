# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""The design-specification citation grammar (docs spec §3.2).

One definition of what a citation is, shared by the pre-commit gate (docs spec §3.6)
and the cross-reference transform (docs spec §3.7). Two copies would agree until one
of them was amended, and the disagreement would then be silent in both directions:
the gate would pass text the transform declined to link, or the transform would link
text the gate had never audited.

Nothing here is imported from outside the standard library, so this module runs
in the CI test matrix, which carries no Sphinx.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

ANCHOR = re.compile(r"^\((?P<slug>[a-z][a-z-]*?)-(?P<num>\d+(?:-\d+)*)\)=\s*$")
HEADING = re.compile(r"^#{2,6}\s+(?P<num>\d+(?:\.\d+)*)\.?\s+\S")
FENCE = re.compile(r"^\s*(?P<rail>`{3,}|~{3,})(?P<info>.*)$")
SEPARATOR = re.compile(r"\s*[,/]\s*")


@dataclass(frozen=True)
class Anchor:
    """Where a MyST target was declared."""

    path: Path
    line: int


@dataclass(frozen=True)
class Citation:
    """One citation, located in the string it was found in.

    Attributes
    ----------
    start, end : int
        The half-open span of the citation, so a caller can rewrite the source
        without searching it a second time and risking a different answer.
    text : str
        The citation exactly as written, e.g. ``spec §3.2`` or a bare ``§N``.
        This is what a link displays.
    number : str
        The section number alone, e.g. ``3.2``.
    slug : str or None
        The anchor the citation names, e.g. ``spec-3-2``. ``None`` when a bare
        ``§N`` was written in a file that owns no sections, which docs spec §3.2
        makes an error rather than a reference to the parent specification.

    """

    start: int
    end: int
    text: str
    number: str
    slug: str | None


def read_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield the 1-indexed lines of ``text`` that sit outside a fenced code block.

    docs spec §3.3 illustrates the anchor rule with a literal target and heading
    inside a fence, so a reader that does not skip fences finds a duplicate anchor
    and a heading in the wrong document (docs spec §3.6).

    The opening rail is remembered rather than counted. A block opened with four
    backticks may quote a three-backtick block, and a reader that toggles on any
    rail treats that inner delimiter as the close and reads the quoted anchors as
    its own — so a fence closes only on a rail of the same character, at least as
    long, and carrying no info string.

    Parameters
    ----------
    text : str
        The file contents.

    Yields
    ------
    tuple of (int, str)
        The line number and the line, without its terminator.

    """
    rail: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        fence = FENCE.match(line)
        if fence is not None:
            found = fence["rail"]
            if rail is None:
                rail = found
                continue
            if (
                found[0] == rail[0]
                and len(found) >= len(rail)
                and not fence["info"].strip()
            ):
                rail = None
                continue
        if rail is None:
            yield number, line


def collect_anchors(
    specs: Iterable[Path],
) -> tuple[dict[str, Anchor], dict[Path, str]]:
    """Read the anchor registry and each specification's owning prefix.

    Parameters
    ----------
    specs : iterable of Path
        The specification documents to read.

    Returns
    -------
    tuple of (dict, dict)
        The anchors keyed by slug, and the owning prefix keyed by path.

    """
    anchors: dict[str, Anchor] = {}
    owners: dict[Path, str] = {}
    for spec in specs:
        for number, line in read_lines(spec.read_text(encoding="utf-8")):
            match = ANCHOR.match(line)
            if match is None:
                continue
            slug = f"{match['slug']}-{match['num']}"
            if slug in anchors:
                first = anchors[slug]
                print(  # noqa: T201
                    f"duplicate anchor '{slug}': "
                    f"{first.path}:{first.line} and "
                    f"{spec}:{number}"
                )
                raise SystemExit(1)
            anchors[slug] = Anchor(spec, number)
            owners.setdefault(spec, match["slug"])
    return anchors, owners


def citation_pattern(anchors: Iterable[str]) -> re.Pattern[str]:
    """Build the citation regular expression from the discovered prefixes.

    The registry is derived, not declared (docs spec §3.6): the citation forms are
    the anchor prefixes with hyphens read back as whitespace. Longest first, so
    ``logo spec`` matches before ``spec``.

    A prefix must start a word. Without that, the ``spec`` alternative matches
    inside ``nonspec``, and a typo validates as the citation it was trying to be.

    Parameters
    ----------
    anchors : iterable of str
        The anchor slugs, e.g. ``logo-spec-3-5``.

    Returns
    -------
    re.Pattern
        A pattern with ``prefix``, ``num`` and ``bare`` groups.

    """
    prefixes = set()
    for slug in anchors:
        parts = slug.split("-")
        digits = next(i for i, part in enumerate(parts) if part.isdigit())
        prefixes.add("-".join(parts[:digits]))
    forms = sorted(prefixes, key=len, reverse=True)
    alternation = "|".join(form.replace("-", r"\s+") for form in forms)
    return re.compile(
        rf"(?<![\w-])(?P<prefix>{alternation})\s*§(?P<num>\d+(?:\.\d+)*)"
        rf"|§(?P<bare>\d+(?:\.\d+)*)",
        flags=re.IGNORECASE,
    )


def notebook_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield the authored lines of a notebook, with markdown fences skipped.

    A notebook is read the way its cells are written (docs spec §3.6): markdown
    cells as markdown, so a fenced illustration of the anchor rule is skipped
    exactly as it is in a ``.md`` file; code cells as Python is read, so a
    citation in a comment is still checked; and outputs not at all, being
    generated rather than authored. A raw cell renders as nothing and is read as
    nothing.

    Line numbers are numbers in the ``.ipynb`` file itself, so a violation points
    where an editor will open. Each source line is located by searching forward
    for its JSON-encoded form, which ``nbformat`` writes one to a physical line.
    The cursor only ever moves forward, so a line repeated across cells resolves
    to its own occurrence; a line that cannot be located at all is reported
    against the last located line, or line 1 if none has been located yet,
    rather than silently ending the scan.

    Parameters
    ----------
    text : str
        The notebook file contents.

    Yields
    ------
    tuple of (int, str)
        The 1-indexed line number within the file, and the authored line.

    """
    try:
        nb = json.loads(text)
    except json.JSONDecodeError:
        return
    if not isinstance(nb, dict):
        return
    raw = text.splitlines()
    cursor = 0
    for cell in nb.get("cells", []):
        kind = cell.get("cell_type")
        if kind not in {"markdown", "code"}:
            continue
        source = cell.get("source", "")
        lines = (
            source.splitlines()
            if isinstance(source, str)
            else [line.rstrip("\n") for line in source]
        )
        located: list[tuple[int, str]] = []
        for line in lines:
            encoded = json.dumps(line, ensure_ascii=False)[1:-1]
            at = cursor
            while at < len(raw) and encoded not in raw[at]:
                at += 1
            if at < len(raw):
                cursor = at + 1
                located.append((at + 1, line))
            else:
                located.append((max(cursor, 1), line))
        if kind == "markdown":
            body = "\n".join(line for _number, line in located)
            for number, line in read_lines(body):
                yield located[number - 1][0], line
        else:
            yield from located


def source_lines(path: Path, text: str) -> Iterator[tuple[int, str]]:
    """Yield the lines of ``text`` that the citation rule governs.

    Parameters
    ----------
    path : Path
        The file the text came from; only its suffix is read.
    text : str
        The file contents.

    Yields
    ------
    tuple of (int, str)
        The 1-indexed line number, and the line.

    """
    if path.suffix == ".md":
        yield from read_lines(text)
    elif path.suffix == ".ipynb":
        yield from notebook_lines(text)
    else:
        yield from enumerate(text.splitlines(), start=1)


def scan(
    source: str,
    pattern: re.Pattern[str],
    owner: str | None,
) -> Iterator[Citation]:
    """Yield each citation in ``source``, resolved to the anchor it names.

    A prefix carries only to the end of its run — the comma- or solidus-separated
    compound of docs spec §3.2. Carrying it further would let it cross a sentence
    boundary, so that a bare ``§N`` opening the next sentence inherited the
    namespace of a prefixed citation earlier on rather than falling back to the
    containing document.

    Parameters
    ----------
    source : str
        The text to scan: one line for the gate, one text node for the transform.
    pattern : re.Pattern
        The citation pattern from :func:`citation_pattern`.
    owner : str or None
        The prefix of the document ``source`` was written in, or ``None`` when it
        owns no sections — a docstring, a test, a notebook.

    Yields
    ------
    Citation
        One per citation, in the order written. ``slug`` is ``None`` for a bare
        ``§N`` with no owner; the caller decides whether that is a violation to
        report or a citation to leave alone.

    """
    carried: str | None = None
    end = 0
    for match in pattern.finditer(source):
        joined = carried is not None and SEPARATOR.fullmatch(
            source[end : match.start()]
        )
        end = match.end()
        if match["prefix"] is not None:
            carried = re.sub(r"\s+", "-", match["prefix"].lower())
            number = match["num"]
        elif joined:
            number = match["bare"]
        elif owner is not None:
            carried, number = owner, match["bare"]
        else:
            carried = None
            yield Citation(
                match.start(), match.end(), match.group(0), match["bare"], None
            )
            continue
        yield Citation(
            match.start(),
            match.end(),
            match.group(0),
            number,
            f"{carried}-{number.replace('.', '-')}",
        )
