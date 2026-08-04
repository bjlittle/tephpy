# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the shared citation grammar (docs spec §3.7)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
MODULE = REPO / "docs" / "src" / "_ext" / "citations.py"

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
    spec = importlib.util.spec_from_file_location("citations", MODULE)
    assert spec is not None
    assert spec.loader is not None
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


def test_the_span_indexes_the_source():
    """The transform rewrites by span, so the span must address the citation."""
    source = cite("see spec @3.2 now")
    (citation,) = citations.scan(source, PATTERN, None)
    assert source[citation.start : citation.end] == citation.text
    assert citation.number == "3.2"


NOTEBOOK = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "Prose citing spec @3.2.\n",
                "\n",
                "```python\n",
                "# spec @9999 inside a fence\n",
                "```\n",
            ],
        },
        {
            "cell_type": "code",
            "metadata": {},
            "execution_count": None,
            "outputs": [
                {
                    "name": "stdout",
                    "output_type": "stream",
                    "text": ["generated output naming spec @8888\n"],
                }
            ],
            "source": ["# code comment citing spec @3.1\n", "print('hi')"],
        },
        {"cell_type": "raw", "metadata": {}, "source": ["raw cell spec @7777\n"]},
    ],
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 5,
}


def notebook(tmp_path):
    """Write the fixture notebook the way ``nbformat`` would, and return its path."""
    path = tmp_path / "probe.ipynb"
    path.write_text(cite(json.dumps(NOTEBOOK, indent=1)), encoding="utf-8")
    return path


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
