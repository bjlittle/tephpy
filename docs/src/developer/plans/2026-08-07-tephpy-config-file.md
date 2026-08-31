# Configuration Files Implementation Plan

> **Point-in-time record.** This plan captures what was intended before implementation. It
> is not updated afterwards — where the implementation departed from it, the departure is
> recorded in the pull request, and the living design specification in
> [`../specs/`](../specs/) is what describes tephpy as it stands.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user keep their tephigram house style in a YAML file instead of retyping it
at the top of every script, and give them a `tephpy config` command that writes the file
for them and says which one is in force.

**Architecture:** A persistence tier *beneath* `tephpy.config`, added without touching the
resolution path any image baseline covers. `_configfile.py` is new and owns everything to do
with the file — discovery, parsing, coercion, template rendering, writing. `_config.py`
gains only lifecycle (`source`, `reset`, `load`, `save`); its dataclasses are unchanged.
`_cli.py` is a thin click wrapper holding no logic that is unreachable from Python. The
template's defaults come from a new declarative `CONFIG_DEFAULTS` table in `_constants.py`,
whose entries reference the existing constants by name rather than restating their literals,
and a gate test holds it against what `IsoplethFamily._resolve` actually produces.

**Tech Stack:** Python 3.12+; PyYAML (`yaml.safe_load` only); platformdirs; click; pytest
with `CliRunner`; sphinx-click; pixi.

**Spec:** `configfile spec §…`, in
[`../specs/2026-08-07-config-file-design.md`](../specs/2026-08-07-config-file-design.md).

**Issue:** None. Requested directly by the maintainer.

## Global Constraints

- **Every pixi invocation carries `--frozen`** — `pixi run --frozen tests`,
  `pixi run --frozen lint`, `pixi run --frozen docs` — with exactly one exception, the
  deliberate re-lock in Task 3. Never let pixi re-solve otherwise.
- **Every new source file carries the BSD copyright header** — ruff `CPY001` enforces it.
  Copy it verbatim from the first four lines of `src/tephpy/_config.py`.
- **Line length is 88 columns**, ruff-enforced.
- **Docstrings are numpydoc**, validated by the `numpydoc-validation` pre-commit hook.
  Every public function needs `Parameters`, `Returns`/`Yields`, and `Raises` where it
  raises.
- **Import order is ruff-isort's**: within a section, plain `import x` statements come
  before `from x import y`, each block alphabetised, and the sections separated by a blank
  line (standard library, third party, first party). `pixi run --frozen lint` settles it —
  run it before reasoning about a failure.
- **Tests mirror the source layout** (`tests/AGENTS.md`). `_config.py`, `_configfile.py`
  and `_cli.py` are top-level modules, so their tests are `tests/test_config*.py` and
  `tests/test_cli.py` — not in a subdirectory.
- **`pyproject.toml` sets `filterwarnings = ["error"]`.** Any test that exercises a
  `TephpyConfigWarning` path must wrap it in `pytest.warns`, or the warning fails the test.
- **Never write to the real user configuration directory from a test.** Every filesystem
  test uses `tmp_path`, and every test that touches `$TEPHPYRC` sets it via
  `monkeypatch.setenv`.
- **`yaml.safe_load` only.** `yaml.load` is forbidden — a configuration file is untrusted
  input (configfile spec §2).
- **CI is linux-64 only** (`.github/workflows/ci-tests.yml` pins `os: ["ubuntu-latest"]`),
  so a test that depends on platform-specific path resolution is never exercised elsewhere.
  Write the subprocess tests to be hermetic on macOS and Windows anyway — the developer most
  likely to have a real user configuration file is the one running the suite locally.
- **The specifications are living documents; the plans are frozen** (docs spec §3.4).
  Nothing under `docs/src/developer/plans/` is edited by this work, including this file
  once its pull request merges.
- **Cite the specification as `configfile spec §N`**, never as a bare `spec §N` — a bare
  citation resolves to the parent specification, whose §3.5 is a different section on a
  closely related subject.
- **Every commit message body references issues and pull requests with the `{issue}` and
  `{pull}` roles**, never a bare `#N` or a GitHub URL — the `check-github-references` gate
  reads the whole tree.
- **Changelog fragments are named `changelog/<PR>.<type>.rst`** and end with
  ``(:user:`<github-username>`)``. Find `<PR>` with

  ```bash
  gh api 'repos/bjlittle/tephpy/issues?state=all&per_page=1' --jq '.[0].number'
  ```

  and add one — `state=all` is load-bearing, because the default lists open issues only and
  under-reports the highest number. The same `<PR>` is used for both fragments this plan
  writes. `<github-username>` is the handle of whoever implements the task.

---

### Task 1: Configuration lifecycle — `source`, `reset()`, and the two new exception names

Foundation with no new dependencies and no file I/O. Everything later builds on `reset()`,
so it lands first and is provable on its own.

**Files:**
- Modify: `src/tephpy/exceptions.py`
- Modify: `src/tephpy/_config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `tephpy.exceptions.TephpyConfigError(TephpyError)`,
  `tephpy.exceptions.TephpyConfigWarning(UserWarning)`;
  `Config.source -> pathlib.Path | None` (read-only property),
  `Config.reset() -> None`, and the private attribute `Config._source` that backs them.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_config.py`, adding `import dataclasses`, `import pathlib` and
`import pytest` to the module's imports if they are not already there:

```python
def test_source_is_not_a_config_section():
    """``source`` must not become an eighth section.

    ``Config.context`` enumerates the sections with ``dataclasses.fields``,
    so an annotated class attribute would present ``source`` as a section
    and make ``context(source=...)`` silently meaningful
    (configfile spec §3.1).
    """
    names = {field.name for field in dataclasses.fields(tephpy.config)}
    assert names == {
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
        "diagram",
        "cursor",
    }


def test_source_is_read_only():
    assert tephpy.config.source is None
    with pytest.raises(AttributeError):
        tephpy.config.source = "somewhere"


def test_reset_restores_the_pristine_configuration():
    tephpy.config.isotherms.color = "purple"
    tephpy.config.diagram.extent = ((900.0, -20.0), (300.0, 30.0))
    tephpy.config.reset()
    assert tephpy.config.isotherms.color is None
    assert tephpy.config.diagram.extent is None


def test_reset_keeps_section_identity():
    """A family holds the section object it was created with.

    ``IsoplethFamily`` is handed ``getattr(config, name)`` and keeps that
    reference, so ``reset`` must clear the sections in place. Rebinding
    them to fresh instances would leave every existing family reading a
    detached object.
    """
    section = tephpy.config.isotherms
    tephpy.config.isotherms.color = "purple"
    tephpy.config.reset()
    assert tephpy.config.isotherms is section
    assert section.color is None


def test_reset_clears_the_source():
    tephpy.config._source = pathlib.Path("/somewhere/tephpyrc.yaml")
    tephpy.config.reset()
    assert tephpy.config.source is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_config.py -k "source or reset" -v`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'source'`.

- [ ] **Step 3: Add the two names to `exceptions.py`**

Add `"TephpyConfigError"` and `"TephpyConfigWarning"` to `__all__`, keeping it
alphabetically sorted (ruff `RUF022`) — they sort after `"MissingDataError"` and before
`"TephpyError"`.

Append the classes after `TephpyIOError`:

```python
class TephpyConfigError(TephpyError):
    """A configuration file could not be read or made sense of.

    A malformed YAML document, a top-level entry that is not a mapping, an
    unknown configuration section, and a ``$TEPHPYRC`` naming a file that
    does not exist all raise this. Raised only when the file was asked for
    explicitly; the import-time auto-load warns instead
    (configfile spec §5).
    """


class TephpyConfigWarning(UserWarning):
    """A configuration file was used, but something in it was ignored.

    An unknown option, an option whose value is an explicit null, and any
    failure during the import-time auto-load warn rather than raise, so a
    typo in a configuration file cannot make ``tephpy`` unimportable
    (configfile spec §5).
    """
```

Extend the module docstring with a sentence, because the existing text promises that
everything in the module derives from `TephpyError`:

```
Configuration-file problems are the one place tephpy also warns:
:class:`TephpyConfigWarning` is a ``UserWarning``, not a
:class:`TephpyError`, because an unusable configuration file degrades to
the hardwired defaults instead of stopping the import (configfile spec §5).
```

- [ ] **Step 4: Add the lifecycle to `Config` in `_config.py`**

Add `from pathlib import Path` to the `TYPE_CHECKING` block. Add these members to `Config`,
after the field declarations and before `context`:

```python
def __post_init__(self) -> None:
    """Initialise the state that is deliberately not a field.

    Notes
    -----
    ``_source`` is set here rather than declared as a class attribute
    because an annotated class attribute becomes a dataclass field, and
    :meth:`context` enumerates the configuration sections with
    ``dataclasses.fields`` — a field here would present ``source`` as an
    eighth section (configfile spec §3.1).
    """
    self._source: Path | None = None


@property
def source(self) -> Path | None:
    """The configuration file in force.

    Returns
    -------
    pathlib.Path or None
        The file this configuration was loaded from, or ``None`` when
        no file was found, none was loaded, or the load failed.
    """
    return self._source


def reset(self) -> None:
    """Restore the pristine, hardwired configuration.

    Every option in every section returns to ``None`` — falling through
    to the ``_constants`` conventions — and :attr:`source` becomes
    ``None``. The section objects are cleared in place rather than
    rebound, because an
    :class:`~tephpy.plotting.isopleths.IsoplethFamily` keeps a reference
    to the section it was created with.
    """
    pristine = Config()
    for field in dataclasses.fields(self):
        section = getattr(self, field.name)
        fresh = getattr(pristine, field.name)
        for option in dataclasses.fields(fresh):
            setattr(section, option.name, getattr(fresh, option.name))
    self._source = None
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_config.py -v`
Expected: PASS, including the pre-existing tests.

- [ ] **Step 6: Prove the identity test is not vacuous**

Stage the work first — `git checkout <path>` reverts from the index, so an unstaged
mutate-verify-revert cycle discards the real change along with the mutation:

```bash
git add src/tephpy/_config.py src/tephpy/exceptions.py tests/test_config.py
```

Then temporarily change the body of `reset`'s loop to rebind instead of clearing in place:

```python
        for field in dataclasses.fields(self):
            setattr(self, field.name, getattr(pristine, field.name))
