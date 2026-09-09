# Contributor Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A contributor can find, on the published documentation, how to get an environment and what to run, how the tests are laid out, what a changelog fragment must carry, and what every continuous-integration workflow is for — including what it means when one of them fails at them unbidden.

**Architecture:** Four hand-written reStructuredText pages in `docs/src/developer/`, promoted from four markdown files the Sphinx build has never seen, plus one page written from scratch for continuous integration. Two new gates hold the pages to the repository they describe, and one existing gate is widened to hold the shared literals. `CONTRIBUTING.md` and `changelog/README.md` shrink to pointers keeping only those literals; the `AGENTS.md` files stay as they are.

**Tech Stack:** reStructuredText, Sphinx 9.1, pydata-sphinx-theme 0.21, pixi, pytest, pre-commit, tomllib, PyYAML.

**Spec:** [`../specs/2026-09-08-contributor-guide-design.md`](../specs/2026-09-08-contributor-guide-design.md) — cited below as `contributor spec §N`. Read it alongside this plan; every task argues from a section of it.

## Global Constraints

- Every source file carries the BSD copyright header (ruff `CPY001`), exactly as `.pre-commit-config.yaml`'s `notice-rgx` spells it.
- Every pull request adds `changelog/<PR>.<type>.rst` ending with ``(:user:`claude`)``.
- Page titles follow CMOS headline style (`docs/src/developer/docs-style.rst`).
- A GitHub reference is written ``:issue:`N``` or ``:pull:`N``` in reStructuredText and ``{issue}`N``` in Markdown — never a bare `#N`, never a hand-written URL.
- Every citation of this plan's specification is written `contributor spec §N`, and every section it names must exist as a `(contributor-spec-N)=` anchor.
- Documentation links from outside the Sphinx project are absolute `https://tephpy.readthedocs.io/en/latest/<page>.html` URLs.
- `pixi run docs` must build clean; the build is fail-on-warning.
- Verify **after** committing, never before: the pre-commit hooks rewrite files.

---

## What This Plan Measured Before It Was Written

Everything below was established on 2026-09-08, before a line of the plan was written. One
finding corrected the specification, which is a living document (docs spec §3.4); that
correction is already committed and is not a task here.

**1. The task-coverage gate needs no exemption list.** `contributor spec §3.8` first
specified "an explicit internal marker in the gate" for tasks the page does not name.
`tests/pixi_tasks.py` already exports `closure(names, tasks)`, which walks `depends-on`.
Measured against the current tree: nine contributor-facing tasks — `tests`, `lint`, `docs`,
`docs-all`, `baselines`, `manifest`, `docs-figures`, `serve-html`, `tests-clean` — reach
the other **eight** through `depends-on`, and **nothing is left over**. So the rule holds
today with no hand-written exemptions. The specification was corrected before this plan was
written.

**2. Developer pages are outside three of the four documentation gates.** Measured:
`USER_SECTIONS` is `("start", "howtos", "tutorials", "explanation")` in
`tests/test_docs_landing_pages.py`, `check_glossary_links.py` and
`tests/test_docs_snippets.py`. `developer` is in none of them. Consequences for these
pages, all deliberate: no landing table is required (`contributor spec §3.1`), a `:term:`
first mention is not enforced, and **a python block on these pages is not executed**. Write
`console` blocks, not `python` blocks — an unexecuted python block on a developer page is
exactly the untested claim `{issue}`193`` is about.

**3. Reading-time banners are required, and both existing developer pages carry one.**
`tests/test_docs_readingtime.py` derives its corpus over the whole tree and exempts only
`developer/index.rst` and `developer/specs/index.rst` by name. `docs-style.rst` and
`packaging.rst` both carry `.. readingtime::`. So do all four new pages.

