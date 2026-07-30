# Isopleth Member Emphasis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give any member of any isopleth family a distinguishing style through a single
`emphasis=` option, so `ax.isotherms(emphasis={0.0: {}})` draws the freezing isotherm
heavier than its neighbours.

**Architecture:** `emphasis` is one new option on the shared `LineOptions`, so all five
families inherit it through the existing accessor > `tephpy.config` > `_constants`
precedence. It resolves to `dict[float, dict[str, object]]` — member value to style
overrides — and joins **both** `_STYLE_KEYS` (every family accepts it) and
`_GEOMETRY_KEYS` (changing it rebuilds the member cache, because an emphasised value the
zoom ladder would never select is added to the build and forced into the selection). At
draw time the family partitions its selected members into plain-then-emphasised on the
single existing `LineCollection`, whose `color`, `linewidth`, `linestyle` and `alpha` all
accept per-segment sequences. No new artist, no new module, no new public name.

**Tech Stack:** Python 3.12–3.14, matplotlib 3.11 (floor 3.10), numpy, pytest, pytest-mpl,
pixi, pre-commit, towncrier, Sphinx.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-22-tephpy-design.md` §3.2 (the two bullets
  beginning "Any member of any family can be emphasised" and "Emphasis forces its member
  to be drawn"). Cite it as `(spec §3.2)` in comments and docstrings, exactly as the
  surrounding code does.
- Every module starts with the 4-line BSD copyright header and `from __future__ import
  annotations`. Do not add either to files that already have them.
- Line length 88 (`ruff`, `line-length = 88` in `pyproject.toml`).
- Docstrings are numpydoc (`convention = "numpy"`), validated by a `numpydoc-validation`
  pre-commit hook. **Private functions and methods are documented in full too** — see the
  existing `_normalize_labels`. Every parameter, return and raise gets an entry.
- Nothing numeric is hard-coded at point of use; it comes from `_constants` (spec §3.5).
- `TephpyError` and its subclasses are for user-correctable *data* input (spec §6). The
  plotting layer raises builtin `TypeError`/`ValueError`. Do not introduce a tephpy
  exception in this work.
- **Nothing is emphasised by default.** No `_constants` value seeds
  `config.<family>.emphasis`, and no baseline image changes except the new one in Task 5.
- Run a targeted test with `pixi run --frozen pytest <path> -k <expr> -v`. Run the full
  suite with `pixi run --frozen tests` — that task adds `--mpl`, which a bare `pytest`
  does not, so the image comparisons are skipped without it. Run the lint gate with
  `pixi run --frozen lint`. `--frozen` is mandatory — never let pixi re-solve.
- This plan and the spec bullets it implements ship as a docs-only PR on the
  `feature/member-emphasis` branch. The implementation is a separate PR: once that has
  merged, branch `feature/member-emphasis-impl` off an updated `main` and commit there.
  The `feature` prefix is what earns the `type: enhancement` label from
  `.github/workflows/ci-label.yml`. Never commit to `main` (a `no-commit-to-branch`
  pre-commit hook enforces this).

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/tephpy/_constants.py` | Convention defaults | Add `EMPHASIS_LINEWIDTH` |
| `src/tephpy/_config.py` | Typed runtime config sections | Add `LineOptions.emphasis` |
| `src/tephpy/plotting/isopleths.py` | Family artist: resolve, build, select, draw | Add `_EMPHASIS_STYLE_KEYS`, `_close_index`, `_emphasis_number`, `_normalize_emphasis`; modify `_GEOMETRY_KEYS`, `_STYLE_KEYS`, `ResolvedOptions`, `configure`, `_resolve`, `_build`, `_zoom_mask`, `draw`, `_draw_labels`; add `_emphasis_style`, `_member_style` |
| `src/tephpy/plotting/axes.py` | The five family accessors | Add `emphasis=` to `isotherms`, `isobars`, `dry_adiabats`, `moist_adiabats`, `mixing_ratios` |
| `tests/plotting/test_isopleths.py` | Family artist tests | Add 16 |
| `tests/plotting/test_axes.py` | Accessor and projection tests | Add 4 |
| `tests/plotting/test_images.py` | Image baselines | Add 1 |
| `tests/baseline/test_member_emphasis.png` | New baseline | Create (generated) |
| `docs/src/howtos/emphasis.rst` | How-to: emphasise a reference isopleth | Create |
| `docs/src/howtos/index.rst` | How-to index | Add a `toctree` |
| `changelog/<PR>.feature.rst` | Towncrier fragment | Create |

No new modules. `transforms.py`, `calc.py` and `shading.py` are untouched.

---

## Task 1: Resolve and validate `emphasis`

After this task `family.options.emphasis` is a validated, copied
`dict[float, dict[str, object]]` resolving through all three precedence tiers. Nothing
looks different yet — building and drawing come in Tasks 2 and 3.

**Files:**
- Modify: `src/tephpy/_constants.py:139-145`
- Modify: `src/tephpy/_config.py:41-65` (`LineOptions`)
- Modify: `src/tephpy/plotting/isopleths.py:25` (imports), `:38-69` (constant imports),
  `:93-102` (key sets), `:421-439` (`ResolvedOptions`), `:708-767` (`configure`),
  `:860-925` (`_resolve`)
- Test: `tests/plotting/test_isopleths.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `tephpy._constants.EMPHASIS_LINEWIDTH: Final[float] = 1.5`
  - `tephpy._config.LineOptions.emphasis: Mapping[float, Mapping[str, object]] | None`
  - `isopleths._EMPHASIS_STYLE_KEYS: Final[tuple[str, ...]]` —
    `("color", "linewidth", "linestyle", "alpha")`
  - `isopleths._normalize_emphasis(value: object, name: str) -> dict[float, dict[str, object]]`
  - `isopleths.ResolvedOptions.emphasis: dict[float, dict[str, object]]` — `{}` when
    nothing is emphasised

- [ ] **Step 1: Write the failing tests**

Append to `tests/plotting/test_isopleths.py`. `_make_family` and the `plain_axes` fixture
already exist in that file (see `tests/plotting/test_isopleths.py:193-220`).

```python
def test_emphasis_defaults_to_empty():
    """A family emphasises nothing until asked (spec §3.2)."""
    family = _make_family("isotherms")
    assert family.options.emphasis == {}


def test_emphasis_normalizes_keys_to_float():
    family = _make_family("isotherms")
    family.configure(emphasis={0: {}, -20: {"color": "tab:cyan"}})
    assert family.options.emphasis == {0.0: {}, -20.0: {"color": "tab:cyan"}}
    assert all(isinstance(key, float) for key in family.options.emphasis)


def test_emphasis_accepts_every_style_key():
    family = _make_family("isotherms")
    style = {
        "color": "tab:cyan",
        "linewidth": 2.0,
        "linestyle": "--",
        "alpha": 0.5,
    }
    family.configure(emphasis={0.0: style})
    assert family.options.emphasis[0.0] == style


