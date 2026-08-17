# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the budgets `ci-docs` gives its network-reaching steps."""

from __future__ import annotations

import ast
from itertools import pairwise
from pathlib import Path
import re
import subprocess
import tomllib
from typing import NamedTuple

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


#: The `pixi run` flags this workflow uses, and whether each takes the token
#: after it as its value. An unrecognised flag is refused rather than guessed
#: at, because guessing wrong shifts which token is read as the task: a flag
#: that takes a value, mistaken for one that does not, makes the *value* the
#: task, and every assertion below then reports on something no job runs.
FLAGS = {
    "--frozen": False,
    "--environment": True,
    "-e": True,
    "--skip-deps": False,
}


class Invocation(NamedTuple):
    """One `pixi run` in a step's script.

    `conditional` is what separates what a step *may* run from what it is
    certain to: a caller asking whether a step reaches the network wants both,
    and a caller asking what an earlier step has already run may count only the
    second.
    """

    target: str
    skipped: bool
    conditional: bool


def _invocations(script):
    """Return each `pixi run` in a script, as its target, flag and certainty.

    The target is the first token that is not a flag: the name of a task where
    the step names one, and a bare command where it spells one out. Both come
    back, undistinguished -- telling them apart is what the callers are for,
    and a reader that returned only the tasks could not report the commands.

    Each invocation ends at the first shell separator, not at the newline: the
    retried steps end theirs with `; then` and the shape this workflow used to
    have chained two with `||`, so reading to the end of the line would take
    `docs-browser-test;` for a task name and miss the second invocation whole.

    An invocation is conditional when `||` is what precedes it, because then it
    runs only if what came before it failed. `&&` is not conditional here, and
    the asymmetry is the point: after `&&` an invocation runs only once its
    left-hand side has succeeded, so by the time it runs everything before it
    has run -- and a chain that never gets there fails its step, which takes
    every later step with it. After `||`, nothing of the sort is promised.
    """
    parts = re.split(r"\bpixi run\b", script.replace("\\\n", " "))
    invocations = []
    for preceding, tail in pairwise(parts):
        tokens = re.split(r"[;&|\n]", tail, maxsplit=1)[0].split()
        skipped = False
        while tokens and tokens[0].startswith("-"):
            flag = tokens[0]
            assert flag in FLAGS, f"unrecognised `pixi run` flag `{flag}`"
            skipped = skipped or flag == "--skip-deps"
            tokens = tokens[2:] if FLAGS[flag] else tokens[1:]
        assert tokens, "`pixi run` with nothing after it to run"
        invocations.append(
            Invocation(tokens[0], skipped, preceding.rstrip().endswith("||"))
        )
    return invocations


def _closure(names, tasks):
    """Return every task that running these ones runs, dependencies included.

    A name with no task of that name behind it comes back all the same. It is
    reported by pixi, not here, but dropping it would make a `depends-on`
    pointing at nothing indistinguishable from one already satisfied -- and the
    gate below, asking what an earlier step has left unrun, would then answer
    "nothing" for the one case where the honest answer is "all of it".
    """
    reached = set()
    pending = list(names)
    while pending:
        name = pending.pop()
        if name in reached:
            continue
        reached.add(name)
        pending.extend(tasks.get(name, {}).get("depends-on", []))
    return reached


def _steps():
    """Return every step that runs a shell script, by the name it reports under."""
    return {
        step.get("name", f"step {index}"): step["run"]
        for index, step in enumerate(_job()["steps"])
        if "run" in step
    }


