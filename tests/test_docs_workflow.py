# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the budgets `ci-docs` gives its network-reaching steps."""

from __future__ import annotations

import ast
from pathlib import Path
import re

import pytest
import yaml

REPO = Path(__file__).parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci-docs.yml"
SCRIPT = REPO / ".github" / "scripts" / "check_browser_demo.py"
SPEC = REPO / "docs" / "src" / "developer" / "specs" / "2026-07-22-tephpy-design.md"

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
#: checkers over its output. Together they take about forty seconds in practice.
UNBOUNDED = 6


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
    """Return every attempt bound in a script as its duration and kill grace."""
    return [
        (int(seconds), int(grace))
        for grace, seconds in re.findall(r"\btimeout\s+-k\s+(\d+)\s+(\d+)\b", script)
    ]


def _worst_case(script):
    """Return the seconds a script may take, counting everything that waits.

    Not the bare `timeout` duration: `-k` grants a further grace period before
    the kill lands, and the loop sleeps between attempts, so an accounting that
    reads the duration alone models a step shorter than the one that runs
    (:pull:`165`). Every attempt is charged a sleep whether or not the last one
    reaches it -- a budget may overstate what a step costs, never understate it.
    """
    attempts = _attempts(script)
    pause = max(
        (int(each) for each in re.findall(r"\bsleep\s+(\d+)\b", script)), default=0
    )
    longest = max((seconds + grace for seconds, grace in _bounds(script)), default=0)
    return attempts * (longest + pause)


def _section(number):
    """Return one numbered section of the specification, its heading to the next.

    Empty when the number names no section, which is a renumbering rather than
    a stale figure -- the caller says so, because a gate handed nothing to read
    reports what it lost, not what it failed to find in it.
    """
    text = SPEC.read_text(encoding="utf-8")
    heading = re.search(rf"^#+ {re.escape(number)} .*$", text, flags=re.MULTILINE)
    if heading is None:
        return ""
    rest = text[heading.end() :]
    following = re.search(r"^#+ ", rest, flags=re.MULTILINE)
    return rest[: following.start()] if following else rest


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


#: What a step runs to gain root. `sudo` is the literal escalation; the other
#: two are Playwright's, which shell out to `sudo apt-get` without saying so --
#: the shape has to be recognised by the spelling a caller actually uses.
ESCALATES = re.compile(r"\bsudo\b|--with-deps\b|\binstall-deps\b")


def test_no_retried_attempt_escalates_privilege():
    # A retry is only worth having if the attempt before it can be made to end,
    # and `timeout` can end only what the runner is allowed to signal. It does
    # signal its whole process group -- but a process running as root is not
    # the runner's to signal, so it survives its own bound. That is not
    # academic: `playwright install --with-deps` stalled in `apt`, outlived the
    # attempt that started it, held the dpkg lock, and failed the second
    # attempt on the lock instead of retrying the stall, so neither attempt
    # ever tested the network again (:pull:`166`).
    steps = _network_steps()
    assert steps, "no network-reaching step found in the documentation workflow"
    for name, script in steps.items():
        found = ESCALATES.findall(script)
        assert not found, (
            f"{name}: `{found[0]}` runs as root, which outlives the bound around it"
        )


def test_the_bounded_steps_fit_inside_the_job():
    # Every bound below is a worst case that nothing reaches -- the whole job
    # runs in about ninety seconds. They still have to sum to less than the
    # job's own budget, or the job timeout is what ends a stall, and a job
    # cancelled from outside reports no failing step, retries nothing and takes
    # the rest of the run's verdict with it.
    worst = sum(_worst_case(script) for script in _network_steps().values())
    budget = _job()["timeout-minutes"]
    assert worst / 60 + UNBOUNDED <= budget, (
        f"bounded steps may take {worst / 60:.0f}m, leaving under {UNBOUNDED}m "
        f"of a {budget}m job for the build"
    )


def test_the_specification_quotes_the_budget_the_job_actually_has():
    # `UNBOUNDED` above is held against the job's budget by the test before
    # this one, so the number is checked where it is used. It is also *quoted*,
    # in prose, in spec §8.7 -- and prose is where it went stale: the sentence
    # said thirty minutes for the three weeks after :pull:`165` raised the job
    # to thirty-five, because raising a workflow value is not an edit anything
    # made the author connect to a paragraph in another directory (:pull:`167`).
    #
    # Matched loosely on purpose. A pattern anchored to the whole sentence
    # would stop matching the moment that sentence is rewritten and pass by
    # finding nothing, which is the failure mode a gate over prose has; the
    # assertion that a figure was found at all is what closes it.
    #
    # Loose in what it matches, then, but not in where: read over the whole
    # document, a `35-minute bound` anywhere else in it -- another job's, a
    # later section's -- would stand in for this one after it is deleted, and
    # both assertions below would pass while the sentence they are about is
    # gone. The section is the scope, so finding nothing means what it says.
    section = _section("8.7")
    assert section, "spec §8.7 not found -- renumbered?"
    quoted = {int(minutes) for minutes in re.findall(r"(\d+)-minute bound", section)}
    assert quoted, "spec §8.7 no longer quotes a bound for the documentation job"
    assert quoted == {_job()["timeout-minutes"]}


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
    attempt = min(seconds for seconds, _grace in _bounds(demo))
    assert waits * milliseconds / 1000 < attempt, (
        f"{waits} waits of {milliseconds / 1000:.0f}s exceed the {attempt}s "
        "an attempt is given"
    )


@pytest.mark.parametrize(
    ("script", "seconds"),
    [
        # What the workflow's steps look like: the grace period and the pause
        # between attempts are charged alongside the duration, because all
        # three are wall clock the job cap is counting.
        ("for a in 1 2; do\n timeout -k 30 180 pixi run x\n sleep 15\ndone", 450),
        ("for a in 1 2 3; do\n timeout -k 5 100 pixi run x\n sleep 10\ndone", 345),
        # A bound with no retry around it still spends its grace.
        ("timeout -k 30 180 pixi run x", 210),
    ],
)
def test_the_accounting_charges_the_grace_and_the_pauses(script, seconds):
    # Reading the duration alone models a step shorter than the one that runs,
    # which is the failure this accounting had: the sum came to 26m against a
    # 35m cap while the steps as written could take 29m, so the gate passed
    # and the job cancellation it exists to prevent stayed reachable.
    assert _worst_case(script) == seconds
