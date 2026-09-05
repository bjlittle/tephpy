# Getting Started Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reader who has never installed tephpy can find out how, install it, draw a tephigram in ten lines, and know where to go next — from a section that carries the same execution, figure and glossary guarantees as every other user page.

**Architecture:** Five hand-written reStructuredText pages in `docs/src/start/`, one of them a landing page in `narrative spec §3.9`'s shape. No new extension of this project's own; one third-party extension, `sphinx-iconify`, for the installation page's tool icons. The work is mostly *joining existing machinery*: four constants that name the Diátaxis quadrants are renamed to name the sections written for users, and then widened to include this one.

**Tech Stack:** reStructuredText, Sphinx 9.1, pydata-sphinx-theme 0.21, sphinx-design 0.7.0 (`tab-set`, `:sync-group:`), sphinx-iconify 0.3.0, matplotlib plot directive, pixi, pytest, pre-commit.

**Spec:** [`../specs/2026-09-05-getting-started-design.md`](../specs/2026-09-05-getting-started-design.md) — cited below as `start spec §N`. Read it alongside this plan; every task argues from a section of it.

## What This Plan Measured Before It Was Written

Everything below was established on 2026-09-05, before a line of the plan was written.
Two findings correct the specification, which is a living document (docs spec §3.4), and
Task 5 amends it.

**1. `sphinx-iconify` resolves its icons in the reader's browser, not at build time.**
This is `start spec §7`'s open item, and the answer is unambiguous. Built a probe project
in a throwaway venv: the extension emits `<iconify-icon icon="devicon:pypi">` elements —
no inline `<svg>` anywhere in the output — and adds one script tag,
`https://code.iconify.design/iconify-icon/3.0.1/iconify-icon.min.js`. Loaded that page in
Chromium and captured every request: **three external calls for two icons** — the script,
plus `https://api.iconify.design/devicon.json?icons=pypi` and
`https://api.iconify.design/vscode-icons.json?icons=file-type-conda`, one per icon
collection. The icons do render, at 16×16.

So adopting it puts a third-party script *and* per-collection data fetches on every reader
of the installation page, at read time. `iconify_script_url` is a config value (default the
CDN), so the *script* could be vendored into `_static`; the data fetches belong to the web
component and the extension exposes no control over them. The decision to adopt is
`start spec §2`'s decision 5 and stands; Task 5 writes this measurement into `start spec §7`
so the cost is recorded rather than discovered later.

**2. It is not on conda-forge.** `api.anaconda.org/package/conda-forge/sphinx-iconify`
returns 404; PyPI has 0.3.0, depending only on `sphinx`. So it belongs in
`[tool.pixi.feature.docs.pypi-dependencies]` beside `playwright`, **not** in the
`docs.dependencies` conda table where every other Sphinx extension of this project sits.

**3. `:sync-group:` works, and costs nothing.** `sphinx-design` reports 0.7.0 in the docs
environment against a `>=0.6.1` floor. A probe page with two `tab-set` blocks sharing
`:sync-group: install` built clean and emitted `design-tabs.js`.

**4. The specification's tranche order is impossible as written.** `start spec §6` says
the gates go first, "widened and renamed while the section does not yet exist". Measured:
widening `tests/test_docs_landing_pages.py::QUADRANTS` to include `"start"` before
`docs/src/start/` exists fails immediately — `AssertionError: start is missing` — because
that gate and `tests/test_glossary_links.py::test_every_quadrant_directory_exists` both
assert every directory they name is on disk. The other two, the snippets and figures
gates, `rglob` a missing directory and silently find nothing, which is worse.
**So the rename goes first and alone, and each widening lands with the pages it governs.**
Task 1 is the rename; Tasks 2 and 4 widen.

**5. The specification is wrong that `tests/test_glossary_links.py` needs no edit.**
`start spec §3.6`'s table says it "reads the gate's own tuple, so it follows without an
edit". True of *widening*, false of *renaming*: line 41 is
`QUADRANTS = gate.QUADRANTS if gate is not None else ()`, which reads the constant **by
name** and breaks the moment the name changes. It is a one-line edit, and Task 5 corrects
the table.

**6. One of the icon names does not exist, and nothing would have said so.**
Checked every `:iconify:` name in Task 3 against the Iconify API: `mdi:download-circle`,
`mdi:check-circle`, `mdi:rocket-launch`, `mdi:tools`, `vscode-icons:file-type-conda`,
`devicon:pypi`, `material-icon-theme:uv` and `twemoji:information` all resolve.
**`devicon:pixi` does not** — the API returns it under `not_found`. A missing icon is not
a build error and not a runtime error; the element simply renders blank, which is the
failure mode that reports nothing. pixi therefore takes `fa6-solid:puzzle-piece`, which is
what geovista's page uses for pixi and presumably for this same reason.

