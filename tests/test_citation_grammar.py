# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the shared citation grammar (docs spec §3.7)."""

from __future__ import annotations

import importlib.util
import itertools
import json
from pathlib import Path
import sys

import nbformat
import pytest

REPO = Path(__file__).parents[1]
MODULE = REPO / "docs" / "src" / "_ext" / "tephpy_citations.py"

# As in `test_citations.py`: this file sits inside the corpus the checker reads
# (docs spec §3.6), so the fixtures below build the section sign rather than
# writing it. A literal one would be a citation from a file that owns no
# sections, and the checker would be right to reject it. The docstrings cite for
# real, and stay literal.
SECTION = "\N{SECTION SIGN}"


def cite(text):
    """Read ``@`` in a fixture as a section sign."""
    return text.replace("@", SECTION)


def _load():
    """Import the grammar by path; ``docs/src/_ext`` is not an importable package."""
    # The file is asserted on rather than the ``ModuleSpec``: a spec comes back
    # populated even for a path that does not exist, so the checks it invites are
    # dead, and a missing module surfaces as a ``FileNotFoundError`` instead.
    assert MODULE.is_file(), f"the citation grammar is missing from {MODULE}"
    spec = importlib.util.spec_from_file_location("tephpy_citations", MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


citations = _load()

ANCHORS = [
    "spec-3-1",
    "spec-3-2",
    "spec-3-3",
    "spec-7",
    "spec-10",
    "logo-spec-1",
    "docs-spec-3-2",
]
PATTERN = citations.citation_pattern(ANCHORS)


def found(source, owner=None):
    """Return ``(text, slug)`` for each citation the grammar finds."""
    return [(c.text, c.slug) for c in citations.scan(cite(source), PATTERN, owner)]


PROSE = """
Draw the isopleth families (spec @3.2), regenerated rather than ported
from tephi (spec @3.1/@10 item 5).  A bare @7 means this document, and
Spec @3.3 may open a sentence.  See spec @3.2, @7 for the pair.
"""


def test_a_block_of_prose_converts_end_to_end():
    """Every form of docs spec §3.2 at once, read as a specification reads it."""
    assert found(PROSE, owner="docs-spec") == [
        (cite("spec @3.2"), "spec-3-2"),
        (cite("spec @3.1"), "spec-3-1"),
        (cite("@10"), "spec-10"),
        (cite("@7"), "docs-spec-7"),
        (cite("Spec @3.3"), "spec-3-3"),
        (cite("spec @3.2"), "spec-3-2"),
        (cite("@7"), "spec-7"),
    ]


@pytest.mark.parametrize(
    ("source", "owner", "expected"),
    [
        ("spec @3.2", None, [("spec @3.2", "spec-3-2")]),
        ("Spec @3.2", None, [("Spec @3.2", "spec-3-2")]),
        ("logo spec @1", None, [("logo spec @1", "logo-spec-1")]),
        ("docs spec @3.2", None, [("docs spec @3.2", "docs-spec-3-2")]),
        ("spec @3.1/@10", None, [("spec @3.1", "spec-3-1"), ("@10", "spec-10")]),
        ("spec @3.1, @10", None, [("spec @3.1", "spec-3-1"), ("@10", "spec-10")]),
        ("@3.2", "docs-spec", [("@3.2", "docs-spec-3-2")]),
        ("@3.2", None, [("@3.2", None)]),
        ("nonspec @3.2", None, [("@3.2", None)]),
        (
            "spec @3.2.  @7 opens a sentence.",
            None,
            [("spec @3.2", "spec-3-2"), ("@7", None)],
        ),
    ],
)
def test_each_citation_form_resolves(source, owner, expected):
    """One form per case, including the two that docs spec §3.2 makes errors."""
    assert found(source, owner) == [(cite(text), slug) for text, slug in expected]


WRAPPED = [
    "the tephpy logo\nspec @3.2 explains it",  # a split-prefix wrap, `logo spec`
    "read the docs\nspec @3.2 for the rule",  # the same wrap, `docs spec`
    "read the spec\n@3.2 for the rule",  # a prefix parted from its sign
]


@pytest.mark.parametrize("source", WRAPPED)
def test_a_citation_cannot_span_a_line(source):
    """A wrapped prefix must not name a document the gate never saw.

    The two callers of :func:`scan` segment their input differently: the gate of
    docs spec §3.6 reads one line at a time, and the transform of docs spec §3.7
    reads a whole text node. Whitespace inside a citation is therefore horizontal
    only, so that the two readings cannot disagree — and this disagreement was
    the silent kind, with the gate validating the parent's section while the link
    went to the ``add_logo`` specification, both anchors existing and both gates
    passing.
    """
    whole = found(source)
    by_line = [citation for line in source.split("\n") for citation in found(line)]
    assert whole == by_line
    assert all("\n" not in text for text, _slug in whole)
    assert all(slug in {None, "spec-3-2"} for _text, slug in whole)


def test_a_compound_run_cannot_span_a_line():
    r"""A run wrapping after its separator must not carry the prefix across.

    The same divergence as above, one citation later: the separator's whitespace
    was ``\s`` too, so the transform carried ``logo spec`` over the wrap while
    the gate, reading the second line alone, fell back to the owning document.
    It takes an owner to bite — inside a specification both slugs resolve, so
    both gates pass and the reader lands in the wrong one.
    """
    source = "see logo spec @3.3,\n@5 for more"
    whole = found(source, owner="docs-spec")
    by_line = [
        citation for line in source.split("\n") for citation in found(line, "docs-spec")
    ]
    assert whole == by_line
    assert "logo-spec-5" not in [slug for _text, slug in whole]


#: Enough grammar to build the divergence of
#: ``test_a_compound_run_cannot_span_a_line`` — a multi-word prefix, a
#: one-word prefix, two section numbers, both run separators, a word that
#: is not one, and the wrap itself — but not every construction that has
#: bitten: the split-prefix wrap of ``WRAPPED[0]`` and ``WRAPPED[1]``
#: needs ``logo`` and ``spec`` held apart, and here they exist only
#: joined, as ``"logo spec"``. Five of these compose that divergence
#: (prefix, number, separator, wrap, number), so nothing shorter than
#: ``repeat=5`` can express it.
#:
#: Lowered to ``repeat=4`` against today's ``PIECES``, this property goes
#: vacuous under ``SEPARATOR`` widened to ``\s*[,/]\s*``: that construction
#: needs all five pieces, and one fewer collapses it away. Do not lower
#: ``repeat`` without re-running that mutation at the new value — lowering
#: it reads as a performance tidy-up, and would silently remove the only
#: guard against a further, unknown divergence of this shape. It would not
#: remove the only guard against the known instance:
#: ``test_a_compound_run_cannot_span_a_line`` fails independently under
#: the same mutation.
#:
#: A second known divergence, the prefix-to-sign gap (``[^\S\n]*§`` in
#: :func:`citation_pattern`) widened to ``\s``, is already caught at
#: ``repeat=3`` and gives no evidence either way about the floor. A
#: third, the gap inside a multi-word prefix widened the same way, is
#: outside this generator's reach at any ``repeat``: ``PIECES`` carries
#: ``"logo spec"`` only as one joined piece, and no ``"logo"`` of its
#: own for a wrap to part from ``"spec"``. It is guarded only by
#: ``test_a_citation_cannot_span_a_line`` (``WRAPPED[0]`` and
#: ``WRAPPED[1]``), not by this property.
PIECES = ["logo spec", "spec", "@3.2", "@1", ",", "/", " and ", "\n"]


@pytest.mark.parametrize("owner", [None, "docs-spec", "spec"])
def test_a_scan_is_indifferent_to_how_its_source_is_segmented(owner):
    r"""Scanning a source whole must equal concatenating the scans of its lines.

    This is the property the two line-span rules above enforce, stated once
    rather than per construction. It is what makes the two callers of
    :func:`scan` safe to disagree about segmentation: the gate of docs spec §3.6
    feeds it one line, the transform of docs spec §3.7 feeds it a whole text
    node, and neither can observe what the other resolved. Where the two
    readings differ, both gates pass and the citation names a document nobody
    checked.

    Three instances of that divergence were found by hand, each a ``\s`` that
    spanned a newline: the gap inside a multi-word prefix and the gap between a
    prefix and its section sign, both held by
    ``test_a_citation_cannot_span_a_line``, and the run separator, held by
    ``test_a_compound_run_cannot_span_a_line``. The property is asserted over
    generated sources so that a further, unknown one is caught here rather than
    by a reader who followed a link into the wrong specification — as far as
    ``PIECES`` reaches, which its own comment bounds.
    """
    for combination in itertools.product(PIECES, repeat=5):
        source = "".join(combination)
        if "\n" not in source or "@" not in source:
            # Without a wrap the two segmentations are the same string.
            continue
        by_line = [
            citation for line in source.split("\n") for citation in found(line, owner)
        ]
        assert found(source, owner) == by_line, source


def test_an_empty_registry_resolves_nothing():
    """A pattern built from no anchors must not resolve every bare form.

    ``"|".join([])`` is the empty string, which as an alternation matches the
    empty string, so the prefix group matches everywhere and a bare section
    number resolves to a prefix that is not there. The transform (docs spec §3.7)
    guards its caller as well; without both, a build whose specifications had
    been moved would emit a page of unresolvable references.
    """
    empty = citations.citation_pattern([])
    resolved = [
        (c.text, c.slug) for c in citations.scan(cite("spec @3.2"), empty, None)
    ]
    assert resolved == [(cite("@3.2"), None)]


def test_a_duplicate_anchor_raises_for_its_caller_to_render(tmp_path):
    """The grammar is shared, so it reports through the caller (docs spec §3.7).

    Printing and exiting here would give the gate absolute paths where it renders
    repository-relative ones, and would end ``sphinx-build`` from inside an event
    handler rather than as a build error.
    """
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("(spec-1)=\n## 1. A\n")
    b.write_text("(spec-1)=\n## 1. B\n")
    with pytest.raises(citations.DuplicateAnchorError) as caught:
        citations.collect_anchors([a, b])
    duplicate = caught.value
    assert isinstance(duplicate, ValueError)
    assert duplicate.slug == "spec-1"
    assert (duplicate.first.path, duplicate.first.line) == (a, 1)
    assert (duplicate.second.path, duplicate.second.line) == (b, 1)


def test_the_span_indexes_the_source():
    """The transform rewrites by span, so the span must address the citation."""
    source = cite("see spec @3.2 now")
    (citation,) = citations.scan(source, PATTERN, None)
    assert source[citation.start : citation.end] == citation.text
    assert citation.number == "3.2"


MARKDOWN = cite(
    "Prose citing spec @3.2.\n\n```python\n# spec @9999 inside a fence\n```\n"
)
CODE = cite("# code comment citing spec @3.1\nprint('hi')")
OUTPUT = cite("generated output naming spec @8888\n")
RAW = cite("raw cell spec @7777\n")


def notebook(tmp_path):
    """Write the fixture notebook with ``nbformat``, and return its path.

    Written by the writer rather than in its likeness (:issue:`95`). The
    line-location logic of ``notebook_lines`` finds each source line by searching
    forward for its JSON-encoded form, "which ``nbformat`` writes one to a
    physical line" -- an assumption about a package this repository does not
    control, which a fixture built by hand can only restate.
    """
    nb = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell(MARKDOWN),
            nbformat.v4.new_code_cell(
                CODE,
                outputs=[nbformat.v4.new_output("stream", name="stdout", text=OUTPUT)],
            ),
            nbformat.v4.new_raw_cell(RAW),
        ]
    )
    path = tmp_path / "probe.ipynb"
    nbformat.write(nb, path)
    return path