def _commands(script, tasks):
    """Return everything a script runs: itself, and each task command it reaches.

    A step naming `docs-browser-test` runs the demo without containing a word
    of it, so a caller judging the script alone judges half of what the step
    does.

    Reaching is transitive, because running a task runs its dependencies too: a
    build step that names only `docs-html` runs whatever `docs-html` comes to
    depend on, and a dependency that fetched an inventory over the network
    would otherwise be work no caller here could see. Unless the invocation
    skips them -- then the task really does run alone, and charging it with its
    closure would credit the step with the work the flag exists to avoid.
    """
    commands = [script]
    for target, skipped, _conditional in _invocations(script):
        reached = {target} if skipped else _closure([target], tasks)
        commands.extend(
            tasks[name].get("cmd", "") for name in sorted(reached) if name in tasks
        )
    return commands


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
        run = "\n".join(_commands(script, tasks))
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
#: three tasks, still non-empty, still passing anything looser than this.
GATES = {"docs-html", "docs-check-citations", "docs-check-links", "docs-browser-test"}


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
        for invocation in _invocations(script)
        if invocation.target in tasks
    }
    assert named == GATES


def _unsatisfied(steps, tasks):
    """Return each skipped dependency no earlier step ran, as step, task, missing.

    What an invocation is asked for is checked whether or not it is certain to
    run -- if it runs, it needs what it skipped -- but only what is certain to
    run is credited with having run, since a task reached down an alternative
    branch may never be reached at all.
    """
    complaints = []
    ran = set()
    for name, script in steps.items():
        for target, skipped, conditional in _invocations(script):
            if target not in tasks:
                continue
            if skipped:
                missing = _closure(tasks[target].get("depends-on", []), tasks) - ran
                if missing:
                    complaints.append((name, target, sorted(missing)))
            if conditional:
                continue
            ran |= {target} if skipped else _closure([target], tasks)
    return complaints


def test_no_step_skips_a_dependency_no_earlier_step_ran():
    # `--skip-deps` is here because pixi deduplicates a shared dependency
    # within one invocation and not across several: three steps each invoking
    # their own task would run `docs-clean` and the Sphinx build three times
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
    complaints = _unsatisfied(_steps(), _tasks())
    assert not complaints, "\n".join(
        f"{step}: `{target}` skips {missing}, which no earlier step has run"
        for step, target, missing in complaints
    )


#: A task graph this workflow does not have, for the readers above to be held
#: to on shapes it could grow into. The gates they feed are about the shapes
#: themselves, and today's four tasks reach none of them: nothing here depends
#: on anything that touches the network, and no step chains two invocations.
GRAPH = {
    "clean": {"cmd": "make clean"},
    "fetch": {"cmd": "playwright install chromium"},
    "html": {"cmd": "make html", "depends-on": ["clean", "fetch"]},
    "check": {"cmd": "python check_links.py", "depends-on": ["html"]},
}


@pytest.mark.parametrize(
    ("script", "reached"),
    [
        # Running a task runs its dependencies, so a step naming one runs every
        # command in its closure. `fetch` is where the network is here, and no
        # step names it: a reader that resolved the named task alone would
        # report this step as reaching nothing, and the three gates above would
        # then judge a step that downloads a browser without knowing it does.
        ("pixi run html", ["make clean", "playwright install chromium", "make html"]),
        # `--skip-deps` runs the task by itself, so the closure is *not* what it
        # reaches -- resolving it the same way would credit this step with work
        # the flag exists to prevent it doing.
        ("pixi run --skip-deps html", ["make html"]),
        # A command spelled out belongs to no task and resolves to nothing.
        ("make -C docs html", []),
    ],
)
def test_the_command_reader_follows_what_a_task_depends_on(script, reached):
    assert _commands(script, GRAPH)[1:] == reached


