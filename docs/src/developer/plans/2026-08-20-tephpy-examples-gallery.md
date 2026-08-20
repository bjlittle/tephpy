# tephpy Examples Gallery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `tephpy.samples` and `tephpy.examples`, the `tephpy examples` command, and a sphinx-gallery gallery built from them — Plan 7a of the roadmap.

**Architecture:** Five `plot_*.py` modules under `src/tephpy/examples`, each defining `main() -> Figure`, each drawing on two IGRA ascents shipped in `src/tephpy/samples`. One registry in `src/tephpy/examples/__init__.py` is read by the command line, by the gallery's sort key and by the tests, so an example that stops being registered fails loudly rather than disappearing. sphinx-gallery scrapes the package into `docs/src/gallery` as a fifth top-level documentation section.

**Tech Stack:** sphinx-gallery 0.21.0 (native tags, `within_subsection_order`), click, pytest-mpl, setuptools package-data, pixi.

**Spec:** [`docs/src/developer/specs/2026-08-20-examples-gallery-design.md`](../specs/2026-08-20-examples-gallery-design.md) — cited throughout as `gallery spec §…`. The parent is `docs/src/developer/specs/2026-07-22-tephpy-design.md`, cited as `spec §…`; the sibling is `2026-08-17-published-figures-design.md`, cited as `plots spec §…`.

## Global Constraints

- **Every source file carries the BSD copyright header** (ruff `CPY001`), exactly:
  ```
  # Copyright (c) 2026, tephpy Contributors.
  #
  # This file is part of tephpy and is distributed under the 3-Clause BSD license.
  # See the LICENSE file in the package root directory for licensing details.
  ```
- **Every module opens `from __future__ import annotations`** (ruff isort `required-imports`).
- **Line length 88**; ruff `select = ["ALL", "D212"]`; numpydoc convention.
- **Every example is named `plot_*.py`.** sphinx-gallery's `filename_pattern` defaults to `/plot` and only a matching file is *executed* — a file outside the pattern renders silently with no figure and no error (gallery spec §3.2).
- **Every example defines `main() -> Figure`** returning the figure, and closes with `if __name__ == "__main__": main(); plt.show()` (gallery spec §3.3).
- **Figure size is `figsize=(8.0, 4.0)`, passed at each example's own `subplots`/`figure` call.** sphinx-gallery calls `plt.rcdefaults()` before every example, so a `conf.py` rcParam would be discarded (gallery spec §3.5).
- **Tag vocabulary is closed:** `analysis`, `barbs`, `diagram`, `indices`, `isopleths`, `metpy`, `overlay`, `shading`, `sounding`. Two to four per example, declared as `# sphinx_gallery_tags = [...]` (gallery spec §3.6).
- **No example reaches the network and none writes a file** (gallery spec §3.3).
- **Snippets and examples carry no linter directives** — `docs/src/developer/docs-style.rst`, "Code Examples". Where an import looks unused, say why in a comment; exemptions go in `pyproject.toml`'s per-file-ignores.
- **The docs build runs `--fail-on-warning --keep-going` with `nitpicky = True`.** Any new warning fails it.
- **Commit style:** imperative sentence-case subject, no `feat:` prefix (see `git log`). Every commit body ends with the `Co-Authored-By` trailer the repo uses.
- **Tests mirror the package layout** (`tests/AGENTS.md`): `tests/examples/` ↔ `tephpy.examples`; `tephpy.samples` has one module, so its tests are `tests/test_samples.py`.
- **Run lint in the `devs` environment:** `pixi run --frozen -e devs lint`. Plain `pixi run lint` fails — `pre-commit` is not in the default environment.
- **Run tests in the `test` environment:** `pixi run --frozen -e test pytest …`.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/tephpy/samples/__init__.py` | **Create.** `available()`, `path()`, `sounding(name)`; provenance in the module docstring. |
| `src/tephpy/samples/USM00072357-data-trimmed.txt` | **Create.** The shipped IGRA v2 station file: Norman, OK 2013-05-20, 12Z and 17Z. |
| `src/tephpy/examples/__init__.py` | **Create.** `REGISTRY` — CLI name to module, in gallery order. Not scraped (`ignore_pattern`). |
| `src/tephpy/examples/GALLERY_HEADER.rst` | **Create.** The gallery index's landing prose and the IGRA attribution. |
| `src/tephpy/examples/plot_parcel_analysis.py` | **Create.** spec §4's canonical figure. Leads the gallery; the pinned baseline. |
| `src/tephpy/examples/plot_tephigram.py` | **Create.** The bare diagram and `set_extent`. |
| `src/tephpy/examples/plot_sounding.py` | **Create.** Profiles plus gutter-staff barbs. |
| `src/tephpy/examples/plot_sounding_comparison.py` | **Create.** 12Z against 17Z; carries the `savefig` line in prose. |
| `src/tephpy/examples/plot_hodograph.py` | **Create.** MetPy's `Hodograph` beside a tephigram. |
| `src/tephpy/_cli.py` | **Modify.** Add the `examples` group: `list`, `run [NAME] [--all]`. |
| `src/tephpy/__init__.py` | **Modify.** Export `samples`. |
| `docs/src/_ext/tephpy_gallery_order.py` | **Create.** `RegistryOrder`, the pickleable `within_subsection_order` key. |
| `docs/src/conf.py` | **Modify.** Populate `sphinx_gallery_conf`; exclude the generated `.ipynb`. |
| `docs/src/index.rst` | **Modify.** Fifth grid card and toctree entry. |
| `docs/Makefile` | **Modify.** `clean` removes the generated gallery. |
| `.gitignore` | **Modify.** Ignore `docs/src/gallery/`. |
| `pyproject.toml` | **Modify**, by three tasks: the generator's `S310` exemption (Task 1), the example per-file-ignores and mypy override (Task 2), package-data (Task 6). |
| `MANIFEST.in` | **Modify.** Ship the sample and the gallery header in the sdist. |
| `.pre-commit-config.yaml` | **Modify.** Whitespace excludes for the capture; numpydoc exclude for examples. |
| `.github/workflows/ci-wheels.yml` | **Modify.** Smoke-test the installed package data. |
| `tests/test_samples.py` | **Create.** The sample accessors. |
| `tests/examples/__init__.py`, `tests/examples/test_examples.py` | **Create.** The three gates of gallery spec §3.7. |
| `tests/baseline/test_parcel_analysis_figure.png` | **Create.** spec §7's composed-figure baseline. |
| `tests/test_cli.py` | **Modify.** The `examples` group. |
| `tests/test_import.py` | **Modify.** `samples` joins `__all__`. |
| `tests/fixtures/generate_io_fixtures.py` | **Modify.** The sample as a second IGRA destination. |
| `tests/fixtures/io/README.md` | **Modify.** Record that second destination. |
| `docs/src/developer/docs-style.rst` | **Modify.** A "Gallery Examples" section. |
| `docs/src/developer/specs/2026-07-22-tephpy-design.md` | **Modify.** §8.6, §10's Plan 7 row, §10 item 15. |
| `docs/src/developer/specs/2026-08-17-published-figures-design.md` | **Modify.** §5's closing sentence. |
| `changelog/<PR>.feature.rst`, `changelog/<PR>.documentation.rst` | **Create.** |

**Branch.** `examples-gallery-…` — `ci-label.yml` maps the `example`/`examples` prefix to `type: examples`. The spec and this plan are already committed on `docs-examples-gallery-spec`; open that as its own `skip-changelog` PR, then branch the implementation from it.

---

## Task 1: The sample data

**Files:**
- Create: `src/tephpy/samples/__init__.py`, `src/tephpy/samples/USM00072357-data-trimmed.txt`
- Modify: `src/tephpy/__init__.py`, `tests/fixtures/generate_io_fixtures.py`, `tests/fixtures/io/README.md`, `.pre-commit-config.yaml`, `tests/test_import.py`, `pyproject.toml` (the generator's `S310` exemption only)
- Test: `tests/test_samples.py`

**Interfaces:**
- Consumes: `tephpy.io.igra.read(path, *, time: datetime | str | None = None) -> Sounding`; `Sounding.station: str | None`, `Sounding.time: datetime | None`, `Sounding.wind_speed`, `Sounding.wind_direction`.
- Produces: `tephpy.samples.available() -> tuple[str, ...]`, `tephpy.samples.path() -> Path`, `tephpy.samples.sounding(name: str) -> Sounding`. Sample names are `"norman-12z"` and `"norman-17z"`. Every later task calls `samples.sounding(...)`.

- [ ] **Step 1: Extend the fixture generator with the sample as a second destination**

Replace the module docstring's closing paragraph and the IGRA constants and loop in `tests/fixtures/generate_io_fixtures.py`. The docstring gains:

```python
Both captures record the same physical ascent (2026-07-21 12Z, released
11:17 UTC), so the two readers cross-validate.

And into ``src/tephpy/samples/``:

- ``USM00072357-data-trimmed.txt`` — the 2013-05-20 12Z and 17Z ascents
  from NCEI's IGRA v2 period-of-record file for Norman, Oklahoma
  (USM00072357), captured the same way. This one is not a fixture but
  shipped data, read by :mod:`tephpy.samples` and drawn by the gallery
  (gallery spec §3.1); it lives here because it is the same capture, and
  a second script would drift from this one.

