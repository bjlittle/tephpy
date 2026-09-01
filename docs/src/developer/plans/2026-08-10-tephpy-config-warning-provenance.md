# Configuration Warning Provenance Implementation Plan

> **Point-in-time record.** This plan captures what was intended before implementation. It
> is not updated afterwards — where the implementation departed from it, the departure is
> recorded in the pull request, and the living design specification in
> [`../specs/`](../specs/) is what describes tephpy as it stands.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every `TephpyConfigWarning` name the user's own `config.load(...)` or
`import tephpy` line, instead of a frame inside `src/tephpy/` that the user cannot edit.

**Architecture:** One private helper in `_configfile.py`, `_warn_from_caller`, issues all
three configuration warnings. It passes `warnings.warn(..., skip_file_prefixes=…)` with the
tephpy package directory, so the warning lands on the first frame outside the package
however deep inside tephpy it was raised. The three existing `warnings.warn` calls — two in
`_configfile.apply`, one in `tephpy._autoload_config` — become calls to it. Nothing else
changes: not the message text, not which conditions warn rather than raise.

**Tech Stack:** Python 3.12 stdlib (`warnings`, `os.path`); pytest; `subprocess` for the
import-time seam; pixi; pre-commit.

**Spec:** `configfile spec §5.1`, in
[`../specs/2026-08-07-config-file-design.md`](../specs/2026-08-07-config-file-design.md).
Section 5 is the surrounding error-handling contract; §5.1 is this work.

**Issue:** {issue}`107`, deferred from {pull}`112`.

## Global Constraints

- **Every pixi invocation carries `--frozen`.** `pixi run --frozen tests`,
  `pixi run --frozen lint`, `pixi run --frozen docs`. Never let pixi re-solve the
  environment.
- **`skip_file_prefixes` is a Python 3.12 addition** and the project floor is
  `requires-python = ">=3.12"` (`pyproject.toml:30`), so no version guard is needed and
  none should be added.
- **Line length is 88 columns**, ruff-enforced and ruff-formatted.
- **Docstrings are numpydoc**, validated by the `numpydoc-validation` pre-commit hook over
  `^src/` only — so `src/tephpy/_configfile.py` and `src/tephpy/__init__.py` need full
  `Parameters`/`Warns` sections, while the test helpers follow the surrounding test-file
  style instead.
- **No new files under `src/`**, so no new BSD copyright headers are needed. Every file
  this plan touches already carries one.
- **`pyproject.toml:67` sets `filterwarnings = ["error"]`.** Any test that triggers a
  configuration warning in-process must catch it with `pytest.warns`, or the suite fails.
- **Stage before mutating.** Every mutation check in this plan runs `git add` first, then
  edits, then restores with `git checkout -- <path>` — which reverts from the index. An
  unstaged mutate-and-revert cycle discards the real work along with the mutation.
- **The specifications are living documents; the plans are frozen** (docs spec §3.4).
  `configfile spec §5.1` is already written and committed (`78c1f83`); this plan adds no
  further specification text, and nothing under `docs/src/developer/plans/` is edited by
  this work, including this file once its pull request merges.
- **Never write a bare `#N` or a `github.com/bjlittle/tephpy` issue URL in prose**,
  including commit-message bodies — the `check-github-references` pre-commit gate is
  `always_run`. Use the `{issue}` and `{pull}` roles.

## Why `stacklevel` cannot be made to work

Recorded here because it is the first thing a reviewer will challenge, and because getting
it wrong means shipping a second wrong number instead of no number.

`apply` is reached at four different depths — from `Config.load`, from the import-time
auto-load, from `_cli._applies`, and directly from the tests — so any single `stacklevel`
is right for one caller and wrong for the other three. The import path is worse than a
different count: the user's `import tephpy` sits behind importlib's frozen bootstrap
frames.

`skip_file_prefixes` sidesteps both. It walks outwards to the first frame whose filename
does not start with a given prefix, and CPython's `warnings` module additionally treats
importlib bootstrap frames as internal and skips them — which is why the import path lands
on the user's `import` line rather than on `<frozen importlib._bootstrap>`.

**Measured** on Python 3.12.3 with a throwaway package mirroring tephpy's call shape:

| Path | `stacklevel=2` | `skip_file_prefixes` |
|---|---|---|
| user → `load` → `apply` | the package's `load` file | the user's file |
| `import` → auto-load → `load` → `apply` | the package's `load` file | the user's `import` line |
| direct `apply` — tests, CLI | the user's file | the user's file |
| four package frames, via a shared helper | — | the user's file |

The last row is why one shared helper is affordable: the frame it adds is inside the
package and skipped like any other. The same refactor under `stacklevel` would have meant
re-counting every call site.

## The vacuous-test trap

Every warning test that exists today calls `_configfile.apply` **directly**
(`tests/test_configfile.py:98`, `:110`, `:117`). A direct call is already one frame from
the caller, which is exactly what `stacklevel=2` gets right — so those tests pass both
before and after this change and guard nothing about provenance. Every new test in this
plan therefore reaches the warning through `Config.load` or through `import tephpy`, and
every task ends by mutating the source back to `stacklevel=2` to prove the new tests
actually fail.

## File Structure

| File | Responsibility after this change |
|---|---|
| `src/tephpy/_configfile.py` | Adds `_PACKAGE_ROOT` and `_warn_from_caller`; `apply`'s two warn sites call it. The module already "owns everything about the file", so owning *how* it warns about the file belongs here. |
| `src/tephpy/__init__.py` | `_autoload_config` calls `_warn_from_caller` instead of `warnings.warn`; keeps its local `warnings` import for `catch_warnings`. |
| `src/tephpy/_cli.py` | Unchanged behaviour. `_applies`' docstring gains the `configfile spec §5.1` citation, so its blanket suppression reads as decided rather than overlooked. |
| `tests/test_configfile.py` | Adds the in-process provenance test, reached through `tephpy.config.load`. |
| `tests/test_config_autoload.py` | Adds `_run_file`, a sibling of `_run` that runs the probe from a real file so the warning has a filename to point at, and two provenance tests over it. |
| `changelog/<PR>.bugfix.rst` | New fragment. |

---

### Task 1: The helper and the two `apply` warn sites

**Files:**
- Modify: `src/tephpy/_configfile.py` (add before `apply` at `:236`; rewrite `:280-285`
  and `:294-298`)
- Test: `tests/test_configfile.py` (add after `test_an_unknown_option_warns_and_is_skipped`
  at `:115-119`)

**Interfaces:**
- Consumes: `warnings`, `os`, `Final` and `TephpyConfigWarning` — all four are already
  imported by `_configfile.py` at `:17`, `:20`, `:21`, `:27`. Add no imports.
- Produces: `_warn_from_caller(message: str) -> None` and
  `_PACKAGE_ROOT: Final[str]`, both module-private in `tephpy._configfile`. Task 2 imports
  `_warn_from_caller`. Neither goes in `__all__` — that list is the module's public
  surface, and these are not part of it.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_configfile.py`, immediately after
`test_an_unknown_option_warns_and_is_skipped`:

```python
def test_a_warning_blames_the_caller_not_tephpy(tmp_path):
    """The user's file is at fault, so the user's own frame is what is named.

    Reached through ``Config.load`` rather than through ``apply`` on
    purpose. A direct ``apply`` call is already one frame from the caller,
    which is what ``stacklevel=2`` gets right, so a test written that way
    passes whatever the warning does and guards nothing
    (configfile spec §5.1).
    """
    path = _write(tmp_path, "isotherms:\n  colour: purple\n")
    with pytest.warns(TephpyConfigWarning, match="colour") as record:
        tephpy.config.load(path)
    assert record[0].filename == __file__
