# tephpy Thermodynamic Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the §3.3 `calc` layer — `parcel_path` (surface and mixed-layer parcels, the −25 mb cloud-base correction), `normand_point`, `indices`, and the `Profile`/`SoundingIndices` dataclasses — plus its plotting surface: the `plot_profile` `Profile` overload, `shade_cape`/`shade_cin` with the `plotting/shading.py` builders, and the `annotate_indices` panel; the analysis-time §6 errors; shading/panel image baselines; the published worked-example integration test; and the scipy declaration drop — so the §4 canonical usage works end to end minus `plot_barbs` (Plan 6).

**Architecture:** One new top-level module along the §3 layering: `calc.py` imports `_units`/`_constants`/`exceptions` at module level, sees `Sounding` only under `TYPE_CHECKING` (it consumes the object duck-typed), and sites every `metpy.calc` import function-locally — so `calc` re-exports eagerly at the top level and `import tephpy` stays light (§10 item 10, resolved: no lazy-loading machinery). `plotting/shading.py` is a free-builder module (numpy + `transforms` only, the `isopleths.py` pattern). `plotting/axes.py` gains the `Profile` overload (duck-typed dispatch — `plotting` never imports `calc` at runtime), the two shading methods, and the `axes_grid1` indices panel (the first consumer of the Plan 3 side-of-axes contract). `_constants.py` accretes the analysis conventions.

