# tephpy Edge Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Point-in-time record.** This plan states what was intended *before* implementation and is not updated afterwards. The review loop routinely revised what it records, so its code blocks drift from what shipped. The code is authoritative, and the design specification in [`../specs/`](../specs/) is the living statement of intent — read this for how the work was approached, not for how tephpy behaves today.

**Goal:** Widen the existing `labels=` option so an isopleth family can place its labels on the diagram's edges — `ax.isobars(labels=("bottom", "left"))` builds the printed chart's pressure scale — with every member that reaches no listed edge still labelled inline, one family per edge, and today's all-inline default untouched.

**Architecture:** `labels` grows from `bool` to `bool | str | tuple[str, ...]`. `IsoplethFamily._resolve` normalises it into two resolved fields — `labels: bool` (label at all) and `label_edges: tuple[str, ...]` (the edges claimed) — so the draw path changes only by filtering its inline set through the new pure function `edge_crossings`. Edge ticks are native matplotlib ticks: `TephigramAxes` owns an edge→family map, points the claimed axis at an `_EdgeLocator`/`_EdgeFormatter` pair, and lets matplotlib call the locator every draw, so pan, zoom, resize and `set_extent` stay correct with no refresh machinery. Bottom and left claim the axes' own hidden `xaxis`/`yaxis`; top and right claim a lazily created secondary axis. One-family-per-edge is enforced by a validator the axes hands each family, so it fires inside `configure`'s existing rollback and a `tephpy.config` conflict surfaces at axes creation.

**Tech Stack:** Python 3.12/3.13/3.14, numpy, matplotlib 3.11 (`Locator`/`Formatter`, `secondary_xaxis`/`secondary_yaxis`, `mpl_toolkits.axes_grid1` divider), pytest + pytest-mpl, pixi tasks. No new dependencies, no new modules — four source files and five test files are modified; the changelog fragment and one image baseline are the only new files.

