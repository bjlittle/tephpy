# What's New Section Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reader arriving at a new release gets a page of highlights in prose, linked to that release's changelog entry — instead of 171 entries about what was merged.

**Architecture:** A new `docs/src/reference/whatsnew/` section whose *What's New* page inlines the newest frozen release. The towncrier template gains a version title and a per-release anchor for those pages to link. Two `rst_epilog` substitutions give `latest.rst` its version and date without a file to edit. Three gates and four runbook steps carry the release-time workflow.

**Tech Stack:** reStructuredText, Sphinx 9.1, `sphinx_changelog`, towncrier 24.8, jinja2, pixi, pytest.

**Spec:** [`../specs/2026-09-14-whatsnew-design.md`](../specs/2026-09-14-whatsnew-design.md) — cited below as `whatsnew spec §N`. Read it alongside this plan; every task argues from a section of it.

## Global Constraints

- Every source file carries the BSD copyright header (ruff `CPY001`), exactly as `.pre-commit-config.yaml`'s `notice-rgx` spells it.
- Every pull request adds `changelog/<PR>.<type>.rst` ending with ``(:user:`claude`)``.
- Page titles follow CMOS headline style (`docs/src/developer/docs-style.rst`).
- A GitHub reference is written ``:issue:`N``` or ``:pull:`N``` in reStructuredText and ``{issue}`N``` in Markdown — never a bare `#N`, never a hand-written URL.
- **Citations are bare, never inside double backticks**, and **name leaves, never containers** — a container citation is a new key in `CONTAINER_CITATIONS` and fails `test_the_container_census_is_what_was_recorded`.
- **A bare `§N` resolves against the containing document.** Write `whatsnew spec §3.2`, never `§3.2`, when citing another specification. `§2` has no subsections; refer to "decision 5 of §2".
- `pixi run docs` must build clean; the build is fail-on-warning.
- Verify **after** committing, never before: the pre-commit hooks rewrite files.

---

## What This Plan Measured Before It Was Written

Established 2026-09-14 on `main` at `3272123`, by building the whole design as a throwaway spike and discarding it.

**1. The two risky mechanics work.** `latest.rst` both `.. include::`d into `index.rst` *and* listed in its toctree builds clean under fail-on-warning — no duplicate label, no orphan. And `sphinx_changelog` carries a label emitted by the towncrier template through to the rendered page as `id="changelog-v0-1-0"`.

**2. `rst_epilog` substitutions expand inside the included copy.** `latest.html` rendered `v0.1.0.dev212+dirty (2026-09-14)`.

**3. The reading-time gate wants exactly one banner per page.** Copying geovista would put one on `index.rst` *and* on the page it includes — two on one rendered page. `test_every_page_a_reader_reads_carries_a_reading_time` and `test_no_page_carries_more_than_one_reading_time` both fire.

**4. `jinja2` is importable in the `test` environment; `towncrier` is not.** So the template is tested by rendering it directly with a fake context, not by shelling out.

**5. Today's built changelog page carries only `id="changelog"`** — the page title. There are no per-release anchors at all, because the template has no `render_title` block and `title_format` is unset (`whatsnew spec §3.3`).

**6. Assembling `CHANGELOG.rst` fails `test_the_container_census_is_what_was_recorded`** ({issue}`318`). **No task in this plan assembles it** — Task 1's test renders the template in memory. {issue}`318` blocks the release, not this work, and is not this plan's to fix (`whatsnew spec §5`).

---

### Task 1: The changelog title and per-release anchor

Fixes a latent defect: without a title block the assembled `CHANGELOG.rst` has no version headings at all, and nothing for a whatsnew page to link (`whatsnew spec §3.3`).

**Files:**
- Modify: `changelog/template.rst`
- Test: `tests/test_docs_whatsnew.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: the anchor format `changelog-v<version>`, which Task 3's `latest.rst` and the runbook's freeze step both name.

- [ ] **Step 1: Write the failing test**

Create `tests/test_docs_whatsnew.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The what's new section, and the changelog hooks it reads (whatsnew spec §4)."""

from __future__ import annotations

from pathlib import Path
import re
from types import SimpleNamespace

from jinja2 import Template