**Tech Stack:** Python 3.12/3.13/3.14, numpy, matplotlib (Agg in tests; `mpl_toolkits.axes_grid1` for the panel), pint (MetPy's registry), metpy ≥ 1.6 (function-local imports), pytest, pytest-mpl, pixi tasks.

**Spec:** `docs/superpowers/specs/2026-07-22-tephpy-design.md` — §3.3 (authority for `calc`), §3.2 (the `plot_profile` overload, shading, `annotate_indices`, side-of-axes contract), §5 (units policy), §6 (analysis-time errors, NaN-versus-zero semantics), §7 (calc testing = composition; the worked example), §10 (Plan 5 row; resolved items 2, 10, 11, 12, 13, 14).

This is **Plan 5 of 7** (spec §10). It produces working software: after it merges, `tephpy.calc.parcel_path(snd)` computes a parcel ascent that `ax.plot_profile(parcel, ...)` draws, `ax.shade_cape`/`shade_cin` fill exactly the regions `cape_cin` integrates, and `ax.annotate_indices(tephpy.calc.indices(snd))` puts the ten derived parameters beside the diagram. Plan 6 (barbs & ingest) is independent and may already be in flight; Plan 7 needs both.

## Global Constraints

Copied from the spec / Plans 1–4; every task's requirements implicitly include these.

- **Python support (SPEC 0):** 3.12, 3.13, and 3.14. **Platforms (pixi):** `linux-64` only.
- **Copyright header (every `.py` file, verbatim — ruff `CPY001` enforces it):**
  ```
  # Copyright (c) 2026, tephpy Contributors.
  #
  # This file is part of tephpy and is distributed under the 3-Clause BSD license.
  # See the LICENSE file in the package root directory for licensing details.
  ```
- **Imports:** every `.py` file needs `from __future__ import annotations` (ruff isort `required-imports`).
- **Lint/type:** ruff `ALL` (repo config); mypy `strict` clean over `src/tephpy` (spec §8.4 — `calc` is numeric core: no per-module relaxations). numpydoc-validation checks **every docstringed object, including private helpers**: documented parameters (PR01) and a `Returns` section on anything returning a value (RT01).
- **numpydoc + dataclasses gotcha (Plan 4 precedent):** document dataclass fields under an **`Attributes` section**, never `Parameters` (the static hook sees no `def __init__` in a dataclass and fails PR02). A dataclass `__post_init__` **must** carry its own docstring (GL08).
- **numpydoc + `@overload` gotcha (verified 2026-07-26, numpydoc 1.10.0):** the static hook flags docstring-less `@overload` stubs as GL08 and has no overload special-casing. Put `# numpydoc ignore=GL08` on each overload's `def` line (Task 8's listing does this); the real docstring lives on the implementation.
- **Function-local MetPy imports** (spec §5, §10 item 10) trigger ruff `PLC0415` — suppress with `# noqa: PLC0415` exactly as shown in the task code. The existing subprocess import-cost guard in `tests/test_units.py` enforces this automatically once `tephpy/__init__.py` imports `calc` (Task 2) — no test change needed there.
- **mpl_toolkits typing (verified 2026-07-26):** `from mpl_toolkits.axes_grid1 import make_axes_locatable` passes mypy strict with **no** new `ignore_missing_imports` override. One stub defect: `Axes.set_axes_locator(None)` (the documented reset) needs `# type: ignore[arg-type]` (Task 11's listing carries it with its justifying comment).
- **matplotlib kwargs pass-through:** `**kwargs: Any` (with `# noqa: ANN401` on the def line where ruff demands it) — `**kwargs: object` fails mypy strict against matplotlib's typed keywords (Plan 4 precedent).
- **Units:** pint quantities at every public boundary; conversion via `.m_as(...)` — never `np.asarray(Quantity)` (`UnitStrippedWarning` is an **error** under the repo's pytest `filterwarnings = ["error"]`).
- **Tests:** pytest strict config with `filterwarnings = ["error"]`; close every matplotlib figure you open (pytest-mpl closes returned figures; the `tephigram_axes` fixture closes its own). The tests tree mirrors `src/tephpy`: `calc.py` is a top-level module so `tests/test_calc.py` lives at the `tests/` root; `shading.py` is a plotting module so `tests/plotting/test_shading.py` joins `tests/plotting/`.
- **Docs:** build must stay warning-free (`pixi run docs`). Titles use CMOS headline style. Glossary entries ship with the terms this plan introduces (spec §10 cross-cutting rule); sphinx-autoapi picks up `tephpy.calc` and `tephpy.plotting.shading` automatically.
- **Changelog:** one `changelog/<PR>.<type>.rst` fragment per PR, ending with ``(:user:`claude`)`` attribution (see `changelog/README.md`).
- **Branch:** work on a feature branch (`no-commit-to-branch` blocks `main`): `git switch -c analysis`.
- **Dedented listings:** the repo's blacken-docs hook formats this plan's fenced listings at top level, so code destined for a **class body** (Tasks 8(b), 10(b), 11(b)) is shown **dedented** — indent every line one level (4 spaces) when inserting into `TephigramAxes`. One line sits on the 88-column boundary: Task 8(b)'s `profile_shaped = all(...)` generator is one line when dedented but re-wraps once indented — paste as shown and let `pixi run lint`'s ruff-format auto-fix wrap it (re-stage and re-run lint after auto-fixes, as always).
- **Lint gotcha:** `pre-commit run --all-files` only checks files git knows about — **`git add` new files before `pixi run lint`** (every task's final step stages first for this reason).
- **Environment facts (verified against the committed lockfile, 2026-07-26):** metpy 1.7.1, pint 0.25.3, numpy 2.5.1, matplotlib 3.11.1, pytest-mpl 0.19.0, numpydoc 1.10.0. Facts the design leans on, all verified empirically on 1.7.1 **and re-verified on a fresh `metpy=1.6` resolve (1.6.3) — the §6 semantics hold at the declared floor, so `metpy>=1.6` stands (spec §10 item 11)**:
  - `lcl`/`mixed_parcel`/`wet_bulb_potential_temperature` return **scalar** quantities; `lifted_index` returns a **length-1 array** quantity (`delta_degree_Celsius` — pint dimensionality `[temperature]`) that must be indexed `[0]`.
  - Zero CAPE/CIN is `0 J/kg`, never NaN; with **no LFC, `cape_cin` returns `(0, 0)`** even over negative-buoyancy layers. LFC/EL return NaN quantities; EL can be NaN while CAPE > 0 (buoyant at the profile top, where `cape_cin` integrates to the top pressure instead).
  - `cape_cin` defaults `which_lfc="bottom"`, `which_el="top"`; standalone `lfc()` defaults `which="top"` — for multi-crossing profiles the reported LFC and the integration's LFC bound can differ (MetPy's own inconsistency, passed through; see the shading design note below).
  - `cape_cin` converts both curves to **virtual temperature** (Doswell & Rasmussen) before finding bounds and integrating, and integrates the **net** trapezoid between its bounds; environment dewpoint aloft therefore shifts CAPE a few percent, invisibly to the plotted temperature curves.
  - A profile topping out below 500 hPa makes `lifted_index` NaN **with** a `UserWarning` ("Interpolation point out of data bounds encountered") — suppressed at the call site, message-matched.
  - `parcel_profile(P, T[0], Td[0])` and a hand-built dry_lapse/moist_lapse curve on the same levels differ by up to ~0.1 K (ODE anchoring), and `surface_based_cape_cin` ≠ `cape_cin` over `parcel_profile` — so the §7 field-equality test targets **`cape_cin` fed an explicit `parcel_profile` curve**, and `indices()` delegates to `parcel_profile` for every uncorrected run (hand-building only the corrected curve, which has no MetPy one-liner).
  - `lcl()`'s temperature is not exactly on the dry adiabat (~0.04 K solver tolerance): never assert `dry_lapse(p_lcl) == t_lcl`; the LCL vertex splices `lcl()`'s own values.
  - `moist_lapse` on an **empty** pressure array raises `IndexError` — the `ProfileTooShortError` guard must fire first.

  The code in this plan was verified against this environment: every listing passes ruff (`ALL` + format), mypy strict, and numpydoc-validation; the full suite (359 tests including the 11 image comparisons) passes on the default/py314, test-py312, and test-py313 environments; the docs build is warning-free; `pixi lock` is a byte-identical no-op after the scipy drop; and the composed figures were rendered and visually inspected (2026-07-26).

---

## File structure created or modified by this plan

```
src/tephpy/
  calc.py                             # NEW: Profile, SoundingIndices, normand_point,
                                      #      parcel_path, indices (§3.3)
  exceptions.py                       # MODIFIED: + MissingDataError, ProfileTooShortError
  _constants.py                       # MODIFIED: + correction, shading, panel conventions
  plotting/shading.py                 # NEW: cape_polygons/cin_polygons free builders
  plotting/axes.py                    # MODIFIED: plot_profile overload; shade_cape,
                                      #           shade_cin, annotate_indices; clear()
  __init__.py                         # MODIFIED: export calc
tests/
  test_calc.py                        # NEW: dataclasses, functions, worked example
  test_exceptions.py                  # MODIFIED: hierarchy + levels for the new pair
  test_constants.py                   # MODIFIED: + shading/correction/panel invariants
  test_import.py                      # MODIFIED: __all__, runtime deps list (scipy out)
  plotting/
    test_shading.py                   # NEW: builder geometry against analytic crossings
    test_axes.py                      # MODIFIED: + overload, shading, panel behaviour
    test_images.py                    # MODIFIED: + 2 baselines
  baseline/
    test_shading_cape_cin.png         # NEW: generated baseline (~67 KB)
    test_indices_panel.png            # NEW: generated baseline (~79 KB)
docs/src/reference/glossary.rst       # MODIFIED: profile updated; + 8 analysis terms
pyproject.toml                        # MODIFIED: scipy dropped from pixi dependencies
requirements/pypi-core.txt            # MODIFIED: scipy dropped
changelog/<PR>.feature.rst            # NEW: news fragment (named after the PR, Task 15)
```

Naming used throughout (Interfaces contract):

```
tephpy.exceptions (additions; both subclass TephpyValidationError):
    MissingDataError                  # sounding lacks a field the operation needs
    ProfileTooShortError              # profile tops out at or below the LCL used

tephpy._constants (additions):
    CLOUD_BASE_CORRECTION = -25.0     # hPa; the operational value, cited (§1/§3.3)
    CAPE_COLOR = "tab:red"            # positive buoyancy red, negative blue
    CIN_COLOR = "tab:blue"
    SHADING_ALPHA = 0.3
    SHADING_ZORDER = 2.0              # between families (<=1.5) and profiles (2.5)
    INDICES_PANEL_WIDTH = "35%"       # axes_grid1 fraction of the diagram width
    INDICES_PANEL_PAD = 0.1           # inches
    INDICES_PANEL_FONTSIZE = 8.0
    INDICES_PANEL_ROWS                # 10 rows: (field, label, pint unit, display, fmt)

tephpy.calc (public; imports _units/_constants/exceptions; metpy function-local):
    Profile                           # @dataclass(frozen=True, eq=False)
        fields: pressure, temperature, lcl_pressure, lcl_temperature,
                parcel="surface", label=None, units=InitVar
    SoundingIndices                   # @dataclass(frozen=True, eq=False)
        fields: cape, cin, lcl_pressure, lcl_temperature, lfc_pressure,
                lfc_temperature, el_pressure, el_temperature, theta_w,
                lifted_index, units=InitVar
    normand_point(pressure, temperature, dewpoint, *, units=None)
        -> tuple[pint.Quantity, pint.Quantity]        # (hPa, degC) scalars
    parcel_path(snd, *, parcel="surface", cloud_base_correction=None,
                label=None) -> Profile
    indices(snd, *, parcel="surface", cloud_base_correction=None)
        -> SoundingIndices

tephpy.plotting.shading (public builders; bare hPa/degC arrays in, (T, theta)
polygons out):
    cape_polygons(pressure, temperature, parcel_pressure, parcel_temperature,
                  *, lcl_pressure) -> list[np.ndarray]
    cin_polygons(...same signature...) -> list[np.ndarray]

tephpy.plotting.axes.TephigramAxes (additions):
    plot_profile(profile, *, label=None, **kwargs) -> Line2D   # new overload;
        # array form unchanged: plot_profile(pressure, temperature, *,
        # units=None, label=None, **kwargs)
    shade_cape(snd, parcel, **kwargs) -> PathPatch | None
    shade_cin(snd, parcel, **kwargs) -> PathPatch | None
    annotate_indices(indices) -> Axes                          # the panel axes

tephpy top level:
    __all__ = ["Sounding", "__version__", "calc", "config", "exceptions",
               "plotting", "transforms"]
```

Design decisions locked here (shared vocabulary for all tasks):

- **`indices()` delegates; only the corrected curve is hand-built.** For every
  uncorrected run — surface *and* mixed-layer — the parcel curve on the
  environment levels is `metpy.calc.parcel_profile(P, T_start, Td_start)`
  (mixed-layer start from `mixed_parcel`), so the §7 field-equality test
  against direct `metpy.calc` calls holds **exactly**. A corrected run has no
  MetPy one-liner: its curve is `dry_lapse` on the levels at or below the
  corrected LCL and `moist_lapse(..., reference_pressure=corrected)` above —
  and the §7 corrected test hand-builds the same curve and feeds it to the
  same generic functions.
- **`parcel_path` composes `normand_point`.** `_lcl_used` calls the public
  `normand_point` (never `metpy.calc.lcl` directly), so "the parcel path
  passes through Normand's point" is literally true and tested. The
  correction is added to the LCL pressure and the corrected temperature is
  **re-read from the dry adiabat** (`dry_lapse` at the corrected pressure) —
  internally consistent, unlike `lcl()`'s own ~0.04 K off-adiabat solver
  tolerance, which is why the corrected case has no vertex kink.
- **Path construction:** dry leg `np.arange(p0, lcl, -5.0)` (empty when the
  parcel is saturated at its start — `lcl()` returns the start exactly), the
  exact LCL vertex, then `np.arange(lcl - 5.0, top, -5.0)` plus the exact
  profile-top pressure; temperatures from `dry_lapse`/`moist_lapse` anchored
  at the start/LCL respectively. Guards in order: `MissingDataError` (no
  dewpoint), `ValueError` (unknown `parcel=`), `TephpyUnitsError` (bad
  correction), `TephpyValidationError` (correction puts the LCL below the
  start), `ProfileTooShortError` (`top >= lcl` — checked **before** any
  `moist_lapse` call, which would `IndexError` on an empty grid).
- **Shading bounds mirror `cape_cin`'s rules on the drawn curves.** The
  builders interpolate both curves onto their merged pressure grid (linear
  in ln p), insert exact zero crossings, and bound regions the way
  `cape_cin` integrates: LFC = bottom of the lowest positive run at or
  above the LCL, clamped to the LCL when the run crosses it
  (`which_lfc="bottom"`); EL = top of the highest such run, which **is** the
  profile top while the parcel is still buoyant there (`which_el="top"`,
  top-when-NaN); no LFC → neither CAPE nor CIN regions (matching
  `cape_cin`'s `(0, 0)`); CIN = negative runs between the parcel start and
  that LFC. Positive buoyancy below the LCL is never CAPE. Two documented
  divergences from the *numbers*: `cape_cin` finds bounds and integrates in
  **virtual temperature** (which the plotted T curves cannot show) and
  integrates the **net** difference between its bounds — the shading is the
  drawn-curve region under the same bounding rules, and the J/kg number
  stays the quantitative truth. (This is also exactly what MetPy's own
  `SkewT.shade_cape` shades.)
- **The dense path vs the coarse curve.** `shade_*` consumes the plotted
  `Profile` (5 hPa sampling), `indices()` the environment-level curve; their
  crossings agree to interpolation, so shading edges land exactly where the
  *drawn* curves cross — visually coherent — while the annotated numbers
  come from the coarse curve MetPy integrates.
- **`Profile`/`SoundingIndices` are `@dataclass(frozen=True, eq=False)`**
  (the `Sounding` idiom: coercion in `__post_init__` via
  `object.__setattr__`; field annotations state the post-init guarantee).
  `Profile` validates 1-D equal-length arrays of ≥ 2 levels with **strictly
  decreasing** pressure (no normalization — `parcel_path` output is already
  surface-first; a NaN or out-of-span LCL fails the span check), then the
  `parcel` literal (`ValueError` — bad code, not bad data).
  `SoundingIndices` dimension-checks ten scalars and validates **nothing
  cross-field** — NaN fields are answers (§6). CAPE/CIN dimensionality is
  `"[energy] / [mass]"` (verified: pint parses it).
- **`normand_point` rejects Td > T** with `DewpointExceedsTemperatureError`
  (it is a public quantity-level boundary that never sees `Sounding`'s
  validation) and non-scalars with `TephpyValidationError`; equality —
  saturation — is physical and returns the parcel itself.
- **The overload dispatch is attribute-shaped:** `pressure`, `temperature`,
  and `lcl_pressure` all present ⇒ `Profile` form (`Sounding` lacks
  `lcl_pressure`; `SoundingIndices` lacks the arrays — spec §3.2). The
  first parameter keeps its Plan 4 name `pressure` in **both** overloads
  (spec: "the first parameter keeps its Plan 4 name") — a positional-only
  `profile` parameter would let `**kwargs` legally carry `pressure=`, which
  mypy strict correctly rejects against the implementation. Wrong
  combinations are `TypeError`s raised **before** any units machinery runs.
- **The panel updates in place** (`self._indices_panel` cached; `clear()`
  removes it and resets the axes locator so a cleared diagram regains its
  full slot). `append_axes` must pass `axes_class=Axes` explicitly —
  axes_grid1 otherwise clones the **parent's** class and would draw a whole
  tephigram grid inside the panel.
- **NaN rendering:** a NaN field renders as an em dash (`"—"`) with no unit
  text; finite values render `f"{value:{fmt}} {display}"` per
  `INDICES_PANEL_ROWS`.
- **Worked-example stance (spec §10 item 13, resolved here):** the pinned
  source is Stull, *Practical Meteorology* v1.02b (CC BY-NC-SA 4.0), ch. 14
  p. 496 — the one full sounding **table** in the book's parcel chapters
  with published answers (P_LCL = 87 kPa, P_LFC = 60 kPa, P_EL = 24 kPa,
  read off a full-size thermo diagram). The book's CAPE sample applications
  (1976 / 1874 J·kg⁻¹) belong to a *different*, figure-only sounding whose
  data is not machine-readable, so no published CAPE number exists for any
  published table: the CAPE assertion instead evaluates Stull's published
  **method** — eq. (14.5), the Rd·Σ(ΔT·Δln p) pressure integral — on the
  same curves, with the ~14% virtual-temperature systematic pinned in
  magnitude *and* direction. Fixture transcribed from the chapter PDF
  2026-07-26; a handful of numeric values used as facts, with citation.
  Unpublished upper-level environment dewpoints are documented placeholders
  that only enter `cape_cin`'s virtual correction. The published EL sits in
  the sounding's isothermal −35 °C layer where the crossing is
  formulation-hypersensitive (MetPy: 275 hPa vs Stull's diagram-read
  240 hPa): asserted as a window, divergence documented, not forced to zero
  (§7).
- **scipy (spec §10 item 14, resolved):** no direct consumer materialized —
  the shading interpolation is plain numpy — so the declaration drops from
  `requirements/pypi-core.txt`, `[tool.pixi.dependencies]`, and the
  `test_import.py` tuple. MetPy keeps scipy transitively: `pixi lock` is a
  verified byte-identical no-op.
- **Lint posture:** `# numpydoc ignore=GL08` on the two overload stubs; one
  `# type: ignore[arg-type]` for `set_axes_locator(None)`; `# noqa: PLR0913`
  on `_parcel_curve` (six parameters, all necessary); function-local imports
  carry `# noqa: PLC0415`. Codespell: never abbreviate environment temperature to a bare
  two-letter word in comments or docstrings (write `T_env`); write
  "unparsable".

---

## Task 1: The analysis-time exceptions

**Files:**
- Modify: `src/tephpy/exceptions.py`
- Test: `tests/test_exceptions.py`

**Interfaces:**
- Produces: `MissingDataError` and `ProfileTooShortError`, both
  `TephpyValidationError` subclasses (spec §6 lists them among its
  specializations). Tasks 4 and 5 raise them; Plan 6's `plot_barbs` will
  reuse `MissingDataError` for absent wind.

- [ ] **Step 1: Create the branch, then write the failing tests**

```bash
git switch -c analysis
```

In `tests/test_exceptions.py`, extend the `tephpy.exceptions` import to
(sorted):

```python
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    MissingDataError,
    NonMonotonicPressureError,
    ProfileTooShortError,
    TephpyError,
    TephpyUnitsError,
    TephpyValidationError,
)
```

In `test_hierarchy`, add the two new lines before the
`issubclass(TephpyError, Exception)` assertion (dedented listing — keep the
function-body indentation when pasting):

```python
assert issubclass(MissingDataError, TephpyValidationError)
assert issubclass(ProfileTooShortError, TephpyValidationError)
```

and extend `test_subclasses_carry_levels`'s parametrize list so the whole
decorated test reads:

```python
@pytest.mark.parametrize(
    "exception",
    [
        NonMonotonicPressureError,
        DewpointExceedsTemperatureError,
        MissingDataError,
        ProfileTooShortError,
    ],
)
def test_subclasses_carry_levels(exception):
    error = exception("boom", levels=(1,))
    assert error.levels == (1,)
    with pytest.raises(TephpyError):
        raise error
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_exceptions.py -q --no-cov`
Expected: FAIL — `ImportError: cannot import name 'MissingDataError'` (collection error is fine).

- [ ] **Step 3: Add the two exceptions**

In `src/tephpy/exceptions.py`, `__all__` becomes (sorted):

```python
__all__ = [
    "DewpointExceedsTemperatureError",
    "MissingDataError",
    "NonMonotonicPressureError",
    "ProfileTooShortError",
    "TephpyError",
    "TephpyUnitsError",
    "TephpyValidationError",
]
```

and append at the end of the module:

```python
class MissingDataError(TephpyValidationError):
    """The sounding lacks a field the requested operation needs (spec §6).

    Raised at the operation's boundary — the earliest point the need is
    knowable — e.g. parcel analysis without dewpoint, or (in a later
    release) wind barbs without wind.
    """


class ProfileTooShortError(TephpyValidationError):
    """The profile tops out at or below the parcel's LCL (spec §6).

    No moist ascent exists, so every parcel-derived quantity would be
    meaningless; ``calc.parcel_path`` and ``calc.indices`` both raise
    this. The LCL tested is the one the path would use — the corrected
    one when a cloud-base correction is requested.
    """
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_exceptions.py -q --no-cov`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/exceptions.py tests/test_exceptions.py
pixi run lint
git commit -m "feat: add the analysis-time MissingDataError and ProfileTooShortError"
```

---

## Task 2: The `calc` module with `Profile` and `SoundingIndices`

**Files:**
- Create: `src/tephpy/calc.py` (dataclasses only — Tasks 3–5 append the functions)
- Modify: `src/tephpy/__init__.py`
- Modify: `tests/test_import.py` (the `__all__` assertion)
- Test: `tests/test_calc.py`

**Interfaces:**
- Consumes: `as_quantity`/`check_units_mapping` (Plan 4's `_units`), `TephpyValidationError` (Plan 4).
- Produces: `Profile` and `SoundingIndices` per the contract above; `_PARCELS`, `_PROFILE_DIMENSIONS`, `_INDEX_DIMENSIONS` (module-private); `calc` exported eagerly at the top level (spec §10 item 10 — the existing subprocess import-cost guard in `tests/test_units.py` now polices `calc`'s function-local MetPy discipline for free).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_calc.py` — the import block is deliberately minimal
(later tasks extend it; unused imports fail this task's lint gate as F401):

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the thermodynamic analysis layer (spec §3.3/§6/§7).

Composition, not thermodynamics: ``indices()`` fields are asserted equal
to direct ``metpy.calc`` calls on the same profile, and the parcel path is
asserted to pass through Normand's point and follow the MetPy adiabats it
composes.
"""

from __future__ import annotations

from metpy.units import units
import numpy as np
import pytest

from tephpy.calc import Profile, SoundingIndices
from tephpy.exceptions import (
    TephpyUnitsError,
    TephpyValidationError,
)

Q = units.Quantity

# A plausible convective mid-latitude sounding (one uninterrupted CAPE
# region; CIN zero).
PRESSURE = Q(
    np.array(
        [1000.0, 950.0, 900.0, 850.0, 800.0, 700.0, 600.0, 500.0, 400.0, 300.0, 200.0]
    ),
    "hPa",
)
TEMPERATURE = Q(
    np.array([30.0, 25.0, 21.0, 18.0, 15.0, 8.0, -1.0, -12.0, -25.0, -42.0, -55.0]),
    "degC",
)
DEWPOINT = Q(
    np.array([21.0, 19.0, 17.0, 14.0, 10.0, 2.0, -8.0, -20.0, -35.0, -55.0, -70.0]),
    "degC",
)


# --- Profile ---------------------------------------------------------------


def test_profile_construction_from_bare_arrays_with_units():
    profile = Profile(
        [1000.0, 900.0, 800.0],
        [20.0, 12.0, 5.0],
        950.0,
        16.0,
        units={
            "pressure": "hPa",
            "temperature": "degC",
            "lcl_pressure": "hPa",
            "lcl_temperature": "degC",
        },
    )
    assert profile.pressure.check("[pressure]")
    assert profile.parcel == "surface"
    assert profile.label is None


def test_profile_requires_strictly_decreasing_pressure():
    with pytest.raises(TephpyValidationError, match="strictly decreasing") as info:
        Profile(
            Q([1000.0, 900.0, 950.0], "hPa"),
            Q([20.0, 12.0, 5.0], "degC"),
            Q(975.0, "hPa"),
            Q(18.0, "degC"),
        )
    assert info.value.levels == (2,)


def test_profile_rejects_increasing_pressure():
    """A Profile is stored surface-first; increasing input is not normalized."""
    with pytest.raises(TephpyValidationError, match="strictly decreasing"):
        Profile(
            Q([800.0, 900.0, 1000.0], "hPa"),
            Q([5.0, 12.0, 20.0], "degC"),
            Q(950.0, "hPa"),
            Q(16.0, "degC"),
        )


def test_profile_length_mismatch_raises():
    with pytest.raises(TephpyValidationError, match="equal length"):
        Profile(
            Q([1000.0, 900.0, 800.0], "hPa"),
            Q([20.0, 12.0], "degC"),
            Q(950.0, "hPa"),
            Q(16.0, "degC"),
        )


def test_profile_too_few_levels_raises():
    with pytest.raises(TephpyValidationError, match="at least 2 levels"):
        Profile(
            Q([1000.0], "hPa"), Q([20.0], "degC"), Q(1000.0, "hPa"), Q(20.0, "degC")
        )


def test_profile_non_1d_raises():
    with pytest.raises(TephpyValidationError, match="must be 1-D"):
        Profile(
            Q([[1000.0, 900.0]], "hPa"),
            Q([[20.0, 12.0]], "degC"),
            Q(950.0, "hPa"),
            Q(16.0, "degC"),
        )


def test_profile_lcl_must_be_scalar():
    with pytest.raises(TephpyValidationError, match="'lcl_pressure' must be a scalar"):
        Profile(
            Q([1000.0, 900.0], "hPa"),
            Q([20.0, 12.0], "degC"),
            Q([950.0], "hPa"),
            Q(16.0, "degC"),
        )


def test_profile_lcl_outside_span_raises():
    with pytest.raises(TephpyValidationError, match="inside the path's pressure span"):
        Profile(
            Q([1000.0, 900.0], "hPa"),
            Q([20.0, 12.0], "degC"),
            Q(850.0, "hPa"),
            Q(8.0, "degC"),
        )


def test_profile_nan_lcl_raises():
    with pytest.raises(TephpyValidationError, match="inside the path's pressure span"):
        Profile(
            Q([1000.0, 900.0], "hPa"),
            Q([20.0, 12.0], "degC"),
            Q(np.nan, "hPa"),
            Q(16.0, "degC"),
        )


def test_profile_unknown_parcel_raises():
    with pytest.raises(ValueError, match="parcel must be one of"):
        Profile(
            Q([1000.0, 900.0], "hPa"),
            Q([20.0, 12.0], "degC"),
            Q(950.0, "hPa"),
            Q(16.0, "degC"),
            parcel="bogus",
        )


# --- SoundingIndices -------------------------------------------------------


def _indices_kwargs(**overrides):
    """Scalar quantity values for every SoundingIndices field."""
    values = {
        "cape": Q(1500.0, "J/kg"),
        "cin": Q(-50.0, "J/kg"),
        "lcl_pressure": Q(900.0, "hPa"),
        "lcl_temperature": Q(15.0, "degC"),
        "lfc_pressure": Q(800.0, "hPa"),
        "lfc_temperature": Q(8.0, "degC"),
        "el_pressure": Q(250.0, "hPa"),
        "el_temperature": Q(-45.0, "degC"),
        "theta_w": Q(18.0, "degC"),
        "lifted_index": Q(-5.0, "delta_degC"),
    }
    values.update(overrides)
    return values


def test_sounding_indices_dimension_checked():
    with pytest.raises(TephpyUnitsError, match="'cape' has dimensionality"):
        SoundingIndices(**_indices_kwargs(cape=Q(1500.0, "hPa")))


def test_sounding_indices_requires_scalars():
    with pytest.raises(TephpyValidationError, match="'cape' must be a scalar"):
        SoundingIndices(**_indices_kwargs(cape=Q([1500.0], "J/kg")))


def test_sounding_indices_nan_fields_are_answers():
    """No cross-field validation: NaN LFC/EL fields construct fine."""
    result = SoundingIndices(
        **_indices_kwargs(
            lfc_pressure=Q(np.nan, "hPa"), lfc_temperature=Q(np.nan, "degC")
        )
    )
    assert np.isnan(result.lfc_pressure.magnitude)


def test_sounding_indices_bare_values_take_units_mapping():
    result = SoundingIndices(
        **{name: value.magnitude for name, value in _indices_kwargs().items()},
        units={
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
        },
    )
    assert result.cape.m_as("J/kg") == 1500.0


def test_sounding_indices_bare_value_without_units_raises():
    with pytest.raises(TephpyUnitsError, match="'cape' has no units"):
        SoundingIndices(**_indices_kwargs(cape=1500.0))
```

Also, in `tests/test_import.py`, the `expected` set in
`test_top_level_namespace` gains `"calc"` (dedented listing — keep the
function-body indentation when pasting):

```python
expected = {
    "Sounding",
    "__version__",
    "calc",
    "config",
    "exceptions",
    "plotting",
    "transforms",
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_calc.py tests/test_import.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'tephpy.calc'` (collection error is fine).

- [ ] **Step 3: Create the module and wire the top level**

**(a)** Create `src/tephpy/calc.py` — this exact code passes ruff (`ALL` +
format), mypy strict, and numpydoc-validation (verified 2026-07-26). The
module docstring intentionally describes the finished module (the Plan 3/4
precedent); `__all__` and the import block are extended by Tasks 3–5 as the
functions land. Dataclass fields are documented under **`Attributes`** and
`__post_init__` carries its own docstring (see Global Constraints):

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tephigram-native thermodynamic analysis over ``metpy.calc`` (spec §3.3).

Physics is delegated to MetPy; only tephigram-native compositions live
here, and everything returns pint quantities on the shared registry
(spec §5). Sounding-level functions take a :class:`~tephpy.sounding.Sounding`
— constructing one already validates units, monotonic pressure, and
dewpoint ≤ temperature — while :func:`normand_point` is the one
quantity-level function. MetPy stays behind function-local imports so that
``import tephpy`` stays light (spec §10 item 10).

Analysis results distinguish "does not exist" from "zero" (spec §6):
``metpy.calc`` returns NaN quantities for a missing LFC/EL and ``0 J/kg``
— never NaN — for zero CAPE/CIN, and tephpy passes both through,
documented per :class:`SoundingIndices` field.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Final, Literal

import numpy as np

from tephpy._units import as_quantity, check_units_mapping
from tephpy.exceptions import (
    TephpyValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pint

__all__ = ["Profile", "SoundingIndices"]

#: The parcel-selection options (spec §3.3).
_PARCELS: Final[tuple[str, ...]] = ("surface", "mixed-layer")

#: The ``Profile`` data fields with their required dimensionalities (spec §5).
_PROFILE_DIMENSIONS: Final[dict[str, str]] = {
    "pressure": "[pressure]",
    "temperature": "[temperature]",
    "lcl_pressure": "[pressure]",
    "lcl_temperature": "[temperature]",
}

#: The ``SoundingIndices`` fields with their required dimensionalities
#: (spec §5). CAPE/CIN are specific energies (J/kg); the lifted index is a
#: temperature difference, so its pint dimensionality is a temperature.
_INDEX_DIMENSIONS: Final[dict[str, str]] = {
    "cape": "[energy] / [mass]",
    "cin": "[energy] / [mass]",
    "lcl_pressure": "[pressure]",
    "lcl_temperature": "[temperature]",
    "lfc_pressure": "[pressure]",
    "lfc_temperature": "[temperature]",
    "el_pressure": "[pressure]",
    "el_temperature": "[temperature]",
    "theta_w": "[temperature]",
    "lifted_index": "[temperature]",
}


@dataclasses.dataclass(frozen=True, eq=False)
class Profile:
    """One computed parcel ascent, ready to plot (spec §3.3).

    Plain plottable data: ``plot_profile`` draws it and the shading
    builders consume it, and neither re-derives the LCL. Construction
    mirrors ``Sounding``: bare arrays take the ``units=`` mapping, fields
    are dimension-checked quantities on the shared registry, and
    validation happens at construction.

    Attributes
    ----------
    pressure : pint.Quantity
        Path pressures, surface-first (strictly decreasing), at least two
        levels.
    temperature : pint.Quantity
        Parcel temperatures along the path.
    lcl_pressure : pint.Quantity
        Scalar pressure of the Normand's point the path actually uses —
        the corrected one when a correction was requested — inside the
        path's pressure span.
    lcl_temperature : pint.Quantity
        Scalar temperature at that point.
    parcel : str
        The lifted parcel: ``"surface"`` or ``"mixed-layer"``.
    label : str or None
        Legend text; ``None`` means no legend entry.
    units : mapping of str to str, optional
        Construction-only (not stored): unit strings for bare-array
        fields, keyed by field name (spec §5).
    """

    pressure: pint.Quantity
    temperature: pint.Quantity
    lcl_pressure: pint.Quantity
    lcl_temperature: pint.Quantity
    parcel: Literal["surface", "mixed-layer"] = "surface"
    label: str | None = None
    units: dataclasses.InitVar[Mapping[str, str] | None] = None

    def __post_init__(self, units: Mapping[str, str] | None) -> None:
        """Coerce and validate the constructed profile.

        Parameters
        ----------
        units : mapping of str to str or None
            The ``units=`` mapping for bare-array fields.
        """
        mapping = check_units_mapping(units, allowed=_PROFILE_DIMENSIONS)
        for name, dimension in _PROFILE_DIMENSIONS.items():
            quantity = as_quantity(
                getattr(self, name),
                name=name,
                units=mapping.get(name),
                dimension=dimension,
            )
            object.__setattr__(self, name, quantity)
        self._validate_arrays()
        self._validate_lcl()
        if self.parcel not in _PARCELS:
            msg = f"parcel must be one of {_PARCELS!r}, got {self.parcel!r}"
            raise ValueError(msg)

    def _validate_arrays(self) -> None:
        """Require 1-D equal-length arrays with strictly decreasing pressure."""
        pressure = self.pressure.magnitude
        temperature = self.temperature.magnitude
        for name, magnitude in (("pressure", pressure), ("temperature", temperature)):
            if magnitude.ndim != 1:
                msg = f"{name!r} must be 1-D, got {magnitude.ndim}-D"
                raise TephpyValidationError(msg)
        if pressure.size != temperature.size:
            msg = (
                "pressure and temperature must be equal length, got "
                f"{pressure.size} and {temperature.size}"
            )
            raise TephpyValidationError(msg)
        if pressure.size < 2:
            msg = f"a profile needs at least 2 levels, got {pressure.size}"
            raise TephpyValidationError(msg)
        offending = np.flatnonzero(~(np.diff(pressure) < 0.0)) + 1
        if offending.size:
            levels = tuple(int(index) for index in offending)
            msg = (
                "profile pressure must be strictly decreasing "
                f"(surface-first); offending levels {levels}"
            )
            raise TephpyValidationError(msg, levels=levels)

    def _validate_lcl(self) -> None:
        """Require a scalar LCL inside the path's pressure span."""
        for name in ("lcl_pressure", "lcl_temperature"):
            magnitude = getattr(self, name).magnitude
            if magnitude.ndim != 0:
                msg = f"{name!r} must be a scalar, got shape {magnitude.shape}"
                raise TephpyValidationError(msg)
        pressure = self.pressure.m_as("hPa")
        lcl = float(self.lcl_pressure.m_as("hPa"))
        if not pressure[-1] <= lcl <= pressure[0]:
            msg = (
                f"lcl_pressure ({lcl:g} hPa) must lie inside the path's "
                f"pressure span [{pressure[-1]:g}, {pressure[0]:g}] hPa"
            )
            raise TephpyValidationError(msg)


@dataclasses.dataclass(frozen=True, eq=False)
class SoundingIndices:
    """Derived thermodynamic parameters for one sounding (spec §3.3).

    Ten scalar quantity fields, each dimension-checked at construction.
    There is no cross-field validation: NaN fields are answers, not
    errors — analysis results distinguish "does not exist" (NaN) from
    "zero" (spec §6).

    Attributes
    ----------
    cape : pint.Quantity
        Convective available potential energy (J/kg); ``0 J/kg`` — never
        NaN — when the parcel has no positive-buoyancy region.
    cin : pint.Quantity
        Convective inhibition (J/kg, non-positive); ``0 J/kg`` when there
        is no LFC or no negative-buoyancy region below it.
    lcl_pressure : pint.Quantity
        Pressure of the lifting condensation level the parcel uses (the
        corrected one when a correction was requested); always defined.
    lcl_temperature : pint.Quantity
        Temperature at that level; always defined.
    lfc_pressure : pint.Quantity
        Pressure of the level of free convection; NaN when the parcel
        never becomes positively buoyant.
    lfc_temperature : pint.Quantity
        Temperature at that level; NaN with `lfc_pressure`.
    el_pressure : pint.Quantity
        Pressure of the equilibrium level; NaN when it does not exist —
        including while ``cape > 0`` with the parcel still buoyant at the
        profile top.
    el_temperature : pint.Quantity
        Temperature at that level; NaN with `el_pressure`.
    theta_w : pint.Quantity
        Wet-bulb potential temperature of the lifted parcel, evaluated at
        the parcel start, so it follows the ``parcel=`` option; always
        defined.
    lifted_index : pint.Quantity
        Lifted index (a temperature difference at 500 hPa); NaN when the
        profile tops out below 500 hPa.
    units : mapping of str to str, optional
        Construction-only (not stored): unit strings for bare scalar
        fields, keyed by field name (spec §5).
    """

    cape: pint.Quantity
    cin: pint.Quantity
    lcl_pressure: pint.Quantity
    lcl_temperature: pint.Quantity
    lfc_pressure: pint.Quantity
    lfc_temperature: pint.Quantity
    el_pressure: pint.Quantity
    el_temperature: pint.Quantity
    theta_w: pint.Quantity
    lifted_index: pint.Quantity
    units: dataclasses.InitVar[Mapping[str, str] | None] = None

    def __post_init__(self, units: Mapping[str, str] | None) -> None:
        """Coerce and dimension-check the constructed indices.

        Parameters
        ----------
        units : mapping of str to str or None
            The ``units=`` mapping for bare scalar fields.
        """
        mapping = check_units_mapping(units, allowed=_INDEX_DIMENSIONS)
        for name, dimension in _INDEX_DIMENSIONS.items():
            quantity = as_quantity(
                getattr(self, name),
                name=name,
                units=mapping.get(name),
                dimension=dimension,
            )
            if quantity.magnitude.ndim != 0:
                msg = f"{name!r} must be a scalar, got shape {quantity.magnitude.shape}"
                raise TephpyValidationError(msg)
            object.__setattr__(self, name, quantity)
```

(The one-element `from tephpy.exceptions import (...)` parenthesized form is
deliberate — Tasks 3–5 grow it without reformatting churn; ruff accepts
both forms.)

**(b)** Update `src/tephpy/__init__.py` — the subpackage import and
`__all__` become:

```python
from tephpy import calc, exceptions, plotting, transforms
from tephpy._config import config
from tephpy.sounding import Sounding

__all__ = [
    "Sounding",
    "__version__",
    "calc",
    "config",
    "exceptions",
    "plotting",
    "transforms",
]
```

(`calc` is cheap by construction — no module-level MetPy import — so the
eager re-export costs nothing; spec §10 item 10, resolved.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_calc.py tests/test_import.py tests/test_units.py -q --no-cov`
Expected: PASS — including the subprocess import-cost guard, which now
proves `import tephpy` (with `calc` wired in) still leaves metpy
unimported.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/calc.py src/tephpy/__init__.py tests/test_calc.py tests/test_import.py
pixi run lint
git commit -m "feat: add the calc module with the Profile and SoundingIndices dataclasses"
```

---

## Task 3: `normand_point`

**Files:**
- Modify: `src/tephpy/calc.py` (append)
- Test: `tests/test_calc.py` (append)

**Interfaces:**
- Consumes: `as_quantity`/`check_units_mapping`; `DewpointExceedsTemperatureError` (existing), `TephpyValidationError`.
- Produces: `normand_point(pressure, temperature, dewpoint, *, units=None) -> tuple[pint.Quantity, pint.Quantity]` and the module-private `_scalar_quantity` helper. Task 4's `_lcl_used` composes `normand_point`; Tasks 4–5 reuse `_scalar_quantity` for the correction argument.

- [ ] **Step 1: Write the failing tests**

In `tests/test_calc.py`, extend the import block — `import metpy.calc as
mpcalc` joins the third-party imports (first line of that block; ruff
sorts `metpy` before `numpy`), `normand_point` joins the `tephpy.calc`
import, and `DewpointExceedsTemperatureError` the exceptions import:

```python
import metpy.calc as mpcalc
from metpy.units import units
import numpy as np
import pytest

from tephpy.calc import Profile, SoundingIndices, normand_point
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    TephpyUnitsError,
    TephpyValidationError,
)
```

then append to the end of the file:

```python
# --- normand_point ---------------------------------------------------------


def test_normand_point_is_the_metpy_lcl():
    result = normand_point(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0])
    expected = mpcalc.lcl(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0])
    assert result[0].m_as("hPa") == expected[0].m_as("hPa")
    assert result[1].m_as("degC") == pytest.approx(expected[1].m_as("degC"))
    assert result[0].units == units.hPa
    assert result[1].units == units.degC


def test_normand_point_bare_values_with_units():
    result = normand_point(
        1000.0,
        30.0,
        21.0,
        units={"pressure": "hPa", "temperature": "degC", "dewpoint": "degC"},
    )
    expected = normand_point(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0])
    assert result[0].m_as("hPa") == pytest.approx(expected[0].m_as("hPa"))


