# Configuration Value Domain Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A configuration-file value that has the right type but is not a value its option can
accept warns as the file is read, is skipped, and leaves the rest of the file applying —
closing {issue}`116`.

**Architecture:** A second stage inside `_configfile.coerce`, behind the same `except` clause
that already carries the type check's warn-and-skip behaviour, so `apply` does not change.
The stage runs on the *converted* value and raises the same `TephpyConfigError` in the same
sentence frame. Ten of its eleven rules are read from draw-time checks that already exist;
the three legal sets those checks consult move down to `_constants`, the floor both
`_configfile` and `plotting` import, because `_configfile` cannot import `plotting` without
reversing the configfile spec §3 dependency arrow.

**Tech Stack:** Python 3.12+, matplotlib (the colour and linestyle oracles), PyYAML, pytest,
pixi, towncrier, Sphinx/autoapi.

## Global Constraints

- **The specification is domain spec** — `docs/src/developer/specs/2026-08-12-config-domain-validation-design.md`.
  Cite it in code and tests as `domain spec §N`. A bare `spec §N` means the parent
  specification, and `configfile spec §N` the sibling; the prefix is load-bearing and a
  pre-commit hook checks the anchors resolve.
- **Cross-document citations in Markdown specs are written bare**, never in backticks —
  backticks make them inline literals that render as dead code boxes rather than links.
- **Every source file carries the BSD copyright header** (ruff `CPY001`). New test modules
  copy the four-line header from `tests/test_configfile.py`.
- **Tests mirror the `src/tephpy` package layout.** `tephpy._configfile` → `tests/test_configfile*.py`;
  `tephpy.plotting.axes` → `tests/plotting/test_axes.py`.
- **pytest runs with `filterwarnings = ["error"]`.** Any test that triggers a
  `TephpyConfigWarning` must wrap it in `pytest.warns`, or it fails as an error.
- **Every command runs through pixi with `--frozen`:** `pixi run --frozen tests`,
  `pixi run --frozen lint`, `pixi run --frozen docs`, `pixi run --frozen python`. Bare
  `python` is not on `PATH`.
- **`pre-commit install` before the first commit** — hooks are not installed in a fresh
  worktree, and `pixi run --frozen lint` (`pre-commit run --all-files`) cannot see untracked
  files, so `git add` new files before linting them.
- **Line width is 88 columns**, enforced by ruff and, for the generated template, by
  `tests/test_configfile_template.py::test_no_generated_template_line_exceeds_the_source_width`.
- **Docstrings are numpydoc**, validated by a pre-commit hook. Private module-level functions
  still need one, with `Parameters`, `Returns` and `Raises` sections.
- **The docs build is strict** — `--fail-on-warning --keep-going` plus `nitpicky = True`. A
  `:data:` role naming an attribute autoapi no longer emits fails the build.
- **Never `cd` out of this worktree.** All paths below are relative to
  `.claude/worktrees/citation-machinery-housekeeping`.
- **Never use bare `git stash` / `git stash pop`** — the stash stack is shared across
  worktrees.

---

## File Structure

**Modified:**

- `src/tephpy/_constants.py` — gains the three legal sets. It is the dependency floor: it
  imports nothing from tephpy, so both `_configfile` and `plotting` can read from it.
- `src/tephpy/_configfile.py` — gains `_DomainError`, ten domain validators, the
  `_DOMAIN_VALIDATORS` table, the second stage in `coerce`, and the reference-page prose
  derived from the vocabularies.
- `src/tephpy/plotting/isopleths.py` — imports the two isopleth vocabularies back from
  `_constants` instead of defining them.
- `src/tephpy/plotting/axes.py` — imports `EDGES` from `_constants` instead of from
  `isopleths`.
- `docs/src/howtos/configuration.rst` — a paragraph on right-type-wrong-value.
- `docs/src/developer/specs/2026-08-07-config-file-design.md` — §5.2 repoints here; §9's
  {issue}`116` entry becomes **Resolved**.

**Created:**

- `tests/test_configfile_domain.py` — every domain test. `_configfile`'s tests are already
  split by concern (`test_configfile.py`, `test_configfile_template.py`,
  `test_configfile_reference.py`); this is the fourth.
- `changelog/<PR>.bugfix.rst`, `changelog/<PR>.documentation.rst`.

**Not created, deliberately:** no new module for the validators. They are ten short
functions that share `_describe` and the `_MismatchError`/`coerce` idiom with the eight type
validators directly above them; splitting them out would put the two stages of one function
in two files.

---

### Task 1: Move the Vocabularies Below the Dependency Arrow

Three legal sets live in `plotting` and the configuration loader needs them.
`plotting.axes` imports `tephpy._config`, which imports `tephpy._configfile`, so
`_configfile` importing `plotting` is a cycle as well as a reversal of the
configfile spec §3 arrow. They move to `_constants` and `plotting` imports them back, so no
draw-time behaviour changes (domain spec §3.2).

**Files:**
- Modify: `src/tephpy/_constants.py:152` (after `EMPHASIS_LINEWIDTH`), `:188` (after
  `CURSOR_FIELDS`), `:293` (before `EDGE_AXIS_TITLES`)
- Modify: `src/tephpy/plotting/isopleths.py:40-72` (the `_constants` import block),
  `:115` (`EDGES`), `:119-124` (`_EMPHASIS_STYLE_KEYS`), `:345`, `:376`, `:380`
- Modify: `src/tephpy/plotting/axes.py:43-67` (the `_constants` import block), `:72-78` (the
  `isopleths` import block)
- Test: `tests/test_constants.py`, `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `tephpy._constants.EDGES: Final[tuple[str, ...]]`,
  `tephpy._constants.EMPHASIS_STYLE_KEYS: Final[tuple[str, ...]]`,
  `tephpy._constants.CURSOR_FIELD_NAMES: Final[tuple[str, ...]]`. Tasks 2 and 4 import all
  three. `tephpy.plotting.isopleths.EDGES` keeps its name, its place in `__all__`, and its
  identity — it *is* the `_constants` object, not a copy.

- [ ] **Step 1: Write the failing gates**

Add to `tests/test_constants.py`, directly after `test_cursor_fields` (line 99-101):

```python
def test_cursor_field_names_cover_the_default_trio():
    """The vocabulary and the default are different facts (domain spec §3.2).

    ``CURSOR_FIELDS`` is what a user gets without asking;
    ``CURSOR_FIELD_NAMES`` is everything they may ask for. A default naming a
    field outside the vocabulary would be a readout that raises on the first
    mouse move.
    """
    assert set(constants.CURSOR_FIELDS) <= set(constants.CURSOR_FIELD_NAMES)
    assert constants.CURSOR_FIELDS != constants.CURSOR_FIELD_NAMES


def test_cursor_field_names_are_sorted():
    """The unknown-field message lists them, and ``format_coord`` sorts.

    ``plotting.axes.format_coord`` says ``expected
    sorted(_CURSOR_FORMATTERS)``, so a vocabulary in registry order would make
    the load-time warning and the draw-time error name the same five fields in
    two different orders (domain spec §4).
    """
    assert list(constants.CURSOR_FIELD_NAMES) == sorted(constants.CURSOR_FIELD_NAMES)


def test_the_isopleth_vocabularies_are_the_objects_plotting_uses():
    """A copy would be two tables a test has to keep in step (domain spec §3.2).

    Identity, not equality: the move is a change of address, and equality
    would pass just as well against a second tuple that has since drifted.
    """
    assert isopleths.EDGES is constants.EDGES
    assert isopleths._EMPHASIS_STYLE_KEYS is constants.EMPHASIS_STYLE_KEYS
```

Add the import at the top of `tests/test_constants.py`, after
`from tephpy.calc import SoundingIndices`:

```python
from tephpy.plotting import isopleths
```

Add to `tests/plotting/test_axes.py`, immediately after the imports block that ends at
line 39:

```python
def test_the_cursor_registry_and_the_vocabulary_agree():
    """Two independently written tables, made to agree (domain spec §3.2).

    The formatter functions call ``tephpy.transforms`` and so cannot move to
    ``_constants`` without dragging it beneath the dependency floor. So the
    registry stays here and the names live there, and this is what stops a
    sixth formatter being unreachable from a configuration file — or a sixth
    name being accepted by the loader and unformattable at the cursor.
    """
    assert set(axes._CURSOR_FORMATTERS) == set(CURSOR_FIELD_NAMES)
```

`tests/plotting/test_axes.py` imports names *from* `tephpy.plotting.axes` (line 38) but does
not bind the module, and `_CURSOR_FORMATTERS` is private, so two import lines change. Add
`CURSOR_FIELD_NAMES,` to the existing `from tephpy._constants import (...)` block between
`CIN_COLOR` and `DEFAULT_EXTENT`, and add above line 38:

```python
from tephpy.plotting import axes
```

Line 39's `from tephpy.plotting.isopleths import EDGES, IsoplethFamily` stays exactly as it
is. That it keeps working is part of what "an address change and nothing else" means.

- [ ] **Step 2: Run the gates to verify they fail**

Run:
```bash
pixi run --frozen python -m pytest tests/test_constants.py tests/plotting/test_axes.py -k "vocabular or cursor_field or cursor_registry" -v
```
Expected: FAIL with `AttributeError: module 'tephpy._constants' has no attribute 'CURSOR_FIELD_NAMES'` (and the same for `EDGES`, `EMPHASIS_STYLE_KEYS`).

- [ ] **Step 3: Add the three constants**

In `src/tephpy/_constants.py`, immediately after `EMPHASIS_LINEWIDTH` (line 152):

```python
#: Style keys one emphasised isopleth member may override; an omitted key falls
#: back to the family's own style (spec §3.2). Here rather than in
#: ``plotting.isopleths`` so that the configuration loader can check an
#: ``emphasis`` style key against the same tuple the draw uses, without
#: importing ``plotting`` and reversing the configfile spec §3 dependency arrow
#: (domain spec §3.2).
EMPHASIS_STYLE_KEYS: Final[tuple[str, ...]] = (
    "color",
    "linewidth",
    "linestyle",
    "alpha",
)
```

Immediately after `CURSOR_FIELDS` (line 188):

```python
#: Every interactive cursor readout field a user may ask for, sorted. The
#: vocabulary behind ``CURSOR_FIELDS`` above, which is the three-field default:
#: a different fact, and a strict subset of this one. Sorted because
#: ``plotting.axes.format_coord`` lists ``sorted(_CURSOR_FORMATTERS)`` when it
#: refuses an unknown field, and the load-time warning must name the five in the
#: same order (domain spec §3.2, domain spec §4). The formatter functions
#: themselves stay in ``plotting.axes``: they call ``tephpy.transforms``, which
#: would drag it beneath this module.
CURSOR_FIELD_NAMES: Final[tuple[str, ...]] = (
    "mixing_ratio",
    "pressure",
    "temperature",
    "theta",
    "theta_w",
)
```

Immediately before `EDGE_AXIS_TITLES` (line 293):

```python
#: The diagram edges an isopleth family may claim for its labels (spec §3.2).
#: Here rather than in ``plotting.isopleths`` so that the configuration loader
#: can check a ``labels`` value against the same tuple the draw uses, without
#: importing ``plotting`` and reversing the configfile spec §3 dependency arrow
#: (domain spec §3.2).
EDGES: Final[tuple[str, ...]] = ("bottom", "top", "left", "right")
```

- [ ] **Step 4: Import them back into `plotting.isopleths`**

In `src/tephpy/plotting/isopleths.py`, add to the `from tephpy._constants import (...)`
block (lines 40-72), in alphabetical position:

```python
    EDGES as _EDGES,
    EMPHASIS_LINEWIDTH,
    EMPHASIS_STYLE_KEYS as _EMPHASIS_STYLE_KEYS,
