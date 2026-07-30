# Edge Tick and Title Styling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split identity from presentation on a claimed diagram edge, so a user's
`tick_params`, `grid` and cleared axis title survive an unrelated isopleth family's
resolve, and publish `ax.edge_axis(edge)` as the uniform handle on all four edges.

**Architecture:** `TephigramAxes._claim_edge` currently does two jobs on one code path,
re-run on every family resolve: it points an edge at a family (*identity*) and it
re-asserts how that edge's ticks look (*presentation*). Presentation moves to a new
`_style_edge_axis`, called once when an edge axis comes into existence — `clear()` for the
axes' own `xaxis`/`yaxis`, the lazy build in `_edge_axis` for a top or right secondary.
Claiming keeps only identity, gated on a new `first` flag that `_sync_edge_labels` derives
from the prior owner, plus the tick colour, re-applied only when the owning family's own
RGBA changes. Releasing a top or right edge hides its secondary axes instead of destroying
it, so a held `Axis` stays live across a release and reclaim.

**Tech Stack:** Python 3.12–3.14, matplotlib 3.11, numpy, pytest, pixi, pre-commit,
towncrier.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-22-tephpy-design.md` §3.2 (the three bullets
  beginning "A claimed edge's ticks are stock matplotlib and yours to style"). Cite it as
  `(spec §3.2)` in comments and docstrings, exactly as the surrounding code does.
- Every module starts with the 4-line BSD copyright header and `from __future__ import
  annotations`. Do not add either to files that already have them.
- Line length 88 (`ruff`, `line-length = 88` in `pyproject.toml`).
- Docstrings are numpydoc (`convention = "numpy"`), validated by a `numpydoc-validation`
  pre-commit hook. **Private methods are documented in full too** — see the existing
  `_claim_edge`. Every parameter, return and raise gets an entry.
- `TephpyError` and its subclasses are for user-correctable *data* input (spec §6). The
  plotting layer raises builtin `TypeError`/`ValueError`. Do not introduce a tephpy
  exception in this work.
- No new `tephpy.config` section and no new accessor keyword. This work adds exactly one
  public name: `TephigramAxes.edge_axis`.
- Run tests with `pixi run --frozen pytest ...`. Run the full gate with
  `pixi run --frozen lint`. `--frozen` is mandatory — never let pixi re-solve.
- This plan and the spec bullets it implements ship as a docs-only PR (#55) on the
  `edge-styling` branch. The implementation is a separate PR: once #55 has merged, branch
  `edge-styling-impl` off an updated `main` and commit there. Never commit to `main`
  (a `no-commit-to-branch` pre-commit hook enforces this).

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/tephpy/plotting/axes.py` | The `TephigramAxes` projection; owns the five families and the edge claim/release lifecycle | Modify: `clear`, `_edge_axis`, `_claim_edge`, `_release_edge`, `_sync_edge_labels`; add `_style_edge_axis` and `edge_axis`; add the `_edge_tick_colors` attribute |
| `tests/plotting/test_axes.py` | Tests for the projection, including every existing edge-claim test | Modify 2 existing tests; add 8 |
| `changelog/<PR>.bugfix.rst` | Towncrier fragment for the styling wipe | Create |
| `changelog/<PR>.enhancement.rst` | Towncrier fragment for `edge_axis` | Create |

No new modules. `src/tephpy/plotting/isopleths.py`, `_constants.py` and `_config.py` are
**not** touched: `_EdgeLocator` already holds a live family reference and recomputes on
every draw, the conventions already live in `_constants`, and no option is added.

---

## Task 1: Move tick presentation to axis creation

This is the headline fix. After this task a user's `tick_params` and `grid` on a claimed
edge stop being reverted. Claiming still re-runs its identity work on every sync — Task 2
handles that.

**Files:**
- Modify: `src/tephpy/plotting/axes.py:375-429` (`clear`), `:979-1010` (`_edge_axis`),
  `:1012-1060` (`_claim_edge`), `:1062-1088` (`_release_edge`)
