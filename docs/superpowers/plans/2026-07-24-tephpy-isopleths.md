# tephpy Isopleth Plotting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the five zoom-aware background isopleth families (isotherms, isobars, dry adiabats, moist adiabats, humidity mixing-ratio lines) with per-family accessor methods, `set_extent`, the `tephpy.config` runtime layer, and the pytest-mpl image-baseline infrastructure — so `plt.subplots(subplot_kw={"projection": "tephigram"})` yields the first real, labelled tephigram.

**Architecture:** `plotting/isopleths.py` holds pure geometry builders (one per family; the two curved families call MetPy behind function-local imports) plus one `IsoplethFamily` matplotlib `Artist` class instantiated five times per axes — members precomputed over a generous physical domain, cached, and selected per `draw()` by a convention-driven zoom ladder plus a vectorized view-bbox mask, with labels re-placed each draw. `_config.py` adds the typed `tephpy.config` singleton (precedence: accessor kwargs > `tephpy.config` > `_constants`); `_constants.py` accretes the family conventions; `TephigramAxes` gains a `clear()` override (the PolarAxes projection pattern) that creates the families on by default, the five accessors, and `set_extent`.

**Tech Stack:** Python 3.12/3.13/3.14, numpy, matplotlib (Agg in tests), metpy (runtime dep, function-local imports), hypothesis, pytest, pytest-mpl, pixi tasks, tephi 0.4.0.post0 (oracle only — a throwaway venv, never a runtime dependency).

**Spec:** `docs/superpowers/specs/2026-07-22-tephpy-design.md` — §3.2 (authority for this plan), §3.5 (`_constants` + `tephpy.config`), §7/§8.5 (image baselines; informational tephi cross-check for curved families), §10 (Plan 3 row; resolved items 6, 7, 15).

This is **Plan 3 of 7** (spec §10). It produces working software: after `import tephpy`, creating a `"tephigram"` axes draws the full labelled background grid, zoom/pan re-select members automatically, and PDF/SVG export works.

## Global Constraints

Copied from the spec / Plans 1–2; every task's requirements implicitly include these.

- **Python support (SPEC 0):** 3.12, 3.13, and 3.14. **Platforms (pixi):** `linux-64` only.
- **Copyright header (every `.py` file, verbatim — ruff `CPY001` enforces it):**
  ```
  # Copyright (c) 2026, tephpy Contributors.
  #
  # This file is part of tephpy and is distributed under the 3-Clause BSD license.
  # See the LICENSE file in the package root directory for licensing details.
  ```
- **Imports:** every `.py` file needs `from __future__ import annotations` (ruff isort `required-imports`).
- **Lint/type:** ruff `ALL` (repo config); mypy `strict` clean over `src/tephpy` (spec §8.4). numpydoc-validation runs on `src/` and checks **every docstringed object, including private helpers**: any function that returns a value needs a `Returns` section (RT01) and documented parameters (PR01) — verified against this repo's config on 2026-07-24.
- **Function-local MetPy imports** (spec §3.2/§10 item 10) trigger ruff `PLC0415` — suppress with `# noqa: PLC0415` exactly as shown in the task code (verified needed).
- **Units:** isopleth geometry is diagram-native bare numpy (hPa/°C/g-per-kg), like `transforms` (spec §5 exemption). pint `Quantity` objects exist **only** immediately around the MetPy calls; strip magnitudes with `.m_as(...)` before any numpy/matplotlib use — `np.asarray(Quantity)` raises `pint.UnitStrippedWarning`, which is an **error** under the repo's pytest `filterwarnings = ["error"]`.
- **Verify-first (spec §3.1/§7):** derive from published sources (Met Office Factsheet 13; Stull ch. 5); MetPy carries the moist thermodynamics; tephi is a corroborating oracle for the curved families (informational — divergence triggers investigation and documentation, not tolerance-widening). Attribution attaches only to artifacts actually copied — this plan copies none (oracle values are *generated* by running tephi).
- **Tests:** pytest strict config with `filterwarnings = ["error"]`; close every matplotlib figure you open (pytest-mpl closes returned figures itself).
- **Docs:** build must stay warning-free (`pixi run docs`). Titles use CMOS headline style. Glossary entries ship with the terms this plan introduces (spec §10 cross-cutting rule).
- **Changelog:** one `changelog/<PR>.<type>.rst` fragment per PR, ending with author attribution via the `:user:` extlink role — Claude-authored fragments credit ``(:user:`claude`)`` (see `changelog/README.md`).
- **Workflow edits:** SHA-pinned actions, `permissions: {}`, zizmor must stay clean.
- **Branch:** work on a feature branch (`no-commit-to-branch` blocks `main`): `git switch -c isopleths`.
- **Lint gotcha:** `pre-commit run --all-files` only checks files git knows about — **`git add` new files before `pixi run lint`** (every task's final step stages first for this reason).
- **Environment facts (verified against the committed lockfile, 2026-07-24/25):** metpy 1.7.1, pint 0.25.3, numpy 2.5.1, matplotlib 3.11.1, pytest-mpl 0.19.0, freetype 2.14.3 — and the three test envs (`test-py312/313/314`) pin the **identical** matplotlib + freetype builds, so pytest-mpl PNG output is bit-identical across them (verified). The code in this plan was verified against this environment: the listings pass ruff (`ALL` + format), mypy strict, and numpydoc-validation; the artist was smoke-tested end to end; and an adversarial review pass executed every task's code and tests against this plan text (2026-07-25).

---

## File structure created or modified by this plan

```
src/tephpy/
  _constants.py                       # MODIFIED: DEFAULT_ANCHOR→DEFAULT_EXTENT; + isopleth conventions
  _config.py                          # NEW: tephpy.config typed singleton + context manager
  plotting/
    isopleths.py                      # NEW: Member, 5 builders, FamilySpec, IsoplethFamily
    axes.py                           # MODIFIED: clear() override, 5 accessors, set_extent
  __init__.py                         # MODIFIED: export config
tests/
  test_constants.py                   # NEW: convention invariants
  test_config.py                      # NEW: config semantics
  test_isopleths.py                   # NEW: builders + artist behaviour
  test_axes.py                        # MODIFIED: accessors, set_extent, clear; __all__ update
  test_isopleth_oracle.py             # NEW: informational tephi cross-check (curved families)
  test_images.py                      # NEW: pytest-mpl baselines + vector-output smoke test
  baseline/*.png                      # NEW: 7 committed baselines (generated, small)
  fixtures/
    generate_tephi_isopleth_oracle.py # NEW: one-shot generator (throwaway venv, not CI)
    tephi_isopleth_oracle.json        # NEW: committed oracle values + provenance
  AGENTS.md                           # MODIFIED: task rename (baselines)
docs/src/reference/glossary.rst       # MODIFIED: + isopleth, isobar, moist adiabat (+aliases),
                                      #   humidity mixing ratio (+aliases)
pyproject.toml                        # MODIFIED: --mpl wiring, baselines/tests-clean tasks
.github/workflows/ci-tests.yml        # MODIFIED: --mpl flag on the pytest run
.gitignore                            # MODIFIED: + .mpl-results/
changelog/<PR>.feature.rst            # NEW: news fragment (named after the PR, Task 10)
```

Naming used throughout (Interfaces contract):

```
tephpy._constants (additions):
    DEFAULT_EXTENT (renames DEFAULT_ANCHOR)
    PRESSURE_DOMAIN, TEMPERATURE_DOMAIN, THETA_DOMAIN, MOIST_ADIABAT_DOMAIN
    ISOPLETH_SAMPLES, MOIST_ADIABAT_PRESSURE_STEP, MOIST_ADIABAT_TRUNCATION
    ISOTHERM_STEPS, DRY_ADIABAT_STEPS, ISOBAR_STEPS, MOIST_ADIABAT_STEPS   # (min_view_width, step) ladders
    MIXING_RATIO_STRIDES                                                    # (min_view_width, stride) ladder
    MIXING_RATIO_VALUES
    ISOTHERM_COLOR, DRY_ADIABAT_COLOR, ISOBAR_COLOR, MOIST_ADIABAT_COLOR, MIXING_RATIO_COLOR
    ISOPLETH_LINEWIDTH, ISOPLETH_ALPHA
    ISOTHERM_ZORDER, DRY_ADIABAT_ZORDER, ISOBAR_ZORDER, MIXING_RATIO_ZORDER, MOIST_ADIABAT_ZORDER
    LABEL_FONTSIZE, LABEL_BOXSTYLE, LABEL_BOX_COLOR, LABEL_BOX_ALPHA

tephpy._config:
    LineOptions / FamilyOptions / MixingRatioOptions / MoistAdiabatOptions / DiagramOptions / Config
    config: Config                       # the singleton; re-exported as tephpy.config

tephpy.plotting.isopleths:
    Member(value: float, xy: NDArray[(N, 2) float64])
    isotherm_members(values) -> list[Member]
    dry_adiabat_members(values) -> list[Member]
    isobar_members(values) -> list[Member]
    moist_adiabat_members(values, truncation=MOIST_ADIABAT_TRUNCATION) -> list[Member]
    mixing_ratio_members(values) -> list[Member]
    ResolvedOptions, FamilySpec, _FAMILY_SPECS: dict[str, FamilySpec]
    IsoplethFamily(spec: FamilySpec, section: object)
        .configure(**kwargs) -> None     # TypeError on unknown option
        .options -> ResolvedOptions      # read-only snapshot

tephpy.plotting.axes.TephigramAxes:
    .clear() -> None                     # recreates families + defaults (projection pattern)
    .set_extent(extent) -> None          # ((p, T), (p, T)) hPa/°C corners; ValueError if unphysical
    .isotherms(...) / .isobars(...) / .dry_adiabats(...) / .moist_adiabats(...)
        / .mixing_ratios(...) -> IsoplethFamily
    ._families: dict[str, IsoplethFamily]

tephpy top level: tephpy.config joins __all__ = ["__version__", "config", "plotting", "transforms"]
```

Design decisions locked here (shared vocabulary for all tasks):

- **Zoom ladder semantics.** A ladder is a tuple of `(min_view_width, step)` pairs, widest first, last pair always `(0.0, finest)`. The *view width* is the axes' data-space x-span (`viewLim.width`); along an isobar 1 x-unit ≈ 1 °C, and the default extent is ≈ 311 units wide. The step in force is the first pair whose `min_view_width <= width`. Interval families show members whose value is a multiple of the step (coarse members therefore never vanish when zooming in); the mixing-ratio family strides into its canonical values list (`values[::stride]`), anchored at index 0 so panning never shifts the visible subset (a deliberate fix for tephi 0.4's pan-dependent decimation).
- **Explicit `values` or `interval` disables the ladder** — the user asked for an exact member set, so all of it shows (subject to the view mask).
- **Configuration precedence** (spec §3.5): accessor kwargs > `tephpy.config` > `_constants`, resolved into a frozen `ResolvedOptions` snapshot when a family is created or reconfigured — never at draw time, so later config changes do not restyle existing axes (rcParams semantics).
- **Labels** are family-colored, drawn at the middle in-view vertex of each member, rotated to the local line direction in *screen* space and folded upright (`(angle + 90) % 180 - 90`), on a translucent white pill so they punch a hole in the line work.

---

## Task 1: `_constants` accretion and the DEFAULT_EXTENT rename

**Files:**
- Modify: `src/tephpy/_constants.py`
- Modify: `src/tephpy/plotting/axes.py` (rename fallout only)
- Test: `tests/test_constants.py`

