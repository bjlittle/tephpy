# API `versionadded` Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every published API object carries `.. versionadded::` in a numpydoc `Notes` section, enforced by a gate that owns a reusable definition of "the public API".

**Architecture:** One script, `.github/scripts/check_api_docstrings.py`, in the shape of the existing `check_*.py` gates. It has two separable halves: a **published-API enumerator** that reproduces statically what sphinx-autoapi publishes, and a **rule layer** that checks each enumerated object's docstring. This plan adds one rule (`versionadded`); {issue}`224` adds a second (`Raises`) to the same script, which is why the enumerator is the deliverable rather than a private helper. A docs-build test pins the enumerator against the built `objects.inv`, so the fast static set is provably the set a reader meets.

**Tech Stack:** Python 3.12+, `ast` + `importlib` for enumeration, `numpydoc.docscrape` for section parsing, `packaging.version` and `setuptools_scm` for the target version, pytest, pre-commit.

**Spec:** No standalone design specification. The design and its rationale are recorded in {issue}`227`; the resulting *policy* — the rule contributors must follow — lands in `docs/src/developer/docs-style.rst` in Task 6, which is the living home for docstring rules and also settles {issue}`225`.

## Global Constraints

- Every source file carries the BSD copyright header (ruff `CPY001`); the exact notice is in `[tool.ruff.lint.flake8-copyright]`.
- `line-length = 88`; ruff `select = ["ALL"]` with the ignore list in `pyproject.toml`.
- `[tool.pytest.ini_options]` sets `filterwarnings = ["error"]` — a warning in a test is a failure.
- numpydoc validation runs over `^src/` only, with `checks = ["all", "GL01", "GL02", "GL03", "SA01", "ES01", "EX01", "YD01"]` (the names after `"all"` are *disabled*).
- **Directive spelling is `versionadded`, not `version-added`.** Sphinx 9 added `version-added` and keeps `versionadded` as a registered alias, but `requirements/pypi-optional-docs.txt` declares `sphinx>=8.0` and `.github/workflows/ci-floors.yml:80-81` builds the docs at that floor, where `version-added` does not exist. `versionadded` also keeps numpydoc's `GL10` two-colon check, which does not fire for the hyphenated name.
- The house form is a `Notes` section as the **last** section, matching the 13 files already using it (`.github/scripts/floors.py`, `docs/src/_ext/tephpy_citations.py`, …):

  ```rst
  Notes
  -----
  .. versionadded:: 0.1.0
  ```

- numpydoc's `ALLOWED_SECTIONS` order is `Parameters, Attributes, Methods, Returns, Yields, Other Parameters, Raises, Warns, Warnings, See Also, Notes, References, Examples`. `Notes` therefore goes **after** `Raises`, and `GL07` fails the build if it does not.
- Every PR adds `changelog/<PR>.<type>.rst` ending with ``(:user:`claude`)``.

---

## File Structure

| File | Responsibility |
|---|---|
| `.github/scripts/check_api_docstrings.py` | **Create.** The enumerator (`published_objects`) and the `versionadded` rule (`check_versionadded`), plus `main()`. Grows a second rule in {issue}`224`. |
| `tests/test_api_docstrings.py` | **Create.** Unit cases for the enumerator and the rule, mirroring `tests/test_glossary_links.py`'s script-loading idiom. |
| `tests/test_docs_api_inventory.py` | **Create.** The docs-build cross-check: the static enumerator equals the built `objects.inv`. |
| `src/tephpy/**/*.py` | **Modify.** 94 docstrings gain a `Notes` section (Task 5). |
| `.pre-commit-config.yaml` | **Modify.** Register the gate as a `local` hook beside the other three. |
| `docs/src/developer/docs-style.rst` | **Modify.** State the policy (Task 6). |
| `changelog/<PR>.internal.rst` | **Create.** Fragment. |

### The published set, measured

Taken from the built `docs/_build/html/objects.inv` on 2026-08-30. Total `tephpy` entries: 207.