Provenance — source URLs, capture date, method, attribution — is kept in
``io/README.md`` beside the fixtures, and for the shipped sample in the
:mod:`tephpy.samples` docstring, which autoapi publishes. Both must be
updated when this script is re-run.
"""
```

Replace the `IGRA` and `KEPT_HEADERS` constants with:

```python
NCEI = "https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/access"
ROOT = Path(__file__).resolve().parents[2]

#: One IGRA v2 capture each: the archive to fetch, the ascents to keep, and
#: where the trimmed station file lands.
IGRA_CAPTURES = (
    (
        f"{NCEI}/data-y2d/UKM00003808-data-beg2026.txt.zip",
        (" 2026 07 21 00 ", " 2026 07 21 12 "),
        ROOT / "tests/fixtures/io/UKM00003808-data-trimmed.txt",
    ),
    (
        f"{NCEI}/data-por/USM00072357-data.txt.zip",
        (" 2013 05 20 12 ", " 2013 05 20 17 "),
        ROOT / "src/tephpy/samples/USM00072357-data-trimmed.txt",
    ),
)
```

Replace the single IGRA block with the loop:

```python
for url, kept_headers, destination in IGRA_CAPTURES:
    with urlopen(url, timeout=300) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
        (member,) = bundle.namelist()
        lines = bundle.read(member).decode("ascii").splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("#") and any(stamp in line for stamp in kept_headers):
            levels = int(line[32:36])
            blocks.extend(lines[index : index + 1 + levels])
            index += 1 + levels
        else:
            index += 1
    destination.write_text("\n".join(blocks) + "\n")
    ascents = sum(1 for block in blocks if block.startswith("#"))
    print(f"igra: {destination.name} kept {ascents} ascents, {len(blocks)} lines")
```

- [ ] **Step 2: Exempt the capture from the whitespace hooks — *before* it exists**

IGRA is a fixed-width format whose records legitimately end with a trailing space. `trailing-whitespace` strips them, and the stripped file **still parses** — 68 levels either way — so nothing fails; only the byte-faithfulness the provenance claims quietly becomes false. Do this first, so the file is never committed already damaged.

In `.pre-commit-config.yaml`, extend three excludes:

```yaml
      - id: end-of-file-fixer
        exclude: '\.svg$|^tests/fixtures/io/|^src/tephpy/samples/.*\.txt$'
      - id: mixed-line-ending
        exclude: '^tests/fixtures/io/|^src/tephpy/samples/.*\.txt$'
      - id: no-commit-to-branch
      - id: trailing-whitespace
        # The io fixtures and the shipped sample are byte-faithful archive
        # captures (their records legitimately end with a trailing space).
        # The browser toolbar SVGs are likewise preserved byte-for-byte from
        # the pinned Matplotlib wheel.
        exclude: '^tests/fixtures/io/|^src/tephpy/samples/.*\.txt$|^docs/src/_static/browser-toolbar/.*\.svg$'
```

- [ ] **Step 3: Capture the sample**

Run **only** the IGRA half. The full script also refetches the Wyoming fixture from a live server, whose response is not guaranteed to reproduce the committed capture.

```bash
mkdir -p src/tephpy/samples
pixi run --frozen -e test python - <<'PY'
import io, pathlib, zipfile
from urllib.request import urlopen

src = pathlib.Path("tests/fixtures/generate_io_fixtures.py").read_text()
loop = src[src.index("for url, kept_headers, destination in IGRA_CAPTURES:"):]
NCEI = "https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/access"
captures = ((
    f"{NCEI}/data-por/USM00072357-data.txt.zip",
    (" 2013 05 20 12 ", " 2013 05 20 17 "),
    pathlib.Path("src/tephpy/samples/USM00072357-data-trimmed.txt"),
),)
exec(compile(loop, "loop", "exec"),
     {"io": io, "zipfile": zipfile, "urlopen": urlopen, "IGRA_CAPTURES": captures})
PY
```

Expected: `igra: USM00072357-data-trimmed.txt kept 2 ascents, 322 lines`. The archive is 80 MB, so allow a few minutes.

- [ ] **Step 4: Verify the capture byte for byte**

```bash
sha256sum src/tephpy/samples/USM00072357-data-trimmed.txt
wc -c src/tephpy/samples/USM00072357-data-trimmed.txt
```

Expected, exactly:

```
7eef36f9023f9a7856c629a333a4b773ba4c85706b861b3436e0c6fa3f4373b3
17104
```

A different size with the same two ascents means a whitespace hook ran on it. Re-run Step 3 after fixing Step 2.

- [ ] **Step 5: Write the failing tests**

Create `tests/test_samples.py` (BSD header, then):

```python
"""The sounding data tephpy ships (gallery spec §3.1)."""

from __future__ import annotations

import pytest

from tephpy import samples


def test_available_names_both_ascents():
    """The names are the gallery's, in the order the ascents were measured."""
    assert samples.available() == ("norman-12z", "norman-17z")


def test_path_is_a_real_file_beside_the_package():
    """An installed tephpy carries it, so it is a path that stays valid."""
    assert samples.path().is_file()
    assert samples.path().parent == samples.path().parent.resolve()


def test_sounding_reads_the_named_ascent():
    """The name selects an ascent, not merely the file holding both."""
    morning = samples.sounding("norman-12z")
    afternoon = samples.sounding("norman-17z")
    assert morning.station == afternoon.station
    assert morning.time.hour == 12
    assert afternoon.time.hour == 17


def test_sounding_carries_winds():
    """The barb and hodograph examples need them (gallery spec §3.1)."""
    snd = samples.sounding("norman-12z")
    assert snd.wind_speed is not None
    assert snd.wind_direction is not None


def test_unknown_sample_names_the_alternatives():
    """The message is the user's route out, so it lists what it accepts."""
    with pytest.raises(ValueError, match="norman-12z, norman-17z") as excinfo:
        samples.sounding("camborne")
    assert "camborne" in str(excinfo.value)
