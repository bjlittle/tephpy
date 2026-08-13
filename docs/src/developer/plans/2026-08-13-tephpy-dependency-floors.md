# Dependency Floors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A weekly `ci-floors` workflow resolves every dependency minimum tephpy declares,
exercises what it resolves, and — where a floor is broken — attributes the failure to one
package, finds the lowest version that works, and files an issue carrying the diagnosis,
closing the gap {issue}`109` named.

**Architecture:** A generator (`.github/scripts/floors.py`) reads the four pixi dependency
tables, resolves each `>=X` to the lowest release conda-forge carries *with a build for the
pinned Python*, and rewrites the manifest in the CI checkout to `==` those versions. One
manifest per tier, each declaring exactly one pixi environment, because pixi solves every
environment a manifest declares and a shared manifest would let one tier's conflict mask the
others. The PyPI half needs no generator: `uv pip install --resolution lowest-direct` reads
the floors straight from `requirements/*.txt`. On failure a diagnosis script attributes by
relaxation, scans upward for the lowest passing version, and writes an artifact; one final
job with `issues: write` turns artifacts into issues.

**Tech Stack:** Python 3.12, `packaging`, `tomllib`, pixi (`pixi search`, `pixi exec`,
`pixi install`), `uv`, GitHub Actions, `gh` CLI, pytest.

## Global Constraints

- **The specification is floors spec** —
  `docs/src/developer/specs/2026-08-13-dependency-floors-design.md`. Cite it in code, tests
  and workflow comments as `floors spec §N`. A bare `spec §N` means the parent
  specification; `configfile spec §N` and `docs spec §N` are siblings. The prefix is
  load-bearing and a pre-commit hook checks the anchors resolve.
- **Python is 3.12 throughout** — the SPEC 0 lower bound (floors spec §3.3). Never the
  newest supported Python.
- **Only the four tables of floors spec §3.1 are pinned:** `[tool.pixi.dependencies]`,
  `[tool.pixi.feature.{test,docs,devs}.dependencies]`. The `pip = ">=25.0"` floor in each
  `py3NN` feature is deliberately left alone — it floors the interpreter feature, not a
  tephpy dependency tier.
- **Every source file carries the BSD copyright header** (ruff `CPY001`). Copy the five-line
  header from `.github/scripts/check_citations.py`, `#!/usr/bin/env python3` included.
- **Line width is 88 columns**, enforced by ruff over `.github/scripts/*.py` as well as
  `src/`.
- **`.github/scripts/*.py` may `print` and take boolean positional arguments** (`T201`,
  `FBT001` are ignored there) but every other `ALL` rule applies: docstrings on every
  function, `from __future__ import annotations` first, annotated signatures. The
  numpydoc-validation hook is scoped to `^src/` and does **not** see these scripts.
- **Tests mirror the `src/tephpy` package layout**, and gate-script tests sit at the top of
  `tests/`: `tests/test_floors.py`, beside `tests/test_citations.py`.
- **A test that loads `.github/scripts` must guard the module, not the test.** `MANIFEST.in`
  prunes `.github/`, so an unguarded import fails *collection* on an unpacked sdist and
  takes the whole suite with it. Copy the `pytestmark`/`_load` pattern from
  `tests/test_citations.py` verbatim.
- **pytest runs with `filterwarnings = ["error"]`.**
- **Every command runs through pixi with `--frozen`:** `pixi run --frozen tests`,
  `pixi run --frozen lint`, `pixi run --frozen docs`. Bare `python` is not on `PATH`.
- **`pre-commit install` before the first commit** — hooks are not installed in a fresh
  worktree, and `pixi run --frozen lint` cannot see untracked files, so `git add` new files
  before linting them.
- **Workflow files must pass `actionlint` and `zizmor`.** Every action is pinned to a full
  commit SHA with a trailing `# vX.Y.Z` comment, `permissions: {}` sits at workflow level,
  and every `actions/checkout` sets `persist-credentials: false`.
- **Never `cd` out of this worktree.** All paths below are relative to the worktree root.
- **Never use bare `git stash` / `git stash pop`** — the stash stack is shared across
  worktrees.

---

## File Structure

**Created:**

- `.github/scripts/floors.py` — reads the manifest, resolves floors to pins, rewrites the
  manifest for one tier. Pure functions plus a thin CLI; the only thing that touches the
  network is `candidates`, which is injectable so the tests never reach it.
- `.github/scripts/floors_diagnose.py` — the failure path: attribution by relaxation
  (floors spec §3.4), the upward scan (floors spec §3.5), and the finding artifact. Imports
  `floors` by path.
- `.github/scripts/floors_issue.py` — turns finding artifacts into issue bodies and dedupes
  against open marker-labelled issues (floors spec §3.6).
- `.github/workflows/ci-floors.yml` — the weekly job.
- `tests/test_floors.py` — the generator's tests, guards first.
- `tests/test_floors_issue.py` — the issue body and the dedupe key.
- `changelog/<PR>.internal.rst`.

**Modified:**

- `pyproject.toml` — `packaging` joins `[tool.pixi.feature.devs.dependencies]`, and
  `python-build` moves from there to `[tool.pixi.feature.test.dependencies]`.
- `requirements/pypi-optional-devs.txt` — the same floors, the other declaration site.
- `requirements/pypi-optional-test.txt` — `build` arrives here, matching the move.
- `docs/src/developer/specs/2026-08-13-dependency-floors-design.md` — the **Status** line
  stops saying "specifies work not yet implemented".
- `docs/src/developer/specs/2026-07-22-tephpy-design.md` — §8.7 moves `ci-floors` out of the
  fast-follow list.

**Not created, deliberately:** no pixi task for the floors run. Every existing task passes
`--frozen`; a task that must not would be the one exception in the table, and the job's
manifest does not exist outside CI anyway.

---

### Task 1: The Pin Generator

The whole job rests on turning `>=X` into a version conda-forge actually carries for
Python 3.12. Three facts make that non-obvious, and all three are measured
(floors spec §3.2): most declared floors are not releases; the lowest release is often not
built for 3.12; and version order is PEP 440, not string order.

**Files:**
- Create: `.github/scripts/floors.py`
- Create: `tests/test_floors.py`
- Modify: `pyproject.toml` (the `devs` and `test` dependency tables)
- Modify: `requirements/pypi-optional-devs.txt`
- Modify: `requirements/pypi-optional-test.txt`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `FloorError(Exception)`
  - `TABLES: dict[str, tuple[str, ...]]`, `HEADERS: dict[str, str]`, `ENVIRONMENTS: str`
  - `admits(depends: list[str], python: Version) -> bool`
  - `candidates(package: str, specifier: str, python: Version) -> list[str]`
  - `pins(manifest: Path, python: Version, lookup: Lookup = candidates) -> Resolved`
    where `Resolved = dict[str, dict[str, tuple[str, str]]]`, tier → package →
    (declared, resolved)
  - `rewrite(text: str, resolved: Resolved, relax: str | None = None) -> str`
  - `environments(text: str, tier: str, python: str) -> str`

- [ ] **Step 1: Declare `packaging`, and move `build` to the test tier**

Two declaration changes, both in service of the tiers §3.3 generates.

`packaging` orders versions. It arrives today only as a matplotlib transitive, which is not
a declaration.

`python-build` moves the other way, out of `devs` and into `test`. Its only consumer in the
repository is `tests/plotting/test_logo.py::test_masters_ship_in_the_wheel`, which shells out
to `python -m build`; the wheel workflow uses `pipx run build` and needs nothing from the
environment. Today every committed environment pairs `test` with `devs`, so the test suite's
need for it has never had to be stated — but the generated `core + test` of §3.3 carries no
`devs`, and there that test fails on every run, with no package floor behind it for §3.4 to
find. This is the same reasoning that put `nbformat` in the `test` table ({issue}`95`).