```

Run: `pixi run --frozen pytest tests/test_config.py -v`
Expected: `test_reset_keeps_section_identity` FAILS, and nothing else does.
Revert with `git checkout -- src/tephpy/_config.py`.

- [ ] **Step 7: Commit**

```bash
git commit -m "Add the configuration lifecycle and its two exception names"
```

---

### Task 2: `CONFIG_DEFAULTS` and the defaults gate

**Files:**
- Modify: `src/tephpy/_constants.py`
- Create: `tests/test_config_defaults.py`

**Interfaces:**
- Consumes: `Config` from Task 1 (for the section enumeration).
- Produces: `tephpy._constants.CONFIG_DEFAULTS`, a
  `Mapping[str, Mapping[str, object]]` keyed by section name then option name. A value of
  `None` records an option with no default — not an option defaulting to null.

- [ ] **Step 1: Write the failing gate**

Create `tests/test_config_defaults.py` — BSD header first, then:

```python
"""Gate CONFIG_DEFAULTS against the defaults the plotting path resolves.

``CONFIG_DEFAULTS`` exists so the template generator never re-enters
``IsoplethFamily._resolve``, which every image baseline covers (configfile
spec §3.4). Being a second copy, it drifts unless something holds it in
place; that is this file.
"""

from __future__ import annotations

import dataclasses

import pytest

import tephpy
from tephpy._config import Config
from tephpy._constants import CONFIG_DEFAULTS, CURSOR_FIELDS, DEFAULT_EXTENT
from tephpy.plotting import isopleths

FAMILY_SECTIONS = (
    "isotherms",
    "isobars",
    "dry_adiabats",
    "moist_adiabats",
    "mixing_ratios",
)


def _resolved(name):
    """Resolve a family's options with no kwargs and a pristine config."""
    spec = isopleths._FAMILY_SPECS[name]
    return isopleths.IsoplethFamily(spec, getattr(tephpy.config, name)).options


def _family_cases():
    return [
        (section, option)
        for section in FAMILY_SECTIONS
        for option in CONFIG_DEFAULTS[section]
    ]


def test_config_defaults_covers_exactly_the_config_sections():
    """The gate's own input must not silently empty out."""
    assert set(CONFIG_DEFAULTS) == {field.name for field in dataclasses.fields(Config)}


def test_config_defaults_covers_exactly_each_section_option():
    for field in dataclasses.fields(Config):
        section = getattr(tephpy.config, field.name)
        expected = {option.name for option in dataclasses.fields(section)}
        assert set(CONFIG_DEFAULTS[field.name]) == expected, field.name


def test_the_gate_covers_every_family_option():
    """A parametrised gate over an empty list passes by checking nothing.

    Forty: eight ``FamilyOptions`` each for isotherms, isobars and dry
    adiabats, nine for moist adiabats (plus ``truncation``), and seven for
    mixing ratios (``LineOptions`` plus ``values``, with no ``interval``).
    With ``diagram.extent`` and ``cursor.fields`` below, that is the 42
    options of configfile spec §3.3.
    """
    assert len(_family_cases()) == 40


@pytest.mark.parametrize(("section", "option"), _family_cases())
def test_config_default_matches_the_resolved_default(section, option):
    resolved = _resolved(section)
    assert CONFIG_DEFAULTS[section][option] == getattr(resolved, option)


def test_diagram_and_cursor_defaults():
    """The two non-family sections resolve outside IsoplethFamily."""
    assert CONFIG_DEFAULTS["diagram"]["extent"] == DEFAULT_EXTENT
    assert CONFIG_DEFAULTS["cursor"]["fields"] == CURSOR_FIELDS
```

`IsoplethFamily(spec, section)` needs no axes — `tests/plotting/test_isopleths.py` builds
families the same way in its own helper.

- [ ] **Step 2: Run the gate to verify it fails**

Run: `pixi run --frozen pytest tests/test_config_defaults.py -v`
Expected: FAIL — `ImportError: cannot import name 'CONFIG_DEFAULTS'`.

- [ ] **Step 3: Add the table to `_constants.py`**

Add `from collections.abc import Mapping` and `from types import MappingProxyType` to the
imports (`Final` is already imported). Append at the end of the module:

```python
#: Effective default for every ``tephpy.config`` option — what a user gets
#: when they set nothing (configfile spec §3.4).
#:
#: Read only by the configuration-file template generator. The plotting path
#: resolves its own defaults in ``IsoplethFamily._resolve``, and
#: ``tests/test_config_defaults.py`` gates the two against each other. Entries
#: name the conventions above rather than restating their values, so the gate
#: guards the structure — which option exists, and which convention it draws
#: on — rather than a second copy of every literal.
#:
#: A ``None`` records an option with **no** default: leaving ``interval`` and
#: ``values`` unset is what enables the zoom-adaptive selection ladder, so the
#: template must never print a number for them.
CONFIG_DEFAULTS: Final[Mapping[str, Mapping[str, object]]] = MappingProxyType(
    {
        "isotherms": MappingProxyType(
            {
                "color": ISOTHERM_COLOR,
                "linewidth": ISOPLETH_LINEWIDTH,
                "alpha": ISOPLETH_ALPHA,
                "labels": True,
                "visible": True,
                "emphasis": {},
                "values": None,
                "interval": None,
            }
        ),
        "isobars": MappingProxyType(
            {
                "color": ISOBAR_COLOR,
                "linewidth": ISOPLETH_LINEWIDTH,
                "alpha": ISOPLETH_ALPHA,
                "labels": True,
                "visible": True,
                "emphasis": {},
                "values": None,
                "interval": None,
            }
        ),
        "dry_adiabats": MappingProxyType(
            {
                "color": DRY_ADIABAT_COLOR,
                "linewidth": ISOPLETH_LINEWIDTH,
                "alpha": ISOPLETH_ALPHA,
                "labels": True,
                "visible": True,
                "emphasis": {},
                "values": None,
                "interval": None,
            }
        ),
        "moist_adiabats": MappingProxyType(
            {
                "color": MOIST_ADIABAT_COLOR,
                "linewidth": ISOPLETH_LINEWIDTH,
                "alpha": ISOPLETH_ALPHA,
                "labels": True,
                "visible": True,
                "emphasis": {},
                "values": None,
                "interval": None,
                "truncation": MOIST_ADIABAT_TRUNCATION,
            }
        ),
        "mixing_ratios": MappingProxyType(
            {
                "color": MIXING_RATIO_COLOR,
                "linewidth": ISOPLETH_LINEWIDTH,
                "alpha": ISOPLETH_ALPHA,
                "labels": True,
                "visible": True,
                "emphasis": {},
                "values": None,
            }
        ),
        "diagram": MappingProxyType({"extent": DEFAULT_EXTENT}),
        "cursor": MappingProxyType({"fields": CURSOR_FIELDS}),
    }
)
```

- [ ] **Step 4: Run the gate to verify it passes**

Run: `pixi run --frozen pytest tests/test_config_defaults.py -v`
Expected: PASS. If `emphasis` mismatches, the resolved value is `_NO_EMPHASIS`, a
`MappingProxyType({})`, which compares equal to `{}` — no change needed. If `labels`
mismatches, check `_normalize_labels`, which returns `(True, ())` for `None`; the gate
compares against `ResolvedOptions.labels`, the first element, not the derived
`label_edges`.

- [ ] **Step 5: Prove the gate bites**

Stage first: `git add src/tephpy/_constants.py tests/test_config_defaults.py`.

Change `"color": ISOTHERM_COLOR` to `"color": "chartreuse"`.
Run: `pixi run --frozen pytest tests/test_config_defaults.py -v`
Expected: exactly one failure —
`test_config_default_matches_the_resolved_default[isotherms-color]`.
Revert: `git checkout -- src/tephpy/_constants.py`.

Then delete the `"cursor"` entry entirely.
Expected: `test_config_defaults_covers_exactly_the_config_sections` FAILS — the membership
assertion is what stops a shrinking table from passing by checking less.
Revert: `git checkout -- src/tephpy/_constants.py`.

- [ ] **Step 6: Commit**

```bash
git commit -m "Record the effective configuration defaults behind a gate"
```

---

### Task 3: Declare the three runtime dependencies

Separate from the code that uses them, because this is the one task that re-solves the pixi
lock and the one whose failure mode is invisible to every check the repository runs:
`pyyaml` and `click` are already installed as transitives of `pre-commit`, `sphinx-autoapi`,
`towncrier` and `jupyter-cache`, so the code would import cleanly, `pixi run --frozen tests`
would pass, and CI would stay green while `pip install tephpy` failed at import
(configfile spec §7).

**Files:**
- Modify: `requirements/pypi-core.txt`
- Modify: `requirements/pypi-optional-docs.txt`
- Modify: `pyproject.toml` (`[tool.pixi.dependencies]`, `[tool.pixi.feature.docs.dependencies]`)
- Modify: `pixi.lock` (regenerated, never hand-edited)
- Create: `changelog/<PR>.dependency.rst`

- [ ] **Step 1: Add the runtime requirements**

`requirements/pypi-core.txt` gains three lines, in the file's existing alphabetical order:

```
click>=8.1
platformdirs>=4.0
pyyaml>=6.0
```

`requirements/pypi-optional-docs.txt` gains `sphinx-click>=6.0`, likewise in alphabetical
position.

- [ ] **Step 2: Mirror them into the pixi tables**

`[tool.pixi.dependencies]` gains, in the alphabetical order taplo enforces:

```toml
click = ">=8.1"
platformdirs = ">=4.0"
pyyaml = ">=6.0"
```

`[tool.pixi.feature.docs.dependencies]` gains `sphinx-click = ">=6.0"`.

- [ ] **Step 3: Re-solve the lock — the one place `--frozen` is dropped**

Run: `pixi install`
Then: `git diff --stat pixi.lock`
Expected: `pixi.lock` shows changes. Every later command in this plan returns to `--frozen`.

- [ ] **Step 4: Verify the declared floors actually resolve**

CI never tests the declared minimums — every environment is `--frozen` — so a floor is a
claim until someone resolves it once by hand. Do it now, in a throwaway environment outside
pixi:

```bash
python3 -m venv /tmp/tephpy-floors
/tmp/tephpy-floors/bin/pip install "click==8.1" "platformdirs==4.0" "pyyaml==6.0"
/tmp/tephpy-floors/bin/python -c "import click, platformdirs, yaml; print(click.__version__, platformdirs.__version__, yaml.__version__)"
rm -rf /tmp/tephpy-floors
```

Expected: all three install and import, printing their versions. Bare `python` is not on
PATH here — use `python3`. If any floor cannot be installed on Python 3.12+, raise it to the
lowest version that can, record the new number in `requirements/pypi-core.txt` and
`pyproject.toml`, and note it in the pull request so `configfile spec §7`'s table can be
corrected.

- [ ] **Step 5: Confirm the environment still works**

Run: `pixi run --frozen pytest tests/test_config.py tests/test_config_defaults.py -v`
Expected: PASS.

- [ ] **Step 6: Write the changelog fragment**

Find the fragment number with the `gh api` command in Global Constraints, then write
`changelog/<PR>.dependency.rst`:

```rst
Added ``click``, ``platformdirs`` and ``pyyaml`` to tephpy's core
dependencies, and ``sphinx-click`` to the documentation extras. The three
runtime additions carry the configuration file and the ``tephpy config``
command. (:user:`<github-username>`)
```

- [ ] **Step 7: Commit**

```bash
git add requirements/ pyproject.toml pixi.lock changelog/
git commit -m "Declare click, platformdirs and pyyaml as core dependencies"
```

---

### Task 4: Discovery cascade

**Files:**
- Create: `src/tephpy/_configfile.py`
- Create: `tests/test_configfile.py`

**Interfaces:**
- Consumes: `TephpyConfigError` from Task 1.
- Produces, all from `tephpy._configfile`:
  - `CONFIG_FILENAME: str` — `"tephpyrc.yaml"`
  - `CONFIG_ENV_VAR: str` — `"TEPHPYRC"`
  - `config_paths() -> tuple[Path, ...]` — the cascade in precedence order
  - `user_config_path() -> Path` — the platformdirs entry, which `generate` writes to
  - `discover() -> Path | None` — the first existing entry, or `None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_configfile.py` — BSD header, then:

```python
"""Discovery, parsing and coercion of the configuration file."""

