# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the floors issue contract (floors spec §3.6)."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from tests.by_path import load_script

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "floors_issue.py"

# The suite runs from a checkout; a tree without `.github` has no script to
# exercise. Guarding the module rather than the test is deliberate: an
# unguarded import fails *collection* there, taking the rest of the suite with
# it (floors spec §5). As in `test_floors.py`, the guard asks after the
# script and not `.git`: nothing here reads history, and a guard naming the index
# would stand the module down wherever history is absent.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="not a checkout of the repository"
)


FINDING = {
    "tier": "core",
    "half": "conda",
    "package": "matplotlib-base",
    "declared": ">=3.10",
    "failure": "PyparsingDeprecationWarning: 'oneOf' deprecated",
    "lowest": "3.10.3",
    "scanned": ["3.10.0", "3.10.1", "3.10.3"],
}


def test_the_key_omits_the_half_so_one_floor_raises_one_issue():
    module = load_script("floors_issue")
    conda = module.key(FINDING)
    pypi = module.key({**FINDING, "half": "pypi"})
    assert conda == pypi


def test_the_body_carries_the_caveat_and_both_declaration_sites():
    module = load_script("floors_issue")
    text = module.body(FINDING, "https://example.invalid/run/1")
    assert "lowest version that passes what tephpy runs" in text
    assert "requirements/pypi-core.txt" in text
    assert "[tool.pixi.dependencies]" in text
    assert "https://example.invalid/run/1" in text


def test_the_scan_line_is_one_sentence_in_both_outcomes():
    # `outcome` is interpolated into a sentence here and into a list item under a
    # two-half heading, so a phrase fitting one shape and not the other reaches
    # the reader as a filed issue that does not parse. Both branches are asserted
    # because only one of them was wrong: a clause where the other returns a noun
    # phrase gave "The scan found no version at or above the floor passed".
    module = load_script("floors_issue")
    found = module.body(FINDING, "url")
    assert "The scan found **3.10.3**, the lowest that passes, of 3 tried." in found
    none = module.body({**FINDING, "lowest": None}, "url")
    assert (
        "The scan found no version at or above the floor that passes, of 3 tried."
        in none
    )


def test_an_unattributed_finding_says_so_and_names_no_declaration_site():
    # The sites are read from the culprit's declaring table, so with no culprit
    # there is nothing to read them from -- and falling back to the tier's own
    # pair is a guess that reads as established, because the core table resolves
    # into every tier (floors spec §3.1). The `test` tier is expected to produce
    # a finding of exactly this shape on the first run, so this is the issue a
    # reader meets before any other.
    module = load_script("floors_issue")
    finding = {**FINDING, "tier": "test", "package": None, "lowest": None}
    text = module.body(finding, "url")
    assert "no attribution was reached" in text
    assert "Both declaration sites need the same edit" not in text
    assert "pypi-optional-test.txt" not in text
    assert "[tool.pixi.feature.test.dependencies]" not in text


#: An unattributed finding of each shape the diagnosis produces, keyed by the
#: stage it records. The prose below is asserted against all of them together:
#: what made this a defect is that the three were indistinguishable in the
#: issue, so a test per stage would check the wording and miss the point
#: (:issue:`188`).
#:
#: Each names its stage rather than leaning on the default, which is `solve` --
#: a fixture that reaches a branch by omission cannot tell it apart from the
#: fallback, and the fallback is separately a case worth asserting.
NO_CULPRIT = {
    stage: {**FINDING, "tier": "test", "package": None, "lowest": None, "stage": stage}
    for stage in ("solve", "exercise", "unreproduced")
}


def test_only_the_verdict_that_relaxed_anything_says_it_relaxed_anything():
    # `attribute` reaches "nothing attributed" three ways and only one of them
    # runs the relaxation loop (floors spec §3.4). The issue said the sentence
    # below of all three, so a reader of the other two was told work had run
    # that never ran, and sent after a dependency conflict that did not exist:
    # :issue:`185` was the exercise branch, and what it quoted was a pytest
    # traceback.
    module = load_script("floors_issue")
    claim = "Relaxing each declared floor in turn resolved nothing"
    bodies = {
        stage: module.body(finding, "url") for stage, finding in NO_CULPRIT.items()
    }
    assert claim in bodies["solve"]
    assert claim not in bodies["exercise"]
    assert claim not in bodies["unreproduced"]
    # All three still reach the same verdict, which is the honest part and must
    # survive the branching.
    for text in bodies.values():
        assert "no attribution was reached" in text
        assert "Both declaration sites need the same edit" not in text