In `pyproject.toml`, keeping both tables alphabetical:

```toml
[tool.pixi.feature.devs.dependencies]
check-manifest = ">=0.49"
mypy = ">=1.13"
packaging = ">=24.0"
pre-commit = ">=4.0"
ruff = ">=0.15"
zizmor = ">=1.9.0"
```

and, in `[tool.pixi.feature.test.dependencies]`, after `pytest-mpl`:

```toml
python-build = ">=1.5"
```

And in `requirements/pypi-optional-devs.txt`, likewise alphabetical, with `build` gone:

```text
check-manifest>=0.49
mypy>=1.13
packaging>=24.0
pre-commit>=4.0
ruff>=0.15
zizmor>=1.9
```

with it landing in `requirements/pypi-optional-test.txt`:

```text
build>=1.5
hypothesis>=6.100
nbformat>=5.10
pytest>=8.0
pytest-cov>=5.0
pytest-mpl>=0.17
```

Then refresh the lockfile — this is the one place in this plan where a solve is expected:

Run: `pixi install`
Expected: succeeds, `pixi.lock` changes.

Confirm the move did not strand the logo test, which is the whole point of making it:

Run: `pixi run --frozen --environment test-py312 pytest tests/plotting/test_logo.py -q`
Expected: passes.

- [ ] **Step 2: Write the failing guard tests**

Both guards fail the run rather than degrade it, and neither is reached by a green run —
which is exactly why they are the tests floors spec §5 asks for. `lookup` is injected so no
test touches the network.

Create `tests/test_floors.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the dependency floor generator (floors spec §5)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import textwrap

from packaging.version import Version
import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "floors.py"

pytestmark = pytest.mark.skipif(
    not (SCRIPT.is_file() and (REPO / ".git").exists()),
    reason="not a git checkout of the repository",
)


def _load():
    """Import the generator by path; ``.github`` is not an importable package."""
    spec = importlib.util.spec_from_file_location("floors", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["floors"] = module
    spec.loader.exec_module(module)
    return module


MANIFEST = textwrap.dedent(
    """\
    [tool.pixi.dependencies]
    click = ">=8.1"

    [tool.pixi.feature.test.dependencies]
    pytest = ">=8.0"

    [tool.pixi.feature.docs.dependencies]
    sphinx = ">=8.0"

    [tool.pixi.feature.devs.dependencies]
    ruff = ">=0.15"
    """
)


def _manifest(tmp_path, text=MANIFEST):
    path = tmp_path / "pyproject.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _lookup(package, specifier, python):  # noqa: ARG001
    """Stand in for the channel: the floor plus two releases above it."""
    base = specifier.removeprefix(">=")
    return [f"{base}.0", f"{base}.1", f"{base}.2"]


def test_a_specifier_that_is_not_a_bare_floor_is_reported(tmp_path):
    floors = _load()
    text = MANIFEST.replace('click = ">=8.1"', 'click = ">=8.1,<9"')
    with pytest.raises(floors.FloorError, match="not a bare"):
        floors.pins(_manifest(tmp_path, text), Version("3.12.0"), lookup=_lookup)


def test_a_tier_that_converts_nothing_fails(tmp_path):
    floors = _load()
    text = MANIFEST.replace('sphinx = ">=8.0"', "")
    with pytest.raises(floors.FloorError, match="docs: no floors converted"):
        floors.pins(_manifest(tmp_path, text), Version("3.12.0"), lookup=_lookup)


def test_a_floor_with_no_build_for_the_python_fails(tmp_path):
    floors = _load()
    with pytest.raises(floors.FloorError, match="no build for Python"):
        floors.pins(
            _manifest(tmp_path),
            Version("3.12.0"),
            lookup=lambda package, specifier, python: [],  # noqa: ARG005
        )
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_floors.py -v`
Expected: three failures, each `FileNotFoundError` or a collection skip — the script does
not exist yet.

- [ ] **Step 4: Write the generator**

Create `.github/scripts/floors.py`. The `admits` and `candidates` bodies below are the
measured ones: without the `depends` filter, `click >=8.1` resolves to 8.1.0, whose
conda-forge builds stop at Python 3.10, and the run then fails on the generator's own
arithmetic rather than on anything tephpy declared.

