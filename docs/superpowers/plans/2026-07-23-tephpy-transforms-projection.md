# tephpy Transforms & Tephigram Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the T–ln θ coordinate mathematics and a minimal, registered `"tephigram"` matplotlib projection, verified per case against first principles with tephi as a recorded oracle.

**Architecture:** `transforms.py` holds pure numpy functions for (p, T) ↔ (T, θ) ↔ (x, y) in diagram-native units (hPa, °C); `plotting/axes.py` wraps them in an invertible matplotlib `Transform` inside a minimal `TephigramAxes` registered as `"tephigram"` (native x–y data space, equal aspect, hidden ticks); `_constants.py` is seeded with the conventions both need. Correctness rests on the §7 four-layer battery: hypothesis round-trips, independently recomputed fixed points, the isotherm ⊥ dry-adiabat invariant, and cross-checks against recorded tephi outputs.

**Tech Stack:** Python 3.12/3.13/3.14, numpy, matplotlib (Agg in tests), hypothesis, pytest, pixi tasks, tephi 0.4.0.post0 (oracle only — a throwaway venv, never a runtime dependency).

**Spec:** `docs/superpowers/specs/2026-07-22-tephpy-design.md` — §3.1 (authority for this plan), §5 (units exemption), §7 (transforms test battery), §10 (Plan 2 row; resolved items 3–5).

This is **Plan 2 of 7** (spec §10). It produces working software: after `import tephpy`, `plt.subplots(subplot_kw={"projection": "tephigram"})` yields working rotated axes, and the full test battery passes on all three Pythons.

## Global Constraints

Copied from the spec / Plan 1; every task's requirements implicitly include these.

- **Python support (SPEC 0):** 3.12, 3.13, and 3.14. `requires-python = ">=3.12"`.
- **Platforms (pixi):** `linux-64` only — the initial platform support.
- **Copyright header (every `.py` file, verbatim — ruff `CPY001` enforces it):**
  ```
  # Copyright (c) 2026, tephpy Contributors.
  #
  # This file is part of tephpy and is distributed under the 3-Clause BSD license.
  # See the LICENSE file in the package root directory for licensing details.
  ```
- **Imports:** every `.py` file needs `from __future__ import annotations` (ruff isort `required-imports`).
- **Lint/type:** ruff `ALL` (repo config); **mypy `strict` must be clean over `src/tephpy` with no per-module relaxations for the numeric core** (spec §8.4). numpydoc-validation runs on `src/` — every public object needs a numpy-style docstring with `Parameters`/`Returns`.
- **Units:** `transforms` is the documented §5 exemption — bare numpy `float64` arrays, hPa/°C native units, NaN for out-of-domain input, never exceptions (spec §3.1).
- **Verify-first (spec §3.1/§7):** derive from published sources (Met Office Factsheet 13; Stull ch. 5); tephi is a corroborating oracle. Divergence from the oracle triggers investigation; first principles win; divergences are documented in the fixture/test. Attribution attaches only to artifacts actually copied — this plan copies none (oracle values are *generated* by running tephi).
- **Tests:** pytest strict config with `filterwarnings = ["error"]` — silence expected numpy warnings *inside* the library with `np.errstate`, and close every matplotlib figure you open.
- **Docs:** build must stay warning-free (`pixi run docs` uses `--fail-on-warning`). Titles use CMOS headline style. Glossary entries ship with the terms this plan introduces (spec §10 cross-cutting rule).
- **Changelog:** one `changelog/<PR>.<type>.rst` fragment per PR.
- **Workflow edits:** SHA-pinned actions, `permissions: {}`, zizmor must stay clean.
- **Branch:** work on a feature branch (`no-commit-to-branch` blocks `main`), e.g. `git switch -c transforms`.

---

## File structure created or modified by this plan

```
src/tephpy/
  _constants.py                 # NEW: KELVIN_ZERO, RD, CPD, KAPPA, P_REF, MA, DEFAULT_ANCHOR
  transforms.py                 # NEW: 4 pure conversion functions (numpy only)
  plotting/
    __init__.py                 # NEW: re-exports TephigramAxes
    axes.py                     # NEW: TephigramTransform(s), TephigramAxes, registration
  __init__.py                   # MODIFIED: import submodules (registers the projection)
tests/
  conftest.py                   # NEW: force the Agg backend
  test_transforms.py            # NEW: fixed points, hypothesis round-trips, ⊥ invariant, NaN domain
  test_axes.py                  # NEW: registration, transform round-trip, axes defaults
  test_oracle.py                # NEW: comparisons against the recorded tephi fixture
  fixtures/
    generate_tephi_oracle.py    # NEW: one-shot generator (run in a throwaway venv, not in CI)
    tephi_oracle.json           # NEW: committed oracle values + provenance
docs/src/reference/glossary.rst # MODIFIED: + potential temperature, dry adiabat, isotherm
.github/workflows/ci-wheels.yml # MODIFIED: wheel-install smoke test step
changelog/<PR>.feature.rst      # NEW: news fragment (named after the PR, Task 7)
```

Naming used throughout (Interfaces contract):

```
tephpy._constants:  KELVIN_ZERO, RD, CPD, KAPPA, P_REF, MA, DEFAULT_ANCHOR
tephpy.transforms:
    theta_from_pressure_temperature(pressure, temperature) -> NDArray[float64]
    pressure_from_temperature_theta(temperature, theta)    -> NDArray[float64]
    xy_from_temperature_theta(temperature, theta) -> tuple[NDArray, NDArray]
    temperature_theta_from_xy(x, y)               -> tuple[NDArray, NDArray]
tephpy.plotting.axes: TephigramTransform, TephigramInvertedTransform, TephigramAxes
```

All transform arguments accept anything `np.asarray` handles (scalars, lists, arrays); all returns are `float64` numpy arrays (0-d for scalar input). Temperatures and θ in °C, pressure in hPa, x/y dimensionless.

---

## Task 1: Constants seed and the pressure ↔ potential-temperature pair

