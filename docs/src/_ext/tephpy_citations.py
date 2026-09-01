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

The ``tephpy_`` prefix claims a top-level name this repository owns, because
``docs/src/_ext`` sits at ``sys.path[0]`` for the whole build (:issue:`92`). It
is not part of the installed package -- nothing under ``docs/`` is.

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
#: The gap a compound run may be written across. Horizontal whitespace only,
#: for the reason :func:`citation_pattern` gives for the gap inside a prefix: a
#: run that spans a line is read by the transform and not by the line-at-a-time
#: gate, and the two then resolve the same continuation differently.
SEPARATOR = re.compile(r"[^\S\n]*[,/][^\S\n]*")


@dataclass(frozen=True)
class Anchor:
    """Where a MyST target was declared."""

    path: Path
    line: int


class DuplicateAnchorError(ValueError):
    """Two specifications declare the same anchor slug (docs spec §3.3).

    Raised rather than reported, because this module is shared and has no
    interface of its own. The gate of docs spec §3.6 renders it as a violation
    on the terminal with repository-relative paths, which are what a reader can
    act on; the transform of docs spec §3.7 renders it as a Sphinx diagnostic.
    Printing and exiting here would give neither: a ``SystemExit`` raised from a
    ``builder-inited`` handler ends ``sphinx-build`` through an event callback
    rather than through the build's own error reporting.

    Attributes
    ----------
    slug : str
        The anchor declared twice, e.g. ``spec-3-2``.
    first, second : Anchor
        Where it was declared, in the order the specifications were read.

    """

    def __init__(self, slug: str, first: Anchor, second: Anchor) -> None:
        super().__init__(slug, first, second)
        self.slug = slug
        self.first = first
        self.second = second


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

    Raises
    ------
    DuplicateAnchorError
        When two specifications declare the same slug. Sphinx labels are global
        (docs spec §3.3), so the second declaration would shadow the first and
        citations of it would resolve, silently, to the wrong document.

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
                raise DuplicateAnchorError(slug, anchors[slug], Anchor(spec, number))
            anchors[slug] = Anchor(spec, number)
            owners.setdefault(spec, match["slug"])
    return anchors, owners