def test_the_solved_verdicts_say_what_is_quoted_and_that_nothing_was_relaxed():
    # The positive half of the test above: not saying the wrong thing is worth
    # little if what replaces it says nothing. Each of the two branches has to
    # tell its reader that no floor was relaxed and what the block below it
    # actually holds -- calling a pytest traceback "the solver output" is half
    # of why :issue:`185` read as a dependency conflict.
    module = load_script("floors_issue")
    exercised = module.body(NO_CULPRIT["exercise"], "url")
    assert "no floor was relaxed" in exercised
    assert "the tier's exercise then failed" in exercised
    assert "Start from the trace below." in exercised
    assert "the solver output" not in exercised
    unreproduced = module.body(NO_CULPRIT["unreproduced"], "url")
    assert "no floor was relaxed" in unreproduced
    assert "a solve that succeeded" in unreproduced
    # This one has nothing in the issue worth starting from, so it sends the
    # reader out of it rather than at a block that reproduced nothing.
    assert "Start from the run log." in unreproduced


def test_the_quoted_block_is_labelled_with_what_produced_it():
    # "failure at the declared floors" is true of all three in the sense that
    # those were the floors in force, and reads as the solve having failed --
    # which is the one thing it was not in two of them.
    module = load_script("floors_issue")
    assert "exercise failure at the declared floors (conda)" in module.body(
        NO_CULPRIT["exercise"], "url"
    )
    assert "resolved and passed here (conda)" in module.body(
        NO_CULPRIT["unreproduced"], "url"
    )
    # An attributed finding is a solve failure by construction -- relaxation is
    # what attributes -- so its label is the one that has always been there.
    assert "failure at the declared floors (conda)" in module.body(FINDING, "url")


def test_a_finding_written_before_the_stage_keeps_the_wording_it_had():
    # An artifact carrying no stage is one a `floors_diagnose.py` from before
    # this field wrote, and the sentence it was written under is the solve one.
    # Reading it as anything else would put a claim in the body that the run
    # producing it never made.
    module = load_script("floors_issue")
    assert module.stage({"tier": "test"}) == module.STAGE_SOLVE
    # Built by removing the key rather than by leaning on the fixture's own
    # `solve`: that one carries the stage explicitly, so asserting against it
    # would pass whether or not the fallback exists.
    stageless = {
        key: value for key, value in NO_CULPRIT["solve"].items() if key != "stage"
    }
    assert "stage" not in stageless
    assert "Relaxing each declared floor in turn" in module.body(stageless, "url")


def test_a_stage_this_composer_does_not_know_asserts_nothing_about_what_ran():
    # The gate in `tests/test_floors.py` holds the two vocabularies together, so
    # this is the state that gate exists to prevent reaching a runner. It must
    # still compose -- the filing job runs when everything it reports on is red,
    # and a `KeyError` there loses the issue entirely -- and it must not guess,
    # because a confident wrong sentence is the whole of what is being fixed.
    module = load_script("floors_issue")
    finding = {**NO_CULPRIT["solve"], "stage": "nonesuch"}
    assert module.stage(finding) == module.STAGE_UNKNOWN
    text = module.body(finding, "url")
    assert "no attribution was reached" in text
    assert "did not record how far it got" in text
    assert "Relaxing each declared floor in turn" not in text
    assert "no floor was relaxed" not in text


def test_two_halves_that_got_different_distances_are_not_described_as_one():
    # The halves are diagnosed separately and can stop at different stages, so
    # one issue can quote a solver conflict from one and a traceback from the
    # other. Each block is labelled by its own half's stage; the sentence that
    # sends the reader to them cannot be, so it names neither rather than
    # naming the primary's and being wrong about the other.
    module = load_script("floors_issue")
    text = module.body(
        NO_CULPRIT["solve"],
        "url",
        [{**NO_CULPRIT["exercise"], "half": "pypi"}],
    )
    assert "failure at the declared floors (conda)" in text
    assert "exercise failure at the declared floors (pypi)" in text
    assert "Start from the output quoted below." in text
    # Each half's own line says what that half did, which is the only place a
    # mixed pair can say it: everything the issue says once is about the stage,
    # and neither stage is the pair's.
    assert "- **conda:** Relaxing each declared floor in turn resolved nothing" in text
    assert "- **pypi:** The declared floors resolved and the tier's exercise" in text
    # And nothing is said once, because there is nothing true of both to say.
    for shared in module.UNATTRIBUTED_MEANS.values():
        assert shared not in text
    # And where they agree it does name it, or the neutral wording above would
    # be all any two-half issue ever got.
    agreed = module.body(
        NO_CULPRIT["exercise"],
        "url",
        [{**NO_CULPRIT["exercise"], "half": "pypi"}],
    )
    assert "Start from the trace below." in agreed