```

- [ ] **Step 6: Run the tests to verify they fail**

Run: `pixi run --frozen -e test pytest tests/test_samples.py -q`
Expected: collection error — `ModuleNotFoundError: No module named 'tephpy.samples'`.

- [ ] **Step 7: Write the accessors**

Create `src/tephpy/samples/__init__.py` (BSD header, then):

```python
"""Sounding data shipped with tephpy (gallery spec §3.1).

Two radiosonde ascents from Norman, Oklahoma on 2013-05-20, the morning of
the Moore EF5 tornado: the 12Z ascent of the canonical example (spec §4),
and the 17Z special released about three hours before the tornado touched
down. Both are in one IGRA v2 station file, read by name.

.. code-block:: python

    from tephpy import samples

    snd = samples.sounding("norman-12z")

**Provenance.** Captured 2026-08-20 by
``tests/fixtures/generate_io_fixtures.py`` from `NCEI's IGRA v2
period-of-record file for station USM00072357
<https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/
access/data-por/USM00072357-data.txt.zip>`__, keeping the two ascents of
that date as whole byte-faithful blocks — a header record and its declared
level count. The archive is the NOAA/NCEI Integrated Global Radiosonde
Archive version 2, a U.S. Government work in the public domain; cite it as
Durre, I., X. Yin, R. S. Vose, S. Applequist, and J. Arnfield (2016),
doi:10.7289/V5X63K0Q.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tephpy.io import igra

if TYPE_CHECKING:
    from tephpy.sounding import Sounding

__all__ = ["available", "path", "sounding"]

# The shipped IGRA v2 station file, holding every sample below.
_FILE = "USM00072357-data-trimmed.txt"

# Sample name to the nominal launch time that selects its ascent.
_SAMPLES = {
    "norman-12z": "2013-05-20 12:00",
    "norman-17z": "2013-05-20 17:00",
}


def available() -> tuple[str, ...]:
    """Report the sample names :func:`sounding` accepts.

    Returns
    -------
    tuple of str
        The names, in the order the ascents were measured.
    """
    return tuple(_SAMPLES)


def path() -> Path:
    """Return the shipped IGRA v2 station file.

    It holds every sample :func:`available` names, which is why this takes
    no argument. It is a file beside this module rather than an
    :mod:`importlib.resources` traversable: the caller this exists for is a
    reader opening it with :func:`tephpy.io.igra.read`, and a zip-imported
    install would hand them a path that vanishes on the next line.

    Returns
    -------
    pathlib.Path
        The station file.
    """
    return Path(__file__).parent / _FILE


def sounding(name: str) -> Sounding:
    """Read a shipped sounding by name.

    Parameters
    ----------
    name : str
        One of the names :func:`available` reports.

    Returns
    -------
    Sounding
        The ascent, read through :func:`tephpy.io.igra.read` — the same
        documented route a user's own file takes.

    Raises
    ------
    ValueError
        If `name` is not a shipped sample.
    """
    when = _SAMPLES.get(name)
    if when is None:
        msg = f"unknown sample {name!r}; available: {', '.join(available())}"
        raise ValueError(msg)
    return igra.read(path(), time=when)
```

The URL is wrapped inside an RST embedded hyperlink because the bare URL exceeds 88 characters. docutils strips whitespace inside `<…>`, so the link resolves to the full URL.

- [ ] **Step 8: Export `samples` from the package root**

In `src/tephpy/__init__.py`:

```python
from tephpy import calc, exceptions, io, plotting, samples, transforms
```

and add `"samples"` to `__all__`, between `"plotting"` and `"transforms"`.

- [ ] **Step 9: Update the namespace test that pins `__all__`**

`tests/test_import.py::test_top_level_namespace` asserts the exact set. Without this the suite fails with `AssertionError` naming `'samples'`. Add it to `expected`, between `"plotting"` and `"transforms"`:

```python
    expected = {
        "Sounding",
        "__version__",
        "calc",
        "config",
        "exceptions",
        "io",
        "plotting",
        "samples",
        "transforms",
    }
```

- [ ] **Step 10: Run the tests to verify they pass**

Run: `pixi run --frozen -e test pytest tests/test_samples.py tests/test_import.py -q`
Expected: 9 passed.

- [ ] **Step 11: Prove the tests are not vacuous**

Stage first — `git checkout <path>` reverts from the index, so an unstaged mutate-revert cycle discards the real work with the mutation.

```bash
git add -A
sed -i 's/"norman-17z": "2013-05-20 17:00",/"norman-17z": "2013-05-20 12:00",/' src/tephpy/samples/__init__.py
pixi run --frozen -e test pytest tests/test_samples.py -q
git checkout src/tephpy/samples/__init__.py
```

Expected: `FAILED tests/test_samples.py::test_sounding_reads_the_named_ascent`, then a clean restore.

- [ ] **Step 12: Record the second destination in the fixtures README**

In `tests/fixtures/io/README.md`, after the opening paragraph:

```markdown
That script writes a third file, which is **not** a fixture:
`src/tephpy/samples/USM00072357-data-trimmed.txt`, the sounding data tephpy
ships and the gallery draws (gallery spec §3.1). It is the same IGRA capture
by the same method, so it is generated here rather than by a second script
that would drift from this one; its provenance is recorded in the
`tephpy.samples` docstring, which the API documentation publishes. Running
the script rewrites it too — update that docstring's capture date as well.
```

- [ ] **Step 13: Lint and commit**

- [ ] **Step 13: Restore the generator's URL check**

Not conditional — this task's own refactor causes it. The IGRA sources are still `https://` literals, but they now reach `urlopen` through a table and a loop variable, so ruff can no longer read the scheme off the argument and reports `S310 suspicious-url-open-usage`. In `pyproject.toml`, replace the generator's per-file-ignores entry:

```toml
# One-shot generator scripts (spec §7 layer 4), not package modules; their
# print is the script's user feedback.
"tests/fixtures/generate_*.py" = [
  "INP001",
  # The IGRA sources are ``https://`` literals a few lines above the call, but
  # they reach ``urlopen`` through a table and a loop variable, so ruff can no
  # longer read the scheme off the argument (gallery spec §3.1).
  "S310",
  "SLF001",
  "T201",
]
```

- [ ] **Step 14: Lint and commit**

```bash
pixi run --frozen -e devs lint
wc -c src/tephpy/samples/USM00072357-data-trimmed.txt   # still 17104
pixi run --frozen -e test pytest -q                      # 1466 collected
git add src/tephpy/samples src/tephpy/__init__.py tests/test_samples.py \
        tests/test_import.py tests/fixtures/generate_io_fixtures.py \
        tests/fixtures/io/README.md .pre-commit-config.yaml pyproject.toml
git commit -m "Ship two Norman soundings as tephpy.samples"
```

---

## Task 2: The examples package and the canonical example

**Files:**
- Create: `src/tephpy/examples/__init__.py`, `src/tephpy/examples/GALLERY_HEADER.rst`, `src/tephpy/examples/plot_parcel_analysis.py`, `tests/examples/__init__.py`, `tests/examples/test_examples.py`, `tests/baseline/test_parcel_analysis_figure.png`
- Modify: `pyproject.toml`, `.pre-commit-config.yaml`

**Interfaces:**
- Consumes: `tephpy.samples.sounding(name)` from Task 1. `tephpy.calc.parcel_path(snd)`, `tephpy.calc.indices(snd)`; the `TephigramAxes` methods `plot_sounding`, `plot_barbs`, `plot_profile`, `shade_cape`, `shade_cin`, `annotate_indices`, `set_extent`, `legend`.
- Produces: `tephpy.examples.REGISTRY: tuple[tuple[str, str], ...]` — `(cli_name, module_name)` pairs in gallery order. Read by Task 3's tests, Task 4's command line and Task 5's sort key. `tephpy.examples.plot_parcel_analysis.main() -> Figure`.

- [ ] **Step 1: Write the registry**

Create `src/tephpy/examples/__init__.py` (BSD header, then):

```python
"""The worked examples tephpy ships (gallery spec §3.2).

Each is a ``plot_*.py`` module with a ``main()`` returning its figure, run
from the command line with ``tephpy examples run <name>``, rendered into
the gallery by sphinx-gallery, and offered there as a download.

`REGISTRY` is the one list of them. The gallery's ordering, the command
line and the tests of gallery spec §3.7 all read it, so an example that
stops being registered is absent from all three at once — which is the
failure discovery by glob could not report.
"""

from __future__ import annotations

__all__ = ["REGISTRY"]

#: Command-line name to module name, in gallery order. The name is the
#: module's with its ``plot_`` prefix removed.
REGISTRY: tuple[tuple[str, str], ...] = (
    ("parcel-analysis", "plot_parcel_analysis"),
)
```

**The registry holds only the example this task creates.** Task 3 appends its four as it writes them, each entry landing in the same commit as its module. Registering all five up front would leave `test_registry_covers_the_directory` and four parametrised cases red for the whole of Task 2 — every commit unbisectable, and every reviewer having to re-derive that the red was planned. The gate is proven instead by Task 3 Step 8's mutation, which removes a registered entry and watches the suite fail.

- [ ] **Step 2: Write the gallery header**

Create `src/tephpy/examples/GALLERY_HEADER.rst` — sphinx-gallery requires `GALLERY_HEADER.[ext]` in the examples directory, so it ships inside the package:

```rst
.. _gallery:

Examples Gallery
================

Worked examples of what tephpy draws. Each is a complete script: click a
thumbnail for the figure and its source, then take the ``.py`` or the
notebook from the links at the foot of the page.

They ship in the package too, so an installed tephpy can run them::

    tephpy examples list
    tephpy examples run parcel-analysis

Every example draws on :mod:`tephpy.samples`, two radiosonde ascents from
Norman, Oklahoma on 2013-05-20 taken from the NOAA/NCEI Integrated Global
Radiosonde Archive version 2, a U.S. Government work in the public domain.
```

- [ ] **Step 3: Configure the three linters that reject an example on sight**

Without this, the file written in Step 6 fails lint four ways. In `pyproject.toml`, add to `[tool.ruff.lint.per-file-ignores]`, after the `docs/src/_ext/*.py` entry:

```toml
# A gallery example opens with sphinx-gallery's title block -- an RST section
# heading, not a docstring summary -- and declares its tags in the comment flag
# sphinx-gallery reads (gallery spec §3.2, §3.6).
"src/tephpy/examples/plot_*.py" = [
  "D205",   # blank line required between summary line and description
  "D400",   # first line should end with a period
  "ERA001", # commented-out code (the ``sphinx_gallery_tags`` flag)
  # Importing tephpy is what registers the "tephigram" projection, so the
  # diagram example imports it and never names it again. A ``# noqa`` on the
  # line would be a linter directive in code the gallery invites a reader to
  # copy, which docs-style.rst rules out; the import carries a comment
  # saying why it is there instead.
  "F401", # imported but unused
]
```

Add a mypy per-module override, after the existing `[[tool.mypy.overrides]]` block:

```toml
[[tool.mypy.overrides]]
# A projection is registered at runtime, so `plt.subplots(subplot_kw=
# {"projection": "tephigram"})` is typed `Axes` and every tephigram method
# on it is `attr-defined`. That is matplotlib's projection registry, not a
# tephpy defect -- cartopy's `GeoAxes` types the same way -- and the answer
# for library code is a `cast`. The examples are not library code: they are
# what a user writes, published for a user to copy, so they are written that
# way and the one error class that follows is disabled here (gallery
# spec §3.3). Everything else mypy checks about them still applies.
disable_error_code = ["attr-defined"]
module = ["tephpy.examples.*"]
```

In `.pre-commit-config.yaml`, on the `numpydoc-validation` hook:

```yaml
      - id: numpydoc-validation
        files: '^src/'
        # A gallery example's module docstring is sphinx-gallery's title
        # block -- an RST section heading and the page's opening prose --
        # so it has no numpydoc summary and never will (gallery spec §3.3).
        # An inline ``numpydoc ignore=SS01`` silences it and keeps ``main()``
        # validated, but docs-style.rst rules linter directives out of code a
        # reader is invited to copy, and the gallery hands them the file.
        # ruff's pydocstyle rules still cover both docstrings.
        exclude: '^src/tephpy/examples/plot_'
```

- [ ] **Step 4: Write the failing tests**

Create `tests/examples/__init__.py` (BSD header, then `"""Tests for :mod:`tephpy.examples`."""`), and `tests/examples/test_examples.py` (BSD header, then):

```python
"""The gallery examples and the registry over them (gallery spec §3.7)."""

from __future__ import annotations

import ast
from importlib import import_module
from pathlib import Path
import re

import matplotlib.pyplot as plt
import pytest

from tephpy import examples
from tephpy.examples import REGISTRY

#: The tag vocabulary of gallery spec §3.6. A tag outside it splits the
#: gallery's own filter, which is the whole reason the tags exist.
VOCABULARY = frozenset(
    {
        "analysis",
        "barbs",
        "diagram",
        "indices",
        "isopleths",
        "metpy",
        "overlay",
        "shading",
        "sounding",
    }
)

#: sphinx-gallery reads exactly this flag and silently discards any other
#: spelling, so this pattern is deliberately as strict as its parser
#: (gallery spec §3.6). Reading the text rather than importing
#: sphinx_gallery is what makes the assertion run in CI: the test
#: environments have no documentation dependencies.
_TAGS = re.compile(r"^# sphinx_gallery_tags = (?P<value>\[.*\])$", re.MULTILINE)

EXAMPLES = Path(examples.__file__).parent


def read_tags(source: str) -> list[str]:
    """Return the tags an example declares.

    Parameters
    ----------
    source : str
        The example module's text.

    Returns
    -------
    list of str
        The declared tags, empty if the file declares none.
    """
    match = _TAGS.search(source)
    if match is None:
        return []
    return ast.literal_eval(match.group("value"))


@pytest.mark.parametrize("module", [module for _, module in REGISTRY])
def test_example_runs(module):
    """Every registered example builds a figure.

    A broken example then fails the test suite across the supported
    Pythons, not only the documentation build.
    """
    figure = import_module(f"tephpy.examples.{module}").main()
    assert figure.axes
    plt.close(figure)


def test_registry_covers_the_directory():
    """Every ``plot_*.py`` is registered, and every registration exists."""
    found = {path.stem for path in EXAMPLES.glob("plot_*.py")}
    assert found == {module for _, module in REGISTRY}


def test_registry_names_drop_the_prefix():
    """The command-line name is the module's, without ``plot_``."""
    assert all(module == f"plot_{name.replace('-', '_')}" for name, module in REGISTRY)


