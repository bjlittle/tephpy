# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the citation-integrity checker (docs spec §3.6)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from tests.by_path import load_script

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_citations.py"

# The suite runs from a checkout; a tree without `.github` -- a copy taken
# without its dotted directories, say -- has no checker to exercise. The gate
# is a contract about the repository, and that is not the repository, so skip
# there rather than fail collection.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="not a checkout of the repository"
)

#: The corpus is derived with `git ls-files` (docs spec §3.6), so the four
#: tests that read the live tree need an index. That is a narrower condition
#: than the module's: an export of the committed tree carries these tests and
#: no repository, and every fixture-driven test below still holds there.
#: Guarding the module on the index instead would skip all twenty-three wherever
#: history is absent, for a reason nineteen of them do not have.
tracked = pytest.mark.skipif(
    not (REPO / ".git").exists(), reason="no index to enumerate the corpus from"
)

# This file sits inside the corpus the checker reads (docs spec §3.6), so the
# section sign is built rather than written in the fixtures below: a literal one
# would be a citation of a file that owns no sections, and the checker would be
# right to reject it. The docstrings cite for real, and stay literal.
SECTION = "\N{SECTION SIGN}"


cc = load_script("check_citations") if SCRIPT.is_file() else None


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


def test_a_container_is_an_anchor_a_subsection_extends():
    """An anchor with subsections beneath it can be cited without naming one.

    The slug carries the section number, so the relationship is in the name:
    ``spec-3-2-1`` extends ``spec-3-2``. Sibling and prefix lookalikes must not
    be mistaken for children -- ``spec-3-20`` is a different section, not a
    subsection of ``spec-3-2``, and the hyphen is what separates them.
    """
    anchors = dict.fromkeys(
        ["spec-1", "spec-3", "spec-3-2", "spec-3-2-1", "spec-3-2-7", "spec-3-20"]
    )
    assert cc.containers(anchors) == {"spec-3", "spec-3-2"}


def test_a_leaf_anchor_is_not_a_container():
    """A collection whose sections are all flat has no containers at all."""
    assert cc.containers(dict.fromkeys(["logo-spec-1", "logo-spec-2"])) == set()


@tracked
def test_the_corpus_covers_every_tracked_text_file():
    """A glob by extension silently omits citation-bearing files (docs spec §3.6)."""
    paths = set(cc.corpus())
    assert cc.REPO / "tests" / "fixtures" / "io" / "README.md" in paths
    assert cc.REPO / "pyproject.toml" in paths
    assert cc.REPO / "docs" / "src" / "developer" / "specs" / "index.rst" in paths
    frozen = "the plans are point-in-time records (docs spec §3.4)"
    assert not any("plans" in path.parts for path in paths), frozen
    assert not any(path.suffix == ".png" for path in paths), "images are not text"


def _container_citations() -> list[str]:
    """Census every citation of a container anchor, outside the specifications.

    The specifications are excluded because a specification naming another's
    section as a topic is ordinary prose, and there is a great deal of it: 111
    citations land on a container across the whole corpus and 36 outside this
    collection, the difference being cross-references between specifications
    and the anchor specification discussing the plotting section at length. What
    the census is for is the other kind — a docstring or a page sending a reader
    to a section that has since been subdivided.

    Returns
    -------
    list of tuple
        One ``(path, slug)`` per citation. The line is deliberately not carried:
        the record is what a reader has already judged, and an edit that moves a
        citation down its file changes nothing they need to judge again.

    """
    anchors, owners = cc.collect_anchors(sorted(cc.SPECS.glob("*.md")))
    pattern = cc.citation_pattern(anchors)
    held = cc.containers(anchors)
    found = []
    for path in cc.corpus():
        if path.parent == cc.SPECS:
            continue
        own = owners.get(path)
        text = path.read_text(encoding="utf-8")
        for _, line in cc.citations.source_lines(path, text):
            found += [
                (cc.display(path), citation.slug)
                for citation in cc.citations.scan(line, pattern, own)
                if citation.slug in held
            ]
    return found


#: Citations naming a section that another anchor subdivides, by file and
#: anchor (`anchor spec §7`). Recorded 2026-09-10 over six of the twenty-three
#: container anchors: `spec-3-2`, the plotting section subdivided by
#: :pull:`295`, 13 — 14 until :issue:`294` gave the side-panel teardown rule a
#: subsection to name; `configfile-spec-5`, two subsections, 14 (:issue:`296`);
#: `configfile-spec-3`, six subsections, 5; and one each on `spec-3`,
#: `logo-spec-3` and `topics-spec-6`, all three grammar specimens in the tests
#: and the extensions rather than references to those sections.
#:
#: Keyed by file rather than by line, so ordinary edits above a citation do not
#: churn it, and counted per file rather than in total, so a citation removed
#: from one file cannot pay for one arriving in another.
#:
#: Moved 2026-09-11 (:pull:`300`): `changelog/300.documentation.rst` adds two on
#: `spec-3-2`, both spanning claims that belong on the container — the section's
#: own length, and that it keeps every word and every anchor. Neither is about a
#: paragraph, so neither has a subsection to name instead.
CONTAINER_CITATIONS = {
    ("changelog/201.enhancement.rst", "spec-3-2"): 1,
    ("changelog/300.documentation.rst", "spec-3-2"): 2,
    ("changelog/90.documentation.rst", "spec-3-2"): 1,
    ("docs/src/_ext/tephpy_citation_xrefs.py", "spec-3-2"): 1,
    ("docs/src/_ext/tephpy_citations.py", "spec-3-2"): 2,
    ("docs/src/_ext/tephpy_topics_data.py", "spec-3-2"): 1,
    ("docs/src/developer/docs-style.rst", "spec-3-2"): 2,
    ("src/tephpy/__init__.py", "configfile-spec-5"): 1,
    ("src/tephpy/_config.py", "configfile-spec-5"): 1,
    ("src/tephpy/_configfile.py", "configfile-spec-3"): 2,
    ("src/tephpy/_configfile.py", "configfile-spec-5"): 8,
    ("src/tephpy/_constants.py", "configfile-spec-3"): 2,
    ("src/tephpy/exceptions.py", "configfile-spec-5"): 3,
    ("src/tephpy/plotting/axes.py", "spec-3-2"): 2,
    ("src/tephpy/plotting/isopleths.py", "configfile-spec-3"): 1,
    ("tests/plotting/test_axes.py", "spec-3-2"): 1,
    ("tests/plotting/test_isopleths.py", "spec-3-2"): 1,
    ("tests/test_citations.py", "logo-spec-3"): 1,
    ("tests/test_citations.py", "spec-3"): 1,
    ("tests/test_citations.py", "spec-3-2"): 1,
    ("tests/test_configfile_domain.py", "configfile-spec-5"): 1,
    ("tests/test_docs_topics.py", "topics-spec-6"): 1,
}