REPO = Path(__file__).parents[1]
TEMPLATE = REPO / "changelog" / "template.rst"


def _rendered(version: str = "9.9.9", date: str = "2099-01-01") -> str:
    """Render the towncrier template with a context towncrier would give it.

    In memory rather than through `towncrier build`: the assembly writes
    `CHANGELOG.rst`, deletes every fragment, and fails the container census
    (:issue:`318`). Rendering the template is what this is about anyway.
    """
    return Template(TEMPLATE.read_text(encoding="utf-8")).render(
        versiondata=SimpleNamespace(version=version, date=date),
        render_title=True,
        top_underline="=",
        underlines=["^", "-"],
        sections={"": {}},
        definitions={},
    )


def test_the_template_anchors_each_release_by_version():
    # A whatsnew page links this anchor. Keyed on version rather than
    # geovista's date, for the legibility reason of `whatsnew spec §2`
    # decision 2: `changelog-v0.1.0` can be guessed and checked against the
    # page it sits on.
    assert ".. _changelog-v9.9.9:" in _rendered()


def test_the_template_titles_each_release():
    # Without this the assembled changelog has no version headings at all --
    # one release hides it, and from the second the file is an undivided run
    # of entries (`whatsnew spec §3.3`).
    rendered = _rendered()
    assert "v9.9.9 (2099-01-01)" in rendered
    assert "=" * len("v9.9.9 (2099-01-01)") in rendered
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pixi run -e test pytest tests/test_docs_whatsnew.py -q --no-cov`
Expected: both FAIL — the template emits neither the anchor nor the title.

- [ ] **Step 3: Write the template**

Replace the whole of `changelog/template.rst` with:

```jinja
.. _changelog-v{{ versiondata.version }}:

{% if render_title %}
v{{ versiondata.version }} ({{ versiondata.date }})
{{ top_underline * ((versiondata.version + versiondata.date)|length + 4) }}
{% endif %}
{% for section, _ in sections.items() %}
{% for category, val in definitions.items() if category in sections[section] %}
{{ definitions[category]['name'] }}
{{ "^" * (definitions[category]['name']|length + 2) }}

{% for text, values in sections[section][category].items() %}
- {{ text }} ({{ values|join(', ') }})
{% endfor %}

{% endfor %}
{% endfor %}
```

The `+ 4` makes the underline match `v` + version + ` (` + date + `)`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run -e test pytest tests/test_docs_whatsnew.py -q --no-cov`
Expected: PASS.

- [ ] **Step 5: Check the draft still renders**

Run: `pixi run changelog --version 0.1.0 --draft | head -5`
Expected: the first lines are `.. _changelog-v0.1.0:` then `v0.1.0 (<today>)` and its underline. **`--draft` writes nothing and deletes no fragment** — confirm with `ls changelog/*.rst | grep -vc template` still reporting the same count as before.

- [ ] **Step 6: Commit**

```bash
git add changelog/template.rst tests/test_docs_whatsnew.py
git commit -m "Give each release a changelog title and an anchor"
```

---

### Task 2: The version and date substitutions

**Files:**
- Modify: `docs/src/conf.py:9-11` (imports), `docs/src/conf.py:23` (after `version = …`)
- Test: `tests/test_docs_whatsnew.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the substitution names `|tp_version|` and `|build_date|`, which Task 4's `latest.rst` and `latest.rst.template` use.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_docs_whatsnew.py`:

```python
CONF = REPO / "docs" / "src" / "conf.py"

#: What `conf.py` must define for the pages to use. Two names in one tuple, so
#: renaming one and not the other fails here rather than rendering a raw
#: `|tp_version|` into the published page (`whatsnew spec §3.2`).
SUBSTITUTIONS = ("tp_version", "build_date")


def _defined_substitutions() -> set[str]:
    """Return the substitution names `conf.py`'s ``rst_epilog`` declares."""
    return set(
        re.findall(r"^\.\. \|(\w+)\| replace::", CONF.read_text(encoding="utf-8"), re.M)
    )


def test_conf_declares_the_substitutions_the_pages_use():
    assert set(SUBSTITUTIONS) <= _defined_substitutions()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pixi run -e test pytest tests/test_docs_whatsnew.py::test_conf_declares_the_substitutions_the_pages_use -q --no-cov`