def test_normand_point_bare_values_without_units_raise():
    with pytest.raises(TephpyUnitsError, match="'pressure' has no units"):
        normand_point(1000.0, TEMPERATURE[0], DEWPOINT[0])


def test_normand_point_unknown_units_key_raises():
    with pytest.raises(TephpyUnitsError, match="unknown argument"):
        normand_point(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0], units={"bogus": "hPa"})


def test_normand_point_wrong_dimension_raises():
    with pytest.raises(TephpyUnitsError, match="'pressure' has dimensionality"):
        normand_point(TEMPERATURE[0], PRESSURE[0], DEWPOINT[0])


def test_normand_point_non_scalar_raises():
    with pytest.raises(TephpyValidationError, match="must be a scalar"):
        normand_point(PRESSURE, TEMPERATURE[0], DEWPOINT[0])


def test_normand_point_dewpoint_above_temperature_raises():
    with pytest.raises(DewpointExceedsTemperatureError):
        normand_point(PRESSURE[0], TEMPERATURE[0], Q(31.0, "degC"))


def test_normand_point_saturation_is_the_parcel():
    """At saturation the Normand's point is the parcel itself."""
    pressure, temperature = normand_point(PRESSURE[0], TEMPERATURE[0], TEMPERATURE[0])
    assert pressure.m_as("hPa") == pytest.approx(1000.0)
    assert temperature.m_as("degC") == pytest.approx(30.0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_calc.py -q --no-cov`
Expected: FAIL — `ImportError: cannot import name 'normand_point'` (collection error is fine).

- [ ] **Step 3: Implement**

In `src/tephpy/calc.py`:

**(a)** The exceptions import gains `DewpointExceedsTemperatureError`
(sorted) and `__all__` gains `"normand_point"`:

```python
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    TephpyValidationError,
)
```

```python
__all__ = ["Profile", "SoundingIndices", "normand_point"]
```

**(b)** Append at the end of the module:

```python
def normand_point(
    pressure: object,
    temperature: object,
    dewpoint: object,
    *,
    units: Mapping[str, str] | None = None,
) -> tuple[pint.Quantity, pint.Quantity]:
    """Construct Normand's point — the LCL — for one parcel (spec §3.3).

    The geometric construction: the dry adiabat through (`pressure`,
    `temperature`) meets the humidity mixing-ratio line through
    (`pressure`, `dewpoint`) at the lifting condensation level. This is
    always the uncorrected construction; the operational cloud-base
    correction is :func:`parcel_path`'s concern.

    Parameters
    ----------
    pressure : pint.Quantity or float
        Scalar parcel pressure; a bare value takes the ``units=`` mapping.
    temperature : pint.Quantity or float
        Scalar parcel temperature.
    dewpoint : pint.Quantity or float
        Scalar parcel dewpoint; must not exceed `temperature` (equality —
        saturation — is physical, and puts Normand's point at the parcel).
    units : mapping of str to str, optional
        Unit strings for bare values, keyed by argument name, e.g.
        ``units={"pressure": "hPa", "temperature": "degC"}`` (spec §5).

    Returns
    -------
    tuple of pint.Quantity
        The scalar ``(pressure, temperature)`` of Normand's point, in
        hPa and degrees Celsius.

    Raises
    ------
    TephpyUnitsError
        For unit-less bare values, ambiguous or unparsable units, or the
        wrong dimensionality.
    DewpointExceedsTemperatureError
        If `dewpoint` exceeds `temperature`.
    TephpyValidationError
        If an argument is not a scalar.
    """
    mapping = check_units_mapping(
        units, allowed=("pressure", "temperature", "dewpoint")
    )
    p = _scalar_quantity(pressure, "pressure", mapping, "[pressure]")
    t = _scalar_quantity(temperature, "temperature", mapping, "[temperature]")
    td = _scalar_quantity(dewpoint, "dewpoint", mapping, "[temperature]")
    if float(td.m_as("degC")) > float(t.m_as("degC")):
        msg = (
            "dewpoint exceeds temperature (equality is saturation and "
            "accepted); no Normand's point exists"
        )
        raise DewpointExceedsTemperatureError(msg)
    # Function-local so `import tephpy` stays light (spec §3.3, §10 item 10).
    from metpy.calc import lcl  # noqa: PLC0415

    lcl_pressure, lcl_temperature = lcl(p, t, td)
    return lcl_pressure.to("hPa"), lcl_temperature.to("degC")


def _scalar_quantity(
    value: object, name: str, mapping: Mapping[str, str], dimension: str
) -> pint.Quantity:
    """Coerce one scalar boundary argument (spec §5).

    Parameters
    ----------
    value : object
        The argument value: a pint quantity, or a bare value with a
        `mapping` entry.
    name : str
        The argument name, used in error messages.
    mapping : mapping of str to str
        The boundary's validated ``units=`` mapping.
    dimension : str
        The required pint dimensionality.

    Returns
    -------
    pint.Quantity
        The scalar quantity on MetPy's registry.

    Raises
    ------
    TephpyUnitsError
        For unit-less bare values, ambiguous or unparsable units, or the
        wrong dimensionality.
    TephpyValidationError
        If the value is not a scalar.
    """
    quantity = as_quantity(
        value, name=name, units=mapping.get(name), dimension=dimension
    )
    if quantity.magnitude.ndim != 0:
        msg = f"{name!r} must be a scalar, got shape {quantity.magnitude.shape}"
        raise TephpyValidationError(msg)
    return quantity
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_calc.py -q --no-cov`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/calc.py tests/test_calc.py
pixi run lint
git commit -m "feat: add normand_point, the geometric LCL construction"
```

---

## Task 4: `parcel_path`

**Files:**
- Modify: `src/tephpy/calc.py` (append)
- Test: `tests/test_calc.py` (append)