def test_emphasis_snapshot_does_not_alias_the_caller():
    """Mutating the caller's mapping afterwards must not reach the family."""
    family = _make_family("isotherms")
    style = {"color": "tab:cyan"}
    emphasis = {0.0: style}
    family.configure(emphasis=emphasis)
    emphasis[10.0] = {"color": "red"}
    style["color"] = "red"
    assert family.options.emphasis == {0.0: {"color": "tab:cyan"}}


def test_emphasis_none_resets_to_config():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {}})
    family.configure(emphasis=None)
    assert family.options.emphasis == {}


def test_emphasis_empty_mapping_clears_config():
    """An empty mapping is how an accessor clears a config-tier emphasis."""
    with config.context(isotherms={"emphasis": {0.0: {"color": "tab:cyan"}}}):
        family = _make_family("isotherms")
        assert family.options.emphasis == {0.0: {"color": "tab:cyan"}}
        family.configure(emphasis={})
        assert family.options.emphasis == {}


def test_emphasis_config_tier_resolves():
    with config.context(isotherms={"emphasis": {0.0: {"color": "tab:cyan"}}}):
        family = _make_family("isotherms")
        assert family.options.emphasis == {0.0: {"color": "tab:cyan"}}


def test_emphasis_not_a_mapping_raises():
    family = _make_family("isotherms")
    with pytest.raises(TypeError, match="'isotherms' emphasis must be a mapping"):
        family.configure(emphasis=[0.0])


def test_emphasis_non_numeric_key_raises():
    family = _make_family("isotherms")
    with pytest.raises(TypeError, match="member value must be a number"):
        family.configure(emphasis={None: {}})


def test_emphasis_style_not_a_mapping_raises():
    family = _make_family("isotherms")
    with pytest.raises(TypeError, match="must be a mapping of style overrides"):
        family.configure(emphasis={0.0: "tab:cyan"})


def test_emphasis_unknown_style_key_raises():
    family = _make_family("isotherms")
    with pytest.raises(TypeError, match=r"unknown 'isotherms' emphasis style key"):
        family.configure(emphasis={0.0: {"colour": "tab:cyan"}})


@pytest.mark.parametrize("linewidth", [0.0, -1.0, float("inf")])
def test_emphasis_bad_linewidth_raises(linewidth):
    family = _make_family("isotherms")
    with pytest.raises(ValueError, match="must be a positive, finite number"):
        family.configure(emphasis={0.0: {"linewidth": linewidth}})


@pytest.mark.parametrize("alpha", [-0.1, 1.1])
def test_emphasis_bad_alpha_raises(alpha):
    family = _make_family("isotherms")
    with pytest.raises(ValueError, match="must be between 0 and 1"):
        family.configure(emphasis={0.0: {"alpha": alpha}})


def test_emphasis_failure_leaves_family_unchanged():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"color": "tab:cyan"}})
    with pytest.raises(TypeError):
        family.configure(emphasis={0.0: {"colour": "red"}})
    assert family.options.emphasis == {0.0: {"color": "tab:cyan"}}


def test_emphasis_is_a_geometry_key():
    """Changing emphasis invalidates the cached member geometry (spec §3.2)."""
    family = _make_family("isotherms")
    family._build()
    assert family._members is not None
    family.configure(emphasis={0.0: {}})
    assert family._members is None


def test_emphasis_accepted_by_every_family():
    for name in (
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
    ):
        family = _make_family(name)
        family.configure(emphasis={0.0: {}})
        assert family.options.emphasis == {0.0: {}}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -k emphasis -v`
Expected: FAIL — `TypeError: unknown option(s) ['emphasis'] for 'isotherms'`

- [ ] **Step 3: Add the constant**

In `src/tephpy/_constants.py`, insert after `ISOPLETH_ALPHA` (currently line 142) and
before `#: Isotherm draw order.`:

```python
#: Line width in points for an emphasised isopleth member (spec §3.2). Emphasis
#: follows the monochrome printed-chart idiom -- same ink, heavier line -- so a
#: distinguished member needs no colour convention; a call supplies ``color`` to
#: override that.
EMPHASIS_LINEWIDTH: Final[float] = 1.5
```

- [ ] **Step 4: Add the config field**

In `src/tephpy/_config.py`, append to `LineOptions` after the `visible` field. The `#:`
comment idiom is what every field in that file already uses — match it, do not switch to
a numpydoc `Attributes` block:

```python
    #: Members drawn with a distinguishing style, keyed by member value in the
    #: family's native units. Each value is a mapping of style overrides --
    #: ``color``, ``linewidth``, ``linestyle`` and ``alpha`` -- and an omitted
    #: key falls back to the family's own style, so ``{0.0: {}}`` is the 0 °C
    #: member at ``EMPHASIS_LINEWIDTH`` in the family's own colour. An emphasised
    #: member is always drawn, whatever the zoom ladder would select. An empty
    #: mapping emphasises nothing (spec §3.2).
    emphasis: Mapping[float, Mapping[str, object]] | None = None
```

`Mapping` is already imported at `_config.py:17`. No import change.

- [ ] **Step 5: Add the normaliser to `isopleths.py`**

Widen the `collections.abc` import at `isopleths.py:25`:

```python
from collections.abc import Iterable, Mapping
```