**7. The editable-install extra is `devs`, not `dev`.**
`optional-dependencies` is dynamic, and `[tool.setuptools.dynamic.optional-dependencies]`
declares exactly `devs`, `docs` and `test`. A page documenting `pip install --editable
".[dev]"` would hand the reader a command that fails, on the page whose whole job is
commands that work.

**8. The quick start's code, taken from the page that already runs it.**
`samples.sounding` takes a name — `samples.available()` returns `('norman-12z',
'norman-17z', 'camborne-igra-12z', 'camborne-wyoming-12z')` — so a bare `samples.sounding()`
would fail. The idiom is `tutorials/first-tephigram.rst`'s own, which is deliberate: the
quick start hands over to that page, so it should show the same call.

## Global Constraints

- Every source file carries the BSD copyright header (ruff `CPY001`); the exact notice is in `[tool.ruff.lint.flake8-copyright]` in `pyproject.toml`. This applies to the new test module.
- `line-length = 88`; ruff `select = ["ALL"]` with the ignore list in `pyproject.toml`. `.github/scripts/*.py` additionally ignores `FBT001`, `T201` and `INP001`.
- ruff isort: `force-sort-within-sections = true`, `required-imports = ["from __future__ import annotations"]`, `known-first-party = ["tephpy"]`.
- numpydoc convention; validation runs over `^src/` only, so a test module needs docstrings but not the full validated section set. `#:` comments on module constants, `Parameters`/`Returns` on each helper.
- `[tool.pytest.ini_options]` sets `filterwarnings = ["error"]` — a warning in a test is a failure.
- The docs build is `--fail-on-warning --keep-going` (`docs/Makefile:1`). Any Sphinx warning fails `pixi run docs`.
- A citation must never be wrapped across a line break: `start spec §3.3` on one line, or the `check-citations` hook resolves it to nothing.
- Cite `start spec §N` in body prose, never in a section heading.
- Every PR adds `changelog/<PR>.<type>.rst` ending with ``(:user:`claude`)``.
- **Everything lands together.** Task 2's widening fails until its pages exist, and Task 4's until the quick start does. The branch is not mergeable until Task 5.

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/src/start/index.rst` | **Create.** The section's landing page: `narrative spec §3.9`'s shape. |
| `docs/src/start/overview.rst` | **Create.** What tephpy is, what it delegates, what it declines. |
| `docs/src/start/installation.rst` | **Create.** Stable, latest, developer × conda, pip, pixi, uv. |
| `docs/src/start/quick-start.rst` | **Create.** Ten lines, one figure, a handover. |
| `docs/src/start/next-steps.rst` | **Create.** Where to go once it works. |
| `tests/test_docs_installation.py` | **Create.** The pre-release note matches the version. |
| `tests/test_docs_snippets.py` | **Modify.** Rename `QUADRANTS`; add `"start"`; register the quick start. |
| `.github/scripts/check_docs_figures.py` | **Modify.** Rename; add `"start"`; register the figure. |
| `.github/scripts/check_glossary_links.py` | **Modify.** Rename; add `"start"`. |
| `tests/test_docs_landing_pages.py` | **Modify.** Rename; add `"start"`. |
| `tests/test_glossary_links.py` | **Modify.** Follow the rename (finding 5). |
| `tests/test_docs_readingtime.py` | **Modify.** `start/index.rst` joins `EXEMPT`. |
| `docs/src/index.rst` | **Modify.** `start/index` leads the root toctree. |
| `docs/src/conf.py`, `pyproject.toml` | **Modify.** `sphinx_iconify`. |
| `docs/baseline/quick-start-sounding.png` | **Create.** Generated, not hand-written. |

---

## Task 1: Rename the Constants, Change Nothing Else

`start spec §3.6`. A pure rename: four gates plus the mirror of finding 5. The suite must
pass exactly as before, which is the evidence that the rename is behaviour-preserving.

**Files:**
- Modify: `tests/test_docs_snippets.py:37-38`, `.github/scripts/check_docs_figures.py:67-69`, `.github/scripts/check_glossary_links.py:58-62`, `tests/test_docs_landing_pages.py:17-20`, `tests/test_glossary_links.py:41`

**Interfaces:**
- Produces: `USER_SECTIONS` in each of the four gates, replacing `QUADRANTS`. Tasks 2 and 4 append `"start"` to it.

- [ ] **Step 1: Record the baseline**

Run: `pixi run tests 2>&1 | tail -3`
Write the passing count down. It must be identical after this task.

- [ ] **Step 2: Rename in `tests/test_docs_snippets.py`**

Replace lines 37-38:

```python
#: The Diátaxis quadrants written for users (docs spec §3.9).
QUADRANTS = ("howtos", "tutorials", "explanation")
```

with:

```python
#: The sections written for users, whose python this gate executes (docs spec §3.9).
#: Named for the audience rather than for Diátaxis because the getting-started
#: section is one of them and is not a quadrant (start spec §3.6).
USER_SECTIONS = ("howtos", "tutorials", "explanation")
```

Then update every use in the file — `for quadrant in QUADRANTS:` at the `user_pages`
sweep and any other reference. Find them with `grep -n QUADRANTS tests/test_docs_snippets.py`.

- [ ] **Step 3: Rename in `.github/scripts/check_docs_figures.py`**

Replace lines 67-69:

```python
#: The Diátaxis quadrants written for users, which are the pages that may publish
#: a figure (plots spec §3.2).
QUADRANTS = ("howtos", "tutorials", "explanation")
```

with:

```python
#: The sections written for users, which are the pages that may publish a figure
#: (plots spec §3.2). Named for the audience rather than for Diátaxis: the
#: getting-started section is one of them and is not a quadrant (start spec §3.6).
USER_SECTIONS = ("howtos", "tutorials", "explanation")
```

Update both loops at the former lines 282 and 351.

- [ ] **Step 4: Rename in `.github/scripts/check_glossary_links.py`**

Replace lines 58-62 with:

```python
#: The sections written for users. The reference quadrant is excluded because the
#: glossary lives there and an entry naming another term is the rule's own
#: exception; the developer section, because it is written for contributors who are
#: not the audience the glossary serves. Named for the audience rather than for
#: Diátaxis, since the getting-started section is neither a quadrant nor excluded
#: (start spec §3.6).
USER_SECTIONS = ("howtos", "tutorials", "explanation")
```

- [ ] **Step 5: Rename in `tests/test_docs_landing_pages.py`**

Replace lines 17-20 with:

```python
#: The sections whose landing page carries a table. The reference quadrant is out:
#: its entries are reached by name rather than chosen between, and narrative spec §7
#: records the question rather than answering it here. Named for the audience
#: rather than for Diátaxis, because the getting-started section takes the same
#: landing shape without being a quadrant (start spec §3.1).
USER_SECTIONS = ("tutorials", "howtos", "explanation")
```

Update all five uses, including the four `@pytest.mark.parametrize` decorators and
`test_every_quadrant_this_gate_governs_is_on_disk`. Rename that test to
`test_every_section_this_gate_governs_is_on_disk`, since its name asserts the same thing
its constant did.

- [ ] **Step 6: Follow the rename in `tests/test_glossary_links.py`** (finding 5)

Line 41 reads the constant by name and breaks otherwise:

```python
QUADRANTS = gate.QUADRANTS if gate is not None else ()
```

becomes:

```python
USER_SECTIONS = gate.USER_SECTIONS if gate is not None else ()
```

Update its `@pytest.mark.parametrize("quadrant", QUADRANTS)` uses, and rename
`test_every_quadrant_directory_exists` to `test_every_section_directory_exists`.

- [ ] **Step 7: Prove nothing changed**

Run: `pixi run tests 2>&1 | tail -3`
Expected: the **same** passing count as Step 1, with no failures and no skips gained.

Then run: `grep -rn "QUADRANTS" tests/ .github/scripts/ | grep -v tephpy_topics_data`
Expected: no output. `docs/src/_ext/tephpy_topics_data.py` keeps its `QUADRANTS`
deliberately — it *is* the Diátaxis quadrants, and the on-ramp is not corpus to browse by
topic (`start spec §3.6`).

- [ ] **Step 8: Commit**

```bash
git add tests/ .github/scripts/
git commit -m "Name the gates for the audience they serve, not for Diátaxis"
```

---

## Task 2: The Section, Its Landing Page, Overview and Next Steps

`start spec §3.1`, `§3.2`, `§3.5`, `§3.8`. The three pages with no code, so the section
exists before anything has to execute in it.

**Files:**
- Create: `docs/src/start/index.rst`, `docs/src/start/overview.rst`, `docs/src/start/next-steps.rst`
- Modify: `docs/src/index.rst`, `tests/test_docs_readingtime.py`, `tests/test_docs_landing_pages.py`, `.github/scripts/check_glossary_links.py`

- [ ] **Step 1: Write the landing page**

`docs/src/start/index.rst`:

```rst
Getting Started
===============

