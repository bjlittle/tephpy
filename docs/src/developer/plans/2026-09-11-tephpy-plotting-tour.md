# Plotting Tour Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A contributor about to change `tephpy.plotting` can read one page that gives them the order things happen in, who owns what, and where to look next — without reading 462 lines of design specification to find out what they must not break.

**Architecture:** One hand-written reStructuredText page in `docs/src/developer/`, mapping seven modules and two cross-module flows. Every mechanism stays stated once in the tree and is cited rather than restated. Two new gates hold the page's *names* to the package it describes; three more come free by registering the page in an existing tuple.

**Tech Stack:** reStructuredText, Sphinx 9.1, pydata-sphinx-theme 0.21, pixi, pytest.

**Spec:** [`../specs/2026-09-11-plotting-tour-design.md`](../specs/2026-09-11-plotting-tour-design.md) — cited below as `tour spec §N`. Read it alongside this plan; every task argues from a section of it.

## Global Constraints

- Every source file carries the BSD copyright header (ruff `CPY001`), exactly as `.pre-commit-config.yaml`'s `notice-rgx` spells it.
- Every pull request adds `changelog/<PR>.<type>.rst` ending with ``(:user:`claude`)``.
- Page titles follow CMOS headline style (`docs/src/developer/docs-style.rst`).
- A GitHub reference is written ``:issue:`N``` or ``:pull:`N``` in reStructuredText and ``{issue}`N``` in Markdown — never a bare `#N`, never a hand-written URL.
- **Citations are bare, never inside double backticks.** A citation in a literal is validated but renders as a literal rather than a link (`tour spec §3.5`).
- **Citations name leaves, never containers.** `spec §3.2.3`, never `spec §3.2` — a container citation on this page is a new key in `CONTAINER_CITATIONS` and fails `test_the_container_census_is_what_was_recorded` (`tour spec §3.5`).
- `pixi run docs` must build clean; the build is fail-on-warning.
- Verify **after** committing, never before: the pre-commit hooks rewrite files.

---

## What This Plan Measured Before It Was Written

Everything below was established on 2026-09-11 on `main` at `99bd2c9`.

**1. Developer pages are outside all three user-section lists.** `USER_SECTIONS` is
`("start", "tutorials", "howtos", "explanation")` in `tests/test_docs_landing_pages.py:22`,
and the same four in `.github/scripts/check_glossary_links.py:64` and
`tests/test_docs_snippets.py:41`. `developer` is in none of them. Consequences, all
deliberate: no landing table is required, a `:term:` first mention is not enforced, and
**a python block on this page would not be executed**. This page needs no code blocks at
all; do not add an unexecuted one.

**2. The citation profile of each module, which the map's third column reports.**
Measured by counting citations per file:

| module | lines | top citations |
|---|---|---|
| `__init__.py` | 18 | none |
| `axes.py` | 2,168 | spec §3.2.3 ×11, §3.2.7 ×9, §3.2.6 ×7, §3.2.5 ×6, §3.2.1 ×6 |
| `isopleths.py` | 1,820 | spec §3.2.2 ×12, §3.2.4 ×9, §3.2.1 ×4, §3.2.3 ×4, §3.5 ×4 |
| `shading.py` | 543 | spec §3.2.5 ×4 |
| `logo.py` | 452 | logo spec §3.4 ×4, §5 ×3, §3.3 ×2, §3.2 ×2 |
| `barbs.py` | 315 | spec §3.2.5 ×3 |
| `_theme.py` | 131 | logo spec §3.5 ×2, spec §3.2.2 ×1 |

The third column of the page's module table is these, not a guess.

**3. The spine's call sites, which the page reports as fact.** In `axes.py`:
`_sync_edge_labels` is reached from two — the `on_change` hook armed on every family
(line 586) and the end of `clear` (line 590). `_relayout_side_panels` is called from
three — a right-edge change inside `_sync_edge_labels` (line 1558), `plot_barbs`
(line 1628) and `annotate_indices` (line 1675). Re-measure with `grep -n` before writing
the numbers if the file has moved under you; a stale count is exactly the defect this
page is supposed not to introduce.