**4. The existing literals gate reads `CONTRIBUTING.md` whole.**
`tests/test_docs_workflow.py:433` sets `GUIDE = REPO / "CONTRIBUTING.md"` and asserts each
of `demo.MISSING`'s commands appears in it, with whitespace collapsed. So the shrunken
`CONTRIBUTING.md` of Task 6 **must keep both Playwright commands verbatim**, or that gate
fails — which is the gate working, not a problem to route around.

**5. The specifications index carries two hand-written lists.** A prefix table and a
toctree over the same documents. Both were updated when the specification landed; nothing
in this plan touches them again.

---

## File Structure

| file | responsibility |
|---|---|
| `docs/src/developer/contributing.rst` | *create* — environment, task graph, pull-request shape |
| `docs/src/developer/testing.rst` | *create* — tests tree, image comparison, the no-network rule |
| `docs/src/developer/changelog.rst` | *create* — fragment name, types, roles |
| `docs/src/developer/ci.rst` | *create* — what runs, why, and what a failure means |
| `docs/src/developer/index.rst` | *modify* — four toctree entries |
| `tests/test_contributor_guide.py` | *create* — both new gates (§3.8) |
| `tests/test_docs_workflow.py` | *modify* — widen the literals assertion (§3.6) |
| `CONTRIBUTING.md` | *modify* — reduce to pointer plus gated literals |
| `changelog/README.md` | *modify* — reduce to pointer |

Both gates live in one module because they are one idea — a page holding an accurate map
of the repository — and because they share the reading of `pyproject.toml` and
`.github/workflows/`.

---

### Task 1: The tests-tree page

**Files:**
- Create: `docs/src/developer/testing.rst`
- Modify: `docs/src/developer/index.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: the page `developer/testing`, referenced by Task 2's prose and by Task 6's pointer.

Taken first because it is the smallest promotion and it proves the page shape — banner,
title, toctree entry, build — before three more pages depend on that shape being right.

- [ ] **Step 1: Write the failing test**

Create `tests/test_contributor_guide.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The contributor guide's pages exist and are reachable (contributor spec §3.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]
DEVELOPER = REPO / "docs" / "src" / "developer"
INDEX = DEVELOPER / "index.rst"

#: The pages contributor spec §3.1 adds, in the order contributor spec §4 gives
#: the toctree. Each page task appends its own as it lands, so every commit is
#: green and each keeps its own red-to-green.
#:
#: The citation is qualified deliberately. A bare ``spec §4`` resolves — to the
#: PARENT specification's "Canonical usage" — and the pre-commit citation gate
#: checks that a citation resolves, not that it names the document meant. Bare
#: ``§4`` fails that gate outright in a real file, though not in this plan: plans
#: are dropped from the citation corpus, so only the code blocks are exposed.
PAGES = ("testing",)


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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pixi run --environment test pytest tests/test_contributor_guide.py -q`

Expected: 12 failures — four pages × three assertions, all reporting missing files.

- [ ] **Step 3: Write the page**

Create `docs/src/developer/testing.rst`. Promote `tests/AGENTS.md`, expanding each rule
with the reason it exists. Required content:

```rst
.. _developer-testing:

Testing
=======

.. readingtime::

The tests tree mirrors the ``src/tephpy`` package layout: tests for top-level modules
live at the ``tests/`` root, and every subpackage has a matching directory —
``tests/plotting/`` for ``tephpy.plotting`` — however few modules it carries.
``tephpy.samples`` is a lone ``__init__.py`` and still has ``tests/samples/``.

``tests/test_layout.py`` holds the tree to that, so a subpackage arriving without its
directory fails a test rather than waiting to be noticed. Place a new test module at the
level of the module it exercises; the shared ``fixtures/`` and ``baseline/`` directories
stay at the root.

Running the Suite
-----------------

.. code:: console

    $ pixi run tests

pytest runs with a strict configuration and ``filterwarnings = ["error"]``, so a warning
is a failure. ``pixi run tests-clean`` removes the artifacts a run leaves behind.

Image Comparison
----------------