Everything you need before the rest of this documentation makes sense: what
``tephpy`` is, how to install it, and a diagram on your screen in a few lines.

.. list-table::
    :widths: auto

    * - :doc:`overview`
      - What ``tephpy`` draws, what it delegates, and what it declines.
    * - :doc:`installation`
      - conda, pip, pixi or uv — released, development, or a working clone.
    * - :doc:`quick-start`
      - A real ascent on a real diagram, in ten lines.
    * - :doc:`next-steps`
      - Where to go once it works.

.. toctree::
    :hidden:

    overview
    installation
    quick-start
    next-steps
```

No `.. readingtime::` — it is a landing page, and Step 4 exempts it.

- [ ] **Step 2: Write the overview**

`docs/src/start/overview.rst`. Summarise and link the non-goals; never restate them
(`start spec §3.2`):

```rst
.. _start-overview:

Overview
========

.. readingtime::

``tephpy`` plots and analyses :term:`tephigrams <tephigram>` — the chart a
forecaster reads a :term:`radiosonde` ascent from. It draws the diagram, puts
your data on it, and reads the standard quantities off it.

It draws, and delegates the physics. The five isopleth families, the rotated
coordinate system and the edge labelling are ``tephpy``'s; :term:`parcel` ascent,
:term:`CAPE`, :term:`CIN` and the rest come from
`MetPy <https://unidata.github.io/MetPy/latest/>`__, so there is one source of
thermodynamic truth and it is not this package.