@tracked
def test_the_container_census_is_what_was_recorded():
    """Watch the sections that have been subdivided for citations left behind.

    A citation of a section that has subsections resolves, and no rule can say
    whether it should: a claim spanning the whole section has nowhere better to
    point, while a claim about one paragraph leaves the reader to find it. So
    this counts rather than judges, and a change to the count is the trigger
    that `anchor spec §7` asks for.

    **If this fails, do not simply update the record.** Read the file the
    message names and decide which kind the citation is. A spanning claim
    belongs on the container and the record moves with a note saying so; a
    claim about one paragraph should name the subsection instead.
    """
    found = Counter(_container_citations())
    recorded = CONTAINER_CITATIONS
    moved = sorted(
        key for key in recorded.keys() | found.keys() if recorded.get(key) != found[key]
    )
    assert not moved, "\n".join(
        f"{path} {slug}: recorded {recorded.get(key, 0)}, found {found[key]}"
        for key in moved
        for path, slug in [key]
    )


@tracked
def test_the_repository_satisfies_the_citation_contract(capsys):
    """The live tree passes all three assertions (docs spec §3.6).

    The pre-commit hook is the primary gate, but hooks are not installed in a
    fresh clone, so this is what catches a citation broken by someone who
    bypassed them.
    """
    assert cc.main() == 0, capsys.readouterr().out


def test_a_citation_wrapped_away_from_its_prefix_is_a_violation(tmp_path):
    """:issue:`197`, in the shape found live in the tree when this was written.

    ``narrative`` ends a line and ``spec §3.6`` opens the next. The existing rule
    passes, because the anchor the shorter prefix names exists; the page then
    links to that anchor instead of the one written.
    """
    parent = tmp_path / "parent.md"
    parent.write_text("(spec-3-6)=\n### 3.6 Browser documentation demo\n")
    narrative = tmp_path / "narrative.md"
    narrative.write_text("(narrative-spec-3-6)=\n### 3.6 The reader how-to\n")
    gallery = tmp_path / "gallery.md"
    gallery.write_text(
        "(gallery-spec-1)=\n## 1. Purpose\n\n"
        f"belongs to 7c regardless. *Specified 2026-08-27:* narrative\n"
        f"spec {SECTION}3.6, which records that it moved the constraint.\n"
    )
    anchors, owners = cc.collect_anchors([parent, narrative, gallery])

    assert cc.check_citations([gallery], anchors, owners) == []

    violations = cc.check_wraps([gallery], anchors, owners)
    assert len(violations) == 1
    assert violations[0].line == 5
    assert "narrative-spec-3-6" in violations[0].message


def test_a_wrap_authored_in_a_notebook_is_a_violation(tmp_path):
    """The gate reads a notebook as a notebook, not as the JSON it is stored in.

    A notebook's authored newlines are escapes inside quoted strings, so a rule
    reading the raw text finds no boundary to look across and the wrap goes by.
    Notebooks are governed by the same derived corpus as everything else.
    """
    nbformat = pytest.importorskip("nbformat")
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-3-2)=\n### 3.2 A\n")
    other = tmp_path / "docs.md"
    other.write_text("(docs-spec-3-2)=\n### 3.2 B\n")
    anchors, owners = cc.collect_anchors([spec, other])

    notebook = tmp_path / "probe.ipynb"
    nbformat.write(
        nbformat.v4.new_notebook(
            cells=[
                nbformat.v4.new_markdown_cell(
                    f"the gate of docs\nspec {SECTION}3.2 is the rule."
                )
            ]
        ),
        notebook,
    )

    violations = cc.check_wraps([notebook], anchors, owners)
    assert len(violations) == 1
    assert "docs-spec-3-2" in violations[0].message


@tracked
def test_the_corpus_passes_over_the_vendored_runtime():
    """The vendored runtime is not this project's prose (tooltip spec §3.2)."""
    # Asserted alongside the directory being non-empty, because "no corpus path
    # is under a directory that does not exist" is a test that passes for the
    # wrong reason the day the bundles move.
    vendored = REPO / "docs" / "src" / "_static" / "js"
    assert list(vendored.glob("*.js")), "the vendored runtime is missing"
    assert not [path for path in cc.corpus() if vendored in path.parents]