def citation_pattern(anchors: Iterable[str]) -> re.Pattern[str]:
    r"""Build the citation regular expression from the discovered prefixes.

    The registry is derived, not declared (docs spec §3.6): the citation forms are
    the anchor prefixes with hyphens read back as whitespace. Longest first, so
    ``logo spec`` matches before ``spec``.

    A prefix must start a word. Without that, the ``spec`` alternative matches
    inside ``nonspec``, and a typo validates as the citation it was trying to be.

    A citation may not span a line. The whitespace inside a prefix, and between
    the prefix and the sign, is horizontal only — ``[^\S\n]`` rather than
    ``\s`` — because the two callers segment their input differently: the gate
    of docs spec §3.6 scans one line at a time, the transform of docs spec §3.7
    scans a whole text node. A prefix able to span a wrap is therefore read by
    the transform and not by the gate, and the two disagree in the one direction
    neither can detect. A line ending in the word ``logo``, followed by a line
    opening ``spec §3.2``, reads to the transform as a citation of the
    ``add_logo`` specification and to the gate as a citation of the parent's;
    both anchors exist, so both gates pass and the reader is sent to the wrong
    document. Confining a citation to one line makes the two segmentations agree
    by construction.

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
    # With no anchors there is no prefix to match, and an empty alternation
    # matches the empty string — which would make every bare section number
    # resolve to a prefix that is not there. ``(?!)`` never matches, so the
    # bare alternative carries the whole grammar and nothing resolves.
    alternation = (
        "|".join(form.replace("-", r"[^\S\n]+") for form in forms) if forms else "(?!)"
    )
    return re.compile(
        rf"(?<![\w-])(?P<prefix>{alternation})[^\S\n]*§(?P<num>\d+(?:\.\d+)*)"
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

    A cell's ``source`` is a string or a list of strings, and the schema does not
    promise one authored line per list entry: an entry may carry embedded
    newlines, and hand-edited and tool-generated notebooks do write them. Each
    entry is therefore split before it is read, rather than merely stripped of
    its terminator — a list read one entry to a line ends up shorter than the
    text it stands for, and the markdown branch below indexes one by the other.

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
            else [part for entry in source for part in entry.splitlines()]
        )
        located: list[tuple[int, str]] = []
        for line in lines:
            # ``ensure_ascii=False`` is load-bearing, not style. The default
            # encodes ``§`` as a ``\u00a7`` escape, which never matches the
            # literal character ``nbformat`` writes, so every citation-bearing
            # notebook line would fail to locate and be reported against the
            # previous located line instead — line 1 only if none has been
            # located yet. ``test_a_notebook_citation_reports_its_own_file_line``
            # catches the revert, but only for someone who runs the suite
            # before deciding.
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

    A run may not span a line either, and for the same reason ``SEPARATOR`` and
    the prefix gap of :func:`citation_pattern` are both horizontal-only: this is
    one rule about one grammar, not two quirks. A run wrapping after its comma
    carries the prefix across the wrap here, while the gate — reading the second
    line alone — falls back to the owning document. In a specification, where an
    owner exists, both of those resolve, so both gates pass and the reader is
    sent to the wrong document.

    A range is the same trap by a different route. ``SEPARATOR`` is a comma or a
    solidus and nothing else, so the dash of a range does not join a run: a
    prefixed ``§N`` followed by a dash and a bare ``§M`` cites that
    specification's ``§N`` and the *containing* document's ``§M``. Write the
    prefix on both ends of a range.

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


@dataclass(frozen=True)
class Wrapped:
    """A citation whose prefix a line break separated from its section.

    Attributes
    ----------
    line : int
        The 1-indexed line the citation was written on -- the second line of the
        wrap, where the section sign sits.
    citation : Citation
        The citation as the gate reads it, which is what the page links to.
    unwrapped : str or None
        The anchor the same text names once the wrap is undone, which is what the
        author wrote. It differs from ``citation.slug``; that difference is the
        defect.

    """

    line: int
    citation: Citation
    unwrapped: str | None


def _paragraphs(
    lines: Iterable[tuple[int, str]],
) -> Iterator[list[tuple[int, str]]]:
    """Group ``lines`` into the runs a line wrap can join.

    A blank line ends a run, and so does a gap in the numbering. The gap matters
    wherever the reader that produced ``lines`` skipped something: a fence in a
    markdown file, and the space between two cells of a notebook, which
    :func:`notebook_lines` numbers by the ``.ipynb`` file and so leaves
    discontinuous rather than blank. Joining across either would pair two lines
    the reader never sees together.
    """
    run: list[tuple[int, str]] = []
    previous: int | None = None
    for number, line in lines:
        if (
            not line.strip()
            or (run and previous is not None and number != previous + 1)
        ) and run:
            yield run
            run = []
        if line.strip():
            run.append((number, line))
        previous = number
    if run:
        yield run


def wrapped_citations(
    lines: Iterable[tuple[int, str]],
    pattern: re.Pattern[str],
    owner: str | None,
) -> Iterator[Wrapped]:
    """Yield each citation a line break separated from its prefix.

    The gate of docs spec §3.6 reads one line at a time, so a prefix ending a line
    never reaches a section sign opening the next: the citation resolves against
    the shorter prefix it is left with, or falls back to the containing document.
    The transform of docs spec §3.7 does the same, because the prefix gap of
    :func:`citation_pattern` is horizontal-only and the text node keeps the
    newline. Both therefore agree, both resolve, and the page links somewhere the
    author did not write (:issue:`197`).

    Nothing here guesses intent. The comparison is between the citation as written
    and the same citation with its wrap undone, and only a citation whose anchor
    *changes* is yielded -- so a bare ``§N`` meaning the containing document reads
    the same both ways and is never reported.

    Parameters
    ----------
    lines : iterable of (int, str)
        The authored lines and their numbers, as :func:`source_lines` yields
        them. The reader is the caller's to choose, so that a notebook is read
        as a notebook: its authored newlines are escapes inside JSON strings,
        and a reader of the raw text finds no line boundary to look across.
    pattern : re.Pattern
        The citation pattern from :func:`citation_pattern`.
    owner : str or None
        The prefix of the document the lines were written in, as for :func:`scan`.

    Yields
    ------
    Wrapped
        One per citation whose anchor the wrap changed, in the order written.

    A paragraph where undoing the wrap changes how many citations there are is
    passed over rather than reported. The two readings cannot then be paired, so
    there is nothing to compare; no paragraph in this repository does it, and
    inventing a report for a shape nobody has written would be guessing at what it
    meant.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    for paragraph in _paragraphs(lines):
        written = [
            (number, citation)
            for number, line in paragraph
            for citation in scan(line, pattern, owner)
        ]
        undone = list(
            scan(" ".join(line.strip() for _, line in paragraph), pattern, owner)
        )
        if len(written) != len(undone):
            continue
        for (number, citation), unwrapped in zip(written, undone, strict=True):
            if citation.slug != unwrapped.slug:
                yield Wrapped(number, citation, unwrapped.slug)
