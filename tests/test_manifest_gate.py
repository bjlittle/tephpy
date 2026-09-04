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
import subprocess
import tomllib

import pytest
import yaml

from tests.pixi_tasks import invocations

REPO = Path(__file__).parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci-wheels.yml"

#: The task the gate is run by, locally and in CI alike.
TASK = "manifest"

# `MANIFEST.in` prunes `.github`, so the workflow this module reads is absent
# wherever the repository is not checked out. The guard asks after the workflow's
# directory rather than the index: nothing here reads history.
pytestmark = pytest.mark.skipif(
    not WORKFLOW.parent.is_dir(), reason="not a checkout of the repository"
)


def _committed_manifest():
    """Return the manifest this repository declares, not the one it was given.

    Read from the index for the reason `tests/test_floors.py` reads it there:
    the conda half of `ci-floors` runs this suite in a checkout whose
    `pyproject.toml` the floors generator has rewritten, down to one environment
    with every feature that tier cannot reach dropped outright (:issue:`155`).
    `devs` is one of the dropped ones, so a working-tree read would find no task
    table here at all -- failing weekly, hours after the push, in a job that
    would then file an issue about a floor.

    Guarded here rather than on the module, because history is not what the rest
    of this module needs: the workflow is, and it is on disk or the module has
    already skipped.
    """
    if not (REPO / ".git").exists():
        pytest.skip("no index to read the committed manifest from")
    return subprocess.run(
        ["git", "show", "HEAD:pyproject.toml"],  # noqa: S607
        check=True,
        capture_output=True,
        cwd=REPO,
        text=True,
    ).stdout


def _tasks():
    """Return the `devs` feature's pixi tasks, by name."""
    manifest = tomllib.loads(_committed_manifest())
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


def test_the_workflow_runs_the_gate_by_task_name():
    # `ci-wheels` is where it belongs: the job that builds the distributions is
    # the one that should be told when the manifest no longer describes them.
    named = {
        invocation.target for script in _steps() for invocation in invocations(script)
    }
    assert TASK in named