Add `EMPHASIS_LINEWIDTH` to the `tephpy._constants` import block (it is alphabetically
first, before `ISOBAR_COLOR`; the block is sorted by `ruff`'s isort):

```python
from tephpy._constants import (
    DRY_ADIABAT_COLOR,
    DRY_ADIABAT_STEPS,
    DRY_ADIABAT_ZORDER,
    EMPHASIS_LINEWIDTH,
    ISOBAR_COLOR,
    ...
```

Replace the two key-set constants at `isopleths.py:93-99`:

```python
#: Options that require rebuilding the cached member geometry when changed.
#: ``emphasis`` is here as well as in the style keys because an emphasised value
#: the zoom ladder would never select is added to the build (spec §3.2).
_GEOMETRY_KEYS: Final[frozenset[str]] = frozenset(
    {"values", "interval", "truncation", "emphasis"}
)

#: Style and visibility options shared by every family.
_STYLE_KEYS: Final[frozenset[str]] = frozenset(
    {"color", "linewidth", "alpha", "labels", "visible", "emphasis"}
)
```

Add after `EDGES` (currently `isopleths.py:105`):

```python
#: Style keys one emphasised member may override; an omitted key falls back to
#: the family's own style (spec §3.2).
_EMPHASIS_STYLE_KEYS: Final[tuple[str, ...]] = (
    "color",
    "linewidth",
    "linestyle",
    "alpha",
)

#: Tolerance for matching a member value against an emphasis key. ``abs_tol``
#: carries the 0 °C case, where a relative tolerance alone matches nothing.
_EMPHASIS_RTOL: Final[float] = 1e-9
_EMPHASIS_ATOL: Final[float] = 1e-9
```

Add these two free functions immediately after `_normalize_labels`
(currently ending at `isopleths.py:224`):

```python
def _emphasis_number(value: object, key: str, name: str, member: float) -> float:
    """Validate one numeric style override on an emphasised member.

    Parameters
    ----------
    value : object
        The resolved override value.
    key : str
        The style key, ``"linewidth"`` or ``"alpha"``.
    name : str
        The family name, for the error message.
    member : float
        The member value the style belongs to, for the error message.

    Returns
    -------
    float
        The validated number.

    Raises
    ------
    TypeError
        If `value` is not a number.
    ValueError
        If a ``linewidth`` is not positive and finite, or an ``alpha`` falls
        outside ``[0, 1]``.
    """
    try:
        number = float(cast("SupportsFloat", value))
    except (TypeError, ValueError) as err:
        msg = (
            f"{name!r} emphasis {key!r} for member {member:g} must be a "
            f"number: {value!r}"
        )
        raise TypeError(msg) from err
    if key == "linewidth":
        valid = number > 0.0 and math.isfinite(number)
        expected = "a positive, finite number"
    else:
        valid = 0.0 <= number <= 1.0
        expected = "between 0 and 1"
    if not valid:
        msg = (
            f"{name!r} emphasis {key!r} for member {member:g} must be "
            f"{expected}: {number!r}"
        )
        raise ValueError(msg)
    return number


def _normalize_emphasis(value: object, name: str) -> dict[float, dict[str, object]]:
    """Validate and copy a raw ``emphasis`` option (spec §3.2).

    Keys become floats and each style mapping is copied into a fresh dict, so
    the family's snapshot never aliases a mapping the caller can still mutate --
    the same reason ``values`` materialises a generator to a tuple. ``color`` and
    ``linestyle`` are left to matplotlib to validate at draw time, exactly as the
    family-level ``color`` already is.

    Parameters
    ----------
    value : object
        The resolved ``emphasis`` option, from any precedence tier.
    name : str
        The family name, for the error messages.

    Returns
    -------
    dict of float to dict of str to object
        Member value mapped to its validated style overrides; empty when
        nothing is emphasised.

    Raises
    ------
    TypeError
        If `value` is not a mapping, a key is not a number, a style is not a
        mapping, or a style names a key outside :data:`_EMPHASIS_STYLE_KEYS`.
    ValueError
        If a ``linewidth`` or ``alpha`` override is out of range.
    """
    if not isinstance(value, Mapping):
        msg = (
            f"{name!r} emphasis must be a mapping of member value to style "
            f"overrides, not {type(value).__name__}"
        )
        raise TypeError(msg)
    emphasis: dict[float, dict[str, object]] = {}
    for raw_member, raw_style in cast("Mapping[object, object]", value).items():
        try:
            member = float(cast("SupportsFloat", raw_member))
        except (TypeError, ValueError) as err:
            msg = (
                f"{name!r} emphasis member value must be a number: {raw_member!r}"
            )
            raise TypeError(msg) from err
        if not isinstance(raw_style, Mapping):
            msg = (
                f"{name!r} emphasis style for member {member:g} must be a mapping "
                f"of style overrides, not {type(raw_style).__name__}"
            )
            raise TypeError(msg)
        style = dict(cast("Mapping[str, object]", raw_style))
        unknown = set(style) - set(_EMPHASIS_STYLE_KEYS)
        if unknown:
            msg = (
                f"unknown {name!r} emphasis style key(s) {sorted(unknown)!r} for "
                f"member {member:g}; expected {list(_EMPHASIS_STYLE_KEYS)!r}"
            )
            raise TypeError(msg)
        for key in ("linewidth", "alpha"):
            if key in style:
                style[key] = _emphasis_number(style[key], key, name, member)
        emphasis[member] = style
    return emphasis
```

- [ ] **Step 6: Wire it into `ResolvedOptions`, `configure` and `_resolve`**

In `ResolvedOptions` (`isopleths.py:421-439`), append a field after `visible` and extend
the class docstring:

```python
@dataclasses.dataclass(frozen=True)
class ResolvedOptions:
    """A family's fully resolved settings snapshot.

    Resolution precedence: accessor kwargs > ``tephpy.config`` >
    ``_constants`` (spec §3.5). ``values``/``interval`` of ``None`` mean the
    zoom-adaptive default ladder is in force. An empty `label_edges` means
    the family labels inline only, and an empty `emphasis` means no member is
    distinguished. The class is frozen against rebinding; `emphasis` is a plain
    dict the family owns outright, copied from the caller's mapping when it
    resolves.
    """

    values: tuple[float, ...] | None
    interval: float | None
    truncation: float | None
    color: str
    linewidth: float
    alpha: float
    labels: bool
    label_edges: tuple[str, ...]
    visible: bool
    emphasis: dict[float, dict[str, object]]
```

In `configure` (`isopleths.py:740-752`), extend the materialisation branch so a bad
mapping raises before `self._overrides` is replaced — the existing rollback contract:

```python
        for key, value in kwargs.items():
            if value is None:
                overrides.pop(key, None)
            else:
                # Materialize one-shot iterables (e.g., generators) to tuple
                # so they survive later reconfigures (spec §3.5, §7 item 1),
                # and copy an emphasis mapping for the same reason.
                if key == "values":
                    override_value: object = tuple(
                        float(v) for v in cast("Iterable[SupportsFloat]", value)
                    )
                elif key == "emphasis":
                    override_value = _normalize_emphasis(value, self._spec.name)
                else:
                    override_value = value
                overrides[key] = override_value
```

Also add to `configure`'s `Raises` section, under the existing `TypeError` entry, the
clause `, or if ``emphasis`` is malformed`.

In `_resolve` (`isopleths.py:860-925`), add after the `raw_visible`/`visible` lines:

```python
        raw_emphasis = pick("emphasis")
        emphasis = (
            {} if raw_emphasis is None else _normalize_emphasis(raw_emphasis, spec.name)
        )
```

and pass it in the `ResolvedOptions(...)` call, after `visible=visible`:

```python
            visible=visible,
            emphasis=emphasis,
        )
```

Extend `_resolve`'s `Raises` section so the `TypeError` entry reads
`If the resolved ``labels`` names an unknown placement, or ``emphasis`` is malformed.`

Two things to get right here, both easy to break:

- **Test for `None`, never for truthiness.** `_pick` (`isopleths.py:855-858`) returns
  `self._overrides.get(key)` and only falls through to the config section when that is
  `None`. An empty dict is not `None`, so `configure(emphasis={})` correctly shadows a
  config-tier emphasis with "emphasise nothing", while `configure(emphasis=None)` pops
  the override and falls back. Writing `if not raw_emphasis` instead of
  `if raw_emphasis is None` silently makes `{}` fall through to the config value and
  breaks `test_emphasis_empty_mapping_clears_config`.
- **Normalising twice is intended.** `configure` normalises to validate early and to copy
  the accessor's mapping; `_resolve` normalises again because the value may have come from
  the config tier instead, which `configure` never touches. The function is idempotent, so
  the second pass costs one small dict rebuild and guarantees the snapshot never aliases a
  live `tephpy.config` mapping either.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -k emphasis -v`
Expected: PASS (17 tests, counting the parametrized cases)

- [ ] **Step 8: Run the full suite and the gate**

Run: `pixi run --frozen tests`
Expected: PASS, no regressions.

Run: `pixi run --frozen lint`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/tephpy/_constants.py src/tephpy/_config.py \
        src/tephpy/plotting/isopleths.py tests/plotting/test_isopleths.py
git commit -m "feat: resolve and validate isopleth member emphasis"
```

---

## Task 2: Force emphasised members into the built and selected set

After this task an emphasised value is always built and always drawn, whatever the zoom
ladder would pick — the property that lets `emphasis` double as the reference-line
mechanism. Styling still comes in Task 3, so the forced member currently draws in the
family's ordinary style.

**Files:**
- Modify: `src/tephpy/plotting/isopleths.py` — add `_close_index` (module level) and
  `_emphasis_style` (method); modify `__init__` (`:645-693`), `_build` (`:969-992`),
  `_zoom_mask` (`:994-1025`)
- Test: `tests/plotting/test_isopleths.py`

**Interfaces:**
- Consumes: `ResolvedOptions.emphasis` and `_EMPHASIS_RTOL`/`_EMPHASIS_ATOL` from Task 1.
- Produces:
  - `isopleths._close_index(values, targets) -> npt.NDArray[np.int64]` — for each entry of
    `values`, the index of the first `targets` entry it matches within tolerance, else
    `-1`.
  - `IsoplethFamily._emphasis_style(value: float) -> dict[str, object] | None` — the
    emphasis overrides for one member value, or `None` when it is not emphasised. Task 3
    consumes this.
  - `IsoplethFamily._member_extra: npt.NDArray[np.bool_]` — per cached member, whether it
    exists *only* because emphasis asked for it.

- [ ] **Step 1: Write the failing tests**

The test values are chosen against the real ladders — do not substitute others without
rechecking these. `ISOTHERM_STEPS` is `((500, 20), (100, 10), (0, 5))`, so the canonical
isotherm members sit at the finest step, 5 °C: **−12 °C is not a member at all**, while
**5 °C is a member the 20 °C step at a 600-unit view width drops**. `MIXING_RATIO_VALUES`
runs `0.05, 0.1, 0.2, 0.5, 1, 1.5, 2, 3, 4, 5, 7, …` — **6 g/kg is not in it**, so it is
an emphasis-only addition landing mid-list, exactly where a naive stride would shift.
`TEMPERATURE_DOMAIN` is `(-120, 60)`.

Append to `tests/plotting/test_isopleths.py`:

```python
def test_emphasis_adds_an_off_ladder_member():
    """-12 °C is on no isotherm ladder step, so emphasis must build it."""
    family = _make_family("isotherms")
    family.configure(emphasis={-12.0: {}})
    family._build()
    assert np.any(np.isclose(family._member_values, -12.0))


def test_emphasis_does_not_duplicate_an_existing_member():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {}})
    family._build()
    assert np.count_nonzero(np.isclose(family._member_values, 0.0)) == 1


def test_emphasis_marks_only_the_added_member_as_extra():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {}, -12.0: {}})
    family._build()
    extra = family._member_values[family._member_extra]
    np.testing.assert_allclose(extra, [-12.0])


def test_emphasis_forces_an_off_ladder_member_into_the_zoom_mask():
    family = _make_family("isotherms")
    family.configure(emphasis={-12.0: {}})
    family._build()
    selected = family._member_values[family._zoom_mask(600.0)]
    assert np.any(np.isclose(selected, -12.0))


def test_emphasis_forces_an_on_grid_member_the_ladder_would_drop():
    """5 °C is a canonical member but not a 20 °C ladder step."""
    family = _make_family("isotherms")
    family.configure(emphasis={5.0: {}})
    family._build()
    selected = family._member_values[family._zoom_mask(600.0)]
    assert np.any(np.isclose(selected, 5.0))
    plain = _make_family("isotherms")
    plain._build()
    assert not np.any(np.isclose(plain._member_values[plain._zoom_mask(600.0)], 5.0))


def test_emphasis_does_not_shift_the_mixing_ratio_stride():
    """A list family strides by canonical position, so an addition cannot shift it."""
    plain = _make_family("mixing_ratios")
    plain._build()
    emphasised = _make_family("mixing_ratios")
    emphasised.configure(emphasis={6.0: {}})
    emphasised._build()
    for width in (600.0, 300.0, 100.0):
        expected = plain._member_values[plain._zoom_mask(width)]
        got = emphasised._member_values[emphasised._zoom_mask(width)]
        np.testing.assert_allclose(got[~np.isclose(got, 6.0)], expected)
        assert np.any(np.isclose(got, 6.0))


def test_emphasis_respects_the_view_mask(plain_axes):
    """An emphasised member off screen stays off screen (spec §3.2)."""
    family = _make_family("isotherms")
    family.configure(emphasis={-100.0: {}})
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    drawn = [m.value for m in family._selected_members()]
    assert not any(math.isclose(value, -100.0) for value in drawn)


def test_emphasis_outside_the_domain_is_a_silent_no_op():
    """``TEMPERATURE_DOMAIN`` ends at 60 °C, so 200 °C is built but never shown."""
    family = _make_family("isotherms")
    family.configure(emphasis={200.0: {}})
    family._build()
    view = mtransforms.Bbox.from_extents(1591.0, 1671.0, 1902.0, 1822.0)
    assert not np.any(family._view_mask(view) & np.isclose(family._member_values, 200.0))


def test_emphasis_style_lookup_matches_within_tolerance():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"color": "tab:cyan"}})
    assert family._emphasis_style(0.0) == {"color": "tab:cyan"}
    assert family._emphasis_style(1e-12) == {"color": "tab:cyan"}
    assert family._emphasis_style(10.0) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -k "emphasis and (ladder or stride or extra or view or domain or style_lookup or duplicate)" -v`
Expected: FAIL — `AttributeError: 'IsoplethFamily' object has no attribute '_member_extra'`
for the first, and assertion failures for the rest.

- [ ] **Step 3: Add the `_close_index` helper**

Add at module level in `isopleths.py`, immediately after `_normalize_emphasis`:

```python
def _close_index(
    values: npt.NDArray[np.float64], targets: npt.NDArray[np.float64]
) -> npt.NDArray[np.int64]:
    """Match each value against a target list within the emphasis tolerance.

    Member values are floats built by arithmetic over a ladder interval, and
    emphasis keys are floats a user typed, so the two are compared with a
    tolerance rather than for equality.

    Parameters
    ----------
    values : numpy.ndarray
        The values to match, shape ``(n,)``.
    targets : numpy.ndarray
        The values to match against, shape ``(m,)``.

    Returns
    -------
    numpy.ndarray
        Shape ``(n,)`` of int64: the index into `targets` of the first match
        for each value, or ``-1`` where there is none.
    """
    if values.size == 0 or targets.size == 0:
        return np.full(values.size, -1, dtype=np.int64)
    close = np.isclose(
        values[:, None], targets[None, :], rtol=_EMPHASIS_RTOL, atol=_EMPHASIS_ATOL
    )
    return np.asarray(
        np.where(close.any(axis=1), close.argmax(axis=1), -1), dtype=np.int64
    )
```

- [ ] **Step 4: Initialise the new cache attribute**

In `IsoplethFamily.__init__` (`isopleths.py:683-684`), add alongside the other member
caches:

```python
        self._member_values: npt.NDArray[np.float64] = np.empty(0)
        self._member_bboxes: npt.NDArray[np.float64] = np.empty((0, 4))
        self._member_extra: npt.NDArray[np.bool_] = np.empty(0, dtype=bool)
```

- [ ] **Step 5: Union the emphasis keys into the build**

Replace `_build` (`isopleths.py:969-992`) with:

```python
    def _build(self) -> None:
        """Build and cache the member polylines, boxes and emphasis marks.

        Emphasised values the canonical set does not already carry are appended
        to the build, so a member the zoom ladder would never select still
        exists to be forced in by :meth:`_zoom_mask` (spec §3.2). Which members
        those are is recorded, because a list family strides by member index and
        an addition must not shift that phase.
        """
        opts = self._options
        canonical = self._candidate_values()
        keys = np.asarray(sorted(opts.emphasis), dtype=np.float64)
        extra = keys[_close_index(keys, canonical) < 0]
        members = self._spec.builder(
            np.concatenate([canonical, extra]), opts.truncation
        )
        self._members = members
        self._member_values = np.array(
            [member.value for member in members], dtype=np.float64
        )
        # By value, not by build position: a builder may drop members (the moist
        # adiabats truncate), so positions do not survive the round trip.
        self._member_extra = np.asarray(
            _close_index(self._member_values, extra) >= 0
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
```

- [ ] **Step 6: Force emphasised members through the zoom mask**

Replace `_zoom_mask` (`isopleths.py:994-1025`) with:

```python
    def _zoom_mask(self, width: float) -> npt.NDArray[np.bool_]:
        """Select members for the zoom level via the convention ladder.

        An emphasised member is always selected, whatever the ladder would pick
        — that is what lets emphasis mark a reference isopleth the interval
        never lands on (spec §3.2). A list family strides by member index, so
        the stride runs over the canonical members by their canonical position
        and an emphasis-only addition cannot shift its phase.

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
        extra = self._member_extra
        if extra.size != count:
            extra = np.zeros(count, dtype=bool)
        keys = np.asarray(sorted(self._options.emphasis), dtype=np.float64)
        forced = np.asarray(_close_index(self._member_values, keys) >= 0)
        spec = self._spec
        if spec.steps is not None:
            step = spec.steps[-1][1]
            for min_width, ladder_step in spec.steps:
                if width >= min_width:
                    step = ladder_step
                    break
            ratio = self._member_values / step
            mask = np.asarray(np.abs(ratio - np.round(ratio)) < 1e-6)
            return np.asarray(mask | forced)
        stride = 1
        if spec.strides is not None:
            for min_width, ladder_stride in spec.strides:
                if width >= min_width:
                    stride = ladder_stride
                    break
        # Position among the canonical members, so an emphasis-only addition
        # never shifts which members the stride picks.
        position = np.cumsum(~extra) - 1
        mask = np.asarray((position % stride) == 0) & ~extra
        return np.asarray(mask | forced)
```

- [ ] **Step 7: Add the style lookup**

Add as a method on `IsoplethFamily`, immediately after `_zoom_mask`:

```python
    def _emphasis_style(self, value: float) -> dict[str, object] | None:
        """Return the emphasis overrides for one member value.

        Parameters
        ----------
        value : float
            The member's isopleth value in the family's native units.

        Returns
        -------
        dict of str to object or None
            The member's style overrides, or ``None`` when it is not
            emphasised.
        """
        emphasis = self._options.emphasis
        if not emphasis:
            return None
        for key, style in emphasis.items():
            if math.isclose(
                key, value, rel_tol=_EMPHASIS_RTOL, abs_tol=_EMPHASIS_ATOL
            ):
                return style
        return None
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -k emphasis -v`
Expected: PASS.

- [ ] **Step 9: Run the full suite and the gate**

Run: `pixi run --frozen tests`
Expected: PASS. In particular `test_isobar_zoom_ladder_masks` and
`test_mixing_ratio_stride_masks` (`tests/plotting/test_isopleths.py:246-267`) must be
unchanged — with no emphasis, `forced` is all-False and `extra` is all-False, so
`position` equals `np.arange(count)` and both branches reduce to their prior behaviour.

Run: `pixi run --frozen lint`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/tephpy/plotting/isopleths.py tests/plotting/test_isopleths.py
git commit -m "feat: force emphasised isopleth members into the drawn set"
```

---

## Task 3: Draw emphasised members with their own style, last

After this task emphasis is visible: the emphasised member draws at
`EMPHASIS_LINEWIDTH` in the family's own colour by default, above its own family's
neighbours, and its inline label matches.

**Files:**
- Modify: `src/tephpy/plotting/isopleths.py` — add `_member_style` and `_order_members`;
  modify `draw` (`:811-839`) and `_draw_labels` (`:1133-1182`)
- Test: `tests/plotting/test_isopleths.py`

**Interfaces:**
- Consumes: `_emphasis_style` from Task 2, `EMPHASIS_LINEWIDTH` from Task 1.
- Produces:
  - `IsoplethFamily._member_style(value: float) -> dict[str, object]` — the fully
    resolved per-member draw style, keys `color`, `linewidth`, `linestyle`, `alpha`.
  - `IsoplethFamily._order_members(selected: list[Member]) -> list[Member]` — the same
    members, emphasised ones last.

Note that `_selected_members` and `_inline_members` keep their current signatures. Style
is looked up by member *value*, not by index, so nothing in `tests/plotting/test_axes.py`
or the existing `tests/plotting/test_isopleths.py` selection tests needs changing.

- [ ] **Step 1: Write the failing tests**

Append to `tests/plotting/test_isopleths.py`:

```python
def test_member_style_defaults_to_the_family_style():
    family = _make_family("isotherms")
    style = family._member_style(10.0)
    assert style == {
        "color": ISOTHERM_COLOR,
        "linewidth": ISOPLETH_LINEWIDTH,
        "linestyle": "solid",
        "alpha": ISOPLETH_ALPHA,
    }


def test_member_style_empty_emphasis_only_thickens():
    """`{}` is the printed-chart idiom: same ink, heavier line (spec §3.2)."""
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {}})
    style = family._member_style(0.0)
    assert style["color"] == ISOTHERM_COLOR
    assert style["linewidth"] == EMPHASIS_LINEWIDTH