| role | count | stamped? |
|---|---|---|
| `py:attribute` | 104 | **no** — dataclass fields, documented in the class `Attributes` section; they have no docstring of their own |
| `py:method` | 32 | yes |
| `py:function` | 24 | yes |
| `py:module` | 15 | yes |
| `py:class` | 11 | yes |
| `py:exception` | 10 | yes |
| `py:property` | 2 | yes |
| `py:data` | 1 | **no** — `EDGES`, documented by a `#:` comment |
| `std:*` | 8 | **no** — CLI options and labels, not Python objects |

**94 objects to stamp.**

### What "published" means

`autoapi_dirs = ["../../src/tephpy"]` with `autoapi_ignore = ["*/_version.py", "*/examples/*"]`, and `autoapi_options` **without** `private-members`, so sphinx-autoapi skips every underscore-prefixed name — modules included. The published module set is therefore every module under `src/tephpy` with no underscore-prefixed path component, excluding `examples`: exactly the 15 pages built.

**One wrinkle the enumerator must handle.** `tephpy.config` is a `Config` instance exported from the *private* module `tephpy._config`, and `tephpy._config` has no page — but its methods are published as `tephpy.config.load`, `tephpy.config.reset`, `tephpy.config.context` and friends, because the singleton is reachable from `tephpy`. The enumerator must reach them through the instance, not through the module list. Task 2 exists to catch exactly this class of divergence.

---

### Task 1: The published-API enumerator

**Files:**
- Create: `.github/scripts/check_api_docstrings.py`
- Test: `tests/test_api_docstrings.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `PublicObject` (a frozen dataclass with fields `name: str`, `role: str`, `obj: object`), and `published_objects() -> list[PublicObject]`, sorted by `name`. Task 3 and Task 4 consume both; {issue}`224` consumes them again.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_docstrings.py
def test_published_objects_covers_the_documented_modules():
    """The 15 module pages autoapi builds, and no private module."""
    names = {o.name for o in gate.published_objects() if o.role == "module"}
    assert names == {
        "tephpy",
        "tephpy.calc",
        "tephpy.exceptions",
        "tephpy.io",
        "tephpy.io.igra",
        "tephpy.io.wyoming",
        "tephpy.plotting",
        "tephpy.plotting.axes",
        "tephpy.plotting.barbs",
        "tephpy.plotting.isopleths",
        "tephpy.plotting.logo",
        "tephpy.plotting.shading",
        "tephpy.samples",
        "tephpy.sounding",
        "tephpy.transforms",
    }


def test_published_objects_reaches_the_config_singleton():
    """`tephpy.config` is a private-module instance whose methods are published.

    `tephpy._config` has no API page, but the singleton is reachable from
    `tephpy`, so autoapi documents `tephpy.config.load` and friends. An
    enumerator built from the module list alone would miss all of them.
    """
    names = {o.name for o in gate.published_objects()}
    assert "tephpy.config.load" in names
    assert "tephpy.config.reset" in names
    assert not any(n.startswith("tephpy._config") for n in names)


def test_published_objects_excludes_attributes_and_data():
    """Dataclass fields carry no docstring, so there is nothing to stamp."""
    names = {o.name for o in gate.published_objects()}
    assert "tephpy.calc.Profile" in names
    assert "tephpy.calc.Profile.lcl_pressure" not in names
    assert "tephpy.plotting.isopleths.EDGES" not in names


def test_published_objects_excludes_private_and_examples():
    names = {o.name for o in gate.published_objects()}
    assert not any(".examples" in n for n in names)
    assert not any(part.startswith("_") for n in names for part in n.split("."))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.pixi/envs/devs/bin/python -m pytest tests/test_api_docstrings.py -v`
Expected: FAIL — `ModuleNotFoundError` / `AttributeError: module has no attribute 'published_objects'`.

- [ ] **Step 3: Write minimal implementation**

Copy the copyright header from `.github/scripts/check_glossary_links.py` verbatim, then:

```python
"""Check the published API docstrings carry what policy requires (:issue:`227`).

The set this walks is the set sphinx-autoapi publishes: every module under
``src/tephpy`` with no underscore-prefixed path component, minus ``examples``,
plus the objects those modules define. ``tephpy.config`` is the exception that
shapes the design -- a ``Config`` instance exported from the private
``tephpy._config``, with no page of its own, whose methods are nonetheless
published as ``tephpy.config.load`` and friends because the singleton is
reachable from ``tephpy``.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path
import pkgutil
import sys

REPO = Path(__file__).parents[2]
PACKAGE = REPO / "src"

#: Roles that own a docstring of their own. ``attribute`` and ``data`` are
#: excluded: a dataclass field is documented in its class's ``Attributes``
#: section and a ``#:`` comment is not a docstring, so neither has anywhere to
#: carry a directive.
STAMPED_ROLES = ("module", "class", "exception", "function", "method", "property")


@dataclasses.dataclass(frozen=True)
class PublicObject:
    """One published API object.

    Parameters
    ----------
    name : str
        The dotted name the API reference publishes it under.
    role : str
        One of ``STAMPED_ROLES``.
    obj : object
        The live object, for reading ``__doc__``.
    """

    name: str
    role: str
    obj: object


def _public_modules():
    """Yield the modules sphinx-autoapi publishes.

    Yields
    ------
    module
        Each imported module with no underscore-prefixed path component.
    """
    import tephpy  # noqa: PLC0415 -- the package under audit

    yield tephpy
    for info in pkgutil.walk_packages(tephpy.__path__, prefix="tephpy."):
        parts = info.name.split(".")
        if any(part.startswith("_") for part in parts) or "examples" in parts:
            continue
        yield __import__(info.name, fromlist=["_"])


def _members(owner, prefix, seen):
    """Collect the published members an owner defines.

    Parameters
    ----------
    owner : object
        The module, class, or singleton to walk.
    prefix : str
        The dotted name `owner` is published under.
    seen : set of str
        Names already emitted, mutated in place.

    Returns
    -------
    list of PublicObject
        The members, in `dir` order.
    """
    found = []
    for name in sorted(vars(owner) if inspect.ismodule(owner) else dir(owner)):
        if name.startswith("_"):
            continue
        try:
            child = getattr(owner, name)
        except AttributeError:  # pragma: no cover -- defensive
            continue
        defined_in = getattr(child, "__module__", None) or ""
        if not defined_in.startswith("tephpy"):
            continue
        dotted = f"{prefix}.{name}"
        if dotted in seen:
            continue
        if inspect.isclass(child):
            role = "exception" if issubclass(child, BaseException) else "class"
            seen.add(dotted)
            found.append(PublicObject(dotted, role, child))
            found.extend(_members(child, dotted, seen))
        elif isinstance(child, property):
            seen.add(dotted)
            found.append(PublicObject(dotted, "property", child.fget))
        elif inspect.isroutine(child):
            role = "method" if not inspect.ismodule(owner) else "function"
            seen.add(dotted)
            found.append(PublicObject(dotted, role, child))
    return found


def published_objects() -> list[PublicObject]:
    """Enumerate every published API object that owns a docstring.

    Returns
    -------
    list of PublicObject
        Sorted by dotted name.
    """
    if str(PACKAGE) not in sys.path:
        sys.path.insert(0, str(PACKAGE))
    import tephpy  # noqa: PLC0415

    seen: set[str] = set()
    found: list[PublicObject] = []
    for module in _public_modules():
        found.append(PublicObject(module.__name__, "module", module))
        found.extend(_members(module, module.__name__, seen))
    # The singleton whose defining module is private (see the module docstring).
    found.extend(_members(type(tephpy.config), "tephpy.config", seen))
    return sorted(found, key=lambda entry: entry.name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.pixi/envs/devs/bin/python -m pytest tests/test_api_docstrings.py -v`
Expected: PASS, 4 tests.

- [ ] **Step 5: Check the count matches the measurement**

Run:

```bash
.pixi/envs/devs/bin/python -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('g', '.github/scripts/check_api_docstrings.py')
m = importlib.util.module_from_spec(spec); sys.modules['g'] = m; spec.loader.exec_module(m)
import collections
print(collections.Counter(o.role for o in m.published_objects()))
print('total', len(m.published_objects()))
"
```

Expected: 94 total, matching the table above. If it differs, Task 2 will say exactly which names diverge — do not adjust the expected number by hand.

- [ ] **Step 6: Commit**

```bash
git add .github/scripts/check_api_docstrings.py tests/test_api_docstrings.py
git commit -m "Enumerate the published API surface"
```

---

### Task 2: Pin the enumerator against the built inventory