**Files:**
- Create: `src/tephpy/_constants.py`
- Create: `src/tephpy/transforms.py`
- Test: `tests/test_transforms.py`

**Interfaces:**
- Produces: `_constants` names above; `theta_from_pressure_temperature`, `pressure_from_temperature_theta` (signatures above). Task 2 extends `transforms.py`; Tasks 4–5 import `_constants`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_transforms.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the tephigram coordinate transforms (spec §3.1/§7)."""

from __future__ import annotations

import math

from hypothesis import given
from hypothesis import strategies as st
import numpy as np
import pytest

from tephpy import transforms
from tephpy._constants import CPD, KAPPA, KELVIN_ZERO, MA, P_REF, RD

# Physical domains for property tests: pressures from the stratosphere to
# below sea level, temperatures well past any atmospheric extreme.
PRESSURES = st.floats(min_value=1.0, max_value=1100.0, allow_nan=False)
TEMPERATURES = st.floats(min_value=-150.0, max_value=100.0, allow_nan=False)


def test_kappa_is_dry_air_ratio():
    """kappa is R_d / c_pd, approximately the 2/7 of Poisson's equation."""
    assert KAPPA == RD / CPD
    assert KAPPA == pytest.approx(2.0 / 7.0, rel=2e-3)


def test_theta_identity_at_reference_pressure():
    """At p = P_REF exactly, theta equals temperature — no arithmetic at all.

    Derivation: theta_K = T_K * (P_REF / P_REF)**kappa = T_K.
    """
    temperatures = np.array([-80.0, -40.0, 0.0, 15.0, 40.0])
    result = transforms.theta_from_pressure_temperature(P_REF, temperatures)
    np.testing.assert_allclose(result, temperatures, rtol=0, atol=1e-12)


def test_theta_known_value_recomputed_independently():
    """Spot value recomputed with the math module, not the numpy code path.

    Derivation (Poisson's equation, Stull ch. 5): for p = 850 hPa, T = 20 °C,
    theta_K = (20 + 273.15) * (1000 / 850)**kappa.
    """
    expected = (20.0 + KELVIN_ZERO) * math.pow(P_REF / 850.0, KAPPA) - KELVIN_ZERO
    result = transforms.theta_from_pressure_temperature(850.0, 20.0)
    assert float(result) == pytest.approx(expected, rel=1e-12)
    # And the independently known ballpark: lifting 850->1000 hPa warms the
    # potential temperature by roughly 13-14 K for this profile.
    assert 33.0 < expected < 35.0


def test_theta_monotonic_decreasing_in_pressure():
    """At fixed T, theta decreases as pressure increases (less lift needed)."""
    pressures = np.array([300.0, 500.0, 700.0, 850.0, 1000.0])
    thetas = transforms.theta_from_pressure_temperature(pressures, 0.0)
    assert np.all(np.diff(thetas) < 0)


@given(pressure=PRESSURES, temperature=TEMPERATURES)
def test_pressure_theta_round_trip(pressure, temperature):
    """(p, T) -> theta -> p is the identity across the physical domain."""
    theta = transforms.theta_from_pressure_temperature(pressure, temperature)
    back = transforms.pressure_from_temperature_theta(temperature, theta)
    assert float(back) == pytest.approx(pressure, rel=1e-9)


def test_theta_out_of_domain_is_nan():
    """Non-positive pressure or sub-absolute-zero theta yields NaN, silently."""
    assert np.isnan(transforms.theta_from_pressure_temperature(0.0, 15.0))
    assert np.isnan(transforms.theta_from_pressure_temperature(-10.0, 15.0))
    assert np.isnan(
        transforms.pressure_from_temperature_theta(15.0, -KELVIN_ZERO - 1.0)
    )


def test_theta_vectorized_shapes():
    """Array inputs broadcast; scalar inputs give 0-d float64 arrays."""
    result = transforms.theta_from_pressure_temperature(
        np.array([1000.0, 850.0]), np.array([15.0, 20.0])
    )
    assert result.shape == (2,)
    assert result.dtype == np.float64
    scalar = transforms.theta_from_pressure_temperature(850.0, 20.0)
    assert scalar.shape == ()
```

(`MA` is imported now and used from Task 2 onward; ruff will not flag it because Task 2's tests land in this same file. If you run ruff between tasks, ignore the transient F401 or add Task 2 first.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run pytest tests/test_transforms.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tephpy.transforms'` (collection error is fine).

- [ ] **Step 3: Create `_constants.py` and the first transform pair**

Create `src/tephpy/_constants.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Convention defaults for the tephigram diagram.

Values follow the UK tephigram convention (Met Office Factsheet 13) and
standard dry-air thermodynamic constants (Stull, *Practical Meteorology*).
Nothing numeric is hard-coded at point of use elsewhere in tephpy — import
it from here (spec §3.5).
"""

from __future__ import annotations

from typing import Final

#: Offset between degrees Celsius and Kelvin.
KELVIN_ZERO: Final[float] = 273.15

#: Specific gas constant for dry air (J kg^-1 K^-1).
RD: Final[float] = 287.05

#: Specific heat capacity of dry air at constant pressure (J kg^-1 K^-1).
CPD: Final[float] = 1004.68

#: Poisson exponent for dry air, R_d / c_pd (approximately 2/7).
KAPPA: Final[float] = RD / CPD

#: Reference pressure for potential temperature (hPa).
P_REF: Final[float] = 1000.0

#: Rotation scale of the tephigram mapping: x = MA ln(theta_K) + T.
MA: Final[float] = 300.0

#: Default diagram extent as ((pressure, temperature), (pressure, temperature))
#: anchor corners in hPa / degrees Celsius: bottom-left and top-right of the
#: default view. Refined into the full anchoring API by Plan 3.
DEFAULT_ANCHOR: Final[tuple[tuple[float, float], tuple[float, float]]] = (
    (1050.0, -40.0),
    (200.0, 40.0),
)
```