from __future__ import annotations

import pytest

from tephpy import _configfile
from tephpy.exceptions import TephpyConfigError


def test_cascade_order_without_the_environment_variable(monkeypatch, tmp_path):
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    paths = _configfile.config_paths()
    assert len(paths) == 2
    assert paths[0] == tmp_path / _configfile.CONFIG_FILENAME
    assert paths[1] == _configfile.user_config_path()


def test_environment_variable_leads_the_cascade(monkeypatch, tmp_path):
    named = tmp_path / "elsewhere.yaml"
    monkeypatch.setenv(_configfile.CONFIG_ENV_VAR, str(named))
    paths = _configfile.config_paths()
    assert len(paths) == 3
    assert paths[0] == named


def test_discover_returns_none_when_nothing_exists(monkeypatch, tmp_path):
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        _configfile, "user_config_path", lambda: tmp_path / "absent" / "tephpyrc.yaml"
    )
    assert _configfile.discover() is None


def test_discover_stops_at_the_first_hit(monkeypatch, tmp_path):
    """First hit wins: a later entry must not override a visible one."""
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    later = tmp_path / "later" / "tephpyrc.yaml"
    later.parent.mkdir()
    later.write_text("isotherms: {}\n", encoding="utf-8")
    monkeypatch.setattr(_configfile, "user_config_path", lambda: later)
    here = tmp_path / _configfile.CONFIG_FILENAME
    here.write_text("isotherms: {}\n", encoding="utf-8")
    assert _configfile.discover() == here


def test_missing_environment_variable_target_is_an_error(monkeypatch, tmp_path):
    """Naming a file explicitly and not having it is a mistake, not a fallthrough."""
    monkeypatch.setenv(_configfile.CONFIG_ENV_VAR, str(tmp_path / "absent.yaml"))
    with pytest.raises(TephpyConfigError, match="TEPHPYRC"):
        _configfile.discover()


def test_a_directory_is_not_a_config_file(monkeypatch, tmp_path):
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / _configfile.CONFIG_FILENAME).mkdir()
    monkeypatch.setattr(
        _configfile, "user_config_path", lambda: tmp_path / "absent" / "tephpyrc.yaml"
    )
    assert _configfile.discover() is None
```

- [ ] **Step 2: Run to verify failure**

Run: `pixi run --frozen pytest tests/test_configfile.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tephpy._configfile'`.

- [ ] **Step 3: Write the module**

Create `src/tephpy/_configfile.py` with the BSD header and:

```python
"""Persistence for ``tephpy.config`` (configfile spec §3).

Discovery, parsing and rendering of the YAML configuration file. This module
owns everything about the file; ``_config`` owns only the shape of the
configuration and its lifecycle. Nothing here imports ``tephpy.plotting``, so
reading a configuration file cannot pull in matplotlib figure machinery.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

import platformdirs

from tephpy.exceptions import TephpyConfigError

__all__ = [
    "CONFIG_ENV_VAR",
    "CONFIG_FILENAME",
    "config_paths",
    "discover",
    "user_config_path",
]

#: The configuration file's name in the working directory and the user
#: configuration directory (configfile spec §3.2).
CONFIG_FILENAME: Final[str] = "tephpyrc.yaml"

#: The environment variable naming a configuration file outright.
CONFIG_ENV_VAR: Final[str] = "TEPHPYRC"


def user_config_path() -> Path:
    """The configuration file in the user's configuration directory.

    Returns
    -------
    pathlib.Path
        The platform's user configuration directory for tephpy, with the
        configuration file name appended. The directory need not exist.
    """
    return Path(platformdirs.user_config_dir("tephpy")) / CONFIG_FILENAME


def config_paths() -> tuple[Path, ...]:
    """The discovery cascade, in precedence order (configfile spec §3.2).

    Returns
    -------
    tuple of pathlib.Path
        ``$TEPHPYRC`` when set, then the working directory, then the user
        configuration directory. The entries need not exist.
    """
    paths: list[Path] = []
    named = os.environ.get(CONFIG_ENV_VAR)
    if named:
        paths.append(Path(named))
    paths.append(Path.cwd() / CONFIG_FILENAME)
    paths.append(user_config_path())
    return tuple(paths)


def discover() -> Path | None:
    """Find the configuration file in force.

    Returns
    -------
    pathlib.Path or None
        The first cascade entry that is a file, or ``None`` when there is
        none — running on the hardwired conventions is normal, not an error.

    Raises
    ------
    TephpyConfigError
        If ``$TEPHPYRC`` is set but does not name a file. Falling through
        would silently ignore an explicit instruction.
    """
    named = os.environ.get(CONFIG_ENV_VAR)
    if named and not Path(named).is_file():
        msg = (
            f"{CONFIG_ENV_VAR} names {named!r}, which is not a file; unset "
            f"{CONFIG_ENV_VAR} to fall back to the {CONFIG_FILENAME} search"
        )
        raise TephpyConfigError(msg)
    for path in config_paths():
        if path.is_file():
            return path
    return None
```

`user_config_path` is a module-level function rather than a constant so the tests can
monkeypatch it without touching the real user directory.

- [ ] **Step 4: Run to verify the tests pass**

Run: `pixi run --frozen pytest tests/test_configfile.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tephpy/_configfile.py tests/test_configfile.py
git commit -m "Find the configuration file by a first-hit-wins cascade"
```

---

### Task 5: Load, coerce, and validate

**Files:**
- Modify: `src/tephpy/_configfile.py`
- Modify: `src/tephpy/_config.py` (add `Config.load`)
- Modify: `tests/test_configfile.py`
- Create: `tests/fixtures/tephpyrc-complete.yaml`
- Create: `tests/test_configfile_fixture.py`

**Interfaces:**
- Consumes: `CONFIG_DEFAULTS` (Task 2), `discover` (Task 4), both exception names (Task 1).
- Produces:
  - `_configfile.read_document(path: Path) -> dict[str, object]` — parse to a mapping; an
    empty or wholly-commented file yields `{}`
  - `_configfile.coerce(section: str, option: str, value: object) -> object`
  - `_configfile.apply(config: Config, document: Mapping[str, object], source: Path | None) -> None`
  - `Config.load(path: str | Path | None = None) -> None`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_configfile.py`, adding `import tephpy` and
`from tephpy.exceptions import TephpyConfigWarning` to its imports:

```python
def _write(tmp_path, text):
    path = tmp_path / "tephpyrc.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_wholly_commented_file_is_an_empty_configuration(tmp_path):
    path = _write(tmp_path, "# isotherms:\n#   color: dimgrey\n")
    assert _configfile.read_document(path) == {}


def test_a_null_section_is_an_empty_section(tmp_path):
    """The expected state of every section the user has not touched."""
    path = _write(tmp_path, "isotherms:\ndiagram:\n")
    assert _configfile.read_document(path) == {"isotherms": None, "diagram": None}
    _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    assert tephpy.config.isotherms.color is None


def test_a_null_option_value_warns_and_names_the_quoting_trap(tmp_path):
    """``color: #b0b0b0`` parses as null — the hex is eaten as a comment."""
    path = _write(tmp_path, "isotherms:\n  color: #b0b0b0\n")
    document = _configfile.read_document(path)
    assert document == {"isotherms": {"color": None}}
    with pytest.warns(TephpyConfigWarning, match="quote"):
        _configfile.apply(tephpy.config, document, source=path)
    assert tephpy.config.isotherms.color is None