**4. `PAGES` already carries the structural trio.** `tests/test_contributor_guide.py:30`
is `PAGES = ("contributing", "testing", "changelog", "ci")`, parametrising exists /
in-the-toctree / carries-a-reading-time-banner. Adding `"plotting"` inherits all three;
its comment says "The pages contributor spec §3.1 adds" and must be re-worded, because
it will then carry two specifications' pages (`tour spec §4`).

**5. The gates were run against the page text before this plan was saved.** The page in
Task 1 was fed to the parsers in Task 2, and three defects came back, all now fixed in the
text below: ``_constants`` is a sibling package rather than a name inside `plotting`,
``configure`` is a method of `IsoplethFamily` and lands on no module, and ``edge_axis``
appears only inside a longer expression, so a whole-literal match missed it. Re-run that
check if you change either the page or the parsers.

**6. Two module docstrings already carry orientation.** `axes.py`'s names the projection
and states the side-panel layout contract; `isopleths.py`'s describes the artist and the
three-tier resolution. The page cites them rather than repeating them, and the *Where to
Look* table points at them by name.

---

## File Structure

| file | responsibility |
|---|---|
| `docs/src/developer/plotting.rst` | *create* — the page (`tour spec §3.2`) |
| `docs/src/developer/index.rst` | *modify* — one toctree entry, third (`tour spec §3.1`) |
| `tests/test_plotting_tour.py` | *create* — both name gates and their floor proofs (`tour spec §5`) |
| `tests/test_contributor_guide.py` | *modify* — `"plotting"` joins `PAGES`; re-word its comment |
| `changelog/<PR>.documentation.rst` | *create* — the fragment |

One test module, because both gates are one idea — a page naming code that exists — and
they share the reading of the page.

---

### Task 1: The page, and its two registrations

**Files:**
- Create: `docs/src/developer/plotting.rst`
- Modify: `docs/src/developer/index.rst`
- Modify: `tests/test_contributor_guide.py:26-30`

**Interfaces:**
- Consumes: nothing.
- Produces: the page `developer/plotting`, with a module table whose rows are
  ``name.py`` literals and a prose body naming the spine's helpers as literals. Task 2's
  gates parse exactly those two things; changing the table to any other markup breaks
  them.

- [ ] **Step 1: Add the page to `PAGES` and watch it fail**

In `tests/test_contributor_guide.py`, replace the comment and tuple at lines 26-30:

```python
#: The developer section's hand-written pages, in the order their specifications
#: give the toctree — contributor spec §3.1's four, then tour spec §3.1's tour.
#: Each page task appends its own as it lands, so every commit is green and
#: each keeps its own red-to-green.
PAGES = ("contributing", "testing", "changelog", "ci", "plotting")
```

- [ ] **Step 2: Run the three inherited gates to verify they fail**

Run: `pixi run tests tests/test_contributor_guide.py -q -k plotting`
Expected: 3 failures — the file does not exist, it is in no toctree, it carries no banner.

- [ ] **Step 3: Write the page**

Create `docs/src/developer/plotting.rst`:

```rst
.. _developer-plotting:

A Tour of the Plotting Package
==============================

.. readingtime::

``tephpy.plotting`` is the matplotlib layer: what turns a sounding into a figure. It
publishes two names — ``TephigramAxes``, registered as the ``"tephigram"`` projection,
and ``add_logo`` — and keeps the rest private. Underneath it sits ``tephpy.transforms``,
which owns the temperature-entropy mathematics; beside it sit ``tephpy.sounding`` and
``tephpy.calc``, which it consumes and which never import it back. The thermodynamics is
MetPy's throughout.

**This page is a map, not an account.** Every mechanism it names is specified in a design
specification or documented on the object itself, and is cited here rather than restated.
Where this page and a specification disagree, the specification is right and this page is
the defect — so follow the citation whenever you need the argument rather than the rule.

The Modules
-----------

.. list-table::
    :header-rows: 1
    :widths: 16 54 30

    * - Module
      - What it owns
      - Where its rules live
    * - ``__init__.py``
      - the package's two public names, and nothing else
      - —
    * - ``axes.py``
      - the projection and its transforms, the plotting accessors, edge ownership, the
        cursor readout, and the side-panel layout
      - spec §3.2.1, §3.2.3, §3.2.5, §3.2.6, §3.2.7
    * - ``isopleths.py``
      - the five background families: their members, option resolution, the zoom ladder,
        and their labels
      - spec §3.2.1, §3.2.2, §3.2.4
    * - ``shading.py``
      - the CAPE and CIN region geometry
      - spec §3.2.5
    * - ``barbs.py``
      - the wind-barb gutter, its staff, and the thinning of levels
      - spec §3.2.5
    * - ``logo.py``
      - the branding artist, which has a specification of its own
      - logo spec §3.2, §3.3, §3.4, §3.5, §3.6
    * - ``_theme.py``
      - one answer to "what colour is the canvas", shared by the logo and the inline
        labels
      - logo spec §3.5, spec §3.2.2

``axes.py`` and ``isopleths.py`` carry roughly three quarters of the package between
them. The other five are small enough to read whole, and the table above is the only
place that has to change when a module arrives or leaves.

How the Isopleths Draw
----------------------

The five families — isotherms, isobars, dry adiabats, moist adiabats and humidity
mixing-ratio lines — are drawn by default, one ``IsoplethFamily`` artist each. Members
are built lazily on the first draw and cached; every ``draw`` then clips that cache to
the view rectangle, selects the members the zoom ladder calls for, and re-places the
labels (spec §3.2.1).

That is why pan, zoom, resize and ``set_extent`` need no special handling: matplotlib
calls ``draw`` on every render, and nothing caches a decision that depends on the view.
A change that moves work out of ``draw`` and into construction is a change that breaks
zoom, quietly.

Settings resolve in three tiers — accessor keywords, then ``tephpy.config``, then
``_constants`` — re-read on every resolve, so a configuration change can move a family
the call never mentions (spec §3.5). Passing ``values`` or ``interval`` explicitly fixes
the member set and turns the zoom ladder off.

Labels go inline or onto an edge, per family (spec §3.2.2). Which edges suit which family
is a measured question rather than a matter of taste: the per-family edge-crossing counts,
and the pairings they recommend, are in spec §3.2.7.

Clear Is the Constructor
------------------------

``TephigramAxes.clear`` is where every piece of projection-owned state is built — the
transform, the equal aspect, the hidden native axes, the five families, the edges they
claim, and the default extent. Matplotlib calls it twice over: once from ``Axes.__init__``
and again on every ``ax.clear()``. There is no separate constructor to read, and anything
that must survive a clear has to be built here.

The order matters in one place. All five families are constructed before the first edge
sync runs, because each arms its ``on_change`` as it is built and a sync running mid-loop
would see a partial set. The extent lands last.

A family's ``configure`` notifies ``on_change`` only when it succeeds, so a call that
raises leaves both the family and the diagram's edges as they were (spec §3.2.3).

Who Owns an Edge
----------------

An edge carries one family's labels, or none. Whichever way a family is reconfigured — an
accessor, a direct ``configure``, an ``Artist.set_visible`` — the same four steps run:

1. the family resolves its new options;
2. ``_check_label_edges`` rejects a claim another family already holds;
3. ``_sync_edge_labels`` compares what the five families now ask for against what is
   currently claimed; and
4. ``_claim_edge`` or ``_release_edge`` applies the difference.

Validation sits at step 2 rather than inside the family because the axes owns all five
families and is therefore the only object that can see a collision. Handing it to the
family as a hook puts the rejection inside that family's own rollback (spec §3.2.3).

Three properties are easy to break from inside any one of those steps.

**A claim installs identity, never presentation.** Locator, formatter, visibility, colour,
title. How the ticks *look* is stamped once, when the edge axis is created, and belongs to
the caller from the claim onwards — so ``ax.edge_axis("top").set_tick_params(labelsize=12)``
survives everything short of a release (spec §3.2.3).

**The tick-colour memory is keyed by owner as well as colour.** It outlives a release, so
comparing colour alone would suppress a new owner's claim whenever its colour happened to
match the previous owner's, leaving the ticks in a colour that ties them to nothing.

**The sync is re-entrancy guarded.** Nothing on the sync path resolves options, so a
nested call would have nothing new to apply. The guard makes that structural rather than a
standing bet on matplotlib's axis internals.

The Side Panels
---------------

Two panels can sit to the right of the diagram: the wind-barb gutter and the indices
panel, in that order, inside out (spec §3.2.7).

**One divider per axes**, created once and cached. A second ``make_axes_locatable`` call
would build a fresh divider and replace the parent locator, detaching the earlier panel so
that it draws over the newcomer.

**Relayout, not teardown.** ``_relayout_side_panels`` rebuilds the divider's horizontal
stack and reassigns every locator whenever a panel appears, so the inside-out order holds
whichever order ``plot_barbs`` and ``annotate_indices`` were called in. Removing and
re-appending would not do: ``append_axes`` only ever appends to the size stack, so the
removed panel's width slot stays behind as a phantom gap.

**The pad widens when the right edge carries ticks.** Isopleth tick labels are wider than
the gutter's own pad, so the panel nearest the diagram takes a wider one while the right
edge is claimed. That is why a right-edge claim relayouts the panels at all, and it is the
one place the two flows on this page meet.

**Who removes the panels on a clear depends on who called it.** They are the diagram's to
remove on a direct ``ax.clear()``, and the figure's on a figure clear, where the diagram's
teardown stands down rather than racing it: ``Figure.clear`` clears and deletes each entry
of a *snapshot* of ``figure.axes``, so an axes removing a sibling from inside its own
``clear`` orphans an entry the figure is still about to visit. The two cases are told apart
by the calling frame — ``_figure_is_clearing`` — because the figure's state is identical
either way (spec §3.2.7).

Where to Look
-------------

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - Changing
      - Read first
    * - a family's geometry, members or labels
      - the ``isopleths.py`` module docstring, then spec §3.2.1, §3.2.2
    * - which edge a family labels
      - spec §3.2.3, then ``_sync_edge_labels``
    * - emphasis styling of individual members
      - spec §3.2.4
    * - what an accessor accepts, or a new accessor
      - spec §3.2.5, then the accessor's own docstring
    * - the cursor readout
      - spec §3.2.6, then ``format_coord``
    * - the default view, or which edges a family can tick
      - spec §3.2.7 for the crossing counts, framing spec §3.1 for what an extent frames
    * - a side panel's width, order or pad
      - spec §3.2.7, then ``_relayout_side_panels``
    * - anything that must survive ``ax.clear()``
      - ``clear`` itself, and this page's *Clear Is the Constructor*
    * - the logo
      - logo spec, which is a specification of its own

The tests for all of this live in ``tests/plotting/``, mirroring the package
(:doc:`testing`).
```