It also declines things, deliberately. There is no skew-T — MetPy owns that
space — no :term:`hodograph`, and no TEMP or BUFR decoding. Each has somewhere
to go instead, and the
`non-goals <https://github.com/bjlittle/tephpy#non-goals>`__ say where.

Where it comes from: ``tephpy`` reimplements `tephi
<https://github.com/SciTools/tephi>`__ on a Matplotlib projection, with the
thermodynamics delegated rather than reimplemented.
```

All six `:term:` targets exist, checked against `docs/src/reference/glossary.rst` on
2026-09-05: `tephigram`, `radiosonde`, `parcel`, `CAPE`, `CIN` and `hodograph`, plus
`sounding` which Task 4 uses. A dangling `:term:` fails the fail-on-warning build, so if
you reach for a seventh, seed the entry in the same change per docs-style's glossary rule.

- [ ] **Step 3: Write next steps**

`docs/src/start/next-steps.rst`:

```rst
.. _start-next-steps:

Next Steps
==========

.. readingtime::

The documentation is in four parts, and which one you want depends on what you
are trying to do rather than on how much you already know.

.. list-table::
    :widths: auto

    * - :doc:`../tutorials/index`
      - Lessons to work through. Start here if the quick start left you wanting
        to know what you had just drawn.
    * - :doc:`../howtos/index`
      - Recipes for when you already know what you want.
    * - :doc:`../explanation/index`
      - Why the diagram is the shape it is.
    * - :doc:`../reference/index`
      - The API, the command line, every configuration option, and the glossary.
    * - :doc:`../gallery/index`
      - Finished examples to work backwards from.

If you would rather browse by subject than by intent, :doc:`../topics` lists
every page against the topics it covers.
```

This page carries a `list-table` but is **not** a landing page, so the gate of
`tests/test_docs_landing_pages.py` must not read it. It does not: that gate reads only
`<section>/index.rst`. Confirm with Step 6.

- [ ] **Step 4: Register the section**

In `docs/src/index.rst`, put `start/index` **first** in the hidden toctree, before
`tutorials/index` (`start spec §3.8`).

In `tests/test_docs_readingtime.py`, add to `EXEMPT`, keeping the existing style of a
reason per entry:

```python
    "start/index.rst",  # section landing page: an introduction and a table
```

- [ ] **Step 5: Widen the two gates that can now see the section**

`tests/test_docs_landing_pages.py`:

```python
USER_SECTIONS = ("start", "tutorials", "howtos", "explanation")
```

`.github/scripts/check_glossary_links.py`:

```python
USER_SECTIONS = ("start", "howtos", "tutorials", "explanation")
```

`"start"` leads both, matching the order a reader meets the sections in.

- [ ] **Step 6: Run the gates**

Run: `pixi run -e devs pytest tests/test_docs_landing_pages.py tests/test_docs_readingtime.py tests/test_glossary_links.py -q`
Expected: PASS. The landing gate now covers four sections; the reading-time gate is
satisfied because two new pages carry banners and the third is exempt.

Run: `pixi run docs-html`
Expected: `build succeeded`, no warnings. A dangling `:term:` or a page missing from a
toctree fails here.

- [ ] **Step 7: Mutate, to prove the landing gate reaches the new section**

Delete the `* - :doc:`next-steps`` row from `start/index.rst`, leaving the toctree.
Run: `pixi run -e devs pytest tests/test_docs_landing_pages.py -q -k start`
Expected: FAIL, naming `next-steps`. Restore, and confirm PASS.

- [ ] **Step 8: Look at it**

Run `pixi run docs-html`, then render and open both viewports:

```bash
LD_LIBRARY_PATH=/home/bill/projects/geovista-jav-2026/.pixi/envs/geojav/lib \
  pixi run -e docs python -c "
import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w, name in ((1280, 'desktop'), (360, 'phone')):
            pg = await b.new_page(viewport={'width': w, 'height': 1000})
            await pg.goto('file:///home/bill/projects/tephpy/docs/_build/html/start/index.html')
            await pg.wait_for_timeout(700)
            await pg.screenshot(path=f'/tmp/start-{name}.png', full_page=True)
        await b.close()