def test_a_line_is_reported_where_nbformat_wrote_it(tmp_path):
    r"""The assumption the line numbers rest on, asked of ``nbformat`` itself.

    Two properties of the writer, neither of them ours: each authored line is
    JSON-encoded onto a physical line of its own, so searching forward finds it;
    and the section sign is written literally, because ``nbformat`` serializes
    with ``ensure_ascii=False``. Were it escaped as a ``\u00a7`` instead, no
    citation-bearing line would ever be located, and every violation in a
    notebook would be reported against the line before it -- a gate still
    printing its violation, pointing an editor at the wrong place. A fixture
    built by hand cannot fail either way, because it is the imitation being
    checked (docs spec §3.6).
    """
    path = notebook(tmp_path)
    text = path.read_text(encoding="utf-8")
    raw = text.splitlines()
    located = list(citations.source_lines(path, text))

    assert SECTION in text, "the writer escaped the section sign out of the fixture"
    cited = [line for _number, line in located if SECTION in line]
    assert cited, "no citation reaches the reader, so nothing above is exercised"
    numbers = [number for number, _line in located]
    assert numbers == sorted(numbers)  # the cursor only ever moves forward
    # One authored line to a physical line, which containment alone does not say:
    # a writer emitting each cell's `source` as one string on one line satisfies
    # every assertion below -- every authored line is a substring of that line --
    # while reporting a whole cell against its opening. `nbformat` writes one to
    # a line today, and this is where a version that stopped would be caught.
    assert len(set(numbers)) == len(numbers), "two lines share one line of the file"
    for number, line in located:
        encoded = json.dumps(line, ensure_ascii=False)[1:-1]
        assert encoded in raw[number - 1], f"line {number} does not carry {line!r}"


