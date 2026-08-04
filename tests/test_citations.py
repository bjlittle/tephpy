# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the citation-integrity checker (docs spec §3.6)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_citations.py"

# This file sits inside the corpus the checker reads (docs spec §3.6), so the
# section sign is built rather than written in the fixtures below: a literal one
# would be a citation of a file that owns no sections, and the checker would be
# right to reject it. The docstrings cite for real, and stay literal.
SECTION = "\N{SECTION SIGN}"


def _load():
    """Import the checker by path; ``.github`` is not an importable package."""
    spec = importlib.util.spec_from_file_location("check_citations", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cc = _load()


def test_fenced_blocks_are_skipped():
    """Docs spec §3.3 illustrates the anchor rule inside a fence (docs spec §3.6)."""
    fence = "`" * 3
    text = (
        f"(spec-1)=\n{fence}markdown\n(spec-3-2)=\n"
        f"### 3.2 `plotting`\n{fence}\n## 1. Purpose\n"
    )
    assert [n for n, _ in cc.read_lines(text)] == [1, 6]


def test_fence_state_survives_a_tilde_fence():
    """MyST accepts ``~~~`` as well as backticks; both must toggle the same state."""
    text = "a\n~~~\nhidden\n~~~\nb\n"
    assert [line for _, line in cc.read_lines(text)] == ["a", "b"]


def test_a_prefixed_citation_resolves_to_its_own_namespace(tmp_path):
    """The prefix selects the document: ``logo spec §3`` is not ``spec §3``."""
    spec = tmp_path / "logo.md"
    spec.write_text("(logo-spec-3)=\n### 3. Sizing\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text(f'"""Doc (logo spec {SECTION}3)."""\n')
    assert cc.check_citations([src], anchors, owners) == []
    src.write_text(f'"""Doc (spec {SECTION}3)."""\n')
    assert len(cc.check_citations([src], anchors, owners)) == 1


def test_a_compound_citation_inherits_the_head_prefix(tmp_path):
    """``spec §3.3, §10`` and ``spec §3.1/§10`` each name two parent sections."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-3-1)=\n### 3.1 A\n\n(spec-10)=\n## 10. B\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text(
        f'"""A (spec {SECTION}3.1/{SECTION}10) '
        f'and B (spec {SECTION}3.1, {SECTION}10)."""\n'
    )
    assert cc.check_citations([src], anchors, owners) == []


def test_a_compound_citation_reports_the_unresolvable_member(tmp_path):
    """The continuation is checked, not just the head."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-3-1)=\n### 3.1 A\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text(f'"""A (spec {SECTION}3.1/{SECTION}10)."""\n')
    violations = cc.check_citations([src], anchors, owners)
    assert len(violations) == 1
    assert "spec-10" in violations[0].message


def test_the_word_spec_is_matched_without_regard_to_case(tmp_path):
    """A sentence may open with ``Spec §3.2`` (docs spec §3.2)."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-3-2)=\n### 3.2 A\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text(f'"""Spec {SECTION}3.2 covers this."""\n')
    assert cc.check_citations([src], anchors, owners) == []


def test_a_bare_reference_in_a_spec_means_that_spec(tmp_path):
    """Inside a specification the bare form points at a neighbour (docs spec §3.2)."""
    spec = tmp_path / "parent.md"
    spec.write_text(f"(spec-3-1)=\n### 3.1 A\n\nSee {SECTION}3.1.\n")
    anchors, owners = cc.collect_anchors([spec])
    assert cc.check_citations([spec], anchors, owners) == []


def test_a_bare_reference_outside_the_specs_is_an_error(tmp_path):
    """``src/`` owns no sections, so a bare ``§N`` has nothing to be relative to."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-6)=\n## 6. Errors\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text(f'"""Fails inside the {SECTION}6 taxonomy."""\n')
    violations = cc.check_citations([src], anchors, owners)
    assert len(violations) == 1
    assert "no prefix" in violations[0].message


def test_a_heading_without_an_anchor_is_a_coverage_violation(tmp_path):
    """Every numbered heading carries a target (docs spec §3.3)."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-1)=\n## 1. A\n\n## 2. B\n")
    _, owners = cc.collect_anchors([spec])
    violations = cc.check_anchors([spec], owners)
    assert len(violations) == 1
    assert violations[0].line == 4


def test_an_anchor_keyed_to_the_wrong_heading_is_a_keying_violation(tmp_path):
    """An anchor that drifts still resolves, so keying is checked separately."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-1)=\n## 1. A\n\n(spec-9)=\n## 2. B\n")
    _, owners = cc.collect_anchors([spec])
    violations = cc.check_anchors([spec], owners)
    assert len(violations) == 1
    assert "spec-2" in violations[0].message


def test_a_duplicate_anchor_is_reported(tmp_path):
    """Sphinx labels are global, so two specs cannot share a slug (docs spec §3.3)."""
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("(spec-1)=\n## 1. A\n")
    b.write_text("(spec-1)=\n## 1. B\n")
    with pytest.raises(SystemExit):
        cc.collect_anchors([a, b])
