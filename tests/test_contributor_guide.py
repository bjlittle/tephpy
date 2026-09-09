# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The contributor guide's pages exist and are reachable (contributor spec §3.1)."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tomllib

import pytest

from tests.pixi_tasks import closure

REPO = Path(__file__).parents[1]
DEVELOPER = REPO / "docs" / "src" / "developer"
INDEX = DEVELOPER / "index.rst"
WORKFLOWS = REPO / ".github" / "workflows"
CI_PAGE = DEVELOPER / "ci.rst"
CONTRIBUTING = DEVELOPER / "contributing.rst"
CHANGELOG_PAGE = DEVELOPER / "changelog.rst"

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


#: The suffixes GitHub Actions reads from ``.github/workflows``. Both, because
#: globbing one of them lets a workflow added under the other escape this gate
#: entirely: `ci.rst` would go incomplete while the check stayed green, which is
#: the one failure a coverage gate must not have. Every workflow here is ``.yml``
#: today and the gate does not depend on that staying true (:pull:`290` review).
SUFFIXES = ("*.yml", "*.yaml")


def workflow_names(directory: Path = WORKFLOWS) -> set[str]:
    """Every workflow in `directory`, by the name the page writes.

    Parameters
    ----------
    directory : pathlib.Path, optional
        Where to look. Defaults to this repository's workflows; the parameter
        exists so the suffix coverage above can be tested against a directory
        holding a ``.yaml`` workflow, which this repository does not.

    Returns
    -------
    set of str
        Each workflow's stem.
    """
    found = {path.stem for suffix in SUFFIXES for path in directory.glob(suffix)}
    assert found, f"no workflows found under {directory}, so this gate proves nothing"
    return found


def _committed_manifest() -> str:
    """Return the manifest this repository declares, not the one it was given.

    Read from the committed tree via ``git show HEAD:pyproject.toml`` -- not
    the working tree, and not the index either (``git show :pyproject.toml``
    would be that) -- for the reason `tests/test_floors.py` reads it the same
    way: the conda half of `ci-floors` runs this suite in a checkout whose
    `pyproject.toml` the floors generator has rewritten, down to one
    environment with every feature that tier cannot reach dropped outright
    (:issue:`155`). A working-tree read would find some of the task table
    below missing, or none of it at all -- failing weekly, hours after the
    push, in a job that would then file an issue about a floor. The distinction
    from the index is live too: a contributor who stages a new task and runs
    this suite before committing would otherwise get a pass from a manifest
    that does not yet have it.

    Guarded here rather than on the module, because history is not what the
    rest of this module needs: the four pages are, and they are on disk
    whether or not `.git` is.
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


def pixi_tasks() -> dict:
    """Every pixi task, keyed by name, as `pixi_tasks` helpers expect."""
    data = tomllib.loads(_committed_manifest())
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


def test_a_yaml_workflow_is_collected_too(tmp_path):
    # GitHub Actions reads `.yml` and `.yaml` alike, so a gate globbing one of
    # them would let a workflow added under the other go undocumented while
    # staying green -- reported on :pull:`290` by review. Tested against a
    # temporary directory because this repository has no `.yaml` workflow to
    # collect, and a gate whose coverage cannot be demonstrated is a gate
    # nobody has watched work.
    (tmp_path / "ci-yml-one.yml").write_text("on: {}\n", encoding="utf-8")
    (tmp_path / "ci-yaml-one.yaml").write_text("on: {}\n", encoding="utf-8")
    assert workflow_names(tmp_path) == {"ci-yml-one", "ci-yaml-one"}


def test_the_workflow_scan_fails_rather_than_reporting_nothing(tmp_path):
    # The empty-directory case: a scan that found nothing would leave both
    # coverage assertions passing over an empty set.
    with pytest.raises(AssertionError, match="no workflows found"):
        workflow_names(tmp_path)


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


def changelog_types_on_page() -> set[str]:
    """Return the fragment types ``changelog.rst`` names, read out of its own prose."""
    text = CHANGELOG_PAGE.read_text(encoding="utf-8")
    match = re.search(r"is one of(.*?)\.", text, flags=re.DOTALL)
    assert match, "changelog.rst does not name the fragment types"
    return set(re.findall(r"``([a-z]+)``", match[1]))


def towncrier_types() -> set[str]:
    """Every towncrier fragment type the manifest configures, by directory."""
    data = tomllib.loads(_committed_manifest())
    types = {entry["directory"] for entry in data["tool"]["towncrier"]["type"]}
    assert types, "no towncrier types found, so this gate proves nothing"
    return types


def test_the_changelog_page_names_the_same_types_towncrier_is_configured_with():
    # contributor spec §3.6 gates this pair of literals, not the fragment name
    # pattern or the `:user:` role -- both of those sit in prose that varies
    # legitimately by audience, where a literal-match gate would fire on a
    # rewording rather than on drift. The eight types are different: they are
    # a closed set copied by hand into the page's prose, and towncrier's own
    # configuration is the one place that set is declared.
    page = changelog_types_on_page()
    manifest = towncrier_types()
    missing = sorted(manifest - page)
    assert not missing, f"changelog.rst does not name {missing}"
    extra = sorted(page - manifest)
    assert not extra, (
        f"changelog.rst names {extra}, which pyproject.toml does not configure"
    )