- [ ] **Step 4: Add the toctree entry**

In `docs/src/developer/index.rst`, the entry goes third — after `testing`, before
`changelog` (`tour spec §3.1`):

```rst
.. toctree::
    :maxdepth: 1

    contributing
    testing
    plotting
    changelog
    docs-style
    packaging
    ci
    specs/index
```

- [ ] **Step 5: Commit, then verify**

The hooks rewrite files, so commit first and check afterwards.

```bash
git add docs/src/developer/plotting.rst docs/src/developer/index.rst tests/test_contributor_guide.py
git commit -m "Publish the plotting tour"
pixi run tests tests/test_contributor_guide.py tests/test_citations.py tests/test_docs_readingtime.py -q
pixi run docs
```

Expected: tests pass, including `test_the_container_census_is_what_was_recorded` — if
that one fails, a citation on the page named `spec §3.2` instead of a leaf. The docs build
succeeds and its five gates pass.

- [ ] **Step 6: Check the citations became links**

A citation inside double backticks renders as a literal, not a link (`tour spec §3.5`).
Confirm the page's citations linked:

```bash
grep -c 'class="reference internal"' docs/_build/html/developer/plotting.html
```

Expected: a count in the tens, not zero. If it is zero, the citations were written inside
``literals`` and must be unwrapped.

---

### Task 2: The two name gates

**Files:**
- Create: `tests/test_plotting_tour.py`
- Test: itself

**Interfaces:**
- Consumes: `docs/src/developer/plotting.rst` from Task 1 — its ``name.py`` table rows
  and its ``_helper`` literals.
- Produces: nothing later tasks depend on.

The page's prose cannot be gated; its names can (`tour spec §5`). Both gates assert a
floor on what the parser found before asserting the property, because a parser that
silently matches nothing otherwise passes green.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plotting_tour.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The plotting tour names code that exists (tour spec §5)."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

