# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the topic coverage report contract (topics spec §3.8)."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from tests.by_path import load_script
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
    report = load_script("topics_issue")
    assert report.corpus(REPO) == gated()


def test_the_matrix_names_every_used_term_and_every_quadrant():
    report = load_script("topics_issue")
    text = report.matrix(FIXTURE)
    for term in ("analysis", "diagram", "shading", "isopleths"):
        assert f"`{term}`" in text
    for quadrant in report.LABELS.values():
        assert quadrant in text


def test_an_empty_cell_is_rendered_as_a_gap_and_not_omitted():
    # `diagram` sits in `tutorials` alone, so its row has three empty cells --
    # the report's entire second job is making those visible rather than
    # collapsing the row to the one quadrant it is in.
    report = load_script("topics_issue")
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
    report = load_script("topics_issue")
    promoted = frozenset({"analysis", "diagram", "isopleths"})
    text = report.body(FIXTURE, promoted, run_url="https://example.invalid/1")
    assert report.read_state(text) == promoted


def test_changes_reports_a_newly_promoted_term():
    report = load_script("topics_issue")
    text = report.changes(frozenset({"analysis"}), frozenset({"analysis", "shading"}))
    assert text is not None
    assert "Newly promoted" in text
    assert "`shading`" in text
    assert "Newly held back" not in text


def test_changes_reports_a_newly_held_back_term():
    report = load_script("topics_issue")
    text = report.changes(frozenset({"analysis", "shading"}), frozenset({"analysis"}))
    assert text is not None
    assert "Newly held back" in text
    assert "`shading`" in text
    assert "Newly promoted" not in text


def test_changes_is_none_when_the_promoted_set_is_unchanged():
    report = load_script("topics_issue")
    same = frozenset({"analysis", "shading"})
    assert report.changes(same, same) is None


def test_reading_a_body_with_no_marker_is_an_error():
    report = load_script("topics_issue")
    with pytest.raises(ValueError, match="topics-state"):
        report.read_state("No marker here at all.")


def test_the_body_carries_the_run_url_and_the_two_recorded_limits():
    report = load_script("topics_issue")
    text = report.body(FIXTURE, frozenset({"analysis"}), "https://example.invalid/9")
    assert "https://example.invalid/9" in text
    assert "candidate for editorial judgement" in text
    assert "gaps between subjects already written about" in text
    assert "#261" in text


def test_main_dry_run_prints_the_body_and_touches_no_network(capsys, monkeypatch):
    report = load_script("topics_issue")
    calls = []
    monkeypatch.setattr(report.subprocess, "run", lambda *a, **_: calls.append(a))
    monkeypatch.setattr(sys, "argv", ["topics_issue.py", "--run-url", "u", "--dry-run"])
    assert report.main() == 0
    assert calls == []
    out = capsys.readouterr().out
    assert "## Coverage matrix" in out
    assert "<!-- topics-state:" in out


def test_main_creates_the_standing_issue_when_none_exists(monkeypatch):
    report = load_script("topics_issue")
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
    report = load_script("topics_issue")
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
    report = load_script("topics_issue")
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
    report = load_script("topics_issue")

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
    report = load_script("topics_issue")
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
    report = load_script("topics_issue")
    promoted = frozenset(report.topics.VOCABULARY)
    text = report.body(FIXTURE, promoted, run_url="u")
    assert report.read_state(text) == promoted
    empty = frozenset()
    text = report.body(FIXTURE, empty, run_url="u")
    assert report.read_state(text) == empty


def test_the_matrix_carries_a_column_total_per_quadrant():
    """The totals read across the grain of the rows (topics spec §3.8).

    A row says where one subject is covered; the totals say how many subjects a
    quadrant covers at all. `FIXTURE` gives tutorials two terms, how-tos one,
    explanation two and the gallery two, and the totals must count *distinct*
    terms rather than tag occurrences -- `analysis` appears in three quadrants
    and must count once in each, not three times in any.
    """
    report = load_script("topics_issue")
    rendered = report.matrix(FIXTURE)
    totals = [line for line in rendered.splitlines() if "terms covered" in line]
    assert len(totals) == 1, "the totals row is written once, at the foot"
    assert totals[0] == "| **terms covered** | 2 | 1 | 2 | 2 |"