**Interfaces:**
- Produces: every `_constants` name in the contract above. `DEFAULT_ANCHOR` is **renamed** to `DEFAULT_EXTENT` (spec §10 item 6 — the anchoring API is now `set_extent`); tephpy is unreleased, so no deprecation shim.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_constants.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the diagram convention constants (spec §3.5)."""

from __future__ import annotations

import numpy as np

from tephpy import _constants as constants

INTERVAL_LADDERS = (
    constants.ISOTHERM_STEPS,
    constants.DRY_ADIABAT_STEPS,
    constants.ISOBAR_STEPS,
    constants.MOIST_ADIABAT_STEPS,
)


def test_default_extent_orientation():
    """Bottom-left has the higher pressure; temperatures increase rightward."""
    (p0, t0), (p1, t1) = constants.DEFAULT_EXTENT
    assert p0 > p1 > 0.0
    assert t0 < t1


def test_domains_are_ordered():
    for lo, hi in (
        constants.PRESSURE_DOMAIN,
        constants.TEMPERATURE_DOMAIN,
        constants.THETA_DOMAIN,
        constants.MOIST_ADIABAT_DOMAIN,
    ):
        assert lo < hi


def test_zoom_ladders_are_well_formed():
    """Widest first, terminated by a catch-all (0.0, finest) pair."""
    for ladder in (*INTERVAL_LADDERS, constants.MIXING_RATIO_STRIDES):
        widths = [width for width, _ in ladder]
        steps = [step for _, step in ladder]
        assert widths == sorted(widths, reverse=True)
        assert widths[-1] == 0.0
        assert steps == sorted(steps, reverse=True)
        assert all(step > 0 for step in steps)


def test_coarser_steps_are_multiples_of_the_finest():
    """Members are built at the finest step; coarser rungs must select a
    subset of them, so every rung must divide evenly by the finest."""
    for ladder in INTERVAL_LADDERS:
        finest = ladder[-1][1]
        for _, step in ladder:
            assert step / finest == np.round(step / finest)


def test_mixing_ratio_values_sorted_and_positive():
    values = np.asarray(constants.MIXING_RATIO_VALUES)
    assert (values > 0.0).all()
    assert (np.diff(values) > 0.0).all()


def test_truncation_below_moist_adiabat_domain():
    """Truncation must bite: below every labelled theta_w start value."""
    assert constants.MOIST_ADIABAT_TRUNCATION < constants.MOIST_ADIABAT_DOMAIN[0]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_constants.py -q`
Expected: FAIL — `AttributeError: module 'tephpy._constants' has no attribute 'ISOTHERM_STEPS'` (collection error is fine).

- [ ] **Step 3: Rename DEFAULT_ANCHOR and append the conventions**

In `src/tephpy/_constants.py`, replace the existing `DEFAULT_ANCHOR` block (the `#:` comment lines and the assignment) with:

```python
#: Default diagram extent as ((pressure, temperature), (pressure, temperature))
#: corners in hPa / degrees Celsius: bottom-left and top-right of the default
#: view (see ``TephigramAxes.set_extent``).
DEFAULT_EXTENT: Final[tuple[tuple[float, float], tuple[float, float]]] = (
    (1050.0, -40.0),
    (200.0, 40.0),
)
```

Then append (all values are conventions: domains sized generously around the
Met Office Factsheet 13 chart ranges; intervals per Factsheet 13 (10 °C
isotherms/dry adiabats at the default view) with tephi's defaults as
corroboration; the ladder semantics are defined in the plan header):

```python
#: Pressure domain the isopleth geometry is computed over (hPa).
PRESSURE_DOMAIN: Final[tuple[float, float]] = (50.0, 1050.0)

#: Temperature domain the isopleth geometry is computed over (°C).
TEMPERATURE_DOMAIN: Final[tuple[float, float]] = (-120.0, 60.0)

#: Potential-temperature domain the isopleth geometry is computed over (°C).
THETA_DOMAIN: Final[tuple[float, float]] = (-100.0, 520.0)

#: Wet-bulb potential-temperature domain for the moist adiabats (°C).
MOIST_ADIABAT_DOMAIN: Final[tuple[float, float]] = (-40.0, 60.0)

#: Vertices per isopleth member polyline.
ISOPLETH_SAMPLES: Final[int] = 101

#: Pressure sampling step for the moist-adiabat integration (hPa).
MOIST_ADIABAT_PRESSURE_STEP: Final[float] = 5.0

#: Temperature below which moist adiabats are truncated (°C) — the curves
#: converge onto the dry adiabats (Met Office Factsheet 13 convention).
MOIST_ADIABAT_TRUNCATION: Final[float] = -50.0

#: Isotherm zoom ladder: (min view width, member interval in °C) pairs,
#: widest first (10 °C at the default view width of ~311 units).
ISOTHERM_STEPS: Final[tuple[tuple[float, float], ...]] = (
    (500.0, 20.0),
    (100.0, 10.0),
    (0.0, 5.0),
)

#: Dry-adiabat zoom ladder (°C of potential temperature); the grid is
#: symmetric with the isotherms.
DRY_ADIABAT_STEPS: Final[tuple[tuple[float, float], ...]] = ISOTHERM_STEPS

#: Isobar zoom ladder (hPa): 50 hPa at the default view width, refining to
#: the 10 hPa printed-chart interval (Met Office Factsheet 13; spec §3.5)
#: at deep zoom.
ISOBAR_STEPS: Final[tuple[tuple[float, float], ...]] = (
    (500.0, 100.0),
    (150.0, 50.0),
    (75.0, 20.0),
    (0.0, 10.0),
)

#: Moist-adiabat zoom ladder (°C of wet-bulb potential temperature).
MOIST_ADIABAT_STEPS: Final[tuple[tuple[float, float], ...]] = (
    (500.0, 10.0),
    (150.0, 5.0),
    (50.0, 2.0),
    (0.0, 1.0),
)

#: Humidity mixing-ratio zoom ladder: (min view width, stride into
#: ``MIXING_RATIO_VALUES``) pairs, widest first.
MIXING_RATIO_STRIDES: Final[tuple[tuple[float, int], ...]] = (
    (500.0, 4),
    (150.0, 2),
    (0.0, 1),
)

#: Humidity mixing-ratio member values (g/kg).
MIXING_RATIO_VALUES: Final[tuple[float, ...]] = (
    0.05,
    0.1,
    0.2,
    0.5,
    1.0,
    1.5,
    2.0,
    3.0,
    4.0,
    5.0,
    7.0,
    10.0,
    14.0,
    20.0,
    28.0,
    40.0,
)

#: Isotherm line colour.
ISOTHERM_COLOR: Final[str] = "dimgrey"

#: Dry-adiabat line colour.
DRY_ADIABAT_COLOR: Final[str] = "darkgrey"

#: Isobar line colour.
ISOBAR_COLOR: Final[str] = "tab:blue"

#: Moist-adiabat line colour.
MOIST_ADIABAT_COLOR: Final[str] = "tab:orange"

#: Humidity mixing-ratio line colour.
MIXING_RATIO_COLOR: Final[str] = "tab:green"

#: Isopleth line width in points.
ISOPLETH_LINEWIDTH: Final[float] = 0.5

#: Isopleth line and label alpha.
ISOPLETH_ALPHA: Final[float] = 1.0

#: Isotherm draw order.
ISOTHERM_ZORDER: Final[float] = 1.1

#: Dry-adiabat draw order.
DRY_ADIABAT_ZORDER: Final[float] = 1.2

#: Isobar draw order.
ISOBAR_ZORDER: Final[float] = 1.3

#: Humidity mixing-ratio draw order.
MIXING_RATIO_ZORDER: Final[float] = 1.4

#: Moist-adiabat draw order.
MOIST_ADIABAT_ZORDER: Final[float] = 1.5

#: Isopleth label font size in points.
LABEL_FONTSIZE: Final[float] = 8.0

#: Isopleth label box style.
LABEL_BOXSTYLE: Final[str] = "round,pad=0.3"

#: Isopleth label box colour.
LABEL_BOX_COLOR: Final[str] = "white"

#: Isopleth label box alpha.
LABEL_BOX_ALPHA: Final[float] = 0.6
```

(All family zorders sit below matplotlib's default `Line2D` zorder of 2, so
user-plotted profiles always draw above the background grid.)

- [ ] **Step 4: Fix the rename fallout in `axes.py`**

In `src/tephpy/plotting/axes.py` (this is the only module that referenced the
old name — verify with `grep -rn DEFAULT_ANCHOR src/ tests/`):
- change the import to `from tephpy._constants import DEFAULT_EXTENT`
- in `_set_default_extent`, change `DEFAULT_ANCHOR` to `DEFAULT_EXTENT` and
  the docstring to ``"""Frame the default view from the ``DEFAULT_EXTENT`` corners."""``

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_constants.py tests/test_axes.py -q`
Expected: PASS (the axes tests prove the rename broke nothing).

- [ ] **Step 6: Lint and commit**

```bash
git add src/tephpy/_constants.py src/tephpy/plotting/axes.py tests/test_constants.py
pixi run lint
git commit -m "feat: seed the isopleth conventions and rename DEFAULT_ANCHOR to DEFAULT_EXTENT"
```

---

## Task 2: The `tephpy.config` runtime configuration layer

**Files:**
- Create: `src/tephpy/_config.py`
- Modify: `src/tephpy/__init__.py`
- Modify: `tests/test_axes.py` (one assertion: top-level `__all__`)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `tephpy._config` names in the contract; `tephpy.config` importable from the package root. Tasks 5–6 read config sections via `getattr(config, family_name)` and `config.diagram.extent`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the tephpy.config runtime configuration layer (spec §3.5)."""

from __future__ import annotations

import dataclasses

import pytest

import tephpy
from tephpy import _config

SECTIONS = (
    "isotherms",
    "isobars",
    "dry_adiabats",
    "moist_adiabats",
    "mixing_ratios",
    "diagram",
)


def test_singleton_identity_and_sections():
    assert tephpy.config is _config.config
    assert isinstance(tephpy.config, _config.Config)
    for section in SECTIONS:
        assert hasattr(tephpy.config, section)


def test_all_defaults_are_none():
    """None means fall through to the `_constants` conventions."""
    for section_field in dataclasses.fields(_config.Config):
        section = getattr(tephpy.config, section_field.name)
        for option in dataclasses.fields(section):
            assert getattr(section, option.name) is None


def test_section_shapes():
    """moist_adiabats gains truncation; mixing_ratios has no interval."""
    assert hasattr(tephpy.config.moist_adiabats, "truncation")
    assert hasattr(tephpy.config.mixing_ratios, "values")
    assert not hasattr(tephpy.config.mixing_ratios, "interval")
    assert hasattr(tephpy.config.diagram, "extent")


def test_context_applies_and_restores():
    with tephpy.config.context(isobars={"interval": 25.0}) as cfg:
        assert cfg is tephpy.config
        assert tephpy.config.isobars.interval == 25.0
    assert tephpy.config.isobars.interval is None


def test_context_restores_on_error():
    msg = "boom"
    with (
        pytest.raises(RuntimeError, match="boom"),
        tephpy.config.context(isobars={"interval": 25.0}),
    ):
        raise RuntimeError(msg)
    assert tephpy.config.isobars.interval is None


def test_context_unknown_section_raises():
    with (
        pytest.raises(TypeError, match="unknown config section"),
        tephpy.config.context(bogus={"interval": 25.0}),
    ):
        pass  # pragma: no cover


def test_context_unknown_option_raises_and_restores_prior_sections():
    """A failure mid-application must roll back what was already applied."""
    with (
        pytest.raises(TypeError, match="unknown option"),
        tephpy.config.context(isobars={"interval": 25.0}, diagram={"bogus": 1}),
    ):
        pass  # pragma: no cover
    assert tephpy.config.isobars.interval is None
