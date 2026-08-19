# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Reading `pixi run` out of a workflow, and resolving it against a task table.

Two workflows now name pixi tasks rather than spelling their commands out --
`ci-docs.yml` since :issue:`120` and the documentation tier of `ci-floors.yml`
since :issue:`178` -- and both are held to the manifest by tests that first have
to answer the same two questions: what does this step invoke, and what does
invoking it run?

Neither answer is a substring search. A flag's value is not the task, `--skip-deps`
changes what an invocation reaches, and an aggregate reaches commands it does not
carry. Getting any of that wrong does not fail the reader; it makes the gate above
it report confidently on something no job runs.

So this is one implementation with one set of tests -- `tests/test_pixi_tasks.py`
-- rather than a copy per workflow. Nothing here skips and nothing here reads the
index: the callers guard themselves, which is what keeps the detector of
`tests/test_floors.py` reading every guard in the module it is looking at.
"""

from __future__ import annotations

from itertools import pairwise
import re
from typing import NamedTuple

#: The `pixi run` flags these workflows use, and whether each takes the token
#: after it as its value. An unrecognised flag is refused rather than guessed
#: at, because guessing wrong shifts which token is read as the task: a flag
#: that takes a value, mistaken for one that does not, makes the *value* the
#: task, and every assertion built on this then reports on something no job runs.
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


def invocations(script):
    """Return each `pixi run` in a script, as its target, flag and certainty.

    The target is the first token that is not a flag: the name of a task where
    the step names one, and a bare command where it spells one out. Both come
    back, undistinguished -- telling them apart is what the callers are for,
    and a reader that returned only the tasks could not report the commands.

    Each invocation ends at the first shell separator, not at the newline: the
    retried steps end theirs with `; then` and the shape `ci-docs.yml` used to
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
    found = []
    for preceding, tail in pairwise(parts):
        tokens = re.split(r"[;&|\n]", tail, maxsplit=1)[0].split()
        skipped = False
        while tokens and tokens[0].startswith("-"):
            flag = tokens[0]
            assert flag in FLAGS, f"unrecognised `pixi run` flag `{flag}`"
            skipped = skipped or flag == "--skip-deps"
            tokens = tokens[2:] if FLAGS[flag] else tokens[1:]
        assert tokens, "`pixi run` with nothing after it to run"
        found.append(Invocation(tokens[0], skipped, preceding.rstrip().endswith("||")))
    return found


def closure(names, tasks):
    """Return every task that running these ones runs, dependencies included.

    A name with no task of that name behind it comes back all the same. It is
    reported by pixi, not here, but dropping it would make a `depends-on`
    pointing at nothing indistinguishable from one already satisfied -- and
    `unsatisfied` below, asking what an earlier step has left unrun, would then
    answer "nothing" for the one case where the honest answer is "all of it".
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


def runs(names, tasks):
    """Return every task with a command of its own that running these ones runs.

    An aggregate carries no command -- it exists to name others -- so counting
    it would put a task on one side of a comparison that can never appear on the
    other: `ci-docs` names the gates, never the aggregate a contributor runs, and
    a contributor runs the aggregate, never the four gates by hand. What both
    sides can be held to is the set of commands each reaches.

    A name behind which there is no task at all reaches nothing, for the same
    reason and by the same test: `depends-on` pointing at something that does not
    exist runs no command, and pixi is where that is reported.
    """
    return {name for name in closure(names, tasks) if "cmd" in tasks.get(name, {})}


def commands(script, tasks):
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
    running = [script]
    for target, skipped, _conditional in invocations(script):
        reached = {target} if skipped else closure([target], tasks)
        running.extend(
            tasks[name].get("cmd", "") for name in sorted(reached) if name in tasks
        )
    return running


def unsatisfied(steps, tasks):
    """Return each skipped dependency no earlier step ran, as step, task, missing.

    What an invocation is asked for is checked whether or not it is certain to
    run -- if it runs, it needs what it skipped -- but only what is certain to
    run is credited with having run, since a task reached down an alternative
    branch may never be reached at all.
    """
    complaints = []
    ran = set()
    for name, script in steps.items():
        for target, skipped, conditional in invocations(script):
            if target not in tasks:
                continue
            if skipped:
                missing = closure(tasks[target].get("depends-on", []), tasks) - ran
                if missing:
                    complaints.append((name, target, sorted(missing)))
            if conditional:
                continue
            ran |= {target} if skipped else closure([target], tasks)
    return complaints