@pytest.mark.parametrize("module", [module for _, module in REGISTRY])
def test_example_tags_are_declared_and_in_vocabulary(module):
    """Each example declares tags, all of them from the vocabulary.

    An empty list is the failure a misspelled flag produces: sphinx-gallery
    parses ``sphinx_gallery_tag`` into a differently-keyed entry and
    discards it without a warning, so the documentation build cannot report
    it (gallery spec §3.6).
    """
    tags = read_tags((EXAMPLES / f"{module}.py").read_text())
    assert tags, f"{module} declares no sphinx_gallery_tags"
    assert set(tags) <= VOCABULARY, sorted(set(tags) - VOCABULARY)


@pytest.mark.mpl_image_compare
def test_parcel_analysis_figure():
    """Pin spec §4's composed figure, which spec §7 has always required."""
    return import_module("tephpy.examples.plot_parcel_analysis").main()
```

- [ ] **Step 5: Run the tests to verify they fail**

Run: `pixi run --frozen -e test pytest tests/examples/ -q`
Expected: `ModuleNotFoundError: No module named 'tephpy.examples.plot_parcel_analysis'` from the parametrised run test and from `test_parcel_analysis_figure`, plus `test_registry_covers_the_directory` failing on an empty directory against a one-entry registry.

- [ ] **Step 6: Write the canonical example**

Create `src/tephpy/examples/plot_parcel_analysis.py` (BSD header, then):

```python
"""Parcel Analysis
===============

Lift a parcel from the surface, shade the energy available to it, and
annotate the indices that summarise the ascent.

The sounding is Norman, Oklahoma at 12Z on 2013-05-20 — the morning of the
Moore EF5 tornado, with about 1750 J/kg of CAPE under a -271 J/kg cap.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

import tephpy
from tephpy import samples

if TYPE_CHECKING:
    from matplotlib.figure import Figure

# sphinx_gallery_tags = ["analysis", "shading", "indices", "sounding"]


def main() -> Figure:
    """Draw the parcel analysis.

    Returns
    -------
    matplotlib.figure.Figure
        The composed figure.
    """
    snd = samples.sounding("norman-12z")
    fig, ax = plt.subplots(figsize=(8.0, 4.0), subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(snd)
    ax.plot_barbs(snd)
    parcel = tephpy.calc.parcel_path(snd)
    ax.plot_profile(parcel, color="k", linestyle="--")
    ax.shade_cape(snd, parcel)
    ax.shade_cin(snd, parcel)
    ax.annotate_indices(tephpy.calc.indices(snd))
    ax.legend()
    return fig


if __name__ == "__main__":
    main()
    plt.show()
```

Use a hyphen-minus in `-271 J/kg`, not U+2212 — ruff `RUF003` rejects the ambiguous minus sign in a docstring.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `pixi run --frozen -e test pytest tests/examples/ -q`
Expected: 5 passed — the registry holds one example, the directory holds one module, and they agree.

- [ ] **Step 8: Generate the composed-figure baseline**

`pixi run baselines` regenerates *every* baseline in the repository. Generate only the new one:

```bash
pixi run --frozen -e test pytest tests/examples/test_examples.py \
    --mpl-generate-path=tests/baseline -q
git status --short tests/baseline
```

Expected: exactly one untracked file, `tests/baseline/test_parcel_analysis_figure.png`. Any modified existing baseline means the whole suite ran — discard those with `git checkout tests/baseline`.

- [ ] **Step 9: Verify the baseline compares**

Run: `pixi run --frozen -e test pytest tests/examples/test_examples.py::test_parcel_analysis_figure --mpl -q`
Expected: 1 passed.

- [ ] **Step 10: Prove the tag gate is not vacuous, in both directions**

```bash
git add -A
sed -i 's/^# sphinx_gallery_tags = /# sphinx_gallery_tag = /' \
    src/tephpy/examples/plot_parcel_analysis.py
pixi run --frozen -e test pytest tests/examples/ -q -k parcel
git checkout src/tephpy/examples/plot_parcel_analysis.py

sed -i 's/\["analysis", /["Analysis", /' src/tephpy/examples/plot_parcel_analysis.py
pixi run --frozen -e test pytest tests/examples/ -q -k parcel
git checkout src/tephpy/examples/plot_parcel_analysis.py
```

Expected: the first fails with `plot_parcel_analysis declares no sphinx_gallery_tags`; the second with `['Analysis']`. A misspelled flag and an out-of-vocabulary tag are the two silent failures §3.6 exists to catch, so both must be loud here.

- [ ] **Step 11: Lint and commit**

```bash
pixi run --frozen -e devs lint
git add src/tephpy/examples tests/examples tests/baseline pyproject.toml \
        .pre-commit-config.yaml
git commit -m "Add the parcel analysis example and the registry over it"
```

Confirm the whole suite is green before committing — `pixi run --frozen -e test pytest --mpl -q`, expecting **1471 passed** (1461 on `main`, plus Task 1's 5 and this task's 5). Every task in this plan leaves the suite green; a red one means the registry and the directory have gone out of step.

---

## Task 3: The remaining four examples

**Files:**
- Create: `src/tephpy/examples/plot_tephigram.py`, `plot_sounding.py`, `plot_sounding_comparison.py`, `plot_hodograph.py`
- Modify: `src/tephpy/examples/__init__.py` (the four remaining registry entries)
- Test: `tests/examples/test_examples.py` (already written; it covers each example as it is registered)

**Interfaces:**
- Consumes: `REGISTRY` and `samples.sounding` as in Task 2; `metpy.calc.wind_components`, `metpy.plots.Hodograph`.
- Produces: `main() -> Figure` in each of the four modules, and the completed five-entry `REGISTRY` every later task reads.

Each module and its registry entry land **together**. Write the module, add its line to `REGISTRY`, run `pytest tests/examples/ -q`, and only then start the next — the suite is green at every one of those points, and a module added without its entry fails `test_registry_covers_the_directory` immediately rather than four steps later.

- [ ] **Step 1: Confirm the starting point is green**

Run: `pixi run --frozen -e test pytest tests/examples/ -q`
Expected: 5 passed — Task 2's one example, registered and drawing.

- [ ] **Step 2: Write `plot_tephigram.py`**

BSD header, then:

```python
"""The Tephigram
=============

The bare diagram: five isopleth families on a coordinate system rotated so
that isotherms and dry adiabats cross at right angles.

The projection is registered by importing tephpy, and the extent is given
as two (pressure, temperature) corners.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

import tephpy  # registers the "tephigram" projection

if TYPE_CHECKING:
    from matplotlib.figure import Figure

# sphinx_gallery_tags = ["diagram", "isopleths"]


def main() -> Figure:
    """Draw a tephigram over a chosen extent.

    Returns
    -------
    matplotlib.figure.Figure
        The composed figure.
    """
    fig, ax = plt.subplots(figsize=(8.0, 4.0), subplot_kw={"projection": "tephigram"})
    ax.set_extent(((1050.0, -40.0), (200.0, 40.0)))
    ax.set_title("Tephigram")
    return fig


if __name__ == "__main__":
    main()
    plt.show()
```

This is the one example whose `import tephpy` is never named again. The trailing comment is the answer docs-style.rst prescribes; the `F401` exemption of Task 2 Step 3 is what keeps it out of a `# noqa`.

- [ ] **Step 3: Write `plot_sounding.py`**

BSD header, then:

```python
"""A Sounding
==========

Temperature and dewpoint profiles, with the ascent's wind barbs on the
gutter staff to the right of the diagram.

The sounding is Norman, Oklahoma at 12Z on 2013-05-20.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from tephpy import samples

if TYPE_CHECKING:
    from matplotlib.figure import Figure

# sphinx_gallery_tags = ["sounding", "barbs"]


def main() -> Figure:
    """Draw a sounding and its wind barbs.

    Returns
    -------
    matplotlib.figure.Figure
        The composed figure.
    """
    snd = samples.sounding("norman-12z")
    fig, ax = plt.subplots(figsize=(8.0, 4.0), subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(snd)
    ax.plot_barbs(snd)
    ax.legend()
    return fig


if __name__ == "__main__":
    main()
    plt.show()
```

No bare `import tephpy` here: importing `tephpy.samples` imports the package, which registers the projection.