def test_a_two_half_issue_says_what_each_half_did_and_what_that_means():
    # The stage prose used to reach a reader only where one half failed, so the
    # common case -- a floor broken on both -- got the labels and the "start
    # from" pointer and none of the sentences that say what ran (:issue:`188`).
    # The unreproduced pair is the sharp instance: two halves, nothing
    # attributed, and no word anywhere that both probes *passed*.
    module = load_script("floors_issue")
    for name, ran, means in (
        (
            "exercise",
            "so no floor was relaxed at all",
            "Relaxation attributes a *solve* failure, and this tier solved.",
        ),
        (
            "unreproduced",
            "the tier's exercise then passed when re-run here",
            "This diagnosis reproduced nothing:",
        ),
        (
            "solve",
            "Relaxing each declared floor in turn resolved nothing",
            "The solver output is below verbatim.",
        ),
    ):
        text = module.body(
            NO_CULPRIT[name], "url", [{**NO_CULPRIT[name], "half": "pypi"}]
        )
        # Once per half, because it is that half's own diagnosis being reported
        # and the two are not guaranteed to agree.
        assert text.count(ran) == 2, name
        # And once for the issue, because it is about the stage rather than
        # about a half, and every sentence in it names what is quoted *below* --
        # which is both halves' blocks, and is read once.
        assert text.count(means) == 1, name


def test_an_attributed_pair_still_lists_the_two_scans_and_nothing_else():
    # The per-half line carries the stage prose only where nothing was
    # attributed. With a culprit the scan is what that half established and the
    # two genuinely differ, so this list has always been worth reading -- and a
    # stage clause bolted onto it would be the relaxation loop described twice.
    module = load_script("floors_issue")
    text = module.body(FINDING, "url", [{**FINDING, "half": "pypi", "lowest": None}])
    assert "- **conda:** **3.10.3**, the lowest that passes, of 3 tried" in text
    assert (
        "- **pypi:** no version at or above the floor that passes, of 3 tried" in text
    )
    assert "Relaxing each declared floor in turn" not in text
    for shared in module.UNATTRIBUTED_MEANS.values():
        assert shared not in text


def test_an_unattributed_pair_is_not_described_as_having_scanned():
    # A scan needs a culprit to scan (floors spec §3.5), so a two-half issue
    # with nothing attributed ran none -- and "each half scanned its own source"
    # over two lines that both say nothing was attributed is the same assertion
    # of work that never ran as the sentence above.
    module = load_script("floors_issue")
    text = module.body(
        NO_CULPRIT["solve"],
        "url",
        [{**NO_CULPRIT["solve"], "half": "pypi"}],
    )
    assert "Each half was diagnosed against its own source" in text
    assert "Each half scanned its own source" not in text
    # And where there is a culprit there was a scan, so the original wording is
    # the right one and has to survive.
    scanned = module.body(FINDING, "url", [{**FINDING, "half": "pypi"}])
    assert "Each half scanned its own source" in scanned


def test_the_stage_is_not_in_the_dedupe_key_or_the_title():
    # One floor is one issue, keyed on tier and package (floors spec §3.6). A
    # tier that fails to solve one week and fails its exercise the next is still
    # one broken thing, so the stage must not reach the key -- and because
    # `_open_issues` rebuilds the key from the *title*, it must not reach that
    # either, or the second week files a fresh issue rather than commenting.
    module = load_script("floors_issue")
    keys = {module.key(finding) for finding in NO_CULPRIT.values()}
    titles = {module.title(finding) for finding in NO_CULPRIT.values()}
    assert len(keys) == 1
    assert len(titles) == 1
    # The round trip itself, which is what the comment above depends on.
    titled = titles.pop().removeprefix("Dependency floor: ")
    assert titled.replace(" / ", "/") == keys.pop()


def test_a_tier_whose_failure_changes_shape_comments_rather_than_refiling(
    monkeypatch, tmp_path
):
    # The key equality above holds by inspection; this is it holding through
    # `main`, which is where it matters. Last week's issue was filed off a solve
    # failure and this week's finding is an exercise failure, and the two are
    # one issue -- the tier is broken either way, and a second issue every time
    # the failure changes shape is the weekly noise the dedupe exists to stop.
    module = load_script("floors_issue")
    finding = NO_CULPRIT["exercise"]
    calls = _stub(monkeypatch, module, existing={module.key(finding): "9"})
    paths = _write(tmp_path, [finding])
    monkeypatch.setattr(sys, "argv", ["floors_issue.py", *paths, "--run-url", "u"])
    assert module.main() == 0
    assert [call[1:3] for call in calls] == [["issue", "comment"]]