Create `src/tephpy/transforms.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Coordinate transforms for the tephigram projection.

Pure numpy functions between the three coordinate frames of the tephigram
(spec §3.1): pressure/temperature (p, T), temperature/potential-temperature
(T, theta), and the rotated display plane (x, y), where

    x = MA * ln(theta_K) + T        y = MA * ln(theta_K) - T

with MA = 300 and theta_K the potential temperature in Kelvin. The
construction is derived from Met Office Factsheet 13 and Stull,
*Practical Meteorology* ch. 5, and cross-validated against tephi as an
oracle (``tests/test_oracle.py``) — not ported from it.

This module is the documented exemption to the pint units policy (spec §5):
bare ``float64`` arrays in diagram-native units — pressure in hPa,
temperatures in degrees Celsius, x/y dimensionless. Out-of-domain input
(non-positive pressure, temperatures at or below absolute zero) propagates
NaN; exception-carrying validation lives at the quantified boundaries
above this module (spec §6).
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from tephpy._constants import KAPPA, KELVIN_ZERO, MA, P_REF

__all__ = [
    "pressure_from_temperature_theta",
    "temperature_theta_from_xy",
    "theta_from_pressure_temperature",
    "xy_from_temperature_theta",
]


def theta_from_pressure_temperature(
    pressure: npt.ArrayLike, temperature: npt.ArrayLike
) -> npt.NDArray[np.float64]:
    """Convert pressure and temperature to potential temperature.

    Poisson's equation: ``theta_K = T_K * (P_REF / p) ** kappa``.

    Parameters
    ----------
    pressure : array_like
        Pressure in hPa. Non-positive values yield NaN.
    temperature : array_like
        Temperature in degrees Celsius.

    Returns
    -------
    numpy.ndarray
        Potential temperature in degrees Celsius, ``float64``, broadcast
        over the inputs.
    """
    p = np.asarray(pressure, dtype=np.float64)
    t = np.asarray(temperature, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        p_valid = np.where(p > 0.0, p, np.nan)
        theta_k = (t + KELVIN_ZERO) * (P_REF / p_valid) ** KAPPA
    return np.asarray(theta_k - KELVIN_ZERO, dtype=np.float64)


def pressure_from_temperature_theta(
    temperature: npt.ArrayLike, theta: npt.ArrayLike
) -> npt.NDArray[np.float64]:
    """Convert temperature and potential temperature to pressure.

    Inverse of :func:`theta_from_pressure_temperature`:
    ``p = P_REF * (T_K / theta_K) ** (1 / kappa)``.

    Parameters
    ----------
    temperature : array_like
        Temperature in degrees Celsius.
    theta : array_like
        Potential temperature in degrees Celsius. Values at or below
        absolute zero yield NaN.

    Returns
    -------
    numpy.ndarray
        Pressure in hPa, ``float64``, broadcast over the inputs.
    """
    t = np.asarray(temperature, dtype=np.float64)
    th = np.asarray(theta, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        theta_k = np.where(th + KELVIN_ZERO > 0.0, th + KELVIN_ZERO, np.nan)
        p = P_REF * ((t + KELVIN_ZERO) / theta_k) ** (1.0 / KAPPA)
    return np.asarray(p, dtype=np.float64)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run pytest tests/test_transforms.py -q`
Expected: PASS — all tests green (hypothesis runs its default 100 examples).

- [ ] **Step 5: Lint, type-check, commit**

Run: `pixi run lint` (fix anything ruff/mypy/numpydoc report), then:

```bash
git add src/tephpy/_constants.py src/tephpy/transforms.py tests/test_transforms.py
git commit -m "feat: seed diagram constants and the pressure/theta transform pair"
```

---

## Task 2: The rotated x–y mapping and the perpendicularity invariant

**Files:**
- Modify: `src/tephpy/transforms.py` (append two functions)
- Test: `tests/test_transforms.py` (append)

**Interfaces:**
- Consumes: `_constants.MA`, `KELVIN_ZERO`.
- Produces: `xy_from_temperature_theta(temperature, theta) -> tuple[NDArray, NDArray]`, `temperature_theta_from_xy(x, y) -> tuple[NDArray, NDArray]`. Task 4's matplotlib `Transform` wraps exactly these two.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_transforms.py`:

```python
THETAS = st.floats(min_value=-100.0, max_value=300.0, allow_nan=False)


def test_xy_known_value_recomputed_independently():
    """Spot value recomputed with the math module, not the numpy code path.

    Derivation: for T = 15 °C, theta = 15 °C (a surface point at P_REF),
    ln(theta_K) = ln(288.15), so x = 300 ln(288.15) + 15, y = 300 ln(288.15) - 15.
    """
    ln_theta = math.log(15.0 + KELVIN_ZERO)
    x, y = transforms.xy_from_temperature_theta(15.0, 15.0)
    assert float(x) == pytest.approx(MA * ln_theta + 15.0, rel=1e-12)
    assert float(y) == pytest.approx(MA * ln_theta - 15.0, rel=1e-12)


@given(temperature=TEMPERATURES, theta=THETAS)
def test_xy_round_trip(temperature, theta):
    """(T, theta) -> (x, y) -> (T, theta) is the identity."""
    x, y = transforms.xy_from_temperature_theta(temperature, theta)
    t_back, theta_back = transforms.temperature_theta_from_xy(x, y)
    assert float(t_back) == pytest.approx(temperature, rel=1e-9, abs=1e-9)
    assert float(theta_back) == pytest.approx(theta, rel=1e-9, abs=1e-9)


@given(pressure=PRESSURES, temperature=TEMPERATURES)
def test_full_round_trip_pressure_temperature(pressure, temperature):
    """(p, T) -> (T, theta) -> (x, y) and back reproduces (p, T) — spec §7."""
    theta = transforms.theta_from_pressure_temperature(pressure, temperature)
    x, y = transforms.xy_from_temperature_theta(temperature, theta)
    t_back, theta_back = transforms.temperature_theta_from_xy(x, y)
    p_back = transforms.pressure_from_temperature_theta(t_back, theta_back)
    assert float(p_back) == pytest.approx(pressure, rel=1e-8)
    assert float(t_back) == pytest.approx(temperature, rel=1e-9, abs=1e-9)


def test_isotherm_perpendicular_to_dry_adiabat():
    """The defining tephigram invariant, asserted in display space (spec §7).

    Along an isotherm (T fixed, theta varies) the direction is
    d(x, y) = (MA dln(theta), MA dln(theta)) ∝ (1, 1); along a dry adiabat
    (theta fixed, T varies) it is (dT, -dT) ∝ (1, -1). Their dot product is
    exactly zero. Verified numerically from function output alone.
    """
    t0, theta0, eps = 10.0, 40.0, 1e-6
    x0, y0 = transforms.xy_from_temperature_theta(t0, theta0)
    # Direction along the isotherm through (t0, theta0).
    x1, y1 = transforms.xy_from_temperature_theta(t0, theta0 + eps)
    isotherm = np.array([float(x1 - x0), float(y1 - y0)])
    # Direction along the dry adiabat through (t0, theta0).
    x2, y2 = transforms.xy_from_temperature_theta(t0 + eps, theta0)
    adiabat = np.array([float(x2 - x0), float(y2 - y0)])
    cosine = np.dot(isotherm, adiabat) / (
        np.linalg.norm(isotherm) * np.linalg.norm(adiabat)
    )
    assert cosine == pytest.approx(0.0, abs=1e-9)


def test_xy_out_of_domain_is_nan():
    """theta at or below absolute zero has no ln(theta_K): NaN, silently."""
    x, y = transforms.xy_from_temperature_theta(0.0, -KELVIN_ZERO - 1.0)
    assert np.isnan(x) and np.isnan(y)
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `pixi run pytest tests/test_transforms.py -q`
Expected: FAIL — `AttributeError: ... 'xy_from_temperature_theta'` on the new tests; Task 1 tests still pass.

- [ ] **Step 3: Append the implementations**

Append to `src/tephpy/transforms.py`:

```python
def xy_from_temperature_theta(
    temperature: npt.ArrayLike, theta: npt.ArrayLike
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Convert temperature and potential temperature to display coordinates.

    The rotated tephigram mapping: ``x = MA * ln(theta_K) + T`` and
    ``y = MA * ln(theta_K) - T``, which renders isotherms and dry adiabats
    as exactly perpendicular straight lines.

    Parameters
    ----------
    temperature : array_like
        Temperature in degrees Celsius.
    theta : array_like
        Potential temperature in degrees Celsius. Values at or below
        absolute zero yield NaN.

    Returns
    -------
    tuple of numpy.ndarray
        The ``(x, y)`` display coordinates, ``float64``, broadcast over
        the inputs.
    """
    t = np.asarray(temperature, dtype=np.float64)
    th = np.asarray(theta, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        theta_k = np.where(th + KELVIN_ZERO > 0.0, th + KELVIN_ZERO, np.nan)
        scaled = MA * np.log(theta_k)
    return (
        np.asarray(scaled + t, dtype=np.float64),
        np.asarray(scaled - t, dtype=np.float64),
    )


def temperature_theta_from_xy(
    x: npt.ArrayLike, y: npt.ArrayLike
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Convert display coordinates back to temperature and theta.

    Inverse of :func:`xy_from_temperature_theta`: ``T = (x - y) / 2`` and
    ``theta_K = exp((x + y) / (2 * MA))``.

    Parameters
    ----------
    x : array_like
        Display x coordinate (dimensionless).
    y : array_like
        Display y coordinate (dimensionless).

    Returns
    -------
    tuple of numpy.ndarray
        ``(temperature, theta)`` in degrees Celsius, ``float64``,
        broadcast over the inputs.
    """
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    temperature = (x_arr - y_arr) / 2.0
    theta = np.exp((x_arr + y_arr) / (2.0 * MA)) - KELVIN_ZERO
    return (
        np.asarray(temperature, dtype=np.float64),
        np.asarray(theta, dtype=np.float64),
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run pytest tests/test_transforms.py -q`
Expected: PASS — all tests including the perpendicularity invariant.

- [ ] **Step 5: Lint and commit**

```bash
pixi run lint
git add src/tephpy/transforms.py tests/test_transforms.py
git commit -m "feat: add the rotated x-y tephigram mapping with invariant tests"
```

---

## Task 3: tephi oracle fixture and cross-validation tests

**Files:**
- Create: `tests/fixtures/generate_tephi_oracle.py`
- Create: `tests/fixtures/tephi_oracle.json` (generated, committed)
- Test: `tests/test_oracle.py`

**Interfaces:**
- Consumes: all four `transforms` functions.
- Produces: the committed fixture; nothing downstream imports these tests.

- [ ] **Step 1: Write the generator script**

Create `tests/fixtures/generate_tephi_oracle.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Generate the tephi oracle fixture (one-shot; not run in CI).

Run in a THROWAWAY environment so tephi never touches the project envs:

    python3 -m venv /tmp/tephi-oracle
    /tmp/tephi-oracle/bin/pip install "tephi==0.4.0.post0"
    /tmp/tephi-oracle/bin/python tests/fixtures/generate_tephi_oracle.py

Writes ``tephi_oracle.json`` beside this script: input grids, tephi's
outputs for the equivalent conversions, tephi's constants, and provenance.
The values are OUTPUTS of running tephi (BSD-3-Clause), not copied source;
provenance is recorded in the fixture (spec §3.1/§10 item 5).
"""

from __future__ import annotations

from datetime import datetime, timezone
import itertools
import json
from pathlib import Path

import tephi
import tephi.transforms as ttr

PRESSURES = [1050.0, 1000.0, 850.0, 700.0, 500.0, 300.0, 200.0, 100.0]
TEMPERATURES = [-80.0, -40.0, -20.0, 0.0, 15.0, 30.0, 45.0]
THETAS = [-40.0, 0.0, 20.0, 40.0, 80.0, 150.0, 300.0]


def main() -> None:
    """Evaluate tephi's transforms on the grids and write the fixture."""
    pt_grid = list(itertools.product(PRESSURES, TEMPERATURES))
    tt_grid = list(itertools.product(TEMPERATURES, THETAS))

    # tephi's transform API (verify against the installed version if these
    # names have moved): convert_pT2Tt maps (pressure, temperature) to
    # (temperature, theta); convert_Tt2xy and convert_xy2Tt map between
    # (temperature, theta) and display (x, y).
    theta_out = [float(ttr.convert_pT2Tt([p], [t])[1][0]) for p, t in pt_grid]
    xy_out = [[float(v[0]) for v in ttr.convert_Tt2xy([t], [th])] for t, th in tt_grid]

    fixture = {
        "provenance": {
            "generator": "tests/fixtures/generate_tephi_oracle.py",
            "generated": datetime.now(timezone.utc).isoformat(),
            "tephi_version": tephi.__version__,
            "note": (
                "Values are outputs of executing tephi (BSD-3-Clause), "
                "recorded as a cross-validation oracle; no tephi source "
                "or data files are copied."
            ),
        },
        "pressure_temperature_grid": pt_grid,
        "theta_from_pressure_temperature": theta_out,
        "temperature_theta_grid": tt_grid,
        "xy_from_temperature_theta": xy_out,
    }
    out = Path(__file__).parent / "tephi_oracle.json"
    out.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"wrote {out} ({len(pt_grid)} p/T cases, {len(tt_grid)} T/theta cases)")


if __name__ == "__main__":
    main()
```

Note for the implementer: if the installed tephi exposes different names
(inspect with `python -c "import tephi.transforms as t; print([n for n in dir(t) if 'convert' in n])"`),
adapt the two call sites and record what you used in the commit message —
the fixture format itself must not change.

- [ ] **Step 2: Generate and inspect the fixture**

Run the three commands from the script's docstring.
Expected: `tephi_oracle.json` written; spot-check that `theta_from_pressure_temperature` for the (1000.0, 15.0) case is ≈ 15.0 (identity at the reference pressure).

- [ ] **Step 3: Write the comparison tests**

Create `tests/test_oracle.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Cross-validation against recorded tephi outputs (spec §7, layer 4).

tephi is a corroborating oracle, not the definition of truth: agreement
within tolerance corroborates both implementations; disagreement beyond it
means STOP and investigate (first principles win, divergences get
documented here).

Known, accepted divergence: none yet. If regeneration or investigation
reveals one (e.g. a differing kappa), document it in this docstring with
the affected tolerance.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tephpy import transforms

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "tephi_oracle.json").read_text()
)