- [ ] **Step 4: Write `plot_sounding_comparison.py`**

BSD header, then:

```python
"""Comparing Two Soundings
=======================

Two ascents from the same station on the same day, overlaid on a fixed
extent so the change between them is the only thing that moves.

Norman, Oklahoma on 2013-05-20: the 12Z ascent, and the 17Z special
released about three hours before the Moore EF5 tornado. Over those five
hours the cap erodes from -271 J/kg to nothing while CAPE nearly triples.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from tephpy import samples

if TYPE_CHECKING:
    from matplotlib.figure import Figure

# sphinx_gallery_tags = ["overlay", "sounding"]

# Both profiles are drawn against this, so neither ascent's own data can
# decide the frame the comparison is read in.
EXTENT = ((1050.0, -30.0), (200.0, 40.0))


def main() -> Figure:
    """Overlay the 12Z and 17Z ascents.

    Returns
    -------
    matplotlib.figure.Figure
        The composed figure.
    """
    morning = samples.sounding("norman-12z")
    afternoon = samples.sounding("norman-17z")
    fig, ax = plt.subplots(figsize=(8.0, 4.0), subplot_kw={"projection": "tephigram"})
    ax.set_extent(EXTENT)
    ax.plot_sounding(morning, linestyle="--")
    ax.plot_sounding(afternoon)
    ax.legend()
    return fig


# %%
# Saving the Figure
# -----------------
#
# The diagram is drawn as vectors, so it saves at publication quality:
#
# .. code-block:: python
#
#     fig.savefig("sounding-comparison.pdf")
#
# It is shown rather than run, so that browsing the gallery writes no
# files.

if __name__ == "__main__":
    main()
    plt.show()
```

The `# %%` block is sphinx-gallery's prose-cell marker: it renders as a section on the page and stays a comment in the downloaded script. It sits **before** the `__main__` guard, so the page ends on prose rather than on plumbing. This is where spec §4's closing `savefig` lands — shown, not executed (gallery spec §3.3).

- [ ] **Step 5: Write `plot_hodograph.py`**

BSD header, then:

```python
"""A Hodograph beside a Tephigram
==============================

tephpy draws tephigrams and leaves hodographs to MetPy, so the two go side
by side in one figure, from one :class:`Sounding <tephpy.sounding.Sounding>`.

A tephigram shows the thermodynamic profile and a hodograph the wind
profile, and a forecaster reads them together.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
from metpy.calc import wind_components
from metpy.plots import Hodograph

from tephpy import samples

if TYPE_CHECKING:
    from matplotlib.figure import Figure

# sphinx_gallery_tags = ["metpy", "barbs", "sounding"]


def main() -> Figure:
    """Draw a tephigram and a hodograph from one sounding.

    Returns
    -------
    matplotlib.figure.Figure
        The composed figure.
    """
    snd = samples.sounding("norman-12z")
    fig = plt.figure(figsize=(8.0, 4.0))
    ax = fig.add_subplot(1, 2, 1, projection="tephigram")
    ax.plot_sounding(snd)
    ax.plot_barbs(snd)
    hodograph = Hodograph(fig.add_subplot(1, 2, 2), component_range=40.0)
    hodograph.add_grid(increment=10.0)
    hodograph.plot(*wind_components(snd.wind_speed, snd.wind_direction))
    return fig


if __name__ == "__main__":
    main()
    plt.show()
```

The cross-reference must be `:class:`Sounding <tephpy.sounding.Sounding>``. autoapi publishes the class at `tephpy.sounding.Sounding`, and `numpydoc_xref_aliases` maps the bare name only for parameter and return types — a plain `` :class:`~tephpy.Sounding` `` fails the docs build with `py:class reference target not found`.

- [ ] **Step 6: Verify the completed registry**

By now `REGISTRY` carries all five entries, in gallery order, added one per module:

```python
REGISTRY: tuple[tuple[str, str], ...] = (
    ("parcel-analysis", "plot_parcel_analysis"),
    ("tephigram", "plot_tephigram"),
    ("sounding", "plot_sounding"),
    ("sounding-comparison", "plot_sounding_comparison"),
    ("hodograph", "plot_hodograph"),
)
```

Run: `pixi run --frozen -e test pytest tests/examples/ --mpl -q`
Expected: 13 passed.

- [ ] **Step 7: Check every figure came out the intended size and shape**

```bash
pixi run --frozen -e test python - <<'PY'
import matplotlib
matplotlib.use("Agg")
from importlib import import_module
from tephpy.examples import REGISTRY

for name, module in REGISTRY:
    fig = import_module(f"tephpy.examples.{module}").main()
    print(f"{name:22} axes={len(fig.axes)} size={fig.get_size_inches()}")
PY
```

Expected:

```
parcel-analysis        axes=3 size=[8. 4.]
tephigram              axes=1 size=[8. 4.]
sounding               axes=2 size=[8. 4.]
sounding-comparison    axes=1 size=[8. 4.]
hodograph              axes=3 size=[8. 4.]
```

An `8.0 × 4.0` that came out `6.4 × 4.8` means a `figsize` was dropped — sphinx-gallery's `plt.rcdefaults()` gives no second chance at it.

- [ ] **Step 8: Prove the registry gate is not vacuous**

```bash
git add -A
sed -i '/("hodograph", "plot_hodograph"),/d' src/tephpy/examples/__init__.py
pixi run --frozen -e test pytest tests/examples/ -q
git checkout src/tephpy/examples/__init__.py
```

Expected: `FAILED tests/examples/test_examples.py::test_registry_covers_the_directory`, and *only* that — dropping the entry also drops its parametrised cases, so the coverage test is the sole thing standing between an example and silent disappearance.

- [ ] **Step 9: Lint and commit**

```bash
pixi run --frozen -e devs lint
git add src/tephpy/examples
git commit -m "Add the four remaining gallery examples"
```

---

## Task 4: The `tephpy examples` command

**Files:**
- Modify: `src/tephpy/_cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `tephpy.examples.REGISTRY`; each module's `main()`.
- Produces: `tephpy examples list`, `tephpy examples run <name>`, `tephpy examples run --all`. `docs/src/reference/cli.rst` needs no edit — `sphinx-click` with `:nested: full` picks the group up automatically.

- [ ] **Step 1: Write the failing tests**

In `tests/test_cli.py`, extend the imports:

```python
from click.testing import CliRunner
import matplotlib.pyplot as plt
import pytest
import yaml

from tephpy import _cli, _configfile
from tephpy.examples import REGISTRY
```

and append, after `test_help_lists_both_subcommands`:

```python
@pytest.fixture
def headless(monkeypatch):
    """Count ``plt.show`` calls instead of opening a window.

    Returns
    -------
    list of int
        One entry per call, so a test can assert how many there were.
    """
    calls = []
    monkeypatch.setattr(plt, "show", lambda *_, **__: calls.append(1))
    return calls


def test_examples_list_is_the_registry_in_order(runner):
    """The names the reader types, in the order the gallery shows them."""
    result = runner.invoke(_cli.main, ["examples", "list"])
    assert result.exit_code == 0
    assert result.output.split() == [name for name, _ in REGISTRY]


def test_examples_run_draws_one_example(runner, headless):
    result = runner.invoke(_cli.main, ["examples", "run", "tephigram"])
    assert result.exit_code == 0
    assert len(headless) == 1
    assert plt.get_fignums()
    plt.close("all")


def test_examples_run_all_shows_once(runner, headless):
    """``--all`` is a set of figures, not a queue of blocking windows.

    Showing inside the loop would make the reader close each figure before
    the next is drawn, which is the opposite of what ``--all`` is for.
    """
    result = runner.invoke(_cli.main, ["examples", "run", "--all"])
    assert result.exit_code == 0
    assert len(headless) == 1
    assert len(plt.get_fignums()) == len(REGISTRY)
    plt.close("all")


def test_examples_run_needs_a_name(runner, headless):
    result = runner.invoke(_cli.main, ["examples", "run"])
    assert result.exit_code == 2
    assert "--all" in result.output
    assert not headless


def test_examples_run_points_an_unknown_name_at_the_list(runner, headless):
    """The user has just mistyped a name, so name the command that has them."""
    result = runner.invoke(_cli.main, ["examples", "run", "tephigrams"])
    assert result.exit_code == 2
    assert "tephpy examples list" in result.output
    assert not headless
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen -e test pytest tests/test_cli.py -q -k examples`
Expected: 5 failed — click exits 2 with `No such command 'examples'`, so even the exit-code-2 tests fail on their message assertions.

- [ ] **Step 3: Write the command group**

In `src/tephpy/_cli.py`, add to the imports:

```python
from importlib import import_module

from tephpy.examples import REGISTRY
```

Neither is there yet — an earlier draft of this plan claimed `import_module`
already was, and it does not. Append to the end of the module:

```python
# Every docstring below is published twice: by ``--help``, and by sphinx-click
# on the CLI reference page. So the citation for this group (gallery spec §3.4)
# is here rather than in it — an internal section number is not an answer to
# "what does this command do?" in either place.
@main.group()
def examples() -> None:
    """List and run the worked examples."""


@examples.command("list")
def list_() -> None:
    """Report the examples, in gallery order."""
    for name, _ in REGISTRY:
        click.echo(name)