def test_an_unknown_option_warns_and_is_skipped(tmp_path):
    path = _write(tmp_path, "isotherms:\n  colour: purple\n  color: purple\n")
    with pytest.warns(TephpyConfigWarning, match="colour"):
        _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    assert tephpy.config.isotherms.color == "purple"


def test_an_unknown_section_raises(tmp_path):
    path = _write(tmp_path, "isotherm:\n  color: purple\n")
    with pytest.raises(TephpyConfigError, match="isotherm"):
        _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)


def test_a_non_mapping_section_raises(tmp_path):
    path = _write(tmp_path, "isotherms:\n  - purple\n")
    with pytest.raises(TephpyConfigError, match="mapping of options"):
        _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)


def test_malformed_yaml_raises(tmp_path):
    path = _write(tmp_path, "isotherms:\n  color: [unclosed\n")
    with pytest.raises(TephpyConfigError, match="not valid YAML"):
        _configfile.read_document(path)


def test_a_non_mapping_document_raises(tmp_path):
    path = _write(tmp_path, "- isotherms\n")
    with pytest.raises(TephpyConfigError, match="mapping of sections"):
        _configfile.read_document(path)


@pytest.mark.parametrize(
    ("text", "section", "option", "expected"),
    [
        (
            "isotherms:\n  labels: [bottom, right]\n",
            "isotherms",
            "labels",
            ("bottom", "right"),
        ),
        ("isotherms:\n  labels: bottom\n", "isotherms", "labels", "bottom"),
        ("isotherms:\n  values: [0, 10]\n", "isotherms", "values", (0.0, 10.0)),
        ("cursor:\n  fields: [pressure]\n", "cursor", "fields", ("pressure",)),
        (
            "diagram:\n  extent: [[1000, -30], [300, 30]]\n",
            "diagram",
            "extent",
            ((1000.0, -30.0), (300.0, 30.0)),
        ),
    ],
)
def test_sequences_coerce_to_tuples(tmp_path, text, section, option, expected):
    path = _write(tmp_path, text)
    _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    assert getattr(getattr(tephpy.config, section), option) == expected


def test_emphasis_keys_coerce_to_float(tmp_path):
    """``850`` and ``850.0`` must not be two different members."""
    path = _write(tmp_path, "isotherms:\n  emphasis:\n    0: {color: red}\n")
    _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    keys = list(tephpy.config.isotherms.emphasis)
    assert keys == [0.0]
    assert isinstance(keys[0], float)


def test_load_sets_the_source(tmp_path):
    path = _write(tmp_path, "isotherms:\n  color: purple\n")
    tephpy.config.load(path)
    assert tephpy.config.source == path
    assert tephpy.config.isotherms.color == "purple"
```

These rely on the autouse `_pristine_config` fixture Task 6 adds. Until then they mutate a
shared configuration, so run this file on its own in Step 5 and re-run the whole suite after
Task 6.

- [ ] **Step 2: Run to verify failure**

Run: `pixi run --frozen pytest tests/test_configfile.py -v`
Expected: FAIL — `AttributeError: module 'tephpy._configfile' has no attribute 'read_document'`.

- [ ] **Step 3: Implement parsing and application**

Set `_configfile.py`'s imports to:

```python
import dataclasses
import os
import warnings
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Final

import platformdirs
import yaml

from tephpy.exceptions import TephpyConfigError, TephpyConfigWarning

if TYPE_CHECKING:
    from tephpy._config import Config
```

Extend `__all__` with `"apply"`, `"coerce"` and `"read_document"`, keeping it sorted. Then
append:

```python
#: Options whose YAML sequence becomes a tuple of strings.
_STRING_TUPLES: Final[frozenset[str]] = frozenset({"labels", "fields"})

#: Options whose YAML sequence becomes a tuple of floats.
_FLOAT_TUPLES: Final[frozenset[str]] = frozenset({"values"})


def read_document(path: Path) -> dict[str, object]:
    """Parse a configuration file into a mapping of sections.

    Parameters
    ----------
    path : pathlib.Path
        The file to read.

    Returns
    -------
    dict
        The document's top-level mapping. A file that is empty or wholly
        commented out yields ``{}`` — that is how a freshly generated
        template reads, and it is an empty configuration, not an error
        (configfile spec §5).

    Raises
    ------
    TephpyConfigError
        If the file cannot be read, is not valid YAML, or holds anything
        other than a mapping at the top level.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"{path}: cannot read the configuration file: {exc}"
        raise TephpyConfigError(msg) from exc
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        msg = f"{path}: not valid YAML: {exc}"
        raise TephpyConfigError(msg) from exc
    if document is None:
        return {}
    if not isinstance(document, Mapping):
        msg = (
            f"{path}: a configuration file must hold a mapping of sections, "
            f"not {type(document).__name__}"
        )
        raise TephpyConfigError(msg)
    return dict(document)


def coerce(section: str, option: str, value: object) -> object:
    """Convert a parsed YAML value to what the configuration expects.

    Parameters
    ----------
    section : str
        The configuration section the option belongs to.
    option : str
        The option name.
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    object
        The value in the type ``tephpy.config`` holds
        (configfile spec §3.3).

    Raises
    ------
    TephpyConfigError
        If the value's shape cannot be converted.
    """
    try:
        if option == "extent":
            return tuple(tuple(float(number) for number in corner) for corner in value)
        if option == "emphasis":
            return {float(member): dict(style) for member, style in value.items()}
        if option in _FLOAT_TUPLES and isinstance(value, list):
            return tuple(float(number) for number in value)
        if option in _STRING_TUPLES and isinstance(value, list):
            return tuple(str(entry) for entry in value)
    except (AttributeError, TypeError, ValueError) as exc:
        msg = f"{section}.{option}: cannot make sense of {value!r}: {exc}"
        raise TephpyConfigError(msg) from exc
    return value


def apply(config: Config, document: Mapping[str, object], source: Path | None) -> None:
    """Apply a parsed configuration document to a configuration.

    Parameters
    ----------
    config : Config
        The configuration to write into, in place.
    document : mapping
        The parsed document, as :func:`read_document` returns it.
    source : pathlib.Path or None
        The file the document came from, recorded as ``config.source``.

    Raises
    ------
    TephpyConfigError
        If a section is unknown or is not a mapping.

    Warns
    -----
    TephpyConfigWarning
        If an option is unknown, or its value is an explicit null.
    """
    sections = {field.name for field in dataclasses.fields(config)}
    for name, options in document.items():
        if name not in sections:
            msg = (
                f"unknown configuration section {name!r}; expected one of "
                f"{sorted(sections)}"
            )
            raise TephpyConfigError(msg)
        if options is None:
            # Every option commented out: the untouched state of a section
            # in a generated template (configfile spec §5).
            continue
        if not isinstance(options, Mapping):
            msg = (
                f"configuration section {name!r} must hold a mapping of "
                f"options, not {type(options).__name__}"
            )
            raise TephpyConfigError(msg)
        section = getattr(config, name)
        valid = {field.name for field in dataclasses.fields(section)}
        for option, value in options.items():
            if option not in valid:
                warnings.warn(
                    f"ignoring unknown option {option!r} in configuration "
                    f"section {name!r}; expected one of {sorted(valid)}",
                    TephpyConfigWarning,
                    stacklevel=2,
                )
                continue
            if value is None:
                warnings.warn(
                    f"ignoring {name}.{option}, whose value is null; an "
                    f"unquoted '#' colour is read as a comment, so quote it "
                    f"as '#b0b0b0' if that is what happened",
                    TephpyConfigWarning,
                    stacklevel=2,
                )
                continue
            setattr(section, option, coerce(name, option, value))
    config._source = source
```

- [ ] **Step 4: Add `Config.load`**

In `_config.py`, move `from pathlib import Path` out of the `TYPE_CHECKING` block to
module level — `load` and `save` call `Path(...)` at runtime, so the Task 1 import is not
enough. Then, after `reset`:

```python
    def load(self, path: str | Path | None = None) -> None:
        """Load a configuration file over this configuration.

        Parameters
        ----------
        path : str or pathlib.Path, optional
            The file to read. When omitted, the discovery cascade selects
            it, and nothing happens if the cascade finds no file.

        Raises
        ------
        TephpyConfigError
            If the file cannot be read, is not valid YAML, or names an
            unknown configuration section. An unknown *option* warns and is
            skipped instead (configfile spec §2).

        Warns
        -----
        TephpyConfigWarning
            If an option is unknown, or its value is an explicit null.
        """
        from tephpy import _configfile

        chosen = _configfile.discover() if path is None else Path(path)
        if chosen is None:
            return
        _configfile.apply(self, _configfile.read_document(chosen), source=chosen)
```

The `_configfile` import is function-local and deliberate: `_configfile` imports `Config`
for typing, so a module-level import here would be circular.

- [ ] **Step 5: Run to verify the tests pass**

Run: `pixi run --frozen pytest tests/test_configfile.py -v`
Expected: PASS.

- [ ] **Step 6: Write the complete fixture**

Create `tests/fixtures/tephpyrc-complete.yaml`. Every option of every section, each set to
a value that differs from its default — a fixture equal to the defaults would load
identically to loading nothing, and would pass whether or not the loader ran
(configfile spec §6):

```yaml
# Every option, every value deliberately non-default (configfile spec §6).
isotherms:
  color: purple
  linewidth: 1.25
  alpha: 0.75
  labels: [bottom, right]
  visible: false
  emphasis:
    0.0: {color: tab:cyan, linewidth: 2.0}
  values: [-20.0, 0.0, 20.0]
  interval: 5.0
isobars:
  color: crimson
  linewidth: 1.5
  alpha: 0.8
  labels: left
  visible: false
  emphasis:
    850.0: {}
  values: [1000.0, 850.0, 500.0]
  interval: 25.0
dry_adiabats:
  color: seagreen
  linewidth: 0.75
  alpha: 0.6
  labels: false
  visible: false
  emphasis:
    30.0: {alpha: 0.9}
  values: [10.0, 30.0]
  interval: 15.0
moist_adiabats:
  color: goldenrod
  linewidth: 0.9
  alpha: 0.55
  labels: top
  visible: false
  emphasis:
    20.0: {linestyle: dashed}
  values: [0.0, 20.0]
  interval: 8.0
  truncation: -30.0
mixing_ratios:
  color: slateblue
  linewidth: 1.1
  alpha: 0.65
  labels: [right]
  visible: false
  emphasis:
    4.0: {color: black}
  values: [1.0, 4.0, 16.0]
diagram:
  extent: [[1000.0, -30.0], [300.0, 30.0]]
cursor:
  fields: [pressure]
```

- [ ] **Step 7: Write the fixture's completeness gate**

Create `tests/test_configfile_fixture.py` — BSD header, then:

```python
"""Prove every configuration option survives the YAML round trip.