```

`EDGES` goes between `DRY_ADIABAT_ZORDER` and `EMPHASIS_LINEWIDTH`; `EMPHASIS_STYLE_KEYS`
directly after `EMPHASIS_LINEWIDTH`.

Replace the definition at line 114-115 with a re-export:

```python
#: The diagram edges an isopleth family may claim for its labels (spec §3.2).
#: The tuple itself lives in ``tephpy._constants``, below the
#: configfile spec §3 dependency arrow, so the configuration loader can check a
#: ``labels`` value against it (domain spec §3.2). Re-bound here, rather than
#: left as a bare import, because it is public API: it is in ``__all__``, and
#: three docstrings in this module reference it as :data:`EDGES`. autoapi is a
#: static parser and does not render imported names, so an import alone would
#: drop the attribute from the API page and break those references under
#: ``nitpicky``. It is the same object, not a copy.
EDGES: Final[tuple[str, ...]] = _EDGES
```

Delete the definition at lines 117-124 (`_EMPHASIS_STYLE_KEYS`) entirely — the aliased
import replaces it, so lines 345, 376 and 380 need no change.

- [ ] **Step 5: Move `EDGES` to the `_constants` block in `plotting.axes`**

In `src/tephpy/plotting/axes.py`, add `EDGES,` to the `from tephpy._constants import (...)`
block between `DEFAULT_EXTENT` (line 51) and `EDGE_AXIS_TITLES` (line 52), and delete the
`EDGES,` line (line 74) from the `from tephpy.plotting.isopleths import (...)` block. The
four `EDGE_*` constants and `EDGES` now sit in one block, which is the split
domain spec §3.2 records this move as tidying.

- [ ] **Step 6: Run the gates to verify they pass, then the full suite**

Run:
```bash
pixi run --frozen python -m pytest tests/test_constants.py tests/plotting/test_axes.py tests/plotting/test_isopleths.py -q
```
Expected: PASS. `tests/plotting/test_isopleths.py:618` asserts
`isopleths.EDGES == ("bottom", "top", "left", "right")` and must still pass unchanged — that
is the address-change-only property from the other side.

Then:
```bash
pixi run --frozen tests
```
Expected: PASS, no new failures.

- [ ] **Step 7: Prove each gate with a mutation that fails it alone**

`git add -A` first — `git checkout <path>` reverts from the index, so an unstaged
mutate-verify-revert cycle discards the real work along with the mutation.

For each mutation: apply it, run the named test, confirm it fails, revert with
`git checkout <path>`.

1. Append `"nonsuch"` to `_constants.CURSOR_FIELD_NAMES` →
   `test_the_cursor_registry_and_the_vocabulary_agree` fails.
2. Reorder `_constants.CURSOR_FIELD_NAMES` to registry order
   (`pressure, temperature, theta, mixing_ratio, theta_w`) →
   `test_cursor_field_names_are_sorted` fails.
3. Change `_constants.CURSOR_FIELDS` to `("pressure", "nonsuch")` →
   `test_cursor_field_names_cover_the_default_trio` fails.
4. In `isopleths.py`, change the re-export to
   `EDGES: Final[tuple[str, ...]] = tuple(list(_EDGES))` →
   `test_the_isopleth_vocabularies_are_the_objects_plotting_uses` fails on the identity
   assertion while `tests/plotting/test_isopleths.py:618`'s equality assertion still passes.
   This is the mutation that shows why the gate is identity and not equality. The
   `list()` is load-bearing: CPython's `tuple()` returns its argument unchanged when given
   an exact tuple, so `tuple(_EDGES) is _EDGES` and that mutation would prove nothing.

- [ ] **Step 8: Build the docs**

Run:
```bash
pixi run --frozen docs
```
Expected: PASS with no new warnings. This is the step that catches the autoapi hazard in
Step 4 — if `EDGES` had been left as a bare import, `:data:`EDGES`` in `edge_crossings` and
in two `IsoplethFamily` docstrings would fail to resolve under `nitpicky = True`.

- [ ] **Step 9: Commit**

```bash
pixi run --frozen lint
git add src/tephpy/_constants.py src/tephpy/plotting/isopleths.py src/tephpy/plotting/axes.py tests/test_constants.py tests/plotting/test_axes.py
git commit -m "Move the isopleth and cursor vocabularies to _constants"
```

---

### Task 2: The Domain Stage in `coerce`

`coerce` gains a second stage that runs on the converted value and raises the same
`TephpyConfigError` the type stage raises, so `apply`'s existing `except` clause carries the
warn-and-skip behaviour unchanged (domain spec §3.1).

**Files:**
- Modify: `src/tephpy/_configfile.py:13-30` (imports), `:554` (new block after `_describe`),
  `:609-619` (`coerce`)
- Create: `tests/test_configfile_domain.py`

**Interfaces:**
- Consumes: `tephpy._constants.EDGES`, `EMPHASIS_STYLE_KEYS`, `CURSOR_FIELD_NAMES` from
  Task 1.
- Produces: `_configfile._DomainError(expects: str, found: str)` with `.expects` and
  `.found` attributes; `_configfile._DOMAIN_VALIDATORS: Mapping[str, Callable[[object], None]]`
  keyed by option name; `coerce` unchanged in signature. Task 3 gates
  `_DOMAIN_VALIDATORS` for completeness and key unambiguity.

- [ ] **Step 1: Write the failing behaviour tests**

Create `tests/test_configfile_domain.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Domain validation of a configuration value that has the right type.