**Spec:** `docs/superpowers/specs/2026-07-22-tephpy-design.md` — §3.1 (hidden native ticks, reclaimed here), §3.2 (the edge-labelling bullet, the coverage table, the side-of-axes layout contract's right-edge paragraph), §3.5 (the option ladder), §6 (fail-loud `TypeError`), §7 (the pytest-mpl baseline list). Post-roadmap addition (not a §10 plan row).

## Global Constraints

Copied from the spec and prior plans; every task's requirements implicitly include these.

- **Python support (SPEC 0):** 3.12, 3.13, and 3.14. **Platforms (pixi):** `linux-64` only.
- **Imports:** every `.py` file carries `from __future__ import annotations` (already present in all files touched here).
- **Lint/type:** ruff `ALL` (repo config); mypy `strict` + `warn_unreachable` clean over `src/tephpy`. numpydoc-validation checks **every docstringed object, including private helpers**: documented parameters (PR01), a `Returns` section on anything returning a value (RT01), and a `Raises` section listing every exception raised directly (RS01-family). Unused parameters take a leading underscore and are documented as "Ignored; …" — the `_build_mixing_ratios(values, _truncation)` precedent in `plotting/isopleths.py`.
- **Import ordering:** ruff's isort puts CONSTANTS before Classes before functions within a `from` list, and sorts case-sensitively (`E` < `_` < lowercase). Don't hand-tune it — run `pixi run --frozen lint`, which rewrites the order in place.
- **`SLF001`:** ruff flags private-member access **even within the same module** (verified 2026-07-29). The one place this plan needs it (`_EdgeLocator` reaching into its family) carries an explicit `# noqa: SLF001` with a comment; do not add others.
- **Units:** conversion via `.m_as(...)` — never `np.asarray(Quantity)` (`UnitStrippedWarning` is an **error** under the repo's pytest `filterwarnings = ["error"]`). Not exercised by this plan; edge geometry is diagram-native throughout.
- **Tests:** pytest strict config with `filterwarnings = ["error"]` and `xfail_strict`. New tests mirror the source layout — `tests/plotting/` for `src/tephpy/plotting/`. In tests, never assign a lambda (ruff E731) — use a `def`. Close every figure you create outside a fixture.
- **Docs:** the build must stay warning-free (`pixi run --frozen docs`, which cleans first). `edge_crossings` and `EDGES` join `tephpy.plotting.isopleths.__all__` and so get autoapi pages; the locator, formatter and every axes helper stay underscore-private and unexported. No user-facing prose documents `labels=` today (checked: only `docs/src/reference/glossary.rst` mentions isopleth labelling, and only in passing), so no `docs/src` edits are required.
- **Changelog:** one `changelog/<PR>.enhancement.rst` fragment for the implementation PR, cross-referencing APIs with Sphinx roles and ending with ``(:user:`claude`)`` (see `changelog/README.md`); verify with a **clean** docs build. The fragment is added *after* the PR number exists (Task 6).
- **Branch:** work on a feature branch (`no-commit-to-branch` blocks `main`): `git switch -c edge-labels-impl`. This plan's spec commits already live on `edge-labels`; branch from there or from `main` once it lands. Ensure the pre-commit git hooks are installed **before the first commit** (`pixi run --frozen pre-commit install`) and run `pixi run --frozen lint` before every push. **`git add` new files before `pixi run --frozen lint`** (pre-commit only checks files git knows about).
- **Dedented listings:** the repo's blacken-docs hook formats this plan's fenced ```python listings at top level, so code destined for a **class body** is shown **dedented** — indent every line one level (4 spaces) when inserting it into the class. Each such listing says so. Listings that are *fragments* rather than whole statements — a bare keyword argument, a lone function parameter — carry a **plain fence with no language**, because black parses `labels=labels,` at top level as an assignment and silently rewrites it to `labels = (labels,)`. Those listings show their real indentation; insert them verbatim.
- **Environment facts (verified empirically against the committed lockfile, 2026-07-29, matplotlib 3.11.1):**
  - `ax.secondary_xaxis("top", functions=mtransforms.IdentityTransform())` and `ax.secondary_yaxis("right", ...)` both work, track the equal-aspect shrunk parent position, and survive the `axes_grid1` divider. **Pass an `IdentityTransform`, not a pair of identity functions** — the matplotlib stubs type `functions` as `tuple[Callable[[ArrayLike], ArrayLike], ...] | Transform | None`, so a `Callable[[float], float]` pair fails mypy strict while the transform type-checks cleanly.
  - A secondary axis lands in `parent.child_axes`, **not** in `figure.axes`. `Axes.clear()` (the `super().clear()` at the top of `TephigramAxes.clear`) already empties `child_axes`, so no explicit teardown and **no `_figure_is_clearing()` guard** is needed for them — unlike the side panels, `Figure.clear` never iterates them. `secondary.remove()` works for the release path and a redraw afterwards is clean.
  - `Locator.__call__` and `Locator.tick_values` are typed `-> Sequence[float]` in the stubs; returning `npt.NDArray[np.float64]` **fails** mypy strict (`[override]`). Return `list[float]`. `Formatter.__call__(self, x: float, pos: int | None = None) -> str` type-checks as written.
  - Under the `classic` style pytest-mpl uses, `axis.set_ticks_position("bottom")` / `("left")` is required to suppress the mirrored ticks on the opposite edge.
  - `BARB_GUTTER_PAD` is 0.1 in. At `LABEL_FONTSIZE` (8 pt), tick length 3 pt and tick pad 2 pt, a right-edge axis needs **0.479 in** from the diagram edge for its ticks, labels and title (widest label 0.210 in). Measured clearances at the gutter: pad 0.10 in → −0.378 in (overlap), 0.45 in → −0.028 in (overlap), **0.55 in → +0.072 in (clear)**, 0.65 in → +0.172 in. Hence `EDGE_LABEL_GUTTER_PAD = 0.55`.
  - Coverage at `DEFAULT_EXTENT`, used verbatim as test oracles (spec §3.2's table): `viewLim` is `x0=1591.3226137173003, y0=1671.3226137173003, x1=1901.955827211137, y1=1821.955827211137`. Isotherms select 19 members (−120…60 °C by 10); bottom ticks −40…60 (11), left ticks −110…−40 (8), so −40 is ticked twice and **−120 reaches no edge**. Isobars select 19 (150…1050 by 50); left ticks 150…1000 (18), bottom ticks 1050 alone (1), top ticks 150 and 200 — **200 hPa crosses the top edge twice**, right ticks 200/250/300 (3). Mixing ratios select 8 (0.05, 0.2, 1, 2, 4, 7, 14, 28) and **all 8 cross the top edge**.
  - The analytic oracle: an isotherm is `x − y = 2T`, so it meets `y = y0` at exactly `x = y0 + 2T` — confirmed to 1e-12 for T = 0 and T = 20 against the real built members.

---

### Task 1: Edge-labelling constants and the widened `labels` config field

**Files:**
- Modify: `src/tephpy/_constants.py` (append after `LABEL_BOX_ALPHA`, the last line — 281)
- Modify: `src/tephpy/_config.py:57-58` (the `LineOptions.labels` field)
- Test: `tests/test_constants.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `_constants.EDGE_AXIS_TITLES: Final[dict[str, str]]` (keyed by the five accessor names), `_constants.EDGE_TICK_LENGTH: Final[float] = 3.0`, `_constants.EDGE_TICK_PAD: Final[float] = 2.0`, `_constants.EDGE_LABEL_GUTTER_PAD: Final[float] = 0.55`, and `_config.LineOptions.labels: bool | str | tuple[str, ...] | None`. Tasks 3, 5 and 6 consume all of them.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_constants.py` (the module imports `_constants` as `constants`):

```python
def test_edge_axis_titles_cover_every_family():
    """One axis title per family accessor, in the accessor's own units."""
    assert set(constants.EDGE_AXIS_TITLES) == {
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
    }
    assert constants.EDGE_AXIS_TITLES["isobars"] == "Pressure (hPa)"
    assert all(title.strip() for title in constants.EDGE_AXIS_TITLES.values())


def test_edge_label_gutter_pad_clears_a_tick_label():
    """The substituted pad is wider than the panel pads it replaces."""
    assert constants.EDGE_LABEL_GUTTER_PAD > constants.BARB_GUTTER_PAD
    assert constants.EDGE_LABEL_GUTTER_PAD > constants.INDICES_PANEL_PAD
    assert constants.EDGE_TICK_LENGTH > 0.0
    assert constants.EDGE_TICK_PAD >= 0.0
```

Append to `tests/test_config.py`:

```python
def test_labels_accepts_placements():
    """`labels` widened from bool to bool-or-edge-names (spec §3.2)."""
    with tephpy.config.context(isobars={"labels": ("bottom", "left")}):
        assert tephpy.config.isobars.labels == ("bottom", "left")
    assert tephpy.config.isobars.labels is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_constants.py tests/test_config.py -q`
Expected: FAIL — `AttributeError: module 'tephpy._constants' has no attribute 'EDGE_AXIS_TITLES'`. (`test_labels_accepts_placements` passes already: the dataclass is untyped at runtime. It is the mypy-visible contract that changes, and it guards the field against being narrowed back.)

- [ ] **Step 3: Add the constants**

Append to `src/tephpy/_constants.py`:

```python
#: Axis titles for edge-labelled isopleth families, keyed by accessor name.
#: A claimed edge takes its family's title only when the axis has none, so a
#: user's ``set_xlabel`` wins whichever side of the accessor call it lands on,
#: and releasing the edge clears the title again (spec §3.2).
EDGE_AXIS_TITLES: Final[dict[str, str]] = {
    "isotherms": "Temperature (°C)",
    "isobars": "Pressure (hPa)",
    "dry_adiabats": "Potential temperature (°C)",
    "moist_adiabats": "Wet-bulb potential temperature (°C)",
    "mixing_ratios": "Mixing ratio (g kg⁻¹)",
}

#: Edge tick mark length in points.
EDGE_TICK_LENGTH: Final[float] = 3.0

#: Edge tick label padding from the tick mark, in points.
EDGE_TICK_PAD: Final[float] = 2.0

#: Side-panel padding substituted for the panel's own when the diagram's
#: right edge carries isopleth ticks, in inches. ``BARB_GUTTER_PAD`` (0.1 in)
#: is narrower than an 8 pt tick label, so right-edge labels would land on the
#: gutter. Measured 2026-07-29: a right axis needs 0.479 in for its ticks,
#: labels and title, so this leaves 0.07 in of clearance (spec §3.2).
EDGE_LABEL_GUTTER_PAD: Final[float] = 0.55
```

- [ ] **Step 4: Widen the config field**

In `src/tephpy/_config.py`, replace the `labels` field of `LineOptions` (lines 57-58):

```python
#: Whether member values are labelled, and where: ``True`` (every member
#: labelled inline — the default), ``False`` (none), or the diagram edge
#: names ``"bottom"``, ``"top"``, ``"left"`` and ``"right"``, singly as a
#: bare string or together as a tuple. Listed edges label the members that
#: reach them; every member left over is labelled inline (spec §3.2).
labels: bool | str | tuple[str, ...] | None = None
```

(Class-body code, shown dedented — indent one level when inserting.)

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_constants.py tests/test_config.py -q`
Expected: PASS. Then `pixi run --frozen lint` — clean.

- [ ] **Step 6: Commit**

```bash
git add src/tephpy/_constants.py src/tephpy/_config.py tests/test_constants.py tests/test_config.py
git commit -m "feat: add the edge-labelling constants and widen config labels"
```

---

### Task 2: `edge_crossings` — where a member meets a view edge

**Files:**
- Modify: `src/tephpy/plotting/isopleths.py` (new `EDGES` constant and `edge_crossings` function after the module constants block ending at `_INTERVAL_KEYS`, ~line 100; two new `__all__` entries)
- Test: `tests/plotting/test_isopleths.py`

**Interfaces:**
- Consumes: Task 1's constants (not needed here).
- Produces:
  - `isopleths.EDGES: Final[tuple[str, ...]] = ("bottom", "top", "left", "right")`
  - `isopleths.edge_crossings(xy: npt.NDArray[np.float64], edge: str, view: mtransforms.Bbox) -> npt.NDArray[np.float64]` — the along-edge coordinates (x for bottom/top, y for left/right) at which the polyline `xy` meets that edge of `view`, restricted to the edge's own span; empty when it does not. Raises `TypeError` for an unknown `edge`. Tasks 3, 4 and 5 consume both.

- [ ] **Step 1: Write the failing tests**

Append to `tests/plotting/test_isopleths.py` (the module already imports `math`, `mtransforms`, `np`, `pytest` and `isopleths`):

```python
VIEW = mtransforms.Bbox.from_extents(1591.0, 1671.0, 1902.0, 1822.0)


def test_edge_crossings_isotherm_bottom_is_analytic():
    """An isotherm x - y = 2T meets y = y0 at exactly x = y0 + 2T."""
    (member,) = isopleths.isotherm_members([20.0])
    crossings = isopleths.edge_crossings(member.xy, "bottom", VIEW)
    np.testing.assert_allclose(crossings, [VIEW.y0 + 40.0], rtol=1e-12)


def test_edge_crossings_isotherm_left_is_analytic():
    """The same isotherm meets x = x0 at exactly y = x0 - 2T."""
    (member,) = isopleths.isotherm_members([-30.0])
    crossings = isopleths.edge_crossings(member.xy, "left", VIEW)
    np.testing.assert_allclose(crossings, [VIEW.x0 + 60.0], rtol=1e-12)


def test_edge_crossings_outside_the_edge_span_are_dropped():
    """A crossing of the infinite line beyond the edge segment is not a hit."""
    tiny = mtransforms.Bbox.from_extents(1591.0, 1671.0, 1600.0, 1822.0)
    (member,) = isopleths.isotherm_members([20.0])
    assert isopleths.edge_crossings(member.xy, "bottom", tiny).size == 0


def test_edge_crossings_vertex_on_the_edge_counts_once():
    """A vertex sitting exactly on the edge yields one crossing, not two."""
    xy = np.array([[1700.0, 1600.0], [1700.0, 1671.0], [1700.0, 1750.0]])
    crossings = isopleths.edge_crossings(xy, "bottom", VIEW)
    np.testing.assert_allclose(crossings, [1700.0])


def test_edge_crossings_ignores_non_finite_segments():
    """Truncated members carry NaN vertices; those segments never hit."""
    xy = np.array([[1700.0, 1600.0], [np.nan, np.nan], [1700.0, 1750.0]])
    assert isopleths.edge_crossings(xy, "bottom", VIEW).size == 0


def test_edge_crossings_needs_two_vertices():
    """A degenerate polyline has no segments to intersect."""
    xy = np.array([[1700.0, 1671.0]])
    assert isopleths.edge_crossings(xy, "bottom", VIEW).size == 0


def test_edge_crossings_rejects_an_unknown_edge():
    """Fail loud on an unknown edge name (spec §6)."""
    (member,) = isopleths.isotherm_members([0.0])
    with pytest.raises(TypeError, match=r"unknown edge 'middle'.*bottom"):
        isopleths.edge_crossings(member.xy, "middle", VIEW)


def test_edges_are_the_four_diagram_edges():
    assert isopleths.EDGES == ("bottom", "top", "left", "right")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -q -k edge`
Expected: FAIL with `AttributeError: module 'tephpy.plotting.isopleths' has no attribute 'edge_crossings'`.

- [ ] **Step 3: Implement `EDGES` and `edge_crossings`**

In `src/tephpy/plotting/isopleths.py`, add to `__all__` (ruff will sort): `"EDGES"` and `"edge_crossings"`. Then, after the `_INTERVAL_KEYS` constant:

```python
#: The diagram edges an isopleth family may claim for its labels (spec §3.2).
EDGES: Final[tuple[str, ...]] = ("bottom", "top", "left", "right")


def edge_crossings(
    xy: npt.NDArray[np.float64], edge: str, view: mtransforms.Bbox
) -> npt.NDArray[np.float64]:
    """Return where a member polyline meets one edge of the view.

    Pure numpy over the cached member geometry: each segment that straddles
    the edge's level contributes one linearly interpolated crossing, kept
    only when it falls within the edge's own span. A vertex lying exactly on
    the edge is attributed to the segment it starts, so it counts once; a
    segment with a non-finite endpoint never counts. A member may cross the
    same edge more than once — a curved isobar leaving and re-entering the
    view — and every crossing is returned (spec §3.2).

    Parameters
    ----------
    xy : numpy.ndarray
        The member polyline, shape ``(n, 2)`` in tephigram data space.
    edge : str
        The edge to intersect, one of :data:`EDGES`.
    view : matplotlib.transforms.Bbox
        The current data-space view rectangle.

    Returns
    -------
    numpy.ndarray
        The along-edge coordinates of the crossings — x for ``"bottom"``
        and ``"top"``, y for ``"left"`` and ``"right"`` — in polyline
        order; empty when the member does not reach the edge.

    Raises
    ------
    TypeError
        If `edge` is not one of :data:`EDGES`.
    """
    if edge not in EDGES:
        msg = f"unknown edge {edge!r}; expected one of {list(EDGES)!r}"
        raise TypeError(msg)
    if xy.shape[0] < 2:
        return np.empty(0, dtype=np.float64)
    if edge in {"bottom", "top"}:
        across, along = xy[:, 1], xy[:, 0]
        level = view.y0 if edge == "bottom" else view.y1
        lo, hi = view.x0, view.x1
    else:
        across, along = xy[:, 0], xy[:, 1]
        level = view.x0 if edge == "left" else view.x1
        lo, hi = view.y0, view.y1
    delta = across - level
    start, end = delta[:-1], delta[1:]
    # A NaN endpoint makes both the equality and the sign product False, so
    # truncated members drop their non-finite segments here.
    hit = (start == 0.0) | (np.sign(start) * np.sign(end) < 0.0)
    if not hit.any():
        return np.empty(0, dtype=np.float64)
    start, end = start[hit], end[hit]
    first, second = along[:-1][hit], along[1:][hit]
    span = end - start
    fraction = np.where(span == 0.0, 0.0, -start / np.where(span == 0.0, 1.0, span))
    positions = first + fraction * (second - first)
    return np.asarray(positions[(positions >= lo) & (positions <= hi)])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -q -k edge`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add src/tephpy/plotting/isopleths.py tests/plotting/test_isopleths.py
git commit -m "feat: add edge_crossings, the member/view-edge intersection"
```

---

### Task 3: Resolving label placements and the inline remainder

**Files:**
- Modify: `src/tephpy/plotting/isopleths.py` — `_normalize_labels` (new free function after `edge_crossings`), `ResolvedOptions` (line 296), `IsoplethFamily.__init__` (line 507) and its class docstring, `configure` (line 546), `draw` (line 612), `_resolve` (line 663), `_draw_labels` (line 857), plus the new `_resolve_validated`, `_selected_members` and `_inline_members`
- Test: `tests/plotting/test_isopleths.py`

**Interfaces:**
- Consumes: Task 2's `EDGES` and `edge_crossings`.
- Produces:
  - `isopleths._normalize_labels(value: object, name: str) -> tuple[bool, tuple[str, ...]]` — splits a raw `labels` option into `(label_at_all, claimed_edges)`; raises `TypeError` on an unknown placement.
  - `ResolvedOptions.label_edges: tuple[str, ...]` — a new field after `labels`, empty for inline-only and always empty when `visible` is False.
  - `IsoplethFamily.__init__(spec, section, validate=None)` with `validate: Callable[[str, ResolvedOptions], None] | None` — called with `(family name, candidate options)` inside the resolution path, so raising rolls the family back.
  - `IsoplethFamily._selected_members() -> list[Member]` — the members the current view and zoom ladder select.
  - `IsoplethFamily._inline_members(view: mtransforms.Bbox, selected: list[Member]) -> list[Member]` — the selected members no claimed edge labels.
  - Tasks 4 and 5 consume `label_edges`, `validate`, `_selected_members` and `EDGES`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/plotting/test_isopleths.py`:

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, (True, ())),
        (True, (True, ())),
        (False, (False, ())),
        ("bottom", (True, ("bottom",))),
        (("bottom", "left"), (True, ("bottom", "left"))),
        (("left", "bottom"), (True, ("left", "bottom"))),
        (("bottom", "bottom"), (True, ("bottom",))),
        ((), (False, ())),
    ],
)
def test_normalize_labels(raw, expected):
    """A bare string and a one-tuple are identical; duplicates collapse."""
    assert isopleths._normalize_labels(raw, "isobars") == expected