@pytest.mark.parametrize(
    ("scripts", "complaints"),
    [
        # The shape the workflow has: one step runs the build, the next skips it.
        (["pixi run html", "pixi run --skip-deps check"], []),
        # Retried with `||`, the shape :pull:`166` replaced. The first attempt
        # runs whatever happens, so the task is run either way.
        (["pixi run html || pixi run html", "pixi run --skip-deps check"], []),
        # `&&` is not conditional for this accounting: the right-hand side runs
        # only once the left has succeeded, and a step whose chain never gets
        # there fails, taking every later step with it. So anything reached
        # after `&&` was reached by everything before it.
        (["pixi run clean && pixi run html", "pixi run --skip-deps check"], []),
        # `||` is. `html` runs only if `clean` *fails*, so a later step skipping
        # its dependencies is reading a build that need never have happened --
        # and the gate has to say so rather than count the alternative as done.
        (
            ["pixi run clean || pixi run html", "pixi run --skip-deps check"],
            [("step 2", "check", ["fetch", "html"])],
        ),
    ],
)
def test_the_gate_credits_only_what_a_step_is_certain_to_have_run(scripts, complaints):
    steps = {f"step {number}": script for number, script in enumerate(scripts, 1)}
    assert _unsatisfied(steps, GRAPH) == complaints


@pytest.mark.parametrize(
    ("script", "invocations"),
    [
        # The shapes this workflow is written in, and the two it is not: a
        # reader with no row it fails on is a reader nothing holds to its
        # docstring, and every branch below is one the workflow depends on.
        (
            "pixi run --frozen --environment docs docs-html",
            [Invocation("docs-html", skipped=False, conditional=False)],
        ),
        (
            "pixi run --frozen --environment docs --skip-deps docs-check-links",
            [Invocation("docs-check-links", skipped=True, conditional=False)],
        ),
        # A flag's value is not its target. Read as a boolean flag, `-e` would
        # leave `docs` as the first bare token and name a task that exists.
        (
            "pixi run -e docs docs-html",
            [Invocation("docs-html", skipped=False, conditional=False)],
        ),
        # Spelled out rather than named -- what this workflow did before
        # :issue:`120`, and what the gate above has to be able to see.
        (
            "pixi run --frozen --environment docs make -C docs html",
            [Invocation("make", skipped=False, conditional=False)],
        ),
        # Inside a retry: continued across a line, and closed by `; then`. The
        # condition of an `if` is evaluated whatever happens, so this is not one
        # of the conditional shapes -- the retry is in the loop around it.
        (
            (
                "for a in 1 2; do\n  if timeout -k 30 480 pixi run --frozen \\\n"
                "      --skip-deps docs-browser-test; then\n    exit 0\n  fi\ndone"
            ),
            [Invocation("docs-browser-test", skipped=True, conditional=False)],
        ),
        # Chained with `||`, the shape :pull:`166` replaced. Both attempts are
        # invocations; reading to the end of the line would find one. Only the
        # second is conditional -- the first runs before anything can fail.
        (
            "pixi run --frozen docs-html || pixi run --frozen docs-html",
            [
                Invocation("docs-html", skipped=False, conditional=False),
                Invocation("docs-html", skipped=False, conditional=True),
            ],
        ),
        # Chained with `&&`, and across a line break, so that the certainty is
        # read from the separator rather than from what happens to be adjacent.
        (
            "pixi run --frozen clean &&\n  pixi run --frozen docs-html",
            [
                Invocation("clean", skipped=False, conditional=False),
                Invocation("docs-html", skipped=False, conditional=False),
            ],
        ),
        # Nothing to find is a legitimate answer, not a failure to look.
        ("playwright install chromium", []),
    ],
)
def test_the_invocation_reader_finds_the_target_however_it_is_written(
    script, invocations
):
    assert _invocations(script) == invocations


@pytest.mark.parametrize(
    ("script", "complaint"),
    [
        ("pixi run --frozen --offline docs-html", "unrecognised"),
        ("pixi run --frozen", "nothing after it"),
    ],
)
def test_the_invocation_reader_refuses_what_it_cannot_read(script, complaint):
    # Failing closed matters more here than anywhere else in this module: a
    # reader that shrugged at a flag it did not know would go on to name some
    # other token as the task, and the two gates above would then report,
    # confidently, on a task the job does not run.
    with pytest.raises(AssertionError, match=complaint):
        _invocations(script)


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