```

Also, in `tests/test_axes.py`, update the final assertion of
`test_top_level_namespace` to:

```python
assert set(tephpy.__all__) == {"__version__", "config", "plotting", "transforms"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_config.py tests/test_axes.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tephpy._config'`, and the `__all__` assertion fails.

- [ ] **Step 3: Create `_config.py` and wire the top level**

Create `src/tephpy/_config.py` — this exact code passes ruff, mypy strict, and
numpydoc-validation (verified 2026-07-24):

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Runtime configuration for tephpy (spec §3.5).

``tephpy.config`` is the mutable, typed runtime layer over the
``_constants`` conventions. Precedence: accessor kwargs > ``tephpy.config``
> ``_constants``. A ``None`` field means "fall through to the next tier".
Configuration is read when an isopleth family is created or reconfigured;
changing it does not retroactively restyle existing axes (matplotlib
rcParams semantics).
"""

from __future__ import annotations

from contextlib import contextmanager
import dataclasses
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

__all__ = [
    "Config",
    "DiagramOptions",
    "FamilyOptions",
    "LineOptions",
    "MixingRatioOptions",
    "MoistAdiabatOptions",
    "config",
]

#: A diagram extent: ((pressure, temperature), (pressure, temperature))
#: corners in hPa / degrees Celsius.
Extent = tuple[tuple[float, float], tuple[float, float]]


@dataclasses.dataclass
class LineOptions:
    """Style and visibility options common to every isopleth family.

    A ``None`` field falls through to the ``_constants`` convention default.
    """

    #: Matplotlib colour for the family's lines and labels.
    color: str | None = None

    #: Line width in points.
    linewidth: float | None = None

    #: Line and label alpha.
    alpha: float | None = None

    #: Whether member values are labelled on the lines.
    labels: bool | None = None

    #: Whether the family is drawn at all.
    visible: bool | None = None


@dataclasses.dataclass
class FamilyOptions(LineOptions):
    """Options for an interval-based isopleth family.

    Setting `values` or `interval` fixes the member set explicitly and
    disables the zoom-adaptive selection ladder.
    """

    #: Explicit member values (diagram-native units).
    values: tuple[float, ...] | None = None

    #: Member value interval (diagram-native units).
    interval: float | None = None


@dataclasses.dataclass
class MixingRatioOptions(LineOptions):
    """Options for the humidity mixing-ratio family (values ladder only)."""

    #: Explicit member values in g/kg.
    values: tuple[float, ...] | None = None


@dataclasses.dataclass
class MoistAdiabatOptions(FamilyOptions):
    """Options for the moist-adiabat family."""

    #: Temperature (°C) below which moist adiabats are truncated.
    truncation: float | None = None


@dataclasses.dataclass
class DiagramOptions:
    """Diagram-wide options."""

    #: Default view extent applied to new tephigram axes.
    extent: Extent | None = None


@dataclasses.dataclass
class Config:
    """The ``tephpy.config`` runtime configuration singleton (spec §3.5).

    One typed section per isopleth family plus a diagram-wide section,
    e.g. ``config.isobars.interval`` or ``config.diagram.extent``. Use
    :meth:`context` for temporary overrides.
    """

    isotherms: FamilyOptions = dataclasses.field(default_factory=FamilyOptions)
    isobars: FamilyOptions = dataclasses.field(default_factory=FamilyOptions)
    dry_adiabats: FamilyOptions = dataclasses.field(default_factory=FamilyOptions)
    moist_adiabats: MoistAdiabatOptions = dataclasses.field(
        default_factory=MoistAdiabatOptions
    )
    mixing_ratios: MixingRatioOptions = dataclasses.field(
        default_factory=MixingRatioOptions
    )
    diagram: DiagramOptions = dataclasses.field(default_factory=DiagramOptions)

    @contextmanager
    def context(self, **overrides: Mapping[str, object]) -> Iterator[Config]:
        """Temporarily override configuration sections.

        Parameters
        ----------
        **overrides : mapping of str to object
            Section names mapped to ``{option: value}`` overrides, e.g.
            ``config.context(isobars={"interval": 25.0})``.

        Yields
        ------
        Config
            This configuration, with the overrides applied; prior values
            are restored on exit, including on error.

        Raises
        ------
        TypeError
            If a section or option name is unknown.
        """
        section_names = {field.name for field in dataclasses.fields(self)}
        snapshots: dict[str, object] = {}
        try:
            for section_name, options in overrides.items():
                if section_name not in section_names:
                    msg = f"unknown config section {section_name!r}"
                    raise TypeError(msg)
                section = getattr(self, section_name)
                valid = {field.name for field in dataclasses.fields(section)}
                snapshots[section_name] = dataclasses.replace(section)
                for key, value in options.items():
                    if key not in valid:
                        msg = (
                            f"unknown option {key!r} for config section "
                            f"{section_name!r}"
                        )
                        raise TypeError(msg)
                    setattr(section, key, value)
            yield self
        finally:
            for section_name, snapshot in snapshots.items():
                section = getattr(self, section_name)
                for field in dataclasses.fields(snapshot):  # type: ignore[arg-type]
                    setattr(section, field.name, getattr(snapshot, field.name))


#: The singleton read by the isopleth families (spec §3.5).
config: Final[Config] = Config()
```

Update `src/tephpy/__init__.py` — the imports and `__all__` become:

```python
from tephpy import plotting, transforms
from tephpy._config import config

__all__ = ["__version__", "config", "plotting", "transforms"]
```

(`tephpy._config` is a private module like `_constants` — sphinx-autoapi skips
it, consistent with the existing docs; the public name is `tephpy.config`.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_config.py tests/test_axes.py -q`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/_config.py src/tephpy/__init__.py tests/test_config.py tests/test_axes.py
pixi run lint
git commit -m "feat: add the tephpy.config runtime configuration layer"
```

---

## Task 3: Straight-family and isobar geometry builders

**Files:**
- Create: `src/tephpy/plotting/isopleths.py` (builders only; the artist arrives in Task 5)
- Test: `tests/test_isopleths.py`

**Interfaces:**
- Consumes: `transforms.xy_from_temperature_theta`, `theta_from_pressure_temperature`; Task 1 domains.
- Produces: `Member`, `isotherm_members`, `dry_adiabat_members`, `isobar_members` (signatures in the contract). Task 4 appends the curved builders to this file; Task 5 appends the artist.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_isopleths.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the isopleth geometry builders and family artist (spec §3.2/§7)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
import numpy as np
import pytest

from tephpy import transforms
from tephpy._constants import ISOPLETH_SAMPLES
from tephpy.plotting import isopleths


def _max_chord_deviation(xy):
    """Maximum perpendicular deviation of vertices from the end-to-end chord."""
    chord = xy[-1] - xy[0]
    chord = chord / np.linalg.norm(chord)
    relative = xy - xy[0]
    cross = relative[:, 0] * chord[1] - relative[:, 1] * chord[0]
    return float(np.max(np.abs(cross)))


def test_isotherm_members_are_straight():
    """Isotherms are exactly straight lines in the tephigram plane."""
    members = isopleths.isotherm_members([-40.0, 0.0, 40.0])
    assert [member.value for member in members] == [-40.0, 0.0, 40.0]
    for member in members:
        assert member.xy.shape == (ISOPLETH_SAMPLES, 2)
        assert member.xy.dtype == np.float64
        assert np.isfinite(member.xy).all()
        assert _max_chord_deviation(member.xy) < 1e-9


def test_dry_adiabat_members_are_straight():
    """Dry adiabats are exactly straight lines in the tephigram plane."""
    members = isopleths.dry_adiabat_members([0.0, 40.0, 100.0])
    assert [member.value for member in members] == [0.0, 40.0, 100.0]
    for member in members:
        assert member.xy.shape == (ISOPLETH_SAMPLES, 2)
        assert np.isfinite(member.xy).all()
        assert _max_chord_deviation(member.xy) < 1e-9


def test_isotherm_perpendicular_to_dry_adiabat():
    """The defining tephigram invariant holds for the built geometry."""
    (isotherm,) = isopleths.isotherm_members([10.0])
    (adiabat,) = isopleths.dry_adiabat_members([40.0])
    v1 = isotherm.xy[-1] - isotherm.xy[0]
    v2 = adiabat.xy[-1] - adiabat.xy[0]
    cosine = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    assert cosine == pytest.approx(0.0, abs=1e-12)


def test_isobar_members_satisfy_poisson():
    """Every isobar vertex maps back to its pressure via the transforms."""
    members = isopleths.isobar_members([1000.0, 850.0, 500.0])
    for member in members:
        t, theta = transforms.temperature_theta_from_xy(
            member.xy[:, 0], member.xy[:, 1]
        )
        pressure = transforms.pressure_from_temperature_theta(t, theta)
        np.testing.assert_allclose(pressure, member.value, rtol=1e-9)


@given(pressure=st.floats(min_value=60.0, max_value=1040.0))
def test_isobar_round_trip_property(pressure):
    """(p) -> isobar polyline -> (p) is the identity across the domain."""
    (member,) = isopleths.isobar_members([pressure])
    t, theta = transforms.temperature_theta_from_xy(member.xy[:, 0], member.xy[:, 1])
    back = transforms.pressure_from_temperature_theta(t, theta)
    np.testing.assert_allclose(back, pressure, rtol=1e-8)


def test_scalar_values_accepted():
    """Builders accept a bare scalar as well as a sequence."""
    (member,) = isopleths.isotherm_members(15.0)
    assert member.value == 15.0
```

This file (and later test files) uses private un-annotated helpers, so also
extend the tests entry in `pyproject.toml`'s
`[tool.ruff.lint.per-file-ignores]` (consistent with the existing ANN
ignores for tests):

```toml
"tests/*" = ["ANN001", "ANN201", "ANN202", "SLF001", "D103"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_isopleths.py -q`
Expected: FAIL — `ImportError: cannot import name 'isopleths'` (collection error is fine).

- [ ] **Step 3: Create the module with the straight builders**

Create `src/tephpy/plotting/isopleths.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Isopleth families for the tephigram projection (spec §3.2).

Each of the five background families — isotherms, isobars, dry adiabats,
moist adiabats, and humidity mixing-ratio lines — is drawn by one
zoom-aware :class:`IsoplethFamily` artist. Member polylines are precomputed
as bare numpy arrays over a generous physical domain (the ``_constants``
domains), mapped once into the tephigram x-y data space, and cached on the
artist; every draw selects the members appropriate to the current view and
zoom ladder and re-places the family's labels. The curved families delegate
their moist thermodynamics to MetPy behind function-local imports so that
``import tephpy`` stays light (spec §10 item 10). The design is derived
from the published tephigram construction with tephi as a corroborating
oracle, not ported from tephi (spec §3.1/§10 item 5).

Units are diagram-native (spec §5 exemption): pressure in hPa, temperatures
and potential temperatures in degrees Celsius, mixing ratios in g/kg.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._constants import (
    ISOPLETH_SAMPLES,
    TEMPERATURE_DOMAIN,
    THETA_DOMAIN,
)

__all__ = [
    "Member",
    "dry_adiabat_members",
    "isobar_members",
    "isotherm_members",
]


@dataclasses.dataclass(frozen=True)
class Member:
    """One isopleth polyline in tephigram x-y data space.

    ``value`` is the member's isopleth value in the family's native units
    (°C, hPa, or g/kg); ``xy`` is the ``(N, 2)`` float64 polyline.
    """

    value: float
    xy: npt.NDArray[np.float64]


def _member(
    value: float,
    temperature: npt.NDArray[np.float64],
    theta: npt.NDArray[np.float64],
) -> Member:
    """Map a (temperature, theta) polyline into a data-space member.

    Parameters
    ----------
    value : float
        The member's isopleth value in its native units.
    temperature : numpy.ndarray
        Vertex temperatures in degrees Celsius.
    theta : numpy.ndarray
        Vertex potential temperatures in degrees Celsius.

    Returns
    -------
    Member
        The member with its polyline in tephigram x-y data space.
    """
    x, y = transforms.xy_from_temperature_theta(temperature, theta)
    return Member(value=float(value), xy=np.column_stack([x, y]))


def isotherm_members(values: npt.ArrayLike) -> list[Member]:
    """Build isotherm polylines (lines of constant temperature).

    Isotherms are exactly straight in the tephigram plane; each member
    spans ``THETA_DOMAIN`` at its constant temperature.

    Parameters
    ----------
    values : array_like
        Member temperatures in degrees Celsius.

    Returns
    -------
    list of Member
        One member per value, in input order.
    """
    theta = np.linspace(THETA_DOMAIN[0], THETA_DOMAIN[1], ISOPLETH_SAMPLES)
    vals = np.atleast_1d(np.asarray(values, dtype=np.float64))
    return [_member(v, np.full_like(theta, v), theta) for v in vals]


def dry_adiabat_members(values: npt.ArrayLike) -> list[Member]:
    """Build dry-adiabat polylines (lines of constant potential temperature).

    Dry adiabats are exactly straight in the tephigram plane, perpendicular
    to the isotherms; each member spans ``TEMPERATURE_DOMAIN`` at its
    constant potential temperature.

    Parameters
    ----------
    values : array_like
        Member potential temperatures in degrees Celsius.

    Returns
    -------
    list of Member
        One member per value, in input order.
    """
    temperature = np.linspace(
        TEMPERATURE_DOMAIN[0], TEMPERATURE_DOMAIN[1], ISOPLETH_SAMPLES
    )
    vals = np.atleast_1d(np.asarray(values, dtype=np.float64))
    return [_member(v, temperature, np.full_like(temperature, v)) for v in vals]


def isobar_members(values: npt.ArrayLike) -> list[Member]:
    """Build isobar polylines (lines of constant pressure).

    Pressure is a derived curve on the tephigram, not an axis: each member
    traces Poisson's equation across ``TEMPERATURE_DOMAIN`` at its constant
    pressure.

    Parameters
    ----------
    values : array_like
        Member pressures in hPa.

    Returns
    -------
    list of Member
        One member per value, in input order.
    """
    temperature = np.linspace(
        TEMPERATURE_DOMAIN[0], TEMPERATURE_DOMAIN[1], ISOPLETH_SAMPLES
    )
    vals = np.atleast_1d(np.asarray(values, dtype=np.float64))
    members = []
    for v in vals:
        theta = transforms.theta_from_pressure_temperature(v, temperature)
        members.append(_member(v, temperature, theta))
    return members
```

(The module docstring intentionally describes the finished module including
`IsoplethFamily`; Tasks 4–5 complete it in place.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_isopleths.py -q`
Expected: PASS (hypothesis runs its default 100 examples for the property test).

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/plotting/isopleths.py tests/test_isopleths.py pyproject.toml
pixi run lint
git commit -m "feat: add the straight-family and isobar isopleth geometry builders"
```

---

## Task 4: Curved-family builders via MetPy

**Files:**
- Modify: `src/tephpy/plotting/isopleths.py` (append two builders; extend imports)
- Modify: `pyproject.toml` (no change needed — verify only; metpy is already a runtime dependency)
- Test: `tests/test_isopleths.py` (append)

**Interfaces:**
- Consumes: `metpy.calc.moist_lapse` (vectorized: pressure array + temperature array + `reference_pressure` kwarg → 2-D result; verified on metpy 1.7.1), `metpy.calc.dewpoint`, `metpy.calc.vapor_pressure`; `_constants` domains.
- Produces: `moist_adiabat_members(values, truncation=MOIST_ADIABAT_TRUNCATION)`, `mixing_ratio_members(values)`. Task 5's `FamilySpec` builders wrap exactly these.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_isopleths.py` (and add these imports to the top of the
file, keeping the block sorted):

```python
import subprocess
import sys

from metpy.calc import saturation_mixing_ratio, wet_bulb_potential_temperature
from metpy.units import units

from tephpy._constants import MIXING_RATIO_VALUES, MOIST_ADIABAT_TRUNCATION
```

then append the tests:

```python
def _pressure_temperature(member):
    """Recover (pressure, temperature) vertices from a member's x-y polyline."""
    t, theta = transforms.temperature_theta_from_xy(member.xy[:, 0], member.xy[:, 1])
    pressure = transforms.pressure_from_temperature_theta(t, theta)
    return pressure, t


def test_moist_adiabat_crosses_reference_at_its_value():
    """theta_w labels the curve: T at 1000 hPa equals the member value."""
    (member,) = isopleths.moist_adiabat_members([20.0])
    pressure, temperature = _pressure_temperature(member)
    index = int(np.argmin(np.abs(pressure - 1000.0)))
    assert pressure[index] == pytest.approx(1000.0, abs=1e-6)
    assert temperature[index] == pytest.approx(20.0, abs=1e-6)


def test_moist_adiabat_matches_metpy_wet_bulb_potential_temperature():
    """Cross-check the pseudoadiabat against MetPy's own theta-w function.

    Along the theta_w = 20 pseudoadiabat, the wet-bulb potential
    temperature of a saturated parcel recovers 20 °C. Tolerance 0.2 °C
    covers the documented formulation difference between moist_lapse
    (pseudoadiabat ODE integration) and wet_bulb_potential_temperature
    (Davies-Jones 2008 approximation); measured offsets on metpy 1.7.1
    were +0.02 to +0.15 °C.
    """
    (member,) = isopleths.moist_adiabat_members([20.0])
    pressure, temperature = _pressure_temperature(member)
    for target in (850.0, 700.0, 500.0, 300.0):
        index = int(np.argmin(np.abs(pressure - target)))
        t_q = units.Quantity(temperature[index], "degC")
        theta_w = wet_bulb_potential_temperature(
            units.Quantity(pressure[index], "hPa"), t_q, t_q
        ).m_as("degC")
        assert theta_w == pytest.approx(20.0, abs=0.2)


def test_moist_adiabat_truncation():
    """Curves stop at the truncation temperature (default and overridden)."""
    (member,) = isopleths.moist_adiabat_members([20.0])
    _, temperature = _pressure_temperature(member)
    assert temperature.min() >= MOIST_ADIABAT_TRUNCATION - 1e-6
    (shorter,) = isopleths.moist_adiabat_members([20.0], truncation=-30.0)
    assert shorter.xy.shape[0] < member.xy.shape[0]
    _, t_short = _pressure_temperature(shorter)
    assert t_short.min() >= -30.0 - 1e-6


def test_moist_adiabat_monotonic_cooling_with_height():
    """Along a pseudoadiabat, temperature falls as pressure falls."""
    (member,) = isopleths.moist_adiabat_members([20.0])
    pressure, temperature = _pressure_temperature(member)
    order = np.argsort(pressure)
    assert np.all(np.diff(temperature[order]) > 0)


def test_mixing_ratio_members_match_metpy_saturation_mixing_ratio():
    """Each vertex is the dew point where saturation mixing ratio equals w.

    Tolerance 1e-2: metpy's dewpoint (a Bolton-formula inversion) is not
    the exact inverse of the saturation vapour pressure inside
    saturation_mixing_ratio, and the mismatch grows at cold dew points —
    measured on metpy 1.7.1 at rel 6.5e-3 for w = 1 g/kg at the 50 hPa
    domain edge (and up to 5e-2 for w = 0.05, deliberately not asserted
    here).
    """
    members = isopleths.mixing_ratio_members([1.0, 10.0, 40.0])
    for member in members:
        pressure, dew = _pressure_temperature(member)
        w = saturation_mixing_ratio(
            units.Quantity(pressure, "hPa"), units.Quantity(dew, "degC")
        ).m_as("g/kg")
        np.testing.assert_allclose(w, member.value, rtol=1e-2)


def test_mixing_ratio_default_values_all_build():
    members = isopleths.mixing_ratio_members(MIXING_RATIO_VALUES)
    assert [member.value for member in members] == list(MIXING_RATIO_VALUES)
    for member in members:
        assert np.isfinite(member.xy).all()


def test_import_tephpy_does_not_import_metpy():
    """Importing tephpy must not import metpy (spec §3.2/§10 item 10).

    metpy loads on the first isopleth build instead. Run in a subprocess
    so the check is independent of what this session already imported.
    """
    code = "import sys, tephpy; raise SystemExit(1 if 'metpy' in sys.modules else 0)"
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603
```

(The `# noqa: S603` is required — ruff flags every `subprocess.run`; the
argv here is a fixed literal run through `sys.executable`.)

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_isopleths.py -q`
Expected: FAIL — `AttributeError: ... 'moist_adiabat_members'` on the new tests; Task 3 tests still pass.

- [ ] **Step 3: Append the implementations**

In `src/tephpy/plotting/isopleths.py`, extend the `from tephpy._constants
import (...)` block to (sorted):

```python
from tephpy._constants import (
    ISOPLETH_SAMPLES,
    MOIST_ADIABAT_PRESSURE_STEP,
    MOIST_ADIABAT_TRUNCATION,
    P_REF,
    PRESSURE_DOMAIN,
    TEMPERATURE_DOMAIN,
    THETA_DOMAIN,
)
```

extend `__all__` to:

```python
__all__ = [
    "Member",
    "dry_adiabat_members",
    "isobar_members",
    "isotherm_members",
    "mixing_ratio_members",
    "moist_adiabat_members",
]
```

and append:

```python
def moist_adiabat_members(
    values: npt.ArrayLike, truncation: float = MOIST_ADIABAT_TRUNCATION
) -> list[Member]:
    """Build moist-adiabat (pseudoadiabat) polylines.

    Each member is labelled by its wet-bulb potential temperature — the
    temperature where the curve crosses ``P_REF`` — and is integrated over
    ``PRESSURE_DOMAIN`` with :func:`metpy.calc.moist_lapse` in a single
    vectorized call, then truncated where the temperature falls below
    `truncation` (the curves converge onto the dry adiabats; Met Office
    Factsheet 13 convention). Members with fewer than two remaining
    vertices are dropped.

    Parameters
    ----------
    values : array_like
        Member wet-bulb potential temperatures in degrees Celsius.
    truncation : float, default: MOIST_ADIABAT_TRUNCATION
        Temperature (°C) below which the curves are truncated.

    Returns
    -------
    list of Member
        One member per surviving value, in input order.
    """
    # Function-local so `import tephpy` stays light (spec §3.2, §10 item 10).
    from metpy.calc import moist_lapse  # noqa: PLC0415
    from metpy.units import units  # noqa: PLC0415

    vals = np.atleast_1d(np.asarray(values, dtype=np.float64))
    lo, hi = PRESSURE_DOMAIN
    step = MOIST_ADIABAT_PRESSURE_STEP
    pressure = np.arange(hi, lo - step, -step)
    temperature = np.atleast_2d(
        moist_lapse(
            units.Quantity(pressure, "hPa"),
            units.Quantity(vals, "degC"),
            reference_pressure=units.Quantity(P_REF, "hPa"),
        ).m_as("degC")
    )
    members = []
    for value, row in zip(vals, temperature, strict=True):
        keep = row >= truncation
        if np.count_nonzero(keep) < 2:
            continue
        theta = transforms.theta_from_pressure_temperature(pressure[keep], row[keep])
        members.append(_member(value, row[keep], theta))
    return members