def test_the_totals_count_a_quadrant_with_no_terms_as_zero():
    """A quadrant nothing covers is reported as zero, not omitted.

    The same reason every quadrant gets a column even when a term is in none of
    them: the gap is the finding, and a missing total reads as an oversight.
    """
    report = load_script("topics_issue")
    rendered = report.matrix({"a": ("tutorials", ["analysis"])})
    totals = next(line for line in rendered.splitlines() if "terms covered" in line)
    assert totals == "| **terms covered** | 1 | 0 | 0 | 0 |"


def test_too_broad_reports_a_term_selecting_exactly_half_the_corpus():
    """The breadth threshold is the exact complement of the promotion rule's.

    `promote` keeps a term selecting *fewer than* half; this reports one
    selecting half or more. Exactly half must land here, or a term at the
    boundary would be in neither and disappear from the report while also
    earning no button.
    """
    report = load_script("topics_issue")
    items = {
        "a": ("tutorials", ["broad", "narrow"]),
        "b": ("howtos", ["broad"]),
        "c": ("explanation", ["narrow"]),
        "d": ("gallery", ["narrow"]),
    }
    found = {term: count for term, count, _ in report.too_broad(items)}
    assert found == {"broad": 2, "narrow": 3}


def test_no_term_is_both_promoted_and_too_broad():
    """The two halves of the report cannot contradict each other.

    Nothing enforces this but the arithmetic agreeing, and the arithmetic lives
    in two modules -- `promote` in the taxonomy, `too_broad` here -- so a change
    to either threshold that broke the complement would otherwise show up as a
    term listed as a filter button and as too broad to be one.
    """
    report = load_script("topics_issue")
    data = report._topics_data()
    for items in (FIXTURE, report.corpus(REPO)):
        broad = {term for term, _, _ in report.too_broad(items)}
        assert not (broad & data.promote(items))


#: Four items, every term used once, so nothing reaches the breadth threshold.
DISCRIMINATING = {
    "a": ("tutorials", ["alpha"]),
    "b": ("howtos", ["beta"]),
    "c": ("explanation", ["gamma"]),
    "d": ("gallery", ["delta"]),
}


def test_the_body_omits_the_broad_section_when_nothing_is_too_broad():
    """Omitting it is the point: an always-present empty heading is noise."""
    report = load_script("topics_issue")
    data = report._topics_data()
    assert not report.too_broad(DISCRIMINATING)
    text = report.body(
        DISCRIMINATING, data.promote(DISCRIMINATING), run_url="https://e.invalid/1"
    )
    assert "Too broad to filter on" not in text


def test_the_body_carries_the_broad_section_when_something_is():
    """And carries the count, the share and the quadrants when there is one.

    The quadrants are named with this module's own lowercase `LABELS` -- the
    issue body reads as prose, where the page's buttons read as titles, so the
    two mappings differ deliberately and this pins the one used here.
    """
    report = load_script("topics_issue")
    data = report._topics_data()
    items = {
        "a": ("tutorials", ["broad", "one"]),
        "b": ("howtos", ["broad", "two"]),
        "c": ("explanation", ["three"]),
        "d": ("gallery", ["four"]),
    }
    assert len(report.too_broad(items)) == 1
    text = report.body(items, data.promote(items), run_url="https://e.invalid/1")
    assert "## Too broad to filter on (1)" in text
    assert "| `broad` | 2 of 4 | 50% | tutorials, how-tos |" in text


#: A corpus in which `beta` and `gamma` each span two quadrants and earn a
#: button. Six items, and it has to be at least six: spanning two quadrants
#: needs a term on two items, and clearing the breadth cap needs it on fewer
#: than half, so on a corpus of four the two conditions cannot both hold and
#: nothing can ever promote.
MOVED = {
    "a": ("tutorials", ["alpha", "beta"]),
    "b": ("howtos", ["beta", "gamma"]),
    "c": ("explanation", ["gamma"]),
    "d": ("gallery", ["delta"]),
    "e": ("gallery", ["epsilon"]),
    "f": ("howtos", ["zeta"]),
}


def test_the_body_marks_a_newly_promoted_term_and_only_that_term():
    """The body says what moved, not only the comment (topics spec §3.8).

    A reader opening the standing issue in a year should not have to scroll a
    year of comments to learn what recently changed.
    """
    report = load_script("topics_issue")
    data = report._topics_data()
    promoted = data.promote(MOVED)
    assert {"beta", "gamma"} <= promoted, "the fixture must promote more than one"
    # Everything but `beta` was already promoted, so `beta` alone is the arrival.
    # A `previous` of nothing would mark the whole set and prove far less.
    text = report.body(MOVED, promoted, "x", previous=promoted - {"beta"})
    assert "`beta` **(new)**" in text
    for term in sorted(promoted - {"beta"}):
        assert f"`{term}` **(new)**" not in text