# The x-y mapping shares MA and KELVIN exactly with tephi: tight tolerance.
XY_RTOL = 1e-10
# Poisson's equation involves each library's kappa; small constant
# differences amplify through the exponent. Loose-but-meaningful tolerance;
# tighten after investigation if tephi's kappa matches ours.
THETA_RTOL = 2e-3


@pytest.mark.parametrize(
    ("case", "expected"),
    list(
        zip(
            FIXTURE["pressure_temperature_grid"],
            FIXTURE["theta_from_pressure_temperature"],
            strict=True,
        )
    ),
)
def test_theta_matches_tephi(case, expected):
    """theta agrees with tephi within the documented tolerance."""
    pressure, temperature = case
    ours = float(transforms.theta_from_pressure_temperature(pressure, temperature))
    # Compare in Kelvin so the tolerance is meaningful near 0 degC.
    assert ours + 273.15 == pytest.approx(expected + 273.15, rel=THETA_RTOL)


@pytest.mark.parametrize(
    ("case", "expected"),
    list(
        zip(
            FIXTURE["temperature_theta_grid"],
            FIXTURE["xy_from_temperature_theta"],
            strict=True,
        )
    ),
)
def test_xy_matches_tephi(case, expected):
    """The x-y mapping agrees with tephi essentially exactly."""
    temperature, theta = case
    x, y = transforms.xy_from_temperature_theta(temperature, theta)
    np.testing.assert_allclose([float(x), float(y)], expected, rtol=XY_RTOL)
```

- [ ] **Step 4: Run the oracle tests**

Run: `pixi run pytest tests/test_oracle.py -q`
Expected: PASS. **If any case fails:** do not widen tolerances to make it pass. Reproduce the case by hand from Poisson's equation / the mapping formulae, decide which implementation is right, and record the finding in `test_oracle.py`'s module docstring (and, if tephi is wrong, consider an upstream issue). This is the verify-first stance in action.

- [ ] **Step 5: Lint and commit**

```bash
pixi run lint
git add tests/fixtures/ tests/test_oracle.py
git commit -m "test: record tephi oracle fixture and cross-validate the transforms"
```

---

## Task 4: The matplotlib Transform pair

**Files:**
- Create: `src/tephpy/plotting/__init__.py`
- Create: `src/tephpy/plotting/axes.py` (transforms only; the Axes class arrives in Task 5)
- Create: `tests/conftest.py`
- Test: `tests/test_axes.py`

**Interfaces:**
- Consumes: `transforms.xy_from_temperature_theta`, `transforms.temperature_theta_from_xy`.
- Produces: `TephigramTransform` and `TephigramInvertedTransform` — matplotlib `Transform` subclasses over `(N, 2)` arrays of `(temperature, theta)` / `(x, y)` columns. Task 5 plugs them into `TephigramAxes`.

- [ ] **Step 1: Create the Agg conftest and write the failing tests**

Create `tests/conftest.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Pytest configuration: force the non-interactive Agg backend."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
```

Create `tests/test_axes.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the tephigram matplotlib projection (spec §3.1)."""

from __future__ import annotations

import numpy as np

from tephpy import transforms
from tephpy.plotting.axes import TephigramTransform


def test_transform_matches_functions():
    """The matplotlib Transform delegates to the transforms module exactly."""
    tr = TephigramTransform()
    points = np.array([[15.0, 15.0], [-40.0, 20.0], [0.0, 100.0]])
    out = tr.transform(points)
    x, y = transforms.xy_from_temperature_theta(points[:, 0], points[:, 1])
    np.testing.assert_allclose(out, np.column_stack([x, y]), rtol=1e-12)


def test_transform_round_trip_via_inverted():
    """Transform followed by its inverse is the identity (invertibility)."""
    tr = TephigramTransform()
    points = np.array([[15.0, 15.0], [-40.0, 20.0], [30.0, 250.0]])
    back = tr.inverted().transform(tr.transform(points))
    np.testing.assert_allclose(back, points, rtol=1e-9, atol=1e-9)


def test_transform_dimensions():
    """2-in, 2-out, non-separable, declared invertible."""
    tr = TephigramTransform()
    assert tr.input_dims == 2
    assert tr.output_dims == 2
    assert not tr.is_separable
    assert tr.has_inverse
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run pytest tests/test_axes.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tephpy.plotting'`.

- [ ] **Step 3: Implement the Transform pair**

Create `src/tephpy/plotting/__init__.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tephigram plotting: the matplotlib projection and (from Plan 3) artists."""

