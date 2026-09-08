# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The contributor guide's pages exist and are reachable (contributor spec §3.1)."""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

import pytest

from tests.pixi_tasks import closure

REPO = Path(__file__).parents[1]
DEVELOPER = REPO / "docs" / "src" / "developer"
INDEX = DEVELOPER / "index.rst"
WORKFLOWS = REPO / ".github" / "workflows"
CI_PAGE = DEVELOPER / "ci.rst"
CONTRIBUTING = DEVELOPER / "contributing.rst"

#: The pages contributor spec §3.1 adds, in the order contributor spec §4 gives
#: the toctree.
#: Each page task appends its own as it lands, so every commit is green and
#: each keeps its own red-to-green.
PAGES = ("contributing", "testing", "changelog", "ci")


@pytest.mark.parametrize("page", PAGES)
def test_each_new_page_exists(page):
    assert (DEVELOPER / f"{page}.rst").is_file()


@pytest.mark.parametrize("page", PAGES)
def test_each_new_page_is_in_the_toctree(page):
    # A page absent from every toctree is caught by the fail-on-warning build,
    # but an `:orphan:` one builds clean -- the hole tests/test_docs_landing_pages.py
    # closes for the quadrants and this closes here.
    entries = [
        line.strip()
        for line in INDEX.read_text(encoding="utf-8").splitlines()
        if line.startswith("    ") and line.strip() and not line.strip().startswith(":")
    ]
    assert page in entries


@pytest.mark.parametrize("page", PAGES)
def test_each_new_page_carries_a_reading_time_banner(page):
    # Measured 2026-09-08: test_docs_readingtime.py exempts only the two index
    # pages, so a developer page without a banner fails that gate too. Asserted
    # here as well so the failure names the page being written.
    text = (DEVELOPER / f"{page}.rst").read_text(encoding="utf-8")
    assert ".. readingtime::" in text


def workflow_names() -> set[str]:
    """Every workflow in the directory, by the name the page writes."""
    found = {path.stem for path in WORKFLOWS.glob("*.yml")}
    assert found, "no workflows found, so this gate proves nothing"
    return found


def pixi_tasks() -> dict:
    """Every pixi task, keyed by name, as `pixi_tasks` helpers expect."""
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    tasks = {
        name: task
        for feature in data["tool"]["pixi"]["feature"].values()
        for name, task in (feature.get("tasks") or {}).items()
    }
    assert tasks, "no pixi tasks found, so this gate proves nothing"
    return tasks


def named_in(page: Path, candidates: set[str]) -> set[str]:
    """Which of `candidates` the page names, matched on whole words."""
    text = page.read_text(encoding="utf-8")
    return {name for name in candidates if re.search(rf"\b{re.escape(name)}\b", text)}


def test_every_workflow_is_named_on_the_ci_page():
    # Derived from the directory, not from a list here: a fourteenth workflow
    # fails this rather than quietly going undocumented (contributor spec §3.8).
    workflows = workflow_names()
    missing = sorted(workflows - named_in(CI_PAGE, workflows))
    assert not missing, f"ci.rst does not name {missing}"


def test_the_ci_page_names_no_workflow_that_does_not_exist():
    # The other direction. A gate checking only that the page is complete passes
    # over a page describing a workflow that was deleted.
    page = CI_PAGE.read_text(encoding="utf-8")
    claimed = set(re.findall(r"``(ci-[\w-]+|codeql)``", page))
    assert claimed, "ci.rst names no workflow at all, so this gate proves nothing"
    unknown = sorted(claimed - workflow_names())
    assert not unknown, f"ci.rst names {unknown}, which do not exist"


def test_every_pixi_task_is_named_or_reachable_from_one_that_is():
    # A task the page does not name is excused exactly when running a task it
    # does name runs it -- the correction contributor spec §3.8 records.
    # Measured 2026-09-08 against the page as shipped: all seventeen tasks are
    # named directly (nine in the Task Graph table, the other eight spelled
    # out in the ASCII diagram above it), so `closure()` excuses nothing
    # today -- there is no task reachable-but-unnamed for it to reach. It
    # stays regardless, because it is what keeps this passing rather than
    # failing spuriously if the diagram is ever redrawn without spelling out
    # every task, or a task is added that only a named one depends on;
    # test_a_named_tasks_dependency_is_excused_without_being_named_itself
    # exercises that mechanism directly, since nothing on the real page does.
    tasks = pixi_tasks()
    named = named_in(CONTRIBUTING, set(tasks))
    assert named, "contributing.rst names no pixi task at all"
    orphans = sorted(set(tasks) - closure(named, tasks))
    assert not orphans, (
        f"contributing.rst neither names {orphans} nor names anything that runs them"
    )


def test_a_named_tasks_dependency_is_excused_without_being_named_itself():
    # A synthetic graph, since the real page currently names every real task
    # directly (see the comment above) and so never exercises `closure()`.
    # `clean` is named nowhere here; it is excused only because `build`,
    # which is named, depends on it.
    tasks = {
        "build": {"cmd": "make html", "depends-on": ["clean"]},
        "clean": {"cmd": "make clean"},
    }
    orphans = set(tasks) - closure({"build"}, tasks)
    assert not orphans, f"closure() failed to excuse {orphans} through depends-on"


def test_the_contributing_page_names_no_task_that_does_not_exist():
    # The Task Graph table is the one place the page asserts "this is a pixi
    # task": each row is a literal ``    * - ``name``  `` line. Reading every
    # double-backtick literal on the page instead over-claims: a bare-word
    # pattern also matches ``tephpy`` with nothing to exempt it, and
    # ``pixi run -e docs playwright install --with-deps chromium`` names a
    # real external command, not a task, so "``pixi run <token>``" cannot be
    # read as a claim of task existence either -- the module docstring of
    # `tests/pixi_tasks.py` makes the same point about workflow steps. The
    # table has neither problem, so this reads only it (contributor spec §3.8).
    text = CONTRIBUTING.read_text(encoding="utf-8")
    claimed = re.findall(r"^    \* - ``([a-z][\w-]*)``$", text, flags=re.MULTILINE)
    assert claimed, "contributing.rst's task table names no task at all"
    unknown = sorted(set(claimed) - set(pixi_tasks()))
    assert not unknown, f"contributing.rst names {unknown}, which are not pixi tasks"
