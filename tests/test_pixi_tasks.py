# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the reader the workflow gates resolve their `pixi run` steps with.

Held against a task graph written here rather than against the manifest: what
these are about is the shapes the reader has to get right, and the manifest is
one arrangement of them that happens to exercise a few. The gates that read the
real workflows live in `tests/test_docs_workflow.py` and `tests/test_floors.py`.

Nothing here reads the repository, so unlike those two this module needs no
guard for the sdist that ships the tests without `.github`.
"""

from __future__ import annotations

import pytest

from tests.pixi_tasks import Invocation, commands, invocations, runs, unsatisfied

#: A task graph neither workflow has, for the reader to be held to on shapes it
#: could grow into. The gates it feeds are about the shapes themselves, and the
#: manifest's tasks reach none of these: nothing there depends on anything that
#: touches the network, and no step chains two invocations.
GRAPH = {
    "clean": {"cmd": "make clean"},
    "fetch": {"cmd": "playwright install chromium"},
    "html": {"cmd": "make html", "depends-on": ["clean", "fetch"]},
    "check": {"cmd": "python check_links.py", "depends-on": ["html"]},
    # An aggregate, carrying no command of its own. The manifest has two and the
    # workflows name neither, which is the asymmetry `runs` exists to flatten.
    "all": {"depends-on": ["check", "fetch"]},
}


@pytest.mark.parametrize(
    ("script", "reached"),
    [
        # Running a task runs its dependencies, so a step naming one runs every
        # command in its closure. `fetch` is where the network is here, and no
        # step names it: a reader that resolved the named task alone would
        # report such a step as reaching nothing, and the budget gates of
        # `tests/test_docs_workflow.py` would then judge a step that downloads a
        # browser without knowing it does.
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
    assert commands(script, GRAPH)[1:] == reached


@pytest.mark.parametrize(
    ("names", "reached"),
    [
        # An aggregate contributes its closure and not itself. Counting itself
        # would make the comparisons in the two gate modules unequal by
        # construction: a workflow names gates, never an aggregate, so no
        # aggregate can appear on both sides and the gate would fail on every
        # manifest including a correct one.
        (["all"], {"clean", "fetch", "html", "check"}),
        # Nothing to drop, so this is the plain closure.
        (["html"], {"clean", "fetch", "html"}),
        # A `depends-on` pointing at no task runs no command. `closure` returns
        # the name regardless, so that the gate reading it can report what it
        # could not resolve; here it has to vanish, or a typo would be counted
        # as a gate that runs -- covering, in those comparisons, for the gate it
        # was a typo of.
        (["absent"], set()),
    ],
)
def test_only_tasks_with_a_command_of_their_own_are_counted(names, reached):
    assert runs(names, GRAPH) == reached


@pytest.mark.parametrize(
    ("scripts", "complaints"),
    [
        # The shape both workflows have: one step runs the build, the next skips
        # it.
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
    assert unsatisfied(steps, GRAPH) == complaints


@pytest.mark.parametrize(
    ("script", "found"),
    [
        # The shapes the workflows are written in, and the two they are not: a
        # reader with no row it fails on is a reader nothing holds to its
        # docstring, and every branch below is one some workflow depends on.
        (
            "pixi run --frozen --environment docs docs-html",
            [Invocation("docs-html", skipped=False, conditional=False)],
        ),
        (
            "pixi run --frozen --environment docs --skip-deps docs-check-links",
            [Invocation("docs-check-links", skipped=True, conditional=False)],
        ),
        # `ci-floors` runs without `--frozen`, resolving fresh on purpose, and
        # names its environment the tier it generated (:issue:`178`).
        (
            "pixi run --environment floors-docs --skip-deps docs-check-citations",
            [Invocation("docs-check-citations", skipped=True, conditional=False)],
        ),
        # A flag's value is not its target. Read as a boolean flag, `-e` would
        # leave `docs` as the first bare token and name a task that exists.
        (
            "pixi run -e docs docs-html",
            [Invocation("docs-html", skipped=False, conditional=False)],
        ),
        # Spelled out rather than named -- what `ci-docs.yml` did before
        # :issue:`120` and the documentation tier of `ci-floors.yml` before
        # :issue:`178`, and what the gates over both have to be able to see.
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
def test_the_invocation_reader_finds_the_target_however_it_is_written(script, found):
    assert invocations(script) == found


@pytest.mark.parametrize(
    ("script", "complaint"),
    [
        ("pixi run --frozen --offline docs-html", "unrecognised"),
        ("pixi run --frozen", "nothing after it"),
    ],
)
def test_the_invocation_reader_refuses_what_it_cannot_read(script, complaint):
    # Failing closed matters more here than anywhere else this reader is used: a
    # reader that shrugged at a flag it did not know would go on to name some
    # other token as the task, and the gates over both workflows would then
    # report, confidently, on a task no job runs.
    with pytest.raises(AssertionError, match=complaint):
        invocations(script)