def mixing_ratio_members(values: npt.ArrayLike) -> list[Member]:
    """Build humidity mixing-ratio polylines (isohumes).

    For a mixing ratio ``w`` the member traces the dew-point temperature at
    which the saturation mixing ratio equals ``w``, sampled across
    ``PRESSURE_DOMAIN``: ``Td = dewpoint(vapor_pressure(p, w))`` via MetPy.

    Parameters
    ----------
    values : array_like
        Member humidity mixing ratios in g/kg.

    Returns
    -------
    list of Member
        One member per value, in input order.
    """
    # Function-local so `import tephpy` stays light (spec §3.2, §10 item 10).
    from metpy.calc import dewpoint, vapor_pressure  # noqa: PLC0415
    from metpy.units import units  # noqa: PLC0415

    vals = np.atleast_1d(np.asarray(values, dtype=np.float64))
    lo, hi = PRESSURE_DOMAIN
    pressure = np.linspace(lo, hi, ISOPLETH_SAMPLES)
    pressure_q = units.Quantity(pressure, "hPa")
    members = []
    for w in vals:
        dew = dewpoint(vapor_pressure(pressure_q, units.Quantity(w, "g/kg")))
        td = np.asarray(dew.m_as("degC"), dtype=np.float64)
        theta = transforms.theta_from_pressure_temperature(pressure, td)
        members.append(_member(w, td, theta))
    return members
```

Implementation notes (verified on metpy 1.7.1, all under
`filterwarnings = ["error"]` with **zero** warnings):
- One `moist_lapse` call handles the whole decreasing pressure array
  including the leg *below* the 1000 hPa reference (downward integration
  works); the temperature array vectorizes to a `(n_values, n_levels)`
  result. `np.atleast_2d` guards the single-value case.
- `moist_lapse` returns the same unit as its temperature input; `.m_as`
  strips to bare float64 before any numpy/matplotlib use.
- Timing: the full default family (101 curves × 201 levels) builds in
  ~25 ms once metpy is imported; the first build pays a one-time ~0.8 s
  metpy import.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_isopleths.py -q`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/plotting/isopleths.py tests/test_isopleths.py
pixi run lint
git commit -m "feat: add the MetPy-backed moist-adiabat and mixing-ratio builders"
```

---

## Task 5: The zoom-aware `IsoplethFamily` artist

**Files:**
- Modify: `src/tephpy/plotting/isopleths.py` (append the artist machinery; extend imports)
- Test: `tests/test_isopleths.py` (append)

**Interfaces:**
- Consumes: the five builders; Task 1 ladders/styling; Task 2 config sections (passed in — the artist never imports `_config`, keeping the dependency one-way).
- Produces: `ResolvedOptions`, `FamilySpec`, `_FAMILY_SPECS`, `IsoplethFamily(spec, section)` with `.configure(**kwargs)` and `.options`. Task 6 instantiates the five families from `_FAMILY_SPECS` inside `TephigramAxes.clear()`.

The matplotlib mechanics used here were all verified against matplotlib 3.11.1: a custom `Artist.draw(renderer)` runs on every canvas draw and sees the live `axes.viewLim`; internally managed children need `set_figure`, `set_transform(ax.transData)`, and `set_clip_box(ax.bbox)` (a `Text` without a figure crashes on draw); `ax.add_artist` never touches `dataLim`, so the families are excluded from autoscale automatically.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_isopleths.py` (add these imports at the top, keeping
the block sorted):

```python
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms

from tephpy._config import config
from tephpy._constants import ISOTHERM_COLOR
```

then append the tests:

```python
@pytest.fixture
def plain_axes():
    """Provide a stock Axes framed on the tephigram default view.

    IsoplethFamily only needs `axes.viewLim`/`transData`, so testing on a
    plain Axes proves the artist stands alone before it is wired into
    TephigramAxes.
    """
    fig, ax = plt.subplots()
    ax.set(xlim=(1591.0, 1902.0), ylim=(1671.0, 1822.0))
    yield ax
    plt.close(fig)


def _make_family(name):
    spec = isopleths._FAMILY_SPECS[name]
    return isopleths.IsoplethFamily(spec, getattr(config, name))


def test_family_specs_cover_the_five_families():
    assert set(isopleths._FAMILY_SPECS) == {
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
    }


def test_family_builds_lazily_and_draws(plain_axes):
    family = _make_family("isobars")
    plain_axes.add_artist(family)
    assert family._members is None
    plain_axes.figure.canvas.draw()
    assert family._members is not None
    assert len(family._lines.get_segments()) > 0


def test_every_family_draws_on_the_default_view(plain_axes):
    for name in isopleths._FAMILY_SPECS:
        plain_axes.add_artist(_make_family(name))
    plain_axes.figure.canvas.draw()
    for artist in plain_axes.get_children():
        if isinstance(artist, isopleths.IsoplethFamily):
            assert len(artist._lines.get_segments()) > 0


def test_family_does_not_participate_in_autoscale(plain_axes):
    family = _make_family("isobars")
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    assert not np.isfinite(plain_axes.dataLim.x0)


def test_isobar_zoom_ladder_masks():
    """The ladder picks 100/50/20/10 hPa members by view width, value-anchored."""
    family = _make_family("isobars")
    family._build()
    wide = family._member_values[family._zoom_mask(600.0)]
    mid = family._member_values[family._zoom_mask(300.0)]
    fine = family._member_values[family._zoom_mask(100.0)]
    finest = family._member_values[family._zoom_mask(50.0)]
    np.testing.assert_array_equal(wide, np.arange(100.0, 1001.0, 100.0))
    np.testing.assert_array_equal(mid, np.arange(50.0, 1051.0, 50.0))
    np.testing.assert_array_equal(fine, np.arange(60.0, 1041.0, 20.0))
    np.testing.assert_array_equal(finest, np.arange(50.0, 1051.0, 10.0))


def test_mixing_ratio_stride_masks():
    """List families stride from index 0, so panning never shifts members."""
    family = _make_family("mixing_ratios")
    family._build()
    wide = family._member_values[family._zoom_mask(600.0)]
    fine = family._member_values[family._zoom_mask(100.0)]
    np.testing.assert_allclose(wide, MIXING_RATIO_VALUES[::4])
    np.testing.assert_allclose(fine, MIXING_RATIO_VALUES)


def test_view_mask_selects_overlapping_bboxes():
    family = _make_family("isotherms")
    family._member_values = np.array([0.0, 1.0])
    family._member_bboxes = np.array([[0.0, 0.0, 1.0, 1.0], [5.0, 5.0, 6.0, 6.0]])
    view = mtransforms.Bbox.from_extents(0.5, 0.5, 2.0, 2.0)
    np.testing.assert_array_equal(family._view_mask(view), [True, False])


def test_zoom_changes_the_drawn_subset(plain_axes):
    """Zooming in switches the isobar ladder from 50 hPa to 20 hPa members."""
    family = _make_family("isobars")
    plain_axes.add_artist(family)
    fig = plain_axes.figure
    fig.canvas.draw()
    wide_count = len(family._lines.get_segments())
    plain_axes.set(xlim=(1700.0, 1800.0), ylim=(1700.0, 1800.0))
    fig.canvas.draw()
    fine_count = len(family._lines.get_segments())
    assert fine_count > 0
    assert fine_count != wide_count


def test_configure_values_override_disables_ladder(plain_axes):
    family = _make_family("isotherms")
    plain_axes.add_artist(family)
    family.configure(values=(0.0, 10.0), color="red")
    plain_axes.figure.canvas.draw()
    assert family.options.color == "red"
    assert family.options.values == (0.0, 10.0)
    assert len(family._lines.get_segments()) <= 2


def test_configure_unknown_option_raises():
    with pytest.raises(TypeError, match="unknown option"):
        _make_family("isotherms").configure(bogus=1)
    with pytest.raises(TypeError, match="unknown option"):
        _make_family("mixing_ratios").configure(interval=5.0)
    with pytest.raises(TypeError, match="unknown option"):
        _make_family("isotherms").configure(truncation=-30.0)


def test_configure_none_resets_override():
    family = _make_family("isotherms")
    family.configure(color="red")
    assert family.options.color == "red"
    family.configure(color=None)
    assert family.options.color == ISOTHERM_COLOR


def test_config_precedence_and_snapshot_semantics():
    """Verify kwargs > config > constants and the snapshot semantics."""
    with config.context(isotherms={"color": "purple", "interval": 20.0}):
        family = _make_family("isotherms")
        assert family.options.color == "purple"
        assert family.options.interval == 20.0
        family.configure(color="black")
        assert family.options.color == "black"
        assert family.options.interval == 20.0
    # Exiting the context must not restyle the existing snapshot (spec §3.5).
    assert family.options.interval == 20.0
    assert family.options.color == "black"


def test_visible_option_maps_to_artist_visibility():
    family = _make_family("isobars")
    assert family.get_visible()
    family.configure(visible=False)
    assert not family.get_visible()
    assert family.options.visible is False


def test_labels_drawn_and_upright(plain_axes):
    family = _make_family("isobars")
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    labelled = [text for text in family._texts if text.get_text()]
    assert labelled
    for text in labelled:
        rotation = text.get_rotation()  # normalised to [0, 360)
        assert rotation <= 90.0 or rotation >= 270.0


def test_labels_disabled(plain_axes):
    family = _make_family("isobars")
    family.configure(labels=False)
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    assert family._texts == []


def test_moist_adiabat_truncation_configurable():
    family = _make_family("moist_adiabats")
    family.configure(truncation=-30.0)
    assert family.options.truncation == -30.0
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_isopleths.py -q`
Expected: FAIL — `AttributeError: ... '_FAMILY_SPECS'`; Tasks 3–4 tests still pass.

- [ ] **Step 3: Append the artist machinery**

In `src/tephpy/plotting/isopleths.py`, replace the import section (everything
between the module docstring and `__all__`) with the final version:

```python
from __future__ import annotations

import dataclasses
import math
from typing import TYPE_CHECKING, Final, cast

from matplotlib import artist as martist
from matplotlib.collections import LineCollection
from matplotlib.text import Text
import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._constants import (
    DRY_ADIABAT_COLOR,
    DRY_ADIABAT_STEPS,
    DRY_ADIABAT_ZORDER,
    ISOBAR_COLOR,
    ISOBAR_STEPS,
    ISOBAR_ZORDER,
    ISOPLETH_ALPHA,
    ISOPLETH_LINEWIDTH,
    ISOPLETH_SAMPLES,
    ISOTHERM_COLOR,
    ISOTHERM_STEPS,
    ISOTHERM_ZORDER,
    LABEL_BOX_ALPHA,
    LABEL_BOX_COLOR,
    LABEL_BOXSTYLE,
    LABEL_FONTSIZE,
    MIXING_RATIO_COLOR,
    MIXING_RATIO_STRIDES,
    MIXING_RATIO_VALUES,
    MIXING_RATIO_ZORDER,
    MOIST_ADIABAT_COLOR,
    MOIST_ADIABAT_DOMAIN,
    MOIST_ADIABAT_PRESSURE_STEP,
    MOIST_ADIABAT_STEPS,
    MOIST_ADIABAT_TRUNCATION,
    MOIST_ADIABAT_ZORDER,
    P_REF,
    PRESSURE_DOMAIN,
    TEMPERATURE_DOMAIN,
    THETA_DOMAIN,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import SupportsFloat

    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    import matplotlib.transforms as mtransforms

__all__ = [
    "FamilySpec",
    "IsoplethFamily",
    "Member",
    "ResolvedOptions",
    "dry_adiabat_members",
    "isobar_members",
    "isotherm_members",
    "mixing_ratio_members",
    "moist_adiabat_members",
]

#: Options that require rebuilding the cached member geometry when changed.
_GEOMETRY_KEYS: Final[frozenset[str]] = frozenset({"values", "interval", "truncation"})

#: Style and visibility options shared by every family.
_STYLE_KEYS: Final[frozenset[str]] = frozenset(
    {"color", "linewidth", "alpha", "labels", "visible"}
)

#: Options accepted by the interval-based families.
_INTERVAL_KEYS: Final[frozenset[str]] = _STYLE_KEYS | {"values", "interval"}
```

then append after `mixing_ratio_members` — this exact code passes ruff
(`ALL` + format), mypy strict, and numpydoc-validation, and was smoke-tested
end to end (verified 2026-07-24):