asyncio.run(main())
"
```

Expected: the header's first entry is *Getting Started*, and *Reference* and
*Examples Gallery* are **still visible** rather than pushed into *More* — which is the
whole reason `start spec §3.8` chose a landing page over four top-level pages. Count the
visible header links; there should be six or fewer before the dropdown.

- [ ] **Step 9: Commit**

```bash
git add docs/src/start/ docs/src/index.rst tests/ .github/scripts/
git commit -m "Give a newcomer a way in: the getting started section"
```

---

## Task 3: Installation, and the Note That Retires Itself

`start spec §3.3`, `§3.7`. The page you named as the bar, and the assertion that keeps its
pre-release note honest.

**Files:**
- Create: `docs/src/start/installation.rst`, `tests/test_docs_installation.py`
- Modify: `pyproject.toml`, `docs/src/conf.py`

**Interfaces:**
- Produces: `PRERELEASE` — the exact sentence the gate looks for, defined in the test module and copied verbatim into the page.

- [ ] **Step 1: Add the dependency** (finding 2 — PyPI, not conda-forge)

In `pyproject.toml`, under `[tool.pixi.feature.docs.pypi-dependencies]`, beside
`playwright`:

```toml
sphinx-iconify = ">=0.3"
```

Then `pixi install -e docs` and confirm the lock updated.

In `docs/src/conf.py`, add `"sphinx_iconify"` to `extensions`, keeping the list's existing
ordering convention.

- [ ] **Step 2: Write the failing test first**

`tests/test_docs_installation.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The installation page's pre-release note tracks the version (start spec §3.7)."""

from __future__ import annotations

from pathlib import Path

import tephpy

REPO = Path(__file__).parents[1]
PAGE = REPO / "docs" / "src" / "start" / "installation.rst"

#: The sentence the note must carry, verbatim. Matched as a substring rather than by
#: shape, so rewording the note is a deliberate act that updates this constant too.
PRERELEASE = "tephpy has not had its first release yet"


def test_the_prerelease_note_is_present_exactly_while_the_version_is_a_dev_version():
    """The note is a claim about the world, so it is not left to memory.

    setuptools_scm reports a `.dev` version until the first tag. On the release
    commit this test fails, and that is the intended behaviour rather than a
    side effect: the tag is cut, this fails, the note comes out, and the page is
    true again. Nothing here reaches the network -- spec §8.5 forbids it, and the
    installed version answers the question offline.
    """
    released = ".dev" not in tephpy.__version__
    carries = PRERELEASE in PAGE.read_text(encoding="utf-8")
    assert carries is not released, (
        f"version {tephpy.__version__} is "
        f"{'released' if released else 'a development version'}, so the page "
        f"{'must not' if released else 'must'} carry the pre-release note"
    )
```

- [ ] **Step 3: Run it and watch it fail**

Run: `pixi run -e devs pytest tests/test_docs_installation.py -q`
Expected: FAIL with `FileNotFoundError` — the page does not exist yet.

- [ ] **Step 4: Write the page**

`docs/src/start/installation.rst`. Three sections, four tools, one sync group. The note's
first clause must match `PRERELEASE` exactly.

```rst
.. _start-installation:

:iconify:`mdi:download-circle` Installation
===========================================

.. readingtime::

.. note::
    tephpy has not had its first release yet, so the commands below do not work
    today. They are what installing will look like from ``v0.1.0`` onward. To use
    it now, take the **Latest** or **Developer** route.

:iconify:`mdi:check-circle` Stable
----------------------------------

The latest **stable release**, from `conda-forge
<https://conda-forge.org/>`__ or `PyPI <https://pypi.org/project/tephpy/>`__:

.. tab-set::
    :sync-group: install

    .. tab-item:: :iconify:`vscode-icons:file-type-conda` conda
        :sync: conda

        .. code:: console

            $ conda create --name myenv --channel conda-forge tephpy
            $ conda activate myenv

        :iconify:`twemoji:information` Consult the ``conda``
        `installation <https://docs.conda.io/projects/conda/en/stable/>`__
        instructions.

    .. tab-item:: :iconify:`devicon:pypi` pip
        :sync: pip

        .. code:: console

            $ pip install tephpy

        :iconify:`twemoji:information` Consult the ``pip``
        `installation <https://pip.pypa.io/en/stable/installation/>`__
        instructions.

    .. tab-item:: :iconify:`fa6-solid:puzzle-piece` pixi
        :sync: pixi
        :selected:

        .. code:: console

            $ pixi init myenv
            $ cd myenv
            $ pixi add tephpy

        :iconify:`twemoji:information` Consult the ``pixi``
        `installation <https://pixi.sh/latest/installation/>`__
        instructions.

    .. tab-item:: :iconify:`material-icon-theme:uv` uv
        :sync: uv

        .. code:: console

            $ uv pip install tephpy

        :iconify:`twemoji:information` Consult the ``uv``
        `installation <https://docs.astral.sh/uv/getting-started/installation/>`__
        instructions.

:iconify:`mdi:rocket-launch` Latest
-----------------------------------

The **development version**, from the ``main`` branch:

.. tab-set::
    :sync-group: install

    .. tab-item:: :iconify:`vscode-icons:file-type-conda` conda
        :sync: conda

        .. code:: console

            $ conda create --name myenv --channel conda-forge pip
            $ conda activate myenv
            $ pip install git+https://github.com/bjlittle/tephpy.git@main

    .. tab-item:: :iconify:`devicon:pypi` pip
        :sync: pip

        .. code:: console

            $ pip install git+https://github.com/bjlittle/tephpy.git@main

    .. tab-item:: :iconify:`fa6-solid:puzzle-piece` pixi
        :sync: pixi
        :selected:

        .. code:: console

            $ pixi init myenv
            $ cd myenv
            $ pixi add python
            $ pixi add --pypi "tephpy @ git+https://github.com/bjlittle/tephpy.git@main"

    .. tab-item:: :iconify:`material-icon-theme:uv` uv
        :sync: uv

        .. code:: console

            $ uv pip install "tephpy @ git+https://github.com/bjlittle/tephpy.git@main"

:iconify:`mdi:tools` Developer
------------------------------

To work on ``tephpy`` itself, clone the repository:

.. code:: console

    $ git clone git@github.com:bjlittle/tephpy.git
    $ cd tephpy

``tephpy`` develops with `pixi <https://pixi.sh>`__, which reads the environments
from ``pyproject.toml`` and needs no separate setup:

.. code:: console

    $ pixi run tests
    $ pixi run lint
    $ pixi run docs

Those three are the checks a pull request must pass, and each creates the
environment it needs on first use. ``pixi run docs`` builds the documentation and
runs every gate over the result.

If you would rather not use ``pixi``:

.. tab-set::
    :sync-group: install

    .. tab-item:: :iconify:`vscode-icons:file-type-conda` conda
        :sync: conda

        .. code:: console

            $ conda create --name tephpy-dev --channel conda-forge python pip
            $ conda activate tephpy-dev
            $ pip install --editable ".[devs]"

    .. tab-item:: :iconify:`devicon:pypi` pip
        :sync: pip

        .. code:: console

            $ pip install --editable ".[devs]"

    .. tab-item:: :iconify:`fa6-solid:puzzle-piece` pixi
        :sync: pixi
        :selected:

        .. code:: console

            $ pixi shell --environment devs

    .. tab-item:: :iconify:`material-icon-theme:uv` uv
        :sync: uv

        .. code:: console

            $ uv pip install --editable ".[devs]"
```

The extra is `devs`, checked rather than guessed: `optional-dependencies` is dynamic, and
`[tool.setuptools.dynamic.optional-dependencies]` in `pyproject.toml` declares exactly
three — `devs`, `docs` and `test`, each reading a file under `requirements/`. There is no
`dev`, so write `devs`. `pixi shell --environment devs` names the same environment the
`pixi run -e devs` commands in this plan use.

Every `:iconify:` name above was checked against the Iconify API before being written
here, because a name that does not exist renders **blank with no build error** — the
failure mode that reports nothing. `mdi:download-circle`, `mdi:check-circle`,
`mdi:rocket-launch`, `mdi:tools`, `vscode-icons:file-type-conda`, `devicon:pypi`,
`material-icon-theme:uv`, `twemoji:information` and `fa6-solid:puzzle-piece` all resolve.
`devicon:pixi` does **not** — it came back in `not_found`, which is why pixi takes a
puzzle piece here, as it does on geovista's page for the same reason. If you add an icon,
check it the same way:
`curl -s -A "Mozilla/5.0" "https://api.iconify.design/<prefix>.json?icons=<name>"` and read
`not_found`.

- [ ] **Step 5: Run the test**

Run: `pixi run -e devs pytest tests/test_docs_installation.py -q`
Expected: PASS — the version is `0.1.0.dev…` and the note is present.

- [ ] **Step 6: Mutate both directions**

Delete the note from the page; run the test.
Expected: FAIL, saying the version is a development version so the page must carry it.
Restore.

Then temporarily edit the test's `released` line to `released = True` and run it.
Expected: FAIL the other way, proving the assertion is not one-sided. Restore.

- [ ] **Step 7: Build, and check the icons resolved**

Run: `pixi run docs-html`
Expected: `build succeeded`, no warnings.

Then confirm what finding 1 predicts, in this project's own build:

```bash
grep -c "iconify-icon" docs/_build/html/start/installation.html
grep -o "https://code.iconify.design[^\"]*" docs/_build/html/start/installation.html | head -1
```

Expected: a non-zero count of `<iconify-icon>` elements and the CDN script URL. If instead
the icons are inlined as `<svg>`, finding 1 is wrong for this version and Task 5's
amendment to `start spec §7` must say so — check before writing it.

- [ ] **Step 8: Render it, and confirm the tabs sync**

Render `start/installation.html` at 1280px, click the *pip* tab in the first tab-set, and
screenshot again. Expected: the second and third tab-sets have switched to pip too, which
is `:sync-group:` working. If they have not, the sync group name differs between blocks —
all four must read `:sync-group: install`.

Note the icons need network to render; if the render is offline they will be blank, which
is finding 1 made visible rather than a bug in the page.

- [ ] **Step 9: Commit**

```bash
git add docs/src/start/installation.rst tests/test_docs_installation.py pyproject.toml pixi.lock docs/src/conf.py
git commit -m "Say how to install tephpy, and gate the note that says you cannot yet"
```

---

## Task 4: The Quick Start, Executed and Figure-Checked

`start spec §3.4`, `§3.6`. The page that costs the remaining two gate widenings.

**Files:**
- Create: `docs/src/start/quick-start.rst`, `docs/baseline/quick-start-sounding.png`
- Modify: `tests/test_docs_snippets.py`, `.github/scripts/check_docs_figures.py`

- [ ] **Step 1: Write the page** (finding 8 — the real API)

`docs/src/start/quick-start.rst`:

```rst
.. _start-quick-start:

Quick Start
===========

.. readingtime::

With ``tephpy`` installed, a real :term:`radiosonde` ascent on a real
:term:`tephigram` is a few lines. The :term:`sounding` ships with the package, so
there is nothing to download.

.. plot::
    :context: reset
    :filename-prefix: quick-start-sounding

    import matplotlib.pyplot as plt

    from tephpy import samples

    snd = samples.sounding("norman-12z")

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(snd)
    ax.legend()

That is Norman, Oklahoma on the morning of 2013-05-20. The two traces are
temperature and dewpoint; everything behind them is the diagram's own grid.

You now have the thing this documentation is about. What you do not yet have is
a way to read it — which is what :ref:`tutorial-first-tephigram` is for. It draws
this same ascent and names every line on it.
```

- [ ] **Step 2: Widen the two remaining gates**

`tests/test_docs_snippets.py`:

```python
USER_SECTIONS = ("start", "howtos", "tutorials", "explanation")
```

and add to `DOCUMENTED` and `PUBLISHES_FIGURES`, both of which are sorted by path:

```python
    "start/quick-start.rst",
```

`.github/scripts/check_docs_figures.py`:

```python
USER_SECTIONS = ("start", "howtos", "tutorials", "explanation")
```

and add `"start/quick-start.rst"` to `PUBLISHES`.

- [ ] **Step 3: Run the snippet gate**

Run: `pixi run -e devs pytest tests/test_docs_snippets.py -q`
Expected: PASS. The page's block becomes one script and runs. If it fails on
`plot_sounding`, check the call against `docs/src/tutorials/first-tephigram.rst`, which is
where finding 6 took it from.

- [ ] **Step 4: Generate the baseline**

Run: `pixi run docs-html` then `pixi run docs-figures`
This blesses the published figure baselines from the build. Confirm exactly one new file:

```bash
git status --short docs/baseline/
```

Expected: one addition, `quick-start-sounding.png`. If more appear, another page's figure
has drifted and that is a separate matter — stop and report it rather than committing it
inside this change.

- [ ] **Step 5: Run the figures gate**

Run: `pixi run docs-check-figures`
Expected: `published figures ok: 32 compared within RMS 2, across 12 pages` — one more
figure and one more page than before.

- [ ] **Step 6: Mutate, to prove the widening took**

Remove `"start"` from `check_docs_figures.py::USER_SECTIONS`, leaving
`"start/quick-start.rst"` in `PUBLISHES`, and run `pixi run docs-check-figures`.
Expected: FAIL — a page listed as publishing that the sweep cannot see. Restore.

- [ ] **Step 7: Look at the figure**

Open `docs/_build/html/start/quick-start.html` at 1280px and confirm the diagram renders
with two traces and a legend, and that the page reads as a shop window rather than a
lesson — one block, one figure, one handover.

- [ ] **Step 8: Commit**

```bash
git add docs/src/start/quick-start.rst docs/baseline/quick-start-sounding.png tests/ .github/scripts/
git commit -m "Draw a tephigram in ten lines, and hold that code to the same gates"
```

---

## Task 5: The Amendments, the Measured Answer, and the Fragment

`start spec §4`, `§7`. What the earlier tasks proved, written back where it belongs.

**Files:**
- Modify: `docs/src/developer/specs/2026-09-05-getting-started-design.md`, `docs/src/developer/specs/2026-08-27-narrative-quadrants-design.md`, `docs/src/developer/docs-style.rst`
- Create: `changelog/<PR>.documentation.rst`

- [ ] **Step 1: Answer `start spec §7`'s open item with what Task 3 Step 7 measured**

Replace the first open item with the finding, keeping the status vocabulary of
docs spec §3.5 and citing what was run:

```markdown
- **Closed 2026-09-05** — `sphinx-iconify` does not embed its icons. It emits
  `<iconify-icon>` elements and adds
  `https://code.iconify.design/iconify-icon/3.0.1/iconify-icon.min.js`; loaded in
  Chromium, a page with two icons made three external requests — that script, and one
  `api.iconify.design` call per icon collection. So the installation page costs its
  reader a third-party script and per-collection data fetches, which is a departure
  from the no-network posture tooltip spec §3.3 recorded, made knowingly for parity
  with the page {issue}`66` names as the bar. `iconify_script_url` could vendor the
  script into `_static`; the data fetches belong to the web component and the
  extension exposes no control over them. Revisit if the cost proves unwelcome.
