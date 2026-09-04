# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for what `ci-docs` runs, and the budgets it gives its network steps.

The gates the job runs are named by their pixi task rather than spelled out
(:issue:`120`), so what the job checks and what a contributor checks locally are
the same set written twice -- once in the workflow and once in the `docs` task
table. Both directions are held here.

Reading a `pixi run` step and resolving it against that table is
`tests/pixi_tasks.py`, shared with the gate over `ci-floors.yml`, whose
documentation tier names its tasks the same way (:issue:`178`).
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess
import tomllib

import pytest
import yaml

from tests.by_path import load_script
from tests.pixi_tasks import commands, invocations, runs, unsatisfied

REPO = Path(__file__).parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci-docs.yml"
SCRIPTS = REPO / ".github" / "scripts"
SCRIPT = SCRIPTS / "check_browser_demo.py"
SPEC = REPO / "docs" / "src" / "developer" / "specs" / "2026-07-22-tephpy-design.md"

# `MANIFEST.in` prunes `.github`, so an sdist ships these tests without either
# file they read. The module is guarded rather than each test, because an
# unguarded read fails *collection* there and takes the rest of the suite with
# it -- the same reason `tests/test_floors.py` guards itself.
pytestmark = pytest.mark.skipif(
    not WORKFLOW.is_file() or not SCRIPT.is_file(),
    reason="not a checkout of the repository",
)


#: The demo script, imported rather than only parsed. It reaches Playwright from
#: inside `main()` precisely so that this import needs nothing the `test`
#: environments lack -- they carry no `docs` feature, and a module-scope import
#: of Playwright would turn everything below that reads this into a skip.
demo = load_script("check_browser_demo") if SCRIPT.is_file() else None

#: Minutes the job needs for everything that is not one of the bounded steps --
#: the checkout, the pixi environment, the documentation build and the five
#: checkers over its output. Together they take about forty seconds in practice.
UNBOUNDED = 6


def _job():
    """Return the sole job of the documentation workflow."""
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    (job,) = workflow["jobs"].values()
    return job


def _committed_manifest():
    """Return the manifest this repository declares, not the one it was given.

    Read from the index for the reason `tests/test_floors.py` reads it there:
    the conda half of `ci-floors` runs this suite in a checkout whose
    `pyproject.toml` the floors generator has rewritten, down to one
    environment with every feature that tier cannot reach dropped outright
    (:issue:`155`). `docs` is one of the dropped ones, so a working-tree read
    would find no task table here at all -- failing weekly, hours after the
    push, in a job that would then file an issue about a floor.

    Guarded here rather than on the module, because a module-level `skipif`
    naming the index stands all of it down wherever history is absent, and
    history is not what the rest of this module needs: `ci-docs.yml` and the
    demo script are, and both are on disk or the module has already skipped.
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
    """Return the `docs` feature's pixi tasks, by name."""
    manifest = tomllib.loads(_committed_manifest())
    return manifest["tool"]["pixi"]["feature"]["docs"]["tasks"]


def _steps():
    """Return every step that runs a shell script, by the name it reports under."""
    return {
        step.get("name", f"step {index}"): step["run"]
        for index, step in enumerate(_job()["steps"])
        if "run" in step
    }


def _network_steps():
    """Return each step that reaches the network, by everything it runs.

    Selecting on what a step does rather than on how it is written is the whole
    point: a step retrying with `||` instead of a loop is the very shape this
    gate rejects, so it has to be *found* before it can be judged. Recognising
    only the correct shape would leave the defect exempt rather than reported.

    Which is why the value is everything the step runs, joined, and not the
    script alone -- a step that stopped spelling its command out would stop
    being found, and the three tests below would narrow to the one step left,
    each still passing, each still asserting it had found something.
    """
    tasks = _tasks()
    steps = {}
    for name, script in _steps().items():
        run = "\n".join(commands(script, tasks))
        if "playwright" in run or "check_browser_demo" in run:
            steps[name] = run
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


#: The tasks `ci-docs` exists to run. Held by membership rather than by count
#: or by "at least one": the failure this gate is for is a gate that stops
#: being run, and a job that dropped `docs-check-links` would still be running
#: five tasks, still non-empty, still passing anything looser than this.
GATES = {
    "docs-html",
    "docs-check-api",
    "docs-check-citations",
    "docs-check-links",
    "docs-check-figures",
    "docs-check-tooltips",
    "docs-browser-test",
}


def test_the_workflow_runs_the_documentation_gates_by_task_name():
    # The commands these tasks own were spelled out here as well as in
    # `pyproject.toml` for as long as both existed, so the same check was
    # written twice and could be changed once (:issue:`120`). Naming the task
    # is what makes that impossible rather than merely unlikely -- there is no
    # second copy left to drift from.
    tasks = _tasks()
    named = {
        invocation.target
        for script in _steps().values()
        for invocation in invocations(script)
        if invocation.target in tasks
    }
    assert named == GATES


#: The local aggregates: the one `CONTRIBUTING.md` and the pull-request template
#: name, and the one that adds the gate it leaves out.
FAST = "docs"
FULL = "docs-all"

#: What `FAST` is allowed not to run. Written down rather than derived, because
#: the split is a decision and not an accident: the browser demo needs a Chromium
#: no environment here installs, so holding it out keeps a docstring fix from
#: failing in a page of browser log (:issue:`171`). Derive this from the manifest
#: and every later omission looks like the intended one.
EXEMPT = {"docs-browser-test"}