def test_member_style_overrides_win_over_the_emphasis_default():
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"color": "tab:cyan", "linewidth": 3.0}})
    style = family._member_style(0.0)
    assert style["color"] == "tab:cyan"
    assert style["linewidth"] == 3.0


def test_emphasised_member_draws_last(plain_axes):
    """Emphasis wins against its own family's neighbours (spec §3.2)."""
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {}})
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    segments = family._lines.get_segments()
    assert len(segments) > 1
    # An isotherm is vertical in (temperature, theta), so every vertex shares
    # the member's temperature; the emphasised member is the final segment.
    widths = family._lines.get_linewidth()
    assert widths[-1] == EMPHASIS_LINEWIDTH
    assert set(widths[:-1]) == {ISOPLETH_LINEWIDTH}


def test_emphasised_member_gets_per_segment_properties(plain_axes):
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"color": "tab:cyan", "linestyle": "--"}})
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    lines = family._lines
    colors = lines.get_color()
    assert len(colors) == len(lines.get_segments())
    np.testing.assert_allclose(colors[-1], mcolors.to_rgba("tab:cyan"))
    np.testing.assert_allclose(colors[0], mcolors.to_rgba(ISOTHERM_COLOR))
    assert len(lines.get_linestyle()) == len(lines.get_segments())


