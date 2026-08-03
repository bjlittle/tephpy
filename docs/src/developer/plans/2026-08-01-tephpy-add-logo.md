# Logo Placement API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Point-in-time record.** This plan states what was intended *before* implementation and is not updated afterwards. The review loop routinely revised what it records, so its code blocks drift from what shipped. The code is authoritative, and the design specification in [`../specs/`](../specs/) is the living statement of intent — read this for how the work was approached, not for how tephpy behaves today.

**Goal:** Add `tephpy.plotting.add_logo`, one public function that draws the tephpy logo
on a figure or an axes at a requested height in inches, in the variant that suits the
background, at a `legend`-style position.

**Architecture:** Six brand masters ship inside the wheel under
`src/tephpy/plotting/_static/`, byte-identical copies of the published bundle. A new
module `src/tephpy/plotting/logo.py` loads one through a `functools.cache`d reader,
converts the requested height in inches into an `OffsetImage` `zoom` (the whole
dpi-independence trick), and wraps it in an `AnnotationBbox` anchored in the target's own
fraction coordinates. Five small private resolvers — target, size, theme, placement,
image options — turn the keyword arguments into those four values, and `add_logo` is the
twenty lines that call them in order and attach the artist. No new class, no new
`tephpy.config` section, no change to any existing module beyond one export and one
`72.0` literal.

**Tech Stack:** Python 3.12–3.14, matplotlib 3.11 (floor 3.10), numpy, pytest, pytest-mpl,
setuptools, pixi, pre-commit, towncrier, Sphinx.

## Global Constraints

- Logo spec: `docs/superpowers/specs/2026-08-01-add-logo-design.md`. Cite it as
  `(logo spec §N)` in comments and docstrings — **not** `(spec §N)`, which the surrounding
  code already uses for the master spec `docs/superpowers/specs/2026-07-22-tephpy-design.md`.
  Both are cited in this plan; keep the two prefixes distinct in everything you write.
- Every module starts with the 4-line BSD copyright header (enforced by ruff's
  `flake8-copyright`) and `from __future__ import annotations`. This includes new test
  modules. Do not add either to files that already have them.

  ```python
  # Copyright (c) 2026, tephpy Contributors.
  #
  # This file is part of tephpy and is distributed under the 3-Clause BSD license.
  # See the LICENSE file in the package root directory for licensing details.
  ```
- Line length 88 (`ruff`, `line-length = 88` in `pyproject.toml`).
- Docstrings are numpydoc (`convention = "numpy"`), validated by a `numpydoc-validation`
  pre-commit hook. **Private functions are documented in full too.** Every parameter,
  return and raise gets an entry, **and every parameter line carries a type** — a bare
  `size :` fails `PR04`. Sphinx roles use full dotted paths with no `~` prefix, e.g.
  ``:class:`matplotlib.offsetbox.OffsetImage` `` — that is the existing idiom in
  `barbs.py`. `SA01`, `ES01`, `EX01` and `YD01` are disabled, so no See Also, Extended
  Summary, Examples or Yields section is required.
- Nothing numeric is hard-coded at point of use; it comes from `_constants` (spec §3.5).
  A signature default is a point of use, which is why `pad` and `zorder` take `None`
  sentinels (logo spec §3.1). The string defaults (`"lockup"`, `"small"`, `"auto"`,
  `"lower left"`) stay literal — they are API vocabulary, not numeric conventions.
- `TephpyError` and its subclasses are for user-correctable *data* input (spec §6). The
  plotting layer raises builtin `TypeError`/`ValueError`. Do not introduce a tephpy
  exception in this work.
- `pyproject.toml` sets `filterwarnings = ["error"]`, `--strict-markers` and
  `--strict-config`. A test that emits a warning fails.
- Tests live in the directory mirroring the module they exercise (`tests/AGENTS.md`), so
  `tephpy.plotting.logo` is tested by `tests/plotting/test_logo.py`. `tests/*` waives
  `ANN001`, `ANN003`, `ANN201`, `ANN202`, `SLF001` and `D103`, so test functions need no
  annotations or docstrings and may touch private names. It does **not** waive `S603`, so
  a `subprocess.run` call needs an inline `# noqa: S603`.
- Run a targeted test with `pixi run --frozen pytest <path> -k <expr> -v`. Run the full
  suite with `pixi run --frozen tests` — that task adds `--mpl`, which a bare `pytest`
  does not, so the image comparisons are skipped without it. Run the lint gate with
  `pixi run --frozen lint`. `--frozen` is mandatory — never let pixi re-solve. A bare
  `pixi run --frozen mypy` is **wrong** and reports ~57 pre-existing errors: the
  pre-commit `mypy` hook supplies the stub dependencies, so `lint` is the only correct
  way to type-check.
- Run `pre-commit install` once in a fresh clone or worktree before your first commit;
  the hooks are not installed automatically.
- mypy runs with `strict` and `warn_unreachable`. `warn_unreachable` is what forces the
  `resolved: object` widening in Task 3 — see the comment there before you "simplify" it.