- Test: `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes: `LABEL_FONTSIZE`, `EDGE_TICK_LENGTH`, `EDGE_TICK_PAD` (already imported in
  `axes.py`); `matplotlib.axis.Axis` (already in the `TYPE_CHECKING` block)
- Produces: `TephigramAxes._style_edge_axis(self, axis: Axis) -> None`, wired into `clear`
  and `_edge_axis` by this task; no later task calls it

**Verified 2026-07-30** — the two matplotlib behaviours this task rests on: `set_tick_params`
*merges* into an axis' `_major_tick_kw` (so does `set_ticks_position`, which is why the pins
in Step 4 may follow the conventions without wiping them), and matplotlib replays that dict
onto the tick artists it rebuilds when a claim swaps the locator. Only `Axes.clear` empties
it, which is what makes `ax.clear()` the reset.

- [ ] **Step 1: Write the failing tests**

Add to `tests/plotting/test_axes.py`, immediately after the existing
`test_a_claimed_edge_draws_no_gridlines`:

```python
def test_user_tick_styling_survives_an_unrelated_family_resolve():
    """Presentation is the user's once the edge is claimed (spec §3.2).

    The first implementation re-asserted ``LABEL_FONTSIZE`` and the tick
    length and pad on every sync, so an *unrelated* family's resolve
    silently reverted a user's ``tick_params``.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        ax.tick_params(axis="y", labelsize=14)
        fig.canvas.draw()
        assert {t.label1.get_fontsize() for t in ax.yaxis.get_major_ticks()} == {14.0}
        ax.isotherms(color="grey")
        fig.canvas.draw()
        assert {t.label1.get_fontsize() for t in ax.yaxis.get_major_ticks()} == {14.0}
        # Nor may the owning family's own restyle revert it.
        ax.isobars(linewidth=2.0)
        fig.canvas.draw()
        assert {t.label1.get_fontsize() for t in ax.yaxis.get_major_ticks()} == {14.0}
    finally:
        plt.close(fig)


def test_clear_restores_the_edge_tick_conventions():
    """``ax.clear()`` is the reset for edge tick presentation (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        ax.tick_params(axis="y", labelsize=14)
        fig.canvas.draw()
        ax.clear()
        ax.isobars(labels="left")
        fig.canvas.draw()
        sizes = {t.label1.get_fontsize() for t in ax.yaxis.get_major_ticks()}
        assert sizes == {LABEL_FONTSIZE}
    finally:
        plt.close(fig)
```

Add `LABEL_FONTSIZE` to the `from tephpy._constants import (...)` block at the top of the
file, in alphabetical order — it goes between `ISOBAR_COLOR` and `PROFILE_DEWPOINT_COLOR`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py::test_user_tick_styling_survives_an_unrelated_family_resolve tests/plotting/test_axes.py::test_clear_restores_the_edge_tick_conventions -v`

Expected: `test_user_tick_styling_survives_an_unrelated_family_resolve` FAILS — the second
assertion finds `{8.0}`, because `ax.isotherms(color="grey")` triggers a sync that
re-asserts `LABEL_FONTSIZE`. `test_clear_restores_the_edge_tick_conventions` PASSES already
(the claim re-asserts the conventions anyway); it is a regression guard for this task's
change, so a pass here is expected and correct.

- [ ] **Step 3: Add `_style_edge_axis`**

Insert this method in `src/tephpy/plotting/axes.py` immediately **before** `_edge_axis`
(i.e. before the `def _edge_axis(self, edge: str) -> Axis:` at line 979):

```python
def _style_edge_axis(self, axis: Axis) -> None:
    """Stamp the tephigram tick conventions on one edge axis.

    Applied once, when the axis comes into existence — :meth:`clear` for
    the axes' own ``xaxis``/``yaxis``, the lazy build in
    :meth:`_edge_axis` for a top or right secondary — and never
    re-applied, so a user's ``tick_params`` on a claimed edge survives
    every later family resolve (spec §3.2). Matplotlib offers no
    provenance on ``set_tick_params``, so *when* is the only guard
    available. The conventions replay onto the tick artists matplotlib
    rebuilds when a claim swaps the locator, because they live in the
    axis' ``_major_tick_kw``.

    Parameters
    ----------
    axis : matplotlib.axis.Axis
        The axis that draws one diagram edge's ticks.
    """
    axis.set_tick_params(
        labelsize=LABEL_FONTSIZE,
        length=EDGE_TICK_LENGTH,
        pad=EDGE_TICK_PAD,
    )
    # Lines of constant data-space x or y mean nothing on a tephigram: the
    # ticks are the crossings, not a scale to rule off. Suppressing here
    # lands after ``Axes.clear`` has read ``rcParams["axes.grid"]``, which
    # several styles set, so a style cannot smuggle them in — while an
    # explicit later ``ax.grid(True)`` is the user's call (spec §3.2).
    axis.grid(visible=False, which="both")
```

- [ ] **Step 4: Call it from `clear`**

In `clear`, replace these two lines (currently at `:397-398`):

```python
self.xaxis.set_visible(False)
self.yaxis.set_visible(False)
```

with:

```python
self.xaxis.set_visible(False)
self.yaxis.set_visible(False)
# Presentation is stamped once, here, and never re-asserted, so it is
# the user's from a claim onwards (spec §3.2).
self._style_edge_axis(self.xaxis)
self._style_edge_axis(self.yaxis)
# The classic style mirrors ticks onto the opposite edge, which would
# collide with that edge's own family. Pinned on the concrete
# ``XAxis``/``YAxis``, whose ``set_ticks_position`` take different
# values, rather than through the ``Axis``-typed helper above.
self.xaxis.set_ticks_position("bottom")
self.yaxis.set_ticks_position("left")
```

- [ ] **Step 5: Call it from `_edge_axis`**

In `_edge_axis`, replace:

```python
self._secondary_axes[edge] = secondary
return secondary.xaxis if edge == "top" else secondary.yaxis
```

with:

```
            self._secondary_axes[edge] = secondary
            self._style_edge_axis(
                secondary.xaxis if edge == "top" else secondary.yaxis
            )
        return secondary.xaxis if edge == "top" else secondary.yaxis
```

The `_style_edge_axis` call is inside the `if secondary is None:` block, so it runs only on
the lazy build. A `SecondaryAxis` pins its own tick position, so there is no counterpart to
the `set_ticks_position` lines above.

- [ ] **Step 6: Strip presentation out of `_claim_edge`**

In `_claim_edge`, replace this block:

```
        rgba = mcolors.to_rgba(family.options.color, family.options.alpha)
        axis.set_tick_params(
            color=rgba,
            labelcolor=rgba,
            labelsize=LABEL_FONTSIZE,
            length=EDGE_TICK_LENGTH,
            pad=EDGE_TICK_PAD,
        )
        # Making the axis visible would otherwise let ``ax.grid(True)`` — and
        # ``rcParams["axes.grid"]``, which several styles set — draw lines of
        # constant data-space x or y, which mean nothing on a tephigram. The
        # ticks are the crossings, not a scale to rule off (spec §3.1/§3.2).
        axis.grid(visible=False, which="both")
        if edge == "bottom":
            # The classic style mirrors ticks onto the opposite edge, which
            # would collide with that edge's own family.
            self.xaxis.set_ticks_position("bottom")
        elif edge == "left":
            self.yaxis.set_ticks_position("left")
        if not axis.get_label_text():
```

with:

```
        rgba = mcolors.to_rgba(family.options.color, family.options.alpha)
        axis.set_tick_params(color=rgba, labelcolor=rgba)
        if not axis.get_label_text():
```

Then update the method's summary line, replacing:

```
        """Point one edge's ticks at a family. Idempotent.

        Re-applied on every sync so a family's restyle reaches its ticks.
```

with:

```
        """Point one edge's ticks at a family. Idempotent.

        Identity only — locator, formatter, visibility, colour and title.
        How the ticks look is stamped once by :meth:`_style_edge_axis` when
        the edge axis is created and is the user's thereafter (spec §3.2).
```

- [ ] **Step 7: Stop `_release_edge` resetting presentation**

In `_release_edge`, delete these three lines:

```python
# Resetting the tick params also restores the axis' grid state from
# ``rcParams["axes.grid"]``, undoing the claim's ``grid(False)``.
axis.set_tick_params(reset=True, which="both")
```

The released axis is hidden, so its leftover colour and grid state are not rendered, and a
later claim by a different family re-applies the colour.

- [ ] **Step 8: Update the two existing tests this changes**

In `test_a_claimed_edge_draws_no_gridlines`, replace the release leg:

```python
# Release hands the axis back to the rcParams default.
ax.isobars(labels=True)
fig.canvas.draw()
assert ax.xaxis._major_tick_kw["gridOn"]
```

with:

```python
# Presentation is the user's after the claim: an explicit
# ``ax.grid(True)`` is honoured, and an unrelated family's
# resolve no longer wipes it (spec §3.2).
ax.grid(True)
ax.isotherms(color="grey")
fig.canvas.draw()
gridlines = ax.xaxis.get_gridlines()
assert gridlines
assert all(line.get_visible() for line in gridlines)
```

The first leg — a claim suppressing `rcParams["axes.grid"]` — is unchanged and is the leg
that matters; the suppression simply happens at axis creation now.

In the same test's docstring, append a sentence after the existing text:

```
    claiming an edge must not smuggle that scale back in as gridlines.
    Suppression happens once, when the edge axis is created, which is after
    ``Axes.clear`` reads the rcParam — so a style still cannot smuggle them
    in, and an explicit ``ax.grid(True)`` is honoured (spec §3.2).
```

- [ ] **Step 9: Run the full projection test module**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -v`

Expected: PASS, including `test_a_user_axis_title_wins_either_way`,
`test_an_invisible_family_releases_its_edge`, `test_clear_drops_every_edge_claim`,
`test_no_edge_is_claimed_by_default` and `test_family_alpha_reaches_both_label_routes`,
none of which this task changes. If `test_top_and_right_use_lazily_created_secondary_axes`
fails, you have changed destroy behaviour — that belongs to Task 3; revert it here.

- [ ] **Step 10: Confirm the default appearance is unchanged**

Run: `pixi run --frozen pytest tests/plotting/test_images.py --mpl -v`

Expected: PASS with no baseline regeneration. The same conventions are applied, only at a
different moment. **Do not run `pixi run --frozen baselines`** — if an image test fails,
the change is wrong, not the baseline.

- [ ] **Step 11: Commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
git commit -m "fix: stamp edge tick conventions once, at axis creation

_claim_edge re-asserted labelsize, tick length, pad and grid suppression on
every family resolve, so an unrelated family's restyle silently reverted a
user's tick_params and re-suppressed gridlines an explicit ax.grid(True) had
enabled. Presentation moves to _style_edge_axis, called when the edge axis is
created — clear() for xaxis/yaxis, the lazy build for a secondary — and is the
user's from a claim onwards (spec §3.2).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: Make claiming idempotent

A sync that changes nothing must now touch nothing. This gates the identity work on a
first claim and gives the tick colour a memory, which is also what makes a cleared axis
title stay cleared.

**Files:**
- Modify: `src/tephpy/plotting/axes.py` — the class attribute block at `:363-373`,
  `clear`, `_claim_edge`, `_sync_edge_labels`
- Test: `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes: `_style_edge_axis` from Task 1
- Produces: `TephigramAxes._claim_edge(self, edge, name, family, *, first: bool) -> None`
  — the `first` keyword is required; `TephigramAxes._edge_tick_colors:
  dict[str, tuple[float, float, float, float]]`

- [ ] **Step 1: Write the failing tests**

Add to `tests/plotting/test_axes.py`, after the tests added in Task 1:

```python
def test_only_a_new_owner_re_points_an_edge():
    """A sync that changes nothing touches nothing (spec §3.2).

    ``_EdgeLocator`` holds a live family reference and recomputes on every
    draw, so re-installing it on each sync is not only wasted work — it is
    the pattern that made unrelated resolves reach into a claimed edge.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        locator = ax.yaxis.get_major_locator()
        ax.isotherms(color="grey")
        ax.isobars(linewidth=2.0)
        assert ax.yaxis.get_major_locator() is locator
        ax.isobars(labels=False)
        ax.isotherms(labels="left")
        assert ax.yaxis.get_major_locator() is not locator
    finally:
        plt.close(fig)


def test_tick_colour_tracks_its_own_family_only():
    """Restyling the owning family restyles its ticks; nothing else does."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        ax.tick_params(axis="y", labelcolor="black")
        fig.canvas.draw()
        black = mcolors.to_rgba("black")
        assert mcolors.to_rgba(
            ax.yaxis.get_ticklabels()[0].get_color()
        ) == pytest.approx(black)
        # An unrelated family, and a non-colour restyle of the owner, leave it.
        ax.isotherms(color="grey")
        ax.isobars(linewidth=2.0)
        fig.canvas.draw()
        assert mcolors.to_rgba(
            ax.yaxis.get_ticklabels()[0].get_color()
        ) == pytest.approx(black)
        # The owner's own colour still reaches its ticks.
        ax.isobars(color="blue")
        fig.canvas.draw()
        assert mcolors.to_rgba(
            ax.yaxis.get_ticklabels()[0].get_color()
        ) == pytest.approx(mcolors.to_rgba("blue"))
    finally:
        plt.close(fig)


def test_a_cleared_axis_title_stays_cleared():
    """``set_ylabel("")`` durably means "ticks, no title" (spec §3.2).

    The fill-when-empty guard runs only on a first claim, so no later sync
    looks at the label again; a genuine release forgets tephpy's own title,
    so a reclaim stamps afresh.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
        ax.set_ylabel("")
        ax.isotherms(color="grey")
        ax.isobars(color="blue")
        ax.set_extent(DEFAULT_EXTENT)
        fig.canvas.draw()
        assert ax.get_ylabel() == ""
        # Dropping the labels and re-adding them is a fresh claim.
        ax.isobars(labels=False)
        ax.isobars(labels="left")
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
    finally:
        plt.close(fig)


def test_a_new_owner_restamps_the_axis_title():
    """Handing an edge to another family retitles it (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
        ax.isobars(labels=False)
        ax.isotherms(labels="left")
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isotherms"]
    finally:
        plt.close(fig)


def test_a_family_visibility_round_trip_preserves_edge_styling():
    """Toggling a family must not discard styling the user did not drop."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        ax.tick_params(axis="y", labelsize=14, labelcolor="black")
        fig.canvas.draw()
        ax.isobars(visible=False)
        ax.isobars(visible=True)
        fig.canvas.draw()
        assert {t.label1.get_fontsize() for t in ax.yaxis.get_major_ticks()} == {14.0}
        assert mcolors.to_rgba(
            ax.yaxis.get_ticklabels()[0].get_color()
        ) == pytest.approx(mcolors.to_rgba("black"))
    finally:
        plt.close(fig)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -k "only_a_new_owner or tracks_its_own_family or cleared_axis_title or new_owner_restamps or visibility_round_trip" -v`

Expected: `test_only_a_new_owner_re_points_an_edge` FAILS (a new `_EdgeLocator` is built on
every sync), `test_tick_colour_tracks_its_own_family_only` FAILS (colour is re-applied
unconditionally), `test_a_cleared_axis_title_stays_cleared` FAILS (the guard re-runs on
every sync and refills the label), `test_a_family_visibility_round_trip_preserves_edge_styling`
FAILS on the colour assertion. `test_a_new_owner_restamps_the_axis_title` PASSES already —
it is the regression guard that the `first` gate must not break.

- [ ] **Step 3: Declare the colour memory**

In the class attribute block, after `_edge_titles: dict[str, str]` (line 370), add:

```python
#: The RGBA last applied to each claimed edge's ticks, so a sync
#: re-applies only what the owning family actually changed. Survives
#: release, which is what makes a family visibility toggle a true round
#: trip; only :meth:`clear` empties it (spec §3.2).
_edge_tick_colors: dict[str, tuple[float, float, float, float]]
```

In `clear`, add the reset alongside the existing ones — after
`self._edge_titles = {}` (line 414):

```python
self._edge_tick_colors = {}
```

- [ ] **Step 4: Gate the identity work on `first`**

Replace the whole body of `_claim_edge` (everything after the docstring) with:

```python
axis = self._edge_axis(edge)
if first:
    locator = _EdgeLocator(family, edge)
    axis.set_major_locator(locator)
    axis.set_major_formatter(_EdgeFormatter(locator))
    # Crossings are exact positions; a minor tick between them means
    # nothing. NullLocator is also matplotlib's linear-axis default, so
    # release restores it.
    axis.set_minor_locator(NullLocator())
    secondary = self._secondary_axes.get(edge)
    if secondary is None:
        axis.set_visible(True)
    else:
        secondary.set_visible(True)
    if not axis.get_label_text():
        title = EDGE_AXIS_TITLES[name]
        axis.set_label_text(title)
        self._edge_titles[edge] = title
# ``set_tick_params`` takes no alpha, and per-``Tick`` alpha would not
# survive matplotlib rebuilding the tick artists on a locator change,
# so the family's alpha is baked into the tick RGBA instead.
rgba = mcolors.to_rgba(family.options.color, family.options.alpha)
if self._edge_tick_colors.get(edge) != rgba:
    axis.set_tick_params(color=rgba, labelcolor=rgba)
    self._edge_tick_colors[edge] = rgba
```

The `secondary`/`axis` split on visibility is deliberate: Task 3 makes a released secondary
hidden rather than destroyed, so a reclaim has to show the axes itself. Until Task 3 lands
the secondary is always freshly built and already visible, so the branch is a harmless
no-op — write it now so Task 3 needs no second edit here.

Then update the signature and docstring. Replace:

```
    def _claim_edge(self, edge: str, name: str, family: IsoplethFamily) -> None:
```

with:

```
    def _claim_edge(
        self, edge: str, name: str, family: IsoplethFamily, *, first: bool
    ) -> None:
```

and add this entry to the docstring's `Parameters` section, after the `family` entry:

```
        first : bool
            Whether this claim is the edge's first under this owner — the
            edge was unowned, or another family held it and has just been
            released. Identity is installed only then; a repeat claim
            re-applies nothing but a changed colour (spec §3.2).
```

- [ ] **Step 5: Derive `first` in `_sync_edge_labels`**

Replace the `for edge in EDGES:` loop body:

```python
for edge in EDGES:
    owner = claims.get(edge)
    if self._edge_owners.get(edge) not in (None, owner):
        self._release_edge(edge)
    if owner is None:
        self._edge_owners.pop(edge, None)
    else:
        self._edge_owners[edge] = owner
        self._claim_edge(edge, owner, self._families[owner])
```

with:

```python
for edge in EDGES:
    owner = claims.get(edge)
    previous = self._edge_owners.get(edge)
    if previous not in (None, owner):
        self._release_edge(edge)
    if owner is None:
        self._edge_owners.pop(edge, None)
    else:
        self._edge_owners[edge] = owner
        self._claim_edge(
            edge,
            owner,
            self._families[owner],
            first=previous != owner,
        )
```

- [ ] **Step 6: Run the new tests**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -k "only_a_new_owner or tracks_its_own_family or cleared_axis_title or new_owner_restamps or visibility_round_trip" -v`

Expected: all five PASS.

- [ ] **Step 7: Run the full module and the image tests**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py tests/plotting/test_images.py --mpl -v`

Expected: PASS. Pay attention to `test_a_user_axis_title_wins_either_way` — its third leg
(auto title applied, user replaces it, release must not clear the replacement) is the one
the `first` gate could plausibly break.

- [ ] **Step 8: Commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
git commit -m "fix: claim an edge's identity once, and its colour only on change

A sync now touches nothing when nothing changed: the locator, formatter,
visibility and title install on a first claim only, and the tick colour
re-applies only when the owning family's own RGBA differs from the one last
applied to that edge. The colour memory survives release, so toggling a
family's visibility is a true round trip, and the fill-when-empty title guard
running only on a first claim is what makes ax.set_ylabel(\"\") durable
(spec §3.2).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: Hide a released secondary axes instead of destroying it

**Files:**
- Modify: `src/tephpy/plotting/axes.py` — `_release_edge`
- Test: `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes: the `secondary`/`axis` visibility branch added to `_claim_edge` in Task 2
- Produces: `self._secondary_axes[edge]` persists across a release; a top or right
  `Axis` object is stable across a release and reclaim — Task 4's tests rely on this

- [ ] **Step 1: Write the failing test**

Add to `tests/plotting/test_axes.py`, after the Task 2 tests:

```python
def test_a_released_secondary_axes_is_hidden_not_destroyed():
    """A held handle must stay live across a release and reclaim (spec §3.2).

    Destroying the secondary axes took its ticks and title with it, so top
    and right could not behave like bottom and left, which are merely
    hidden. An invisible secondary returns ``None`` from ``get_tightbbox``,
    so the persistence costs nothing in layout.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        secondary = ax._secondary_axes["top"]
        axis = secondary.xaxis
        assert len(ax.child_axes) == 1
        ax.mixing_ratios(labels=True)
        fig.canvas.draw()
        assert ax._secondary_axes["top"] is secondary
        assert not secondary.get_visible()
        assert secondary.get_tightbbox() is None
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        assert ax._secondary_axes["top"] is secondary
        assert secondary.xaxis is axis
        assert secondary.get_visible()
        assert _ticks(axis)
    finally:
        plt.close(fig)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py::test_a_released_secondary_axes_is_hidden_not_destroyed -v`

Expected: FAIL with `KeyError: 'top'` — `_release_edge` pops and removes the secondary.

- [ ] **Step 3: Rewrite `_release_edge`**

Replace the whole body after the docstring:

```python
title = self._edge_titles.pop(edge, None)
if edge in {"top", "right"}:
    # The whole secondary axis goes, and its ticks and title with it —
    # so the title popped above is dead for these two edges, popped
    # only to keep the bookkeeping uniform.
    secondary = self._secondary_axes.pop(edge, None)
    if secondary is not None:
        secondary.remove()
    return
axis = self.xaxis if edge == "bottom" else self.yaxis
if title is not None and axis.get_label_text() == title:
    axis.set_label_text("")
axis.set_major_locator(AutoLocator())
axis.set_major_formatter(ScalarFormatter())
axis.set_minor_locator(NullLocator())
axis.set_visible(False)
```

with:

```python
title = self._edge_titles.pop(edge, None)
secondary = self._secondary_axes.get(edge)
if secondary is None and edge in {"top", "right"}:
    # Never claimed, so there is no secondary axes to return; the
    # early exit also keeps ``_edge_axis`` below from building one.
    return
axis = self._edge_axis(edge)
if title is not None and axis.get_label_text() == title:
    axis.set_label_text("")
axis.set_major_locator(AutoLocator())
axis.set_major_formatter(ScalarFormatter())
axis.set_minor_locator(NullLocator())
if secondary is None:
    axis.set_visible(False)
else:
    # The whole secondary axes hides, not merely its ``Axis``, or the
    # spine it owns would keep drawing. It is kept, not removed, so a
    # handle held across a release stays live and its ticks and title
    # survive the reclaim exactly as bottom and left do (spec §3.2).
    secondary.set_visible(False)
```

Also replace the docstring's summary line:

```
        """Return one edge to its unclaimed state.
```

with:

```
        """Return one edge to its unclaimed state.

        Teardown only: the locator and formatter go back to matplotlib's
        linear-axis defaults, tephpy's own axis title is cleared and
        forgotten, and the edge hides. Presentation is left exactly as it
        is — it belongs to the user, and the hidden axis renders none of it
        (spec §3.2).
```

- [ ] **Step 4: Run the new test**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py::test_a_released_secondary_axes_is_hidden_not_destroyed -v`

Expected: PASS.

- [ ] **Step 5: Update the existing test this changes**

`test_top_and_right_use_lazily_created_secondary_axes` asserts the old destroy behaviour.
Replace its docstring and its final leg:

```python
def test_top_and_right_use_lazily_created_secondary_axes():
    """Claiming creates one child axes; releasing removes it."""
```

becomes:

```python
def test_top_and_right_use_lazily_created_secondary_axes():
    """Claiming creates one child axes; releasing hides it (spec §3.2)."""
```

and:

```python
ax.mixing_ratios(labels=True)
fig.canvas.draw()
assert ax.child_axes == []
assert ax._secondary_axes == {}
```

becomes:

```python
ax.mixing_ratios(labels=True)
fig.canvas.draw()
assert len(ax.child_axes) == 1
assert not ax.child_axes[0].get_visible()
assert set(ax._secondary_axes) == {"top"}
```

- [ ] **Step 6: Run the full module and the image tests**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py tests/plotting/test_images.py --mpl -v`

Expected: PASS. `test_clear_drops_every_edge_claim` must still pass — `Axes.clear` empties
`child_axes`, and `clear` still resets `_secondary_axes` to `{}`.
`test_right_edge_labels_widen_the_gutter_pad` must also still pass: the side-panel relayout
keys on `_edge_owners`, not on the secondary's existence.

- [ ] **Step 7: Commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
git commit -m "fix: hide a released top or right secondary axes, do not destroy it

Destroying it took its ticks and title with it, so a handle held across a
release went dead and top and right could not behave like bottom and left,
which are merely hidden. An invisible secondary returns None from
get_tightbbox and Axes.clear still empties child_axes, so the persistence
costs nothing in layout and TephigramAxes.clear still reaps them (spec §3.2).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: Publish `ax.edge_axis(edge)`

**Files:**
- Modify: `src/tephpy/plotting/axes.py` — add `edge_axis` immediately before
  `_check_label_edges`
- Test: `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes: `_edge_axis` (private, creating); `EDGES` (already imported); `_edge_owners`
- Produces: `TephigramAxes.edge_axis(self, edge: str) -> Axis` — public API

- [ ] **Step 1: Write the failing tests**

Add to `tests/plotting/test_axes.py`, after the Task 3 test:

```python
def test_edge_axis_returns_each_edge_s_axis():
    """The uniform public handle on all four edges (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels=("bottom", "left"))
        ax.mixing_ratios(labels="top")
        ax.dry_adiabats(labels="right")
        fig.canvas.draw()
        assert ax.edge_axis("bottom") is ax.xaxis
        assert ax.edge_axis("left") is ax.yaxis
        assert ax.edge_axis("top") is ax._secondary_axes["top"].xaxis
        assert ax.edge_axis("right") is ax._secondary_axes["right"].yaxis
    finally:
        plt.close(fig)


def test_edge_axis_rejects_an_unknown_or_unclaimed_edge():
    """An unknown name is a TypeError; an unlabelled edge a ValueError."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        with pytest.raises(TypeError, match="unknown edge 'middle'"):
            ax.edge_axis("middle")
        with pytest.raises(ValueError, match="'top' edge carries no isopleth"):
            ax.edge_axis("top")
        # Probing must not have built a secondary axes nothing is using.
        assert ax._secondary_axes == {}
        assert ax.child_axes == []
    finally:
        plt.close(fig)


def test_edge_axis_styling_reaches_top_and_survives_a_reclaim():
    """Stock matplotlib styling now reaches top and right, and sticks."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        ax.edge_axis("top").set_tick_params(labelsize=12)
        ax.edge_axis("top").set_label_text("W")
        fig.canvas.draw()
        assert {
            t.label2.get_fontsize() for t in ax.edge_axis("top").get_major_ticks()
        } == {12.0}
        ax.mixing_ratios(labels=False)
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        assert ax.edge_axis("top").get_label_text() == "W"
        assert {
            t.label2.get_fontsize() for t in ax.edge_axis("top").get_major_ticks()
        } == {12.0}
    finally:
        plt.close(fig)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -k edge_axis -v`

Expected: all three FAIL with `AttributeError: 'TephigramAxes' object has no attribute
'edge_axis'`.

- [ ] **Step 3: Add the method**

Insert in `src/tephpy/plotting/axes.py` immediately **before**
`def _check_label_edges(self, name: str, options: ResolvedOptions) -> None:` (line 943), so
the public method sits with the other public methods and above the private edge machinery:

```python
def edge_axis(self, edge: str) -> Axis:
    """Return the matplotlib axis drawing one diagram edge's ticks.

    The uniform handle on all four edges (spec §3.2), keyed by the same
    names the ``labels`` option takes. Bottom and left are the axes' own
    ``xaxis``/``yaxis``; top and right belong to a secondary axes that
    has no other public handle. tephpy stamps its tick conventions on an
    edge axis once, when that axis is created, so everything stock
    matplotlib offers is the caller's from the claim onwards — e.g.
    ``ax.edge_axis("top").set_tick_params(labelsize=12)``, or
    ``set_label_text("")`` to keep the ticks and drop the axis title.
    The only thing tephpy changes afterwards is the tick colour, and
    only when the owning family's own colour or alpha changes.

    Parameters
    ----------
    edge : str
        The edge, one of ``EDGES``.

    Returns
    -------
    matplotlib.axis.Axis
        The axis drawing that edge's ticks.

    Raises
    ------
    TypeError
        If `edge` is not one of ``EDGES``.
    ValueError
        If no family labels that edge. Styling an unclaimed edge would
        be overwritten by the conventions its claim stamps, and probing
        one must not build a secondary axes nothing is using.
    """
    if edge not in EDGES:
        msg = f"unknown edge {edge!r}; expected one of {list(EDGES)!r}"
        raise TypeError(msg)
    if edge not in self._edge_owners:
        msg = (
            f"the {edge!r} edge carries no isopleth labels; claim it "
            f'first, e.g. ax.isobars(labels="{edge}") (spec §3.2)'
        )
        raise ValueError(msg)
    return self._edge_axis(edge)
```

- [ ] **Step 4: Run the new tests**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -k edge_axis -v`

Expected: all three PASS.

- [ ] **Step 5: Run the full suite**

Run: `pixi run --frozen pytest --mpl`

Expected: PASS, whole suite.

- [ ] **Step 6: Commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
git commit -m "feat: add TephigramAxes.edge_axis for the four diagram edges

Top and right are drawn by lazily created secondary axes reachable only
through a private attribute or an undifferentiated child_axes that has to be
sniffed, so stock matplotlib styling could not reach them. edge_axis returns
the Axis for any edge, keyed by the names the labels option already takes;
an unknown name raises TypeError and an unlabelled edge ValueError, so
probing never builds a secondary axes nothing uses (spec §3.2).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: Changelog and the full gate

**Files:**
- Create: `changelog/<PR>.bugfix.rst`, `changelog/<PR>.enhancement.rst`

**Interfaces:**
- Consumes: everything above
- Produces: nothing further

- [ ] **Step 1: Find the PR number**

Fragments are named for the pull request, not the issue. Push the implementation branch and
open its PR if it is not already open — this is the code PR, distinct from the docs-only
#55 that carried this plan:

```bash
git push -u origin edge-styling-impl
gh pr create --repo bjlittle/tephpy --title "Give the edge-label ticks and titles their own styling control" --body "Closes #52"
```

Note the number it prints; call it `<PR>` below.

- [ ] **Step 2: Write the bugfix fragment**

Create `changelog/<PR>.bugfix.rst`:

```rst
Styling a claimed diagram edge's ticks with
:meth:`~matplotlib.axes.Axes.tick_params` now lasts. tephpy re-applied its own
tick conventions on every isopleth family resolve, so an unrelated family —
``ax.isotherms(color="grey")`` after ``ax.isobars(labels="left")`` — silently
reverted the tick label size, tick length and padding a user had set, and
re-suppressed gridlines an explicit :meth:`~matplotlib.axes.Axes.grid` call had
enabled. The conventions are now stamped once, when the edge axis is created,
and an axis title cleared with ``ax.set_ylabel("")`` likewise stays cleared for
as long as the edge is labelled. (:issue:`52`, :user:`claude`)
```

- [ ] **Step 3: Write the enhancement fragment**

Create `changelog/<PR>.enhancement.rst`:

```rst
:meth:`~tephpy.plotting.axes.TephigramAxes.edge_axis` returns the matplotlib
:class:`~matplotlib.axis.Axis` that draws one diagram edge's isopleth ticks,
keyed by the same ``"bottom"``, ``"top"``, ``"left"`` and ``"right"`` names the
``labels`` option takes. The top and right edges are drawn by lazily created
secondary axes and had no public handle, so stock matplotlib styling could not
reach them; ``ax.edge_axis("top").set_tick_params(labelsize=12)`` now works on
all four edges alike. Releasing a top or right edge hides its secondary axes
instead of destroying it, so a handle held across the release stays live and
its ticks and title survive the reclaim. (:issue:`52`, :user:`claude`)
```

- [ ] **Step 4: Run the full lint gate**

Run: `pixi run --frozen lint`

Expected: PASS. `pre-commit install` first if the hooks are not installed in this
checkout — a fresh clone or worktree does not have them.

- [ ] **Step 5: Build the docs clean and check the cross-references**

Run: `pixi run --frozen docs`

Expected: no warnings naming the new fragments. **The build must be clean** — the `docs`
task depends on `docs-clean`, so this is already a from-scratch build; an incremental
build serves a stale changelog draft and will not surface a broken role. Confirm
`docs/_build/html/reference/generated/api/tephpy/plotting/axes/index.html` documents
`edge_axis`, and that the changelog page renders both fragments with live links for
`:issue:`52`` and `:user:`claude``.

- [ ] **Step 6: Commit and push**

```bash
git add changelog/
git commit -m "docs: add the edge styling changelog fragments

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push
```

---

## Verification checklist

Run once at the end, from the repository root:

- [ ] `pixi run --frozen pytest --mpl` — whole suite passes, no baseline regenerated
- [ ] `pixi run --frozen lint` — every pre-commit hook passes
- [ ] `pixi run --frozen docs` — clean build, `edge_axis` in the API reference, both
      changelog fragments rendering
- [ ] The issue's original reproduction now holds:

```python
import matplotlib.pyplot as plt
import tephpy

fig = plt.figure()
ax = fig.add_subplot(projection="tephigram")
ax.isobars(labels=("bottom", "left"))
ax.tick_params(axis="y", labelsize=14)
ax.set_ylabel("My pressure", fontsize=16, fontweight="bold")
fig.canvas.draw()
ax.isotherms(color="grey")  # the unrelated resolve that used to wipe
fig.canvas.draw()
assert {t.label1.get_fontsize() for t in ax.yaxis.get_major_ticks()} == {14.0}
assert ax.get_ylabel() == "My pressure"

ax.isotherms(labels="top")
ax.edge_axis("top").set_tick_params(labelsize=14)  # top reachable at last
```