Plotting tests compare a rendered figure against a recorded baseline with pytest-mpl,
marked ``@pytest.mark.mpl_image_compare``. Both CI and ``pixi run tests`` pass ``--mpl``,
so the comparison is enforced rather than skipped.

.. code:: console

    $ pixi run baselines

regenerates ``tests/baseline``. Reach for it when a lockfile bump moves matplotlib or
freetype, and re-verify across all three test environments afterwards — the baselines are
shared, and a regeneration that satisfies one Python can fail another.

No Test Touches the Network
---------------------------

The ingest readers are tested against recorded captures under ``tests/fixtures/io/``,
byte-faithful and with their provenance recorded beside them. Nothing in the suite makes a
request.

The reason is worth stating, because the rule costs something. A suite that reached the
University of Wyoming would fail on their outage rather than on a defect here, and a red
tick that means "somebody else is down" teaches a reader to ignore red ticks. What the rule
gives up is knowing when the archive moves under us — every gate stays green while
``tephpy.io.wyoming`` stops working. :doc:`ci` describes the scheduled job that pays that
cost instead.
```

Add `testing` to `docs/src/developer/index.rst`'s toctree, after `contributing` (which
Task 2 creates) — for now place it first; Task 2 inserts `contributing` above it.

- [ ] **Step 4: Run the tests**

Run: `pixi run --environment test pytest tests/test_contributor_guide.py -q -k testing`

Expected: the three `testing` cases PASS; the other nine still fail.

- [ ] **Step 5: Build the docs**

Run: `pixi run docs`

Expected: `build succeeded`, every gate ok. A `document isn't included in any toctree`
warning means Step 3's index edit was missed.

- [ ] **Step 6: Commit**

```bash
git add tests/test_contributor_guide.py docs/src/developer/testing.rst docs/src/developer/index.rst
git commit -m "Publish the tests tree a contributor has to work in"
```

---

### Task 2: The contributing page and the task graph

**Files:**
- Create: `docs/src/developer/contributing.rst`
- Modify: `docs/src/developer/index.rst`

**Interfaces:**
- Consumes: `developer/testing` from Task 1, cross-referenced by `:doc:`.
- Produces: the page `developer/contributing`, whose task names Task 5's gate reads.

- [ ] **Step 1: Write the page**

Create `docs/src/developer/contributing.rst`. Promote `CONTRIBUTING.md` and add the task
graph of `contributor spec §3.7`. The nine task names measured in finding 1 must all
appear, because Task 5's gate asserts exactly that:

```rst
.. _developer-contributing:

Contributing to tephpy
======================

.. readingtime::

``tephpy`` develops with `pixi <https://pixi.sh>`__, which reads its environments from
``pyproject.toml`` and needs no setup of its own:

.. code:: console

    $ git clone git@github.com:bjlittle/tephpy.git
    $ cd tephpy
    $ pixi run tests

The first run builds the environment it needs. ``pixi run <task>`` selects that
environment for you, so there is normally no ``--environment`` to remember.

What to Run
-----------

Three commands are what a pull request must pass:

.. code:: console

    $ pixi run tests
    $ pixi run lint
    $ pixi run docs

``pixi run docs`` builds the documentation and runs every gate over the result. It is the
one to reach for. ``pixi run docs-all`` adds the gate it leaves out — a smoke test of the
browser demo in Chromium.

The Task Graph
--------------

Seventeen tasks are declared; about nine are worth knowing. The rest are steps these run
on your behalf:

.. code:: text

    docs-clean ─→ docs-html ─→ docs-check-api        ─┐
                            ─→ docs-check-citations   │
                            ─→ docs-check-figures     ├─→ docs ─┐
                            ─→ docs-check-links       │         ├─→ docs-all
                            ─→ docs-check-tooltips   ─┘         │
                            ─→ docs-browser-test ────────────────┘

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Task
      - What it does
    * - ``tests``
      - The suite, with image comparison enforced (:doc:`testing`)
    * - ``tests-clean``
      - Removes what a test run leaves behind
    * - ``baselines``
      - Regenerates the pytest-mpl baselines
    * - ``lint``
      - Every pre-commit hook, over every file
    * - ``docs``
      - Builds the documentation and runs every gate over the result
    * - ``docs-all``
      - ``docs``, plus the browser demo's smoke test
    * - ``docs-figures``
      - Regenerates the published figures' baselines
    * - ``serve-html``
      - Serves the built HTML locally
    * - ``manifest``
      - Checks ``MANIFEST.in`` against what the sdist carries

The Browser Demo Needs a Browser
--------------------------------

``pixi run docs-all`` runs Playwright, which lives in the ``docs`` environment and is on no
other ``PATH``. Install a browser once:

.. code:: console

    $ pixi run -e docs playwright install chromium

On Linux the browser also needs system libraries pixi does not provide, which
``pixi run -e docs playwright install --with-deps chromium`` adds as root. Both go through
pixi for the same reason. If the browser will not start, the check says which of the two is
missing and names it the same way.

What a Pull Request Carries
---------------------------

- A changelog fragment — see :doc:`changelog`.
- A passing ``pixi run docs`` where the documentation changed.
- Prose reviewed against *Reviewing Claims* in :doc:`docs-style`.

:doc:`ci` describes what runs once the pull request is open.
```

Insert `contributing` above `testing` in the toctree.

- [ ] **Step 2: Run the tests**

Run: `pixi run --environment test pytest tests/test_contributor_guide.py -q -k "contributing or testing"`

Expected: six PASS.

- [ ] **Step 3: Build the docs**

Run: `pixi run docs`

Expected: **do not run the build in this task.** A `:doc:` naming a page that does not
yet exist warns and fails the fail-on-warning build, and no task ordering avoids that:
the four pages cross-reference each other in a **cycle** — `testing`→`ci`,
`ci`→`contributing`+`testing`, `contributing`→all three — so whichever lands first
points at pages that do not exist. Tasks 1–3 therefore verify with pytest alone and
Task 4 runs `pixi run docs` once, when the cycle closes. Do not comment the references
out: a commented-out cross-reference is the kind of thing that survives to merge.

- [ ] **Step 4: Commit**

```bash
git add docs/src/developer/contributing.rst docs/src/developer/index.rst
git commit -m "Publish what a contributor runs, and the graph behind it"
```

---

### Task 3: The changelog page

**Files:**
- Create: `docs/src/developer/changelog.rst`
- Modify: `docs/src/developer/index.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: the page `developer/changelog`, cross-referenced by Task 2 and pointed at by Task 6.

- [ ] **Step 1: Write the page**

Promote `changelog/README.md`. The eight types are measured from `pyproject.toml`'s
`[[tool.towncrier.type]]` blocks — there are exactly eight; do not add a ninth from memory.

```rst
.. _developer-changelog:

Changelog Fragments
===================

.. readingtime::

Every pull request adds a news fragment under ``changelog/``, named ``<PR>.<type>.rst``,
where ``<type>`` is one of ``breaking``, ``feature``, ``enhancement``, ``bugfix``,
``dependency``, ``documentation``, ``internal`` or ``misc``. towncrier assembles them into
``CHANGELOG.rst`` at release time, and the fragment is deleted then — so it is a pending
release note, not a permanent record.

The content is one short, sentence-case entry ending with author attribution through the
``:user:`` extlink role, for example ``(:user:`bjlittle`)``.

Citing an Issue
---------------

When the pull request closes an issue, cite it with the ``:issue:`` role at the point the
fragment describes what the issue reported, rather than trailing it at the end:

.. code:: rst

    Fixed the fills pulling away from the plotted profiles (:issue:`42`): …

Choosing a Role
---------------

When an entry names a documented API, cross-reference it with the matching Sphinx domain
role — ``:class:``, ``:func:``, ``:meth:``, ``:mod:``, ``:obj:`` — so a reader can follow
the link into the API documentation:

.. code:: rst

    Added :func:`~tephpy.calc.parcel_path` and the :class:`~tephpy.calc.Profile` dataclass.

rather than spelling those names in double backticks. Third-party objects resolve the same
way through intersphinx.

Reserve a plain double-backtick literal for a name with no documentation target: a private
member, an external tool, a filename, a configuration key.
```