@pytest.mark.parametrize("raw", ["middle", ("bottom", "middle"), (0,), 3.5])
def test_normalize_labels_rejects_unknown_placements(raw):
    """Fail loud, naming the placement and the valid set (spec §6)."""
    with pytest.raises(TypeError, match=r"'isobars' label placement"):
        isopleths._normalize_labels(raw, "isobars")


def test_resolved_label_edges_and_invisibility():
    """An invisible family labels nothing and holds no edge (spec §3.2)."""
    spec = isopleths._FAMILY_SPECS["isobars"]
    family = isopleths.IsoplethFamily(spec, config.isobars)
    assert family.options.labels is True
    assert family.options.label_edges == ()
    family.configure(labels=("bottom", "left"))
    assert family.options.label_edges == ("bottom", "left")
    family.configure(visible=False)
    assert family.options.label_edges == ()
    family.configure(visible=True)
    assert family.options.label_edges == ("bottom", "left")
    family.configure(labels=True)
    assert family.options.label_edges == ()


def test_validator_rejection_rolls_the_family_back():
    """A validator veto leaves the family exactly as it was."""

    def veto(name, options):
        if options.label_edges:
            msg = f"{name} may not claim an edge"
            raise TypeError(msg)

    spec = isopleths._FAMILY_SPECS["isobars"]
    family = isopleths.IsoplethFamily(spec, config.isobars, validate=veto)
    family.configure(color="red")
    with pytest.raises(TypeError, match="may not claim an edge"):
        family.configure(labels="left", color="blue")
    assert family.options.label_edges == ()
    assert family.options.color == "red"


