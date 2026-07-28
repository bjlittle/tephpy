# tephpy Wind Barbs & Data Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver `ax.plot_barbs` — the sounding's wind barbs on a zoom-aware right-hand gutter staff with Met Office symbology — together with the §3.4 ingest layer (`tephpy.io.wyoming.fetch`, `tephpy.io.igra.read` returning validated `Sounding`s from recorded-fixture-tested parsers), `TephpyIOError`, the shared side-panel divider with order-independent layout, and the barb image baselines — so the §4 canonical usage runs end to end.

**Architecture:** `plotting/barbs.py` is free geometry (pure numpy `staff_y`/`select_barbs`, the `shading.py` builder pattern) plus `BarbStaff`, a zoom-aware artist (the `IsoplethFamily` refresh pattern) managing a `matplotlib.quiver.Barbs` child via same-length masked updates. `plotting/axes.py` grows one cached `axes_grid1` divider shared by every side-panel method, a `_relayout_side_panels` helper that rebuilds the divider stack inside-out (diagram, gutter, indices panel) whichever order the panel methods are called in, and `plot_barbs`. `tephpy/io/` holds `wyoming.py` (stdlib `urllib` behind a function-local import + a pure `TEXT:CSV` parser), `igra.py` (fixed-width IGRA v2, zip-or-text), and `_util.py` (shared time coercion and the strictly-decreasing pressure filter); both readers construct `Sounding(units=...)`, so §6 ingest validation applies unchanged, and `tephpy.io` re-exports eagerly (§10 item 10 — network/archive imports stay function-local, policed by the extended import-cost guard).