from __future__ import annotations

from tephpy.plotting.axes import TephigramAxes

__all__ = ["TephigramAxes"]
```

(This import will fail until Task 5 adds `TephigramAxes`; for this task, create it with `__all__: list[str] = []` and no import, then restore the version above in Task 5. Alternatively run Task 5 immediately after — the intermediate state only needs `tephpy.plotting.axes` importable.)

Create `src/tephpy/plotting/axes.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The tephigram matplotlib projection.

``TephigramAxes`` (registered as the ``"tephigram"`` projection, Task 5)
uses the native rotated x-y plane as its data space, with the
temperature/theta mapping exposed as an invertible matplotlib transform.
Plan 3 extends this class in place with the isopleth machinery.
"""

from __future__ import annotations

import matplotlib.transforms as mtransforms
import numpy as np
import numpy.typing as npt

from tephpy import transforms

__all__ = ["TephigramInvertedTransform", "TephigramTransform"]


class TephigramTransform(mtransforms.Transform):
    """Map ``(temperature, theta)`` pairs to tephigram ``(x, y)`` pairs.

    A thin, invertible matplotlib wrapper over
    :func:`tephpy.transforms.xy_from_temperature_theta`; operates on
    ``(N, 2)`` arrays in diagram-native units (degrees Celsius).
    """

    input_dims = 2
    output_dims = 2
    is_separable = False
    has_inverse = True

    def transform_non_affine(
        self, values: npt.NDArray[np.float64]
    ) -> npt.NDArray[np.float64]:
        """Transform ``(N, 2)`` (temperature, theta) columns to (x, y).

        Parameters
        ----------
        values : numpy.ndarray
            Array of shape ``(N, 2)``: temperature, theta in degrees
            Celsius.

        Returns
        -------
        numpy.ndarray
            Array of shape ``(N, 2)``: the x, y display coordinates.
        """
        arr = np.asarray(values, dtype=np.float64)
        x, y = transforms.xy_from_temperature_theta(arr[:, 0], arr[:, 1])
        return np.column_stack([x, y])

    def inverted(self) -> TephigramInvertedTransform:
        """Return the inverse (x, y) -> (temperature, theta) transform."""
        return TephigramInvertedTransform()


class TephigramInvertedTransform(mtransforms.Transform):
    """Map tephigram ``(x, y)`` pairs back to ``(temperature, theta)``."""

    input_dims = 2
    output_dims = 2
    is_separable = False
    has_inverse = True

    def transform_non_affine(
        self, values: npt.NDArray[np.float64]
    ) -> npt.NDArray[np.float64]:
        """Transform ``(N, 2)`` (x, y) columns to (temperature, theta).

        Parameters
        ----------
        values : numpy.ndarray
            Array of shape ``(N, 2)``: x, y display coordinates.

        Returns
        -------
        numpy.ndarray
            Array of shape ``(N, 2)``: temperature, theta in degrees
            Celsius.
        """
        arr = np.asarray(values, dtype=np.float64)
        t, theta = transforms.temperature_theta_from_xy(arr[:, 0], arr[:, 1])
        return np.column_stack([t, theta])

    def inverted(self) -> TephigramTransform:
        """Return the forward (temperature, theta) -> (x, y) transform."""
        return TephigramTransform()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run pytest tests/test_axes.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Lint and commit**

```bash
pixi run lint
git add src/tephpy/plotting/ tests/conftest.py tests/test_axes.py
git commit -m "feat: add the invertible tephigram matplotlib transform pair"
```

---

## Task 5: TephigramAxes, projection registration, and package wiring

**Files:**
- Modify: `src/tephpy/plotting/axes.py` (append `TephigramAxes` + registration)
- Modify: `src/tephpy/plotting/__init__.py` (the Task 4 note's final version)
- Modify: `src/tephpy/__init__.py` (import submodules; extend `__all__`)
- Test: `tests/test_axes.py` (append)

**Interfaces:**
- Consumes: the Task 4 transforms; `_constants.DEFAULT_ANCHOR`; `transforms.theta_from_pressure_temperature`, `xy_from_temperature_theta`.
- Produces: `TephigramAxes` with `name = "tephigram"`, attribute `tephigram_transform: TephigramTransform`; registered so `plt.subplots(subplot_kw={"projection": "tephigram"})` works after `import tephpy`. Plan 3 extends this class; Plan 4's `plot_profile` composes `ax.tephigram_transform + ax.transData`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_axes.py`:

```python
import matplotlib.pyplot as plt
import pytest

import tephpy
from tephpy.plotting.axes import TephigramAxes


@pytest.fixture
def tephigram_axes():
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    yield ax
    plt.close(fig)


def test_projection_registered_by_package_import(tephigram_axes):
    """`import tephpy` registers the projection for stock matplotlib idioms."""
    assert isinstance(tephigram_axes, TephigramAxes)
    assert tephigram_axes.name == "tephigram"


def test_axes_defaults(tephigram_axes):
    """Equal aspect, hidden native ticks, finite default extents."""
    assert tephigram_axes.get_aspect() == 1.0
    assert not tephigram_axes.xaxis.get_visible()
    assert not tephigram_axes.yaxis.get_visible()
    x0, x1 = tephigram_axes.get_xlim()
    y0, y1 = tephigram_axes.get_ylim()
    assert np.isfinite([x0, x1, y0, y1]).all()
    assert x0 < x1 and y0 < y1


def test_axes_exposes_invertible_tephigram_transform(tephigram_axes):
    """The (T, theta) mapping is available for artists and later plans."""
    composed = tephigram_axes.tephigram_transform + tephigram_axes.transData
    points = np.array([[15.0, 15.0], [-40.0, 20.0]])
    display = composed.transform(points)
    assert np.isfinite(display).all()
    back = tephigram_axes.tephigram_transform.inverted().transform(
        tephigram_axes.tephigram_transform.transform(points)
    )
    np.testing.assert_allclose(back, points, rtol=1e-9)


def test_plot_in_temperature_theta_space(tephigram_axes):
    """Plotting through the exposed transform draws within the default view."""
    (line,) = tephigram_axes.plot(
        [0.0, 10.0],
        [10.0, 40.0],
        transform=tephigram_axes.tephigram_transform + tephigram_axes.transData,
    )
    assert line in tephigram_axes.lines


def test_top_level_namespace():
    """Submodules are reachable from the package root (spec §4 idiom)."""
    assert tephpy.transforms is not None
    assert tephpy.plotting is not None
    assert set(tephpy.__all__) == {"__version__", "plotting", "transforms"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run pytest tests/test_axes.py -q`
Expected: FAIL — `ImportError: cannot import name 'TephigramAxes'`.

- [ ] **Step 3: Implement the axes and wire the package**

Append to `src/tephpy/plotting/axes.py` (extend the existing imports with the two new ones shown):

```python
from matplotlib.axes import Axes
from matplotlib.projections import register_projection

from tephpy._constants import DEFAULT_ANCHOR
```

```python
class TephigramAxes(Axes):
    """Matplotlib axes for the ``"tephigram"`` projection.

    The data space is the native rotated x-y plane (dimensionless), with
    equal aspect so the isotherm/dry-adiabat grid stays exactly
    perpendicular on screen. The temperature/theta mapping is exposed as
    :attr:`tephigram_transform`; artists plot in (temperature, theta)
    space via ``transform=ax.tephigram_transform + ax.transData``. Native
    x/y ticks carry no meteorological meaning and are hidden — meaningful
    labelling arrives with the Plan 3 isopleths.
    """

    name = "tephigram"

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise the axes and apply the tephigram view defaults.

        Parameters
        ----------
        *args : object
            Positional arguments forwarded to :class:`matplotlib.axes.Axes`.
        **kwargs : object
            Keyword arguments forwarded to :class:`matplotlib.axes.Axes`.
        """
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.tephigram_transform = TephigramTransform()
        self.set_aspect(1.0, adjustable="box")
        self.xaxis.set_visible(False)
        self.yaxis.set_visible(False)
        self._set_default_extent()

    def _set_default_extent(self) -> None:
        """Frame the default view from the ``DEFAULT_ANCHOR`` corners."""
        (p_bottom, t_left), (p_top, t_right) = DEFAULT_ANCHOR
        corner_pressures = np.array([p_bottom, p_top])
        corner_temperatures = np.array([t_left, t_right])
        thetas = transforms.theta_from_pressure_temperature(
            corner_pressures, corner_temperatures
        )
        x, y = transforms.xy_from_temperature_theta(corner_temperatures, thetas)
        self.set_xlim(float(np.min(x)), float(np.max(x)))
        self.set_ylim(float(np.min(y)), float(np.max(y)))


