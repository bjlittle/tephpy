# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the browser demo check and the budgets `ci-docs` gives it."""

from __future__ import annotations

import ast
from pathlib import Path
import re

import pytest
import yaml

REPO = Path(__file__).parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci-docs.yml"
SCRIPT = REPO / ".github" / "scripts" / "check_browser_demo.py"

# `MANIFEST.in` prunes `.github`, so an sdist ships these tests without either
# file they read. The module is guarded rather than each test, because an
# unguarded read fails *collection* there and takes the rest of the suite with
# it -- the same reason `tests/test_floors.py` guards itself.
pytestmark = pytest.mark.skipif(
    not WORKFLOW.is_file() or not SCRIPT.is_file(),
    reason="not a checkout of the repository",
)

#: Minutes the job needs for everything that is not one of the bounded steps --
#: the checkout, the pixi environment, the documentation build and the two
#: checkers over its output. Together they take about a minute in practice.
UNBOUNDED = 9


def _job():
    """Return the sole job of the documentation workflow."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    (job,) = workflow["jobs"].values()
    return job


def _network_steps():
    """Return each step that reaches the network, by what it runs.

    Selecting on what a step does rather than on how it is written is the whole
    point: a step retrying with `||` instead of a loop is the very shape this
    gate rejects, so it has to be *found* before it can be judged. Recognizing
    only the correct shape would leave the defect exempt rather than reported.
    """
    steps = {}
    for index, step in enumerate(_job()["steps"]):
        script = step.get("run", "")
        if "playwright" in script or "check_browser_demo" in script:
            steps[step.get("name", f"step {index}")] = script
    return steps


def _attempts(script):
    """Return how many attempts a script makes, one when it does not loop."""
    loop = re.search(r"for\s+\w+\s+in\s+([\d\s]+?);\s*do", script)
    return len(loop[1].split()) if loop else 1


def _bounds(script):
    """Return the wall-clock bound on each attempt the script makes."""
    return [int(each) for each in re.findall(r"\btimeout\s+-k\s+\d+\s+(\d+)\b", script)]


def test_every_retried_attempt_is_bounded():
    # A retry covers a failure. It covers a stall only if the attempt before it
    # is made to end, and `timeout-minutes` on the step cannot do that here,
    # because both attempts live in one step and a step-level bound would
    # cancel the pair. So the bound has to be inside the shell, once per
    # attempt -- and without it the retry is decoration, which is how a stalled
    # browser install spent the job's entire budget rather than failing over.
    steps = _network_steps()
    assert steps, "no network-reaching step found in the documentation workflow"
    for name, script in steps.items():
        invocations = len(re.findall(r"\bpixi run\b", script))
        bounds = _bounds(script)
        assert invocations == len(bounds), (
            f"{name}: {invocations} invocation(s) but {len(bounds)} bounded"
        )
        assert _attempts(script) > 1, f"{name}: does not retry"


def test_the_bounded_steps_fit_inside_the_job():
    # Every bound below is a worst case that nothing reaches -- the whole job
    # runs in about ninety seconds. They still have to sum to less than the
    # job's own budget, or the job timeout is what ends a stall, and a job
    # cancelled from outside reports no failing step, retries nothing and takes
    # the rest of the run's verdict with it.
    worst = sum(
        _attempts(script) * max(_bounds(script), default=0)
        for script in _network_steps().values()
    )
    budget = _job()["timeout-minutes"]
    assert worst / 60 + UNBOUNDED <= budget, (
        f"bounded steps may take {worst / 60:.0f}m, leaving under {UNBOUNDED}m "
        f"of a {budget}m job for the build"
    )


def test_the_demo_s_waits_fit_inside_one_of_its_attempts():
    # The script bounds each wait itself, and those bounds have to fit within
    # the attempt the shell gives the script -- otherwise the shell is what
    # ends a slow run, reporting a signal, where the script would have named
    # the wait that hung and the state the demo had reached by then.
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    (assignment,) = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "TIMEOUT"
            for target in node.targets
        )
    ]
    milliseconds = ast.literal_eval(assignment.value)
    waits = sum(
        1
        for node in ast.walk(tree)
        for word in getattr(node, "keywords", [])
        if word.arg == "timeout"
        and isinstance(word.value, ast.Name)
        and word.value.id == "TIMEOUT"
    )
    assert waits > 1, "no waits found to hold against the attempt's bound"
    (demo,) = [
        script for script in _network_steps().values() if "check_browser_demo" in script
    ]
    attempt = max(_bounds(demo))
    assert waits * milliseconds / 1000 < attempt, (
        f"{waits} waits of {milliseconds / 1000:.0f}s exceed the {attempt}s "
        "an attempt is given"
    )