**Files:**
- Create: `tests/test_docs_api_inventory.py`

**Interfaces:**
- Consumes: `published_objects()` and `STAMPED_ROLES` from Task 1.
- Produces: nothing consumed later. This is the proof that the fast static set equals the published set.

This is the task that makes the whole design trustworthy: without it, the enumerator is an assertion about autoapi's behaviour rather than a checked fact, and the `tephpy.config` wrinkle is precisely the kind of thing that would drift silently.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_docs_api_inventory.py
"""The static enumerator agrees with what the documentation publishes.

`check_api_docstrings.published_objects` reproduces sphinx-autoapi's selection
without a build, so the gate can run in pre-commit. This test is what earns
that shortcut: it reads the `objects.inv` a real build wrote and asserts the
two sets are identical.
"""

from __future__ import annotations

import pathlib
import re
import zlib

import pytest

REPO = pathlib.Path(__file__).parents[1]
INVENTORY = REPO / "docs" / "_build" / "html" / "objects.inv"

ROLE_OF = {
    "py:module": "module",
    "py:class": "class",
    "py:exception": "exception",
    "py:function": "function",
    "py:method": "method",
    "py:property": "property",
}


def _inventory_names():
    """Read the published `tephpy` objects from the built inventory.

    Returns
    -------
    set of str
        Dotted names whose role owns a docstring.
    """
    raw = INVENTORY.read_bytes()
    offset = 0
    for _ in range(4):  # four plain-text header lines precede the zlib stream
        offset = raw.index(b"\n", offset) + 1
    body = zlib.decompress(raw[offset:]).decode("utf-8")
    names = set()
    for line in body.splitlines():
        match = re.match(r"(\S+)\s+(\S+)\s+-?\d+\s+\S*\s+.*", line)
        if match and match.group(1).startswith("tephpy"):
            if ROLE_OF.get(match.group(2)):
                names.add(match.group(1))
    return names


@pytest.mark.skipif(
    not INVENTORY.exists(), reason="needs `pixi run docs-html` to have run"
)
def test_enumerator_matches_the_published_inventory(gate):
    published = {entry.name for entry in gate.published_objects()}
    inventory = _inventory_names()
    assert published - inventory == set(), "enumerated but not published"
    assert inventory - published == set(), "published but not enumerated"