def test_selected_and_inline_members_at_the_default_extent():
    """Spec §3.2's coverage table, exercised through the family."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        view = ax.viewLim

        isobars = ax.isobars(labels=("bottom", "left"))
        selected = isobars._selected_members()
        assert [member.value for member in selected][:3] == [150.0, 200.0, 250.0]
        assert len(selected) == 19
        assert isobars._inline_members(view, selected) == []

        # Release the edges before the isotherms take them: Task 5 makes a
        # second claimant an error, and this test must keep passing.
        ax.isobars(labels=True)
        isotherms = ax.isotherms(labels=("bottom", "left"))
        selected = isotherms._selected_members()
        assert len(selected) == 19
        remainder = isotherms._inline_members(view, selected)
        assert [member.value for member in remainder] == [-120.0]

        adiabats = ax.dry_adiabats()
        selected = adiabats._selected_members()
        assert adiabats._inline_members(view, selected) == selected
    finally:
        plt.close(fig)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -q -k "normalize or label_edges or validator or inline"`
Expected: FAIL — `AttributeError: module 'tephpy.plotting.isopleths' has no attribute '_normalize_labels'`.

- [ ] **Step 3: Add `_normalize_labels`**

In `src/tephpy/plotting/isopleths.py`, after `edge_crossings`:

```python
def _normalize_labels(value: object, name: str) -> tuple[bool, tuple[str, ...]]:
    """Split a raw ``labels`` option into a flag and the edges it claims.

    ``True``/``None`` mean every member is labelled inline, ``False`` means
    none is, and one or more edge names claim those edges — a bare string
    and a one-tuple are identical, and duplicates collapse in first-seen
    order (spec §3.2). The bare-string case is handled before the iterable
    case so ``"bottom"`` is never iterated character by character.

    Parameters
    ----------
    value : object
        The resolved ``labels`` option, from any precedence tier.
    name : str
        The family name, for the error message.

    Returns
    -------
    tuple of (bool, tuple of str)
        Whether the family labels anything, and the edges it claims.

    Raises
    ------
    TypeError
        If `value` is neither a bool nor edge name(s) from :data:`EDGES`.
    """
    if value is None or isinstance(value, bool):
        return (True if value is None else value), ()
    placements: tuple[object, ...]
    if isinstance(value, str):
        placements = (value,)
    elif isinstance(value, Iterable):
        placements = tuple(cast("Iterable[object]", value))
    else:
        placements = (value,)
    edges: list[str] = []
    for placement in placements:
        if not isinstance(placement, str) or placement not in EDGES:
            msg = (
                f"unknown {name!r} label placement {placement!r}; expected "
                f"True, False, or edge name(s) from {list(EDGES)!r}"
            )
            raise TypeError(msg)
        if placement not in edges:
            edges.append(placement)
    return bool(edges), tuple(edges)
```

`isinstance(value, Iterable)` needs `Iterable` at runtime: move it out of the `TYPE_CHECKING` block into a module-level `from collections.abc import Iterable` (leave `Callable` and `SupportsFloat` under `TYPE_CHECKING`).

- [ ] **Step 4: Widen `ResolvedOptions` and `_resolve`**

Add the field to `ResolvedOptions` immediately after `labels` (class body, shown dedented — indent one level):

```python
labels: bool
label_edges: tuple[str, ...]
visible: bool
```

Extend the `ResolvedOptions` docstring with a sentence: ``An empty `label_edges` means the family labels inline only.``

In `_resolve`, replace the `raw_labels`/`raw_visible` lines and the two constructor arguments:

```python
raw_labels = pick("labels")
labels, label_edges = _normalize_labels(raw_labels, spec.name)
raw_visible = pick("visible")
visible = True if raw_visible is None else bool(raw_visible)
```

Then in the `return ResolvedOptions(...)` call at the end of `_resolve`, replace the single argument

```
    labels=True if raw_labels is None else bool(raw_labels),
```

with these three (keeping `visible=` on the line after, unchanged):

```
    labels=labels,
    # An invisible family draws nothing, so it holds no edge (spec §3.2).
    label_edges=label_edges if visible else (),
```

and replace the `visible=` argument with `visible=visible,` — the local now holds the coerced value.

Add to `_resolve`'s `Raises` section:

```
TypeError
    If the resolved ``labels`` names an unknown placement.
```

- [ ] **Step 5: Add the validator hook**

In `IsoplethFamily`, widen the constructor (class body, shown dedented — indent one level):

```python
def __init__(
    self,
    spec: FamilySpec,
    section: object,
    validate: Callable[[str, ResolvedOptions], None] | None = None,
) -> None:
    """Initialise the family and snapshot its resolved options.

    Parameters
    ----------
    spec : FamilySpec
        The family's static wiring (builder plus convention defaults).
    section : object
        The family's ``tephpy.config`` section, read at creation and
        on :meth:`configure`.
    validate : callable, optional
        Called with ``(family name, candidate options)`` whenever the
        options resolve; raising rejects the change. The owning axes
        passes its one-family-per-edge check here so the rejection
        lands inside this class's rollback (spec §3.2).
    """
    super().__init__()
    self._spec = spec
    self._section = section
    self._validate = validate
    self._overrides: dict[str, object] = {}
```

(the remaining `__init__` body is unchanged except the last resolution line), and change

```python
self._options = self._resolve()
```

to

```python
self._options = self._resolve_validated()
```

Mirror the `validate` entry in the **class**-level docstring's `Parameters` section (numpydoc checks both).

Add the helper next to `_resolve` (class body, shown dedented — indent one level):

```python
def _resolve_validated(self) -> ResolvedOptions:
    """Resolve the options and put them past the owner's validator.

    Returns
    -------
    ResolvedOptions
        The accepted snapshot.

    Raises
    ------
    TypeError
        If the owner's validator rejects the candidate options.
    ValueError
        If an option value is invalid (see :meth:`_resolve`).
    """
    options = self._resolve()
    if self._validate is not None:
        self._validate(self._spec.name, options)
    return options
```

In `configure`, change the staged resolution inside the `try` from `self._options = self._resolve()` to `self._options = self._resolve_validated()`, and add to its `Raises` section:

```
TypeError
    If an option name is unknown for this family, if ``labels`` names
    an unknown placement, or if the owning axes rejects an edge claim
    already held by another family.
```

- [ ] **Step 6: Add `_selected_members` / `_inline_members` and use them in `draw`**

Add both methods just above `_draw_labels` (class body, shown dedented — indent one level):

```python
def _selected_members(self) -> list[Member]:
    """Return the members the current view and zoom ladder select.

    Building lazily on first use, this is the single definition of "what
    this family shows right now" — shared by :meth:`draw` and by the edge
    tick locator, which matplotlib calls outside the draw path.

    Returns
    -------
    list of Member
        The selected members in build order; empty until the family has
        an axes.
    """
    axes = self.axes
    if axes is None:
        return []
    if self._members is None:
        self._build()
    members = self._members if self._members is not None else []
    view = axes.viewLim
    mask = self._zoom_mask(view.width) & self._view_mask(view)
    return [m for m, keep in zip(members, mask, strict=True) if keep]


def _inline_members(
    self, view: mtransforms.Bbox, selected: list[Member]
) -> list[Member]:
    """Return the selected members that no claimed edge labels.

    The automatic remainder of spec §3.2: listed edges label the members
    that reach them, and every member left over is labelled inline. With
    no claimed edge every selected member is inline, which is the default.
    The crossings are recomputed here rather than shared with the locator
    because tick location and artist drawing have no guaranteed ordering.

    Parameters
    ----------
    view : matplotlib.transforms.Bbox
        The current data-space view rectangle.
    selected : list of Member
        The members drawn this pass.

    Returns
    -------
    list of Member
        The members to label inline.
    """
    edges = self._options.label_edges
    if not edges:
        return selected
    return [
        member
        for member in selected
        if not any(edge_crossings(member.xy, edge, view).size for edge in edges)
    ]
```

In `draw`, replace the build-and-select block

```python
if self._members is None:
    self._build()
members = self._members if self._members is not None else []
opts = self._options
view = axes.viewLim
mask = self._zoom_mask(view.width) & self._view_mask(view)
selected = [m for m, keep in zip(members, mask, strict=True) if keep]
```

with

```python
opts = self._options
selected = self._selected_members()
```

(`view` is unused in the rest of `draw` — `_draw_labels` takes its own.)

- [ ] **Step 7: Filter the inline set in `_draw_labels`**

In `_draw_labels`, after `view = axes.viewLim`, insert

```python
labelled = self._inline_members(view, selected)
```

then replace the two uses of `selected` below it — `while len(self._texts) < len(selected):` and `for member, text in zip(selected, self._texts, strict=False):` — with `labelled`. Extend the method's summary paragraph with: "Members a claimed edge already ticks are dropped first (spec §3.2)."

- [ ] **Step 8: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/ -q`
Expected: PASS, including the existing image baselines (the default is `labels=True` with no claimed edge, so `_inline_members` returns `selected` unchanged and nothing renders differently).

- [ ] **Step 9: Commit**

```bash
git add src/tephpy/plotting/isopleths.py tests/plotting/test_isopleths.py
git commit -m "feat: resolve label placements and filter the inline remainder"
```

---

### Task 4: The edge tick locator and formatter

**Files:**
- Modify: `src/tephpy/plotting/isopleths.py` (new `_EdgeLocator` and `_EdgeFormatter` after `IsoplethFamily`, at the end of the module; one new import line)
- Test: `tests/plotting/test_isopleths.py`

**Interfaces:**
- Consumes: Task 2's `edge_crossings`, Task 3's `IsoplethFamily._selected_members`.
- Produces:
  - `isopleths._EdgeLocator(family: IsoplethFamily, edge: str)` — a `matplotlib.ticker.Locator` whose `__call__() -> list[float]` returns the along-edge tick positions and refreshes the parallel `positions: list[float]` / `values: list[float]` caches.
  - `isopleths._EdgeFormatter(locator: _EdgeLocator)` — a `matplotlib.ticker.Formatter` returning `f"{value:g}"` for a cached position and `""` for anything else.
  - Task 5 constructs both.

- [ ] **Step 1: Write the failing tests**

Append to `tests/plotting/test_isopleths.py`:

```python
def test_edge_locator_matches_the_coverage_table():
    """Spec §3.2's measured coverage, through the locator (spec §7)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        locator = isopleths._EdgeLocator(ax.isobars(), "left")
        positions = locator()
        assert len(positions) == 18
        assert locator.values == [float(p) for p in range(150, 1050, 50)]
        assert locator.positions == positions

        locator = isopleths._EdgeLocator(ax.mixing_ratios(), "top")
        locator()
        assert locator.values == [0.05, 0.2, 1.0, 2.0, 4.0, 7.0, 14.0, 28.0]

        locator = isopleths._EdgeLocator(ax.isotherms(), "bottom")
        locator()
        assert locator.values == [float(t) for t in range(-40, 70, 10)]
    finally:
        plt.close(fig)