def test_the_declaration_sites_follow_the_declaring_table_not_the_tier():
    # The core table is resolved into every tier, so the `test` tier can fail on
    # a package declared in `[tool.pixi.dependencies]` -- which is exactly the
    # first finding expected of this job, `matplotlib-base`. Naming the tier's
    # sites would send the fix to two files that do not declare it.
    module = load_script("floors_issue")
    text = module.body({**FINDING, "tier": "test", "site": "core"}, "url")
    assert "requirements/pypi-core.txt" in text
    assert "[tool.pixi.dependencies]" in text
    assert "pypi-optional-test.txt" not in text


def test_the_issue_quotes_what_the_highest_version_tried_failed_on():
    # The baseline failure is the failure of the floors as declared, which the
    # reader knows before opening the issue -- it is why the tier is red. Where
    # nothing passed, what the candidates failed on is the finding, and
    # :issue:`145` threw it away: it reported no passing `sphinx-design`,
    # when 0.6.1 passes and every candidate had been stopped by a second broken
    # floor. Naming the version the trace belongs to matters as much as the
    # trace: a reader who cannot see how far the scan got cannot tell an
    # unsolvable package from one blocked by something else (:issue:`149`).
    module = load_script("floors_issue")
    finding = {**FINDING, "lowest": None, "blocked": "Unable to read file"}
    text = module.body(finding, "url")
    assert "3.10.3, the highest version tried, and what it failed on" in text
    assert "Unable to read file" in text
    assert "failure at the declared floors (conda)" in text


def test_the_issue_says_why_no_passing_version_is_not_a_contradiction():
    # "Attributed X, and no version of X passes" reads as "X has no good
    # version", which is how :issue:`145` was read. The two steps ask different
    # questions -- relaxation asks whether the tier resolves, the scan asks for
    # resolve *and* exercise -- and the gap is where the second broken floor
    # sits. Tied to a quoted trace, since the sentence ends by pointing at one.
    module = load_script("floors_issue")
    stalled = module.body({**FINDING, "lowest": None, "blocked": "trace"}, "url")
    assert "ask different questions" in stalled
    found = module.body({**FINDING, "blocked": "trace"}, "url")
    assert "ask different questions" not in found
    dry = module.body({**FINDING, "lowest": None, "scanned": [], "blocked": ""}, "url")
    assert "ask different questions" not in dry
    assert "highest version tried" not in dry


def test_the_pixi_table_named_is_the_one_the_floor_is_declared_in():
    # A tier declares floors in two pixi tables, and both pair with the one
    # requirements file. Naming the dependency table by default would send the
    # reader to a table the package is not in, where the fix is to add a second
    # declaration of it -- the manifest then floors it twice (:issue:`151`).
    module = load_script("floors_issue")
    finding = {**FINDING, "tier": "docs", "package": "playwright"}
    text = module.body({**finding, "table": "pypi-dependencies"}, "url")
    assert "[tool.pixi.feature.docs.pypi-dependencies]" in text
    assert "requirements/pypi-optional-docs.txt" in text
    conda = module.body(finding, "url")
    assert "[tool.pixi.feature.docs.dependencies]" in conda
    assert "pypi-dependencies" not in conda


def _stub(monkeypatch, module, existing=None):
    """Stub out `gh`; return the list that records each argv `main` runs."""
    calls = []

    def _run(command, **_):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module.subprocess, "run", _run)
    monkeypatch.setattr(module, "_open_issues", lambda: existing or {})
    monkeypatch.setattr(module, "_gh", lambda: "/usr/bin/gh")
    return calls


def _write(tmp_path, findings):
    """Write each finding as an artifact; return the paths as `main` takes them."""
    paths = []
    for finding in findings:
        path = tmp_path / f"finding-{finding['half']}-{finding['tier']}.json"
        path.write_text(json.dumps(finding), encoding="utf-8")
        paths.append(str(path))
    return paths


def test_an_unattributed_finding_comments_rather_than_refiling(monkeypatch, tmp_path):
    # `_open_issues` rebuilds each key from the issue title, so a key that does
    # not round-trip through `title` never matches an issue already open and the
    # weekly run files another. The unattributed finding is the one whose two can
    # differ, and it is not hypothetical: the `test` tier solves and fails its
    # exercise today, which is exactly the finding that carries no package.
    module = load_script("floors_issue")
    finding = {**FINDING, "package": None, "lowest": None}
    titled = module.title(finding).removeprefix("Dependency floor: ")
    assert module.key(finding) == titled.replace(" / ", "/")
    calls = _stub(monkeypatch, module, existing={module.key(finding): "7"})
    paths = _write(tmp_path, [finding])
    monkeypatch.setattr(sys, "argv", ["floors_issue.py", *paths, "--run-url", "u"])
    assert module.main() == 0
    assert [call[1:3] for call in calls] == [["issue", "comment"]]