```python
@dataclasses.dataclass(frozen=True)
class ResolvedOptions:
    """A family's fully resolved settings snapshot.

    Resolution precedence: accessor kwargs > ``tephpy.config`` >
    ``_constants`` (spec §3.5). ``values``/``interval`` of ``None`` mean the
    zoom-adaptive default ladder is in force.
    """

    values: tuple[float, ...] | None
    interval: float | None
    truncation: float | None
    color: str
    linewidth: float
    alpha: float
    labels: bool
    visible: bool


@dataclasses.dataclass(frozen=True)
class FamilySpec:
    """Static wiring of one isopleth family: builder plus conventions.

    Exactly one of (``domain`` + ``steps``) for interval families or
    (``values`` + ``strides``) for list families is set.
    """

    name: str
    builder: Callable[[npt.NDArray[np.float64], float | None], list[Member]]
    allowed: frozenset[str]
    color: str
    zorder: float
    domain: tuple[float, float] | None = None
    steps: tuple[tuple[float, float], ...] | None = None
    strides: tuple[tuple[float, int], ...] | None = None
    values: tuple[float, ...] | None = None
    truncation: float | None = None


def _build_isotherms(
    values: npt.NDArray[np.float64], _truncation: float | None
) -> list[Member]:
    """Adapt :func:`isotherm_members` to the uniform builder signature.

    Parameters
    ----------
    values : numpy.ndarray
        Member temperatures in degrees Celsius.
    _truncation : float or None
        Ignored; only meaningful for the moist adiabats.

    Returns
    -------
    list of Member
        The family members.
    """
    return isotherm_members(values)


def _build_dry_adiabats(
    values: npt.NDArray[np.float64], _truncation: float | None
) -> list[Member]:
    """Adapt :func:`dry_adiabat_members` to the uniform builder signature.

    Parameters
    ----------
    values : numpy.ndarray
        Member potential temperatures in degrees Celsius.
    _truncation : float or None
        Ignored; only meaningful for the moist adiabats.

    Returns
    -------
    list of Member
        The family members.
    """
    return dry_adiabat_members(values)


def _build_isobars(
    values: npt.NDArray[np.float64], _truncation: float | None
) -> list[Member]:
    """Adapt :func:`isobar_members` to the uniform builder signature.

    Parameters
    ----------
    values : numpy.ndarray
        Member pressures in hPa.
    _truncation : float or None
        Ignored; only meaningful for the moist adiabats.

    Returns
    -------
    list of Member
        The family members.
    """
    return isobar_members(values)


def _build_moist_adiabats(
    values: npt.NDArray[np.float64], truncation: float | None
) -> list[Member]:
    """Adapt :func:`moist_adiabat_members` to the uniform builder signature.

    Parameters
    ----------
    values : numpy.ndarray
        Member wet-bulb potential temperatures in degrees Celsius.
    truncation : float or None
        Truncation temperature in degrees Celsius; ``None`` selects the
        ``MOIST_ADIABAT_TRUNCATION`` convention.

    Returns
    -------
    list of Member
        The family members.
    """
    resolved = MOIST_ADIABAT_TRUNCATION if truncation is None else truncation
    return moist_adiabat_members(values, resolved)


def _build_mixing_ratios(
    values: npt.NDArray[np.float64], _truncation: float | None
) -> list[Member]:
    """Adapt :func:`mixing_ratio_members` to the uniform builder signature.

    Parameters
    ----------
    values : numpy.ndarray
        Member humidity mixing ratios in g/kg.
    _truncation : float or None
        Ignored; only meaningful for the moist adiabats.

    Returns
    -------
    list of Member
        The family members.
    """
    return mixing_ratio_members(values)


#: The five families, keyed by accessor name (spec §10 item 6).
_FAMILY_SPECS: Final[dict[str, FamilySpec]] = {
    "isotherms": FamilySpec(
        name="isotherms",
        builder=_build_isotherms,
        allowed=_INTERVAL_KEYS,
        color=ISOTHERM_COLOR,
        zorder=ISOTHERM_ZORDER,
        domain=TEMPERATURE_DOMAIN,
        steps=ISOTHERM_STEPS,
    ),
    "dry_adiabats": FamilySpec(
        name="dry_adiabats",
        builder=_build_dry_adiabats,
        allowed=_INTERVAL_KEYS,
        color=DRY_ADIABAT_COLOR,
        zorder=DRY_ADIABAT_ZORDER,
        domain=THETA_DOMAIN,
        steps=DRY_ADIABAT_STEPS,
    ),
    "isobars": FamilySpec(
        name="isobars",
        builder=_build_isobars,
        allowed=_INTERVAL_KEYS,
        color=ISOBAR_COLOR,
        zorder=ISOBAR_ZORDER,
        domain=PRESSURE_DOMAIN,
        steps=ISOBAR_STEPS,
    ),
    "moist_adiabats": FamilySpec(
        name="moist_adiabats",
        builder=_build_moist_adiabats,
        allowed=_INTERVAL_KEYS | {"truncation"},
        color=MOIST_ADIABAT_COLOR,
        zorder=MOIST_ADIABAT_ZORDER,
        domain=MOIST_ADIABAT_DOMAIN,
        steps=MOIST_ADIABAT_STEPS,
        truncation=MOIST_ADIABAT_TRUNCATION,
    ),
    "mixing_ratios": FamilySpec(
        name="mixing_ratios",
        builder=_build_mixing_ratios,
        allowed=_STYLE_KEYS | {"values"},
        color=MIXING_RATIO_COLOR,
        zorder=MIXING_RATIO_ZORDER,
        strides=MIXING_RATIO_STRIDES,
        values=MIXING_RATIO_VALUES,
    ),
}


class IsoplethFamily(martist.Artist):
    """One zoom-aware background isopleth family (spec §3.2).

    Member polylines are built lazily on first draw and cached; each draw
    clips the cache to the current view rectangle, selects the members
    appropriate to the zoom level via the family's convention ladder, and
    re-places the member labels. Settings resolve as accessor kwargs >
    ``tephpy.config`` > ``_constants``, read when the family is created or
    reconfigured (spec §3.5); explicit ``values`` or ``interval`` fixes the
    member set and disables the zoom ladder.

    Parameters
    ----------
    spec : FamilySpec
        The family's static wiring (builder plus convention defaults).
    section : object
        The family's ``tephpy.config`` section, read at creation and on
        :meth:`configure`.
    """

    def __init__(self, spec: FamilySpec, section: object) -> None:
        """Initialise the family and snapshot its resolved options.

        Parameters
        ----------
        spec : FamilySpec
            The family's static wiring (builder plus convention defaults).
        section : object
            The family's ``tephpy.config`` section, read at creation and
            on :meth:`configure`.
        """
        super().__init__()
        self._spec = spec
        self._section = section
        self._overrides: dict[str, object] = {}
        self._members: list[Member] | None = None
        self._member_values: npt.NDArray[np.float64] = np.empty(0)
        self._member_bboxes: npt.NDArray[np.float64] = np.empty((0, 4))
        self._zoom_adaptive = True
        self._lines = LineCollection([])
        self._texts: list[Text] = []
        self._options = self._resolve()
        self.set_zorder(spec.zorder)
        self.set_visible(self._options.visible)

    @property
    def options(self) -> ResolvedOptions:
        """The resolved settings snapshot currently in force.

        Returns
        -------
        ResolvedOptions
            The snapshot (accessor kwargs > ``tephpy.config`` >
            ``_constants``) taken at creation or the last
            :meth:`configure`.
        """
        return self._options

    def configure(self, **kwargs: object) -> None:
        """Reconfigure the family (the accessor-kwargs precedence tier).

        Re-reads ``tephpy.config`` now (spec §3.5 semantics). Passing
        ``None`` for an option removes any prior override so the value
        falls back to ``tephpy.config`` and then ``_constants``.

        Parameters
        ----------
        **kwargs : object
            Options to override; the family's accessor documents the
            accepted names.

        Raises
        ------
        TypeError
            If an option name is unknown for this family.
        """
        unknown = set(kwargs) - self._spec.allowed
        if unknown:
            msg = f"unknown option(s) {sorted(unknown)!r} for {self._spec.name!r}"
            raise TypeError(msg)
        for key, value in kwargs.items():
            if value is None:
                self._overrides.pop(key, None)
            else:
                self._overrides[key] = value
        self._options = self._resolve()
        self.set_visible(self._options.visible)
        if _GEOMETRY_KEYS & set(kwargs):
            self._members = None
        self.stale = True

    def set_figure(self, fig: Figure | SubFigure) -> None:
        """Propagate the owning figure to the managed child artists.

        Parameters
        ----------
        fig : matplotlib.figure.Figure or matplotlib.figure.SubFigure
            The figure the family belongs to.
        """
        super().set_figure(fig)
        self._lines.set_figure(fig)
        for text in self._texts:
            text.set_figure(fig)

    @martist.allow_rasterization  # type: ignore[untyped-decorator]
    def draw(self, renderer: RendererBase) -> None:
        """Draw the members visible in the current view.

        Parameters
        ----------
        renderer : matplotlib.backend_bases.RendererBase
            The active renderer.
        """
        if not self.get_visible():
            return
        axes = self.axes
        if axes is None:
            return
        if self._members is None:
            self._build()
        members = self._members if self._members is not None else []
        opts = self._options
        view = axes.viewLim
        mask = self._zoom_mask(view.width) & self._view_mask(view)
        selected = [m for m, keep in zip(members, mask, strict=True) if keep]
        renderer.open_group("isopleth-family", gid=self.get_gid())
        lines = self._lines
        lines.set_segments([m.xy for m in selected])
        lines.set_color(opts.color)
        lines.set_linewidth(opts.linewidth)
        lines.set_alpha(opts.alpha)
        lines.set_transform(axes.transData)
        lines.set_clip_box(axes.bbox)
        lines.draw(renderer)
        if opts.labels:
            self._draw_labels(renderer, selected)
        renderer.close_group("isopleth-family")
        self.stale = False

    def _pick(self, key: str) -> object:
        """Return the highest-precedence non-``None`` value for an option.

        Parameters
        ----------
        key : str
            The option name.

        Returns
        -------
        object
            The override or ``tephpy.config`` value, or ``None`` to fall
            back to the ``_constants`` convention.
        """
        value: object = self._overrides.get(key)
        if value is None:
            value = getattr(self._section, key, None)
        return value

    def _resolve(self) -> ResolvedOptions:
        """Snapshot the resolved options (kwargs > config > constants).

        Returns
        -------
        ResolvedOptions
            The frozen snapshot the family builds and draws from.
        """
        spec = self._spec
        pick = self._pick
        raw_values = pick("values")
        values: tuple[float, ...] | None = None
        if raw_values is not None:
            values = tuple(
                float(v) for v in cast("Iterable[SupportsFloat]", raw_values)
            )
        raw_interval = pick("interval")
        interval = (
            None if raw_interval is None else float(cast("SupportsFloat", raw_interval))
        )
        raw_truncation = pick("truncation")
        truncation = (
            spec.truncation
            if raw_truncation is None
            else float(cast("SupportsFloat", raw_truncation))
        )
        raw_color = pick("color")
        raw_linewidth = pick("linewidth")
        raw_alpha = pick("alpha")
        raw_labels = pick("labels")
        raw_visible = pick("visible")
        return ResolvedOptions(
            values=values,
            interval=interval,
            truncation=truncation,
            color=spec.color if raw_color is None else str(raw_color),
            linewidth=(
                ISOPLETH_LINEWIDTH
                if raw_linewidth is None
                else float(cast("SupportsFloat", raw_linewidth))
            ),
            alpha=(
                ISOPLETH_ALPHA
                if raw_alpha is None
                else float(cast("SupportsFloat", raw_alpha))
            ),
            labels=True if raw_labels is None else bool(raw_labels),
            visible=True if raw_visible is None else bool(raw_visible),
        )

    def _candidate_values(self) -> npt.NDArray[np.float64]:
        """Return the member values to build, at the finest granularity.

        Returns
        -------
        numpy.ndarray
            Explicit ``values`` if resolved, else interval multiples over
            the family domain (the finest ladder step by default), else
            the family's canonical values list.
        """
        opts = self._options
        spec = self._spec
        if opts.values is not None:
            return np.asarray(opts.values, dtype=np.float64)
        if spec.steps is not None and spec.domain is not None:
            interval = opts.interval if opts.interval is not None else spec.steps[-1][1]
            lo, hi = spec.domain
            start = math.ceil(lo / interval) * interval
            return np.arange(start, hi + 0.5 * interval, interval)
        values = spec.values if spec.values is not None else ()
        return np.asarray(values, dtype=np.float64)

    def _build(self) -> None:
        """Build and cache the member polylines and their bounding boxes."""
        opts = self._options
        members = self._spec.builder(self._candidate_values(), opts.truncation)
        self._members = members
        self._member_values = np.array(
            [member.value for member in members], dtype=np.float64
        )
        if members:
            self._member_bboxes = np.array(
                [
                    (
                        member.xy[:, 0].min(),
                        member.xy[:, 1].min(),
                        member.xy[:, 0].max(),
                        member.xy[:, 1].max(),
                    )
                    for member in members
                ],
                dtype=np.float64,
            )
        else:
            self._member_bboxes = np.empty((0, 4))
        self._zoom_adaptive = opts.values is None and opts.interval is None

    def _zoom_mask(self, width: float) -> npt.NDArray[np.bool_]:
        """Select members for the zoom level via the convention ladder.

        Parameters
        ----------
        width : float
            The current view width in data-space x units.

        Returns
        -------
        numpy.ndarray
            Boolean mask over the cached members.
        """
        count = self._member_values.size
        if not self._zoom_adaptive:
            return np.ones(count, dtype=bool)
        spec = self._spec
        if spec.steps is not None:
            step = spec.steps[-1][1]
            for min_width, ladder_step in spec.steps:
                if width >= min_width:
                    step = ladder_step
                    break
            ratio = self._member_values / step
            return np.asarray(np.abs(ratio - np.round(ratio)) < 1e-6)
        stride = 1
        if spec.strides is not None:
            for min_width, ladder_stride in spec.strides:
                if width >= min_width:
                    stride = ladder_stride
                    break
        return np.asarray((np.arange(count) % stride) == 0)

    def _view_mask(self, view: mtransforms.Bbox) -> npt.NDArray[np.bool_]:
        """Select members whose bounding box overlaps the view rectangle.

        Parameters
        ----------
        view : matplotlib.transforms.Bbox
            The current data-space view rectangle.

        Returns
        -------
        numpy.ndarray
            Boolean mask over the cached members.
        """
        boxes = self._member_bboxes
        if boxes.size == 0:
            return np.zeros(0, dtype=bool)
        return np.asarray(
            (boxes[:, 0] <= view.x1)
            & (boxes[:, 2] >= view.x0)
            & (boxes[:, 1] <= view.y1)
            & (boxes[:, 3] >= view.y0)
        )

    def _make_text(self) -> Text:
        """Create one pooled label with the family label conventions.

        Returns
        -------
        matplotlib.text.Text
            An unattached label owned and drawn by the family.
        """
        text = Text(
            0.0,
            0.0,
            "",
            ha="center",
            va="center",
            fontsize=LABEL_FONTSIZE,
            rotation_mode="anchor",
            bbox={
                "boxstyle": LABEL_BOXSTYLE,
                "facecolor": LABEL_BOX_COLOR,
                "edgecolor": LABEL_BOX_COLOR,
                "alpha": LABEL_BOX_ALPHA,
            },
        )
        figure = self.get_figure(root=False)
        if figure is not None:
            text.set_figure(figure)
        return text

    def _draw_labels(self, renderer: RendererBase, selected: list[Member]) -> None:
        """Place and draw one label per selected member.

        The label anchors at the middle in-view vertex, rotated to the
        local line direction in screen space and folded upright.

        Parameters
        ----------
        renderer : matplotlib.backend_bases.RendererBase
            The active renderer.
        selected : list of Member
            The members drawn this pass.
        """
        axes = self.axes
        if axes is None:
            return
        opts = self._options
        view = axes.viewLim
        while len(self._texts) < len(selected):
            self._texts.append(self._make_text())
        for member, text in zip(selected, self._texts, strict=False):
            xy = member.xy
            inside = (
                (xy[:, 0] >= view.x0)
                & (xy[:, 0] <= view.x1)
                & (xy[:, 1] >= view.y0)
                & (xy[:, 1] <= view.y1)
            )
            indices = np.flatnonzero(inside)
            if indices.size < 2:
                continue
            mid = int(indices[indices.size // 2])
            lo = max(mid - 1, 0)
            hi = min(mid + 1, xy.shape[0] - 1)
            display = axes.transData.transform(xy[[lo, hi]])
            angle = math.degrees(
                math.atan2(display[1, 1] - display[0, 1], display[1, 0] - display[0, 0])
            )
            angle = (angle + 90.0) % 180.0 - 90.0
            text.set_position((float(xy[mid, 0]), float(xy[mid, 1])))
            text.set_text(f"{member.value:g}")
            text.set_color(opts.color)
            text.set_rotation(angle)
            text.set_transform(axes.transData)
            text.set_clip_box(axes.bbox)
            text.set_clip_on(True)
            text.draw(renderer)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_isopleths.py -q`