def test_edge_locator_ticks_every_crossing():
    """200 hPa leaves and re-enters the view across the top edge."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        locator = isopleths._EdgeLocator(ax.isobars(), "top")
        locator()
        assert locator.values == [150.0, 200.0, 200.0]
    finally:
        plt.close(fig)


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
        assert all(500.0 <= value <= 900.0 for value in locator.values)
        assert locator.tick_values(0.0, 1.0) == locator.positions
    finally:
        plt.close(fig)


def test_edge_formatter_reads_the_cached_values():
    """No inverse math: the formatter reads the value beside the position."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        locator = isopleths._EdgeLocator(ax.mixing_ratios(), "top")
        formatter = isopleths._EdgeFormatter(locator)
        positions = locator()
        assert formatter(positions[0]) == "0.05"
        assert formatter(positions[-1]) == "28"
        assert formatter(positions[0] + 1.0) == ""
    finally:
        plt.close(fig)


def test_edge_locator_without_axes_is_empty():
    """A detached family has no view to intersect."""
    spec = isopleths._FAMILY_SPECS["isobars"]
    locator = isopleths._EdgeLocator(
        isopleths.IsoplethFamily(spec, config.isobars), "left"
    )
    assert locator() == []
    assert locator.values == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -q -k "locator or formatter"`
Expected: FAIL with `AttributeError: module 'tephpy.plotting.isopleths' has no attribute '_EdgeLocator'`.

- [ ] **Step 3: Implement the pair**

Add `from matplotlib.ticker import Formatter, Locator` to the runtime imports of `src/tephpy/plotting/isopleths.py`, then append at the end of the module:

```python
class _EdgeLocator(Locator):
    """Locate one family's crossings of one diagram edge as ticks.

    Matplotlib calls the locator on every draw, so pan, zoom, resize and
    ``set_extent`` stay correct with no refresh machinery (spec §3.2). Each
    call caches the member value beside each position for
    :class:`_EdgeFormatter`, which is why the formatter needs no inverse
    math and works identically for all five families.

    Parameters
    ----------
    family : IsoplethFamily
        The family that claimed the edge.
    edge : str
        The claimed edge, one of :data:`EDGES`.
    """

    def __init__(self, family: IsoplethFamily, edge: str) -> None:
        """Initialise the locator with empty caches.

        Parameters
        ----------
        family : IsoplethFamily
            The family that claimed the edge.
        edge : str
            The claimed edge, one of :data:`EDGES`.
        """
        super().__init__()
        self.family = family
        self.edge = edge
        self.positions: list[float] = []
        self.values: list[float] = []

    def __call__(self) -> list[float]:
        """Return the tick positions, refreshing the caches.

        Returns
        -------
        list of float
            The along-edge crossing coordinates, in member order; empty
            while the family has no axes.
        """
        positions: list[float] = []
        values: list[float] = []
        axes = self.family.axes
        if axes is not None:
            view = axes.viewLim
            # The locator is the family's own machinery, one module away
            # from a method it has no reason to publish.
            for member in self.family._selected_members():  # noqa: SLF001
                for position in edge_crossings(member.xy, self.edge, view):
                    positions.append(float(position))
                    values.append(member.value)
        self.positions = positions
        self.values = values
        return positions

    def tick_values(self, vmin: float, vmax: float) -> list[float]:
        """Return the tick positions, ignoring the requested interval.

        Parameters
        ----------
        vmin : float
            Ignored; the crossings define their own interval.
        vmax : float
            Ignored; the crossings define their own interval.

        Returns
        -------
        list of float
            The same positions :meth:`__call__` returns.
        """
        del vmin, vmax
        return self()


