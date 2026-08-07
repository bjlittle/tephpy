# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the GitHub-reference checker (docs spec §3.8)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_github_references.py"

# `MANIFEST.in` prunes `.github`, so an sdist ships these tests without the checker
# they exercise, and a source archive carries no index for the corpus to be
# enumerated from. The gate is a contract about the repository, and neither of those
# is the repository, so skip there rather than fail collection.
pytestmark = pytest.mark.skipif(
    not (SCRIPT.is_file() and (REPO / ".git").exists()),
    reason="not a git checkout of the repository",
)

# This file sits inside the corpus the gate reads (docs spec §3.8), so the number
# sign is built rather than written in the fixtures below: a literal one followed by
# digits is exactly what the gate exists to reject, and it would be right to reject
# it here. The docstrings refer to the forms in code spans, and stay literal.
HASH = "\N{NUMBER SIGN}"
BASE = "https://github.com/bjlittle/tephpy"


def _load():
    """Import the checker by path; ``.github`` is not an importable package.

    Returns
    -------
    module
        The loaded ``check_github_references`` module.

    """
    spec = importlib.util.spec_from_file_location("check_github_references", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gr = _load() if SCRIPT.is_file() else None


def test_a_bare_reference_is_reported(tmp_path):
    """The plain form reaches a reader as text (docs spec §3.8)."""
    source = tmp_path / "spec.md"
    source.write_text(f"Settled in PR {HASH}40 last week.\n")
    violations = gr.check_unlinked([source])
    assert len(violations) == 1
    assert violations[0].line == 1
    assert "40" in violations[0].message


def test_a_role_is_not_a_bare_reference(tmp_path):
    """The role is the form the rule asks for, and passes."""
    source = tmp_path / "spec.md"
    source.write_text("Settled in PR {pull}`40` last week.\n")
    assert gr.check_unlinked([source]) == []
    assert gr.check_hardcoded([source]) == []


def test_a_hardcoded_url_is_reported(tmp_path):
    """The URL is stated once, in the extlinks configuration (docs spec §3.8)."""
    source = tmp_path / "spec.md"
    source.write_text(f"See [{HASH}65]({BASE}/issues/65) for the rest.\n")
    unlinked = gr.check_unlinked([source])
    hardcoded = gr.check_hardcoded([source])
    assert unlinked == [], "the number is link text, so only the URL is at fault"
    assert len(hardcoded) == 1
    assert "issue" in hardcoded[0].message


def test_the_suggested_role_follows_the_url_path(tmp_path):
    """A pull-request URL is told to use ``pull``, not ``issue``."""
    source = tmp_path / "spec.md"
    source.write_text(f"See [{HASH}73]({BASE}/pull/73).\n")
    violations = gr.check_hardcoded([source])
    assert len(violations) == 1
    assert "pull" in violations[0].message
    assert "issue" not in violations[0].message


def test_another_project_s_issue_is_left_alone(tmp_path):
    """The roles are scoped to this repository (docs spec §3.8)."""
    source = tmp_path / "spec.md"
    other = "https://github.com/Unidata/MetPy/issues/1234"
    source.write_text(f"See [Unidata/MetPy{HASH}1234]({other}).\n")
    assert gr.check_unlinked([source]) == []
    assert gr.check_hardcoded([source]) == []


def test_a_fenced_block_is_skipped(tmp_path):
    """A passage documenting the rule quotes the form it forbids (docs spec §3.6)."""
    fence = "`" * 3
    source = tmp_path / "spec.md"
    source.write_text(f"{fence}\ngh pr create --body 'Closes {HASH}65'\n{fence}\nok\n")
    assert gr.check_unlinked([source]) == []


def test_an_inline_code_span_is_skipped(tmp_path):
    """The specification quotes the bare form as an example of one."""
    source = tmp_path / "spec.md"
    source.write_text(f"Two forms are errors: a bare `{HASH}65`, and a URL.\n")
    assert gr.check_unlinked([source]) == []


def test_a_double_backtick_literal_is_skipped(tmp_path):
    """Two backticks delimit a reStructuredText inline literal, where MyST uses one."""
    source = tmp_path / "guide.rst"
    source.write_text(f"Keep a colour in literal markup -- ``{HASH}808080``.\n")
    assert gr.check_unlinked([source]) == []


def test_a_quoted_colour_is_skipped(tmp_path):
    """A colour passed to a Matplotlib call is not issue 101820."""
    source = tmp_path / "mod.py"
    source.write_text(f'axes.set_facecolor("{HASH}101820")\n')
    assert gr.check_unlinked([source]) == []


def test_a_hardcoded_url_in_a_code_span_is_skipped(tmp_path):
    """A forbidden URL is quoted as an example of one in docs spec §3.8."""
    source = tmp_path / "spec.md"
    source.write_text(f"and a hand-written `{BASE}/issues/65`.\n")
    assert gr.check_hardcoded([source]) == []


def test_a_restructuredtext_hyperlink_keeps_its_url_judged(tmp_path):
    """Backticks with a trailing underscore are a link, not a literal.

    Its text is linked, so the first assertion passes it; its URL is hardcoded, so
    the second must still see it. Blanking every backtick span for both assertions
    would let this one form state a URL that nothing objects to.
    """
    source = tmp_path / "guide.rst"
    source.write_text(f"See `{HASH}65 <{BASE}/issues/65>`_ for the rest.\n")
    assert gr.check_unlinked([source]) == []
    assert len(gr.check_hardcoded([source])) == 1


def test_a_hex_colour_with_a_letter_is_not_a_reference(tmp_path):
    """A colour carrying a letter never matched, and this pins that it cannot."""
    source = tmp_path / "spec.md"
    source.write_text(f"The label colour is {HASH}7af461 in the workflow.\n")
    assert gr.check_unlinked([source]) == []


def test_a_spaced_near_miss_is_reported_rather_than_skipped(tmp_path):
    """The detector is wider than the validator (docs spec §3.8).

    No role produces this, and nothing renders it as a link, so a detector matching
    only the well-formed shape would pass it in silence.
    """
    source = tmp_path / "spec.md"
    source.write_text(f"Closed by {HASH} 65 last week.\n")
    violations = gr.check_unlinked([source])
    assert len(violations) == 1
    assert "65" in violations[0].message


def test_a_number_sign_opening_a_line_is_not_a_reference(tmp_path):
    """Markdown writes a heading that way, and Python a whole-line comment."""
    source = tmp_path / "test_igra.py"
    source.write_text(f"{HASH} 360 degrees at 4.1 m/s\n{HASH} 3. Foundation\n")
    assert gr.check_unlinked([source]) == []


def test_the_widened_detector_reports_a_trailing_comment_too(tmp_path):
    """Pins the cost of the widening, which is a deliberate trade.

    Nothing tells a comment whose first word is a number apart from a reference that
    lost its adjacency: both put a space between the sign and the digits, mid-line.
    Reporting it is chosen over missing the reference; sharpening the detector should
    break this, so that the trade is re-decided rather than quietly reversed.
    """
    source = tmp_path / "mod.py"
    source.write_text(f"x = 1  {HASH} 3 files remain\n")
    assert len(gr.check_unlinked([source])) == 1


def test_a_misspelt_url_path_is_reported(tmp_path):
    """GitHub lists pull requests at ``pulls`` but serves one at ``pull``.

    The plural that is right for the list is wrong for the item, so this URL reaches
    no page. Validating against the canonical paths alone would pass it unmentioned.
    """
    source = tmp_path / "spec.md"
    source.write_text(f"See {BASE}/pulls/65 for the rest.\n")
    violations = gr.check_hardcoded([source])
    assert len(violations) == 1
    assert "pull" in violations[0].message


def test_a_url_naming_neither_kind_is_left_alone(tmp_path):
    """A discussion is not an issue or a pull request, and has no role to be written.

    The detector matches any path so that a misspelling reaches it; this pins that
    the breadth does not turn into a demand for a role that does not exist.
    """
    source = tmp_path / "spec.md"
    source.write_text(f"See {BASE}/discussions/12 for the rest.\n")
    assert gr.check_hardcoded([source]) == []


def test_a_one_line_docstring_does_not_hide_a_reference(tmp_path):
    """Its own delimiters are quote marks, and docs spec §3.8 puts it in scope.

    Exempting every quoted string blanked the shortest docstring there is, which is
    the form most likely to carry a regression's reference.
    """
    source = tmp_path / "test_mod.py"
    source.write_text(f'    """Regression for PR {HASH}104."""\n')
    violations = gr.check_unlinked([source])
    assert len(violations) == 1
    assert "104" in violations[0].message


def test_a_pair_of_apostrophes_does_not_hide_a_reference(tmp_path):
    """A quote mark in prose is an apostrophe, and two of them span the words between.

    The reference sits inside that span, so exempting quoted strings blanked a real
    one -- and the more ordinary the sentence, the more likely it is to happen.
    """
    source = tmp_path / "spec.md"
    source.write_text(f"It's fixed in {HASH}103, but don't regress it.\n")
    violations = gr.check_unlinked([source])
    assert len(violations) == 1
    assert "103" in violations[0].message


def test_the_corpus_excludes_the_plans_and_covers_the_specifications():
    """The plans are frozen with their references (docs spec §3.4)."""
    paths = set(gr.corpus())
    specs = REPO / "docs" / "src" / "developer" / "specs"
    assert specs / "2026-07-22-tephpy-design.md" in paths
    assert specs / "2026-08-03-published-specs-design.md" in paths
    assert REPO / "tests" / "plotting" / "test_shading.py" in paths
    frozen = "the plans are point-in-time records (docs spec §3.4)"
    assert not any("plans" in path.parts for path in paths), frozen


def test_the_repository_satisfies_the_reference_contract(capsys):
    """The live tree passes both assertions (docs spec §3.8).

    The pre-commit hook is the primary gate, but hooks are not installed in a fresh
    clone, so this is what catches a reference broken by someone who bypassed them.
    """
    assert gr.main() == 0, capsys.readouterr().out
