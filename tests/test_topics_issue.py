# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the topic coverage report contract (topics spec §3.8)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from tests.test_docs_topics import corpus as gated

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "topics_issue.py"
WORKFLOW = REPO / ".github" / "workflows" / "ci-topics.yml"

# `MANIFEST.in` prunes `.github`, so an sdist ships these tests without the
# script they exercise. Guarding the module rather than the test is deliberate:
# an unguarded import fails *collection* there, taking the rest of the suite
# with it. As in `test_floors_issue.py`, the guard asks after the script and
# not `.git`: nothing here reads history, and a guard naming the index would
# stand the module down wherever history is absent.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="not a checkout of the repository"
)


def _load():
    """Import the issue composer by path."""
    spec = importlib.util.spec_from_file_location("topics_issue", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["topics_issue"] = module
    spec.loader.exec_module(module)
    return module


#: A corpus small enough to read at a glance, with one term spanning three
#: quadrants, one confined to a single quadrant (so the matrix has a gap to
#: render), and real vocabulary terms throughout so the round-trip test below
#: reads as the live report would.
FIXTURE = {
    "a": ("tutorials", ["analysis", "diagram"]),
    "b": ("howtos", ["analysis"]),
    "c": ("explanation", ["analysis", "shading"]),
    "d": ("gallery", ["shading", "isopleths"]),
}


def test_the_corpus_matches_the_gate_s():
    """Two readers of one corpus, and the report is the one nobody looks at.

    The gate assembles the corpus to check it and this script assembles it to
    report on it. They read the same declarations with the same functions, so a
    divergence here is a bug in one of the two assemblies -- and it would show
    up as a report quietly describing a different corpus than the one
    published.
    """
    report = _load()
    assert report.corpus(REPO) == gated()


def test_the_matrix_names_every_used_term_and_every_quadrant():
    report = _load()
    text = report.matrix(FIXTURE)
    for term in ("analysis", "diagram", "shading", "isopleths"):
        assert f"`{term}`" in text
    for quadrant in report.LABELS.values():
        assert quadrant in text


def test_an_empty_cell_is_rendered_as_a_gap_and_not_omitted():
    # `diagram` sits in `tutorials` alone, so its row has three empty cells --
    # the report's entire second job is making those visible rather than
    # collapsing the row to the one quadrant it is in.
    report = _load()
    lines = report.matrix(FIXTURE).splitlines()
    row = next(line for line in lines if line.startswith("| `diagram` |"))
    assert row.count("—") == 3
    assert row.count("✓") == 1


def test_the_state_marker_round_trips():
    """The report's one real failure mode, pinned.

    "Newly promoted since the last run" is computed by reading the previous
    promoted set back out of the issue body. A marker that cannot be read makes
    every month report every term as new, and the report would look like it was
    working -- it would be full of findings.
    """
    report = _load()
    promoted = frozenset({"analysis", "diagram", "isopleths"})
    text = report.body(FIXTURE, promoted, run_url="https://example.invalid/1")
    assert report.read_state(text) == promoted


def test_changes_reports_a_newly_promoted_term():
    report = _load()
    text = report.changes(frozenset({"analysis"}), frozenset({"analysis", "shading"}))
    assert text is not None
    assert "Newly promoted" in text
    assert "`shading`" in text
    assert "Newly held back" not in text


def test_changes_reports_a_newly_held_back_term():
    report = _load()
    text = report.changes(frozenset({"analysis", "shading"}), frozenset({"analysis"}))
    assert text is not None
    assert "Newly held back" in text
    assert "`shading`" in text
    assert "Newly promoted" not in text


def test_changes_is_none_when_the_promoted_set_is_unchanged():
    report = _load()
    same = frozenset({"analysis", "shading"})
    assert report.changes(same, same) is None


def test_reading_a_body_with_no_marker_is_an_error():
    report = _load()
    with pytest.raises(ValueError, match="topics-state"):
        report.read_state("No marker here at all.")


def test_the_body_carries_the_run_url_and_the_two_recorded_limits():
    report = _load()
    text = report.body(FIXTURE, frozenset({"analysis"}), "https://example.invalid/9")
    assert "https://example.invalid/9" in text
    assert "candidate for editorial judgement" in text
    assert "gaps between subjects already written about" in text
    assert "#261" in text


def test_main_dry_run_prints_the_body_and_touches_no_network(capsys, monkeypatch):
    report = _load()
    calls = []
    monkeypatch.setattr(report.subprocess, "run", lambda *a, **_: calls.append(a))
    monkeypatch.setattr(sys, "argv", ["topics_issue.py", "--run-url", "u", "--dry-run"])
    assert report.main() == 0
    assert calls == []
    out = capsys.readouterr().out
    assert "## Coverage matrix" in out
    assert "<!-- topics-state:" in out


def test_main_creates_the_standing_issue_when_none_exists(monkeypatch):
    report = _load()
    calls = []

    def _run(command, **_):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(report.subprocess, "run", _run)
    monkeypatch.setattr(report, "_standing_issue", lambda: None)
    monkeypatch.setattr(report, "_gh", lambda: "/usr/bin/gh")
    monkeypatch.setattr(sys, "argv", ["topics_issue.py", "--run-url", "u"])
    assert report.main() == 0
    assert [call[1:3] for call in calls] == [["issue", "create"]]
    assert report.MARKER in calls[0]


def test_main_edits_the_body_and_comments_only_when_something_changed(monkeypatch):
    report = _load()
    calls = []

    def _run(command, **_):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(report.subprocess, "run", _run)
    previous = report._state_line(frozenset())
    monkeypatch.setattr(report, "_standing_issue", lambda: ("42", previous))
    monkeypatch.setattr(report, "_gh", lambda: "/usr/bin/gh")
    monkeypatch.setattr(sys, "argv", ["topics_issue.py", "--run-url", "u"])
    assert report.main() == 0
    assert [call[1:3] for call in calls] == [["issue", "edit"], ["issue", "comment"]]


def test_main_edits_the_body_and_posts_no_comment_when_nothing_changed(monkeypatch):
    report = _load()
    calls = []

    def _run(command, **_):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(report.subprocess, "run", _run)
    items = report.corpus(REPO)
    promoted = report.topics.promote(items)
    previous = report._state_line(promoted)
    monkeypatch.setattr(report, "_standing_issue", lambda: ("42", previous))
    monkeypatch.setattr(report, "_gh", lambda: "/usr/bin/gh")
    monkeypatch.setattr(sys, "argv", ["topics_issue.py", "--run-url", "u"])
    assert report.main() == 0
    assert [call[1:3] for call in calls] == [["issue", "edit"]]


def test_a_missing_label_is_reported_comprehensibly_rather_than_a_traceback(
    monkeypatch, capsys
):
    # The `topic-coverage` label does not exist in this repository yet
    # (confirmed by hand), and `gh issue create --label` fails on a label that
    # does not exist -- that failure would otherwise be the first scheduled
    # run, and it must not be a bare traceback.
    report = _load()

    def _run(command, **_):
        if command[1:3] == ["issue", "create"]:
            raise subprocess.CalledProcessError(1, command, stderr="label not found")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(report.subprocess, "run", _run)
    monkeypatch.setattr(report, "_standing_issue", lambda: None)
    monkeypatch.setattr(report, "_gh", lambda: "/usr/bin/gh")
    monkeypatch.setattr(sys, "argv", ["topics_issue.py", "--run-url", "u"])
    assert report.main() == 1
    assert report.MARKER in capsys.readouterr().err


def test_reading_the_previous_body_with_no_marker_raises_rather_than_reports_nothing(
    monkeypatch,
):
    report = _load()
    calls = []
    monkeypatch.setattr(
        report.subprocess, "run", lambda command, **_: calls.append(command)
    )
    monkeypatch.setattr(report, "_standing_issue", lambda: ("42", "no marker here"))
    monkeypatch.setattr(report, "_gh", lambda: "/usr/bin/gh")
    monkeypatch.setattr(sys, "argv", ["topics_issue.py", "--run-url", "u"])
    with pytest.raises(ValueError, match="topics-state"):
        report.main()
    assert calls == []


def test_the_workflow_parses_as_yaml_and_the_schedule_is_monthly():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML's default resolver reads the bare scalar key `on` as the boolean
    # `True` under YAML 1.1, not the string `"on"` -- `test_floors.py`'s
    # workflow tests never index `on` and so never meet this; this one has to.
    schedule = doc[True]["schedule"]
    assert len(schedule) == 1
    _minute, _hour, day, month, _weekday = schedule[0]["cron"].split()
    assert day != "*", "not scheduled on any particular day of the month"
    assert month == "*", "pinned to one month, rather than run every month"


def test_the_report_job_is_scoped_to_issues_write_and_nothing_more_at_top():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert doc["permissions"] == {}
    assert doc["jobs"]["report"]["permissions"] == {"issues": "write"}


def test_the_run_step_names_the_script_this_module_tests():
    # The one that matters: a workflow calling a script that has been renamed
    # fails once a month, in a run nobody is watching.
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = doc["jobs"]["report"]["steps"]
    commands = " ".join(step.get("run") or "" for step in steps)
    assert f".github/scripts/{SCRIPT.name}" in commands


def test_the_checkout_pin_matches_the_floors_workflow():
    # A stale pin here is a second copy that drifts from the one `ci-floors.yml`
    # already carries.
    floors = yaml.safe_load(
        (REPO / ".github" / "workflows" / "ci-floors.yml").read_text(encoding="utf-8")
    )
    topics_doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    floors_pin = floors["jobs"]["file"]["steps"][0]["uses"]
    topics_pin = topics_doc["jobs"]["report"]["steps"][0]["uses"]
    assert topics_pin == floors_pin


def test_json_data_written_and_read_by_state_round_trips_arbitrary_terms():
    # `promote` returns whatever terms the vocabulary happens to have, so the
    # round trip has to survive a set with no members in common with the
    # fixture used elsewhere in this module -- not just the three terms the
    # headline test above pins.
    report = _load()
    promoted = frozenset(report.topics.VOCABULARY)
    text = report.body(FIXTURE, promoted, run_url="u")
    assert report.read_state(text) == promoted
    empty = frozenset()
    text = report.body(FIXTURE, empty, run_url="u")
    assert report.read_state(text) == empty