def read(path):
    """Return the lines the citation rule governs, joined."""
    text = path.read_text(encoding="utf-8")
    return "\n".join(line for _number, line in citations.source_lines(path, text))


def test_a_notebook_is_read_as_markdown_and_as_code(tmp_path):
    """A notebook is read the way each of its cells is written (docs spec §3.6)."""
    body = read(notebook(tmp_path))
    assert cite("spec @3.2") in body  # markdown prose is read
    assert cite("spec @3.1") in body  # a code cell is read as a .py is


def test_a_notebook_hides_fences_output_and_raw_cells(tmp_path):
    """A fence is markdown; output and raw cells are not authored prose."""
    body = read(notebook(tmp_path))
    assert cite("@9999") not in body  # a fence inside a markdown cell
    assert cite("@8888") not in body  # generated output
    assert cite("@7777") not in body  # a raw cell renders as nothing


def test_a_notebook_citation_reports_its_own_file_line(tmp_path):
    """A violation must point where an editor will open the file."""
    path = notebook(tmp_path)
    raw = path.read_text(encoding="utf-8").splitlines()
    located = [
        number
        for number, line in citations.source_lines(path, "\n".join(raw))
        if cite("@3.2") in line
    ]
    assert len(located) == 1
    assert cite("@3.2") in raw[located[0] - 1]