Expected: PASS.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/plotting/isopleths.py tests/test_isopleths.py
pixi run lint
git commit -m "feat: add the zoom-aware IsoplethFamily artist"
```

---

## Task 6: `TephigramAxes` integration — families on by default, accessors, `set_extent`

**Files:**
- Modify: `src/tephpy/plotting/axes.py`
- Test: `tests/test_axes.py` (append)

**Interfaces:**
- Consumes: `_FAMILY_SPECS`, `IsoplethFamily` (Task 5); `config` (Task 2); `DEFAULT_EXTENT` (Task 1).
- Produces: `TephigramAxes.clear()`, `set_extent(extent)`, and the five accessors (contract above). Plan 4's `plot_profile` composes `ax.tephigram_transform + ax.transData` (unchanged); Plans 5/6 consume the layout contract documented in the module docstring.

Key mechanics (verified against matplotlib 3.11.1 source and by execution):
`Axes.__init__` calls `self.clear()` during construction, and a user-facing
`ax.clear()` removes **all** children unconditionally — so the projection
pattern (exactly what `PolarAxes` does) is to override `clear()` (never
`cla()`, which triggers a `PendingDeprecationWarning`), call `super().clear()`,
then re-establish all projection-owned state: transform, aspect, hidden axes,
families, and default extent. The `__init__` override and
`_set_default_extent` are **deleted** — `clear()` replaces both. The five
accessors carry `# noqa: PLR0913` (verified needed): their wide keyword-only
signatures deliberately mirror the config sections and must not be
restructured to appease the argument-count rule.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_axes.py` (add these imports at the top, keeping the
block sorted):

```python
from tephpy._config import config
from tephpy._constants import DEFAULT_EXTENT
from tephpy.plotting.isopleths import IsoplethFamily
```

then append the tests:

```python
FAMILY_NAMES = (
    "isotherms",
    "isobars",
    "dry_adiabats",
    "moist_adiabats",
    "mixing_ratios",
)


def _expected_limits(extent):
    """Map extent corners through the transforms to expected x/y limits."""
    (p0, t0), (p1, t1) = extent
    thetas = transforms.theta_from_pressure_temperature(
        np.array([p0, p1]), np.array([t0, t1])
    )
    x, y = transforms.xy_from_temperature_theta(np.array([t0, t1]), thetas)
    return (float(np.min(x)), float(np.max(x))), (float(np.min(y)), float(np.max(y)))


def test_families_present_and_on_by_default(tephigram_axes):
    families = [
        artist
        for artist in tephigram_axes.get_children()
        if isinstance(artist, IsoplethFamily)
    ]
    assert len(families) == 5
    for name in FAMILY_NAMES:
        family = getattr(tephigram_axes, name)()
        assert isinstance(family, IsoplethFamily)
        assert family in families
        assert family.get_visible()


def test_default_draw_populates_every_family(tephigram_axes):
    tephigram_axes.figure.canvas.draw()
    for name in FAMILY_NAMES:
        family = getattr(tephigram_axes, name)()
        assert len(family._lines.get_segments()) > 0


def test_accessors_reconfigure_and_return(tephigram_axes):
    family = tephigram_axes.isobars(color="black", labels=False)
    assert family is tephigram_axes.isobars()
    assert family.options.color == "black"
    assert family.options.labels is False


def test_accessor_visibility_toggle(tephigram_axes):
    family = tephigram_axes.mixing_ratios(visible=False)
    assert not family.get_visible()


def test_accessor_rejects_unknown_kwarg(tephigram_axes):
    with pytest.raises(TypeError):
        tephigram_axes.isotherms(steps=3)
    with pytest.raises(TypeError):
        tephigram_axes.mixing_ratios(interval=5.0)


def test_moist_adiabats_truncation_kwarg(tephigram_axes):
    family = tephigram_axes.moist_adiabats(truncation=-30.0)
    assert family.options.truncation == -30.0


def test_default_extent_applied(tephigram_axes):
    (x0, x1), (y0, y1) = _expected_limits(DEFAULT_EXTENT)
    assert tephigram_axes.get_xlim() == pytest.approx((x0, x1))
    assert tephigram_axes.get_ylim() == pytest.approx((y0, y1))


def test_set_extent_moves_the_view(tephigram_axes):
    extent = ((1050.0, -10.0), (700.0, 30.0))
    tephigram_axes.set_extent(extent)
    (x0, x1), (y0, y1) = _expected_limits(extent)
    assert tephigram_axes.get_xlim() == pytest.approx((x0, x1))
    assert tephigram_axes.get_ylim() == pytest.approx((y0, y1))


def test_set_extent_disables_autoscale_so_overlays_do_not_drift(tephigram_axes):
    tephigram_axes.set_extent(DEFAULT_EXTENT)
    before = (tephigram_axes.get_xlim(), tephigram_axes.get_ylim())
    assert not tephigram_axes.get_autoscale_on()
    tephigram_axes.plot(
        [0.0, 200.0],
        [10.0, 400.0],
        transform=tephigram_axes.tephigram_transform + tephigram_axes.transData,
    )
    tephigram_axes.figure.canvas.draw()
    assert (tephigram_axes.get_xlim(), tephigram_axes.get_ylim()) == before


def test_set_extent_rejects_unphysical_corners(tephigram_axes):
    with pytest.raises(ValueError, match="physical"):
        tephigram_axes.set_extent(((0.0, -40.0), (200.0, 40.0)))
    with pytest.raises(ValueError, match="degenerate"):
        tephigram_axes.set_extent(((850.0, 10.0), (850.0, 10.0)))


def test_clear_restores_projection_defaults(tephigram_axes):
    old_family = tephigram_axes.isobars()
    tephigram_axes.plot([1700.0, 1750.0], [1700.0, 1750.0])
    tephigram_axes.clear()
    assert old_family.axes is None
    fresh = [
        artist
        for artist in tephigram_axes.get_children()
        if isinstance(artist, IsoplethFamily)
    ]
    assert len(fresh) == 5
    assert old_family not in fresh
    assert not tephigram_axes.lines
    assert tephigram_axes.get_aspect() == 1.0
    assert not tephigram_axes.xaxis.get_visible()
    assert not tephigram_axes.yaxis.get_visible()
    (x0, x1), (y0, y1) = _expected_limits(DEFAULT_EXTENT)
    assert tephigram_axes.get_xlim() == pytest.approx((x0, x1))
    assert tephigram_axes.get_ylim() == pytest.approx((y0, y1))


def test_config_diagram_extent_honoured_at_creation():
    extent = ((1000.0, -20.0), (500.0, 20.0))
    with config.context(diagram={"extent": extent}):
        fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        (x0, x1), (y0, y1) = _expected_limits(extent)
        assert ax.get_xlim() == pytest.approx((x0, x1))
        assert ax.get_ylim() == pytest.approx((y0, y1))
    finally:
        plt.close(fig)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_axes.py -q`
Expected: FAIL — `AttributeError: 'TephigramAxes' object has no attribute 'isobars'` (and friends); the Plan 2 tests still pass.

- [ ] **Step 3: Rework `TephigramAxes`**

In `src/tephpy/plotting/axes.py`:

**(a)** Replace the module docstring with:

```python
"""The tephigram matplotlib projection.

``TephigramAxes`` (registered as the ``"tephigram"`` projection) uses the
native rotated x-y plane as its data space, with the temperature/theta
mapping exposed as an invertible matplotlib transform and the five
background isopleth families drawn by default as zoom-aware artists
(spec §3.2).

Side-of-axes layout contract (spec §10 item 7 — decided here, built by the
consuming plans): panels beside the diagram are appended with
``mpl_toolkits.axes_grid1``'s axes divider, which tracks the equal-aspect
box height — right side, inside-out: the wind-barb gutter (Plan 6), then
the indices panel (Plan 5). Panel widths join ``_constants`` with their
plans. No layout code ships in this release.
"""
```

**(b)** Replace the import block (below `from __future__ import annotations`)
with:

```python
from typing import TYPE_CHECKING

from matplotlib.axes import Axes
from matplotlib.projections import register_projection
import matplotlib.transforms as mtransforms
import numpy as np
import numpy.typing as npt

from tephpy import transforms
from tephpy._config import config
from tephpy._constants import DEFAULT_EXTENT
from tephpy.plotting.isopleths import _FAMILY_SPECS, IsoplethFamily

if TYPE_CHECKING:
    from collections.abc import Iterable
```

**(c)** Leave `TephigramTransform` and `TephigramInvertedTransform` untouched.

**(d)** Replace the whole `TephigramAxes` class (from `class TephigramAxes(Axes):`
through `_set_default_extent`, inclusive — `__init__` and
`_set_default_extent` are deleted) with:

```python
class TephigramAxes(Axes):
    """Matplotlib axes for the ``"tephigram"`` projection.

    The data space is the native rotated x-y plane (dimensionless), with
    equal aspect so the isotherm/dry-adiabat grid stays exactly
    perpendicular on screen. The five background isopleth families are
    drawn by default as zoom-aware artists and reconfigured through the
    accessor methods (:meth:`isotherms`, :meth:`isobars`,
    :meth:`dry_adiabats`, :meth:`moist_adiabats`, :meth:`mixing_ratios`).
    The temperature/theta mapping is exposed as
    :attr:`tephigram_transform`; artists plot in (temperature, theta)
    space via ``transform=ax.tephigram_transform + ax.transData``. Native
    x/y ticks carry no meteorological meaning and are hidden.
    """

    name = "tephigram"

    tephigram_transform: TephigramTransform
    _families: dict[str, IsoplethFamily]

    def clear(self) -> None:
        """Reset the axes to the tephigram projection defaults.

        Matplotlib calls this during ``Axes.__init__`` and on user
        ``ax.clear()``; both paths recreate the projection-owned state:
        the tephigram transform, equal aspect, hidden native axes, the
        five background isopleth families, and the default extent
        (``tephpy.config`` diagram extent, else ``DEFAULT_EXTENT``).
        """
        super().clear()
        self.tephigram_transform = TephigramTransform()
        self.set_aspect(1.0, adjustable="box")
        self.xaxis.set_visible(False)
        self.yaxis.set_visible(False)
        self._families = {}
        for name, spec in _FAMILY_SPECS.items():
            family = IsoplethFamily(spec, getattr(config, name))
            self.add_artist(family)
            self._families[name] = family
        extent = config.diagram.extent
        self.set_extent(DEFAULT_EXTENT if extent is None else extent)

    def set_extent(
        self, extent: tuple[tuple[float, float], tuple[float, float]]
    ) -> None:
        """Fix the view from ((pressure, temperature), ...) corners.

        The cartopy-style idiom for directly comparable figures
        (spec §3.2): the two corners are mapped through the tephigram
        transforms to x/y limits, and autoscaling is disabled so later
        overlays never drift the window.

        Parameters
        ----------
        extent : tuple
            ``((pressure, temperature), (pressure, temperature))``
            bottom-left and top-right corners in hPa / degrees Celsius.

        Raises
        ------
        ValueError
            If a corner is unphysical (non-positive pressure) or the
            corners are degenerate.
        """
        (p0, t0), (p1, t1) = extent
        pressures = np.array([p0, p1], dtype=np.float64)
        temperatures = np.array([t0, t1], dtype=np.float64)
        thetas = transforms.theta_from_pressure_temperature(pressures, temperatures)
        x, y = transforms.xy_from_temperature_theta(temperatures, thetas)
        if not (np.isfinite(x).all() and np.isfinite(y).all()):
            msg = f"extent corners must be physical (pressure > 0 hPa): {extent!r}"
            raise ValueError(msg)
        if x[0] == x[1] or y[0] == y[1]:
            msg = f"extent corners must span a non-degenerate view: {extent!r}"
            raise ValueError(msg)
        self.set_xlim(float(np.min(x)), float(np.max(x)))
        self.set_ylim(float(np.min(y)), float(np.max(y)))
        self.set_autoscale_on(False)

    def _configure_family(self, name: str, kwargs: dict[str, object]) -> IsoplethFamily:
        """Apply non-``None`` accessor kwargs to a family and return it.

        Parameters
        ----------
        name : str
            The family key in ``_families``.
        kwargs : dict
            The accessor's keyword arguments; ``None`` values mean "not
            passed" and are dropped.

        Returns
        -------
        IsoplethFamily
            The (possibly reconfigured) family artist.
        """
        family = self._families[name]
        provided = {key: value for key, value in kwargs.items() if value is not None}
        if provided:
            family.configure(**provided)
        return family

    # The accessors deliberately mirror their config sections as wide
    # keyword-only signatures (spec §3.2/§3.5): PLR0913 is suppressed on
    # each rather than restructured away.
    def isotherms(  # noqa: PLR0913
        self,
        *,
        values: Iterable[float] | None = None,
        interval: float | None = None,
        color: str | None = None,
        linewidth: float | None = None,
        alpha: float | None = None,
        labels: bool | None = None,
        visible: bool | None = None,
    ) -> IsoplethFamily:
        """Return (and optionally reconfigure) the isotherm family.

        With no arguments this returns the family artist unchanged; any
        keyword given reconfigures it first (spec §3.2). Values are in
        degrees Celsius.

        Parameters
        ----------
        values : iterable of float, optional
            Explicit member temperatures; disables the zoom ladder.
        interval : float, optional
            Member interval; disables the zoom ladder.
        color : str, optional
            Line and label colour.
        linewidth : float, optional
            Line width in points.
        alpha : float, optional
            Line and label alpha.
        labels : bool, optional
            Whether member values are labelled.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The isotherm family artist.
        """
        return self._configure_family(
            "isotherms",
            {
                "values": values,
                "interval": interval,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "labels": labels,
                "visible": visible,
            },
        )

    def isobars(  # noqa: PLR0913
        self,
        *,
        values: Iterable[float] | None = None,
        interval: float | None = None,
        color: str | None = None,
        linewidth: float | None = None,
        alpha: float | None = None,
        labels: bool | None = None,
        visible: bool | None = None,
    ) -> IsoplethFamily:
        """Return (and optionally reconfigure) the isobar family.

        With no arguments this returns the family artist unchanged; any
        keyword given reconfigures it first (spec §3.2). Values are in
        hPa.

        Parameters
        ----------
        values : iterable of float, optional
            Explicit member pressures; disables the zoom ladder.
        interval : float, optional
            Member interval; disables the zoom ladder.
        color : str, optional
            Line and label colour.
        linewidth : float, optional
            Line width in points.
        alpha : float, optional
            Line and label alpha.
        labels : bool, optional
            Whether member values are labelled.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The isobar family artist.
        """
        return self._configure_family(
            "isobars",
            {
                "values": values,
                "interval": interval,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "labels": labels,
                "visible": visible,
            },
        )

    def dry_adiabats(  # noqa: PLR0913
        self,
        *,
        values: Iterable[float] | None = None,
        interval: float | None = None,
        color: str | None = None,
        linewidth: float | None = None,
        alpha: float | None = None,
        labels: bool | None = None,
        visible: bool | None = None,
    ) -> IsoplethFamily:
        """Return (and optionally reconfigure) the dry-adiabat family.

        With no arguments this returns the family artist unchanged; any
        keyword given reconfigures it first (spec §3.2). Values are
        potential temperatures in degrees Celsius.

        Parameters
        ----------
        values : iterable of float, optional
            Explicit member potential temperatures; disables the zoom
            ladder.
        interval : float, optional
            Member interval; disables the zoom ladder.
        color : str, optional
            Line and label colour.
        linewidth : float, optional
            Line width in points.
        alpha : float, optional
            Line and label alpha.
        labels : bool, optional
            Whether member values are labelled.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The dry-adiabat family artist.
        """
        return self._configure_family(
            "dry_adiabats",
            {
                "values": values,
                "interval": interval,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "labels": labels,
                "visible": visible,
            },
        )

    def moist_adiabats(  # noqa: PLR0913
        self,
        *,
        values: Iterable[float] | None = None,
        interval: float | None = None,
        truncation: float | None = None,
        color: str | None = None,
        linewidth: float | None = None,
        alpha: float | None = None,
        labels: bool | None = None,
        visible: bool | None = None,
    ) -> IsoplethFamily:
        """Return (and optionally reconfigure) the moist-adiabat family.

        With no arguments this returns the family artist unchanged; any
        keyword given reconfigures it first (spec §3.2). Values are
        wet-bulb potential temperatures in degrees Celsius.

        Parameters
        ----------
        values : iterable of float, optional
            Explicit member wet-bulb potential temperatures; disables the
            zoom ladder.
        interval : float, optional
            Member interval; disables the zoom ladder.
        truncation : float, optional
            Temperature (°C) below which the curves are truncated.
        color : str, optional
            Line and label colour.
        linewidth : float, optional
            Line width in points.
        alpha : float, optional
            Line and label alpha.
        labels : bool, optional
            Whether member values are labelled.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The moist-adiabat family artist.
        """
        return self._configure_family(
            "moist_adiabats",
            {
                "values": values,
                "interval": interval,
                "truncation": truncation,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "labels": labels,
                "visible": visible,
            },
        )

    def mixing_ratios(  # noqa: PLR0913
        self,
        *,
        values: Iterable[float] | None = None,
        color: str | None = None,
        linewidth: float | None = None,
        alpha: float | None = None,
        labels: bool | None = None,
        visible: bool | None = None,
    ) -> IsoplethFamily:
        """Return (and optionally reconfigure) the mixing-ratio family.

        With no arguments this returns the family artist unchanged; any
        keyword given reconfigures it first (spec §3.2). Values are
        humidity mixing ratios in g/kg; this family has no ``interval``
        (its members come from the ``MIXING_RATIO_VALUES`` ladder).

        Parameters
        ----------
        values : iterable of float, optional
            Explicit member mixing ratios; disables the zoom ladder.
        color : str, optional
            Line and label colour.
        linewidth : float, optional
            Line width in points.
        alpha : float, optional
            Line and label alpha.
        labels : bool, optional
            Whether member values are labelled.
        visible : bool, optional
            Whether the family is drawn.

        Returns
        -------
        IsoplethFamily
            The mixing-ratio family artist.
        """
        return self._configure_family(
            "mixing_ratios",
            {
                "values": values,
                "color": color,
                "linewidth": linewidth,
                "alpha": alpha,
                "labels": labels,
                "visible": visible,
            },
        )