def test_the_local_aggregates_run_every_gate_the_workflow_runs():
    # The other half of the test above. That one keeps the workflow naming the
    # tasks; this one keeps the tasks covering the workflow -- and the set is
    # still written out by hand in the manifest, so a gate added to `ci-docs`
    # and to no aggregate is a gate no contributor can run before pushing.
    #
    # The total alone would not say it. `docs` is the aggregate people actually
    # run, and a gate moved out of it into `docs-all` leaves the total intact
    # while quietly making that gate CI-only, which is the arrangement this
    # issue was filed about. So the split is asserted too, in both directions:
    # what the fast check omits, and that it omits nothing else.
    tasks = _tasks()
    assert runs([FULL], tasks) == runs(GATES, tasks)
    assert runs(GATES, tasks) - runs([FAST], tasks) == EXEMPT
    assert not runs([FAST], tasks) - runs(GATES, tasks)


def test_no_step_skips_a_dependency_no_earlier_step_ran():
    # `--skip-deps` is here because pixi deduplicates a shared dependency
    # within one invocation and not across several: four steps each invoking
    # their own task would run `docs-clean` and the Sphinx build four times
    # over, once per step, since `docs-html` is a dependency of each gate.
    #
    # What the flag actually skips, though, is *every* dependency, not the one
    # the preceding step happens to have supplied. A second dependency added
    # to a gate later -- an inventory fetch, a translation build -- is dropped
    # here with nothing in the diff to say so, and the gate then reads a build
    # that never had it and passes. So the flag is allowed only where an
    # earlier step has already run what it skips, dependencies of those
    # dependencies included: `docs-clean` is never invoked by any step, and is
    # covered only because the step that runs `docs-html` runs it in passing.
    complaints = unsatisfied(_steps(), _tasks())
    assert not complaints, "\n".join(
        f"{step}: `{target}` skips {missing}, which no earlier step has run"
        for step, target, missing in complaints
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
    ("reported", "commands"),
    [
        # Playwright's own wording, for a browser it never downloaded. It already
        # arrives in a box naming the command, so what this row is really for is
        # keeping the other advice *off* it: sending someone to `apt-get` as root
        # for a missing download is worse than saying nothing.
        (
            "BrowserType.launch: Executable doesn't exist at /ms-playwright/chrome",
            ["pixi run -e docs playwright install chromium"],
        ),
        # The dynamic linker's, for a browser downloaded and unable to start.
        # This is what `pixi install` and `playwright install chromium` between
        # them still leave on a machine without the system libraries -- verified
        # against this repository's own sandbox, where it is the actual failure.
        # Nothing in it names Playwright, and it arrives some forty lines into a
        # browser log, which is the whole reason for translating it.
        (
            (
                "chrome-headless-shell: error while loading shared libraries: "
                "libnspr4.so: cannot open shared object file: No such file"
            ),
            ["pixi run -e docs playwright install --with-deps chromium"],
        ),
        # Recognised as neither, so both come back rather than nothing. A
        # wording this does not know is not one it can rule anything out from.
        (
            "BrowserType.launch: Target page, context or browser has been closed",
            [
                "pixi run -e docs playwright install chromium",
                "pixi run -e docs playwright install --with-deps chromium",
            ],
        ),
    ],
)
def test_the_demo_names_what_to_install_when_chromium_will_not_start(
    reported, commands
):
    # `docs-browser-test` is the one gate `pixi run docs` leaves out, so the
    # contributor who meets this failure is one who went looking for the full
    # set on purpose (:issue:`171`). Handing them a browser log for an answer is
    # what would send them back to CI to find out what they were missing.
    advice = demo._launch_advice(reported)
    for line, command in zip(advice, commands, strict=True):
        assert line.startswith(f"{command}  (")


#: How a remedy above has to start. Playwright belongs to the `docs` feature and
#: to nothing else, so the shell that read the failure -- the one that ran
#: `pixi run docs-all` -- has no `playwright` on its `PATH`. One spelling is
#: pinned rather than any working prefix, because the point of the gate below is
#: that the two copies of these commands say the same thing.
PREFIX = "pixi run -e docs "

#: Where the second copy lives: the guide names both commands for the reader who
#: has not met the failure yet, which is where they are found before there is a
#: browser log to translate.
GUIDE = REPO / "CONTRIBUTING.md"


def test_the_advice_runs_where_it_is_read_and_the_guide_says_the_same():
    # Both halves are needed. The prefix alone leaves the guide free to drift
    # from the message; the guide alone is satisfied by two copies that agree on
    # a command neither shell can run -- which is what they did agree on until
    # now, `playwright install chromium` in both, answering a browser that will
    # not start with `command not found` (:pull:`177`).
    #
    # The guide is matched with its wrapping collapsed. These commands are long
    # enough to be wrapped mid-command in the source, and the reader sees one
    # line however the paragraph is filled.
    assert all(command.startswith(PREFIX) for _markers, command, _why in demo.MISSING)
    guide = " ".join(GUIDE.read_text(encoding="utf-8").split())
    missing = [
        command for _markers, command, _why in demo.MISSING if command not in guide
    ]
    assert not missing, f"{GUIDE.name} does not name {missing}"


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