@examples.command()
@click.argument("name", required=False)
@click.option("--all", "run_all", is_flag=True, help="Run every example.")
def run(name: str | None, *, run_all: bool = False) -> None:
    """Run one example, or every example."""
    # name and run_all are already explained by the argument and option
    # above, which is what --help actually shows: numpydoc ignore=PR01
    #
    # Deferred on purpose: ``import tephpy`` does not import pyplot, and
    # this is the only command that needs it. At the top of the module it
    # would make ``tephpy config path`` select a matplotlib backend to
    # print a list of file paths.
    import matplotlib.pyplot as plt  # noqa: PLC0415

    modules = dict(REGISTRY)
    if run_all:
        chosen = list(modules.values())
    elif name is None:
        msg = "give an example name, or --all"
        raise click.UsageError(msg)
    elif name not in modules:
        msg = f"unknown example {name!r}; try 'tephpy examples list'"
        raise click.UsageError(msg)
    else:
        chosen = [modules[name]]
    for module in chosen:
        import_module(f"tephpy.examples.{module}").main()
    # One show for all of them: it blocks until the reader closes the
    # windows, so showing inside the loop would make --all a queue of
    # figures rather than a set.
    plt.show()
```

The `list` command is the function `list_` with an explicit `"list"` name, because `list` shadows the builtin (ruff `A001`).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen -e test pytest tests/test_cli.py -q`
Expected: 20 passed.

- [ ] **Step 5: Prove the one-show-for-all claim is guarded**

```bash
git add -A
sed -i '/import_module(f"tephpy.examples.{module}").main()/a\        plt.show()' \
    src/tephpy/_cli.py
pixi run --frozen -e test pytest tests/test_cli.py -q
git checkout src/tephpy/_cli.py
```

Expected: `FAILED … test_examples_run_draws_one_example - assert 2 == 1` and `FAILED … test_examples_run_all_shows_once - assert 6 == 1`.

- [ ] **Step 6: Check the command by hand**

```bash
pixi run --frozen -e test tephpy examples list
pixi run --frozen -e test tephpy examples --help
```

Expected: the five names in registry order, then a help screen listing `list` and `run`.

- [ ] **Step 7: Lint and commit**

```bash
pixi run --frozen -e devs lint
git add src/tephpy/_cli.py tests/test_cli.py
git commit -m "Add a tephpy examples command that lists and runs them"
```

---

## Task 5: The gallery build

**Files:**
- Create: `docs/src/_ext/tephpy_gallery_order.py`
- Modify: `docs/src/conf.py`, `docs/src/index.rst`, `docs/Makefile`, `.gitignore`

**Interfaces:**
- Consumes: `tephpy.examples.REGISTRY`; `src/tephpy/examples/GALLERY_HEADER.rst`.
- Produces: `docs/src/gallery/` (generated, git-ignored) with `index.rst` and one page per example; the `gallery` label from `GALLERY_HEADER.rst`.

- [ ] **Step 1: Write the sort key**

Create `docs/src/_ext/tephpy_gallery_order.py` (BSD header, then):

```python
"""Order the gallery by :data:`tephpy.examples.REGISTRY` (gallery spec §3.5).

sphinx-gallery's default sorts a subsection by code length, which buries
the canonical figure -- the longest example, and the one that should lead.

This is named in ``conf.py`` as the dotted string
``"tephpy_gallery_order.RegistryOrder"``, not as the class itself:
sphinx-gallery imports either, but a class in ``sphinx_gallery_conf`` makes
that value unpickleable, and Sphinx then warns ``cannot cache unpickleable
configuration value`` -- which this project's ``--fail-on-warning`` build
turns into a failure.
"""

from __future__ import annotations

from tephpy.examples import REGISTRY

_ORDER = {f"{module}.py": index for index, (_, module) in enumerate(REGISTRY)}


class RegistryOrder:
    """Sort key placing gallery entries in registry order."""

    def __init__(self, src_dir: str) -> None:
        """Record the directory being sorted.

        Parameters
        ----------
        src_dir : str
            The examples directory sphinx-gallery is sorting. Unused: one
            registry covers every example, and sphinx-gallery constructs
            the key per directory regardless.
        """
        self.src_dir = src_dir

    def __call__(self, filename: str) -> int:
        """Return `filename`'s position in the registry.

        Parameters
        ----------
        filename : str
            An example's basename, as sphinx-gallery found it.

        Returns
        -------
        int
            Its registry index.

        Raises
        ------
        KeyError
            If the file is not registered. The test of gallery spec §3.7
            reports that first; this is the build's own backstop.
        """
        return _ORDER[filename]
```

`docs/src/_ext/` is already a `sys.path` entry with an `INP001` per-file-ignore, so no configuration change is needed to import it by top-level module name.

- [ ] **Step 2: Point sphinx-gallery at the package**

In `docs/src/conf.py`, replace the empty configuration:

```python
# -- sphinx-gallery ----------------------------------------------------------
# Scrapes the examples out of the package (gallery spec §3.5). `gallery_dirs`
# is inside the Sphinx source tree because sphinx-gallery writes there, and
# git-ignored because everything in it is generated.
sphinx_gallery_conf = {
    "examples_dirs": ["../../src/tephpy/examples"],
    "gallery_dirs": ["gallery"],
    # A dotted string, not the class: see tephpy_gallery_order's docstring.
    "within_subsection_order": "tephpy_gallery_order.RegistryOrder",
}
```

- [ ] **Step 3: Exclude the generated notebooks**

Still in `conf.py`, replace `exclude_patterns`:

```python
exclude_patterns = [
    "brand/assets/*",
    "developer/plans/**",
    # sphinx-gallery writes a downloadable notebook beside each generated page,
    # and myst-nb makes ``.ipynb`` a source suffix -- so without this Sphinx
    # finds two documents claiming the docname ``gallery/plot_tephigram`` and
    # reads whichever it discovered first, leaving every
    # ``sphx_glr_gallery_*`` label undefined (gallery spec §3.5).
    "gallery/**.ipynb",
]
```

Skipping this costs fifteen warnings under `--fail-on-warning`: five `multiple files found for the document gallery/plot_*` and ten `undefined label: sphx_glr_gallery_plot_*.py`.

- [ ] **Step 4: Give the gallery a place in the navigation**

In `docs/src/index.rst`, add a fifth grid card after the reference card:

```rst
    .. grid-item-card:: Examples Gallery
        :link: gallery/index
        :link-type: doc

        Worked examples of what tephpy draws.
```

and a toctree entry between `reference/index` and `developer/index`:

```rst
    tutorials/index
    howtos/index
    explanation/index
    reference/index
    gallery/index
    developer/index
```

- [ ] **Step 5: Ignore and clean the generated tree**

In `.gitignore`, after `docs/src/sg_execution_times.rst`:

```
docs/src/gallery/
```

In `docs/Makefile`, extend `clean`:

```make
clean:
	rm -rf $(BUILDDIR) $(SOURCEDIR)/reference/generated $(SOURCEDIR)/gallery
	rm -f $(SOURCEDIR)/sg_execution_times.rst
```

Tabs, not spaces — it is a Makefile recipe.

- [ ] **Step 6: Build the documentation**

```bash
pixi run --frozen -e docs docs-html
```

Expected: `Sphinx-Gallery successfully executed 5 out of 5 files`, then `build succeeded.` — no warnings, because the build runs `--fail-on-warning`.

`docs-html` depends on `docs-clean`, which is `make clean` in `docs/`, so Step 5's Makefile edit is what makes this build a clean one. Without it the stale `docs/src/gallery` survives and the build serves a draft of the previous run.

- [ ] **Step 7: Verify the ordering, the tags and the filter UI**

```bash
pixi run --frozen -e test python - <<'PY'
import pathlib, re

index = pathlib.Path("docs/_build/html/gallery/index.html").read_text()
print("order:", re.findall(r'gallery/(plot_\w+)\.html', index)[:5])
print("tags: ", re.findall(r"data-sgtags='([^']+)'", index))
print("filter:", pathlib.Path("docs/_build/html/_static/sg-tags.js").is_file())
page = pathlib.Path("docs/_build/html/gallery/plot_parcel_analysis.html").read_text()
print("rendered:", "Tags" in page and "analysis" in page)
PY
```

Expected: the order `['plot_parcel_analysis', 'plot_tephigram', 'plot_sounding', 'plot_sounding_comparison', 'plot_hodograph']` — registry order, not length order; five `data-sgtags` lists; `sg-tags.js` present; `rendered: True`.

- [ ] **Step 8: Confirm the CLI reference page picked the group up**

```bash
pixi run --frozen -e test python -c "
import html, pathlib, re
t = html.unescape(re.sub(r'<[^>]+>', ' ', pathlib.Path('docs/_build/html/reference/cli.html').read_text()))
print('examples' in t, 'Run every example' in t)
"
```

Expected: `True True`. If either is False, `sphinx-click`'s `:nested:` option has changed and `docs/src/reference/cli.rst` does need an edit after all.

- [ ] **Step 9: Lint and commit**

```bash
pixi run --frozen -e devs lint
git add docs/src/_ext/tephpy_gallery_order.py docs/src/conf.py docs/src/index.rst \
        docs/Makefile .gitignore
git commit -m "Build the examples gallery as a fifth documentation section"
```

---

## Task 6: Packaging the data into the wheel

**Files:**
- Modify: `pyproject.toml`, `MANIFEST.in`, `.github/workflows/ci-wheels.yml`

**Interfaces:**
- Consumes: `src/tephpy/samples/*.txt`, `src/tephpy/examples/GALLERY_HEADER.rst`, the `tephpy` console script.
- Produces: a wheel and sdist that carry both non-Python files; a CI check that proves it.

- [ ] **Step 1: Declare the package data**

