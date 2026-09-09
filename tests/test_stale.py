# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The stale bot's exemptions, and the standing reports they have to protect."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

from tests.by_path import SCRIPTS, load_script

REPO = Path(__file__).parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci-stale.yml"

# The suite runs from a checkout; a tree without `.github` has none of the
# scripts this module derives its expectations from. As in
# `tests/test_floors.py`, the guard asks after what this module needs rather
# than after the index: nothing here reads history.
#
# It asks after the *directory* and not after the workflow, deliberately. A
# guard naming the workflow would stand this module down wherever the workflow
# is absent -- including a checkout where someone had deleted it, which is the
# one case these assertions exist to catch. Absent `.github` is not a checkout;
# a checkout without the workflow is a failure.
pytestmark = pytest.mark.skipif(
    not SCRIPTS.is_dir(), reason="not a checkout of the repository"
)

#: Both of the action's exemption inputs, which are parsed identically.
FIELDS = ("exempt-issue-labels", "exempt-pr-labels")

#: The suffixes GitHub Actions reads from ``.github/workflows``. Both, because a
#: standing report declared in a ``.yaml`` workflow would otherwise go uncollected
#: here -- its marker would not be required in `exempt-issue-labels`, and the
#: issue it keeps could stale, close, and be replaced by one carrying none of its
#: history, which is the failure this module exists to prevent (:pull:`290`).
SUFFIXES = ("*.yml", "*.yaml")


def _exempt(field: str) -> list[str]:
    """Return the labels ``actions/stale`` will read from one exemption input.

    Parsed the way the action parses it -- ``words.split(',').map(trim)``, with
    no unquoting -- so that what this module asserts on is what the action
    would act on, rather than what the workflow looks like it says.
    """
    assert WORKFLOW.is_file(), f"the stale workflow is missing from {WORKFLOW}"
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    (step,) = doc["jobs"]["stale"]["steps"]
    return [word.strip() for word in step["with"][field].split(",")]


#: How a workflow looks up the standing issue it keeps: the label given to
#: ``gh issue list``. That lookup label *is* the marker -- it is what decides
#: whether the next run edits the existing report or files a second one -- so it
#: is the thing the exemption has to match, wherever it happens to be written.
LOOKUP = re.compile(r"gh issue list[^\n]*--label (?P<marker>[\w:-]+)")


def _script_markers() -> set[str]:
    """Return the label each standing report *script* files its issue under."""
    scripts = sorted(SCRIPTS.glob("*_issue.py"))
    # A scan that found nothing would leave every assertion below passing with
    # nothing behind it, and the honest reading of an empty scan is that the
    # scan broke.
    assert scripts, f"no report scripts found under {SCRIPTS}"
    return {load_script(path.stem).MARKER for path in scripts}


def _workflow_markers(directory: Path | None = None) -> set[str]:
    """Return the label each standing report declared *in a workflow* uses.

    Not every standing report has a script. ``ci-linkcheck`` keeps two issues
    and looks each up with ``gh issue list --label`` written inline in the
    workflow, so a gate reading only ``*_issue.py`` passed over both of them --
    which is how they reached :pull:`285` unexempt, one dispatch away from a
    report that stales, closes, and is replaced by a fresh issue carrying none
    of its history.
    """
    workflows = sorted(
        path
        for suffix in SUFFIXES
        for path in (directory or REPO / ".github" / "workflows").glob(suffix)
    )
    assert workflows, "no workflows found"
    return {
        match["marker"]
        for path in workflows
        for match in LOOKUP.finditer(path.read_text(encoding="utf-8"))
    }


def _markers() -> set[str]:
    """Return every label a standing report finds its issue by."""
    markers = _script_markers() | _workflow_markers()
    assert markers, "no standing-report markers found, so the scan broke"
    return markers


def test_a_standing_report_declared_in_a_yaml_workflow_is_collected(tmp_path):
    # GitHub Actions reads `.yml` and `.yaml` alike, so a scan globbing one of
    # them would pass over a standing report declared in the other -- its marker
    # would not be required below, and the issue it keeps could stale, close,
    # and be replaced by a fresh one carrying none of its history. That is the
    # same shape as the hole `_workflow_markers` was written to close, one
    # suffix over (:pull:`290` review).
    #
    # Against a temporary directory because this repository has no `.yaml`
    # workflow: coverage that cannot be demonstrated is coverage nobody has
    # watched work.
    lookup = "          number=$(gh issue list --state open --label {} \\\n"
    (tmp_path / "ci-in-yml.yml").write_text(lookup.format("from-yml"), encoding="utf-8")
    (tmp_path / "ci-in-yaml.yaml").write_text(
        lookup.format("from-yaml"), encoding="utf-8"
    )
    assert _workflow_markers(tmp_path) == {"from-yml", "from-yaml"}


def test_every_label_a_standing_report_files_under_is_exempt_from_staling():
    # Each report keeps *one* issue and finds it again with `--label <marker>
    # --state open`. Closed for inactivity, that issue is never looked at again:
    # the next run files a fresh one and the history carried in the old one
    # stops being read. Both reports comment on their issue on a schedule, which
    # resets the clock -- but that is a cadence happening to save them, not
    # anything holding them safe, and a report that goes quiet is exactly the
    # one that would be closed.
    #
    # Derived from the scripts rather than written out here: the marker in the
    # script is the label `gh issue list` and `gh issue create` are given, so it
    # is the thing this exemption has to match.
    assert _markers() <= set(_exempt("exempt-issue-labels"))


@pytest.mark.parametrize("field", FIELDS)
def test_no_exemption_is_written_inside_quotation_marks(field):
    # The action splits on commas and trims whitespace; it does not strip
    # quotes. A list written as `"a,b,c"` therefore exempts `"a` and `c"` --
    # neither of which names a label -- and does so silently, because a label
    # that matches nothing is indistinguishable from one that never fired.
    for label in _exempt(field):
        assert '"' not in label, f"{label!r} carries a quotation mark"
        assert "'" not in label, f"{label!r} carries a quotation mark"
