# tephpy Sounding Data Model & Profile Plotting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Point-in-time record.** This plan states what was intended *before* implementation and is not updated afterwards. The review loop routinely revised what it records, so its code blocks drift from what shipped. The code is authoritative, and the design specification in [`../specs/`](../specs/) is the living statement of intent — read this for how the work was approached, not for how tephpy behaves today.

**Goal:** Deliver the `Sounding` data model with ingest-time validation and pandas/xarray constructors, the §5 units machinery (`_units.as_quantity` over MetPy's pint registry) with the public `tephpy.exceptions` hierarchy, and `TephigramAxes.plot_profile`/`plot_sounding` with multi-sounding overlays, legends, and profile image baselines — so the §4 canonical usage works up to `ax.plot_sounding(snd)`.

**Architecture:** Three new top-level modules along the §3 layering: public `exceptions.py` (no tephpy imports), private `_units.py` (imports only `exceptions`; MetPy behind function-local imports), and public `sounding.py` (imports `_units`/`_constants`/`exceptions`; the pandas/xarray constructors consume the objects handed to them, with `TYPE_CHECKING`-only imports — neither library is imported at runtime). `plotting/axes.py` gains two methods that convert quantities to diagram-native hPa/°C and plot through the existing `tephigram_transform + transData` machinery — `plotting` never imports `sounding` at runtime (duck-typed; a `TYPE_CHECKING` import only). `_constants.py` accretes the profile conventions; `Sounding` re-exports eagerly at the top level.

**Tech Stack:** Python 3.12/3.13/3.14, numpy, matplotlib (Agg in tests), pint (MetPy's registry), metpy (runtime dep, function-local imports), pandas/xarray (runtime deps, never imported by tephpy at runtime), hypothesis, pytest, pytest-mpl, pixi tasks.

**Spec:** `docs/src/developer/specs/2026-07-22-tephpy-design.md` — §3.4 (authority for `Sounding`), §5 (units policy — authority for `_units`), §6 (error handling — authority for `exceptions`), §3.2 (`plot_profile`/`plot_sounding`), §1 item 4 + §4 (overlays, legends, canonical usage), §7/§8.5 (profile image baselines), §10 (Plan 4 row; resolved items 2, 8, 9, 10).

This is **Plan 4 of 7** (spec §10). It produces working software: after it merges, `Sounding` ingests quantified/bare/DataFrame/Dataset profiles with validation at construction, and `ax.plot_sounding(snd)` draws red/green temperature/dewpoint profiles with derived legends over the Plan 3 diagram. Plans 5 and 6 are unblocked and may proceed in parallel.

## Global Constraints

Copied from the spec / Plans 1–3; every task's requirements implicitly include these.

- **Python support (SPEC 0):** 3.12, 3.13, and 3.14. **Platforms (pixi):** `linux-64` only.
- **Copyright header (every `.py` file, verbatim — ruff `CPY001` enforces it):**
  ```
  # Copyright (c) 2026, tephpy Contributors.
  #
  # This file is part of tephpy and is distributed under the 3-Clause BSD license.
  # See the LICENSE file in the package root directory for licensing details.
  ```
- **Imports:** every `.py` file needs `from __future__ import annotations` (ruff isort `required-imports`).
- **Lint/type:** ruff `ALL` (repo config); mypy `strict` clean over `src/tephpy` (spec §8.4). numpydoc-validation checks **every docstringed object, including private helpers**: any function that returns a value needs a `Returns` section (RT01) and documented parameters (PR01).
- **numpydoc + dataclasses gotcha (verified 2026-07-25):** the numpydoc-validation pre-commit hook is *static* — for a class it looks for a literal `def __init__` in the class body. A dataclass has none, so a `Parameters` section in a dataclass docstring fails PR02 ("Unknown parameters"). Document dataclass fields under an **`Attributes` section** instead (the Task 4 listing does this). Conversely, a hand-written `__init__` (Task 1's `TephpyValidationError`) **must** carry its own docstring or GL08 fires.
- **Function-local MetPy imports** (spec §5, §10 item 10) trigger ruff `PLC0415` — suppress with `# noqa: PLC0415` exactly as shown in the task code. pandas and xarray need no runtime import anywhere: the `Sounding` constructors are duck-typed over the objects handed to them, with `TYPE_CHECKING`-only annotation imports.
- **matplotlib kwargs pass-through:** `**kwargs: Any` (with `# noqa: ANN401`) is required on `plot_profile`/`plot_sounding` — `**kwargs: object` fails mypy strict because splatting `dict[str, object]` cannot satisfy `Axes.plot`'s typed keywords (verified 2026-07-25).
- **Units:** pint quantities at every public boundary; conversion via `.m_as(...)` — never `np.asarray(Quantity)`, which raises `pint.UnitStrippedWarning`, an **error** under the repo's pytest `filterwarnings = ["error"]`.
- **Tests:** pytest strict config with `filterwarnings = ["error"]`; close every matplotlib figure you open (pytest-mpl closes returned figures itself; the `tephigram_axes` fixture in `tests/plotting/test_axes.py` closes its own). The tests tree mirrors `src/tephpy`: `sounding.py`/`_units.py`/`exceptions.py` are top-level modules, so their tests live at the `tests/` root; the plotting tests join `tests/plotting/`.
- **Docs:** build must stay warning-free (`pixi run docs`). Titles use CMOS headline style. Glossary entries ship with the terms this plan introduces (spec §10 cross-cutting rule); sphinx-autoapi picks up new *public* modules (`exceptions`, `sounding`) automatically — `_units`, like `_constants`/`_config`, is private and gets no page.
- **Changelog:** one `changelog/<PR>.<type>.rst` fragment per PR, ending with author attribution via the `:user:` extlink role — Claude-authored fragments credit ``(:user:`claude`)`` (see `changelog/README.md`).
- **Branch:** work on a feature branch (`no-commit-to-branch` blocks `main`): `git switch -c sounding`.
- **Dedented listings:** the repo's blacken-docs hook formats this plan's fenced listings at top level, so code destined for a class body (Tasks 5(b), 6(b), 7(b)) and function body (Task 4's `test_import.py` fragment) is shown **dedented** — indent every line one level (4 spaces) when inserting.
- **Lint gotcha:** `pre-commit run --all-files` only checks files git knows about — **`git add` new files before `pixi run lint`** (every task's final step stages first for this reason).
- **Environment facts (verified against the committed lockfile, 2026-07-25):** metpy 1.7.1, pint 0.25.3, numpy 2.5.1, matplotlib 3.11.1, pandas 3.0.3, xarray 2026.7.0, pytest-mpl 0.19.0, freetype 2.14.3, pixi 0.72.1. pandas and xarray are **already in every locked environment** (transitive via MetPy), so declaring them direct (Task 5) leaves `pixi.lock` byte-identical — `pixi lock` reports "Lock-file was already up-to-date" (verified). pandas 3.0.3 ships **no `py.typed`** (xarray does), so `pandas.*` joins the mypy `ignore_missing_imports` override. pint facts verified: `isinstance(x, pint.Quantity)` is `True` for quantities from *any* registry; `.check("[pressure]")`/`.check("[temperature]")`/`.check("[speed]")` work as expected (including on offset units like `degC`), and `.check("")` means dimensionless. The code in this plan was verified against this environment: every listing passes ruff (`ALL` + format), mypy strict, and numpydoc-validation; the full suite (277 tests including the 9 image comparisons) passes on the `default`/py314 and `test-py312` environments; the docs build is warning-free; and an adversarial review pass executed every task's code and tests against this plan text (2026-07-25).

---

## File structure created or modified by this plan

```
src/tephpy/
  exceptions.py                       # NEW: public exception hierarchy (§6)
  _units.py                           # NEW: as_quantity + check_units_mapping (§5)
  sounding.py                         # NEW: Sounding dataclass + constructors (§3.4)
  _constants.py                       # MODIFIED: + profile conventions, label format
  plotting/axes.py                    # MODIFIED: + plot_profile, plot_sounding
  __init__.py                         # MODIFIED: export Sounding + exceptions
tests/
  test_exceptions.py                  # NEW: hierarchy + levels payload
  test_units.py                       # NEW: as_quantity/check_units_mapping + import-cost guard
  test_sounding.py                    # NEW: construction, validation, labels, constructors
  test_constants.py                   # MODIFIED: + profile-convention invariants
  test_import.py                      # MODIFIED: __all__, runtime deps list
  plotting/
    test_axes.py                      # MODIFIED: + plot_profile/plot_sounding behaviour
    test_images.py                    # MODIFIED: + 2 profile baselines
  baseline/
    test_profile_sounding.png         # NEW: generated baseline (~64 KB)
    test_sounding_overlay.png         # NEW: generated baseline (~64 KB)
docs/src/reference/glossary.rst       # MODIFIED: sounding updated; + dewpoint, profile
pyproject.toml                        # MODIFIED: pixi deps, mypy override, test per-file-ignores
requirements/pypi-core.txt            # MODIFIED: + pandas, xarray
changelog/<PR>.feature.rst            # NEW: news fragment (named after the PR, Task 10)
```

Naming used throughout (Interfaces contract):

```
tephpy.exceptions (public; imports nothing from tephpy):
    TephpyError(Exception)
    TephpyUnitsError(TephpyError)
    TephpyValidationError(TephpyError)
        __init__(message: str, *, levels: tuple[int, ...] = ())
        .levels: tuple[int, ...]          # zero-based offending level indices
    NonMonotonicPressureError(TephpyValidationError)
    DewpointExceedsTemperatureError(TephpyValidationError)

tephpy._units (private; imports exceptions only at module level):
    check_units_mapping(units: Mapping[str, str] | None, *, allowed) -> dict[str, str]
    as_quantity(value, *, name: str, units: str | None = None, dimension: str)
        -> pint.Quantity                  # float64, on MetPy's registry

tephpy._constants (additions):
    PROFILE_TEMPERATURE_COLOR = "red"     # operational/MetPy convention
    PROFILE_DEWPOINT_COLOR = "green"
    PROFILE_LINEWIDTH = 1.5
    PROFILE_ZORDER = 2.5                  # above families (<=1.5) and Line2D default (2)
    SOUNDING_LABEL_FORMAT = "{station} {time:%Y-%m-%d %H}Z"

tephpy.sounding:
    Sounding                              # @dataclass(frozen=True, eq=False)
        fields: pressure, temperature, dewpoint=None, wind_speed=None,
                wind_direction=None, station=None, time=None, label=None,
                units=InitVar (Mapping[str, str] | None)
        from_dataframe(df, *, units=None, station=None, time=None, label=None,
                       **column_map) -> Sounding
        from_dataset(ds, *, units=None, station=None, time=None, label=None,
                     **var_map) -> Sounding

tephpy.plotting.axes.TephigramAxes (additions):
    plot_profile(pressure, temperature, *, units=None, label=None, **kwargs)
        -> Line2D
    plot_sounding(snd, *, label=None, **kwargs)
        -> tuple[Line2D, Line2D | None]   # (temperature_line, dewpoint_line)

tephpy top level:
    __all__ = ["Sounding", "__version__", "config", "exceptions", "plotting",
               "transforms"]
```

Design decisions locked here (shared vocabulary for all tasks):

- **`as_quantity` always re-wraps onto MetPy's registry.** Any input quantity is decomposed to `(magnitude, str(units))` and re-wrapped, and bare arrays are wrapped with the caller's unit string — so every output is float64 on the one registry, and quantities from a user's own registry flow into `metpy.calc` (Plan 5) without cross-registry errors (spec §5). Dimensionality is checked *after* wrapping; the empty string `""` means dimensionless (wind direction — an angle).
- **`units=` is per-boundary.** At multi-argument boundaries the public `units=` argument is a mapping keyed by argument/field name (spec §5), validated once with `check_units_mapping` (unknown keys are a `TephpyUnitsError` — they are almost certainly typos), then each entry feeds `as_quantity(..., units=mapping.get(name))`.
- **Error taxonomy.** Bad *data* raises the §6 hierarchy (`TephpyUnitsError`, `TephpyValidationError` + subclasses, with `levels` naming the offending indices). Bad *code* raises Python-idiom errors: unknown field names in `column_map`/`var_map` → `TypeError`; a required or explicitly mapped column/variable missing → `KeyError`; a `time` of an unsupported type → `TypeError`. `set_extent`'s existing `ValueError`s stay as they are (documented Plan 3 judgment call).
- **`Sounding` is `@dataclass(frozen=True, eq=False)`.** Frozen per spec §3.4; `eq=False` because the generated `__eq__` would compare arrays and raise "truth value is ambiguous". Coercion/validation happens in `__post_init__` via `object.__setattr__` (the standard frozen-dataclass idiom). Field annotations state the *post-init guarantee* (`pint.Quantity`), not the permissive runtime inputs — mypy-strict users are steered toward quantities while bare-array + `units=` input keeps working (spec §3.4).
- **Validation order** (§6 — fail at ingest): units coercion per field → shapes (1-D, equal length, ≥ 2 levels) → wind pairing → dewpoint ≤ temperature where both non-NaN (compared in °C, so mixed input units compare physically; checked *before* pressure normalization so every error's `levels` payload indexes the caller's input order) → pressure finite + strictly monotonic (normalize to decreasing, reversing **all** present data arrays together) → time normalization (naive → UTC; aware → converted; `numpy.datetime64` accepted, `pandas.Timestamp` already *is* a `datetime`) → label derivation.
- **Label semantics** (spec §10 item 8): explicit `label=` stands; else derived via `SOUNDING_LABEL_FORMAT` when both `station` and `time` are present; else `None`. `plot_sounding` resolves `label=` argument > `snd.label` > `None`; a `None` label leaves matplotlib's auto `"_childN"` label, which `ax.legend()` skips — so "no legend entry" needs no special casing. The dewpoint line is always `"_nolegend_"`: one legend entry per sounding, attached to the temperature line.
- **`plot_sounding` kwargs** apply to **both** lines and override the convention defaults (so `color="purple"` makes both lines purple — per-call styling is exactly how forecast-vs-observed overlays stay distinguishable, spec §1 item 4). `plot_profile` sets **no** style defaults: it is the low-level primitive (§4 styles parcel paths explicitly at the call site).
- **SPEC 0 floors** for the new direct dependencies (checked against the SPEC 0 schedule, 2026-07-25): `pandas>=2.3`, `xarray>=2024.10`. Both are conda-forge packages; both already arrive transitively via MetPy, so the declaration adds no install weight (spec §10 item 9).
- **Placement:** the `PROFILE_*`/`SOUNDING_LABEL_FORMAT` constants are inserted in `_constants.py` after the `MOIST_ADIABAT_ZORDER` block, before the `LABEL_*` (isopleth label) block.
- **Lint posture:** tests gain `ANN003` (unannotated `**kwargs` on test helpers) and `DTZ001` (naive datetimes are deliberate fixtures — the boundary under test reads them as UTC) in their per-file-ignores; the two axes methods suppress `ANN401` per parameter (matplotlib pass-through).

---

## Task 1: The public exception hierarchy

**Files:**
- Create: `src/tephpy/exceptions.py`
- Test: `tests/test_exceptions.py`

**Interfaces:**
- Produces: the `tephpy.exceptions` names in the contract above. Tasks 2 and 4 import them; the module joins the top-level namespace in Task 4 (one `__init__.py`/`test_import.py` update instead of two). Until then `from tephpy.exceptions import ...` already works.

- [ ] **Step 1: Create the branch, then write the failing tests**

```bash
git switch -c sounding
```

Create `tests/test_exceptions.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the public exception hierarchy (spec §6)."""

from __future__ import annotations

import pytest

from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    NonMonotonicPressureError,
    TephpyError,
    TephpyUnitsError,
    TephpyValidationError,
)


def test_hierarchy():
    """Every tephpy exception is catchable as TephpyError."""
    assert issubclass(TephpyUnitsError, TephpyError)
    assert issubclass(TephpyValidationError, TephpyError)
    assert issubclass(NonMonotonicPressureError, TephpyValidationError)
    assert issubclass(DewpointExceedsTemperatureError, TephpyValidationError)
    assert issubclass(TephpyError, Exception)


def test_validation_error_carries_levels():
    error = TephpyValidationError("bad levels", levels=(2, 5))
    assert error.levels == (2, 5)
    assert str(error) == "bad levels"


def test_validation_error_levels_default_empty():
    assert TephpyValidationError("nothing specific").levels == ()


@pytest.mark.parametrize(
    "exception", [NonMonotonicPressureError, DewpointExceedsTemperatureError]
)
def test_subclasses_carry_levels(exception):
    error = exception("boom", levels=(1,))
    assert error.levels == (1,)
    with pytest.raises(TephpyError):
        raise error
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_exceptions.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'tephpy.exceptions'` (collection error is fine).

- [ ] **Step 3: Create the module**

Create `src/tephpy/exceptions.py` — this exact code passes ruff (`ALL` + format), mypy strict, and numpydoc-validation (verified 2026-07-25); note the `__init__` docstring, which the static numpydoc hook requires (GL08):

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The public tephpy exception hierarchy (spec §6).

Every exception tephpy raises for user-correctable input derives from
:class:`TephpyError`, so ``except TephpyError`` catches them all. Units
problems raise :class:`TephpyUnitsError`; physically impossible data raises
a :class:`TephpyValidationError` subclass carrying the offending level
indices. Validation happens at ingest (``Sounding`` construction), not
mid-plot.
"""

from __future__ import annotations

__all__ = [
    "DewpointExceedsTemperatureError",
    "NonMonotonicPressureError",
    "TephpyError",
    "TephpyUnitsError",
    "TephpyValidationError",
]


class TephpyError(Exception):
    """Root of the tephpy exception hierarchy."""


class TephpyUnitsError(TephpyError):
    """Missing, ambiguous, unparsable, or wrong-dimension units (spec §5)."""


class TephpyValidationError(TephpyError):
    """Physically impossible input, identified by level indices (spec §6).

    Parameters
    ----------
    message : str
        Description of the failed validation.
    levels : tuple of int, optional
        Zero-based indices of the offending levels, when the failure is
        attributable to specific levels.

    Attributes
    ----------
    levels : tuple of int
        Zero-based indices of the offending levels; empty when the failure
        is not attributable to specific levels.
    """

    def __init__(self, message: str, *, levels: tuple[int, ...] = ()) -> None:
        """Store the message and the offending level indices.

        Parameters
        ----------
        message : str
            Description of the failed validation.
        levels : tuple of int, optional
            Zero-based indices of the offending levels.
        """
        super().__init__(message)
        self.levels = levels


class NonMonotonicPressureError(TephpyValidationError):
    """Pressure is not strictly monotonic (spec §3.4)."""


class DewpointExceedsTemperatureError(TephpyValidationError):
    """Dewpoint exceeds temperature at one or more levels (spec §3.4).

    Equality — saturation — is physical and accepted; only strict excess
    is rejected.
    """
```

(Codespell note: spell it "unparsable" — the variant spelling with an extra "e" fails the codespell hook.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_exceptions.py -q --no-cov`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/exceptions.py tests/test_exceptions.py
pixi run lint
git commit -m "feat: add the public tephpy exception hierarchy"
```

---

## Task 2: The `_units` boundary coercion helpers

**Files:**
- Create: `src/tephpy/_units.py`
- Test: `tests/test_units.py`

**Interfaces:**
- Consumes: `TephpyUnitsError` (Task 1).
- Produces: `as_quantity(value, *, name, units=None, dimension)` and `check_units_mapping(units, *, allowed)` (contract above). Tasks 4 and 6 call exactly these.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_units.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the boundary units coercion helpers (spec §5)."""

from __future__ import annotations

import subprocess
import sys

from metpy.units import units
import numpy as np
import pint
import pytest

from tephpy._units import as_quantity, check_units_mapping
from tephpy.exceptions import TephpyUnitsError


def test_quantity_passes_through():
    quantity = units.Quantity(np.array([1000.0, 850.0]), "hPa")
    result = as_quantity(quantity, name="pressure", dimension="[pressure]")
    np.testing.assert_array_equal(result.magnitude, [1000.0, 850.0])
    assert result.units == units.hPa


def test_foreign_registry_quantity_rewrapped():
    """A quantity from another pint registry lands on MetPy's registry."""
    foreign = pint.UnitRegistry()
    quantity = foreign.Quantity(np.array([1000.0]), "hPa")
    result = as_quantity(quantity, name="pressure", dimension="[pressure]")
    assert result._REGISTRY is not foreign
    assert result.m_as("Pa") == pytest.approx(100000.0)


def test_bare_array_with_units():
    result = as_quantity(
        [20.0, 10.0], name="temperature", units="degC", dimension="[temperature]"
    )
    assert result.magnitude.dtype == np.float64
    assert result.m_as("K")[0] == pytest.approx(293.15)


def test_integer_input_coerced_to_float64():
    result = as_quantity(
        np.array([1000, 850]), name="pressure", units="hPa", dimension="[pressure]"
    )
    assert result.magnitude.dtype == np.float64


def test_bare_array_without_units_raises():
    with pytest.raises(TephpyUnitsError, match=r"'pressure' has no units"):
        as_quantity([1000.0], name="pressure", dimension="[pressure]")


def test_quantity_plus_units_is_ambiguous():
    quantity = units.Quantity([1000.0], "hPa")
    with pytest.raises(TephpyUnitsError, match="already a quantity"):
        as_quantity(quantity, name="pressure", units="hPa", dimension="[pressure]")


def test_wrong_dimensionality_raises():
    quantity = units.Quantity([20.0], "degC")
    with pytest.raises(TephpyUnitsError, match="expected \\[pressure\\]"):
        as_quantity(quantity, name="pressure", dimension="[pressure]")


def test_unparsable_unit_raises():
    with pytest.raises(TephpyUnitsError, match="unparsable unit"):
        as_quantity([1.0], name="pressure", units="bogons", dimension="[pressure]")


def test_dimensionless_dimension():
    """The empty dimension string means dimensionless (e.g. wind direction)."""
    result = as_quantity([270.0], name="wind_direction", units="deg", dimension="")
    assert result.dimensionless
    with pytest.raises(TephpyUnitsError, match="expected dimensionless"):
        as_quantity([270.0], name="wind_direction", units="hPa", dimension="")


def test_check_units_mapping():
    allowed = ("pressure", "temperature")
    assert check_units_mapping(None, allowed=allowed) == {}
    mapping = {"pressure": "hPa"}
    assert check_units_mapping(mapping, allowed=allowed) == mapping
    with pytest.raises(TephpyUnitsError, match="unknown argument"):
        check_units_mapping({"bogus": "hPa"}, allowed=allowed)


def test_import_tephpy_does_not_import_heavy_dependencies():
    """`import tephpy` must not import metpy, pandas, or xarray (item 10).

    MetPy loads on first use (as_quantity); pandas and xarray are never
    imported by tephpy at runtime at all. Run in a subprocess so the
    check is independent of what this session already imported.
    """
    code = (
        "import sys, tephpy; raise SystemExit("
        "1 if {'metpy', 'pandas', 'xarray'} & set(sys.modules) else 0)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603
```

(The `# noqa: S603` is required — ruff flags every `subprocess.run`; the argv
here is a fixed literal run through `sys.executable`.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_units.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'tephpy._units'` (collection error is fine).

- [ ] **Step 3: Create the module**

Create `src/tephpy/_units.py` — this exact code passes ruff, mypy strict, and numpydoc-validation (verified 2026-07-25):

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Boundary units coercion over MetPy's pint registry (spec §5).

Every public tephpy boundary accepts pint quantities and converts
internally; bare arrays are accepted only with an explicit ``units=``
argument — never silently assumed. At multi-argument boundaries ``units=``
is a mapping keyed by argument or field name, validated by
:func:`check_units_mapping`; each value then passes through
:func:`as_quantity`, the single coercion helper.

tephpy standardizes on MetPy's registry — one registry across tephpy,
MetPy, and user code — so quantities flow into ``metpy.calc`` without
cross-registry errors. MetPy is imported function-locally so that
``import tephpy`` stays light (spec §10 item 10).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from tephpy.exceptions import TephpyUnitsError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    import pint

__all__ = ["as_quantity", "check_units_mapping"]


def check_units_mapping(
    units: Mapping[str, str] | None, *, allowed: Iterable[str]
) -> dict[str, str]:
    """Validate the keys of a boundary's ``units=`` mapping.

    Parameters
    ----------
    units : mapping of str to str or None
        The ``units=`` argument: argument or field names mapped to unit
        strings, or ``None`` when not given.
    allowed : iterable of str
        The argument or field names this boundary accepts.

    Returns
    -------
    dict of str to str
        The validated mapping (empty for ``None``).

    Raises
    ------
    TephpyUnitsError
        If the mapping names an unknown argument or field.
    """
    if units is None:
        return {}
    unknown = set(units) - set(allowed)
    if unknown:
        msg = (
            f"units= names unknown argument(s) {sorted(unknown)!r}; "
            f"expected a mapping keyed by {sorted(allowed)!r}"
        )
        raise TephpyUnitsError(msg)
    return dict(units)


def as_quantity(
    value: object, *, name: str, units: str | None = None, dimension: str
) -> pint.Quantity:
    """Coerce one boundary argument to a MetPy-registry pint quantity.

    A pint quantity (from any registry) is re-wrapped onto MetPy's
    registry; a bare array is wrapped with the required `units`. Either
    way the result is float64 and dimension-checked.

    Parameters
    ----------
    value : object
        The argument value: a pint quantity, or a bare array-like with
        `units` given.
    name : str
        The argument or field name, used in error messages.
    units : str, optional
        The unit for a bare array-like `value` (from the boundary's
        ``units=`` mapping). Must be omitted when `value` is already a
        quantity.
    dimension : str
        The required pint dimensionality, e.g. ``"[pressure]"``;
        ``""`` means dimensionless.

    Returns
    -------
    pint.Quantity
        The float64 quantity on MetPy's registry.

    Raises
    ------
    TephpyUnitsError
        For unit-less input without `units`, the ambiguous
        quantity-plus-`units` case, an unparsable unit string, or the
        wrong dimensionality.
    """
    # Function-local so `import tephpy` stays light (spec §5, §10 item 10).
    from metpy.units import units as registry  # noqa: PLC0415
    import pint  # noqa: PLC0415

    if isinstance(value, pint.Quantity):
        if units is not None:
            msg = (
                f"{name!r} is already a quantity, but units= names it too: "
                f"drop the units[{name!r}] entry or pass a bare array"
            )
            raise TephpyUnitsError(msg)
        magnitude = np.asarray(value.magnitude, dtype=np.float64)
        unit = str(value.units)
    else:
        if units is None:
            msg = (
                f"{name!r} has no units: pass a pint quantity, or add "
                f'units={{"{name}": "<unit>"}}'
            )
            raise TephpyUnitsError(msg)
        magnitude = np.asarray(value, dtype=np.float64)
        unit = units
    try:
        quantity = registry.Quantity(magnitude, unit)
    except (pint.PintError, TypeError, ValueError) as error:
        msg = f"{name!r} has an unparsable unit {unit!r}: {error}"
        raise TephpyUnitsError(msg) from error
    if not quantity.check(dimension):
        expected = dimension or "dimensionless"
        msg = (
            f"{name!r} has dimensionality {quantity.dimensionality} "
            f"({quantity.units}); expected {expected}"
        )
        raise TephpyUnitsError(msg)
    return quantity
```

Implementation notes (verified on pint 0.25.3 / metpy 1.7.1):
- `isinstance(value, pint.Quantity)` is `True` for quantities from any
  registry, so foreign-registry quantities are detected and re-wrapped
  through `(magnitude, str(units))` — no registry-identity checks needed.
- `np.asarray(value.magnitude, ...)` touches only the bare magnitude —
  never the quantity — so no `UnitStrippedWarning` is possible.
- The `except` clause catches `pint.PintError` (undefined/garbled unit
  strings) plus `TypeError`/`ValueError` (non-string nonsense passed as a
  unit), converting all of them to the §6 `TephpyUnitsError`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_units.py -q --no-cov`
Expected: PASS (the subprocess import-cost guard runs `import tephpy` in a clean interpreter).

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/_units.py tests/test_units.py
pixi run lint
git commit -m "feat: add the pint boundary coercion helpers over MetPy's registry"
```

---

## Task 3: `_constants` profile conventions

**Files:**
- Modify: `src/tephpy/_constants.py`
- Test: `tests/test_constants.py` (append)

**Interfaces:**
- Produces: `PROFILE_TEMPERATURE_COLOR`, `PROFILE_DEWPOINT_COLOR`, `PROFILE_LINEWIDTH`, `PROFILE_ZORDER`, `SOUNDING_LABEL_FORMAT`. Task 4 consumes the label format; Task 7 consumes the styles.

- [ ] **Step 1: Write the failing tests**

In `tests/test_constants.py`, extend the import block at the top of the file to (keeping it sorted — `datetime` precedes `numpy`):

```python
from __future__ import annotations

from datetime import UTC, datetime

import numpy as np

from tephpy import _constants as constants
```

then append to the end of the file:

```python
def test_profile_conventions():
    """Profiles draw above every family and matplotlib's default lines."""
    family_zorders = (
        constants.ISOTHERM_ZORDER,
        constants.DRY_ADIABAT_ZORDER,
        constants.ISOBAR_ZORDER,
        constants.MIXING_RATIO_ZORDER,
        constants.MOIST_ADIABAT_ZORDER,
    )
    assert max(family_zorders) < constants.PROFILE_ZORDER
    assert constants.PROFILE_ZORDER > 2.0
    assert constants.PROFILE_TEMPERATURE_COLOR != constants.PROFILE_DEWPOINT_COLOR
    assert constants.PROFILE_LINEWIDTH > constants.ISOPLETH_LINEWIDTH


def test_sounding_label_format():
    """The derived-label convention renders as station then UTC time."""
    label = constants.SOUNDING_LABEL_FORMAT.format(
        station="03808", time=datetime(2026, 7, 21, 12, tzinfo=UTC)
    )
    assert label == "03808 2026-07-21 12Z"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_constants.py -q --no-cov`
Expected: FAIL — `AttributeError: module 'tephpy._constants' has no attribute 'PROFILE_ZORDER'`.

- [ ] **Step 3: Add the conventions**

In `src/tephpy/_constants.py`, insert after the `MOIST_ADIABAT_ZORDER` block
(before the `LABEL_FONTSIZE` block):

```python
#: Temperature profile line colour (the operational/MetPy convention:
#: temperature red, dewpoint green; spec §3.2).
PROFILE_TEMPERATURE_COLOR: Final[str] = "red"

#: Dewpoint profile line colour (the operational/MetPy convention).
PROFILE_DEWPOINT_COLOR: Final[str] = "green"

#: Profile line width in points.
PROFILE_LINEWIDTH: Final[float] = 1.5

#: Profile draw order: above every isopleth family and above matplotlib's
#: default ``Line2D`` zorder of 2.
PROFILE_ZORDER: Final[float] = 2.5

#: Derived sounding legend label (spec §3.4), e.g. ``"03808 2026-07-21 12Z"``.
SOUNDING_LABEL_FORMAT: Final[str] = "{station} {time:%Y-%m-%d %H}Z"
```

(The label format is a `str.format` template with a nested `datetime`
format spec: hours only, per the operational `"12Z"` convention; the
Task 4 normalizer guarantees the `time` it receives is UTC.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_constants.py -q --no-cov`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/_constants.py tests/test_constants.py
pixi run lint
git commit -m "feat: seed the profile and sounding-label conventions"
```

---

## Task 4: The `Sounding` data model core

**Files:**
- Create: `src/tephpy/sounding.py` (without the pandas/xarray constructors — Task 5 appends those)
- Modify: `src/tephpy/__init__.py`
- Modify: `tests/test_import.py` (the `__all__` assertion)
- Test: `tests/test_sounding.py`

**Interfaces:**
- Consumes: `as_quantity`/`check_units_mapping` (Task 2), the exception types (Task 1), `SOUNDING_LABEL_FORMAT` (Task 3).
- Produces: `Sounding` with the field set in the contract, re-exported at the top level (`from tephpy import Sounding`, spec §10 item 10); `_FIELD_DIMENSIONS` (module-private), which Task 5's constructors iterate. Task 7's `plot_sounding` reads `snd.pressure`/`snd.temperature`/`snd.dewpoint`/`snd.label`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sounding.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the Sounding data model (spec §3.4/§6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from hypothesis import given
from hypothesis import strategies as st
from metpy.units import units
import numpy as np
import pytest

import tephpy
from tephpy import Sounding
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    NonMonotonicPressureError,
    TephpyUnitsError,
    TephpyValidationError,
)

PRESSURE = units.Quantity(np.array([1000.0, 850.0, 700.0, 500.0]), "hPa")
TEMPERATURE = units.Quantity(np.array([20.0, 12.0, 4.0, -12.0]), "degC")
DEWPOINT = units.Quantity(np.array([15.0, 8.0, np.nan, -30.0]), "degC")


def test_sounding_reexported_at_top_level():
    """`from tephpy import Sounding` works (spec §10 item 10)."""
    assert tephpy.Sounding is Sounding


def test_construction_from_quantities():
    snd = Sounding(PRESSURE, TEMPERATURE, dewpoint=DEWPOINT)
    np.testing.assert_array_equal(snd.pressure.m_as("hPa"), PRESSURE.magnitude)
    np.testing.assert_array_equal(snd.temperature.m_as("degC"), TEMPERATURE.magnitude)
    assert snd.station is None
    assert snd.time is None
    assert snd.label is None


def test_construction_from_bare_arrays_with_units():
    snd = Sounding(
        [1000.0, 850.0],
        [20.0, 12.0],
        units={"pressure": "hPa", "temperature": "degC"},
    )
    assert snd.pressure.check("[pressure]")
    assert snd.temperature.check("[temperature]")


def test_kelvin_and_pascal_just_work():
    """Any pressure/temperature units convert on use (spec §5)."""
    snd = Sounding(
        units.Quantity(np.array([100000.0, 85000.0]), "Pa"),
        units.Quantity(np.array([293.15, 285.15]), "K"),
    )
    np.testing.assert_allclose(snd.pressure.m_as("hPa"), [1000.0, 850.0])
    np.testing.assert_allclose(snd.temperature.m_as("degC"), [20.0, 12.0])


def test_bare_arrays_without_units_raise():
    with pytest.raises(TephpyUnitsError, match="'pressure' has no units"):
        Sounding([1000.0, 850.0], TEMPERATURE[:2])


def test_unknown_units_key_raises():
    with pytest.raises(TephpyUnitsError, match="unknown argument"):
        Sounding(PRESSURE[:2], TEMPERATURE[:2], units={"bogus": "hPa"})


def test_swapped_dimensions_raise():
    with pytest.raises(TephpyUnitsError, match="'pressure' has dimensionality"):
        Sounding(TEMPERATURE, PRESSURE)


def test_too_few_levels_raises():
    with pytest.raises(TephpyValidationError, match="at least 2 levels"):
        Sounding(PRESSURE[:1], TEMPERATURE[:1])


def test_length_mismatch_raises():
    with pytest.raises(TephpyValidationError, match="equal length"):
        Sounding(PRESSURE[:3], TEMPERATURE)


def test_non_1d_raises():
    pressure = units.Quantity(np.array([[1000.0, 850.0]]), "hPa")
    temperature = units.Quantity(np.array([[20.0, 12.0]]), "degC")
    with pytest.raises(TephpyValidationError, match="must be 1-D"):
        Sounding(pressure, temperature)


def test_wind_fields_must_arrive_together():
    speed = units.Quantity(np.full(4, 15.0), "knots")
    direction = units.Quantity(np.full(4, 270.0), "deg")
    with pytest.raises(TephpyValidationError, match="arrive together"):
        Sounding(PRESSURE, TEMPERATURE, wind_speed=speed)
    with pytest.raises(TephpyValidationError, match="arrive together"):
        Sounding(PRESSURE, TEMPERATURE, wind_direction=direction)
    snd = Sounding(PRESSURE, TEMPERATURE, wind_speed=speed, wind_direction=direction)
    assert snd.wind_speed is not None
    assert snd.wind_direction is not None


def test_increasing_pressure_normalized_with_all_arrays_reversed():
    """Either monotonic direction is accepted; storage is surface-first."""
    speed = units.Quantity(np.array([5.0, 10.0, 20.0, 40.0]), "knots")
    direction = units.Quantity(np.array([180.0, 200.0, 240.0, 270.0]), "deg")
    snd = Sounding(
        PRESSURE[::-1],
        TEMPERATURE[::-1],
        dewpoint=DEWPOINT[::-1],
        wind_speed=speed[::-1],
        wind_direction=direction[::-1],
    )
    np.testing.assert_array_equal(snd.pressure.magnitude, PRESSURE.magnitude)
    np.testing.assert_array_equal(snd.temperature.magnitude, TEMPERATURE.magnitude)
    np.testing.assert_array_equal(snd.dewpoint.magnitude, DEWPOINT.magnitude)
    np.testing.assert_array_equal(snd.wind_speed.magnitude, speed.magnitude)
    np.testing.assert_array_equal(snd.wind_direction.magnitude, direction.magnitude)


@given(
    pressures=st.lists(
        st.floats(min_value=10.0, max_value=1050.0),
        min_size=2,
        max_size=30,
        unique=True,
    ),
    increasing=st.booleans(),
)
def test_any_strictly_monotonic_pressure_stores_decreasing(pressures, increasing):
    """Property: monotonic input of either direction stores decreasing."""
    ordered = np.sort(np.asarray(pressures, dtype=np.float64))
    if not increasing:
        ordered = ordered[::-1]
    temperature = np.linspace(20.0, -40.0, ordered.size)
    snd = Sounding(
        ordered,
        temperature,
        units={"pressure": "hPa", "temperature": "degC"},
    )
    assert np.all(np.diff(snd.pressure.magnitude) < 0.0)


def test_non_monotonic_pressure_raises_with_levels():
    pressure = units.Quantity(np.array([1000.0, 850.0, 900.0, 800.0]), "hPa")
    with pytest.raises(NonMonotonicPressureError, match="strictly monotonic") as info:
        Sounding(pressure, TEMPERATURE)
    assert info.value.levels == (2,)


def test_nan_pressure_raises_with_levels():
    """NaN gaps are data everywhere except pressure (spec §3.4)."""
    pressure = units.Quantity(np.array([1000.0, np.nan, 700.0, 500.0]), "hPa")
    with pytest.raises(TephpyValidationError, match="finite") as info:
        Sounding(pressure, TEMPERATURE)
    assert info.value.levels == (1,)


def test_nan_temperature_and_dewpoint_are_data():
    temperature = units.Quantity(np.array([20.0, np.nan, 4.0, -12.0]), "degC")
    snd = Sounding(PRESSURE, temperature, dewpoint=DEWPOINT)
    assert np.isnan(snd.temperature.magnitude[1])


def test_dewpoint_above_temperature_raises_with_levels():
    dewpoint = units.Quantity(np.array([25.0, 8.0, np.nan, -10.0]), "degC")
    with pytest.raises(DewpointExceedsTemperatureError) as info:
        Sounding(PRESSURE, TEMPERATURE, dewpoint=dewpoint)
    assert info.value.levels == (0, 3)


def test_dewpoint_levels_index_the_input_order():
    """Levels index the caller's arrays, not the normalized storage."""
    pressure = units.Quantity(np.array([500.0, 700.0, 850.0, 1000.0]), "hPa")
    temperature = units.Quantity(np.array([-12.0, 4.0, 12.0, 20.0]), "degC")
    dewpoint = units.Quantity(np.array([-5.0, 0.0, 8.0, 15.0]), "degC")
    with pytest.raises(DewpointExceedsTemperatureError) as info:
        Sounding(pressure, temperature, dewpoint=dewpoint)
    assert info.value.levels == (0,)


def test_saturation_is_physical():
    """Dewpoint equal to temperature — saturation — is accepted."""
    snd = Sounding(PRESSURE, TEMPERATURE, dewpoint=TEMPERATURE)
    assert snd.dewpoint is not None


def test_dewpoint_comparison_converts_units():
    """The Td > T check compares physical values, not magnitudes."""
    dewpoint_k = units.Quantity(TEMPERATURE.m_as("K") + 1.0, "K")
    with pytest.raises(DewpointExceedsTemperatureError):
        Sounding(PRESSURE, TEMPERATURE, dewpoint=dewpoint_k)


def test_label_derives_from_station_and_time():
    snd = Sounding(
        PRESSURE, TEMPERATURE, station="03808", time=datetime(2026, 7, 21, 12)
    )
    assert snd.label == "03808 2026-07-21 12Z"


def test_label_requires_both_station_and_time():
    assert Sounding(PRESSURE, TEMPERATURE, station="03808").label is None
    assert Sounding(PRESSURE, TEMPERATURE, time=datetime(2026, 7, 21, 12)).label is None


def test_explicit_label_wins():
    snd = Sounding(
        PRESSURE,
        TEMPERATURE,
        station="03808",
        time=datetime(2026, 7, 21, 12),
        label="forecast",
    )
    assert snd.label == "forecast"


def test_naive_time_read_as_utc_aware_converted():
    """Naive datetimes are UTC; aware ones convert to UTC (spec §3.4)."""
    naive = Sounding(PRESSURE, TEMPERATURE, station="X", time=datetime(2026, 7, 21, 12))
    assert naive.time == datetime(2026, 7, 21, 12, tzinfo=UTC)
    plus_two = timezone(timedelta(hours=2))
    aware = Sounding(
        PRESSURE,
        TEMPERATURE,
        station="X",
        time=datetime(2026, 7, 21, 14, tzinfo=plus_two),
    )
    assert aware.time == datetime(2026, 7, 21, 12, tzinfo=UTC)
    assert aware.label == "X 2026-07-21 12Z"


def test_datetime64_time_accepted():
    snd = Sounding(
        PRESSURE, TEMPERATURE, station="X", time=np.datetime64("2026-07-21T12:00")
    )
    assert snd.time == datetime(2026, 7, 21, 12, tzinfo=UTC)


def test_bad_time_type_raises():
    with pytest.raises(TypeError, match="time must be"):
        Sounding(PRESSURE, TEMPERATURE, time="2026-07-21")
```

Also, in `tests/test_import.py`, replace the final assertion of
`test_top_level_namespace` with (dedented listing — keep the function-body
indentation when pasting):

```python
expected = {
    "Sounding",
    "__version__",
    "config",
    "exceptions",
    "plotting",
    "transforms",
}
assert set(tephpy.__all__) == expected
```

(Naive `datetime(...)` calls in tests trigger ruff `DTZ001`; that rule joins
the tests per-file-ignores in this task's Step 3 — the naive-input cases are
exactly what is under test.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_sounding.py tests/test_import.py -q --no-cov`
Expected: FAIL — `ImportError: cannot import name 'Sounding' from 'tephpy'` (collection error is fine).

- [ ] **Step 3: Create the module and wire the top level**

**(a)** Create `src/tephpy/sounding.py` — this exact code passes ruff, mypy
strict, and numpydoc-validation (verified 2026-07-25). Notes baked into the
listing: the class docstring uses an **`Attributes`** section (the static
numpydoc hook cannot see a dataclass `__init__` — a `Parameters` section
fails PR02); the module docstring intentionally describes the finished
module including the Task 5 constructors (the Plan 3 precedent); the
`time: object` local in `_normalize_time` is what keeps mypy's
`warn_unreachable` satisfied while the boundary accepts more types than the
field annotation.

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The ``Sounding`` data model (spec §3.4).

A :class:`Sounding` is a frozen dataclass holding one ascent's
pressure/temperature/dewpoint/wind arrays as pint quantities on MetPy's
registry, plus optional station/time metadata and a derived legend label.
Inputs are coerced and validated at construction — bad data fails at
ingest, not mid-plot (spec §6) — and pressure is normalized to decreasing
(surface-first) storage with all arrays reversed together, so downstream
``metpy.calc`` sees one orientation.

The pandas/xarray constructors consume the objects handed to them —
neither library is imported at runtime — so ``import tephpy`` stays
light (spec §10 item 10).
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

import numpy as np

from tephpy._constants import SOUNDING_LABEL_FORMAT
from tephpy._units import as_quantity, check_units_mapping
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    NonMonotonicPressureError,
    TephpyValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pint

__all__ = ["Sounding"]

#: The data fields with their required dimensionalities (spec §5);
#: ``""`` means dimensionless (wind direction is an angle).
_FIELD_DIMENSIONS: Final[dict[str, str]] = {
    "pressure": "[pressure]",
    "temperature": "[temperature]",
    "dewpoint": "[temperature]",
    "wind_speed": "[speed]",
    "wind_direction": "",
}

#: Minimum number of levels in a sounding.
_MIN_LEVELS: Final[int] = 2


@dataclasses.dataclass(frozen=True, eq=False)
class Sounding:
    """One sounding: quantified profile arrays plus metadata (spec §3.4).

    Pressure and temperature are required; dewpoint and wind are optional,
    and the two wind fields must arrive together. Bare arrays need the
    ``units=`` mapping; a constructed Sounding always holds pint
    quantities on MetPy's registry, with pressure stored decreasing
    (surface-first). NaN gaps are data everywhere except pressure.

    Attributes
    ----------
    pressure : pint.Quantity
        Level pressures; required, finite, and strictly monotonic (either
        direction accepted, normalized to decreasing).
    temperature : pint.Quantity
        Level temperatures; required.
    dewpoint : pint.Quantity or None
        Level dewpoints; where dewpoint and temperature are both non-NaN,
        dewpoint above temperature is rejected (equality — saturation —
        is physical).
    wind_speed : pint.Quantity or None
        Level wind speeds; requires `wind_direction`.
    wind_direction : pint.Quantity or None
        Level wind directions (degrees from north); requires `wind_speed`.
    station : str or None
        Station identifier, e.g. ``"03808"``.
    time : datetime.datetime or None
        Launch time; ``numpy.datetime64`` input is accepted, naive
        datetimes are read as UTC, and aware ones are converted to UTC.
    label : str or None
        Legend text. When not given it derives as e.g.
        ``"03808 2026-07-21 12Z"`` if both `station` and `time` are
        present, else ``None`` — and ``None`` means no legend entry.
    units : mapping of str to str, optional
        Construction-only (not stored): unit strings for bare-array
        fields, keyed by field name, e.g. ``units={"pressure": "hPa",
        "temperature": "degC"}`` (spec §5).
    """

    pressure: pint.Quantity
    temperature: pint.Quantity
    dewpoint: pint.Quantity | None = None
    wind_speed: pint.Quantity | None = None
    wind_direction: pint.Quantity | None = None
    station: str | None = None
    time: datetime | None = None
    label: str | None = None
    units: dataclasses.InitVar[Mapping[str, str] | None] = None

    def __post_init__(self, units: Mapping[str, str] | None) -> None:
        """Coerce, validate, and normalize the constructed sounding.

        Parameters
        ----------
        units : mapping of str to str or None
            The ``units=`` mapping for bare-array fields.
        """
        mapping = check_units_mapping(units, allowed=_FIELD_DIMENSIONS)
        for name, dimension in _FIELD_DIMENSIONS.items():
            value = getattr(self, name)
            if value is None:
                continue
            quantity = as_quantity(
                value, name=name, units=mapping.get(name), dimension=dimension
            )
            object.__setattr__(self, name, quantity)
        self._validate_shapes()
        self._validate_wind_pairing()
        self._validate_dewpoint()
        self._normalize_pressure()
        self._normalize_time()
        self._derive_label()

    def _fields_present(self) -> dict[str, pint.Quantity]:
        """Collect the data fields provided to this sounding.

        Returns
        -------
        dict of str to pint.Quantity
            Field name to coerced quantity, in field order.
        """
        present = {}
        for name in _FIELD_DIMENSIONS:
            value = getattr(self, name)
            if value is not None:
                present[name] = value
        return present

    def _validate_shapes(self) -> None:
        """Require 1-D equal-length arrays of at least two levels."""
        lengths = {}
        for name, quantity in self._fields_present().items():
            if quantity.magnitude.ndim != 1:
                msg = f"{name!r} must be 1-D, got {quantity.magnitude.ndim}-D"
                raise TephpyValidationError(msg)
            lengths[name] = quantity.magnitude.size
        if len(set(lengths.values())) > 1:
            msg = f"fields must be equal length, got {lengths!r}"
            raise TephpyValidationError(msg)
        if min(lengths.values()) < _MIN_LEVELS:
            msg = f"a sounding needs at least {_MIN_LEVELS} levels, got {lengths!r}"
            raise TephpyValidationError(msg)

    def _validate_wind_pairing(self) -> None:
        """Require wind speed and direction to arrive together."""
        if (self.wind_speed is None) != (self.wind_direction is None):
            missing = "wind_direction" if self.wind_direction is None else "wind_speed"
            msg = (
                "wind_speed and wind_direction must arrive together: "
                f"{missing!r} is missing"
            )
            raise TephpyValidationError(msg)

    def _normalize_pressure(self) -> None:
        """Require finite, strictly monotonic pressure; store it decreasing.

        Increasing input is accepted and reversed — with every data array
        reversed together — so storage is always surface-first.
        """
        pressure = self.pressure.magnitude
        bad = np.flatnonzero(~np.isfinite(pressure))
        if bad.size:
            levels = tuple(int(index) for index in bad)
            msg = f"pressure must be finite at every level; offending levels {levels}"
            raise TephpyValidationError(msg, levels=levels)
        diffs = np.diff(pressure)
        if np.all(diffs < 0.0):
            return
        if np.all(diffs > 0.0):
            for name, quantity in self._fields_present().items():
                object.__setattr__(self, name, quantity[::-1])
            return
        direction = 1.0 if pressure[-1] > pressure[0] else -1.0
        offending = np.flatnonzero(diffs * direction <= 0.0) + 1
        levels = tuple(int(index) for index in offending)
        msg = (
            "pressure must be strictly monotonic; "
            f"offending levels {levels} of the {pressure.size}-level profile"
        )
        raise NonMonotonicPressureError(msg, levels=levels)

    def _validate_dewpoint(self) -> None:
        """Reject dewpoint above temperature where both are non-NaN.

        Runs before pressure normalization, so ``levels`` index the
        caller's input arrays — the same frame as the pressure errors.
        """
        if self.dewpoint is None:
            return
        temperature = self.temperature.m_as("degC")
        dewpoint = self.dewpoint.m_as("degC")
        both = np.isfinite(temperature) & np.isfinite(dewpoint)
        bad = np.flatnonzero(both & (dewpoint > temperature))
        if bad.size:
            levels = tuple(int(index) for index in bad)
            msg = (
                "dewpoint exceeds temperature (equality is saturation and "
                f"accepted); offending levels {levels}"
            )
            raise DewpointExceedsTemperatureError(msg, levels=levels)

    def _normalize_time(self) -> None:
        """Read naive times as UTC and convert aware ones to UTC."""
        # Typed `object`: the field annotation says datetime, but the
        # boundary also accepts numpy.datetime64 and rejects the rest.
        time: object = self.time
        if time is None:
            return
        if isinstance(time, np.datetime64):
            time = time.astype("datetime64[us]").item()
        if not isinstance(time, datetime):
            msg = f"time must be a datetime or numpy.datetime64, got {type(time)!r}"
            raise TypeError(msg)
        time = time.replace(tzinfo=UTC) if time.tzinfo is None else time.astimezone(UTC)
        object.__setattr__(self, "time", time)

    def _derive_label(self) -> None:
        """Derive the legend label when not explicitly given (spec §3.4)."""
        if self.label is None and self.station is not None and self.time is not None:
            label = SOUNDING_LABEL_FORMAT.format(station=self.station, time=self.time)
            object.__setattr__(self, "label", label)
```

**(b)** Update `src/tephpy/__init__.py` — the imports and `__all__` become:

```python
from tephpy import exceptions, plotting, transforms
from tephpy._config import config
from tephpy.sounding import Sounding

__all__ = [
    "Sounding",
    "__version__",
    "config",
    "exceptions",
    "plotting",
    "transforms",
]
```

(Both new imports are cheap: `exceptions` has no dependencies, and
`sounding` keeps MetPy behind `_units`'s function-local imports — the
Task 2 subprocess test enforces this.)

**(c)** In `pyproject.toml`, extend the tests entry of
`[tool.ruff.lint.per-file-ignores]` to (with its new comment):

```toml
# DTZ001: naive datetimes are deliberate fixtures — the boundary under
# test reads them as UTC (spec §3.4).
"tests/*" = ["ANN001", "ANN003", "ANN201", "ANN202", "DTZ001", "SLF001", "D103"]
```

(`ANN003` is consumed by Task 7's and Task 8's `**kwargs` test helpers;
adding it together with `DTZ001` here avoids touching this line twice.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_sounding.py tests/test_import.py tests/test_units.py -q --no-cov`
Expected: PASS (hypothesis runs its default 100 examples for the property
test; `test_units.py` re-proves the import-cost guard now that
`tephpy/__init__.py` imports `sounding`).

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/sounding.py src/tephpy/__init__.py pyproject.toml tests/test_sounding.py tests/test_import.py
pixi run lint
git commit -m "feat: add the Sounding data model with ingest-time validation"
```

---

## Task 5: pandas/xarray constructors and the direct dependency declaration

**Files:**
- Modify: `src/tephpy/sounding.py` (append the constructors; extend `TYPE_CHECKING` imports)
- Modify: `pyproject.toml` (pixi dependencies; mypy overrides)
- Modify: `requirements/pypi-core.txt`
- Modify: `tests/test_import.py` (runtime deps list)
- Test: `tests/test_sounding.py` (append)

**Interfaces:**
- Consumes: `_FIELD_DIMENSIONS`, `check_units_mapping`, the `Sounding` core (Task 4).
- Produces: `Sounding.from_dataframe(df, *, units=None, station=None, time=None, label=None, **column_map)` and `Sounding.from_dataset(ds, *, units=None, station=None, time=None, label=None, **var_map)`; pandas/xarray as declared direct runtime dependencies (spec §10 item 9, resolved 2026-07-25).

- [ ] **Step 1: Declare the dependencies**

**(a)** `requirements/pypi-core.txt` becomes (sorted; SPEC 0 floors checked
2026-07-25):

```
matplotlib>=3.9
metpy>=1.6
numpy>=2.0
pandas>=2.3
pint>=0.24
scipy>=1.13
xarray>=2024.10
```

**(b)** In `pyproject.toml`, `[tool.pixi.dependencies]` gains the same two
(taplo keeps the table sorted):

```toml
matplotlib-base = ">=3.9"
metpy = ">=1.6"
numpy = ">=2.0"
pandas = ">=2.3"
pint = ">=0.24"
scipy = ">=1.13"
setuptools = ">=77.0.3"
setuptools-scm = ">=8"
xarray = ">=2024.10"
```

**(c)** In `pyproject.toml`, the mypy override block becomes (pandas 3.0.3
ships no `py.typed`; xarray does and needs no entry):

```toml
[[tool.mypy.overrides]]
# MetPy, pint, and pandas ship partial/absent stubs; do not fail on their
# imports.
ignore_missing_imports = true
module = ["metpy.*", "pandas.*", "pint.*"]
```

**(d)** In `tests/test_import.py`, the runtime-deps loop becomes:

```python
def test_runtime_dependencies_importable() -> None:
    """The declared runtime dependencies import."""
    for package in (
        "matplotlib",
        "metpy",
        "numpy",
        "pandas",
        "pint",
        "scipy",
        "xarray",
    ):
        importlib.import_module(package)
```

**(e)** Refresh the lockfile:

```bash
pixi lock
git diff --stat pixi.lock
```

Expected: `✔ Lock-file was already up-to-date` and an **empty diff** —
pandas 3.0.3 and xarray 2026.7.0 are already in every locked environment
via MetPy (verified 2026-07-25). If the diff is *not* empty, stop and
inspect: a matplotlib or freetype bump would invalidate the pytest-mpl
baselines (see `tests/AGENTS.md`).

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_sounding.py`, and add the two imports to the top of
the file (keeping the block sorted: `pandas` after `numpy`, `xarray` after
`pytest`):

```python
import pandas as pd
import xarray as xr
```

then append the tests:

```python
def test_from_dataframe():
    df = pd.DataFrame(
        {
            "pressure": [1000.0, 850.0],
            "temperature": [20.0, 12.0],
            "dwpt": [15.0, 8.0],
        }
    )
    snd = Sounding.from_dataframe(
        df,
        units={"pressure": "hPa", "temperature": "degC", "dewpoint": "degC"},
        dewpoint="dwpt",
        station="03808",
        time=pd.Timestamp("2026-07-21 12:00"),
    )
    assert snd.label == "03808 2026-07-21 12Z"
    np.testing.assert_array_equal(snd.dewpoint.m_as("degC"), [15.0, 8.0])


def test_from_dataframe_missing_required_column():
    df = pd.DataFrame({"temperature": [20.0, 12.0]})
    with pytest.raises(KeyError, match="pressure"):
        Sounding.from_dataframe(df, units={"temperature": "degC"})


def test_from_dataframe_missing_mapped_column():
    df = pd.DataFrame({"pressure": [1000.0, 850.0], "temperature": [20.0, 12.0]})
    with pytest.raises(KeyError, match="dwpt"):
        Sounding.from_dataframe(
            df,
            units={"pressure": "hPa", "temperature": "degC"},
            dewpoint="dwpt",
        )


def test_from_dataframe_unknown_field():
    df = pd.DataFrame({"pressure": [1000.0, 850.0], "temperature": [20.0, 12.0]})
    with pytest.raises(TypeError, match="unknown field"):
        Sounding.from_dataframe(df, bogus="x")


def test_from_dataset_reads_attrs_units():
    ds = xr.Dataset(
        {
            "pressure": ("level", np.array([1000.0, 850.0]), {"units": "hPa"}),
            "temperature": ("level", np.array([293.15, 285.15]), {"units": "K"}),
        }
    )
    snd = Sounding.from_dataset(ds)
    np.testing.assert_allclose(snd.temperature.m_as("degC"), [20.0, 12.0])


def test_from_dataset_units_override_and_var_map():
    ds = xr.Dataset(
        {
            "p": ("level", np.array([1000.0, 850.0]), {"units": "hPa"}),
            "t": ("level", np.array([20.0, 12.0]), {"units": "K"}),
        }
    )
    snd = Sounding.from_dataset(
        ds, units={"temperature": "degC"}, pressure="p", temperature="t"
    )
    np.testing.assert_allclose(snd.temperature.m_as("degC"), [20.0, 12.0])


def test_from_dataset_missing_units_raises():
    ds = xr.Dataset(
        {
            "pressure": ("level", np.array([1000.0, 850.0]), {"units": "hPa"}),
            "temperature": ("level", np.array([20.0, 12.0])),
        }
    )
    with pytest.raises(TephpyUnitsError, match="attrs"):
        Sounding.from_dataset(ds)


def test_from_dataset_missing_required_variable():
    ds = xr.Dataset(
        {"temperature": ("level", np.array([20.0, 12.0]), {"units": "degC"})}
    )
    with pytest.raises(KeyError, match="pressure"):
        Sounding.from_dataset(ds)
```

(`test_from_dataset_units_override_and_var_map` pins the override
semantics: the ``units=`` entry replaces the variable's ``attrs["units"]``
when *wrapping the bare values* — the user is asserting the attrs are
wrong, so 20.0-with-attrs-K + override-degC reads as 20 °C.)

- [ ] **Step 3: Run the new tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_sounding.py -q --no-cov`
Expected: FAIL — `AttributeError: ... has no attribute 'from_dataframe'` on the new tests; Task 4 tests still pass.

- [ ] **Step 4: Append the constructors**

In `src/tephpy/sounding.py`:

**(a)** Extend the module-level imports: `TephpyUnitsError` joins the
`tephpy.exceptions` import (sorted):

```python
from tephpy.exceptions import (
    DewpointExceedsTemperatureError,
    NonMonotonicPressureError,
    TephpyUnitsError,
    TephpyValidationError,
)
```

and the `TYPE_CHECKING` block becomes:

```python
if TYPE_CHECKING:
    from collections.abc import Mapping

    import pandas as pd
    import pint
    import xarray as xr
```

**(b)** Append inside the `Sounding` class (after `_derive_label`; dedented
listing — indent one level, see Global Constraints):

```python
@classmethod
def from_dataframe(
    cls,
    df: pd.DataFrame,
    *,
    units: Mapping[str, str] | None = None,
    station: str | None = None,
    time: datetime | None = None,
    label: str | None = None,
    **column_map: str,
) -> Sounding:
    """Build a sounding from a pandas DataFrame (spec §3.4).

    Column names default to the field names; `column_map` overrides
    per field (e.g. ``dewpoint="dwpt"``). Columns are bare arrays, so
    the present fields need the ``units=`` mapping.

    Parameters
    ----------
    df : pandas.DataFrame
        The profile table; must contain pressure and temperature
        columns.
    units : mapping of str to str, optional
        Unit strings keyed by field name (spec §5).
    station : str, optional
        Station identifier.
    time : datetime.datetime, optional
        Launch time; ``pandas.Timestamp`` and ``numpy.datetime64``
        are accepted.
    label : str, optional
        Legend text override.
    **column_map : str
        Field names mapped to their column names in `df`.

    Returns
    -------
    Sounding
        The validated sounding.

    Raises
    ------
    KeyError
        If a required or explicitly mapped column is missing.
    TypeError
        If `column_map` names an unknown field.
    """
    cls._check_field_map(column_map)
    data: dict[str, np.ndarray] = {}
    for name in _FIELD_DIMENSIONS:
        column = column_map.get(name, name)
        if column in df.columns:
            data[name] = df[column].to_numpy()
        elif name in column_map or name in ("pressure", "temperature"):
            msg = f"column {column!r} (field {name!r}) is not in the DataFrame"
            raise KeyError(msg)
    return cls(units=units, station=station, time=time, label=label, **data)


@classmethod
def from_dataset(
    cls,
    ds: xr.Dataset,
    *,
    units: Mapping[str, str] | None = None,
    station: str | None = None,
    time: datetime | None = None,
    label: str | None = None,
    **var_map: str,
) -> Sounding:
    """Build a sounding from an xarray Dataset (spec §3.4).

    Variable names default to the field names; `var_map` overrides per
    field. Units are read from each variable's ``attrs["units"]`` (the
    xarray/CF convention); the ``units=`` mapping is the explicit
    override.

    Parameters
    ----------
    ds : xarray.Dataset
        The profile dataset; must contain pressure and temperature
        variables.
    units : mapping of str to str, optional
        Unit strings keyed by field name, overriding
        ``attrs["units"]``.
    station : str, optional
        Station identifier.
    time : datetime.datetime, optional
        Launch time; ``pandas.Timestamp`` and ``numpy.datetime64``
        are accepted.
    label : str, optional
        Legend text override.
    **var_map : str
        Field names mapped to their variable names in `ds`.

    Returns
    -------
    Sounding
        The validated sounding.

    Raises
    ------
    KeyError
        If a required or explicitly mapped variable is missing.
    TephpyUnitsError
        If a field has neither ``attrs["units"]`` nor a ``units=``
        entry.
    TypeError
        If `var_map` names an unknown field.
    """
    cls._check_field_map(var_map)
    mapping = check_units_mapping(units, allowed=_FIELD_DIMENSIONS)
    data: dict[str, np.ndarray] = {}
    resolved: dict[str, str] = {}
    for name in _FIELD_DIMENSIONS:
        variable = var_map.get(name, name)
        if variable not in ds.variables:
            if name in var_map or name in ("pressure", "temperature"):
                msg = f"variable {variable!r} (field {name!r}) not in the Dataset"
                raise KeyError(msg)
            continue
        unit = mapping.get(name) or ds[variable].attrs.get("units")
        if not unit:
            msg = (
                f"{name!r} (variable {variable!r}) has no attrs['units'] "
                f'and no override: add units={{"{name}": "<unit>"}}'
            )
            raise TephpyUnitsError(msg)
        data[name] = ds[variable].to_numpy()
        resolved[name] = unit
    return cls(units=resolved, station=station, time=time, label=label, **data)


@staticmethod
def _check_field_map(field_map: Mapping[str, str]) -> None:
    """Reject unknown field names in a constructor's field mapping.

    Parameters
    ----------
    field_map : mapping of str to str
        Field names mapped to column or variable names.

    Raises
    ------
    TypeError
        If the mapping names an unknown field.
    """
    unknown = set(field_map) - set(_FIELD_DIMENSIONS)
    if unknown:
        msg = (
            f"unknown field(s) {sorted(unknown)!r}; "
            f"expected {sorted(_FIELD_DIMENSIONS)!r}"
        )
        raise TypeError(msg)
```

Implementation notes:
- pandas and xarray are *not* imported at module level, nor inside these
  methods — the constructors only consume the objects handed to them
  (`df.columns`/`.to_numpy()`, `ds.variables`/`.attrs`), so no import is
  needed at all; the `TYPE_CHECKING` imports carry the annotations.
  `pandas.Timestamp` needs no special handling because it *is* a
  `datetime` subclass (Task 4's normalizer accepts it as-is).
- Membership is tested against `ds.variables` (data variables *and*
  coordinates), so a pressure *coordinate* works as a field source.
- `mapping.get(name) or ds[variable].attrs.get("units")` deliberately
  treats an empty-string `attrs["units"]` as missing.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_sounding.py tests/test_import.py tests/test_units.py -q --no-cov`
Expected: PASS (including the import-cost guard: the constructors add no
module-level pandas/xarray imports).

- [ ] **Step 6: Lint and commit**

```bash
git add src/tephpy/sounding.py pyproject.toml requirements/pypi-core.txt pixi.lock tests/test_sounding.py tests/test_import.py
pixi run lint
git commit -m "feat: add the DataFrame/Dataset Sounding constructors and declare pandas/xarray"
```

---

## Task 6: `TephigramAxes.plot_profile`

**Files:**
- Modify: `src/tephpy/plotting/axes.py`
- Test: `tests/plotting/test_axes.py` (append)

**Interfaces:**
- Consumes: `as_quantity`/`check_units_mapping` (Task 2); the existing `tephigram_transform + transData` plumbing and `transforms.theta_from_pressure_temperature`.
- Produces: `plot_profile(pressure, temperature, *, units=None, label=None, **kwargs) -> Line2D`. Task 7's `plot_sounding` calls it twice; Plan 5 adds a `Profile` overload to the same signature (spec §10 item 2 — **do not** design for it now).

- [ ] **Step 1: Write the failing tests**

In `tests/plotting/test_axes.py`, extend the import block at the top to
(sorted; `units` and the new tephpy names):

```python
import matplotlib.pyplot as plt
from metpy.units import units
import numpy as np
import pytest

from tephpy import transforms
from tephpy._config import config
from tephpy._constants import DEFAULT_EXTENT
from tephpy.exceptions import TephpyUnitsError
from tephpy.plotting.axes import TephigramAxes, TephigramTransform
from tephpy.plotting.isopleths import IsoplethFamily
```

(Only what Task 6's tests use is added — eagerly importing Task 7's names
here would fail this task's lint gate as F401 unused imports, which ruff
`--fix` strips. Task 7 Step 1 extends the block again.)

Then append to the end of the file:

```python
PROFILE_PRESSURE = units.Quantity(np.array([1000.0, 850.0, 700.0, 500.0]), "hPa")
PROFILE_TEMPERATURE = units.Quantity(np.array([20.0, 12.0, 4.0, -12.0]), "degC")


def test_plot_profile_maps_through_the_transforms(tephigram_axes):
    line = tephigram_axes.plot_profile(PROFILE_PRESSURE, PROFILE_TEMPERATURE)
    expected_theta = transforms.theta_from_pressure_temperature(
        PROFILE_PRESSURE.m_as("hPa"), PROFILE_TEMPERATURE.m_as("degC")
    )
    np.testing.assert_allclose(line.get_xdata(), PROFILE_TEMPERATURE.m_as("degC"))
    np.testing.assert_allclose(line.get_ydata(), expected_theta)
    expected_transform = tephigram_axes.tephigram_transform + tephigram_axes.transData
    assert line.get_transform() == expected_transform


def test_plot_profile_any_units_just_work(tephigram_axes):
    """K/Pa quantities plot identically to their hPa/degC equivalents."""
    native = tephigram_axes.plot_profile(PROFILE_PRESSURE, PROFILE_TEMPERATURE)
    converted = tephigram_axes.plot_profile(
        PROFILE_PRESSURE.to("Pa"), PROFILE_TEMPERATURE.to("K")
    )
    np.testing.assert_allclose(converted.get_xdata(), native.get_xdata())
    np.testing.assert_allclose(converted.get_ydata(), native.get_ydata())


def test_plot_profile_bare_arrays_with_units(tephigram_axes):
    line = tephigram_axes.plot_profile(
        [1000.0, 850.0],
        [20.0, 12.0],
        units={"pressure": "hPa", "temperature": "degC"},
    )
    np.testing.assert_allclose(line.get_xdata(), [20.0, 12.0])


def test_plot_profile_bare_arrays_without_units_raise(tephigram_axes):
    with pytest.raises(TephpyUnitsError, match="'pressure' has no units"):
        tephigram_axes.plot_profile([1000.0, 850.0], [20.0, 12.0])


def test_plot_profile_kwargs_and_label_pass_through(tephigram_axes):
    line = tephigram_axes.plot_profile(
        PROFILE_PRESSURE,
        PROFILE_TEMPERATURE,
        label="parcel",
        color="black",
        linestyle="--",
    )
    assert line.get_label() == "parcel"
    assert line.get_color() == "black"
    assert line.get_linestyle() == "--"


def test_plot_profile_does_not_drift_the_view(tephigram_axes):
    """Profiles never autoscale the fixed extent (spec §3.2)."""
    before = (tephigram_axes.get_xlim(), tephigram_axes.get_ylim())
    tephigram_axes.plot_profile(PROFILE_PRESSURE, PROFILE_TEMPERATURE)
    tephigram_axes.figure.canvas.draw()
    assert (tephigram_axes.get_xlim(), tephigram_axes.get_ylim()) == before
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -q --no-cov`
Expected: FAIL — `AttributeError: 'TephigramAxes' object has no attribute 'plot_profile'`; the existing tests still pass.

- [ ] **Step 3: Implement `plot_profile`**

In `src/tephpy/plotting/axes.py`:

**(a)** Replace the import section (below the module docstring) with:

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from matplotlib.axes import Axes
from matplotlib.projections import register_projection
import matplotlib.transforms as mtransforms
import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._config import config
from tephpy._constants import DEFAULT_EXTENT
from tephpy._units import as_quantity, check_units_mapping
from tephpy.plotting.isopleths import _FAMILY_SPECS, IsoplethFamily

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from matplotlib.lines import Line2D
```

(Task 7 extends the `_constants` import and the `TYPE_CHECKING` block; the
layering holds — `plotting` imports `_units`, never `sounding`, at
runtime.)

**(b)** Insert the method into `TephigramAxes` after `set_extent` (before
`_configure_family`) — this exact code (a dedented listing: indent one
level, see Global Constraints) passes ruff, mypy strict, and
numpydoc-validation (verified 2026-07-25); `**kwargs: Any` + `noqa: ANN401`
is required (see Global Constraints):

```python
def plot_profile(
    self,
    pressure: object,
    temperature: object,
    *,
    units: Mapping[str, str] | None = None,
    label: str | None = None,
    **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
) -> Line2D:
    """Plot one profile of temperature against pressure (spec §3.2).

    Both arrays are pint quantities — or bare arrays with the
    ``units=`` mapping (spec §5) — converted to diagram-native units
    and plotted through the tephigram transform machinery. Matplotlib
    keywords pass through untouched, and out-of-domain values
    (pressure <= 0 hPa) propagate NaN, breaking the line (spec §3.1).

    Parameters
    ----------
    pressure : pint.Quantity or array_like
        Level pressures.
    temperature : pint.Quantity or array_like
        Level temperatures.
    units : mapping of str to str, optional
        Unit strings for bare arrays, keyed by argument name, e.g.
        ``units={"pressure": "hPa", "temperature": "degC"}``.
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
    """
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
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
pixi run lint
git commit -m "feat: add TephigramAxes.plot_profile through the tephigram transform"
```

---

## Task 7: `TephigramAxes.plot_sounding` — overlays and legends

**Files:**
- Modify: `src/tephpy/plotting/axes.py`
- Test: `tests/plotting/test_axes.py` (append)

**Interfaces:**
- Consumes: `plot_profile` (Task 6); `PROFILE_*` conventions (Task 3); `Sounding` fields (Task 4).
- Produces: `plot_sounding(snd, *, label=None, **kwargs) -> tuple[Line2D, Line2D | None]` — the §4 canonical-usage surface for this plan. Plans 5/6 plot parcel paths and barbs *alongside* it.

- [ ] **Step 1: Write the failing tests**

In `tests/plotting/test_axes.py`, extend the import block again — the
tephpy import becomes `from tephpy import Sounding, transforms`, and the
`_constants` import gains the profile styles:

```python
from tephpy import Sounding, transforms
from tephpy._config import config
from tephpy._constants import (
    DEFAULT_EXTENT,
    PROFILE_DEWPOINT_COLOR,
    PROFILE_LINEWIDTH,
    PROFILE_TEMPERATURE_COLOR,
    PROFILE_ZORDER,
)
```

then add the dewpoint fixture beside the Task 6 module constants:

```python
PROFILE_DEWPOINT = units.Quantity(np.array([15.0, 8.0, np.nan, -30.0]), "degC")
```

and append the tests to the end of the file:

```python
def _sounding(**kwargs):
    """Build the module's reference sounding with metadata overrides."""
    return Sounding(
        PROFILE_PRESSURE, PROFILE_TEMPERATURE, dewpoint=PROFILE_DEWPOINT, **kwargs
    )


def test_plot_sounding_conventional_colours_and_zorder(tephigram_axes):
    temperature_line, dewpoint_line = tephigram_axes.plot_sounding(_sounding())
    assert temperature_line.get_color() == PROFILE_TEMPERATURE_COLOR
    assert dewpoint_line.get_color() == PROFILE_DEWPOINT_COLOR
    assert temperature_line.get_linewidth() == PROFILE_LINEWIDTH
    for line in (temperature_line, dewpoint_line):
        assert line.get_zorder() == PROFILE_ZORDER
        assert line.get_zorder() > max(
            family.get_zorder() for family in tephigram_axes._families.values()
        )


def test_plot_sounding_without_dewpoint(tephigram_axes):
    snd = Sounding(PROFILE_PRESSURE, PROFILE_TEMPERATURE)
    temperature_line, dewpoint_line = tephigram_axes.plot_sounding(snd)
    assert temperature_line is not None
    assert dewpoint_line is None


def test_plot_sounding_label_precedence(tephigram_axes):
    """label= argument > snd.label > no legend entry (spec §3.2)."""
    labelled = _sounding(label="observed")
    temperature_line, _ = tephigram_axes.plot_sounding(labelled)
    assert temperature_line.get_label() == "observed"
    overridden, _ = tephigram_axes.plot_sounding(labelled, label="forecast")
    assert overridden.get_label() == "forecast"
    anonymous, _ = tephigram_axes.plot_sounding(_sounding())
    assert anonymous.get_label().startswith("_")


def test_plot_sounding_one_legend_entry_per_sounding(tephigram_axes):
    """The dewpoint line is _nolegend_; unlabelled soundings add nothing."""
    _, dewpoint_line = tephigram_axes.plot_sounding(_sounding(label="obs"))
    assert dewpoint_line.get_label() == "_nolegend_"
    tephigram_axes.plot_sounding(_sounding())
    legend = tephigram_axes.legend()
    assert [text.get_text() for text in legend.get_texts()] == ["obs"]


def test_plot_sounding_overlay_with_distinguishable_styles(tephigram_axes):
    """Two soundings overlay with per-call styles and legend entries."""
    first, _ = tephigram_axes.plot_sounding(_sounding(label="00Z"))
    second, _ = tephigram_axes.plot_sounding(
        _sounding(label="12Z"), linestyle="--", alpha=0.6
    )
    assert second.get_linestyle() == "--"
    assert second.get_alpha() == 0.6
    assert first.get_linestyle() == "-"
    legend = tephigram_axes.legend()
    assert [text.get_text() for text in legend.get_texts()] == ["00Z", "12Z"]


def test_plot_sounding_kwargs_override_convention_colours(tephigram_axes):
    temperature_line, dewpoint_line = tephigram_axes.plot_sounding(
        _sounding(), color="purple"
    )
    assert temperature_line.get_color() == "purple"
    assert dewpoint_line.get_color() == "purple"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -q --no-cov`
Expected: FAIL — `AttributeError: 'TephigramAxes' object has no attribute 'plot_sounding'`; Task 6 tests still pass.

- [ ] **Step 3: Implement `plot_sounding`**

In `src/tephpy/plotting/axes.py`:

**(a)** Extend the `_constants` import to:

```python
from tephpy._constants import (
    DEFAULT_EXTENT,
    PROFILE_DEWPOINT_COLOR,
    PROFILE_LINEWIDTH,
    PROFILE_TEMPERATURE_COLOR,
    PROFILE_ZORDER,
)
```

and the `TYPE_CHECKING` block to:

```python
if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from matplotlib.lines import Line2D

    from tephpy.sounding import Sounding
```

(The `Sounding` import stays inside `TYPE_CHECKING`: at runtime the method
is duck-typed, so `plotting` never imports `sounding` and the §3 layering
`transforms ← plotting ← sounding` is preserved.)

**(b)** Insert the method directly after `plot_profile` (dedented listing —
indent one level, see Global Constraints):

```python
def plot_sounding(
    self,
    snd: Sounding,
    *,
    label: str | None = None,
    **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
) -> tuple[Line2D, Line2D | None]:
    """Plot a sounding's temperature and dewpoint profiles (spec §3.2).

    Temperature and dewpoint-when-present draw as two profile lines in
    the conventional colours (temperature red, dewpoint green), with
    one legend entry per sounding attached to the temperature line.
    Label precedence: `label` argument > ``snd.label`` > no entry.
    Matplotlib keywords pass through to both lines, overriding the
    convention defaults; legends stay stock matplotlib — call
    ``ax.legend()``.

    Parameters
    ----------
    snd : Sounding
        The sounding to plot.
    label : str, optional
        Legend label override.
    **kwargs : Any
        Passed through to :meth:`matplotlib.axes.Axes.plot` for both
        lines.

    Returns
    -------
    tuple of matplotlib.lines.Line2D
        ``(temperature_line, dewpoint_line)``; the dewpoint line is
        ``None`` when the sounding has no dewpoint.
    """
    resolved = label if label is not None else snd.label
    defaults: dict[str, object] = {
        "linewidth": PROFILE_LINEWIDTH,
        "zorder": PROFILE_ZORDER,
    }
    temperature_line = self.plot_profile(
        snd.pressure,
        snd.temperature,
        label=resolved,
        **{"color": PROFILE_TEMPERATURE_COLOR, **defaults, **kwargs},
    )
    dewpoint_line = None
    if snd.dewpoint is not None:
        dewpoint_line = self.plot_profile(
            snd.pressure,
            snd.dewpoint,
            label="_nolegend_",
            **{"color": PROFILE_DEWPOINT_COLOR, **defaults, **kwargs},
        )
    return temperature_line, dewpoint_line
```

Implementation notes:
- A resolved label of `None` reaches `plot_profile(label=None)`, leaving
  matplotlib's auto `"_childN"` label — which `ax.legend()` skips, exactly
  the "no legend entry" semantics of spec §3.4 (verified: two unlabelled
  soundings add zero legend entries).
- The dict merges put user `kwargs` last, so per-call styles override the
  colour/linewidth/zorder conventions on **both** lines — the §1 item 4
  overlay-distinguishability mechanism.

- [ ] **Step 4: Run the full test suite**

Run: `pixi run --frozen pytest -q --no-cov`
Expected: PASS — everything from Tasks 1–7 plus all Plan 1–3 tests.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
pixi run lint
git commit -m "feat: add TephigramAxes.plot_sounding with overlay and legend semantics"
```

---

## Task 8: Profile image baselines

**Files:**
- Modify: `tests/plotting/test_images.py` (append)
- Create: `tests/baseline/test_profile_sounding.png`, `tests/baseline/test_sounding_overlay.png` (generated)

**Interfaces:**
- Consumes: `plot_sounding` (Task 7), the Plan 3 pytest-mpl infrastructure (`pixi run baselines`, `mpl-baseline-path`, `--mpl` already wired into `pixi run tests` and CI).
- Produces: the two §7/§8.5 profile baselines assigned to this plan ("image baselines ship with their feature").

- [ ] **Step 1: Write the image tests**

In `tests/plotting/test_images.py`, replace the import block with (the
`import tephpy` convenience alias is subsumed — importing any tephpy name
registers the projection):

```python
from __future__ import annotations

import matplotlib.pyplot as plt
from metpy.units import units
import numpy as np
import pytest

# Importing tephpy (via any of its names) registers the "tephigram" projection.
from tephpy import Sounding
```

then append to the end of the file:

```python
def _reference_sounding(**kwargs):
    """Build a small, plausible mid-latitude sounding for the baselines."""
    return Sounding(
        units.Quantity(
            np.array([1006.0, 925.0, 850.0, 700.0, 500.0, 400.0, 300.0]), "hPa"
        ),
        units.Quantity(np.array([26.0, 20.0, 15.4, 7.0, -8.5, -18.5, -31.0]), "degC"),
        dewpoint=units.Quantity(
            np.array([22.0, 18.0, 14.0, 2.0, -20.0, -35.0, -50.0]), "degC"
        ),
        **kwargs,
    )


@pytest.mark.mpl_image_compare
def test_profile_sounding():
    """One sounding: red temperature and green dewpoint over the grid."""
    fig, ax = _tephigram_figure()
    ax.plot_sounding(_reference_sounding(label="03808 2026-07-21 12Z"))
    ax.legend(loc="upper right", fontsize=6)
    return fig


@pytest.mark.mpl_image_compare
def test_sounding_overlay():
    """Two soundings overlay with distinguishable styles and a legend."""
    fig, ax = _tephigram_figure()
    ax.plot_sounding(_reference_sounding(label="00Z"))
    cooler = Sounding(
        units.Quantity(np.array([1006.0, 850.0, 700.0, 500.0, 300.0]), "hPa"),
        units.Quantity(np.array([18.0, 9.0, 0.0, -16.0, -40.0]), "degC"),
        dewpoint=units.Quantity(np.array([12.0, 6.0, -8.0, -30.0, -55.0]), "degC"),
        label="12Z",
    )
    ax.plot_sounding(cooler, linestyle="--", alpha=0.7)
    ax.legend(loc="upper right", fontsize=6)
    return fig
```

- [ ] **Step 2: Generate the baselines, then verify them**

```bash
pixi run baselines        # regenerates ALL baselines; marked tests are SKIPPED
git status --porcelain tests/baseline
pixi run tests            # full suite with --mpl comparisons and coverage
```

Expected: `git status` shows exactly two untracked files
(`test_profile_sounding.png`, `test_sounding_overlay.png`, ~64 KB each) and
**zero modified** existing baselines — regeneration is bit-identical on the
committed lockfile (verified 2026-07-25). The full suite passes with all 9
image comparisons. If an existing baseline shows as modified, stop: the
environment does not match the lockfile.

Visually inspect the two new PNGs: red temperature and green dewpoint
profiles rising from bottom-centre over the labelled grid, legend in the
upper right; the overlay adds a dashed second pair with entries "00Z" and
"12Z".

- [ ] **Step 3: Lint and commit**

```bash
git add tests/plotting/test_images.py tests/baseline/test_profile_sounding.png tests/baseline/test_sounding_overlay.png
pixi run lint
git commit -m "test: add the profile and sounding-overlay image baselines"
```

---

## Task 9: Glossary entries and a warning-free docs build

**Files:**
- Modify: `docs/src/reference/glossary.rst`

**Interfaces:**
- Produces: an updated `sounding` entry (its "(added in a later release)" caveat is now false) and new `dewpoint` and `profile` entries — the terms this plan introduces to the API surface (spec §8.6 lists both as entry-worthy; §10 cross-cutting rule). sphinx-autoapi adds `tephpy.sounding` and `tephpy.exceptions` pages automatically; `_units` is private and gets none.

- [ ] **Step 1: Update and append the entries**

In `docs/src/reference/glossary.rst`, replace the existing `sounding` entry
(keeping the established indent inside `.. glossary::`) with the following
three entries:

```rst
    sounding
        A vertical profile of atmospheric measurements (pressure, temperature,
        :term:`dewpoint`, wind) from a single ascent. In ``tephpy`` a sounding
        is carried by the ``Sounding`` dataclass — pressure and temperature
        arrays (plus optional dewpoint and wind) held as pint quantities with
        station/time metadata — and drawn with ``ax.plot_sounding(...)`` as
        red temperature and green dewpoint :term:`profiles <profile>`.

    dewpoint
        The temperature air must cool to, at constant pressure and moisture
        content, to become saturated; it is never above the air temperature
        (equality means saturation). In ``tephpy`` it is the optional
        ``dewpoint`` field of a ``Sounding`` (°C internally, any pint
        temperature unit accepted), plotted green alongside the red
        temperature line.

    profile
        One curve of a temperature-like quantity against pressure — a
        :term:`sounding`'s temperature or dewpoint trace, or a computed
        parcel path (added in a later release). ``ax.plot_profile(pressure,
        temperature)`` draws one through the tephigram transform machinery.
```

- [ ] **Step 2: Build the docs**

Run: `pixi run docs`
Expected: `build succeeded`, **0 warnings** (verified 2026-07-25: the new
`:term:` references resolve and the autoapi pages for `tephpy.sounding` and
`tephpy.exceptions` generate cleanly). If a warning appears, fix it — do
not suppress.

- [ ] **Step 3: Commit**

```bash
git add docs/src/reference/glossary.rst
git commit -m "docs: update the sounding glossary entry and add dewpoint and profile"
```

---

## Task 10: Full verification, pull request, and changelog fragment

**Files:** `changelog/<PR>.feature.rst` (created after the PR number exists)

- [ ] **Step 1: Full local gate**

```bash
pixi run lint
pixi run --frozen --environment test-py312 pytest --cov --cov-report=xml --mpl
pixi run --frozen --environment test-py313 pytest --cov --cov-report=xml --mpl
pixi run --frozen --environment test-py314 pytest --cov --cov-report=xml --mpl
pixi run docs
```

Expected: lint fully green; the suite (277 tests, including all 9 image
comparisons) passes on all three Pythons against the same committed
baselines; docs build with 0 warnings.

- [ ] **Step 2: Open the pull request**

```bash
git push -u origin sounding
gh pr create --base main --title "Sounding data model & profile plotting (Plan 4)" --fill
```

- [ ] **Step 3: Add the changelog fragment named for the PR**

With `<PR>` the number just created:

```bash
cat > changelog/<PR>.feature.rst <<'EOF'
Added the ``Sounding`` data model with ingest-time validation and pandas/xarray constructors, the pint units machinery over MetPy's registry with the public ``tephpy.exceptions`` hierarchy, and ``TephigramAxes.plot_profile``/``plot_sounding`` with multi-sounding overlays, derived legends, and profile image baselines.
(:user:`claude`)
EOF
git add changelog/<PR>.feature.rst
git commit -m "docs: add Plan 4 changelog fragment"
git push
```

Expected: the `ci-changelog` check passes on the PR; all other checks
(tests ×3 with image comparisons, docs, wheels + smoke test, CodeQL,
pre-commit.ci) go green.

---

## Self-review

**Spec coverage (§3.4/§5/§6/§3.2/§1 item 4/§7/§8.5/§10 Plan 4 row):**
frozen `Sounding` dataclass with required pressure/temperature, optional
dewpoint and paired wind, coercion in `__post_init__`, §6 validation at
ingest (1-D/equal-length/≥2 levels; finite strictly-monotonic pressure
normalized to decreasing with all arrays reversed together; Td > T rejected
with equality accepted; NaN-as-data outside pressure), station/time
metadata with the resolved item-8 label semantics → Task 4.
`from_dataframe`/`from_dataset` with column/var maps, `attrs["units"]`
reading, `units=` override, Timestamp/datetime64 acceptance, and the
item-9 direct pandas/xarray declaration (SPEC 0 floors, zero import
weight — the constructors are duck-typed) → Task 5. §5 machinery — MetPy's registry as the one
registry, `as_quantity(value, *, name, units=None, dimension)` with the
exact spec'd failure modes (unit-less, ambiguous quantity-plus-`units=`,
wrong dimensionality), mapping-keyed `units=` at multi-argument boundaries
→ Task 2, exercised at every boundary in Tasks 4 and 6. §6 shared
hierarchy with `TephpyError` root, `TephpyUnitsError`,
`TephpyValidationError.levels`, `NonMonotonicPressureError`,
`DewpointExceedsTemperatureError` → Task 1. `plot_profile` quantities
signature (item 2: the `Profile` overload is deliberately Plan 5's) →
Task 6. `plot_sounding` red/green conventions from `_constants`, one
legend entry per sounding on the temperature line, `_nolegend_` dewpoint,
label precedence, stock-matplotlib legends, kwargs pass-through → Tasks 3
and 7. Multi-sounding overlay with distinguishable styles (§1 item 4) →
Task 7 tests + Task 8 overlay baseline. Item-10 slice — eager top-level
`Sounding` re-export kept cheap, enforced by a subprocess import test →
Tasks 2/4. Profile image baselines (§7/§8.5 cross-cutting rule) → Task 8.
Glossary rule → Task 9. Changelog + full gate → Task 10.

**Placeholder scan:** every code step carries complete, runnable code. All
listings were developed against the live environment first — each passes
ruff (`ALL` + format), mypy strict, numpydoc-validation, and the full
pytest gate (277 tests, 9 image comparisons, `filterwarnings = ["error"]`)
on py314 and py312, with the docs build warning-free — and an adversarial
review pass then executed every task's code and tests against this plan
text (2026-07-25). No TBDs, no "similar to Task N".

**Type/name consistency:** the exception names, `as_quantity`/
`check_units_mapping` signatures, `_FIELD_DIMENSIONS`, the `PROFILE_*`/
`SOUNDING_LABEL_FORMAT` constants, the `Sounding` field set, and the two
axes-method signatures are identical across the Interfaces contract and
Tasks 1–8; Task 7's tests import exactly the Task 3 constants; Task 5's
constructors call exactly the Task 2 helpers.

**Known judgment calls (documented, not hidden):**
- `as_quantity` *always* re-wraps onto MetPy's registry (float64), so
  foreign-registry quantities are normalized once at the boundary instead
  of failing later inside `metpy.calc` (Plan 5's concern, paid for here).
- Programming errors (unknown field names, missing mapped columns, bad
  `time` type) raise `TypeError`/`KeyError`, not the §6 hierarchy — §6 is
  for *data* a user can fix by correcting their measurements or units.
- `eq=False` on the frozen dataclass: the generated `__eq__` would compare
  arrays elementwise and raise; equality of soundings has no obvious
  semantics, so none is offered.
- Field annotations state the post-init guarantee (`pint.Quantity`), not
  the permissive inputs; bare-array + `units=` construction remains fully
  supported and tested.
- `time` is stored timezone-aware in UTC (naive input reinterpreted, aware
  converted); the label format prints hours only (`"12Z"`), per the
  operational convention hinted in spec §4.
- Non-monotonic `levels` are computed against the majority direction
  (`p[-1]` vs `p[0]`), reporting the indices of levels that break it —
  deterministic and correct for the common single-spike case.
- `plot_profile` sets no style defaults (it is the §4 primitive for parcel
  paths); all convention styling lives in `plot_sounding`. User kwargs on
  `plot_sounding` intentionally apply to both lines.
- Wind fields are dimension-checked and stored now but first *consumed* by
  Plan 6's `plot_barbs` (which raises when they are absent, per §3.4).
- The two baselines total ~130 KB, riding into the sdist like the Plan 3
  set; `pixi run baselines` regeneration was verified bit-identical for
  the existing seven.
- Refines resolved item 9's letter: the constructors need **no** runtime
  pandas/xarray import at all (duck-typed, `TYPE_CHECKING`-only
  annotations) — even lighter than the spec's "imported function-locally";
  worth a one-line spec touch-up when this plan's PR merges.
- Lint posture: `ANN401` suppressed per matplotlib pass-through parameter;
  tests add `ANN003`/`DTZ001` to their per-file-ignores; the "unparsable"
  spelling per codespell.

---

## Execution handoff

Plan 4 of 7 (spec §10). On completion, Plans 5 and 6 are both unblocked
and may proceed in parallel: **Plan 5 (thermodynamic analysis)** builds
`calc`, the `Profile` type and its `plot_profile` overload, shading, and
the indices panel on top of this plan's `Sounding`/units machinery;
**Plan 6 (wind barbs & data ingest)** consumes the wind fields validated
here and returns `Sounding` objects from the Wyoming/IGRA readers, adding
`TephpyIOError` to the Task 1 hierarchy.