The second stage of ``coerce`` (domain spec §3.1): every case here has already
passed the type check that ``tests/test_configfile.py`` covers.
"""

from __future__ import annotations

import re

import pytest

import tephpy
from tephpy import _configfile
from tephpy._constants import CURSOR_FIELD_NAMES, EDGES, EMPHASIS_STYLE_KEYS
from tephpy.exceptions import TephpyConfigWarning


def _write(tmp_path, text):
    path = tmp_path / "tephpyrc.yaml"
    path.write_text(text, encoding="utf-8")
    return path


#: One case per row of the domain spec §1 table, plus the three parts of
#: ``emphasis`` that table reaches only through a style key. Each is
#: ``(section, option, yaml, expected message tail)``, the tail picking up
#: after "which expects". Where the tail names a closed vocabulary it is
#: built from the constant rather than written out: the message is built
#: from that constant too, so a literal here would only be a second copy to
#: keep in step, and a legitimate new edge or field would fail this test
#: rather than Task 4's, which is the one that owns it.
REFUSED = [
    (
        "isotherms",
        "linewidth",
        "-1.0",
        "a positive, finite number, not the number -1.0",
    ),
    ("isotherms", "values", "[0, .nan]", "finite numbers, not the number nan"),
    ("moist_adiabats", "truncation", ".nan", "a finite number, not the number nan"),
    (
        "isotherms",
        "color",
        "notacolour",
        "a colour matplotlib knows, not the string 'notacolour'",
    ),
    ("isotherms", "alpha", "5.0", "a number between 0 and 1, not the number 5.0"),
    (
        "isotherms",
        "emphasis",
        "{0.0: {color: notacolour}}",
        "member 0 'color' to be a colour matplotlib knows, not the string 'notacolour'",
    ),
    (
        "isotherms",
        "emphasis",
        "{0.0: {linestyle: notaline}}",
        "member 0 'linestyle' to be a linestyle matplotlib knows, "
        "not the string 'notaline'",
    ),
    (
        "isotherms",
        "labels",
        "[botom]",
        f"true, false, or edge name(s) from {list(EDGES)}, not the string 'botom'",
    ),
    ("isobars", "interval", "0.0", "a positive, finite number, not the number 0.0"),
    (
        "diagram",
        "extent",
        "[[0.0, -80.0], [1050.0, 40.0]]",
        "corner pressures above 0 hPa, not the number 0.0",
    ),
    (
        "diagram",
        "extent",
        "[[1050.0, .nan], [300.0, 40.0]]",
        "finite corner numbers, not the number nan",
    ),
    (
        "isotherms",
        "emphasis",
        "{700.0: {lw: 2.0}}",
        f"member 700 to use style key(s) from {list(EMPHASIS_STYLE_KEYS)}, "
        "not the string 'lw'",
    ),
    (
        "isotherms",
        "emphasis",
        "{0.0: {linewidth: thick}}",
        "member 0 'linewidth' to be a positive, finite number, not the string 'thick'",
    ),
    (
        "isotherms",
        "emphasis",
        "{0.0: {alpha: 5.0}}",
        "member 0 'alpha' to be a number between 0 and 1, not the number 5.0",
    ),
    ("isotherms", "emphasis", "{.nan: {}}", "finite member values, not the number nan"),
    (
        "cursor",
        "fields",
        "[nonsuch]",
        f"field name(s) from {list(CURSOR_FIELD_NAMES)}, not the string 'nonsuch'",
    ),
]


@pytest.mark.parametrize(("section", "option", "yaml", "tail"), REFUSED)
def test_a_bad_value_warns_keeps_the_default_and_spares_the_file(
    tmp_path, section, option, yaml, tail
):
    """The whole of domain spec §2's rule, in one assertion each.

    Every one of these loaded silently before: eight failed at the first
    draw with tephpy's own message, four with matplotlib's, and three drew a
    diagram that was simply not the one the file asked for (domain spec §1).

    The sibling option is what makes "the rest of the file still applies" a
    claim about something. It goes in a second section, so a rule that
    discarded the section rather than the option would fail here too.
    """
    text = f"{section}:\n  {option}: {yaml}\nmixing_ratios:\n  color: purple\n"
    path = _write(tmp_path, text)
    expected = re.escape(f"{section}.{option}, which expects {tail}")
    with pytest.warns(TephpyConfigWarning, match=expected):
        tephpy.config.load(path)
    assert getattr(getattr(tephpy.config, section), option) is None
    assert tephpy.config.mixing_ratios.color == "purple"


def test_the_refused_table_covers_every_rule():
    """The parametrisation above is the gate; an empty table would pass it.

    Pinning the count and the option set is what stops a rule being deleted
    from ``REFUSED`` along with the bug report that motivated it.
    """
    assert len(REFUSED) == 16
    covered = {option for _, option, _, _ in REFUSED}
    assert covered == set(_configfile._DOMAIN_VALIDATORS)


def test_a_hex_colour_missing_its_hash_is_told_so(tmp_path):
    """The mirror image of the trap configfile spec §5 already warns about.

    ``color: #b0b0b0`` parses to null, because YAML eats the unquoted ``#``
    as a comment. ``color: b0b0b0`` is a perfectly good string that is not a
    colour, and lands here. The hint is tested rather than guessed: it is
    offered only because prefixing ``#`` makes ``is_color_like`` true
    (domain spec §4).
    """
    path = _write(tmp_path, "isotherms:\n  color: b0b0b0\n")
    with pytest.warns(TephpyConfigWarning, match=re.escape("did you mean '#b0b0b0'?")):
        tephpy.config.load(path)
    assert tephpy.config.isotherms.color is None


def test_an_ordinary_bad_colour_gets_no_hint(tmp_path):
    """A hint that fires for every bad colour is noise, not a hint."""
    path = _write(tmp_path, "isotherms:\n  color: notacolour\n")
    with pytest.warns(TephpyConfigWarning, match="notacolour") as record:
        tephpy.config.load(path)
    assert "did you mean" not in str(record[0].message)


def test_one_bad_member_skips_the_whole_emphasis_option(tmp_path):
    """Granularity is the option, not the part (domain spec §3.3).

    Not visible from outside, so it is pinned here and documented in the
    configuration how-to. A user told ``emphasis`` was ignored can read
    their own file; one told it was partly applied cannot tell what is in
    force.
    """
    text = "isotherms:\n  emphasis: {850.0: {linewidth: 2.0}, 700.0: {lw: 2.0}}\n"
    path = _write(tmp_path, text)
    with pytest.warns(TephpyConfigWarning, match="isotherms.emphasis"):
        tephpy.config.load(path)
    assert tephpy.config.isotherms.emphasis is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
pixi run --frozen python -m pytest tests/test_configfile_domain.py -q
```
Expected: FAIL — every parametrised case with `DID NOT WARN`, and
`test_the_refused_table_covers_every_rule` with
`AttributeError: module 'tephpy._configfile' has no attribute '_DOMAIN_VALIDATORS'`.

- [ ] **Step 3: Add the imports**

In `src/tephpy/_configfile.py`, add `import math` to the standard-library block, between
`import inspect` (line 18) and `import os` (line 19).

Add to the third-party block, before `import platformdirs` (line 26):

```python
from matplotlib.collections import LineCollection
from matplotlib.colors import is_color_like
```

Ruff sorts `from` and plain imports together by module name, so
`matplotlib.collections` precedes `matplotlib.colors` precedes `platformdirs`.

Extend the `from tephpy._constants import CONFIG_DEFAULTS` line (line 29) to:

```python
from tephpy._constants import (
    CONFIG_DEFAULTS,
    CURSOR_FIELD_NAMES,
    EDGES,
    EMPHASIS_STYLE_KEYS,
)
```

matplotlib is not a new dependency in any sense that costs anything: `from tephpy import
_configfile` already leaves both modules in `sys.modules`, because importing any tephpy
submodule runs the package `__init__`, which imports `plotting` (domain spec §3.2).

- [ ] **Step 4: Add the domain validators**

In `src/tephpy/_configfile.py`, after `_describe` (ends line 553) and before `_option_hints`
(line 556), insert:

```python
class _DomainError(Exception):
    """A value of the right type that its option still cannot accept.

    Carries the two halves of the message separately, where
    :class:`_MismatchError` carries at most one. For a compound option both
    halves vary with the offending part — ``emphasis`` names the member and
    the style key in the *expects* half — so :func:`coerce` cannot compose
    the sentence from the option alone as it does for a type mismatch
    (domain spec §3.1).

    Parameters
    ----------
    expects : str
        The noun phrase for what the option can accept, as it reads after
        "which expects".
    found : str
        The offending value, named as :func:`_describe` names it. For a
        compound option this is the offending *part*, not the whole value:
        printing a forty-member ``values`` list back at someone who
        mistyped one entry helps nobody (domain spec §4).
    """

    def __init__(self, expects: str, found: str) -> None:
        super().__init__(f"{expects}, not {found}")
        self.expects = expects
        self.found = found


def _as_float(value: object, expects: str) -> float:
    """Convert a style override to a float, or say what was expected instead.

    Parameters
    ----------
    value : object
        The value to convert.
    expects : str
        The noun phrase to report if it will not convert.

    Returns
    -------
    float
        The value as a float.

    Raises
    ------
    _DomainError
        If the value is not a number.

    Notes
    -----
    Coercion rather than an ``isinstance`` test, matching
    ``isopleths._emphasis_number`` exactly. An ``emphasis`` style *value* is
    annotated ``object`` and so reaches this stage unconverted, which makes
    ``emphasis: {850: {linewidth: 2}}`` an ``int`` where ``linewidth: 2`` is
    a ``float`` (configfile spec §5.2). A rule that tested the type would
    refuse a value the draw accepts (domain spec §3.3).
    """
    try:
        return float(cast("SupportsFloat", value))
    except (TypeError, ValueError):
        raise _DomainError(expects, _describe(value)) from None


def _domain_color(value: object) -> None:
    """Check a colour is one matplotlib knows.

    Parameters
    ----------
    value : object
        The converted ``color`` value, or a ``color`` style override.

    Returns
    -------
    None

    Raises
    ------
    _DomainError
        If matplotlib does not recognise the colour. matplotlib is asked
        rather than re-derived, because it owns the domain (domain spec §2).
        A string that becomes a colour with a ``#`` in front earns a hint:
        ``color: #b0b0b0`` is eaten by YAML as a comment
        (configfile spec §5) and ``color: b0b0b0`` lands here, so the two
        halves of one trap warn about each other (domain spec §4).
    """
    if is_color_like(value):
        return
    hint = ""
    if isinstance(value, str) and is_color_like(f"#{value}"):
        hint = f"; did you mean '#{value}'?"
    raise _DomainError("a colour matplotlib knows", f"{_describe(value)}{hint}")


def _domain_linestyle(value: object) -> None:
    """Check a linestyle is one matplotlib knows.

    Parameters
    ----------
    value : object
        A ``linestyle`` style override.

    Returns
    -------
    None

    Raises
    ------
    _DomainError
        If ``LineCollection.set_linestyle`` will not take it. That is the
        oracle because a ``LineCollection`` is what the draw sets the style
        on. Measured on matplotlib 3.11.1: it and ``Line2D.set_linestyle``
        accept and reject the same ten probes and differ only in wording,
        and ``matplotlib.rcsetup._validate_linestyle`` is private
        (domain spec §3.3).
    """
    try:
        LineCollection([]).set_linestyle(cast("str", value))
    except (TypeError, ValueError):
        raise _DomainError("a linestyle matplotlib knows", _describe(value)) from None


def _domain_positive(value: object) -> None:
    """Check a number is positive and finite.

    Parameters
    ----------
    value : object
        A ``linewidth`` or ``interval`` value, or a ``linewidth`` override.

    Returns
    -------
    None

    Raises
    ------
    _DomainError
        If the value is not a positive, finite number. Lifted from
        ``isopleths._emphasis_number`` and ``IsoplethFamily._resolve``
        (domain spec §3.3).
    """
    expects = "a positive, finite number"
    number = _as_float(value, expects)
    if not (number > 0.0 and math.isfinite(number)):
        raise _DomainError(expects, _describe(value))


def _domain_alpha(value: object) -> None:
    """Check an opacity falls in ``[0, 1]``.

    Parameters
    ----------
    value : object
        An ``alpha`` value, or an ``alpha`` style override.

    Returns
    -------
    None

    Raises
    ------
    _DomainError
        If the value is outside ``[0, 1]``. The bounds are inclusive, as
        ``isopleths._emphasis_number`` has them (domain spec §3.3).
    """
    expects = "a number between 0 and 1"
    number = _as_float(value, expects)
    if not 0.0 <= number <= 1.0:
        raise _DomainError(expects, _describe(value))


def _domain_finite(value: object) -> None:
    """Check a number is finite.

    Parameters
    ----------
    value : object
        A ``truncation`` value.

    Returns
    -------
    None

    Raises
    ------
    _DomainError
        If the value is not finite. This is the one invented rule, and
        deliberately the weakest available: a temperature below which moist
        adiabats are truncated has no defensible bound that is not a guess,
        and a validator that refuses a value the draw would have accepted is
        a regression wearing a feature's clothes (domain spec §3.3).
    """
    expects = "a finite number"
    if not math.isfinite(_as_float(value, expects)):
        raise _DomainError(expects, _describe(value))


def _domain_values(value: object) -> None:
    """Check every explicit member value is finite.

    Parameters
    ----------
    value : object
        The converted ``values`` tuple.

    Returns
    -------
    None

    Raises
    ------
    _DomainError
        If any member is not finite. No draw-time counterpart on this
        option, but not invented either: it is
        ``isopleths._normalize_emphasis``'s member rule applied to the other
        place member values come from, for the reason that function already
        records — a non-finite member would build a full NaN polyline that
        the view mask silently drops (domain spec §3.3).
    """
    for member in cast("tuple[float, ...]", value):
        if not math.isfinite(member):
            raise _DomainError("finite numbers", _describe(member))


def _domain_labels(value: object) -> None:
    """Check a label placement names diagram edges.

    Parameters
    ----------
    value : object
        The converted ``labels`` value: a bool, an edge name, or a tuple of
        them.

    Returns
    -------
    None

    Raises
    ------
    _DomainError
        If a name is not in :data:`tephpy._constants.EDGES`. Lifted from
        ``isopleths._normalize_labels`` (domain spec §3.3). The bool arms
        return early, and the bare-string arm is handled before the iterable
        one so ``"bottom"`` is never iterated character by character.
    """
    if isinstance(value, bool):
        return
    names = (value,) if isinstance(value, str) else cast("tuple[str, ...]", value)
    for name in names:
        if name not in EDGES:
            raise _DomainError(
                f"true, false, or edge name(s) from {list(EDGES)}", _describe(name)
            )


def _domain_fields(value: object) -> None:
    """Check every cursor readout field is one that exists.

    Parameters
    ----------
    value : object
        The converted ``fields`` tuple.

    Returns
    -------
    None

    Raises
    ------
    _DomainError
        If a name is not in :data:`tephpy._constants.CURSOR_FIELD_NAMES`.
        Lifted from ``plotting.axes.format_coord``, whose check fires on
        mouse motion and so only ever reaches an interactive user
        (domain spec §1).
    """
    for name in cast("tuple[str, ...]", value):
        if name not in CURSOR_FIELD_NAMES:
            raise _DomainError(
                f"field name(s) from {list(CURSOR_FIELD_NAMES)}", _describe(name)
            )


def _domain_extent(value: object) -> None:
    """Check both view corners are physical.

    Parameters
    ----------
    value : object
        The converted ``extent``, as two ``(pressure, temperature)`` pairs.

    Returns
    -------
    None

    Raises
    ------
    _DomainError
        If a corner number is not finite, or a pressure is not above zero.
        Lifted from ``axes.TephigramAxes.set_extent``, whose message names
        the pressure but whose test is finiteness after the transform — so a
        non-finite temperature is refused there too (domain spec §3.3).
    """
    corners = cast("tuple[tuple[float, float], tuple[float, float]]", value)
    for pressure, temperature in corners:
        if not math.isfinite(temperature):
            raise _DomainError("finite corner numbers", _describe(temperature))
        if not (pressure > 0.0 and math.isfinite(pressure)):
            raise _DomainError("corner pressures above 0 hPa", _describe(pressure))


#: The rule for each ``emphasis`` style override, keyed by style key. A key
#: absent from this table is a legal style key with no domain of its own;
#: today there is none, and ``tests/test_configfile_domain.py`` pins that.
_EMPHASIS_STYLE_RULES: Final[Mapping[str, Callable[[object], None]]] = MappingProxyType(
    {
        "color": _domain_color,
        "linewidth": _domain_positive,
        "linestyle": _domain_linestyle,
        "alpha": _domain_alpha,
    }
)


def _domain_emphasis(value: object) -> None:
    """Check every emphasised member and every style override it carries.

    Parameters
    ----------
    value : object
        The converted ``emphasis`` mapping.

    Returns
    -------
    None

    Raises
    ------
    _DomainError
        If a member value is not finite, a style names a key outside
        :data:`tephpy._constants.EMPHASIS_STYLE_KEYS`, or an override falls
        outside its own domain. The six rules of domain spec §3.3, this
        being the one option that nests a style mapping. A failing override
        is re-raised with the member and the key in front of it, so the
        warning locates the fault inside a mapping that may hold dozens
        (domain spec §4).
    """
    members = cast("Mapping[float, Mapping[str, object]]", value)
    for member, style in members.items():
        if not math.isfinite(member):
            raise _DomainError("finite member values", _describe(member))
        for key in style:
            if key not in EMPHASIS_STYLE_KEYS:
                raise _DomainError(
                    f"member {member:g} to use style key(s) from "
                    f"{list(EMPHASIS_STYLE_KEYS)}",
                    _describe(key),
                )
        for key, rule in _EMPHASIS_STYLE_RULES.items():
            if key in style:
                try:
                    rule(style[key])
                except _DomainError as exc:
                    raise _DomainError(
                        f"member {member:g} {key!r} to be {exc.expects}", exc.found
                    ) from None


#: The domain rule for each option that has one, keyed by **option name**
#: where ``_TYPE_VALIDATORS`` is keyed by annotation. The two tables are
#: shaped by different things: eight annotations cover all 42 options because
#: a type is a coarse property, while a domain is a property of what the
#: option *means* -- ``color`` and ``linewidth`` are both scalars and share no
#: domain at all. Ten names cover the 42 options bar the five ``visible``
#: flags, which are bools and need no domain (domain spec §3.1).
#:
#: Keying by name alone is sound only because no two sections give one option
#: name different domains: ``values`` is finite numbers whether the family
#: measures degrees Celsius or g/kg. That is a property of the current
#: ``Config``, not a law, so ``tests/test_configfile_domain.py`` gates it
#: rather than trusting it.
_DOMAIN_VALIDATORS: Final[Mapping[str, Callable[[object], None]]] = MappingProxyType(
    {
        "color": _domain_color,
        "linewidth": _domain_positive,
        "alpha": _domain_alpha,
        "labels": _domain_labels,
        "emphasis": _domain_emphasis,
        "values": _domain_values,
        "interval": _domain_positive,
        "extent": _domain_extent,
        "fields": _domain_fields,
        "truncation": _domain_finite,
    }
)
```

`_as_float` casts to `SupportsFloat`, which is a type-checking-only name. Add it to the
existing `if TYPE_CHECKING:` block at line 32-33, above the `from tephpy._config import
Config` line:

```python
if TYPE_CHECKING:
    from typing import SupportsFloat

    from tephpy._config import Config
```

That is the shape `plotting/isopleths.py:74-76` uses for the same cast, which is the
precedent to follow rather than adding `SupportsFloat` to the runtime `typing` import at
line 23.

- [ ] **Step 5: Run the domain stage from `coerce`**

Replace the body of `coerce` at lines 610-619 with:

```python
    validator = _TYPE_VALIDATORS.get(annotation)
    if validator is None:
        return value
    description, convert = validator
    try:
        converted = convert(value)
    except _MismatchError as exc:
        found = str(exc) or _describe(value)
        msg = f"{section}.{option}, which expects {description}, not {found}"
        raise TephpyConfigError(msg) from None
    domain = _DOMAIN_VALIDATORS.get(option)
    if domain is not None:
        try:
            domain(converted)
        except _DomainError as exc:
            msg = f"{section}.{option}, which expects {exc.expects}, not {exc.found}"
            raise TephpyConfigError(msg) from None
    return converted
```

Extend `coerce`'s docstring. In `Returns`, after the existing sentence about an annotation
with no validator, add:

```
        An option with no *domain* rule is likewise returned untouched: the
        five ``visible`` flags are bools, and a bool needs no domain
        (domain spec §3.3).
```

Replace the `Raises` section with:

```
    Raises
    ------
    TephpyConfigError
        If the value does not match the declared type, or matches it and is
        still not a value the option can accept. The message is a noun
        phrase — ``isotherms.linewidth, which expects a number, not the
        string 'thick'`` — so that :func:`apply` can lead with the file and
        the word "ignoring" and have the whole read as one sentence. One
        frame serves both stages, so a domain warning reads like a type
        warning and the description does the work of locating the fault
        (domain spec §4).
```

And add a `Notes` section:

```
    Notes
    -----
    Two stages. The type stage checks the value against the type its field
    declares and performs the configfile spec §3.3 coercions; the domain
    stage then runs on the *converted* value, so a rule sees a
    ``tuple[float, ...]`` and never a list of ``int`` (domain spec §3.1).
    Both raise the same exception, so :func:`apply` needs no second
    ``except`` and nothing about the warning, the provenance or the message
    prefix has to be restated.
```

- [ ] **Step 6: Run the tests to verify they pass**

Run:
```bash
pixi run --frozen python -m pytest tests/test_configfile_domain.py -q
```
Expected: PASS, 20 tests — the 16 rows of `REFUSED` plus the four tests that
follow it.

Then the rest of the configuration suite, which must be untouched:
```bash
pixi run --frozen python -m pytest tests/test_configfile.py tests/test_config.py tests/test_config_autoload.py tests/test_config_defaults.py tests/test_configfile_fixture.py -q
```
Expected: PASS. `tests/test_configfile_fixture.py` loads a fixture file; if it carries a
value the new stage refuses, that is a real finding about the fixture — fix the fixture and
say so, do not weaken the rule.

- [ ] **Step 7: Commit**

```bash
pixi run --frozen lint
git add src/tephpy/_configfile.py tests/test_configfile_domain.py
git commit -m "Check a configuration value against its option's domain"
```

---

### Task 3: The Structural Gates

Four of domain spec §5's seven gates are structural rather than behavioural, and two of them
carry the weight: no false positives, and load/draw agreement.

**Files:**
- Modify: `tests/test_configfile_domain.py`

**Interfaces:**
- Consumes: `_configfile._DOMAIN_VALIDATORS` and `coerce` from Task 2;
  `_constants.EDGES`/`EMPHASIS_STYLE_KEYS`/`CURSOR_FIELD_NAMES` from Task 1.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Write the completeness and unambiguity gates**

Append to `tests/test_configfile_domain.py`, and add `import dataclasses` and
`from tephpy._constants import CONFIG_DEFAULTS` to its imports:

```python
#: The five options that have no domain rule, and why. A bool is the whole of
#: its own domain, so ``visible`` needs none (domain spec §3.3).
UNDOMAINED = {
    (section, "visible")
    for section, defaults in CONFIG_DEFAULTS.items()
    if "visible" in defaults
}


def test_every_option_bar_the_flags_has_a_domain_rule():
    """An option with no rule must fail here, not go quietly unchecked.

    ``coerce`` returns an option with no entry in ``_DOMAIN_VALIDATORS``
    untouched, exactly as it does for an unrecognised annotation and for the
    same reason: adding an option must not be able to stop an import. So
    nothing else in the suite would notice the gap — the option would simply
    go back to being applied unchecked, which is the defect this work exists
    to close.

    The first two assertions are what stop this gate passing by checking
    nothing, and the count comes from ``CONFIG_DEFAULTS`` rather than being
    written down, so adding an option updates it.
    """
    options = {
        (section, option)
        for section, defaults in CONFIG_DEFAULTS.items()
        for option in defaults
    }
    assert options
    assert len(options) == 42
    assert len(UNDOMAINED) == 5
    missing = sorted(
        key
        for key in options - UNDOMAINED
        if key[1] not in _configfile._DOMAIN_VALIDATORS
    )
    assert missing == []
    assert {option for _, option in options} - set(_configfile._DOMAIN_VALIDATORS) == {
        "visible"
    }


def test_no_option_name_carries_two_domains():
    """The assumption behind keying by name rather than by annotation.

    ``_DOMAIN_VALIDATORS`` is keyed by option name, so ``values`` in
    ``isotherms`` and ``values`` in ``mixing_ratios`` get the same rule.
    That is sound today because the two mean the same kind of thing — finite
    numbers, whether the family measures degrees Celsius or g/kg — and it is
    a property of the current ``Config``, not a law (domain spec §3.1).

    An option that ever needs a per-section domain has to be keyed by
    ``(section, option)``, and this is where that shows up. The proxy for
    "same domain" is the declared type: two sections that give one option
    name different types cannot share a rule that runs on the converted
    value.
    """
    annotations: dict[str, set[object]] = {}
    for field in dataclasses.fields(tephpy.config):
        section = getattr(tephpy.config, field.name)
        hints = _configfile._option_hints(type(section))
        for option in dataclasses.fields(section):
            annotations.setdefault(option.name, set()).add(hints[option.name])
    assert annotations
    ambiguous = sorted(name for name, types in annotations.items() if len(types) > 1)
    assert ambiguous == []
```

- [ ] **Step 2: Write the no-false-positives gate**

Append:

```python
#: Values every rule must accept: the legitimate lookalikes. A validator that
#: refuses a value the draw would have accepted is worse than no validator,
#: and no other gate here can see it -- every refusal test passes just as
#: well against a rule that is too strict (domain spec §5).
ACCEPTED = [
    ("isotherms", "color", "C0"),
    ("isotherms", "color", "'xkcd:sky blue'"),
    ("isotherms", "color", "'0.5'"),
    ("isotherms", "color", "'#b0b0b0'"),
    ("isotherms", "linewidth", "0.5"),
    ("isotherms", "alpha", "0"),
    ("isotherms", "alpha", "1"),
    ("isotherms", "labels", "true"),
    ("isotherms", "labels", "false"),
    ("isotherms", "labels", "bottom"),
    ("isotherms", "labels", "[bottom, left]"),
    ("isotherms", "values", "[]"),
    ("isotherms", "values", "[0, 10]"),
    ("isotherms", "visible", "false"),
    ("isotherms", "emphasis", "{}"),
    ("isotherms", "emphasis", "{850.0: {}}"),
    ("isotherms", "emphasis", "{850.0: {linestyle: '--'}}"),
    ("isotherms", "emphasis", "{850.0: {linestyle: dashed}}"),
    ("isotherms", "emphasis", "{850.0: {linewidth: 2}}"),
    ("isotherms", "emphasis", "{850.0: {alpha: 1}}"),
    ("isotherms", "emphasis", "{850.0: {color: red, linewidth: 2.0, alpha: 1.0}}"),
    ("isobars", "interval", "10.0"),
    ("moist_adiabats", "truncation", "-40"),
    ("diagram", "extent", "[[1050.0, -80.0], [300.0, 40.0]]"),
    ("cursor", "fields", "[pressure, theta_w]"),
]


@pytest.mark.parametrize(("section", "option", "yaml"), ACCEPTED)
def test_a_legitimate_value_is_not_refused(tmp_path, section, option, yaml):
    """Each rule's lookalikes, loaded through the file (domain spec §5).

    ``C0``, ``xkcd:sky blue`` and ``0.5`` are all colours and none of them
    looks like one. ``alpha: 0`` and ``alpha: 1`` are the inclusive bounds.
    ``labels: bottom`` is the bare-string arm and ``[bottom, left]`` the list
    arm. ``truncation: -40`` is the negative number the one invented rule
    must not read as out of range. The three ``emphasis`` overrides written
    as integers are the case that drove ``_as_float``: a style value is
    annotated ``object`` and so arrives unconverted, so a rule testing for
    ``float`` would refuse ``linewidth: 2`` where ``linewidth: 2.0`` passes
    (domain spec §3.3).
    """
    path = _write(tmp_path, f"{section}:\n  {option}: {yaml}\n")
    with warnings.catch_warnings():
        warnings.simplefilter("error", TephpyConfigWarning)
        tephpy.config.load(path)
    assert getattr(getattr(tephpy.config, section), option) is not None


def test_the_accepted_table_reaches_every_rule():
    """An emptied table would pass the gate above having checked nothing."""
    assert len(ACCEPTED) == 25
    assert {option for _, option, _ in ACCEPTED} == set(
        _configfile._DOMAIN_VALIDATORS
    ) | {"visible"}
```

Add `import warnings` to the module's imports.

`values: []` and `emphasis: {}` load as an empty tuple and an empty mapping, which are not
`None`, so the final assertion holds for them.

- [ ] **Step 3: Write the load/draw agreement gate**

Append:

```python
#: The four values the draw accepts in silence (domain spec §1). Each draws a
#: diagram that is simply not the one the file asked for, which is the worst
#: outcome available and the reason this work exists. Their rules are lifted
#: from the *emphasis* checks on the same quantities, not from a check the
#: family-level option reaches, so the load refuses what the draw does not --
#: and this set is where that asymmetry is written down rather than assumed.
#:
#: Both ``linewidth`` values are here for one reason: the family-level option
#: is not range-checked anywhere in the draw, so -1.0 and .inf alike reach
#: matplotlib and produce a line width that is not the one asked for. The
#: infinity was measured, not assumed -- it emits two numpy RuntimeWarnings
#: from a scalar multiply and draws.
#:
#: A list, and a separate one, rather than an exemption set consulted by
#: membership: seven of the refused values below are dicts, which are
#: unhashable, and two are NaN, which is not equal to itself -- so
#: ``(section, option, value) in a_set`` neither runs nor means anything
#: here. Which list a row is written in carries the split, and no value is
#: ever compared.
DRAWS_IN_SILENCE = [
    ("isotherms", "linewidth", -1.0),
    ("isotherms", "linewidth", float("inf")),
    ("isotherms", "values", (0.0, float("nan"))),
    ("moist_adiabats", "truncation", float("nan")),
]

#: The sixteen the draw refuses loudly, in one of the three exception types
#: the gate below accepts.
RAISES_AT_THE_DRAW = [
    ("isotherms", "color", "notacolour"),
    ("isotherms", "alpha", 5.0),
    ("isotherms", "emphasis", {0.0: {"color": "notacolour"}}),
    ("isotherms", "emphasis", {0.0: {"linestyle": "notaline"}}),
    ("isotherms", "labels", ("botom",)),
    ("isobars", "interval", 0.0),
    ("isobars", "interval", float("inf")),
    ("diagram", "extent", ((0.0, -80.0), (1050.0, 40.0))),
    ("diagram", "extent", ((1050.0, float("nan")), (300.0, 40.0))),
    ("diagram", "extent", ((float("inf"), -80.0), (300.0, 40.0))),
    ("isotherms", "emphasis", {700.0: {"lw": 2.0}}),
    ("isotherms", "emphasis", {0.0: {"linewidth": "thick"}}),
    ("isotherms", "emphasis", {0.0: {"alpha": 5.0}}),
    ("isotherms", "emphasis", {float("nan"): {}}),
    ("isotherms", "emphasis", {850.0: {"linewidth": int("9" * 400)}}),
    ("cursor", "fields", ("nonsuch",)),
]

#: What the draw does with a refused value, as a parametrisation label:
#: strings rather than booleans so a failing case names its own expectation.
DRAWS, RAISES = "draws", "raises"

#: Every refused value again, as the Python objects ``coerce`` would have
#: produced, for the draw to be asked about directly. Written out rather than
#: derived from ``REFUSED`` because ``coerce`` refuses these -- deriving them
#: would mean running the stage under test to build the input to its own gate.
REFUSED_AT_THE_DRAW = [
    (section, option, value, DRAWS) for section, option, value in DRAWS_IN_SILENCE
] + [(section, option, value, RAISES) for section, option, value in RAISES_AT_THE_DRAW]


def _draw_with(section, option, value):
    """Set an option through the Python API and exercise everything that reads it.

    Three actions, because "the draw" is not one thing: ``diagram.extent``
    is consumed when the axes are built, the isopleth options when the
    canvas is drawn, and ``cursor.fields`` only on mouse motion — which is
    why its mistake reaches an interactive user and nobody else
    (domain spec §1).
    """
    with tephpy.config.context(**{section: {option: value}}):
        fig = plt.figure()
        try:
            ax = fig.add_subplot(projection="tephigram")
            fig.canvas.draw()
            ax.format_coord(0.0, 0.0)
        finally:
            plt.close(fig)


@pytest.mark.parametrize(("section", "option", "value", "outcome"), REFUSED_AT_THE_DRAW)
def test_what_the_load_refuses_the_draw_refuses_too(section, option, value, outcome):
    """Makes "lifted, not invented" a checked property (domain spec §5).

    The Python API is unguarded by design (domain spec §2), so setting the
    value there and drawing asks the draw-time rule directly. Sixteen of these
    raise; the four in ``DRAWS_IN_SILENCE`` do not, and pinning that silence
    is the point — a later change that makes one of them raise is a change to
    a diagram a user already has, and this is where it surfaces.

    ``OverflowError`` is in the tuple for the huge-integer row alone. It is
    not a ``ValueError`` — it descends from ``ArithmeticError`` — so leaving
    it out would let that row pass this gate by raising something the gate
    never asked about. It is the draw-time counterpart of the rule that keeps
    such a value from stopping an import (configfile spec §5.2).
    """
    if outcome == DRAWS:
        _draw_with(section, option, value)
        return
    with pytest.raises((TypeError, ValueError, OverflowError)):
        _draw_with(section, option, value)


@pytest.mark.parametrize(("section", "option", "yaml"), ACCEPTED)
def test_what_the_load_accepts_the_draw_accepts_too(tmp_path, section, option, yaml):
    """The half that has no exceptions, and the false-positive gate's teeth.

    A rule that is too strict refuses a diagram that would have drawn. Here
    the value goes in through the file — so the whole pipeline runs — and
    then the diagram is drawn from the configuration it produced.
    """
    path = _write(tmp_path, f"{section}:\n  {option}: {yaml}\n")
    with warnings.catch_warnings():
        warnings.simplefilter("error", TephpyConfigWarning)
        tephpy.config.load(path)
    _draw_with(section, option, getattr(getattr(tephpy.config, section), option))


def test_the_draw_table_covers_every_refusal():
    """``REFUSED_AT_THE_DRAW`` is hand-written, so nothing else keeps it in step.

    It is deliberately not derived from ``REFUSED`` — deriving it would mean
    running the stage under test to build the input to its own gate — and the
    price of writing it out is that a row added to one table and forgotten in
    the other goes unnoticed. The refusal would keep its own test and quietly
    stop being asked whether the draw agrees, which is the property this
    module exists to check.

    Compared by ``(section, option)`` rather than by value: the two tables
    hold the same cases in different forms, YAML text on one side and the
    Python objects ``coerce`` would have produced on the other.
    """
    assert len(REFUSED_AT_THE_DRAW) == len(REFUSED)
    refused = sorted((section, option) for section, option, _, _ in REFUSED)
    drawn = sorted((section, option) for section, option, _, _ in REFUSED_AT_THE_DRAW)
    assert drawn == refused
```

Add `import matplotlib.pyplot as plt` to the module's imports, and check
`tests/conftest.py` for the fixture that resets `tephpy.config` between tests — if
`tephpy.config.load` is not already isolated per test, `_draw_with`'s
`tephpy.config.context` is doing that job for the draw and the loaded state must be reset by
whatever `tests/test_configfile.py` relies on.

- [ ] **Step 4: Run the gates**

Run:
```bash
pixi run --frozen python -m pytest tests/test_configfile_domain.py -q
```
Expected: PASS. The load/draw agreement tests draw ~45 diagrams and take appreciably longer
than the rest of the module; that is the cost of the gate and is expected.

Two of those draws emit `RuntimeWarning: invalid value encountered in scalar multiply` from
matplotlib, for the `isotherms.linewidth: .inf` row in `DRAWS_IN_SILENCE`. That is a numpy
warning from the render, not a tephpy signal, and `_draw_with` must not let the suite's
`filterwarnings = ["error"]` turn it into a failure — the whole point of that row is that
the draw *succeeds*. Suppress `RuntimeWarning` around the draw inside `_draw_with`, and
nothing else.

- [ ] **Step 5: Prove each gate with a mutation that fails it alone**

`git add -A` first. Mutate in the direction that isolates — a mutation that breaks a shared
helper floods the suite and proves nothing.

1. Delete the `"truncation"` entry from `_DOMAIN_VALIDATORS` →
   `test_every_option_bar_the_flags_has_a_domain_rule` fails, the one `truncation` row of
   `test_a_bad_value_warns_keeps_the_default_and_spares_the_file` alongside it, and both
   completeness gates — `test_the_refused_table_covers_every_rule` and
   `test_the_accepted_table_reaches_every_rule` — which read the same table and now see a
   rule that has rows but no entry. Four failures, not two: the gates added in this task
   overlap by design, so the blast radius here is wider than a single missing rule.
2. Change `_config`'s `mixing_ratios.values` annotation to `tuple[str, ...] | None` →
   `test_no_option_name_carries_two_domains` fails. Revert immediately; this one does break
   other tests, which is why it is listed last-resort rather than first.
3. In `_domain_alpha`, change `0.0 <= number <= 1.0` to `0.0 < number < 1.0` →
   `test_a_legitimate_value_is_not_refused` fails on the two bound rows, and no refusal test
   fails. This is the mutation that shows the no-false-positives gate is the only one that
   can see an over-strict rule.
4. In `_as_float`, replace the body with an `isinstance` test in place of the coercion:

   ```python
       if not isinstance(value, float):
           raise _DomainError(expects, _describe(value))
       return value
   ```

   → `test_a_legitimate_value_is_not_refused` fails on `emphasis: {850.0: {linewidth: 2}}`
   and `{850.0: {alpha: 1}}`, and every refusal test still passes. The `return value` is
   load-bearing: `_as_float` is annotated `-> float` and its callers use the result, so a
   body that only raises returns `None` on the success path and takes ~25 tests down with
   it, which proves nothing about the coercion.
5. *Move* the `("isotherms", "alpha", 5.0)` row from `RAISES_AT_THE_DRAW` into
   `DRAWS_IN_SILENCE` → one `test_what_the_load_refuses_the_draw_refuses_too` case fails,
   with `ValueError: alpha (5.0) is outside 0-1 range` escaping `_draw_with` uncaught, and
   nothing else does. Move rather than copy: a copy leaves the row in both lists, so the
   correspondence gate fails on the length too and the isolation is lost. `DRAWS_IN_SILENCE`
   has to be four specific triples the draw is *known* to accept, and this is what shows it
   is not a blanket that would swallow a genuine disagreement.
6. Delete the `("cursor", "fields", ("nonsuch",))` entry from `RAISES_AT_THE_DRAW` →
   `test_the_draw_table_covers_every_refusal` fails on the length assertion, and no other
   test does. This is the drift the gate exists to catch: the `cursor.fields` refusal keeps
   its own row in `REFUSED` and simply stops being asked whether the draw agrees. Confirm
   that without the new gate the suite is entirely green with that entry gone — that is the
   whole argument for adding it.

- [ ] **Step 6: Correct a count that has already drifted**

`test_a_bad_value_warns_keeps_the_default_and_spares_the_file`'s docstring says "eight
failed at the first draw with tephpy's own message, four with matplotlib's, and three drew a
diagram that was simply not the one the file asked for". Those numbers describe fifteen
rows. `REFUSED` held sixteen when they were written and holds twenty now, so the sentence
was wrong before this task and is wronger after it.

Replace the hand-count with a sentence that carries no number, pointing instead at the gate
below that measures it:

```python
    Every one of these loaded silently before: most failed at the first draw,
    with tephpy's message or matplotlib's, and the rest drew a diagram that
    was simply not the one the file asked for (domain spec §1). Which case
    falls where is not counted here — ``DRAWS_IN_SILENCE`` below is where
    that split is recorded, and it is checked rather than asserted in prose.
```

A number in a docstring that nothing checks will drift again; this is the third time these
counts have needed correcting, so remove the number rather than fixing it.

- [ ] **Step 7: Commit**

```bash
pixi run --frozen lint
git add tests/test_configfile_domain.py
git commit -m "Gate the domain rules for completeness and against the draw"
```

---

### Task 4: Publish the Vocabularies on the Options Reference Page

The options reference page must publish the closed vocabularies from the same `_constants`
objects that enforce them, so the page cannot document a legal set the loader rejects
(domain spec §6).

**Files:**
- Modify: `src/tephpy/_configfile.py:727-738` (`_LINE_DESCRIPTIONS`), `:845-849`
  (`CONFIG_DESCRIPTIONS["cursor"]`), `:858-875` (`_LINE_DETAILS`)
- Test: `tests/test_configfile_reference.py`

**Interfaces:**
- Consumes: `_constants.EDGES`, `EMPHASIS_STYLE_KEYS`, `CURSOR_FIELD_NAMES`, already
  imported into `_configfile` by Task 2.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_configfile_reference.py`, and add
`from tephpy._constants import CURSOR_FIELD_NAMES, EDGES, EMPHASIS_STYLE_KEYS` to its
imports:

```python
@pytest.mark.parametrize(
    ("section", "option", "vocabulary"),
    [
        ("isotherms", "labels", EDGES),
        ("cursor", "fields", CURSOR_FIELD_NAMES),
    ],
)
def test_a_description_lists_its_whole_closed_vocabulary(section, option, vocabulary):
    """The page cannot document a legal set the loader rejects.

    The joined names are asserted as one run, not member by member, so a
    name added to the constant and not to the prose fails here — which is
    the only way to tell a derived string from a hand-written one that
    happens to agree today (domain spec §6).
    """
    description = _configfile.CONFIG_DESCRIPTIONS[section][option]
    assert ", ".join(vocabulary) in description


def test_the_emphasis_detail_names_every_style_key():
    """The other closed vocabulary, in the prose that documents overrides.

    The whole ``and``-list as one run, for the same reason: a key added to
    the constant and left out of the prose has to fail somewhere.
    """
    keys = ", ".join(f"``{key}``" for key in EMPHASIS_STYLE_KEYS[:-1])
    detail = _configfile.CONFIG_DETAILS["isotherms"]["emphasis"]
    assert f"{keys} and ``{EMPHASIS_STYLE_KEYS[-1]}``" in detail


def test_the_page_carries_the_vocabularies_it_documents():
    """The descriptions above reach the rendered page, not just the table."""
    page = rendered()
    assert ", ".join(EDGES) in page
    assert ", ".join(CURSOR_FIELD_NAMES) in page
```

- [ ] **Step 2: Run them to verify which fail**

Run:
```bash
pixi run --frozen python -m pytest tests/test_configfile_reference.py -q
```
Expected: FAIL on the `cursor.fields` parametrisation and on
`test_the_page_carries_the_vocabularies_it_documents` — `CONFIG_DESCRIPTIONS["cursor"]["fields"]`
names no vocabulary at all today. The `labels` and `emphasis` cases pass already, against
hand-written strings that happen to agree; Step 5's mutation is what proves the derivation.

- [ ] **Step 3: Derive the descriptions from the constants**

In `src/tephpy/_configfile.py`, replace the `labels` entry of `_LINE_DESCRIPTIONS`
(lines 732-735) —

```python
        "labels": (
            "true, false, or the diagram edges to label (bottom, top, left, "
            "right), singly or as a list."
        ),
```

— with:

```python
        "labels": (
            "true, false, or the diagram edges to label "
            f"({', '.join(EDGES)}), singly or as a list."
        ),
```

The rendered run is unchanged, character for character: it is the same four names in the
same order, now read from the tuple the loader checks against instead of retyped.

Replace the `cursor` section of `CONFIG_DESCRIPTIONS` (lines 845-849) with:

```python
        "cursor": MappingProxyType(
            {
                "fields": (
                    "Cursor readout fields, in display order, from "
                    f"{', '.join(CURSOR_FIELD_NAMES)}."
                ),
            }
        ),
```

A description is dual-register — the same string is a template comment and reStructuredText
— so `test_every_description_is_free_of_markup` forbids `*`, `` ` ``, `|`, `--` and a
trailing underscore. The field names carry mid-word underscores only and none of the
forbidden tokens, so they clear it. Measured: the template's `textwrap.fill` takes the new
description to two lines of at most 86 columns, inside the 88 the template gate allows.

Add above `_LINE_DETAILS` (line 858):

```python
#: ``EMPHASIS_STYLE_KEYS`` as an ``and``-list of reStructuredText literals, for
#: the ``emphasis`` detail below. Built from the constant the loader checks
#: against, so the page cannot list a style key the loader rejects, nor omit
#: one it accepts (domain spec §6). Detail prose, not a description, so the
#: double backquotes are wanted here — the markup ban applies to
#: ``CONFIG_DESCRIPTIONS`` alone, which has to read as a plain-text comment in
#: the generated template too.
_EMPHASIS_STYLE_PROSE: Final[str] = (
    f"{', '.join(f'``{key}``' for key in EMPHASIS_STYLE_KEYS[:-1])} "
    f"and ``{EMPHASIS_STYLE_KEYS[-1]}``"
)
```

and replace the first two lines of the `emphasis` entry of `_LINE_DETAILS` (lines 866-867) —

```python
"Each value is a mapping of style overrides -- ``color``,"

"``linewidth``, ``linestyle`` and ``alpha`` -- and an omitted key "
```

— with:

```python
"Each value is a mapping of style overrides --"

f"{_EMPHASIS_STYLE_PROSE} -- and an omitted key "
```

leaving the remaining five lines of that string unchanged. The first line stays a plain
string, not an f-string: an f-string with no placeholder is ruff `F541`. Only the second
line becomes one, which leaves the literal braces in `` ``{20.0: {}}`` `` two lines below
untouched — implicit concatenation formats each piece separately.

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
pixi run --frozen python -m pytest tests/test_configfile_reference.py tests/test_configfile_template.py -q
```
Expected: PASS. `test_no_generated_template_line_exceeds_the_source_width` is the one to
watch — the `cursor.fields` line grew by 52 characters.

- [ ] **Step 5: Prove the derivation with a mutation**

`git add -A` first, then for each: apply, run, confirm the failure, revert both edits with
`git checkout <paths>`.

Every mutation here is a **pair**, and it has to be. Mutating a constant alone cannot fail
these tests: the prose is derived from the constant and so is the expectation, so both move
together and the assertion still holds. That agreement is the property, not a weakness — but
it means the isolating mutation is to break the derivation first and then move the constant.
Each pair is: revert one prose string to the literal it replaced, append a name to its
constant, run, confirm the named test fails.

1. Restore `_LINE_DESCRIPTIONS["labels"]` to the literal `"(bottom, top, left, right)"`
   form, and append `"middle"` to `_constants.EDGES` →
   `test_a_description_lists_its_whole_closed_vocabulary[isotherms-labels]` and
   `test_the_page_carries_the_vocabularies_it_documents` both fail.
2. Restore `CONFIG_DESCRIPTIONS["cursor"]["fields"]` to `"Cursor readout fields, in display
   order."`, and append `"dewpoint"` to `_constants.CURSOR_FIELD_NAMES` →
   `test_a_description_lists_its_whole_closed_vocabulary[cursor-fields]` fails. Task 1's
   `test_the_cursor_registry_and_the_vocabulary_agree` fails on this one too, because
   `dewpoint` has no formatter — that is the gate that owns the constant, and both firing is
   correct.
3. Restore the `emphasis` detail's opening to its literal ``` ``color``, ``linewidth``,
   ``linestyle`` and ``alpha`` ``` form, and append `"joinstyle"` to
   `_constants.EMPHASIS_STYLE_KEYS` → `test_the_emphasis_detail_names_every_style_key` fails.

- [ ] **Step 6: Build the docs and read the page**

Run:
```bash
pixi run --frozen docs
```
Expected: PASS. Then open the generated options reference page and read the three entries —
`isotherms.labels`, `isotherms.emphasis` and `cursor.fields` — as a user would. A literal
block is tokenised as Python in the rendered HTML, so grep the *source* of the generated
page rather than the HTML if checking by hand.

- [ ] **Step 7: Commit**

```bash
pixi run --frozen lint
git add src/tephpy/_configfile.py tests/test_configfile_reference.py
git commit -m "Publish the closed vocabularies on the options reference page"
```

---

### Task 5: Documentation and Specification Housekeeping

**Files:**
- Modify: `docs/src/howtos/configuration.rst:118-137`
- Modify: `docs/src/developer/specs/2026-08-07-config-file-design.md:533-539`, `:681-687`
- Modify: `docs/src/developer/specs/2026-08-12-config-domain-validation-design.md` — §1's
  table and its two class counts, §4, §5's table row and asymmetry paragraph
- Create: `changelog/<PR>.bugfix.rst`, `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: the behaviour of Tasks 2-4.
- Produces: nothing.

- [ ] **Step 1: Add the how-to paragraph**

In `docs/src/howtos/configuration.rst`, after the paragraph ending "Quote them if you meant
the words." (line 131) and before "These warnings arrive once" (line 133), insert:

```rst
A value of the right type can still be refused. ``color: notacolour`` is a
string and ``interval: 0`` is a number, and neither is something tephpy can
draw; both warn and are skipped exactly as ``linewidth: thick`` is, and the
warning says what the option can accept:

.. code-block:: text

    tephpyrc.yaml: ignoring isotherms.color, which expects a colour matplotlib knows, not the string 'notacolour'
    tephpyrc.yaml: ignoring isobars.interval, which expects a positive, finite number, not the number 0.0

Where the set of legal values is closed, the warning lists it, because your
next move is to pick from it. Where it is open — no message can enumerate the
colours matplotlib knows — it is described instead. And ``color: b0b0b0``,
the mirror image of the ``#`` trap above, is told what it is probably missing:

.. code-block:: text

    tephpyrc.yaml: ignoring isotherms.color, which expects a colour matplotlib knows, not the string 'b0b0b0'; did you mean '#b0b0b0'?

An option is skipped whole. ``emphasis`` holds a mapping of members to
styles, so one bad member costs you the whole ``emphasis`` option, not just
that member — the good members go back to being drawn like every other
member of the family. This is deliberate: told that ``emphasis`` was ignored
you can read your own file and see what you lost, where told it was partly
applied you could not tell what was in force.
```

- [ ] **Step 2: Verify the how-to renders and the snippets are true**

Run:
```bash
pixi run --frozen docs
```
Expected: PASS.

Then run every message in the new prose against the code rather than trusting it — lint,
tests and a docs build all pass a snippet that cannot work:

```bash
pixi run --frozen python - <<'PY'
import pathlib, tempfile, warnings
import tephpy
cases = [
    ("isotherms:\n  color: notacolour\n"),
    ("isobars:\n  interval: 0.0\n"),
    ("isotherms:\n  color: b0b0b0\n"),
]
with tempfile.TemporaryDirectory() as tmp:
    path = pathlib.Path(tmp) / "tephpyrc.yaml"
    for text in cases:
        path.write_text(text, encoding="utf-8")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            tephpy.config.load(path)
        for entry in caught:
            print(entry.message)
PY
```
Expected: three lines matching the three literal blocks above, character for character
except for the temporary path in place of `tephpyrc.yaml`. If any differs, the prose is
wrong — fix the prose, not the message.

- [ ] **Step 3: Repoint configfile spec §5.2**

In `docs/src/developer/specs/2026-08-07-config-file-design.md`, replace the closing sentences
of the §5.2 "A limit, stated rather than designed around" paragraph (lines 536-539) —

```markdown
draw. Checking it needs to know which style keys exist and what each accepts, which is the
knowledge a domain check needs — and domain validity is out of scope here. This section
covers types only. Whether `notacolour` names a colour, or `nonsuch` a cursor field, is a
separate question, deliberately left unanswered (§9).
```

— with:

```markdown
draw. Checking it needs to know which style keys exist and what each accepts, which is the
knowledge a domain check needs — and domain validity is out of scope here. This section
covers types only. Whether `notacolour` names a colour, or `nonsuch` a cursor field, is a
separate question, answered by domain spec §3: a second stage behind this one, which reads
the converted value and so reaches the `emphasis` style values this section cannot (§9).
```

Both citations are written bare. A backticked cross-document pointer is an inline literal,
not a link, and the citation gate counts literals as legitimate — so it renders as a dead
code box and nothing reports it.

- [ ] **Step 4: Resolve configfile spec §9's deferred entry**

Replace lines 681-687 with:

```markdown
- **Resolved** (2026-08-12, PR {pull}`<PR>`) — **domain validation of a value that has the
  right type.** §5.2 checks a value against the type its field declares and stops there:
  `color: notacolour` is a string, so it loaded, and matplotlib rejected it at the first
  draw. Answering it properly meant a per-option vocabulary — the colours, the edge names,
  the cursor fields, the `emphasis` style keys — which is why it was a larger piece of work
  than the type check it sits behind. Specified as domain spec §1–domain spec §7 and settled by that
  work ({issue}`116`). This was the one entry here that was not a decision against, and the
  only one the docs spec §3.5 contract required an issue for.
```

`<PR>` is filled in at Step 8, once the pull request exists.

- [ ] **Step 5: Sweep the domain specification for the drift this work caused**

The domain spec is a living document (docs spec §3.4), so editing it means sweeping its
enumerations for drift rather than only the section you came for. Three measurements taken
during Tasks 2 and 3 are not in it. All three were measured against the current tree through
the unguarded Python API, which reproduces the pre-change draw path exactly — nothing on
this branch touches the draw, only the address the constants live at — so they belong in
§1's "as of {pull}`125`" table without a caveat.

In `docs/src/developer/specs/2026-08-12-config-domain-validation-design.md`, add to §1's
table, each directly below the row it belongs with:

```markdown
| `isotherms: {linewidth: .inf}` | silent | **draws** |
| `isobars: {interval: .inf}` | silent | `ValueError: 'isobars' interval must be a positive, finite number: inf` |
| `diagram: {extent: [[.inf, -80.0], [300.0, 40.0]]}` | silent | `ValueError: extent corners must be physical (pressure > 0 hPa): ((inf, -80.0), (300.0, 40.0))` |
```

Then correct the two class counts the table feeds. "**Three values never produce a message
at all.**" becomes **Four**, and its list gains `linewidth: .inf` — the same option as
`linewidth: -1.0`, unchecked at the family level in either direction. "**Eight fail with
tephpy's own message**" becomes **Ten**. The matplotlib count of four is unchanged.

§4 gains the one case that fits none of §1's three classes. A style override holding a
309-or-more-digit integer raises `OverflowError: int too large to convert to float` from
`float()` — Python's message, naming neither tephpy nor the option. Task 2 added the guard;
§4 currently cites the 401-digit number only as precedent for not echoing a value back.
Record the refusal itself, after the compound-option paragraph:

```markdown
A number too large to convert is refused with the same frame rather than escaping as an
`OverflowError`. The type stage already guards this for a plain number (configfile spec
§5.2); an `emphasis` style value reaches the domain stage unconverted, so the guard has to
be repeated where the conversion actually happens.
```

§5 is where the drift bites hardest, because its numbers are inherited from §1 and the gate
does not measure §1 — it measures its own two tables, which are deliberately not the same
set. Replace the paragraph beginning "The other direction is deliberately not symmetric"
(lines 297-304) with:

```markdown
The other direction is deliberately not symmetric, because §1 measured that it is not. The
gate's own table holds twenty refused values; sixteen raise at the draw and four do not.
Those four — `linewidth: -1.0`, `linewidth: .inf`, `values: [.nan]` and `truncation: .nan` —
are the rows §1 calls the worst outcome available, and they are the reason this work exists:
a rule with no draw-time counterpart on the option that carries it (§3.3). So the gate
asserts what each case actually does, and a further gate asserts that the two tables hold
the same `(section, option)` pairs, because both are hand-written and would otherwise drift.
Pinning the silence is the point. A later change that makes one of those four raise is a
change to the diagram a user already has, and this gate is where it surfaces.

The counts here are the gate's, not §1's. The two sets overlap without matching: the gate
drops `color: 'b0b0b0'`, which has its own named test for the `#` hint, and adds cases §1
does not tabulate.
```

and the §5 table's **Load/draw agreement** row, whose "bar the three §1 rows that do not" is
the same stale claim:

```markdown
| **Load/draw agreement** | Every accepted value draws; every refused value raises at the draw bar the four that silently do not, and the two tables cover the same options |
```

- [ ] **Step 6: Run the citation gates**

Run:
```bash
pixi run --frozen lint
pixi run --frozen docs
```
Expected: PASS. Read the `docs-check-citations` output's linked/literal counts rather than
just its exit code — the gate counts a literal citation as legitimate, so a backticked
cross-document pointer passes silently while rendering as a dead code box. The linked count
must rise by the number of citations added.

- [ ] **Step 7: Commit the documentation**

```bash
git add docs/src/howtos/configuration.rst docs/src/developer/specs/2026-08-07-config-file-design.md docs/src/developer/specs/2026-08-12-config-domain-validation-design.md
git commit -m "Document domain validation and resolve its deferred entry"
```

- [ ] **Step 8: Push, open the pull request, then write the changelog**

The fragment is named for the pull request, and an issue filed between now and then steals
the number — so the PR comes first.

```bash
git push -u origin <branch>
gh pr create --base main --title "Check a configuration value against its option's domain" --body "..."
```

The PR body uses bare `#N` references, not `{issue}`/`{pull}` roles — Sphinx roles render
literally on GitHub. Close {issue}`116` from the body.

Then, with the number in hand, create `changelog/<PR>.bugfix.rst`:

```rst
Fixed a configuration file value being applied without any check that its option
can accept it (:issue:`116`). ``color: notacolour`` is a string and
``interval: 0`` is a number, so both passed the type check added in
:issue:`105` and loaded in silence; matplotlib or tephpy then rejected them at
the first draw, in a traceback naming neither the file nor the line you edited.
Some did not even do that — ``linewidth: -1.0``, ``linewidth: .inf``,
``values: [.nan]`` and ``truncation: .nan`` drew a diagram that was simply not
the one the file asked for. Every one of these now warns as the file is read,
naming the file, the option and what the option can accept, and skips just that
option — the rest of the file still applies. Where the legal set is closed, the
warning lists it.
``color: b0b0b0`` is told it is probably missing a ``#``, the mirror image of
the ``color: #b0b0b0`` trap that YAML reads as a comment. A compound option is
skipped whole: one bad member of an ``emphasis`` mapping costs the whole
``emphasis`` option. Values set through Python — ``config.isotherms.color =
"notacolour"`` — are unaffected, and still fail at the draw as before.
(:user:`claude`)
```

and `changelog/<PR>.documentation.rst`:

```rst
The configuration how-to now covers a value of the right type that its option
still cannot accept, and the options reference page lists the closed sets of
legal values — the diagram edges for ``labels``, the style keys for
``emphasis``, and the cursor readout fields — from the same objects the loader
checks against, so the page cannot document a value the loader rejects
(:issue:`116`). (:user:`claude`)
```

```bash
pixi run --frozen lint
git add changelog/
git commit -m "Add the changelog fragments"
git push
```

- [ ] **Step 9: Close out the issue's label**

`design: open` is checked in both directions, so removing it from {issue}`116` is part of
the work (domain spec §6). Do this after the PR merges, or note it for the merge.

- [ ] **Step 10: Full verification**

```bash
pixi run --frozen tests
pixi run --frozen lint
pixi run --frozen docs
```
Expected: all three PASS. Then verify the RTD PR preview at
`tephpy--<PR>.org.readthedocs.build` — RTD skips commits, so a missing status is not the
same as no build.

---

## Self-Review

**Spec coverage.**

| domain spec | Task |
|---|---|
| §3.1 second stage in `coerce`, `_DomainError`, keyed by option name | Task 2 Steps 4-5 |
| §3.2 vocabularies move to `_constants`, `plotting` imports back, matplotlib imports | Task 1, Task 2 Step 3 |
| §3.3 the eleven rules, `emphasis`'s six, the `_as_float` coercion, granularity | Task 2 Steps 4, 1 |
| §4 the message frame, the closed-set listing, the compound *found* half, the `#` hint | Task 2 Steps 1, 5 |
| §5 one case per §1 row | Task 2 Step 1 |
| §5 completeness, unambiguous keys | Task 3 Step 1 |
| §5 vocabulary agreement, address change only | Task 1 Step 1 |
| §5 no false positives | Task 3 Step 2 |
| §5 load/draw agreement | Task 3 Step 3 |
| §5 each gate proved by a mutation that fails it alone | Task 1 Step 7, Task 3 Step 5, Task 4 Step 5 |
| §6 how-to paragraph | Task 5 Step 1 |
| §6 reference page publishes the vocabularies | Task 4 |
| §6 configfile spec §5.2 repoint, §9 → Resolved, `design: open` removal | Task 5 Steps 3, 4, 9 |
| docs spec §3.4 living-spec housekeeping: §1's table, §4's overflow case, §5's counts | Task 5 Step 5 |
| §7 non-goals | nothing to implement; Task 2's `_DOMAIN_VALIDATORS` deliberately has no `__setattr__` counterpart, and the changelog says so |

**Type consistency.** `_DomainError(expects, found)` is constructed in eight places and read
in two (`_domain_emphasis`'s re-raise and `coerce`), always via `.expects`/`.found`. Every
`_domain_*` function has signature `(value: object) -> None`; `_as_float` alone is
`(value: object, expects: str) -> float` and is the only one that returns. `_DOMAIN_VALIDATORS`
and `_EMPHASIS_STYLE_RULES` are both `Mapping[str, Callable[[object], None]]`.
`CURSOR_FIELD_NAMES`, `EDGES` and `EMPHASIS_STYLE_KEYS` are `Final[tuple[str, ...]]`
throughout, and `isopleths` binds the first two under their original names.

**Known asymmetry, stated rather than designed around.** A degenerate `extent` — two corners
that map to the same x or y — is refused by `set_extent` and not by the load-time rule, which
checks only finiteness and positive pressure. That direction is out of scope by construction:
domain spec §5's agreement gate runs load-refuses ⇒ draw-refuses, not the converse, because
the converse would require the loader to re-derive the tephigram transforms. Coincident
*pressures* are not degenerate — measured: `((1050, -80), (1050, 40))` draws.