A representative fixture would let a newly added option with a type YAML
cannot express land unnoticed, so this one is complete: the gate below fails
until the fixture covers every option in ``CONFIG_DEFAULTS`` (configfile
spec §6).
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

import tephpy
from tephpy import _configfile
from tephpy._constants import CONFIG_DEFAULTS

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "tephpyrc-complete.yaml"


def _document():
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def test_the_fixture_covers_every_section():
    assert set(_document()) == set(CONFIG_DEFAULTS)


@pytest.mark.parametrize("section", sorted(CONFIG_DEFAULTS))
def test_the_fixture_covers_every_option(section):
    assert set(_document()[section]) == set(CONFIG_DEFAULTS[section])


@pytest.mark.parametrize("section", sorted(CONFIG_DEFAULTS))
def test_no_fixture_value_coincides_with_its_default(section):
    """A fixture equal to the defaults would pass without the loader running."""
    loaded = _document()[section]
    for option, default in CONFIG_DEFAULTS[section].items():
        coerced = _configfile.coerce(section, option, loaded[option])
        assert coerced != default, f"{section}.{option}"


def test_loading_the_fixture_reaches_every_option():
    tephpy.config.load(FIXTURE)
    document = _document()
    for section, options in CONFIG_DEFAULTS.items():
        applied = getattr(tephpy.config, section)
        for option in options:
            expected = _configfile.coerce(section, option, document[section][option])
            assert getattr(applied, option) == expected, f"{section}.{option}"
```

The last two tests divide the work deliberately. The third proves each fixture value differs
from its default; the fourth proves loading reaches every option. Neither alone would catch
an `apply` that skipped a section — the pair does. `coerce` itself is proved by the inline
cases in `tests/test_configfile.py`, not here.

`visible: false` is a legitimate non-default that is also falsey, which is why the last test
compares values rather than testing truthiness.

- [ ] **Step 8: Run the fixture gate**

Run: `pixi run --frozen pytest tests/test_configfile_fixture.py -v`
Expected: PASS. A `KeyError` from `loaded[option]` means the fixture left an option out
entirely; a plain assertion failure means a fixture value coincides with its default.

- [ ] **Step 9: Prove the completeness gate bites**

Stage first: `git add src/tephpy tests/`.

Delete the `truncation: -30.0` line from the fixture.
Run: `pixi run --frozen pytest tests/test_configfile_fixture.py -v`
Expected: `test_the_fixture_covers_every_option[moist_adiabats]` FAILS.
Revert: `git checkout -- tests/fixtures/tephpyrc-complete.yaml`.

Then change `mixing_ratios.color` in the fixture to `tab:green`, its default.
Expected: `test_no_fixture_value_coincides_with_its_default[mixing_ratios]` FAILS.
Revert: `git checkout -- tests/fixtures/tephpyrc-complete.yaml`.

- [ ] **Step 10: Commit**

```bash
git commit -m "Load a configuration file, coercing YAML to the config types"
```

---

### Task 6: Auto-load at import, and test isolation

These land together in one commit. The auto-load is what makes a developer's own
configuration file leak into the test suite, so shipping it without the conftest hook would
leave the suite non-hermetic between two commits — and with `filterwarnings = ["error"]`, a
single unknown key in a developer's file would turn into a collection error
(configfile spec §6).

**Files:**
- Modify: `src/tephpy/__init__.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_config_autoload.py`

**Interfaces:**
- Consumes: `Config.load`, `Config.reset` (Tasks 1 and 5).
- Produces: the import-time side effect, and an autouse `_pristine_config` fixture that
  every other test file in this plan relies on.

- [ ] **Step 1: Write the failing subprocess test**

Create `tests/test_config_autoload.py` — BSD header, then:

```python
"""Prove the import-time auto-load actually runs.

``tephpy`` is already imported by the time any in-process test runs, so this
seam is invisible from inside the suite and has to be exercised in a fresh
interpreter (configfile spec §6).
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import matplotlib as mpl

PROBE = textwrap.dedent(
    """
    import tephpy

    print(tephpy.config.isotherms.color)
    print(tephpy.config.source)
    """
)


def _run(tmp_path, **env_extra):
    """Import tephpy in a fresh interpreter under a controlled environment.

    ``HOME`` and ``XDG_CONFIG_HOME`` both move, so the user configuration
    directory is empty on every platform, not just the linux-64 CI runs.
    ``MPLCONFIGDIR`` keeps pointing at this process's matplotlib cache, so
    the relocated ``HOME`` does not trigger a font-cache rebuild.
    """
    env = dict(os.environ)
    env.pop("TEPHPYRC", None)
    env["HOME"] = str(tmp_path)
    env["XDG_CONFIG_HOME"] = str(tmp_path / "config")
    env["MPLCONFIGDIR"] = mpl.get_configdir()
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c", PROBE],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
        env=env,
    )


def test_autoload_applies_the_named_file(tmp_path):
    named = tmp_path / "named.yaml"
    named.write_text("isotherms:\n  color: purple\n", encoding="utf-8")
    result = _run(tmp_path, TEPHPYRC=str(named))
    colour, source = result.stdout.split()
    assert colour == "purple"
    assert source == str(named)


def test_autoload_finds_the_working_directory_file(tmp_path):
    (tmp_path / "tephpyrc.yaml").write_text(
        "isotherms:\n  color: purple\n", encoding="utf-8"
    )
    result = _run(tmp_path)
    colour, _ = result.stdout.split()
    assert colour == "purple"


def test_autoload_finds_nothing_without_a_file(tmp_path):
    result = _run(tmp_path)
    colour, source = result.stdout.split()
    assert colour == "None"
    assert source == "None"


def test_a_broken_file_warns_and_does_not_stop_the_import(tmp_path):
    """``check=True`` is the assertion: a raising import would exit non-zero."""
    broken = tmp_path / "broken.yaml"
    broken.write_text("isotherms:\n  color: [unclosed\n", encoding="utf-8")
    result = _run(tmp_path, TEPHPYRC=str(broken))
    assert "TephpyConfigWarning" in result.stderr
    colour, source = result.stdout.split()
    assert colour == "None"
    assert source == "None"
```

- [ ] **Step 2: Run to verify failure**

Run: `pixi run --frozen pytest tests/test_config_autoload.py -v`
Expected: FAIL — the probe prints `None` for a file that should have applied.

- [ ] **Step 3: Add the auto-load hook**

In `src/tephpy/__init__.py`, after the `__all__` block:

```python
def _autoload_config() -> None:
    """Apply the discovered configuration file, if there is one.

    A configuration file that cannot be read must not stop the import: that
    would also take out ``tephpy config path``, which is the tool for
    finding out which file is at fault. Any failure therefore warns and
    leaves the configuration pristine (configfile spec §5).
    """
    import warnings

    try:
        config.load()
    except exceptions.TephpyConfigError as exc:
        config.reset()
        warnings.warn(
            f"ignoring the configuration file: {exc}",
            exceptions.TephpyConfigWarning,
            stacklevel=2,
        )


_autoload_config()
```

`exceptions` is already imported at module level; `warnings` stays function-local so it does
not become a `tephpy.warnings` attribute. Leave `_autoload_config` out of `__all__`.

- [ ] **Step 4: Make the test suite hermetic**

Replace `tests/conftest.py` with:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Pytest configuration: non-interactive backend, pristine configuration.

``tephpy`` auto-loads a configuration file at import, so a developer with
their own ``tephpyrc.yaml`` would otherwise feed it into every image
comparison — and with ``filterwarnings = ["error"]`` a single unknown key in
it would become a collection error. Importing inside ``catch_warnings`` and
resetting immediately removes both, without depending on when pytest
installs its own filters (configfile spec §6).
"""

from __future__ import annotations

import warnings

import matplotlib as mpl
import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import tephpy

tephpy.config.reset()

mpl.use("Agg")


@pytest.fixture(autouse=True)
def _pristine_config():
    """Reset ``tephpy.config`` around every test.

    Yields
    ------
    None
        Control, with the configuration pristine.
    """
    tephpy.config.reset()
    yield
    tephpy.config.reset()