```

`_write`, `tephpy`, `pytest` and `TephpyConfigWarning` are all already in this module
(`:74-77`, `:11`, `:13`, `:15`). The autouse `_pristine_config` fixture in
`tests/conftest.py:36` resets `tephpy.config` around the test, so loading into the global
configuration is safe.

- [ ] **Step 2: Run the test and confirm it fails for the right reason**

```bash
pixi run --frozen tests tests/test_configfile.py::test_a_warning_blames_the_caller_not_tephpy -v
```

Expected: FAIL on the final assertion, with the recorded filename ending in
`src/tephpy/_config.py` — the intermediate frame `stacklevel=2` blames. If it fails
anywhere earlier, stop and diagnose: the test is not yet measuring what it claims to.

- [ ] **Step 3: Add the constant and the helper**

In `src/tephpy/_configfile.py`, insert immediately above `def apply(` at `:236`:

```python
#: Every file in the tephpy package, with the trailing separator that stops
#: the prefix also matching a sibling ``tephpy_extras`` — matching is a plain
#: string compare (configfile spec §5.1).
_PACKAGE_ROOT: Final[str] = os.path.dirname(__file__) + os.sep


def _warn_from_caller(message: str) -> None:
    """Warn about the configuration file, blaming the user's own frame.

    ``skip_file_prefixes`` walks outwards to the first frame outside the
    tephpy package, so the warning names the user's ``config.load(...)`` or
    ``import tephpy`` line however deep inside tephpy it was raised.
    ``stacklevel`` cannot: ``apply`` is reached at four different depths,
    and the import path sits behind importlib's frozen bootstrap frames,
    which no fixed count reaches (configfile spec §5.1).

    Parameters
    ----------
    message : str
        The warning text.

    Warns
    -----
    TephpyConfigWarning
        Always. The caller has already decided the situation warrants it.
    """
    warnings.warn(message, TephpyConfigWarning, skip_file_prefixes=(_PACKAGE_ROOT,))
```

`os.path.dirname(__file__)` is applied once, not twice: `_configfile.py` sits directly in
`src/tephpy/`, so one call already gives the package directory.

- [ ] **Step 4: Route both `apply` warn sites through it**

Replace `src/tephpy/_configfile.py:279-299` (the body of the `for option, value` loop up to
and including the second `continue`) with:

```python
if option not in valid:
    _warn_from_caller(
        f"ignoring unknown option {option!r} in configuration "
        f"section {name!r}; expected one of {sorted(valid)}"
    )
    continue
if value is None:
    hint = (
        "; an unquoted '#' colour is read as a comment, so quote "
        "it as '#b0b0b0' if that is what happened"
        if option in _COLOR_OPTIONS
        else ""
    )
    _warn_from_caller(f"ignoring {name}.{option}, whose value is null{hint}")
    continue
```

Both message strings are unchanged, character for character. `apply`'s own docstring is
unchanged too: its `Warns` section already says what it warns about, and that is still
true.

- [ ] **Step 5: Run the test and confirm it passes**

```bash
pixi run --frozen tests tests/test_configfile.py -v
```

Expected: PASS, including all pre-existing tests in the file.

- [ ] **Step 6: Stage, then mutate to prove the test guards the fix**

```bash
git add src/tephpy/_configfile.py tests/test_configfile.py
```

In `_warn_from_caller`, replace `skip_file_prefixes=(_PACKAGE_ROOT,)` with `stacklevel=2`,
then:

```bash
pixi run --frozen tests tests/test_configfile.py -v
```

Expected: exactly one failure — `test_a_warning_blames_the_caller_not_tephpy`. Every
pre-existing test in the file still passes, which is the point: they were never guarding
this. Restore:

```bash
git checkout -- src/tephpy/_configfile.py
```

- [ ] **Step 7: Lint and commit**

```bash
pixi run --frozen lint
git commit -m "Blame the caller for configuration-file warnings

Both warnings in \`_configfile.apply\` reported \`_config.py\` — tephpy's
own code — because \`stacklevel=2\` counts a fixed number of frames and
\`apply\` is reached at four different depths. They now route through
\`_warn_from_caller\`, which passes \`skip_file_prefixes\` and so lands on
the first frame outside the package (configfile spec §5.1).

The existing warning tests call \`apply\` directly, one frame from the
caller, which is what \`stacklevel=2\` gets right — so they pass either
way. The new test goes through \`config.load\`.

Part of {issue}\`107\`."
```

---

### Task 2: The import-time warn site and its probe

**Files:**
- Modify: `src/tephpy/__init__.py` (imports at `:18-20`; docstring at `:51-52`; warn site at
  `:62-66`)
- Test: `tests/test_config_autoload.py` (refactor `_run` at `:31-55`; add `_run_file` and
  two tests)

**Interfaces:**
- Consumes: `tephpy._configfile._warn_from_caller`, from Task 1.
- Produces: `_environ(tmp_path, **env_extra) -> dict[str, str]` and
  `_run_file(tmp_path, **env_extra) -> tuple[Path, subprocess.CompletedProcess]` in
  `tests/test_config_autoload.py`. `_run`'s signature and return value are unchanged, so
  the eight existing tests that call it need no edit.

**Why a file and not `-c`.** `_run` runs the probe with `python -c`, which gives every
frame in it the filename `<string>`. That is not a filename a warning can usefully point
at, and it is not distinguishable from a tephpy frame for the purpose of these assertions.
A script on disk gives the `import tephpy` line a real path and line number.

- [ ] **Step 1: Split the environment out of `_run`**

In `tests/test_config_autoload.py`, replace `_run` at `:31-55` with:

```python
def _environ(tmp_path, **env_extra):
    """Build the controlled environment both probes run under.

    ``HOME`` and ``XDG_CONFIG_HOME`` both move, which empties the user
    configuration directory on linux — where CI runs — and on macOS.
    Windows resolves it from ``%LOCALAPPDATA%``, which neither variable
    touches, so a developer running these there with a user configuration
    file of their own would still see it. ``MPLCONFIGDIR`` keeps pointing
    at this process's matplotlib cache, so the relocated ``HOME`` does not
    trigger a font-cache rebuild.
    """
    env = dict(os.environ)
    env.pop("TEPHPYRC", None)
    env["HOME"] = str(tmp_path)
    env["XDG_CONFIG_HOME"] = str(tmp_path / "config")
    env["MPLCONFIGDIR"] = mpl.get_configdir()
    env.update(env_extra)
    return env


def _run(tmp_path, **env_extra):
    """Import tephpy in a fresh interpreter under a controlled environment."""
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", PROBE],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
        env=_environ(tmp_path, **env_extra),
    )


def _run_file(tmp_path, **env_extra):
    """Run the same probe from a real file, and return the file with the result.

    ``-c`` gives every frame the filename ``<string>``, which is no use to
    a test about which file a warning points at. A script on disk gives the
    ``import tephpy`` line a path and a line number — line 2, after the
    leading blank ``textwrap.dedent`` preserves (configfile spec §5.1).
    """
    probe = tmp_path / "probe.py"
    probe.write_text(PROBE, encoding="utf-8")
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(probe)],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
        env=_environ(tmp_path, **env_extra),
    )
    return probe, result
```

Add `from pathlib import Path` and `import tephpy` to the module's imports at `:12-19` —
`Path` for the package-directory assertion, `tephpy` to locate that directory. Both go in
the positions ruff's isort ordering requires: `pathlib` among the stdlib block, `tephpy`
in a first-party block after `matplotlib`.

- [ ] **Step 2: Confirm the refactor changed nothing**

```bash
pixi run --frozen tests tests/test_config_autoload.py -v
```

Expected: all eight existing tests PASS. This step exists so that a failure in Step 4 is
unambiguously about provenance and not about the refactor.

- [ ] **Step 3: Write the two failing tests**

Append to `tests/test_config_autoload.py`:

```python
def test_a_typo_blames_the_users_import_line(tmp_path):
    """The deepest warn site: ``apply``, four frames inside tephpy.

    ``stacklevel`` has nothing to aim at here. The user's frame is the
    ``import`` statement, and it sits behind importlib's frozen bootstrap
    frames (configfile spec §5.1).
    """
    typo = tmp_path / "typo.yaml"
    typo.write_text("isotherms:\n  colour: purple\n", encoding="utf-8")
    probe, result = _run_file(tmp_path, TEPHPYRC=str(typo))
    assert f"{probe}:2:" in result.stderr
    assert str(Path(tephpy.__file__).parent) not in result.stderr


def test_an_unreadable_file_blames_the_users_import_line(tmp_path):
    """The other warn site: the ``except`` clause in ``_autoload_config``.

    A typo'd key warns from inside ``apply``; a file that cannot be parsed
    at all never reaches it and warns from the handler instead. Two sites,
    so two tests — one would leave the other free to regress.
    """
    broken = tmp_path / "broken.yaml"
    broken.write_text("isotherms:\n  color: [unclosed\n", encoding="utf-8")
    probe, result = _run_file(tmp_path, TEPHPYRC=str(broken))
    assert f"{probe}:2:" in result.stderr
    assert str(Path(tephpy.__file__).parent) not in result.stderr
```

The second assertion in each is the sharper half: it fails for *any* tephpy frame, not just
the one `stacklevel=2` happens to pick today.

- [ ] **Step 4: Run them and confirm both fail for the right reason**

```bash
pixi run --frozen tests tests/test_config_autoload.py -v
```

Expected: both new tests FAIL. `test_a_typo_blames_the_users_import_line` reports a
`src/tephpy/_config.py` line in stderr; `test_an_unreadable_file_blames_the_users_import_line`
reports a `src/tephpy/__init__.py` line. Two different tephpy files, which is the four-depths
problem made visible.

- [ ] **Step 5: Route the import-time warn site through the helper**

In `src/tephpy/__init__.py`, add the import after `from tephpy._config import config` at
`:19`:

```python
from tephpy._configfile import _warn_from_caller
```

Module level, not inside the function: `_configfile` is already imported transitively by
`tephpy._config`, so this costs nothing, and the underscore keeps `_warn_from_caller` off
the public surface — which is the concern the local `import warnings` at `:54` exists to
address, and it does not apply here.

Then replace the warn site at `:62-66`:

```python
        try:
            config.load()
        except exceptions.TephpyConfigError as exc:
            config.reset()
            _warn_from_caller(f"ignoring the configuration file: {exc}")
```

Keep the local `import warnings` at `:54`: `catch_warnings` and `filterwarnings` still need
it.

- [ ] **Step 6: Correct `_autoload_config`'s docstring**

Its `Notes` section at `:51-52` reads "It has to span the ``warnings.warn`` below as well as
``config.load``". There is no longer a `warnings.warn` below. Replace those two lines with:

```
    every other warning category on the user's own setting. It has to span
    the ``_warn_from_caller`` call below as well as ``config.load``: that
    call is on the very failure path this function exists to survive.
```

- [ ] **Step 7: Run the tests and confirm they pass**

```bash
pixi run --frozen tests tests/test_config_autoload.py -v
```

Expected: all ten tests PASS.

- [ ] **Step 8: Stage, then mutate each site in turn**

```bash
git add src/tephpy/__init__.py tests/test_config_autoload.py
```

Mutation A — put the inline warn back in `src/tephpy/__init__.py`:

```python
            warnings.warn(
                f"ignoring the configuration file: {exc}",
                exceptions.TephpyConfigWarning,
                stacklevel=2,
            )
```

```bash
pixi run --frozen tests tests/test_config_autoload.py -v
git checkout -- src/tephpy/__init__.py
```

Expected: exactly `test_an_unreadable_file_blames_the_users_import_line` fails;
`test_a_typo_blames_the_users_import_line` still passes, because it exercises the other
site.

Mutation B — in `src/tephpy/_configfile.py`, replace
`skip_file_prefixes=(_PACKAGE_ROOT,)` with `stacklevel=2`:

```bash
pixi run --frozen tests tests/test_config_autoload.py -v
git checkout -- src/tephpy/_configfile.py
```

Expected: exactly `test_a_typo_blames_the_users_import_line` fails.

Two mutations, two disjoint failures: each test guards its own warn site.

- [ ] **Step 9: Run the whole suite, lint, and commit**

```bash
pixi run --frozen tests
pixi run --frozen lint
git commit -m "Blame the caller for the auto-load warning too

The import-time failure path warned with \`stacklevel=2\`, which lands on
\`tephpy/__init__.py\` — the module-level \`_autoload_config()\` call.
The user's frame is their \`import tephpy\` statement, behind importlib's
frozen bootstrap frames, so no fixed count reaches it; \`_warn_from_caller\`
does, because CPython's warnings machinery skips those frames as internal.

The probe now runs from a file rather than \`python -c\`, which gave every
frame the filename \`<string>\`.

Closes {issue}\`107\`."
```

---

### Task 3: The CLI citation, the changelog fragment, and full verification

**Files:**
- Modify: `src/tephpy/_cli.py:53-56` (docstring only)
- Create: `changelog/<PR>.bugfix.rst`

**Interfaces:**
- Consumes: nothing new. `_applies` keeps calling `_configfile.apply`, and the warnings it
  provokes keep being suppressed.
- Produces: nothing other tasks depend on. This is the task that makes the change
  reviewable and releasable.

**Why `_applies` is not changed.** It is the one caller with no user frame worth blaming:
the call originates in tephpy's own CLI, against a file the user asked to *locate* rather
than to load, and `import tephpy` has already warned over the same cascade. Its blanket
`simplefilter("ignore", TephpyConfigWarning)` is therefore correct as it stands — the
citation is what stops a later reader from mistaking it for an oversight.

- [ ] **Step 1: Cite the specification in `_applies`**

In `src/tephpy/_cli.py`, extend the `Returns` description at `:53-56`, which currently
ends "importing tephpy has already issued them, over the same cascade and the same file.":

```
    Returns
    -------
    bool
        Whether applying it to a throwaway configuration succeeds. The
        warnings it may emit along the way are not this command's to
        repeat: importing tephpy has already issued them, over the same
        cascade and the same file. Suppressing them wholesale is why this
        is the one caller with no frame worth blaming
        (configfile spec §5.1).
    """
```

- [ ] **Step 2: Open the pull request and read its number**

The fragment is named for the pull request, and an issue filed in the meantime takes the
next number — so the number must be read from the open pull request, never guessed from
the current maximum.

```bash
git push -u origin fix/config-warning-provenance
gh pr create --fill --draft
gh pr view --json number --jq .number
```

Call that number `N` in the next step.

- [ ] **Step 3: Write the changelog fragment**

Create `changelog/N.bugfix.rst` (with `N` substituted):

```rst
Fixed the configuration-file warnings blaming a file inside ``tephpy`` rather than
the code that triggered them (:issue:`107`). An unknown option, a null option
value, and an unreadable configuration file each reported a tephpy frame the
reader cannot act on; they now name your own ``tephpy.config.load`` call, or the
``import tephpy`` that ran the auto-load. Code suppressing these by module —
``filterwarnings(..., module="tephpy")`` — no longer matches as a result, and
should filter on the :exc:`~tephpy.exceptions.TephpyConfigWarning` category
instead, which is unaffected. (:user:`claude`)
```

`tephpy.config.load` stays in double backticks rather than a cross-reference: `Config`
lives in the private `_config` module, which autoapi does not document, so there is no
target to link — the same choice `docs/src/howtos/configuration.rst:108` already makes.

- [ ] **Step 4: Verify the fragment renders**

```bash
pixi run --frozen docs
```

Expected: `build succeeded`, no warnings. Then confirm the entry and its two links landed:

```bash
grep -o "issues/107\|TephpyConfigWarning\|github.com/claude" docs/_build/html/reference/changelog.html | sort | uniq -c
```

Expected: all three present. A clean build is the point — an incremental one serves a stale
draft of the changelog page.

- [ ] **Step 5: Full verification**

```bash
pixi run --frozen tests
pixi run --frozen lint
```

Expected: the whole suite passes, and every pre-commit hook passes — including
`design specification citations resolve`, which is what checks that the six new
`configfile spec §5.1` citations — two in `_configfile.py`, one in `_cli.py`, one in
`tests/test_configfile.py`, two in `tests/test_config_autoload.py` — resolve to the
`(configfile-spec-5-1)=` anchor. The gate derives the slug by replacing the dot, so
`§5.1` and `configfile-spec-5-1` are the matching pair.

- [ ] **Step 6: Commit and mark the pull request ready**

```bash
git add src/tephpy/_cli.py changelog/
git commit -m "Add the changelog fragment and cite the specification

Records why \`_cli._applies\` is the one caller that suppresses these
warnings outright rather than re-aiming them (configfile spec §5.1).

Part of {issue}\`107\`."
git push
gh pr ready
```

---

## Self-review

**Spec coverage.** `configfile spec §5.1` makes six claims. Each has a task:

| §5.1 claim | Where |
|---|---|
| One helper issues every configuration warning | Task 1 Steps 3-4, Task 2 Step 5 |
| `skip_file_prefixes`, not `stacklevel` | Task 1 Step 3 |
| The prefix carries a trailing `os.sep` | Task 1 Step 3, and its `#:` comment |
| A shared helper costs nothing | Task 1 Step 3 (the helper), proven by Task 2's tests passing through it |
| `_cli._applies`' suppression is deliberate | Task 3 Step 1 |
| `module=` filtering stops matching | Task 3 Step 3, the changelog fragment |

**Placeholders.** `N` in Task 3 is a value the plan says exactly how to obtain (Step 2),
not an unresolved decision. No other step defers content.

**Type consistency.** `_warn_from_caller(message: str) -> None` is defined once (Task 1
Step 3) and called with a single positional string at all three sites (Task 1 Step 4, Task
2 Step 5). `_environ` returns the dict `_run` and `_run_file` both pass as `env=`.
`_run_file` returns `(probe, result)` and both new tests unpack it that way. `_run`'s
signature is untouched, so the eight existing callers are unaffected.