```

- [ ] **Step 4: Run the full test suite**

Run: `pixi run --frozen pytest -q`
Expected: PASS — every test from Tasks 1–6 plus all Plan 1–2 tests.

- [ ] **Step 5: Lint and commit**

```bash
git add src/tephpy/plotting/axes.py tests/test_axes.py
pixi run lint
git commit -m "feat: draw the five isopleth families by default with accessors and set_extent"
```

---

## Task 7: tephi isopleth oracle fixture and informational cross-validation

**Files:**
- Create: `tests/fixtures/generate_tephi_isopleth_oracle.py`
- Create: `tests/fixtures/tephi_isopleth_oracle.json` (generated, committed)
- Test: `tests/test_isopleth_oracle.py`

**Interfaces:**
- Consumes: `moist_adiabat_members`, `mixing_ratio_members`, the `transforms` inverse pipeline.
- Produces: the committed fixture; nothing downstream imports these tests.

This is the §7 "informational" cross-check: MetPy's and tephi's moist-thermo
formulations genuinely differ, so agreement corroborates both while
divergence is investigated and documented — never forced to zero. Measured
divergences (tephi 0.4.0.post0 vs metpy 1.7.1, over the full fixture grid):
pseudoadiabat θw = 20 °C differs by ≤ 0.05 °C at 850/700/500 hPa, **growing
to ~0.44 °C at 300 hPa**; mixing-ratio dew points differ by ~0.09 °C at
w = 10/850 hPa, growing toward low pressure to ~0.40 °C (w = 1) and
~0.36 °C (w = 20) at 300 hPa — tephi approximates 1/ε ≈ 1.6 and omits the
vapour-pressure correction. The tolerances below (0.5 °C for both families)
are sized from those worst-case measurements — loose-but-meaningful, with
thin but real headroom.

- [ ] **Step 1: Write the generator script**

Create `tests/fixtures/generate_tephi_isopleth_oracle.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Generate the tephi isopleth oracle fixture (one-shot; not run in CI).

Run in a THROWAWAY environment so tephi never touches the project envs
(the venv is created from the pixi interpreter because the system python3
may lack ensurepip):

    pixi run --frozen python -m venv /tmp/tephi-oracle
    /tmp/tephi-oracle/bin/pip install "tephi==0.4.0.post0"
    /tmp/tephi-oracle/bin/python tests/fixtures/generate_tephi_isopleth_oracle.py

Writes ``tephi_isopleth_oracle.json`` beside this script: tephi's
pseudoadiabat temperatures (its own forward-Euler scheme, dp = -5 hPa) and
mixing-ratio dew points at fixed pressure targets, plus provenance. The
values are OUTPUTS of running tephi (BSD-3-Clause), not copied source
(spec §3.1/§10 items 5 and 13).

tephi's ``WetAdiabat._generate_points`` only touches ``data`` (theta_w),
``bounds``, and ``_delta_pressure``, so it is driven here without a
``TephiAxes`` via ``__new__`` (verified against tephi 0.4.0.post0; if a
different tephi version moves these internals, inspect the class with
``inspect.getsource(tephi.isopleths.WetAdiabat)`` and adapt — the fixture
format itself must not change).
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import tephi
from tephi import isopleths, transforms as ttr
from tephi.constants import default

THETA_WS = [0.0, 10.0, 20.0, 30.0]
MIXING_RATIOS = [1.0, 5.0, 10.0, 20.0]
PRESSURES = [1000.0, 925.0, 850.0, 700.0, 500.0, 400.0, 300.0]

#: A target counts as on-curve only if a vertex lands within half of
#: tephi's 5 hPa integration step of it.
ON_CURVE_TOLERANCE = 2.6


def wet_adiabat_temperatures(theta_w: float) -> list[float | None]:
    """Drive tephi's pseudoadiabat integration and sample it at PRESSURES.

    Parameters
    ----------
    theta_w : float
        The wet-bulb potential temperature (degrees Celsius) labelling the
        pseudoadiabat.

    Returns
    -------
    list of float or None
        tephi's temperature at each target pressure, or None where the
        curve was truncated before reaching the target.
    """
    adiabat = isopleths.WetAdiabat.__new__(isopleths.WetAdiabat)
    adiabat.data = theta_w
    adiabat.bounds = isopleths.BOUNDS(
        default["wet_adiabat_min_temperature"], default["wet_adiabat_max_pressure"]
    )
    adiabat._delta_pressure = isopleths._SATURATION_ADIABAT_PRESSURE_DELTA
    points = adiabat._generate_points()
    pressure = np.asarray(points.pressure, dtype=float)
    temperature = np.asarray(points.temperature, dtype=float)
    out: list[float | None] = []
    for target in PRESSURES:
        index = int(np.argmin(np.abs(pressure - target)))
        if abs(pressure[index] - target) > ON_CURVE_TOLERANCE:
            out.append(None)
        else:
            out.append(float(temperature[index]))
    return out


def main() -> None:
    """Evaluate tephi's curved-family maths and write the fixture."""
    moist = {str(theta_w): wet_adiabat_temperatures(theta_w) for theta_w in THETA_WS}
    mixing = {
        str(w): [float(t) for t in ttr.convert_pw2T(np.asarray(PRESSURES), w)]
        for w in MIXING_RATIOS
    }
    fixture = {
        "provenance": {
            "generator": "tests/fixtures/generate_tephi_isopleth_oracle.py",
            "generated": datetime.now(timezone.utc).isoformat(),
            "tephi_version": tephi.__version__,
            "note": (
                "Values are outputs of executing tephi (BSD-3-Clause), "
                "recorded as an informational cross-validation oracle for "
                "the curved isopleth families; no tephi source or data "
                "files are copied."
            ),
        },
        "pressures": PRESSURES,
        "moist_adiabat_theta_w": THETA_WS,
        "moist_adiabat_temperature": moist,
        "mixing_ratio_values": MIXING_RATIOS,
        "mixing_ratio_temperature": mixing,
    }
    out = Path(__file__).parent / "tephi_isopleth_oracle.json"
    out.write_text(json.dumps(fixture, indent=2) + "\n")
    print(
        f"wrote {out} ({len(THETA_WS)} pseudoadiabats, {len(MIXING_RATIOS)} isohumes)"
    )


if __name__ == "__main__":
    main()
```

Also extend the existing `tests/fixtures/generate_tephi_oracle.py` per-file
ignore in `pyproject.toml` to cover this script — change the per-file-ignores
key to a glob:

```toml
# One-shot generator scripts (spec §7 layer 4), not package modules; their
# print is the script's user feedback.
"tests/fixtures/generate_tephi_*.py" = ["INP001", "T201", "SLF001"]
```

(`SLF001` because the generator intentionally drives tephi private internals;
delete the now-redundant single-file entry it replaces.)

- [ ] **Step 2: Generate and inspect the fixture**

Run the three commands from the script's docstring.
Expected: `tephi_isopleth_oracle.json` written. Spot-check: for θw = 20 the
850 hPa entry is ≈ 13.98 and the 500 hPa entry ≈ −8.44 (values observed
2026-07-24); θw = 0 has `null` for the highest targets (truncated at −50 °C).

- [ ] **Step 3: Write the comparison tests**

Create `tests/test_isopleth_oracle.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Informational cross-validation of the curved families against tephi (§7).

tephi is a corroborating oracle, not the definition of truth. Known,
accepted formulation differences (documented per spec §7 — investigate,
don't widen; both grow toward low pressure, so the tolerances are sized
from the worst case over the fixture grid, with thin headroom that a
future metpy/scipy lockfile bump may consume — expected drift, not a
mystery):

- Pseudoadiabats: tephi integrates its own forward-Euler scheme
  (dp = -5 hPa; Cp = 1004, L = 2.501e6) while tephpy delegates to
  metpy.calc.moist_lapse (ODE integration). Measured divergence at
  theta_w = 20 °C: <= 0.05 °C at 850/700/500 hPa, ~0.44 °C at 300 hPa.
- Mixing-ratio lines: tephi approximates 1/epsilon as 1.6 and omits the
  vapour-pressure correction; MetPy uses the exact formulations. Measured
  divergence: ~0.09 °C at w = 10/850 hPa, ~0.40 °C (w = 1) and ~0.36 °C
  (w = 20) at 300 hPa.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tephpy import transforms
from tephpy.plotting import isopleths

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "tephi_isopleth_oracle.json").read_text()
)

#: Loose-but-meaningful tolerances (°C), sized from the worst measured
#: formulation differences above (0.44 and 0.40 °C at 300 hPa).
MOIST_ATOL = 0.5
MIXING_ATOL = 0.5

#: A fixture target counts as on our curve only if a vertex lands within
#: half our 5 hPa sampling step of it (mirrors the generator).
ON_CURVE_TOLERANCE = 2.6


def _pressure_temperature(member):
    """Recover (pressure, temperature) vertices from a member polyline."""
    t, theta = transforms.temperature_theta_from_xy(member.xy[:, 0], member.xy[:, 1])
    pressure = transforms.pressure_from_temperature_theta(t, theta)
    return pressure, t


@pytest.mark.parametrize("theta_w", FIXTURE["moist_adiabat_theta_w"])
def test_moist_adiabat_matches_tephi(theta_w):
    """Pseudoadiabats agree with tephi within the documented tolerance."""
    (member,) = isopleths.moist_adiabat_members([theta_w])
    pressure, temperature = _pressure_temperature(member)
    expected = FIXTURE["moist_adiabat_temperature"][str(theta_w)]
    compared = 0
    for target, value in zip(FIXTURE["pressures"], expected, strict=True):
        if value is None:
            continue
        index = int(np.argmin(np.abs(pressure - target)))
        if abs(pressure[index] - target) > ON_CURVE_TOLERANCE:
            continue  # our curve truncated before this target
        assert temperature[index] == pytest.approx(value, abs=MOIST_ATOL)
        compared += 1
    assert compared > 0


@pytest.mark.parametrize("mixing_ratio", FIXTURE["mixing_ratio_values"])
def test_mixing_ratio_matches_tephi(mixing_ratio):
    """Isohume dew points agree with tephi within the documented tolerance."""
    (member,) = isopleths.mixing_ratio_members([mixing_ratio])
    pressure, temperature = _pressure_temperature(member)
    expected = FIXTURE["mixing_ratio_temperature"][str(mixing_ratio)]
    order = np.argsort(pressure)
    for target, value in zip(FIXTURE["pressures"], expected, strict=True):
        # Our 10 hPa sampling grid doesn't land exactly on every target
        # (e.g. 925): interpolate along the member, which spans the full
        # pressure domain.
        interpolated = float(np.interp(target, pressure[order], temperature[order]))
        assert interpolated == pytest.approx(value, abs=MIXING_ATOL)