```

- [ ] **Step 5: Run the whole suite**

Run: `pixi run --frozen tests`
Expected: PASS, image baselines included. A baseline failure here means a section is being
rebound rather than cleared — re-check `Config.reset` against Task 1, Step 6.

- [ ] **Step 6: Prove the isolation is not vacuous**

Stage first: `git add src/tephpy tests/`. Then create a configuration file the suite would
otherwise pick up, and confirm it does not:

```bash
mkdir -p /tmp/tephpy-leak
printf 'isotherms:\n  color: chartreuse\n' > /tmp/tephpy-leak/tephpyrc.yaml
TEPHPYRC=/tmp/tephpy-leak/tephpyrc.yaml pixi run --frozen tests
```

Expected: PASS — identical to the run without the variable.

Now comment out the module-scope `tephpy.config.reset()` in `tests/conftest.py` and run the
same command.
Expected: image comparisons FAIL, because the isotherms are chartreuse.
Revert with `git checkout -- tests/conftest.py`, then `rm -rf /tmp/tephpy-leak`.

- [ ] **Step 7: Commit**

```bash
git commit -m "Auto-load the configuration file, and keep it out of the tests"
```

---

### Task 7: Render the template, and save

**Files:**
- Modify: `src/tephpy/_configfile.py`
- Modify: `src/tephpy/_config.py` (add `Config.save`)
- Create: `tests/test_configfile_template.py`

**Interfaces:**
- Consumes: `CONFIG_DEFAULTS` (Task 2), `read_document`/`apply` (Task 5).
- Produces:
  - `_configfile.CONFIG_DESCRIPTIONS: Mapping[str, Mapping[str, str]]`
  - `_configfile.render_template() -> str`
  - `_configfile.write_template(path: Path, *, force: bool = False) -> None`
  - `_configfile.write_config(config: Config, path: Path) -> None`
  - `Config.save(path: str | Path | None = None) -> Path`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_configfile_template.py` — BSD header, then:

```python
"""Template rendering and the values-only save."""

from __future__ import annotations

import dataclasses

import pytest
import yaml

import tephpy
from tephpy import _configfile
from tephpy._config import Config
from tephpy._constants import CONFIG_DEFAULTS
from tephpy.exceptions import TephpyConfigError


def _description_cases():
    return [
        (section, option)
        for section in CONFIG_DEFAULTS
        for option in CONFIG_DEFAULTS[section]
    ]


def test_the_description_gate_covers_every_option():
    """A gate over an empty list passes by checking nothing.

    Forty-two, the option count of configfile spec §3.3.
    """
    assert len(_description_cases()) == 42


def test_descriptions_cover_exactly_the_config_sections():
    assert set(_configfile.CONFIG_DESCRIPTIONS) == set(CONFIG_DEFAULTS)


@pytest.mark.parametrize("section", sorted(CONFIG_DEFAULTS))
def test_descriptions_cover_exactly_each_section_option(section):
    assert set(_configfile.CONFIG_DESCRIPTIONS[section]) == set(
        CONFIG_DEFAULTS[section]
    )


@pytest.mark.parametrize(("section", "option"), _description_cases())
def test_every_description_is_prose(section, option):
    description = _configfile.CONFIG_DESCRIPTIONS[section][option]
    assert isinstance(description, str)
    assert description.strip()


def test_the_template_is_an_empty_configuration_as_generated():
    """Every option commented out, so an untouched template changes nothing."""
    document = yaml.safe_load(_configfile.render_template())
    assert set(document) == set(CONFIG_DEFAULTS)
    assert all(value is None for value in document.values())


def test_the_template_names_every_option_in_a_comment():
    text = _configfile.render_template()
    for section, options in CONFIG_DEFAULTS.items():
        assert f"\n{section}:" in text
        for option in options:
            assert f"# {option}:" in text, f"{section}.{option}"


def test_the_template_prints_no_number_for_the_ladder_options():
    """``interval`` and ``values`` have no default; a number would disable the ladder."""
    for line in _configfile.render_template().splitlines():
        stripped = line.strip()
        if stripped.startswith(("# interval:", "# values:")):
            assert stripped in {"# interval:", "# values:"}, line


def test_an_untouched_template_loads_as_no_configuration(tmp_path):
    path = tmp_path / "tephpyrc.yaml"
    _configfile.write_template(path)
    tephpy.config.load(path)
    for field in dataclasses.fields(Config):
        section = getattr(tephpy.config, field.name)
        for option in dataclasses.fields(section):
            assert getattr(section, option.name) is None, f"{field.name}.{option.name}"


def test_write_template_refuses_to_clobber(tmp_path):
    path = tmp_path / "tephpyrc.yaml"
    path.write_text("isotherms: {}\n", encoding="utf-8")
    with pytest.raises(TephpyConfigError, match="--force"):
        _configfile.write_template(path)
    assert path.read_text(encoding="utf-8") == "isotherms: {}\n"


def test_write_template_overwrites_with_force(tmp_path):
    path = tmp_path / "tephpyrc.yaml"
    path.write_text("isotherms: {}\n", encoding="utf-8")
    _configfile.write_template(path, force=True)
    assert "# color:" in path.read_text(encoding="utf-8")


def test_save_writes_only_what_was_set(tmp_path):
    path = tmp_path / "saved.yaml"
    tephpy.config.isotherms.color = "purple"
    tephpy.config.save(path)
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == {
        "isotherms": {"color": "purple"}
    }


def test_save_round_trips_the_tuple_valued_options(tmp_path):
    """PyYAML has no tuple representer; extent nests them two deep."""
    path = tmp_path / "saved.yaml"
    tephpy.config.cursor.fields = ("pressure",)
    tephpy.config.diagram.extent = ((1000.0, -30.0), (300.0, 30.0))
    tephpy.config.save(path)
    tephpy.config.reset()
    tephpy.config.load(path)
    assert tephpy.config.cursor.fields == ("pressure",)
    assert tephpy.config.diagram.extent == ((1000.0, -30.0), (300.0, 30.0))


def test_save_returns_the_path_written(tmp_path):
    path = tmp_path / "saved.yaml"
    assert tephpy.config.save(path) == path
```

- [ ] **Step 2: Run to verify failure**

Run: `pixi run --frozen pytest tests/test_configfile_template.py -v`
Expected: FAIL — `AttributeError: module 'tephpy._configfile' has no attribute 'CONFIG_DESCRIPTIONS'`.

- [ ] **Step 3: Add the description table**

The `#:` comments in `_config.py` are consumed by the documentation build and are invisible
at runtime, so the template's prose lives here (configfile spec §3.4). Add
`from types import MappingProxyType` to `_configfile.py`'s imports, add
`"CONFIG_DESCRIPTIONS"` to `__all__`, and append:

```python
#: One line of prose per option, rendered above it in the generated template
#: (configfile spec §3.4). Gated for completeness against ``CONFIG_DEFAULTS``
#: by ``tests/test_configfile_template.py``.
#:
#: The units differ per family — hPa for isobars, degrees Celsius for the
#: temperature families, g/kg for mixing ratios — so each family spells out
#: its own rather than sharing one string that would be wrong for four of
#: the five.
CONFIG_DESCRIPTIONS: Final[Mapping[str, Mapping[str, str]]] = MappingProxyType(
    {
        "isotherms": MappingProxyType(
            {
                "color": "Matplotlib colour for the lines and their labels.",
                "linewidth": "Line width in points.",
                "alpha": "Line and label opacity, 0 to 1.",
                "labels": (
                    "true, false, or the diagram edges to label - bottom, top, "
                    "left, right - singly or as a list."
                ),
                "visible": "Whether the family is drawn at all.",
                "emphasis": (
                    "Members drawn with a distinguishing style, keyed by "
                    "temperature in degrees Celsius."
                ),
                "values": (
                    "Explicit member temperatures in degrees Celsius. Unset, the "
                    "zoom-adaptive ladder selects them."
                ),
                "interval": (
                    "Member spacing in degrees Celsius. Unset, the zoom-adaptive "
                    "ladder selects it."
                ),
            }
        ),
        "isobars": MappingProxyType(
            {
                "color": "Matplotlib colour for the lines and their labels.",
                "linewidth": "Line width in points.",
                "alpha": "Line and label opacity, 0 to 1.",
                "labels": (
                    "true, false, or the diagram edges to label - bottom, top, "
                    "left, right - singly or as a list."
                ),
                "visible": "Whether the family is drawn at all.",
                "emphasis": (
                    "Members drawn with a distinguishing style, keyed by pressure "
                    "in hPa."
                ),
                "values": (
                    "Explicit member pressures in hPa. Unset, the zoom-adaptive "
                    "ladder selects them."
                ),
                "interval": (
                    "Member spacing in hPa. Unset, the zoom-adaptive ladder selects it."
                ),
            }
        ),
        "dry_adiabats": MappingProxyType(
            {
                "color": "Matplotlib colour for the lines and their labels.",
                "linewidth": "Line width in points.",
                "alpha": "Line and label opacity, 0 to 1.",
                "labels": (
                    "true, false, or the diagram edges to label - bottom, top, "
                    "left, right - singly or as a list."
                ),
                "visible": "Whether the family is drawn at all.",
                "emphasis": (
                    "Members drawn with a distinguishing style, keyed by potential "
                    "temperature in degrees Celsius."
                ),
                "values": (
                    "Explicit member potential temperatures in degrees Celsius. "
                    "Unset, the zoom-adaptive ladder selects them."
                ),
                "interval": (
                    "Member spacing in degrees Celsius. Unset, the zoom-adaptive "
                    "ladder selects it."
                ),
            }
        ),
        "moist_adiabats": MappingProxyType(
            {
                "color": "Matplotlib colour for the lines and their labels.",
                "linewidth": "Line width in points.",
                "alpha": "Line and label opacity, 0 to 1.",
                "labels": (
                    "true, false, or the diagram edges to label - bottom, top, "
                    "left, right - singly or as a list."
                ),
                "visible": "Whether the family is drawn at all.",
                "emphasis": (
                    "Members drawn with a distinguishing style, keyed by wet-bulb "
                    "potential temperature in degrees Celsius."
                ),
                "values": (
                    "Explicit member wet-bulb potential temperatures in degrees "
                    "Celsius. Unset, the zoom-adaptive ladder selects them."
                ),
                "interval": (
                    "Member spacing in degrees Celsius. Unset, the zoom-adaptive "
                    "ladder selects it."
                ),
                "truncation": (
                    "Temperature in degrees Celsius below which a moist adiabat "
                    "stops being drawn."
                ),
            }
        ),
        "mixing_ratios": MappingProxyType(
            {
                "color": "Matplotlib colour for the lines and their labels.",
                "linewidth": "Line width in points.",
                "alpha": "Line and label opacity, 0 to 1.",
                "labels": (
                    "true, false, or the diagram edges to label - bottom, top, "
                    "left, right - singly or as a list."
                ),
                "visible": "Whether the family is drawn at all.",
                "emphasis": (
                    "Members drawn with a distinguishing style, keyed by mixing "
                    "ratio in g/kg."
                ),
                "values": (
                    "Explicit member mixing ratios in g/kg. Unset, the "
                    "zoom-adaptive ladder selects them."
                ),
            }
        ),
        "diagram": MappingProxyType(
            {
                "extent": (
                    "Default view corners as [[pressure, temperature], [pressure, "
                    "temperature]], in hPa and degrees Celsius."
                ),
            }
        ),
        "cursor": MappingProxyType(
            {
                "fields": "Cursor readout fields, in display order.",
            }
        ),
    }
)
```