```python
#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Resolve tephpy's declared dependency floors to pins (floors spec §3.2).

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
from typing import TYPE_CHECKING

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from collections.abc import Callable

    Lookup = Callable[[str, str, Version], list[str]]
    Resolved = dict[str, dict[str, tuple[str, str]]]

#: The four dependency tables of floors spec §3.1, by tier.
TABLES: dict[str, tuple[str, ...]] = {
    "core": ("tool", "pixi", "dependencies"),
    "test": ("tool", "pixi", "feature", "test", "dependencies"),
    "docs": ("tool", "pixi", "feature", "docs", "dependencies"),
    "devs": ("tool", "pixi", "feature", "devs", "dependencies"),
}

#: The same four tables as they appear as manifest headers.
HEADERS: dict[str, str] = {
    "core": "[tool.pixi.dependencies]",
    "test": "[tool.pixi.feature.test.dependencies]",
    "docs": "[tool.pixi.feature.docs.dependencies]",
    "devs": "[tool.pixi.feature.devs.dependencies]",
}

ENVIRONMENTS = "[tool.pixi.environments]"

FLOOR = re.compile(r"^>=(?P<version>[0-9][0-9a-zA-Z.*+!-]*)$")
DECLARATION = re.compile(r'^(?P<name>[A-Za-z0-9._-]+) = "(?P<specifier>[^"]+)"$')


class FloorError(Exception):
    """A declaration the generator will not guess at."""


def tool(name: str) -> str:
    """Resolve an executable off ``PATH`` to an absolute path.

    Every ``subprocess`` call in this job passes a fixed argv whose first
    element came from here, which is what makes the ``S603`` waivers below
    honest: nothing user-supplied reaches the shell, and no partial path is
    resolved at spawn time.

    Parameters
    ----------
    name : str
        The executable to find.

    Returns
    -------
    str
        Its absolute path.

    Raises
    ------
    FloorError
        If the executable is not on ``PATH``.

    """
    found = shutil.which(name)
    if found is None:
        msg = f"{name} is not on PATH"
        raise FloorError(msg)
    return found


def admits(depends: list[str], python: Version) -> bool:
    """Whether a build's ``python`` constraint admits the wanted interpreter.

    Parameters
    ----------
    depends : list of str
        The build's ``depends`` entries, as conda-forge writes them.
    python : Version
        The interpreter the floors are being resolved against.

    Returns
    -------
    bool
        True when the build declares no ``python`` constraint, or one that
        contains ``python``.

    """
    for entry in depends:
        parts = entry.split(maxsplit=1)
        if parts[0] != "python":
            continue
        if len(parts) == 1:
            return True
        try:
            spec = SpecifierSet(
                ",".join(
                    piece if piece[0] in "<>=!~" else f"=={piece}"
                    for piece in parts[1].replace(" ", "").split(",")
                )
            )
        except InvalidSpecifier:
            return True
        return spec.contains(python, prereleases=True)
    return True


def candidates(package: str, specifier: str, python: Version) -> list[str]:
    """Every release satisfying ``specifier`` with a build for ``python``.

    Parameters
    ----------
    package : str
        The conda package name.
    specifier : str
        A conda matchspec suffix, such as ``>=8.1``.
    python : Version
        The interpreter the floors are being resolved against.

    Returns
    -------
    list of str
        Version strings in ascending PEP 440 order, lowest first.

    """
    command = [
        tool("pixi"),
        "search",
        f"{package}{specifier}",
        "--platform",
        "linux-64",
        "--json",
    ]
    out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        command, capture_output=True, text=True, check=True
    ).stdout
    # `pixi search` prints "Using channels: ..." before the JSON document.
    document = json.loads(out[out.index("{") :])
    keep: dict[str, Version] = {}
    for entries in document.values():
        for entry in entries:
            if entry["name"] != package:
                continue
            if not admits(entry.get("depends", []), python):
                continue
            try:
                keep[entry["version"]] = Version(entry["version"])
            except InvalidVersion:
                continue
    return [text for text, _ in sorted(keep.items(), key=lambda item: item[1])]


def pins(manifest: Path, python: Version, lookup: Lookup = candidates) -> Resolved:
    """Resolve every declared floor to a release the channel carries.

    Parameters
    ----------
    manifest : Path
        The ``pyproject.toml`` to read.
    python : Version
        The interpreter the floors are being resolved against.
    lookup : callable, optional
        The candidate source; defaults to :func:`candidates`.

    Returns
    -------
    dict
        Tier to package to ``(declared, resolved)``.

    Raises
    ------
    FloorError
        If a specifier is not a bare ``>=``, if a floor has no build for
        ``python``, or if a tier converts nothing.

    """
    document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    resolved: Resolved = {}
    for tier, path in TABLES.items():
        node: object = document
        for key in path:
            node = node.get(key, {}) if isinstance(node, dict) else {}
        table: dict[str, tuple[str, str]] = {}
        for package, specifier in sorted(dict(node).items()):  # type: ignore[arg-type]
            if not isinstance(specifier, str) or not FLOOR.match(specifier):
                msg = (
                    f"{tier}: {package} = {specifier!r} is not a bare '>=' floor; "
                    "the generator cannot know which release it floors "
                    "(floors spec §3.2)"
                )
                raise FloorError(msg)
            found = lookup(package, specifier, python)
            if not found:
                msg = (
                    f"{tier}: {package}{specifier} has no build for Python "
                    f"{python} on linux-64 (floors spec §3.2)"
                )
                raise FloorError(msg)
            table[package] = (specifier, found[0])
        if not table:
            msg = f"{tier}: no floors converted; the table is empty or renamed"
            raise FloorError(msg)
        resolved[tier] = table
    return resolved


def rewrite(text: str, resolved: Resolved, relax: str | None = None) -> str:
    """Replace each declared floor with its resolved pin.

    Parameters
    ----------
    text : str
        The manifest source.
    resolved : dict
        The mapping :func:`pins` returned.
    relax : str, optional
        A package left at its declared ``>=`` floor (floors spec §3.4).

    Returns
    -------
    str
        The rewritten manifest source.

    """
    tiers = {header: tier for tier, header in HEADERS.items()}
    out: list[str] = []
    tier: str | None = None
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("["):
            tier = tiers.get(stripped)
        if tier is not None:
            match = DECLARATION.match(stripped)
            if match is not None and match["name"] in resolved[tier]:
                package = match["name"]
                if package != relax:
                    _, pin = resolved[tier][package]
                    out.append(f'{package} = "=={pin}"\n')
                    continue
        out.append(line)
    return "".join(out)


def environments(text: str, tier: str, python: str) -> str:
    """Replace the environment table with the one this tier needs.

    pixi solves every environment a manifest declares, so a manifest carrying
    all of them would let one tier's conflict block another (floors spec §3.3).

    Parameters
    ----------
    text : str
        The manifest source.
    tier : str
        One of ``test``, ``docs``, ``devs``.
    python : str
        The interpreter minor version, such as ``3.12``.

    Returns
    -------
    str
        The rewritten manifest source.

    Raises
    ------
    FloorError
        If the manifest declares no environment table.

    """
    tag = python.replace(".", "")
    name = f"floors-{tier}"
    entry = (
        f'{name} = {{ features = ["{tier}", "py{tag}"], solve-group = "{name}" }}\n\n'
    )
    out: list[str] = []
    inside = False
    seen = False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if inside:
            if not stripped.startswith("["):
                continue
            inside = False
        if stripped == ENVIRONMENTS:
            out.append(line)
            out.append(entry)
            inside, seen = True, True
            continue
        out.append(line)
    if not seen:
        msg = f"{ENVIRONMENTS} not found; the manifest layout has changed"
        raise FloorError(msg)
    return "".join(out)


def report(resolved: Resolved, tier: str) -> str:
    """Render one tier as a step-summary table.

    Parameters
    ----------
    resolved : dict
        The mapping :func:`pins` returned.
    tier : str
        The tier to render.

    Returns
    -------
    str
        GitHub-flavoured Markdown.

    """
    lines = [
        f"### Floors resolved — `{tier}`",
        "",
        "| package | declared | resolved |",
        "|---|---|---|",
    ]
    for package, (declared, pin) in resolved[tier].items():
        lines.append(f"| `{package}` | `{declared}` | `{pin}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """Run the generator.

    Returns
    -------
    int
        The process exit status.

    """
    parser = argparse.ArgumentParser(description="Resolve tephpy's floors.")
    parser.add_argument("--manifest", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--tier", required=True, choices=["test", "docs", "devs"])
    parser.add_argument("--python", default="3.12")
    parser.add_argument("--relax")
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    python = Version(f"{args.python}.0")
    try:
        resolved = pins(args.manifest, python)
    except FloorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(report(resolved, "core"))
    print(report(resolved, args.tier))
    if args.summary is not None:
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(report(resolved, "core"))
            handle.write(report(resolved, args.tier))

    if args.write:
        text = args.manifest.read_text(encoding="utf-8")
        text = rewrite(text, resolved, relax=args.relax)
        text = environments(text, args.tier, args.python)
        args.manifest.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_floors.py -v`
Expected: three passes.

- [ ] **Step 6: Prove the generator against the real channel**

The unit tests never reach the network, so run it once for real. This writes nothing:

Run: `pixi exec --spec python=3.12.* --spec packaging python .github/scripts/floors.py --tier test`
Expected: two tables. `core` resolves `click >=8.1` to **8.1.3** (not 8.1.0 — the lower
builds stop at Python 3.10), `setuptools-scm >=8` to **8.0.1** (not 8 — no such release),
and `setuptools >=77.0.3` to **78.1.0**. `test` resolves `nbformat >=5.10` to 5.10.2.

- [ ] **Step 7: Lint and commit**

```bash
pre-commit install
git add .github/scripts/floors.py tests/test_floors.py pyproject.toml \
  requirements/pypi-optional-devs.txt pixi.lock
pixi run --frozen lint
git commit -m "feat: resolve declared dependency floors to channel pins"
```

---

### Task 2: The Weekly Workflow, Conda Half

The green path for the three pixi tiers. Nothing here diagnoses anything: a tier either
resolves and passes its exercise or it goes red, and Task 4 adds the diagnosis behind it.

**Files:**
- Create: `.github/workflows/ci-floors.yml`

**Interfaces:**
- Consumes: `floors.py --tier {test,docs,devs} --write --summary`.
- Produces: a `conda` job with `matrix.tier`, whose failing legs Task 4 hooks with
  `if: failure()`.

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/ci-floors.yml`. The SHAs are the ones `ci-tests.yml` and
`ci-docs.yml` already pin, so they are already trusted here.

```yaml
name: ci-floors

# The other end of the declaration `ci-locks` moves upward: this job resolves
# every dependency minimum tephpy declares and exercises what it resolves
# (floors spec §1). Scheduled, never a pull-request gate — it goes red for
# reasons no pull request caused (floors spec §2).

on:
  schedule:
    - cron: "17 4 * * 1"
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions: {}

jobs:
  conda:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        tier: ["test", "docs", "devs"]
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: prefix-dev/setup-pixi@f00437f565399d418b0acc85936d12c1fb668347  # v0.10.1
        with:
          run-install: false
      - name: Resolve the floors
        run: >
          pixi exec --spec python=3.12.* --spec packaging
          python .github/scripts/floors.py
          --tier ${{ matrix.tier }} --write --summary "$GITHUB_STEP_SUMMARY"
      - name: Solve and install at the floors
        run: pixi install --environment floors-${{ matrix.tier }}
      - name: Run the test suite
        if: matrix.tier == 'test'
        # Image comparison is excluded: pytest-mpl compares against baselines
        # generated under the matplotlib the lockfile pins, so at a floor
        # matplotlib it reports the version difference every time, whatever the
        # state of the floor (floors spec §3.3).
        run: pixi run --environment floors-test pytest
      - name: Build the documentation
        if: matrix.tier == 'docs'
        run: pixi run --environment floors-docs make -C docs html
      - name: Check the documentation output
        if: matrix.tier == 'docs'
        run: >
          pixi run --environment floors-docs
          python .github/scripts/check_rendered_citations.py docs/_build/html
      - name: Check the documentation links
        if: matrix.tier == 'docs'
        run: >
          pixi run --environment floors-docs
          python .github/scripts/check_documentation_links.py docs/_build/html
```

`devs` gets no exercise step. Its packages are linters, and pre-commit at a floor `ruff`
reports that version's rule set rather than anything about tephpy (floors spec §3.3).

- [ ] **Step 2: Lint the workflow**

Run: `git add .github/workflows/ci-floors.yml && pixi run --frozen lint`
Expected: `Validate GitHub Workflows` and `zizmor` both pass.

- [ ] **Step 3: Reproduce the `test` leg locally**

The workflow cannot be run here, but every command in it can. Work in a scratch copy so the
worktree's manifest is never rewritten:

```bash
rm -rf /tmp/floorsrepo /tmp/floorsrepo.tar
mkdir -p /tmp/floorsrepo
git archive --format=tar -o /tmp/floorsrepo.tar HEAD
tar -xf /tmp/floorsrepo.tar -C /tmp/floorsrepo
```

Then, from `/tmp/floorsrepo`:

```bash
pixi exec --spec python=3.12.* --spec packaging \
  python .github/scripts/floors.py --tier test --write
SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0 pixi install --environment floors-test
SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0 \
  pixi run --environment floors-test pytest -q
```

Expected: the install succeeds; the test run **fails**, at `conftest.py` import, with
`PyparsingDeprecationWarning: 'oneOf' deprecated`. That is a real finding about
`matplotlib-base >=3.10`, recorded in floors spec §1 — not a defect in this task. The leg
working means it *reached* that failure.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add the weekly dependency floors workflow"
```

---

### Task 3: The Weekly Workflow, PyPI Half

The other declaration site. It needs no generated pins:
`uv pip install --resolution lowest-direct` reads the floors straight from the requirements
files. It is also a genuinely different test — `lowest-direct` will lift a direct
requirement above its floor to make the set resolve, where the conda half's `==` pins
cannot — and the two halves are expected to disagree (floors spec §3.3).

**Files:**
- Modify: `.github/workflows/ci-floors.yml` (a second job)

**Interfaces:**
- Consumes: `requirements/pypi-core.txt` and the three optional files.
- Produces: a `pypi` job with `matrix.tier` over `core-test`, `docs`, `devs`.

- [ ] **Step 1: Add the job**

Append to `.github/workflows/ci-floors.yml`, inside `jobs:`:

```yaml
  pypi:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - tier: "core-test"
            requirements: >-
              -r requirements/pypi-core.txt
              -r requirements/pypi-optional-test.txt
          - tier: "docs"
            requirements: >-
              -r requirements/pypi-core.txt
              -r requirements/pypi-optional-docs.txt
          - tier: "devs"
            requirements: >-
              -r requirements/pypi-core.txt
              -r requirements/pypi-optional-devs.txt
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: prefix-dev/setup-pixi@f00437f565399d418b0acc85936d12c1fb668347  # v0.10.1
        with:
          run-install: false
      - name: Create the interpreter
        run: pixi exec --spec uv uv venv --python 3.12 .venv-floors
      - name: Install at the floors
        run: >
          pixi exec --spec uv uv pip install --python .venv-floors
          --resolution lowest-direct ${{ matrix.requirements }} .
      - name: Record what resolved
        run: >
          pixi exec --spec uv uv pip freeze --python .venv-floors
          >> "$GITHUB_STEP_SUMMARY"
      - name: Run the test suite
        if: matrix.tier == 'core-test'
        run: .venv-floors/bin/python -m pytest
```

`docs` and `devs` are installed and not run, matching the conda half: the documentation
build needs `make`, which the pip declaration deliberately does not carry
(floors spec §3.1), and the linters report their own rule sets (floors spec §3.3).

- [ ] **Step 2: Reproduce the resolution locally**

`--dry-run` is enough to see what the floors resolve to, and takes seconds:

```bash
mkdir -p /tmp/uvprobe
cp requirements/pypi-core.txt requirements/pypi-optional-docs.txt /tmp/uvprobe/
cd /tmp/uvprobe
pixi exec --spec uv uv venv --python 3.12 .venv
pixi exec --spec uv uv pip install --python .venv \
  --resolution lowest-direct --dry-run -r pypi-core.txt
```

Expected: every direct requirement lands exactly on its declared floor — `click==8.1.0`,
`matplotlib==3.10.0`, `numpy==2.0.0`, `pint==0.24`, `xarray==2024.10.0` — while transitives
float to newest. Note `click==8.1.0` here against the conda half's `8.1.3`: the same floor
resolves differently on the two sides, which is why floors spec §3.5 scans them separately.

Then the docs file:

```bash
pixi exec --spec uv uv pip install --python .venv \
  --resolution lowest-direct --dry-run -r pypi-optional-docs.txt
```

Expected: it **succeeds**, choosing `sphinx==8.0.0` with `sphinx-design==0.6.1` — lifted
above its `>=0.6` floor because 0.6.0 requires `sphinx <8`. The conda half has no solution
for the same pair. Both verdicts are correct about their own claim (floors spec §3.3).

- [ ] **Step 3: Lint and commit**

```bash
git add .github/workflows/ci-floors.yml
pixi run --frozen lint
git commit -m "feat: resolve the pip-declared floors from PyPI"
```

---

### Task 4: Attribution by Relaxation

A solve failure often names several packages, or none of the ones at fault. So the job
re-solves once per declared floor with that one specifier returned to its `>=X`, leaving the
rest pinned; the floor whose relaxation lets the tier solve is the culprit
(floors spec §3.4).

**Files:**
- Create: `.github/scripts/floors_diagnose.py`
- Modify: `.github/workflows/ci-floors.yml`

**Interfaces:**
- Consumes: `floors.pins`, `floors.rewrite`, `floors.environments` from Task 1.
- Produces:
  - `Finding` — a `dataclass` with `tier: str`, `half: str`, `package: str | None`,
    `declared: str | None`, `failure: str`, `lowest: str | None`, `scanned: list[str]`
  - `solves(root: Path, tier: str, python: str, relax: str | None) -> tuple[bool, str]`
  - `chosen(root: Path, tier: str, package: str) -> str | None`
  - `attribute(source: Path, scratch: Path, tier: str, python: str)` →
    `tuple[str | None, str | None, str]` — the culprit, the version the relaxed
    solve chose for it (the scan's upper bound, floors spec §3.5), and the
    unrelaxed solver output
  - `write_finding(path: Path, finding: Finding) -> None`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_floors.py`:

```python
def test_relaxing_one_package_leaves_the_others_pinned(tmp_path):
    floors = _load()
    resolved = floors.pins(_manifest(tmp_path), Version("3.12.0"), lookup=_lookup)
    text = floors.rewrite(MANIFEST, resolved, relax="click")
    assert 'click = ">=8.1"' in text
    assert 'pytest = "==8.0.0"' in text


def test_the_environment_table_is_replaced_not_appended():
    floors = _load()
    text = MANIFEST + "\n[tool.pixi.environments]\ndefault = { features = [] }\n"
    out = floors.environments(text, "test", "3.12")
    assert "floors-test" in out
    assert "default = " not in out
```

- [ ] **Step 2: Run to verify they fail**

Run: `pixi run --frozen pytest tests/test_floors.py -v`
Expected: two failures — `rewrite` has no `relax` behaviour under test yet and
`environments` is unexercised. If Task 1 was implemented exactly, they may pass
immediately; that is fine, they are the regression net for Task 4's use of them.

- [ ] **Step 3: Write the diagnosis script**

Create `.github/scripts/floors_diagnose.py`:

```python
#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Attribute a floors failure to one package (floors spec §3.4, §3.5).

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

from packaging.version import Version

if TYPE_CHECKING:
    from types import ModuleType

SCRIPTS = Path(__file__).parent


def _floors() -> ModuleType:
    """Import the generator beside this script."""
    spec = importlib.util.spec_from_file_location("floors", SCRIPTS / "floors.py")
    if spec is None or spec.loader is None:  # pragma: no cover - import guard
        msg = "floors.py not found beside floors_diagnose.py"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules["floors"] = module
    spec.loader.exec_module(module)
    return module


floors = _floors()


@dataclasses.dataclass(frozen=True)
class Probe:
    """Where and how one tier is exercised.

    The four values are invariant across a diagnosis, so they travel
    together rather than through every signature.
    """

    source: Path
    scratch: Path
    tier: str
    python: str


@dataclasses.dataclass
class Finding:
    """One tier's verdict, as floors spec §3.6 files it."""

    tier: str
    half: str
    failure: str
    package: str | None = None
    declared: str | None = None
    lowest: str | None = None
    scanned: list[str] = dataclasses.field(default_factory=list)


def solves(probe: Probe, root: Path, relax: str | None) -> tuple[bool, str]:
    """Report whether the tier solves with one floor relaxed.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.
    root : Path
        A scratch copy of the repository.
    relax : str, optional
        The package to return to its declared floor.

    Returns
    -------
    tuple of (bool, str)
        Whether it solved, and the solver's combined output.

    """
    command = [
        sys.executable,
        str(SCRIPTS / "floors.py"),
        "--manifest",
        str(root / "pyproject.toml"),
        "--tier",
        probe.tier,
        "--python",
        probe.python,
        "--write",
    ]
    if relax is not None:
        command += ["--relax", relax]
    subprocess.run(  # noqa: S603 -- fixed argv, this interpreter
        command, check=True, capture_output=True, text=True
    )
    out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        [floors.tool("pixi"), "install", "--environment", f"floors-{probe.tier}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return out.returncode == 0, out.stdout + out.stderr


def chosen(probe: Probe, root: Path, package: str) -> str | None:
    """Return the version an installed environment resolved for one package.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.
    root : Path
        The scratch copy whose environment was installed.
    package : str
        The package to read.

    Returns
    -------
    str or None
        The resolved version, or None when the environment lacks it.

    """
    out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        [
            floors.tool("pixi"),
            "list",
            "--environment",
            f"floors-{probe.tier}",
            "--json",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return None
    for entry in json.loads(out.stdout):
        if entry.get("name") == package:
            return str(entry["version"])
    return None


def attribute(probe: Probe) -> tuple[str | None, str | None, str]:
    """Find the one floor whose relaxation lets the tier solve.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.

    Returns
    -------
    tuple of (str or None, str or None, str)
        The culprit package, or None when nothing attributed; the version
        the relaxed solve chose for it, which bounds the scan above
        (floors spec §3.5); and the solver output of the unrelaxed attempt.

    """
    resolved = floors.pins(
        probe.source / "pyproject.toml", Version(f"{probe.python}.0")
    )
    packages = list(resolved["core"]) + list(resolved.get(probe.tier, {}))
    _, baseline = solves(probe, _copy(probe, "baseline"), None)
    for index, package in enumerate(packages):
        root = _copy(probe, f"relax-{index}")
        solved, _ = solves(probe, root, package)
        if solved:
            return package, chosen(probe, root, package), baseline
    return None, None, baseline


def _copy(probe: Probe, name: str) -> Path:
    """Make a throwaway copy of the checkout."""
    root = probe.scratch / name
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(probe.source, root, ignore=shutil.ignore_patterns(".pixi", ".git"))
    return root


def write_finding(path: Path, finding: Finding) -> None:
    """Write one finding as JSON.

    Parameters
    ----------
    path : Path
        The artifact to write.
    finding : Finding
        The verdict to record.

    """
    path.write_text(json.dumps(dataclasses.asdict(finding), indent=2), "utf-8")


def main() -> int:
    """Diagnose one failing tier.

    Returns
    -------
    int
        Always 0 — a diagnosis is not itself a failure.

    """
    parser = argparse.ArgumentParser(description="Diagnose a floors failure.")
    parser.add_argument("--source", type=Path, default=Path())
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--tier", required=True)
    parser.add_argument("--half", required=True, choices=["conda", "pypi"])
    parser.add_argument("--python", default="3.12")
    parser.add_argument("--failure", default="")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    args.scratch.mkdir(parents=True, exist_ok=True)
    probe = Probe(
        source=args.source,
        scratch=args.scratch,
        tier=args.tier,
        python=args.python,
    )
    package, upper, baseline = attribute(probe)
    finding = Finding(
        tier=args.tier,
        half=args.half,
        failure=args.failure or baseline[-4000:],
        package=package,
    )
    if package is not None:
        resolved = floors.pins(
            args.source / "pyproject.toml", Version(f"{args.python}.0")
        )
        for table in resolved.values():
            if package in table:
                finding.declared = table[package][0]
    write_finding(args.out, finding)
    print(f"attributed: {package or 'nothing'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Wire it into the conda job**

In `.github/workflows/ci-floors.yml`, after the `docs` link check step, add:

```yaml
      - name: Diagnose the failure
        if: failure()
        run: >
          pixi exec --spec python=3.12.* --spec packaging
          python .github/scripts/floors_diagnose.py
          --scratch /tmp/floors-scratch --tier ${{ matrix.tier }}
          --half conda --out finding-conda-${{ matrix.tier }}.json
      - uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a  # v7.0.1
        if: failure()
        with:
          name: finding-conda-${{ matrix.tier }}
          path: finding-conda-${{ matrix.tier }}.json
```

The diagnosis step re-generates the manifest from a clean copy, so it must run against the
checkout as committed — `--source` defaults to the working directory, which the earlier
`--write` has already rewritten. Pass `--source` explicitly from a pristine copy made before
the first `--write`. Add this as the first step after `setup-pixi`:

```yaml
      - name: Keep a pristine copy of the manifest
        run: cp pyproject.toml /tmp/pyproject.pristine.toml
```

and restore it at the head of the diagnosis step:

```yaml
      - name: Diagnose the failure
        if: failure()
        run: |
          cp /tmp/pyproject.pristine.toml pyproject.toml
          pixi exec --spec python=3.12.* --spec packaging \
            python .github/scripts/floors_diagnose.py \
            --scratch /tmp/floors-scratch --tier ${{ matrix.tier }} \
            --half conda --out finding-conda-${{ matrix.tier }}.json
```

- [ ] **Step 5: Run the tests and lint**

Run: `pixi run --frozen pytest tests/test_floors.py -v`
Expected: five passes.

Run: `git add -A && pixi run --frozen lint`
Expected: all hooks pass.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: attribute a floors failure to one package"
```

---

### Task 5: The Upward Scan

Given a culprit, find what would work: take the candidates the generator already enumerated,
keep those at or below the version the relaxed solve of floors spec §3.4 chose, try them in
ascending order, and stop at the first that both resolves and passes the tier's exercise
(floors spec §3.5). Ascending and linear, so the first pass is by construction the lowest
that works, with no assumption about the shape of the pass/fail boundary. The upper bound is
what makes the scan terminate: the relaxed solve already proved that version works, so
anything above it is known and pointless, and without the bound a floor that nothing fixes
walks the package's entire release history.

**Files:**
- Modify: `.github/scripts/floors_diagnose.py`
- Modify: `tests/test_floors.py`

**Interfaces:**
- Consumes: `floors.candidates`, `solves` and `chosen` from Task 4.
- Produces: `scan(source, scratch, tier, python, package, specifier, upper)` →
  `tuple[str | None, list[str]]`

- [ ] **Step 1: Write the failing test**

The scan's logic is "first candidate at or below the bound that passes", and both halves of
that are worth a test that touches neither the network nor a solver. The second test is the
one that matters: without the bound the scan still returns the right answer, so only a case
where nothing passes distinguishes the two. Add to `tests/test_floors.py`:

```python
LADDER = ["3.10.0", "3.10.1", "3.10.3", "3.11.0", "3.11.1"]


def _rigged(monkeypatch, tmp_path, passes):
    """Replace the solver and the channel; return the probe and what was tried."""
    diagnose = _load_diagnose()
    tried = []

    def _probe(probe, root):  # noqa: ARG001
        tried.append(root.name)
        return passes(len(tried) - 1)

    monkeypatch.setattr(diagnose, "_probe_pin", _probe)
    monkeypatch.setattr(diagnose, "_copy", lambda probe, name: tmp_path / name)  # noqa: ARG005
    monkeypatch.setattr(diagnose, "_pin_one", lambda manifest, package, pin: None)  # noqa: ARG005
    monkeypatch.setattr(
        diagnose.floors,
        "candidates",
        lambda package, specifier, python: LADDER,  # noqa: ARG005
    )
    probe = diagnose.Probe(
        source=tmp_path, scratch=tmp_path, tier="test", python="3.12"
    )
    return diagnose, probe


def test_the_scan_stops_at_the_first_version_that_passes(monkeypatch, tmp_path):
    diagnose, probe = _rigged(monkeypatch, tmp_path, lambda index: index == 2)
    lowest, scanned = diagnose.scan(probe, "matplotlib-base", ">=3.10", "3.11.0")
    assert lowest == "3.10.3"
    assert scanned == ["3.10.0", "3.10.1", "3.10.3"]


def test_the_scan_never_goes_above_the_bound(monkeypatch, tmp_path):
    diagnose, probe = _rigged(monkeypatch, tmp_path, lambda index: False)  # noqa: ARG005
    lowest, scanned = diagnose.scan(probe, "matplotlib-base", ">=3.10", "3.10.3")
    assert lowest is None
    assert scanned == ["3.10.0", "3.10.1", "3.10.3"]
```

with a loader beside `_load`:

```python
def _load_diagnose():
    """Import the diagnosis script by path."""
    path = REPO / ".github" / "scripts" / "floors_diagnose.py"
    spec = importlib.util.spec_from_file_location("floors_diagnose", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["floors_diagnose"] = module
    spec.loader.exec_module(module)
    return module
```

- [ ] **Step 2: Run to verify it fails**

Run: `pixi run --frozen pytest tests/test_floors.py -k scan -v`
Expected: two failures, each `AttributeError: module 'floors_diagnose' has no attribute
'scan'`.

- [ ] **Step 3: Implement the scan**

Add to `.github/scripts/floors_diagnose.py`, above `main`:

```python
EXERCISE = {
    "test": ["pytest"],
    "docs": ["make", "-C", "docs", "html"],
    "devs": None,
}


def _probe_pin(probe: Probe, root: Path) -> bool:
    """Report whether the tier resolves and passes its exercise."""
    solved, _ = solves(probe, root, None)
    if not solved:
        return False
    command = EXERCISE[probe.tier]
    if command is None:
        return True
    out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        [
            floors.tool("pixi"),
            "run",
            "--environment",
            f"floors-{probe.tier}",
            *command,
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return out.returncode == 0


def scan(
    probe: Probe, package: str, specifier: str, upper: str | None
) -> tuple[str | None, list[str]]:
    """Find the lowest version of ``package`` that passes the tier's exercise.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.
    package : str
        The culprit :func:`attribute` named.
    specifier : str
        Its declared floor, such as ``>=3.10``.
    upper : str or None
        The version the relaxed solve chose, which bounds the scan above
        (floors spec §3.5); None scans the whole ladder.

    Returns
    -------
    tuple of (str or None, list of str)
        The lowest passing version, or None, and every version tried.

    """
    ladder = floors.candidates(package, specifier, Version(f"{probe.python}.0"))
    if upper is not None:
        ceiling = Version(upper)
        ladder = [pin for pin in ladder if Version(pin) <= ceiling]
    tried: list[str] = []
    for pin in ladder:
        root = _copy(probe, f"scan-{len(tried)}")
        _pin_one(root / "pyproject.toml", package, pin)
        tried.append(pin)
        if _probe_pin(probe, root):
            return pin, tried
    return None, tried


def _pin_one(manifest: Path, package: str, pin: str) -> None:
    """Rewrite one declaration to an exact pin, leaving the rest alone."""
    text = manifest.read_text(encoding="utf-8")
    out = []
    for line in text.splitlines(keepends=True):
        match = floors.DECLARATION.match(line.strip())
        if match is not None and match["name"] == package:
            out.append(f'{package} = "=={pin}"\n')
            continue
        out.append(line)
    manifest.write_text("".join(out), encoding="utf-8")
```

and, in `main`, after the attribution block:

```python
    if package is not None and finding.declared is not None:
        finding.lowest, finding.scanned = scan(probe, package, finding.declared, upper)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_floors.py -v`
Expected: seven passes.

- [ ] **Step 5: Sanity-check the candidate ladder against the channel**

Run: `pixi exec --spec python=3.12.* --spec packaging python -c "import importlib.util,sys;s=importlib.util.spec_from_file_location('f','.github/scripts/floors.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);from packaging.version import Version;print(m.candidates('matplotlib-base','>=3.10',Version('3.12.0')))"`
Expected: an ascending list beginning `3.10.0, 3.10.1, 3.10.3, 3.10.5` — note 3.10.2 and
3.10.4 are absent, which is what makes the ladder a channel query rather than arithmetic.

- [ ] **Step 6: Lint and commit**

```bash
git add -A && pixi run --frozen lint
git commit -m "feat: scan upward for the lowest working floor"
```

---

### Task 6: The Issue Contract

A finding becomes an issue per tier and package, deduped against the open marker-labelled
issues so a floor that stays broken comments rather than files again (floors spec §3.6).

**Files:**
- Create: `.github/scripts/floors_issue.py`
- Create: `tests/test_floors_issue.py`
- Modify: `.github/workflows/ci-floors.yml`

**Interfaces:**
- Consumes: the `Finding` JSON artifacts of Tasks 4 and 5.
- Produces: `key(finding: dict) -> str`, `title(finding: dict) -> str`,
  `body(finding: dict, run_url: str) -> str`.

- [ ] **Step 1: Write the failing tests**

Two things must hold and neither is obvious: the key omits the half, so one floor failing on
both sides raises one issue rather than two; and the body carries the §3.5 caveat verbatim,
because a version reported without it reads as an answer.

Create `tests/test_floors_issue.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the floors issue contract (floors spec §3.6)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "floors_issue.py"

pytestmark = pytest.mark.skipif(
    not (SCRIPT.is_file() and (REPO / ".git").exists()),
    reason="not a git checkout of the repository",
)


def _load():
    """Import the issue composer by path."""
    spec = importlib.util.spec_from_file_location("floors_issue", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["floors_issue"] = module
    spec.loader.exec_module(module)
    return module


FINDING = {
    "tier": "core",
    "half": "conda",
    "package": "matplotlib-base",
    "declared": ">=3.10",
    "failure": "PyparsingDeprecationWarning: 'oneOf' deprecated",
    "lowest": "3.10.3",
    "scanned": ["3.10.0", "3.10.1", "3.10.3"],
}


def test_the_key_omits_the_half_so_one_floor_raises_one_issue():
    module = _load()
    conda = module.key(FINDING)
    pypi = module.key({**FINDING, "half": "pypi"})
    assert conda == pypi


def test_the_body_carries_the_caveat_and_both_declaration_sites():
    module = _load()
    text = module.body(FINDING, "https://example.invalid/run/1")
    assert "lowest version that passes what tephpy runs" in text
    assert "requirements/pypi-core.txt" in text
    assert "[tool.pixi.dependencies]" in text
    assert "https://example.invalid/run/1" in text


def test_an_unattributed_finding_says_so():
    module = _load()
    text = module.body({**FINDING, "package": None, "lowest": None}, "url")
    assert "no attribution was reached" in text
```

- [ ] **Step 2: Run to verify they fail**

Run: `pixi run --frozen pytest tests/test_floors_issue.py -v`
Expected: three skips (the script is absent, so the guard fires). Create an empty
`.github/scripts/floors_issue.py` and re-run to see three real failures.

- [ ] **Step 3: Write the composer**

Create `.github/scripts/floors_issue.py`:

```python
#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Compose and dedupe dependency floor issues (floors spec §3.6).

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

MARKER = "dependency-floors"

#: The two declaration sites of floors spec §3.1, by tier.
SITES = {
    "core": ("[tool.pixi.dependencies]", "requirements/pypi-core.txt"),
    "test": (
        "[tool.pixi.feature.test.dependencies]",
        "requirements/pypi-optional-test.txt",
    ),
    "docs": (
        "[tool.pixi.feature.docs.dependencies]",
        "requirements/pypi-optional-docs.txt",
    ),
    "devs": (
        "[tool.pixi.feature.devs.dependencies]",
        "requirements/pypi-optional-devs.txt",
    ),
}

CAVEAT = (
    "What the scan reports is the *lowest version that passes what tephpy "
    "runs*, which is a weaker claim than the lowest version that is correct. "
    "`sphinx-click 6.0.0` resolved, built the documentation clean under "
    "`--fail-on-warning` with both output gates green, and still rendered a "
    "page differently from the pinned version (#109). Read this as a starting "
    "point, not an answer."
)


def _gh() -> str:
    """Resolve ``gh`` off ``PATH``.

    This script shells out to nothing else, so it carries its own resolver
    rather than importing the pin generator for one function.

    Returns
    -------
    str
        The absolute path to ``gh``.

    Raises
    ------
    RuntimeError
        If ``gh`` is not on ``PATH``.

    """
    found = shutil.which("gh")
    if found is None:
        msg = "gh is not on PATH"
        raise RuntimeError(msg)
    return found


def key(finding: dict) -> str:
    """Return the dedupe key: tier and package, never the half.

    Parameters
    ----------
    finding : dict
        One finding artifact.

    Returns
    -------
    str
        The key both halves of one floor share.

    """
    return f"{finding['tier']}/{finding['package']}"


def title(finding: dict) -> str:
    """Return the issue title.

    Parameters
    ----------
    finding : dict
        One finding artifact.

    Returns
    -------
    str
        A title carrying the dedupe key.

    """
    package = finding["package"] or "unattributed"
    return f"Dependency floor: {finding['tier']} / {package}"


def body(finding: dict, run_url: str) -> str:
    """Return the issue body.

    Parameters
    ----------
    finding : dict
        One finding artifact.
    run_url : str
        A link to the workflow run.

    Returns
    -------
    str
        GitHub-flavoured Markdown.

    """
    conda, pypi = SITES[finding["tier"]]
    lines = [
        f"The `{finding['tier']}` tier failed at its declared floors "
        f"({finding['half']} half).",
        "",
        f"- **package:** `{finding['package'] or 'unattributed'}`",
        f"- **declared:** `{finding['declared'] or 'n/a'}`",
        f"- **run:** {run_url}",
        "",
    ]
    if finding["package"] is None:
        lines += [
            "Relaxing each declared floor in turn resolved nothing, so "
            "**no attribution was reached**. The solver output is below "
            "verbatim.",
            "",
        ]
    elif finding["lowest"] is None:
        lines += [
            "No version at or above the floor passed the scan.",
            "",
        ]
    else:
        lines += [
            f"The lowest version that passed is **{finding['lowest']}**, "
            f"from {len(finding['scanned'])} tried.",
            "",
        ]
    lines += [
        "Both declaration sites need the same edit — a fix that changes one "
        "and not the other leaves the two sides disagreeing:",
        "",
        f"- `pyproject.toml`, `{conda}`",
        f"- `{pypi}`",
        "",
        CAVEAT,
        "",
        "<details><summary>failure</summary>",
        "",
        "```text",
        finding["failure"],
        "```",
        "",
        "</details>",
    ]
    return "\n".join(lines)