Expected: FAIL — `conf.py` declares no substitutions.

- [ ] **Step 3: Add the import**

In `docs/src/conf.py`, change the stdlib import block so it reads:

```python
from datetime import UTC, datetime
from importlib.metadata import version as _dist_version
from pathlib import Path
import sys
```

- [ ] **Step 4: Add the epilog**

Immediately after `version = ".".join(release.split(".")[:2])`, add:

```python
# The what's new section reads both (whatsnew spec §3.2). `release` is the
# installed version, so `latest.rst` states what this build is of without a
# file to edit. A *frozen* page must not use them -- it would then announce
# whatever version the next build happens to be -- and Task 5's gate holds it.
_built = datetime.now(tz=UTC).strftime("%Y-%m-%d")

rst_epilog = f"""
.. |tp_version| replace:: v{release}
.. |build_date| replace:: ({_built})
"""
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pixi run -e test pytest tests/test_docs_whatsnew.py -q --no-cov`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add docs/src/conf.py tests/test_docs_whatsnew.py
git commit -m "Define the version and build-date substitutions"
```

---

### Task 3: The changelog preamble and its latest anchor

**Files:**
- Modify: `docs/src/reference/changelog.rst`
- Test: `tests/test_docs_whatsnew.py`

**Interfaces:**
- Consumes: Task 1's anchor format.
- Produces: the label `changelog-latest`, which Task 4's `latest.rst` links.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_docs_whatsnew.py`:

```python
CHANGELOG_PAGE = REPO / "docs" / "src" / "reference" / "changelog.rst"

#: The label `latest.rst` links. It sits immediately above the directive, so it
#: resolves to the top of the changelog -- the newest release -- whichever
#: release that is (`whatsnew spec §3.4`).
LATEST_ANCHOR = "changelog-latest"


def test_the_changelog_page_anchors_its_newest_release():
    assert f".. _{LATEST_ANCHOR}:" in CHANGELOG_PAGE.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pixi run -e test pytest tests/test_docs_whatsnew.py::test_the_changelog_page_anchors_its_newest_release -q --no-cov`
Expected: FAIL.

- [ ] **Step 3: Write the page**

Replace the whole of `docs/src/reference/changelog.rst` with:

```rst
Changelog
=========

Release versions follow `Semantic Versioning <https://semver.org>`__, that is
``<major>.<minor>.<patch>``.

This page is the full record, one entry per pull request. For what is worth
knowing about a release rather than everything that went into it, read
:doc:`whatsnew/index`.

----

.. _changelog-latest:

.. changelog::
    :towncrier: ../../../
    :towncrier-skip-if-empty:
    :changelog_file: ../../../CHANGELOG.rst
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pixi run -e test pytest tests/test_docs_whatsnew.py -q --no-cov`
Expected: PASS. The `:doc:` target does not exist until Task 4, so **do not build the documentation yet** — it would fail on an unknown document.

- [ ] **Step 5: Commit**

```bash
git add docs/src/reference/changelog.rst tests/test_docs_whatsnew.py
git commit -m "Give the changelog a preamble and an anchor for its newest release"
```

---

### Task 4: The section itself

**Files:**
- Create: `docs/src/reference/whatsnew/index.rst`, `docs/src/reference/whatsnew/latest.rst`, `docs/src/reference/whatsnew/latest.rst.template`
- Modify: `docs/src/reference/index.rst` (toctree), `tests/test_docs_readingtime.py:257-269` (`EXEMPT`)
- Test: `tests/test_docs_whatsnew.py`

**Interfaces:**
- Consumes: Task 2's substitutions, Task 3's `changelog-latest`.
- Produces: the directory layout Task 5's gates and Task 6's runbook steps operate on.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_docs_whatsnew.py`:

```python
WHATSNEW = REPO / "docs" / "src" / "reference" / "whatsnew"
INDEX = WHATSNEW / "index.rst"
LATEST = WHATSNEW / "latest.rst"
TEMPLATE_PAGE = WHATSNEW / "latest.rst.template"


def _pages() -> set[str]:
    """Return every page in the section, by stem. The seed is not a page."""
    return {path.stem for path in WHATSNEW.glob("*.rst")}


def _toctree_entries() -> list[str]:
    """Return the section index's toctree entries, in order."""
    body = INDEX.read_text(encoding="utf-8").split(".. toctree::", 1)[1]
    return [
        line.strip()
        for line in body.splitlines()
        if line.startswith("    ") and line.strip() and not line.strip().startswith(":")
    ]


def test_the_toctree_lists_every_page_in_the_section():
    # A page the toctree does not name builds clean and is unreachable from the
    # section it belongs to -- the rule `narrative spec §3.9` gives the quadrant
    # landing pages, borrowed here (`whatsnew spec §4`). The include is a
    # convenience that always duplicates one entry and is never a page's only
    # route, so the toctree alone is what this reads.
    assert set(_toctree_entries()) == _pages()


def test_the_section_index_includes_a_page_the_toctree_names():
    # The body a reader meets is the newest *released* highlights -- decision 5
    # of `whatsnew spec §2` -- so whatever it includes must be a real page.
    (included,) = re.findall(r"^\.\. include:: (\S+)$", INDEX.read_text(encoding="utf-8"), re.M)
    assert included.removesuffix(".rst") in _pages()


def test_the_seed_is_not_a_page():
    # `latest.rst.template` is copied into place at release time and is not
    # itself published; `.glob("*.rst")` must not collect it.
    assert TEMPLATE_PAGE.is_file()
    assert "latest.rst" not in _pages()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pixi run -e test pytest tests/test_docs_whatsnew.py -q --no-cov`
Expected: the four new tests FAIL — the directory does not exist.

- [ ] **Step 3: Write the seed**

Create `docs/src/reference/whatsnew/latest.rst.template`:

```rst
|tp_version| |build_date|
-------------------------

.. readingtime::

This is a **minor** release of ``tephpy``.

See the :ref:`changelog <changelog-latest>` for the full record of what changed.

Announcements
^^^^^^^^^^^^^

* ``TBD`` prior to release.

Highlights
^^^^^^^^^^

Notable changes in this release of ``tephpy`` include:

* ``TBD`` prior to release.

Patches
^^^^^^^

The patches for this release of ``tephpy`` include:

* N/A
```

- [ ] **Step 4: Seed `latest.rst` from it**

```bash
cp docs/src/reference/whatsnew/latest.rst.template docs/src/reference/whatsnew/latest.rst
```

- [ ] **Step 5: Write the section index**

Create `docs/src/reference/whatsnew/index.rst`:

```rst
What's New
==========

The highlights of each release, in prose — what is worth knowing rather than
everything that changed. The :doc:`../changelog` carries the full record, one
entry per pull request.

.. include:: latest.rst

.. toctree::
    :maxdepth: 1
    :hidden:

    latest
```

Before the first release there is no frozen page, so the include names
`latest.rst`; `v0.1.0` is where it switches over for good (`whatsnew spec §3.1`).

- [ ] **Step 6: Register the section**

In `docs/src/reference/index.rst`, change the toctree's last two entries from

```
    references
    changelog
```

to

```
    references
    whatsnew/index
    changelog
```

- [ ] **Step 7: Exempt the section index from the reading-time banner**

In `tests/test_docs_readingtime.py`, add to `EXEMPT`, after the
`"developer/specs/index.rst"` entry:

```python
    # an introduction, an include of the newest release, and a toctree; the
    # included page carries the banner and a second would render twice
    # (whatsnew spec §3.1)
    "reference/whatsnew/index.rst",
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `pixi run -e test pytest tests/test_docs_whatsnew.py tests/test_docs_readingtime.py -q --no-cov`
Expected: PASS.

- [ ] **Step 9: Commit, then build**

```bash
git add docs/src/reference/whatsnew docs/src/reference/index.rst tests/
git commit -m "Add the what's new section"
pixi run docs
```

Expected: a clean build. Then confirm the substitution expanded and the
reference resolved:

```bash
grep -o 'v[0-9][^<]*([0-9-]*)' docs/_build/html/reference/whatsnew/index.html | head -1
grep -c 'href="../changelog.html#changelog-latest"' docs/_build/html/reference/whatsnew/index.html
```

Expected: a version-and-date line, and `1`.

---

### Task 5: The two release-time gates

Neither condition can occur yet — there is no frozen page and tephpy is
unreleased — so both gates are written against the state the runbook creates.

**Files:**
- Modify: `tests/test_docs_whatsnew.py`

**Interfaces:**
- Consumes: Task 4's directory layout, Task 2's `SUBSTITUTIONS`.
- Produces: nothing.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_docs_whatsnew.py`:

```python
import pytest
from packaging.version import Version

import tephpy

#: The first release. The placeholder gate below is one-sided against this for
#: the reason `start spec §3.7` records having to become one-sided: the release
#: signal moves when the repository is tagged, and the page is edited on a
#: different commit over the same tree.
FIRST_RELEASE = Version("0.1.0")

#: What the seed carries until a release manager writes over it.
PLACEHOLDER = "``TBD`` prior to release."


def _frozen() -> list[Path]:
    """Return the frozen release pages -- every page but `latest.rst`."""
    return sorted(p for p in WHATSNEW.glob("*.rst") if p.name != "latest.rst")


def test_no_frozen_page_carries_the_substitutions():
    # A frozen page stays in the toctree for the life of the project. Left
    # substituted it would render with whatever version the *next* build is --
    # a page about 0.1 announcing 0.2 (`whatsnew spec §3.2`). Freezing replaces
    # them with literal text, and forgetting that is invisible until the next
    # release, which is why this reads the pages rather than trusting the step.
    offenders = {
        path.name: name
        for path in _frozen()
        for name in SUBSTITUTIONS
        if f"|{name}|" in path.read_text(encoding="utf-8")
    }
    assert offenders == {}


def test_the_accumulating_page_is_written_before_a_release():
    # One-sided: released forbids the placeholder, unreleased does not require
    # its absence. Shipping `TBD` as the highlights of a release is the one
    # failure here that reaches every reader.
    if Version(tephpy.__version__) < FIRST_RELEASE:
        pytest.skip(f"{tephpy.__version__} predates the first release")
    assert PLACEHOLDER not in LATEST.read_text(encoding="utf-8")
```

Move the `import pytest`, `from packaging.version import Version` and
`import tephpy` lines up into the module's import block; ruff will fail on
imports below module level.

- [ ] **Step 2: Run them**

Run: `pixi run -e test pytest tests/test_docs_whatsnew.py -q --no-cov -rs`
Expected: `test_no_frozen_page_carries_the_substitutions` PASSES vacuously — there are no frozen pages — and `test_the_accumulating_page_is_written_before_a_release` SKIPS.

- [ ] **Step 3: Prove both gates bite**

Neither passed against a real condition, so make one. Commit first — `git checkout` restores from the index and would discard uncommitted work:

```bash
git add tests/test_docs_whatsnew.py
git commit -m "Gate the two release-time whatsnew mistakes"
cp docs/src/reference/whatsnew/latest.rst docs/src/reference/whatsnew/0.1.rst
pixi run -e test pytest tests/test_docs_whatsnew.py::test_no_frozen_page_carries_the_substitutions -q --no-cov
```

Expected: FAIL, naming `0.1.rst` and both substitutions. Then:

```bash
rm docs/src/reference/whatsnew/0.1.rst
sed -i 's/^FIRST_RELEASE = Version("0.1.0")$/FIRST_RELEASE = Version("0.1.0.dev1")/' tests/test_docs_whatsnew.py
pixi run -e test pytest tests/test_docs_whatsnew.py::test_the_accumulating_page_is_written_before_a_release -q --no-cov
```

Expected: FAIL — the current dev version now counts as released and the seed still carries the placeholder. Restore:

```bash
git checkout tests/test_docs_whatsnew.py
git status --porcelain   # expect empty
```

- [ ] **Step 4: Commit**

Nothing to commit if the mutations were reverted cleanly; confirm with
`git status --porcelain` and move on.

---

### Task 6: The runbook steps

**Files:**
- Modify: `docs/src/developer/release.rst`
- Test: none — prose, held by the docs build and the task-table gate already over the page.

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