def test_a_source_entry_may_carry_embedded_newlines(tmp_path):
    """``nbformat`` promises a multiline string, not one line per list entry.

    A markdown cell whose ``source`` list holds an entry with a newline in it is
    schema-valid, and hand-edited and tool-generated notebooks write them. Read
    one entry to a line, the list comes out shorter than the text it stands for,
    and the markdown branch — which indexes the one by the other — walks off the
    end (docs spec §3.6).
    """
    nb = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["alpha\nbeta\n", "gamma\n"],
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    text = json.dumps(nb, indent=1)
    path = tmp_path / "embedded.ipynb"
    path.write_text(text, encoding="utf-8")
    located = list(citations.source_lines(path, text))
    assert [line for _number, line in located] == ["alpha", "beta", "gamma"]
    numbers = [number for number, _line in located]
    raw = text.splitlines()
    assert numbers == sorted(numbers)  # the cursor only ever moves forward
    assert all(1 <= number <= len(raw) for number in numbers)
    assert "alpha" in raw[numbers[0] - 1]  # the entry is found where it is written
    assert "gamma" in raw[numbers[2] - 1]


def test_markdown_and_plain_files_are_unaffected(tmp_path):
    """The suffix branch is new; the two behaviours it subsumes are not."""
    md = tmp_path / "probe.md"
    md.write_text(cite("prose spec @3.2\n\n```\nspec @9999\n```\n"), encoding="utf-8")
    assert cite("@3.2") in read(md)
    assert cite("@9999") not in read(md)

    py = tmp_path / "probe.py"
    py.write_text(cite('"""spec @3.2."""\n'), encoding="utf-8")
    assert cite("@3.2") in read(py)


def test_a_malformed_notebook_is_read_as_nothing(tmp_path):
    """An unparsable notebook is a problem for the build, not for this gate."""
    path = tmp_path / "broken.ipynb"
    path.write_text("{not json", encoding="utf-8")
    assert read(path) == ""


def test_scan_continues_past_an_unlocatable_source_line(tmp_path):
    """An unlocatable source line is yielded and later lines are still scanned.

    The fixture encodes one source line using a JSON Unicode escape that
    normalises away on parsing, so the decoded form cannot be found in the
    raw file text.  The fallback path fires for that line; the assertion on
    ``"second line"`` pins that the scan continues past it.
    """
    raw = (
        '{"cells": [{"cell_type": "code", "metadata": {}, "outputs": [],'
        ' "source": ["\\u0041 first\\n", "second line"]}],'
        ' "metadata": {}, "nbformat": 4, "nbformat_minor": 5}'
    )
    assert "A first" not in raw  # decoded form is absent; fallback fires
    path = tmp_path / "esc.ipynb"
    path.write_text(raw, encoding="utf-8")
    lines = [line for _n, line in citations.source_lines(path, raw)]
    assert "A first" in lines  # (a) unlocatable line is still yielded
    assert "second line" in lines  # (b) scan continues past the unlocatable line