```

Add the shared `gate` fixture to `tests/conftest.py`, loading the script the way `tests/test_glossary_links.py` does:

```python
@pytest.fixture(scope="session")
def gate():
    """Import the API docstring gate, which is a script not an installed module."""
    import importlib.util

    path = pathlib.Path(__file__).parents[1] / ".github" / "scripts"
    spec = importlib.util.spec_from_file_location(
        "check_api_docstrings", path / "check_api_docstrings.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
```

- [ ] **Step 2: Build the docs, then run the test**

Run: `pixi run docs-html && .pixi/envs/devs/bin/python -m pytest tests/test_docs_api_inventory.py -v`
Expected: initially FAIL, listing the divergence in one of the two assertion messages.

- [ ] **Step 3: Reconcile the enumerator, not the expectation**

Every divergence is a real statement about what readers see. Fix `_members` / `_public_modules` until both differences are empty. Do **not** add names to a skip list to make it pass.

- [ ] **Step 4: Re-run to verify it passes**

Run: `.pixi/envs/devs/bin/python -m pytest tests/test_docs_api_inventory.py -v`
Expected: PASS.

- [ ] **Step 5: Wire it into the docs task chain**

Add to `pyproject.toml` beside the other post-build gates (`docs-check-citations`, `docs-check-links`, `docs-check-figures`):

```toml
[tool.pixi.feature.docs.tasks.docs-check-api]
cmd = "python -m pytest tests/test_docs_api_inventory.py -q"
depends-on = ["docs-html"]
description = "Check the API gate's surface matches the published inventory"
```

and add `docs-check-api` to the `docs` task's `depends-on` list.

- [ ] **Step 6: Commit**

```bash
git add tests/test_docs_api_inventory.py tests/conftest.py pyproject.toml
git commit -m "Pin the enumerated surface to the published inventory"
```

---

### Task 3: Derive the target version

**Files:**
- Modify: `.github/scripts/check_api_docstrings.py`
- Test: `tests/test_api_docstrings.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `target_version() -> str | None` — the base version the next tag will carry, or `None` when it cannot be confirmed. Task 4 consumes it.

- [ ] **Step 1: Write the failing test**

```python
def test_target_version_is_the_base_of_the_scm_version(monkeypatch):
    """`setuptools_scm` reports the version the next tag will carry."""
    monkeypatch.setattr(gate, "_scm_version", lambda: "0.2.0.dev3")
    assert gate.target_version() == "0.2.0"


@pytest.mark.parametrize(
    ("reported", "expected"),
    [
        ("0.1.0.dev148+dirty", "0.1.0"),  # today: no tags, local segment present
        ("0.2.0.dev3", "0.2.0"),  # mid-cycle after v0.1.0
        ("0.2.0", "0.2.0"),  # exactly on a tag
    ],
)
def test_target_version_strips_dev_and_local_segments(monkeypatch, reported, expected):
    monkeypatch.setattr(gate, "_scm_version", lambda: reported)
    assert gate.target_version() == expected


def test_target_version_refuses_a_shallow_checkout(monkeypatch):
    """A shallow clone derives the wrong target, so refuse rather than guess.

    Without tags `setuptools_scm` falls back to `0.1.0`, so once `v0.1.0`
    exists a shallow checkout would compare against `0.1.0` instead of
    `0.2.0` -- and under any `<=` rule that produces *false failures* on
    correctly stamped symbols (:issue:`227`).
    """
    monkeypatch.setattr(gate, "_is_shallow", lambda: True)
    assert gate.target_version() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.pixi/envs/devs/bin/python -m pytest tests/test_api_docstrings.py -k target_version -v`
Expected: FAIL — `AttributeError: module has no attribute 'target_version'`.

- [ ] **Step 3: Write minimal implementation**

```python
def _is_shallow() -> bool:
    """Report whether the checkout is shallow.

    Returns
    -------
    bool
        True when git reports a shallow repository.
    """
    result = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "--is-shallow-repository"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO,
    )
    return result.stdout.strip() == "true"


def _scm_version() -> str:
    """Return the version setuptools_scm derives for this checkout.

    Returns
    -------
    str
        A PEP 440 version, e.g. ``"0.2.0.dev3"``.
    """
    from setuptools_scm import get_version  # noqa: PLC0415

    return str(get_version(root=str(REPO)))


def target_version() -> str | None:
    """Return the base version the next tag will carry.

    Returns
    -------
    str or None
        The base version, e.g. ``"0.1.0"``; ``None`` when the checkout is
        shallow and the derivation cannot be trusted.
    """
    if _is_shallow():
        return None
    from packaging.version import Version  # noqa: PLC0415

    return Version(_scm_version()).base_version
```

Add `import subprocess` to the imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `.pixi/envs/devs/bin/python -m pytest tests/test_api_docstrings.py -k target_version -v`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add .github/scripts/check_api_docstrings.py tests/test_api_docstrings.py
git commit -m "Derive the target version, refusing a shallow checkout"
```

---

### Task 4: The `versionadded` rule and the gate entry point

**Files:**
- Modify: `.github/scripts/check_api_docstrings.py`
- Test: `tests/test_api_docstrings.py`

**Interfaces:**
- Consumes: `published_objects()`, `PublicObject` (Task 1); `target_version()` (Task 3).
- Produces: `cited_version(doc: str) -> str | None`, `check_versionadded(entries, target) -> list[str]` returning human-readable violation lines, and `main() -> int`.

**The rule, phase 1.** While no tag exists nothing can predate the first release, so every object must cite **exactly** the target. That is total and exact, and needs no snapshot. {issue}`227` records the phase-2 rules that take over once `v0.1.0` lands.

- [ ] **Step 1: Write the failing test**

```python
GOOD = """Summary line.

Notes
-----
.. versionadded:: 0.1.0
"""

NO_NOTES = "Summary line.\n"

WRONG = """Summary line.

Notes
-----
.. versionadded:: 0.9.9
"""


def test_cited_version_reads_the_directive():
    assert gate.cited_version(GOOD) == "0.1.0"


def test_cited_version_is_none_without_a_directive():
    assert gate.cited_version(NO_NOTES) is None


def test_cited_version_ignores_a_single_colon():
    """A one-colon directive renders as nothing, so it does not count.

    numpydoc's `GL10` catches this for `versionadded`, but the gate must not
    depend on another tool having run first.
    """
    assert gate.cited_version("Notes\n-----\n.. versionadded: 0.1.0\n") is None


def test_check_reports_a_missing_directive():
    entry = gate.PublicObject(
        "tephpy.thing", "function", type("O", (), {"__doc__": NO_NOTES})
    )
    problems = gate.check_versionadded([entry], "0.1.0")
    assert len(problems) == 1
    assert "tephpy.thing" in problems[0]
    assert "no versionadded" in problems[0]


def test_check_reports_a_version_that_is_not_the_target():
    entry = gate.PublicObject(
        "tephpy.thing", "function", type("O", (), {"__doc__": WRONG})
    )
    problems = gate.check_versionadded([entry], "0.1.0")
    assert len(problems) == 1
    assert "0.9.9" in problems[0]


def test_check_accepts_the_target():
    entry = gate.PublicObject(
        "tephpy.thing", "function", type("O", (), {"__doc__": GOOD})
    )
    assert gate.check_versionadded([entry], "0.1.0") == []


def test_check_skips_the_version_comparison_without_a_target():
    """A shallow checkout still checks presence, just not the value."""
    entry = gate.PublicObject(
        "tephpy.thing", "function", type("O", (), {"__doc__": WRONG})
    )
    assert gate.check_versionadded([entry], None) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.pixi/envs/devs/bin/python -m pytest tests/test_api_docstrings.py -k "cited or check_" -v`
Expected: FAIL — `AttributeError: module has no attribute 'cited_version'`.

- [ ] **Step 3: Write minimal implementation**

```python
#: The house directive. ``version-added`` is Sphinx 9 only and the docs floor
#: is ``sphinx>=8.0``, so the alias is what this repository writes (:issue:`227`).
DIRECTIVE = re.compile(r"^\s*\.\.\s+versionadded::\s*(\S+)\s*$", re.MULTILINE)


def cited_version(doc: str) -> str | None:
    """Return the version a docstring's ``versionadded`` cites.

    Parameters
    ----------
    doc : str
        The docstring, already dedented.

    Returns
    -------
    str or None
        The cited version, or ``None`` when the directive is absent or
        malformed (a single colon renders as nothing, so it does not count).
    """
    match = DIRECTIVE.search(doc or "")
    return match.group(1) if match else None


def check_versionadded(entries, target: str | None) -> list[str]:
    """Check each entry carries the directive, citing `target`.

    Parameters
    ----------
    entries : iterable of PublicObject
        The published objects to check.
    target : str or None
        The base version the next tag will carry; ``None`` skips the value
        comparison and checks presence only.

    Returns
    -------
    list of str
        One line per violation, empty when the corpus is clean.
    """
    problems = []
    for entry in entries:
        doc = inspect.getdoc(entry.obj) or ""
        cited = cited_version(doc)
        if cited is None:
            problems.append(
                f"{entry.name} ({entry.role}): no versionadded directive in a "
                f"Notes section"
            )
        elif target is not None and cited != target:
            problems.append(
                f"{entry.name} ({entry.role}): versionadded cites {cited}, "
                f"expected {target}"
            )
    return problems


def main() -> int:
    """Run the gate.

    Returns
    -------
    int
        ``0`` when clean, ``1`` when any rule reports a violation.
    """
    entries = published_objects()
    target = target_version()
    problems = check_versionadded(entries, target)
    if problems:
        print(  # noqa: T201 -- gate output
            f"{len(problems)} published API object(s) fail the versionadded "
            f"rule (docs-style, :issue:`227`):\n"
        )
        for line in problems:
            print(f"  {line}")  # noqa: T201
        return 1
    print(f"versionadded ok: {len(entries)} published objects")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Add `import re` to the imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `.pixi/envs/devs/bin/python -m pytest tests/test_api_docstrings.py -v`
Expected: PASS.

- [ ] **Step 5: Run the gate against the real corpus, expecting it to fail**

Run: `.pixi/envs/devs/bin/python .github/scripts/check_api_docstrings.py`
Expected: exit 1, reporting **94** objects with no directive. That number is the Task 5 worklist.

- [ ] **Step 6: Commit**

```bash
git add .github/scripts/check_api_docstrings.py tests/test_api_docstrings.py
git commit -m "Check every published API docstring cites the target version"
```

---

### Task 5: Stamp the 94 docstrings

**Files:**
- Modify: `src/tephpy/**/*.py` (94 docstrings)

**Interfaces:**
- Consumes: `published_objects()` (Task 1).
- Produces: a corpus the Task 4 gate passes on.

**Generate the edit; do not type it 94 times.** Hand-stamping and then running the gate makes a later disagreement ambiguous between a gate bug and a missed stamp. Driving the edit from the enumerator makes the gate green by construction.

- [ ] **Step 1: Write the one-shot stamping script**

Write to the scratchpad (this script is a tool, not a deliverable — it is not committed):

```python
"""Append a Notes/versionadded section to every unstamped published docstring."""

from __future__ import annotations

import ast
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location(
    "gate", ".github/scripts/check_api_docstrings.py"
)
gate = importlib.util.module_from_spec(spec)
sys.modules["gate"] = gate
spec.loader.exec_module(gate)

TARGET = gate.target_version()
BLOCK = f"\n    Notes\n    -----\n    .. versionadded:: {TARGET}\n\n    "

# Group the unstamped objects by the file that defines them, then walk each
# file's AST to find each docstring's exact end offset, and insert from the
# bottom up so earlier offsets stay valid.
```

The mechanics that matter, because they are where a bulk edit goes wrong:

1. Resolve each object to its defining file with `inspect.getsourcefile`, and its docstring node via `ast.parse` on that file — matching by `__qualname__`, not by name.
2. **Insert before the closing quotes**, using the docstring node's `end_lineno`/`end_col_offset`, so the existing text is untouched.
3. **Apply edits bottom-up per file** so earlier insertions do not shift later offsets.
4. **Match the indentation of the docstring's own body**, not a fixed four spaces — methods are indented eight.
5. A one-line docstring (`"""Summary."""`) must first be expanded to the multi-line form; there are such docstrings in `exceptions.py`.

- [ ] **Step 2: Run it, then check the gate**

Run:
```bash
.pixi/envs/devs/bin/python /tmp/.../stamp.py
.pixi/envs/devs/bin/python .github/scripts/check_api_docstrings.py
```
Expected: `versionadded ok: 94 published objects`.

- [ ] **Step 3: Verify nothing else broke**

Run: `pixi run lint && pixi run tests`
Expected: all hooks pass (numpydoc `GL07` is the one to watch — `Notes` must come after `Raises`), 1677+ tests pass.

- [ ] **Step 4: Verify it renders**

Run: `pixi run docs`
Expected: clean build. Then confirm the directive reaches a real page:

```bash
grep -c "Added in version 0.1.0" docs/_build/html/reference/generated/api/tephpy/calc/index.html
```
Expected: a non-zero count.

- [ ] **Step 5: Commit**

```bash
git add src/tephpy
git commit -m "Stamp the published API with the version it arrived in"
```

---

### Task 6: Register the gate, state the policy, add the fragment

**Files:**
- Modify: `.pre-commit-config.yaml`
- Modify: `docs/src/developer/docs-style.rst`
- Create: `changelog/<PR>.internal.rst`
- Test: `tests/test_api_docstrings.py`

**Interfaces:**
- Consumes: everything above.
- Produces: the enforced policy.

- [ ] **Step 1: Write the failing test**

```python
def test_the_gate_is_registered_in_pre_commit():
    """A gate nobody runs is a gate that does not exist."""
    config = (REPO / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "check_api_docstrings.py" in config
    assert "published API docstrings carry versionadded" in config
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.pixi/envs/devs/bin/python -m pytest tests/test_api_docstrings.py -k pre_commit -v`
Expected: FAIL.

- [ ] **Step 3: Register the hook**

Append to the `- repo: local` block in `.pre-commit-config.yaml`, after `check-glossary-links`:

```yaml
      # A published API object with no `versionadded` leaves a reader unable to
      # tell when it arrived, and numpydoc has no check for it (:issue:`227`).
      # Runs over the whole package rather than the staged files: the surface is
      # defined by what the documentation publishes, not by what this commit
      # touched.
      - id: check-api-docstrings
        name: published API docstrings carry versionadded
        entry: .github/scripts/check_api_docstrings.py
        language: python
        additional_dependencies: ["packaging", "setuptools_scm"]
        always_run: true
        pass_filenames: false
```

- [ ] **Step 4: State the policy in docs-style.rst**

Add a section, which is also the living answer {issue}`225` asks for:

> **Every published API object records the version it arrived in.** A ``Notes``
> section carrying ``.. versionadded::`` is the last section of the docstring, and
> ``check_api_docstrings.py`` enforces it — numpydoc does not, and has no ``RS``-family
> check for ``Raises`` either, so neither is enforced by ``numpydoc-validation``
> whatever a plan may say. Write ``versionadded``, not Sphinx 9's ``version-added``:
> the documentation floor is ``sphinx>=8.0``, where the hyphenated spelling does not exist.

- [ ] **Step 5: Run the full verification**

Run: `pixi run lint && pixi run tests && pixi run docs`
Expected: all green.

- [ ] **Step 6: Add the changelog fragment and commit**

```bash
git add .pre-commit-config.yaml docs/src/developer/docs-style.rst changelog tests
git commit -m "Enforce the versionadded policy, and write it down"
```

---

## Self-Review

**Spec coverage.** {issue}`227`'s requirements map as: the enumerator → Task 1, pinned by Task 2; `versionadded` presence → Task 4; `cited == target` phase 1 → Tasks 3 and 4; the shallow-clone caveat → Task 3 Step 1's third test and `target_version()` returning `None`; the spelling decision → Global Constraints and Task 6 Step 4; the stamping → Task 5. Phase 2 (the API-surface snapshot) is deliberately **out of scope** — it cannot be written until a tag exists, and {issue}`227` records it.

**Type consistency.** `PublicObject(name, role, obj)` is defined in Task 1 and used with those field names in Tasks 2, 4 and 5. `published_objects()`, `target_version()`, `cited_version()`, `check_versionadded()` and `main()` keep their signatures across tasks. `STAMPED_ROLES` is defined in Task 1 and consumed by Task 2's `ROLE_OF` mapping.

**Known risk.** Task 1's implementation is a first cut; Task 2 exists precisely because it is expected to disagree with the real inventory on the first run. That is the intended workflow, not a failure — reconcile the enumerator, never the expectation.

---

## Execution notes

Recorded on completion, because a plan is frozen once its implementation merges
(docs spec §3.4) and two things did not go as written above.

**Task 6: the gate is a test, not a pre-commit hook.** Registered as written, it
failed immediately — pre-commit builds an isolated environment per hook, and this
gate imports `tephpy`. The repository's other local hooks (`check_citations`,
`check_github_references`, `check_glossary_links`) are pure-stdlib text scanners,
which is why they work there. Listing numpy, matplotlib, MetPy, pandas, xarray
and pint as `additional_dependencies` would restate `requirements/pypi-core.txt`
and drift from it, and `pre-commit.ci` has no pixi environment to borrow. So
enforcement moved to `tests/test_api_docstrings.py`, which runs where the package
is installed and on every pull request; the script remains the developer-facing
report. `docs-style.rst` says so.

**Task 2 was load-bearing, exactly as hoped.** The first enumeration found 156
objects against the published 94. All 62 extra were re-exports, fixed by using
`vars` rather than `dir` and requiring a module member's `__module__` to be the
module itself. `tephpy.config` needed a separate walk, and measurement corrected
the guess: a build publishes its four *methods* and not its `source` property.

**Two adjacent findings, neither in scope.** `version_scheme =
"release-branch-semver"` is deprecated upstream in favour of
`semver-pep440-release-branch` ({issue}`228`) — the warning is suppressed where
the gate reads it rather than renamed here, because version derivation is
release-critical configuration. And adding a fourth documentation gate meant
updating four registries, not one: the pixi task, `ci-docs.yml`,
`tests/test_docs_workflow.py`'s `GATES`, and `floors_diagnose.EXERCISE`.