class _EdgeFormatter(Formatter):
    """Label an edge tick with the member value that produced it.

    Parameters
    ----------
    locator : _EdgeLocator
        The locator whose caches supply the values; matplotlib runs it
        immediately before this formatter within a draw, so the two agree.
    """

    def __init__(self, locator: _EdgeLocator) -> None:
        """Bind the formatter to its locator's caches.

        Parameters
        ----------
        locator : _EdgeLocator
            The locator whose caches supply the values.
        """
        super().__init__()
        self.locator = locator

    def __call__(self, x: float, pos: int | None = None) -> str:
        """Format one tick.

        Parameters
        ----------
        x : float
            The tick position, in along-edge data coordinates.
        pos : int, optional
            Ignored; the registry signature matplotlib calls with.

        Returns
        -------
        str
            The member value formatted ``"{value:g}"``, as inline labels
            already are, or ``""`` for a position this locator did not
            produce.
        """
        del pos
        locator = self.locator
        for position, value in zip(locator.positions, locator.values, strict=True):
            if math.isclose(position, x, rel_tol=1e-9, abs_tol=1e-9):
                return f"{value:g}"
        return ""
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -q -k "locator or formatter"`
Expected: PASS (5 tests). Then `pixi run --frozen lint` — clean apart from any import reordering it fixes itself.

- [ ] **Step 5: Commit**

```bash
git add src/tephpy/plotting/isopleths.py tests/plotting/test_isopleths.py
git commit -m "feat: add the edge tick locator and formatter"
```

---

### Task 5: Edge ownership on the axes

**Files:**
- Modify: `src/tephpy/plotting/axes.py` — imports (25-65), class attributes (345-349), `clear` (351-388) and its docstring, `_relayout_side_panels` (866-893), `_configure_family` (1027-1047), plus the five new private methods
- Test: `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes: Task 1's constants, Task 2's `EDGES`, Task 3's `label_edges` and the `validate` hook, Task 4's `_EdgeLocator`/`_EdgeFormatter`.
- Produces (all private to `TephigramAxes`):
  - `_edge_owners: dict[str, str]` — claimed edge → owning family name; absent key means unclaimed.
  - `_secondary_axes: dict[str, SecondaryAxis]` — the lazily created `"top"`/`"right"` axes.
  - `_edge_titles: dict[str, str]` — the axis titles this axes set, so release clears only its own.
  - `_check_label_edges(name: str, options: ResolvedOptions) -> None` — the validator handed to every family.
  - `_edge_axis(edge: str) -> Axis`, `_claim_edge(edge: str, family: IsoplethFamily) -> None`, `_release_edge(edge: str) -> None`, `_sync_edge_labels() -> None`.
  - Task 6 consumes none of these directly; it only widens the accessors' types.

- [ ] **Step 1: Write the failing tests**

Append to `tests/plotting/test_axes.py` (add `EDGE_AXIS_TITLES`, `EDGE_LABEL_GUTTER_PAD` to its `_constants` import list, and `from tephpy.plotting.isopleths import EDGES` alongside the existing `IsoplethFamily` import):

```python
def _ticks(axis):
    """The rendered tick label strings of an axis."""
    return [text.get_text() for text in axis.get_ticklabels()]


def test_no_edge_is_claimed_by_default():
    """Today's default stands: hidden native axes, no secondary axes."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        fig.canvas.draw()
        assert ax._edge_owners == {}
        assert ax.child_axes == []
        assert not ax.xaxis.get_visible()
        assert not ax.yaxis.get_visible()
    finally:
        plt.close(fig)


def test_isobars_claim_bottom_and_left():
    """The printed chart's pressure scale, from one call (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels=("bottom", "left"))
        fig.canvas.draw()
        assert ax._edge_owners == {"bottom": "isobars", "left": "isobars"}
        assert ax.xaxis.get_visible()
        assert _ticks(ax.xaxis) == ["1050"]
        assert _ticks(ax.yaxis)[:2] == ["150", "200"]
        assert len(_ticks(ax.yaxis)) == 18
        assert ax.get_xlabel() == EDGE_AXIS_TITLES["isobars"]
        assert ax.get_ylabel() == EDGE_AXIS_TITLES["isobars"]
    finally:
        plt.close(fig)


def test_a_user_axis_title_wins_either_way():
    """The convention title only fills an empty axis label (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.set_xlabel("Mine")
        ax.isobars(labels="bottom")
        assert ax.get_xlabel() == "Mine"
        ax.set_xlabel("Still mine")
        ax.isobars(labels=True)
        assert ax.get_xlabel() == "Still mine"
    finally:
        plt.close(fig)


def test_top_and_right_use_lazily_created_secondary_axes():
    """Claiming creates one child axes; releasing removes it."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        assert len(ax.child_axes) == 1
        assert _ticks(ax._secondary_axes["top"].xaxis) == [
            "0.05",
            "0.2",
            "1",
            "2",
            "4",
            "7",
            "14",
            "28",
        ]
        ax.mixing_ratios(labels=True)
        fig.canvas.draw()
        assert ax.child_axes == []
        assert ax._secondary_axes == {}
    finally:
        plt.close(fig)


def test_one_family_per_edge():
    """Two claimants raise, naming both and the edge (spec §3.2)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        with pytest.raises(TypeError, match=r"'left'.*'isobars'.*'isotherms'"):
            ax.isotherms(labels=("bottom", "left"))
        assert ax._edge_owners == {"left": "isobars"}
        assert ax.isotherms().options.label_edges == ()
    finally:
        plt.close(fig)


def test_a_config_conflict_surfaces_at_axes_creation():
    """Not at first draw: the axes funnels the creation path too."""
    with (
        config.context(isotherms={"labels": "bottom"}, isobars={"labels": "bottom"}),
        pytest.raises(TypeError, match="'bottom'"),
    ):
        fig = plt.figure()
        try:
            fig.add_subplot(projection="tephigram")
        finally:
            plt.close(fig)


def test_unknown_placement_is_rejected():
    """Fail loud, naming the placement and the valid set (spec §6)."""
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        with pytest.raises(TypeError, match=r"label placement 'middle'"):
            ax.isobars(labels="middle")
        assert ax._edge_owners == {}
    finally:
        plt.close(fig)


def test_an_invisible_family_releases_its_edge():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        assert ax._edge_owners == {"left": "isobars"}
        ax.isobars(visible=False)
        assert ax._edge_owners == {}
        assert not ax.yaxis.get_visible()
        ax.isotherms(labels="left")
        assert ax._edge_owners == {"left": "isotherms"}
    finally:
        plt.close(fig)


def test_clear_drops_every_edge_claim():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels=("bottom", "left"))
        ax.mixing_ratios(labels="top")
        fig.canvas.draw()
        ax.clear()
        fig.canvas.draw()
        assert ax._edge_owners == {}
        assert ax._secondary_axes == {}
        assert ax.child_axes == []
        assert not ax.xaxis.get_visible()
        assert ax.get_xlabel() == ""
    finally:
        plt.close(fig)


def test_right_edge_labels_widen_the_gutter_pad():
    """The relayout helper substitutes the wider pad (spec §3.2)."""
    pressure = np.array([1000.0, 900.0, 800.0]) * units.hPa
    snd = Sounding(
        pressure=pressure,
        temperature=np.array([20.0, 14.0, 8.0]) * units.degC,
        wind_speed=np.array([10.0, 20.0, 30.0]) * units.knots,
        wind_direction=np.array([180.0, 200.0, 220.0]) * units.deg,
    )
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.plot_barbs(snd)
        fig.canvas.draw()
        narrow = ax._barb_gutter.get_window_extent().x0 - ax.get_window_extent().x1
        ax.isobars(labels="right")
        fig.canvas.draw()
        wide = ax._barb_gutter.get_window_extent().x0 - ax.get_window_extent().x1
        assert wide == pytest.approx(EDGE_LABEL_GUTTER_PAD * fig.dpi, abs=1.0)
        assert wide > narrow
    finally:
        plt.close(fig)


def test_edge_ticks_follow_set_extent():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels="left")
        fig.canvas.draw()
        wide = _ticks(ax.yaxis)
        ax.set_extent(((900.0, -10.0), (500.0, 20.0)))
        fig.canvas.draw()
        zoomed = _ticks(ax.yaxis)
        assert zoomed != wide
        assert all(500.0 <= float(text) <= 900.0 for text in zoomed)
    finally:
        plt.close(fig)


def test_every_edge_can_be_claimed_at_once():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        ax.isobars(labels=("bottom", "left"))
        ax.mixing_ratios(labels="top")
        ax.isotherms(labels="right")
        fig.canvas.draw()
        assert set(ax._edge_owners) == set(EDGES)
        assert len(ax.child_axes) == 2
    finally:
        plt.close(fig)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -q -k "edge or claim or placement or gutter_pad"`