`[tool.setuptools.packages.find]`'s glob already picks up `tephpy.samples` and `tephpy.examples`, but setuptools ships only `.py` from them. In `pyproject.toml`:

```toml
[tool.setuptools.package-data]
tephpy = [
  "py.typed",
  "plotting/_static/*.png",
  # The shipped sounding data, and the gallery's landing page. Both are read
  # from an installed tephpy: the first by `tephpy.samples`, the second by
  # sphinx-gallery building the documentation against one (gallery spec §3.1).
  "samples/*.txt",
  "examples/GALLERY_HEADER.rst",
]
```

- [ ] **Step 2: Declare them for the sdist**

In `MANIFEST.in`, after the `plotting/_static` line:

```
recursive-include src/tephpy/samples *.txt
include src/tephpy/examples/GALLERY_HEADER.rst
```

- [ ] **Step 3: Confirm the generator's `S310` exemption is already in place**

Task 1 Step 13 added it — that task could not pass its own lint gate without it. Verify rather than re-add:

```bash
grep -A4 'generate_\*\.py' pyproject.toml
```

Expected: the entry lists `INP001`, `S310`, `SLF001`, `T201`, with the comment explaining that the URLs reach `urlopen` through a loop variable. If `S310` is missing, Task 1 was committed with a lint failure — stop and fix it there.

- [ ] **Step 4: Extend the wheel smoke test**

`.github/workflows/ci-wheels.yml` is the only check that exercises the installed artifact rather than the checkout, so it is the only one that can catch a `package-data` miss. In the `Wheel install smoke test` step, extend the heredoc and add a line after it:

```yaml
          import tephpy
          fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
          assert type(ax).__name__ == "TephigramAxes", type(ax)
          # The sample data and the gallery header are package data, not
          # Python, so only an installed wheel can prove they were shipped
          # (gallery spec §3.7). Reading a sounding covers the sample file;
          # the header is what sphinx-gallery reads out of an installed
          # tephpy to build the gallery's landing page.
          from importlib.resources import files
          snd = tephpy.samples.sounding("norman-12z")
          assert snd.wind_speed is not None
          header = files("tephpy.examples") / "GALLERY_HEADER.rst"
          assert header.is_file(), header
          print("wheel smoke OK:", tephpy.__version__)
          PY
          /tmp/smoke/bin/tephpy examples list
```

- [ ] **Step 5: Build both artifacts**

```bash
rm -rf /tmp/wheelcheck && mkdir /tmp/wheelcheck
pixi run --frozen -e devs python -m build --outdir /tmp/wheelcheck .
```

- [ ] **Step 6: Verify both carry the data**

```bash
tar tzf /tmp/wheelcheck/*.tar.gz | grep -E "samples/|GALLERY_HEADER"
pixi run --frozen -e test python -c "
import glob, zipfile
for n in sorted(zipfile.ZipFile(glob.glob('/tmp/wheelcheck/*.whl')[0]).namelist()):
    if 'samples' in n or 'examples' in n: print(n)
"
```

Expected from the wheel, exactly nine entries — five `plot_*.py`, `examples/__init__.py`, `examples/GALLERY_HEADER.rst`, `samples/__init__.py`, `samples/USM00072357-data-trimmed.txt`. The sdist shows the same under a version-prefixed directory.

- [ ] **Step 7: Run the smoke test locally against the built wheel**

The venv borrows the pixi environment's dependencies so this needs no network:

```bash
rm -rf /tmp/smoke
pixi run --frozen -e test python -m venv --system-site-packages /tmp/smoke
/tmp/smoke/bin/pip install --no-deps --force-reinstall -q /tmp/wheelcheck/*.whl
/tmp/smoke/bin/python - <<'PY'
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tephpy
fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
assert type(ax).__name__ == "TephigramAxes", type(ax)
from importlib.resources import files
snd = tephpy.samples.sounding("norman-12z")
assert snd.wind_speed is not None
header = files("tephpy.examples") / "GALLERY_HEADER.rst"
assert header.is_file(), header
print("wheel smoke OK:", tephpy.__version__, tephpy.__file__)
PY
/tmp/smoke/bin/tephpy examples list
```

Expected: `wheel smoke OK: …` with a `tephpy.__file__` under `/tmp/smoke/`, not under the checkout — the check is worthless if it resolved the source tree — then the five names.

- [ ] **Step 8: Lint and commit**

```bash
pixi run --frozen -e devs lint
git add pyproject.toml MANIFEST.in .github/workflows/ci-wheels.yml
git commit -m "Ship the sample data and gallery header in the wheel"
```

---

## Task 7: Companion documentation

**Files:**
- Modify: `docs/src/developer/docs-style.rst`, `docs/src/developer/specs/2026-07-22-tephpy-design.md`, `docs/src/developer/specs/2026-08-17-published-figures-design.md`
- Create: `changelog/<PR>.feature.rst`, `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: everything above. Nothing consumes this task.

- [ ] **Step 1: Open the pull request first**

Changelog fragments are named for the PR, and an issue filed in between steals the number. Open the PR, then name the fragments from the number it is given.

```bash
gh pr create --fill --base main
```

If `gh pr create` returns 503, GitHub's GraphQL endpoint is down while REST still answers — create it through `gh api repos/:owner/:repo/pulls` instead.

- [ ] **Step 2: Add a "Gallery Examples" section to the docs style guide**

In `docs/src/developer/docs-style.rst`, between the `Published Figures` and `Attribute Documentation` sections:

```rst
Gallery Examples
----------------

The gallery is scraped from ``src/tephpy/examples``, which ships in the wheel:
every entry is a module a reader can download, and also one an installed tephpy
can run with ``tephpy examples run <name>``. The rules below are specified in
gallery spec §3.2, §3.3, §3.5, §3.6. Every one a test can read off a file — the
registry, the ``main()`` shape and its guard, the figure size, the tag
vocabulary and how many tags — is asserted by
``tests/examples/test_examples.py``. What belongs in the gallery at all, and
that an example reaches no network and writes no file, are left to review.

The gallery shows what the package draws. Everything else is a how-to. An
example whose subject is not a picture — getting data in, configuring the
package, installing it — belongs in the how-to quadrant, however much code it
carries (gallery spec §5). An example that happens to load data is fine; the
subject is what is tested, not the API surface touched.

Every module is named ``plot_*.py``, and the prefix is load-bearing.
sphinx-gallery's ``filename_pattern`` defaults to ``/plot``, and only a matching
file is *executed*: a file outside the pattern is still rendered, silently, with
no figure and no error.

Every module defines ``main()``, which builds the figure and returns it, and
closes with the guard that shows it:

.. code-block:: python

    def main() -> Figure:
        ...
        return fig


    if __name__ == "__main__":
        main()
        plt.show()

One construction then serves four consumers — sphinx-gallery, which executes the
file as ``__main__``; ``tephpy examples run``; ``pytest-mpl``, which decorates a
function returning a figure; and the reader running the downloaded script.
Showing inside ``main`` would cost the third of those, and the pinned figure
would then be a claim about the test rather than about what was published.

An example takes any data it needs from :mod:`tephpy.samples`, reaches no
network, and writes no file. The documentation build executes it, so a
``savefig`` call would leave an artefact in the generated tree on every build;
the vector-output line appears in an example's prose instead, shown and not
run.

Add a new example to ``REGISTRY`` in ``src/tephpy/examples/__init__.py``, in the
position it should occupy. Registry order is gallery order is
``examples run --all`` order, and the tests read it: an unregistered
``plot_*.py`` fails them rather than disappearing quietly. Pass
``figsize=(8.0, 4.0)`` at the example's own ``subplots`` or ``figure`` call —
sphinx-gallery calls ``plt.rcdefaults()`` before every example, so a configured
default is discarded before the first line runs.

Tags come from a closed vocabulary — ``analysis``, ``barbs``, ``diagram``,
``indices``, ``isopleths``, ``metpy``, ``overlay``, ``shading``, ``sounding`` —
two to four per example, declared in the flag sphinx-gallery reads:

.. code-block:: python

    # sphinx_gallery_tags = ["analysis", "shading", "indices", "sounding"]

They render on the page and drive the index's filter buttons, so a ``barb``
beside a ``barbs`` splits the very index the feature exists to build. Widening
the vocabulary means editing ``VOCABULARY`` in
``tests/examples/test_examples.py``, which is deliberate. Spell the flag exactly:
sphinx-gallery parses ``sphinx_gallery_tag`` into a differently-keyed entry and
discards it in silence, with no warning to fail the build on — which is why the
test reads the flag out of the source text rather than asking the parser.

Leave the flag visible. ``sphinx_gallery_start_ignore`` would hide it from the
page, but the source is the point on a page whose purpose is showing source.
```

- [ ] **Step 3: Amend parent spec §8.6**

Replace the extensions bullet — sphinx-gallery's parenthesis grows, and `sphinx-tags` is deleted:

```markdown
- Extensions per geovista: **`sphinx-autoapi`** (API reference generated from `src/`),
  **`numpydoc`**, **`myst-nb`**, **`sphinx-gallery`** (one example per identified use case,
  scraped from `src/tephpy/examples`, tagged with the extension's own
  `sphinx_gallery_tags` flag and published as a fifth top-level section beside the four
  quadrants — gallery spec §3.5, §3.6), `sphinx-design`, `sphinx-copybutton`,
  `sphinx-togglebutton`, `sphinxcontrib-bibtex` (cited meteorology references).