- [ ] **Step 4: Render and write the template**

Append to `_configfile.py`, and extend `__all__` with `"render_template"`, `"write_config"`
and `"write_template"`:

```python
def _as_sequences(value: object) -> object:
    """Recursively replace tuples with lists, for ``yaml.safe_dump``.

    Parameters
    ----------
    value : object
        A configuration value, possibly holding nested tuples.

    Returns
    -------
    object
        The same value with every tuple, at every depth, replaced by a
        list. PyYAML's safe dumper has no tuple representer, and ``extent``
        nests them two deep.
    """
    if isinstance(value, tuple | list):
        return [_as_sequences(entry) for entry in value]
    if isinstance(value, Mapping):
        return {key: _as_sequences(entry) for key, entry in value.items()}
    return value


def _format_default(value: object) -> str:
    """Render a default as the YAML a user can uncomment.

    Parameters
    ----------
    value : object
        The default from ``CONFIG_DEFAULTS``.

    Returns
    -------
    str
        The value in YAML flow style, or the empty string for an option
        with no default and for an empty ``emphasis`` mapping.
    """
    if value is None or value == {}:
        return ""
    rendered = yaml.safe_dump(_as_sequences(value), default_flow_style=True).strip()
    # A scalar document is dumped with an explicit "..." end marker.
    if rendered.endswith("..."):
        rendered = rendered[: -len("...")].strip()
    return rendered


def _write(path: Path, text: str) -> None:
    """Write text to a file, creating its parent directory.

    Parameters
    ----------
    path : pathlib.Path
        The file to write.
    text : str
        The content.

    Raises
    ------
    TephpyConfigError
        If the file cannot be written.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        msg = f"{path}: cannot write the configuration file: {exc}"
        raise TephpyConfigError(msg) from exc


def render_template() -> str:
    """Render the fully-commented configuration template.

    Returns
    -------
    str
        A YAML document whose section headers are live and whose every
        option is commented out, so an untouched template parses to an
        empty configuration (configfile spec §5).
    """
    lines = [
        "# tephpy configuration file.",
        "#",
        "# Every option below is commented out and shows the default in force.",
        "# Uncomment a line and edit it to change that option; leave the rest",
        "# alone. Quote any colour written as a hex triplet - an unquoted",
        "# '#b0b0b0' is read as a comment, not a colour.",
        "#",
        "# Discovery, first match wins: $TEPHPYRC, then ./tephpyrc.yaml, then",
        "# this file's own directory. 'tephpy config path' reports the search.",
    ]
    for section, options in CONFIG_DEFAULTS.items():
        lines.append("")
        lines.append(f"{section}:")
        for option, default in options.items():
            lines.append(f"  # {CONFIG_DESCRIPTIONS[section][option]}")
            lines.append(f"  # {option}: {_format_default(default)}".rstrip())
    return "\n".join(lines) + "\n"


def write_template(path: Path, *, force: bool = False) -> None:
    """Write the configuration template.

    Parameters
    ----------
    path : pathlib.Path
        The file to write. Its parent directory is created if absent.
    force : bool, optional
        Overwrite an existing file. Default is ``False``.

    Raises
    ------
    TephpyConfigError
        If the file exists and `force` is false, or it cannot be written.
    """
    if path.exists() and not force:
        msg = f"{path} already exists; pass --force to overwrite it"
        raise TephpyConfigError(msg)
    _write(path, render_template())


def write_config(config: Config, path: Path) -> None:
    """Write a configuration's set options to a file.

    Parameters
    ----------
    config : Config
        The configuration to serialise.
    path : pathlib.Path
        The file to write. Its parent directory is created if absent.

    Raises
    ------
    TephpyConfigError
        If the file cannot be written.
    """
    document: dict[str, object] = {}
    for field in dataclasses.fields(config):
        section = getattr(config, field.name)
        options = {
            option.name: _as_sequences(getattr(section, option.name))
            for option in dataclasses.fields(section)
            if getattr(section, option.name) is not None
        }
        if options:
            document[field.name] = options
    _write(path, yaml.safe_dump(document, default_flow_style=False, sort_keys=False))
```

Add `CONFIG_DEFAULTS` to the `from tephpy._constants import …` line — Task 4's module does
not import it yet.

`f"  # {option}: {''}".rstrip()` collapses to `  # interval:`, which is what the ladder test
asserts — no number, ever.

- [ ] **Step 5: Add `Config.save`**

In `_config.py`, after `load`:

```python
    def save(self, path: str | Path | None = None) -> Path:
        """Write the options set on this configuration to a file.

        Only options that were actually set are written; everything still
        falling through to the conventions is left out. Comments and key
        order in an existing file are **not** preserved — use
        ``tephpy config generate`` for the commented template
        (configfile spec §3.5).

        Parameters
        ----------
        path : str or pathlib.Path, optional
            Where to write. Defaults to the file in the user's
            configuration directory.

        Returns
        -------
        pathlib.Path
            The file written.

        Raises
        ------
        TephpyConfigError
            If the file cannot be written.
        """
        from tephpy import _configfile

        chosen = _configfile.user_config_path() if path is None else Path(path)
        _configfile.write_config(self, chosen)
        return chosen
```

- [ ] **Step 6: Run to verify the tests pass**

Run: `pixi run --frozen pytest tests/test_configfile_template.py -v`
Expected: PASS.

- [ ] **Step 7: Prove the description gate bites**

Stage first: `git add src/tephpy tests/`.

Delete the `"visible"` entry from `CONFIG_DESCRIPTIONS["isotherms"]`.
Run: `pixi run --frozen pytest tests/test_configfile_template.py -v`
Expected: `test_descriptions_cover_exactly_each_section_option[isotherms]` FAILS.
Revert: `git checkout -- src/tephpy/_configfile.py`.

Then change `CONFIG_DEFAULTS["isotherms"]["interval"]` in `_constants.py` from `None` to
`10.0`.
Expected: `test_the_template_prints_no_number_for_the_ladder_options` FAILS, along with the
Task 2 defaults gate.
Revert: `git checkout -- src/tephpy/_constants.py`.

- [ ] **Step 8: Commit**

```bash
git commit -m "Generate the commented template, and save what was set"
```

---

### Task 8: The `tephpy config` command

**Files:**
- Create: `src/tephpy/_cli.py`
- Modify: `pyproject.toml` (`[project.scripts]`)
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `config_paths`, `discover`, `render_template`, `user_config_path`,
  `write_template` from `_configfile`.
- Produces: console script `tephpy` → `tephpy._cli:main`; the click group `main` and its
  `config` subgroup, which `sphinx-click` documents in Task 9.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli.py` — BSD header, then:

```python
"""The tephpy console script (configfile spec §4)."""

from __future__ import annotations

import pytest
import yaml
from click.testing import CliRunner

from tephpy import _cli, _configfile


@pytest.fixture
def runner():
    return CliRunner()


def test_bare_config_reports_the_path(runner, monkeypatch, tmp_path):
    """``tephpy config`` defaults to ``path``, which can never write a file."""
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(_cli.main, ["config"])
    assert result.exit_code == 0
    assert "tephpyrc.yaml" in result.output


def test_path_reports_every_cascade_entry(runner, monkeypatch, tmp_path):
    """A user reaching for this is asking why their file is ignored."""
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 0
    assert result.output.count("tephpyrc.yaml") >= 2


def test_path_marks_the_active_file(runner, monkeypatch, tmp_path):
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tephpyrc.yaml").write_text("isotherms: {}\n", encoding="utf-8")
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 0
    assert "in force" in result.output


def test_path_reports_a_broken_environment_variable(runner, monkeypatch, tmp_path):
    monkeypatch.setenv(_configfile.CONFIG_ENV_VAR, str(tmp_path / "absent.yaml"))
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 1
    assert "TEPHPYRC" in result.output


def test_generate_writes_a_template(runner, tmp_path):
    target = tmp_path / "generated.yaml"
    result = runner.invoke(_cli.main, ["config", "generate", "-o", str(target)])
    assert result.exit_code == 0
    assert set(yaml.safe_load(target.read_text(encoding="utf-8"))) == {
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
        "diagram",
        "cursor",
    }


def test_generate_refuses_to_clobber(runner, tmp_path):
    target = tmp_path / "generated.yaml"
    target.write_text("isotherms: {}\n", encoding="utf-8")
    result = runner.invoke(_cli.main, ["config", "generate", "-o", str(target)])
    assert result.exit_code == 1
    assert "--force" in result.output
    assert target.read_text(encoding="utf-8") == "isotherms: {}\n"


def test_generate_force_overwrites(runner, tmp_path):
    target = tmp_path / "generated.yaml"
    target.write_text("isotherms: {}\n", encoding="utf-8")
    result = runner.invoke(
        _cli.main, ["config", "generate", "-o", str(target), "--force"]
    )
    assert result.exit_code == 0
    assert "# color:" in target.read_text(encoding="utf-8")