- This plan and the logo spec ship as a docs-only PR on the `feature/add-logo` branch,
  labelled `skip-changelog`. The implementation is a separate PR: once the docs PR has
  merged, branch `feature/add-logo-impl` off an updated `main` and commit there. The
  `feature` prefix is what earns the `type: enhancement` label from
  `.github/workflows/ci-label.yml`. Never commit to `main` (a `no-commit-to-branch`
  pre-commit hook enforces this).

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/tephpy/plotting/_static/*.png` | The six brand masters, byte-identical to the bundle | Create (6 files) |
| `pyproject.toml` | Build and packaging config | Add `[tool.setuptools.package-data]` |
| `MANIFEST.in` | sdist contents | Add a `recursive-include` for the masters |
| `docs/src/_static/brand/assets/README.md` | Bundle-to-published mapping | Add the wheel-shipped set; correct the "larger sizes" bullet |
| `src/tephpy/_constants.py` | Convention defaults | Add `POINTS_PER_INCH`, `LOGO_SIZES`, `LOGO_PAD`, `LOGO_ZORDER`, `LOGO_LUMINANCE_THRESHOLD`, `LOGO_LUMINANCE_WEIGHTS` |
| `src/tephpy/plotting/barbs.py` | Wind-barb staff artist | Replace the one `72.0` literal with `POINTS_PER_INCH` |
| `src/tephpy/plotting/logo.py` | Load a master, resolve the four inputs, build the artist | Create |
| `src/tephpy/plotting/__init__.py` | Plotting namespace | Export `add_logo` |
| `tests/plotting/test_logo.py` | Assets, resolvers, and the public contract | Create |
| `tests/test_constants.py` | Constant invariants | Add `test_logo_conventions` |
| `tests/plotting/test_images.py` | Image baselines | Add `test_logo_on_a_tephigram` |
| `tests/baseline/test_logo_on_a_tephigram.png` | That baseline | Create (generated) |
| `docs/src/howtos/logo.rst` | How-to guide | Create |
| `docs/src/howtos/index.rst` | How-to toctree | Add `logo` |
| `changelog/<PR>.feature.rst` | Release note | Create |

**Task order matters.** Task 1 puts the assets where Task 2's loader reads them; Task 2's
loader is what Task 4 draws; Task 3's constants are what Tasks 3 and 4 both import. Task 5
needs the public function to exist. Do not reorder.

---

## Task 1: Bundle the brand masters and pin them to the wheel

**Files:**
- Create: `src/tephpy/plotting/_static/icon-512-light.png`, `icon-512-dark.png`,
  `lockup-716-light.png`, `lockup-716-dark.png`, `stacked-512-light.png`,
  `stacked-512-dark.png`
- Create: `tests/plotting/test_logo.py`
- Modify: `pyproject.toml` (insert `[tool.setuptools.package-data]` immediately **before**
  `[tool.setuptools.packages.find]`, currently at line 45)
- Modify: `MANIFEST.in`
- Modify: `docs/src/_static/brand/assets/README.md`

**Interfaces:**
- Consumes: `docs/src/_static/brand/assets/logo-bundle.zip`, already in the repo. The six
  masters live inside it at `bundle/png/<name>.png`.
- Produces: `src/tephpy/plotting/_static/<name>.png` for the six names above, present in
  a built wheel at `tephpy/plotting/_static/`. Task 2's `_MASTERS` table maps to exactly
  these filenames.

**Verified 2026-08-01** — the six members total 131,359 B (128.3 KiB). A wheel-only build
(`python -m build --wheel --no-isolation`) takes 0.92 s, and `python-build` is a `devs`
dependency, which every test environment carries — so the packaging test is affordable in
the ordinary suite.

- [ ] **Step 1: Write the failing asset tests**

Create `tests/plotting/test_logo.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the logo artist and its bundled brand masters (logo spec §6)."""

from __future__ import annotations

import hashlib
from pathlib import Path
import zipfile

import pytest

REPO = Path(__file__).parents[2]
STATIC = REPO / "src" / "tephpy" / "plotting" / "_static"
BUNDLE = REPO / "docs" / "src" / "_static" / "brand" / "assets" / "logo-bundle.zip"

MASTERS = (
    "icon-512-light.png",
    "icon-512-dark.png",
    "lockup-716-light.png",
    "lockup-716-dark.png",
    "stacked-512-light.png",
    "stacked-512-dark.png",
)


def test_static_holds_exactly_the_masters():
    """No stragglers: the packaged directory is the six masters and nothing else."""
    assert sorted(p.name for p in STATIC.iterdir()) == sorted(MASTERS)


@pytest.mark.parametrize("name", MASTERS)
def test_master_matches_the_bundle(name):
    """The bundle is the source of truth; a copy that drifts is a silent rebrand."""
    with zipfile.ZipFile(BUNDLE) as archive:
        expected = hashlib.sha256(archive.read(f"bundle/png/{name}")).hexdigest()
    assert hashlib.sha256((STATIC / name).read_bytes()).hexdigest() == expected
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -v`

Expected: 7 failures — `FileNotFoundError` on `STATIC.iterdir()` and on each
`STATIC / name`, because `src/tephpy/plotting/_static/` does not exist yet.

- [ ] **Step 3: Extract the six masters**

Run exactly this — copying the bytes out of the zip is what makes the hashes match:

```bash
pixi run --frozen python - <<'PY'
from pathlib import Path
import zipfile

static = Path("src/tephpy/plotting/_static")
static.mkdir(parents=True, exist_ok=True)
names = [
    "icon-512-light.png",
    "icon-512-dark.png",
    "lockup-716-light.png",
    "lockup-716-dark.png",
    "stacked-512-light.png",
    "stacked-512-dark.png",
]
with zipfile.ZipFile("docs/src/_static/brand/assets/logo-bundle.zip") as archive:
    for name in names:
        (static / name).write_bytes(archive.read(f"bundle/png/{name}"))
        print(name, (static / name).stat().st_size)
PY
```

Expected output: six lines totalling 131,359 bytes.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -v`

Expected: 7 passed.

- [ ] **Step 5: Write the failing packaging test**

**Do not `git add` the PNGs yet.** The setuptools_scm file finder only sees git-tracked
files, so while they are untracked this test genuinely fails — which is the point.

Append to `tests/plotting/test_logo.py`:

```python
def test_masters_ship_in_the_wheel(tmp_path):
    """A source-tree copy nobody packaged is the failure a source-tree test cannot see."""
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(tmp_path),
            str(REPO),
        ],
        check=True,
        capture_output=True,
    )
    (wheel,) = tmp_path.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        packaged = {
            Path(name).name
            for name in archive.namelist()
            if name.startswith("tephpy/plotting/_static/")
        }
    assert packaged == set(MASTERS)
```

and extend the imports at the top of the module to:

```python
import hashlib
from pathlib import Path
import subprocess
import sys
import zipfile
```

- [ ] **Step 6: Run the packaging test to verify it fails**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -k wheel -v`

Expected: FAIL with `AssertionError: assert set() == {...}` — the wheel contains no
`tephpy/plotting/_static/` entries at all.

- [ ] **Step 7: Declare the package data**

In `pyproject.toml`, insert immediately **before** `[tool.setuptools.packages.find]`:

```toml
[tool.setuptools.package-data]
tephpy = ["py.typed", "plotting/_static/*.png"]
```

`py.typed` is listed alongside because a `package-data` table replaces the implicit
handling for that package; omitting it would drop the typing marker from the wheel.

In `MANIFEST.in`, insert after the `include src/tephpy/py.typed` line:

```
recursive-include src/tephpy/plotting/_static *.png
```

- [ ] **Step 8: Run the packaging test to verify it passes**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -v`

Expected: 8 passed.

- [ ] **Step 9: Verify the sdist by hand (one-off, not a committed test)**

`MANIFEST.in` governs the sdist, which no test builds. Check it once here:

```bash
pixi run --frozen python -m build --sdist --no-isolation --outdir /tmp/tplogo-sdist .
pixi run --frozen python -c "
import glob, tarfile
(path,) = glob.glob('/tmp/tplogo-sdist/*.tar.gz')
with tarfile.open(path) as archive:
    print(sorted(n.split('/')[-1] for n in archive.getnames() if '_static/' in n and n.endswith('.png')))
"
rm -rf /tmp/tplogo-sdist
```

Expected: the six master filenames.

Note for the record: once the PNGs are committed, `include-package-data` (on by default
under a `pyproject.toml` build) plus the setuptools_scm file finder would ship them on
their own. The declaration is belt-and-braces that survives losing either, and the test
guards the *outcome* (logo spec §2) — the mutation that fails it is removing an asset from
the source tree.

- [ ] **Step 10: Document what the wheel ships**

In `docs/src/_static/brand/assets/README.md`, replace this bullet under
"What the bundle has that `brand/` does not":

```markdown
- **Larger sizes** — icon at 256/512, lockup at 716, stacked at 512.
```

with:

```markdown
- **Larger sizes** — icon at 256. The 512/716 masters are not published under
  `brand/`; they ship inside the wheel instead (see below).
```

and insert this section immediately after the "What is published" section (i.e. after the
paragraph ending "`lockup-358-dark.png` is 358×128."):

```markdown
## What the wheel ships

`tephpy.plotting.add_logo` draws from six masters copied into the package under
`src/tephpy/plotting/_static/`, so the function works from a wheel with no docs
tree and no network:

| In the package | From the bundle |
|---|---|
| `icon-512-{light,dark}.png` | `bundle/png/` |
| `lockup-716-{light,dark}.png` | `bundle/png/` |
| `stacked-512-{light,dark}.png` | `bundle/png/` |

These are the largest raster of each form, downscaled at draw time to the height
in inches the caller asks for. Like everything else here they are byte-identical
to the bundle, and `tests/plotting/test_logo.py` hashes them against it — the
snippet below covers `brand/` only, because it matches on basename within that
directory.
```

- [ ] **Step 11: Run the lint gate**

Run: `pixi run --frozen lint`

Expected: all hooks pass. `check for added large files` has a 500 KiB default limit and
the largest master is 29 KiB, so the PNGs pass.

- [ ] **Step 12: Commit**

```bash
git add src/tephpy/plotting/_static tests/plotting/test_logo.py pyproject.toml \
        MANIFEST.in docs/src/_static/brand/assets/README.md
git commit -m "Bundle the six brand masters into the package"
```

---

## Task 2: Load a master, once, from package data

**Files:**
- Create: `src/tephpy/plotting/logo.py`
- Modify: `tests/plotting/test_logo.py`

**Interfaces:**
- Consumes: the six PNGs from Task 1, at `tephpy/plotting/_static/`.
- Produces:
  - `_MASTERS: Final[dict[tuple[str, str], str]]` — `(form, variant)` to filename, where
    `form` is one of `"icon"`, `"lockup"`, `"stacked"` and `variant` is `"light"` or
    `"dark"`.
  - `_load_master(form: str, variant: str) -> npt.NDArray` — a `functools.cache`d reader
    returning a read-only float RGBA array of shape `(height, width, 4)`. Task 4 divides
    the requested height in inches by `image.shape[0]` to get the `OffsetImage` zoom, so
    the **first** axis being height is load-bearing.

- [ ] **Step 1: Write the failing loader tests**

Append to `tests/plotting/test_logo.py`:

```python
@pytest.mark.parametrize(
    ("form", "variant", "shape"),
    [
        ("icon", "light", (512, 512)),
        ("icon", "dark", (512, 512)),
        ("lockup", "light", (256, 716)),
        ("lockup", "dark", (256, 716)),
        ("stacked", "light", (720, 512)),
        ("stacked", "dark", (720, 512)),
    ],
)
def test_load_master_shape(form, variant, shape):
    """Height first: the zoom calculation divides by ``shape[0]`` (logo spec §3.3)."""
    image = logo._load_master(form, variant)
    assert image.shape == (*shape, 4)


def test_load_master_is_read_only():
    """One shared array per variant; a caller mutating it would poison every figure."""
    with pytest.raises(ValueError, match="read-only"):
        logo._load_master("icon", "light")[0, 0, 0] = 1.0


def test_load_master_caches():
    """Decoding a 512x720 PNG per call would cost more than drawing the figure."""
    assert logo._load_master("stacked", "dark") is logo._load_master("stacked", "dark")


def test_masters_table_covers_every_shipped_file():
    """The table and the packaged directory must not drift apart."""
    assert sorted(logo._MASTERS.values()) == sorted(MASTERS)


def test_importing_reads_no_asset():
    """A logo nobody asked for costs nothing (logo spec §3.6)."""
    code = (
        "from tephpy.plotting import logo;"
        " info = logo._load_master.cache_info();"
        " raise SystemExit(0 if info.hits == 0 and info.currsize == 0 else 1)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603
```

and add the import (isort orders `from tephpy...` after the third-party block):

```python
from tephpy.plotting import logo
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -v`

Expected: collection error — `ImportError: cannot import name 'logo' from
'tephpy.plotting'`.

- [ ] **Step 3: Create the module with the loader**

Create `src/tephpy/plotting/logo.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Place the tephpy logo on a figure or an axes.

The masters under ``_static`` are byte-identical copies of the published brand
bundle (logo spec §3.2), kept that way by a drift guard in
``tests/plotting/test_logo.py``. Sizing is a height in inches and is
dpi-independent (logo spec §3.3); placement follows the ``legend`` vocabulary
(logo spec §3.4).
"""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from io import BytesIO
from typing import TYPE_CHECKING, Final

import matplotlib.image as mimage

if TYPE_CHECKING:
    import numpy.typing as npt

_MASTERS: Final[dict[tuple[str, str], str]] = {
    ("icon", "light"): "icon-512-light.png",
    ("icon", "dark"): "icon-512-dark.png",
    ("lockup", "light"): "lockup-716-light.png",
    ("lockup", "dark"): "lockup-716-dark.png",
    ("stacked", "light"): "stacked-512-light.png",
    ("stacked", "dark"): "stacked-512-dark.png",
}


@cache
def _load_master(form: str, variant: str) -> npt.NDArray:
    """Read one packaged master, decoded once and shared thereafter.

    The array is marked read-only because every figure drawing that variant
    holds the same object (logo spec §3.6).

    Parameters
    ----------
    form : str
        Which mark: a key of the first element of ``_MASTERS``.
    variant : str
        Which background the mark is drawn on: ``"light"`` or ``"dark"``.

    Returns
    -------
    numpy.ndarray
        A read-only float RGBA array of shape ``(height, width, 4)``.
    """
    resource = files("tephpy.plotting").joinpath("_static", _MASTERS[form, variant])
    # ``read_bytes`` rather than ``open``: ``Traversable.open`` is typed
    # ``IO[bytes]``, which ``imread`` does not accept, and a cast would hide it.
    image = mimage.imread(BytesIO(resource.read_bytes()), format="png")
    image.setflags(write=False)
    return image
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -v`

Expected: 18 passed — Task 1's eight plus these ten.

- [ ] **Step 5: Write the failing import-discipline test**

`add_logo` calls `plt.gcf()` when `target is None`, and the obvious way to write that —
a module-level `import matplotlib.pyplot as plt` — would pull pyplot into every
`import tephpy`. Lock the current behaviour in before writing the code that could break
it. Append to `tests/plotting/test_logo.py`:

```python
def test_import_tephpy_does_not_import_pyplot():
    """``pyplot`` is an interactive-session import, not a library one (logo spec §3.2)."""
    code = "import sys, tephpy; raise SystemExit(1 if 'matplotlib.pyplot' in sys.modules else 0)"
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603
```

- [ ] **Step 6: Run it to verify it passes, for the right reason**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -k pyplot -v`

Expected: PASS. This one is a guard, not a red-green step — it passes now and Task 4 must
keep it passing. Confirm it can fail: temporarily add `import matplotlib.pyplot` to the
top of `src/tephpy/plotting/logo.py`, re-run (expect FAIL with
`CalledProcessError ... exit status 1`), then remove it and re-run (expect PASS).

- [ ] **Step 7: Run the lint gate**

Run: `pixi run --frozen lint`

Expected: all hooks pass.

- [ ] **Step 8: Commit**

```bash
git add src/tephpy/plotting/logo.py tests/plotting/test_logo.py
git commit -m "Load a brand master once from package data"
```

---

## Task 3: Resolve the target, size, theme, placement and image options

**Files:**
- Modify: `src/tephpy/_constants.py` (append at the end of the file)
- Modify: `src/tephpy/plotting/barbs.py:254`
- Modify: `src/tephpy/plotting/logo.py`
- Modify: `tests/plotting/test_logo.py`
- Modify: `tests/test_constants.py`

**Interfaces:**
- Consumes: `_MASTERS` and `_load_master` from Task 2 (unused here, but the module is
  shared).
- Produces, in `src/tephpy/_constants.py`:
  - `POINTS_PER_INCH: Final[float]`
  - `LOGO_SIZES: Final[dict[str, dict[str, float]]]` — form to `{"small": …, "large": …}`
  - `LOGO_PAD: Final[float]`, `LOGO_ZORDER: Final[float]`
  - `LOGO_LUMINANCE_THRESHOLD: Final[float]`,
    `LOGO_LUMINANCE_WEIGHTS: Final[tuple[float, float, float]]`
- Produces, in `src/tephpy/plotting/logo.py`:
  - `_LOC: Final[dict[str, tuple[tuple[float, float], tuple[float, float], tuple[float, float]]]]`
    — placement string to `(anchor, box_alignment, offset_signs)`
  - `_IMAGE_KEYS: Final[frozenset[str]]`
  - `_resolve_target(target: Figure | Axes | None) -> tuple[Figure, Axes | None]`
  - `_resolve_size(size: str | float, form: str) -> float` — note the argument order
  - `_resolve_theme(theme: str, figure: Figure, axes: Axes | None) -> str`
  - `_resolve_loc(loc: str | tuple[float, float], pad: float) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]`
  - `_image_options(kwargs: dict[str, Any]) -> dict[str, Any]`

**Verified 2026-08-01** — the presets are per-form because the forms give the wordmark
different shares of their height (44.1% for the lockup, 17.8% for the stacked form), so a
single shared pair would leave one of them illegible: at the `"small"` presets the
wordmark is 13.2 px in the lockup and 12.4 px in the stacked form at dpi 100.

- [ ] **Step 1: Write the failing constants test**

Append to `tests/test_constants.py`:

```python
def test_logo_conventions():
    """Every form has both presets, ordered, and the luminance weights are Rec. 709."""
    assert constants.POINTS_PER_INCH == 72.0
    assert set(constants.LOGO_SIZES) == {"icon", "lockup", "stacked"}
    for presets in constants.LOGO_SIZES.values():
        assert set(presets) == {"small", "large"}
        assert 0.0 < presets["small"] < presets["large"]
    assert constants.LOGO_PAD > 0.0
    assert constants.LOGO_ZORDER > 5.0
    assert 0.0 < constants.LOGO_LUMINANCE_THRESHOLD < 1.0
    assert sum(constants.LOGO_LUMINANCE_WEIGHTS) == pytest.approx(1.0)
```

`tests/test_constants.py` does not currently import pytest. Add `import pytest` to its
third-party import block (after `import numpy as np`).

- [ ] **Step 2: Run it to verify it fails**

Run: `pixi run --frozen pytest tests/test_constants.py::test_logo_conventions -v`

Expected: FAIL with `AttributeError: module 'tephpy._constants' has no attribute
'POINTS_PER_INCH'`.

- [ ] **Step 3: Add the constants**

Append to `src/tephpy/_constants.py`:

```python
#: Points per inch, the typographic unit matplotlib sizes text and offsets in.
POINTS_PER_INCH: Final[float] = 72.0

#: Logo height in inches for each ``(form, size)`` preset of ``add_logo``.
#: The presets are per-form because the forms give the wordmark different
#: shares of their height — 44.1% for the lockup, 17.8% for the stacked
#: form — so a shared pair would leave one of them illegible (logo spec §3.3).
LOGO_SIZES: Final[dict[str, dict[str, float]]] = {
    "icon": {"small": 0.40, "large": 0.70},
    "lockup": {"small": 0.30, "large": 0.55},
    "stacked": {"small": 0.70, "large": 1.15},
}

#: Default gap in points between the logo and its target's edge, matching the
#: legend's ``borderaxespad`` of 0.5 font-size units at the 10 pt default font.
LOGO_PAD: Final[float] = 6.0

#: Default logo draw order: above lines (2), text (3) and legends (5).
LOGO_ZORDER: Final[float] = 100.0

#: sRGB relative luminance below which ``theme="auto"`` calls a background dark.
LOGO_LUMINANCE_THRESHOLD: Final[float] = 0.5

#: Rec. 709 relative-luminance weights for the red, green and blue channels.
LOGO_LUMINANCE_WEIGHTS: Final[tuple[float, float, float]] = (0.2126, 0.7152, 0.0722)
```

- [ ] **Step 4: Run it to verify it passes**

Run: `pixi run --frozen pytest tests/test_constants.py -v`

Expected: all pass.

- [ ] **Step 5: Retire the one hard-coded 72.0**

A refactor, not new behaviour: `POINTS_PER_INCH` now exists, so the literal at
`src/tephpy/plotting/barbs.py:254` is the only place in the package that hard-codes it,
and spec §3.5 says it should not. The values are equal, so no baseline moves.

Change line 254 from:

```python
            separation = self._minimum_separation * figure.dpi / 72.0
```

to:

```python
            separation = self._minimum_separation * figure.dpi / POINTS_PER_INCH
```

and add `POINTS_PER_INCH` to the existing `from tephpy._constants import (...)` block at
`barbs.py:27`, keeping it alphabetical:

```python
from tephpy._constants import (
    BARB_INCREMENTS,
    BARB_LENGTH,
    BARB_STAFF_POSITION,
    KAPPA,
    KELVIN_ZERO,
    MA,
    P_REF,
    POINTS_PER_INCH,
)
```

- [ ] **Step 6: Run the barb tests to verify nothing moved**

Run: `pixi run --frozen pytest tests/plotting/test_barbs.py tests/plotting/test_images.py --mpl -v`

Expected: all pass, including the barb image baseline. That baseline is the proof the
substitution is value-identical.

- [ ] **Step 7: Write the failing target-resolution tests**

Append to `tests/plotting/test_logo.py`:

```python
def test_resolve_target_axes_returns_its_figure():
    figure, axes = plt.subplots()
    assert logo._resolve_target(axes) == (figure, axes)
    plt.close(figure)


def test_resolve_target_figure_has_no_axes():
    figure = plt.figure()
    assert logo._resolve_target(figure) == (figure, None)
    plt.close(figure)


def test_resolve_target_none_takes_the_current_figure():
    figure = plt.figure()
    assert logo._resolve_target(None) == (figure, None)
    plt.close(figure)


def test_resolve_target_rejects_anything_else():
    with pytest.raises(TypeError, match="Figure or an Axes"):
        logo._resolve_target("figure")


def test_resolve_target_rejects_a_subfigure_axes():
    """``SubFigure`` is out of scope (logo spec §8); say so rather than lie about it."""
    figure = plt.figure()
    axes = figure.subfigures(1, 1).subplots()
    with pytest.raises(TypeError, match="not a SubFigure"):
        logo._resolve_target(axes)
    plt.close(figure)
```

and add `import matplotlib.pyplot as plt` to the third-party import block of the test
module.

- [ ] **Step 8: Run them to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -k resolve_target -v`

Expected: 5 failures, `AttributeError: module 'tephpy.plotting.logo' has no attribute
'_resolve_target'`.

- [ ] **Step 9: Implement `_resolve_target`**

Add to `src/tephpy/plotting/logo.py`, after `_MASTERS` and before `_load_master`:

```python
def _resolve_target(target: Figure | Axes | None) -> tuple[Figure, Axes | None]:
    """Split the target into the figure that owns it and the axes, if any.

    Parameters
    ----------
    target : matplotlib.figure.Figure or matplotlib.axes.Axes or None
        What to brand. ``None`` takes the current figure.

    Returns
    -------
    tuple of (matplotlib.figure.Figure, matplotlib.axes.Axes or None)
        The owning figure, and the axes when one was given.

    Raises
    ------
    TypeError
        If `target` is neither a figure nor an axes, or is an axes belonging to
        a :class:`matplotlib.figure.SubFigure`.
    """
    if target is None:
        # Local: keeps pyplot out of ``import tephpy`` (logo spec §3.2).
        import matplotlib.pyplot as plt  # noqa: PLC0415

        target = plt.gcf()
    # Widened so the guard below stays reachable under mypy's ``warn_unreachable``
    # for a caller who ignores the annotation — which is the caller it protects
    # against. Narrow it back and mypy calls the final ``raise`` dead code.
    resolved: object = target
    if isinstance(resolved, Axes):
        figure = resolved.figure
        if not isinstance(figure, Figure):
            msg = "target axes must belong to a Figure, not a SubFigure."
            raise TypeError(msg)
        return figure, resolved
    if isinstance(resolved, Figure):
        return resolved, None
    msg = f"target must be a Figure or an Axes, got {type(resolved).__name__}."
    raise TypeError(msg)
```

and extend the module imports. `Axes` and `Figure` are needed at runtime by `isinstance`,
so they are real imports, not `TYPE_CHECKING` ones:

```python
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import matplotlib.image as mimage
```

- [ ] **Step 10: Run them to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -v`

Expected: all pass.

- [ ] **Step 11: Write the failing size-resolution tests**

Append to `tests/plotting/test_logo.py`:

```python
@pytest.mark.parametrize("form", ["icon", "lockup", "stacked"])
@pytest.mark.parametrize("size", ["small", "large"])
def test_resolve_size_preset(form, size):
    assert logo._resolve_size(size, form) == LOGO_SIZES[form][size]


def test_resolve_size_explicit_height():
    assert logo._resolve_size(1.25, "lockup") == 1.25


def test_resolve_size_rejects_an_unknown_form():
    with pytest.raises(ValueError, match="unknown form 'wordmark'"):
        logo._resolve_size("small", "wordmark")


def test_resolve_size_rejects_an_unknown_preset():
    with pytest.raises(ValueError, match="unknown size 'medium'"):
        logo._resolve_size("medium", "lockup")


@pytest.mark.parametrize("size", [-1.0, 0.0, float("nan"), float("inf")])
def test_resolve_size_rejects_a_nonpositive_or_nonfinite_height(size):
    with pytest.raises(ValueError, match="positive finite"):
        logo._resolve_size(size, "lockup")


def test_resolve_size_rejects_a_sequence():
    with pytest.raises(TypeError):
        logo._resolve_size([1.0, 2.0], "lockup")
```

and add to the test module's tephpy import block — `LOGO_SIZES` only, since ruff's `F401`
fails an import nothing uses yet; Task 4 widens it:

```python
from tephpy._constants import LOGO_SIZES
```

- [ ] **Step 12: Run them to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -k resolve_size -v`

Expected: 14 failures, `AttributeError: ... has no attribute '_resolve_size'`.

- [ ] **Step 13: Implement `_resolve_size`**

Add to `src/tephpy/plotting/logo.py` after `_resolve_target`:

```python
def _resolve_size(size: str | float, form: str) -> float:
    """Turn a preset name or an explicit height into a height in inches.

    Parameters
    ----------
    size : str or float
        A key of the `form`'s ``LOGO_SIZES`` entry, or a height in inches.
    form : str
        Which mark, which selects the preset table.

    Returns
    -------
    float
        The logo height in inches.

    Raises
    ------
    ValueError
        If `form` names no mark, if `size` names no preset, or if `size` is not
        a positive finite height.
    """
    presets = LOGO_SIZES.get(form)
    if presets is None:
        valid = ", ".join(sorted(LOGO_SIZES))
        msg = f"unknown form {form!r}, expected one of: {valid}."
        raise ValueError(msg)
    if isinstance(size, str):
        height = presets.get(size)
        if height is None:
            valid = ", ".join(sorted(presets))
            msg = (
                f"unknown size {size!r}, expected one of: {valid}, "
                "or a height in inches."
            )
            raise ValueError(msg)
        return height
    height = float(size)
    if not math.isfinite(height) or height <= 0.0:
        msg = f"size must be a positive finite height in inches, got {size!r}."
        raise ValueError(msg)
    return height
```

and extend the module imports with `import math` (stdlib block) and
`from tephpy._constants import LOGO_SIZES` (first-party block).

- [ ] **Step 14: Run them to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -v`

Expected: all pass. `float([1.0, 2.0])` raises `TypeError`, which is what
`test_resolve_size_rejects_a_sequence` asserts.

- [ ] **Step 15: Write the failing theme-resolution tests**

Append to `tests/plotting/test_logo.py`:

```python
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_resolve_theme_explicit_is_taken_as_given(theme):
    figure, axes = plt.subplots()
    axes.set_facecolor("black" if theme == "light" else "white")
    assert logo._resolve_theme(theme, figure, axes) == theme
    plt.close(figure)


def test_resolve_theme_auto_on_a_default_figure():
    figure, axes = plt.subplots()
    assert logo._resolve_theme("auto", figure, axes) == "light"
    plt.close(figure)


def test_resolve_theme_auto_reads_the_axes_first():
    """The axes is the background the logo actually sits on."""
    figure, axes = plt.subplots()
    axes.set_facecolor("#101820")
    assert logo._resolve_theme("auto", figure, axes) == "dark"
    plt.close(figure)


def test_resolve_theme_auto_falls_through_a_transparent_axes():
    """A transparent axes shows the figure, so the figure is what to measure."""
    figure, axes = plt.subplots()
    axes.set_facecolor("none")
    figure.set_facecolor("black")
    assert logo._resolve_theme("auto", figure, axes) == "dark"
    plt.close(figure)


def test_resolve_theme_auto_under_the_dark_background_style():
    with plt.style.context("dark_background"):
        figure, axes = plt.subplots()
        assert logo._resolve_theme("auto", figure, axes) == "dark"
        plt.close(figure)


def test_resolve_theme_auto_with_nothing_opaque_assumes_light():
    """Nothing to measure: print is the default medium, and print is white."""
    figure = plt.figure()
    figure.set_facecolor("none")
    assert logo._resolve_theme("auto", figure, None) == "light"
    plt.close(figure)


def test_resolve_theme_rejects_an_unknown_name():
    figure = plt.figure()
    with pytest.raises(ValueError, match="unknown theme 'sepia'"):
        logo._resolve_theme("sepia", figure, None)
    plt.close(figure)
```

- [ ] **Step 16: Run them to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -k resolve_theme -v`

Expected: 8 failures, `AttributeError: ... has no attribute '_resolve_theme'`.

- [ ] **Step 17: Implement `_resolve_theme`**

Add to `src/tephpy/plotting/logo.py` after `_resolve_size`:

```python
def _resolve_theme(theme: str, figure: Figure, axes: Axes | None) -> str:
    """Choose the light or dark variant, reading the background when asked to.

    ``"auto"`` measures the sRGB relative luminance of the first opaque
    facecolor among the axes and then the figure, so a transparent axes defers
    to the figure showing through it (logo spec §3.5).

    Parameters
    ----------
    theme : str
        ``"auto"``, ``"light"`` or ``"dark"``, naming the *background*.
    figure : matplotlib.figure.Figure
        The owning figure, measured when the axes is absent or transparent.
    axes : matplotlib.axes.Axes or None
        The target axes, measured first when there is one.

    Returns
    -------
    str
        ``"light"`` or ``"dark"``.

    Raises
    ------
    ValueError
        If `theme` is none of the three accepted names.
    """
    if theme in {"dark", "light"}:
        return theme
    if theme != "auto":
        msg = f"unknown theme {theme!r}, expected one of: auto, dark, light."
        raise ValueError(msg)
    for artist in (axes, figure):
        if artist is None:
            continue
        red, green, blue, alpha = mcolors.to_rgba(artist.get_facecolor())
        if alpha == 0.0:
            continue
        weight_red, weight_green, weight_blue = LOGO_LUMINANCE_WEIGHTS
        luminance = weight_red * red + weight_green * green + weight_blue * blue
        return "dark" if luminance < LOGO_LUMINANCE_THRESHOLD else "light"
    return "light"
```

and extend the module imports with `import matplotlib.colors as mcolors` and the two new
constants, so the first-party block reads:

```python
from tephpy._constants import (
    LOGO_LUMINANCE_THRESHOLD,
    LOGO_LUMINANCE_WEIGHTS,
    LOGO_SIZES,
)
```

- [ ] **Step 18: Run them to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -v`

Expected: all pass.

- [ ] **Step 19: Write the failing placement-resolution tests**

Append to `tests/plotting/test_logo.py`:

```python
def test_loc_table_covers_the_legend_vocabulary():
    """Ten strings, nine positions — ``right`` is ``center right``, as in ``legend``."""
    assert set(logo._LOC) == {
        "upper right",
        "upper left",
        "lower left",
        "lower right",
        "right",
        "center left",
        "center right",
        "lower center",
        "upper center",
        "center",
    }
    assert logo._LOC["right"] == logo._LOC["center right"]


@pytest.mark.parametrize(
    ("loc", "anchor", "alignment", "offset"),
    [
        ("lower left", (0.0, 0.0), (0.0, 0.0), (6.0, 6.0)),
        ("lower right", (1.0, 0.0), (1.0, 0.0), (-6.0, 6.0)),
        ("upper left", (0.0, 1.0), (0.0, 1.0), (6.0, -6.0)),
        ("upper right", (1.0, 1.0), (1.0, 1.0), (-6.0, -6.0)),
        ("lower center", (0.5, 0.0), (0.5, 0.0), (0.0, 6.0)),
        ("upper center", (0.5, 1.0), (0.5, 1.0), (0.0, -6.0)),
        ("center left", (0.0, 0.5), (0.0, 0.5), (6.0, 0.0)),
        ("center right", (1.0, 0.5), (1.0, 0.5), (-6.0, 0.0)),
        ("center", (0.5, 0.5), (0.5, 0.5), (0.0, 0.0)),
    ],
)
def test_resolve_loc_string(loc, anchor, alignment, offset):
    """The pad pushes inward from whichever edge the anchor sits on."""
    assert logo._resolve_loc(loc, 6.0) == (anchor, alignment, offset)


def test_resolve_loc_pair_places_the_lower_left_corner_and_ignores_pad():
    assert logo._resolve_loc((0.35, 0.2), 50.0) == ((0.35, 0.2), (0.0, 0.0), (0.0, 0.0))


def test_resolve_loc_pair_allows_coordinates_outside_the_box():
    """``annotation_clip=False`` renders these, and ``legend`` permits them too."""
    anchor, _alignment, _offset = logo._resolve_loc((-0.1, 1.4), 6.0)
    assert anchor == (-0.1, 1.4)


def test_resolve_loc_rejects_best_by_name():
    with pytest.raises(ValueError, match="no collision detection"):
        logo._resolve_loc("best", 6.0)


def test_resolve_loc_rejects_an_unknown_string():
    with pytest.raises(ValueError, match="unknown loc 'middle'"):
        logo._resolve_loc("middle", 6.0)


@pytest.mark.parametrize("loc", [(0.1, 0.2, 0.3), ("a", 0.1), 0.5])
def test_resolve_loc_rejects_a_malformed_pair(loc):
    with pytest.raises(TypeError, match=r"\(x, y\) pair"):
        logo._resolve_loc(loc, 6.0)


@pytest.mark.parametrize("loc", [(float("nan"), 0.1), (0.1, float("inf"))])
def test_resolve_loc_rejects_a_nonfinite_coordinate(loc):
    with pytest.raises(ValueError, match="must be finite"):
        logo._resolve_loc(loc, 6.0)
```

- [ ] **Step 20: Run them to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -k "loc" -v`

Expected: 19 failures, `AttributeError: ... has no attribute '_LOC'` /
`'_resolve_loc'`.

- [ ] **Step 21: Implement `_LOC` and `_resolve_loc`**

Add the table to `src/tephpy/plotting/logo.py`, after `_MASTERS`:

```python
#: Placement string to ``(anchor, box_alignment, offset signs)``. The anchor is a
#: point in the target's fraction coordinates, the alignment names which corner
#: of the logo lands on it, and the signs turn ``pad`` into an inward offset in
#: points (logo spec §3.4). ``right`` aliases ``center right``, as in ``legend``.
_LOC: Final[
    dict[str, tuple[tuple[float, float], tuple[float, float], tuple[float, float]]]
] = {
    "upper right": ((1.0, 1.0), (1.0, 1.0), (-1.0, -1.0)),
    "upper left": ((0.0, 1.0), (0.0, 1.0), (1.0, -1.0)),
    "lower left": ((0.0, 0.0), (0.0, 0.0), (1.0, 1.0)),
    "lower right": ((1.0, 0.0), (1.0, 0.0), (-1.0, 1.0)),
    "right": ((1.0, 0.5), (1.0, 0.5), (-1.0, 0.0)),
    "center left": ((0.0, 0.5), (0.0, 0.5), (1.0, 0.0)),
    "center right": ((1.0, 0.5), (1.0, 0.5), (-1.0, 0.0)),
    "lower center": ((0.5, 0.0), (0.5, 0.0), (0.0, 1.0)),
    "upper center": ((0.5, 1.0), (0.5, 1.0), (0.0, -1.0)),
    "center": ((0.5, 0.5), (0.5, 0.5), (0.0, 0.0)),
}
```

and the resolver after `_resolve_theme`:

```python
def _resolve_loc(
    loc: str | tuple[float, float], pad: float
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """Turn a placement into an anchor, a box alignment and an offset in points.

    A pair places the logo's lower-left corner at those fraction coordinates and
    ignores `pad`, because the caller has already said exactly where they want
    it (logo spec §3.4).

    Parameters
    ----------
    loc : str or tuple of float
        A key of ``_LOC``, or an ``(x, y)`` pair in fraction coordinates.
    pad : float
        Points between the logo and the target's edge, for the string form.

    Returns
    -------
    tuple of (tuple of float, tuple of float, tuple of float)
        The anchor, the box alignment, and the offset in points.

    Raises
    ------
    TypeError
        If `loc` is neither a string nor a pair of floats.
    ValueError
        If `loc` names no placement, or holds a non-finite coordinate.
    """
    if isinstance(loc, str):
        placement = _LOC.get(loc)
        if placement is None:
            valid = ", ".join(sorted(_LOC))
            detail = (
                "loc='best' is unsupported: add_logo performs no collision detection"
                if loc == "best"
                else f"unknown loc {loc!r}"
            )
            msg = f"{detail}, expected one of: {valid}, or an (x, y) pair."
            raise ValueError(msg)
        anchor, alignment, signs = placement
        return anchor, alignment, (signs[0] * pad, signs[1] * pad)
    try:
        x, y = (float(value) for value in loc)
    except (TypeError, ValueError) as err:
        msg = f"loc must be a placement string or an (x, y) pair of floats, got {loc!r}."
        raise TypeError(msg) from err
    if not (math.isfinite(x) and math.isfinite(y)):
        msg = f"loc coordinates must be finite, got {loc!r}."
        raise ValueError(msg)
    return (x, y), (0.0, 0.0), (0.0, 0.0)
```

Unpacking a 3-element or 1-element sequence raises `ValueError`, and iterating a float
raises `TypeError`; both are caught and re-raised as the one `TypeError` the docstring
promises, which is why `test_resolve_loc_rejects_a_malformed_pair` covers all three.

- [ ] **Step 22: Run them to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -v`

Expected: all pass.

- [ ] **Step 23: Write the failing image-option tests**

Append to `tests/plotting/test_logo.py`:

```python
def test_image_options_passes_known_keys_through():
    options = {"alpha": 0.5, "interpolation": "nearest"}
    assert logo._image_options(options) == options


def test_image_options_rejects_an_unknown_key():
    """``OffsetImage`` would raise ``AttributeError`` from deep inside; be clearer."""
    with pytest.raises(TypeError, match="unknown option bogus"):
        logo._image_options({"bogus": 1})


def test_image_options_names_every_unknown_key():
    with pytest.raises(TypeError, match="unknown option bogus, spurious"):
        logo._image_options({"spurious": 2, "bogus": 1})
```

- [ ] **Step 24: Run them to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -k image_options -v`

Expected: 3 failures, `AttributeError: ... has no attribute '_image_options'`.

- [ ] **Step 25: Implement `_IMAGE_KEYS` and `_image_options`**

Add the set after `_LOC`:

```python
#: The ``OffsetImage`` options ``add_logo`` forwards. Anything else is a typo
#: worth naming, because ``OffsetImage`` reports it as an ``AttributeError``
#: raised by ``BboxImage.set`` (logo spec §5).
_IMAGE_KEYS: Final[frozenset[str]] = frozenset(
    {"alpha", "filternorm", "filterrad", "interpolation", "resample"}
)
```

and the check after `_resolve_loc`:

```python
def _image_options(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Check the forwarded keywords against what ``OffsetImage`` accepts.

    Parameters
    ----------
    kwargs : dict
        The caller's surplus keyword arguments.

    Returns
    -------
    dict
        `kwargs` unchanged, once every key is known.

    Raises
    ------
    TypeError
        If any key is not an ``OffsetImage`` option.
    """
    unknown = sorted(set(kwargs) - _IMAGE_KEYS)
    if unknown:
        valid = ", ".join(sorted(_IMAGE_KEYS))
        msg = f"unknown option {', '.join(unknown)}; expected one of: {valid}."
        raise TypeError(msg)
    return kwargs
```

and add `Any` to the `typing` import: `from typing import TYPE_CHECKING, Any, Final`.

- [ ] **Step 26: Run the whole suite**

Run: `pixi run --frozen tests`

Expected: all pass.

- [ ] **Step 27: Run the lint gate**

Run: `pixi run --frozen lint`

Expected: all hooks pass. If mypy reports `Statement is unreachable` in `_resolve_target`,
the `resolved: object` widening has been removed — put it back.

- [ ] **Step 28: Commit**

```bash
git add src/tephpy/_constants.py src/tephpy/plotting/barbs.py \
        src/tephpy/plotting/logo.py tests/plotting/test_logo.py tests/test_constants.py
git commit -m "Resolve the logo target, size, theme and placement"
```

---

## Task 4: `add_logo` — build, attach and return the artist

**Files:**
- Modify: `src/tephpy/plotting/logo.py`
- Modify: `src/tephpy/plotting/__init__.py`
- Modify: `tests/plotting/test_logo.py`

**Interfaces:**
- Consumes: `_load_master` (Task 2); `_resolve_target`, `_resolve_size`, `_resolve_theme`,
  `_resolve_loc`, `_image_options` (Task 3); `LOGO_PAD`, `LOGO_ZORDER`, `POINTS_PER_INCH`
  (Task 3).
- Produces: `tephpy.plotting.add_logo(target=None, *, form="lockup", size="small",
  theme="auto", loc="lower left", pad=None, zorder=None, **kwargs) -> AnnotationBbox`,
  the one public name this work adds.

**Verified 2026-08-01** — `zoom = height * POINTS_PER_INCH / image.shape[0]` renders to
the requested height exactly at dpi 100, 300 and 600, on both the figure-fraction and
axes-fraction paths, with corner gaps of exactly 6.00 pt. `pad=0.0` on the
`AnnotationBbox` is **mandatory**: its default of 0.4 font-size units adds a constant
0.111 in at the 10 pt default font, so a 0.30 in lockup renders at 0.4111 in without it.
That is the mutation Step 5's test catches.

- [ ] **Step 1: Write the failing sizing tests**

Append to `tests/plotting/test_logo.py`:

```python
def _extent(artist, figure):
    """The artist's rendered box in display units, after a draw."""
    figure.canvas.draw()
    return artist.get_window_extent(figure.canvas.get_renderer())


@pytest.mark.parametrize("dpi", [100, 300, 600])
@pytest.mark.parametrize("form", ["icon", "lockup", "stacked"])
@pytest.mark.parametrize("size", ["small", "large"])
def test_rendered_height_is_the_requested_inches_at_any_dpi(dpi, form, size):
    """The whole point of the zoom calculation (logo spec §3.3)."""
    figure, axes = plt.subplots(figsize=(6, 4), dpi=dpi)
    box = _extent(add_logo(axes, form=form, size=size), figure)
    assert box.height / dpi == pytest.approx(LOGO_SIZES[form][size], abs=1e-6)
    plt.close(figure)


def test_annotation_bbox_pad_is_zero():
    """``AnnotationBbox``'s default 0.4 font-size units adds 0.111 in at 10 pt."""
    figure, axes = plt.subplots(figsize=(6, 4), dpi=100)
    box = _extent(add_logo(axes, form="lockup", size="small"), figure)
    assert box.height / 100 == pytest.approx(0.30, abs=1e-6)
    plt.close(figure)


def test_explicit_height_in_inches_is_honoured():
    figure, axes = plt.subplots(figsize=(6, 4), dpi=100)
    box = _extent(add_logo(axes, size=1.25), figure)
    assert box.height / 100 == pytest.approx(1.25, abs=1e-6)
    plt.close(figure)
```

and widen the test module's two tephpy imports, now that the rest of the constants are
used:

```python
from tephpy._constants import LOGO_PAD, LOGO_SIZES, LOGO_ZORDER, POINTS_PER_INCH
from tephpy.plotting import add_logo, logo
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -k height -v`

Expected: collection error — `ImportError: cannot import name 'add_logo' from
'tephpy.plotting'`.

- [ ] **Step 3: Implement `add_logo` and export it**

Add to the end of `src/tephpy/plotting/logo.py`:

```python
def add_logo(  # noqa: PLR0913 -- the placement contract is one flat keyword set
    target: Figure | Axes | None = None,
    *,
    form: str = "lockup",
    size: str | float = "small",
    theme: str = "auto",
    loc: str | tuple[float, float] = "lower left",
    pad: float | None = None,
    zorder: float | None = None,
    **kwargs: Any,  # noqa: ANN401 -- pass-through to matplotlib
) -> AnnotationBbox:
    """Draw the tephpy logo on a figure or an axes.

    The logo is an :class:`matplotlib.offsetbox.AnnotationBbox` anchored in the
    target's own fraction coordinates, so a figure target places it against the
    figure edges and an axes target against the axes edges, exactly as ``legend``
    does (logo spec §3.4). Its rendered height is the number of inches asked for
    whatever the figure dpi (logo spec §3.3).

    Parameters
    ----------
    target : matplotlib.figure.Figure or matplotlib.axes.Axes, optional
        What to brand, and what the position is relative to. ``None`` takes the
        current figure.
    form : str, optional
        Which mark to draw: ``"lockup"``, ``"stacked"`` or ``"icon"``.
    size : str or float, optional
        A preset, ``"small"`` or ``"large"``, or an explicit height in inches.
    theme : str, optional
        Which variant to draw: ``"auto"``, ``"light"`` or ``"dark"``. The name is
        the *background* the logo is drawn on, so ``"dark"`` is the variant for a
        dark background. ``"auto"`` reads the target's facecolor.
    loc : str or tuple of float, optional
        A ``legend`` placement string, or an ``(x, y)`` pair in the target's
        fraction coordinates giving the logo's lower-left corner.
    pad : float, optional
        Points between the logo and the target's edge, ignored when `loc` is a
        pair. ``None`` takes ``LOGO_PAD``.
    zorder : float, optional
        Draw order. ``None`` takes ``LOGO_ZORDER``, which is above lines, text
        and legends.
    **kwargs : Any
        Passed through to :class:`matplotlib.offsetbox.OffsetImage`: ``alpha``,
        ``filternorm``, ``filterrad``, ``interpolation`` and ``resample``.

    Returns
    -------
    matplotlib.offsetbox.AnnotationBbox
        The artist, already added to the target, for restyling or removal.

    Raises
    ------
    TypeError
        If `target` is neither a figure nor an axes, if `loc` is neither a
        placement string nor a pair of floats, or if a keyword is not an
        ``OffsetImage`` option.
    ValueError
        If `form`, `size`, `theme` or `loc` names something that does not exist,
        if `size` is not a positive finite height, or if a `loc` pair holds a
        non-finite coordinate.
    """
    figure, axes = _resolve_target(target)
    height = _resolve_size(size, form)
    variant = _resolve_theme(theme, figure, axes)
    anchor, alignment, offset = _resolve_loc(
        loc, LOGO_PAD if pad is None else float(pad)
    )
    options = _image_options(kwargs)
    image = _load_master(form, variant)
    artist = AnnotationBbox(
        OffsetImage(image, zoom=height * POINTS_PER_INCH / image.shape[0], **options),
        xy=anchor,
        xycoords="axes fraction" if axes is not None else "figure fraction",
        xybox=offset,
        boxcoords="offset points",
        box_alignment=alignment,
        frameon=False,
        # Mandatory: the AnnotationBbox default of 0.4 font-size units adds a
        # constant 0.111 in to the rendered box at the 10 pt default font.
        pad=0.0,
        zorder=LOGO_ZORDER if zorder is None else float(zorder),
        annotation_clip=False,
    )
    owner: Figure | Axes = figure if axes is None else axes
    owner.add_artist(artist)
    return artist
```

Extend the module imports with
`from matplotlib.offsetbox import AnnotationBbox, OffsetImage`, add `LOGO_PAD`,
`LOGO_ZORDER` and `POINTS_PER_INCH` to the `tephpy._constants` block (keeping it
alphabetical), and add the export just below the imports:

```python
__all__ = ["add_logo"]
```

Then in `src/tephpy/plotting/__init__.py`:

```python
from tephpy.plotting.axes import TephigramAxes
from tephpy.plotting.logo import add_logo

__all__ = ["TephigramAxes", "add_logo"]
```

and update that module's docstring, which currently promises artists in a future release:

```python
"""Tephigram plotting: the matplotlib projection and the logo artist."""
```

- [ ] **Step 4: Run them to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -v`

Expected: all pass, including the 18 dpi/form/size combinations.

- [ ] **Step 5: Prove the `pad=0.0` test is not vacuous**

Delete the `pad=0.0,` line from the `AnnotationBbox` call, run
`pixi run --frozen pytest tests/plotting/test_logo.py -k "pad_is_zero or requested_inches" -v`,
and confirm 19 failures reporting heights inflated by 0.111 in (0.4111 rather than 0.30
for the small lockup). Restore the line and re-run: all pass.

- [ ] **Step 6: Write the failing placement tests**

Append to `tests/plotting/test_logo.py`:

```python
@pytest.mark.parametrize(("dpi", "figsize"), [(100, (6, 4)), (300, (4.5, 6))])
@pytest.mark.parametrize("loc", sorted(logo._LOC))
def test_every_placement_lands_where_its_table_row_says(loc, dpi, figsize):
    """One arithmetic check per row, so a transposed sign cannot hide.

    Two dpi and two aspect ratios, because the gap is in points and the anchor
    is a fraction — either could be right at one shape and wrong at the other.
    """
    figure, axes = plt.subplots(figsize=figsize, dpi=dpi)
    box = _extent(add_logo(axes, loc=loc, pad=LOGO_PAD), figure)
    target = axes.get_window_extent()
    scale = dpi / POINTS_PER_INCH
    anchor, alignment, signs = logo._LOC[loc]
    x = target.x0 + anchor[0] * target.width + signs[0] * LOGO_PAD * scale
    y = target.y0 + anchor[1] * target.height + signs[1] * LOGO_PAD * scale
    assert box.x0 == pytest.approx(x - alignment[0] * box.width, abs=0.01)
    assert box.y0 == pytest.approx(y - alignment[1] * box.height, abs=0.01)
    plt.close(figure)


def test_a_pair_places_the_lower_left_corner_and_ignores_pad():
    figure, axes = plt.subplots(figsize=(6, 4), dpi=100)
    box = _extent(add_logo(axes, loc=(0.35, 0.2), pad=50.0), figure)
    target = axes.get_window_extent()
    assert box.x0 == pytest.approx(target.x0 + 0.35 * target.width, abs=0.01)
    assert box.y0 == pytest.approx(target.y0 + 0.2 * target.height, abs=0.01)
    plt.close(figure)


def test_a_figure_target_anchors_to_the_figure_not_the_axes():
    """The distinguishing property: the figure box is strictly outside the axes box."""
    figure, axes = plt.subplots(figsize=(6, 4), dpi=100)
    on_figure = _extent(add_logo(figure, loc="lower left"), figure)
    on_axes = _extent(add_logo(axes, loc="lower left"), figure)
    assert on_figure.x0 < on_axes.x0
    assert on_figure.y0 < on_axes.y0
    assert on_figure.x0 == pytest.approx(LOGO_PAD * 100 / POINTS_PER_INCH, abs=0.01)
    plt.close(figure)
```

- [ ] **Step 7: Run them to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -k "placement or pair or anchors" -v`

Expected: all pass. These are green on arrival because Step 3 wired `_resolve_loc`'s
output into the artist; confirm they can fail by swapping `box_alignment=alignment` for
`box_alignment=(0.0, 0.0)`, re-running (expect 18 failures — nine placements × two figure
shapes; `lower left` survives because its alignment already is the lower-left corner),
then restoring it.

- [ ] **Step 8: Write the failing artist-contract tests**

Append to `tests/plotting/test_logo.py`:

```python
def test_the_artist_is_returned_attached_and_removable():
    """The caller can restyle or drop it — the reason it is returned at all."""
    figure, axes = plt.subplots()
    artist = add_logo(axes)
    assert artist in axes.artists
    assert artist.get_zorder() == LOGO_ZORDER
    artist.remove()
    assert artist not in axes.artists
    plt.close(figure)


def test_image_options_reach_the_offsetimage():
    figure, axes = plt.subplots()
    artist = add_logo(axes, alpha=0.5)
    assert artist.offsetbox.get_children()[0].get_alpha() == 0.5
    plt.close(figure)


def test_no_target_brands_the_current_figure():
    figure = plt.figure(figsize=(6, 4), dpi=100)
    assert add_logo().figure is figure
    plt.close(figure)


@pytest.mark.parametrize(
    ("kwargs", "error", "match"),
    [
        ({"form": "wordmark"}, ValueError, "unknown form"),
        ({"size": "medium"}, ValueError, "unknown size"),
        ({"theme": "sepia"}, ValueError, "unknown theme"),
        ({"loc": "best"}, ValueError, "no collision detection"),
        ({"bogus": 1}, TypeError, "unknown option"),
    ],
)
def test_every_resolver_is_wired_into_the_public_call(kwargs, error, match):
    """Each resolver's rejection must survive the trip through ``add_logo``."""
    figure, axes = plt.subplots()
    with pytest.raises(error, match=match):
        add_logo(axes, **kwargs)
    plt.close(figure)


def test_an_unusable_target_is_rejected():
    with pytest.raises(TypeError, match="Figure or an Axes"):
        add_logo("figure")
```

- [ ] **Step 9: Run them to verify they pass**

Run: `pixi run --frozen pytest tests/plotting/test_logo.py -v`

Expected: all pass.

- [ ] **Step 10: Run the whole suite and the lint gate**

Run: `pixi run --frozen tests` then `pixi run --frozen lint`

Expected: all pass. `test_import_tephpy_does_not_import_pyplot` from Task 2 is the one to
watch — if it fails, the `import matplotlib.pyplot` in `_resolve_target` has been hoisted
to module scope.

- [ ] **Step 11: Commit**

```bash
git add src/tephpy/plotting/logo.py src/tephpy/plotting/__init__.py \
        tests/plotting/test_logo.py
git commit -m "Add tephpy.plotting.add_logo"
```

---

## Task 5: How-to, image baseline and changelog

**Files:**
- Create: `docs/src/howtos/logo.rst`
- Modify: `docs/src/howtos/index.rst`
- Modify: `tests/plotting/test_images.py`
- Create: `tests/baseline/test_logo_on_a_tephigram.png` (generated)
- Create: `changelog/<PR>.feature.rst`

**Interfaces:**
- Consumes: `tephpy.plotting.add_logo` (Task 4).
- Produces: nothing further code depends on.

- [ ] **Step 1: Write the failing baseline test**

Append to `tests/plotting/test_images.py`:

```python
@pytest.mark.mpl_image_compare
def test_logo_on_a_tephigram():
    fig, ax = _tephigram_figure()
    add_logo(ax, loc="lower right")
    return fig
```

and extend that module's tephpy import to:

```python
from tephpy import Sounding, calc
from tephpy.plotting import add_logo
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pixi run --frozen pytest tests/plotting/test_images.py::test_logo_on_a_tephigram --mpl -v`

Expected: FAIL — `Image file not found for comparison test ... tests/baseline/test_logo_on_a_tephigram.png`.

- [ ] **Step 3: Generate just that baseline**

Do **not** run `pixi run --frozen baselines` — that regenerates every baseline in the
suite and would sweep unrelated changes into this PR. Generate the one:

```bash
pixi run --frozen pytest tests/plotting/test_images.py::test_logo_on_a_tephigram \
    --mpl-generate-path=tests/baseline
```

- [ ] **Step 4: Run it to verify it passes, and check the image**

Run: `pixi run --frozen pytest tests/plotting/test_images.py --mpl -v`

Expected: all pass.

Then open `tests/baseline/test_logo_on_a_tephigram.png` and confirm by eye that the
lockup sits inside the lower-right of the plotting box, is legible, and is the light
variant. A baseline nobody looked at only proves the output is *stable*, not *right*.

- [ ] **Step 5: Verify the three test environments agree**

Run:

```bash
pixi run --frozen -e test-py312 pytest tests/plotting/test_images.py --mpl -q
pixi run --frozen -e test-py313 pytest tests/plotting/test_images.py --mpl -q
pixi run --frozen -e test-py314 pytest tests/plotting/test_images.py --mpl -q
```

Expected: all pass. The baseline is generated in one environment and compared in three;
CI runs all three, so catching a mismatch here saves a round trip.

- [ ] **Step 6: Write the how-to**

Create `docs/src/howtos/logo.rst`:

```rst
.. _howto-logo:

Add the tephpy Logo
===================

``add_logo`` brands a figure or an axes in one call. It draws an
:class:`matplotlib.offsetbox.AnnotationBbox`, so the logo is a normal artist —
returned for restyling, and removable.

On the Plot or Around It
------------------------

What you call it on decides what the position is relative to, exactly as
``legend`` does. Pass the axes to place the logo inside the plotting box, or the
figure to place it against the figure edges — in the margin, clear of the
diagram:

.. code-block:: python

    import matplotlib.pyplot as plt

    import tephpy  # noqa: F401
    from tephpy.plotting import add_logo

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    add_logo(ax, loc="lower right")
    add_logo(fig, loc="upper left")

Calling it with no target at all brands the current figure, which is what you
want at an interactive prompt:

.. code-block:: python

    add_logo()

Size and Form
-------------

``size`` is a height in **inches**, so the logo renders the same size on screen
at 100 dpi and in a 600 dpi figure for print. The ``"small"`` and ``"large"``
presets are per form, because the three forms give the wordmark different shares
of their height:

.. code-block:: python

    add_logo(ax, form="stacked", size="large")
    add_logo(ax, form="icon", size=0.25)

Use ``form="lockup"`` — the default — where there is room for the wordmark,
``"stacked"`` where the space is taller than it is wide, and ``"icon"`` only
where the mark is already recognised.

Light and Dark
--------------

``theme`` names the **background** the logo is drawn on, not the ink. The
default, ``"auto"``, reads the target's facecolor, so the right variant appears
without being asked for on a white figure and under a dark style alike:

.. code-block:: python

    with plt.style.context("dark_background"):
        fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
        add_logo(ax)  # draws the dark-background variant

Override it when you are compositing the figure onto something else:

.. code-block:: python

    add_logo(ax, theme="dark")

One case ``"auto"`` cannot get right: ``savefig(transparent=True)`` does not change
any facecolor, it overrides alpha at draw time. ``"auto"`` still reads white and
picks the light variant — correct for a figure destined for a white page, wrong
for a dark one. Say which you meant:

.. code-block:: python

    add_logo(ax, theme="dark")
    fig.savefig("sounding.png", transparent=True)

Exact Placement
---------------

``loc`` takes the ``legend`` placement strings, with ``pad`` setting the gap in
points from the edge. ``loc="best"`` is not among them: ``add_logo`` does no
collision detection, and silently guessing wrong is worse than saying so.

For a position no string names, pass an ``(x, y)`` pair in the target's fraction
coordinates. It places the logo's lower-left corner and ignores ``pad``:

.. code-block:: python

    add_logo(ax, loc=(0.42, 0.05))

Coordinates outside ``[0, 1]`` are allowed and put the logo outside the box,
which is one way to caption a figure below its axes.

Restyling and Removal
---------------------

The returned artist is yours:

.. code-block:: python

    logo = add_logo(ax, alpha=0.6)
    logo.set_zorder(0)  # behind the isopleths rather than over them
    logo.remove()  # changed your mind
```

- [ ] **Step 7: Add it to the toctree**

In `docs/src/howtos/index.rst`, extend the toctree:

```rst
.. toctree::
    :maxdepth: 1

    emphasis
    logo
```

- [ ] **Step 8: Build the docs clean and check the cross-references**

Run: `pixi run --frozen docs-clean && pixi run --frozen docs`

An incremental build serves a stale draft, so `docs-clean` first is not optional.

Expected: no warnings. Then confirm in the built HTML that
``:class:`matplotlib.offsetbox.AnnotationBbox` `` in the how-to resolves to the matplotlib
docs through intersphinx, and that `add_logo` appears in the autoapi pages under
`tephpy.plotting.logo`.

- [ ] **Step 9: Write the changelog fragment**

Create `changelog/<PR>.feature.rst`, where `<PR>` is this pull request's number:

```rst
Added :func:`~tephpy.plotting.logo.add_logo`, which places the tephpy logo on a
figure or an axes in one call. The position is relative to whatever it is called
on — an axes anchors inside the plotting box, a figure against the figure edges —
using the ``legend`` placement vocabulary, and ``size`` is a height in inches, so
``add_logo(ax, loc="lower right")`` renders the same size at 100 dpi and at 600.
``theme="auto"`` picks the light or dark variant from the target's background.
The six brand masters ship inside the wheel, so it needs no docs tree and no
network. (:user:`claude`)
```

If the pull request closes an issue, cite it with the ``:issue:`` role in the sentence
describing what it fixes.

- [ ] **Step 10: Run the whole suite and the lint gate**

Run: `pixi run --frozen tests` then `pixi run --frozen lint`

Expected: all pass.

- [ ] **Step 11: Commit**

```bash
git add docs/src/howtos/logo.rst docs/src/howtos/index.rst \
        tests/plotting/test_images.py tests/baseline/test_logo_on_a_tephigram.png \
        changelog/
git commit -m "Document add_logo with a how-to and an image baseline"
```

- [ ] **Step 12: Raise the deferred follow-up**

The logo spec defers the tinted mono variant (`color=`) and records it as tracked, so
raise it. Confirm with your human partner before running this — it is outward-facing:

```bash
gh issue create \
  --title "add_logo: tinted mono variant via color=" \
  --label "type: enhancement" \
  --body 'The logo spec (docs/superpowers/specs/2026-08-01-add-logo-design.md §8) defers a
`color=` option that would tint the mark to a single colour.

It needs the mono SVGs from `logo-bundle.zip` rasterised offline and shipped as a
seventh through ninth master; matplotlib cannot rasterise SVG. The light masters
cannot substitute as an alpha mask — measured, they are three-tone with
substantial white knockout (19.2% of `icon-512-light.png` is pure white), so
flattening them by alpha collapses the mark.'
```

Do **not** apply `good-first-issue`.

---

## Done When

- `pixi run --frozen tests` and `pixi run --frozen lint` both pass on `feature/add-logo-impl`.
- `pixi run --frozen -e test-py312`, `-e test-py313` and `-e test-py314` all pass with `--mpl`.
- `pixi run --frozen docs-clean && pixi run --frozen docs` builds without warnings.
- `from tephpy.plotting import add_logo` works from a wheel built out of a clean checkout.
- The PR carries `type: enhancement` and a `changelog/<PR>.feature.rst` fragment.