```

- [ ] **Step 2: Correct `start spec §3.6`'s claim about `test_glossary_links.py`** (finding 5)

That table's last row says it follows "without an edit". True of widening, false of the
rename. Change the row's reason to:

```markdown
| `tests/test_glossary_links.py::USER_SECTIONS` | **no** | it reads the gate's own tuple, so it follows the *widening* without an edit — though the rename touched it, since it names the constant |
```

- [ ] **Step 3: Correct `start spec §6`'s tranche order** (finding 4)

Replace the tranche paragraph with what the work actually required:

```markdown
**Tranches.** The rename first and alone, so it is provably behaviour-preserving: the
suite passes with an identical count. Then each widening lands with the pages it
governs, because two of the four gates assert that every directory they name is on
disk and fail with `start is missing` if widened before the section exists.
```

- [ ] **Step 4: Amend `narrative spec §3.9` and docs-style** (`start spec §4`)

In `narrative spec §3.9`, after the sentence beginning "**The shape.** A landing page in
the tutorials, how-to and explanation quadrants is", add:

```markdown
*Amended 2026-09-05 (`start spec §3.1`).* The shape is not quadrant-only. The
getting-started section takes it too, and `tests/test_docs_landing_pages.py` governs
four sections rather than three — which is why its constant names the audience rather
than Diátaxis.
```

In `docs/src/developer/docs-style.rst`, in the *Landing Pages* section, change the
opening "A quadrant landing page" to "A section landing page — the four Diátaxis
quadrants, and :doc:`getting started <../start/index>`" and check the sentence still
reads. Build after editing; a `:doc:` from the developer guide into `start/` must resolve.

- [ ] **Step 5: Write the changelog fragment**

`changelog/<PR>.documentation.rst`, with `<PR>` the pull request's number. Keep
``start spec §…`` on one line:

```rst
A getting started section: an overview, installation instructions for conda, pip,
pixi and uv, a quick start that draws a real ascent in ten lines, and a page of
next steps (``start spec §…``). Until now nothing in the documentation or the
README said how to install ``tephpy`` at all, while every page assumed the reader
already had it. The quick start's code is executed by the test suite and its
figure compared against a baseline, like every other user page, which is what the
four renamed section constants now reach. (:user:`claude`)
```

- [ ] **Step 6: Run everything**

```bash
pixi run lint
pixi run docs
pixi run tests
```

Run `pixi run tests` **after** committing, not before — the hooks rewrite files, so a run
beforehand measures a tree that no longer exists.

- [ ] **Step 7: Commit and open the pull request**

```bash
git add docs/ changelog/
git commit -m "Record what the getting started work measured"
```

The pull request body states which member of each set was counted, per *Reviewing
Claims*: the five pages of the section, all five; the four renamed constants and the two
that were not, each named with its reason; the mutations of Task 2 Step 7, Task 3 Step 6
and Task 4 Step 6, with what each failed with.

---

## Self-Review Notes

**Spec coverage.** `start spec §3.1` → Task 2 Steps 1 and 4. `§3.2` → Task 2 Step 2.
`§3.3` → Task 3 Step 4. `§3.4` → Task 4 Step 1. `§3.5` → Task 2 Step 3. `§3.6` → Task 1
in full, with the widenings in Tasks 2 and 4. `§3.7` → Task 3 Steps 2-6. `§3.8` → Task 2
Steps 4 and 8. `§4`'s companion list → Tasks 2, 3 and 5. `§5`'s testing table → the gate
runs in each task. `§7` → Task 5 Steps 1-3.

**Two corrections this plan makes to the specification**, both from measurement rather
than reading: the tranche order of `§6` is impossible as written (finding 4), and `§3.6`'s
claim that `tests/test_glossary_links.py` needs no edit is true only of widening
(finding 5). Task 5 writes both back.

**Type consistency.** `USER_SECTIONS` is the name in all four gates and in the mirror,
introduced in Task 1 and appended to in Tasks 2 and 4 — never `USER_PAGES`, which would
collide with `test_docs_snippets.py`'s existing `user_pages()` function. `PRERELEASE` is
defined once, in `tests/test_docs_installation.py`, and the page copies it verbatim.

**Two things a reviewer should check rather than assume.** Whether `.[dev]` is a real
extra (Task 3 Step 4 says how to find out, and what to write if it is not), and whether
`pixi run docs-figures` blesses exactly one baseline (Task 4 Step 4 says to stop if it
does not).

**What no task does.** It does not touch `README.md` — `start spec §7` holds that open —
and it does not change the non-goals, which are scope spec §3.1's.