Expected: FAIL with `AttributeError: 'TephigramAxes' object has no attribute '_edge_owners'`.

- [ ] **Step 3: Extend the imports and class attributes**

In `src/tephpy/plotting/axes.py`, add to the runtime imports

```python
from matplotlib.ticker import AutoLocator, NullLocator, ScalarFormatter
```

extend the `tephpy._constants` import list with `EDGE_AXIS_TITLES`, `EDGE_LABEL_GUTTER_PAD`, `EDGE_TICK_LENGTH`, `EDGE_TICK_PAD` and `LABEL_FONTSIZE` (which `axes.py` does not import yet), extend the `tephpy.plotting.isopleths` import with `EDGES`, `_EdgeFormatter`, `_EdgeLocator`, and add to the `TYPE_CHECKING` block

```python
from matplotlib.axes._secondary_axes import SecondaryAxis
from matplotlib.axis import Axis

from tephpy.plotting.isopleths import ResolvedOptions
```

Add the three class attributes after `_side_divider` (class body, shown dedented — indent one level):

```python
_edge_owners: dict[str, str]
_secondary_axes: dict[str, SecondaryAxis]
_edge_titles: dict[str, str]
```

- [ ] **Step 4: Reset and re-sync the edge state in `clear`**

In `clear`, immediately before `self._families = {}`, insert

```python
self._edge_owners = {}
self._secondary_axes = {}
self._edge_titles = {}
```

(`super().clear()` already empties `child_axes`, so the secondary axes need no explicit removal and no `_figure_is_clearing()` guard — unlike the side panels, `Figure.clear` never iterates them.)

Pass the validator when building each family:

```python
family = IsoplethFamily(spec, getattr(config, name), self._check_label_edges)
```

and add the re-sync after the loop, before `set_extent`:

```python
self._sync_edge_labels()
```

Extend the `clear` docstring's first paragraph — after "the five background isopleth families" — with ", any edges they claim for their labels,", and add a `Raises` section:

```
Raises
------
TypeError
    If ``tephpy.config`` gives one diagram edge to two families.
```

- [ ] **Step 5: Add the five edge methods**

Insert after `_relayout_side_panels` (class body, shown dedented — indent one level):

```python
def _check_label_edges(self, name: str, options: ResolvedOptions) -> None:
    """Reject an edge claim another family already holds.

    The axes owns all five families, so it is the only place that can see
    a collision; handing this to each family as its validator puts the
    rejection inside ``IsoplethFamily.configure``'s rollback, and running
    it during family creation surfaces a ``tephpy.config`` conflict at
    axes creation rather than at first draw (spec §3.2).

    Parameters
    ----------
    name : str
        The family the candidate options belong to.
    options : ResolvedOptions
        The candidate options, not yet in force.

    Raises
    ------
    TypeError
        If another family already claims one of the candidate's edges.
    """
    claimed = set(options.label_edges)
    if not claimed:
        return
    for other_name, other in self._families.items():
        if other_name == name:
            continue
        clash = claimed & set(other.options.label_edges)
        if clash:
            msg = (
                f"the {sorted(clash)[0]!r} edge is already labelled by "
                f"{other_name!r}: one family per edge, so release it "
                f"before {name!r} can claim it (spec §3.2)"
            )
            raise TypeError(msg)


def _edge_axis(self, edge: str) -> Axis:
    """Return the axis that draws one diagram edge's ticks.

    Bottom and left reclaim the axes' own hidden ``xaxis``/``yaxis``
    (spec §3.1); top and right take a secondary axis, created on first
    demand and cached. The identity transform keeps the secondary axis in
    the parent's data coordinates, which is what the crossings are in.

    Parameters
    ----------
    edge : str
        The edge, one of ``EDGES``.

    Returns
    -------
    matplotlib.axis.Axis
        The axis to point a locator and formatter at.
    """
    if edge == "bottom":
        return self.xaxis
    if edge == "left":
        return self.yaxis
    secondary = self._secondary_axes.get(edge)
    if secondary is None:
        identity = mtransforms.IdentityTransform()
        secondary = (
            self.secondary_xaxis(edge, functions=identity)
            if edge == "top"
            else self.secondary_yaxis(edge, functions=identity)
        )
        self._secondary_axes[edge] = secondary
    return secondary.xaxis if edge == "top" else secondary.yaxis


def _claim_edge(self, edge: str, name: str, family: IsoplethFamily) -> None:
    """Point one edge's ticks at a family. Idempotent.

    Re-applied on every sync so a family's restyle reaches its ticks.

    Parameters
    ----------
    edge : str
        The edge to claim, one of ``EDGES``.
    name : str
        The claiming family's accessor name, which keys the axis titles.
    family : IsoplethFamily
        The claiming family.
    """
    axis = self._edge_axis(edge)
    locator = _EdgeLocator(family, edge)
    axis.set_major_locator(locator)
    axis.set_major_formatter(_EdgeFormatter(locator))
    # Crossings are exact positions; a minor tick between them means
    # nothing. NullLocator is also matplotlib's linear-axis default, so
    # release restores it.
    axis.set_minor_locator(NullLocator())
    axis.set_visible(True)
    color = family.options.color
    axis.set_tick_params(
        color=color,
        labelcolor=color,
        labelsize=LABEL_FONTSIZE,
        length=EDGE_TICK_LENGTH,
        pad=EDGE_TICK_PAD,
    )
    if edge == "bottom":
        # The classic style mirrors ticks onto the opposite edge, which
        # would collide with that edge's own family.
        self.xaxis.set_ticks_position("bottom")
    elif edge == "left":
        self.yaxis.set_ticks_position("left")
    if not axis.get_label_text():
        title = EDGE_AXIS_TITLES[name]
        axis.set_label_text(title)
        self._edge_titles[edge] = title


def _release_edge(self, edge: str) -> None:
    """Return one edge to its unclaimed state.

    Parameters
    ----------
    edge : str
        The edge to release, one of ``EDGES``.
    """
    title = self._edge_titles.pop(edge, None)
    if edge in {"top", "right"}:
        # The whole secondary axis goes, and its ticks and title with it.
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
    axis.set_tick_params(reset=True)
    axis.set_visible(False)


def _sync_edge_labels(self) -> None:
    """Match the claimed edges to what the five families now ask for.

    Called after every family (re)configure and at the end of
    :meth:`clear`. Ownership conflicts were already rejected by
    :meth:`_check_label_edges`, so this only applies the outcome. A change
    on the right edge also relayouts the side panels, whose pad widens to
    clear the tick labels (spec §3.2).
    """
    claims: dict[str, str] = {}
    for name, family in self._families.items():
        for edge in family.options.label_edges:
            claims[edge] = name
    had_right = "right" in self._edge_owners
    for edge in EDGES:
        owner = claims.get(edge)
        if self._edge_owners.get(edge) not in (None, owner):
            self._release_edge(edge)
        if owner is None:
            self._edge_owners.pop(edge, None)
        else:
            self._edge_owners[edge] = owner
            self._claim_edge(edge, owner, self._families[owner])
    if had_right != ("right" in self._edge_owners):
        self._relayout_side_panels()
```