def test_the_body_names_a_term_that_left_the_promoted_set():
    """The other half of the delta, for the same reason as the marker."""
    report = load_script("topics_issue")
    data = report._topics_data()
    promoted = data.promote(MOVED)
    text = report.body(MOVED, promoted, "x", previous=promoted | {"gone"})
    assert "Held back since the last run: `gone`." in text


def test_the_body_marks_nothing_on_the_run_that_creates_the_issue():
    """`previous=None` is "there was no last run", not "nothing was promoted".

    Marking all of it new on a first run would say nothing, and reporting the
    whole set as newly held back would be simply false.
    """
    report = load_script("topics_issue")
    data = report._topics_data()
    text = report.body(MOVED, data.promote(MOVED), "x", previous=None)
    assert "**(new)**" not in text
    assert "Held back since the last run" not in text


def test_the_body_and_the_comment_never_tell_different_stories():
    """The one invariant tying the two halves of the report together.

    `changes` composes the comment and the body marks the same delta, from the
    same two sets but by separate code. If they disagree, one of them is lying
    to a reader who has no way to tell which -- so the body carries a marker
    exactly when a comment is posted, and carries none when none is.
    """
    report = load_script("topics_issue")
    data = report._topics_data()
    promoted = data.promote(MOVED)
    for previous in (frozenset(), promoted, promoted | {"gone"}, frozenset({"alpha"})):
        text = report.body(MOVED, promoted, "x", previous=previous)
        marked = "**(new)**" in text or "Held back since the last run" in text
        assert marked == (report.changes(previous, promoted) is not None)


def test_the_dated_record_outlives_the_new_markers():
    """The finding on :pull:`268`: the markers alone answer for one month only.

    `(new)` means "moved at the most recent run" and is gone at the next, which
    is correct -- calling a term new a year after it promoted would be false.
    So the body also carries a dated record of when the set last moved, and that
    is what a reader arriving in a quiet month reads instead of the comments.
    """
    report = load_script("topics_issue")
    data = report._topics_data()
    promoted = data.promote(MOVED)
    record = {"at": "2026-10-01", "gained": ["beta"], "lost": []}

    moved = report.body(MOVED, promoted, "x", promoted - {"beta"}, record)
    assert "`beta` **(new)**" in moved
    assert "**Last change** — 2026-10-01: `beta` promoted." in moved

    quiet = report.body(MOVED, promoted, "x", promoted, record)
    assert "**(new)**" not in quiet
    assert "**Last change** — 2026-10-01: `beta` promoted." in quiet


def test_the_record_names_both_directions_when_both_moved():
    report = load_script("topics_issue")
    data = report._topics_data()
    record = {"at": "2026-11-01", "gained": ["beta"], "lost": ["gone"]}
    text = report.body(MOVED, data.promote(MOVED), "x", frozenset(), record)
    assert "**Last change** — 2026-11-01: `beta` promoted; `gone` held back." in text


def test_the_record_round_trips_through_the_state_marker():
    """The record is state, so it takes the round trip the promoted set takes.

    A record that cannot be read back would be silently dropped on the next
    quiet run, restoring exactly the one-month lifetime this exists to fix --
    and the body would still look correct on the run that wrote it.
    """
    report = load_script("topics_issue")
    data = report._topics_data()
    record = {"at": "2026-10-01", "gained": ["beta"], "lost": ["gone"]}
    text = report.body(MOVED, data.promote(MOVED), "x", frozenset(), record)
    assert report.read_last_change(text) == record
    assert report.read_state(text) == data.promote(MOVED)


def test_a_body_recording_no_change_yet_reads_as_none_rather_than_failing():
    """Its absence is ordinary, unlike the promoted set's.

    A body written before this was recorded -- the live issue is one -- and the
    body the creating run writes both carry no record, and neither is an error.
    """
    report = load_script("topics_issue")
    data = report._topics_data()
    text = report.body(MOVED, data.promote(MOVED), "x", None, None)
    assert report.read_last_change(text) is None
    assert "Last change" not in text
    assert report.read_last_change("no marker here at all") is None