def test_plain_family_still_draws_one_colour(plain_axes):
    """With nothing emphasised the collection is uniform, as before."""
    family = _make_family("isotherms")
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    colors = family._lines.get_color()
    assert len({tuple(row) for row in colors}) == 1
    assert set(family._lines.get_linewidth()) == {ISOPLETH_LINEWIDTH}


def test_emphasised_label_takes_the_emphasis_colour(plain_axes):
    """Exactly one label carries the emphasis colour: the emphasised member's."""
    family = _make_family("isotherms")
    family.configure(emphasis={0.0: {"color": "tab:cyan"}})
    plain_axes.add_artist(family)
    plain_axes.figure.canvas.draw()
    colors = [mcolors.to_rgba(text.get_color()) for text in family._texts]
    assert colors.count(mcolors.to_rgba("tab:cyan")) == 1
```

`0.0` is safe to emphasise on `plain_axes`: at the default extent the isotherm ladder
selects 19 members from −120 °C to 60 °C at the 10 °C step (see
`test_selected_and_inline_members_at_the_default_extent`), so 0 °C is drawn already and
these tests measure emphasis rather than forcing.

Add `matplotlib.colors as mcolors`, `EMPHASIS_LINEWIDTH` and `ISOPLETH_LINEWIDTH` to the
imports at the top of `tests/plotting/test_isopleths.py`:

```python
import matplotlib.colors as mcolors
```

```python
from tephpy._constants import (
    EMPHASIS_LINEWIDTH,
    ISOPLETH_ALPHA,
    ISOPLETH_LINEWIDTH,
    ISOPLETH_SAMPLES,
    ISOTHERM_COLOR,
    MIXING_RATIO_VALUES,
    MOIST_ADIABAT_TRUNCATION,
)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -k "member_style or emphasised or plain_family" -v`
Expected: FAIL — `AttributeError: 'IsoplethFamily' object has no attribute '_member_style'`

- [ ] **Step 3: Add `_member_style`**

Add as a method on `IsoplethFamily`, immediately after `_emphasis_style`:

```python
    def _member_style(self, value: float) -> dict[str, object]:
        """Return the style one member draws with.

        The family's own resolved style, with an emphasised member's overrides
        applied over it. Emphasis with no overrides still thickens the line to
        ``EMPHASIS_LINEWIDTH`` — the monochrome printed-chart idiom of same ink,
        heavier line (spec §3.2).

        Parameters
        ----------
        value : float
            The member's isopleth value in the family's native units.

        Returns
        -------
        dict of str to object
            Keys ``color``, ``linewidth``, ``linestyle`` and ``alpha``.
        """
        opts = self._options
        style: dict[str, object] = {
            "color": opts.color,
            "linewidth": opts.linewidth,
            "linestyle": "solid",
            "alpha": opts.alpha,
        }
        override = self._emphasis_style(value)
        if override is not None:
            style["linewidth"] = EMPHASIS_LINEWIDTH
            style.update(override)
        return style
