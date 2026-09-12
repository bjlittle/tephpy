# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The gate that holds ``MANIFEST.in`` to what the sdist actually carries.

``MANIFEST.in`` has gone stale once already: a ``prune`` entry stopped matching
when the directory it named moved, and only a hand-run ``python -m build
--sdist`` caught it (:issue:`77`). What makes that catchable now is the shape of
the manifest -- exclusions written out rather than inclusions layered over a
file finder that already took everything -- because a prune that stops matching
then leaves files the manifest no longer accounts for.
"""

from __future__ import annotations

from pathlib import Path
import tomllib

import pytest
import yaml

from tests.committed import committed_manifest
from tests.pixi_tasks import invocations

REPO = Path(__file__).parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci-wheels.yml"

#: The task the gate is run by, locally and in CI alike, and the job that runs it.
TASK = JOB = "manifest"

#: What publishes: the action that uploads a distribution to an index. Detected
#: rather than listed, so a third publisher added later is covered by having to
#: use it, and not by anyone remembering to name it here.
PUBLISHER = "pypa/gh-action-pypi-publish"

# `MANIFEST.in` prunes `.github`, so the workflow this module reads is absent
# wherever the repository is not checked out. The guard asks after the workflow's
# directory rather than the repository: nothing here reads history.
pytestmark = pytest.mark.skipif(
    not WORKFLOW.parent.is_dir(), reason="not a checkout of the repository"
)


def _tasks():
    """Return the `devs` feature's pixi tasks, by name."""
    # `devs` is one of the features the floors generator drops outright,
    # so a working-tree read would find no task table here at all --
    # failing weekly, in a job that would then file an issue about a floor.
    manifest = tomllib.loads(committed_manifest())
    return manifest["tool"]["pixi"]["feature"]["devs"]["tasks"]


def _steps():
    """Return every step of the workflow that runs a shell script."""
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return [
        step["run"]
        for job in doc["jobs"].values()
        for step in job["steps"]
        if "run" in step
    ]


def test_a_task_owns_the_gate_so_a_contributor_can_run_it():
    # The declared dependency is `check-manifest>=0.49`, and a floor nothing
    # invokes is a floor nothing tests. Naming the task rather than spelling the
    # command out in the workflow is what stops the two drifting (:issue:`120`).
    assert TASK in _tasks()
    assert "check-manifest" in _tasks()[TASK]["cmd"]


def _doc():
    """Return the workflow, parsed."""
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _needs(doc, name):
    """Return the jobs one job waits on, whether it names one or several."""
    needs = doc["jobs"][name].get("needs", [])
    return [needs] if isinstance(needs, str) else list(needs)


def _waits_on(doc, name):
    """Return every job that must have succeeded before this one starts."""
    seen, pending = set(), _needs(doc, name)
    while pending:
        job = pending.pop()
        if job not in seen:
            seen.add(job)
            pending.extend(_needs(doc, job))
    return seen


def test_nothing_is_published_without_the_gate_having_passed():
    # A gate beside the thing it guards, rather than in front of it, does not
    # guard: `build` and the publishers would run whatever this reported, and a
    # tag push would upload a distribution the manifest no longer describes.
    #
    # Asserted over the *transitive* closure, because what matters is that the
    # gate cannot be skipped and not which job happens to name it. Reached
    # today through `build`, which is also what keeps a wrong distribution from
    # being uploaded as a workflow artifact.
    doc = _doc()
    publishers = [
        name
        for name, job in doc["jobs"].items()
        if any(PUBLISHER in step.get("uses", "") for step in job["steps"])
    ]
    assert publishers, f"no job uses {PUBLISHER}; has the publisher been renamed?"
    for name in publishers:
        assert JOB in _waits_on(doc, name), f"`{name}` can publish without `{JOB}`"


def test_the_workflow_runs_the_gate_by_task_name():
    # `ci-wheels` is where it belongs: the job that builds the distributions is
    # the one that should be told when the manifest no longer describes them.
    named = {
        invocation.target for script in _steps() for invocation in invocations(script)
    }
    assert TASK in named
