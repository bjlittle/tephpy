# Edge-Label Test Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the seven surviving findings parked during the review of #51 and
collected in :issue:`53` — four test-hardening edits, one new test for the untested
top-to-right edge move, and two production tidy-ups — with no change in behaviour.

**Architecture:** Nothing here changes the design. Spec §3.2 already records the edge
claim/release contract and #51 plus #56 already implement it; this work only makes the
tests discriminate what they claim to discriminate, adds the one transition that was
probed but never pinned, and removes a redundant parameter. The single production
signature change is on a private method with one call site.

**Tech Stack:** Python 3.12–3.14, matplotlib 3.11, numpy, pytest, pixi, pre-commit,
towncrier.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-22-tephpy-design.md` §3.2. Cite it as
  `(spec §3.2)` in comments and docstrings, exactly as the surrounding code does.
- Line length 88 (`ruff`, `line-length = 88` in `pyproject.toml`). This binds comments
  and docstrings too.
- Docstrings are numpydoc (`convention = "numpy"`), validated by a `numpydoc-validation`
  pre-commit hook. Private methods are documented in full — every parameter, return and
  raise gets an entry.
- Run targeted tests with `pixi run --frozen pytest <path>`. Run the full suite with
  `pixi run --frozen tests` (the repo task, which adds coverage) and the hook gate with
  `pixi run --frozen lint`. `--frozen` is mandatory — never let pixi re-solve.
- **Line numbers in this plan are as of `main` at `f0abc9c`, before any task has run.**
  Tasks 2 and 3 both edit `tests/plotting/test_axes.py`, so Task 3's anchors have
  shifted by the time it runs. Anchor every edit on the function name and the quoted
  source, never on the line number alone.
- `pre-commit install` before the first commit. Hooks are not installed in a fresh
  clone or worktree, and a `no-commit-to-branch` hook is what stops a commit landing
  on `main`.
- **Two PRs, as for #55/#56.** This plan ships first as a docs-only PR on branch
  `debt/edge-label-hardening` — `docs/**` only, so it carries `skip-changelog` and no
  towncrier fragment. The implementation is the second PR: once the plan PR has merged,
  branch `debt/edge-label-hardening-impl` off an updated `main` and run Tasks 1-5 there.
  Tasks 1-5 below are the *implementation* PR; the plan PR is already done by the time
  Task 1 starts.
- **Type labels are applied automatically — never pass `--label` for one.** Two
  mechanisms run on every PR, and both fire. `.github/workflows/ci-label.yml` matches
  the **branch prefix**: `startsWith(head.ref, 'debt')` adds `type: tech-debt`, so both
  PRs in this work earn it from the branch name alone — which is the reason the branch
  is named `debt/...`. `.github/labeler.yml` matches **changed paths**: `docs/**` adds
  `type: documentation`, `tests/**` adds `type: testing`, `.github/**` adds `type: ci`.
  The one label needing a hand is `skip-changelog`, and only on the docs-only plan PR.
- Never commit to `main` (a `no-commit-to-branch` pre-commit hook enforces this).
- Execute in a git worktree (superpowers:using-git-worktrees). Once inside it, every
  Bash command, edit and build must use the worktree path — never `cd` to
  `/data/home/billlittle/projects/tephpy`, or the work lands on `main`.
- **No behaviour change.** The full suite must be green before and after every task.
  Baseline for the two touched test files: `158 passed`.

---

## Findings Disposition

The issue lists eight bullets under a prose count of "nine findings". Seven are live;
one is dead. Verified against `main` at `f0abc9c` (post-#56).

| Issue bullet | Now at | Task |
|---|---|---|
| Tautological `tick_values` assertion | `tests/plotting/test_isopleths.py:691` | 1 |
| Misleading curvature comment | `tests/plotting/test_isopleths.py:686-689` | 1 |
| `narrow` unpinned in the gutter test | `tests/plotting/test_axes.py:920` | 2 |
| Non-discriminating `get_ylabel() == ""` | `tests/plotting/test_axes.py:882-883` | 2 |
| Untested top-to-right edge move | — | 3 |
| `_claim_edge` takes `family` redundantly | `src/tephpy/plotting/axes.py:1107` | 4 |
| `_inline_members` docstring reads awkwardly | `src/tephpy/plotting/isopleths.py:1104` | 4 |
| `_edge_titles` write-only for top/right | `src/tephpy/plotting/axes.py:1178` | **none — dead** |

**Why the last one is dead.** At #51, `_release_edge` popped the title and then
returned early for top and right, removing the secondary axes outright — so the popped
value was never read. #56 rewrote release to *hide* the secondary rather than destroy
it, which deleted that early return; the popped title now reaches the
`axis.set_label_text("")` consumer below it. Probed on current `main`: claiming `top`
sets the axis label, releasing clears it to `""`. Nothing to fix. Task 5 records this
on the issue rather than dropping it silently.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `tests/plotting/test_isopleths.py` | Tests for `IsoplethFamily`, `_EdgeLocator`, `_EdgeFormatter`, `edge_crossings` | Modify 1 test |
| `tests/plotting/test_axes.py` | Tests for the `TephigramAxes` projection, including the edge claim/release lifecycle | Modify 2 tests, add 1, add 2 imports |
| `src/tephpy/plotting/axes.py` | The projection; owns the five families and the edge lifecycle | Modify `_claim_edge` signature and its sole call site in `_sync_edge_labels` |
| `src/tephpy/plotting/isopleths.py` | Isopleth families, edge locator and formatter | Modify one docstring summary line |
| `changelog/<PR>.internal.rst` | Towncrier fragment | Create |

No new modules, no new public names, no new config key.

---

## Task 1: Make the locator's view-tracking test discriminate

**Files:**
- Modify: `tests/plotting/test_isopleths.py:676-693`

**Interfaces:**
- Consumes: `isopleths._EdgeLocator(family, edge)` — `__call__() -> list[float]` sets
  `self.positions`/`self.values` and returns the same list object it assigned to
  `self.positions`; `tick_values(vmin, vmax) -> list[float]` discards both arguments
  and delegates to `__call__`.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Read the current test to confirm it still matches**

Run: `sed -n '676,693p' tests/plotting/test_isopleths.py`

Expected — exactly this:

```python
def test_edge_locator_tracks_the_view():
    """Matplotlib calls the locator every draw, so zoom needs no plumbing."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        locator = isopleths._EdgeLocator(ax.isobars(), "left")
        wide = locator()
        ax.set_extent(((900.0, -10.0), (500.0, 20.0)))
        fig.canvas.draw()
        assert locator() != wide
        # Note: The zoomed extent may include isobars outside the nominal
        # 500-900 hPa range because isobars curve and may enter from the view
        # edges; edge_crossings filters to members that actually reach the
        # requested edge within the view bounds.
        assert all(450.0 <= value <= 900.0 for value in locator.values)
        assert locator.tick_values(0.0, 1.0) == locator.positions
    finally:
        plt.close(fig)
```

If it differs, stop and re-derive the edit — do not force the replacement below.

- [ ] **Step 2: Replace the test body**

Replace the whole function with:

```python
def test_edge_locator_tracks_the_view():
    """Matplotlib calls the locator every draw, so zoom needs no plumbing."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        locator = isopleths._EdgeLocator(ax.isobars(), "left")
        wide = locator()
        ax.set_extent(((900.0, -10.0), (500.0, 20.0)))
        fig.canvas.draw()
        zoomed = locator()
        assert zoomed != wide
        # Two separate reasons the ticks reach below the 500 hPa the extent
        # names.  The zoom ladder promotes the isobar step to 20 hPa at this
        # view width, which is what puts 460 and 480 in the family at all;
        # and the left edge is a vertical line in (x, y) space rather than a
        # constant-pressure line, so it sweeps down to ~457 hPa at the
        # top-left corner and those two members genuinely cross it.  The
        # curvature is why the 450 bound cannot be read off the corner
        # pressures; the ladder is why these particular members exist.
        assert all(450.0 <= value <= 900.0 for value in locator.values)
        # ``tick_values`` must ignore the interval matplotlib hands it and
        # return the crossings.  Compared against the snapshot above, never
        # against ``locator.positions``: ``__call__`` returns the very list
        # it assigns there, so ``tick_values(...) == locator.positions`` is
        # an identity comparison that cannot fail.
        ticks = locator.tick_values(0.0, 1.0)
        assert ticks is not zoomed
        assert ticks == zoomed
    finally:
        plt.close(fig)
```

- [ ] **Step 3: Prove the new assertions can fail**

Temporarily break `tick_values` in `src/tephpy/plotting/isopleths.py` — change its body
from

```python
        del vmin, vmax
        return self()
```

to

```python
        del vmax
        return [p for p in self() if p >= vmin]
```

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py::test_edge_locator_tracks_the_view -q`

Expected: FAIL on `assert ticks == zoomed`. The old assertion would have passed here —
that is the point of the change. **Revert the edit to `isopleths.py` immediately.**

- [ ] **Step 4: Run the test to verify it passes**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -q`

Expected: PASS, no reduction in the collected count.

- [ ] **Step 5: Commit**

```bash
git add tests/plotting/test_isopleths.py
git commit -m "test: make the edge locator's view-tracking assertions discriminate"
```

---

## Task 2: Pin the gutter test's unlabelled pad and retarget the release comment

**Files:**
- Modify: `tests/plotting/test_axes.py:19-34` (import block)
- Modify: `tests/plotting/test_axes.py:882-883` (release comment)
- Modify: `tests/plotting/test_axes.py:918-925` (gutter assertions)

**Interfaces:**
- Consumes: `tephpy._constants.BARB_GUTTER_PAD` (`0.1`, inches) and
  `EDGE_LABEL_GUTTER_PAD` (`0.55`, inches). `TephigramAxes._relayout_side_panels`
  substitutes the latter for the former on the panel nearest the diagram while the
  right edge is claimed.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Add `BARB_GUTTER_PAD` to the constants import**

In `tests/plotting/test_axes.py`, change

```python
from tephpy._constants import (
    CAPE_COLOR,
```

to

```python
from tephpy._constants import (
    BARB_GUTTER_PAD,
    CAPE_COLOR,
```

- [ ] **Step 2: Pin `narrow` in the gutter test**

In `test_right_edge_labels_widen_the_gutter_pad`, change

```python
        narrow = ax._barb_gutter.get_window_extent().x0 - ax.get_window_extent().x1
        ax.isobars(labels="right")
```

to

```python
        narrow = ax._barb_gutter.get_window_extent().x0 - ax.get_window_extent().x1
        # Pinned, not merely ordered.  The load-bearing half of this test is
        # that an unclaimed right edge leaves the layout exactly as it was
        # before edges could be labelled at all; an inequality against
        # ``wide`` would still pass if the unlabelled pad drifted.
        assert narrow == pytest.approx(BARB_GUTTER_PAD * fig.dpi, abs=1.0)
        ax.isobars(labels="right")
```

Leave the existing `wide` assertion and `assert wide > narrow` untouched — the
inequality stays as the cheap statement of intent.

- [ ] **Step 3: Retarget the release comment**

In `test_an_invisible_family_releases_its_edge`, change

```python
        # Release must clear the auto-title it set (spec §3.2).
        assert ax.get_ylabel() == ""
```

to

```python
        # Release clears the auto-title it set (spec §3.2).  That it clears
        # *only* its own title and never a user's is a separate clause, and
        # is pinned by the third leg of
        # ``test_a_user_axis_title_wins_either_way`` — not by this assertion,
        # which passes either way.
        assert ax.get_ylabel() == ""
```

The assertion itself is deliberately unchanged: it does pin real behaviour (that
release clears the title at all), and duplicating the guard coverage that already
exists would leave two tests on one clause.

- [ ] **Step 4: Prove the pinned `narrow` can fail**

Temporarily change the new assertion's expected value to
`BARB_GUTTER_PAD * fig.dpi * 2`.

Run: `pixi run --frozen pytest tests/plotting/test_axes.py::test_right_edge_labels_widen_the_gutter_pad -q`

Expected: FAIL, reporting approximately `10.0 != 20.0`. **Revert to
`BARB_GUTTER_PAD * fig.dpi`.**

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -q`

Expected: PASS, no reduction in the collected count.

- [ ] **Step 6: Commit**

```bash
git add tests/plotting/test_axes.py
git commit -m "test: pin the unlabelled gutter pad and retarget the release comment"
```

---

## Task 3: Cover a family moving its own edge

**Files:**
- Modify: `tests/plotting/test_axes.py:9-14` (matplotlib import block)
- Modify: `tests/plotting/test_axes.py` — insert one test after
  `test_top_and_right_use_lazily_created_secondary_axes` (ends at line 805) and before
  `test_one_family_per_edge` (line 807)

**Interfaces:**
- Consumes: `TephigramAxes.edge_axis(edge) -> matplotlib.axis.Axis`;
  `TephigramAxes._edge_owners: dict[str, str]`;
  `TephigramAxes._secondary_axes: dict[str, SecondaryAxis]`;
  `TephigramAxes._edge_titles: dict[str, str]`;
  `tephpy._constants.EDGE_AXIS_TITLES["isobars"] == "Pressure (hPa)"`; the module-level
  `_ticks(axis)` helper already in this file, which returns the rendered tick label
  strings.
- Produces: nothing consumed by later tasks.

**Why this transition is the interesting one.** `_sync_edge_labels` walks `EDGES` in
order and, for each edge, releases the previous owner then claims the new one. Moving a
family from `top` to `right` is the only case where one secondary axes is released and
a different one is built inside a single sync. Every existing test moves an edge to
inline (`labels=True`) or hands an edge between families — never both halves of a move
in one resolve.

**Expected values, probed on `main` at `f0abc9c`** — do not guess these:

| Assertion | Value |
|---|---|
| `_ticks(top)` before the move | `["150", "200", "200"]` (200 hPa leaves and re-enters the view) |
| `_ticks(right)` after the move | `["200", "250", "300"]` |
| `EDGE_AXIS_TITLES["isobars"]` | `"Pressure (hPa)"` |
| `len(ax.child_axes)` after | `2` |

- [ ] **Step 1: Add the `AutoLocator` import**

In `tests/plotting/test_axes.py`, after `import matplotlib.pyplot as plt`, add

```python
from matplotlib.ticker import AutoLocator
```

so the matplotlib block reads

```python
import matplotlib.colors as mcolors
from matplotlib.patches import PathPatch
from matplotlib.path import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoLocator
```

- [ ] **Step 2: Write the failing test**

Insert between `test_top_and_right_use_lazily_created_secondary_axes` and
`test_one_family_per_edge`:

```python
def test_a_family_can_move_its_own_edge():
    """Top to right in one resolve: a release and a claim in the same sync.

    The only transition that releases one secondary axes and builds another
    inside a single ``_sync_edge_labels``.  The released edge must come away
    fully unclaimed — hidden, untitled and back on matplotlib's linear-axis
    defaults — while the claimed edge comes up ticked and titled (spec §3.2).
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="top")
        fig.canvas.draw()
        top = ax.edge_axis("top")
        assert _ticks(top) == ["150", "200", "200"]
        ax.isobars(labels="right")
        fig.canvas.draw()
        assert ax._edge_owners == {"right": "isobars"}
        # The top secondary hides rather than being destroyed, so the handle
        # taken before the move is still the live axis afterwards.
        assert ax._secondary_axes["top"].xaxis is top
        assert not ax._secondary_axes["top"].get_visible()
        assert top.get_label_text() == ""
        # Not just hidden: the locator goes back to matplotlib's default, so
        # the released edge no longer holds the family through an
        # ``_EdgeLocator``.
        assert isinstance(top.get_major_locator(), AutoLocator)
        right = ax.edge_axis("right")
        assert ax._secondary_axes["right"].get_visible()
        assert right.get_label_text() == EDGE_AXIS_TITLES["isobars"]
        assert _ticks(right) == ["200", "250", "300"]
        assert ax._edge_titles == {"right": EDGE_AXIS_TITLES["isobars"]}
        assert len(ax.child_axes) == 2
    finally:
        plt.close(fig)
```

- [ ] **Step 3: Run the new test**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py::test_a_family_can_move_its_own_edge -q`

Expected: **PASS.** This is characterisation coverage for behaviour that already works
— the transition was probed during the #51 review but never pinned. There is no
implementation step; the test *is* the deliverable.

- [ ] **Step 4: Prove it discriminates**

Temporarily comment out the `self._release_edge(edge)` call in `_sync_edge_labels`
(`src/tephpy/plotting/axes.py:1226`).

Run: `pixi run --frozen pytest tests/plotting/test_axes.py::test_a_family_can_move_its_own_edge -q`

Expected: FAIL — the top secondary stays visible and keeps its title and
`_EdgeLocator`. **Revert the edit to `axes.py`.**

- [ ] **Step 5: Run the file to verify nothing regressed**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -q`

Expected: PASS, collected count one higher than the baseline.

- [ ] **Step 6: Commit**

```bash
git add tests/plotting/test_axes.py
git commit -m "test: pin a family moving its own edge from top to right"
```

---

## Task 4: Drop the redundant `_claim_edge` parameter and copy-edit the docstring

**Files:**
- Modify: `src/tephpy/plotting/axes.py:1107-1132` (`_claim_edge` signature, docstring
  and first statement)
- Modify: `src/tephpy/plotting/axes.py:1231-1236` (the sole call site in
  `_sync_edge_labels`)
- Modify: `src/tephpy/plotting/isopleths.py:1104` (`_inline_members` summary line)

**Interfaces:**
- Consumes: `TephigramAxes._families: dict[str, IsoplethFamily]`, keyed by accessor
  name — the same `name` `_claim_edge` already takes to key `EDGE_AXIS_TITLES`.
- Produces: `_claim_edge(self, edge: str, name: str, *, first: bool) -> None`. Private,
  one call site, no deprecation surface.

- [ ] **Step 1: Confirm there is exactly one call site**

Run: `grep -rn "_claim_edge" src/ tests/ docs/`

Expected: the definition at `src/tephpy/plotting/axes.py:1107` and the call at
`src/tephpy/plotting/axes.py:1231`. Nothing else. If a test calls it directly, that
test must be updated in this task too.

- [ ] **Step 2: Narrow the signature**

Change

```python
    def _claim_edge(
        self, edge: str, name: str, family: IsoplethFamily, *, first: bool
    ) -> None:
```

to

```python
    def _claim_edge(self, edge: str, name: str, *, first: bool) -> None:
```

In the same docstring, delete the `family` parameter entry

```python
        family : IsoplethFamily
            The claiming family.
```

and extend the `name` entry from

```python
        name : str
            The claiming family's accessor name, which keys the axis titles.
```

to

```python
        name : str
            The claiming family's accessor name, which keys both the axis
            titles and ``self._families``.
```

Then add the lookup as the method's first statement, immediately above the existing
`axis = self._edge_axis(edge)`:

```python
        family = self._families[name]
        axis = self._edge_axis(edge)
```

- [ ] **Step 3: Update the call site**

In `_sync_edge_labels`, change

```python
                    self._claim_edge(
                        edge,
                        owner,
                        self._families[owner],
                        first=previous != owner,
                    )
```

to

```python
                    self._claim_edge(edge, owner, first=previous != owner)
```

- [ ] **Step 4: Copy-edit the `_inline_members` summary**

In `src/tephpy/plotting/isopleths.py`, change

```python
        """Return the selected members that no claimed edge labels.
```

to

```python
        """Return the selected members no claimed edge already labels.
```

Leave the rest of the docstring alone.

- [ ] **Step 5: Confirm `IsoplethFamily` is still imported for a reason**

Run: `grep -n "IsoplethFamily" src/tephpy/plotting/axes.py`

Expected: still used by the `_families` annotation (line 364), the construction in
`clear` (line 437) and the accessor return annotations. The import at line 75 stays.
`ruff` would flag it in `lint` if it did not.

- [ ] **Step 6: Run the full suite**

Run: `pixi run --frozen tests`

Expected: PASS, all tests. A `TypeError` about positional arguments here means the call
site and the signature disagree.

- [ ] **Step 7: Run the lint gate**

Run: `pixi run --frozen lint`

Expected: PASS. The `numpydoc-validation` hook is what catches a docstring parameter
list that no longer matches the signature.

- [ ] **Step 8: Commit**

```bash
git add src/tephpy/plotting/axes.py src/tephpy/plotting/isopleths.py
git commit -m "refactor: derive the claiming family from its name in _claim_edge"
```

---

## Task 5: Changelog fragment, PR and issue disposition

**Files:**
- Create: `changelog/<PR>.internal.rst`

**Interfaces:**
- Consumes: towncrier types declared in `pyproject.toml` — `breaking`, `feature`,
  `enhancement`, `bugfix`, `dependency`, `documentation`, `internal`, `misc`. This work
  is `internal`: tests and a private refactor, no user-visible change.
- Produces: nothing.

**Fragment naming.** Fragments are named for the **PR** number, not the issue number
(see `changelog/56.enhancement.rst`, which cites `:issue:`52``). The PR number is not
known until the PR is opened, so this task opens the PR first and then adds the
fragment.

- [ ] **Step 1: Push the branch and open the PR**

```bash
git push -u origin debt/edge-label-hardening-impl
gh pr create --repo bjlittle/tephpy \
  --title "Harden the edge-label tests and tidy the residual bookkeeping" \
  --body "$(cat <<'EOF'
Closes #53. Implements the plan merged in the preceding docs-only PR.

Seven of the eight findings parked during the review of #51. The eighth —
`_edge_titles` being write-only for the top and right edges — was already
fixed by #56, which replaced the early return that made the popped title dead
with a hide-rather-than-destroy release. See the issue for the detail.

No behaviour change: four test edits, one new test, and one private signature
narrowed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Note the PR number it returns — the changelog fragment is named for it.

- [ ] **Step 2: Write the fragment**

Create `changelog/<PR>.internal.rst`, substituting the PR number for `<PR>`:

```rst
Hardened the isopleth edge-label tests and tidied the bookkeeping they left
behind (:issue:`53`). Two assertions that could not fail were replaced: the edge
locator's ``tick_values`` was compared against the very list object its
``__call__`` assigns to ``positions``, and the side-panel gutter test ordered its
unlabelled pad against the widened one instead of pinning it. New coverage was
added for a family moving its own claim from the top edge to the right — the one
transition that releases one secondary axes and builds another inside a single
resolve. ``TephigramAxes._claim_edge`` no longer takes the family that its
``name`` argument already identifies. (:user:`claude`)
```

- [ ] **Step 3: Verify the fragment renders and its cross-references resolve**

Run: `pixi run --frozen docs`

Expected: a clean build with no warnings about `:issue:` or `:user:`. The `docs` task
depends on `docs-clean`, so this is a full rebuild — an incremental build serves a
stale towncrier draft and will not show a broken fragment.

- [ ] **Step 4: Commit and push**

```bash
git add changelog/
git commit -m "docs: add the edge-label hardening changelog fragment"
git push
```

- [ ] **Step 5: Record the dead finding on the issue**

```bash
gh issue comment 53 --repo bjlittle/tephpy --body "$(cat <<'EOF'
Verified all eight bullets against `main` at f0abc9c before starting. Seven are
live and are addressed in the linked PR. One is dead:

**`axes.py` — `_edge_titles` entries for top/right are write-only** — already
fixed by #56. At #51 `_release_edge` popped the title and then returned early
for top and right, removing the secondary axes outright, so the popped value was
never read. #56 rewrote release to *hide* the secondary rather than destroy it,
which removed that early return; the popped title now reaches the
`axis.set_label_text("")` consumer below it. Probed on current `main`: claiming
`top` sets the axis label, releasing clears it to `""`. No change needed.

Two smaller corrections to the issue text while it is open: the prose says
"nine minor findings" but lists eight; and the top-to-right bullet describes the
move as tearing down and recreating a secondary axis, which was true at #51 but
not after #56 — the old secondary is now hidden and kept.
EOF
)"
```

- [ ] **Step 6: Final gate**

Run: `pixi run --frozen lint && pixi run --frozen tests`

Expected: both PASS. The full suite must be green, with the collected count exactly one
higher than the baseline.

---

## Out of Scope

- Making `_EdgeLocator.__call__` return a copy rather than the list it assigns to
  `self.positions`. That would let the test assert non-identity directly, but it is a
  production change to fix a test, and matplotlib locators are not documented to return
  a fresh list. The test compares against a snapshot instead.
- Adding a user-title leg to `test_an_invisible_family_releases_its_edge`. The
  `== title` clause is already pinned by the third leg of
  `test_a_user_axis_title_wins_either_way`; a second test on one clause is duplication.
  The comment is retargeted instead.
- Popping `_edge_tick_colors` on release. It is deliberately retained — the comment at
  `axes.py:1153-1158` explains that the memory is keyed by owner as well as RGBA
  precisely so it can survive a release. `clear()` resets it. Not a leak, not in the
  issue.
- Any change to spec §3.2. Nothing here alters the design it records.