import tephpy
from tephpy.plotting import _theme, barbs, isopleths, logo, shading
from tephpy.plotting import axes as axes_module
from tephpy.plotting.axes import TephigramAxes
from tephpy.plotting.barbs import BarbStaff
from tephpy.plotting.isopleths import IsoplethFamily

REPO = Path(__file__).parents[1]
PAGE = REPO / "docs" / "src" / "developer" / "plotting.rst"
PACKAGE = REPO / "src" / "tephpy" / "plotting"

#: The modules the map must have a row for. Seven today; the floor below is
#: what makes a parser that matched nothing fail rather than pass.
MODULE_FLOOR = 7

#: Public names the page must name and which must resolve. The private
#: helpers are found by pattern instead (they are unambiguous), but a public
#: method is an ordinary word and cannot be, so these are declared.
PUBLIC_SPINE = (
    "TephigramAxes",
    "IsoplethFamily",
    "clear",
    "configure",
    "edge_axis",
    "format_coord",
    "plot_barbs",
    "annotate_indices",
)

#: Where a name may resolve. Measured 2026-09-11 against the page's own text:
#: the modules alone are not enough. ``configure`` is a method of
#: ``IsoplethFamily`` and lands on no module, and ``_constants`` is a sibling
#: package of ``plotting`` rather than a name inside it -- so the classes the
#: page names and the ``tephpy`` root both hold names it legitimately mentions.
_HOLDERS = (
    TephigramAxes,
    IsoplethFamily,
    BarbStaff,
    axes_module,
    isopleths,
    shading,
    barbs,
    logo,
    _theme,
    tephpy,
)


def _literals(text: str) -> set[str]:
    """Every ``double backtick`` literal on the page."""
    return set(re.findall(r"``([^`]+)``", text))


def _module_rows(text: str) -> set[str]:
    """Return the module names the map has a row for."""
    return {lit for lit in _literals(text) if lit.endswith(".py")}


def _private_names(text: str) -> set[str]:
    """Every private helper the page names, e.g. ``_claim_edge``."""
    return {lit for lit in _literals(text) if re.fullmatch(r"_[a-z][a-z0-9_]*", lit)}


def _resolves(name: str) -> bool:
    """Whether `name` is a real attribute of the plotting package."""
    return any(hasattr(holder, name) for holder in _HOLDERS)


def test_every_module_in_the_package_has_a_row():
    rows = _module_rows(PAGE.read_text(encoding="utf-8"))
    assert len(rows) >= MODULE_FLOOR, (
        f"the module map parsed {len(rows)} rows, fewer than the {MODULE_FLOOR} "
        "modules that exist -- the table's markup has changed under the parser"
    )
    on_disk = {path.name for path in PACKAGE.glob("*.py")}
    assert not on_disk - rows, f"{sorted(on_disk - rows)} has no row on the map"


def test_the_map_names_no_module_that_is_gone():
    rows = _module_rows(PAGE.read_text(encoding="utf-8"))
    on_disk = {path.name for path in PACKAGE.glob("*.py")}
    assert not rows - on_disk, f"the map names {sorted(rows - on_disk)}, which is gone"


def test_every_private_helper_the_page_names_resolves():
    names = _private_names(PAGE.read_text(encoding="utf-8"))
    assert len(names) >= 3, (
        f"the page names {len(names)} private helpers; the tour describes two flows "
        "through at least three, so the parser has stopped matching"
    )
    missing = sorted(name for name in names if not _resolves(name))
    assert not missing, f"the page names {missing}, which no longer exist"


@pytest.mark.parametrize("name", PUBLIC_SPINE)
def test_each_public_spine_name_is_named_and_resolves(name):
    # Matched on a word boundary rather than as a whole literal: the page names
    # some of these inside a longer expression, e.g. ``ax.edge_axis("top")``.
    page = PAGE.read_text(encoding="utf-8")
    assert re.search(rf"\b{re.escape(name)}\b", page), (
        f"the page no longer names {name!r}"
    )
    assert _resolves(name), f"{name!r} no longer exists in tephpy.plotting"


def test_the_row_parser_finds_nothing_without_the_table():
    # The floor is the point: prove it fails rather than trusting it would.
    assert _module_rows("a page with ``prose`` but no table") == set()