Add `changelog` to the toctree after `testing`, and restore any cross-reference Task 2
commented out.

- [ ] **Step 2: Verify the type list against the source**

Run:

```bash
grep -c "^\[\[tool.towncrier.type\]\]" pyproject.toml
```

Expected: `8`. If it is not 8, the page is wrong — correct the page, not the count.

- [ ] **Step 3: Run the tests and build**

Run: `pixi run --environment test pytest tests/test_contributor_guide.py -q` then `pixi run docs`

Expected: nine of twelve PASS (all but `ci`); `build succeeded`.

- [ ] **Step 4: Commit**

```bash
git add docs/src/developer/changelog.rst docs/src/developer/index.rst
git commit -m "Publish the changelog fragment's shape and its roles"
```

---

### Task 4: The continuous-integration page

**Files:**
- Create: `docs/src/developer/ci.rst`
- Modify: `docs/src/developer/index.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: the page `developer/ci`, whose workflow names Task 5's gate reads.

This is the page written rather than promoted. Hold it at `contributor spec §3.5`'s
altitude: purpose, intent, consequence. Every one of the thirteen workflow files must be
named, because Task 5 asserts it.

- [ ] **Step 1: Enumerate the workflows from the directory, not from memory**

Run:

```bash
ls .github/workflows/*.yml | xargs -n1 basename | sed 's/\.yml$//'
```

Expected, on the tree this plan was written against: `ci-changelog`, `ci-citation`,
`ci-docs`, `ci-first-contribution`, `ci-floors`, `ci-label`, `ci-linkcheck`, `ci-locks`,
`ci-stale`, `ci-tests`, `ci-topics`, `ci-wheels`, `codeql`. If the list differs, the page
follows the directory.

- [ ] **Step 2: Write the page**

```rst
.. _developer-ci:

Continuous Integration
======================

.. readingtime::

Thirteen workflows run in this repository. Most of them you will meet on your own pull
request; six run on a schedule and will reach you without your having done anything, which
is the part worth reading before it happens.

This page says what each one is for and what its failure means. It does not describe how
they work — the workflow files say that, and cannot drift from themselves — and it does not
carry the reasoning behind a gate's design, which lives in the
:doc:`design specifications <specs/index>`.

On Your Pull Request
--------------------

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Workflow
      - What it is for
    * - ``ci-tests``
      - The suite, on every supported Python
    * - ``ci-docs``
      - Builds the documentation and runs every gate over it — the same set
        ``pixi run docs`` runs locally, named by task so the two cannot diverge
    * - ``ci-changelog``
      - Checks the news fragment: that there is one, and that it is well formed
    * - ``ci-citation``
      - Validates ``CITATION.cff``, the machine-readable record of how to cite
        this software. It runs only when that file changes — the one
        path-filtered workflow in the repository. (The ``spec §…`` citation
        check is the ``check_citations.py`` pre-commit hook, not a workflow.)
    * - ``ci-wheels``
      - Builds the sdist and wheel, and checks ``MANIFEST.in`` against what the
        sdist carries
    * - ``ci-label``
      - Labels the pull request from the paths it touches
    * - ``codeql``
      - Static security analysis

On a Schedule
-------------

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Workflow
      - What it is for
    * - ``ci-locks``
      - Refreshes ``pixi.lock`` weekly and opens a pull request with what moved.
        Nothing else moves the lock, so without this the whole of CI goes on
        testing whichever day's resolution was last written
    * - ``ci-floors``
      - Resolves each declared minimum version and exercises what it resolves,
        so a floor that has become untrue is found rather than assumed
    * - ``ci-linkcheck``
      - Checks every external link, and separately that the University of Wyoming
        archive still answers ``tephpy.io`` — the one external URL this project
        calls rather than links, which no link checker can judge
    * - ``ci-topics``
      - Reports monthly on which glossary topics the documentation covers
    * - ``ci-stale``
      - Marks a long-quiet issue or pull request stale
    * - ``codeql``
      - The same analysis, weekly, against code that has not changed

On an Issue or a First Pull Request
-----------------------------------

``ci-first-contribution`` greets somebody's first issue or pull request and labels it.

When One of Them Finds Something
--------------------------------

Four cases are worth knowing in advance, because you meet them without having caused them,
or because the remedy is not guessable.

**A lock refresh turns the bot's pull request red on image comparison.** When
``ci-locks`` moves matplotlib or freetype, rendered figures shift by more than the
comparison tolerance. The remedy is to regenerate the baselines on that branch with
``pixi run baselines``, then re-verify across all three test environments (:doc:`testing`).
This is expected rather than a defect in the proposal.

**A scheduled job opens an issue.** ``ci-floors``, ``ci-linkcheck`` and ``ci-topics`` each
keep a single standing issue and edit it in place rather than filing a new one per run, so
the history stays in one place. An issue appearing under your name in a notification is
one of these, not something you broke.

**Something of yours was labelled stale.** ``ci-stale`` marks an issue or pull request
quiet for six months and closes it four weeks later. Any comment takes the label straight
back off. It never touches anything held deliberately — a blocked or paused item, a
tracked design question, or the standing reports above.

**The browser demo will not start.** ``pixi run docs-all`` needs a Chromium that pixi does
not install. The check names the command to run; :doc:`contributing` carries both forms.

Where the Detail Lives
----------------------

The workflow files under ``.github/workflows/`` are the authority on what runs. The
:doc:`design specifications <specs/index>` carry why each gate is shaped as it is —
``floors spec §…`` for the dependency floors, ``topics spec §…`` for the coverage report,
``docs spec §…`` for the documentation gates.
```

Add `ci` to the toctree after `packaging`.

- [ ] **Step 3: Build the docs**

Run: `pixi run docs`

Expected: `build succeeded`, every gate ok.

- [ ] **Step 4: Commit**

```bash
git add docs/src/developer/ci.rst docs/src/developer/index.rst
git commit -m "Publish what CI is for, and what it means when it finds something"
```

---

### Task 5: The two coverage gates

**Files:**
- Modify: `tests/test_contributor_guide.py`

**Interfaces:**
- Consumes: `tests.pixi_tasks.closure(names, tasks)` — returns the set of task names reachable from `names` through `depends-on`, including `names` themselves.
- Produces: nothing later tasks read.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_contributor_guide.py`:

**The three imports below go in the module header** alongside Task 1's, not mid-file:
ruff rejects `import-outside-top-level` and the commit will be refused. Standard
library first, then third-party, then first-party, each group sorted.

```python
# these join the header: `import re`, `import subprocess`, `import tomllib`,
# and `from tests.pixi_tasks import closure`

WORKFLOWS = REPO / ".github" / "workflows"
CI_PAGE = DEVELOPER / "ci.rst"
CONTRIBUTING = DEVELOPER / "contributing.rst"


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
    unknown = sorted(claimed - workflow_names())
    assert not unknown, f"ci.rst names {unknown}, which do not exist"


def test_every_pixi_task_is_named_or_reachable_from_one_that_is():
    # A task the page does not name is excused exactly when running a task it
    # does name runs it. Measured 2026-09-08: nine named tasks reach the other
    # eight, nothing left over -- so this needs no exemption list, which is the
    # correction contributor spec §3.8 records.
    tasks = pixi_tasks()
    named = named_in(CONTRIBUTING, set(tasks))
    assert named, "contributing.rst names no pixi task at all"
    orphans = sorted(set(tasks) - closure(named, tasks))
    assert not orphans, (
        f"contributing.rst neither names {orphans} nor names anything that runs them"
    )


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
```

- [ ] **Step 2: Run them to verify they pass against the pages just written**

Run: `pixi run --environment test pytest tests/test_contributor_guide.py -q`

Expected: all PASS. A failure here means a page from Tasks 2 or 4 is incomplete — fix the
page, not the gate.

- [ ] **Step 3: Prove each gate fails when it should**

Run each mutation, confirm the named test fails, then restore:

```bash
# 1. a workflow the page does not name
git mv .github/workflows/ci-label.yml .github/workflows/ci-relabel.yml
pixi run --environment test pytest tests/test_contributor_guide.py -q -k workflow
git mv .github/workflows/ci-relabel.yml .github/workflows/ci-label.yml

# 2. a task the page neither names nor reaches
python - <<'PY'
from pathlib import Path
p = Path("docs/src/developer/contributing.rst")
p.write_text(p.read_text().replace("``serve-html``", "``serve-htm``"))
PY
pixi run --environment test pytest tests/test_contributor_guide.py -q -k pixi_task
git checkout docs/src/developer/contributing.rst
```

Expected: mutation 1 fails `test_every_workflow_is_named_on_the_ci_page`; mutation 2 fails
`test_every_pixi_task_is_named_or_reachable_from_one_that_is`. A mutation that passes means
the gate is asserting a proxy — fix the gate before continuing.

- [ ] **Step 4: Commit**

```bash
git add tests/test_contributor_guide.py
git commit -m "Hold the guide to the repository it describes"
```

---

### Task 6: The pointers, and the widened literals gate

**Files:**
- Modify: `CONTRIBUTING.md`, `changelog/README.md`
- Modify: `tests/test_docs_workflow.py`

**Interfaces:**
- Consumes: the four published pages.
- Produces: nothing later tasks read.

Last, because it removes prose that the pages must already carry.

- [ ] **Step 1: Widen the literals assertion**

In `tests/test_docs_workflow.py`, replace the single `GUIDE` with both carriers:

```python
#: Where the commands are written for a reader who has not met the failure yet.
#: Two carriers since contributor spec §3.6: the published page explains them, and
#: `CONTRIBUTING.md` keeps them because GitHub puts it in front of a first-time
#: contributor who may never reach the documentation.
GUIDES = (
    REPO / "CONTRIBUTING.md",
    REPO / "docs" / "src" / "developer" / "contributing.rst",
)


@pytest.mark.parametrize("guide", GUIDES, ids=lambda path: path.name)
def test_the_advice_runs_where_it_is_read_and_the_guide_says_the_same(guide):
    assert all(command.startswith(PREFIX) for _markers, command, _why in demo.MISSING)
    text = " ".join(guide.read_text(encoding="utf-8").split())
    missing = [
        command for _markers, command, _why in demo.MISSING if command not in text
    ]
    assert not missing, f"{guide.name} does not name {missing}"
```

- [ ] **Step 2: Run it — it must pass already**

Run: `pixi run --environment test pytest tests/test_docs_workflow.py -q -k advice`

Expected: both parameters PASS. Task 2's page already carries both commands verbatim. A
failure means the page paraphrased one — fix the page.

- [ ] **Step 3: Reduce `CONTRIBUTING.md` to a pointer**

Keep the gated literals; move the explanation to the page.

```markdown
# Contributing to tephpy

The full contributor guide is published with the documentation:

- [Contributing](https://tephpy.readthedocs.io/en/latest/developer/contributing.html) — getting an environment, and what to run
- [Testing](https://tephpy.readthedocs.io/en/latest/developer/testing.html) — the tests tree, and image comparison
- [Changelog fragments](https://tephpy.readthedocs.io/en/latest/developer/changelog.html) — what every pull request adds
- [Continuous integration](https://tephpy.readthedocs.io/en/latest/developer/ci.html) — what runs, and what a failure means

The short version. Development uses [pixi](https://pixi.sh):

```bash
pixi run tests      # run the test suite
pixi run lint       # run pre-commit
pixi run docs       # build the docs, then check the HTML the build produced
pixi run docs-all   # ...and check the browser demo, as CI does
```

`pixi run docs-all` needs a browser pixi does not install. Run
`pixi run -e docs playwright install chromium` once; on Linux the browser also needs
system libraries, which `pixi run -e docs playwright install --with-deps chromium` adds
as root.

Every pull request adds a `changelog/<PR>.<type>.rst` news fragment ending with author
attribution via the `:user:` extlink role.
```

- [ ] **Step 4: Reduce `changelog/README.md` to a pointer**

```markdown
# Changelog fragments

Every pull request adds a news fragment here named `<PR>.<type>.rst`, ending with author
attribution via the `:user:` extlink role. towncrier assembles them into `CHANGELOG.rst`
at release time.

The types, when to cite an issue, and which cross-reference role to reach for are
documented in
[Changelog fragments](https://tephpy.readthedocs.io/en/latest/developer/changelog.html).
```

- [ ] **Step 5: Add the changelog fragment**

Create `changelog/<PR>.documentation.rst`, substituting the real pull-request number:

```rst
A contributor guide in the published documentation (``contributor spec §…``): how to get
an environment and what to run, how the tests are laid out, what a changelog fragment
carries, and what each of the thirteen continuous-integration workflows is for — including
what it means when one of the six scheduled ones reaches you unbidden. ``CONTRIBUTING.md``
and ``changelog/README.md`` become pointers keeping only the commands a gate holds them
to, rather than a third copy of rules that were already written three times.
(:user:`claude`)
```

- [ ] **Step 6: Commit, then verify**

```bash
git add -A
git commit -m "Point the root files at the guide instead of repeating it"
pixi run tests
pixi run lint
pixi run docs
```

Expected: suite passes; lint clean; `build succeeded` with every gate ok, including
`Documentation links ok`.

**That line covers the new pointer URLs only if this task also adds both pointer files
to `SOURCES`.** `check_documentation_links.py` reads an explicit list, and before this
task it held only `README.md`, `.github/scripts/changelog.py` and
`.github/pull_request_template.md` — so without that change the pointers ship unchecked,
which is worse than the duplication they replaced. Update
`tests/test_documentation_links.py`'s membership assertion to match.

A `Missing pages` failure means a page path in Step 3 does not match what the build
produced.

---

## Self-Review

**Spec coverage.** `contributor spec §3.1` → Task 1's toctree and banner assertions;
§3.2 → Task 2; §3.3 → Task 1; §3.4 → Task 3; §3.5 → Task 4; §3.6 → Task 6; §3.7 → Task 2's
task graph; §3.8 → Task 5. §4's companion changes: the index in Tasks 1–4, the two root
files in Task 6, the specifications index already done when the specification landed. §5's
testing table is Tasks 1, 5 and 6.

**Placeholders.** None. Every page has its content written out; the one substitution is the
pull-request number in Task 6 Step 5, which cannot be known before the branch is pushed.

**Type consistency.** `closure(names, tasks)` is used in Task 5 exactly as
`tests/pixi_tasks.py` defines it. `PAGES`, `DEVELOPER`, `REPO` and `INDEX` are defined in
Task 1 and reused in Task 5 within the same module. `GUIDES` replaces `GUIDE` wholly in
Task 6; no other module reads that name.

**One risk carried deliberately.** Task 2's page cross-references `changelog` and `ci`
before Tasks 3 and 4 create them, which fails a fail-on-warning build if the tasks run
strictly in order. Step 3 of Task 2 says so and gives both ways out. Reordering to write
all four pages before any build would hide the per-page feedback these tasks exist to give.
