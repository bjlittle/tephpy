# Config Cluster Housekeeping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the three configuration-file housekeeping issues — the duplicated
`$TEPHPYRC` rule (#110), the generated template's over-long comment lines (#106), and the
absence of an API reference page for `tephpy.config` (#108).

**Architecture:** `src/tephpy/_configfile.py` already owns everything about the
configuration file, including the declarative tables (`CONFIG_DESCRIPTIONS`) that render the
commented template. This plan (a) collapses the two readings of `$TEPHPYRC` into one helper
so the path validated is the path returned, (b) wraps the template's comment lines to the
same 88 columns ruff holds the sources to, and (c) adds a second renderer over the same
tables — `render_reference()` — whose reStructuredText a thin Sphinx directive parses into a
published options page. One table, two renderings: a new option reaches both or neither.
Everything that produces text ships in the package, so its correctness is gated by ordinary
tests rather than by a docs build the test suite never runs.

**Tech Stack:** Python 3.11+, `textwrap`, `inspect`, `dataclasses`, `typing.get_type_hints`,
PyYAML, pytest, Sphinx (docutils directive, `sphinx.util.nodes.nested_parse_with_titles`),
autoapi, pixi.

**Design:** `docs/src/developer/specs/2026-08-07-config-file-design.md` — §3.2 (discovery),
§3.4 (the declarative tables and their gates), §3.6 (two renderings of one table), §6
(testing), §8 (documentation), §9 (non-goals). Cite it in code and prose as
`configfile spec §N`; a bare `spec §N` means the *parent* spec and will silently land
elsewhere.

## Global Constraints

- Every command runs from the worktree root via pixi with `--frozen`: `pixi run --frozen
  tests`, `pixi run --frozen lint`, `pixi run --frozen docs-html`, `pixi run --frozen docs`.
- Every source file carries the BSD copyright header, verbatim as in every existing file
  (ruff `CPY001`):
  ```
  # Copyright (c) 2026, tephpy Contributors.
  #
  # This file is part of tephpy and is distributed under the 3-Clause BSD license.
  # See the LICENSE file in the package root directory for licensing details.
  ```
- Line length is 88 columns (ruff). This is the same 88 the template gate enforces.
- Tests mirror the `src/tephpy` layout. `_configfile.py` is a top-level module, so its tests
  live at the `tests/` root.
- **`_configfile` must never import `_config` at runtime.** `src/tephpy/_config.py:23` has
  `from tephpy import _configfile` at module scope, so the arrow is one-way. `Config` may
  appear in `_configfile` only under `if TYPE_CHECKING:` (already present at
  `src/tephpy/_configfile.py:30-31`). Anything in `_configfile` needing the live
  configuration takes it as a parameter, exactly as `apply(config: Config, document, source)`
  does at `src/tephpy/_configfile.py:604`.
- Nothing in `_configfile` imports `tephpy.plotting` (module docstring, `_configfile.py:5-11`).
- Every public *and* private function in `_configfile.py` carries a full numpydoc docstring
  with `Parameters` / `Returns` / `Raises` as applicable — numpydoc validation runs in
  pre-commit. Follow `_format_default` at `src/tephpy/_configfile.py:833-853` as the model.
- The docs build is strict: `docs/Makefile` sets `SPHINXOPTS ?= --fail-on-warning
  --keep-going` and `docs/src/conf.py:162` sets `nitpicky = True`. Every unresolved
  cross-reference fails the build.
- Documentation titles use CMOS headline style (`docs/src/developer/docs-style.rst`).
- **Every new test must be mutation-proved:** stage the real work first (`git add`), then
  break the source, watch *only* the new test fail, and restore. `git checkout <path>`
  reverts from the index, so an unstaged mutate-revert cycle throws the work away with the
  mutation.
- The changelog fragment is written **last**, after the PR exists, because its number is the
  PR number (Task 6).

---

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `src/tephpy/_configfile.py` | `_named_path()`, `_cascade()`; wrapped `render_template()`; `CONFIG_DETAILS`; `render_reference()` | 1, 2, 3, 4 |
| `src/tephpy/_config.py` | `#:` comments on `labels` / `emphasis` shrink to type semantics; behaviour prose moves to `CONFIG_DETAILS` | 3 |
| `tests/test_configfile.py` | discovery tests — the changing-environment stub | 1 |
| `tests/test_configfile_template.py` | template gates — the 88-column width gate | 2 |
| `tests/test_configfile_reference.py` | **new** — detail, coverage and type-text gates | 3, 4 |
| `docs/src/_ext/tephpy_config_reference.py` | **new** — the `tephpy-config-options` directive | 5 |
| `docs/src/conf.py` | registers the extension | 5 |
| `docs/src/reference/config.rst` | **new** — the page hosting the directive | 5 |
| `docs/src/reference/index.rst` | toctree entry | 5 |
| `docs/src/howtos/configuration.rst` | three bare literals become `:meth:` roles | 5 |
| `changelog/<PR>.internal.rst`, `changelog/<PR>.documentation.rst` | news fragments | 6 |

---

## Task 1: One Reading of `$TEPHPYRC` (#110)

`config_paths()` and `discover()` each call `os.environ.get(CONFIG_ENV_VAR)` — at
`src/tephpy/_configfile.py:86` and `:114`. Two readings of a mutable environment leave a
window in which the file `discover()` checked for existence and the file it returns are two
different files. Collapse both onto one helper, resolved once per call.

Note the asymmetry the fix must preserve (configfile spec §3.2): `config_paths()` reports
absent entries — `tephpy config path` marks them `[absent]` — so the "set but not a file is
an error" rule belongs to `discover()` alone. `_cascade()` must not raise for a named path
that does not exist.

**Files:**
- Modify: `src/tephpy/_configfile.py:68-124`
- Test: `tests/test_configfile.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `_named_path() -> Path | None` and `_cascade(named: Path | None) -> tuple[Path, ...]`.
  No later task uses either. The public signatures `config_paths() -> tuple[Path, ...]` and
  `discover() -> Path | None` are unchanged.

- [ ] **Step 1: Write the failing test**

First add `import os` to the stdlib import block of `tests/test_configfile.py` — the block at
lines 9-11 reads `dataclasses`, `re`, `warnings`, and `os` sorts between the first two. Then
append the test:

```python
def test_discover_returns_the_path_it_validated(monkeypatch, tmp_path):
    """The path checked for existence is the path returned (configfile spec §3.2).

    Reading ``$TEPHPYRC`` once in ``discover`` and again in ``config_paths``
    leaves a window in which those are two different files. The stub makes the
    window visible by answering with a different file the second time.
    """
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text("", encoding="utf-8")
    second.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    answers = iter([str(first), str(second)])
    real_get = os.environ.get

    def get(key, default=None):
        if key == _configfile.CONFIG_ENV_VAR:
            return next(answers, str(second))
        return real_get(key, default)

    monkeypatch.setattr(os.environ, "get", get)

    assert _configfile.discover() == first
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pixi run --frozen pytest tests/test_configfile.py::test_discover_returns_the_path_it_validated -v
```

Expected: FAIL. The current code validates `first` and then returns `second`, so the
assertion reports `second.yaml == first.yaml`.

- [ ] **Step 3: Add the two helpers**

Insert both immediately above `config_paths()` in `src/tephpy/_configfile.py` (before line
68):

```python
def _named_path() -> Path | None:
    """Return the path ``$TEPHPYRC`` names, if it names one.

    Returns
    -------
    pathlib.Path or None
        The path the environment variable names, or ``None`` when it is unset
        or empty. Both entry points to the discovery cascade take their answer
        from here, so the environment is read once per call: the file
        ``discover`` checks for existence is then necessarily the file it
        returns (configfile spec §3.2).
    """
    named = os.environ.get(CONFIG_ENV_VAR)
    return Path(named) if named else None


def _cascade(named: Path | None) -> tuple[Path, ...]:
    """Build the discovery cascade around an already-resolved ``$TEPHPYRC``.

    Parameters
    ----------
    named : pathlib.Path or None
        The path ``$TEPHPYRC`` names, as :func:`_named_path` resolved it, or
        ``None`` when it names none.

    Returns
    -------
    tuple of pathlib.Path
        The named path when there is one, then the working directory, then the
        user configuration directory. The entries need not exist: a caller
        reporting the search shows the absent ones too, so nothing here rejects
        a path for not being a file.

    Raises
    ------
    TephpyConfigError
        If the current working directory no longer exists, so the failure
        surfaces the same way every other unreadable-configuration case does,
        instead of an uncontained ``FileNotFoundError`` reaching
        ``import tephpy`` (configfile spec §5).
    """
    paths: list[Path] = []
    if named is not None:
        paths.append(named)
    try:
        cwd = Path.cwd()
    except FileNotFoundError as exc:
        msg = f"cannot read the working directory to look for {CONFIG_FILENAME}: {exc}"
        raise TephpyConfigError(msg) from exc
    paths.append(cwd / CONFIG_FILENAME)
    paths.append(user_config_path())
    return tuple(paths)
```

- [ ] **Step 4: Rewrite the two public functions over the helpers**

Replace the body of `config_paths()` (currently `src/tephpy/_configfile.py:85-96`) with a
single line, leaving its docstring as it stands:

```python
    return _cascade(_named_path())
```

Replace the body of `discover()` (currently `src/tephpy/_configfile.py:113-124`):

```python
    named = _named_path()
    if named is not None and not named.is_file():
        msg = (
            f"{CONFIG_ENV_VAR} names {str(named)!r}, which is not a file; unset "
            f"{CONFIG_ENV_VAR} to fall back to the {CONFIG_FILENAME} search"
        )
        raise TephpyConfigError(msg)
    for path in _cascade(named):
        if path.is_file():
            return path
    return None
```

The `str(named)!r` keeps the existing message byte-for-byte: the old code interpolated the
raw environment string, and `str(Path(s))` differs from `s` only for input the message would
be quoting oddly anyway (a trailing slash). Existing message assertions in
`tests/test_configfile.py` must still pass unchanged — if one fails, that is a real
regression, not a test to update.

- [ ] **Step 5: Run the whole configuration suite**

```bash
pixi run --frozen pytest tests/test_configfile.py tests/test_configfile_template.py tests/test_config.py -v
```

Expected: PASS, including the new test.

- [ ] **Step 6: Mutation-prove the new test**

```bash
git add -A
```

Then in `discover()`, change `for path in _cascade(named):` back to
`for path in _cascade(_named_path()):` — reintroducing the second read. Run:

```bash
pixi run --frozen pytest tests/test_configfile.py -v
```

Expected: **only** `test_discover_returns_the_path_it_validated` fails. Restore with
`git checkout src/tephpy/_configfile.py` (safe: the work is staged) and re-run to confirm
green.

- [ ] **Step 7: Lint and commit**

```bash
pixi run --frozen lint
git add src/tephpy/_configfile.py tests/test_configfile.py
git commit -m "fix: read \$TEPHPYRC once per discovery cascade

The path discover() validated and the path it returned came from two
separate reads of a mutable environment. Both entry points now take the
answer from _named_path(), resolved once per call (configfile spec §3.2).

Closes #110"
```

---

## Task 2: Wrap the Generated Template to 88 Columns (#106)

`render_template()` emits each option's description as a single `  # ` comment line. Eleven
of the 42 overrun 88 columns; the longest is 117. Wrap them with `textwrap.fill`, counting
the `  # ` prefix in the width.

Value lines are deliberately **not** wrapped (configfile spec §3.6): the widest is 44
columns, and a wrapped YAML value would no longer be uncommentable — the whole point of the
template. Only the description comments are wrapped.

**Files:**
- Modify: `src/tephpy/_configfile.py` (imports at `:13-21`, `render_template()` at `:879-907`)
- Test: `tests/test_configfile_template.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: module constant `_TEMPLATE_WIDTH: Final[int] = 88`. Task 4's renderer does not
  use it — the reference page is reStructuredText, which has no width rule.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_configfile_template.py`:

```python
def test_no_generated_template_line_exceeds_the_source_width():
    """The template is held to the width ruff holds the sources to.

    88 is written here as a literal rather than imported from ``_configfile``,
    so that raising the renderer's width cannot silently carry the gate up with
    it (configfile spec §3.4).
    """
    over = [line for line in _configfile.render_template().splitlines() if len(line) > 88]
    assert over == []
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pixi run --frozen pytest tests/test_configfile_template.py::test_no_generated_template_line_exceeds_the_source_width -v
```

Expected: FAIL, listing eleven over-long lines, the longest 117 characters.

- [ ] **Step 3: Import `textwrap`**

In `src/tephpy/_configfile.py`, add to the stdlib import block. The block is sorted by module
name regardless of import style, so `import textwrap` goes immediately after
`from pathlib import Path` (line 18) and before `from types import MappingProxyType`:

```python
from pathlib import Path
import textwrap
from types import MappingProxyType
```

- [ ] **Step 4: Add the width constant**

Immediately above `def render_template() -> str:` (currently `src/tephpy/_configfile.py:879`):

```python
#: Width the generated template's comment lines are wrapped to, matching the
#: line length ruff holds this repository's own sources to. Value lines are not
#: wrapped: a wrapped YAML value would no longer be uncommentable, which is the
#: whole point of the template (configfile spec §3.6).
_TEMPLATE_WIDTH: Final[int] = 88
```

- [ ] **Step 5: Wrap the description comments**

In `render_template()`, replace the inner loop (currently `src/tephpy/_configfile.py:903-905`):

```python
        for option, default in options.items():
            lines.append(f"  # {CONFIG_DESCRIPTIONS[section][option]}")
            lines.append(f"  # {option}: {_format_default(default)}".rstrip())
```

with:

```python
        for option, default in options.items():
            lines.extend(
                textwrap.fill(
                    CONFIG_DESCRIPTIONS[section][option],
                    width=_TEMPLATE_WIDTH,
                    initial_indent="  # ",
                    subsequent_indent="  # ",
                ).splitlines()
            )
            lines.append(f"  # {option}: {_format_default(default)}".rstrip())
```

- [ ] **Step 6: Run the template suite**

```bash
pixi run --frozen pytest tests/test_configfile_template.py -v
```

Expected: PASS. In particular `test_an_untouched_template_loads_as_no_configuration` must
still pass — wrapping adds comment lines only, so the parsed document is unchanged.

- [ ] **Step 7: Read the output by eye**

```bash
pixi run --frozen python -c "from tephpy import _configfile; print(_configfile.render_template())" | head -40
```

Confirm continuation lines carry the `  # ` prefix and no option's description is orphaned
from its value line.

- [ ] **Step 8: Mutation-prove the gate**

```bash
git add -A
```

Revert Step 5's loop to the single-line form, run
`pixi run --frozen pytest tests/test_configfile_template.py -v`, and confirm **only** the new
width test fails. Restore with `git checkout src/tephpy/_configfile.py` and re-run.

- [ ] **Step 9: Lint and commit**

```bash
pixi run --frozen lint
git add src/tephpy/_configfile.py tests/test_configfile_template.py
git commit -m "fix: wrap generated template comments to 88 columns

Eleven of the 42 option descriptions overran the line length ruff holds
the sources to, the longest at 117. Value lines stay unwrapped: a wrapped
YAML value would no longer be uncommentable (configfile spec §3.6).

Closes #106"
```

---

## Task 3: `CONFIG_DETAILS`, the Second Register of Prose

`CONFIG_DESCRIPTIONS` carries the one-line summary both renderings show. The reference page
has room for more, and richer prose already exists — as `#:` comments on `LineOptions` in
`src/tephpy/_config.py`. Those comments are published **nowhere**: they are not docstrings,
so they are invisible at runtime; `_config` is private and excluded from autoapi; and autoapi
parses statically, so it drops `#:` comments regardless. Move the behaviour prose into a new
table that the reference page renders, and shrink the `#:` comments to the type semantics a
reader of `_config.py` actually needs there.

`CONFIG_DETAILS` is **sparse by design** (configfile spec §3.4): its gate is a subset check
against `CONFIG_DEFAULTS`, not a completeness check, so it must also pin its own membership —
a subset gate over an empty table passes by checking nothing.

One correction lands en route. The existing `#:` comment on `LineOptions.emphasis`
(`src/tephpy/_config.py:70-76`) says "``{0.0: {}}`` is the 0 °C member", but `LineOptions` is
the base class for isobars (hPa) and mixing ratios (g/kg) as well as the temperature
families. The moved prose is unit-neutral.

**Files:**
- Modify: `src/tephpy/_configfile.py` (`__all__` at `:33`ff; new table after
  `CONFIG_DESCRIPTIONS`, which ends around `:804`)
- Modify: `src/tephpy/_config.py:60-64` and `:70-76`
- Create: `tests/test_configfile_reference.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2.
- Produces: `CONFIG_DETAILS: Final[Mapping[str, Mapping[str, str]]]` — a sparse
  section→option→prose mapping. Task 4's `render_reference()` reads it via
  `CONFIG_DETAILS.get(section, {}).get(option)`.

- [ ] **Step 1: Write the failing gates**

Create `tests/test_configfile_reference.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The reference-page rendering of the configuration tables (configfile spec §3.6)."""

from __future__ import annotations

from tephpy import _configfile
from tephpy._constants import CONFIG_DEFAULTS

#: Every option ``CONFIG_DETAILS`` is expected to carry. Written out rather than
#: derived, so that both losing a detail and gaining an ungated one are failures
#: (configfile spec §3.4).
EXPECTED_DETAILS = {
    (section, option)
    for section in (
        "isotherms",
        "isobars",
        "dry_adiabats",
        "moist_adiabats",
        "mixing_ratios",
    )
    for option in ("labels", "emphasis")
}


def test_details_name_only_real_options():
    """A detail cannot outlive the option it details (configfile spec §3.4)."""
    for section, options in _configfile.CONFIG_DETAILS.items():
        assert section in CONFIG_DEFAULTS, section
        assert set(options) <= set(CONFIG_DEFAULTS[section]), section


def test_the_detail_table_carries_what_it_is_expected_to():
    """The subset gate above passes vacuously over an empty table.

    Pinning membership is what makes it refuse its own empty input.
    """
    detailed = {
        (section, option)
        for section, options in _configfile.CONFIG_DETAILS.items()
        for option in options
    }
    assert detailed == EXPECTED_DETAILS


def test_every_detail_is_prose():
    """Details are sentences the reference page prints, not fragments."""
    for options in _configfile.CONFIG_DETAILS.values():
        for option, detail in options.items():
            assert detail.strip() == detail, option
            assert detail.endswith("."), option
            assert len(detail) > 40, option
```

- [ ] **Step 2: Run to verify it fails**

```bash
pixi run --frozen pytest tests/test_configfile_reference.py -v
```

Expected: FAIL with `AttributeError: module 'tephpy._configfile' has no attribute
'CONFIG_DETAILS'`.

- [ ] **Step 3: Add the shared details and the table**

In `src/tephpy/_configfile.py`, immediately after the `CONFIG_DESCRIPTIONS` definition ends
(around line 804), add:

```python
#: Detail shared by the ``labels`` and ``emphasis`` options, which behave the
#: same way for every isopleth family, as ``_LINE_DESCRIPTIONS`` above is.
#: Unlike the descriptions, this prose is unit-neutral: ``LineOptions`` is the
#: base for isobars in hPa and mixing ratios in g/kg as well as the temperature
#: families, so no example here names a unit.
_LINE_DETAILS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "labels": (
            "Listed edges label the members that reach them, and every member "
            "left over is labelled inline. ``true`` labels every member "
            "inline; ``false`` labels none."
        ),
        "emphasis": (
            "Each value is a mapping of style overrides -- ``color``, "
            "``linewidth``, ``linestyle`` and ``alpha`` -- and an omitted key "
            "falls back to the family's own style, so ``{20.0: {}}`` is the "
            "member at 20 in the family's own units, drawn at the emphasis "
            "line width in the family's own colour. An emphasised member is "
            "always drawn, whatever the zoom-adaptive ladder would otherwise "
            "select. An empty mapping emphasises nothing."
        ),
    }
)

#: The longer prose the options reference page has room for and the generated
#: template does not (configfile spec §3.6). Sparse: an option with nothing
#: more to say than its ``CONFIG_DESCRIPTIONS`` line is absent, and the gate in
#: ``tests/test_configfile_reference.py`` is a subset check against
#: ``CONFIG_DEFAULTS`` with its own membership pinned, not a completeness check.
CONFIG_DETAILS: Final[Mapping[str, Mapping[str, str]]] = MappingProxyType(
    {
        "isotherms": MappingProxyType(dict(_LINE_DETAILS)),
        "isobars": MappingProxyType(dict(_LINE_DETAILS)),
        "dry_adiabats": MappingProxyType(dict(_LINE_DETAILS)),
        "moist_adiabats": MappingProxyType(dict(_LINE_DETAILS)),
        "mixing_ratios": MappingProxyType(dict(_LINE_DETAILS)),
    }
)
```

- [ ] **Step 4: Export it**

Add `"CONFIG_DETAILS",` to `__all__` in `src/tephpy/_configfile.py` (starting line 33),
keeping the list's existing alphabetical order — it sorts immediately after
`"CONFIG_DESCRIPTIONS"`.

- [ ] **Step 5: Run the gates**

```bash
pixi run --frozen pytest tests/test_configfile_reference.py -v
```

Expected: PASS, all three.

- [ ] **Step 6: Shrink the `#:` comments in `_config.py`**

Replace `src/tephpy/_config.py:60-64` (the `labels` comment) with:

```python
    #: Whether member values are labelled, and where: ``True`` (every member
    #: labelled inline — the default), ``False`` (none), or the diagram edge
    #: names ``"bottom"``, ``"top"``, ``"left"`` and ``"right"``, singly as a
    #: bare string or together as a tuple. What each choice draws is
    #: ``_configfile.CONFIG_DETAILS["<family>"]["labels"]``, which the options
    #: reference page publishes (configfile spec §3.6).
    labels: bool | str | tuple[str, ...] | None = None
```

Replace `src/tephpy/_config.py:70-76` (the `emphasis` comment) with:

```python
    #: Members drawn with a distinguishing style, keyed by member value in the
    #: family's native units, each value a mapping of style overrides. What an
    #: override does, and what an omitted key or an empty mapping means, is
    #: ``_configfile.CONFIG_DETAILS["<family>"]["emphasis"]``, which the options
    #: reference page publishes (configfile spec §3.6).
    emphasis: Mapping[float, Mapping[str, object]] | None = None
```

- [ ] **Step 7: Run the full suite**

```bash
pixi run --frozen tests
```

Expected: PASS. `#:` comments are inert at runtime, so nothing should move; if something
does, it is a genuine surprise worth reporting rather than working around.

- [ ] **Step 8: Mutation-prove the membership gate**

```bash
git add -A
```

Delete the `"mixing_ratios"` entry from `CONFIG_DETAILS`, run
`pixi run --frozen pytest tests/test_configfile_reference.py -v`, and confirm **only**
`test_the_detail_table_carries_what_it_is_expected_to` fails — this proves
`test_details_name_only_real_options` alone would have let the table empty out silently.
Then instead add a bogus `"isotherms": {"nosuchoption": "..."}` entry and confirm
`test_details_name_only_real_options` fails. Restore with
`git checkout src/tephpy/_configfile.py` and re-run.

- [ ] **Step 9: Lint and commit**

```bash
pixi run --frozen lint
git add src/tephpy/_configfile.py src/tephpy/_config.py tests/test_configfile_reference.py
git commit -m "feat: add CONFIG_DETAILS, the prose the reference page has room for

The behaviour prose lived in #: comments on _config.LineOptions, where
nothing published it: those are not docstrings, _config is private, and
autoapi parses statically. It moves to a table the options reference page
renders, unit-neutral now that it is shared by families measured in hPa
and g/kg as well as degrees Celsius (configfile spec §3.4, §3.6)."
```

---

## Task 4: `render_reference()` (#108, package side)

The second rendering of the same tables: reStructuredText declaring a `py:attribute` target
per option and a `py:method` target per public method of `tephpy.config`, so prose anywhere
in the documentation can cross-reference them. It ships in the package rather than in the
Sphinx extension so that its gates are ordinary tests — `pixi run tests` has no Sphinx and
never runs a build.

Types come from the *evaluated* annotations `_option_hints()` already returns for the
validators. Because `typing.get_type_hints` has resolved them, `str()` alone yields text
carrying what a source annotation would not: `Mapping` arrives as
`collections.abc.Mapping[float, collections.abc.Mapping[str, object]]`, and the private
`Extent` alias arrives expanded to `tuple[tuple[float, float], tuple[float, float]]`. No
qualification table is needed and none should be added — it would be a second spelling of
what the annotations already say, of exactly the kind these gates exist to catch. What the
type-text gate guards is the case `str()` cannot render: an annotation naming a class
stringifies as `<class 'tephpy._config.Thing'>`, which reaches the page as neither valid type
text nor a resolvable target.

**Files:**
- Modify: `src/tephpy/_configfile.py` (imports; `__all__`; new functions after
  `render_template()`)
- Test: `tests/test_configfile_reference.py`

**Interfaces:**
- Consumes: `CONFIG_DETAILS` (Task 3); the existing `_option_hints(cls)` helper and
  `_format_default(value)` at `src/tephpy/_configfile.py:833`.
- Produces: `render_reference(config: Config) -> str`, returning reStructuredText. Task 5's
  Sphinx directive calls it as `render_reference(tephpy.config)`. It takes the instance
  because `_configfile` may not import `_config` at runtime (Global Constraints) — the same
  reason `apply(config: Config, ...)` does.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_configfile_reference.py`. Add to its import block, keeping the existing
grouping:

```python
import builtins
import re

import tephpy
```

and the tests:

```python
#: A dotted or bare Python name inside rendered type text.
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")


def rendered():
    """Return the reference page as ``render_reference`` renders it."""
    return _configfile.render_reference(tephpy.config)


def test_the_reference_names_every_option_and_no_others():
    """The page and the template render the same table (configfile spec §3.6)."""
    prefix = ".. py:attribute:: "
    emitted = {
        line.removeprefix(prefix) for line in rendered().splitlines() if line.startswith(prefix)
    }
    assert emitted == {
        f"tephpy.config.{section}.{option}"
        for section, options in CONFIG_DEFAULTS.items()
        for option in options
    }


def test_the_option_set_the_page_is_gated_against_is_not_empty():
    """Forty-two, so the gate above cannot pass by rendering nothing."""
    assert sum(len(options) for options in CONFIG_DEFAULTS.values()) == 42


def test_every_rendered_type_is_resolvable_text():
    """``str()`` of an annotation naming a class yields ``<class '...'>``.

    That reaches the page as neither valid type text nor a resolvable target,
    and the docs build is where it would surface — a build ``pixi run tests``
    never runs (configfile spec §3.4).
    """
    prefix = "   :type: "
    types = [
        line.removeprefix(prefix) for line in rendered().splitlines() if line.startswith(prefix)
    ]
    assert len(types) == 42
    for text in types:
        assert "<" not in text, text
        for name in NAME.findall(text):
            assert "." in name or hasattr(builtins, name), f"{name!r} in {text!r}"


def test_every_method_is_given_a_target():
    """Prose cross-references the methods; the page is where they resolve."""
    emitted = [line for line in rendered().splitlines() if line.startswith(".. py:method:: ")]
    assert emitted == [
        ".. py:method:: tephpy.config.load(path=None)",
        ".. py:method:: tephpy.config.save(path=None)",
        ".. py:method:: tephpy.config.reset()",
        ".. py:method:: tephpy.config.context(**overrides)",
    ]


def test_a_default_is_rendered_by_its_kind():
    """Three branches, where the template's renderer has two.

    ``_format_default`` renders both ``None`` and an empty mapping as the empty
    string, because the template needs a line the reader can uncomment. The
    page has no such constraint: an absent default and an empty one are
    different facts and are printed differently (configfile spec §3.6).
    """
    text = rendered()
    assert "Default: unset" in text
    assert "Default: ``None``" not in text
    assert "Default: ``{}``" in text
    assert "Default: ``dimgrey``" in text
    assert "Default: ``[[1050.0, -40.0], [200.0, 40.0]]``" in text
```

Nine options default to `None` and five to an empty mapping, so the first three assertions
each have something to find. `dimgrey` is `isotherms.color`; the last is `diagram.extent`,
the only nested default, so it also proves the flow-style rendering survives a value two
levels deep.

`hasattr(builtins, name)` covers `None` — it is an attribute of the `builtins` module even
though it cannot be written as one. `tuple[float, ...]` needs nothing: `...` matches no
name, and `docs/src/conf.py:163` already carries `("py:class", "Ellipsis")`.

- [ ] **Step 2: Run to verify they fail**

```bash
pixi run --frozen pytest tests/test_configfile_reference.py -v
```

Expected: the four new rendering tests FAIL with `AttributeError: ... has no attribute
'render_reference'`; `test_the_option_set_the_page_is_gated_against_is_not_empty` passes.

- [ ] **Step 3: Import `inspect`**

In `src/tephpy/_configfile.py`, add `import inspect` to the stdlib block, sorted by module
name — after `import datetime` and before `import os`.

- [ ] **Step 4: Add the method roster and the two helpers**

Immediately after `render_template()` ends (after the current line 907), add:

```python
#: Methods of ``tephpy.config`` given a target on the options reference page,
#: in the order a reader meets them. Thinner than the docstrings ``Config``
#: carries: numpydoc's docstring processing is an autodoc hook, and this
#: project renders its API with autoapi, so a full rendering here would be a
#: second, hand-maintained one (configfile spec §3.6, §9).
_REFERENCE_METHODS: Final[tuple[str, ...]] = ("load", "save", "reset", "context")


def _reference_signature(method: object) -> str:
    """Spell a method's parameters as the reference page shows them.

    Parameters
    ----------
    method : object
        An unbound method of ``Config``.

    Returns
    -------
    str
        The parameter list without enclosing parentheses, ``self`` dropped and
        annotations omitted. ``inspect.signature`` renders resolved annotations
        as quoted strings, which is noise on a page whose types come from
        elsewhere; name and default are what the reader needs.
    """
    parameters = list(inspect.signature(method).parameters.values())[1:]
    rendered = []
    for parameter in parameters:
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            rendered.append(f"**{parameter.name}")
        elif parameter.default is inspect.Parameter.empty:
            rendered.append(parameter.name)
        else:
            rendered.append(f"{parameter.name}={parameter.default!r}")
    return ", ".join(rendered)


def _reference_default(value: object) -> str:
    """Render a default as the reference page shows it.

    Parameters
    ----------
    value : object
        The default from ``CONFIG_DEFAULTS``.

    Returns
    -------
    str
        The value as inline literal YAML, or the word ``unset`` for an option
        with no default. ``_format_default`` renders both ``None`` and an empty
        mapping as the empty string, because the template needs a line a reader
        can uncomment; the page has no such constraint and distinguishes them.
    """
    if value is None:
        return "unset"
    return f"``{_format_default(value) or '{}'}``"
```

- [ ] **Step 5: Add the renderer**

Immediately after `_reference_default`:

```python
def render_reference(config: Config) -> str:
    """Render the options reference page as reStructuredText.

    Parameters
    ----------
    config : Config
        The live configuration, supplying each section's dataclass so the
        annotations can be evaluated. It is a parameter rather than an import
        because ``_config`` imports this module at module scope: passing the
        instance in is what keeps that arrow one-way (configfile spec §3.6).

    Returns
    -------
    str
        A section per configuration section, a ``py:attribute`` target per
        option and a ``py:method`` target per method in
        ``_REFERENCE_METHODS`` — the second rendering of the same tables the
        configuration template is rendered from, so a new option reaches both
        or neither.
    """
    lines = [
        ".. Generated by tephpy._configfile.render_reference from the tables in",
        ".. _configfile.py. Edit those, not this output (configfile spec §3.6).",
        "",
    ]
    for section, options in CONFIG_DEFAULTS.items():
        hints = _option_hints(type(getattr(config, section)))
        lines.append(section)
        lines.append("-" * len(section))
        lines.append("")
        for option, default in options.items():
            lines.append(f".. py:attribute:: tephpy.config.{section}.{option}")
            lines.append(f"   :type: {hints[option]!s}")
            lines.append("")
            lines.append(f"   {CONFIG_DESCRIPTIONS[section][option]}")
            detail = CONFIG_DETAILS.get(section, {}).get(option)
            if detail is not None:
                lines.append("")
                lines.append(f"   {detail}")
            lines.append("")
            lines.append(f"   Default: {_reference_default(default)}")
            lines.append("")
    lines.append("Methods")
    lines.append("-------")
    lines.append("")
    lines.append(
        "These entries exist so that prose can cross-reference them; "
        ":ref:`configure-from-a-file` is the how-to that explains when to reach "
        "for each."
    )
    lines.append("")
    for name in _REFERENCE_METHODS:
        method = getattr(type(config), name)
        lines.append(f".. py:method:: tephpy.config.{name}({_reference_signature(method)})")
        lines.append("")
        lines.append(f"   {inspect.getdoc(method).splitlines()[0]}")
        lines.append("")
    return "\n".join(lines)
```

`_option_hints` is called with `type(getattr(config, section))` — the section's dataclass —
matching how `apply()` uses it at `src/tephpy/_configfile.py:604`ff. Iterating
`CONFIG_DEFAULTS` rather than `dataclasses.fields(config)` keeps the page's order identical
to the template's.

- [ ] **Step 6: Export it**

Add `"render_reference",` to `__all__` in `src/tephpy/_configfile.py`, in alphabetical
position — immediately before `"render_template"`.

- [ ] **Step 7: Run the tests**

```bash
pixi run --frozen pytest tests/test_configfile_reference.py -v
```

Expected: PASS, all eight.

- [ ] **Step 8: Read the output by eye**

```bash
pixi run --frozen python -c "import tephpy; from tephpy import _configfile; print(_configfile.render_reference(tephpy.config))" | head -60
```

Confirm the `:type:` lines read as valid Python type text (`str | None`,
`collections.abc.Mapping[float, collections.abc.Mapping[str, object]] | None`,
`tuple[tuple[float, float], tuple[float, float]] | None`) and that no `<class '...'>` appears.

- [ ] **Step 9: Mutation-prove the type-text gate**

```bash
git add -A
```

In `render_reference`, change `f"   :type: {hints[option]!s}"` to
`f"   :type: {type(config)}"` — a class object, the exact failure the gate exists for. Run
`pixi run --frozen pytest tests/test_configfile_reference.py -v` and confirm
`test_every_rendered_type_is_resolvable_text` fails on the `<` assertion. Then mutate the
coverage gate's target: drop the `for option, default in options.items():` body's
`py:attribute` line and confirm `test_the_reference_names_every_option_and_no_others` fails.
Restore with `git checkout src/tephpy/_configfile.py` and re-run.

- [ ] **Step 10: Lint and commit**

```bash
pixi run --frozen lint
git add src/tephpy/_configfile.py tests/test_configfile_reference.py
git commit -m "feat: render the tephpy.config options reference

A second rendering of the same tables the configuration template is
rendered from: a py:attribute target per option and a py:method target
per public method, so prose can cross-reference them. It ships with the
package so that its gates are ordinary tests -- pixi run tests has no
Sphinx and never runs a build (configfile spec §3.6)."
```

---

## Task 5: The Published Page (#108, docs side)

A thin Sphinx directive parses `render_reference()`'s output into the doctree, on a page in
the reference section. Then the three bare literals in the configuration how-to become live
cross-references — the point of having targets at all.

**Files:**
- Create: `docs/src/_ext/tephpy_config_reference.py`
- Modify: `docs/src/conf.py:25-40` (extensions)
- Create: `docs/src/reference/config.rst`
- Modify: `docs/src/reference/index.rst` (toctree)
- Modify: `docs/src/howtos/configuration.rst:108`, `:156`, `:168`

**Interfaces:**
- Consumes: `tephpy._configfile.render_reference(config)` (Task 4).
- Produces: the directive `.. tephpy-config-options::` and the label `_tephpy-config-options:`.

- [ ] **Step 1: Write the extension**

Create `docs/src/_ext/tephpy_config_reference.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Publish the ``tephpy.config`` options reference (configfile spec §3.6).

The directive owns no prose of its own. Everything it emits comes from
``tephpy._configfile.render_reference``, which is rendered from the same tables
the configuration template is rendered from, so a new option reaches both
renderings or neither. Keeping the renderer in the package rather than here is
what makes its output testable: ``pixi run tests`` has no Sphinx.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles

import tephpy
from tephpy import _configfile

if TYPE_CHECKING:
    from sphinx.application import Sphinx


class ConfigOptionsDirective(SphinxDirective):
    """Emit a documented target for every ``tephpy.config`` option."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        """Parse the rendered reference into the calling document.

        Returns
        -------
        list of docutils.nodes.Node
            One section per configuration section, plus the methods section.
        """
        # The rendered text is not a source file Sphinx knows to watch, so an
        # incremental build would serve the previous options until this page's
        # own source changed.
        self.env.note_dependency(_configfile.__file__)
        text = _configfile.render_reference(tephpy.config)
        lines = StringList(
            text.splitlines(), source="tephpy._configfile.render_reference"
        )
        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, lines, node)
        return node.children


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the directive.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.

    Returns
    -------
    dict
        The extension metadata.
    """
    app.add_directive("tephpy-config-options", ConfigOptionsDirective)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
```

- [ ] **Step 2: Register it**

In `docs/src/conf.py`, append `"tephpy_config_reference",` to the end of the `extensions`
list (after `"sphinxcontrib.bibtex"`). Do **not** disturb `"tephpy_citation_xrefs"` at the
head of the list — a gate checks it is still first. `docs/src/conf.py:17` already puts
`docs/src/_ext` on `sys.path`.

- [ ] **Step 3: Write the page**

Create `docs/src/reference/config.rst`:

```rst
.. _tephpy-config-options:

Configuration Options
=====================

Every option ``tephpy.config`` carries, with the type it accepts and the
default in force. The same options, as a commented file you can edit, come
from ``tephpy config generate``; see :ref:`configure-from-a-file` for how that
file is found and applied, and :ref:`tephpy-cli` for the commands that manage
it.

This page is generated from the tables in the configuration module at build
time, so it and the generated file always describe the same options.

.. tephpy-config-options::
```

- [ ] **Step 4: Add it to the toctree**

In `docs/src/reference/index.rst`, add `config` to the toctree between `cli` and `glossary`,
matching the existing 4-space indentation.

- [ ] **Step 5: Build and check the page exists**

```bash
rm -rf docs/_build docs/src/_build
pixi run --frozen docs-html
```

Expected: `build succeeded`, exit 0 under `--fail-on-warning --keep-going` and
`nitpicky = True`. A `WARNING: py:class reference target not found` here means a rendered
type failed to resolve — report it rather than adding a `nitpick_ignore` entry, because
`("py:class", "Ellipsis")` is the only one the design sanctions.

- [ ] **Step 6: Verify the rendered HTML, not just the build**

```bash
grep -c 'id="tephpy.config.isotherms.color"' docs/_build/html/reference/config.html
grep -c 'id="tephpy.config.load"' docs/_build/html/reference/config.html
grep -o 'left over is labelled inline' docs/_build/html/reference/config.html | head -1
```

The Python domain uses the full dotted name as the element id, not a slugified one — that is
also the anchor the `:meth:` links in Step 7 will point at.

Expected: `1`, `1`, and the moved detail prose present. If `docs/_build` is not where the
build lands, take the path from the build's closing "The HTML pages are in ..." line.

- [ ] **Step 7: Convert the how-to's bare literals**

In `docs/src/howtos/configuration.rst`, replace the inline literals with roles:

- line 108: ``` ``tephpy.config.load`` ``` → ``` :meth:`tephpy.config.load` ```
- line 156: ``` ``tephpy.config.save`` ``` → ``` :meth:`tephpy.config.save` ```
- line 168: ``` ``tephpy.config.save`` ``` → ``` :meth:`tephpy.config.save` ```

Leave line 95's ``` ``tephpy.config`` ``` alone — it names the object, not a method — and
leave lines 151 and 163 alone: they are inside code blocks.

- [ ] **Step 8: Rebuild clean and confirm the links resolve**

```bash
rm -rf docs/_build docs/src/_build
pixi run --frozen docs
```

`pixi run docs` builds and then runs the gates that read the HTML. Expected: exit 0. Then:

```bash
grep -o 'href="[^"]*#tephpy.config.load"' docs/_build/html/howtos/configuration.html | head -2
```

Expected: at least one hit — a bare literal that failed to resolve would have failed the
build under `nitpicky`, but this confirms the anchor is the reference page's.

- [ ] **Step 9: Lint and commit**

```bash
pixi run --frozen lint
git add docs/src/_ext/tephpy_config_reference.py docs/src/conf.py docs/src/reference/config.rst docs/src/reference/index.rst docs/src/howtos/configuration.rst
git commit -m "docs: publish the tephpy.config options reference

tephpy.config had no API reference page: it is an instance of a private
dataclass, so autoapi documents the name and nothing under it. A directive
now parses render_reference()'s output into a page in the reference
section, giving every option and the four public methods a target, and the
configuration how-to's bare literals become live cross-references
(configfile spec §3.6).

Closes #108"
```

---

## Task 6: Changelog Fragments

The fragment's number is the pull request's number, and an issue filed between opening the PR
and writing the fragment would steal it. Open the PR first, then write the fragments against
the number GitHub assigned.

**Files:**
- Create: `changelog/<PR>.internal.rst`
- Create: `changelog/<PR>.documentation.rst`

- [ ] **Step 1: Push and open the pull request**

Confirm with the human partner before pushing — opening a PR is outward-facing. Then:

```bash
git push -u origin debt-config-cluster
```

Open the PR against `main` with `gh pr create`. In the PR *body*, reference the issues as
bare `#110`, `#106`, `#108` — Sphinx roles such as `:issue:` render literally on GitHub.

- [ ] **Step 2: Write the internal fragment**

Create `changelog/<PR>.internal.rst` with the PR's number, e.g.:

```rst
The two entry points to the configuration-file discovery cascade now read
``$TEPHPYRC`` once between them, closing the window in which the file checked for
existence and the file returned were two different files (:issue:`110`).
(:user:`claude`)
```

- [ ] **Step 3: Write the documentation fragment**

Create `changelog/<PR>.documentation.rst`:

```rst
``tephpy.config`` now has an options reference page, listing every option with the
type it accepts and the default in force, and giving each a target that
documentation and docstrings can cross-reference (:issue:`108`). The page and the
file ``tephpy config generate`` writes are two renderings of one table, so they
cannot describe different options; the generated file's comments are also wrapped
now, having overrun 88 columns (:issue:`106`). (:user:`claude`)
```

- [ ] **Step 4: Verify the fragments render**

```bash
rm -rf docs/_build docs/src/_build
pixi run --frozen docs
```

Expected: exit 0, with the `:issue:` and `:user:` extlinks resolving. Check them in the built
changelog page — an incremental build serves a stale draft, which is why the clean rebuild
matters.

- [ ] **Step 5: Lint and commit**

```bash
pixi run --frozen lint
git add changelog/
git commit -m "docs: add changelog fragments for the config housekeeping trio"
git push
```

---

## Verification Checklist

- [ ] `pixi run --frozen tests` passes.
- [ ] `pixi run --frozen lint` passes (pre-commit hooks installed — run `pre-commit install`
      first in a fresh worktree).
- [ ] `pixi run --frozen docs` passes from a clean `_build`.
- [ ] Each new test has been mutation-proved: the source broken, only that test failing, the
      source restored.
- [ ] Issues #110, #106 and #108 are each closed by a commit message in this branch.
- [ ] The spec amendment (`docs/src/developer/specs/2026-08-07-config-file-design.md`) is
      committed with the work it describes.

## Out of Scope

- **#116** — validating right-typed values against their domain (a colour that matplotlib
  will reject, an unknown cursor field). It gets its own spec; nothing here should start it.
- **Making `Config` public**, documenting the methods in full, or adding a matching reference
  page for `_constants.py` — all three recorded as rejected in configfile spec §9.