def wrapped_lines(lines, owner=None):
    """Return ``(line, text, slug, unwrapped)`` for each wrap the grammar finds."""
    return [
        (w.line, w.citation.text, w.citation.slug, w.unwrapped)
        for w in citations.wrapped_citations(lines, PATTERN, owner)
    ]


def wrapped(source, owner=None):
    """As ``wrapped_lines``, reading ``source`` the way a ``.md`` file is read."""
    return wrapped_lines(citations.read_lines(cite(source)), owner)


def test_a_prefix_wrapped_away_from_its_section_is_reported():
    """The shape :issue:`197` describes, live in the tree when this was written.

    ``docs`` ends a line and ``spec @3.2`` opens the next, so the gate reads the
    second line alone and resolves the shorter prefix. Both existing gates pass:
    the anchor it lands on exists, and the transform renders a link to it.
    """
    source = "the gate of docs\nspec @3.2 is what every page is written against.\n"
    assert wrapped(source, owner="plots-spec") == [
        (2, cite("spec @3.2"), "spec-3-2", "docs-spec-3-2")
    ]


def test_a_run_wrapping_after_its_comma_is_reported():
    """The second route ``scan``'s docstring names: the separator wraps.

    The prefix stays put; the comma that joins the run is what crosses the break.
    """
    source = "the two guards of docs spec @3.2,\n@3.3 and the fallback beneath them.\n"
    assert wrapped(source, owner="spec") == [
        (2, cite("@3.3"), "spec-3-3", "docs-spec-3-3")
    ]


def test_a_bare_section_meaning_the_containing_document_is_left_alone():
    """The 61% case: undoing the wrap does not move it, so nothing is reported."""
    source = (
        "the four guards of docs spec @3.2 are what\n@3.3 of this document requires.\n"
    )
    assert wrapped(source, owner="spec") == []


def test_a_separator_joined_run_on_one_line_is_left_alone():
    """``docs spec @3.2, @3.3`` is a run the grammar already reads correctly."""
    assert wrapped("the pair at docs spec @3.2, @3.3 governs it.\n", owner="spec") == []


def test_a_section_wrapped_away_from_an_and_is_left_alone():
    """The class :issue:`197` records as undetectable, asserted as out of scope.

    ``" and "`` is not a separator, so the prefix does not carry across it in
    either reading. Both agree on the containing document, and no comparison can
    tell that from a citation the author meant that way.
    """
    source = "the guards of docs spec @3.2 and\n@3.3 govern the fallback.\n"
    assert wrapped(source, owner="spec") == []


def test_a_prefix_ending_a_paragraph_does_not_reach_the_next_one():
    """A blank line ends the join; two paragraphs are never one sentence."""
    source = "a sentence ending in docs\n\nspec @3.2 opens the next paragraph.\n"
    assert wrapped(source, owner="spec") == []


def test_a_wrap_inside_a_fenced_block_is_not_read():
    """``read_lines`` skips fences, and an illustration of the defect is not one."""
    source = "```\nthe gate of docs\nspec @3.2 is illustrated here.\n```\n"
    assert wrapped(source, owner="spec") == []


def test_a_wrap_authored_in_a_notebook_cell_is_found(tmp_path):
    """The reader is chosen by the caller, so a notebook is read as a notebook.

    Reading a notebook's raw text would look for the wrap in JSON, where the
    authored newline is an escape inside a quoted string and no line boundary
    exists to find.
    """
    nb = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell(
                cite("the gate of docs\nspec @3.2 is the rule.")
            )
        ]
    )
    path = tmp_path / "probe.ipynb"
    nbformat.write(nb, path)
    lines = citations.source_lines(path, path.read_text(encoding="utf-8"))

    found = wrapped_lines(lines, owner="spec")
    assert [(text, slug, unwrapped) for _line, text, slug, unwrapped in found] == [
        (cite("spec @3.2"), "spec-3-2", "docs-spec-3-2")
    ]


def test_a_cell_boundary_is_not_a_line_wrap(tmp_path):
    """Two cells are two paragraphs, though no blank line separates them.

    ``notebook_lines`` numbers by the ``.ipynb`` file, so consecutive cells leave
    a gap rather than a blank line. Joining across one would report a wrap that
    the reader of the rendered notebook never sees.
    """
    nb = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell("a cell ending in docs"),
            nbformat.v4.new_markdown_cell(cite("spec @3.2 opens the next.")),
        ]
    )
    path = tmp_path / "probe.ipynb"
    nbformat.write(nb, path)
    lines = citations.source_lines(path, path.read_text(encoding="utf-8"))

    assert wrapped_lines(lines, owner="spec") == []