```

- [ ] **Step 4: Split parent spec §10's Plan 7 row**

Replace the single row with two, and use the PR number from Step 1:

```markdown
| 7a | Examples gallery | gallery spec: `src/tephpy/samples` (two shipped IGRA ascents) and `src/tephpy/examples` (five examples — one per §1 use case, plus the §9 hodograph composition); the `tephpy examples` command; the sphinx-gallery build, its registry ordering and its native tags; composed §4-figure baseline (§7 — needed the union of Plans 5 and 6) | 2–6 | ✅ complete (PR {pull}`<N>`) |
| 7b | Documentation completion | §8.6: tutorials/how-tos/explanation content, glossary completion, `doctest` task + CI doctest run; README non-goals statement, the eccodes recipe and the reader how-to (§9, gallery spec §5); §8.3's SPEC 0 packaging statement (item 15) | 7a | **next** |
```

- [ ] **Step 5: Resolve the sphinx-tags deferral in parent spec §10 item 15**

In item 15's lead paragraph, replace `sphinx-tags (§8.6) → Plan 7;` with `sphinx-tags (§8.6) → rejected in Plan 7a;`, and rewrite the three Plan 7 lines of the per-deferral status:

```markdown
    - **Rejected** (2026-08-20, gallery spec §3.6): sphinx-tags (§8.6) — superseded.
      sphinx-gallery now reads a `sphinx_gallery_tags` flag and ships the index filter
      that was the whole reason to want tags, so adopting sphinx-tags would take a
      dependency to duplicate an installed feature. Site-wide tag pages across the
      narrative documentation are 7b's question.
    - **Deferred** (Plan 7b — {issue}`76`): the `doctest` task and the `ci-docs` doctest run (§8.2/§8.7).
    - **Deferred** (Plan 7b — {issue}`76`): the §8.3 packaging-guide SPEC 0 statement.
```

- [ ] **Step 6: Amend plots spec §5's closing sentence**

Replace ``sphinx_gallery_conf` keeps its empty directories. Nothing here populates them.`:

```markdown
`sphinx_gallery_conf` kept its empty directories through this document.
[`2026-08-20-examples-gallery-design.md`](2026-08-20-examples-gallery-design.md)
populates them: gallery spec §3.5 adopts §3.1's figure recipe and single `png` format
as this section asked, amending only where the recipe is applied — sphinx-gallery
resets matplotlib before every example, so each passes `figsize=(8.0, 4.0)` at its own
`subplots` call — and pinning one figure against a baseline rather than all five.
```

- [ ] **Step 7: Write the changelog fragments**

`changelog/<PR>.feature.rst`:

```rst
Added :mod:`tephpy.samples`, two radiosonde ascents shipped in the package, and
a ``tephpy examples`` command that lists and runs the worked examples an
installed tephpy carries. ``samples.sounding("norman-12z")`` reads one of the
two Norman, Oklahoma ascents of 2013-05-20 through :func:`tephpy.io.igra.read`,
so a script no longer has to build a sounding before it can draw one, and
``tephpy examples run parcel-analysis`` draws the figure the specification has
described in prose since the project started. See :ref:`gallery`.
(:user:`claude`)
```

`changelog/<PR>.documentation.rst`:

```rst
Added the :ref:`gallery`, five worked examples of what tephpy draws, built with
``sphinx-gallery`` from the modules the package ships. Each page shows the
figure and its source, offers the script and a notebook to download, and carries
tags the gallery index filters on. The example set covers the bare diagram, a
sounding with wind barbs, the parcel analysis with its CAPE and CIN shading, two
ascents overlaid, and MetPy's hodograph composed beside a tephigram.
(:user:`claude`)
```

Substitute your own GitHub username for `claude` in both.

- [ ] **Step 8: Update issue 76**

The sphinx-tags residual is superseded, not delivered. Comment on the issue rather than closing it — the other two residuals are still open and move to 7b. Use bare `#N` references, not Sphinx roles, which render literally on GitHub:

```bash
gh issue comment 76 --body "sphinx-tags is superseded rather than deferred. sphinx-gallery 0.21 reads a \`sphinx_gallery_tags\` flag per example and registers \`sg-tags.js\`, which gives the gallery index the tag filter that was the reason to want tags — so taking the dependency would duplicate an installed feature and leave two tag mechanisms live with nothing to say which an example's tags feed. Recorded as **Rejected** in the examples gallery design specification §3.6 and §7, and in spec §10 item 15. The other two residuals here — the doctest task with its ci-docs run, and the §8.3 SPEC 0 packaging statement — are unaffected and move to Plan 7b."
```

- [ ] **Step 9: Verify the citations resolve and the docs build clean**

```bash
pixi run --frozen -e devs lint
pixi run --frozen -e docs docs-html
pixi run --frozen -e docs docs-check-citations
```

`lint` runs the `check-citations` hook — "design specification citations resolve" — over the new `gallery spec §…` anchors in the source. Read its linked/literal counts, not just its exit code: a backticked citation is an inline literal, not a link, and the gate counts literals as legitimate.

`docs-check-citations` is the same question asked of the rendered HTML, and its page count is the one that moves — 52 pages with the gallery, since the five generated pages are pages like any other. Expect `739 linked, 43 literal`.

Do **not** reach for `docs-all` here. It adds `docs-browser-test`, which drives the PyScript demo in a Chromium the documentation environment installs Playwright for but does not carry, so it fails on a machine without a hand-installed browser — an unrelated dependency, and nothing in this plan touches the demo.

The other two gates are worth *not* running, and worth knowing why. `docs-check-figures` builds its expected set from the `:filename-prefix:` each `plot_directive` declares, deliberately rather than by globbing `_images/`; sphinx-gallery writes its figures through its own scraper and declares no prefix, so the gate stays at `12 compared across 2 pages` and is blind to all five gallery figures. `docs-check-links` likewise stays at `9 checked across 3 pages`. Nothing published by this plan is covered by either — which is precisely why gallery spec §3.7 pins the canonical figure with `pytest-mpl` in `tests/` instead, and why Task 2 Step 8's baseline is the only thing standing behind what the gallery draws.

- [ ] **Step 10: Run everything**

```bash
pixi run --frozen -e test pytest --mpl -q
```

Expected: `1490 passed, 1 skipped` — 29 more than `main`'s 1461 collected (18 in `tests/examples/`, 5 in `tests/test_samples.py`, 6 in `tests/test_cli.py`). A count that fell means something was destroyed; check against `main` before pushing.

- [ ] **Step 11: Commit**

```bash
git add docs/src/developer changelog
git commit -m "Record the gallery in the style guide and the specifications"
git push
```

- [ ] **Step 12: Verify the rendered documentation on the ReadTheDocs preview**

Probe `https://tephpy--<PR>.org.readthedocs.build/en/<PR>/gallery/index.html`. RTD skips commits, so a missing status check is not the same as no build. Check that the thumbnails are in registry order, that the tag filter buttons narrow them, and that the landing grid's fifth card reaches the gallery.

---

## Self-Review

**Spec coverage.** §3.1 → Task 1. §3.2 → Task 2 Steps 1–2, Task 3. §3.3 → Tasks 2–3 (the `main()` shape, the prose `savefig` in Task 3 Step 4). §3.4 → Task 4. §3.5 → Task 5. §3.6 → the tag flags in Tasks 2–3 and the gate in Task 2 Step 4. §3.7 → the three tests in Task 2 Step 4, packaging in Task 6, `docs-clean` in Task 5 Step 5. §4's five examples → Tasks 2–3. §5 → Task 7 Step 2's style-guide section. §6's companion changes → Task 7 (specs/index.rst was already updated in the spec commit). §7's open items need no action: three are rejections recorded in the spec, two are 7b deferrals, and {issue}`77`'s check-manifest gate is explicitly not fixed here.

**Type consistency.** `REGISTRY: tuple[tuple[str, str], ...]` of `(cli_name, module_name)` is read identically by `tephpy_gallery_order._ORDER` (Task 5), `_cli.list_`/`_cli.run` (Task 4) and all four registry tests (Task 2). `main() -> Figure` is the signature every example defines and every consumer calls. `samples.sounding(name) -> Sounding` is the only data entry point in all five examples. `samples.available() -> tuple[str, ...]` is used by `sounding`'s error message and asserted in `tests/test_samples.py`.

**Verification status.** Every code block in this plan was written at its real path and executed before the plan shipped: `pixi run --frozen -e devs lint` clean over the whole tree, `pytest --mpl` at 1484 passed, a clean `--fail-on-warning` docs build with the gallery, the built wheel installed into a venv and smoke-tested, and the mutation checks of Task 1 Step 11, Task 2 Step 10, Task 3 Step 8 and Task 4 Step 5 each confirmed failing and restoring.

**Amendments during execution.** Four, each recorded where it applies rather than only here. Task 2 registers only the example it creates and Task 3 appends the other four, so no commit leaves the registry gate red. Task 1 applies the generator's ruff `S310` exemption itself, since its own refactor is what provokes the rule, and Task 6 verifies it rather than adding it. Task 4's `run` refuses a name and `--all` together instead of silently letting the flag win, which is the sixth test in `tests/test_cli.py` and why the count before the final review was 1485 rather than the 1484 verified at ship time. And the whole-branch review closed the gap between what Task 7's style-guide section promised was asserted and what `tests/examples/test_examples.py` actually asserted: the figure size of gallery spec §3.5 and §3.6's two-to-four tag bound fold into the existing parametrisations, and the `__main__` guard — the branch's one silent failure mode, invisible to a suite that calls `main()` directly and to a build sphinx-gallery emits no warning from — gets a parametrised test of its own, which is the five that take the count above to 1490 and the rendered citations to 739.
