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

# `MANIFEST.in` prunes `.github`, so an sdist ships these tests without the
# checker they exercise, and a source archive carries no index for the corpus to
# be enumerated from. The gate is a contract about the repository, and neither of
# those is the repository, so skip there rather than fail collection.
pytestmark = pytest.mark.skipif(
    not (SCRIPT.is_file() and (REPO / ".git").exists()),
    reason="not a git checkout of the repository",
)

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


cc = _load() if SCRIPT.is_file() else None


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


def test_an_inner_fence_does_not_close_an_outer_one():
    """A quad-backtick block may quote a triple-backtick one (docs spec §3.6)."""
    outer, inner = "`" * 4, "`" * 3
    text = (
        f"{outer}markdown\n{inner}\n(spec-999)=\n"
        f"## 999. Leaked\n{inner}\n{outer}\nkept\n"
    )
    assert [line for _, line in cc.read_lines(text)] == ["kept"]


def test_a_prefix_must_start_a_word(tmp_path):
    """``nonspec §N`` is a typo, not a citation of the parent's ``§N``."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-3)=\n## 3. A\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text(f'"""A typo: nonspec {SECTION}3."""\n')
    violations = cc.check_citations([src], anchors, owners)
    assert len(violations) == 1
    assert "no prefix" in violations[0].message


def test_a_prefix_does_not_carry_past_its_run(tmp_path):
    """The run is comma- or solidus-separated, and ends at the sentence.

    The separators are fixed by docs spec §3.2; a full stop is not one of them.
    """
    spec = tmp_path / "docs.md"
    spec.write_text("(docs-spec-3-2)=\n### 3.2 A\n\n(docs-spec-4)=\n## 4. B\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text(f'"""See docs spec {SECTION}3.2, {SECTION}4."""\n')
    assert cc.check_citations([src], anchors, owners) == []
    src.write_text(f'"""See docs spec {SECTION}3.2. Also {SECTION}4."""\n')
    violations = cc.check_citations([src], anchors, owners)
    assert len(violations) == 1
    assert "no prefix" in violations[0].message


def test_an_anchor_whose_heading_is_gone_is_reported(tmp_path):
    """Deleting a section leaves its target resolving to nothing (docs spec §3.6).

    The heading pass cannot see this one — there is no heading left to start
    from — yet the anchor stays in the registry and citations keep resolving.
    """
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-1)=\n## 1. A\n\n(spec-2)=\n\nProse where the heading was.\n")
    _, owners = cc.collect_anchors([spec])
    violations = cc.check_anchors([spec], owners)
    assert len(violations) == 1
    assert violations[0].line == 4
    assert "names no heading" in violations[0].message


def test_the_corpus_covers_every_tracked_text_file():
    """A glob by extension silently omits citation-bearing files (docs spec §3.6)."""
    paths = set(cc.corpus())
    assert cc.REPO / "tests" / "fixtures" / "io" / "README.md" in paths
    assert cc.REPO / "pyproject.toml" in paths
    assert cc.REPO / "docs" / "src" / "developer" / "specs" / "index.rst" in paths
    frozen = "the plans are point-in-time records (docs spec §3.4)"
    assert not any("plans" in path.parts for path in paths), frozen
    assert not any(path.suffix == ".png" for path in paths), "images are not text"


def test_the_repository_satisfies_the_citation_contract(capsys):
    """The live tree passes all three assertions (docs spec §3.6).

    The pre-commit hook is the primary gate, but hooks are not installed in a
    fresh clone, so this is what catches a citation broken by someone who
    bypassed them.
    """
    assert cc.main() == 0, capsys.readouterr().out
