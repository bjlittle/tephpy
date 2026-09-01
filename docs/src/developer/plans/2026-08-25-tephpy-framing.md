# View Framing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `set_extent`'s `((p, T), (p, T))` corner pairs with keyword ranges that map all four corners of the region they name, add `TephigramAxes.fit(...)` for data-driven framing, and reshape `config.diagram` to match — Plan 8 of the roadmap, answering {issue}`184`.

**Architecture:** One private helper, `_limits_from_ranges`, turns a pressure range and a temperature range into x/y limits by mapping all four corners of the region through the existing transforms. `set_extent` is that helper plus validation; `fit` is that helper plus a nan-aware reduction over its arguments plus a margin. The transforms are untouched — this plan changes which numbers reach them, never what they compute.

**Tech Stack:** Python 3.12+, numpy, matplotlib, pint (via MetPy's registry), pytest + pytest-mpl, pixi for every task.

**Spec:** `docs/src/developer/specs/2026-08-25-framing-design.md` (citation prefix `framing spec §…`). Read it alongside this plan. Where the two disagree the specification is right and this plan is stale.

## Global Constraints

- **Copyright header.** Every source file carries the BSD header (ruff `CPY001`).
- **Changelog.** One `changelog/<PR>.<type>.rst` fragment, ending ``(:user:`<github-username>`)``. This plan adds one, type `feature`.
- **Units policy (spec §5).** Public API takes and returns pint quantities; bare arrays need a `units=` mapping. `set_extent` and `fit` are the exception already established for view geometry: `set_extent` takes plain floats in hPa and °C, as it does today. `fit` takes objects that already carry units and reads their magnitudes internally.
- **Errors (spec §6).** Geometry errors from `set_extent` are `ValueError`, as today. `fit`'s argument errors are `TephpyValidationError` from `tephpy.exceptions`; a `fit` argument carrying no finite data raises `MissingDataError`, which subclasses it.
- **Specification citations** are plain text with a document prefix — `framing spec §3.1`, `spec §3.2`, `docs spec §3.9`. **A bare `§N` means a section of the document you are writing in**, so in `.py` and `.rst` files always give the prefix. A citation sits whole on one line. Verified by `.github/scripts/check_citations.py`.
- **A citation must never appear inside a section heading** (docs spec §3.7) — the fail-on-warning build reports it.
- **GitHub references** use ``:issue:`184``` in reStructuredText and docstrings, `` {issue}`184` `` in the Markdown specifications. Never a bare `#184`, never a hardcoded URL.
- **Titles** use Chicago Manual of Style headline style (spec §8.6).
- **numpydoc** validation runs in pre-commit: every public function needs Parameters, Returns/Raises sections as applicable.
- **Page shape where figures are published** (plots spec §3.2): every python block on such a page is a `.. plot::`; the first carries `:context: reset`; later blocks carry `:context:` or `:context: close-figs`; a block whose picture adds nothing carries `:nofigs:` and **no** `:filename-prefix:`; every figure-producing block carries a `:filename-prefix:`.

**Working branch:** `framing`, already created, already carrying the specification commit. Do not branch again.

**Commands:** `pixi run --frozen tests` (full suite), `pixi run --frozen --environment docs docs` (build + three gates), `pixi run --frozen lint` (pre-commit). Focused tests: `pixi run --frozen tests -- tests/plotting/test_axes.py -k extent -v`.

---

### Task 1: The Extent Becomes Two Ranges

Implements framing spec §3.1 and §3.4. This task is deliberately large and **atomic**: `_constants.DEFAULT_EXTENT` feeds `CONFIG_DEFAULTS`, which the configuration machinery reads, which the axes constructor applies. Reshaping any one of them alone leaves the tree broken, so they move together.

**Files:**
- Modify: `src/tephpy/_constants.py` (`DEFAULT_EXTENT`, ~line 39)
- Modify: `src/tephpy/_config.py` (`Extent` alias ~line 39, `DiagramOptions` ~line 115)
- Modify: `src/tephpy/_configfile.py` (`_as_extent` ~line 447, `_domain_extent` ~line 863, template text ~line 1305)
- Modify: `src/tephpy/plotting/axes.py` (`set_extent` ~line 492, the `clear()` call site ~line 456)
- Modify: `src/tephpy/examples/plot_tephigram.py:42`
- Modify: `src/tephpy/examples/plot_sounding_comparison.py:39,53`
- Test: `tests/plotting/test_axes.py`, `tests/test_constants.py`, `tests/test_configfile*.py`, `tests/examples/test_examples.py`

**Interfaces:**
- Produces, for Task 2:
  - `_limits_from_ranges(pressure: tuple[float, float], temperature: tuple[float, float]) -> tuple[float, float, float, float]` — module-level private in `axes.py`, returning `(xlo, xhi, ylo, yhi)`.
  - `TephigramAxes.set_extent(*, pressure: tuple[float, float], temperature: tuple[float, float]) -> None`
  - `Extent = Mapping[str, tuple[float, float]]` in `_config.py`, keys exactly `"pressure"` and `"temperature"`.
  - `DEFAULT_EXTENT: Final[Extent]` — a `MappingProxyType`, so it cannot be mutated by a caller.

- [ ] **Step 1: Write the failing tests**

Add to `tests/plotting/test_axes.py`:

```python
def test_set_extent_takes_keyword_ranges(tephigram_axes):
    """The view is named by a pressure range and a temperature range."""
    tephigram_axes.set_extent(pressure=(900.0, 200.0), temperature=(-65.0, 5.0))
    assert tephigram_axes.get_xlim() == pytest.approx((1545.51, 1831.40), abs=0.01)
    assert tephigram_axes.get_ylim() == pytest.approx((1675.51, 1821.40), abs=0.01)


def test_order_within_a_range_carries_no_meaning(tephigram_axes, tephigram_axes_b):
    """(a, b) and (b, a) name the same window (framing spec §3.1)."""
    tephigram_axes.set_extent(pressure=(900.0, 200.0), temperature=(-65.0, 5.0))
    tephigram_axes_b.set_extent(pressure=(200.0, 900.0), temperature=(5.0, -65.0))
    assert tephigram_axes.get_xlim() == tephigram_axes_b.get_xlim()
    assert tephigram_axes.get_ylim() == tephigram_axes_b.get_ylim()


def test_the_view_contains_the_whole_region_it_names(tephigram_axes):
    """Every corner of the named region falls inside the view.

    The defect this replaces mapped two corners and took the extremes,
    which is the bounding box of two *points* rather than of the region
    they delimit. Measured 2026-08-25, the old code placed
    (1000 hPa, -10 degC) and (900 hPa, 30 degC) outside the view that
    ``((1000, 30), (900, -10))`` asked for -- half the named region
    (framing spec §1).
    """
    tephigram_axes.set_extent(pressure=(1000.0, 900.0), temperature=(30.0, -10.0))
    xlo, xhi = tephigram_axes.get_xlim()
    ylo, yhi = tephigram_axes.get_ylim()
    for p in (1000.0, 900.0):
        for t in (30.0, -10.0):
            theta = transforms.theta_from_pressure_temperature(
                np.array([p]), np.array([t])
            )
            x, y = transforms.xy_from_temperature_theta(np.array([t]), theta)
            assert xlo <= float(x[0]) <= xhi, f"({p}, {t}) outside x"
            assert ylo <= float(y[0]) <= yhi, f"({p}, {t}) outside y"


def test_the_old_corner_call_is_now_unwritable(tephigram_axes):
    """The transposition of framing spec §1 cannot be expressed."""
    with pytest.raises(TypeError):
        tephigram_axes.set_extent(((900.0, -65.0), (200.0, 5.0)))


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"pressure": (0.0, 200.0), "temperature": (-65.0, 5.0)}, "pressure"),
        ({"pressure": (-5.0, 200.0), "temperature": (-65.0, 5.0)}, "pressure"),
        ({"pressure": (float("nan"), 200.0), "temperature": (-65.0, 5.0)}, "pressure"),
        ({"pressure": (900.0, 900.0), "temperature": (-65.0, 5.0)}, "pressure"),
        ({"pressure": (900.0, 200.0), "temperature": (float("inf"), 5.0)}, "temperature"),
        ({"pressure": (900.0, 200.0), "temperature": (5.0, 5.0)}, "temperature"),
    ],
)
def test_an_unusable_range_is_refused_by_name(tephigram_axes, kwargs, expected):
    """The message names the offending keyword, not a nested tuple."""
    with pytest.raises(ValueError, match=expected):
        tephigram_axes.set_extent(**kwargs)


def test_set_extent_disables_autoscaling(tephigram_axes):
    """A caller who fixed a window meant it (framing spec §3.5)."""
    tephigram_axes.set_extent(pressure=(900.0, 200.0), temperature=(-65.0, 5.0))
    assert tephigram_axes.get_autoscale_on() is False
```

These tests use `np`, `math`, `transforms` and `pytest`; check the module's import block and
add whatever is missing. `tephigram_axes` is the existing fixture in that module (line ~115). If there is no `tephigram_axes_b`, add one beside it that builds a second axes on its own figure — read the existing fixture and mirror it exactly rather than inventing a different shape.

- [ ] **Step 2: Run them and watch them fail**

```bash
pixi run --frozen tests -- tests/plotting/test_axes.py -k "extent or region or range" -v
```

Expected: failures. `test_set_extent_takes_keyword_ranges` fails with `TypeError: set_extent() got an unexpected keyword argument 'pressure'`. `test_the_old_corner_call_is_now_unwritable` **passes for the wrong reason** — the old signature accepts it — so treat its failure-to-fail as expected here and confirm it fails after Step 3 only if you break it. It is the one test in this group that starts green and must stay green for a different reason once the signature changes.

- [ ] **Step 3: Reshape the constant**

In `src/tephpy/_constants.py`, replace the `DEFAULT_EXTENT` block:

```python
#: Default diagram extent as pressure and temperature ranges in hPa and
#: degrees Celsius (see ``TephigramAxes.set_extent``). Chosen to frame a
#: mid-latitude ascent from the surface to 200 hPa, centred and near 2:1
#: (spec §3.2). A mapping rather than nested pairs because the view is
#: named by ranges and not by points: naming points in a rotated space is
#: what framing spec §1 records going wrong.
DEFAULT_EXTENT: Final[Mapping[str, tuple[float, float]]] = MappingProxyType(
    {"pressure": (900.0, 200.0), "temperature": (-65.0, 5.0)}
)
```

`MappingProxyType` is already imported in this module (it is used by `CONFIG_DEFAULTS`); add `Mapping` to the `collections.abc` import if it is not there.

- [ ] **Step 4: Reshape the type alias and add nothing else yet**

In `src/tephpy/_config.py`, replace the `Extent` alias:

```python
#: A diagram extent: pressure and temperature ranges in hPa / degrees
#: Celsius, keyed ``"pressure"`` and ``"temperature"`` (framing spec §3.4).
Extent = Mapping[str, tuple[float, float]]
```

Add `from collections.abc import Mapping` if absent. `DiagramOptions.extent` keeps its name and its `Extent | None` annotation — only the alias changed. **Do not add `margin` here; that is Task 2.**

- [ ] **Step 5: Rewrite `set_extent` and extract the shared helper**

In `src/tephpy/plotting/axes.py`, add this module-level private function above the class (place it beside the other module-level helpers; do not nest it):

```python
def _limits_from_ranges(
    pressure: tuple[float, float], temperature: tuple[float, float]
) -> tuple[float, float, float, float]:
    """Map a named (pressure, temperature) region to x/y limits.

    All four corners of the region are mapped, not the two a caller
    happens to write: the view is an axis-aligned rectangle in a rotated
    space, so the bounding box of two *points* need not contain the
    region they delimit (framing spec §1, §3.1).

    Parameters
    ----------
    pressure : tuple of float
        Pressure bounds in hPa, in either order.
    temperature : tuple of float
        Temperature bounds in degrees Celsius, in either order.

    Returns
    -------
    tuple of float
        ``(xlo, xhi, ylo, yhi)`` in data space.
    """
    p_lo, p_hi = sorted(pressure)
    t_lo, t_hi = sorted(temperature)
    pressures = np.array([p_lo, p_lo, p_hi, p_hi], dtype=np.float64)
    temperatures = np.array([t_lo, t_hi, t_lo, t_hi], dtype=np.float64)
    thetas = transforms.theta_from_pressure_temperature(pressures, temperatures)
    x, y = transforms.xy_from_temperature_theta(temperatures, thetas)
    return float(np.min(x)), float(np.max(x)), float(np.min(y)), float(np.max(y))
```

Then replace `set_extent` entirely:

```python
    def set_extent(
        self,
        *,
        pressure: tuple[float, float],
        temperature: tuple[float, float],
    ) -> None:
        """Fix the view to a pressure range and a temperature range.

        For directly comparable figures (spec §3.2). Both ranges are
        keyword-only and both are required: two positional sequences that
        cannot be told apart is the defect this replaces, and fixing one
        axis while leaving the other is a different operation
        (framing spec §3.1). Order within a range carries no meaning and is
        normalised. Autoscaling is disabled, so later overlays never drift
        a window the caller fixed.

        The view is an axis-aligned rectangle and pressure is not an axis,
        so it always reaches further than the ranges name. For the default
        extent the view's other two corners are 84.9 hPa / -137.9 degC and
        1058.4 hPa / +77.9 degC. Nothing draws there because it is
        unphysical, but the region is reachable and the ranges do not say
        so (framing spec §1).

        Parameters
        ----------
        pressure : tuple of float
            Pressure bounds in hPa, in either order, both finite and above
            zero.
        temperature : tuple of float
            Temperature bounds in degrees Celsius, in either order, both
            finite.

        Raises
        ------
        ValueError
            If either range is non-finite, degenerate, or -- for pressure
            -- not above zero. The message names the keyword at fault.
        """
        for name, bounds in (("pressure", pressure), ("temperature", temperature)):
            lo, hi = sorted(bounds)
            if not (math.isfinite(lo) and math.isfinite(hi)):
                msg = f"set_extent {name} bounds must be finite: {bounds!r}"
                raise ValueError(msg)
            if lo == hi:
                msg = f"set_extent {name} range must not be degenerate: {bounds!r}"
                raise ValueError(msg)
            if name == "pressure" and lo <= 0.0:
                msg = f"set_extent pressure bounds must be above 0 hPa: {bounds!r}"
                raise ValueError(msg)
        xlo, xhi, ylo, yhi = _limits_from_ranges(pressure, temperature)
        self.set_xlim(xlo, xhi)
        self.set_ylim(ylo, yhi)
        self.set_autoscale_on(False)
```

- [ ] **Step 6: Fix the construction path**

In `clear()`, the line currently reads:

```python
        self.set_extent(DEFAULT_EXTENT if extent is None else extent)
```

Replace with:

```python
        self.set_extent(**(DEFAULT_EXTENT if extent is None else extent))
```

- [ ] **Step 7: Run the axes tests**

```bash
pixi run --frozen tests -- tests/plotting/test_axes.py -v
```

Expected: the six new tests pass. Other tests in the module that call `set_extent` with the old shape now fail with `TypeError` — that is correct and Step 10 fixes them.

- [ ] **Step 8: Reshape the configuration converter and validator**

In `src/tephpy/_configfile.py`, replace `_as_extent`:

```python
def _as_extent(value: object) -> dict[str, tuple[float, float]]:
    """Check a value is a mapping of pressure and temperature ranges.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    dict of str to tuple of float
        The extent as named ranges (framing spec §3.4).

    Raises
    ------
    _MismatchError
        If the value is not a mapping carrying exactly ``pressure`` and
        ``temperature``, each a pair of numbers.
    """
    if not isinstance(value, dict) or set(value) != {"pressure", "temperature"}:
        raise _MismatchError
    return {name: _as_range(value[name]) for name in ("pressure", "temperature")}
```

`_as_range` replaces `_as_corner`. Read `_as_corner` first and mirror its shape exactly — same guard style, same `_MismatchError`, same float coercion — renaming it and its docstring to speak of a range rather than a corner. It is the same function with a different name and a different sentence; do not invent a new implementation.

Then replace `_domain_extent`:

```python
def _domain_extent(value: object) -> None:
    """Check both view ranges are physical.

    Parameters
    ----------
    value : object
        The converted ``extent``, as named ``pressure`` and
        ``temperature`` ranges.

    Raises
    ------
    _DomainError
        If a bound is not finite, or a pressure bound is not above zero.
        Lifted from ``axes.TephigramAxes.set_extent``, whose message names
        the pressure but whose test is finiteness after the transform -- so
        a non-finite temperature is refused there too (domain spec §3.3,
        framing spec §3.4).
    """
    ranges = cast("dict[str, tuple[float, float]]", value)
    finite = "finite extent bounds"
    positive = "extent pressures above 0 hPa"
    for bound in ranges["temperature"]:
        if not math.isfinite(bound):
            raise _DomainError(finite, _describe(bound))
    for bound in ranges["pressure"]:
        if not (bound > 0.0 and math.isfinite(bound)):
            raise _DomainError(positive, _describe(bound))
```

- [ ] **Step 9: Reshape the template text**

At `_configfile.py` ~line 1305, replace the `diagram.extent` description:

```python
                "extent": (
                    "Default view as ``{pressure: [hPa, hPa], temperature: "
                    "[degC, degC]}``; order within a range does not matter."
                ),
```

- [ ] **Step 10: Migrate every remaining caller and test**

```bash
grep -rn "set_extent\|DEFAULT_EXTENT" src tests --include="*.py"
```

Work the list. Each `ax.set_extent(((p0, t0), (p1, t1)))` becomes
`ax.set_extent(pressure=(p0, p1), temperature=(t0, t1))` — note the **regrouping**: pressures together, temperatures together. This is not a mechanical text substitution and a careless `sed` will produce a call that is syntactically valid and geometrically wrong.

Two examples specifically:
- `src/tephpy/examples/plot_tephigram.py:42` → `ax.set_extent(pressure=(900.0, 200.0), temperature=(-65.0, 5.0))`
- `src/tephpy/examples/plot_sounding_comparison.py` → `EXTENT` becomes
  `EXTENT = {"pressure": (950.0, 300.0), "temperature": (-50.0, 5.0)}` and line 53 becomes
  `ax.set_extent(**EXTENT)`. **Leave it as `set_extent` for now** — Task 3 converts this example to `fit`, and doing it here would mix two reviews.

`tests/test_constants.py:29` unpacks `(p0, t0), (p1, t1) = constants.DEFAULT_EXTENT`; rewrite it to read the mapping. Read what the test asserts before rewriting it — it checks the default frames a mid-latitude ascent, and that intent must survive.

- [ ] **Step 11: Run the full suite**

```bash
pixi run --frozen tests
```

Expected: all pass. Image baselines must be unchanged — the default extent maps identically under two-corner and four-corner mapping, which is why no baseline moves (framing spec §3.1). **If a pytest-mpl baseline fails, stop and report it**: it means a view moved that the specification says does not, and blessing it would approve a regression.

- [ ] **Step 12: Build the docs and run lint**

```bash
pixi run --frozen --environment docs docs
pixi run --frozen lint
```

Expected: `build succeeded.`, three `ok` lines, all hooks pass. The generated configuration reference re-renders from the new template text.

- [ ] **Step 13: Commit**

```bash
git add -A src tests
git commit -m "Name a view by ranges, and map the region it names

set_extent documented its argument as bottom-left and top-right corners,
then mapped those two points and took the extremes on each axis -- the
bounding box of two points in a rotated space, which need not contain the
region they delimit. Measured: set_extent(((1000, 30), (900, -10)))
produced a view excluding (1000, -10) and (900, 30), half the region the
caller named. The corner naming was also false for three of four ordinary
inputs, and a (T, p) transposition was accepted whenever both
temperatures were positive.

Ranges fix all three. Order within a range cannot carry a bug because it
carries no meaning; the keywords make transposition unwritable; and
mapping all four corners of the named region is what makes the view
contain it. The default extent is unchanged under the new mapping, so no
image baseline moves.

config.diagram.extent follows, which YAML expresses better than nested
bare pairs -- the shape issue #128 records biting.

Implements framing spec §3.1 and §3.4.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `fit` by Data

Implements framing spec §3.2, §3.3 and §3.5.

**Files:**
- Modify: `src/tephpy/plotting/axes.py` (new `_framing_coordinates`, new `TephigramAxes.fit`)
- Modify: `src/tephpy/_constants.py` (`DEFAULT_FIT_MARGIN`, and the `CONFIG_DEFAULTS` diagram entry)
- Modify: `src/tephpy/_config.py` (`DiagramOptions.margin`)
- Modify: `src/tephpy/_configfile.py` (a `margin` converter entry, a domain rule, template text)
- Test: `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes from Task 1: `_limits_from_ranges(pressure, temperature) -> (xlo, xhi, ylo, yhi)`.
- Produces: `TephigramAxes.fit(*objects: Sounding | Profile, margin: float | None = None) -> None`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/plotting/test_axes.py`:

```python
def test_fit_frames_one_sounding(tephigram_axes, sample_sounding):
    """Every finite datum falls inside the fitted view."""
    tephigram_axes.fit(sample_sounding, margin=0.0)
    xlo, xhi = tephigram_axes.get_xlim()
    ylo, yhi = tephigram_axes.get_ylim()
    p = sample_sounding.pressure.to("hPa").magnitude
    t = sample_sounding.temperature.to("degC").magnitude
    theta = transforms.theta_from_pressure_temperature(p, t)
    x, y = transforms.xy_from_temperature_theta(t, theta)
    assert xlo <= float(np.nanmin(x)) and float(np.nanmax(x)) <= xhi
    assert ylo <= float(np.nanmin(y)) and float(np.nanmax(y)) <= yhi


def test_fit_without_the_parcel_clips_the_path_it_is_read_against(
    tephigram_axes, tephigram_axes_b, sample_sounding
):
    """The defect ``fit`` exists to prevent (framing spec §3.2).

    A parcel is warmer than its environment through the CAPE region, so
    fitting the sounding alone can clip the very path the parcel analysis
    is drawn to show. Passing the parcel is what dissolves it.
    """
    parcel = calc.parcel_path(sample_sounding)
    tephigram_axes.fit(sample_sounding, margin=0.0)
    tephigram_axes_b.fit(sample_sounding, parcel, margin=0.0)
    without = tephigram_axes.get_xlim()
    with_parcel = tephigram_axes_b.get_xlim()
    assert with_parcel[1] > without[1] or with_parcel[0] < without[0]


def test_fit_takes_several_soundings(tephigram_axes, sample_sounding, sample_sounding_b):
    """A station's day, framed alike."""
    tephigram_axes.fit(sample_sounding, sample_sounding_b, margin=0.0)
    xlo, xhi = tephigram_axes.get_xlim()
    for snd in (sample_sounding, sample_sounding_b):
        p = snd.pressure.to("hPa").magnitude
        t = snd.temperature.to("degC").magnitude
        theta = transforms.theta_from_pressure_temperature(p, t)
        x, _ = transforms.xy_from_temperature_theta(t, theta)
        assert xlo <= float(np.nanmin(x)) and float(np.nanmax(x)) <= xhi


def test_a_nan_dewpoint_bounds_nothing_and_poisons_nothing(
    tephigram_axes, sample_sounding
):
    """NaN gaps are data everywhere except pressure (spec §3.4)."""
    dewpoint = sample_sounding.dewpoint.magnitude.copy()
    dewpoint[1] = float("nan")
    gapped = dataclasses.replace(
        sample_sounding,
        dewpoint=dewpoint * sample_sounding.dewpoint.units,
    )
    tephigram_axes.fit(gapped, margin=0.0)
    assert all(math.isfinite(v) for v in (*tephigram_axes.get_xlim(), *tephigram_axes.get_ylim()))


def test_fit_needs_something_to_frame(tephigram_axes):
    with pytest.raises(TephpyValidationError, match="at least one"):
        tephigram_axes.fit()


def test_fit_refuses_what_it_cannot_frame(tephigram_axes):
    with pytest.raises(TephpyValidationError, match="Sounding or Profile"):
        tephigram_axes.fit(object())


def test_margin_resolves_keyword_over_config_over_constant(
    tephigram_axes, tephigram_axes_b, sample_sounding
):
    """The resolution order every tunable here uses (framing spec §3.3)."""
    tephigram_axes.fit(sample_sounding, margin=0.0)
    tight = tephigram_axes.get_xlim()
    with config.context(diagram={"margin": 0.5}):
        tephigram_axes_b.fit(sample_sounding)
    loose = tephigram_axes_b.get_xlim()
    assert loose[1] - loose[0] > tight[1] - tight[0]


def test_fit_disables_autoscaling(tephigram_axes, sample_sounding):
    tephigram_axes.fit(sample_sounding)
    assert tephigram_axes.get_autoscale_on() is False
```

`sample_sounding` and `sample_sounding_b`: read the module for existing sounding fixtures
first. If it has none, build them from the shipped samples —
`tephpy.samples.sounding("norman-17z")` and `tephpy.samples.sounding("norman-12z")` — rather
than inventing arrays. The 17Z ascent is the one with CAPE, so use it wherever a parcel is
needed. These tests also use `dataclasses`, `calc`, `config` and `TephpyValidationError`;
add the imports the module lacks. `config.context(diagram={"margin": 0.5})` is the existing override helper (spec §3.5); the
keyword shape matches `tests/test_config.py:53`, verified 2026-08-25.

- [ ] **Step 2: Run them and watch them fail**

```bash
pixi run --frozen tests -- tests/plotting/test_axes.py -k fit -v
```

Expected: `AttributeError: 'TephigramAxes' object has no attribute 'fit'`.

- [ ] **Step 3: Add the margin constant**

In `src/tephpy/_constants.py`, beside `DEFAULT_EXTENT`:

```python
#: Default ``fit`` margin, as a fraction of the fitted span added to each
#: side in the drawn plane. Fractional so that one value frames a
#: boundary-layer window and a full-troposphere one alike (framing spec
#: §3.3).
DEFAULT_FIT_MARGIN: Final[float] = 0.05
```

And extend the `CONFIG_DEFAULTS` diagram entry:

```python
        "diagram": MappingProxyType(
            {"extent": DEFAULT_EXTENT, "margin": DEFAULT_FIT_MARGIN}
        ),
```

- [ ] **Step 4: Add the config field**

In `src/tephpy/_config.py`, `DiagramOptions` becomes:

```python
@dataclasses.dataclass
class DiagramOptions:
    """Diagram-wide options."""

    #: Default view extent applied to new tephigram axes.
    extent: Extent | None = None
    #: Default ``fit`` margin, as a fraction of the fitted span
    #: (framing spec §3.3).
    margin: float | None = None
```

- [ ] **Step 5: Wire margin through the configuration file**

`margin` is a plain float, so it needs no bespoke converter — find how another float-valued option is declared in `_configfile.py`'s converter table and add `margin` the same way. Its domain rule is that it is finite and not negative:

```python
def _domain_margin(value: object) -> None:
    """Check the fit margin is a usable fraction.

    Parameters
    ----------
    value : object
        The converted ``margin``.

    Raises
    ------
    _DomainError
        If the margin is negative or not finite. Zero is legal and fits
        exactly, which is what a caller composing panels wants
        (framing spec §3.3).
    """
    margin = cast("float", value)
    if not (math.isfinite(margin) and margin >= 0.0):
        raise _DomainError("a finite margin of 0 or more", _describe(margin))
```

Register it in the domain table beside `"extent"`, and add the template text:

```python
                "margin": (
                    "Default ``fit`` margin, as a fraction of the fitted "
                    "span added to each side; 0 fits exactly."
                ),
```

- [ ] **Step 6: Implement the dispatch helper**

In `src/tephpy/plotting/axes.py`, beside `_limits_from_ranges`:

```python
def _framing_coordinates(
    obj: object,
) -> tuple[npt.NDArray[np.float64], list[npt.NDArray[np.float64]]]:
    """Pressure and the temperature-like values that bound a view.

    The only place ``fit`` knows what a ``Sounding`` or a ``Profile`` is,
    so a third plottable is taught here rather than inside ``fit``
    (framing spec §3.2). Wind is absent by design: ``plot_barbs`` draws
    into the gutter, so it is not a coordinate of the plane.

    Parameters
    ----------
    obj : object
        A ``Sounding`` or a ``calc.Profile``.

    Returns
    -------
    tuple
        Pressures in hPa, and a list of temperature-like arrays in
        degrees Celsius.

    Raises
    ------
    TephpyValidationError
        If the object is neither.
    """
    # ``Sounding`` and ``Profile`` are TYPE_CHECKING-only imports in this
    # module, so they are not bound at runtime; import them here rather than
    # widening the module's import graph for one isinstance check. Neither
    # imports ``plotting``, so this cannot cycle -- verified 2026-08-25.
    from tephpy.calc import Profile  # noqa: PLC0415
    from tephpy.sounding import Sounding  # noqa: PLC0415

    if isinstance(obj, Sounding):
        temperatures = [obj.temperature.to("degC").magnitude]
        if obj.dewpoint is not None:
            temperatures.append(obj.dewpoint.to("degC").magnitude)
        return obj.pressure.to("hPa").magnitude, temperatures
    if isinstance(obj, Profile):
        return (
            obj.pressure.to("hPa").magnitude,
            [obj.temperature.to("degC").magnitude],
        )
    msg = f"fit() takes a Sounding or Profile, not {type(obj).__name__}"
    raise TephpyValidationError(msg)
```

`axes.py` imports `MissingDataError` already (line 70); add `TephpyValidationError` beside it. The lazy-import precedent in this file is `_figure_is_clearing`, which imports `inspect` the same way.

- [ ] **Step 7: Implement `fit`**

As a method on `TephigramAxes`, directly after `set_extent`:

```python
    def fit(
        self,
        *objects: Any,
        margin: float | None = None,
    ) -> None:
        """Frame the view around the data given.

        Answers "frame this neatly", where :meth:`set_extent` answers
        "make these figures directly comparable". Takes soundings and
        parcel paths interchangeably, and frames everything it is given:
        a parcel is warmer than its environment through the CAPE region,
        so fitting a sounding alone can clip the path the parcel analysis
        is drawn to show (framing spec §3.2). Autoscaling is disabled, as
        for :meth:`set_extent`.

        Parameters
        ----------
        *objects : Sounding or Profile
            What to frame. At least one is required.
        margin : float, optional
            Fraction of the fitted span added to each side in the drawn
            plane. Resolves keyword > ``config.diagram.margin`` >
            ``DEFAULT_FIT_MARGIN``. Zero fits exactly.

        Raises
        ------
        TephpyValidationError
            If no objects are given, or one is neither a ``Sounding`` nor
            a ``Profile``.
        MissingDataError
            If the objects carry no finite data to frame.
        """
        if not objects:
            msg = "fit() needs at least one Sounding or Profile to frame"
            raise TephpyValidationError(msg)
        pressures: list[npt.NDArray[np.float64]] = []
        temperatures: list[npt.NDArray[np.float64]] = []
        for obj in objects:
            pressure, temps = _framing_coordinates(obj)
            pressures.append(np.asarray(pressure, dtype=np.float64))
            temperatures.extend(np.asarray(t, dtype=np.float64) for t in temps)
        all_p = np.concatenate(pressures)
        all_t = np.concatenate(temperatures)
        if not (np.isfinite(all_p).any() and np.isfinite(all_t).any()):
            msg = "fit() found no finite data to frame"
            raise MissingDataError(msg)
        xlo, xhi, ylo, yhi = _limits_from_ranges(
            (float(np.nanmin(all_p)), float(np.nanmax(all_p))),
            (float(np.nanmin(all_t)), float(np.nanmax(all_t))),
        )
        if margin is None:
            configured = config.diagram.margin
            margin = DEFAULT_FIT_MARGIN if configured is None else configured
        pad_x = (xhi - xlo) * margin
        pad_y = (yhi - ylo) * margin
        self.set_xlim(xlo - pad_x, xhi + pad_x)
        self.set_ylim(ylo - pad_y, yhi + pad_y)
        self.set_autoscale_on(False)
```

Add `DEFAULT_FIT_MARGIN` to the `_constants` import block. `MissingDataError` is already imported at line 70.

- [ ] **Step 8: Run the fit tests**

```bash
pixi run --frozen tests -- tests/plotting/test_axes.py -k fit -v
```

Expected: all pass. If `test_fit_without_the_parcel_clips_the_path_it_is_read_against` fails, **do not weaken it** — it asserts the reason `fit` is variadic. Report instead: either the sample sounding has no CAPE (choose one that does, from `tephpy.samples`), or the reduction is wrong.

- [ ] **Step 9: Run the full suite, build, lint**

```bash
pixi run --frozen tests
pixi run --frozen --environment docs docs
pixi run --frozen lint
```

- [ ] **Step 10: Commit**

```bash
git add -A src tests
git commit -m "Add ax.fit for data-driven framing

set_extent answers 'make these figures directly comparable'. Nothing
answered 'frame this neatly', which is what a reader reaches for first,
so plot_sounding_comparison.py hand-picked a literal extent to do it.

fit takes soundings and parcel paths interchangeably and frames
everything it is given. That is what dissolves the clipping problem: a
parcel is warmer than its environment through the CAPE region, so fitting
the sounding alone can cut off the path the parcel analysis is drawn to
show. The test asserting that is the point of the design, not a detail.

Margin is a fraction of the fitted span in the drawn plane -- scale-free,
and isotropic where the eye reads it -- resolving keyword over
config.diagram.margin over the constant.

Implements framing spec §3.2, §3.3 and §3.5.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: The `pressure` Clamp

Implements framing spec §3.2's clamp. **This task exists because execution falsified the specification.** An earlier draft claimed `fit` "answers *frame this neatly*"; rendering it showed otherwise. Measured over the two shipped samples, an unclamped fit spans `pressure=(966.4, 10.2)` — into the mid-stratosphere — and the view becomes a narrow diagonal band of isopleths in a mostly empty rectangle. Clamping to `(1000, 200)` hPa moves the fitted temperature only from `(-79.4, 27.5)` to `(-72.3, 27.5)` and turns an unusable figure into a conventional one. The pressure span is the whole problem.

**Files:**
- Modify: `src/tephpy/plotting/axes.py` (`TephigramAxes.fit`)
- Test: `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes: `_limits_from_ranges`, `_framing_coordinates` from Tasks 1 and 2.
- Produces: `TephigramAxes.fit(*objects, pressure: tuple[float, float] | None = None, margin: float | None = None) -> None`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/plotting/test_axes.py`:

```python
def test_a_pressure_clamp_sets_the_pressure_range(tephigram_axes, sample_sounding):
    """The clamp names the layer; temperature is fitted inside it."""
    tephigram_axes.fit(sample_sounding, pressure=(950.0, 300.0), margin=0.0)
    xlo, xhi, ylo, yhi = _expected_limits(
        {"pressure": (950.0, 300.0), "temperature": (-58.7, 24.1)}
    )
    assert tephigram_axes.get_xlim() == pytest.approx((xlo, xhi), abs=0.5)
    assert tephigram_axes.get_ylim() == pytest.approx((ylo, yhi), abs=0.5)


def test_a_pressure_clamp_narrows_the_view(tephigram_axes, tephigram_axes_b, sample_sounding):
    """The defect this parameter exists to fix (framing spec §3.2).

    A radiosonde ascent does not stop at the tropopause; the shipped
    samples reach about 10 hPa. Framing all of that gives a view whose
    span is dominated by the stratosphere.
    """
    tephigram_axes.fit(sample_sounding, margin=0.0)
    tephigram_axes_b.fit(sample_sounding, pressure=(950.0, 300.0), margin=0.0)
    unclamped = tephigram_axes.get_xlim()
    clamped = tephigram_axes_b.get_xlim()
    assert (clamped[1] - clamped[0]) < 0.6 * (unclamped[1] - unclamped[0])


def test_a_clamp_excludes_data_outside_it(tephigram_axes, tephigram_axes_b, sample_sounding):
    """Levels outside the band do not bound the view."""
    tephigram_axes.fit(sample_sounding, pressure=(950.0, 300.0), margin=0.0)
    narrow = tephigram_axes.get_ylim()
    tephigram_axes_b.fit(sample_sounding, pressure=(950.0, 100.0), margin=0.0)
    wide = tephigram_axes_b.get_ylim()
    assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])


def test_a_clamp_order_carries_no_meaning(tephigram_axes, tephigram_axes_b, sample_sounding):
    tephigram_axes.fit(sample_sounding, pressure=(950.0, 300.0), margin=0.0)
    tephigram_axes_b.fit(sample_sounding, pressure=(300.0, 950.0), margin=0.0)
    assert tephigram_axes.get_xlim() == tephigram_axes_b.get_xlim()
    assert tephigram_axes.get_ylim() == tephigram_axes_b.get_ylim()


def test_a_clamp_containing_no_data_raises(tephigram_axes, sample_sounding):
    with pytest.raises(MissingDataError, match="no finite data"):
        tephigram_axes.fit(sample_sounding, pressure=(5.0, 1.0))


def test_an_unusable_clamp_is_refused(tephigram_axes, sample_sounding):
    with pytest.raises(ValueError, match="pressure"):
        tephigram_axes.fit(sample_sounding, pressure=(0.0, 300.0))
```

The temperature values `(-58.7, 24.1)` are what the shipped samples actually occupy between 950 and 300 hPa — measured, not chosen. If `sample_sounding` is not `norman-17z`, recompute them rather than adjusting the tolerance.

- [ ] **Step 2: Run them and watch them fail**

```bash
pixi run --frozen tests -- tests/plotting/test_axes.py -k "clamp or pressure_clamp" -v
```

Expected: `TypeError: fit() got an unexpected keyword argument 'pressure'` on all six.

- [ ] **Step 3: Add the parameter**

`fit`'s signature gains `pressure`, between the varargs and `margin`:

```python
    def fit(
        self,
        *objects: Sounding | Profile,
        pressure: tuple[float, float] | None = None,
        margin: float | None = None,
    ) -> None:
```

- [ ] **Step 4: Apply the clamp in the reduction**

Inside `fit`, the per-object loop currently collects every pressure and every temperature. It becomes: when a clamp is given, each object's temperature arrays are masked to the levels inside the band, and the view's pressure range is the clamp rather than the data.

Replace the reduction with:

```python
        if pressure is not None:
            for name, bounds in (("pressure", pressure),):
                lo, hi = sorted(bounds)
                if not (math.isfinite(lo) and math.isfinite(hi)):
                    msg = f"fit {name} clamp bounds must be finite: {bounds!r}"
                    raise ValueError(msg)
                if lo == hi:
                    msg = f"fit {name} clamp must not be degenerate: {bounds!r}"
                    raise ValueError(msg)
                if lo <= 0.0:
                    msg = f"fit pressure clamp bounds must be above 0 hPa: {bounds!r}"
                    raise ValueError(msg)
        pressures: list[npt.NDArray[np.float64]] = []
        temperatures: list[npt.NDArray[np.float64]] = []
        for obj in objects:
            level, temps = _framing_coordinates(obj)
            level = np.asarray(level, dtype=np.float64)
            if pressure is None:
                inside = np.ones(level.shape, dtype=bool)
            else:
                lo, hi = sorted(pressure)
                inside = (level >= lo) & (level <= hi)
            pressures.append(level[inside])
            temperatures.extend(np.asarray(t, dtype=np.float64)[inside] for t in temps)
        all_p = np.concatenate(pressures) if pressures else np.array([])
        all_t = np.concatenate(temperatures) if temperatures else np.array([])
        if not (
            all_p.size
            and all_t.size
            and np.isfinite(all_p).any()
            and np.isfinite(all_t).any()
        ):
            msg = "fit() found no finite data to frame"
            raise MissingDataError(msg)
        if pressure is None:
            span_p = (float(np.nanmin(all_p)), float(np.nanmax(all_p)))
        else:
            span_p = (float(min(pressure)), float(max(pressure)))
        xlo, xhi, ylo, yhi = _limits_from_ranges(
            span_p, (float(np.nanmin(all_t)), float(np.nanmax(all_t)))
        )
```

Everything below that — the margin resolution, the padded `set_xlim`/`set_ylim`, and `set_autoscale_on(False)` — is unchanged.

- [ ] **Step 5: Rewrite the docstring's promise**

`fit`'s docstring currently says it answers "frame this neatly". It does not, and the specification no longer claims it does. Replace the opening paragraph and add `pressure` to Parameters:

```python
        """Frame the view around the data given.

        Guarantees that nothing you gave it falls outside the frame. It
        does not guarantee a neat-looking diagram: a radiosonde ascent
        does not stop at the tropopause, and framing all of one gives a
        view whose span is dominated by the stratosphere. ``pressure=``
        is what makes it neat -- it names the layer you care about, and
        the temperature range is then fitted to the data inside it
        (framing spec §3.2).

        Takes soundings and parcel paths interchangeably, and frames
        everything it is given: a parcel is warmer than its environment
        through the CAPE region, so fitting a sounding alone can clip the
        path the parcel analysis is drawn to show. Autoscaling is
        disabled, as for :meth:`set_extent`.

        Parameters
        ----------
        *objects : Sounding or Profile
            What to frame. At least one is required.
        pressure : tuple of float, optional
            Pressure bounds in hPa, in either order, naming the layer to
            frame. Levels outside it do not bound the view. When omitted
            the whole of every object is framed, which is correct and is
            usually wide.
        margin : float, optional
            Fraction of the fitted span added to each side in the drawn
            plane. Resolves keyword > ``config.diagram.margin`` >
            ``DEFAULT_FIT_MARGIN``. Zero fits exactly.

        Raises
        ------
        TephpyValidationError
            If no objects are given, or one is neither a ``Sounding`` nor
            a ``Profile``.
        ValueError
            If the ``pressure`` clamp is non-finite, degenerate, or not
            above zero.
        MissingDataError
            If no finite data survives the clamp.
        """
```

- [ ] **Step 6: Run the tests, then the suite**

```bash
pixi run --frozen tests -- tests/plotting/test_axes.py -v
pixi run --frozen tests
```

Expected: all pass, including every `fit` test from Task 2 — the clamp is additive and the unclamped path is unchanged.

- [ ] **Step 7: Lint and commit**

```bash
pixi run --frozen lint
git add src tests
git commit -m "Give fit a pressure clamp, and stop promising neatness

An earlier draft of the specification claimed fit answers 'frame this
neatly'. Rendering it falsified that: a radiosonde ascent does not stop
at the tropopause, the shipped samples reach 10.2 hPa, and framing all of
one gives a narrow diagonal band of isopleths in a mostly empty
rectangle. The temperature span is barely implicated -- clamping to
(1000, 200) hPa moves the fitted temperature only from (-79.4, 27.5) to
(-72.3, 27.5), and turns an unusable figure into a conventional one.

So fit takes a pressure clamp, which names the layer and fits temperature
to the data inside it, and its docstring now promises what it actually
delivers: nothing you gave it falls outside the frame. There is no
default clamp -- any value would be arbitrary and would silently discard
the data above it, which is worse than a visibly wide view.

Implements framing spec §3.2.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: The Comparison Example Uses the Clamped `fit`

Implements framing spec §4. {issue}`184` names this example as what `fit` is for, and its hand-picked `EXTENT` was evidence the API was missing.

An earlier attempt at this task used an unclamped `fit` and produced a figure markedly worse than the hand-picked view; it was reverted. Task 3's clamp is what makes it work.

**Files:**
- Modify: `src/tephpy/examples/plot_sounding_comparison.py`
- Test: `tests/examples/test_examples.py`

- [ ] **Step 1: Read the example**

```bash
cat src/tephpy/examples/plot_sounding_comparison.py
```

Note the two sounding variable names and what the module docstring says about `EXTENT`.

- [ ] **Step 2: Replace the literal extent with a clamped fit**

Delete the `EXTENT` constant. Replace `ax.set_extent(**EXTENT)` with a clamped fit over both soundings, using the file's actual variable names:

```python
    ax.fit(first, second, pressure=(950.0, 300.0))
```

The band is the one the hand-picked extent used, and it is the layer the comparison is about.

Rewrite the module docstring: it currently justifies a hand-picked window. What is true now is that `fit` frames both ascents over the named layer, so the two are directly comparable without anyone choosing a temperature range by eye.

- [ ] **Step 3: Build and look at the figure**

```bash
pixi run --frozen tests -- tests/examples/ -v
pixi run --frozen --environment docs docs-html
```

Then **open** `docs/_build/html/_images/sphx_glr_plot_sounding_comparison_001.png`.

You are checking for the conventional tephigram look: the isopleth grid filling the frame, both profiles legible, no large empty corners, and the legend not sitting on the data. **If it does not look like that, stop and report** — an earlier attempt at this task produced exactly that failure and it was reverted rather than blessed.

- [ ] **Step 4: Run everything and commit**

```bash
pixi run --frozen tests
pixi run --frozen lint
git add src tests
git commit -m "Frame the comparison example with a clamped fit

The example hand-picked a literal EXTENT to make two ascents comparable,
which issue #184 names as what fit is for. Clamped to the layer the
comparison is about, fit derives the same kind of view without anyone
choosing a temperature range by eye.

Implements framing spec §4.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Do not use `git add -A`: an unrelated untracked directory sits in this tree.

---

### Task 5: The Framing How-To

Implements framing spec §7. Its spine is the contrast Task 3 exists because of.

**Files:**
- Create: `docs/src/howtos/framing.rst`
- Create: `docs/baseline/framing-*.png` (generated by blessing)
- Modify: `docs/src/howtos/index.rst`
- Modify: `tests/test_docs_snippets.py` (`DOCUMENTED`, `PUBLISHES_FIGURES`)
- Modify: `.github/scripts/check_docs_figures.py` (`PUBLISHES`)

- [ ] **Step 1: Write the page**

This page publishes figures, so **every** python block is a `.. plot::` (plots spec §3.2).

```rst
.. _howto-framing:

Frame the View
==============

Two questions, two answers. *Frame this neatly* is :meth:`ax.fit(...)
<tephpy.plotting.axes.TephigramAxes.fit>` with a pressure clamp; *make
these figures directly comparable* is :meth:`ax.set_extent(...)
<tephpy.plotting.axes.TephigramAxes.set_extent>`.

Fit to the Data, and Say Which Layer
------------------------------------

``fit`` guarantees that nothing you give it falls outside the frame. On a
whole :term:`radiosonde` ascent that is not what you want:

.. plot::
    :context: reset
    :filename-prefix: framing-fit-unclamped

    import matplotlib.pyplot as plt

    import tephpy

    sounding = tephpy.samples.sounding("norman-17z")
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.fit(sounding)
    ax.plot_sounding(sounding)

The ascent reaches about 10 hPa, and potential temperature climbs steeply
through the stratosphere, so framing all of it spends the diagram on air
nobody was asking about. Name the layer instead:

.. plot::
    :context: close-figs
    :filename-prefix: framing-fit-clamped

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.fit(sounding, pressure=(950.0, 300.0))
    ax.plot_sounding(sounding)

Same call, same data, one argument. Levels outside the band no longer
bound the view.

Include the Parcel
------------------

A lifted :term:`parcel` is warmer than its environment through the
:term:`CAPE` region, so a view fitted to the :term:`sounding` alone can
clip the :term:`parcel ascent` the analysis exists to show. Pass it too:

.. plot::
    :context: close-figs
    :filename-prefix: framing-fit-parcel

    parcel = tephpy.calc.parcel_path(sounding)

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.fit(sounding, parcel, pressure=(950.0, 300.0))
    ax.plot_sounding(sounding)
    ax.plot_profile(parcel)

``fit`` is variadic, so several ascents frame alike — a station's day in
one window is ``ax.fit(*ascents, pressure=(950.0, 300.0))``.

Fix the View by Ranges
----------------------

When two figures must be directly comparable, name the window outright:

.. plot::
    :context: close-figs
    :filename-prefix: framing-set-extent

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.set_extent(pressure=(950.0, 300.0), temperature=(-50.0, 5.0))
    ax.plot_sounding(sounding)

Order within a range does not matter, and both keywords are required.
Because the view is an axis-aligned rectangle and pressure is not an axis,
it always reaches a little further than the ranges name — see
:meth:`set_extent <tephpy.plotting.axes.TephigramAxes.set_extent>` for
what the default extent actually spans.

Leave Room, or None
-------------------

``margin`` is a fraction of the fitted span, added to each side. Set it
per call, or once in a configuration file as ``diagram.margin``:

.. plot::
    :context: close-figs
    :filename-prefix: framing-margin

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.fit(sounding, pressure=(950.0, 300.0), margin=0.0)
    ax.plot_sounding(sounding)

``margin=0`` fits exactly, which is what composing panels whose frames
must agree to the pixel wants.
```

- [ ] **Step 2: Register the page**

Add `framing` to `docs/src/howtos/index.rst`'s toctree. Add `"howtos/framing.rst"` to **both** `DOCUMENTED` and `PUBLISHES_FIGURES` in `tests/test_docs_snippets.py`, and to `PUBLISHES` in `.github/scripts/check_docs_figures.py`. Three lists — a page in some but not all is the silent-fail case they exist to prevent.

- [ ] **Step 3: Run the snippet gate before any figure exists**

```bash
pixi run --frozen tests -- tests/test_docs_snippets.py -v
```

Expected: PASS. This runs the page as one script and catches a broken call before the slow build does.

- [ ] **Step 4: Build, bless, and look**

```bash
pixi run --frozen --environment docs docs          # figure gate fails: no baselines
pixi run --frozen --environment docs docs-figures  # writes docs/baseline/framing-*.png
```

**Open all five PNGs.** The page's argument is the first two: `framing-fit-unclamped` must visibly be the poor one — narrow band of isopleths, empty corners — and `framing-fit-clamped` must visibly be the conventional one. If they look alike the page is teaching something its figures do not show; stop and report.

- [ ] **Step 5: Re-run everything and commit**

```bash
pixi run --frozen --environment docs docs
pixi run --frozen tests
pixi run --frozen lint
git add docs tests .github
git commit -m "Add the framing how-to

Its spine is the contrast that shaped the API: fit on a whole ascent,
which reaches the stratosphere and looks it, beside the same call with a
pressure clamp. The defect found in execution is the thing the page
teaches.

Implements framing spec §7.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Specifications, Changelog, and the Pull Request

Implements framing spec §4's specification migration and §8's open item.

**Files:**
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md` (§3.2, §3.4, §10 row 8)
- Modify: `docs/src/developer/specs/2026-08-12-config-domain-validation-design.md` (§3.3 table)
- Modify: `docs/src/developer/specs/2026-08-17-published-figures-design.md`
- Modify: `docs/src/developer/specs/2026-08-20-examples-gallery-design.md`
- Modify: `docs/src/developer/specs/2026-08-07-config-file-design.md`
- Modify: `docs/src/developer/specs/2026-08-25-scope-and-support-design.md`
- Modify: `docs/src/developer/specs/2026-08-25-framing-design.md` (§8's open item)
- Create: `changelog/<PR>.feature.rst`

- [ ] **Step 1: Find every specification sentence describing the old shape**

```bash
grep -rn "set_extent\|corner" docs/src/developer/specs/*.md | grep -v 2026-08-25-framing
```

Work the list, rewriting corner-pair prose to ranges and citing `framing spec §3.1` rather than restating its reasoning. **Never put a citation in a section heading** (docs spec §3.7).

Four need particular care:
- **spec §3.2** calls this "the cartopy idiom" (line ~410). That is now doubly wrong — cartopy takes flat ranges and this takes named ones. Say what the API is rather than whose it resembles.
- **domain spec §3.3**'s table row reads `| extent | 1 | every corner number finite, both pressures > 0 | axes.TephigramAxes.set_extent |`. Update the rule to ranges and add a `margin` row.
- **configfile spec** (`2026-08-07-config-file-design.md:520`) quotes a worked example error, `"...expects two [pressure, temperature] corners, not [1, 2]"`, which no longer matches the message the code produces. Quote the real one.
- **scope spec §5**'s testing table cites "the docs-style review checklist", which does not exist ({issue}`193`). Leave it — that is #193's business, not this plan's.

- [ ] **Step 2: Mark the roadmap row complete**

In spec §10's table, Plan 8's row status becomes `✅ complete (PR {pull}`NNN`)`. Substitute the real number in Step 4.

- [ ] **Step 3: Resolve the framing spec's own open item**

`framing spec §8`'s open item becomes:

```
- **Resolved** (2026-08-25, PR {pull}`NNN`) — **the whole of this specification.**
  {issue}`184` closes with it.
```

**Keep the date 2026-08-25.** docs spec §3.5 dates a decision when it was *taken*, not when its pull request merged, and these decisions were taken on the 25th.

- [ ] **Step 4: Open the pull request, then fill in its number**

```bash
git push -u origin framing
gh pr create --title "Frame the tephigram by ranges and by data" --body "$(cat <<'BODY'
Plan 8 of the roadmap. Closes #184.

`set_extent` documented its argument as bottom-left and top-right corners,
then mapped those two points and took the extremes on each axis. That is the
bounding box of two *points* in a rotated space, and it need not contain the
region they delimit — measured, `set_extent(((1000, 30), (900, -10)))`
produced a view excluding `(1000, -10)` and `(900, 30)`, half the region the
caller named. #184 found the corner naming false for three of four ordinary
inputs and the `(T, p)` transposition silently accepted; it did not find this
one.

`ax.fit(...)` is the API that was missing. It frames the view around
soundings and parcel paths directly, with a `pressure=` clamp naming the
layer of interest.

Nothing is released, so there is no deprecation cycle — every caller moves
here.

## What execution changed about the design

The specification originally claimed `fit` "answers *frame this neatly*".
Rendering it falsified that: a radiosonde ascent does not stop at the
tropopause, the shipped samples reach 10.2 hPa, and framing all of one gives
a narrow band of isopleths in a mostly empty rectangle. The `pressure=` clamp
is the fix, `fit` now promises only what it delivers — nothing you gave it
falls outside the frame — and the how-to teaches the contrast rather than
hiding it.

## Verification

`pixi run tests`, `pixi run docs` and `pixi run lint`, all green. No image
baseline moved under the `set_extent` change — the default extent maps
identically under two-corner and four-corner mapping.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_017fz9nNazC5nuiYk69iGL1k
BODY
)"
```

Then, with `196` as an example — **use the real number**:

```bash
sed -i 's/{pull}`NNN`/{pull}`196`/g' docs/src/developer/specs/*.md
grep -rn "NNN" docs/src/developer/specs/ && echo "PLACEHOLDER SURVIVED" || echo "clean"
```

- [ ] **Step 5: Write the changelog fragment**

`changelog/196.feature.rst`:

```rst
:meth:`ax.set_extent(...) <tephpy.plotting.axes.TephigramAxes.set_extent>`
now takes a ``pressure`` range and a ``temperature`` range as keywords, in
place of two ``(pressure, temperature)`` corners, and frames the whole region
it is given rather than the bounding box of the two corners named. The new
:meth:`ax.fit(...) <tephpy.plotting.axes.TephigramAxes.fit>` frames the view
around soundings and parcel paths, with ``pressure=`` naming the layer of
interest and ``margin=`` defaulting to ``diagram.margin``. Configuration files
spell an extent as ``{pressure: [...], temperature: [...]}``.
(:user:`bjlittle`)
```

- [ ] **Step 6: Verify, commit, push, watch**

```bash
pixi run --frozen tests
pixi run --frozen --environment docs docs
pixi run --frozen lint
git add changelog docs
git commit -m "Update the specifications, and add the changelog fragment

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push
gh pr checks --watch
```

---

## Self-Review Record

**Spec coverage.** framing spec §3.1 → Task 1; §3.2's reduction → Task 2, its clamp and its corrected promise → Task 3; §3.3 → Task 2, with the clamp interaction in Task 3; §3.4 → Task 1; §3.5 → Tasks 1 and 2; §4 → Task 1 Step 10, Task 4, Task 6 Step 1; §5's alternatives → no task, correctly, since it records what is *not* built; §6 testing → the test steps of Tasks 1, 2 and 3 plus Task 5's baselines; §7 → Task 5; §8's open item → Task 6 Step 3. No gap.

**Placeholder scan.** Two deliberate substitutions, each with a verifying command: the PR number (Task 6 Step 4, greps for survivors) and the two sounding variable names in the comparison example (Task 4 Step 1, says to read the file).

**Type consistency.** `_limits_from_ranges` returns `(xlo, xhi, ylo, yhi)` in Task 1 and is unpacked in that order in Tasks 2 and 3. `_framing_coordinates` returns `(pressures, [temperatures])`, and Task 3's clamp masks both by the same boolean, which requires the temperature arrays to be the same length as the pressure array — true for both `Sounding` and `Profile`, whose fields are per-level. `fit`'s signature is `(*objects, pressure=None, margin=None)` in Task 3 and is called with `pressure=` in Tasks 4 and 5.

**One thing this plan now records that it did not before.** Task 3 exists because execution falsified the specification, and its text says so. A plan is a point-in-time record; the record should show that the design was wrong and how it was found, not present the clamp as though it had been the intention all along.