def test_both_halves_of_one_floor_file_one_issue(monkeypatch, tmp_path):
    # The key omits the half so that one floor is one issue, but the open-issue
    # map is read once, before anything is filed -- so without grouping the pypi
    # half cannot see the issue the conda half just created, and files a second
    # under the same title. The `key` equality above holds either way, which is
    # why telling the two apart takes filing two artifacts (floors spec §3.6).
    module = load_script("floors_issue")
    calls = _stub(monkeypatch, module)
    paths = _write(tmp_path, [FINDING, {**FINDING, "half": "pypi"}])
    monkeypatch.setattr(sys, "argv", ["floors_issue.py", *paths, "--run-url", "u"])
    assert module.main() == 0
    assert [call[1:3] for call in calls] == [["issue", "create"]]
    # And the one issue reports each half, because a package can be at a
    # different version in the channel and the index (floors spec §3.5).
    body = calls[0][calls[0].index("--body") + 1]
    assert "conda" in body
    assert "pypi" in body


def test_no_artifacts_is_refused_rather_than_reported_as_nothing_wrong(
    monkeypatch, tmp_path
):
    # The filing job runs only when a tier failed, so reaching it with nothing to
    # read means the diagnosis did not produce its artifact. Exiting 0 there is
    # indistinguishable from a run that found nothing to file, which is the one
    # thing this job must never say while something is broken.
    module = load_script("floors_issue")
    calls = _stub(monkeypatch, module)
    missing = str(tmp_path / "findings" / "*.json")
    monkeypatch.setattr(sys, "argv", ["floors_issue.py", missing, "--run-url", "u"])
    assert module.main() == 1
    assert calls == []


def test_the_issue_names_the_package_as_the_file_it_sends_you_to_spells_it():
    # The issue is keyed and titled on the manifest's spelling, so that one floor
    # is one issue whichever half found it (floors spec §3.6) -- and a reader
    # sent to the requirements file with only that name finds no such line, the
    # package being `matplotlib` there. The body sends them to both files to make
    # the same edit, so it has to name both lines.
    module = load_script("floors_issue")
    text = module.body({**FINDING, "alias": "matplotlib"}, "url")
    assert "`requirements/pypi-core.txt` — declared there as `matplotlib`" in text
    # And says nothing where the two sites agree, which is most of them: an
    # "also known as" reading back the name above it is noise on every issue.
    assert "declared there as" not in module.body(FINDING, "url")


def test_the_requirements_file_named_is_the_one_declaring_the_floor():
    # The two sites need not floor a package in the same tier: `setuptools_scm`
    # is a `test` requirement and a core declaration in the manifest, so reading
    # both files off one key names one of them wrongly -- and names it as a file
    # to make the same edit in, where there is no such line to edit.
    module = load_script("floors_issue")
    text = module.body(
        {
            **FINDING,
            "tier": "test",
            "package": "setuptools-scm",
            "site": "core",
            "requirements": "requirements/pypi-optional-test.txt",
            "alias": "setuptools_scm",
        },
        "url",
    )
    assert "`pyproject.toml`, `[tool.pixi.dependencies]`" in text
    assert "requirements/pypi-optional-test.txt" in text
    assert "requirements/pypi-core.txt" not in text


def test_a_floor_declared_for_pixi_alone_names_one_line():
    # The manifest declares packages the pip requirements have no counterpart
    # for -- `make`, which drives the documentation build. Telling that reader
    # that "both declaration sites need the same edit" and naming a file with no
    # such line reads as a line they failed to find, so the body says instead
    # that this floor is declared once. An absent key is a finding from before
    # the diagnosis answered this, and keeps the pairing it was read with.
    module = load_script("floors_issue")
    finding = {**FINDING, "tier": "docs", "package": "make", "site": "docs"}
    text = module.body({**finding, "requirements": ""}, "url")
    assert "Declared for pixi alone" in text
    assert "requirements/" not in text
    # The caveat of floors spec §3.5 is about the scanned version, not about the
    # declaration, so it is owed to this reader too.
    assert module.CAVEAT in text
    assert "requirements/pypi-optional-docs.txt" in module.body(finding, "url")
