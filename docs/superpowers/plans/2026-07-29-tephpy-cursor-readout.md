# tephpy Cursor Readout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the navigation toolbar's raw tephigram (x, y) readout with diagram-meaningful values — `850 hPa, -4.2 °C, θ 8.6 °C` by default — selected from a five-field registry via `config.cursor.fields`, with stock `ax.format_coord = fn` assignment as the documented full-custom path.

**Architecture:** `TephigramAxes.format_coord(x, y)` (the stock matplotlib toolbar hook) inverts the cursor position through the existing `transforms.temperature_theta_from_xy`, derives pressure via `transforms.pressure_from_temperature_theta`, and joins per-field formatter outputs in listed order. The formatters live in a module-level registry in `plotting/axes.py` keyed by field name — closed-form `pressure`/`temperature`/`theta` (the `_constants.CURSOR_FIELDS` default), opt-in `mixing_ratio`/`theta_w` via function-local `metpy.calc`. Field selection reads `config.cursor.fields` live on every call (unlike the families' read-at-creation snapshot), so `config.context(cursor={"fields": ...})` scopes over existing axes; instance assignment of `format_coord` shadows the method — the "accessor tier" of the ladder — for free.

**Tech Stack:** Python 3.12/3.13/3.14, numpy, matplotlib (Agg in tests), metpy 1.7.1 (`saturation_mixing_ratio`, `wet_bulb_potential_temperature`, function-local), pytest, pixi tasks. No new dependencies, no new files (three source files and three test files are modified; the changelog fragment is the only new file).

**Spec:** `docs/superpowers/specs/2026-07-22-tephpy-design.md` — §3.2 (the `ax.format_coord` bullet), §3.5 (the `config.cursor` section and its live-read exception), §6 (fail-loud `TypeError` conventions). Post-roadmap addition (not a §10 plan row).

## Global Constraints

Copied from the spec / prior plans; every task's requirements implicitly include these.

- **Python support (SPEC 0):** 3.12, 3.13, and 3.14. **Platforms (pixi):** `linux-64` only.
- **Imports:** every `.py` file carries `from __future__ import annotations` (already present in all files touched here).
- **Lint/type:** ruff `ALL` (repo config); mypy `strict` clean over `src/tephpy`. numpydoc-validation checks **every docstringed object, including private helpers**: documented parameters (PR01) and a `Returns` section on anything returning a value (RT01). Unused formatter parameters take a leading underscore and are documented as "Ignored; …" — the `_build_mixing_ratios(values, _truncation)` precedent in `plotting/isopleths.py`.
- **Function-local heavy imports** (spec §10 item 10): `metpy` import sites carry `# noqa: PLC0415` exactly as shown. The subprocess import-cost guard in `tests/test_units.py` already forbids `metpy` at `import tephpy` time — the opt-in formatters must not import it at module level.
- **Units:** conversion via `.m_as(...)` — never `np.asarray(Quantity)` (`UnitStrippedWarning` is an **error** under the repo's pytest `filterwarnings = ["error"]`).
- **Tests:** pytest strict config with `filterwarnings = ["error"]`; the `tephigram_axes` fixture in `tests/plotting/test_axes.py` already closes its figure. In tests, never assign a lambda (ruff E731) — use a `def`.
- **Docs:** build must stay warning-free (`pixi run --frozen docs` — it cleans first). No new public names are introduced (`format_coord` overrides an existing matplotlib method; the config section is an instance attribute), so no `numpydoc_xref_aliases` additions are expected.
- **Changelog:** one `changelog/<PR>.enhancement.rst` fragment for the implementation PR, cross-referencing APIs with Sphinx roles and ending with ``(:user:`claude`)`` (see `changelog/README.md`); verify with a **clean** docs build. The fragment is added *after* the PR number exists (Task 4).
- **Branch:** work on a feature branch (`no-commit-to-branch` blocks `main`): `git switch -c cursor-readout`. Ensure the pre-commit git hooks are installed **before the first commit** (`pixi run --frozen pre-commit install` — fresh clones/worktrees only have `.sample` hooks; in a worktree, commit via `pixi run --frozen git commit ...` so the hook finds `pre-commit` on PATH) and run `pixi run --frozen lint` before every push. **`git add` new files before `pixi run --frozen lint`** (pre-commit only checks files git knows about).
- **Dedented listings:** the repo's blacken-docs hook formats this plan's fenced listings at top level, so code destined for a **class body** (Task 2 step 3, the `format_coord` method) is shown **dedented** — indent every line one level (4 spaces) when inserting into `TephigramAxes`.
- **Environment facts (verified empirically against the committed lockfile, 2026-07-29):**
  - At the spec's example point — 850 hPa, −4.2 °C — the forward mapping gives θ = 8.582837599616823 °C and data-space (x, y) = (1688.0877712462059, 1696.487771246206); the round-trip back through `temperature_theta_from_xy` + `pressure_from_temperature_theta` reproduces (850, −4.2, 8.58…) to 13 significant figures, so `"{:.0f} hPa"`/`"{:.1f} °C"` formatting yields exactly `850 hPa, -4.2 °C, θ 8.6 °C`.
  - `metpy.calc.saturation_mixing_ratio(pressure, temperature)` at that point → 3.29377 g/kg (`"3.3 g/kg"` at one decimal); `metpy.calc.wet_bulb_potential_temperature(pressure, temperature, dewpoint)` with `dewpoint=temperature` (the saturated point — the moist adiabat through it) → 4.00705 °C (`"θw 4.0 °C"`). Both accept scalar pint quantities and support `.m_as(...)`.
  - **NaN reaches the readout through *pressure*, not the inverse transform:** `temperature_theta_from_xy` is finite almost everywhere (`exp` of the y+x term), but `pressure_from_temperature_theta` raises a **negative** Kelvin temperature to a fractional power when the cursor sits left of the −273.15 °C isotherm → NaN. Data-space `(-300.0, 300.0)` (T = −300 °C) is a verified blank-readout probe. The finiteness guard must therefore check all of p, T, θ — and `p > 0` besides (a theoretical `θ = inf` overflow yields `p = 0.0`, finite but absurd).
  - Assigning `ax.format_coord = fn` shadows the class method via the instance `__dict__` — stock Python attribute lookup; matplotlib's toolbar calls `ax.format_coord(x, y)` and picks up the assignment. A `TypeError` raised from `format_coord` surfaces as a printed traceback on the first mouse move — loud by design (§3.2).

---

### Task 1: The `cursor` config section and its constants default

**Files:**
- Modify: `src/tephpy/_constants.py` (after the `SOUNDING_LABEL_FORMAT` block, ~line 174)
- Modify: `src/tephpy/_config.py` (new `CursorOptions` dataclass before `Config`; new `Config` field; `Config` docstring)
- Test: `tests/test_constants.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `_constants.CURSOR_FIELDS: Final[tuple[str, ...]] = ("pressure", "temperature", "theta")`; `config.cursor.fields: tuple[str, ...] | None` (default `None`). Task 2 reads both.

- [ ] **Step 1: Write the failing tests**

In `tests/test_constants.py`, after `test_sounding_label_format` (mirroring its style — the file imports `_constants` as `constants`):

```python
def test_cursor_fields():
    """The default cursor readout trio, in display order (spec §3.2)."""
    assert constants.CURSOR_FIELDS == ("pressure", "temperature", "theta")
```

In `tests/test_config.py`: add `"cursor"` to the module-level `SECTIONS` tuple (after `"diagram"`), extend `test_section_shapes` with one line —

```python
assert hasattr(tephpy.config.cursor, "fields")
```

— and add, after `test_context_applies_and_restores`:

```python
def test_context_cursor_fields_applies_and_restores():
    with tephpy.config.context(cursor={"fields": ("pressure",)}):
        assert tephpy.config.cursor.fields == ("pressure",)
    assert tephpy.config.cursor.fields is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen tests -k "cursor_fields or singleton or section_shapes"`
Expected: FAIL — `AttributeError: ... has no attribute 'CURSOR_FIELDS'`, and the config tests fail with `unknown config section 'cursor'` / missing attribute.

- [ ] **Step 3: Write the minimal implementation**

In `src/tephpy/_constants.py`, immediately after the `SOUNDING_LABEL_FORMAT` entry:

```python
#: Default interactive cursor readout fields (spec §3.2), in display order;
#: names index the ``plotting.axes`` cursor formatter registry.
CURSOR_FIELDS: Final[tuple[str, ...]] = ("pressure", "temperature", "theta")
```

In `src/tephpy/_config.py`, a new section dataclass directly above `Config` (house style: `#:` attribute comments, `None` falls through to `_constants`):

```python
@dataclasses.dataclass
class CursorOptions:
    """Options for the interactive cursor readout (spec §3.2)."""

    #: Readout fields in display order, naming entries in the
    #: ``TephigramAxes.format_coord`` registry; ``None`` falls through to
    #: the ``_constants.CURSOR_FIELDS`` convention.
    fields: tuple[str, ...] | None = None
```

In `Config`, after the `diagram` field:

```python
cursor: CursorOptions = dataclasses.field(default_factory=CursorOptions)
```

And update the `Config` docstring's first line from "One typed section per isopleth family plus a diagram-wide section" to "One typed section per isopleth family plus diagram-wide and cursor sections", keeping the examples line and appending `or ``config.cursor.fields``` to it.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen tests`
Expected: full suite PASSES (`test_all_defaults_are_none` iterates `dataclasses.fields(Config)` and picks the new section up automatically; nothing else enumerates sections).

- [ ] **Step 5: Commit**

```bash
git add src/tephpy/_constants.py src/tephpy/_config.py tests/test_constants.py tests/test_config.py
pixi run --frozen git commit -m "Add the cursor config section and its constants default"
```

---

### Task 2: `format_coord` — the closed-form default trio

**Files:**
- Modify: `src/tephpy/plotting/axes.py` (module level: three formatters + registry, after the `_FIGURE_CLEAR_CODE` block ~line 78; class body: `format_coord` after `set_extent`; the `_constants` import block gains `CURSOR_FIELDS`)
- Test: `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes: `config.cursor.fields`, `_constants.CURSOR_FIELDS` (Task 1); `transforms.temperature_theta_from_xy`, `transforms.pressure_from_temperature_theta` (existing).
- Produces: `TephigramAxes.format_coord(x: float, y: float) -> str`; module-level `_CURSOR_FORMATTERS: dict[str, Callable[[float, float, float], str]]` with keys `"pressure"`, `"temperature"`, `"theta"` — Task 3 adds two more entries and relies on every formatter taking `(pressure, temperature, theta)` floats and returning `str`.

- [ ] **Step 1: Write the failing tests**

In `tests/plotting/test_axes.py` (`transforms`, `config`, and the `tephigram_axes` fixture are already imported/defined there), after the `set_extent` tests:

```python
def _cursor_xy(pressure, temperature):
    """Map a (pressure, temperature) point into cursor data-space (x, y)."""
    theta = transforms.theta_from_pressure_temperature(pressure, temperature)
    x, y = transforms.xy_from_temperature_theta(temperature, theta)
    return float(x), float(y)


def test_format_coord_default_trio(tephigram_axes):
    """The toolbar readout renders p, T, theta — not raw data-space (x, y)."""
    x, y = _cursor_xy(850.0, -4.2)
    assert tephigram_axes.format_coord(x, y) == "850 hPa, -4.2 °C, θ 8.6 °C"


def test_format_coord_config_fields_read_live(tephigram_axes):
    """config.cursor.fields reorders/selects, live on an existing axes (§3.5)."""
    x, y = _cursor_xy(850.0, -4.2)
    with config.context(cursor={"fields": ("theta", "pressure")}):
        assert tephigram_axes.format_coord(x, y) == "θ 8.6 °C, 850 hPa"
    assert tephigram_axes.format_coord(x, y) == "850 hPa, -4.2 °C, θ 8.6 °C"


def test_format_coord_out_of_domain_blank(tephigram_axes):
    """Left of the -273.15 °C isotherm the pressure is NaN: blank readout."""
    assert tephigram_axes.format_coord(-300.0, 300.0) == ""


def test_format_coord_instance_assignment_wins(tephigram_axes):
    """Stock matplotlib full-custom path: assignment shadows the method (§3.2)."""

    def custom(x, y):
        return "custom"

    tephigram_axes.format_coord = custom
    assert tephigram_axes.format_coord(1.0, 2.0) == "custom"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen tests -k "format_coord"`
Expected: the first three FAIL (stock `Axes.format_coord` returns `x=... y=...` strings); `test_format_coord_instance_assignment_wins` PASSES already (it pins stock behaviour the design documents — that is expected; do not delete it).

- [ ] **Step 3: Write the minimal implementation**

In `src/tephpy/plotting/axes.py`, add `CURSOR_FIELDS` to the `from tephpy._constants import (...)` block (alphabetical order). At module level, after the `_FIGURE_CLEAR_CODE` block:

```python
def _cursor_pressure(pressure: float, _temperature: float, _theta: float) -> str:
    """Format the cursor point's pressure (spec §3.2).

    Parameters
    ----------
    pressure : float
        Cursor pressure in hPa.
    _temperature : float
        Ignored; the uniform registry signature.
    _theta : float
        Ignored; the uniform registry signature.

    Returns
    -------
    str
        The pressure readout, whole hPa.
    """
    return f"{pressure:.0f} hPa"


def _cursor_temperature(_pressure: float, temperature: float, _theta: float) -> str:
    """Format the cursor point's temperature (spec §3.2).

    Parameters
    ----------
    _pressure : float
        Ignored; the uniform registry signature.
    temperature : float
        Cursor temperature in degrees Celsius.
    _theta : float
        Ignored; the uniform registry signature.

    Returns
    -------
    str
        The temperature readout, one decimal.
    """
    return f"{temperature:.1f} °C"


def _cursor_theta(_pressure: float, _temperature: float, theta: float) -> str:
    """Format the cursor point's potential temperature (spec §3.2).

    Parameters
    ----------
    _pressure : float
        Ignored; the uniform registry signature.
    _temperature : float
        Ignored; the uniform registry signature.
    theta : float
        Cursor potential temperature in degrees Celsius.

    Returns
    -------
    str
        The potential-temperature readout, one decimal.
    """
    return f"θ {theta:.1f} °C"


#: The cursor readout field registry (spec §3.2): field name to a
#: ``(pressure, temperature, theta) -> str`` formatter.
_CURSOR_FORMATTERS: Final[dict[str, Callable[[float, float, float], str]]] = {
    "pressure": _cursor_pressure,
    "temperature": _cursor_temperature,
    "theta": _cursor_theta,
}
```

(`Callable` is already imported under `TYPE_CHECKING`; with `from __future__ import annotations` the `Final[...]` annotation never evaluates at runtime. `Final` is imported from `typing` — extend the existing `typing` import line.)

In the `TephigramAxes` class body, after `set_extent` (shown dedented — indent one level when inserting):

```python
def format_coord(self, x: float, y: float) -> str:
    """Report diagram-meaningful values for the cursor position (spec §3.2).

    The navigation toolbar's readout: the data-space cursor position
    inverts to (temperature, theta), pressure derives via Poisson's
    equation, and the configured fields render in listed order, e.g.
    ``850 hPa, -4.2 °C, θ 8.6 °C``. Fields resolve as instance
    assignment > ``tephpy.config`` > ``_constants``: assigning
    ``ax.format_coord = fn`` (stock matplotlib) shadows this method
    entirely, and ``config.cursor.fields`` is read live on every call,
    so a ``config.context(cursor={"fields": ...})`` override applies to
    existing axes for its duration (spec §3.5).

    Parameters
    ----------
    x : float
        Cursor x in tephigram data space.
    y : float
        Cursor y in tephigram data space.

    Returns
    -------
    str
        The formatted readout, or ``""`` when the position is
        unphysical (e.g. left of the -273.15 °C isotherm).

    Raises
    ------
    TypeError
        If ``config.cursor.fields`` names an unknown field.
    """
    fields = config.cursor.fields
    if fields is None:
        fields = CURSOR_FIELDS
    unknown = set(fields) - set(_CURSOR_FORMATTERS)
    if unknown:
        msg = (
            f"unknown cursor field(s) {sorted(unknown)!r}; "
            f"expected {sorted(_CURSOR_FORMATTERS)!r}"
        )
        raise TypeError(msg)
    temperature, theta = transforms.temperature_theta_from_xy(x, y)
    pressure = transforms.pressure_from_temperature_theta(temperature, theta)
    p, t, th = float(pressure), float(temperature), float(theta)
    finite = math.isfinite(p) and math.isfinite(t) and math.isfinite(th)
    if not (finite and p > 0.0):
        return ""
    return ", ".join(_CURSOR_FORMATTERS[name](p, t, th) for name in fields)
```

(The unknown-field guard ships here — Task 3 tests it once the registry is complete; `math` is already imported.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen tests`
Expected: full suite PASSES.

- [ ] **Step 5: Commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
pixi run --frozen git commit -m "Make the tephigram cursor readout diagram-meaningful"
```

---

### Task 3: The opt-in MetPy fields and the unknown-field error

**Files:**
- Modify: `src/tephpy/plotting/axes.py` (two formatters after `_cursor_theta`; two registry entries)
- Test: `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes: the `_CURSOR_FORMATTERS` registry and formatter signature from Task 2.
- Produces: registry keys `"mixing_ratio"` and `"theta_w"`; the complete five-field registry the spec names.

- [ ] **Step 1: Write the failing tests**

In `tests/plotting/test_axes.py`, after the Task 2 readout tests:

```python
def test_format_coord_metpy_fields(tephigram_axes):
    """Opt-in fields: saturation mixing ratio and the moist adiabat (θw)."""
    x, y = _cursor_xy(850.0, -4.2)
    with config.context(cursor={"fields": ("mixing_ratio", "theta_w")}):
        assert tephigram_axes.format_coord(x, y) == "3.3 g/kg, θw 4.0 °C"


def test_format_coord_unknown_field_raises(tephigram_axes):
    with (
        config.context(cursor={"fields": ("bogus",)}),
        pytest.raises(TypeError, match="unknown cursor field"),
    ):
        tephigram_axes.format_coord(0.0, 0.0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen tests -k "metpy_fields or unknown_field"`
Expected: `test_format_coord_metpy_fields` FAILS with the Task 2 `TypeError` ("unknown cursor field(s) ['mixing_ratio', 'theta_w']"); `test_format_coord_unknown_field_raises` PASSES already (the guard shipped in Task 2 — expected; it pins the message and stays).

- [ ] **Step 3: Write the minimal implementation**

In `src/tephpy/plotting/axes.py`, after `_cursor_theta`:

```python
def _cursor_mixing_ratio(pressure: float, temperature: float, _theta: float) -> str:
    """Format the saturation mixing ratio through the cursor point (§3.2).

    Parameters
    ----------
    pressure : float
        Cursor pressure in hPa.
    temperature : float
        Cursor temperature in degrees Celsius.
    _theta : float
        Ignored; the uniform registry signature.

    Returns
    -------
    str
        The mixing-ratio readout in g/kg, one decimal.
    """
    # Function-local so `import tephpy` stays light (spec §10 item 10).
    from metpy.calc import saturation_mixing_ratio  # noqa: PLC0415
    from metpy.units import units as registry  # noqa: PLC0415

    ratio = saturation_mixing_ratio(
        registry.Quantity(pressure, "hPa"), registry.Quantity(temperature, "degC")
    ).m_as("g/kg")
    return f"{float(ratio):.1f} g/kg"


def _cursor_theta_w(pressure: float, temperature: float, _theta: float) -> str:
    """Format the moist adiabat (θw) through the cursor point (§3.2).

    The point is treated as saturated (``dewpoint=temperature``), giving
    the wet-bulb potential temperature of the pseudoadiabat through it —
    the moist-adiabat family's member value (the §3.2/§3.3
    one-source-of-truth idiom).

    Parameters
    ----------
    pressure : float
        Cursor pressure in hPa.
    temperature : float
        Cursor temperature in degrees Celsius.
    _theta : float
        Ignored; the uniform registry signature.

    Returns
    -------
    str
        The wet-bulb potential-temperature readout, one decimal.
    """
    # Function-local so `import tephpy` stays light (spec §10 item 10).
    from metpy.calc import wet_bulb_potential_temperature  # noqa: PLC0415
    from metpy.units import units as registry  # noqa: PLC0415

    quantity = registry.Quantity
    theta_w = wet_bulb_potential_temperature(
        quantity(pressure, "hPa"),
        quantity(temperature, "degC"),
        quantity(temperature, "degC"),
    ).m_as("degC")
    return f"θw {float(theta_w):.1f} °C"
```

And extend the registry:

```python
_CURSOR_FORMATTERS: Final[dict[str, Callable[[float, float, float], str]]] = {
    "pressure": _cursor_pressure,
    "temperature": _cursor_temperature,
    "theta": _cursor_theta,
    "mixing_ratio": _cursor_mixing_ratio,
    "theta_w": _cursor_theta_w,
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen tests`
Expected: full suite PASSES (the import-cost guard in `tests/test_units.py` confirms metpy stays out of `import tephpy`).

- [ ] **Step 5: Commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
pixi run --frozen git commit -m "Add the opt-in mixing-ratio and theta-w cursor fields"
```

---

### Task 4: Lint, PR, changelog fragment, docs verification

**Files:**
- Create: `changelog/<PR>.enhancement.rst` (number known only after the PR exists)

**Interfaces:**
- Consumes: everything above.
- Produces: the merged-ready PR.

- [ ] **Step 1: Full verification and push**

```bash
pixi run --frozen tests
pixi run --frozen lint
git push -u origin cursor-readout
```

Expected: 461 tests pass (453 before this plan, plus eight added here); every hook passes.

- [ ] **Step 2: Open the PR**

```bash
gh pr create --title "Make the tephigram cursor readout diagram-meaningful" \
  --body "Implements the spec §3.2 cursor readout design (captured in #46, planned in the
docs/superpowers/plans/2026-07-29-tephpy-cursor-readout.md plan): the toolbar readout
inverts the cursor position through the existing transforms and renders the configured
fields in order — default '850 hPa, -4.2 °C, θ 8.6 °C' — from a five-field registry
(pressure, temperature, theta closed-form; mixing_ratio and theta_w opt-in via
function-local metpy.calc). Selection resolves instance assignment > tephpy.config >
_constants; config.cursor.fields is read live per mouse event so config.context scopes
over existing axes; out-of-domain positions blank the toolbar; an unknown field raises
TypeError naming the valid names."
```

Note the PR number `<N>` from the returned URL.

- [ ] **Step 3: Write the changelog fragment**

Create `changelog/<N>.enhancement.rst`:

```rst
The interactive cursor readout (the matplotlib navigation toolbar's
coordinate text) over a tephigram now reports diagram-meaningful values —
``850 hPa, -4.2 °C, θ 8.6 °C`` — instead of the raw rotated (x, y) data
space. ``tephpy.config.cursor.fields`` selects and orders the readout from
a five-field registry (``"pressure"``, ``"temperature"``, ``"theta"``,
``"mixing_ratio"``, ``"theta_w"``), and assigning
:meth:`~matplotlib.axes.Axes.format_coord` remains the stock full-custom
path. (:user:`claude`)
```

- [ ] **Step 4: Verify the fragment with a clean docs build**

Run: `pixi run --frozen docs`
Expected: warning-free; open `docs/_build/html/reference/changelog.html` and confirm the draft entry renders with the `format_coord` cross-reference resolving through intersphinx (matplotlib inventory) and the `@claude` user link.

- [ ] **Step 5: Commit the fragment and push**

```bash
git add changelog/<N>.enhancement.rst
pixi run --frozen git commit -m "Add the changelog fragment for PR #<N>"
git push
```

- [ ] **Step 6: Confirm CI is green**

Run: `gh pr checks <N>` until every check passes (tests on 3.12/3.13/3.14, docs, changelog validation, pre-commit.ci, CodeQL).