```

- [ ] **Step 4: Partition and style the draw**

Replace the body of `draw` (`isopleths.py:820-839`) from `if not self.get_visible():`
onwards with:

```python
        if not self.get_visible():
            return
        axes = self.axes
        if axes is None:
            return
        opts = self._options
        selected = self._order_members(self._selected_members())
        renderer.open_group("isopleth-family", gid=self.get_gid())
        lines = self._lines
        lines.set_segments([m.xy for m in selected])
        if selected:
            styles = [self._member_style(m.value) for m in selected]
            lines.set_color([style["color"] for style in styles])
            lines.set_linewidth([style["linewidth"] for style in styles])
            lines.set_linestyle([style["linestyle"] for style in styles])
            lines.set_alpha([style["alpha"] for style in styles])
        else:
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
```

Add the ordering helper immediately after `_member_style`:

```python
    def _order_members(self, selected: list[Member]) -> list[Member]:
        """Order the drawn members plain first, emphasised last.

        Draw order stays inside the family: an emphasised member wins against
        its own family's neighbours, while the families drawn above this one
        still cross it (spec §3.2).

        Parameters
        ----------
        selected : list of Member
            The members the view and zoom ladder selected, in build order.

        Returns
        -------
        list of Member
            The same members, emphasised ones moved to the end in build order.
        """
        if not self._options.emphasis:
            return selected
        plain = [m for m in selected if self._emphasis_style(m.value) is None]
        emphasised = [m for m in selected if self._emphasis_style(m.value) is not None]
        return plain + emphasised
```

- [ ] **Step 5: Style the inline labels**

In `_draw_labels` (`isopleths.py:1155-1182`), replace the two lines that set the label
colour and alpha from the family options:

```python
            text.set_color(opts.color)
            text.set_alpha(opts.alpha)
```

with a per-member lookup:

```python
            style = self._member_style(member.value)
            text.set_color(cast("str", style["color"]))
            text.set_alpha(cast("float", style["alpha"]))
```

`opts` is still used for `opts.label_edges` via `_inline_members`, so leave the
`opts = self._options` line in place. Update the `_draw_labels` summary paragraph to note
that an emphasised member's label takes the emphasis colour and alpha.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_isopleths.py -v`
Expected: PASS.

- [ ] **Step 7: Run the full suite and the gate**