**Tech Stack:** Python 3.12/3.13/3.14, numpy, matplotlib (Agg in tests; `mpl_toolkits.axes_grid1` divider + `matplotlib.quiver.Barbs`), pint (MetPy's registry), metpy ≥ 1.6 (`wind_components`, function-local), stdlib `urllib`/`zipfile`/`csv` (no new dependency), pytest, pytest-mpl, pixi tasks.

**Spec:** `docs/superpowers/specs/2026-07-22-tephpy-design.md` — §3.2 (`plot_barbs`, the side-of-axes contract and its 2026-07-27 resolution), §3.4 (readers), §5 (units policy), §6 (`TephpyIOError`, `MissingDataError` for absent wind, NaN gaps are data), §7 (recorded-fixture IO tests, no live network in CI), §10 (Plan 6 row; items 10 and 13 Plan 6 slices).

This is **Plan 6 of 7** (spec §10). It produces working software: after it merges, `wyoming.fetch("03808", "2026-07-21 12:00")` returns a validated `Sounding` and `ax.plot_barbs(snd)` draws its winds beside the diagram, composing with Plan 5's panel in either call order. Plan 7 (examples & docs completion) needs the union of Plans 5 and 6 — including the composed §4-figure baseline this plan deliberately does not add.

## Global Constraints

Copied from the spec / Plans 1–5; every task's requirements implicitly include these.

- **Python support (SPEC 0):** 3.12, 3.13, and 3.14. **Platforms (pixi):** `linux-64` only.
- **Copyright header (every `.py` file, verbatim — ruff `CPY001` enforces it):**
  ```
  # Copyright (c) 2026, tephpy Contributors.
  #
  # This file is part of tephpy and is distributed under the 3-Clause BSD license.
  # See the LICENSE file in the package root directory for licensing details.
  ```
- **Imports:** every `.py` file needs `from __future__ import annotations` (ruff isort `required-imports`).
- **Lint/type:** ruff `ALL` (repo config); mypy `strict` clean over `src/tephpy`, no per-module relaxations. numpydoc-validation checks **every docstringed object, including private helpers**: documented parameters (PR01) and a `Returns` section on anything returning a value (RT01).
- **Function-local heavy imports** (spec §3.4, §10 item 10): `urllib`, `zipfile`, and `metpy.calc` sites carry `# noqa: PLC0415` exactly as shown. The subprocess import-cost guard in `tests/test_units.py` is extended by Task 10 to also forbid `urllib.request` and `zipfile` at `import tephpy` time.
- **matplotlib kwargs pass-through:** `**kwargs: Any` with `# noqa: ANN401` on the def line (Plan 4/5 precedent) — including on **private** helpers that forward kwargs (`_append_side_axes`).
- **Units:** pint quantities at every public boundary; conversion via `.m_as(...)` — never `np.asarray(Quantity)` (`UnitStrippedWarning` is an **error** under the repo's pytest `filterwarnings = ["error"]`).
- **Tests:** pytest strict config with `filterwarnings = ["error"]`; close every matplotlib figure you open. The tests tree mirrors `src/tephpy`: `tests/plotting/test_barbs.py`, and a new `tests/io/` package (`test_util.py`, `test_wyoming.py`, `test_igra.py`).
- **Docs:** build must stay warning-free (`pixi run docs` — it cleans first, so changelog/xref checks always see a fresh build). Glossary entries ship with this plan's terms (radiosonde, IGRA, wind barb). Every **new public class or exception name used as a numpydoc parameter/return/raises type needs a `numpydoc_xref_aliases` entry** in `docs/src/conf.py`, or nitpicky fails the build (Task 11; this is how `TephpyUnitsError` etc. resolve today).
- **Changelog:** one `changelog/<PR>.feature.rst` fragment per PR, cross-referencing the new APIs with Sphinx roles and ending with ``(:user:`claude`)`` (see `changelog/README.md`); verify with a **clean** docs build.
- **Branch:** work on a feature branch (`no-commit-to-branch` blocks `main`): `git switch -c barbs-ingest`. Ensure the pre-commit git hooks are installed **before the first commit** (`pixi run --frozen pre-commit install` — fresh clones/worktrees only have `.sample` hooks) and run `pixi run lint` before every push.
- **Lint gotcha:** `pre-commit run --all-files` only checks files git knows about — **`git add` new files before `pixi run lint`** (every task's final step stages first for this reason).
- **Dedented listings:** the repo's blacken-docs hook formats this plan's fenced listings at top level, so code destined for a **class body** (Tasks 3(b), 4(c)) is shown **dedented** — indent every line one level (4 spaces) when inserting into `TephigramAxes`.
- **Environment facts (verified against the committed lockfile, 2026-07-27):** matplotlib 3.11.1, numpy 2.5.1, metpy 1.7.1, pint 0.25.3, pytest-mpl 0.19.0. Facts this design leans on, all probed empirically:
  - **`axes_grid1` relayout:** `divider.set_horizontal([...])` plus `divider.new_locator(nx=..., ny=0)` reassigns every axes' slot cleanly — this is how call order becomes irrelevant. Naive `remove()` + `append_axes` is NOT viable: `append_axes` only ever appends to the stack, so a removed panel leaves a stale `Size` slot (a phantom gap). `append_axes(..., axes_class=Axes, sharey=self)` works, and `sharey` keeps the gutter's y-window locked to the diagram through zoom/pan/`set_extent`. `axes_class=Axes` stays **mandatory** — otherwise axes_grid1 clones the tephigram projection into the panel (Plan 5 precedent).
  - **`matplotlib.quiver.Barbs`:** accepts same-length masked `set_offsets` + `set_UVC` updates (masked points simply aren't drawn) but **raises on length changes** — so `BarbStaff` keeps full-length arrays and thins by mask. A `Barbs` can be constructed directly (never added to the axes), given `set_figure(...)`, and drawn manually from an owning artist's `draw()` — the managed-child idiom `IsoplethFamily` uses for its `LineCollection`. Calm (below-half-increment) points natively render as a small **circle** — which is the Met Office calm symbol. `barb_increments={"half": 5, "full": 10, "flag": 50}` with `rounding=True` is exactly the 5 kt binning.
  - **`metpy.calc.wind_components(speed, direction)`** uses the meteorological from-direction convention (360° at 10 kt → u ≈ 0, v = −10 kt) and preserves the speed's units.
  - **University of Wyoming (probed live 2026-07-27):** the classic `cgi-bin/sounding` TEXT:LIST endpoint now returns **404** — the archive moved to `https://weather.uwyo.edu/wsgi/sounding`. Its `type=TEXT:CSV` form returns **bare, self-describing CSV** (no HTML wrapper): header `time,longitude,latitude,pressure_hPa,geopotential height_m,temperature_C,dew point temperature_C,ice point temperature_C,relative humidity_%,humidity wrt ice_%,mixing ratio_g/kg,wind direction_degree,wind speed_m/s` — note wind speed in **m/s** (the classic format's SKNT knots is gone). `src=` is optional. Failures are one-line plain-text bodies: HTTP **400** "Unable to retrieve the data for 03808 at 2026-07-21 03:00:00." (no data at that time) and HTTP **404** (unknown station). A BUFR-era ascent is dense (2,395 rows for Camborne 2026-07-21 12Z) and, in the captured case, strictly monotonic — the running-minimum filter is a defensive no-op there.
  - **IGRA v2 (probed live 2026-07-27):** Camborne is **UKM00003808** (`GBM` is Gabon — check `igra2-station-list.txt`, not intuition). Year-to-date per-station files live at `data-y2d/UKM00003808-data-beg2026.txt.zip` (one member per zip). The fixed-width layout verified against real records, cross-checked value-for-value against the Wyoming capture of the same launch: header `#` + ID [1:12], year [13:17], month [18:20], day [21:23], hour [24:26] (99 = missing), numlev [32:36]; data PRESS [9:15] (Pa), TEMP [22:27] (tenths °C), DPDP [34:39] (tenths °C), WDIR [40:45] (deg), WSPD [46:51] (tenths m/s); sentinels −9999/−8888.
  - **`urllib.error.HTTPError` must be closed** after reading its body (`with error: ...`) — an unclosed one emits `ResourceWarning`, which `filterwarnings = ["error"]` turns into a test failure.
  - **Lint/type posture discovered on this exact code:** `tests/io/__init__.py` trips ruff A005 (stdlib-module shadowing; `src/tephpy/io` doesn't, thanks to the `src` root) — per-file-ignored with a comment; the byte-faithful fixtures need `^tests/fixtures/io/` excluded from the whitespace hooks (their records end with a trailing space); `numpy.bool_` joins `nitpick_ignore` (numpy's inventory publishes `numpy.bool`); `coerce_time` needs the `value: object` narrowing idiom (mypy strict flags the runtime `TypeError` guard unreachable otherwise); `Sounding(**dict)` fails mypy strict — pass the fields explicitly; `Artist.axes` is typed `_AxesBase` — `cast("Axes", ...)` before handing it to `Barbs`; `append_axes` returns `Any` per the stubs — `cast("Axes", ...)` at the one return site.

  Every listing in this plan is the **verified implementation**: it passes ruff (`ALL` + format), mypy strict, and numpydoc-validation; the full suite (420 tests including the 13 image comparisons) passes on the test-py312, test-py313, and default/py314 environments against the same committed baselines; the docs build is warning-free; `wyoming.fetch` was exercised live (success, 400, and 404 paths) on 2026-07-27; and the two readers were cross-validated on the same physical ascent from both archives.

---

## File structure created or modified by this plan

```
src/tephpy/
  exceptions.py                       # MODIFIED: + TephpyIOError
  _constants.py                       # MODIFIED: + barb and io conventions
  plotting/barbs.py                   # NEW: staff_y, select_barbs, BarbStaff
  plotting/axes.py                    # MODIFIED: shared divider + relayout;
                                      #           plot_barbs; annotate_indices
                                      #           refactor; clear() teardown
  io/__init__.py                      # NEW: eager re-export (minimal in Task 6,
                                      #      completed in Task 10)
  io/_util.py                         # NEW: coerce_time, strictly_decreasing
  io/wyoming.py                       # NEW: fetch + pure TEXT:CSV parser
  io/igra.py                          # NEW: read + fixed-width IGRA v2 parser
  __init__.py                         # MODIFIED: export io
tests/
  test_exceptions.py                  # MODIFIED: + TephpyIOError hierarchy
  test_constants.py                   # MODIFIED: + barb and io conventions
  test_import.py                      # MODIFIED: __all__ + io reachability
  test_units.py                       # MODIFIED: import-cost guard + urllib/zipfile
  plotting/test_barbs.py              # NEW: geometry, artist, layout, method
  plotting/test_images.py             # MODIFIED: + 2 barb baselines
  baseline/test_barbs_staff.png       # NEW: generated baseline (~54 KB)
  baseline/test_barbs_with_indices_panel.png  # NEW: generated baseline (~70 KB)
  io/__init__.py                      # NEW: test package (mirrors src)
  io/test_util.py                     # NEW: shared-helper tests
  io/test_wyoming.py                  # NEW: parser, URL, error mapping
  io/test_igra.py                     # NEW: parser, selection, error mapping
  fixtures/generate_io_fixtures.py    # NEW: one-shot capture script
  fixtures/io/README.md               # NEW: provenance (spec §10 item 13)
  fixtures/io/wyoming-03808-2026-07-21-12Z.csv     # NEW: recorded capture
  fixtures/io/UKM00003808-data-trimmed.txt         # NEW: recorded capture
docs/src/conf.py                      # MODIFIED: xref aliases; nitpick entry
docs/src/reference/glossary.rst       # MODIFIED: + radiosonde, IGRA, wind barb
.pre-commit-config.yaml               # MODIFIED: fixture whitespace excludes
pyproject.toml                        # MODIFIED: per-file-ignores additions
changelog/<PR>.feature.rst            # NEW: news fragment (named after the PR)
```

Naming used throughout (Interfaces contract):

```
tephpy.exceptions (addition):
    TephpyIOError(TephpyError)        # reader failures; NOT a validation error

tephpy._constants (additions):
    BARB_GUTTER_WIDTH = "15%"         # axes_grid1 fraction of the diagram width
    BARB_GUTTER_PAD = 0.1             # inches
    BARB_STAFF_POSITION = 0.5         # fraction across the gutter
    BARB_MIN_SEPARATION = 18.0        # points, between drawn barbs
    BARB_INCREMENTS = {"half": 5.0, "full": 10.0, "flag": 50.0}   # knots
    BARB_LENGTH = 6.0                 # points
    WYOMING_URL                       # https wsgi TEXT:CSV template
    WYOMING_TIMEOUT = 30.0            # seconds
    IGRA_MISSING = (-9999, -8888)     # sentinels

tephpy.plotting.barbs (public builders + artist):
    staff_y(pressure, x_edge) -> NDArray[float64]          # bare hPa in, data-y out
    select_barbs(y, *, minimum_separation) -> NDArray[bool_]
    BarbStaff(main_axes, pressure, u, v, *, x=BARB_STAFF_POSITION,
              minimum_separation, **kwargs)                # Artist; .barbs property

tephpy.plotting.axes.TephigramAxes (additions; attrs join clear()):
    _side_divider: AxesDivider | None                      # created once, cached
    _barb_gutter: Axes | None
    _append_side_axes(*, width, pad, **kwargs) -> Axes     # private helper
    _relayout_side_panels() -> None                        # inside-out rebuild
    plot_barbs(snd, *, x=None, **kwargs) -> BarbStaff

tephpy.io (public):
    wyoming.fetch(station, time, *, timeout=None) -> Sounding
    igra.read(path, *, time=None) -> Sounding
    _util.coerce_time(time) -> datetime                    # naive => UTC
    _util.strictly_decreasing(pressure) -> NDArray[bool_]  # running-min filter

tephpy top level:
    __all__ = ["Sounding", "__version__", "calc", "config", "exceptions",
               "io", "plotting", "transforms"]
```

Design decisions locked here (shared vocabulary for all tasks):

- **Staff placement solves on the isobar's analytic extension.** The tephigram x
  decomposes along an isobar into `x = g(T) + c(p)` with
  `g(T) = MA·ln(T + KELVIN_ZERO) + T` (level-independent, strictly increasing)
  and `c(p) = MA·KAPPA·ln(P_REF/p)`, so every level's crossing temperature is one
  inverse interpolation on a shared sampled `g`, then the real transforms give y.
  The inversion grid deliberately spans far beyond `TEMPERATURE_DOMAIN`
  (−200…300 °C, 2048 samples): a drawn isobar polyline often **ends inside the
  view** (its 60 °C endpoint falls mid-panel at the default extent), and a barb
  must still get its geometric anchor — Poisson's equation is smooth there.
  Solving on the drawn polylines instead loses most barbs at the default view
  (observed empirically, not hypothetical).
- **Thinning is greedy, surface-first, in display space.** `select_barbs` keeps
  each position at least the separation from the last kept one; the surface barb
  always survives; positions and separation share one space, and `BarbStaff`
  feeds it display pixels (`BARB_MIN_SEPARATION` points × dpi/72), which is what
  makes zooming in reveal more levels.
- **Order-independence is relayout, not teardown.** One divider is created per
  axes and cached (`_side_divider`); every panel is created through it; and
  `_relayout_side_panels` rebuilds `set_horizontal([AxesX(diagram), pad, gutter,
  pad, panel])` — skipping absent panels — and reassigns every locator. No panel
  is removed or re-rendered; `annotate_indices` needs no caching. `clear()`
  removes both panels, resets the locator, and nulls the divider, so a cleared
  diagram reclaims its full slot.
- **One staff per `plot_barbs` call.** Each call adds one `BarbStaff` to the one
  shared gutter; overlaid soundings pick another `x` (fraction across the
  gutter) and a colour — the explicit-styles convention profile overlays use.
- **Readers parse; `Sounding` validates.** Both parsers only shape data: blank
  cells/sentinels → NaN, dewpoint = temperature − depression (IGRA), rows kept
  only while pressure strictly undercuts the running minimum (first occurrence
  wins — duplicates AND balloon-wobble rises drop), and an optional field that
  is entirely NaN passed as absent (`None`) so `MissingDataError` stays
  meaningful downstream. Everything else — shapes, monotonicity, Td ≤ T, wind
  pairing — is `Sounding.__post_init__`'s single validation path (§3.4).
- **Time is coerced once, the `Sounding` way.** `coerce_time` accepts a datetime
  or ISO 8601 string; naive reads as UTC, aware converts; a non-ISO string is a
  `ValueError` and a wrong type a `TypeError` (usage errors, not
  `TephpyIOError`).
- **Error taxonomy:** transport failures, HTTP errors (with the archive's
  one-line reply summarised), unrecognisable responses, malformed or truncated
  IGRA records, a multi-member zip, an unmatched `time=` (nearest nominal times
  reported), and an ambiguous no-`time=` read of a multi-sounding file are all
  `TephpyIOError`. A single-sounding file may omit `time=` (the fixture/subset
  grace). `igra.read` reports count and span for ambiguity, and the three
  nearest ascents for a miss.
- **The fixtures are one physical launch, twice.** Camborne, nominal 2026-07-21
  12Z, released 11:17 UTC — captured from both archives by
  `tests/fixtures/generate_io_fixtures.py` (network needed only when
  regenerating; the archives are stable for a past date). The Wyoming capture is
  thinned to every 40th row (61 byte-faithful rows); the IGRA capture keeps the
  00Z and 12Z ascents as whole blocks. Provenance lives in
  `tests/fixtures/io/README.md` (spec §10 item 13): Wyoming credited to the
  University of Wyoming, Department of Atmospheric Science; IGRA is NOAA/NCEI
  public domain (doi:10.7289/V5X63K0Q).
- **Lint posture:** `# noqa: PLC0415` on function-local imports, `# noqa: S310`
  (with its justifying comment) on the one `urlopen` call, `# noqa: PTH123` on
  the plain `open` in `igra._text`, `# noqa: PLR0913` on `BarbStaff.__init__`,
  `# noqa: ANN401` on kwargs pass-throughs, `# numpydoc ignore=GL08` nowhere
  (no overloads this plan). Codespell: `PRES` is already in `ignore-words-list`
  (PR #38).

---

## Task 1: `TephpyIOError`

**Files:**
- Modify: `src/tephpy/exceptions.py`
- Test: `tests/test_exceptions.py`

**Interfaces:**
- Consumes: `TephpyError` (the existing hierarchy root).
- Produces: `TephpyIOError(TephpyError)` — raised by every reader failure in Tasks 8–9. It is **not** a `TephpyValidationError`: reader failures have no offending-level indices.

- [ ] **Step 1: Write the failing tests**

In `tests/test_exceptions.py`, add `TephpyIOError` to the import:

```python
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    MissingDataError,
    NonMonotonicPressureError,
    ProfileTooShortError,
    TephpyError,
    TephpyIOError,
    TephpyUnitsError,
    TephpyValidationError,
)
```

and extend `test_hierarchy` — the two new lines go immediately before the final `TephpyError` assertion:

```python
assert issubclass(TephpyIOError, TephpyError)
assert not issubclass(TephpyIOError, TephpyValidationError)
assert issubclass(TephpyError, Exception)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_exceptions.py -v`
Expected: FAIL — `ImportError: cannot import name 'TephpyIOError'`

- [ ] **Step 3: Implement the exception**

In `src/tephpy/exceptions.py`, add `"TephpyIOError",` to `__all__` (alphabetical — after `"TephpyError",`), and insert the class immediately **before** `class ProfileTooShortError`:

```python
class TephpyIOError(TephpyError):
    """A reader could not fetch or make sense of its source (spec §6).

    Network failures, HTTP errors, the archive's "no data" replies, a
    malformed or unrecognisable file, and an ambiguous read (an IGRA
    station file holding many soundings with no ``time=`` selector) all
    raise this, summarising the upstream response or file state.
    """
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_exceptions.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/exceptions.py tests/test_exceptions.py
pixi run --frozen lint
git commit -m "feat: add TephpyIOError for reader failures"
```

---

## Task 2: Barb conventions and the pure staff geometry

**Files:**
- Modify: `src/tephpy/_constants.py`
- Create: `src/tephpy/plotting/barbs.py` (the free builders; Task 4 appends the artist)
- Test: `tests/plotting/test_barbs.py` (the pure tests; Task 4 appends the rest), `tests/test_constants.py`

**Interfaces:**
- Consumes: `tephpy.transforms.theta_from_pressure_temperature(pressure, temperature)`, `tephpy.transforms.xy_from_temperature_theta(temperature, theta)`, and the `_constants` physics (`MA`, `KAPPA`, `KELVIN_ZERO`, `P_REF`).
- Produces: `staff_y(pressure, x_edge) -> NDArray[float64]` (bare hPa in, tephigram data-space y out, NaN where unreachable) and `select_barbs(y, *, minimum_separation) -> NDArray[bool_]` — Task 4's `BarbStaff.draw` composes exactly these two, and the Task 4 count test recomputes them headlessly.

- [ ] **Step 1: Add the barb conventions to `_constants.py`**

Insert immediately **before** the `LABEL_FONTSIZE` entry:

```python
#: Wind-barb gutter width, as an ``axes_grid1`` fraction of the diagram
#: width (spec §3.2).
BARB_GUTTER_WIDTH: Final[str] = "15%"

#: Wind-barb gutter padding from the diagram, in inches.
BARB_GUTTER_PAD: Final[float] = 0.1

#: Default staff position, as a fraction across the gutter; overlaid
#: soundings pick other positions via ``plot_barbs(..., x=...)``.
BARB_STAFF_POSITION: Final[float] = 0.5

#: Minimum vertical separation between drawn barbs, in points; the staff
#: keeps the densest subset at least this far apart, so zooming in reveals
#: more levels (spec §3.2).
BARB_MIN_SEPARATION: Final[float] = 18.0

#: Wind-barb speed increments in knots — half barb 5 kt, full barb 10 kt,
#: flag 50 kt, with speeds rounded to the nearest increment (5 kt binning):
#: the Met Office/WMO symbology (Met Office Factsheet 13; spec §1, §3.2).
BARB_INCREMENTS: Final[dict[str, float]] = {"half": 5.0, "full": 10.0, "flag": 50.0}

#: Wind-barb glyph length in points.
BARB_LENGTH: Final[float] = 6.0
```

(The io conventions — `WYOMING_URL`, `WYOMING_TIMEOUT`, `IGRA_MISSING` — arrive with their readers in Tasks 8–9.)

- [ ] **Step 2: Write the failing tests**

Create `tests/plotting/test_barbs.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the wind-barb gutter staff (spec §3.2)."""

from __future__ import annotations

import numpy as np
import pytest

from tephpy import transforms
from tephpy.plotting.barbs import select_barbs, staff_y
from tephpy.plotting.isopleths import isobar_members


def test_staff_y_points_lie_on_their_isobars():
    """Inverting a crossing recovers a point at exactly that pressure."""
    pressure = np.array([1000.0, 850.0, 500.0, 300.0])
    x_edge = 1800.0
    y = staff_y(pressure, x_edge)
    assert np.isfinite(y).all()
    temperature, theta = transforms.temperature_theta_from_xy(
        np.full(y.shape, x_edge), y
    )
    expected = transforms.theta_from_pressure_temperature(pressure, temperature)
    np.testing.assert_allclose(theta, expected, rtol=1e-6)


def test_staff_y_matches_the_drawn_isobar_polyline():
    """Where the crossing lies inside the drawn domain, the polyline agrees."""
    (member,) = isobar_members([500.0])
    inside = member.xy[member.xy[:, 0] <= member.xy[-1, 0] - 1.0]
    x_edge = float(inside[len(inside) // 2, 0])
    y_polyline = np.interp(x_edge, member.xy[:, 0], member.xy[:, 1])
    assert staff_y([500.0], x_edge)[0] == pytest.approx(y_polyline, abs=1e-2)


def test_staff_y_extends_beyond_the_drawn_temperature_domain():
    """A crossing past TEMPERATURE_DOMAIN stays finite (spec placement rule)."""
    (member,) = isobar_members([850.0])
    beyond = float(member.xy[-1, 0]) + 10.0
    assert np.isfinite(staff_y([850.0], beyond)[0])


def test_staff_y_nan_for_unphysical_or_unreachable_input():
    y = staff_y([-10.0, 0.0, 850.0], 1e9)
    assert np.isnan(y).all()


def test_select_barbs_keeps_the_first_and_spaced_positions():
    y = np.array([0.0, 10.0, 25.0, 30.0, 55.0])
    np.testing.assert_array_equal(
        select_barbs(y, minimum_separation=20.0),
        [True, False, True, False, True],
    )


def test_select_barbs_boundary_separation_is_kept():
    y = np.array([0.0, 20.0])
    np.testing.assert_array_equal(
        select_barbs(y, minimum_separation=20.0), [True, True]
    )


def test_select_barbs_drops_non_finite_positions():
    y = np.array([np.nan, 5.0, np.inf, 50.0])
    np.testing.assert_array_equal(
        select_barbs(y, minimum_separation=20.0), [False, True, False, True]
    )
```

and append to `tests/test_constants.py`:

```python
def test_barb_conventions():
    """Met Office symbology, a sane staff, and knot-calibrated increments."""
    assert constants.BARB_INCREMENTS == {"half": 5.0, "full": 10.0, "flag": 50.0}
    assert constants.BARB_GUTTER_WIDTH.endswith("%")
    assert constants.BARB_GUTTER_PAD > 0.0
    assert 0.0 < constants.BARB_STAFF_POSITION < 1.0
    assert constants.BARB_MIN_SEPARATION > 0.0
    assert constants.BARB_LENGTH > 0.0
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_barbs.py tests/test_constants.py -v`
Expected: test_barbs FAILS collecting — `ModuleNotFoundError: No module named 'tephpy.plotting.barbs'`; `test_barb_conventions` PASSES already (Step 1 added the constants).

- [ ] **Step 4: Implement the geometry module**

Create `src/tephpy/plotting/barbs.py`. This is the Task 2 form — Task 4 widens the imports, extends `__all__`, and appends the artist class:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The wind-barb gutter staff (spec §3.2).

Free geometry builders — bare numpy in diagram-native units, headlessly
testable (the ``isopleths.py``/``shading.py`` pattern) — plus
:class:`BarbStaff`, the zoom-aware artist ``plot_barbs`` installs in the
gutter axes. Each draw places every barb at the y where its level's isobar
meets the diagram's right edge (the printed-form staff convention), thins
the visible levels to the densest subset at least ``BARB_MIN_SEPARATION``
apart, and renders them through matplotlib's barbs machinery with the Met
Office increments (flag 50 kt, full 10 kt, half 5 kt, 5 kt binning).
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._constants import (
    KAPPA,
    KELVIN_ZERO,
    MA,
    P_REF,
)

__all__ = ["select_barbs", "staff_y"]

#: Temperature span (°C) sampled for the g(T) inversion. Deliberately far
#: wider than ``TEMPERATURE_DOMAIN``: an isobar's drawn polyline ends at
#: the domain edge, often inside the view, but its staff crossing is a
#: geometric anchor on the isobar's analytic extension — Poisson's
#: equation is smooth there, and a crossing beyond even this span means
#: the view is nowhere near that level (the barb drops as NaN).
_STAFF_TEMPERATURE_SPAN = (-200.0, 300.0)

#: Sample count for the shared g(T) inversion grid.
_STAFF_SAMPLES = 2048


def staff_y(pressure: npt.ArrayLike, x_edge: float) -> npt.NDArray[np.float64]:
    """Find the y where each pressure's isobar crosses a staff x.

    The tephigram x decomposes along an isobar into a level-independent
    part and a pressure offset: ``x = g(T) + c(p)`` with
    ``g(T) = MA·ln(T + KELVIN_ZERO) + T`` (strictly increasing) and
    ``c(p) = MA·KAPPA·ln(P_REF / p)``, from ``x = MA·ln(theta_K) + T``
    and Poisson's equation. Each level's crossing temperature solves
    ``g(T*) = x_edge - c(p)`` by inverse interpolation on one sampled
    ``g``, and the crossing y then comes from the real transforms at
    ``(T*, p)``.

    Parameters
    ----------
    pressure : ArrayLike
        Level pressures in hPa.
    x_edge : float
        The staff's x in tephigram data space — the diagram's right
        edge.

    Returns
    -------
    numpy.ndarray
        The float64 crossing ys in tephigram data space; NaN where the
        crossing temperature falls outside ``_STAFF_TEMPERATURE_SPAN``
        (or the pressure is not positive and finite).
    """
    p = np.atleast_1d(np.asarray(pressure, dtype=np.float64))
    grid = np.linspace(
        _STAFF_TEMPERATURE_SPAN[0], _STAFF_TEMPERATURE_SPAN[1], _STAFF_SAMPLES
    )
    g = MA * np.log(grid + KELVIN_ZERO) + grid
    with np.errstate(invalid="ignore", divide="ignore"):
        target = np.where(p > 0.0, x_edge - MA * KAPPA * np.log(P_REF / p), np.nan)
    t_star = np.interp(target, g, grid, left=np.nan, right=np.nan)
    theta = transforms.theta_from_pressure_temperature(p, t_star)
    _, y = transforms.xy_from_temperature_theta(t_star, theta)
    return np.asarray(y, dtype=np.float64)


def select_barbs(
    y: npt.ArrayLike, *, minimum_separation: float
) -> npt.NDArray[np.bool_]:
    """Thin barb positions to a minimum vertical separation.

    A greedy scan in input order — surface-first, so the surface barb
    always survives — keeps each position at least `minimum_separation`
    from the last kept one; non-finite positions are dropped. Positions
    and separation share one space (the staff uses display points), so
    zooming in spreads the ys and reveals more levels (spec §3.2).

    Parameters
    ----------
    y : ArrayLike
        Barb positions, ordered surface-first.
    minimum_separation : float
        The minimum spacing between kept positions.

    Returns
    -------
    numpy.ndarray
        Boolean keep-mask over `y`.
    """
    positions = np.atleast_1d(np.asarray(y, dtype=np.float64))
    keep = np.zeros(positions.shape, dtype=np.bool_)
    last = -np.inf
    for index, position in enumerate(positions):
        if not np.isfinite(position):
            continue
        if abs(position - last) >= minimum_separation or last == -np.inf:
            keep[index] = True
            last = position
    return keep
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_barbs.py tests/test_constants.py -v`
Expected: PASS (all tests)

- [ ] **Step 6: Lint and commit**

```bash
git add src/tephpy/_constants.py src/tephpy/plotting/barbs.py \
        tests/plotting/test_barbs.py tests/test_constants.py
pixi run --frozen lint
git commit -m "feat: add the barb conventions and pure staff geometry"
```

---

## Task 3: The shared side-panel divider and inside-out relayout

**Files:**
- Modify: `src/tephpy/plotting/axes.py`

**Interfaces:**
- Consumes: `mpl_toolkits.axes_grid1.axes_size` (`AxesX`, `Fixed`, `from_any`), `make_axes_locatable`, the Task 2 gutter constants.
- Produces: `TephigramAxes._side_divider`/`_barb_gutter` attributes, `_append_side_axes(*, width, pad, **kwargs) -> Axes`, and `_relayout_side_panels()` — Task 4's `plot_barbs` creates the gutter through exactly these. `annotate_indices` behaviour is unchanged from the outside (this is the spec §3.2 "reuse the divider" resolution).

This task is a refactor: its gate is the existing suite — including the
`test_indices_panel` **image comparison**, which proves the relayouted
single-panel geometry is pixel-identical to the `append_axes` layout it
replaces.

- [ ] **Step 1: Update the module docstring's layout paragraph**

Replace the "Side-of-axes layout contract" paragraph (which ends "No layout
code ships in this release.") with:

```
Side-of-axes layout contract (spec §10 item 7): panels beside the diagram
are appended with ``mpl_toolkits.axes_grid1``'s axes divider, which tracks
the equal-aspect box height — right side, inside-out: the wind-barb
gutter, then the indices panel. One divider is created per axes, cached,
and shared by every side-panel method; ``_relayout_side_panels`` rebuilds
the divider's horizontal stack and reassigns every locator whenever a
panel appears, so the inside-out order holds regardless of the order the
panel methods are called in (spec §3.2).
```

- [ ] **Step 2: Update the imports**

The `mpl_toolkits` import becomes:

```python
from mpl_toolkits.axes_grid1 import axes_size, make_axes_locatable
```

the `tephpy._constants` import block gains (alphabetical):

```python
BARB_GUTTER_PAD,
BARB_GUTTER_WIDTH,
```

and the `TYPE_CHECKING` block gains:

```python
from mpl_toolkits.axes_grid1.axes_divider import AxesDivider
```

- [ ] **Step 3: Add the panel slots and teardown to `clear()`**

The class-level attribute declarations become:

```python
tephigram_transform: TephigramTransform
_families: dict[str, IsoplethFamily]
_indices_panel: Axes | None
_barb_gutter: Axes | None
_side_divider: AxesDivider | None
```

and in `clear()`, replace the single-panel teardown (from `panel = getattr(...)`
through `self._indices_panel = None`) with — dedented one level here:

```python
removed = False
for name in ("_barb_gutter", "_indices_panel"):
    panel = getattr(self, name, None)
    if panel is not None:
        panel.remove()
        removed = True
if removed:
    # The stub demands a callable, but None resets the locator
    # (the documented matplotlib behaviour).
    self.set_axes_locator(None)  # type: ignore[arg-type]
self._indices_panel = None
self._barb_gutter = None
self._side_divider = None
```

(also update the docstring line "An indices panel is removed with the diagram
it annotated." to "Side panels — the barb gutter and the indices panel — are
removed with the diagram they annotated.")

- [ ] **Step 4: Insert the two layout helpers**

Immediately before `annotate_indices`, insert — dedented one level here:

```python
def _append_side_axes(
    self,
    *,
    width: str,
    pad: float,
    **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
) -> Axes:
    """Append one side panel through the shared, cached divider.

    The divider is created on first use and reused by every
    side-panel method — a second ``make_axes_locatable`` call would
    build a fresh divider and detach the earlier panel (spec §3.2).
    The caller stores the returned axes on its slot attribute and
    must call :meth:`_relayout_side_panels` afterwards.

    Parameters
    ----------
    width : str
        The panel width, as an ``axes_grid1`` size (e.g. ``"35%"``).
    pad : float
        The panel padding from the diagram, in inches.
    **kwargs : Any
        Passed through to the axes constructor (e.g. ``sharey=``).

    Returns
    -------
    matplotlib.axes.Axes
        The appended plain axes.
    """
    if self._side_divider is None:
        self._side_divider = make_axes_locatable(self)
    return cast(
        "Axes",
        self._side_divider.append_axes(
            "right", size=width, pad=pad, axes_class=Axes, **kwargs
        ),
    )


def _relayout_side_panels(self) -> None:
    """Rebuild the divider stack in the contracted inside-out order.

    ``append_axes`` stacks panels in call order; this rebuilds the
    divider's horizontal sizes as diagram, barb gutter, indices
    panel — skipping absent panels — and reassigns every locator, so
    the spec §3.2 order holds regardless of the order the panel
    methods were called in.
    """
    divider = self._side_divider
    if divider is None:
        return
    horizontal = [axes_size.AxesX(self)]
    slots: list[tuple[Axes, int]] = []
    panels: tuple[tuple[Axes | None, float, str], ...] = (
        (self._barb_gutter, BARB_GUTTER_PAD, BARB_GUTTER_WIDTH),
        (self._indices_panel, INDICES_PANEL_PAD, INDICES_PANEL_WIDTH),
    )
    for panel, pad, width in panels:
        if panel is None:
            continue
        horizontal.append(axes_size.Fixed(pad))
        horizontal.append(axes_size.from_any(width, fraction_ref=horizontal[0]))
        slots.append((panel, len(horizontal) - 1))
    divider.set_horizontal(horizontal)
    self.set_axes_locator(divider.new_locator(nx=0, ny=0))
    for panel, nx in slots:
        panel.set_axes_locator(divider.new_locator(nx=nx, ny=0))
```

- [ ] **Step 5: Refactor `annotate_indices` onto the shared divider**

Replace its creation branch:

```python
if self._indices_panel is None:
    divider = make_axes_locatable(self)
    self._indices_panel = divider.append_axes(
        "right",
        size=INDICES_PANEL_WIDTH,
        pad=INDICES_PANEL_PAD,
        axes_class=Axes,
    )
```

with:

```python
if self._indices_panel is None:
    self._indices_panel = self._append_side_axes(
        width=INDICES_PANEL_WIDTH, pad=INDICES_PANEL_PAD
    )
    self._relayout_side_panels()
```

and replace the docstring's ordering sentences ("Calling it again updates the
panel in place rather than stacking a second one. With ``axes_grid1``, append
order is position order: once the wind-barb gutter exists (a later release),
``plot_barbs`` must be called before this method for the contracted
inside-out order.") with:

```
Calling it again updates the panel in place rather than stacking a
second one, and the side-panel layout is rebuilt inside-out (barb
gutter, then this panel) whichever order the panel methods are
called in (spec §3.2).
```

- [ ] **Step 6: Run the regression gate**

Run: `pixi run --frozen pytest tests/plotting --mpl -v`
Expected: PASS — every existing test, **including the `test_indices_panel`
image comparison against the unchanged baseline**.

- [ ] **Step 7: Lint and commit**

```bash
git add src/tephpy/plotting/axes.py
pixi run --frozen lint
git commit -m "refactor: share one cached side-panel divider with inside-out relayout"
```

---

## Task 4: `BarbStaff` and `plot_barbs`

**Files:**
- Modify: `src/tephpy/plotting/barbs.py` (append the artist), `src/tephpy/plotting/axes.py` (the method)
- Test: `tests/plotting/test_barbs.py`

**Interfaces:**
- Consumes: Task 2's `staff_y`/`select_barbs` and constants, Task 3's `_append_side_axes`/`_relayout_side_panels`, `Sounding` (wind fields are pint quantities or `None`; pairing already validated at construction), `metpy.calc.wind_components`, `MissingDataError`.
- Produces: `BarbStaff(main_axes, pressure, u, v, *, x, minimum_separation, **kwargs)` with a `.barbs` property (the managed `matplotlib.quiver.Barbs`, `None` before first draw), and `TephigramAxes.plot_barbs(snd, *, x=None, **kwargs) -> BarbStaff`. Task 5's baselines and Task 12's changelog reference exactly these.

- [ ] **Step 1: Write the failing tests**

In `tests/plotting/test_barbs.py`, replace the import section (everything
between the `from __future__` line and the first test) with:

```python
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytest

from tephpy import Sounding, calc, transforms
from tephpy._constants import (
    BARB_MIN_SEPARATION,
    BARB_STAFF_POSITION,
)
from tephpy.exceptions import MissingDataError
from tephpy.plotting.barbs import BarbStaff, select_barbs, staff_y
from tephpy.plotting.isopleths import isobar_members

N = 30
PRESSURE = np.linspace(1000.0, 200.0, N)
TEMPERATURE = np.linspace(20.0, -55.0, N)
WIND_SPEED = np.linspace(5.0, 80.0, N)
WIND_DIRECTION = np.linspace(200.0, 320.0, N) % 360.0
UNITS = {
    "pressure": "hPa",
    "temperature": "degC",
    "wind_speed": "knots",
    "wind_direction": "degree",
}


def _sounding(**kwargs):
    """Build the module's reference wind-carrying sounding."""
    return Sounding(
        PRESSURE,
        TEMPERATURE,
        wind_speed=WIND_SPEED,
        wind_direction=WIND_DIRECTION,
        units=UNITS,
        **kwargs,
    )


def _indices():
    """Build a plausible SoundingIndices for the panel-layout tests."""
    values = {
        "cape": 250.0,
        "cin": -20.0,
        "lcl_pressure": 900.0,
        "lcl_temperature": 12.0,
        "lfc_pressure": 850.0,
        "lfc_temperature": 10.0,
        "el_pressure": 300.0,
        "el_temperature": -45.0,
        "theta_w": 15.0,
        "lifted_index": -2.0,
    }
    units = {
        "cape": "J/kg",
        "cin": "J/kg",
        "lcl_pressure": "hPa",
        "lcl_temperature": "degC",
        "lfc_pressure": "hPa",
        "lfc_temperature": "degC",
        "el_pressure": "hPa",
        "el_temperature": "degC",
        "theta_w": "degC",
        "lifted_index": "delta_degC",
    }
    return calc.SoundingIndices(units=units, **values)


@pytest.fixture
def tephigram_axes():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    yield ax
    plt.close(fig)
```

then append the behavioural tests after the existing pure tests:

```python
def test_plot_barbs_requires_wind(tephigram_axes):
    snd = Sounding(
        PRESSURE,
        TEMPERATURE,
        units={"pressure": "hPa", "temperature": "degC"},
    )
    with pytest.raises(MissingDataError, match="needs wind"):
        tephigram_axes.plot_barbs(snd)


def test_plot_barbs_returns_a_staff_in_the_gutter(tephigram_axes):
    staff = tephigram_axes.plot_barbs(_sounding())
    assert isinstance(staff, BarbStaff)
    gutter = tephigram_axes._barb_gutter
    assert staff.axes is gutter
    assert staff.barbs is None
    tephigram_axes.figure.canvas.draw()
    assert staff.barbs is not None
    assert len(staff.barbs.get_paths()) > 0


def test_plot_barbs_draws_the_selected_levels(tephigram_axes):
    """The drawn count equals the headless geometry pipeline's count."""
    staff = tephigram_axes.plot_barbs(_sounding())
    fig = tephigram_axes.figure
    fig.canvas.draw()
    gutter = tephigram_axes._barb_gutter
    y = staff_y(PRESSURE, tephigram_axes.get_xlim()[1])
    y0, y1 = sorted(tephigram_axes.get_ylim())
    visible = np.isfinite(y) & (y >= y0) & (y <= y1)
    offsets = np.column_stack([np.full(N, BARB_STAFF_POSITION), y])
    display = gutter.transData.transform(offsets)[:, 1]
    display[~visible] = np.nan
    expected = select_barbs(
        display, minimum_separation=BARB_MIN_SEPARATION * fig.dpi / 72.0
    )
    assert len(staff.barbs.get_paths()) == int(expected.sum())


def test_plot_barbs_zoom_changes_the_drawn_levels(tephigram_axes):
    staff = tephigram_axes.plot_barbs(_sounding())
    tephigram_axes.figure.canvas.draw()
    default_count = len(staff.barbs.get_paths())
    tephigram_axes.set_extent(((1000.0, -20.0), (850.0, 30.0)))
    tephigram_axes.figure.canvas.draw()
    zoomed_count = len(staff.barbs.get_paths())
    assert zoomed_count != default_count


def test_plot_barbs_shares_one_gutter_across_calls(tephigram_axes):
    first = tephigram_axes.plot_barbs(_sounding())
    second = tephigram_axes.plot_barbs(_sounding(), x=0.2)
    assert first.axes is second.axes
    tephigram_axes.figure.canvas.draw()
    assert first.barbs.get_offsets()[0, 0] == pytest.approx(BARB_STAFF_POSITION)
    assert second.barbs.get_offsets()[0, 0] == pytest.approx(0.2)


def test_plot_barbs_kwargs_pass_through(tephigram_axes):
    staff = tephigram_axes.plot_barbs(_sounding(), color="tab:blue")
    tephigram_axes.figure.canvas.draw()
    expected = mcolors.to_rgba("tab:blue")
    assert tuple(staff.barbs.get_facecolor()[0]) == pytest.approx(expected)


def test_plot_barbs_converts_wind_speed_units(tephigram_axes):
    """A m/s sounding feeds the knot-calibrated increments correctly."""
    snd = Sounding(
        PRESSURE,
        TEMPERATURE,
        wind_speed=np.full(N, 10.0),
        wind_direction=np.full(N, 360.0),
        units={**UNITS, "wind_speed": "m/s"},
    )
    staff = tephigram_axes.plot_barbs(snd)
    speed = np.hypot(staff._u, staff._v)
    np.testing.assert_allclose(speed, 10.0 / 0.514444, rtol=1e-4)


def test_plot_barbs_gutter_tracks_the_view(tephigram_axes):
    tephigram_axes.plot_barbs(_sounding())
    tephigram_axes.set_extent(((1000.0, -20.0), (850.0, 30.0)))
    assert tephigram_axes._barb_gutter.get_ylim() == tephigram_axes.get_ylim()


def _bounds(axes):
    return axes.get_position().bounds


def test_side_panels_land_inside_out_barbs_first(tephigram_axes):
    snd = _sounding()
    tephigram_axes.plot_barbs(snd)
    panel = tephigram_axes.annotate_indices(_indices())
    tephigram_axes.figure.canvas.draw()
    main, gutter = _bounds(tephigram_axes), _bounds(tephigram_axes._barb_gutter)
    assert main[0] < gutter[0] < _bounds(panel)[0]


def test_side_panels_land_inside_out_indices_first(tephigram_axes):
    """Call order is irrelevant: the layout is rebuilt inside-out (§3.2)."""
    snd = _sounding()
    panel = tephigram_axes.annotate_indices(_indices())
    tephigram_axes.plot_barbs(snd)
    tephigram_axes.figure.canvas.draw()
    main, gutter = _bounds(tephigram_axes), _bounds(tephigram_axes._barb_gutter)
    assert main[0] < gutter[0] < _bounds(panel)[0]


def test_side_panels_share_one_divider(tephigram_axes):
    snd = _sounding()
    tephigram_axes.annotate_indices(_indices())
    divider = tephigram_axes._side_divider
    tephigram_axes.plot_barbs(snd)
    assert tephigram_axes._side_divider is divider


def test_clear_removes_the_gutter_and_restores_the_slot(tephigram_axes):
    fig = tephigram_axes.figure
    fig.canvas.draw()
    full = _bounds(tephigram_axes)
    tephigram_axes.plot_barbs(_sounding())
    fig.canvas.draw()
    assert _bounds(tephigram_axes)[2] < full[2]
    tephigram_axes.clear()
    fig.canvas.draw()
    assert tephigram_axes._barb_gutter is None
    assert tephigram_axes._side_divider is None
    assert _bounds(tephigram_axes) == pytest.approx(full)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_barbs.py -v`
Expected: FAIL collecting — `ImportError: cannot import name 'BarbStaff'`

- [ ] **Step 3: Append the artist to `plotting/barbs.py`**

Replace the module's import-and-`__all__` head (from `import numpy as np`
through the `__all__` line) with:

```python
from typing import TYPE_CHECKING, Any, cast

from matplotlib import artist as martist
from matplotlib.quiver import Barbs
import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._constants import (
    BARB_INCREMENTS,
    BARB_LENGTH,
    BARB_STAFF_POSITION,
    KAPPA,
    KELVIN_ZERO,
    MA,
    P_REF,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure

__all__ = ["BarbStaff", "select_barbs", "staff_y"]
```

and append the class at the end of the module:

```python
class BarbStaff(martist.Artist):
    """One sounding's wind barbs on the gutter staff (spec §3.2).

    A zoom-aware artist (the ``IsoplethFamily`` refresh pattern) that
    manages a :class:`matplotlib.quiver.Barbs` child. Each draw reads the
    main axes' view, places every level at its isobar's staff crossing
    (:func:`staff_y`), masks the levels outside the view or closer than
    the minimum separation (:func:`select_barbs`), and hands the child
    the same-length masked arrays — matplotlib's barbs machinery skips
    masked points, so the member count never changes.

    Parameters
    ----------
    main_axes : matplotlib.axes.Axes
        The tephigram axes the staff annotates.
    pressure : numpy.ndarray
        Level pressures in hPa, surface-first.
    u, v : numpy.ndarray
        Wind components in knots (the barb-increment units).
    x : float
        The staff position as a fraction across the gutter.
    minimum_separation : float
        Minimum vertical separation between drawn barbs, in points.
    **kwargs : Any
        Passed through to :class:`matplotlib.quiver.Barbs`, over the
        ``_constants`` conventions (increments, rounding, length).
    """

    def __init__(  # noqa: PLR0913 -- the staff's full geometry contract
        self,
        main_axes: Axes,
        pressure: npt.NDArray[np.float64],
        u: npt.NDArray[np.float64],
        v: npt.NDArray[np.float64],
        *,
        x: float = BARB_STAFF_POSITION,
        minimum_separation: float,
        **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
    ) -> None:
        """Wire the staff and its managed barbs child.

        Parameters
        ----------
        main_axes : matplotlib.axes.Axes
            The tephigram axes the staff annotates.
        pressure : numpy.ndarray
            Level pressures in hPa, surface-first.
        u, v : numpy.ndarray
            Wind components in knots.
        x : float
            The staff position as a fraction across the gutter.
        minimum_separation : float
            Minimum vertical separation between drawn barbs, in points.
        **kwargs : Any
            Passed through to :class:`matplotlib.quiver.Barbs`.
        """
        super().__init__()
        self._main_axes = main_axes
        self._pressure = np.asarray(pressure, dtype=np.float64)
        self._u = np.asarray(u, dtype=np.float64)
        self._v = np.asarray(v, dtype=np.float64)
        self._x = float(x)
        self._minimum_separation = float(minimum_separation)
        self._kwargs = {
            "barb_increments": dict(BARB_INCREMENTS),
            "rounding": True,
            "length": BARB_LENGTH,
            **kwargs,
        }
        self._barbs: Barbs | None = None

    @property
    def barbs(self) -> Barbs | None:
        """The managed matplotlib barbs collection.

        Returns
        -------
        matplotlib.quiver.Barbs or None
            The child collection, or ``None`` before the first draw.
        """
        return self._barbs

    def set_figure(self, fig: Figure | SubFigure) -> None:
        """Propagate the owning figure to the managed child.

        Parameters
        ----------
        fig : matplotlib.figure.Figure or matplotlib.figure.SubFigure
            The figure the staff belongs to.
        """
        super().set_figure(fig)
        if self._barbs is not None:
            self._barbs.set_figure(fig)

    @martist.allow_rasterization  # type: ignore[untyped-decorator]
    def draw(self, renderer: RendererBase) -> None:
        """Draw the barbs visible in the current view.

        Parameters
        ----------
        renderer : matplotlib.backend_bases.RendererBase
            The active renderer.
        """
        if not self.get_visible():
            return
        figure = self.get_figure(root=True)
        if self.axes is None or figure is None or self._pressure.size == 0:
            return
        gutter = cast("Axes", self.axes)
        main = self._main_axes
        y = staff_y(self._pressure, main.get_xlim()[1])
        y0, y1 = sorted(main.get_ylim())
        candidate = (
            np.isfinite(y)
            & (y >= y0)
            & (y <= y1)
            & np.isfinite(self._u)
            & np.isfinite(self._v)
        )
        keep = np.zeros(y.shape, dtype=np.bool_)
        indices = np.flatnonzero(candidate)
        if indices.size:
            offsets = np.column_stack([np.full(indices.size, self._x), y[indices]])
            separation = self._minimum_separation * figure.dpi / 72.0
            display = gutter.transData.transform(offsets)[:, 1]
            keep[indices] = select_barbs(display, minimum_separation=separation)
        if self._barbs is None:
            self._barbs = Barbs(
                gutter,
                np.full(y.shape, self._x),
                np.where(keep, y, 0.0),
                np.ma.masked_array(self._u, mask=~keep),
                np.ma.masked_array(self._v, mask=~keep),
                **self._kwargs,
            )
            self._barbs.set_figure(figure)
        else:
            self._barbs.set_offsets(
                np.column_stack([np.full(y.shape, self._x), np.where(keep, y, 0.0)])
            )
            self._barbs.set_UVC(
                np.ma.masked_array(self._u, mask=~keep),
                np.ma.masked_array(self._v, mask=~keep),
            )
        renderer.open_group("barb-staff", gid=self.get_gid())
        self._barbs.set_clip_box(gutter.bbox)
        self._barbs.draw(renderer)
        renderer.close_group("barb-staff")
        self.stale = False
```

- [ ] **Step 4: Add `plot_barbs` to `TephigramAxes`**

In `src/tephpy/plotting/axes.py`: the `tephpy._constants` import block gains
(alphabetical):

```python
BARB_MIN_SEPARATION,
BARB_STAFF_POSITION,
```

add the two runtime imports (alphabetical among the `tephpy` imports):

```python
from tephpy.exceptions import MissingDataError
from tephpy.plotting.barbs import BarbStaff
```

and insert the method between `_relayout_side_panels` and `annotate_indices` —
dedented one level here:

```python
def plot_barbs(
    self,
    snd: Sounding,
    *,
    x: float | None = None,
    **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
) -> BarbStaff:
    """Plot the sounding's wind barbs on the gutter staff (spec §3.2).

    The barbs draw on a right-hand gutter appended with the shared
    divider, each level at the y where its isobar meets the
    diagram's right edge (the printed-form staff convention),
    thinned per draw to a minimum vertical separation — zooming in
    reveals more levels. Met Office symbology: flag 50 kt, full barb
    10 kt, half barb 5 kt, speeds rounded to 5 kt bins; calm levels
    render as matplotlib's small circle. Each call draws one staff:
    overlay soundings by calling again with another `x` and a
    colour.

    Parameters
    ----------
    snd : Sounding
        The sounding to plot; must carry wind.
    x : float, optional
        The staff position as a fraction across the gutter
        (default ``BARB_STAFF_POSITION``).
    **kwargs : Any
        Passed through to :class:`matplotlib.quiver.Barbs`, over
        the ``_constants`` conventions (increments, rounding,
        length).

    Returns
    -------
    BarbStaff
        The zoom-aware staff artist; its ``barbs`` property is the
        underlying matplotlib collection.

    Raises
    ------
    MissingDataError
        If the sounding has no wind (spec §6).
    """
    if snd.wind_speed is None or snd.wind_direction is None:
        msg = "plot_barbs() needs wind: this sounding has none (spec §3.4)"
        raise MissingDataError(msg)
    # Function-local so `import tephpy` stays light (spec §10 item 10).
    from metpy.calc import wind_components  # noqa: PLC0415

    u, v = wind_components(snd.wind_speed, snd.wind_direction)
    if self._barb_gutter is None:
        gutter = self._append_side_axes(
            width=BARB_GUTTER_WIDTH, pad=BARB_GUTTER_PAD, sharey=self
        )
        gutter.set_xlim(0.0, 1.0)
        gutter.set_axis_off()
        self._barb_gutter = gutter
        self._relayout_side_panels()
    staff = BarbStaff(
        self,
        snd.pressure.m_as("hPa"),
        np.asarray(u.m_as("knots"), dtype=np.float64),
        np.asarray(v.m_as("knots"), dtype=np.float64),
        x=BARB_STAFF_POSITION if x is None else float(x),
        minimum_separation=BARB_MIN_SEPARATION,
        **kwargs,
    )
    self._barb_gutter.add_artist(staff)
    return staff
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_barbs.py -v`
Expected: PASS (all tests — pure and behavioural)

- [ ] **Step 6: Lint and commit**

```bash
git add src/tephpy/plotting/barbs.py src/tephpy/plotting/axes.py \
        tests/plotting/test_barbs.py
pixi run --frozen lint
git commit -m "feat: draw wind barbs on a zoom-aware gutter staff"
```

---

## Task 5: Barb image baselines

**Files:**
- Test: `tests/plotting/test_images.py`
- Create: `tests/baseline/test_barbs_staff.png` (~54 KB), `tests/baseline/test_barbs_with_indices_panel.png` (~70 KB) — generated, not hand-made

**Interfaces:**
- Consumes: Task 4's `plot_barbs`, Plan 5's `annotate_indices` and `calc.indices`.
- Produces: the two §7 barb baselines; Plan 7's composed §4 figure will reuse `_windy_sounding`.

- [ ] **Step 1: Add the image tests**

Append to `tests/plotting/test_images.py`:

```python
def _windy_sounding():
    """Build a sounding whose wind sweeps the barb glyph vocabulary."""
    return Sounding(
        units.Quantity(
            np.array([1000.0, 950.0, 900.0, 850.0, 700.0, 500.0, 300.0, 200.0]), "hPa"
        ),
        units.Quantity(
            np.array([26.0, 24.0, 23.0, 21.0, 10.0, -12.0, -40.0, -55.0]), "degC"
        ),
        dewpoint=units.Quantity(
            np.array([20.0, 17.0, 14.0, 10.0, 2.0, -15.0, -45.0, -60.0]), "degC"
        ),
        wind_speed=units.Quantity(
            np.array([2.0, 7.0, 15.0, 25.0, 40.0, 55.0, 75.0, 105.0]), "knots"
        ),
        wind_direction=units.Quantity(
            np.array([180.0, 200.0, 220.0, 240.0, 260.0, 280.0, 300.0, 320.0]),
            "degree",
        ),
    )


@pytest.mark.mpl_image_compare
def test_barbs_staff():
    """The wind-barb gutter staff beside the diagram (spec §3.2)."""
    fig, ax = _tephigram_figure()
    snd = _windy_sounding()
    ax.plot_sounding(snd)
    ax.plot_barbs(snd)
    return fig


@pytest.mark.mpl_image_compare
def test_barbs_with_indices_panel():
    """Both side panels composed inside-out: gutter, then indices panel."""
    fig, ax = plt.subplots(figsize=(5.0, 3.5), subplot_kw={"projection": "tephigram"})
    ax.set_extent(((1050.0, -30.0), (200.0, 40.0)))
    snd = _windy_sounding()
    ax.plot_sounding(snd)
    ax.plot_barbs(snd)
    ax.annotate_indices(calc.indices(snd))
    return fig
```

- [ ] **Step 2: Run to verify they fail for the right reason**

Run: `pixi run --frozen pytest tests/plotting/test_images.py -v --mpl`
Expected: the two new tests FAIL with "Image file not found for comparison test" (no baseline yet); every existing image test PASSES.

- [ ] **Step 3: Generate the baselines**

```bash
pixi run --frozen baselines
git status --short tests/baseline/
```

Expected: exactly two untracked files (`test_barbs_staff.png`,
`test_barbs_with_indices_panel.png`); **no existing baseline modified**
(regeneration is bit-identical for the eleven current images — verified
2026-07-27).

- [ ] **Step 4: Inspect the two rendered baselines**

Open both PNGs. Expected: `test_barbs_staff` — the sounding with a barb
staff in a right-hand gutter, glyphs sweeping calm-circle → half/full barbs
→ a flag at the 105 kt level, all inside the gutter; `test_barbs_with_indices_panel` —
gutter **between** the diagram and the indices panel (the inside-out
contract), no overlap.

- [ ] **Step 5: Run the image tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_images.py -v --mpl`
Expected: PASS (13 image comparisons)

- [ ] **Step 6: Lint and commit**

```bash
git add tests/plotting/test_images.py tests/baseline/test_barbs_staff.png \
        tests/baseline/test_barbs_with_indices_panel.png
pixi run --frozen lint
git commit -m "test: add the wind-barb image baselines"
```

---

## Task 6: The `io` scaffolding and shared helpers

**Files:**
- Create: `src/tephpy/io/__init__.py` (minimal; Task 10 completes it), `src/tephpy/io/_util.py`, `tests/io/__init__.py`
- Modify: `pyproject.toml` (one per-file-ignore)
- Test: `tests/io/test_util.py`

**Interfaces:**
- Consumes: nothing beyond stdlib/numpy.
- Produces: `coerce_time(time) -> datetime` (datetime|ISO-string in, UTC out; `TypeError`/`ValueError` for misuse) and `strictly_decreasing(pressure) -> NDArray[bool_]` (running-minimum keep-mask, first occurrence wins, non-finite drops) — both readers (Tasks 8–9) share exactly these.

- [ ] **Step 1: Add the ruff per-file-ignore**

In `pyproject.toml` under `[tool.ruff.lint.per-file-ignores]`, after the
`generate_tephi_*` entry:

```toml
# The tests tree mirrors the package (spec §8.5): tests/io shadows nothing
# importable — it is reached as tests.io.
"tests/io/__init__.py" = ["A005"]
```

(Without it, ruff A005 flags `tests/io` as shadowing stdlib `io`;
`src/tephpy/io` is exempt because the `src` root gives it the full dotted
path `tephpy.io`.)

- [ ] **Step 2: Create the packages**

`src/tephpy/io/__init__.py` (Task 10 adds the eager re-export):

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Data ingest readers returning :class:`~tephpy.sounding.Sounding` (spec §3.4).

Light readers over the University of Wyoming sounding archive
(:mod:`tephpy.io.wyoming`) and NCEI's Integrated Global Radiosonde Archive
version 2 (:mod:`tephpy.io.igra`). Reader failures raise
:class:`~tephpy.exceptions.TephpyIOError`; the returned soundings pass the
ordinary ingest validation (spec §6). TEMP/BUFR decoding is out of scope —
the documentation points at eccodes.
"""

from __future__ import annotations
```

`tests/io/__init__.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Unit tests for the tephpy.io subpackage."""

from __future__ import annotations
```

- [ ] **Step 3: Write the failing tests**

Create `tests/io/test_util.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the shared ingest helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import numpy as np
import pytest

from tephpy.io._util import coerce_time, strictly_decreasing


def test_coerce_time_naive_string_reads_as_utc():
    assert coerce_time("2026-07-21 12:00") == datetime(2026, 7, 21, 12, tzinfo=UTC)


def test_coerce_time_aware_input_converts_to_utc():
    plus_two = timezone(timedelta(hours=2))
    when = coerce_time(datetime(2026, 7, 21, 14, tzinfo=plus_two))
    assert when == datetime(2026, 7, 21, 12, tzinfo=UTC)
    assert when.tzinfo == UTC


def test_coerce_time_rejects_non_iso_string():
    with pytest.raises(ValueError, match="Invalid isoformat"):
        coerce_time("21/07/2026 12Z")


def test_coerce_time_rejects_wrong_type():
    with pytest.raises(TypeError, match="datetime or an ISO 8601 string"):
        coerce_time(20260721)


def test_strictly_decreasing_passes_monotonic_input():
    pressure = np.array([1000.0, 850.0, 700.0])
    np.testing.assert_array_equal(strictly_decreasing(pressure), [True, True, True])


def test_strictly_decreasing_drops_duplicates_keeping_first():
    pressure = np.array([1000.0, 1000.0, 850.0, 850.0, 700.0])
    np.testing.assert_array_equal(
        strictly_decreasing(pressure), [True, False, True, False, True]
    )


def test_strictly_decreasing_drops_rises_against_the_running_minimum():
    pressure = np.array([1000.0, 900.0, 950.0, 850.0])
    np.testing.assert_array_equal(
        strictly_decreasing(pressure), [True, True, False, True]
    )


def test_strictly_decreasing_drops_non_finite_rows():
    pressure = np.array([np.nan, 1000.0, np.nan, 850.0])
    np.testing.assert_array_equal(
        strictly_decreasing(pressure), [False, True, False, True]
    )
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/io -v`
Expected: FAIL collecting — `ModuleNotFoundError: No module named 'tephpy.io._util'`

- [ ] **Step 5: Implement the helpers**

Create `src/tephpy/io/_util.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Helpers shared by the ingest readers (spec §3.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import numpy.typing as npt

__all__ = ["coerce_time", "strictly_decreasing"]


def coerce_time(time: datetime | str) -> datetime:
    """Read a launch time as a UTC datetime.

    Parameters
    ----------
    time : datetime.datetime or str
        The nominal launch time; a string is read with
        :meth:`datetime.datetime.fromisoformat`.

    Returns
    -------
    datetime.datetime
        The UTC time: naive input read as UTC, aware input converted.

    Raises
    ------
    TypeError
        If `time` is neither a datetime nor a string.
    ValueError
        If a `time` string is not ISO 8601.
    """
    # Typed `object`: the annotation says datetime or str, but the boundary
    # also rejects the rest at runtime (the Sounding._normalize_time idiom).
    value: object = time
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        msg = f"time must be a datetime or an ISO 8601 string, got {type(value)!r}"
        raise TypeError(msg)
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def strictly_decreasing(pressure: npt.NDArray[np.float64]) -> npt.NDArray[np.bool_]:
    """Keep the rows whose pressure strictly undercuts the running minimum.

    Parameters
    ----------
    pressure : numpy.ndarray
        Row pressures in file order (surface-first).

    Returns
    -------
    numpy.ndarray
        Boolean keep-mask: the first occurrence wins; non-finite
        pressures drop.
    """
    with np.errstate(invalid="ignore"):
        floor = np.minimum.accumulate(np.where(np.isfinite(pressure), pressure, np.inf))
    keep: npt.NDArray[np.bool_] = np.empty(pressure.shape, dtype=np.bool_)
    keep[0:1] = np.isfinite(pressure[0:1])
    keep[1:] = np.isfinite(pressure[1:]) & (pressure[1:] < floor[:-1])
    return keep
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/io -v`
Expected: PASS (all tests)

- [ ] **Step 7: Lint and commit**

```bash
git add src/tephpy/io tests/io pyproject.toml
pixi run --frozen lint
git commit -m "feat: scaffold tephpy.io with the shared reader helpers"
```

---

## Task 7: The recorded fixtures and their provenance

**Files:**
- Create: `tests/fixtures/generate_io_fixtures.py`, `tests/fixtures/io/README.md`, `tests/fixtures/io/wyoming-03808-2026-07-21-12Z.csv`, `tests/fixtures/io/UKM00003808-data-trimmed.txt`
- Modify: `.pre-commit-config.yaml`

Network is needed **once**, to run the generator (both archives are stable
for a past date, so a re-capture reproduces the same ascent). If the
execution environment is offline, run the generator on any machine with
network and copy `tests/fixtures/io/` in unchanged — then update the capture
dates in the README.

**Interfaces:**
- Consumes: the live archive endpoints recorded in Global Constraints.
- Produces: the two recorded fixtures Tasks 8–9's tests parse — one physical launch (Camborne, nominal 2026-07-21 12Z, released 11:17 UTC) captured from **both** archives, so the readers cross-validate. Surface record for both: 1019 hPa, ~19.6–19.7 °C, dewpoint ~15.9–16.0 °C, wind 360° at 4.1 m/s.

- [ ] **Step 1: Exclude the fixtures from the whitespace hooks**

IGRA records legitimately end with a trailing space, and both captures must
stay byte-faithful. In `.pre-commit-config.yaml`:

```yaml
      - id: end-of-file-fixer
        exclude: '\.svg$|^tests/fixtures/io/'
      - id: mixed-line-ending
        exclude: '^tests/fixtures/io/'
      - id: no-commit-to-branch
      - id: trailing-whitespace
        # The io fixtures are byte-faithful archive captures (their records
        # legitimately end with a trailing space).
        exclude: '^tests/fixtures/io/'
```

- [ ] **Step 2: Write the capture script**

Create `tests/fixtures/generate_io_fixtures.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Capture and trim the ingest-reader fixtures (one-shot; not run in CI).

Run with network access from the repo root:

    pixi run python tests/fixtures/generate_io_fixtures.py

Writes into ``tests/fixtures/io/``:

- ``wyoming-03808-2026-07-21-12Z.csv`` — the University of Wyoming
  ``TEXT:CSV`` body for Camborne (WMO 03808) at 2026-07-21 12Z, thinned to
  every 40th data row (plus the first and last) so the fixture stays a few
  KB; the kept rows are byte-faithful.
- ``UKM00003808-data-trimmed.txt`` — the 2026-07-21 00Z and 12Z ascents
  from NCEI's IGRA v2 year-to-date file for Camborne (UKM00003808),
  byte-faithful whole blocks (header + declared level count).

Both captures record the same physical ascent (2026-07-21 12Z, released
11:17 UTC), so the two readers cross-validate. Provenance — source URLs,
capture date, method, attribution — is kept in ``io/README.md`` beside the
fixtures and must be updated when this script is re-run.
"""

from __future__ import annotations

import io
from pathlib import Path
from urllib.request import urlopen
import zipfile

WYOMING = (
    "https://weather.uwyo.edu/wsgi/sounding"
    "?datetime=2026-07-21%2012:00:00&id=03808&type=TEXT:CSV"
)
IGRA = (
    "https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/"
    "access/data-y2d/UKM00003808-data-beg2026.txt.zip"
)
KEPT_HEADERS = (" 2026 07 21 00 ", " 2026 07 21 12 ")
STRIDE = 40

out = Path(__file__).parent / "io"
out.mkdir(exist_ok=True)

with urlopen(WYOMING, timeout=60) as response:
    rows = response.read().decode("utf-8").splitlines()
kept = [rows[0], *rows[1::STRIDE]]
if rows[-1] != kept[-1]:
    kept.append(rows[-1])
(out / "wyoming-03808-2026-07-21-12Z.csv").write_text("\n".join(kept) + "\n")
print(f"wyoming: kept {len(kept) - 1} of {len(rows) - 1} data rows")

with urlopen(IGRA, timeout=120) as response:
    payload = response.read()
with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
    (member,) = bundle.namelist()
    lines = bundle.read(member).decode("ascii").splitlines()
blocks: list[str] = []
index = 0
while index < len(lines):
    line = lines[index]
    if line.startswith("#") and any(stamp in line for stamp in KEPT_HEADERS):
        levels = int(line[32:36])
        blocks.extend(lines[index : index + 1 + levels])
        index += 1 + levels
    else:
        index += 1
(out / "UKM00003808-data-trimmed.txt").write_text("\n".join(blocks) + "\n")
ascents = sum(1 for block in blocks if block.startswith("#"))
print(f"igra: kept {ascents} ascents, {len(blocks)} lines")
```

- [ ] **Step 3: Run it and sanity-check the captures**

```bash
pixi run --frozen python tests/fixtures/generate_io_fixtures.py
head -2 tests/fixtures/io/wyoming-03808-2026-07-21-12Z.csv
grep -c '^#' tests/fixtures/io/UKM00003808-data-trimmed.txt
```

Expected: `wyoming: kept 61 of 2395 data rows` and `igra: kept 2 ascents, 559
lines`; the CSV header starts `time,longitude,latitude,pressure_hPa,...` with
first data row `2026-07-21 11:17:10, -5.3275,50.2184,1019.2,   87, 19.7, 16.0,...`;
the IGRA grep prints `2`.

- [ ] **Step 4: Write the provenance note**

Create `tests/fixtures/io/README.md`:

```markdown
# Ingest-Reader Fixtures

Recorded captures for the `tephpy.io` tests — no live network in CI
(spec §7); provenance recorded per spec §10 item 13. Regenerate both files
with `pixi run python tests/fixtures/generate_io_fixtures.py` (network
required) and update the capture dates below.

Both fixtures record the **same physical ascent** — Camborne, nominal
2026-07-21 12Z, released 11:17 UTC — so the two readers cross-validate
against each other in the tests.

## wyoming-03808-2026-07-21-12Z.csv

- **Source:** <https://weather.uwyo.edu/wsgi/sounding?datetime=2026-07-21%2012:00:00&id=03808&type=TEXT:CSV>
- **Captured:** 2026-07-27, thinned to every 40th data row plus the first
  and last (kept rows are byte-faithful; the header row is complete).
- **Attribution:** sounding data courtesy of the University of Wyoming,
  College of Engineering, Department of Atmospheric Science
  (<https://weather.uwyo.edu/upperair/sounding.shtml>). One recorded
  ascent, used as test facts.

## UKM00003808-data-trimmed.txt

- **Source:** <https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/access/data-y2d/UKM00003808-data-beg2026.txt.zip>
- **Captured:** 2026-07-27; the 2026-07-21 00Z and 12Z ascents as whole
  byte-faithful blocks (header record plus its declared level count).
- **Attribution:** NOAA/NCEI Integrated Global Radiosonde Archive (IGRA)
  version 2, a U.S. Government work in the public domain. Durre, I.,
  X. Yin, R. S. Vose, S. Applequist, and J. Arnfield (2016):
  doi:10.7289/V5X63K0Q.
```

- [ ] **Step 5: Lint and commit**

```bash
git add .pre-commit-config.yaml tests/fixtures/generate_io_fixtures.py tests/fixtures/io
pixi run --frozen lint
git commit -m "test: record the Wyoming and IGRA reader fixtures with provenance"
```

---

## Task 8: The Wyoming reader

**Files:**
- Modify: `src/tephpy/_constants.py`
- Create: `src/tephpy/io/wyoming.py`
- Test: `tests/io/test_wyoming.py`

**Interfaces:**
- Consumes: Task 6's `coerce_time`/`strictly_decreasing`, Task 7's CSV fixture, Task 1's `TephpyIOError`, `Sounding`.
- Produces: `wyoming.fetch(station, time, *, timeout=None) -> Sounding`, with `_request(url, timeout)` as the monkeypatchable transport seam and `_parse(text, *, station, time)` the pure parser. Task 10 re-exports the module; Task 12's changelog references `fetch`.

- [ ] **Step 1: Add the Wyoming conventions**

In `src/tephpy/_constants.py`, after the `BARB_LENGTH` entry:

```python
#: University of Wyoming sounding request (spec §3.4): the post-2024 wsgi
#: interface's machine-readable form — ``type=TEXT:CSV`` returns bare,
#: self-describing CSV (verified 2026-07-27; the classic ``cgi-bin``
#: TEXT:LIST endpoint now 404s).
WYOMING_URL: Final[str] = (
    "https://weather.uwyo.edu/wsgi/sounding?datetime={datetime}&id={station}"
    "&type=TEXT:CSV"
)

#: Default timeout for a University of Wyoming request, in seconds.
WYOMING_TIMEOUT: Final[float] = 30.0
```

- [ ] **Step 2: Write the failing tests**

Create `tests/io/test_wyoming.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the University of Wyoming reader (spec §3.4, §7).

The recorded fixture is a thinned but byte-faithful ``TEXT:CSV`` capture
(see ``tests/fixtures/io/README.md``); no test touches the network — the
transport seam (``_request``) is monkeypatched where ``fetch`` itself is
under test.
"""

from __future__ import annotations

from datetime import UTC, datetime
import io as stdlib_io
from pathlib import Path
import urllib.error
import urllib.request

import numpy as np
import pytest

from tephpy.exceptions import TephpyIOError
from tephpy.io import wyoming

FIXTURE = (
    Path(__file__).parents[1] / "fixtures" / "io" / "wyoming-03808-2026-07-21-12Z.csv"
)
WHEN = datetime(2026, 7, 21, 12, tzinfo=UTC)

HEADER = (
    "time,longitude,latitude,pressure_hPa,geopotential height_m,"
    "temperature_C,dew point temperature_C,ice point temperature_C,"
    "relative humidity_%,humidity wrt ice_%,mixing ratio_g/kg,"
    "wind direction_degree,wind speed_m/s"
)


def _parse_fixture():
    return wyoming._parse(FIXTURE.read_text(), station="03808", time=WHEN)


def test_parse_carries_the_fixture_profile():
    snd = _parse_fixture()
    assert snd.pressure.size == 61
    assert snd.pressure[0].m_as("hPa") == pytest.approx(1019.2)
    assert snd.temperature[0].m_as("degC") == pytest.approx(19.7)
    assert snd.dewpoint[0].m_as("degC") == pytest.approx(16.0)
    assert snd.wind_direction[0].m_as("degree") == pytest.approx(360.0)
    assert snd.wind_speed[0].m_as("m/s") == pytest.approx(4.1)


def test_parse_derives_the_label_from_metadata():
    assert _parse_fixture().label == "03808 2026-07-21 12Z"


def test_parse_missing_column_raises():
    text = "time,latitude\n2026-07-21 11:17:10,50.2184\n"
    with pytest.raises(TephpyIOError, match=r"column.*pressure_hPa"):
        wyoming._parse(text, station="03808", time=WHEN)


def test_parse_empty_response_raises():
    with pytest.raises(TephpyIOError, match="empty response"):
        wyoming._parse("", station="03808", time=WHEN)


def test_parse_non_numeric_cell_raises():
    text = f"{HEADER}\n2026,1,2,oops,4,5,6,7,8,9,10,11,12\n"
    with pytest.raises(TephpyIOError, match="'oops' is not numeric"):
        wyoming._parse(text, station="03808", time=WHEN)


def test_parse_blank_cells_read_as_nan_gaps():
    rows = [
        "2026,1,2,1000.0,4,15.0,,7,8,9,10,360,5.0",
        "2026,1,2,900.0,4,10.0,4.0,7,8,9,10,,",
    ]
    snd = wyoming._parse("\n".join([HEADER, *rows]), station=None, time=None)
    assert np.isnan(snd.dewpoint[0].magnitude)
    assert np.isnan(snd.wind_speed[1].magnitude)
    assert np.isnan(snd.wind_direction[1].magnitude)


def test_parse_all_nan_optional_fields_are_absent():
    rows = [
        "2026,1,2,1000.0,4,15.0,,7,8,9,10,,",
        "2026,1,2,900.0,4,10.0,,7,8,9,10,,",
    ]
    snd = wyoming._parse("\n".join([HEADER, *rows]), station=None, time=None)
    assert snd.dewpoint is None
    assert snd.wind_speed is None
    assert snd.wind_direction is None


def test_parse_drops_non_decreasing_pressure_rows():
    rows = [
        "2026,1,2,1000.0,4,15.0,5.0,7,8,9,10,360,5.0",
        "2026,1,2,1000.0,4,14.0,5.0,7,8,9,10,350,6.0",
        "2026,1,2,900.0,4,10.0,4.0,7,8,9,10,340,7.0",
    ]
    snd = wyoming._parse("\n".join([HEADER, *rows]), station=None, time=None)
    np.testing.assert_array_equal(snd.pressure.m_as("hPa"), [1000.0, 900.0])
    np.testing.assert_array_equal(snd.temperature.m_as("degC"), [15.0, 10.0])


def test_fetch_builds_the_documented_url(monkeypatch):
    seen = {}

    def fake_request(url, timeout):
        seen["url"], seen["timeout"] = url, timeout
        return FIXTURE.read_text()

    monkeypatch.setattr(wyoming, "_request", fake_request)
    snd = wyoming.fetch("03808", "2026-07-21 12:00")
    assert seen["url"] == (
        "https://weather.uwyo.edu/wsgi/sounding"
        "?datetime=2026-07-21%2012%3A00%3A00&id=03808&type=TEXT:CSV"
    )
    assert seen["timeout"] == 30.0
    assert snd.label == "03808 2026-07-21 12Z"


def test_fetch_timeout_argument_overrides_the_default(monkeypatch):
    seen = {}

    def fake_request(_url, timeout):
        seen["timeout"] = timeout
        return FIXTURE.read_text()

    monkeypatch.setattr(wyoming, "_request", fake_request)
    wyoming.fetch("03808", WHEN, timeout=5.0)
    assert seen["timeout"] == 5.0


def test_fetch_rejects_a_non_iso_time_string():
    with pytest.raises(ValueError, match="Invalid isoformat"):
        wyoming.fetch("03808", "21/07/2026")


def test_fetch_maps_http_errors_with_the_archive_reply(monkeypatch):
    def fake_urlopen(url, **_kwargs):
        raise urllib.error.HTTPError(
            url,
            400,
            "Bad Request",
            None,
            stdlib_io.BytesIO(b"Unable to retrieve the data for 03808.\n"),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(TephpyIOError, match="HTTP 400: Unable to retrieve the data"):
        wyoming.fetch("03808", WHEN)


def test_fetch_maps_transport_failures(monkeypatch):
    def fake_urlopen(_url, **_kwargs):
        reason = "name resolution failed"
        raise urllib.error.URLError(reason)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(TephpyIOError, match="could not reach the Wyoming archive"):
        wyoming.fetch("03808", WHEN)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/io/test_wyoming.py -v`
Expected: FAIL collecting — `ImportError: cannot import name 'wyoming'`

- [ ] **Step 4: Implement the reader**

Create `src/tephpy/io/wyoming.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""University of Wyoming sounding archive reader (spec §3.4).

:func:`fetch` requests one ascent from the archive's post-2024 wsgi
interface in its machine-readable ``TEXT:CSV`` form — bare, self-describing
CSV (verified 2026-07-27) — over stdlib ``urllib`` behind a function-local
import, and hands the body to a pure, transport-free parser. Network
failures, HTTP errors, and the archive's "no data" replies raise
:class:`~tephpy.exceptions.TephpyIOError` summarising the upstream
response; the parsed sounding passes the ordinary ingest validation
(spec §6).
"""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING

import numpy as np

from tephpy._constants import WYOMING_TIMEOUT, WYOMING_URL
from tephpy.exceptions import TephpyIOError
from tephpy.io._util import coerce_time, strictly_decreasing
from tephpy.sounding import Sounding

if TYPE_CHECKING:
    from datetime import datetime

    import numpy.typing as npt

__all__ = ["fetch"]

#: Archive CSV column → (sounding field, pint unit) for the carried fields.
_COLUMNS: dict[str, tuple[str, str]] = {
    "pressure_hPa": ("pressure", "hPa"),
    "temperature_C": ("temperature", "degC"),
    "dew point temperature_C": ("dewpoint", "degC"),
    "wind direction_degree": ("wind_direction", "degree"),
    "wind speed_m/s": ("wind_speed", "m/s"),
}


def fetch(
    station: str, time: datetime | str, *, timeout: float | None = None
) -> Sounding:
    """Fetch one sounding from the University of Wyoming archive.

    Parameters
    ----------
    station : str
        The WMO station identifier, e.g. ``"03808"``.
    time : datetime.datetime or str
        The nominal launch time; a string is read with
        :meth:`datetime.datetime.fromisoformat`, and a naive value is
        read as UTC (the ``Sounding`` convention).
    timeout : float, optional
        The request timeout in seconds (default ``WYOMING_TIMEOUT``).

    Returns
    -------
    Sounding
        The validated sounding, with `station` and `time` as metadata —
        so the legend label derives for free (spec §3.4).

    Raises
    ------
    TephpyIOError
        For network failures, HTTP errors (including the archive's "no
        data at that time" and "unknown station" replies), or a response
        the parser does not recognise.
    ValueError
        If a `time` string is not ISO 8601.
    """
    when = coerce_time(time)
    from urllib.parse import quote  # noqa: PLC0415 -- spec §3.4 idiom

    url = WYOMING_URL.format(
        datetime=quote(f"{when:%Y-%m-%d %H:%M:%S}"), station=quote(station)
    )
    text = _request(url, WYOMING_TIMEOUT if timeout is None else timeout)
    return _parse(text, station=station, time=when)


def _request(url: str, timeout: float) -> str:
    """Perform the archive request, mapping failures to `TephpyIOError`.

    Parameters
    ----------
    url : str
        The request URL (the formatted ``WYOMING_URL``).
    timeout : float
        The request timeout in seconds.

    Returns
    -------
    str
        The decoded response body.

    Raises
    ------
    TephpyIOError
        For HTTP error statuses (summarising the archive's reply) or
        any transport failure.
    """
    # Function-local so `import tephpy` stays light (spec §3.4, §10 item 10).
    from urllib.error import HTTPError, URLError  # noqa: PLC0415
    from urllib.request import urlopen  # noqa: PLC0415

    try:
        # The URL derives from the https-scheme WYOMING_URL constant.
        with urlopen(url, timeout=timeout) as response:  # noqa: S310
            return str(response.read().decode("utf-8", errors="replace"))
    except HTTPError as error:
        with error:
            body = error.read().decode("utf-8", errors="replace").strip()
        summary = body.splitlines()[0] if body else str(error.reason)
        msg = f"the Wyoming archive returned HTTP {error.code}: {summary}"
        raise TephpyIOError(msg) from error
    except (TimeoutError, URLError, OSError) as error:
        msg = f"could not reach the Wyoming archive: {error}"
        raise TephpyIOError(msg) from error


def _parse(text: str, *, station: str, time: datetime) -> Sounding:
    """Parse one ``TEXT:CSV`` archive body into a sounding.

    Blank cells read as NaN (NaN gaps are data, spec §3.4); rows whose
    pressure does not strictly decrease on the running minimum are
    dropped keeping the first occurrence, so the dense BUFR-era ascents
    satisfy ``Sounding``'s strict monotonicity; an optional field that
    is entirely NaN is treated as absent, so the missing-data errors
    stay meaningful downstream (spec §6).

    Parameters
    ----------
    text : str
        The response body.
    station : str
        The WMO station identifier, carried as metadata.
    time : datetime.datetime
        The nominal launch time, carried as metadata.

    Returns
    -------
    Sounding
        The validated sounding.

    Raises
    ------
    TephpyIOError
        If the body is not the archive's CSV form, expected columns are
        missing, or a cell is not numeric.
    """
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        msg = "the Wyoming archive returned an empty response"
        raise TephpyIOError(msg)
    header = [column.strip() for column in rows[0]]
    missing = sorted(set(_COLUMNS) - set(header))
    if missing:
        msg = (
            f"unexpected Wyoming response format: column(s) {missing!r} "
            f"not in header {header!r}"
        )
        raise TephpyIOError(msg)
    indices = {column: header.index(column) for column in _COLUMNS}
    data: dict[str, list[float]] = {field: [] for field, _ in _COLUMNS.values()}
    for row in rows[1:]:
        if not row:
            continue
        for column, (field, _) in _COLUMNS.items():
            cell = row[indices[column]].strip()
            try:
                data[field].append(float(cell) if cell else np.nan)
            except ValueError as error:
                msg = (
                    f"unexpected Wyoming response format: {column!r} "
                    f"cell {cell!r} is not numeric"
                )
                raise TephpyIOError(msg) from error
    arrays = {
        field: np.asarray(values, dtype=np.float64) for field, values in data.items()
    }
    keep = strictly_decreasing(arrays["pressure"])
    arrays = {field: values[keep] for field, values in arrays.items()}
    fields: dict[str, npt.NDArray[np.float64] | None] = {}
    for field, _ in _COLUMNS.values():
        values = arrays[field]
        optional = field not in ("pressure", "temperature")
        fields[field] = None if optional and bool(np.all(np.isnan(values))) else values
    return Sounding(
        fields["pressure"],
        fields["temperature"],
        dewpoint=fields["dewpoint"],
        wind_speed=fields["wind_speed"],
        wind_direction=fields["wind_direction"],
        units=dict(_COLUMNS.values()),
        station=station,
        time=time,
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/io/test_wyoming.py -v`
Expected: PASS (all tests)

- [ ] **Step 6 (optional, once, not in CI): exercise the live paths**

```bash
pixi run --frozen python -c "
from tephpy.io import wyoming
print(wyoming.fetch('03808', '2026-07-21 12:00').label)"
```

Expected: `03808 2026-07-21 12Z` (verified live 2026-07-27, along with the
400 no-data and 404 unknown-station mappings).

- [ ] **Step 7: Lint and commit**

```bash
git add src/tephpy/_constants.py src/tephpy/io/wyoming.py tests/io/test_wyoming.py
pixi run --frozen lint
git commit -m "feat: fetch soundings from the University of Wyoming archive"
```

---

## Task 9: The IGRA v2 reader

**Files:**
- Modify: `src/tephpy/_constants.py`
- Create: `src/tephpy/io/igra.py`
- Test: `tests/io/test_igra.py`, `tests/test_constants.py`

**Interfaces:**
- Consumes: Task 6's helpers, Task 7's IGRA fixture, `TephpyIOError`, `Sounding`.
- Produces: `igra.read(path, *, time=None) -> Sounding` with the `time=`-selection semantics (single-sounding grace; ambiguity and misses are `TephpyIOError`s carrying count/span/nearest). Task 10 re-exports the module.

- [ ] **Step 1: Add the IGRA sentinels**

In `src/tephpy/_constants.py`, after the `WYOMING_TIMEOUT` entry:

```python
#: IGRA v2 missing-value sentinels (NCEI ``igra2-data-format.txt``): -9999
#: throughout; -8888 additionally flags a removed-by-QA value.
IGRA_MISSING: Final[tuple[int, ...]] = (-9999, -8888)
```

- [ ] **Step 2: Write the failing tests**

Create `tests/io/test_igra.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the IGRA v2 reader (spec §3.4, §7).

The recorded fixture holds the Camborne 2026-07-21 00Z and 12Z ascents as
byte-faithful blocks (see ``tests/fixtures/io/README.md``); the 12Z ascent
is the same physical launch as the Wyoming fixture, so the surface values
cross-validate the two readers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import zipfile

import numpy as np
import pytest

from tephpy.exceptions import TephpyIOError
from tephpy.io import igra

FIXTURE = Path(__file__).parents[1] / "fixtures" / "io" / "UKM00003808-data-trimmed.txt"
WHEN = datetime(2026, 7, 21, 12, tzinfo=UTC)


def test_read_carries_the_fixture_profile():
    snd = igra.read(FIXTURE, time=WHEN)
    assert snd.station == "UKM00003808"
    assert snd.time == WHEN
    assert snd.label == "UKM00003808 2026-07-21 12Z"
    # The surface record: 101900 Pa, 19.6 degC, 3.7 degC depression,
    # 360 degrees at 4.1 m/s — the same launch as the Wyoming fixture
    # (19.7 degC surface), released 11:17 UTC.
    assert snd.pressure[0].m_as("hPa") == pytest.approx(1019.0)
    assert snd.temperature[0].m_as("degC") == pytest.approx(19.6)
    assert snd.dewpoint[0].m_as("degC") == pytest.approx(19.6 - 3.7)
    assert snd.wind_direction[0].m_as("degree") == pytest.approx(360.0)
    assert snd.wind_speed[0].m_as("m/s") == pytest.approx(4.1)


def test_read_sentinels_become_nan_gaps():
    snd = igra.read(FIXTURE, time=WHEN)
    # The second surviving record has -9999 wind fields.
    assert np.isnan(snd.wind_speed.magnitude).any()
    assert np.isnan(snd.dewpoint.magnitude).any()
    assert not np.isnan(snd.pressure.magnitude).any()


def test_read_accepts_the_distributed_zip_form(tmp_path):
    bundle = tmp_path / "UKM00003808-data.txt.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("UKM00003808-data.txt", FIXTURE.read_text())
    snd = igra.read(bundle, time="2026-07-21 12:00")
    assert snd.pressure[0].m_as("hPa") == pytest.approx(1019.0)


def test_read_without_time_is_ambiguous_for_several_soundings():
    with pytest.raises(
        TephpyIOError,
        match=r"holds 2 soundings spanning 2026-07-21 00Z to 2026-07-21 12Z",
    ):
        igra.read(FIXTURE)


def test_read_without_time_reads_a_single_sounding_file(tmp_path):
    lines = FIXTURE.read_text().splitlines()
    second = [i for i, line in enumerate(lines) if line.startswith("#")][1]
    single = tmp_path / "single.txt"
    single.write_text("\n".join(lines[:second]) + "\n")
    snd = igra.read(single)
    assert snd.time == datetime(2026, 7, 21, 0, tzinfo=UTC)


def test_read_unmatched_time_reports_the_nearest_ascents():
    with pytest.raises(TephpyIOError, match=r"nearest: 2026-07-21 12Z"):
        igra.read(FIXTURE, time="2026-07-21 13:00")


def test_read_rejects_a_file_without_headers(tmp_path):
    path = tmp_path / "noise.txt"
    path.write_text("this is not an IGRA station file\n")
    with pytest.raises(TephpyIOError, match="holds no IGRA v2 header records"):
        igra.read(path)


def test_read_rejects_a_truncated_block(tmp_path):
    lines = FIXTURE.read_text().splitlines()
    path = tmp_path / "truncated.txt"
    path.write_text("\n".join(lines[:10]) + "\n")
    with pytest.raises(TephpyIOError, match=r"declares .* levels but the file ends"):
        igra.read(path)


def test_read_rejects_a_malformed_data_record(tmp_path):
    lines = FIXTURE.read_text().splitlines()
    lines[1] = lines[1][:9] + "oopsie" + lines[1][15:]
    path = tmp_path / "malformed.txt"
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(TephpyIOError, match="malformed IGRA v2 data record on line 2"):
        igra.read(path, time="2026-07-21 00:00")


def test_read_rejects_a_multi_member_zip(tmp_path):
    bundle = tmp_path / "two.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("a.txt", "x")
        archive.writestr("b.txt", "y")
    with pytest.raises(TephpyIOError, match="expected one archive member"):
        igra.read(bundle)


def test_read_maps_unreadable_paths(tmp_path):
    with pytest.raises(TephpyIOError, match="could not read"):
        igra.read(tmp_path / "absent.txt")


def test_read_rejects_a_non_iso_time_string():
    with pytest.raises(ValueError, match="Invalid isoformat"):
        igra.read(FIXTURE, time="21/07/2026")
```

and append to `tests/test_constants.py`:

```python
def test_io_conventions():
    """The Wyoming request is https with both placeholders; sane sentinels."""
    assert constants.WYOMING_URL.startswith("https://weather.uwyo.edu/")
    assert "{datetime}" in constants.WYOMING_URL
    assert "{station}" in constants.WYOMING_URL
    assert "TEXT:CSV" in constants.WYOMING_URL
    assert constants.WYOMING_TIMEOUT > 0.0
    assert constants.IGRA_MISSING == (-9999, -8888)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/io/test_igra.py tests/test_constants.py -v`
Expected: test_igra FAILS collecting — `ImportError: cannot import name 'igra'`; `test_io_conventions` PASSES already (Step 1 completed the constants).

- [ ] **Step 4: Implement the reader**

Create `src/tephpy/io/igra.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Integrated Global Radiosonde Archive (IGRA) version 2 reader (spec §3.4).

:func:`read` takes one ascent from an IGRA v2 per-station file — the
as-distributed ``.zip`` or the extracted ``.txt``, sniffed with
``zipfile.is_zipfile`` rather than by suffix — parsing the fixed-width
records per NCEI's ``igra2-data-format.txt``: pressure in Pa, temperature
and dewpoint depression in tenths of °C, wind in degrees and tenths of
m s⁻¹, with the missing-value sentinels reading as NaN and dewpoint
derived as temperature minus depression. Unreadable, malformed, or
ambiguous input raises :class:`~tephpy.exceptions.TephpyIOError`; the
returned sounding passes the ordinary ingest validation (spec §6).
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import numpy as np

from tephpy._constants import IGRA_MISSING
from tephpy.exceptions import TephpyIOError
from tephpy.io._util import coerce_time, strictly_decreasing
from tephpy.sounding import Sounding

if TYPE_CHECKING:
    import os

__all__ = ["read"]

#: The nominal-hour sentinel for an ascent with no nominal hour.
_MISSING_HOUR = 99

#: Data-record slices (0-based) per NCEI ``igra2-data-format.txt``, with
#: the value scale to the sounding's unit.
_FIELDS: dict[str, tuple[slice, float, str]] = {
    "pressure": (slice(9, 15), 0.01, "hPa"),
    "temperature": (slice(22, 27), 0.1, "degC"),
    "dewpoint_depression": (slice(34, 39), 0.1, "delta_degC"),
    "wind_direction": (slice(40, 45), 1.0, "degree"),
    "wind_speed": (slice(46, 51), 0.1, "m/s"),
}


@dataclasses.dataclass(frozen=True)
class _Header:
    """One ascent's header record.

    ``line`` is the header's line index, ``levels`` its record count,
    ``station`` the 11-character IGRA identifier, and ``when`` the
    nominal UTC time — ``None`` when the nominal hour is missing.
    """

    line: int
    levels: int
    station: str
    when: datetime | None


def read(
    path: str | os.PathLike[str], *, time: datetime | str | None = None
) -> Sounding:
    """Read one sounding from an IGRA v2 per-station file.

    Parameters
    ----------
    path : str or os.PathLike
        The station file: the as-distributed ``.zip`` or the extracted
        ``.txt``.
    time : datetime.datetime or str, optional
        The nominal launch time selecting the ascent; a string is read
        with :meth:`datetime.datetime.fromisoformat`, and a naive value
        is read as UTC. May be omitted only when the file holds exactly
        one sounding (trimmed research subsets, fixtures).

    Returns
    -------
    Sounding
        The validated sounding, with the IGRA station identifier and
        the nominal time as metadata.

    Raises
    ------
    TephpyIOError
        For an unreadable or malformed file, a `time` matching no
        ascent (the nearest nominal times are reported), or an
        ambiguous read — several soundings with no ``time=`` selector
        (the file's count and span are reported).
    ValueError
        If a `time` string is not ISO 8601.
    """
    lines = _text(path).splitlines()
    headers = _headers(lines)
    if not headers:
        msg = f"{path!s} holds no IGRA v2 header records"
        raise TephpyIOError(msg)
    return _sounding(lines, _select(headers, time, path))


def _text(path: str | os.PathLike[str]) -> str:
    """Return a station file's text, transparently opening the zip form.

    Parameters
    ----------
    path : str or os.PathLike
        The station file path.

    Returns
    -------
    str
        The decoded file text.

    Raises
    ------
    TephpyIOError
        If the file is unreadable, or a zip without exactly one member.
    """
    # Function-local so `import tephpy` stays light (spec §3.4, §10 item 10).
    import zipfile  # noqa: PLC0415

    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if len(names) != 1:
                    msg = (
                        f"{path!s} is not an IGRA v2 station file: expected "
                        f"one archive member, found {names!r}"
                    )
                    raise TephpyIOError(msg)
                return archive.read(names[0]).decode("ascii", errors="replace")
        with open(path, encoding="ascii", errors="replace") as handle:  # noqa: PTH123
            return handle.read()
    except OSError as error:
        msg = f"could not read {path!s}: {error}"
        raise TephpyIOError(msg) from error


def _headers(lines: list[str]) -> list[_Header]:
    """Collect the header records from a station file's lines.

    Parameters
    ----------
    lines : list of str
        The file's lines.

    Returns
    -------
    list of _Header
        One entry per ascent, in file order.

    Raises
    ------
    TephpyIOError
        If a header record does not parse.
    """
    headers = []
    for index, line in enumerate(lines):
        if not line.startswith("#"):
            continue
        try:
            year, month, day = int(line[13:17]), int(line[18:20]), int(line[21:23])
            hour = int(line[24:26])
            when = (
                None
                if hour == _MISSING_HOUR
                else datetime(year, month, day, hour, tzinfo=UTC)
            )
            headers.append(
                _Header(
                    line=index,
                    levels=int(line[32:36]),
                    station=line[1:12].strip(),
                    when=when,
                )
            )
        except ValueError as error:
            msg = f"malformed IGRA v2 header record on line {index + 1}: {line!r}"
            raise TephpyIOError(msg) from error
    return headers


def _select(
    headers: list[_Header],
    time: datetime | str | None,
    path: str | os.PathLike[str],
) -> _Header:
    """Select the requested ascent from a file's headers.

    Parameters
    ----------
    headers : list of _Header
        The file's ascents, in file order.
    time : datetime.datetime or str or None
        The nominal launch time, or ``None`` for the sole ascent.
    path : str or os.PathLike
        The station file path, for error messages.

    Returns
    -------
    _Header
        The selected ascent.

    Raises
    ------
    TephpyIOError
        For an ambiguous read (no `time` with several ascents) or a
        `time` matching no ascent.
    """
    if time is None:
        if len(headers) == 1:
            return headers[0]
        stamped = [header.when for header in headers if header.when is not None]
        span = (
            f" spanning {min(stamped):%Y-%m-%d %H}Z to {max(stamped):%Y-%m-%d %H}Z"
            if stamped
            else ""
        )
        msg = f"{path!s} holds {len(headers)} soundings{span}: pass time= to select one"
        raise TephpyIOError(msg)
    when = coerce_time(time)
    for header in headers:
        if header.when == when:
            return header
    nearest = sorted(
        (header.when for header in headers if header.when is not None),
        key=lambda stamp: abs(stamp - when),
    )[:3]
    listed = ", ".join(f"{stamp:%Y-%m-%d %H}Z" for stamp in nearest)
    msg = f"{path!s} has no sounding at {when:%Y-%m-%d %H:%M}Z (nearest: {listed})"
    raise TephpyIOError(msg)


def _sounding(lines: list[str], header: _Header) -> Sounding:
    """Parse one ascent's records into a sounding.

    Records without a pressure value are dropped (`Sounding` requires
    finite pressure), the sentinels read as NaN, dewpoint derives as
    temperature minus dewpoint depression, and rows whose pressure does
    not strictly undercut the running minimum drop keeping the first
    occurrence. An optional field that is entirely NaN is treated as
    absent, so the missing-data errors stay meaningful downstream
    (spec §6).

    Parameters
    ----------
    lines : list of str
        The file's lines.
    header : _Header
        The selected ascent.

    Returns
    -------
    Sounding
        The validated sounding.

    Raises
    ------
    TephpyIOError
        If a data record does not parse.
    """
    start = header.line + 1
    block = lines[start : start + header.levels]
    if len(block) < header.levels:
        msg = (
            f"IGRA v2 header on line {header.line + 1} declares "
            f"{header.levels} levels but the file ends after {len(block)}"
        )
        raise TephpyIOError(msg)
    columns: dict[str, list[float]] = {field: [] for field in _FIELDS}
    for offset, line in enumerate(block):
        for field, (chars, scale, _) in _FIELDS.items():
            cell = line[chars].strip()
            try:
                raw = int(cell)
            except ValueError as error:
                msg = (
                    f"malformed IGRA v2 data record on line "
                    f"{start + offset + 1}: {line!r}"
                )
                raise TephpyIOError(msg) from error
            columns[field].append(np.nan if raw in IGRA_MISSING else raw * scale)
    arrays = {
        field: np.asarray(values, dtype=np.float64) for field, values in columns.items()
    }
    keep = strictly_decreasing(arrays["pressure"])
    arrays = {field: values[keep] for field, values in arrays.items()}
    dewpoint = arrays["temperature"] - arrays.pop("dewpoint_depression")
    wind = ("wind_direction", "wind_speed")
    wind_absent = all(bool(np.all(np.isnan(arrays[field]))) for field in wind)
    return Sounding(
        arrays["pressure"],
        arrays["temperature"],
        dewpoint=None if bool(np.all(np.isnan(dewpoint))) else dewpoint,
        wind_speed=None if wind_absent else arrays["wind_speed"],
        wind_direction=None if wind_absent else arrays["wind_direction"],
        units={
            "pressure": "hPa",
            "temperature": "degC",
            "dewpoint": "degC",
            "wind_direction": "degree",
            "wind_speed": "m/s",
        },
        station=header.station,
        time=header.when,
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/io tests/test_constants.py -v`
Expected: PASS (all tests)

- [ ] **Step 6: Lint and commit**

```bash
git add src/tephpy/_constants.py src/tephpy/io/igra.py \
        tests/io/test_igra.py tests/test_constants.py
pixi run --frozen lint
git commit -m "feat: read soundings from IGRA v2 station files"
```

---

## Task 10: The public `tephpy.io` namespace

**Files:**
- Modify: `src/tephpy/io/__init__.py`, `src/tephpy/__init__.py`
- Test: `tests/test_import.py`, `tests/test_units.py`

**Interfaces:**
- Consumes: Tasks 8–9's modules.
- Produces: `tephpy.io` re-exported eagerly at the top level (spec §10 item 10 — `import tephpy; tephpy.io.wyoming.fetch(...)` works), with the import-cost guard extended so the eager import stays light.

- [ ] **Step 1: Extend the failing tests**

In `tests/test_import.py::test_top_level_namespace`, add the reachability
asserts and `"io"` to the expected set:

```python
assert tephpy.transforms is not None
assert tephpy.plotting is not None
assert tephpy.io.wyoming is not None
assert tephpy.io.igra is not None
expected = {
    "Sounding",
    "__version__",
    "calc",
    "config",
    "exceptions",
    "io",
    "plotting",
    "transforms",
}
```

In `tests/test_units.py`, the import-cost guard function becomes (only the
docstring and the `code` set change):

```python
def test_import_tephpy_does_not_import_heavy_dependencies():
    """`import tephpy` must not import metpy, pandas, or xarray (item 10).

    MetPy loads on first use (as_quantity); pandas and xarray are never
    imported by tephpy at runtime at all; the readers keep their
    network/archive imports (urllib.request, zipfile) function-local
    (spec §3.4). Run in a subprocess so the check is independent of what
    this session already imported.
    """
    code = (
        "import sys, tephpy; raise SystemExit("
        "1 if {'metpy', 'pandas', 'xarray', 'urllib.request', 'zipfile'}"
        " & set(sys.modules) else 0)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_import.py tests/test_units.py -v`
Expected: `test_top_level_namespace` FAILS — `AttributeError: ... no attribute 'io'` (the guard already passes: nothing imports the readers yet).

- [ ] **Step 3: Wire the namespace**

Append to `src/tephpy/io/__init__.py`:

```python
from tephpy.io import igra, wyoming

__all__ = ["igra", "wyoming"]
```

and in `src/tephpy/__init__.py` add `io` to the subpackage import and
`__all__` (both alphabetical):

```python
from tephpy import calc, exceptions, io, plotting, transforms
```

```python
__all__ = [
    "Sounding",
    "__version__",
    "calc",
    "config",
    "exceptions",
    "io",
    "plotting",
    "transforms",
]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_import.py tests/test_units.py -v`
Expected: PASS — including the extended guard: the eager `tephpy.io` import
pulls neither `urllib.request` nor `zipfile` (they are function-local).

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/io/__init__.py src/tephpy/__init__.py \
        tests/test_import.py tests/test_units.py
pixi run --frozen lint
git commit -m "feat: re-export tephpy.io eagerly at the top level"
```

---

## Task 11: Docs — xref aliases, glossary entries, warning-free build

**Files:**
- Modify: `docs/src/conf.py`, `docs/src/reference/glossary.rst`

**Interfaces:**
- Consumes: every public name this plan added.
- Produces: a warning-free nitpicky docs build over the new API pages, and the spec §10 cross-cutting glossary entries (radiosonde, IGRA, wind barb).

- [ ] **Step 1: Run the docs build to see the four expected failures**

Run: `pixi run --frozen docs`
Expected: FAIL with exactly four unresolved-reference warnings — `TephpyIOError` (py:obj, on the two reader pages), `BarbStaff` (py:obj, on the axes page), and `numpy.bool_` (py:class, on the barbs page). This is the numpydoc types-need-aliases rule from Global Constraints in action.

- [ ] **Step 2: Fix the configuration**

In `docs/src/conf.py`, extend `numpydoc_xref_aliases`:

```
    "TephpyIOError": "tephpy.exceptions.TephpyIOError",
    "BarbStaff": "tephpy.plotting.barbs.BarbStaff",
```

and add to `nitpick_ignore`, after the `numpy.float64` entry (same rationale —
numpy's inventory publishes ``numpy.bool``, autoapi renders the annotation as
``numpy.bool_``):

```python
("py:class", "numpy.bool_"),
```

- [ ] **Step 3: Add the glossary entries**

Append to `docs/src/reference/glossary.rst` (inside the `.. glossary::`
directive, after the `lifted index` entry):

```rst
    radiosonde
        The instrument package a weather balloon carries aloft,
        transmitting pressure, temperature, humidity, and wind as it
        rises — the source of most real :term:`soundings <sounding>`.
        ``tephpy`` ingests radiosonde archives through the ``tephpy.io``
        readers.

    IGRA
    Integrated Global Radiosonde Archive
        NCEI's quality-controlled archive of the global
        :term:`radiosonde` record, distributed as one fixed-width file
        per station (version 2).
        :func:`igra.read(...) <tephpy.io.igra.read>` reads one ascent
        from such a file into a
        :class:`Sounding <tephpy.sounding.Sounding>`.

    wind barb
        A glyph giving the wind at one level: the shaft points toward
        the direction the wind comes from, and its feathers sum to the
        speed — half barb 5 kt, full barb 10 kt, flag 50 kt, rounded to
        5 kt bins; a bare circle is calm.
        :meth:`ax.plot_barbs(snd) <tephpy.plotting.axes.TephigramAxes.plot_barbs>`
        draws a :term:`sounding`'s barbs on a staff in the right-hand
        gutter, each level at the height where its isobar meets the
        diagram's edge.
```

- [ ] **Step 4: Run the docs build to verify it is clean**

Run: `pixi run --frozen docs`
Expected: `build succeeded.` — zero warnings. Spot-check the rendered pages:
`reference/generated/api/tephpy/io/wyoming/` shows `fetch` with `TephpyIOError`
cross-referenced; the glossary's *wind barb* entry links `ax.plot_barbs(snd)`.

- [ ] **Step 5: Lint and commit**

```bash
git add docs/src/conf.py docs/src/reference/glossary.rst
pixi run --frozen lint
git commit -m "docs: cross-reference the barb and ingest APIs; seed their glossary terms"
```

---

## Task 12: Full verification, pull request, and changelog fragment

**Files:** `changelog/<PR>.feature.rst` (created after the PR number exists)

- [ ] **Step 1: Full local gate**

```bash
pixi run --frozen lint
pixi run --frozen --environment test-py312 pytest --cov --cov-report=xml --mpl
pixi run --frozen --environment test-py313 pytest --cov --cov-report=xml --mpl
pixi run --frozen --environment test-py314 pytest --cov --cov-report=xml --mpl
pixi run --frozen docs
```

Expected: lint fully green; the suite (420 tests, including all 13 image
comparisons) passes on all three Pythons against the same committed baselines
(verified 2026-07-27); docs build with 0 warnings.

- [ ] **Step 2: Open the pull request**

```bash
git push -u origin barbs-ingest
gh pr create --base main --title "Wind barbs & data ingest (Plan 6)" --fill
```

- [ ] **Step 3: Add the changelog fragment named for the PR**

With `<PR>` the number just created:

```bash
cat > changelog/<PR>.feature.rst <<'EOF'
Added wind barbs and data ingest —
:meth:`~tephpy.plotting.axes.TephigramAxes.plot_barbs` drawing Met Office
barbs (flag 50 kt, full 10 kt, half 5 kt, 5 kt binning) on a zoom-aware
right-hand gutter staff, with the side panels sharing one divider so the
gutter and the indices panel compose in either call order; the ``tephpy.io``
readers :func:`~tephpy.io.wyoming.fetch` (University of Wyoming) and
:func:`~tephpy.io.igra.read` (IGRA v2) returning validated
:class:`~tephpy.sounding.Sounding` objects, with recorded, provenance-tracked
fixtures; :class:`~tephpy.exceptions.TephpyIOError`; and the barb image
baselines.
(:user:`claude`)
EOF
git add changelog/<PR>.feature.rst
git commit -m "docs: add Plan 6 changelog fragment"
```

- [ ] **Step 4: Verify the fragment with a clean docs build, then push**

```bash
pixi run --frozen docs
git push
```

Expected: the fragment renders under "unreleased" with every role resolved
(the docs task cleans first, so no stale draft can hide a bad reference); the
`ci-changelog` check passes on the PR; all other checks (tests ×3 with image
comparisons, docs, wheels + smoke test, CodeQL, pre-commit.ci) go green.

---

## Self-review

**Spec coverage (Plan 6 row: §3.2 `plot_barbs` + barb baselines, §3.4 `io`
with recorded-fixture tests, §6 `TephpyIOError`):** `plot_barbs(snd, *,
x=None, **kwargs)` with Met Office increments and 5 kt binning, the
zoom-aware staff placed at the isobar/right-edge crossings, minimum-separation
thinning, `MissingDataError` on absent wind, staff-position overlays, and the
staff artist returned → Tasks 2, 4. The §3.2 side-of-axes resolution — one
cached divider, `make_axes_locatable` called exactly once per axes, call
order made irrelevant by relayout — → Task 3 (and the Task 4 both-orders
tests). Calm renders as matplotlib's native circle — which **is** the Met
Office calm symbol, so the spec's "open-circle glyph as a v1.x nicety" note
is already satisfied (spec touch-up rides this plan's PR). Barb baselines
(§7/§8.5 cross-cutting rule) → Task 5. `wyoming.fetch` — wsgi `TEXT:CSV`
(the spec's TEXT:LIST wording predates the live-endpoint probe; touch-up on
this plan's PR), stdlib urllib with `_constants` timeout, pure transport-free
parser, NaN gaps, running-minimum monotonicity filter, all-NaN-optional
absence, station/time metadata → label, HTTP/transport failures summarised in
`TephpyIOError` → Task 8. `igra.read` — zip-or-text sniffing, fixed-width
parse with sentinels, dewpoint from depression, `time=` selection with the
single-sounding grace, ambiguity/miss errors carrying count/span/nearest →
Task 9. Readers return `Sounding` so §6 ingest validation applies unchanged →
Tasks 8–9 construction. `TephpyIOError` in the public hierarchy (§6) →
Task 1. Eager `tephpy.io` re-export with function-local network imports and
the extended guard (§10 item 10 Plan 6 slice) → Task 10. Recorded fixtures
with source, capture method, and attribution (§10 item 13 Plan 6 slice) →
Task 7. Glossary terms ship with the plan (§8.6/§10 cross-cutting) →
Task 11. Full gate + PR + fragment → Task 12.

**Placeholder scan:** every code step carries complete, runnable code — the
listings **are** the verified implementation (ruff `ALL` + format, mypy
strict, numpydoc-validation all green; 420 tests including 13 image
comparisons passing on py312/py313/py314; docs warning-free; live fetch
exercised on 2026-07-27; the two readers cross-validated on the same physical
ascent). No TBDs, no "similar to Task N".

**Type/name consistency:** the `_constants` names, `staff_y`/`select_barbs`
signatures, `BarbStaff.__init__`'s keyword-only contract, the
`_append_side_axes`/`_relayout_side_panels` helpers, `plot_barbs`'s signature
and return, `coerce_time`/`strictly_decreasing`, `_request`/`_parse`
(wyoming), and `_text`/`_headers`/`_select`/`_sounding` (igra) are identical
across the Interfaces contract and Tasks 1–11; Task 4's count test recomputes
Task 2's pipeline verbatim; Task 9's tests read Task 7's fixture values.

**Known judgment calls (documented, not hidden):**
- The staff solves crossings on the isobar's **analytic extension**
  (−200…300 °C inversion span): drawn polylines end at `TEMPERATURE_DOMAIN`,
  often inside the view, and barbs must not vanish at the default extent
  (observed failure mode, not hypothetical). Crossings beyond even that span
  drop as NaN.
- `BARB_MIN_SEPARATION = 18.0` points is a readability convention tuned on
  the rendered baselines (24 was visibly too sparse on the letterboxed
  default view); like every convention it is a `_constants` value, overridable
  per call.
- Thinning is greedy from the surface, so the surface barb always draws — an
  operational-reading choice over mathematically-optimal packing.
- One `BarbStaff` per call in one shared gutter; distinguishing overlays is
  the caller's `x=`/colour job (the profile-overlay convention). No dynamic
  gutter widening.
- The readers pass through *shape*, not *judgment*: the running-minimum
  filter drops duplicate and re-rising pressure rows (first occurrence wins)
  because `Sounding` demands strict monotonicity and real BUFR-era ascents
  are dense; everything else fails loudly in `Sounding.__post_init__`.
- An optional field that is entirely NaN is passed as **absent**, so
  `plot_barbs`/`parcel_path` raise `MissingDataError` instead of silently
  drawing/computing nothing.
- `igra.read` matches on the header's **nominal** time; an ascent with a
  missing nominal hour (hour 99 — rare, pre-1960s) is unmatchable by `time=`
  and carries `time=None` metadata if selected via the single-sounding grace.
- `wyoming.fetch` trusts the archive's self-describing header (exact column
  names pinned; a drift raises `TephpyIOError` naming the missing columns)
  rather than scraping the HTML TEXT:LIST page.
- `urllib.error.HTTPError` is read inside a `with error:` block — hygiene
  that also keeps `filterwarnings = ["error"]` suites green (ResourceWarning).
- The fixtures are thinned/trimmed but **byte-faithful in the kept rows**,
  with the whitespace hooks excluded from `tests/fixtures/io/` so pre-commit
  cannot silently mutate them (it did, once, before the exclude).
- The two baselines total ~124 KB, riding into the sdist like the Plan 3/4/5
  sets; regeneration was verified bit-identical for the existing eleven.

---

## Execution handoff

Plan 6 of 7 (spec §10). On completion, the §4 canonical usage runs end to
end: `wyoming.fetch` → `plot_sounding` + `plot_barbs` + parcel analysis +
shading + indices panel, in any panel order. **Plan 7 (examples gallery &
documentation completion)** needs the union of Plans 5 and 6 — including the
composed §4-figure baseline this plan deliberately does not add. Spec
touch-ups riding this plan's own PR (docs-only): §3.4's Wyoming bullet
updated from TEXT:LIST/knots to the verified wsgi TEXT:CSV/m-per-s facts;
§3.2's layout resolution updated from remove-and-re-render to the relayout
mechanism; §3.2's calm-glyph note updated (matplotlib's native calm circle is
already the Met Office symbol). When the implementation PR merges: mark the
Plan 6 row complete in §10.