- [ ] **Step 6: Widen the gutter pad and re-sync on configure**

In `_relayout_side_panels`, replace the panel loop with

```python
right_labelled = "right" in self._edge_owners
for panel, pad, width in panels:
    if panel is None:
        continue
    # The first panel abuts the diagram, so it is the one the right
    # edge's tick labels would land on (spec §3.2).
    gap = EDGE_LABEL_GUTTER_PAD if right_labelled and not slots else pad
    horizontal.append(axes_size.Fixed(gap))
    horizontal.append(axes_size.from_any(width, fraction_ref=horizontal[0]))
    slots.append((panel, len(horizontal) - 1))
```

and extend its docstring with a sentence: "The panel nearest the diagram takes ``EDGE_LABEL_GUTTER_PAD`` in place of its own pad while the right edge carries isopleth ticks, which are wider than the 0.1 in conventions (spec §3.2)."

In `_configure_family`, re-sync after a successful reconfigure:

```python
if provided:
    family.configure(**provided)
    self._sync_edge_labels()
return family
```

and add a `Raises` section to its docstring:

```
Raises
------
TypeError
    If an option name or ``labels`` placement is unknown, or if another
    family already claims a requested edge.
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/ -q`
Expected: PASS, existing image baselines included.

- [ ] **Step 8: Commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
git commit -m "feat: give the tephigram axes edges to isopleth families"
```

---

### Task 6: Accessor signatures, the image baseline, and the changelog

**Files:**
- Modify: `src/tephpy/plotting/axes.py` — the five accessors `isotherms`, `isobars`, `dry_adiabats`, `moist_adiabats`, `mixing_ratios` (1052 onward), plus the `TephigramAxes` class docstring (330-341)
- Modify: `tests/plotting/test_images.py`
- Create: `tests/baseline/test_printed_chart_edges.png`
- Create: `changelog/<PR>.enhancement.rst`

**Interfaces:**
- Consumes: everything from Tasks 1-5.
- Produces: the five accessors typed `labels: bool | str | tuple[str, ...] | None = None`. No new public names.

- [ ] **Step 1: Write the failing baseline test**

Append to `tests/plotting/test_images.py`:

```python
@pytest.mark.mpl_image_compare(savefig_kwargs={"bbox_inches": "tight"})
def test_printed_chart_edges():
    """The printed-chart edge-labelling configuration (spec §3.2/§7)."""
    fig, ax = _tephigram_figure()
    ax.isobars(labels=("bottom", "left"))
    ax.mixing_ratios(labels="top")
    return fig
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pixi run --frozen pytest tests/plotting/test_images.py::test_printed_chart_edges --mpl -q`
Expected: FAIL — "Image file not found for comparison test … (This is expected for new tests.)"

- [ ] **Step 3: Widen the accessor signatures and docstrings**

In each of the five accessors in `src/tephpy/plotting/axes.py`, change the parameter

```
    labels: bool | None = None,
```

to

```
    labels: bool | str | tuple[str, ...] | None = None,
```

and replace the numpydoc entry

```
labels : bool, optional
    Whether member values are labelled.
```

with

```
labels : bool or str or tuple of str, optional
    Where member values are labelled: ``True`` (every member inline —
    the default), ``False`` (none), or the diagram edge names
    ``"bottom"``, ``"top"``, ``"left"`` and ``"right"``, singly or as a
    tuple. Listed edges label the members that reach them; every member
    left over is labelled inline. One family per edge.
```

Add a `Raises` section to each accessor, after `Returns`:

```
Raises
------
TypeError
    If ``labels`` names an unknown placement, or an edge another family
    already claims.
```

In the `TephigramAxes` class docstring, replace the sentence "Native x/y ticks carry no meteorological meaning and are hidden." with:

```
Native x/y ticks carry no meteorological meaning and are hidden until
a family claims an edge for its labels — ``labels=("bottom", "left")``
turns them into that family's scale (spec §3.2).
```

- [ ] **Step 4: Generate and inspect the baseline**

Run: `pixi run --frozen pytest tests/plotting/test_images.py::test_printed_chart_edges --mpl-generate-path=tests/baseline -q`

Then **open `tests/baseline/test_printed_chart_edges.png` and look at it.** It must show: pressure ticks down the left edge and a single `1050` below the bottom-left corner, mixing-ratio ticks across the top, axis titles `Pressure (hPa)` on both claimed sides and `Mixing ratio (g kg⁻¹)` above, **no inline isobar or mixing-ratio labels at all** (every member of both families reaches a claimed edge at the default extent), and inline labels still on the isotherms, dry adiabats and moist adiabats. Expect roughly 70 KB, in line with the other baselines.

Confirm nothing else moved: `git status --short tests/baseline` must list only the new file.

- [ ] **Step 5: Run the whole suite**

Run: `pixi run --frozen tests`
Expected: PASS, all baselines included.

Run: `pixi run --frozen lint` and `pixi run --frozen docs`
Expected: clean, warning-free.

- [ ] **Step 6: Commit and open the PR**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_images.py tests/baseline/test_printed_chart_edges.png
git commit -m "feat: widen the accessor labels option to edge placements"
git push -u origin edge-labels-impl
gh pr create --title "Label isopleth families on the diagram edges" --body "$(cat <<'EOF'
Widens the existing `labels=` option so an isopleth family can place its
labels on the diagram's edges as well as inline — the declutter control of
spec §3.2, adding no new public names.

`ax.isobars(labels=("bottom", "left"))` builds the printed chart's pressure
scale. Listed edges label the members that reach them and every member left
over is labelled inline, so nothing goes missing when a family only partly
reaches an edge. Edge labels are native matplotlib ticks — bottom and left
reclaim the axes' own hidden xaxis/yaxis, top and right take a lazily
created secondary axis — so pan, zoom and `set_extent` stay correct with no
refresh machinery. One family may hold an edge at a time; a second claimant
raises `TypeError`, including a `tephpy.config` conflict at axes creation.

The out-of-the-box diagram is unchanged and every existing image baseline
still matches; one new baseline covers the printed-chart configuration.

Implements `docs/superpowers/plans/2026-07-29-tephpy-edge-labels.md`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 7: Add the changelog fragment**

With the PR number in hand, create `changelog/<PR>.enhancement.rst`:

```rst
The ``labels`` option of every isopleth family accessor — for example
:meth:`~tephpy.plotting.axes.TephigramAxes.isobars` — now places labels on
the diagram's edges as well as inline. Alongside ``True`` and ``False`` it
accepts the edge names ``"bottom"``, ``"top"``, ``"left"`` and ``"right"``,
singly or as a tuple, so ``ax.isobars(labels=("bottom", "left"))`` builds the
printed chart's pressure scale. Listed edges label the members that reach
them and every member left over is labelled inline, so nothing goes missing
when a family only partly reaches an edge. Edge labels are native matplotlib
ticks and track pan, zoom and
:meth:`~tephpy.plotting.axes.TephigramAxes.set_extent`. One family may hold
an edge at a time; a second claimant raises :exc:`TypeError`. The
out-of-the-box diagram is unchanged. (:user:`claude`)
```

- [ ] **Step 8: Verify the fragment with a clean docs build**

Run: `pixi run --frozen docs` (it cleans first), then check the rendered changelog draft for unresolved cross-references.

- [ ] **Step 9: Commit**

```bash
git add changelog/
git commit -m "docs: add the edge-labelling changelog fragment"
git push
```