Run: `pixi run --frozen tests`
Expected: PASS. The existing image baselines must still match — with no emphasis
configured, `_order_members` returns its input unchanged and the per-segment sequences
are uniform, so the rendering is identical.

Run: `pixi run --frozen lint`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/tephpy/plotting/isopleths.py tests/plotting/test_isopleths.py
git commit -m "feat: draw emphasised isopleth members with their own style"
```

---

## Task 4: Expose `emphasis=` on the five accessors

After this task the feature is reachable from the public API:
`ax.isotherms(emphasis={0.0: {}})`.

**Files:**
- Modify: `src/tephpy/plotting/axes.py:1402-1465` (`isotherms`), `:1466-1529` (`isobars`),
  `:1530-1594` (`dry_adiabats`), `:1595-1663` (`moist_adiabats`), `:1664-1726`
  (`mixing_ratios`)
- Test: `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes: everything from Tasks 1–3.
- Produces: `emphasis: Mapping[float, Mapping[str, object]] | None = None` as a
  keyword-only argument on all five accessors, threaded through the existing
  `_configure_family` dict.

- [ ] **Step 1: Write the failing tests**

Append to `tests/plotting/test_axes.py`:

```python
def test_accessor_emphasis_reaches_the_family(tephigram_axes):
    family = tephigram_axes.isotherms(emphasis={0.0: {"color": "tab:cyan"}})
    assert family.options.emphasis == {0.0: {"color": "tab:cyan"}}


def test_accessor_emphasis_available_on_every_family(tephigram_axes):
    for name in (
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
    ):
        family = getattr(tephigram_axes, name)(emphasis={0.0: {}})
        assert family.options.emphasis == {0.0: {}}


def test_accessor_emphasis_error_propagates(tephigram_axes):
    with pytest.raises(TypeError, match="emphasis style key"):
        tephigram_axes.isotherms(emphasis={0.0: {"colour": "red"}})


def test_emphasis_forced_member_reaches_the_edge_ticks(tephigram_axes):
    """A forced member is ticked like any other (spec §3.2)."""
    tephigram_axes.isotherms(labels="bottom", emphasis={-12.0: {}})
    tephigram_axes.figure.canvas.draw()
    labels = [
        text.get_text() for text in tephigram_axes.xaxis.get_ticklabels()
    ]
    assert "-12" in labels
```

The `tephigram_axes` fixture already exists at `tests/plotting/test_axes.py:98`. Do not
add a fixture.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -k emphasis -v`
Expected: FAIL — `TypeError: isotherms() got an unexpected keyword argument 'emphasis'`

- [ ] **Step 3: Add the keyword to all five accessors**

For **each** of `isotherms`, `isobars`, `dry_adiabats`, `moist_adiabats` and
`mixing_ratios`, make three edits.

First, add the parameter to the signature, after `labels` and before `visible`:

```python
        labels: bool | str | tuple[str, ...] | None = None,
        emphasis: Mapping[float, Mapping[str, object]] | None = None,
        visible: bool | None = None,
```

Second, add the numpydoc entry to `Parameters`, after the `labels` entry and before
`visible` — the same text in all five, with the unit phrase matching the family
(`degrees Celsius` for `isotherms` and `dry_adiabats`, `hPa` for `isobars`,
`degrees Celsius` for `moist_adiabats`, `g/kg` for `mixing_ratios`):

```
        emphasis : mapping of float to mapping, optional
            Members to distinguish, keyed by member value in degrees Celsius.
            Each value is a mapping of style overrides — ``color``,
            ``linewidth``, ``linestyle``, ``alpha`` — and an omitted key falls
            back to the family's own style, so ``{0.0: {}}`` draws that member
            at ``EMPHASIS_LINEWIDTH`` in the family's own colour. An emphasised
            member is always drawn, whatever the zoom ladder would select, so a
            value the interval never lands on still appears. An empty mapping
            emphasises nothing.
```

Third, add it to the dict passed to `_configure_family`, after `"labels"`:

```python
                "labels": labels,
                "emphasis": emphasis,
                "visible": visible,
```

Also extend each accessor's `Raises` `TypeError` entry to read
`If ``labels`` names an unknown placement, ``emphasis`` is malformed, or an edge another
family already claims.` and each `ValueError` entry — where one exists — to mention an
out-of-range emphasis ``linewidth``/``alpha``. Where an accessor has no `ValueError`
entry, add one:

```
        ValueError
            If an ``emphasis`` ``linewidth`` is not positive and finite, or an
            ``alpha`` falls outside ``[0, 1]``.
```

No import change is needed: `axes.py:81` already has
`from collections.abc import Callable, Iterable, Mapping` under `TYPE_CHECKING`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_axes.py -k emphasis -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite and the gate**

Run: `pixi run --frozen tests`
Expected: PASS.

Run: `pixi run --frozen lint`
Expected: PASS. `numpydoc-validation` checks that every parameter is documented in the
same order as the signature — if it complains, the `emphasis` entry is in the wrong place
relative to `labels`/`visible`.

- [ ] **Step 6: Commit**

```bash
git add src/tephpy/plotting/axes.py tests/plotting/test_axes.py
git commit -m "feat: accept emphasis on every isopleth family accessor"
```

---

## Task 5: Baseline image, how-to and changelog

The rendering proof, the user-facing documentation, and the release note.

**Files:**
- Modify: `tests/plotting/test_images.py`
- Create: `tests/baseline/test_member_emphasis.png` (generated, not hand-written)
- Create: `docs/src/howtos/emphasis.rst`
- Modify: `docs/src/howtos/index.rst`
- Create: `changelog/<PR>.feature.rst`

**Interfaces:**
- Consumes: the public `emphasis=` keyword from Task 4.
- Produces: nothing later tasks rely on.

- [ ] **Step 1: Add the image test**

Append to `tests/plotting/test_images.py`, after the existing family tests. `_solo` and
`_tephigram_figure` are already defined at the top of that file.

```python
@pytest.mark.mpl_image_compare
def test_member_emphasis():
    fig, ax = _tephigram_figure()
    _solo(ax, "isotherms")
    ax.isotherms(
        emphasis={
            0.0: {},
            -20.0: {"color": "tab:cyan", "linestyle": "--"},
        }
    )
    return fig
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pixi run --frozen pytest --mpl tests/plotting/test_images.py::test_member_emphasis -v`
Expected: FAIL — the baseline image does not exist. The `--mpl` flag is what turns
`mpl_image_compare` into an actual comparison; without it the test merely builds the
figure and passes vacuously.

- [ ] **Step 3: Generate the baseline**

Run: `pixi run --frozen baselines`

That task is `pytest --mpl-generate-path=tests/baseline`, so it rewrites **every**
baseline, not just the new one. Then inspect `tests/baseline/test_member_emphasis.png` by
eye before committing it. It must show: the 0 °C isotherm heavier than its neighbours in
the same grey, and the −20 °C isotherm dashed cyan. **Confirm no other baseline changed**
— `git status tests/baseline/` should list exactly one untracked file and no modified
ones. A modified baseline means Task 3 changed default rendering, which is a bug to fix
rather than a baseline to re-bless.

- [ ] **Step 4: Run it to verify it passes**

Run: `pixi run --frozen pytest --mpl tests/plotting/test_images.py -v`
Expected: PASS, all image tests.

- [ ] **Step 5: Write the how-to**

The page uses `.. code-block:: python`, not `.. plot::`. `docs/src/conf.py:17-30` does
**not** load `matplotlib.sphinxext.plot_directive`, and `sphinx_gallery_conf` has empty
`examples_dirs`/`gallery_dirs`, so nothing in this project renders a figure from source
yet. Do not add a Sphinx extension as part of this work.

`EMPHASIS_LINEWIDTH` lives in the private `tephpy._constants`, which `autoapi_ignore` does
not exclude but which is not part of the documented public surface — write it as a
double-backtick literal with its value stated, not a `:data:` role, so the build has no
unresolved reference. Per `docs/src/developer/docs-style.rst`, plain literals are for
names with no documentation target; `tephpy.config` and the accessors do have targets, so
those get roles.

Create `docs/src/howtos/emphasis.rst`:

```rst
.. _howto-emphasis:

Emphasise a reference isopleth
==============================

Forecasters read a tephigram against a handful of reference lines — the 0 °C
isotherm for the freezing level, −20 °C for the cold limit of the airframe
icing band, a mandatory pressure level. The ``emphasis`` option distinguishes
any member of any isopleth family.

The freezing level
------------------

Map the member value to an empty style. The member keeps its family's colour and
draws at 1.5 pt instead of the usual 0.5 pt — the printed-chart idiom of same
ink, heavier line:

.. code-block:: python

    import matplotlib.pyplot as plt

    import tephpy  # noqa: F401

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.isotherms(emphasis={0.0: {}})

Colour and dashes
-----------------

Any of ``color``, ``linewidth``, ``linestyle`` and ``alpha`` overrides that
default, so the airframe icing band's bounds can carry their own styling:

.. code-block:: python

    ax.isotherms(
        emphasis={
            0.0: {"color": "tab:cyan"},
            -20.0: {"color": "tab:cyan", "linestyle": "--"},
        }
    )

An omitted key falls back to the family's own style, so
``{0.0: {"linestyle": "--"}}`` is a dashed member in the family's colour at the
emphasis width.

Values the interval never lands on
----------------------------------

An emphasised member is always drawn, whatever the zoom ladder would select, so
the dendritic growth zone's −12 °C and −18 °C bounds appear even though no
isotherm interval includes them:

.. code-block:: python

    ax.isotherms(
        emphasis={
            -12.0: {"color": "tab:purple"},
            -18.0: {"color": "tab:purple"},
        }
    )

A value outside the diagram's domain is a silent no-op — it is simply never in
view.

Every family, every tier
------------------------

The option is the same on all five families, so a mandatory pressure level is
the same gesture:

.. code-block:: python

    ax.isobars(emphasis={500.0: {}})

and it takes the usual precedence — the accessor keyword over
:obj:`tephpy.config` over the convention default:

.. code-block:: python

    tephpy.config.isotherms.emphasis = {0.0: {}}

Passing an empty mapping at the accessor emphasises nothing, which is how one
diagram opts out of a configured emphasis:

.. code-block:: python

    ax.isotherms(emphasis={})

.. note::

    Emphasis reaches a member's line and its inline label. Where a family labels
    a diagram edge instead, that edge's tick marks and tick labels take one
    colour for the whole family — matplotlib styles ticks per axis, not per
    tick — so an emphasised member's edge tick is placed but not recoloured.
```

- [ ] **Step 6: Add the how-to to the index**

Replace `docs/src/howtos/index.rst` with:

```rst
How-To Guides
=============

Task-focused recipes.

.. toctree::
    :maxdepth: 1

    emphasis
```

- [ ] **Step 7: Build the docs**

Run: `pixi run --frozen docs`

That task is `depends-on = ["docs-clean"]`, so it is always a clean build — which is what
the cross-reference check needs, since an incremental build serves a stale draft and hides
a broken role.

Expected: build succeeds with no warnings mentioning `emphasis.rst`, no "document isn't
included in any toctree", and no unresolved cross-reference for `tephpy.config`.

- [ ] **Step 8: Write the changelog fragment**

Find the PR number first — the fragment is named for it. If the PR is not open yet, open
it, then create `changelog/<PR>.feature.rst`:

```rst
Added the ``emphasis`` option to every isopleth family, so a member can be drawn
with a distinguishing style: :meth:`~tephpy.plotting.axes.TephigramAxes.isotherms`
and its four siblings, and the matching :obj:`tephpy.config` sections, map a
member value to ``color``, ``linewidth``, ``linestyle`` and ``alpha`` overrides.
An emphasised member is always drawn, whatever the zoom ladder would select, so
``ax.isotherms(emphasis={0.0: {}})`` marks the freezing level and
``emphasis={-12.0: {}, -18.0: {}}`` marks the dendritic growth zone that no
isotherm interval lands on. (:user:`claude`)
```

Per `changelog/README.md`: one entry, sentence case, `:user:` attribution, documented
APIs cross-referenced with Sphinx roles rather than quoted. Attribute the author to
whoever opens the PR — `:user:` takes a GitHub handle, so use the real one rather than
copying the placeholder above. If the PR closes an issue, add ``(:issue:`NN`)`` at the
point the fragment describes what that issue reported.

Confirm the `:meth:` target resolves before relying on it: check the built
`reference/generated/api` tree from Step 7 for the `TephigramAxes.isotherms` page and
match the dotted path autoapi actually emits.

- [ ] **Step 9: Verify the fragment renders**

Run: `pixi run --frozen docs`
Expected: no unresolved cross-reference warnings from the changelog page.

- [ ] **Step 10: Run the full gate**

Run: `pixi run --frozen tests`
Expected: PASS.

Run: `pixi run --frozen lint`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add tests/plotting/test_images.py tests/baseline/test_member_emphasis.png \
        docs/src/howtos/emphasis.rst docs/src/howtos/index.rst changelog/
git commit -m "docs: document isopleth member emphasis and baseline its rendering"
```

---

## Verification checklist

Run before opening the implementation PR.

- [ ] `pixi run --frozen tests` passes.
- [ ] `pixi run --frozen lint` passes.
- [ ] `git status tests/baseline/` shows exactly one new file and no modified ones —
      emphasis changes nothing by default.
- [ ] `pixi run --frozen docs` builds clean.
- [ ] `ax.isotherms(emphasis={0.0: {}})` in a scratch script renders a visibly heavier
      0 °C isotherm; `ax.isotherms(emphasis={-12.0: {}})` renders a member the default
      ladder does not include.
- [ ] `pre-commit install` has been run in this clone, and the hooks ran on every commit.