```

- [ ] **Step 4: Run the oracle tests**

Run: `pixi run --frozen pytest tests/test_isopleth_oracle.py -q`
Expected: PASS. **If any case fails:** do not widen the tolerance. Reproduce
the case by hand (Poisson + the pseudoadiabatic lapse rate, or the
Clausius-Clapeyron inversion), decide which implementation is right, and
record the finding in this module's docstring.

- [ ] **Step 5: Lint and commit**

```bash
git add tests/fixtures/ tests/test_isopleth_oracle.py pyproject.toml
pixi run lint
git commit -m "test: record the tephi isopleth oracle and cross-validate the curved families"
```

---

## Task 8: pytest-mpl infrastructure, image baselines, and the vector-output smoke test

**Files:**
- Modify: `pyproject.toml` (pytest ini options; pixi tasks)
- Modify: `.github/workflows/ci-tests.yml` (add `--mpl`)
- Modify: `tests/AGENTS.md`, `.gitignore`
- Create: `tests/test_images.py`
- Create: `tests/baseline/*.png` (7 generated baselines)

**Interfaces:**
- Produces: the §8.5 image-test infrastructure (spec §10 item 15 resolution: a `baselines` task regenerates baselines; `tests-clean` removes test artifacts) and the §9 vector-output smoke test assigned to this plan.

pytest-mpl facts this task relies on (all verified on pytest-mpl 0.19.0 with
this repo's strict config, 2026-07-24): without `--mpl` a marked test runs
but compares nothing — so CI **must** gain the flag or image tests are
silent no-ops; `mpl-baseline-path`/`mpl-results-path` are legal ini options
under `--strict-config`; when `--mpl-generate-path` is present generation
wins and marked tests are *skipped* (a baselines run never verifies);
default tolerance is 2 (RMS on 0–255 pixels) under the plugin's `classic`
style (savefig dpi 100), and PNGs are bit-identical across the three pinned
test envs, so the default tolerance stays. Baselines must be regenerated
(and all three envs re-verified) whenever a lockfile bump changes
matplotlib or freetype.

- [ ] **Step 1: Wire pyproject and CI**

In `pyproject.toml`:

**(a)** Append to `[tool.pytest.ini_options]` (after `markers`):

```toml
mpl-baseline-path = "tests/baseline"
mpl-results-path = ".mpl-results"
```

**(b)** Change the `tests` task command:

```toml
[tool.pixi.feature.test.tasks.tests]
cmd = "pytest --cov --cov-report=xml --mpl"
description = "Run the unit test suite with coverage"
```

**(c)** Replace the `tests-mpl-generate` task (delete it) with:

```toml
[tool.pixi.feature.test.tasks.baselines]
cmd = "pytest --mpl-generate-path=tests/baseline"
description = "Regenerate matplotlib image-comparison baselines"

[tool.pixi.feature.test.tasks.tests-clean]
cmd = "rm -rf .coverage coverage.xml .pytest_cache .mpl-results .hypothesis"
description = "Remove coverage, pytest, pytest-mpl, and hypothesis artifacts"
```

In `.github/workflows/ci-tests.yml`, change the pytest run line to:

```yaml
      - run: pixi run --frozen --environment ${{ matrix.environment }} pytest --cov --cov-report=xml --mpl
```

Append to `.gitignore`:

```
.mpl-results/
```

Update `tests/AGENTS.md` — replace its pytest-mpl sentence so the file reads:

```markdown
# Agent guidance — tests

pytest with strict config and `filterwarnings = ["error"]`. Image tests use
pytest-mpl (`@pytest.mark.mpl_image_compare`); CI and `pixi run tests` pass
`--mpl` so comparisons are enforced; baselines live in `tests/baseline` and
regenerate via `pixi run baselines` (regenerate whenever a lockfile bump
changes matplotlib or freetype, then re-verify all three test envs).
`pixi run tests-clean` removes test artifacts. Property tests use hypothesis.
```

- [ ] **Step 2: Validate the workflow edit**

Run:
```bash
pixi run -e devs pre-commit run check-github-workflows --all-files
pixi run -e devs pre-commit run zizmor --all-files
```
Expected: both pass.

- [ ] **Step 3: Write the image and vector tests**

Create `tests/test_images.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Image-baseline and vector-output tests for the tephigram diagram (§8.5).

Baselines live in ``tests/baseline`` (pyproject ``mpl-baseline-path``),
generated with ``pixi run baselines`` on the committed lockfile. The
plugin's defaults apply: classic style, savefig dpi 100, RMS tolerance 2 —
output is bit-identical across the pinned py312/py313/py314 environments.
pytest-mpl closes returned figures itself.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

import tephpy  # noqa: F401 -- registers the "tephigram" projection

FAMILIES = ("isotherms", "isobars", "dry_adiabats", "moist_adiabats", "mixing_ratios")


def _tephigram_figure():
    """Create a small tephigram figure (baselines stay a few tens of KB)."""
    return plt.subplots(figsize=(3.5, 3.5), subplot_kw={"projection": "tephigram"})


def _solo(ax, name):
    """Hide every family except `name`."""
    for family in FAMILIES:
        if family != name:
            getattr(ax, family)(visible=False)


@pytest.mark.mpl_image_compare
def test_default_diagram():
    fig, _ax = _tephigram_figure()
    return fig


@pytest.mark.mpl_image_compare
def test_zoomed_diagram():
    fig, ax = _tephigram_figure()
    ax.set_extent(((1050.0, -10.0), (700.0, 30.0)))
    return fig


@pytest.mark.mpl_image_compare
def test_family_isotherms():
    fig, ax = _tephigram_figure()
    _solo(ax, "isotherms")
    return fig


@pytest.mark.mpl_image_compare
def test_family_isobars():
    fig, ax = _tephigram_figure()
    _solo(ax, "isobars")
    return fig


@pytest.mark.mpl_image_compare
def test_family_dry_adiabats():
    fig, ax = _tephigram_figure()
    _solo(ax, "dry_adiabats")
    return fig


@pytest.mark.mpl_image_compare
def test_family_moist_adiabats():
    fig, ax = _tephigram_figure()
    _solo(ax, "moist_adiabats")
    return fig


@pytest.mark.mpl_image_compare
def test_family_mixing_ratios():
    fig, ax = _tephigram_figure()
    _solo(ax, "mixing_ratios")
    return fig


def test_savefig_vector_formats(tmp_path):
    """The first real diagram exports to PDF and SVG (spec §9, Plan 3 row)."""
    fig, _ax = _tephigram_figure()
    pdf = tmp_path / "tephigram.pdf"
    svg = tmp_path / "tephigram.svg"
    try:
        fig.savefig(pdf)
        fig.savefig(svg)
    finally:
        plt.close(fig)
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert b"</svg>" in svg.read_bytes()
```

- [ ] **Step 4: Generate the baselines, then verify them**

```bash
pixi run baselines        # writes tests/baseline/*.png; marked tests are SKIPPED
pixi run tests            # now compares against the fresh baselines
ls -la tests/baseline     # expect 7 PNGs, each well under 100 KB
```
Expected: 7 baselines generated; the full suite (including comparisons and
the vector smoke test) passes with coverage.

- [ ] **Step 5: Lint and commit**

```bash
git add pyproject.toml .github/workflows/ci-tests.yml .gitignore tests/AGENTS.md tests/test_images.py tests/baseline/
pixi run lint
git commit -m "test: add pytest-mpl baselines, tasks, and the vector-output smoke test"
```

---

## Task 9: Glossary entries and a warning-free docs build

**Files:**
- Modify: `docs/src/reference/glossary.rst` (append four entries)

**Interfaces:**
- Produces: glossary terms `isopleth`, `isobar`, `moist adiabat` (with the spec §10 item 6 aliases `saturation adiabat`, `saturated adiabat`, `wet adiabat`), `wet-bulb potential temperature` (§8.6 lists it as entry-worthy; this plan introduces it as the moist-adiabat label), and `humidity mixing ratio` (with aliases `mixing ratio`, `isohume`) available for `:term:` references.

- [ ] **Step 1: Append the entries**

Append inside the existing `.. glossary::` directive in
`docs/src/reference/glossary.rst`, keeping the established indent:

```rst
    isopleth
        A line along which one quantity is constant. The tephigram
        background is five isopleth families — :term:`isotherms
        <isotherm>`, :term:`isobars <isobar>`, :term:`dry adiabats
        <dry adiabat>`, :term:`moist adiabats <moist adiabat>`, and lines
        of constant :term:`humidity mixing ratio` — each drawn by one
        zoom-aware Matplotlib artist (``IsoplethFamily``) that selects
        the members appropriate to the current view.

    isobar
        A line of constant pressure. Pressure is not an axis of the
        tephigram, so each isobar is a gentle curve across the
        temperature/:term:`potential temperature` grid; ``tephpy`` labels
        isobars in hPa and reconfigures them via ``ax.isobars(...)``.

    moist adiabat
    saturation adiabat
    saturated adiabat
    wet adiabat
        The path a saturated air parcel follows when lifted: heat released
        by condensation makes it cool more slowly than a :term:`dry
        adiabat`. Each curve is labelled by its :term:`wet-bulb potential
        temperature` — the temperature where it crosses 1000 hPa.
        ``tephpy`` computes moist adiabats with ``metpy.calc.moist_lapse``
        and truncates them at low temperature where they converge onto
        the dry adiabats; "moist adiabat" is the canonical name, matching
        the AMS Glossary headword and MetPy's vocabulary.

    wet-bulb potential temperature
        The temperature a parcel would have if brought saturated along a
        :term:`moist adiabat` to the 1000 hPa reference pressure; written
        θw (theta-w). It is conserved along a moist adiabat, which is why
        ``tephpy`` uses it (°C) as the member value labelling each moist
        adiabat.

    humidity mixing ratio
    mixing ratio
    isohume
        The mass of water vapour per mass of dry air, in g/kg. On a
        tephigram, a line of constant *saturation* mixing ratio (an
        isohume) marks where air of a given moisture content saturates;
        ``tephpy`` computes these lines with MetPy and labels them in
        g/kg via ``ax.mixing_ratios(...)``.
```

- [ ] **Step 2: Build the docs**

Run: `pixi run docs`
Expected: `build succeeded`, **0 warnings**. The autoapi section now includes
the `tephpy.plotting.isopleths` page (`_config`, like `_constants`, is
private and intentionally has no page). If a warning appears (e.g. a
cross-reference typo), fix it — do not suppress.

- [ ] **Step 3: Commit**

```bash
git add docs/src/reference/glossary.rst
git commit -m "docs: seed glossary entries for the isopleth-layer terms"
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
Expected: lint fully green; tests (including all 7 image comparisons) pass
on all three Pythons against the same committed baselines; docs build with
0 warnings.

- [ ] **Step 2: Open the pull request**

```bash
git push -u origin isopleths
gh pr create --base main --title "Isopleth plotting (Plan 3)" --fill
```

- [ ] **Step 3: Add the changelog fragment named for the PR**

With `<PR>` the number just created:

```bash
cat > changelog/<PR>.feature.rst <<'EOF'
Added the five zoom-aware background isopleth families with per-family accessor methods, ``TephigramAxes.set_extent``, the ``tephpy.config`` runtime configuration layer, and pytest-mpl image baselines.
(:user:`claude`)
EOF
git add changelog/<PR>.feature.rst
git commit -m "docs: add Plan 3 changelog fragment"
git push
```
Expected: the `ci-changelog` check passes on the PR; all other checks
(tests ×3 with image comparisons, docs, wheels + smoke test, CodeQL,
pre-commit.ci) go green.

---

## Self-review

**Spec coverage (§3.2/§3.5/§7/§8.5/§10 Plan 3 row):** grid + five families as
zoom-aware artists reimplementing the locator/refresh idea as one
`IsoplethFamily` per family → Tasks 3–5 (precomputed bare-numpy members over
a generous domain, cached, per-draw clip/select/label; curved families via
`metpy.calc` behind function-local imports). Accessor methods with the
resolved item-6 names and semantics (no-arg returns, kwargs reconfigure) →
Task 6. `set_extent` (cartopy idiom, autoscale off, `DEFAULT_ANCHOR` →
`DEFAULT_EXTENT`) → Tasks 1/6. §3.5 `_constants` accretion + `tephpy.config`
typed singleton with `context()` and the kwargs > config > constants
precedence, read at create/reconfigure only → Tasks 1–2, enforced in Task 5's
snapshot tests. pytest-mpl infrastructure + per-family/composed baselines +
item-15 task reconciliation (`baselines`, `tests-clean`) → Task 8.
Vector-output smoke test (§9, Plan 3 row) → Task 8. Informational tephi
cross-check for curved families (§7) with recorded provenance (item 13) →
Task 7. Layout contract documented, no code (item 7) → Task 6 module
docstring. Glossary rule → Task 9. Changelog + full gate → Task 10.
Import-cost guard (item 10, Plan 3's share) → Task 4 subprocess test.

**Placeholder scan:** every code step carries complete, runnable code — the
`_config.py` and isopleths artist listings were verified verbatim against
ruff/mypy-strict/numpydoc plus a runtime draw test before being written into
this plan, and an adversarial review pass then executed the assembled plan
end to end (all tasks' code and tests, baseline generation and comparison
included), with its findings — two empirically re-sized tolerances, the
PLR0913/ANN202 suppressions, the `import tephpy` registration in
`test_images.py`, and assorted lint reflows — folded back in. The only
execution-time contingency is tephi's private API in the Task 7 generator,
which was verified against the pinned tephi 0.4.0.post0 and carries an
inspection instruction plus a frozen fixture schema (the Plan 2 precedent).

**Type/name consistency:** builder names (`isotherm_members` …
`mixing_ratio_members`), `Member`, `ResolvedOptions`, `FamilySpec`,
`_FAMILY_SPECS`, `IsoplethFamily(spec, section)`, `.configure/.options`, the
five accessor names, `set_extent`, and every `_constants` name are identical
across Tasks 1–8 and the Interfaces contract; Task 5's tests import the same
`config` sections Task 6 wires in.

**Known judgment calls (documented, not hidden):**
- Zoom selection is value-multiple steps / index strides against absolute
  view width — deterministic, pan-stable, and value-preferring, deliberately
  *not* tephi 0.3's data-dependent zoom ratio nor tephi 0.4's
  pan-dependent nbins decimation (both observed misbehaving during research).
- Zoom ladders live in `_constants` only (not in `config`); users who want a
  different density set `values=`/`interval=`, which disables the ladder.
- The isobar ladder bottoms out at the spec §3.5 "10 mb" printed-chart
  interval at deep zoom (100/50/20/10 — every rung an integer multiple of the
  finest, as the selection scheme requires), with 50 hPa at the default view.
- Oracle and cross-check tolerances are sized from *measured worst cases over
  the full comparison grids* (divergences grow toward low pressure), not from
  single mid-level spot checks; the measurements are recorded in the test
  docstrings so future lockfile-bump drift is diagnosable.
- Lint posture: the five accessors suppress `PLR0913` per method (the wide
  keyword-only signatures are the API design); tests add `ANN202` to their
  existing ANN per-file-ignores rather than annotating private test helpers.
- The isopleth build/draw path is bare numpy end to end; pint appears only
  immediately around the MetPy calls (the §5 exemption extended to the
  geometry layer that matplotlib drives on every draw).
- First draw pays a one-time ~0.8 s metpy import + ~25 ms geometry build
  (lazy, so bare axes creation stays fast); a warm full-grid draw measured
  ~80 ms, dominated by label Text rendering — acceptable for v1, matching
  tephi's approach.
- Labels anchor at the middle in-view vertex per member (isobar labels
  therefore stack near the view-centre column, as tephi's do); smarter
  de-overlapping is deferred until a real need appears.
- `MIXING_RATIO_VALUES` is tephpy's own 16-value ladder (roughly 1–1.5–2–3–5–7
  decades), not tephi's 43-value list — denser than the default view can
  label legibly; documented as a convention in `_constants`.
- `set_extent` raises `ValueError` (the shared exception module is Plan 4's
  deliverable per §10 item 4/§6).
- Committed PNG baselines ride into the sdist via the setuptools-scm file
  finder like the rest of `tests/` (~200 KB total; each well under the
  `check-added-large-files` limit).

---

## Execution handoff

Plan 3 of 7 (spec §10). On completion, **Plan 4: sounding data model &
profile plotting** is unblocked — it builds the `Sounding` dataclass, the §5
units machinery and shared exception module, `plot_profile`/`plot_sounding`
with overlays and legends, and profile image baselines on top of this plan's
axes and pytest-mpl infrastructure. Plans 5 and 6 follow Plan 4 and may then
proceed in parallel.
