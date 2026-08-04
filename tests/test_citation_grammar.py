# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the shared citation grammar (docs spec §3.7)."""

from __future__ import annotations

import importlib.util
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