**Interfaces:**
- Consumes: `Profile` (Task 2), `normand_point`/`_scalar_quantity` (Task 3), `MissingDataError`/`ProfileTooShortError` (Task 1), `MOIST_ADIABAT_PRESSURE_STEP` (Plan 3's `_constants`).
- Produces: `parcel_path(snd, *, parcel="surface", cloud_base_correction=None, label=None) -> Profile`, plus the module-private helpers `_parcel_start`, `_lcl_used`, and `_require_moist_ascent` that Task 5's `indices` reuses (exact signatures in the listing).

- [ ] **Step 1: Write the failing tests**

In `tests/test_calc.py`, extend the import block to (its final Task 4
state — `import tephpy`, `Sounding`, the `_constants` step, `parcel_path`,
and the two Task 1 exceptions join in):

```python
import metpy.calc as mpcalc
from metpy.units import units
import numpy as np
import pytest

import tephpy
from tephpy import Sounding
from tephpy._constants import MOIST_ADIABAT_PRESSURE_STEP
from tephpy.calc import Profile, SoundingIndices, normand_point, parcel_path
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    MissingDataError,
    ProfileTooShortError,
    TephpyUnitsError,
    TephpyValidationError,
)
```

then append to the end of the file:

```python
# --- parcel_path -----------------------------------------------------------


def _sounding(**kwargs):
    """Build the module's reference convective sounding."""
    return Sounding(PRESSURE, TEMPERATURE, dewpoint=DEWPOINT, **kwargs)


def test_calc_reexports_eagerly():
    """`tephpy.calc.parcel_path` works after `import tephpy` (spec §4)."""
    assert tephpy.calc.parcel_path is parcel_path
    assert tephpy.calc.Profile is Profile


def test_parcel_path_passes_through_normand_point():
    """The LCL vertex is spliced into the path exactly (spec §3.3/§7)."""
    profile = parcel_path(_sounding())
    lcl_pressure, lcl_temperature = normand_point(
        PRESSURE[0], TEMPERATURE[0], DEWPOINT[0]
    )
    assert profile.lcl_pressure.m_as("hPa") == lcl_pressure.m_as("hPa")
    position = np.flatnonzero(profile.pressure.m_as("hPa") == lcl_pressure.m_as("hPa"))
    assert position.size == 1
    assert profile.temperature.m_as("degC")[position[0]] == pytest.approx(
        lcl_temperature.m_as("degC")
    )


def test_parcel_path_spans_start_to_top():
    profile = parcel_path(_sounding())
    pressure = profile.pressure.m_as("hPa")
    assert pressure[0] == PRESSURE[0].m_as("hPa")
    assert pressure[-1] == PRESSURE[-1].m_as("hPa")
    assert np.all(np.diff(pressure) < 0.0)


def test_parcel_path_samples_the_background_step():
    """Both legs sample the moist-adiabat family's 5 hPa step (spec §3.3)."""
    profile = parcel_path(_sounding())
    pressure = profile.pressure.m_as("hPa")
    lcl = profile.lcl_pressure.m_as("hPa")
    dry = pressure[pressure > lcl]
    moist = pressure[pressure < lcl]
    np.testing.assert_allclose(np.diff(dry), -MOIST_ADIABAT_PRESSURE_STEP)
    np.testing.assert_allclose(np.diff(moist)[:-1], -MOIST_ADIABAT_PRESSURE_STEP)


def test_parcel_path_dry_leg_follows_the_dry_adiabat():
    profile = parcel_path(_sounding())
    pressure = profile.pressure.m_as("hPa")
    lcl = profile.lcl_pressure.m_as("hPa")
    dry = pressure > lcl
    expected = mpcalc.dry_lapse(
        Q(pressure[dry], "hPa"), TEMPERATURE[0], reference_pressure=PRESSURE[0]
    )
    np.testing.assert_allclose(
        profile.temperature.m_as("degC")[dry], expected.m_as("degC")
    )


def test_parcel_path_moist_leg_is_anchored_at_the_lcl():
    """The moist leg is moist_lapse(..., reference_pressure=p_lcl) (spec §3.3)."""
    profile = parcel_path(_sounding())
    pressure = profile.pressure.m_as("hPa")
    lcl = profile.lcl_pressure.m_as("hPa")
    moist = pressure < lcl
    expected = mpcalc.moist_lapse(
        Q(pressure[moist], "hPa"),
        profile.lcl_temperature,
        reference_pressure=profile.lcl_pressure,
    )
    np.testing.assert_allclose(
        profile.temperature.m_as("degC")[moist], expected.m_as("degC")
    )


def test_parcel_path_fields_and_label():
    anonymous = parcel_path(_sounding())
    assert anonymous.parcel == "surface"
    assert anonymous.label is None
    labelled = parcel_path(_sounding(), label="surface parcel")
    assert labelled.label == "surface parcel"


def test_parcel_path_mixed_layer_starts_at_the_mixed_parcel():
    profile = parcel_path(_sounding(), parcel="mixed-layer")
    start_pressure, start_temperature, _ = mpcalc.mixed_parcel(
        PRESSURE, TEMPERATURE, DEWPOINT
    )
    assert profile.parcel == "mixed-layer"
    assert profile.pressure[0].m_as("hPa") == start_pressure.m_as("hPa")
    assert profile.temperature[0].m_as("degC") == pytest.approx(
        start_temperature.m_as("degC")
    )


def test_parcel_path_correction_applied_only_when_requested():
    """The -25 mb correction moves the LCL only when asked (spec §3.3)."""
    plain = parcel_path(_sounding())
    corrected = parcel_path(_sounding(), cloud_base_correction=Q(-25.0, "hPa"))
    assert corrected.lcl_pressure.m_as("hPa") == pytest.approx(
        plain.lcl_pressure.m_as("hPa") - 25.0
    )
    expected_temperature = mpcalc.dry_lapse(
        corrected.lcl_pressure, TEMPERATURE[0], reference_pressure=PRESSURE[0]
    )
    assert corrected.lcl_temperature.m_as("degC") == pytest.approx(
        expected_temperature.m_as("degC")
    )


def test_parcel_path_saturated_parcel_has_no_dry_leg():
    """A saturated surface parcel ascends moist from its start."""
    snd = Sounding(PRESSURE, TEMPERATURE, dewpoint=TEMPERATURE)
    profile = parcel_path(snd)
    assert profile.lcl_pressure.m_as("hPa") == pytest.approx(1000.0)
    assert profile.pressure[0].m_as("hPa") == pytest.approx(1000.0)


def test_parcel_path_missing_dewpoint_raises():
    snd = Sounding(PRESSURE, TEMPERATURE)
    with pytest.raises(MissingDataError, match="needs dewpoint"):
        parcel_path(snd)


def test_parcel_path_unknown_parcel_raises():
    with pytest.raises(ValueError, match="parcel must be one of"):
        parcel_path(_sounding(), parcel="bogus")


def test_parcel_path_profile_too_short_raises():
    """A profile topping out at or below the LCL has no moist ascent."""
    snd = Sounding(PRESSURE[:2], TEMPERATURE[:2], dewpoint=DEWPOINT[:2])
    with pytest.raises(ProfileTooShortError, match="no moist ascent"):
        parcel_path(snd)


def test_parcel_path_corrected_lcl_above_top_raises():
    """The too-short test uses the corrected LCL when one is requested."""
    with pytest.raises(ProfileTooShortError, match="no moist ascent"):
        parcel_path(_sounding(), cloud_base_correction=Q(-700.0, "hPa"))


def test_parcel_path_correction_below_start_raises():
    with pytest.raises(TephpyValidationError, match=r"below the .* parcel start"):
        parcel_path(_sounding(), cloud_base_correction=Q(200.0, "hPa"))


def test_parcel_path_correction_wrong_dimension_raises():
    with pytest.raises(TephpyUnitsError, match="'cloud_base_correction'"):
        parcel_path(_sounding(), cloud_base_correction=Q(-25.0, "degC"))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_calc.py -q --no-cov`
Expected: FAIL — `ImportError: cannot import name 'parcel_path'` (collection error is fine).

- [ ] **Step 3: Implement**

In `src/tephpy/calc.py`:

**(a)** The module-level imports gain the two Task 1 exceptions and the
`_constants` step (each block sorted):

```python
from tephpy._constants import MOIST_ADIABAT_PRESSURE_STEP
from tephpy._units import as_quantity, check_units_mapping
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    MissingDataError,
    ProfileTooShortError,
    TephpyValidationError,
)
```

the `TYPE_CHECKING` block gains `Sounding` (annotation-only — the §3
layering means `calc` consumes the object it is handed):

```python
if TYPE_CHECKING:
    from collections.abc import Mapping

    import pint

    from tephpy.sounding import Sounding
```

and `__all__` becomes:

```python
__all__ = ["Profile", "SoundingIndices", "normand_point", "parcel_path"]
```

**(b)** Append at the end of the module:

```python
def parcel_path(
    snd: Sounding,
    *,
    parcel: Literal["surface", "mixed-layer"] = "surface",
    cloud_base_correction: object = None,
    label: str | None = None,
) -> Profile:
    """Compute a parcel's ascent path over the sounding's span (spec §3.3).

    Dry adiabat from the parcel start to Normand's point, then moist
    adiabat to the profile top. Both legs sample the background moist
    adiabats' 5 hPa step, the moist leg is integrated with
    ``metpy.calc.moist_lapse(..., reference_pressure=lcl_pressure)`` —
    same integrator, same sampling, same anchoring as the background
    family — and the LCL vertex is spliced in exactly.

    Parameters
    ----------
    snd : Sounding
        The environment sounding; must carry dewpoint.
    parcel : str, default: "surface"
        The lifted parcel: ``"surface"`` starts from the lowest level;
        ``"mixed-layer"`` starts from ``metpy.calc.mixed_parcel`` (its
        100 hPa default depth is the operational convention).
    cloud_base_correction : pint.Quantity, optional
        A pressure-dimension correction added to the LCL pressure, applied
        only when explicitly requested; the operational -25 mb value lives
        in ``tephpy._constants.CLOUD_BASE_CORRECTION``. The corrected LCL
        temperature is re-read from the dry adiabat at the corrected
        pressure.
    label : str, optional
        Legend text for the profile; ``None`` means no legend entry.

    Returns
    -------
    Profile
        The parcel path, surface-first, with the LCL it actually uses.

    Raises
    ------
    MissingDataError
        If the sounding has no dewpoint.
    ProfileTooShortError
        If the profile tops out at or below the LCL the path would use
        (the corrected one when a correction is requested).
    TephpyUnitsError
        If `cloud_base_correction` is not a pressure-dimension quantity.
    TephpyValidationError
        If the correction places the LCL below the parcel start.
    ValueError
        If `parcel` is not a known option.
    """
    start_pressure, start_temperature, start_dewpoint = _parcel_start(snd, parcel)
    lcl_pressure, lcl_temperature = _lcl_used(
        start_pressure, start_temperature, start_dewpoint, cloud_base_correction
    )
    _require_moist_ascent(snd, lcl_pressure)
    # Function-local so `import tephpy` stays light (spec §3.3, §10 item 10).
    from metpy.calc import dry_lapse, moist_lapse  # noqa: PLC0415
    from metpy.units import units as registry  # noqa: PLC0415

    p0 = float(start_pressure.m_as("hPa"))
    lcl_hpa = float(lcl_pressure.m_as("hPa"))
    top = float(snd.pressure[-1].m_as("hPa"))
    step = MOIST_ADIABAT_PRESSURE_STEP
    dry_pressure = np.arange(p0, lcl_hpa, -step)
    moist_pressure = np.concatenate([np.arange(lcl_hpa - step, top, -step), [top]])
    if dry_pressure.size:
        dry_temperature = dry_lapse(
            registry.Quantity(dry_pressure, "hPa"),
            start_temperature,
            reference_pressure=start_pressure,
        ).m_as("degC")
    else:  # A saturated parcel: Normand's point is the parcel start.
        dry_temperature = np.empty(0, dtype=np.float64)
    moist_temperature = moist_lapse(
        registry.Quantity(moist_pressure, "hPa"),
        lcl_temperature,
        reference_pressure=lcl_pressure,
    ).m_as("degC")
    pressure = np.concatenate([dry_pressure, [lcl_hpa], moist_pressure])
    temperature = np.concatenate(
        [dry_temperature, [float(lcl_temperature.m_as("degC"))], moist_temperature]
    )
    return Profile(
        pressure=registry.Quantity(pressure, "hPa"),
        temperature=registry.Quantity(temperature, "degC"),
        lcl_pressure=lcl_pressure,
        lcl_temperature=lcl_temperature,
        parcel=parcel,
        label=label,
    )


def _parcel_start(
    snd: Sounding, parcel: str
) -> tuple[pint.Quantity, pint.Quantity, pint.Quantity]:
    """Select the lifted parcel's starting point (spec §3.3).

    Parameters
    ----------
    snd : Sounding
        The environment sounding.
    parcel : str
        The parcel option: ``"surface"`` or ``"mixed-layer"``.

    Returns
    -------
    tuple of pint.Quantity
        Scalar ``(pressure, temperature, dewpoint)`` of the parcel start.

    Raises
    ------
    MissingDataError
        If the sounding has no dewpoint.
    ValueError
        If `parcel` is not a known option.
    """
    if parcel not in _PARCELS:
        msg = f"parcel must be one of {_PARCELS!r}, got {parcel!r}"
        raise ValueError(msg)
    if snd.dewpoint is None:
        msg = "parcel analysis needs dewpoint: this sounding has none (spec §3.4)"
        raise MissingDataError(msg)
    if parcel == "mixed-layer":
        # Function-local so `import tephpy` stays light (spec §10 item 10).
        from metpy.calc import mixed_parcel  # noqa: PLC0415

        pressure, temperature, dewpoint = mixed_parcel(
            snd.pressure, snd.temperature, snd.dewpoint
        )
        return pressure.to("hPa"), temperature.to("degC"), dewpoint.to("degC")
    return snd.pressure[0], snd.temperature[0], snd.dewpoint[0]


def _lcl_used(
    start_pressure: pint.Quantity,
    start_temperature: pint.Quantity,
    start_dewpoint: pint.Quantity,
    cloud_base_correction: object,
) -> tuple[pint.Quantity, pint.Quantity]:
    """Locate the LCL the ascent uses, applying any requested correction.

    Parameters
    ----------
    start_pressure : pint.Quantity
        Scalar parcel-start pressure.
    start_temperature : pint.Quantity
        Scalar parcel-start temperature.
    start_dewpoint : pint.Quantity
        Scalar parcel-start dewpoint.
    cloud_base_correction : pint.Quantity or None
        The pressure-dimension correction, or ``None`` for the plain
        Normand's point.

    Returns
    -------
    tuple of pint.Quantity
        The scalar ``(pressure, temperature)`` of the LCL the path uses,
        in hPa and degrees Celsius. The corrected LCL temperature is
        re-read from the dry adiabat at the corrected pressure.

    Raises
    ------
    TephpyUnitsError
        If the correction is not a pressure-dimension quantity.
    TephpyValidationError
        If the correction places the LCL below the parcel start.
    """
    lcl_pressure, lcl_temperature = normand_point(
        start_pressure, start_temperature, start_dewpoint
    )
    if cloud_base_correction is None:
        return lcl_pressure, lcl_temperature
    correction = _scalar_quantity(
        cloud_base_correction, "cloud_base_correction", {}, "[pressure]"
    )
    corrected = (lcl_pressure + correction).to("hPa")
    if float(corrected.m_as("hPa")) > float(start_pressure.m_as("hPa")):
        msg = (
            f"cloud_base_correction ({correction:~P}) places the LCL at "
            f"{corrected:~P}, below the {start_pressure:~P} parcel start"
        )
        raise TephpyValidationError(msg)
    # Function-local so `import tephpy` stays light (spec §10 item 10).
    from metpy.calc import dry_lapse  # noqa: PLC0415

    corrected_temperature = dry_lapse(
        corrected, start_temperature, reference_pressure=start_pressure
    )
    return corrected, corrected_temperature.to("degC")


def _require_moist_ascent(snd: Sounding, lcl_pressure: pint.Quantity) -> None:
    """Require the profile to extend above the LCL the ascent uses.

    Parameters
    ----------
    snd : Sounding
        The environment sounding.
    lcl_pressure : pint.Quantity
        Scalar pressure of the LCL the ascent uses.

    Raises
    ------
    ProfileTooShortError
        If the profile tops out at or below the LCL — no moist ascent
        exists (spec §6).
    """
    top = float(snd.pressure[-1].m_as("hPa"))
    lcl_hpa = float(lcl_pressure.m_as("hPa"))
    if top >= lcl_hpa:
        msg = (
            f"the profile tops out at {top:g} hPa, at or below the parcel's "
            f"{lcl_hpa:g} hPa LCL: no moist ascent exists"
        )
        raise ProfileTooShortError(msg)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_calc.py -q --no-cov`
Expected: PASS (the moist-lapse ODE makes this module a second or two
slower than the pure-validation tasks).

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/calc.py tests/test_calc.py
pixi run lint
git commit -m "feat: add parcel_path with mixed-layer parcels and the cloud-base correction"
```

---

## Task 5: `indices`

**Files:**
- Modify: `src/tephpy/calc.py` (append)
- Test: `tests/test_calc.py` (append)

**Interfaces:**
- Consumes: `SoundingIndices` (Task 2), `_parcel_start`/`_lcl_used`/`_require_moist_ascent` (Task 4).
- Produces: `indices(snd, *, parcel="surface", cloud_base_correction=None) -> SoundingIndices` and the module-private `_parcel_curve`. This completes `tephpy.calc`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_calc.py`, the `tephpy.calc` import reaches its final form:

```python
from tephpy.calc import Profile, SoundingIndices, indices, normand_point, parcel_path
```

then append to the end of the file:

```python
# --- indices ---------------------------------------------------------------

# A stable sounding: no positive buoyancy anywhere (zero CAPE).
STABLE_TEMPERATURE = Q(
    np.array([5.0, 4.0, 3.5, 3.0, 2.0, -2.0, -8.0, -16.0, -28.0, -44.0, -58.0]),
    "degC",
)
STABLE_DEWPOINT = Q(
    np.array([-5.0, -6.0, -7.0, -9.0, -12.0, -18.0, -25.0, -35.0, -45.0, -60.0, -75.0]),
    "degC",
)


def _direct_indices(pressure, temperature, dewpoint, curve, start):
    """Compute the ten fields by direct metpy.calc delegation (spec §7)."""
    cape, cin = mpcalc.cape_cin(pressure, temperature, dewpoint, curve)
    lfc_pressure, lfc_temperature = mpcalc.lfc(
        pressure, temperature, dewpoint, parcel_temperature_profile=curve
    )
    el_pressure, el_temperature = mpcalc.el(
        pressure, temperature, dewpoint, parcel_temperature_profile=curve
    )
    lifted = mpcalc.lifted_index(pressure, temperature, curve)[0]
    theta_w = mpcalc.wet_bulb_potential_temperature(*start)
    return (
        cape,
        cin,
        lfc_pressure,
        lfc_temperature,
        el_pressure,
        el_temperature,
        lifted,
        theta_w,
    )


def _assert_indices_equal(result, direct, lcl):
    """Assert every SoundingIndices field equals its direct counterpart.

    `assert_array_equal` treats NaN as equal — a NaN LFC/EL must match a
    NaN field (spec §6).
    """
    cape, cin, lfc_p, lfc_t, el_p, el_t, lifted, theta_w = direct
    lcl_pressure, lcl_temperature = lcl
    equal = np.testing.assert_array_equal
    equal(result.cape.m_as("J/kg"), cape.m_as("J/kg"))
    equal(result.cin.m_as("J/kg"), cin.m_as("J/kg"))
    equal(result.lcl_pressure.m_as("hPa"), lcl_pressure.m_as("hPa"))
    equal(result.lcl_temperature.m_as("degC"), lcl_temperature.m_as("degC"))
    equal(result.lfc_pressure.m_as("hPa"), lfc_p.m_as("hPa"))
    equal(result.lfc_temperature.m_as("degC"), lfc_t.m_as("degC"))
    equal(result.el_pressure.m_as("hPa"), el_p.m_as("hPa"))
    equal(result.el_temperature.m_as("degC"), el_t.m_as("degC"))
    equal(result.lifted_index.m_as("delta_degC"), lifted.m_as("delta_degC"))
    equal(result.theta_w.m_as("degC"), theta_w.m_as("degC"))


def test_indices_default_is_plain_surface_parcel_delegation():
    """Every field equals the direct metpy.calc call (spec §7)."""
    result = indices(_sounding())
    curve = mpcalc.parcel_profile(PRESSURE, TEMPERATURE[0], DEWPOINT[0])
    direct = _direct_indices(
        PRESSURE,
        TEMPERATURE,
        DEWPOINT,
        curve,
        (PRESSURE[0], TEMPERATURE[0], DEWPOINT[0]),
    )
    _assert_indices_equal(
        result, direct, mpcalc.lcl(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0])
    )


def test_indices_mixed_layer_delegates_to_the_mixed_parcel():
    result = indices(_sounding(), parcel="mixed-layer")
    start = mpcalc.mixed_parcel(PRESSURE, TEMPERATURE, DEWPOINT)
    curve = mpcalc.parcel_profile(PRESSURE, start[1], start[2])
    direct = _direct_indices(PRESSURE, TEMPERATURE, DEWPOINT, curve, start)
    _assert_indices_equal(result, direct, mpcalc.lcl(*start))


def test_indices_corrected_feeds_the_hand_built_curve():
    """A corrected run feeds the generic functions the corrected curve."""
    correction = Q(-25.0, "hPa")
    result = indices(_sounding(), cloud_base_correction=correction)
    lcl_pressure, _ = mpcalc.lcl(PRESSURE[0], TEMPERATURE[0], DEWPOINT[0])
    corrected_pressure = lcl_pressure + correction
    corrected_temperature = mpcalc.dry_lapse(
        corrected_pressure, TEMPERATURE[0], reference_pressure=PRESSURE[0]
    )
    below = corrected_pressure <= PRESSURE
    curve = np.empty(PRESSURE.size)
    curve[below] = mpcalc.dry_lapse(
        PRESSURE[below], TEMPERATURE[0], reference_pressure=PRESSURE[0]
    ).m_as("degC")
    curve[~below] = mpcalc.moist_lapse(
        PRESSURE[~below],
        corrected_temperature,
        reference_pressure=corrected_pressure,
    ).m_as("degC")
    direct = _direct_indices(
        PRESSURE,
        TEMPERATURE,
        DEWPOINT,
        Q(curve, "degC"),
        (PRESSURE[0], TEMPERATURE[0], DEWPOINT[0]),
    )
    _assert_indices_equal(
        result,
        direct,
        (corrected_pressure.to("hPa"), corrected_temperature.to("degC")),
    )


def test_indices_zero_cape_is_zero_not_nan():
    """Zero CAPE/CIN is 0 J/kg — never NaN (spec §6, item 11)."""
    snd = Sounding(PRESSURE, STABLE_TEMPERATURE, dewpoint=STABLE_DEWPOINT)
    result = indices(snd)
    assert result.cape.m_as("J/kg") == 0.0
    assert result.cin.m_as("J/kg") == 0.0
    assert np.isnan(result.lfc_pressure.magnitude)
    assert np.isnan(result.el_pressure.magnitude)
    assert np.isfinite(result.lcl_pressure.magnitude)


def test_indices_el_nan_while_cape_positive():
    """The parcel can still be buoyant at the profile top (spec §6)."""
    snd = Sounding(
        Q([1000.0, 900.0, 800.0, 700.0], "hPa"),
        Q([30.0, 19.0, 10.0, 0.0], "degC"),
        dewpoint=Q([24.0, 15.0, 5.0, -5.0], "degC"),
    )
    result = indices(snd)
    assert result.cape.m_as("J/kg") > 0.0
    assert np.isnan(result.el_pressure.magnitude)


def test_indices_lifted_index_nan_below_500():
    """A profile topping out below 500 hPa reports NaN.

    The MetPy warning is suppressed at the call site — the suite runs
    ``filterwarnings = ["error"]``, so this test passing proves it.
    """
    snd = Sounding(
        PRESSURE[:6], TEMPERATURE[:6], dewpoint=DEWPOINT[:6]
    )  # tops at 700 hPa
    result = indices(snd)
    assert np.isnan(result.lifted_index.magnitude)
    assert result.cape.m_as("J/kg") > 0.0


def test_indices_interior_nan_gaps_pass_through():
    """NaN gaps in temperature/dewpoint are data, tolerated by MetPy."""
    temperature = TEMPERATURE.copy()
    temperature[3] = Q(np.nan, "degC")
    dewpoint = DEWPOINT.copy()
    dewpoint[5] = Q(np.nan, "degC")
    snd = Sounding(PRESSURE, temperature, dewpoint=dewpoint)
    result = indices(snd)
    assert np.isfinite(result.cape.magnitude)


def test_indices_missing_dewpoint_raises():
    with pytest.raises(MissingDataError, match="needs dewpoint"):
        indices(Sounding(PRESSURE, TEMPERATURE))


def test_indices_profile_too_short_raises():
    snd = Sounding(PRESSURE[:2], TEMPERATURE[:2], dewpoint=DEWPOINT[:2])
    with pytest.raises(ProfileTooShortError, match="no moist ascent"):
        indices(snd)


def test_indices_theta_w_follows_the_parcel_option():
    surface = indices(_sounding())
    mixed = indices(_sounding(), parcel="mixed-layer")
    start = mpcalc.mixed_parcel(PRESSURE, TEMPERATURE, DEWPOINT)
    expected = mpcalc.wet_bulb_potential_temperature(*start)
    assert mixed.theta_w.m_as("degC") == expected.m_as("degC")
    assert mixed.theta_w.m_as("degC") != surface.theta_w.m_as("degC")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_calc.py -q --no-cov`
Expected: FAIL — `ImportError: cannot import name 'indices'` (collection error is fine).

- [ ] **Step 3: Implement**

In `src/tephpy/calc.py`:

**(a)** `import warnings` joins the stdlib imports (ruff's
force-sort-within-sections puts it after the `typing` import) and
`__all__` reaches its final form:

```python
import dataclasses
from typing import TYPE_CHECKING, Final, Literal
import warnings
```

```python
__all__ = ["Profile", "SoundingIndices", "indices", "normand_point", "parcel_path"]
```

**(b)** Insert the suppressed-warning constant after `_INDEX_DIMENSIONS`:

```python
#: The MetPy warning suppressed at the ``lifted_index`` call site: a profile
#: topping out below 500 hPa makes the index NaN *with* a ``UserWarning``,
#: and the NaN field is the meteorological answer (spec §6, §10 item 11).
_OUT_OF_BOUNDS_MESSAGE: Final[str] = (
    "Interpolation point out of data bounds encountered"
)
```

**(c)** Append at the end of the module:

```python
def indices(
    snd: Sounding,
    *,
    parcel: Literal["surface", "mixed-layer"] = "surface",
    cloud_base_correction: object = None,
) -> SoundingIndices:
    """Compute the derived thermodynamic parameters (spec §3.3).

    The mechanism: derive the parcel curve on the environment levels
    under the same parcel-selection and correction rules as
    :func:`parcel_path`, then feed it to the generic ``metpy.calc``
    functions that take a parcel-profile argument (``cape_cin``, ``lfc``,
    ``el``, ``lifted_index``). With the defaults this reduces to plain
    surface-parcel delegation. The ``lcl_*`` fields report the point the
    path uses (corrected when requested) and `theta_w` the parcel start,
    mirroring :class:`Profile`.

    `theta_w` is computed with ``wet_bulb_potential_temperature``, whose
    Davies-Jones formulation differs from the moist-adiabat integrator by
    ≲0.1 °C: the path is drawn by the integrator, the number by the named
    function (spec §3.3).

    Parameters
    ----------
    snd : Sounding
        The environment sounding; must carry dewpoint.
    parcel : str, default: "surface"
        The lifted parcel, as for :func:`parcel_path`.
    cloud_base_correction : pint.Quantity, optional
        The LCL correction, as for :func:`parcel_path`.

    Returns
    -------
    SoundingIndices
        The ten derived parameters, with the spec §6 NaN-versus-zero
        semantics documented per field.

    Raises
    ------
    MissingDataError
        If the sounding has no dewpoint.
    ProfileTooShortError
        If the profile tops out at or below the LCL the parcel would use.
    TephpyUnitsError
        If `cloud_base_correction` is not a pressure-dimension quantity.
    TephpyValidationError
        If the correction places the LCL below the parcel start.
    ValueError
        If `parcel` is not a known option.
    """
    start_pressure, start_temperature, start_dewpoint = _parcel_start(snd, parcel)
    lcl_pressure, lcl_temperature = _lcl_used(
        start_pressure, start_temperature, start_dewpoint, cloud_base_correction
    )
    _require_moist_ascent(snd, lcl_pressure)
    curve = _parcel_curve(
        snd,
        start_pressure,
        start_temperature,
        start_dewpoint,
        lcl_pressure,
        lcl_temperature,
        corrected=cloud_base_correction is not None,
    )
    # Function-local so `import tephpy` stays light (spec §3.3, §10 item 10).
    from metpy.calc import (  # noqa: PLC0415
        cape_cin,
        el,
        lfc,
        lifted_index,
        wet_bulb_potential_temperature,
    )

    cape, cin = cape_cin(snd.pressure, snd.temperature, snd.dewpoint, curve)
    lfc_pressure, lfc_temperature = lfc(
        snd.pressure, snd.temperature, snd.dewpoint, parcel_temperature_profile=curve
    )
    el_pressure, el_temperature = el(
        snd.pressure, snd.temperature, snd.dewpoint, parcel_temperature_profile=curve
    )
    with warnings.catch_warnings():
        # A profile topping out below 500 hPa makes the index NaN *with* a
        # UserWarning; the NaN field is the answer (spec §6, §10 item 11).
        warnings.filterwarnings(
            "ignore", message=_OUT_OF_BOUNDS_MESSAGE, category=UserWarning
        )
        lifted = lifted_index(snd.pressure, snd.temperature, curve)[0]
    theta_w = wet_bulb_potential_temperature(
        start_pressure, start_temperature, start_dewpoint
    )
    return SoundingIndices(
        cape=cape.to("J/kg"),
        cin=cin.to("J/kg"),
        lcl_pressure=lcl_pressure,
        lcl_temperature=lcl_temperature,
        lfc_pressure=lfc_pressure.to("hPa"),
        lfc_temperature=lfc_temperature.to("degC"),
        el_pressure=el_pressure.to("hPa"),
        el_temperature=el_temperature.to("degC"),
        theta_w=theta_w.to("degC"),
        lifted_index=lifted.to("delta_degC"),
    )


def _parcel_curve(  # noqa: PLR0913
    snd: Sounding,
    start_pressure: pint.Quantity,
    start_temperature: pint.Quantity,
    start_dewpoint: pint.Quantity,
    lcl_pressure: pint.Quantity,
    lcl_temperature: pint.Quantity,
    *,
    corrected: bool,
) -> pint.Quantity:
    """Derive the parcel curve on the environment levels (spec §3.3).

    Uncorrected ascents delegate to ``metpy.calc.parcel_profile`` — the
    plain delegation the spec §7 field-equality test targets. A corrected
    ascent has no MetPy one-liner: its curve is the dry adiabat from the
    parcel start on the levels at or below the corrected LCL, and the
    corrected-LCL-anchored moist adiabat above.

    Parameters
    ----------
    snd : Sounding
        The environment sounding.
    start_pressure : pint.Quantity
        Scalar parcel-start pressure.
    start_temperature : pint.Quantity
        Scalar parcel-start temperature.
    start_dewpoint : pint.Quantity
        Scalar parcel-start dewpoint.
    lcl_pressure : pint.Quantity
        Scalar pressure of the LCL the ascent uses.
    lcl_temperature : pint.Quantity
        Scalar temperature at that LCL.
    corrected : bool
        Whether a cloud-base correction was requested.

    Returns
    -------
    pint.Quantity
        Parcel temperatures on the environment pressure levels.
    """
    # Function-local so `import tephpy` stays light (spec §3.3, §10 item 10).
    from metpy.calc import dry_lapse, moist_lapse, parcel_profile  # noqa: PLC0415
    from metpy.units import units as registry  # noqa: PLC0415

    if not corrected:
        return parcel_profile(snd.pressure, start_temperature, start_dewpoint)
    pressure = snd.pressure.m_as("hPa")
    below = pressure >= float(lcl_pressure.m_as("hPa"))
    curve = np.empty(pressure.size, dtype=np.float64)
    if below.any():
        curve[below] = dry_lapse(
            registry.Quantity(pressure[below], "hPa"),
            start_temperature,
            reference_pressure=start_pressure,
        ).m_as("degC")
    curve[~below] = moist_lapse(
        registry.Quantity(pressure[~below], "hPa"),
        lcl_temperature,
        reference_pressure=lcl_pressure,
    ).m_as("degC")
    return registry.Quantity(curve, "degC")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_calc.py tests/test_units.py -q --no-cov`
Expected: PASS (the import-cost guard re-proves the completed `calc` adds
no heavy import).

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/calc.py tests/test_calc.py
pixi run lint
git commit -m "feat: add indices, the derived-parameter delegation over metpy.calc"
```

---

## Task 6: The published worked example

**Files:**
- Test: `tests/test_calc.py` (append — test-only task; the provenance record lives with the fixture, spec §10 item 13)

**Interfaces:**
- Consumes: `indices` (Task 5), `Sounding`.
- Produces: the §7 integration test against a published worked example. No code changes.

- [ ] **Step 1: Write the tests**

Append to the end of `tests/test_calc.py`:

```python
# --- the published worked example (spec §7, §10 item 13) -------------------

# Stull, R., 2017: "Practical Meteorology: An Algebra-based Survey of
# Atmospheric Science", version 1.02b, CC BY-NC-SA 4.0, ch. 14 p. 496
# (https://www.eoas.ubc.ca/books/Practical_Meteorology/): the sample
# application sounding — P (kPa) 100, 96, 80, 70, 50, 30, 20; T (°C) 30,
# 25, 10, 15, -10, -35, -35; surface Td 20 °C — with published
# thermo-diagram answers P_LCL = 87 kPa, P_LFC = 60 kPa, P_EL = 24 kPa.
# Values transcribed from the chapter PDF on 2026-07-26: a handful of
# numeric facts, reproduced with citation. The environment dewpoints above
# the surface are not published; the placeholders below enter only
# cape_cin's virtual-temperature correction, not the LCL/LFC/EL
# comparisons.
STULL_PRESSURE = Q(np.array([1000.0, 960.0, 800.0, 700.0, 500.0, 300.0, 200.0]), "hPa")
STULL_TEMPERATURE = Q(np.array([30.0, 25.0, 10.0, 15.0, -10.0, -35.0, -35.0]), "degC")
STULL_DEWPOINT = Q(np.array([20.0, 15.0, 0.0, -5.0, -25.0, -50.0, -60.0]), "degC")


def test_worked_example_stull_ch14():
    """Integration: the published Stull ch. 14 parcel-ascent answers."""
    snd = Sounding(STULL_PRESSURE, STULL_TEMPERATURE, dewpoint=STULL_DEWPOINT)
    result = indices(snd)
    # Stull reads 870 and 600 off a full-size skew-T; his own Sample
    # Applications carry a "slightly different answer if you used a
    # different thermo diagram... is normal" caveat.
    assert result.lcl_pressure.m_as("hPa") == pytest.approx(870.0, abs=10.0)
    assert result.lfc_pressure.m_as("hPa") == pytest.approx(600.0, abs=5.0)
    # The published EL (240 hPa) sits in the isothermal -35 °C layer,
    # where the crossing is hypersensitive to the moist-adiabat
    # formulation: metpy 1.7.1 places it at 275 hPa. Divergence
    # documented, not forced to zero (spec §7).
    assert 240.0 <= result.el_pressure.m_as("hPa") <= 300.0
    assert result.cin.m_as("J/kg") == 0.0


def test_worked_example_cape_against_stull_equation_14_5():
    """CAPE agrees with Stull's published pressure-integral, eq. (14.5).

    CAPE = Rd * sum((T_parcel - T_env) * ln(p_bottom / p_top)) over the
    area between the LFC and the EL — evaluated here on a fine ln-p grid
    over MetPy's own parcel curve. cape_cin integrates the same area in
    *virtual* temperature (the Doswell & Rasmussen correction), which
    inflates it — by 14% for this moist parcel over its dry mid-level
    environment (1182 vs 1033 J/kg, metpy 1.7.1). The check pins the
    magnitude and the direction of that documented divergence: a
    composition bug (wrong units, wrong curve, wrong bounds) lands far
    outside it.
    """
    snd = Sounding(STULL_PRESSURE, STULL_TEMPERATURE, dewpoint=STULL_DEWPOINT)
    result = indices(snd)
    curve = mpcalc.parcel_profile(
        STULL_PRESSURE, STULL_TEMPERATURE[0], STULL_DEWPOINT[0]
    )
    # cape_cin's integration bounds: its LFC ("bottom") is the LCL here —
    # the parcel is buoyant from the LCL up — and its EL is the reported
    # one.
    bottom = result.lcl_pressure.m_as("hPa")
    top = result.el_pressure.m_as("hPa")
    grid = np.geomspace(bottom, top, 4001)
    x = -np.log(STULL_PRESSURE.m_as("hPa"))
    environment = np.interp(-np.log(grid), x, STULL_TEMPERATURE.m_as("degC"))
    parcel = np.interp(-np.log(grid), x, curve.m_as("degC"))
    rd = 287.053
    cape_stull = rd * np.trapezoid(parcel - environment, -np.log(grid))
    cape = result.cape.m_as("J/kg")
    assert cape >= cape_stull
    assert cape == pytest.approx(cape_stull, rel=0.2)
```

Context for a reviewer (measured 2026-07-26, metpy 1.7.1): this fixture
reproduces the published LCL at 864.2 hPa and LFC at 601.1 hPa; the EL
lands at 275.4 hPa; CAPE is 1181.8 J/kg against the eq.-(14.5) plain-T
integral of 1033.2 J/kg. This sounding also exercises the **interrupted
CAPE region**: the capping inversion (960→800→700 hPa with 15 °C at
700 hPa) splits the positive area into two lobes, and `cape_cin`'s
bottom-LFC is the LCL (864 hPa) while the standalone `lfc()` reports the
top crossing (601 hPa) — the MetPy inconsistency documented in the Global
Constraints, passed through faithfully.

- [ ] **Step 2: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_calc.py -q --no-cov`
Expected: PASS — these tests exercise code that already exists; they are
an integration anchor, not TDD of new behaviour.

- [ ] **Step 3: Lint and commit**

```bash
git add tests/test_calc.py
pixi run lint
git commit -m "test: anchor indices against the published Stull worked example"
```

---

## Task 7: The analysis conventions in `_constants`

**Files:**
- Modify: `src/tephpy/_constants.py`
- Test: `tests/test_constants.py` (append)

**Interfaces:**
- Produces: `CLOUD_BASE_CORRECTION`, `CAPE_COLOR`, `CIN_COLOR`, `SHADING_ALPHA`, `SHADING_ZORDER`, `INDICES_PANEL_WIDTH`, `INDICES_PANEL_PAD`, `INDICES_PANEL_FONTSIZE`, `INDICES_PANEL_ROWS`. Tasks 10–11 consume the styles and panel wiring; users consume `CLOUD_BASE_CORRECTION` as the documented operational value.

- [ ] **Step 1: Write the failing tests**

In `tests/test_constants.py`, the import block gains `dataclasses` and
`SoundingIndices` (sorted — `dataclasses` precedes `datetime`):

```python
from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import numpy as np

from tephpy import _constants as constants
from tephpy.calc import SoundingIndices
```

then append to the end of the file:

```python
def test_shading_conventions():
    """Shading draws between the families and the profile lines."""
    family_zorders = (
        constants.ISOTHERM_ZORDER,
        constants.DRY_ADIABAT_ZORDER,
        constants.ISOBAR_ZORDER,
        constants.MIXING_RATIO_ZORDER,
        constants.MOIST_ADIABAT_ZORDER,
    )
    assert max(family_zorders) < constants.SHADING_ZORDER < constants.PROFILE_ZORDER
    assert constants.CAPE_COLOR != constants.CIN_COLOR
    assert 0.0 < constants.SHADING_ALPHA < 1.0


def test_cloud_base_correction_is_the_operational_value():
    """The operational correction raises the LCL by 25 mb (spec §1/§3.3)."""
    assert constants.CLOUD_BASE_CORRECTION == -25.0


def test_indices_panel_rows_cover_every_field():
    """One panel row per SoundingIndices field, in field order."""
    fields = [field.name for field in dataclasses.fields(SoundingIndices)]
    assert [row[0] for row in constants.INDICES_PANEL_ROWS] == fields
```

(`dataclasses.fields` excludes the `units` `InitVar`, so the row/field
correspondence is exact.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_constants.py -q --no-cov`
Expected: FAIL — `AttributeError: module 'tephpy._constants' has no attribute 'SHADING_ZORDER'`.

- [ ] **Step 3: Add the conventions**

In `src/tephpy/_constants.py`, insert after the `SOUNDING_LABEL_FORMAT`
block (before the `LABEL_FONTSIZE` block):

```python
#: The operational cloud-base correction to Normand's point, in hPa: UK
#: operational tephigram practice raises the constructed LCL by 25 mb to
#: better match observed convective cloud base (spec §1/§3.3; Met Office
#: forecasting practice). Applied only when explicitly requested via
#: ``cloud_base_correction=``.
CLOUD_BASE_CORRECTION: Final[float] = -25.0

#: CAPE shading fill colour (the operational/MetPy convention: positive
#: buoyancy red, negative blue; spec §3.2).
CAPE_COLOR: Final[str] = "tab:red"

#: CIN shading fill colour (the operational/MetPy convention).
CIN_COLOR: Final[str] = "tab:blue"

#: CAPE/CIN shading fill alpha.
SHADING_ALPHA: Final[float] = 0.3

#: CAPE/CIN shading draw order: between the isopleth families and the
#: profile lines (spec §3.2).
SHADING_ZORDER: Final[float] = 2.0

#: Indices panel width, as an ``axes_grid1`` fraction of the diagram width
#: (spec §3.2).
INDICES_PANEL_WIDTH: Final[str] = "35%"

#: Indices panel padding from the diagram, in inches.
INDICES_PANEL_PAD: Final[float] = 0.1

#: Indices panel text font size in points.
INDICES_PANEL_FONTSIZE: Final[float] = 8.0

#: Indices panel rows, one per ``SoundingIndices`` field, in display order:
#: (field name, display label, pint unit to convert to, display unit,
#: format spec). NaN values render as an em dash (spec §3.2).
INDICES_PANEL_ROWS: Final[tuple[tuple[str, str, str, str, str], ...]] = (
    ("cape", "CAPE", "J/kg", "J/kg", ".0f"),
    ("cin", "CIN", "J/kg", "J/kg", ".0f"),
    ("lcl_pressure", "LCL", "hPa", "hPa", ".0f"),
    ("lcl_temperature", "LCL T", "degC", "°C", ".1f"),
    ("lfc_pressure", "LFC", "hPa", "hPa", ".0f"),
    ("lfc_temperature", "LFC T", "degC", "°C", ".1f"),
    ("el_pressure", "EL", "hPa", "hPa", ".0f"),
    ("el_temperature", "EL T", "degC", "°C", ".1f"),
    ("theta_w", "θw", "degC", "°C", ".1f"),
    ("lifted_index", "LI", "delta_degC", "°C", ".1f"),
)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_constants.py -q --no-cov`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/_constants.py tests/test_constants.py
pixi run lint
git commit -m "feat: seed the correction, shading, and indices-panel conventions"
```

---

## Task 8: `plot_profile` accepts a `Profile`

**Files:**
- Modify: `src/tephpy/plotting/axes.py`
- Test: `tests/plotting/test_axes.py` (append)

**Interfaces:**
- Consumes: `Profile` (as a `TYPE_CHECKING`-only annotation — the runtime dispatch is duck-typed, preserving the §3 layering: `plotting` never imports `calc`).
- Produces: the `@overload`ed `plot_profile` — `plot_profile(profile, *, label=None, **kwargs)` alongside the unchanged Plan 4 array form. `plot_sounding` (which calls the array form) is untouched.

- [ ] **Step 1: Write the failing tests**

In `tests/plotting/test_axes.py`, the tephpy import gains `calc`:

```python
from tephpy import Sounding, calc, transforms
```

then append to the end of the file:

```python
# --- Profile plotting, shading, and the indices panel (spec §3.2/§3.3) ----

CAPPED_PRESSURE = units.Quantity(
    np.array([1000.0, 950.0, 900.0, 850.0, 700.0, 500.0, 300.0, 200.0]), "hPa"
)
CAPPED_TEMPERATURE = units.Quantity(
    np.array([26.0, 24.0, 23.0, 21.0, 10.0, -12.0, -40.0, -55.0]), "degC"
)
CAPPED_DEWPOINT = units.Quantity(
    np.array([20.0, 17.0, 14.0, 10.0, 2.0, -15.0, -45.0, -60.0]), "degC"
)


def _capped_sounding():
    """Build a capped convective sounding with both CAPE and CIN."""
    return Sounding(CAPPED_PRESSURE, CAPPED_TEMPERATURE, dewpoint=CAPPED_DEWPOINT)


def test_plot_profile_accepts_a_parcel_profile(tephigram_axes):
    """The Profile form plots the path through the transform machinery."""
    parcel = calc.parcel_path(_capped_sounding(), label="surface parcel")
    line = tephigram_axes.plot_profile(parcel, color="black", linestyle="--")
    np.testing.assert_allclose(line.get_xdata(), parcel.temperature.m_as("degC"))
    expected_theta = transforms.theta_from_pressure_temperature(
        parcel.pressure.m_as("hPa"), parcel.temperature.m_as("degC")
    )
    np.testing.assert_allclose(line.get_ydata(), expected_theta)
    assert line.get_label() == "surface parcel"
    assert line.get_color() == "black"


def test_plot_profile_profile_label_precedence(tephigram_axes):
    """label= argument > profile.label > no legend entry (spec §3.2)."""
    labelled = calc.parcel_path(_capped_sounding(), label="from the profile")
    assert tephigram_axes.plot_profile(labelled).get_label() == "from the profile"
    overridden = tephigram_axes.plot_profile(labelled, label="argument wins")
    assert overridden.get_label() == "argument wins"
    anonymous = tephigram_axes.plot_profile(calc.parcel_path(_capped_sounding()))
    assert anonymous.get_label().startswith("_")


def test_plot_profile_profile_form_sets_no_style_defaults(tephigram_axes):
    """The low-level primitive: matplotlib defaults, not conventions."""
    line = tephigram_axes.plot_profile(calc.parcel_path(_capped_sounding()))
    assert line.get_linewidth() == plt.rcParams["lines.linewidth"]
    assert line.get_zorder() == 2


def test_plot_profile_wrong_combinations_are_type_errors(tephigram_axes):
    """Bad argument shapes are TypeErrors, never units errors (spec §3.2)."""
    snd = _capped_sounding()
    parcel = calc.parcel_path(snd)
    with pytest.raises(TypeError, match="no separate temperature"):
        tephigram_axes.plot_profile(parcel, CAPPED_TEMPERATURE)
    with pytest.raises(TypeError, match="no units="):
        tephigram_axes.plot_profile(parcel, units={"pressure": "hPa"})
    with pytest.raises(TypeError, match="needs pressure and temperature"):
        tephigram_axes.plot_profile(CAPPED_PRESSURE)
    with pytest.raises(TypeError, match="needs pressure and temperature"):
        tephigram_axes.plot_profile(snd)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -q --no-cov`
Expected: FAIL — the first four new tests error (`TypeError: plot_profile() missing 1 required positional argument: 'temperature'` and friends); the existing tests still pass.

- [ ] **Step 3: Implement the overload**

In `src/tephpy/plotting/axes.py`:

**(a)** The typing import gains `cast` and `overload`, and the
`TYPE_CHECKING` block gains `Profile`:

```python
from typing import TYPE_CHECKING, Any, cast, overload
```

```python
if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from matplotlib.lines import Line2D

    from tephpy.calc import Profile
    from tephpy.sounding import Sounding
```

**(b)** Replace the entire `plot_profile` method (signature through
`return line`) with the following (a dedented listing — indent one level,
see Global Constraints). Notes baked in: both overload stubs carry
`# numpydoc ignore=GL08` (Global Constraints); the first parameter keeps
its Plan 4 name `pressure` in both overloads — mypy strict rejects a
positional-only `profile` form whose `**kwargs` could then legally carry
`pressure=`; the implementation's `**kwargs: Any` line needs no `noqa`
(ruff only flags the stubs' annotated `Any`):

```python
@overload
def plot_profile(  # numpydoc ignore=GL08
    self,
    pressure: Profile,
    *,
    label: str | None = None,
    **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
) -> Line2D: ...


@overload
def plot_profile(  # numpydoc ignore=GL08
    self,
    pressure: object,
    temperature: object,
    *,
    units: Mapping[str, str] | None = None,
    label: str | None = None,
    **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
) -> Line2D: ...


def plot_profile(
    self,
    pressure: object,
    temperature: object | None = None,
    *,
    units: Mapping[str, str] | None = None,
    label: str | None = None,
    **kwargs: Any,
) -> Line2D:
    """Plot one profile of temperature against pressure (spec §3.2).

    Both arrays are pint quantities — or bare arrays with the
    ``units=`` mapping (spec §5) — converted to diagram-native units
    and plotted through the tephigram transform machinery. Matplotlib
    keywords pass through untouched, and out-of-domain values
    (pressure <= 0 hPa) propagate NaN, breaking the line (spec §3.1).

    The same signature also accepts a ``calc.Profile`` (e.g. the
    return of ``calc.parcel_path``) as its only positional argument;
    dispatch is duck-typed on the ``Profile`` shape — `temperature`
    omitted and ``pressure``/``temperature``/``lcl_pressure``
    attributes present. Label precedence in that form: `label`
    argument > ``profile.label`` > no entry. In both forms no style
    defaults are set — this is the low-level primitive (spec §4
    styles parcel paths explicitly at the call site).

    Parameters
    ----------
    pressure : pint.Quantity, array_like, or Profile
        Level pressures, or the profile to plot.
    temperature : pint.Quantity or array_like, optional
        Level temperatures; omitted in the ``Profile`` form.
    units : mapping of str to str, optional
        Unit strings for bare arrays, keyed by argument name, e.g.
        ``units={"pressure": "hPa", "temperature": "degC"}``; not
        accepted in the ``Profile`` form.
    label : str, optional
        Legend label for the line.
    **kwargs : Any
        Passed through to :meth:`matplotlib.axes.Axes.plot`.

    Returns
    -------
    matplotlib.lines.Line2D
        The profile line.

    Raises
    ------
    TephpyUnitsError
        For unit-less bare arrays, ambiguous or unparsable units, or
        the wrong dimensionality.
    TypeError
        For wrong argument combinations: a ``Profile`` together with
        `temperature` or ``units=``, or `temperature` omitted when
        the sole argument is not ``Profile``-shaped (a bare pressure
        array, or a ``Sounding`` passed by mistake).
    """
    profile_shaped = all(
        hasattr(pressure, attr) for attr in ("pressure", "temperature", "lcl_pressure")
    )
    if profile_shaped:
        if temperature is not None:
            msg = "plot_profile() takes no separate temperature with a Profile"
            raise TypeError(msg)
        if units is not None:
            msg = "plot_profile() takes no units= with a Profile"
            raise TypeError(msg)
        profile = cast("Profile", pressure)
        pressure = profile.pressure
        temperature = profile.temperature
        if label is None:
            label = profile.label
    elif temperature is None:
        msg = (
            "plot_profile() needs pressure and temperature, or a single "
            "Profile as its only positional argument"
        )
        raise TypeError(msg)
    mapping = check_units_mapping(units, allowed=("pressure", "temperature"))
    p = as_quantity(
        pressure,
        name="pressure",
        units=mapping.get("pressure"),
        dimension="[pressure]",
    )
    t = as_quantity(
        temperature,
        name="temperature",
        units=mapping.get("temperature"),
        dimension="[temperature]",
    )
    pressure_hpa = p.m_as("hPa")
    temperature_c = t.m_as("degC")
    theta = transforms.theta_from_pressure_temperature(pressure_hpa, temperature_c)
    (line,) = self.plot(
        temperature_c,
        theta,
        transform=self.tephigram_transform + self.transData,
        label=label,
        **kwargs,
    )
    return line
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -q --no-cov`
Expected: PASS — including every pre-existing `plot_profile`/`plot_sounding` test (the array form is behaviourally unchanged).

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
pixi run lint
git commit -m "feat: accept a calc.Profile in TephigramAxes.plot_profile"
```

---

## Task 9: The shading builders

**Files:**
- Create: `src/tephpy/plotting/shading.py`
- Test: `tests/plotting/test_shading.py`

**Interfaces:**
- Consumes: `tephpy.transforms` (for the (T, θ) vertices) — nothing else; the builders are pure numpy over bare hPa/°C arrays (the §5 exemption, like `isopleths.py`).
- Produces: `cape_polygons(...)`/`cin_polygons(...)` per the contract above. Task 10's axes methods are thin wrappers over them.

- [ ] **Step 1: Write the failing tests**

Create `tests/plotting/test_shading.py` — the fixture's crossings have
closed-form pressures, so the tests pin the ln-p interpolation itself
(vertex pressures are recovered through
`transforms.pressure_from_temperature_theta`):

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the CAPE/CIN shading builders (spec §3.2).

Headless geometry tests against an analytic fixture: an isothermal 0 °C
environment and a piecewise-linear (in ln p) parcel curve, whose buoyancy
sign-change crossings have closed-form pressures.
"""

from __future__ import annotations

import numpy as np

from tephpy import transforms
from tephpy.plotting.shading import cape_polygons, cin_polygons

ENV_PRESSURE = np.array([1000.0, 800.0, 500.0, 300.0])
ENV_TEMPERATURE = np.zeros(4)
PARCEL_TEMPERATURE = np.array([-4.0, 6.0, 6.0, -6.0])

#: Buoyancy crossings of the fixture, exact in ln p: the -4 → +6 segment
#: crosses zero at 0.4 of ln(1000/800); the +6 → -6 segment at its ln-p
#: midpoint.
CROSS_LOW = 1000.0 * np.exp(-0.4 * np.log(1000.0 / 800.0))
CROSS_HIGH = np.sqrt(500.0 * 300.0)


def _cape(lcl_pressure, parcel_temperature=PARCEL_TEMPERATURE):
    return cape_polygons(
        ENV_PRESSURE,
        ENV_TEMPERATURE,
        ENV_PRESSURE,
        parcel_temperature,
        lcl_pressure=lcl_pressure,
    )


def _cin(lcl_pressure, parcel_temperature=PARCEL_TEMPERATURE):
    return cin_polygons(
        ENV_PRESSURE,
        ENV_TEMPERATURE,
        ENV_PRESSURE,
        parcel_temperature,
        lcl_pressure=lcl_pressure,
    )


def _vertex_pressures(polygon):
    """Recover each polygon vertex's pressure from (T, theta) space."""
    return transforms.pressure_from_temperature_theta(polygon[:, 0], polygon[:, 1])


def test_cape_region_bounded_by_the_interpolated_crossings():
    """Crossings are located by linear interpolation in ln p (spec §3.2)."""
    (polygon,) = _cape(lcl_pressure=950.0)
    pressures = _vertex_pressures(polygon)
    np.testing.assert_allclose(pressures.max(), CROSS_LOW, rtol=1e-9)
    np.testing.assert_allclose(pressures.min(), CROSS_HIGH, rtol=1e-9)


def test_cape_region_clipped_at_the_lcl():
    """Positive buoyancy below the LCL never counts towards CAPE."""
    (polygon,) = _cape(lcl_pressure=900.0)
    pressures = _vertex_pressures(polygon)
    np.testing.assert_allclose(pressures.max(), 900.0, rtol=1e-9)
    np.testing.assert_allclose(pressures.min(), CROSS_HIGH, rtol=1e-9)


def test_cape_polygon_closes_on_the_drawn_curves():
    """Up the parcel curve, back down the isothermal environment."""
    (polygon,) = _cape(lcl_pressure=950.0)
    half = polygon.shape[0] // 2
    environment_branch = polygon[half:, 0]
    np.testing.assert_allclose(environment_branch, 0.0, atol=1e-12)
    # The branches meet exactly at the crossings: parcel == environment.
    np.testing.assert_allclose(polygon[0, 0], 0.0, atol=1e-12)
    np.testing.assert_allclose(polygon[half - 1, 0], 0.0, atol=1e-12)


def test_cin_region_spans_start_to_the_lfc():
    """CIN runs from the parcel start up to the LFC crossing."""
    (polygon,) = _cin(lcl_pressure=950.0)
    pressures = _vertex_pressures(polygon)
    np.testing.assert_allclose(pressures.max(), 1000.0, rtol=1e-9)
    np.testing.assert_allclose(pressures.min(), CROSS_LOW, rtol=1e-9)


def test_interrupted_cape_yields_plural_polygons():
    """An embedded stable layer splits the region (spec §3.2)."""
    pressure = np.array([1000.0, 900.0, 800.0, 600.0, 300.0])
    environment = np.zeros(5)
    parcel = np.array([-4.0, 5.0, -3.0, 4.0, -6.0])
    polygons = cape_polygons(
        pressure, environment, pressure, parcel, lcl_pressure=980.0
    )
    assert len(polygons) == 2
    lower, upper = polygons
    assert _vertex_pressures(lower).min() > _vertex_pressures(upper).max()


def test_no_positive_buoyancy_yields_no_regions():
    """With no LFC there is neither CAPE nor CIN (cape_cin's zeros)."""
    colder = np.full(4, -5.0)
    assert _cape(lcl_pressure=950.0, parcel_temperature=colder) == []
    assert _cin(lcl_pressure=950.0, parcel_temperature=colder) == []


def test_positive_buoyancy_only_below_the_lcl_is_not_cape():
    """A superadiabatic surface layer is no LFC (spec §3.2)."""
    parcel = np.array([2.0, -2.0, -4.0, -8.0])
    assert _cape(lcl_pressure=700.0, parcel_temperature=parcel) == []
    assert _cin(lcl_pressure=700.0, parcel_temperature=parcel) == []


def test_nan_gap_breaks_the_region():
    """NaN environment gaps are data; the region stops at the gap."""
    environment = np.array([0.0, 0.0, np.nan, 0.0])
    (polygon,) = cape_polygons(
        ENV_PRESSURE,
        environment,
        ENV_PRESSURE,
        PARCEL_TEMPERATURE,
        lcl_pressure=950.0,
    )
    pressures = _vertex_pressures(polygon)
    np.testing.assert_allclose(pressures.max(), CROSS_LOW, rtol=1e-9)
    np.testing.assert_allclose(pressures.min(), 800.0, rtol=1e-9)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_shading.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'tephpy.plotting.shading'` (collection error is fine).

- [ ] **Step 3: Create the module**

Create `src/tephpy/plotting/shading.py` — this exact code passes ruff,
mypy strict, and numpydoc-validation (verified 2026-07-26):

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""CAPE/CIN shading geometry for the tephigram (spec §3.2).

Free builders in the ``isopleths`` pattern: pure functions over bare numpy
arrays in diagram-native units (hPa, °C — the spec §5 exemption) that
return closed polygons in (temperature, theta) space, headlessly testable.
``TephigramAxes.shade_cape``/``shade_cin`` draw them through the tephigram
transform as one compound-path ``PathPatch`` per call.

Both curves are interpolated onto their merged pressure grid (linear in
ln p) with the exact buoyancy sign-change crossings inserted, and the
regions are bounded as ``metpy.calc.cape_cin`` integrates (its
``which_lfc="bottom"``/``which_el="top"`` defaults): CAPE is the
positive-buoyancy region between the LFC — the bottom of the lowest
positive run at or above the LCL — and the EL — the top of the highest
such run, which is the profile top while the parcel is still buoyant
there; CIN is the negative-buoyancy region between the parcel start and
the LFC. With no LFC there is neither region (``cape_cin`` returns
``0 J/kg`` for both). Two documented divergences from the *numbers*:
``cape_cin`` finds its bounds on virtual-temperature profiles and
integrates the net virtual-temperature difference (Doswell & Rasmussen
1994), neither of which the plotted temperature curves can show — the
shading is the drawn-curve region between the same rules' bounds, and the
annotated J/kg number remains the quantitative truth.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from tephpy import transforms

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["cape_polygons", "cin_polygons"]


def cape_polygons(
    pressure: npt.ArrayLike,
    temperature: npt.ArrayLike,
    parcel_pressure: npt.ArrayLike,
    parcel_temperature: npt.ArrayLike,
    *,
    lcl_pressure: float,
) -> list[npt.NDArray[np.float64]]:
    """Build the CAPE region's closed polygons (spec §3.2).

    Parameters
    ----------
    pressure : array_like
        Environment pressures in hPa, strictly decreasing.
    temperature : array_like
        Environment temperatures in degrees Celsius; NaN gaps break the
        region.
    parcel_pressure : array_like
        Parcel-path pressures in hPa, strictly decreasing.
    parcel_temperature : array_like
        Parcel-path temperatures in degrees Celsius.
    lcl_pressure : float
        Pressure of the LCL the parcel uses, in hPa; buoyancy below it
        never counts towards CAPE.

    Returns
    -------
    list of numpy.ndarray
        One ``(N, 2)`` closed polygon in (temperature, theta) space per
        uninterrupted positive-buoyancy run — plural when the region is
        interrupted, empty when there is no CAPE (0 is an answer, not an
        error; spec §6).
    """
    p, env, parcel = _merged_curves(
        pressure, temperature, parcel_pressure, parcel_temperature
    )
    regions = [
        (lo, hi)
        for lo, hi in _regions(p, parcel - env, positive=True)
        if p[hi - 1] < lcl_pressure
    ]
    polygons = []
    for lo, hi in regions:
        clipped = _clip_pressure_span(
            p[lo:hi], env[lo:hi], parcel[lo:hi], bottom=lcl_pressure
        )
        if clipped is not None:
            polygons.append(_polygon(*clipped))
    return polygons


def cin_polygons(
    pressure: npt.ArrayLike,
    temperature: npt.ArrayLike,
    parcel_pressure: npt.ArrayLike,
    parcel_temperature: npt.ArrayLike,
    *,
    lcl_pressure: float,
) -> list[npt.NDArray[np.float64]]:
    """Build the CIN region's closed polygons (spec §3.2).

    Parameters
    ----------
    pressure : array_like
        Environment pressures in hPa, strictly decreasing.
    temperature : array_like
        Environment temperatures in degrees Celsius; NaN gaps break the
        region.
    parcel_pressure : array_like
        Parcel-path pressures in hPa, strictly decreasing.
    parcel_temperature : array_like
        Parcel-path temperatures in degrees Celsius.
    lcl_pressure : float
        Pressure of the LCL the parcel uses, in hPa; it locates the LFC
        that bounds the region.

    Returns
    -------
    list of numpy.ndarray
        One ``(N, 2)`` closed polygon in (temperature, theta) space per
        uninterrupted negative-buoyancy run between the parcel start and
        the LFC — empty when there is no LFC (``cape_cin`` reports both
        CAPE and CIN as zero then) or no inhibition below it.
    """
    p, env, parcel = _merged_curves(
        pressure, temperature, parcel_pressure, parcel_temperature
    )
    diff = parcel - env
    lfc_pressure = _lfc(p, diff, lcl_pressure)
    if lfc_pressure is None:
        return []
    regions = [
        (lo, hi) for lo, hi in _regions(p, diff, positive=False) if p[lo] > lfc_pressure
    ]
    polygons = []
    for lo, hi in regions:
        clipped = _clip_pressure_span(
            p[lo:hi], env[lo:hi], parcel[lo:hi], top=lfc_pressure
        )
        if clipped is not None:
            polygons.append(_polygon(*clipped))
    return polygons


def _merged_curves(
    pressure: npt.ArrayLike,
    temperature: npt.ArrayLike,
    parcel_pressure: npt.ArrayLike,
    parcel_temperature: npt.ArrayLike,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Interpolate both curves onto their merged pressure grid.

    Both curves are interpolated linearly in ln p onto the union of their
    pressure levels over the overlapping span, and the exact buoyancy
    sign-change crossings are inserted so every run of one buoyancy sign
    starts and ends on a zero-difference vertex (or a span end).

    Parameters
    ----------
    pressure : array_like
        Environment pressures in hPa, strictly decreasing.
    temperature : array_like
        Environment temperatures in degrees Celsius.
    parcel_pressure : array_like
        Parcel-path pressures in hPa, strictly decreasing.
    parcel_temperature : array_like
        Parcel-path temperatures in degrees Celsius.

    Returns
    -------
    tuple of numpy.ndarray
        ``(pressure, temperature, parcel_temperature)`` on the merged,
        crossing-augmented grid, pressure strictly decreasing.
    """
    env_p = np.asarray(pressure, dtype=np.float64)
    env_t = np.asarray(temperature, dtype=np.float64)
    path_p = np.asarray(parcel_pressure, dtype=np.float64)
    path_t = np.asarray(parcel_temperature, dtype=np.float64)
    top = max(env_p.min(), path_p.min())
    bottom = min(env_p.max(), path_p.max())
    grid = np.unique(np.concatenate([env_p, path_p]))
    grid = grid[(grid >= top) & (grid <= bottom)][::-1]
    # Interpolate linearly in ln p; -ln p is increasing for np.interp.
    x = -np.log(grid)
    env = np.interp(x, -np.log(env_p), env_t)
    parcel = np.interp(x, -np.log(path_p), path_t)
    diff = parcel - env
    crossing = np.flatnonzero(diff[:-1] * diff[1:] < 0.0)
    if crossing.size:
        fraction = diff[crossing] / (diff[crossing] - diff[crossing + 1])
        x_cross = x[crossing] + fraction * (x[crossing + 1] - x[crossing])
        t_cross = np.interp(x_cross, x, env)
        grid = np.insert(grid, crossing + 1, np.exp(-x_cross))
        env = np.insert(env, crossing + 1, t_cross)
        parcel = np.insert(parcel, crossing + 1, t_cross)
    return grid, env, parcel


def _regions(
    pressure: npt.NDArray[np.float64],
    diff: npt.NDArray[np.float64],
    *,
    positive: bool,
) -> Iterator[tuple[int, int]]:
    """Locate the uninterrupted runs of one buoyancy sign.

    Each run is widened to the adjacent zero-difference crossing vertices
    so its polygon closes exactly on the drawn curves; runs too short to
    enclose area are dropped.

    Parameters
    ----------
    pressure : numpy.ndarray
        The merged, crossing-augmented pressure grid.
    diff : numpy.ndarray
        Parcel minus environment temperature on that grid.
    positive : bool
        Select positive-buoyancy runs (CAPE) or negative ones (CIN).

    Yields
    ------
    tuple of int
        Half-open ``(start, stop)`` index bounds of one region.
    """
    mask = diff > 0.0 if positive else diff < 0.0
    padded = np.concatenate([[False], mask, [False]])
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    for start, stop in zip(edges[::2], edges[1::2], strict=True):
        lo = int(start)
        hi = int(stop)
        if lo > 0 and diff[lo - 1] == 0.0:
            lo -= 1
        if hi < diff.size and diff[hi] == 0.0:
            hi += 1
        if hi - lo >= 2 and pressure[lo] > pressure[hi - 1]:
            yield lo, hi


def _lfc(
    pressure: npt.NDArray[np.float64],
    diff: npt.NDArray[np.float64],
    lcl_pressure: float,
) -> float | None:
    """Locate the LFC bound the way ``cape_cin`` does (spec §3.2).

    The bottom of the lowest positive-buoyancy run reaching above the
    LCL, clamped to the LCL itself when that run starts below it
    (``which_lfc="bottom"`` semantics on the drawn curves).

    Parameters
    ----------
    pressure : numpy.ndarray
        The merged, crossing-augmented pressure grid.
    diff : numpy.ndarray
        Parcel minus environment temperature on that grid.
    lcl_pressure : float
        Pressure of the LCL the parcel uses, in hPa.

    Returns
    -------
    float or None
        The LFC pressure in hPa, or ``None`` when the parcel never
        becomes positively buoyant at or above the LCL.
    """
    for lo, hi in _regions(pressure, diff, positive=True):
        if pressure[hi - 1] < lcl_pressure:
            return min(float(pressure[lo]), lcl_pressure)
    return None


def _clip_pressure_span(
    pressure: npt.NDArray[np.float64],
    temperature: npt.NDArray[np.float64],
    parcel_temperature: npt.NDArray[np.float64],
    *,
    bottom: float | None = None,
    top: float | None = None,
) -> (
    tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]]
    | None
):
    """Trim one region to a pressure span, keeping the cut level exact.

    Parameters
    ----------
    pressure : numpy.ndarray
        The region's pressures, strictly decreasing.
    temperature : numpy.ndarray
        Environment temperatures on those levels.
    parcel_temperature : numpy.ndarray
        Parcel temperatures on those levels.
    bottom : float, optional
        Keep only ``pressure <= bottom``, inserting the exact cut level
        (the CAPE clip at the LCL).
    top : float, optional
        Keep only ``pressure >= top``, inserting the exact cut level
        (the CIN clip at the LFC).

    Returns
    -------
    tuple of numpy.ndarray or None
        The clipped ``(pressure, temperature, parcel_temperature)``, or
        ``None`` when fewer than two levels survive.
    """
    p, env, parcel = pressure, temperature, parcel_temperature
    if bottom is not None and p[0] > bottom:
        keep = p <= bottom
        cut = _interpolated_level(p, env, parcel, bottom)
        p = np.concatenate([[bottom], p[keep]])
        env = np.concatenate([[cut[0]], env[keep]])
        parcel = np.concatenate([[cut[1]], parcel[keep]])
    if top is not None and p[-1] < top:
        keep = p >= top
        cut = _interpolated_level(p, env, parcel, top)
        p = np.concatenate([p[keep], [top]])
        env = np.concatenate([env[keep], [cut[0]]])
        parcel = np.concatenate([parcel[keep], [cut[1]]])
    if p.size < 2 or p[0] <= p[-1]:
        return None
    return p, env, parcel


def _interpolated_level(
    pressure: npt.NDArray[np.float64],
    temperature: npt.NDArray[np.float64],
    parcel_temperature: npt.NDArray[np.float64],
    level: float,
) -> tuple[float, float]:
    """Interpolate both curves at one pressure level (linear in ln p).

    Parameters
    ----------
    pressure : numpy.ndarray
        The region's pressures, strictly decreasing.
    temperature : numpy.ndarray
        Environment temperatures on those levels.
    parcel_temperature : numpy.ndarray
        Parcel temperatures on those levels.
    level : float
        The pressure to interpolate at, in hPa.

    Returns
    -------
    tuple of float
        The ``(environment, parcel)`` temperatures at `level`.
    """
    x = -np.log(pressure)
    at = -np.log(level)
    return (
        float(np.interp(at, x, temperature)),
        float(np.interp(at, x, parcel_temperature)),
    )


def _polygon(
    pressure: npt.NDArray[np.float64],
    temperature: npt.NDArray[np.float64],
    parcel_temperature: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    """Close one region into a (temperature, theta) polygon.

    Up the parcel curve, then back down the environment curve; the
    vertices are ready for the tephigram transform (no duplicate closing
    vertex — the drawing side appends ``CLOSEPOLY``).

    Parameters
    ----------
    pressure : numpy.ndarray
        The region's pressures, strictly decreasing.
    temperature : numpy.ndarray
        Environment temperatures on those levels.
    parcel_temperature : numpy.ndarray
        Parcel temperatures on those levels.

    Returns
    -------
    numpy.ndarray
        The closed ``(N, 2)`` polygon in (temperature, theta) space.
    """
    parcel_theta = transforms.theta_from_pressure_temperature(
        pressure, parcel_temperature
    )
    env_theta = transforms.theta_from_pressure_temperature(pressure, temperature)
    vertices_t = np.concatenate([parcel_temperature, temperature[::-1]])
    vertices_theta = np.concatenate([parcel_theta, env_theta[::-1]])
    return np.column_stack([vertices_t, vertices_theta])
```

Implementation notes:
- The LCL and LFC cut levels are in practice always grid points (the
  parcel path splices the LCL exactly; the LFC is either the LCL or an
  inserted crossing), so `_clip_pressure_span`'s insertion branch guards
  float-edge cases rather than doing routine work — but the CAPE clip at
  the LCL *is* routinely a trim (the LCL-crossing positive run keeps only
  its at-or-above-LCL part).
- NaN environment gaps propagate through `np.interp` into `diff`, where
  they are neither positive nor negative — regions simply stop at the
  gap, no special-casing.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_shading.py -q --no-cov`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/plotting/shading.py tests/plotting/test_shading.py
pixi run lint
git commit -m "feat: add the CAPE/CIN shading polygon builders"
```

---

## Task 10: `shade_cape` and `shade_cin`

**Files:**
- Modify: `src/tephpy/plotting/axes.py`
- Test: `tests/plotting/test_axes.py` (append)

**Interfaces:**
- Consumes: the Task 9 builders; the Task 7 style conventions; `Profile` fields (`pressure`, `temperature`, `lcl_pressure` — duck-typed at runtime).
- Produces: `shade_cape(snd, parcel, **kwargs) -> PathPatch | None` and `shade_cin(...)` with the shared `_shade` helper.

- [ ] **Step 1: Write the failing tests**

In `tests/plotting/test_axes.py`, extend the import block — three
matplotlib imports and four constants join (each block sorted; `mcolors`
before the `matplotlib.patches`/`path` imports per
force-sort-within-sections):

```python
import matplotlib.colors as mcolors
from matplotlib.patches import PathPatch
from matplotlib.path import Path
import matplotlib.pyplot as plt
from metpy.units import units
import numpy as np
import pytest

from tephpy import Sounding, calc, transforms
from tephpy._config import config
from tephpy._constants import (
    CAPE_COLOR,
    CIN_COLOR,
    DEFAULT_EXTENT,
    PROFILE_DEWPOINT_COLOR,
    PROFILE_LINEWIDTH,
    PROFILE_TEMPERATURE_COLOR,
    PROFILE_ZORDER,
    SHADING_ALPHA,
    SHADING_ZORDER,
)
from tephpy.exceptions import TephpyUnitsError
from tephpy.plotting.axes import TephigramAxes, TephigramTransform
from tephpy.plotting.isopleths import IsoplethFamily
```

then append to the end of the file:

```python
def _stable_sounding():
    """Build a stable sounding: no positive buoyancy anywhere."""
    return Sounding(
        units.Quantity(np.array([1000.0, 850.0, 700.0, 500.0, 300.0]), "hPa"),
        units.Quantity(np.array([5.0, 3.0, 0.0, -14.0, -40.0]), "degC"),
        dewpoint=units.Quantity(np.array([-5.0, -10.0, -15.0, -30.0, -55.0]), "degC"),
    )


def test_shade_cape_draws_one_compound_patch(tephigram_axes):
    snd = _capped_sounding()
    parcel = calc.parcel_path(snd)
    patch = tephigram_axes.shade_cape(snd, parcel)
    assert isinstance(patch, PathPatch)
    assert patch in tephigram_axes.patches
    expected = tephigram_axes.tephigram_transform + tephigram_axes.transData
    assert patch.get_data_transform() == expected
    np.testing.assert_allclose(
        patch.get_facecolor(), mcolors.to_rgba(CAPE_COLOR, SHADING_ALPHA)
    )
    assert (patch.get_path().codes == Path.MOVETO).sum() == 1


def test_shade_cin_draws_below_the_lfc(tephigram_axes):
    snd = _capped_sounding()
    parcel = calc.parcel_path(snd)
    patch = tephigram_axes.shade_cin(snd, parcel)
    assert isinstance(patch, PathPatch)
    np.testing.assert_allclose(
        patch.get_facecolor(), mcolors.to_rgba(CIN_COLOR, SHADING_ALPHA)
    )


def test_shading_zorder_between_families_and_profiles(tephigram_axes):
    snd = _capped_sounding()
    patch = tephigram_axes.shade_cape(snd, calc.parcel_path(snd))
    family_zorders = [
        family.get_zorder() for family in tephigram_axes._families.values()
    ]
    assert max(family_zorders) < patch.get_zorder() == SHADING_ZORDER
    assert patch.get_zorder() < PROFILE_ZORDER


def test_shade_kwargs_override_the_conventions(tephigram_axes):
    snd = _capped_sounding()
    patch = tephigram_axes.shade_cape(
        snd, calc.parcel_path(snd), facecolor="purple", alpha=0.5
    )
    np.testing.assert_allclose(patch.get_facecolor(), mcolors.to_rgba("purple", 0.5))


def test_shade_zero_area_returns_none(tephigram_axes):
    """0 is an answer, not an error (spec §6)."""
    snd = _stable_sounding()
    parcel = calc.parcel_path(snd)
    assert tephigram_axes.shade_cape(snd, parcel) is None
    assert tephigram_axes.shade_cin(snd, parcel) is None


def test_shading_does_not_drift_the_view(tephigram_axes):
    """Patches never autoscale the fixed extent (spec §3.2)."""
    before = (tephigram_axes.get_xlim(), tephigram_axes.get_ylim())
    snd = _capped_sounding()
    parcel = calc.parcel_path(snd)
    tephigram_axes.shade_cape(snd, parcel)
    tephigram_axes.shade_cin(snd, parcel)
    tephigram_axes.figure.canvas.draw()
    assert (tephigram_axes.get_xlim(), tephigram_axes.get_ylim()) == before
```

(Patch assertions use `get_data_transform()` — a Patch's plain
`get_transform()` composes the patch-local transform in front and would
never compare equal. The capped fixture's measured values, for a reviewer:
CAPE 1698 J/kg, CIN −290 J/kg, LCL 915.6 hPa, LFC 657.8 hPa, EL 219.0 hPa,
one polygon per region; the stable fixture yields no LFC, hence
`None`/`None`.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -q --no-cov`
Expected: FAIL — `AttributeError: 'TephigramAxes' object has no attribute 'shade_cape'`; everything else still passes.

- [ ] **Step 3: Implement**

In `src/tephpy/plotting/axes.py`:

**(a)** The matplotlib imports gain `PathPatch` and `Path` (sorted between
`matplotlib.axes` and `matplotlib.projections`):

```python
from matplotlib.axes import Axes
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.projections import register_projection
```

the `_constants` import gains the four shading names (sorted):

```python
from tephpy._constants import (
    CAPE_COLOR,
    CIN_COLOR,
    DEFAULT_EXTENT,
    PROFILE_DEWPOINT_COLOR,
    PROFILE_LINEWIDTH,
    PROFILE_TEMPERATURE_COLOR,
    PROFILE_ZORDER,
    SHADING_ALPHA,
    SHADING_ZORDER,
)
```

the plotting import block gains the builder module:

```python
from tephpy.plotting import shading
from tephpy.plotting.isopleths import _FAMILY_SPECS, IsoplethFamily
```

and `Callable` joins the `TYPE_CHECKING` collections import:

```python
if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping
```

(only the `collections.abc` line changes — the rest of the block stays.)

**(b)** Insert the three methods directly after `plot_sounding` (dedented
listing — indent one level, see Global Constraints):

```python
def shade_cape(
    self,
    snd: Sounding,
    parcel: Profile,
    **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
) -> PathPatch | None:
    """Shade the CAPE area between the sounding and a parcel path.

    The positive-buoyancy region between the environment temperature
    and the parcel path, bounded as ``metpy.calc.cape_cin``
    integrates — from the LFC to the EL, to the profile top when the
    parcel is still buoyant there — so the shading matches the
    annotated numbers (spec §3.2). Drawn as one compound-path patch;
    interrupted regions become multiple polygons in the same patch.

    Parameters
    ----------
    snd : Sounding
        The environment sounding.
    parcel : Profile
        The parcel path, e.g. from ``calc.parcel_path``.
    **kwargs : Any
        Passed through to :class:`matplotlib.patches.PathPatch`,
        overriding the ``_constants`` conventions.

    Returns
    -------
    matplotlib.patches.PathPatch or None
        The shaded patch, or ``None`` for zero area — 0 is an
        answer, not an error (spec §6).
    """
    return self._shade(snd, parcel, shading.cape_polygons, CAPE_COLOR, kwargs)


def shade_cin(
    self,
    snd: Sounding,
    parcel: Profile,
    **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
) -> PathPatch | None:
    """Shade the CIN area between the sounding and a parcel path.

    The negative-buoyancy region between the environment temperature
    and the parcel path, bounded as ``metpy.calc.cape_cin``
    integrates — from the parcel start to the LFC — so the shading
    matches the annotated numbers (spec §3.2). Drawn as one
    compound-path patch; with no LFC there is no CIN region.

    Parameters
    ----------
    snd : Sounding
        The environment sounding.
    parcel : Profile
        The parcel path, e.g. from ``calc.parcel_path``.
    **kwargs : Any
        Passed through to :class:`matplotlib.patches.PathPatch`,
        overriding the ``_constants`` conventions.

    Returns
    -------
    matplotlib.patches.PathPatch or None
        The shaded patch, or ``None`` for zero area — 0 is an
        answer, not an error (spec §6).
    """
    return self._shade(snd, parcel, shading.cin_polygons, CIN_COLOR, kwargs)


def _shade(
    self,
    snd: Sounding,
    parcel: Profile,
    builder: Callable[..., list[npt.NDArray[np.float64]]],
    facecolor: str,
    kwargs: dict[str, Any],
) -> PathPatch | None:
    """Build one shading region and draw it as a compound-path patch.

    Parameters
    ----------
    snd : Sounding
        The environment sounding.
    parcel : Profile
        The parcel path.
    builder : callable
        The ``plotting.shading`` polygon builder to delegate to.
    facecolor : str
        The region's conventional fill colour.
    kwargs : dict
        User overrides, passed through to the patch.

    Returns
    -------
    matplotlib.patches.PathPatch or None
        The shaded patch, or ``None`` for zero area.
    """
    polygons = builder(
        snd.pressure.m_as("hPa"),
        snd.temperature.m_as("degC"),
        parcel.pressure.m_as("hPa"),
        parcel.temperature.m_as("degC"),
        lcl_pressure=float(parcel.lcl_pressure.m_as("hPa")),
    )
    if not polygons:
        return None
    vertices = []
    codes = []
    for polygon in polygons:
        count = polygon.shape[0]
        vertices.append(np.vstack([polygon, polygon[:1]]))
        codes.append(
            np.concatenate(
                [[Path.MOVETO], np.full(count - 1, Path.LINETO), [Path.CLOSEPOLY]]
            )
        )
    path = Path(np.vstack(vertices), np.concatenate(codes))
    patch = PathPatch(
        path,
        **{
            "facecolor": facecolor,
            "edgecolor": "none",
            "alpha": SHADING_ALPHA,
            "zorder": SHADING_ZORDER,
            "transform": self.tephigram_transform + self.transData,
            **kwargs,
        },
    )
    self.add_patch(patch)
    return patch
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py tests/plotting/test_shading.py -q --no-cov`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
pixi run lint
git commit -m "feat: add shade_cape and shade_cin over the shading builders"
```

---

## Task 11: `annotate_indices` and the panel lifecycle

**Files:**
- Modify: `src/tephpy/plotting/axes.py`
- Test: `tests/plotting/test_axes.py` (append)

**Interfaces:**
- Consumes: `SoundingIndices` (`TYPE_CHECKING`-only annotation; runtime access is `getattr` by field name), the Task 7 panel conventions, the Plan 3 side-of-axes contract (spec §10 item 7 — `axes_grid1` divider, right side).
- Produces: `annotate_indices(indices) -> Axes`, the cached `_indices_panel`, and `clear()`'s panel teardown. Completes the §4 canonical usage minus barbs.

- [ ] **Step 1: Write the failing tests**

In `tests/plotting/test_axes.py`, the `_constants` import gains
`INDICES_PANEL_ROWS` (sorted, after `DEFAULT_EXTENT`), then append to the
end of the file:

```python
def test_annotate_indices_returns_a_side_panel(tephigram_axes):
    result = calc.indices(_capped_sounding())
    panel = tephigram_axes.annotate_indices(result)
    assert panel in tephigram_axes.figure.axes
    assert not isinstance(panel, TephigramAxes)
    assert not panel.axison
    texts = [text.get_text() for text in panel.texts]
    assert len(texts) == 2 * len(INDICES_PANEL_ROWS)
    assert "CAPE" in texts
    assert any(text.endswith("J/kg") for text in texts)


def test_annotate_indices_updates_in_place(tephigram_axes):
    """Calling it again updates the panel, never stacks a second one."""
    result = calc.indices(_capped_sounding())
    panel = tephigram_axes.annotate_indices(result)
    count = len(tephigram_axes.figure.axes)
    assert tephigram_axes.annotate_indices(result) is panel
    assert len(tephigram_axes.figure.axes) == count
    assert len(panel.texts) == 2 * len(INDICES_PANEL_ROWS)


def test_annotate_indices_renders_nan_as_em_dash(tephigram_axes):
    """A stable sounding has no LFC/EL: those rows show an em dash."""
    panel = tephigram_axes.annotate_indices(calc.indices(_stable_sounding()))
    texts = [text.get_text() for text in panel.texts]
    assert "—" in texts


def test_clear_removes_the_indices_panel(tephigram_axes):
    tephigram_axes.annotate_indices(calc.indices(_capped_sounding()))
    assert len(tephigram_axes.figure.axes) == 2
    tephigram_axes.clear()
    assert len(tephigram_axes.figure.axes) == 1
    assert tephigram_axes.get_axes_locator() is None


def test_canonical_usage_composes(tephigram_axes):
    """The spec §4 sequence works end to end (minus barbs, a later plan)."""
    snd = _capped_sounding()
    tephigram_axes.plot_sounding(snd)
    parcel = calc.parcel_path(snd)
    tephigram_axes.plot_profile(parcel, color="k", linestyle="--")
    assert tephigram_axes.shade_cape(snd, parcel) is not None
    assert tephigram_axes.shade_cin(snd, parcel) is not None
    panel = tephigram_axes.annotate_indices(calc.indices(snd))
    assert panel in tephigram_axes.figure.axes
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -q --no-cov`
Expected: FAIL — `AttributeError: 'TephigramAxes' object has no attribute 'annotate_indices'`.

- [ ] **Step 3: Implement**

In `src/tephpy/plotting/axes.py`:

**(a)** `import math` joins the stdlib imports (first import line),
`make_axes_locatable` joins the third-party block (after
`matplotlib.transforms`), the `_constants` import gains the four panel
names, and the `TYPE_CHECKING` block gains `SoundingIndices` — its
`tephpy.calc` line becomes (dedented listing — keep the block indentation
when pasting):

```python
import math
from typing import TYPE_CHECKING, Any, cast, overload
```

```python
import matplotlib.transforms as mtransforms
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
```

```python
from tephpy._constants import (
    CAPE_COLOR,
    CIN_COLOR,
    DEFAULT_EXTENT,
    INDICES_PANEL_FONTSIZE,
    INDICES_PANEL_PAD,
    INDICES_PANEL_ROWS,
    INDICES_PANEL_WIDTH,
    PROFILE_DEWPOINT_COLOR,
    PROFILE_LINEWIDTH,
    PROFILE_TEMPERATURE_COLOR,
    PROFILE_ZORDER,
    SHADING_ALPHA,
    SHADING_ZORDER,
)
```

```python
from tephpy.calc import Profile, SoundingIndices
```

**(b)** In the `TephigramAxes` class-attribute annotations, add the panel
cache after `_families` (dedented listing — indent one level when
pasting):

```python
_indices_panel: Axes | None
```

**(c)** In `clear()`, extend the docstring's final sentence and add the
panel teardown between the axis-hiding lines and the `_families` loop —
the method becomes (dedented listing — indent one level):

```python
def clear(self) -> None:
    """Reset the axes to the tephigram projection defaults.

    Matplotlib calls this during ``Axes.__init__`` and on user
    ``ax.clear()``; both paths recreate the projection-owned state:
    the tephigram transform, equal aspect, hidden native axes, the
    five background isopleth families, and the default extent
    (``tephpy.config`` diagram extent, else ``DEFAULT_EXTENT``).
    An indices panel is removed with the diagram it annotated.
    """
    super().clear()
    self.tephigram_transform = TephigramTransform()
    self.set_aspect(1.0, adjustable="box")
    self.xaxis.set_visible(False)
    self.yaxis.set_visible(False)
    panel = getattr(self, "_indices_panel", None)
    if panel is not None:
        panel.remove()
        # The stub demands a callable, but None resets the locator
        # (the documented matplotlib behaviour).
        self.set_axes_locator(None)  # type: ignore[arg-type]
    self._indices_panel = None
    self._families = {}
    for name, spec in _FAMILY_SPECS.items():
        family = IsoplethFamily(spec, getattr(config, name))
        self.add_artist(family)
        self._families[name] = family
    extent = config.diagram.extent
    self.set_extent(DEFAULT_EXTENT if extent is None else extent)
```

(`getattr(self, ..., None)` because matplotlib calls `clear()` during
`Axes.__init__`, before the attribute exists; resetting the locator gives
a cleared diagram its full subplot slot back.)

**(d)** Insert `annotate_indices` directly after `_shade` (dedented
listing — indent one level):

```python
def annotate_indices(self, indices: SoundingIndices) -> Axes:
    """Display derived parameters in a panel beside the diagram.

    The first consumer of the side-of-axes contract (spec §3.2):
    the panel is appended with the ``axes_grid1`` divider, one
    formatted line per ``SoundingIndices`` field, NaN rendered as an
    em dash. Calling it again updates the panel in place rather than
    stacking a second one. With ``axes_grid1``, append order is
    position order: once the wind-barb gutter exists (a later
    release), ``plot_barbs`` must be called before this method for
    the contracted inside-out order.

    Parameters
    ----------
    indices : SoundingIndices
        The derived parameters, e.g. from ``calc.indices``.

    Returns
    -------
    matplotlib.axes.Axes
        The panel axes, for restyling.
    """
    if self._indices_panel is None:
        divider = make_axes_locatable(self)
        self._indices_panel = divider.append_axes(
            "right",
            size=INDICES_PANEL_WIDTH,
            pad=INDICES_PANEL_PAD,
            axes_class=Axes,
        )
    panel = self._indices_panel
    panel.clear()
    panel.set_axis_off()
    rows = len(INDICES_PANEL_ROWS)
    for row, (field, label, unit, display, spec) in enumerate(INDICES_PANEL_ROWS):
        value = float(getattr(indices, field).m_as(unit))
        text = "—" if math.isnan(value) else f"{value:{spec}} {display}"
        y = 1.0 - (row + 0.5) / rows
        panel.text(
            0.04,
            y,
            label,
            fontsize=INDICES_PANEL_FONTSIZE,
            ha="left",
            va="center",
            transform=panel.transAxes,
        )
        panel.text(
            0.96,
            y,
            text,
            fontsize=INDICES_PANEL_FONTSIZE,
            ha="right",
            va="center",
            transform=panel.transAxes,
        )
    return panel
```

(`axes_class=Axes` is load-bearing: axes_grid1 otherwise clones the
parent's class and the panel would draw a whole tephigram grid.)

- [ ] **Step 4: Run the full test suite**

Run: `pixi run --frozen pytest -q --no-cov`
Expected: PASS — everything from Tasks 1–11 plus all Plan 1–4 tests.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
pixi run lint
git commit -m "feat: add the annotate_indices side panel"
```

---

## Task 12: Shading and indices-panel image baselines

**Files:**
- Modify: `tests/plotting/test_images.py` (append)
- Create: `tests/baseline/test_shading_cape_cin.png`, `tests/baseline/test_indices_panel.png` (generated)

**Interfaces:**
- Consumes: everything above; the Plan 3 pytest-mpl infrastructure (`pixi run baselines`, `--mpl` wired into `pixi run tests` and CI).
- Produces: the §7/§8.5 shading baselines assigned to this plan ("image baselines ship with their feature"); the composed §4 figure baseline stays with Plan 7 (it needs Plan 6's barbs).

- [ ] **Step 1: Write the image tests**

In `tests/plotting/test_images.py`, the tephpy import gains `calc`:

```python
# Importing tephpy (via any of its names) registers the "tephigram" projection.
from tephpy import Sounding, calc
```

then append to the end of the file:

```python
def _capped_sounding():
    """Build a capped convective sounding with both CAPE and CIN."""
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
    )


@pytest.mark.mpl_image_compare
def test_shading_cape_cin():
    """CAPE/CIN shading and the parcel path over a capped sounding."""
    fig, ax = _tephigram_figure()
    snd = _capped_sounding()
    ax.plot_sounding(snd)
    parcel = calc.parcel_path(snd)
    ax.plot_profile(parcel, color="black", linestyle="--", linewidth=1.0)
    ax.shade_cape(snd, parcel)
    ax.shade_cin(snd, parcel)
    return fig


@pytest.mark.mpl_image_compare
def test_indices_panel():
    """The indices panel beside the diagram (the axes_grid1 divider)."""
    fig, ax = plt.subplots(figsize=(5.0, 3.5), subplot_kw={"projection": "tephigram"})
    ax.set_extent(((1050.0, -30.0), (200.0, 40.0)))
    snd = _capped_sounding()
    ax.plot_sounding(snd)
    ax.annotate_indices(calc.indices(snd))
    return fig
```

(The panel baseline uses a wider 5.0 × 3.5 figure with a zoomed extent —
at the shared 3.5-inch square the point-sized panel text collides with its
values, since text is absolute while the 35% panel scales with the
figure.)

- [ ] **Step 2: Generate the baselines, then verify them**

```bash
pixi run baselines        # regenerates ALL baselines; marked tests are SKIPPED
git status --porcelain tests/baseline
pixi run tests            # full suite with --mpl comparisons and coverage
```

Expected: `git status` shows exactly two untracked files
(`test_shading_cape_cin.png` ~67 KB, `test_indices_panel.png` ~79 KB) and
**zero modified** existing baselines — regeneration is bit-identical on
the committed lockfile (verified 2026-07-26). The full suite passes with
all 11 image comparisons.

Visually inspect the two new PNGs: the shading figure shows the red/green
sounding, a black dashed parcel path, a small blue CIN sliver under the
capping inversion, and the red CAPE region above it; the panel figure
shows ten cleanly right-aligned rows (CAPE 1698 J/kg … LI −6.4 °C) beside
the zoomed diagram.

- [ ] **Step 3: Lint and commit**

```bash
git add tests/plotting/test_images.py tests/baseline/test_shading_cape_cin.png tests/baseline/test_indices_panel.png
pixi run lint
git commit -m "test: add the shading and indices-panel image baselines"
```

---

## Task 13: Glossary entries and a warning-free docs build

**Files:**
- Modify: `docs/src/reference/glossary.rst`

**Interfaces:**
- Produces: the `profile` entry updated (its "(added in a later release)" caveat is now false) and eight new entries for the terms this plan introduces (spec §8.6 audience-first rules; §10 cross-cutting rule). sphinx-autoapi adds `tephpy.calc` and `tephpy.plotting.shading` pages automatically.

- [ ] **Step 1: Update and append the entries**

In `docs/src/reference/glossary.rst`, replace the existing `profile` entry
(keeping the established indent inside `.. glossary::`) with:

```rst
    profile
        One curve of a temperature-like quantity against pressure — a
        :term:`sounding`'s temperature or dewpoint trace, or a computed
        :term:`parcel` path (the ``calc.Profile`` dataclass).
        ``ax.plot_profile(...)`` draws either through the tephigram
        transform machinery.
```

and append at the end of the glossary:

```rst
    parcel
    air parcel
        An imagined small mass of air lifted through the surrounding
        environment without mixing with it — the tephigram's basic tool
        for reasoning about stability. In ``tephpy``,
        ``calc.parcel_path(...)`` computes a parcel's ascent as a
        ``calc.Profile``, and the ``parcel=`` option selects the starting
        parcel: ``"surface"`` or ``"mixed-layer"`` (the lowest 100 hPa
        averaged).

    lifting condensation level
    LCL
    Normand's point
        The level where a lifted, unsaturated :term:`parcel` first
        saturates — on a tephigram it is Normand's construction: the
        :term:`dry adiabat` through the parcel's temperature meets the
        :term:`humidity mixing ratio` line through its :term:`dewpoint`.
        ``calc.normand_point(...)`` returns it as scalar (pressure,
        temperature) pint quantities, ``calc.parcel_path`` splices it
        into the ascent exactly, and the operational -25 mb cloud-base
        correction is applied only when requested via
        ``cloud_base_correction=``.

    level of free convection
    LFC
        The level above which a lifted :term:`parcel` becomes warmer than
        its environment and rises freely. In ``tephpy`` it is the
        ``lfc_pressure``/``lfc_temperature`` fields of
        ``calc.SoundingIndices`` — NaN quantities when the parcel never
        becomes positively buoyant ("does not exist" is an answer, not an
        error).

    equilibrium level
    EL
        The level above the :term:`LFC` where a rising :term:`parcel`
        cools back to the environment temperature — roughly the anvil
        top of a thunderstorm. The ``el_pressure``/``el_temperature``
        fields of ``calc.SoundingIndices``; NaN when the parcel is still
        buoyant at the profile top (:term:`CAPE` can be positive with no
        EL).

    CAPE
    convective available potential energy
        The energy per unit mass (J/kg) available to a :term:`parcel`
        between the :term:`LFC` and the :term:`EL`, where it is warmer
        than the environment — the fuel gauge for deep convection.
        ``calc.indices(...)`` reports it (``0 J/kg`` — never NaN — when
        there is none) and ``ax.shade_cape(snd, parcel)`` shades the
        region.

    CIN
    convective inhibition
        The energy per unit mass (J/kg, non-positive) a :term:`parcel`
        must be given to reach its :term:`LFC` through the layers where
        it is cooler than the environment — the lid that must break
        before :term:`CAPE` is released. Reported by
        ``calc.indices(...)`` and shaded by ``ax.shade_cin(snd,
        parcel)``.

    lifted index
        The environment-minus-parcel temperature difference at 500 hPa
        (°C); large negative values mean instability. The
        ``lifted_index`` field of ``calc.SoundingIndices``; NaN when the
        profile tops out below 500 hPa.
```

- [ ] **Step 2: Build the docs**

Run: `pixi run docs`
Expected: `build succeeded`, **0 warnings** (verified 2026-07-26: the new
`:term:` references resolve — `dry adiabat`, `dewpoint`, and
`humidity mixing ratio` already exist — and the autoapi pages for
`tephpy.calc` and `tephpy.plotting.shading` generate cleanly). If a
warning appears, fix it — do not suppress.

- [ ] **Step 3: Commit**

```bash
git add docs/src/reference/glossary.rst
git commit -m "docs: update the profile glossary entry and add the analysis terms"
```

---

## Task 14: Drop the scipy declaration

**Files:**
- Modify: `requirements/pypi-core.txt`
- Modify: `pyproject.toml`
- Modify: `tests/test_import.py`

**Interfaces:**
- Resolves spec §10 item 14: Plan 5 completed with no direct scipy consumer (the shading interpolation is plain numpy), so the speculative declaration goes; MetPy keeps scipy transitively.

- [ ] **Step 1: Remove the declaration**

**(a)** `requirements/pypi-core.txt` becomes:

```
matplotlib>=3.9
metpy>=1.6
numpy>=2.0
pandas>=2.3
pint>=0.24
xarray>=2024.10
```

**(b)** In `pyproject.toml`, delete the `scipy = ">=1.13"` line from
`[tool.pixi.dependencies]`:

```toml
matplotlib-base = ">=3.9"
metpy = ">=1.6"
numpy = ">=2.0"
pandas = ">=2.3"
pint = ">=0.24"
setuptools = ">=77.0.3"
setuptools-scm = ">=8"
xarray = ">=2024.10"
```

**(c)** In `tests/test_import.py`, the runtime-deps loop becomes:

```python
def test_runtime_dependencies_importable() -> None:
    """The declared runtime dependencies import."""
    for package in (
        "matplotlib",
        "metpy",
        "numpy",
        "pandas",
        "pint",
        "xarray",
    ):
        importlib.import_module(package)
```

- [ ] **Step 2: Verify the lockfile is untouched**

```bash
pixi lock
git diff --stat pixi.lock
```

Expected: `✔ Lock-file was already up-to-date` and an **empty diff** —
scipy stays in every locked environment via MetPy (verified 2026-07-26).
If the diff is *not* empty, stop and inspect: a matplotlib or freetype
bump would invalidate the pytest-mpl baselines (see `tests/AGENTS.md`).

- [ ] **Step 3: Run the tests, lint, and commit**

```bash
pixi run --frozen pytest tests/test_import.py -q --no-cov
git add requirements/pypi-core.txt pyproject.toml tests/test_import.py
pixi run lint
git commit -m "build: drop the unconsumed scipy declaration (spec item 14)"
```

---

## Task 15: Full verification, pull request, and changelog fragment

**Files:** `changelog/<PR>.feature.rst` (created after the PR number exists)

- [ ] **Step 1: Full local gate**

```bash
pixi run lint
pixi run --frozen --environment test-py312 pytest --cov --cov-report=xml --mpl
pixi run --frozen --environment test-py313 pytest --cov --cov-report=xml --mpl
pixi run --frozen --environment test-py314 pytest --cov --cov-report=xml --mpl
pixi run docs
```

Expected: lint fully green; the suite (359 tests, including all 11 image
comparisons) passes on all three Pythons against the same committed
baselines (verified 2026-07-26); docs build with 0 warnings.

- [ ] **Step 2: Open the pull request**

```bash
git push -u origin analysis
gh pr create --base main --title "Thermodynamic analysis (Plan 5)" --fill
```

- [ ] **Step 3: Add the changelog fragment named for the PR**

With `<PR>` the number just created:

```bash
cat > changelog/<PR>.feature.rst <<'EOF'
Added the ``tephpy.calc`` thermodynamic analysis layer — ``parcel_path`` with surface and mixed-layer parcels and the operational cloud-base correction, ``normand_point``, ``indices``, and the ``Profile``/``SoundingIndices`` dataclasses — together with ``plot_profile`` accepting a parcel ``Profile``, CAPE/CIN shading via ``shade_cape``/``shade_cin``, the ``annotate_indices`` side panel, and their image baselines; dropped the unconsumed scipy dependency declaration.
(:user:`claude`)
EOF
git add changelog/<PR>.feature.rst
git commit -m "docs: add Plan 5 changelog fragment"
git push
```

Expected: the `ci-changelog` check passes on the PR; all other checks
(tests ×3 with image comparisons, docs, wheels + smoke test, CodeQL,
pre-commit.ci) go green.

---

## Self-review

**Spec coverage (Plan 5 row: §3.3, §3.2 slices, §6, §7, §8.1 item 14):**
`Profile` with the exact §3.3 field set (surface-first arrays, the LCL the
path actually uses, `parcel` literal, `label`), `Sounding`-idiom
construction and the spec'd validation split (`TephpyValidationError` for
data, `ValueError` for the literal) → Task 2. `SoundingIndices` with the
ten §3.3 fields, dimension-checked scalars, no cross-field validation, §6
NaN-versus-zero semantics documented per field → Task 2.
`normand_point` — always the uncorrected geometric construction, scalar
quantities, §5 `units=` mapping → Task 3. `parcel_path` — dry adiabat →
Normand's point → moist adiabat spanning start to top; 5 hPa sampling on
both legs; `moist_lapse(..., reference_pressure=p_lcl)` anchoring; exact
LCL splice; `parcel="surface"|"mixed-layer"` with `mixed_parcel`'s
operational 100 hPa default; `cloud_base_correction` applied only when
requested, −25 mb value in `_constants` with its convention cited,
corrected temperature re-read from the dry adiabat; θw
Davies-Jones-versus-integrator divergence documented → Tasks 4, 7.
`indices` — parcel curve on environment levels under the same rules, fed
to the generic `cape_cin`/`lfc`/`el`/`lifted_index`; plain surface-parcel
delegation with the defaults (the §7 field-equality target); `lcl_*`
report the used point; `theta_w` at the parcel start following `parcel=`
→ Task 5. Analysis-time §6 errors at the `calc` boundary
(`MissingDataError`, `ProfileTooShortError` with the corrected-LCL
semantics) → Tasks 1, 4, 5. §6 NaN behaviours (zero CAPE = `0 J/kg`; NaN
LFC/EL; EL NaN with CAPE > 0; `lifted_index` NaN below 500 hPa with the
MetPy warning suppressed at the call site under
`filterwarnings = ["error"]`; interior NaN gaps pass through) → Task 5
tests. §10 item 11's floor verification (`metpy==1.6.*` semantics) →
done at plan-writing time (1.6.3, recorded in Global Constraints), so the
floor stays `>=1.6`. The `plot_profile` `Profile` overload — duck-typed
dispatch, `@overload`-typed, label precedence, TypeErrors-never-units-errors,
no style defaults → Task 8 (spec §10 item 2). `shade_cape`/`shade_cin` —
free builders in `plotting/shading.py`, merged ln-p grid, sign-change
crossings, closed (T, θ) polygons plural-when-interrupted, cape_cin-rule
bounds, compound-path `PathPatch` through the tephigram transform,
`None` for zero area, `_constants` styling with kwargs override, no
config section at v1 → Tasks 7, 9, 10. `annotate_indices` — `axes_grid1`
divider (the Plan 3 contract's first consumer), one line per field, NaN
as em dash, formats/width in `_constants`, returns the panel, updates in
place, barbs-before-indices ordering documented in the docstring →
Tasks 7, 11. §4 canonical usage minus barbs → Task 11's composition
test. Shading baselines (§7/§8.5 cross-cutting rule; panel baseline
included as prudent extra) → Task 12. Glossary rule (§8.6; parcel, LCL
triple-alias with Normand's point, LFC, EL, CAPE, CIN, lifted index;
`profile` caveat lifted) → Task 13. Item 14 scipy drop incl. the
`test_import.py` tuple and the lockfile no-op check → Task 14. Item 12
(layer highlights): correctly absent — not in v1. Full gate + PR +
fragment → Task 15.

**Placeholder scan:** every code step carries complete, runnable code.
All listings were developed against the live environment first — each
passes ruff (`ALL` + format), mypy strict, and numpydoc-validation; the
full pytest gate (359 tests, 11 image comparisons,
`filterwarnings = ["error"]`) passes on py312/py313/py314; the docs build
is warning-free; the two baseline figures were rendered and visually
inspected; and the MetPy behaviours the design leans on were probed
empirically on both metpy 1.7.1 and 1.6.3 (2026-07-26). No TBDs, no
"similar to Task N".

**Type/name consistency:** the exception names, the `calc` dataclass
field sets, `normand_point`/`parcel_path`/`indices` signatures, the
`_parcel_start`/`_lcl_used`/`_require_moist_ascent`/`_parcel_curve`
helper signatures, the builder signatures
(`cape_polygons`/`cin_polygons` with keyword-only `lcl_pressure`), the
`_constants` names, and the three axes-method signatures are identical
across the Interfaces contract and Tasks 1–12; Task 10's `_shade` calls
exactly Task 9's builders with exactly Task 7's conventions; Task 11's
panel iterates exactly Task 7's `INDICES_PANEL_ROWS`, whose field order
Task 7's test pins to `dataclasses.fields(SoundingIndices)`.

**Known judgment calls (documented, not hidden):**
- `indices()` uses `parcel_profile` for *all* uncorrected runs rather
  than always hand-building: hand-built curves differ from
  `parcel_profile` by ~0.1 K (ODE anchoring), and the spec's §7 equality
  test demands exact agreement with plain delegation. The corrected
  branch is the only hand-built one, and its test hand-builds the same
  curve.
- The reported `lfc_*` fields use `lfc()`'s defaults (`which="top"`)
  while `cape_cin` integrates from its bottom-LFC — MetPy's own
  inconsistency for multi-crossing profiles, deliberately passed through
  (§3.3: plain delegation). The Stull worked example exhibits exactly
  this case and pins both behaviours.
- The shading is the drawn-curve (plain-temperature) region under
  `cape_cin`'s bounding rules; the J/kg numbers additionally carry the
  virtual-temperature correction and net integration the plotted curves
  cannot show. Bounds match; the divergence is documented in the module
  docstring and pinned (±, direction) by the eq.-(14.5) test.
- No published full-sounding CAPE value exists in the pinned source (its
  CAPE examples are figure-only), so the "known CAPE" anchor is Stull's
  published *formula* on the published sounding, plus tightly-toleranced
  published LCL/LFC and a windowed EL (formulation-hypersensitive in the
  isothermal layer). Fall-back to an NWS profile was considered and
  rejected: same virtual-correction mismatch, weaker provenance.
- `normand_point` validates Td ≤ T itself (`calc`'s one quantity-level
  boundary never sees `Sounding`'s single validation path).
- A NaN parcel start (NaN surface temperature/dewpoint — legal `Sounding`
  data) propagates NaN into the LCL and fails `Profile`'s span validation
  with a `TephpyValidationError` rather than a bespoke message — bad data
  still fails loudly at construction.
- `annotate_indices` takes no styling kwargs at v1 (spec names none); the
  panel axes is returned for restyling. The panel-width convention is
  relative ("35%"), so very small figures crowd the absolute-size text —
  the baseline uses a wider figure and the constant stays a convention.
- `clear()` tears the panel down and resets the axes locator — a
  re-cleared diagram reclaims its full slot instead of orphaning divider
  geometry.
- The two baselines total ~146 KB, riding into the sdist like the Plan 3/4
  sets; regeneration was verified bit-identical for the existing nine.
- Lint posture: `# numpydoc ignore=GL08` on the overload stubs (numpydoc
  1.10.0 has no overload handling), one justified
  `# type: ignore[arg-type]` for the `set_axes_locator(None)` stub defect,
  `# noqa: PLR0913` on `_parcel_curve`, and codespell-safe wording
  (`T_env`, never the bare two-letter abbreviation).

---

## Execution handoff

Plan 5 of 7 (spec §10). On completion, the §4 canonical usage runs end to
end except `ax.plot_barbs(snd)`: **Plan 6 (wind barbs & data ingest)** is
independent of this plan and consumes only Plan 4's `Sounding`; **Plan 7
(examples gallery & documentation completion)** needs the union of Plans
5 and 6 — including the composed §4-figure baseline this plan deliberately
does not add. Spec touch-ups when this plan's PR merges: mark the Plan 5
row complete in §10, and item 13's worked-example slice can record the
final fixture provenance (Stull v1.02b ch. 14 p. 496, transcribed
2026-07-26).