def test_the_name_parser_reports_a_helper_that_is_gone():
    assert _private_names("the diagram calls ``_no_such_helper`` on a clear") == {
        "_no_such_helper"
    }
    assert not _resolves("_no_such_helper")
```

- [ ] **Step 2: Run them to verify they pass against the page Task 1 wrote**

Run: `pixi run tests tests/test_plotting_tour.py -q`
Expected: all pass. A failure here names a real defect in the page — a module with no row,
or a helper the page renamed. Fix the page, not the gate.

- [ ] **Step 3: Prove each gate fails when it should**

Not a code change — a manual check, run and then reverted, because a gate nobody has seen
fail is a gate nobody has tested:

```bash
# 1. a module with no row on the map
sed -i 's/``shading.py``/``shading_renamed.py``/' docs/src/developer/plotting.rst
pixi run tests tests/test_plotting_tour.py -q   # expect 2 failures: no row, and a row that is gone
git checkout docs/src/developer/plotting.rst

# 2. a helper the page names that does not exist
sed -i 's/``_claim_edge``/``_claim_the_edge``/' docs/src/developer/plotting.rst
pixi run tests tests/test_plotting_tour.py -q   # expect 1 failure naming _claim_the_edge
git checkout docs/src/developer/plotting.rst
```

Expected: the failures above, with those messages. Then confirm the tree is clean again:
`git status --short` reports nothing.

- [ ] **Step 4: Commit**

```bash
git add tests/test_plotting_tour.py
git commit -m "Gate the plotting tour's names against the package"
pixi run tests -q
```

---

### Task 3: The fragment, and the whole-suite sweep

**Files:**
- Create: `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: the pull request number, which exists only once the pull request is open.
- Produces: nothing.

- [ ] **Step 1: Open the pull request, then write the fragment**

The fragment is named for the pull request, so the pull request comes first. Write
`changelog/<PR>.documentation.rst` describing the page in the terms `tour spec §1` uses —
the package documented at both extremes and not in the middle — and end it with
``(:user:`claude`)``.

**Cite leaves.** A fragment naming `spec §3.2` is a container citation and fails the
census; that is exactly how :pull:`300` went red on continuous integration, having passed
locally because the suite was run before the fragment was written.

- [ ] **Step 2: Commit, then run the whole suite — not a subset**

```bash
git add changelog/
git commit -m "Add the changelog fragment for the plotting tour"
pixi run tests -q
pixi run docs
```

Expected: the full suite passes and the docs build is clean. The subset that covers this
work is not the subset that catches it: the census lives in `tests/test_citations.py`,
which a fragment-only change does not obviously touch.

- [ ] **Step 3: Close out**

Report to the pull request what the page does *not* hold (`tour spec §5`): whether a
sentence is still true is not gated, only whether it names live code. {issue}`66` stays
open — this closes its mid layer only, and {issue}`299` carries the relocation.

---

## Self-Review

**Spec coverage.** `tour spec §3.1` placement → Task 1 Steps 3-4. `§3.2`'s seven sections
→ Task 1 Step 3, all seven present in the page text. `§3.3` module map and its
both-directions gate → Task 1 Step 3 (the table), Task 2 (the two tests). `§3.4` the spine
and its invariants → Task 1 Step 3, the *Who Owns an Edge* and *The Side Panels* sections,
three properties and four bullets respectively. `§3.5` citation direction → Global
Constraints, and Task 1 Step 6 checks the rendering. `§3.6` map-versus-account → the page's
own lead paragraph states the rule for later editors. `§4` companion changes → Task 1
Steps 1 and 4, Task 3. `§5` both gates with floors → Task 2 Steps 1-3. `§6` scope → nothing
in this plan touches `spec §3.2`, the explanation quadrant, or a diagram.

**Placeholders.** None: the page is written out in full, both gates are written out in
full, and the only deferred value is the pull request number, which cannot exist earlier.

**Type consistency.** `_module_rows`, `_private_names`, `_literals` and `_resolves` are
defined once in Task 2 and used under those names throughout. `PAGES`, `MODULE_FLOOR` and
`PUBLIC_SPINE` likewise. The page's markup — ``name.py`` literals in the table, ``_helper``
literals in prose — is what both parsers expect, and Task 1's *Interfaces* block says so.
