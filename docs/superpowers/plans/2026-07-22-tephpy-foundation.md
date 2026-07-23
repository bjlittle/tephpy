# tephpy Foundation & Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up an installable, linted, type-checked, tested, documented, CI-gated `tephpy` package skeleton that meets the geovista engineering standard, so subsequent plans add domain code onto a solid base.

**Architecture:** `src/` layout package built with `setuptools` + `setuptools_scm`; pixi is the primary environment/workflow tool (config in `pyproject.toml`); quality enforced by ruff (`ALL`), mypy `strict`, numpydoc, and the geovista pre-commit suite; docs are a Diátaxis skeleton on `pydata-sphinx-theme` with `sphinx-autoapi` and towncrier; CI runs the v1 core gates.

**Tech Stack:** Python 3.12/3.13/3.14, setuptools_scm, pixi, ruff, mypy, pytest + pytest-cov + hypothesis + pytest-mpl, Sphinx (pydata-sphinx-theme, sphinx-autoapi, numpydoc, myst-nb, sphinx-gallery), towncrier, pre-commit, GitHub Actions.

This is **Plan 1 of 7** (see the spec's plan roadmap, §10). It produces working software: `pip install -e .` succeeds, `import tephpy` exposes a `setuptools_scm` version, `pixi run tests` and `pixi run docs` pass, and pre-commit is green. No tephigram functionality yet — that begins in Plan 2.

**Spec:** `docs/superpowers/specs/2026-07-22-tephpy-design.md` (§8 is the authority for this plan).

## Global Constraints

Every task's requirements implicitly include these, copied verbatim from the spec:

- **Python support (SPEC 0):** 3.12, 3.13, and 3.14 — the full SPEC 0 window as of 2026-07. `requires-python = ">=3.12"`.
- **Platforms (pixi):** `linux-64` only — the initial platform support. Multi-OS (`osx-arm64`, `osx-64`, `win-64`) is a deliberate future expansion, not an omission.
- **Build backend:** `setuptools` + `setuptools_scm`; version written to `src/tephpy/_version.py` (git-ignored, never committed).
- **Runtime dependencies:** `matplotlib`, `numpy`, `scipy`, `pint`, `metpy` (all conda-forge).
- **Lint/format:** ruff `select = ["ALL"]` with the curated ignore list; numpy docstring convention; isort `required-imports = ["from __future__ import annotations"]`; `CPY001` copyright-header enforcement.
- **Copyright header (every source file, verbatim regex target):**
  ```
  # Copyright (c) 2026, tephpy Contributors.
  #
  # This file is part of tephpy and is distributed under the 3-Clause BSD license.
  # See the LICENSE file in the package root directory for licensing details.
  ```
- **Types:** mypy `strict` over `src/tephpy`, `warn_unreachable = true`; ship `py.typed`.
- **Docs theme:** `pydata-sphinx-theme` (deliberate deviation from geovista's sphinx-book-theme).
- **Docs titles:** Chicago Manual of Style headline style with the documented exceptions (§8.6). Review-enforced; no build gate.
- **Changelog:** towncrier fragments in `changelog/<PR>.<type>.rst`; the geovista type taxonomy.
- **CI hygiene:** SHA-pinned actions, `permissions: {}` default, `persist-credentials: false`, `concurrency` cancel-in-progress, pixi via `prefix-dev/setup-pixi` with `frozen: true`.
- **License:** BSD-3-Clause; holder "tephpy Contributors" (matches the `LICENSE`).

**Version pins below** are copied from a fresh geovista checkout (2026-07). Where a pin may have moved, the pre-commit `autoupdate` and pixi solve will refresh it; treat them as known-good starting points, not hard requirements.

---

## File structure created by this plan

```
pyproject.toml                      # metadata, tool configs, [tool.pixi.*]
pixi.lock                           # committed, binary-merge
MANIFEST.in
.gitattributes                      # export-subst + pixi.lock rules
.git_archival.txt
.pre-commit-config.yaml
README.md                           # badges + one-liner
CHANGELOG.rst                       # empty until first release
CITATION.cff
codecov.yml
CODE_OF_CONDUCT.md
CONTRIBUTING.md
SECURITY.md
AGENTS.md
requirements/
  pypi-core.txt
  pypi-optional-test.txt
  pypi-optional-docs.txt
  pypi-optional-devs.txt
changelog/
  README.md
  template.rst
  .gitignore                        # keep dir, ignore built fragments? (keep dir)
src/tephpy/
  __init__.py
  py.typed
tests/
  __init__.py
  test_import.py
  AGENTS.md
docs/
  Makefile
  make.bat
  AGENTS.md
  src/
    conf.py
    index.rst
    refs.bib
    _static/.gitkeep
    tutorials/index.rst
    howtos/index.rst
    explanation/index.rst
    reference/index.rst
    reference/glossary.rst
    reference/changelog.rst
    developer/index.rst
    developer/docs-style.rst        # CMOS title rule + glossary rules
.github/
  dependabot.yml
  labeler.yml
  CODEOWNERS
  pull_request_template.md
  ISSUE_TEMPLATE/config.yml
  ISSUE_TEMPLATE/bug-report.md
  ISSUE_TEMPLATE/feature-request.md
  ISSUE_TEMPLATE/documentation.md
  workflows/
    ci-tests.yml
    ci-docs.yml
    ci-wheels.yml
    ci-changelog.yml
    ci-citation.yml
    codeql.yml
```

---

## Task 1: Package skeleton and setuptools_scm versioning

**Files:**
- Create: `pyproject.toml` (minimal — grows in later tasks)
- Create: `src/tephpy/__init__.py`
- Create: `src/tephpy/py.typed` (empty)
- Create: `.gitattributes`
- Create: `.git_archival.txt`
- Create: `MANIFEST.in`
- Modify: `.gitignore` (append `_version.py` and pixi dirs)

**Interfaces:**
- Produces: importable package `tephpy` with `tephpy.__version__: str`.

- [ ] **Step 1: Write the failing test**

Create `tests/__init__.py` (empty) and `tests/test_import.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Smoke tests for the tephpy package skeleton."""

from __future__ import annotations

import tephpy


def test_package_imports() -> None:
    """tephpy imports and exposes a non-empty version string."""
    assert isinstance(tephpy.__version__, str)
    assert tephpy.__version__


def test_version_is_pep440() -> None:
    """The setuptools_scm version parses as a PEP 440 version."""
    from packaging.version import Version

    Version(tephpy.__version__)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_import.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tephpy'` (package not installed yet).

- [ ] **Step 3: Create the package and build configuration**

Create `src/tephpy/py.typed` as an empty file.

Create `src/tephpy/__init__.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Plot and analyse tephigrams.

``tephpy`` renders tephigrams on a rotated temperature-entropy coordinate
system and delegates thermodynamic analysis to MetPy.
"""

from __future__ import annotations

try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

__all__ = ["__version__"]
```

Create `pyproject.toml` (this minimal version grows in Tasks 2–8):

```toml
[build-system]
requires = ["setuptools>=77.0.3", "setuptools_scm>=8"]
build-backend = "setuptools.build_meta"

[project]
name = "tephpy"
description = "Plot and analyse tephigrams, with MetPy-powered thermodynamic analysis."
authors = [{ name = "tephpy Contributors" }]
license = "BSD-3-Clause"
license-files = ["LICENSE"]
requires-python = ">=3.12"
dynamic = ["dependencies", "optional-dependencies", "readme", "version"]
keywords = ["tephigram", "meteorology", "thermodynamics", "sounding", "matplotlib"]
classifiers = [
  "Development Status :: 1 - Planning",
  "Intended Audience :: Science/Research",
  "Operating System :: OS Independent",
  "Programming Language :: Python :: 3 :: Only",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Programming Language :: Python :: 3.14",
  "Topic :: Scientific/Engineering :: Atmospheric Science",
  "Topic :: Scientific/Engineering :: Visualization",
]

[project.urls]
Repository = "https://github.com/bjlittle/tephpy"
Issues = "https://github.com/bjlittle/tephpy/issues"

[tool.setuptools.dynamic]
readme = { file = "README.md", content-type = "text/markdown" }

[tool.setuptools.packages.find]
where = ["src"]
include = ["tephpy*"]

[tool.setuptools_scm]
version_scheme = "release-branch-semver"
local_scheme = "dirty-tag"
version_file = "src/tephpy/_version.py"
```

Create `.git_archival.txt`:

```
node: $Format:%H$
node-date: $Format:%cI$
describe-name: $Format:%(describe:tags=true,match=*[0-9]*)$
```

Create `.gitattributes`:

```
.git_archival.txt  export-subst
pixi.lock          merge=binary linguist-language=YAML linguist-generated=true
```

Create `MANIFEST.in`:

```
include LICENSE README.md CHANGELOG.rst CITATION.cff
include src/tephpy/py.typed
recursive-include requirements *.txt
exclude src/tephpy/_version.py
prune .github
prune docs/superpowers
```

Append to `.gitignore`:

```
# setuptools_scm generated version file
src/tephpy/_version.py

# pixi
.pixi/
```

- [ ] **Step 4: Install and run the tests**

Run:
```bash
python -m pip install -e . packaging pytest
python -m pytest tests/test_import.py -q
```
Expected: PASS — 2 passed. `python -c "import tephpy; print(tephpy.__version__)"` prints a `0.1.dev…+…` style version derived from git.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ tests/ .gitattributes .git_archival.txt MANIFEST.in .gitignore
git commit -m "feat: package skeleton with setuptools_scm versioning"
```

---

## Task 2: Dependency wiring (core + optional extras)

**Files:**
- Create: `requirements/pypi-core.txt`
- Create: `requirements/pypi-optional-test.txt`
- Create: `requirements/pypi-optional-docs.txt`
- Create: `requirements/pypi-optional-devs.txt`
- Modify: `pyproject.toml` (add `[tool.setuptools.dynamic]` dependency file references)

**Interfaces:**
- Produces: `pip install tephpy[test]`, `[docs]`, `[devs]` extras resolvable; runtime imports available.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_import.py`:

```python
def test_runtime_dependencies_importable() -> None:
    """The declared runtime dependencies import."""
    import matplotlib  # noqa: F401
    import metpy  # noqa: F401
    import numpy  # noqa: F401
    import pint  # noqa: F401
    import scipy  # noqa: F401
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_import.py::test_runtime_dependencies_importable -q`
Expected: FAIL — `ModuleNotFoundError` for `metpy` (not yet installed).

- [ ] **Step 3: Create requirements files and wire them in**

Create `requirements/pypi-core.txt`:

```
matplotlib>=3.9
metpy>=1.6
numpy>=2.0
pint>=0.24
scipy>=1.13
```

Create `requirements/pypi-optional-test.txt`:

```
hypothesis>=6.100
pytest>=8.0
pytest-cov>=5.0
pytest-mpl>=0.17
```

Create `requirements/pypi-optional-docs.txt`:

```
myst-nb>=1.1
numpydoc>=1.8
pydata-sphinx-theme>=0.16
sphinx>=8.0
sphinx-autoapi>=3.3
sphinx-copybutton>=0.5
sphinx-design>=0.6
sphinx-gallery>=0.17
sphinx-togglebutton>=0.3
sphinx_changelog>=1.6
sphinxcontrib-bibtex>=2.6
towncrier>=24.8
```

Create `requirements/pypi-optional-devs.txt`:

```
check-manifest>=0.49
pre-commit>=4.0
ruff>=0.15
```

Add to `pyproject.toml` under `[tool.setuptools.dynamic]` (merge with the existing `readme` line):

```toml
[tool.setuptools.dynamic]
dependencies = { file = ["requirements/pypi-core.txt"] }
readme = { file = "README.md", content-type = "text/markdown" }

[tool.setuptools.dynamic.optional-dependencies]
test = { file = ["requirements/pypi-optional-test.txt"] }
docs = { file = ["requirements/pypi-optional-docs.txt"] }
devs = { file = ["requirements/pypi-optional-devs.txt"] }
```

- [ ] **Step 4: Install and run the tests**

Run:
```bash
python -m pip install -e ".[test]"
python -m pytest tests/test_import.py -q
```
Expected: PASS — 3 passed (all runtime deps import).

- [ ] **Step 5: Commit**

```bash
git add requirements/ pyproject.toml tests/test_import.py
git commit -m "feat: declare core runtime and optional dependencies"
```

---

## Task 3: pytest and coverage configuration

**Files:**
- Modify: `pyproject.toml` (add `[tool.pytest.ini_options]`, `[tool.coverage.*]`)
- Create: `codecov.yml`

**Interfaces:**
- Produces: `pytest` runs from repo root with strict config; coverage collected for `tephpy`.

- [ ] **Step 1: Add pytest and coverage config to `pyproject.toml`**

```toml
[tool.pytest.ini_options]
addopts = ["--import-mode=importlib", "--strict-config", "--strict-markers", "-ra"]
minversion = "8.0"
testpaths = ["tests"]
xfail_strict = true
filterwarnings = ["error"]
markers = ["mpl_image_compare: matplotlib image comparison tests"]

[tool.coverage.run]
branch = true
source = ["tephpy"]
omit = ["*/_version.py"]

[tool.coverage.report]
exclude_also = ["if TYPE_CHECKING:", "raise NotImplementedError", "@overload"]
show_missing = true
```

- [ ] **Step 2: Run pytest to verify strict config is accepted**

Run: `python -m pytest -q`
Expected: PASS — 3 passed, no "unknown config option" errors (proves `--strict-config` is satisfied).

- [ ] **Step 3: Create `codecov.yml`**

```yaml
coverage:
  status:
    project:
      default:
        target: auto
        threshold: 5%
    patch: false
comment: false
ignore:
  - "src/tephpy/examples/**"
  - "src/tephpy/_version.py"
```

- [ ] **Step 4: Verify coverage runs**

Run: `python -m pytest --cov --cov-report=term-missing -q`
Expected: PASS — coverage table printed for `tephpy`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml codecov.yml
git commit -m "feat: configure pytest strict mode and coverage"
```

---

## Task 4: Ruff lint + format with copyright headers

**Files:**
- Modify: `pyproject.toml` (add `[tool.ruff*]`)
- Modify: all `.py` files (ensure BSD header present — already added in Tasks 1–2)

**Interfaces:**
- Produces: `ruff check` and `ruff format --check` clean across the repo.

- [ ] **Step 1: Add ruff config to `pyproject.toml`**

```toml
[tool.ruff]
line-length = 88
src = ["src", "tests", "docs/src"]

[tool.ruff.format]
docstring-code-format = true

[tool.ruff.lint]
extend-select = ["CPY001"]
preview = true
explicit-preview-rules = true
select = ["ALL", "D212"]
ignore = [
  "COM812",  # trailing comma missing (conflicts with formatter)
  "COM819",  # trailing comma prohibited
  "D105",    # missing docstring in magic method
  "FBT002",  # boolean default positional argument
  "FIX002",  # line contains TODO
  "ISC001",  # implicit string concat (conflicts with formatter)
  "N806",    # variable in function should be lowercase (T, P are physics symbols)
  "PLR2004", # magic value in comparison
  "S101",    # use of assert (pytest)
  "TD003",   # missing issue link after TODO
]

[tool.ruff.lint.flake8-copyright]
notice-rgx = '''
# Copyright \(c\) 2026, tephpy Contributors\.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license\.
# See the LICENSE file in the package root directory for licensing details\.
'''

[tool.ruff.lint.isort]
force-sort-within-sections = true
known-first-party = ["tephpy"]
required-imports = ["from __future__ import annotations"]

[tool.ruff.lint.pydocstyle]
convention = "numpy"

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["ANN001", "ANN201", "SLF001", "D103"]
"docs/src/conf.py" = ["INP001", "A001"]
```

- [ ] **Step 2: Run ruff to see current state**

Run: `python -m pip install ruff && ruff check . && ruff format --check .`
Expected: If any file lacks the copyright header or import ordering, ruff reports it (e.g. `CPY001`). Note the failures.

- [ ] **Step 3: Fix reported issues**

Apply `ruff check --fix .` then `ruff format .`. Manually add the copyright header block (from Global Constraints) to any file `CPY001` still flags. Confirm `src/tephpy/__init__.py` and `tests/*.py` all start with the 4-line header.

- [ ] **Step 4: Verify clean**

Run: `ruff check . && ruff format --check .`
Expected: PASS — "All checks passed!" and no format diffs.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: configure ruff (ALL) with BSD copyright-header enforcement"
```

---

## Task 5: mypy strict typing

**Files:**
- Modify: `pyproject.toml` (add `[tool.mypy]`)

**Interfaces:**
- Produces: `mypy` clean over `src/tephpy`.

- [ ] **Step 1: Add mypy config to `pyproject.toml`**

```toml
[tool.mypy]
strict = true
warn_unreachable = true
enable_error_code = ["ignore-without-code", "redundant-expr", "truthy-bool"]
files = ["src/tephpy"]

[[tool.mypy.overrides]]
# MetPy and pint ship partial/absent stubs; do not fail on their imports.
module = ["metpy.*", "pint.*"]
ignore_missing_imports = true
```

- [ ] **Step 2: Run mypy to verify it passes**

Run: `python -m pip install mypy && mypy`
Expected: PASS — "Success: no issues found in 1 source file" (only `__init__.py` exists so far).

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat: configure mypy strict typing"
```

---

## Task 6: numpydoc validation and towncrier changelog

**Files:**
- Modify: `pyproject.toml` (add `[tool.numpydoc_validation]`, `[tool.towncrier]`)
- Create: `changelog/README.md`
- Create: `changelog/template.rst`
- Create: `changelog/1.internal.rst` (first fragment)
- Create: `CHANGELOG.rst` (empty)

**Interfaces:**
- Produces: `towncrier build --draft` renders the pending fragment; numpydoc rules registered for the pre-commit hook (Task 7).

- [ ] **Step 1: Add numpydoc and towncrier config to `pyproject.toml`**

```toml
[tool.numpydoc_validation]
checks = ["all", "GL01", "GL02", "GL03", "SA01", "ES01", "EX01", "YD01"]

[tool.towncrier]
directory = "changelog"
filename = "CHANGELOG.rst"
package = "tephpy"
package_dir = "src"
template = "changelog/template.rst"

[[tool.towncrier.type]]
directory = "breaking"
name = "💣 Breaking Changes"
showcontent = true

[[tool.towncrier.type]]
directory = "feature"
name = "✨ New Features"
showcontent = true

[[tool.towncrier.type]]
directory = "enhancement"
name = "🚀 Enhancements"
showcontent = true

[[tool.towncrier.type]]
directory = "bugfix"
name = "🐛 Bug Fixes"
showcontent = true

[[tool.towncrier.type]]
directory = "dependency"
name = "🔗 Dependencies"
showcontent = true

[[tool.towncrier.type]]
directory = "documentation"
name = "📚 Documentation"
showcontent = true

[[tool.towncrier.type]]
directory = "internal"
name = "💼 Internal"
showcontent = true

[[tool.towncrier.type]]
directory = "misc"
name = "🧰 Miscellaneous"
showcontent = true
```

- [ ] **Step 2: Create the changelog scaffolding**

Create empty `CHANGELOG.rst` (zero bytes).

Create `changelog/template.rst`:

```rst
{% for section, _ in sections.items() %}
{% for category, val in definitions.items() if category in sections[section] %}
{{ definitions[category]['name'] }}
{{ "^" * (definitions[category]['name']|length + 2) }}

{% for text, values in sections[section][category].items() %}
- {{ text }} ({{ values|join(', ') }})
{% endfor %}

{% endfor %}
{% endfor %}
```

Create `changelog/README.md`:

```markdown
# Changelog fragments

Every pull request adds a news fragment here named `<PR>.<type>.rst`, where
`<type>` is one of: `breaking`, `feature`, `enhancement`, `bugfix`,
`dependency`, `documentation`, `internal`, `misc`. The content is one short,
sentence-case line. Fragments are assembled into `CHANGELOG.rst` at release
time by towncrier.
```

Create `changelog/1.internal.rst`:

```
Established the project foundation: packaging, pixi workflow, linting, typing, tests, documentation skeleton, and CI.
```

- [ ] **Step 3: Verify towncrier renders the draft**

Run: `python -m pip install towncrier && towncrier build --draft --version 0.1.0`
Expected: Output contains the "💼 Internal" section with the fragment text. No files are modified (`--draft`).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml CHANGELOG.rst changelog/
git commit -m "feat: configure towncrier changelog and numpydoc validation"
```

---

## Task 7: Pre-commit suite

**Files:**
- Create: `.pre-commit-config.yaml`

**Interfaces:**
- Produces: `pre-commit run --all-files` passes; the same gate CI and contributors use.

- [ ] **Step 1: Create `.pre-commit-config.yaml`**

```yaml
ci:
  autofix_prs: false
  autofix_commit_msg: "style: pre-commit.ci auto-fixes"
  autoupdate_commit_msg: "chore: update pre-commit hooks"
  autoupdate_schedule: weekly

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: check-added-large-files
        exclude: "pixi.lock"
      - id: check-ast
      - id: check-case-conflict
      - id: check-merge-conflict
      - id: check-toml
      - id: check-yaml
      - id: debug-statements
      - id: end-of-file-fixer
        exclude: '\.svg$'
      - id: mixed-line-ending
      - id: no-commit-to-branch
      - id: trailing-whitespace

  - repo: https://github.com/abravalheri/validate-pyproject
    rev: v0.25
    hooks:
      - id: validate-pyproject
        additional_dependencies: ["validate-pyproject-schema-store[all]"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.21
    hooks:
      - id: ruff-check
        args: ["--fix", "--show-fixes"]
      - id: ruff-format

  - repo: https://github.com/adamchainz/blacken-docs
    rev: 1.20.0
    hooks:
      - id: blacken-docs
        additional_dependencies: ["black==24.*"]

  - repo: https://github.com/codespell-project/codespell
    rev: v2.4.2
    hooks:
      - id: codespell
        additional_dependencies: ["tomli"]
        types_or: [python, markdown, rst]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v2.3.0
    hooks:
      - id: mypy
        pass_filenames: false
        additional_dependencies: ["numpy", "types-docutils"]

  - repo: https://github.com/numpy/numpydoc
    rev: v1.11.0rc0
    hooks:
      - id: numpydoc-validation
        files: '^src/'

  - repo: https://github.com/pre-commit/pygrep-hooks
    rev: v1.10.0
    hooks:
      - id: python-check-blanket-noqa
      - id: python-check-blanket-type-ignore
      - id: python-no-eval
      - id: python-no-log-warn
      - id: python-use-type-annotations
      - id: rst-backticks
      - id: rst-directive-colons
      - id: rst-inline-touching-normal
      - id: text-unicode-replacement-char

  - repo: https://github.com/python-jsonschema/check-jsonschema
    rev: 0.37.4
    hooks:
      - id: check-dependabot
      - id: check-github-workflows
      - id: check-readthedocs

  - repo: https://github.com/scientific-python/cookie
    rev: 2026.06.18
    hooks:
      - id: sp-repo-review
        args: ["--show=errskip"]

  - repo: https://github.com/ComPWA/taplo-pre-commit
    rev: v0.9.3
    hooks:
      - id: taplo-format
        args: ["--option", "reorder_keys=true"]

  - repo: https://github.com/sphinx-contrib/sphinx-lint
    rev: v1.0.2
    hooks:
      - id: sphinx-lint

  - repo: https://github.com/zizmorcore/zizmor-pre-commit
    rev: v1.26.1
    hooks:
      - id: zizmor
```

- [ ] **Step 2: Configure repo-review ignores in `pyproject.toml`**

Add:

```toml
[tool.repo-review]
ignore = [
  "PC180",  # prettier (not used)
  "PP006",  # dev dependency group
]
```

- [ ] **Step 3: Run pre-commit**

Run:
```bash
python -m pip install pre-commit
pre-commit run --all-files
```
Expected: All hooks pass. `check-github-workflows`/`check-dependabot`/`check-readthedocs` will be no-ops until those files exist (Tasks 10–12); they must not error. Fix any hook failures (most auto-fix) and re-run until green.

Note: `no-commit-to-branch` blocks commits to `main`. Development happens on a branch — create one now if not already: `git switch -c foundation` before committing here.

- [ ] **Step 4: Commit**

```bash
git add .pre-commit-config.yaml pyproject.toml
git commit -m "feat: add geovista-standard pre-commit suite"
```

---

## Task 8: pixi environments, tasks, and lockfile

**Files:**
- Modify: `pyproject.toml` (add `[tool.pixi.*]` tables)
- Create: `pixi.lock` (generated)

**Interfaces:**
- Produces: `pixi run tests` and `pixi run -e docs docs` work in reproducible pixi environments; `pixi.lock` committed.

- [ ] **Step 1: Add pixi configuration to `pyproject.toml`**

```toml
[tool.pixi.workspace]
channels = ["conda-forge"]
platforms = ["linux-64"]

[tool.pixi.pypi-dependencies]
tephpy = { path = ".", editable = true }

[tool.pixi.dependencies]
matplotlib-base = ">=3.9"
metpy = ">=1.6"
numpy = ">=2.0"
pint = ">=0.24"
scipy = ">=1.13"
setuptools = ">=77.0.3"
setuptools-scm = ">=8"

[tool.pixi.environments]
# default carries the tooling features so unqualified `pixi run <task>`
# resolves without ambiguity (pixi errors when a task exists in 2+ non-default envs).
default = { features = ["test", "docs", "devs", "py314"], solve-group = "default" }
test = { features = ["test", "devs", "py314"], solve-group = "default" }
docs = { features = ["docs", "devs", "py314"], solve-group = "default" }
devs = { features = ["test", "docs", "devs", "py314"], solve-group = "default" }
test-py312 = { features = ["test", "devs", "py312"], solve-group = "py312" }
test-py313 = { features = ["test", "devs", "py313"], solve-group = "py313" }
test-py314 = { features = ["test", "devs", "py314"], solve-group = "py314" }

[tool.pixi.feature.py312.dependencies]
python = "3.12.*"

[tool.pixi.feature.py313.dependencies]
python = "3.13.*"

[tool.pixi.feature.py314.dependencies]
python = "3.14.*"

[tool.pixi.feature.test.dependencies]
hypothesis = ">=6.100"
pytest = ">=8.0"
pytest-cov = ">=5.0"
pytest-mpl = ">=0.17"

[tool.pixi.feature.test.tasks.tests]
cmd = "pytest --cov --cov-report=xml"
description = "Run the unit test suite with coverage"

[tool.pixi.feature.test.tasks.tests-mpl-generate]
cmd = "pytest --mpl-generate-path=tests/baseline"
description = "Regenerate matplotlib image-comparison baselines"

[tool.pixi.feature.devs.dependencies]
check-manifest = ">=0.49"
mypy = ">=1.13"
pre-commit = ">=4.0"
ruff = ">=0.15"

[tool.pixi.feature.devs.tasks.lint]
cmd = "pre-commit run --all-files"
description = "Run all pre-commit hooks"

[tool.pixi.feature.docs.dependencies]
myst-nb = ">=1.1"
numpydoc = ">=1.8"
pydata-sphinx-theme = ">=0.16"
sphinx = ">=8.0"
sphinx-autoapi = ">=3.3"
sphinx-copybutton = ">=0.5"
sphinx-design = ">=0.6"
sphinx-gallery = ">=0.17"
sphinx-togglebutton = ">=0.3"
sphinx_changelog = ">=1.6"
sphinxcontrib-bibtex = ">=2.6"
towncrier = ">=24.8"

[tool.pixi.feature.docs.tasks.docs]
cmd = "make html"
cwd = "docs"
description = "Build the HTML documentation"

[tool.pixi.feature.docs.tasks.docs-clean]
cmd = "make clean"
cwd = "docs"
description = "Remove built documentation artifacts"

[tool.pixi.feature.docs.tasks.serve-html]
cmd = "python -m http.server 11000 --directory _build/html"
cwd = "docs"
description = "Serve built docs on http://localhost:11000"
```

- [ ] **Step 2: Solve and lock**

Run: `pixi install`
Expected: pixi resolves all environments and writes `pixi.lock`. If `matplotlib-base`/`metpy` versions conflict, relax the floor to what conda-forge offers and record it.

- [ ] **Step 3: Run the test task through pixi**

Run: `pixi run tests`
Expected: PASS — 3 passed (same tests as Task 2), coverage XML written.

- [ ] **Step 4: Verify the lockfile is committed as binary**

Run: `git check-attr merge -- pixi.lock`
Expected: `pixi.lock: merge: binary`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml pixi.lock
git commit -m "feat: add pixi environments, tasks, and lockfile"
```

---

## Task 9: Documentation skeleton (Diátaxis + autoapi + glossary)

**Files:**
- Create: `docs/Makefile`, `docs/make.bat`
- Create: `docs/src/conf.py`
- Create: `docs/src/index.rst`
- Create: `docs/src/refs.bib`
- Create: `docs/src/_static/.gitkeep`
- Create: `docs/src/{tutorials,howtos,explanation,reference,developer}/index.rst`
- Create: `docs/src/reference/glossary.rst`
- Create: `docs/src/reference/changelog.rst`
- Create: `docs/src/developer/docs-style.rst`
- Create: `.readthedocs.yml`

**Interfaces:**
- Produces: `pixi run docs` builds HTML with zero warnings (fail-on-warning), including an autoapi API section and a glossary page.

- [ ] **Step 1: Create the Sphinx `conf.py`**

`docs/src/conf.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Sphinx configuration for the tephpy documentation."""

from __future__ import annotations

from importlib.metadata import version as _dist_version

project = "tephpy"
author = "tephpy Contributors"
copyright = "2026, tephpy Contributors"  # noqa: A001
release = _dist_version("tephpy")
version = ".".join(release.split(".")[:2])

extensions = [
    "autoapi.extension",
    "myst_nb",
    "numpydoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_changelog",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_gallery.gen_gallery",
    "sphinx_togglebutton",
    "sphinxcontrib.bibtex",
]

# -- autoapi -----------------------------------------------------------------
autoapi_type = "python"
autoapi_dirs = ["../../src/tephpy"]
autoapi_root = "reference/generated/api"
autoapi_ignore = ["*/_version.py", "*/examples/*"]
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]
autoapi_keep_files = False
autoapi_add_toctree_entry = (
    False  # nav is the five Diátaxis entries; API lives under Reference
)
suppress_warnings = ["autoapi.python_import_resolution"]

# -- numpydoc ----------------------------------------------------------------
numpydoc_show_class_members = False

# -- bibtex ------------------------------------------------------------------
bibtex_bibfiles = ["refs.bib"]

# -- sphinx-gallery ----------------------------------------------------------
sphinx_gallery_conf = {
    "examples_dirs": [],
    "gallery_dirs": [],
}

# -- myst-nb -----------------------------------------------------------------
nb_execution_mode = "off"

# -- intersphinx -------------------------------------------------------------
intersphinx_mapping = {
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "python": ("https://docs.python.org/3/", None),
}

# -- HTML output -------------------------------------------------------------
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_title = "tephpy"
html_theme_options = {
    "github_url": "https://github.com/bjlittle/tephpy",
    "navbar_align": "left",
}

nitpicky = False
```

Note: `examples_dirs`/`gallery_dirs` are empty here; Plan 7 populates the gallery. Keeping the extension loaded now avoids a config churn later.

- [ ] **Step 2: Create the Makefile and Windows batch**

`docs/Makefile`:

```makefile
SPHINXOPTS    ?= --fail-on-warning --keep-going
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = src
BUILDDIR      = _build

.PHONY: help clean html
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

clean:
	rm -rf $(BUILDDIR) $(SOURCEDIR)/reference/generated

html:
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS)
```

`docs/make.bat`:

```bat
@ECHO OFF
if "%SPHINXBUILD%" == "" set SPHINXBUILD=sphinx-build
set SOURCEDIR=src
set BUILDDIR=_build
set SPHINXOPTS=--fail-on-warning --keep-going
%SPHINXBUILD% -b %1 %SOURCEDIR% %BUILDDIR%\%1 %SPHINXOPTS%
```

- [ ] **Step 3: Create the Diátaxis pages**

`docs/src/index.rst`:

```rst
tephpy
======

Plot and analyse :term:`tephigrams <tephigram>`.

.. grid:: 2

    .. grid-item-card:: Tutorials
        :link: tutorials/index
        :link-type: doc

        Learning-oriented lessons.

    .. grid-item-card:: How-To Guides
        :link: howtos/index
        :link-type: doc

        Goal-oriented recipes.

    .. grid-item-card:: Explanation
        :link: explanation/index
        :link-type: doc

        Understanding-oriented background.

    .. grid-item-card:: Reference
        :link: reference/index
        :link-type: doc

        Information-oriented API and glossary.

.. toctree::
    :hidden:

    tutorials/index
    howtos/index
    explanation/index
    reference/index
    developer/index
```

`docs/src/tutorials/index.rst`:

```rst
Tutorials
=========

Learning-oriented lessons will appear here as the package grows.
```

`docs/src/howtos/index.rst`:

```rst
How-To Guides
=============

Task-focused recipes will appear here as the package grows.
```

`docs/src/explanation/index.rst`:

```rst
Explanation
===========

Background on the :term:`tephigram`, its rotated temperature-entropy coordinate
system, and parcel analysis will appear here as the package grows.
```

`docs/src/reference/index.rst`:

```rst
Reference
=========

.. toctree::
    :maxdepth: 1

    generated/api/tephpy/index
    glossary
    changelog
```

`docs/src/reference/glossary.rst`:

```rst
Glossary
========

Terms are written for scientific software engineers rather than
meteorologists. Each entry states the concept plainly, then how it appears in
``tephpy``. See :doc:`../developer/docs-style` for the entry and
cross-reference rules.

.. glossary::

    tephigram
        A thermodynamic diagram that plots temperature against entropy on a
        rotated coordinate system, so that isotherms and dry adiabats form an
        exactly perpendicular straight-line grid. ``tephpy`` renders it as a
        Matplotlib projection named ``"tephigram"``.

    sounding
        A vertical profile of atmospheric measurements (pressure, temperature,
        dewpoint, wind) from a single ascent. In ``tephpy`` a sounding is
        carried by the ``Sounding`` data model (added in a later release).
```

`docs/src/reference/changelog.rst`:

```rst
Changelog
=========

.. changelog::
    :towncrier: ../../../
    :towncrier-skip-if-empty:
    :changelog_file: ../../../CHANGELOG.rst
```

`docs/src/developer/index.rst`:

```rst
Developer Guide
===============

.. toctree::
    :maxdepth: 1

    docs-style
```

`docs/src/developer/docs-style.rst` (captures the §8.6 rules verbatim for contributors):

```rst
Documentation Style
====================

Title Style
-----------

Hand-authored page and section titles use Chicago Manual of Style headline
style: capitalize the first and last words and all major words; lowercase
articles, coordinating conjunctions, prepositions, and the infinitive "to".

Preserve literal case for: code and API identifiers, filenames, config keys,
CLI commands, and paths; project and library names in their own casing
(matplotlib, numpy, pint, metpy, pixi, tephpy); and acronyms and scientific
symbols (CAPE, CIN, LCL, WMO, SPEC 0). The rule does not apply to
autoapi-generated API pages, numpydoc section headers, changelog entries, or
anything that is a full sentence (captions, admonition text, docstring
summaries), which use sentence case. Bibliography entries reproduce the
source's published title.

Glossary
--------

The glossary is written for software engineers, not meteorologists. Each entry
gives the concept in one plain sentence, then how it appears in ``tephpy`` (the
data, its units, the API type that carries it), and links deeper physics to the
Explanation quadrant.

Cross-reference the *first* mention of a glossary term per page with
``:term:``, in narrative prose only — never in titles, code blocks, API
signatures, or admonition labels. Within a definition, link related terms but
never the term itself. Keep one canonical spelling per concept.
```

`docs/src/refs.bib`:

```bibtex
@misc{amsglossary,
  author       = {{American Meteorological Society}},
  title        = {Glossary of Meteorology},
  howpublished = {\url{https://glossary.ametsoc.org/}},
  year         = {2024}
}
```

`docs/src/_static/.gitkeep`: empty file.

- [ ] **Step 4: Create `.readthedocs.yml`**

```yaml
version: 2

build:
  os: ubuntu-24.04
  tools:
    python: "3.13"
  jobs:
    post_checkout:
      - git fetch --unshallow || true
    create_environment:
      # pixi is NOT on PyPI (the `pixi` PyPI name is an unrelated project) —
      # install the real binary and invoke it by absolute path (PATH does not
      # persist between RTD job steps; $HOME does).
      - curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=v0.72.1 bash
    install:
      - $HOME/.pixi/bin/pixi install --frozen --environment docs
    build:
      html:
        - $HOME/.pixi/bin/pixi run --frozen --environment docs sphinx-build -T -b html docs/src $READTHEDOCS_OUTPUT/html
```

- [ ] **Step 5: Build the docs**

Run: `pixi run docs`
Expected: `build succeeded` with **0 warnings** (the Makefile uses `--fail-on-warning`). The output includes a `reference/generated/api/tephpy/index.html` page and a rendered `Glossary`. Fix any warning until the build is clean.

- [ ] **Step 6: Commit**

```bash
git add docs/ .readthedocs.yml
git commit -m "feat: Diataxis documentation skeleton with autoapi and glossary"
```

---

## Task 10: Community and hygiene files

**Files:**
- Create: `README.md` (replace the one-line stub)
- Create: `CITATION.cff`
- Create: `.github/dependabot.yml`
- Create: `.github/labeler.yml`
- Create: `.github/CODEOWNERS`
- Create: `.github/pull_request_template.md`
- Create: `.github/ISSUE_TEMPLATE/config.yml`
- Create: `.github/ISSUE_TEMPLATE/{bug-report,feature-request,documentation}.md`
- Create: `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`
- Create: `AGENTS.md`, `docs/AGENTS.md`, `tests/AGENTS.md`

**Interfaces:**
- Produces: schema-valid dependabot/config files (checked by pre-commit); valid `CITATION.cff`.

- [ ] **Step 1: Create `README.md`**

```markdown
# tephpy

[![SPEC 0 — Minimum Supported Dependencies](https://img.shields.io/badge/SPEC-0-green?labelColor=%23004811&color=%235CB85C)](https://scientific-python.org/specs/spec-0000/)
[![pixi Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)

Plot and analyse tephigrams. `tephpy` renders tephigrams on a rotated
temperature-entropy coordinate system and delegates thermodynamic analysis
(parcel ascent, CAPE, CIN, LCL/LFC/EL) to MetPy.

Successor to [SciTools/tephi](https://github.com/SciTools/tephi).

> **Status:** early development — the plotting and analysis API is being built
> out plan by plan. See `docs/superpowers/specs/` for the design.
```

- [ ] **Step 2: Create `CITATION.cff`**

```yaml
cff-version: 1.2.0
message: "If you use this software, please cite it using these metadata."
title: tephpy
abstract: "Plot and analyse tephigrams, with MetPy-powered thermodynamic analysis."
authors:
  - name: "tephpy Contributors"
license: BSD-3-Clause
repository-code: "https://github.com/bjlittle/tephpy"
type: software
```

- [ ] **Step 3: Create the GitHub config files**

`.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: daily
    cooldown:
      default-days: 7
    groups:
      actions:
        patterns: ["*"]
    labels: ["bot", "skip-changelog"]
    commit-message:
      prefix: "chore: "
  - package-ecosystem: pip
    directory: "/requirements"
    schedule:
      interval: weekly
    cooldown:
      default-days: 7
    groups:
      pip:
        patterns: ["*"]
    labels: ["bot", "skip-changelog"]
```

`.github/labeler.yml`:

```yaml
"type: documentation":
  - changed-files:
      - any-glob-to-any-file: ["docs/**"]
"type: spec-0":
  - head-branch: ["^spec", "^spec0"]
"type: ci":
  - changed-files:
      - any-glob-to-any-file: [".github/**"]
```

`.github/CODEOWNERS`:

```
* @bjlittle
```

`.github/pull_request_template.md`:

```markdown
## Description

<!-- What does this PR change, and why? -->

## Checklist

- [ ] Added a `changelog/<PR>.<type>.rst` news fragment (or applied `skip-changelog`).
- [ ] Tests pass (`pixi run tests`).
- [ ] Pre-commit passes (`pixi run lint`).
- [ ] Docs build (`pixi run docs`) if docs changed.
```

`.github/ISSUE_TEMPLATE/config.yml`:

```yaml
blank_issues_enabled: false
contact_links:
  - name: Question or Discussion
    url: https://github.com/bjlittle/tephpy/discussions
    about: Ask questions and discuss ideas here.
```

`.github/ISSUE_TEMPLATE/bug-report.md`:

```markdown
---
name: Bug report
about: Report a defect
labels: "type: bug"
---

## What happened

## What you expected

## Minimal reproducer

## Environment (`pixi run python -c "import tephpy; print(tephpy.__version__)"`)
```

`.github/ISSUE_TEMPLATE/feature-request.md`:

```markdown
---
name: Feature request
about: Suggest a capability
labels: "type: enhancement"
---

## Problem

## Proposed solution

## Alternatives considered
```

`.github/ISSUE_TEMPLATE/documentation.md`:

```markdown
---
name: Documentation
about: Report a docs problem or gap
labels: "type: documentation"
---

## Page / section

## Problem
```

- [ ] **Step 4: Create the community markdown files**

`CODE_OF_CONDUCT.md`:

```markdown
# Code of Conduct

This project adopts the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/), version 2.1. By participating you agree to uphold it. Report unacceptable behaviour to the maintainers via a private security advisory or direct contact.
```

`CONTRIBUTING.md`:

```markdown
# Contributing to tephpy

Thanks for your interest! Development uses [pixi](https://pixi.sh):

```bash
pixi install
pixi run tests    # run the test suite
pixi run lint     # run pre-commit
pixi run docs     # build the docs
```

Every pull request adds a `changelog/<PR>.<type>.rst` news fragment. Titles in
documentation follow Chicago Manual of Style headline style (see
`docs/src/developer/docs-style.rst`).
```

`SECURITY.md`:

```markdown
# Security Policy

Please report vulnerabilities privately via GitHub's "Report a vulnerability"
(Security advisories) for this repository, not through public issues. All
released versions are in scope until stated otherwise.
```

- [ ] **Step 5: Create the AGENTS.md files**

`AGENTS.md`:

```markdown
# Agent guidance — tephpy

`tephpy` plots and analyses tephigrams. Layered architecture: `transforms`
(T–ln θ math + Matplotlib projection) ← `plotting` ← (`calc`, `sounding`,
`io`). Thermodynamics is delegated to MetPy; units are pint quantities.

- Environments and tasks: pixi (`pixi run tests`, `pixi run lint`, `pixi run docs`).
- Every source file carries the BSD copyright header (ruff `CPY001`).
- Every PR adds a `changelog/<PR>.<type>.rst` fragment.
- Docs follow Diátaxis; titles use CMOS headline style (`docs/src/developer/docs-style.rst`).
```

`docs/AGENTS.md`:

```markdown
# Agent guidance — docs

Diátaxis quadrants under `docs/src/{tutorials,howtos,explanation,reference}`.
Theme is pydata-sphinx-theme. API reference is autoapi-generated — do not
hand-write it. Build with `pixi run docs` (fail-on-warning). Titles: CMOS
headline style; glossary entries are written for software engineers (see
`src/developer/docs-style.rst`).
```

`tests/AGENTS.md`:

```markdown
# Agent guidance — tests

pytest with strict config and `filterwarnings = ["error"]`. Image tests use
pytest-mpl (`@pytest.mark.mpl_image_compare`); baselines regenerate via
`pixi run tests-mpl-generate`. Property tests use hypothesis.
```

- [ ] **Step 6: Validate**

Run:
```bash
pre-commit run check-dependabot --all-files
pre-commit run check-github-workflows --all-files || true
pip install cffconvert && cffconvert --validate
```
Expected: `check-dependabot` passes; `cffconvert --validate` reports the file is valid. (`check-github-workflows` has nothing to check until Task 11.)

- [ ] **Step 7: Commit**

```bash
git add README.md CITATION.cff codecov.yml CODE_OF_CONDUCT.md CONTRIBUTING.md SECURITY.md AGENTS.md docs/AGENTS.md tests/AGENTS.md .github/
git commit -m "feat: add community, hygiene, and repository configuration files"
```

---

## Task 11: CI core gates (GitHub Actions)

**Files:**
- Create: `.github/workflows/ci-tests.yml`
- Create: `.github/workflows/ci-docs.yml`
- Create: `.github/workflows/ci-wheels.yml`
- Create: `.github/workflows/ci-changelog.yml`
- Create: `.github/workflows/ci-citation.yml`
- Create: `.github/workflows/codeql.yml`

**Interfaces:**
- Produces: workflow files that pass `check-github-workflows` and `zizmor`, encoding the v1 core CI gates.

Note on SHA pinning: the plan shows readable tags in comments; the implementer replaces each `uses:` with the tag's full commit SHA (`gh api repos/OWNER/REPO/commits/TAG --jq .sha`) so `zizmor` passes. The pins below list the intended tag.

- [ ] **Step 1: Create `ci-tests.yml`**

```yaml
name: ci-tests

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions: {}

jobs:
  tests:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: ["ubuntu-latest"]  # linux-64 only — the initial platform support
        environment: ["test-py312", "test-py313", "test-py314"]
    steps:
      - uses: actions/checkout@v5  # pin to SHA
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: prefix-dev/setup-pixi@v0.9.1  # pin to SHA
        with:
          environments: ${{ matrix.environment }}
          frozen: true
      - run: pixi run --frozen --environment ${{ matrix.environment }} pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v5  # pin to SHA
        if: matrix.os == 'ubuntu-latest' && matrix.environment == 'test-py314'
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
```

- [ ] **Step 2: Create `ci-docs.yml`**

```yaml
name: ci-docs

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions: {}

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5  # pin to SHA
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: prefix-dev/setup-pixi@v0.9.1  # pin to SHA
        with:
          environments: docs
          frozen: true
      - run: pixi run --frozen --environment docs make -C docs html
```

- [ ] **Step 3: Create `ci-wheels.yml`**

```yaml
name: ci-wheels

on:
  push:
    branches: [main]
    tags: ["v*"]
  pull_request:
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions: {}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5  # pin to SHA
        with:
          fetch-depth: 0
          persist-credentials: false
      - run: pipx run build
      - run: pipx run twine check dist/*
      - uses: actions/upload-artifact@v4  # pin to SHA
        with:
          name: dist
          path: dist/

  publish-testpypi:
    needs: build
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: test-pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4  # pin to SHA
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1  # pin to SHA
        with:
          repository-url: https://test.pypi.org/legacy/
          skip-existing: true

  publish-pypi:
    needs: build
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4  # pin to SHA
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1  # pin to SHA
```

- [ ] **Step 4: Create `ci-changelog.yml`**

```yaml
name: ci-changelog

on:
  pull_request:
    types: [opened, reopened, synchronize, labeled, unlabeled]

permissions: {}

jobs:
  changelog:
    if: ${{ !contains(github.event.pull_request.labels.*.name, 'skip-changelog') }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5  # pin to SHA
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Require a news fragment for this PR
        env:
          PR: ${{ github.event.pull_request.number }}
        run: |
          shopt -s nullglob
          files=(changelog/${PR}.*.rst)
          if [ ${#files[@]} -eq 0 ]; then
            echo "::error::No changelog fragment changelog/${PR}.<type>.rst found. Add one or apply the 'skip-changelog' label."
            exit 1
          fi
          echo "Found: ${files[*]}"
```

- [ ] **Step 5: Create `ci-citation.yml`**

```yaml
name: ci-citation

on:
  pull_request:
    paths: ["CITATION.cff"]
  push:
    branches: [main]
    paths: ["CITATION.cff"]
  workflow_dispatch:

permissions: {}

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5  # pin to SHA
        with:
          persist-credentials: false
      - run: pipx run cffconvert --validate
```

- [ ] **Step 6: Create `codeql.yml`**

```yaml
name: codeql

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "24 3 * * 1"

permissions: {}

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@v5  # pin to SHA
        with:
          persist-credentials: false
      - uses: github/codeql-action/init@v3  # pin to SHA
        with:
          languages: python
      - uses: github/codeql-action/analyze@v3  # pin to SHA
```

- [ ] **Step 7: Replace tags with SHAs and validate**

For each `uses: OWNER/REPO@TAG  # pin to SHA`, resolve and substitute the commit SHA (keep the tag in a trailing comment), e.g.:
```bash
gh api repos/actions/checkout/commits/v5 --jq .sha
```

Then run:
```bash
pre-commit run check-github-workflows --all-files
pre-commit run zizmor --all-files
```
Expected: both pass. `zizmor` must report no findings (it checks `permissions`, `persist-credentials`, and SHA pinning — all satisfied above).

- [ ] **Step 8: Commit**

```bash
git add .github/workflows/
git commit -m "feat: add v1 core CI gates (tests, docs, wheels, changelog, citation, codeql)"
```

---

## Task 12: Full pre-commit pass and foundation verification

**Files:** none (verification task)

**Interfaces:**
- Produces: a fully green foundation — the exit criteria for Plan 1.

- [ ] **Step 1: Run the entire pre-commit suite**

Run: `pixi run lint`
Expected: every hook passes, including `check-github-workflows`, `check-dependabot`, `check-readthedocs`, `sp-repo-review`, and `zizmor`.

- [ ] **Step 2: Run the test task on every supported Python version**

Run:
```bash
pixi run -e test-py312 pytest -q
pixi run -e test-py313 pytest -q
pixi run -e test-py314 pytest -q
```
Expected: PASS on all three — 3 passed each.

- [ ] **Step 3: Build the docs clean**

Run: `pixi run docs`
Expected: `build succeeded`, 0 warnings.

- [ ] **Step 4: Build and check the distribution**

Run:
```bash
pipx run build
pipx run twine check dist/*
```
Expected: sdist + wheel build; `twine check` reports `PASSED` for both. Confirm `src/tephpy/_version.py` is **not** in the sdist file list except as generated content (it must not be tracked in git — `git status` shows it ignored).

- [ ] **Step 5: Add the verification changelog fragment and commit**

Create `changelog/1.documentation.rst` (same PR number as the existing
`1.internal.rst` — both fragments belong to the foundation PR):

```
Added the developer documentation-style guide (title style and glossary rules).
```

```bash
git add changelog/1.documentation.rst
git commit -m "docs: add documentation-style developer guide fragment"
```

- [ ] **Step 6: Open the pull request**

```bash
git push -u origin foundation
gh pr create --fill --base main --title "Project foundation and scaffolding"
```
Expected: PR opens; CI (`ci-tests` matrix, `ci-docs`, `ci-wheels` build, `ci-changelog`, `codeql`) runs and goes green.

---

## Self-review

**Spec coverage (§8):**
- §8.1 packaging/layout/setuptools_scm/MANIFEST/check-manifest → Tasks 1, 2 (check-manifest is in the `devs` requirements; a `ci-manifest` gate is a fast-follow, noted in spec §8.7).
- §8.2 pixi platforms/features/environments/tasks/lockfile → Task 8.
- §8.3 SPEC 0 (3.12/3.13/3.14, badge, sp-repo-review, matrix) → Tasks 1 (`requires-python`), 8 (per-py envs), 10 (badge), 7 (sp-repo-review), 11 (matrix).
- §8.4 ruff ALL + CPY001, mypy strict, numpydoc, pre-commit suite → Tasks 4, 5, 6, 7.
- §8.5 pytest strict + filterwarnings, hypothesis, pytest-cov, codecov, pytest-mpl → Tasks 3, 2 (deps), 8 (mpl task). *(Actual image tests arrive with plotting code in Plan 3.)*
- §8.6 Diátaxis, pydata theme, autoapi, numpydoc, myst-nb, sphinx-gallery, sphinx-design/copybutton/togglebutton/bibtex, towncrier, RTD, title style, glossary → Tasks 6, 9. *(sphinx-tags omitted from v1 skeleton — low value until there are gallery/tutorial pages to tag; add in Plan 7. Noted so the omission is deliberate.)*
- §8.7 CI core gates + fast-follow list → Task 11 (core); fast-follow bots intentionally not built (spec-documented).
- §8.8 CITATION.cff, codecov, dependabot, CoC/CONTRIBUTING/SECURITY, issue/PR templates, labeler, CODEOWNERS, AGENTS.md → Task 10.

**Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N". Empty `sphinx_gallery_conf` dirs and empty `examples_dirs` are explicitly explained as Plan 7 seams, not placeholders. SHA pins are an explicit substitution step with the exact `gh api` command, not a vague instruction.

**Type/name consistency:** `tephpy.__version__` (Tasks 1, 10, tests) consistent. pixi environment names (`test-py312`, `test-py313`, `test-py314`, `docs`) consistent between Task 8 and Task 11. Task names (`tests`, `lint`, `docs`) consistent between Task 8 and Tasks 11–12. Copyright regex identical in Task 4 and every file header.

**Deliberate deviations recorded:** pytest-mpl vs pytest-pyvista (spec §8.5); pydata-sphinx-theme (spec §8.6); sphinx-tags deferred to Plan 7 (above); doctest run in ci-docs deferred until doctests exist (spec §8.7); wheel-install smoke test in ci-wheels deferred while the wheel is pure-Python scaffolding (spec §8.7); labeler workflow deferred to the fast-follow bots wave — `.github/labeler.yml` ships inert until then (spec §8.7/§8.8).

---

## Execution handoff

This is Plan 1 of 7 (spec §10). On completion, the next plan is **Plan 2: transforms & the tephigram projection**, which will get its own spec-derived plan.