def test_generate_to_stdout_writes_no_file(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(_cli.main, ["config", "generate", "-o", "-"])
    assert result.exit_code == 0
    assert "# color:" in result.output
    assert list(tmp_path.iterdir()) == []


def test_help_lists_both_subcommands(runner):
    result = runner.invoke(_cli.main, ["config", "--help"])
    assert result.exit_code == 0
    assert "generate" in result.output
    assert "path" in result.output
```

- [ ] **Step 2: Run to verify failure**

Run: `pixi run --frozen pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tephpy._cli'`.

- [ ] **Step 3: Write the CLI**

Create `src/tephpy/_cli.py` with the BSD header and:

```python
"""The ``tephpy`` command line (configfile spec §4).

Argument parsing and output text only. Everything this module does is
reachable from Python through ``tephpy.config`` and ``tephpy._configfile``,
so the command line is never the only way to do something.
"""

from __future__ import annotations

from pathlib import Path

import click

from tephpy import _configfile
from tephpy.exceptions import TephpyConfigError

__all__ = ["main"]


@click.group()
@click.version_option(package_name="tephpy")
def main() -> None:
    """Plot and analyse tephigrams."""


@main.group(invoke_without_command=True)
@click.pass_context
def config(ctx: click.Context) -> None:
    """Inspect and generate the tephpy configuration file."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(path)


@config.command()
def path() -> None:
    """Report the configuration file search, and which file is in force."""
    try:
        active = _configfile.discover()
    except TephpyConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    for candidate in _configfile.config_paths():
        if candidate == active:
            state = "in force"
        elif candidate.exists():
            state = "shadowed"
        else:
            state = "absent"
        click.echo(f"{candidate}  [{state}]")
    if active is None:
        click.echo("")
        click.echo("No configuration file found; tephpy is using its defaults.")


@config.command()
@click.option(
    "-o",
    "--output",
    "destination",
    default=None,
    help="Where to write. Use '-' for standard output.",
)
@click.option("--force", is_flag=True, help="Overwrite an existing file.")
def generate(destination: str | None, force: bool) -> None:
    """Write a fully-commented configuration template."""
    if destination == "-":
        click.echo(_configfile.render_template(), nl=False)
        return
    target = (
        _configfile.user_config_path() if destination is None else Path(destination)
    )
    try:
        _configfile.write_template(target, force=force)
    except TephpyConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Wrote {target}")
```

`click.ClickException` prints its message and exits 1, which is what the clobber and broken
`$TEPHPYRC` tests assert. No `if __name__ == "__main__"` block: the entry point is the
console script.

- [ ] **Step 4: Declare the console script**

In `pyproject.toml`, add:

```toml
[project.scripts]
tephpy = "tephpy._cli:main"
```

taplo reorders keys within a table and orders the tables themselves; run
`pixi run --frozen lint` and let it settle the placement rather than arguing with it.

- [ ] **Step 5: Run to verify the tests pass**

Run: `pixi run --frozen pytest tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 6: Verify the installed entry point**

The console script only exists once the editable install is re-linked:

Run: `pixi run --frozen tephpy config path`
Expected: three lines — the cascade with the user configuration directory last, each marked
`[absent]`, `[shadowed]` or `[in force]`. If the command is not found, run `pixi install`
once to re-link the editable install, then retry.

Run: `pixi run --frozen tephpy config generate -o -`
Expected: the template on standard output, no file written.

- [ ] **Step 7: Commit**

```bash
git add src/tephpy/_cli.py pyproject.toml tests/test_cli.py
git commit -m "Add the tephpy config command"
```

---

### Task 9: Documentation

**Files:**
- Modify: `docs/src/conf.py`
- Create: `docs/src/reference/cli.rst`
- Modify: `docs/src/reference/index.rst`
- Create: `docs/src/howtos/configuration.rst`
- Modify: `docs/src/howtos/index.rst`
- Create: `changelog/<PR>.feature.rst`

- [ ] **Step 1: Enable sphinx-click**

Add `"sphinx_click"` to the `extensions` list in `docs/src/conf.py`. The list is
alphabetical after its first two entries, so it goes between `"sphinx_changelog"` and
`"sphinx_copybutton"`.

- [ ] **Step 2: Add the reference page**

Create `docs/src/reference/cli.rst`:

```rst
.. _tephpy-cli:

Command Line
============

``tephpy`` installs a console script of the same name. It generates the
configuration file and reports which one is in force; see
:ref:`configure-from-a-file` for what to do with it.

.. click:: tephpy._cli:main
    :prog: tephpy
    :nested: full
```

Add `cli` to the `toctree` in `docs/src/reference/index.rst`, which uses four-space
indentation:

```rst
.. toctree::
    :maxdepth: 1

    generated/api/tephpy/index
    cli
    glossary
    changelog
```

- [ ] **Step 3: Write the how-to**

Create `docs/src/howtos/configuration.rst`. The title is CMOS headline style
(`docs/src/developer/docs-style.rst`), and the page follows the shape of
`docs/src/howtos/emphasis.rst` — a short framing paragraph, then task-sized sections:

```rst
.. _configure-from-a-file:

Configure tephpy From a File
============================

A house style is the same handful of lines at the top of every script — a
colour scheme, a preferred extent, a cursor readout. A configuration file
gives them a home on disk, and every later ``import tephpy`` picks them up.

Generate the Template
---------------------

.. code-block:: console

    $ tephpy config generate
    Wrote /home/you/.config/tephpy/tephpyrc.yaml

The template carries every option tephpy has, each commented out and showing
the default in force, with a line of prose above it. Nothing in it is active
until you uncomment something, so a freshly generated file changes nothing.

Uncomment what you want and edit the value:

.. code-block:: yaml

    isotherms:
      # Matplotlib colour for the lines and their labels.
      color: purple
      # Line width in points.
      # linewidth: 0.5

Where tephpy Looks
------------------

The first file found wins; there is no merging across the three:

1. the file named by ``$TEPHPYRC``
2. ``tephpyrc.yaml`` in the current working directory
3. ``tephpyrc.yaml`` in your user configuration directory

``tephpy config path`` reports the whole search, not just the winner, which
is what you want when a file appears to be ignored:

.. code-block:: console

    $ tephpy config path
    /home/you/work/tephpyrc.yaml  [in force]
    /home/you/.config/tephpy/tephpyrc.yaml  [shadowed]

Setting ``$TEPHPYRC`` to a file that does not exist is an error rather than a
fallthrough — naming a file explicitly and not having it is a mistake worth
reporting.

Quote Hex Colours
-----------------

YAML reads an unquoted ``#`` as the start of a comment, so

.. code-block:: yaml

    isotherms:
      color: #b0b0b0

sets ``color`` to null, not to grey. Quote it:

.. code-block:: yaml

    isotherms:
      color: '#b0b0b0'

tephpy warns about a null value rather than passing it on, and names the
missing quotes as the likely cause. Named colours such as ``purple`` and
``tab:blue`` need no quoting.

When the File Takes Effect
--------------------------

The file is read once, at ``import tephpy``, and an isopleth family reads
``tephpy.config`` when it is created. A configuration file therefore sets the
starting values for axes you create afterwards; it does not restyle axes that
already exist. This is the ``rcParams`` behaviour matplotlib users already
expect.

Saving From Python
------------------

``tephpy.config.save`` writes the options you actually set, and nothing else:

.. code-block:: python

    import tephpy

    tephpy.config.isotherms.color = "purple"
    tephpy.config.save()

It is a data dump: comments and key order in an existing file are not
preserved, because PyYAML cannot round-trip them. ``tephpy config generate``
is the command that produces the annotated file — reach for
``tephpy.config.save`` to capture a configuration you arrived at
interactively, not to edit one you already have.
```

Add `configuration` to the `toctree` in `docs/src/howtos/index.rst`, keeping the existing
alphabetical order:

```rst
    configuration
    emphasis
    logo
```

- [ ] **Step 4: Write the feature fragment**

`changelog/<PR>.feature.rst`, using the same `<PR>` as Task 3:

```rst
Added a YAML configuration file, so a tephigram house style no longer has to
be retyped at the top of every script. ``tephpy config generate`` writes a
fully-commented template of every option at its current default, and
``tephpy config path`` reports which file is in force. tephpy reads the first
match of ``$TEPHPYRC``, ``./tephpyrc.yaml``, and the file in your user
configuration directory. See :ref:`configure-from-a-file`.
(:user:`<github-username>`)
```

- [ ] **Step 5: Build the documentation**

Run: `pixi run --frozen docs`
Expected: the last line reads `build succeeded.` — the build treats warnings as errors.
Do not pipe the command into `tail` or `head`: a pipeline reports the exit status of the
last stage, which turns a failed build into a silent success. Redirect to a file and echo
`$?` if the output is long.

Check by eye in the built pages that `:ref:`configure-from-a-file`` resolves from both the
reference page and the changelog fragment, and that `tephpy config` renders with both
subcommands under it.

- [ ] **Step 6: Run everything**

Run: `pixi run --frozen tests`
Run: `pixi run --frozen lint`
Expected: both PASS. If `pre-commit` is not installed in this worktree, run
`pixi run --frozen pre-commit install` first — hooks are not installed in a fresh clone or
worktree, and `pixi run --frozen lint` cannot see untracked files, so `git add` the new
files before relying on it.

- [ ] **Step 7: Commit**

```bash
git add docs/ changelog/
git commit -m "Document configuring tephpy from a file"
```

---

## Definition of Done

- [ ] `pixi run --frozen tests` passes, image baselines included.
- [ ] `pixi run --frozen lint` passes with the pre-commit hooks installed and every new file
      staged.
- [ ] `pixi run --frozen docs` ends in `build succeeded.`
- [ ] `pixi run --frozen tephpy config path` prints the cascade; `tephpy config generate -o -`
      prints a template that `yaml.safe_load` accepts.
- [ ] The suite is unchanged by `$TEPHPYRC` pointing at a real configuration file
      (Task 6, Step 6).
- [ ] Every mutation-proof step ran and only the intended test failed: Task 1 Step 6,
      Task 2 Step 5, Task 5 Step 9, Task 6 Step 6, Task 7 Step 7.
- [ ] Two changelog fragments exist under the same pull request number: `.feature` and
      `.dependency`.
- [ ] The declared dependency floors were resolved by hand once (Task 3, Step 4), and any
      that had to be raised is noted in the pull request so `configfile spec §7` can be
      corrected.