register_projection(TephigramAxes)
```

Add `"TephigramAxes"` to the module's `__all__`. Restore `src/tephpy/plotting/__init__.py` to the Task 4 listing (importing and re-exporting `TephigramAxes`).

Update `src/tephpy/__init__.py` — replace the existing `__all__` line and add the submodule imports after the version block:

```python
from tephpy import plotting, transforms

__all__ = ["__version__", "plotting", "transforms"]
```

(The `plotting` import registers the projection as a side effect; the re-export through `__all__` keeps ruff satisfied without a `noqa`. Note: `import tephpy` now imports matplotlib — acceptable for a plotting library; the MetPy import-cost question is spec §10 item 10, owned by Plans 4/5.)

- [ ] **Step 4: Run the full test suite**

Run: `pixi run pytest -q`
Expected: PASS — every test from Tasks 1–5 (import smoke tests from Plan 1 included).

- [ ] **Step 5: mypy note, lint, and commit**

If `pixi run lint` surfaces mypy errors *originating from matplotlib's stubs* (not from tephpy code), extend the existing override table in `pyproject.toml`'s `[[tool.mypy.overrides]]` with `"matplotlib.*"` — but only for `ignore_missing_imports`; do not relax strictness for `tephpy` modules (spec §8.4 forbids it for the numeric core).

```bash
pixi run lint
git add src/tephpy/ tests/test_axes.py
git commit -m "feat: add TephigramAxes and register the tephigram projection"
```

---

## Task 6: Glossary entries and a warning-free docs build

**Files:**
- Modify: `docs/src/reference/glossary.rst` (append three entries)

**Interfaces:**
- Produces: glossary terms `potential temperature`, `dry adiabat`, `isotherm` available for `:term:` references (spec §10 cross-cutting rule; §8.6 glossary style — engineer-first, one plain sentence then the tephpy angle).

- [ ] **Step 1: Append the entries**

Append inside the existing `.. glossary::` directive in `docs/src/reference/glossary.rst`, keeping the established indent:

```rst
    potential temperature
        The temperature an air parcel would have if moved dry-adiabatically
        to the 1000 hPa reference pressure; written θ (theta). In ``tephpy``
        it is the second native coordinate of the tephigram plane —
        ``transforms.theta_from_pressure_temperature`` computes it (°C)
        from pressure (hPa) and temperature (°C).

    dry adiabat
        A line of constant :term:`potential temperature` — the path an
        unsaturated parcel follows when lifted. On a tephigram, dry
        adiabats are straight lines exactly perpendicular to the
        :term:`isotherms <isotherm>`.

    isotherm
        A line of constant temperature. On a tephigram, isotherms are
        straight parallel lines; their exact perpendicularity to the
        :term:`dry adiabats <dry adiabat>` is the diagram's defining
        property and is asserted directly in the test suite.