- [ ] **Step 1: Add the freeze to step 1 of The Sequence**

In `docs/src/developer/release.rst`, immediately after the numbered step
**"Get on the release branch"** and before **"Assemble the changelog"**, insert a
new step:

```rst
2. **Freeze the what's new page.** Write the release's Announcements and
   Highlights into ``docs/src/reference/whatsnew/latest.rst``, then:

   - replace ``|tp_version|`` and ``|build_date|`` with the literal version and
     release date — a frozen page that keeps them announces whatever version the
     next documentation build happens to be;
   - repoint its changelog link from ``changelog-latest`` to
     ``changelog-vX.Y.Z``;
   - rename the file to ``A.B.rst`` — the major and minor only, since a patch
     release appends to this same page;
   - in ``whatsnew/index.rst``, point the ``include`` at ``A.B.rst`` and replace
     ``latest`` with ``A.B`` in the toctree.

   Both index edits are obligatory. The rename takes ``latest.rst`` out of
   existence, so a toctree entry still naming it names nothing — on the one
   commit that gets tagged, built and published.
```

Renumber the steps that follow.

- [ ] **Step 2: Add the reseed after the merge-back**

Immediately after the **"Merge the release branch back into main"** step, insert:

```rst
10. **Reseed the what's new page**, on ``main``, and only now.

    .. code-block:: console

       $ cp docs/src/reference/whatsnew/latest.rst.template \
            docs/src/reference/whatsnew/latest.rst

    In the same commit, put ``latest`` back at the head of
    ``whatsnew/index.rst``'s toctree. The freeze removed it and nothing else
    puts it back, and a page the toctree does not name is unreachable from the
    section it belongs to.

    Leave the ``include`` alone: it stays on the release just frozen, so the
    page a reader meets is the newest release they can install rather than a
    placeholder for the next one.

    Seeding earlier does not work. On the release branch it would travel back
    through the merge-back as a second empty page; on ``main`` before the
    merge-back it would leave two pages both claiming to be newest.
```

Renumber the steps that follow.

- [ ] **Step 3: Note what a patch release skips**

At the end of *The Sequence*, after the last step, add:

```rst
A patch release re-enters at the freeze step against the existing ``A.B.rst``,
appending to its *Patches* section, and skips the reseed: ``latest.rst`` on
``main`` is already accumulating for the next minor version and is not what a
patch describes.
```

- [ ] **Step 4: Commit and verify**

```bash
git add docs/src/developer/release.rst
git commit -m "Carry the what's new steps in the release sequence"
pixi run tests && pixi run lint && pixi run docs
```

Expected: all clean. Check the page's step numbering reads 1..13 with no repeats:

```bash
grep -nE "^[0-9]+\. \*\*" docs/src/developer/release.rst
```

- [ ] **Step 5: Add the changelog fragment**

Create `changelog/<PR>.feature.rst` naming the pull request's own number:

```rst
Added a :ref:`What's New <whatsnew-spec-1>` section to the reference quadrant,
carrying the highlights of each release in prose beside the changelog's record
of every pull request. Each release's page links that release's changelog entry
through a new per-release anchor, and the towncrier template now titles each
release — it emitted no version headings at all before, so a second release
would have run into the first. (:user:`claude`)
```

```bash
git add changelog/
git commit -m "Add the changelog fragment"
```

---

## Self-Review

**Spec coverage.** §3.1 → Task 4. §3.2 → Tasks 2 and 5. §3.3 → Task 1. §3.4 → Task 3. §3.5 → Task 6. §4's three gates → Task 4 (the toctree gate) and Task 5 (the other two). §2 decision 5 → Task 4 step 5 and Task 6 step 2. §5 is {issue}`318`, deliberately out of scope.

**Placeholders.** The only `TBD` strings are the seed's own content and the constant that matches them.

**Type consistency.** `SUBSTITUTIONS` is defined in Task 2 and consumed in Task 5; `LATEST_ANCHOR` in Task 3 and used by Task 4's page; `_pages()`, `_frozen()` and `WHATSNEW` are defined once each.

**One ordering constraint to respect.** Task 3 writes a `:doc:` to a page Task 4 creates, so the documentation must not be built between them. Both tasks say so.