def _open_issues() -> dict[str, str]:
    """Map the dedupe key of every open marker-labelled issue to its number."""
    out = subprocess.run(  # noqa: S603 -- fixed argv, gh resolved off PATH
        [
            _gh(),
            "issue",
            "list",
            "--label",
            MARKER,
            "--state",
            "open",
            "--json",
            "number,title",
            "--limit",
            "200",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    found = {}
    for issue in json.loads(out):
        prefix = "Dependency floor: "
        if issue["title"].startswith(prefix):
            found[issue["title"].removeprefix(prefix).replace(" / ", "/")] = str(
                issue["number"]
            )
    return found


def main() -> int:
    """File or comment on one issue per finding artifact.

    Returns
    -------
    int
        The process exit status.

    """
    parser = argparse.ArgumentParser(description="File dependency floor issues.")
    parser.add_argument("artifacts", type=Path, nargs="+")
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()

    existing = _open_issues()
    for path in args.artifacts:
        finding = json.loads(path.read_text(encoding="utf-8"))
        text = body(finding, args.run_url)
        number = existing.get(key(finding))
        if number is None:
            subprocess.run(  # noqa: S603 -- fixed argv, gh resolved off PATH
                [
                    _gh(),
                    "issue",
                    "create",
                    "--title",
                    title(finding),
                    "--body",
                    text,
                    "--label",
                    MARKER,
                    "--label",
                    "type: dependencies",
                ],
                check=True,
            )
        else:
            subprocess.run(  # noqa: S603 -- fixed argv, gh resolved off PATH
                [_gh(), "issue", "comment", number, "--body", text], check=True
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_floors_issue.py -v`
Expected: three passes.

- [ ] **Step 5: Add the filing job**

`issues: write` is granted on this job alone; everything else runs under the workflow's
`permissions: {}` (floors spec §3.6). Append to `jobs:` in
`.github/workflows/ci-floors.yml`:

```yaml
  file:
    runs-on: ubuntu-latest
    needs: [conda, pypi]
    if: always() && (needs.conda.result == 'failure' || needs.pypi.result == 'failure')
    permissions:
      issues: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false
      - uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c  # v8.0.1
        with:
          path: findings
          pattern: finding-*
          merge-multiple: true
      - name: File or comment
        env:
          GH_TOKEN: ${{ github.token }}
          RUN_URL: >-
            ${{ github.server_url }}/${{ github.repository
            }}/actions/runs/${{ github.run_id }}
        run: >
          pixi exec --spec python=3.12.* python
          .github/scripts/floors_issue.py findings/*.json --run-url "$RUN_URL"
```

- [ ] **Step 6: Create the marker label**

The label must exist before the first run, or `gh issue create` fails. Ask the maintainer to
run, or run with their approval:

```bash
gh label create dependency-floors \
  --description "Filed by ci-floors (floors spec §3.6)" --color ededed
```

- [ ] **Step 7: Lint and commit**

```bash
git add -A && pixi run --frozen lint
git commit -m "feat: file an issue per broken dependency floor"
```

---

### Task 7: The Retry, the Docs, and the Changelog

Two failure modes are not findings and would each cost someone a reading (floors spec §4).
Then the paperwork.

**Files:**
- Modify: `.github/workflows/ci-floors.yml`
- Modify: `docs/src/developer/specs/2026-08-13-dependency-floors-design.md`
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md`
- Create: `changelog/<PR>.internal.rst`

- [ ] **Step 1: Retry the solve once**

This job is the only one in the repository that solves fresh, so it inherits a live
channel's failure modes. Replace the conda job's install step:

```yaml
      - name: Solve and install at the floors
        # This job solves fresh, so a mirror hiccup or a metadata timeout
        # reads as a broken floor. One retry is the difference between weekly
        # noise and an occasional one (floors spec §4).
        run: >
          pixi install --environment floors-${{ matrix.tier }} ||
          pixi install --environment floors-${{ matrix.tier }}
```

- [ ] **Step 2: Name the `setuptools-scm` shape**

Its failure mode is "nothing builds", not "one package is wrong": tephpy installs editable,
so a build backend that cannot build makes every tier look broken and leaves the attribution
pass nothing useful to relax. Add to the conda job, before the diagnosis step:

```yaml
      - name: Note the build-backend shape
        if: failure()
        run: >
          echo "If every tier failed at once, suspect setuptools-scm at its
          floor before reading the attribution (floors spec §4)."
          >> "$GITHUB_STEP_SUMMARY"
```

- [ ] **Step 3: Flip the specification's status**

In `docs/src/developer/specs/2026-08-13-dependency-floors-design.md`, the metadata line:

```markdown
- **Status:** living design specification
```

- [ ] **Step 4: Move `ci-floors` out of the fast-follow list**

In `docs/src/developer/specs/2026-07-22-tephpy-design.md` §8.7, drop the `ci-floors` clause
from the fast-follow sentence and add the workflow to the list of what CI runs, matching how
the other workflows are named there.

- [ ] **Step 5: Write the changelog fragment**

Open the pull request first — the fragment is named for its number, and issues filed in the
meantime take numbers the pull request will not get. Then, in
`changelog/<PR>.internal.rst`:

```rst
Added the ``ci-floors`` workflow, which weekly resolves every dependency
minimum tephpy declares, exercises what it resolves, and files an issue
attributing any failure to a single package (:issue:`109`, :user:`bjlittle`)
```

- [ ] **Step 6: Full verification**

```bash
pixi run --frozen tests
git add -A && pixi run --frozen lint
pixi run --frozen docs-clean && pixi run --frozen docs
```

Expected: the suite passes; every hook passes, the citation hook included; the docs build
succeeds and both output gates report ok.

- [ ] **Step 7: Run the workflow before scheduling it**

`workflow_dispatch` is in the trigger list for this. Run it once on the branch and read the
step summaries: the `devs` leg should be green, and `test` and `docs` should each go red on
a real finding — `matplotlib-base >=3.10` and `sphinx-design >=0.6` respectively, both
recorded in floors spec §1 and floors spec §3.3. That is the failure path exercised on a
genuine failure rather than a contrived one, which is what floors spec §5 asks for.

- [ ] **Step 8: Commit**

```bash
git commit -m "docs: record the dependency floors job as built"
```

---

## Known Findings This Job Will Report on Its First Run

Measured by hand on 2026-08-13 while the specification was written, in a scratch copy of the
checkout at Python 3.12. They are recorded here so the first run's red is recognised as the
job working rather than the job being broken. None is in scope for this plan to fix; each
defect is filed, with its reproducer and its indicated floor.

| declaration | half | what happens | indicated floor | filed |
|---|---|---|---|---|
| `matplotlib-base >=3.10` / `matplotlib>=3.10` | both | 3.10.0 calls `pyparsing.oneOf`, deprecated in the pyparsing that resolves, and `filterwarnings = ["error"]` turns it into an error during `conftest.py` import — fixed at 3.10.7. Then `_domain_linestyle`'s oracle refuses a nested `'none'` until 3.11.0, failing two `test_configfile_domain.py` parametrisations | `>=3.11` | {issue}`135` |
| `pint >=0.24` | both | 0.24's recipe declares `flexparser` uncapped, so the solve takes 0.4 and the metpy import chain dies with `TypeError: cannot inherit frozen dataclass from a non-frozen one` — collection interrupted, 6 errors. 0.24.1 caps it `<0.4` | `>=0.24.1` | {issue}`136` |
| `metpy >=1.6` with `numpy >=2.0` | both | 1.6.0 imports `numpy.core.numeric`, deprecated by numpy 2 — two collection errors, guarded at 1.6.3. Then `saturation_mixing_ratio` returns a finite −1194.07 g/kg where the quantity is undefined until 1.7.0, failing the supersaturated cursor readout | `>=1.7` | {issue}`137` |
| `sphinx-design >=0.6` with `sphinx >=8.0` | conda only | no solution: sphinx-design 0.6.0 requires `sphinx <8`. PyPI resolves it by lifting to 0.6.1 | `>=0.6.1` | {issue}`138` |
| `setuptools >=77.0.3` | conda | conda-forge carries nothing below 78.1.0, so the declared span cannot be tested. Not a defect | — | — |

The layering is the point, and worth expecting on the first run. Each of the first three rows
hid the next: the metpy row was invisible until the pint row was fixed, because collection
never reached `metpy.calc`; and within two of the rows an import failure hid a behaviour
difference behind it, which is why the indicated floor is higher than the version that merely
imports. A tier reports the first thing that stops it, not every thing that would, so the run
after a floor bump is not expected to be green — it is expected to be *further on*. This is
also §3.5's caveat from the other side: the scan finds the lowest version that passes what
tephpy runs, and what tephpy runs only reaches as far as the last failure allowed.

With `matplotlib-base` 3.11.0, `metpy` 1.7.0 and `pint` 0.24.1 pinned and everything else left
at its declared floor, the conda test tier runs 1248 passed and 1 failed. That one is
`test_masters_ship_in_the_wheel`, which needs `build` — the environment-composition gap Task 1
Step 1 closes by declaring `python-build` in the `test` tier, not a floor defect at all.