```

- [ ] **Step 2: Build the docs**

Run: `pixi run docs`
Expected: `build succeeded`, **0 warnings**. The autoapi section now includes `tephpy.transforms` and `tephpy.plotting.axes` pages. If a warning appears (e.g. a cross-reference typo), fix it — do not suppress.

- [ ] **Step 3: Commit**

```bash
git add docs/src/reference/glossary.rst
git commit -m "docs: seed glossary entries for the transform-layer terms"
```

---

## Task 7: Wheel-install smoke test in ci-wheels

**Files:**
- Modify: `.github/workflows/ci-wheels.yml` (append a step to the `build` job, after `twine check`)

**Interfaces:**
- Produces: CI proof that the built wheel installs standalone and the projection registers (spec §10 item 15, assigned to Plan 2).

- [ ] **Step 1: Append the smoke-test step**

In the `build` job of `.github/workflows/ci-wheels.yml`, after the `pipx run twine check dist/*` step:

```yaml
      - name: Wheel install smoke test
        run: |
          python3 -m venv /tmp/smoke
          /tmp/smoke/bin/pip install dist/*.whl
          /tmp/smoke/bin/python - <<'PY'
          import matplotlib
          matplotlib.use("Agg")
          import matplotlib.pyplot as plt
          import tephpy
          fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
          assert type(ax).__name__ == "TephigramAxes", type(ax)
          print("wheel smoke OK:", tephpy.__version__)
          PY
```

No new permissions, no new actions — the zizmor posture is unchanged.

- [ ] **Step 2: Validate the workflow locally**

Run:
```bash
pixi run -e devs pre-commit run check-github-workflows --all-files
pixi run -e devs pre-commit run zizmor --all-files
```
Expected: both pass.

- [ ] **Step 3: Reproduce the smoke test locally**

```bash
pixi run -e devs python -m build
python3 -m venv /tmp/smoke && /tmp/smoke/bin/pip install dist/*.whl
/tmp/smoke/bin/python -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; import tephpy; fig, ax = plt.subplots(subplot_kw={'projection': 'tephigram'}); print('OK', tephpy.__version__)"
```
Expected: `OK 0.1.dev...` printed.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci-wheels.yml
git commit -m "ci: smoke-test the built wheel installs and registers the projection"
```

---

## Task 8: Full verification, pull request, and changelog fragment

**Files:** `changelog/<PR>.feature.rst` (created after the PR number exists)

- [ ] **Step 1: Full local gate**

```bash
pixi run lint
pixi run -e test-py312 pytest -q
pixi run -e test-py313 pytest -q
pixi run -e test-py314 pytest -q
pixi run docs
```
Expected: lint fully green; tests pass on all three Pythons; docs build with 0 warnings.

- [ ] **Step 2: Open the pull request**

```bash
git push -u origin transforms
gh pr create --base main --title "Tephigram transforms and minimal projection (Plan 2)" --fill
```

- [ ] **Step 3: Add the changelog fragment named for the PR**

With `<PR>` the number just created:

```bash
cat > changelog/<PR>.feature.rst <<'EOF'
Added the tephigram coordinate transforms and a minimal ``"tephigram"`` Matplotlib projection, cross-validated against tephi.
EOF
git add changelog/<PR>.feature.rst
git commit -m "docs: add Plan 2 changelog fragment"
git push
```
Expected: the `ci-changelog` check passes on the PR; all other checks (tests ×3, docs, wheels + smoke test, CodeQL, pre-commit.ci) go green.

---

## Self-review

**Spec coverage (§3.1/§7/§10 Plan 2 row):** T–ln θ math derived from published sources → Tasks 1–2 (formulae cited to Factsheet 13/Stull; fixed points recomputed independently). Projection + minimal `TephigramAxes` in `plotting/axes.py`, transforms numpy-pure → Tasks 4–5. `_constants` seed (MA, θ reference pressure, default extents) → Task 1. Four-layer §7 battery → hypothesis round-trips (Tasks 1–2), independent fixed points (Tasks 1–2), ⊥ invariant (Task 2), tephi oracle (Task 3). NaN domain policy → Tasks 1–2. Equal aspect/hidden ticks/default extents/zoom-free-via-transform → Task 5. Glossary seeding rule → Task 6. Wheel smoke test (item 15) → Task 7. Changelog + full gate → Task 8.

**Placeholder scan:** the only intentionally deferred detail is tephi's exact `convert_*` names in Task 3, with the inspection command and the constraint (fixture format frozen) stated — an external-package fact checkable only at execution. No TBDs otherwise; every code step shows complete code.

**Type/name consistency:** `theta_from_pressure_temperature` / `pressure_from_temperature_theta` / `xy_from_temperature_theta` / `temperature_theta_from_xy` used identically in Tasks 1–5 and the Interfaces contract; `TephigramTransform`/`TephigramInvertedTransform`/`TephigramAxes` consistent across Tasks 4–5 and the smoke test; constants names consistent with `_constants.py`.

**Known judgment calls (documented, not hidden):** data space is native x-y with the mapping exposed as `tephigram_transform` (the approved "invertible Transform wrapping the transforms functions" design — full (T, θ) data-space projection was rejected as needless complexity before Plan 3's artists exist); `KAPPA = 287.05/1004.68` from first principles with the oracle tolerance (`THETA_RTOL = 2e-3`) sized for a possible tephi kappa difference and an explicit investigate-don't-widen rule; `import tephpy` now imports matplotlib (a plotting library — acceptable; the heavier MetPy question stays with Plans 4/5 per spec §10 item 10).

---

## Execution handoff

Plan 2 of 7 (spec §10). On completion, **Plan 3: isopleth plotting** is unblocked — it extends `TephigramAxes` in place with the five isopleth families, the `_constants`-backed conventions and config object, and the pytest-mpl baseline infrastructure.
