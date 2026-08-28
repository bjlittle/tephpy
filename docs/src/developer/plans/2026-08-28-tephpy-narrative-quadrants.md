# Narrative Quadrants Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill the tutorial and explanation quadrants, add the reader how-to, and ship the sample data that lets both ingest routes run — delivering spec §10's Plan 7c row.

**Architecture:** Five reStructuredText pages in three quadrants, written in two tranches of prose plus one of package change. Each tutorial pairs with the one explanation page answering the question it raises. Every python block executes under the snippet gate of docs spec §3.9; every figure is pinned against `docs/baseline/`. No new gate and no new dependency — the machinery was built by Plans 7a, 7b and the four documentation plans before them.

**Tech Stack:** Sphinx + `pydata-sphinx-theme`, `matplotlib.sphinxext.plot_directive`, `sphinxcontrib-bibtex`, pytest, pixi.

**Spec:** [`docs/src/developer/specs/2026-08-27-narrative-quadrants-design.md`](../specs/2026-08-27-narrative-quadrants-design.md) — read it first; every task below argues from a section of it.

## Global Constraints

- **Every page is reStructuredText.** `test_no_user_page_is_written_in_a_format_this_gate_cannot_read` fails on any `.md` or `.ipynb` under `howtos/`, `tutorials/` or `explanation/` (narrative spec §2, {pull}`199`).
- **A page publishes figures or it does not — never both.** On a figure page every python block is a `.. plot::`; a plain `code-block:: python` there is the defect the rule exists to stop (plots spec §3.2).
- **First plot on a page carries `:context: reset`; every later one carries `:context:` or `:context: close-figs`.** A block with no `:context:` runs in a namespace where the page's imports never happened.
- **Every published figure carries `:filename-prefix:`, unique across the whole documentation**, and a baseline in `docs/baseline/`.
- **A page carrying python registers in four places** — its quadrant toctree, `tests/test_docs_snippets.py::DOCUMENTED`, and if it publishes figures `tests/test_docs_snippets.py::PUBLISHES_FIGURES` and `.github/scripts/check_docs_figures.py::PUBLISHES` ({issue}`193` records the cost of missing one).
- **The build is fail-on-warning.** A `:term:` whose glossary entry does not exist breaks it: seed the entry in the same commit as the prose that reaches for it.
- **Cross-references are fully qualified.** `nitpicky` is on: write ``:func:`igra.read(...) <tephpy.io.igra.read>` ``, never a bare ``:func:`igra.read` ``.
- **Titles use CMOS headline style** and are read against docs-style's *Reviewing Claims* before the pull request opens.
- **Every pull request adds `changelog/<PR>.<type>.rst`** ending with ``(:user:`<github-username>`)``.
- **Run `pixi run tests`, never bare `pytest`.** The task is `pytest --cov --cov-report=xml --mpl`; a bare invocation silently skips every image comparison.

---

# Tranche A — the explanation quadrant

Two pages, no session continuity to maintain and the fewest gate surfaces. They land first because the tutorials link into them.

### Task 1: *Why the Axes Are Rotated*

**Files:**
- Create: `docs/src/explanation/rotated-axes.rst`
- Modify: `docs/src/explanation/index.rst`
- Modify: `docs/src/refs.bib`
- Modify: `tests/test_docs_snippets.py` (`DOCUMENTED`, `PUBLISHES_FIGURES`)
- Modify: `.github/scripts/check_docs_figures.py` (`PUBLISHES`)
- Create: `docs/baseline/rotated-axes-grid.png` (generated, Step 7)

**Interfaces:**
- Consumes: nothing.
- Produces: the built page `explanation/rotated-axes.html`, and the label `_explanation-rotated-axes`, which Task 4 links to with ``:ref:`explanation-rotated-axes` ``.

- [ ] **Step 1: Replace the placeholder index**

`docs/src/explanation/index.rst` currently promises content and has no toctree. Replace its body:

```rst
Explanation
===========

Background on the :term:`tephigram` — why its axes are what they are, and what
a parcel ascent is doing when ``tephpy`` draws one.

.. toctree::
    :maxdepth: 1

    rotated-axes
```

- [ ] **Step 2: Write the page**

Create `docs/src/explanation/rotated-axes.rst`. Cover, in this order: temperature against entropy as the coordinate pair; why that makes isotherms and dry adiabats exactly perpendicular; the 45° rotation and what it buys (pressure running roughly up the page); and why pressure is therefore a derived curve rather than an axis. Cite Factsheet 13 with ``:cite:`metoffice_factsheet13` `` for the printed chart's conventions. Open with the label and the title:

```rst
.. _explanation-rotated-axes:

Why the Axes Are Rotated
========================
```

One figure only — the grid itself, which is the argument. It is the page's first and only plot:

```rst
.. plot::
    :context: reset
    :filename-prefix: rotated-axes-grid

    import matplotlib.pyplot as plt

    import tephpy  # registers the "tephigram" projection

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
```

- [ ] **Step 3: Seed any glossary term the prose reaches for**

The prose will want vocabulary the glossary does not carry — *entropy* at minimum. For each, add an entry to `docs/src/reference/glossary.rst` in the same commit, following the house rule: one plain sentence of the concept, then how it appears in ``tephpy``. The build fails on a dangling ``:term:``, so this is not optional.

- [ ] **Step 4: Register the page**

In `tests/test_docs_snippets.py` add `"explanation/rotated-axes.rst"` to both `DOCUMENTED` and `PUBLISHES_FIGURES`. In `.github/scripts/check_docs_figures.py` add `"explanation/rotated-axes.rst"` to `PUBLISHES`.

- [ ] **Step 5: Run the snippet gate and watch it fail on the missing baseline**

Run: `pixi run tests`
Expected: the page executes; `pixi run docs` will be what reports the absent baseline in Step 7.

- [ ] **Step 6: Build the docs**

Run: `pixi run docs`
Expected: the build succeeds and the figure gate reports the new prefix as `MISSING` — it has no baseline yet.

- [ ] **Step 7: Generate and read the baseline**

Run: `pixi run docs-figures`
Expected: `1 added, 0 updated, 0 removed`. **Open `docs/baseline/rotated-axes-grid.png` and look at it.** The command approves whatever was rendered; a wrong figure is approved exactly as willingly as a right one.

- [ ] **Step 8: Verify everything green**

Run: `pixi run tests && pixi run lint && pixi run docs`
Expected: all three pass, and the figure gate reports one more page than before.

- [ ] **Step 9: Commit**

```bash
git add docs/src/explanation/rotated-axes.rst docs/src/explanation/index.rst \
        docs/src/reference/glossary.rst docs/src/refs.bib docs/baseline/rotated-axes-grid.png \
        tests/test_docs_snippets.py .github/scripts/check_docs_figures.py
git commit -m "Explain why the tephigram's axes are rotated"
```

### Task 2: *Parcel Ascent and Normand's Point*

**Files:**
- Create: `docs/src/explanation/parcel-ascent.rst`
- Modify: `docs/src/explanation/index.rst`
- Modify: `tests/test_docs_snippets.py`, `.github/scripts/check_docs_figures.py`
- Create: `docs/baseline/parcel-ascent-construction.png` (generated)

**Interfaces:**
- Consumes: Task 1's glossary additions.
- Produces: the label `_explanation-parcel-ascent`, which Task 5 links to.

- [ ] **Step 1: Write the page**

Create `docs/src/explanation/parcel-ascent.rst`, opening:

```rst
.. _explanation-parcel-ascent:

Parcel Ascent and Normand's Point
=================================
```

Cover: a parcel lifted dry-adiabatically from the surface; the mixing-ratio line rising from its dewpoint; their intersection at Normand's point and why the LCL falls out of the construction rather than being computed separately; saturated ascent above it; and why the areas between parcel and environment are energies — which is what makes CAPE an area here and a number in a table elsewhere.

State where the arithmetic happens: spec §3.3 delegates the thermodynamics to MetPy, so ``tephpy`` draws the construction and MetPy computes the values. Name the −25 mb operational cloud-base correction of spec §1 as a convention with a reason rather than a magic number.

- [ ] **Step 2: Add the one figure that is the argument**

```rst
.. plot::
    :context: reset
    :filename-prefix: parcel-ascent-construction

    import matplotlib.pyplot as plt

    import tephpy
    from tephpy import samples

    snd = samples.sounding("norman-12z")
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(snd)
    parcel = tephpy.calc.parcel_path(snd)
    ax.plot_profile(parcel, color="k", linestyle="--")
    ax.legend()
```

- [ ] **Step 3: Add to the index toctree**

Add `parcel-ascent` under `rotated-axes` in `docs/src/explanation/index.rst`.

- [ ] **Step 4: Register the page**

Add `"explanation/parcel-ascent.rst"` to `DOCUMENTED`, `PUBLISHES_FIGURES` and `PUBLISHES`, as in Task 1 Step 4.

- [ ] **Step 5: Seed any new glossary term**

The prose will reach for terms around the construction. Seed each in `docs/src/reference/glossary.rst` in this commit.

- [ ] **Step 6: Build, generate the baseline, read it**

```bash
pixi run docs
pixi run docs-figures
```
Expected: `1 added`. Open `docs/baseline/parcel-ascent-construction.png` and confirm the parcel path is drawn dashed in black over the sounding.

- [ ] **Step 7: Verify**

Run: `pixi run tests && pixi run lint && pixi run docs`

- [ ] **Step 8: Commit**

```bash
git add docs/src/explanation/parcel-ascent.rst docs/src/explanation/index.rst \
        docs/src/reference/glossary.rst docs/baseline/parcel-ascent-construction.png \
        tests/test_docs_snippets.py .github/scripts/check_docs_figures.py
git commit -m "Explain parcel ascent and Normand's point"
```

### Task 3: Close the tranche

- [ ] **Step 1: Add the changelog fragment**

Create `changelog/<PR>.documentation.rst` naming the two pages and what they answer, ending ``(:user:`<your-github-username>`)``.

- [ ] **Step 2: Review the prose against *Reviewing Claims***

Read `docs/src/developer/docs-style.rst`'s *Reviewing Claims* section and apply its three questions to both pages: which member of any set did you check, does the title survive that, and what did you actually run for any claim about an external source. Answer them in the pull request body.

- [ ] **Step 3: Open the pull request**

Base `main`. Cite `narrative spec §3.4` and `narrative spec §3.5` as the sections implemented.

---

# Tranche B — the tutorials

Two pages, written on top of explanation pages they can link to.

### Task 4: *Your First Tephigram*

**Files:**
- Create: `docs/src/tutorials/first-tephigram.rst`
- Modify: `docs/src/tutorials/index.rst`
- Modify: `tests/test_docs_snippets.py`, `.github/scripts/check_docs_figures.py`
- Create: `docs/baseline/first-tephigram-empty.png`, `docs/baseline/first-tephigram-sounding.png` (generated)

**Interfaces:**
- Consumes: Task 1's `_explanation-rotated-axes` label.
- Produces: the label `_tutorial-first-tephigram`, which Task 5 links back to.

- [ ] **Step 1: Write the opening and the empty diagram**

```rst
.. _tutorial-first-tephigram:

Your First Tephigram
====================
```

The reader has installed the package and knows no meteorology. Open with what they will have at the end, then the empty diagram:

```rst
.. plot::
    :context: reset
    :filename-prefix: first-tephigram-empty

    import matplotlib.pyplot as plt

    import tephpy  # registers the "tephigram" projection

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
```

Name the five isopleth families the grid draws — isotherms, isobars, dry adiabats, moist adiabats, humidity mixing-ratio lines — and link the *why* to ``:ref:`explanation-rotated-axes` `` rather than answering it here.

- [ ] **Step 2: Add the sounding**

```rst
.. plot::
    :context: close-figs
    :filename-prefix: first-tephigram-sounding

    from tephpy import samples

    snd = samples.sounding("norman-12z")
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(snd)
    ax.legend()
```

Explain reading the two traces apart: temperature red, dewpoint green, and the gap between them as dryness.

- [ ] **Step 3: Point at the freezing level**

The 0 °C isotherm is already heavier than its neighbours, by default (spec §3.2). Tell the reader what that line is — they have been looking at it since Step 1 — and note that `emphasis={}` turns it off. Do **not** add a figure for this; the point is that it needed no code.

- [ ] **Step 4: Add to the index toctree**

In `docs/src/tutorials/index.rst`, add `first-tephigram` **above** `browser-demo`: a newcomer meets the diagram before the exhibit.

- [ ] **Step 5: Register the page**

Add `"tutorials/first-tephigram.rst"` to `DOCUMENTED`, `PUBLISHES_FIGURES` and `PUBLISHES`.

- [ ] **Step 6: Build, generate baselines, read them**

```bash
pixi run docs
pixi run docs-figures
```
Expected: `2 added`. Open both files. The first must be an empty grid; the second must carry two coloured traces and a legend.

- [ ] **Step 7: Verify**

Run: `pixi run tests && pixi run lint && pixi run docs`

- [ ] **Step 8: Commit**

```bash
git add docs/src/tutorials/first-tephigram.rst docs/src/tutorials/index.rst \
        docs/src/reference/glossary.rst docs/baseline/first-tephigram-*.png \
        tests/test_docs_snippets.py .github/scripts/check_docs_figures.py
git commit -m "Add the first-tephigram tutorial"
```

### Task 5: *Analyse a Sounding*

**Files:**
- Create: `docs/src/tutorials/analyse-a-sounding.rst`
- Modify: `docs/src/tutorials/index.rst`
- Modify: `tests/test_docs_snippets.py`, `.github/scripts/check_docs_figures.py`
- Create: `docs/baseline/analyse-a-sounding-parcel.png`, `docs/baseline/analyse-a-sounding-shaded.png`, `docs/baseline/analyse-a-sounding-indices.png` (generated)

**Interfaces:**
- Consumes: Task 4's `_tutorial-first-tephigram` label; Task 2's `_explanation-parcel-ascent` label.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Write the opening and the parcel**

```rst
.. _tutorial-analyse-a-sounding:

Analyse a Sounding
==================
```

Say it continues from :ref:`tutorial-first-tephigram` and that a reader arriving cold loses only one block. Then:

```rst
.. plot::
    :context: reset
    :filename-prefix: analyse-a-sounding-parcel

    import matplotlib.pyplot as plt

    import tephpy
    from tephpy import samples

    snd = samples.sounding("norman-12z")
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(snd)
    parcel = tephpy.calc.parcel_path(snd)
    ax.plot_profile(parcel, color="k", linestyle="--")
    ax.legend()
```

Explain what the dashed line is, and link the derivation to ``:ref:`explanation-parcel-ascent` ``.

- [ ] **Step 2: Shade the areas**

```rst
.. plot::
    :context: close-figs
    :filename-prefix: analyse-a-sounding-shaded

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(snd)
    ax.plot_profile(parcel, color="k", linestyle="--")
    ax.shade_cape(snd, parcel)
    ax.shade_cin(snd, parcel)
    ax.legend()
```

- [ ] **Step 3: Add the indices panel**

```rst
.. plot::
    :context: close-figs
    :filename-prefix: analyse-a-sounding-indices

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(snd)
    ax.plot_profile(parcel, color="k", linestyle="--")
    ax.shade_cape(snd, parcel)
    ax.shade_cin(snd, parcel)
    ax.annotate_indices(tephpy.calc.indices(snd))
    ax.legend()
```

Close by handing over: this is where the gallery's parcel-analysis example begins. The tutorial is how it is built; the gallery is what it looks like finished.

- [ ] **Step 4: Index, register, seed terms**

Add `analyse-a-sounding` to the tutorials toctree under `first-tephigram`; add the page to `DOCUMENTED`, `PUBLISHES_FIGURES` and `PUBLISHES`; seed any new `:term:`.

- [ ] **Step 5: Build, generate baselines, read them**

```bash
pixi run docs
pixi run docs-figures
```
Expected: `3 added`. Open each. The shaded figure must show two distinctly coloured areas; the indices figure must carry a readable panel that does not overlap the diagram.

- [ ] **Step 6: Verify**

Run: `pixi run tests && pixi run lint && pixi run docs`

- [ ] **Step 7: Commit and open the pull request**

```bash
git add docs/src/tutorials/analyse-a-sounding.rst docs/src/tutorials/index.rst \
        docs/src/reference/glossary.rst docs/baseline/analyse-a-sounding-*.png \
        tests/test_docs_snippets.py .github/scripts/check_docs_figures.py \
        changelog/<PR>.documentation.rst
git commit -m "Add the sounding-analysis tutorial"
```

Cite `narrative spec §3.2` and `narrative spec §3.3` in the pull request, and answer *Reviewing Claims*' three questions in its body.

---

# Tranche C — the reader how-to, and the samples it needs

The package change and the page that justifies it land together (narrative spec §6).

### Task 6: Ship the Camborne pair

**Files:**
- Create: `src/tephpy/samples/UKM00003808-data-trimmed.txt` (copied from `tests/fixtures/io/`)
- Create: `src/tephpy/samples/wyoming-03808-2026-07-21-12Z.csv` (copied from `tests/fixtures/io/`)
- Modify: `src/tephpy/samples/__init__.py`
- Modify: `pyproject.toml` (`[tool.setuptools.package-data]`)
- Modify: `tests/test_samples.py`
- Modify: `docs/src/developer/specs/2026-08-20-examples-gallery-design.md` (§3.1's `path()` line)

**Interfaces:**
- Consumes: `wyoming.parse` from {pull}`203`.
- Produces: `samples.available()` gains `"camborne-igra-12z"` and `"camborne-wyoming-12z"`; `samples.path(name: str) -> Path` **replaces** the current no-argument `path()`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_samples.py`:

```python
def test_the_camborne_pair_is_one_ascent_in_two_formats():
    """The page's whole point: two readers, one Sounding (narrative spec §3.6)."""
    igra = samples.sounding("camborne-igra-12z")
    wyo = samples.sounding("camborne-wyoming-12z")
    assert igra.time == wyo.time
    assert igra.pressure[0].m_as("hPa") == pytest.approx(
        wyo.pressure[0].m_as("hPa"), abs=0.5
    )


def test_every_sample_routes_through_a_public_reader():
    """A sample a user cannot reproduce is a sample that proves nothing."""
    for name in samples.available():
        assert samples.sounding(name).pressure.size > 0


def test_path_takes_the_sample_name():
    assert samples.path("camborne-wyoming-12z").suffix == ".csv"
    assert samples.path("norman-12z").suffix == ".txt"
```

- [ ] **Step 2: Run them and watch them fail**

Run: `pixi run tests -k samples`
Expected: FAIL — unknown sample names, and `path()` takes no argument.

- [ ] **Step 3: Copy the two files**

```bash
cp tests/fixtures/io/UKM00003808-data-trimmed.txt src/tephpy/samples/
cp tests/fixtures/io/wyoming-03808-2026-07-21-12Z.csv src/tephpy/samples/
```

- [ ] **Step 4: Rework the samples module**

Replace `_FILE` and `_SAMPLES` with a per-sample mapping of name to file, reader and selecting time, so `sounding()` dispatches by sample and every sample still goes through a public reader. Change `path()` to take the sample name. Carry the attribution from `tests/fixtures/io/README.md` into the module docstring — the University of Wyoming one especially, since it now travels in the wheel — together with the provenance already recorded there and the position narrative spec §3.6 states.

- [ ] **Step 5: Carry the second format into the wheel**

In `pyproject.toml`, `[tool.setuptools.package-data]` lists `"samples/*.txt"`. Add `"samples/*.csv"` beside it, with a comment saying why there are now two globs.

- [ ] **Step 6: Run the tests**

Run: `pixi run tests`
Expected: PASS, including the existing gallery and example tests that call `samples.sounding("norman-12z")`.

- [ ] **Step 7: Correct the gallery specification**

`gallery spec §3.1` documents `samples.path()  # -> the shipped IGRA file` and the module docstring explains that it takes no argument *because* there is one file. Both statements are now false. Correct them in place — the specification is a living document, and a stale line here is exactly the defect {issue}`193` catalogues.

- [ ] **Step 8: Verify and commit**

```bash
pixi run tests && pixi run lint && pixi run docs
git add src/tephpy/samples pyproject.toml tests/test_samples.py \
        docs/src/developer/specs/2026-08-20-examples-gallery-design.md
git commit -m "Ship the Camborne ascent in both its formats"
```

### Task 7: *Read a Sounding*

**Files:**
- Create: `docs/src/howtos/read-a-sounding.rst`
- Modify: `docs/src/howtos/index.rst`
- Modify: `tests/test_docs_snippets.py`, `.github/scripts/check_docs_figures.py`
- Create: `docs/baseline/read-a-sounding-converged.png` (generated)

**Interfaces:**
- Consumes: Task 6's `samples.path(name)` and the two Camborne samples.
- Produces: the built page, which the README does not link (no change there).

- [ ] **Step 1: Write the page**

```rst
.. _howto-read-a-sounding:

Read a Sounding From an Archive
===============================
```

Two routes in, one type out. Show IGRA first because it is the format the package ships most of:

```rst
.. plot::
    :context: reset
    :nofigs:

    from tephpy import samples
    from tephpy.io import igra, wyoming

    igra_sounding = igra.read(samples.path("camborne-igra-12z"), time="2026-07-21 12:00")
```

Then the Wyoming route over the same ascent:

```rst
.. plot::
    :context:
    :nofigs:

    body = samples.path("camborne-wyoming-12z").read_text()
    wyoming_sounding = wyoming.parse(body, station="03808", time="2026-07-21 12:00")
```

- [ ] **Step 2: Draw the convergence**

```rst
.. plot::
    :context:
    :filename-prefix: read-a-sounding-converged

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(igra_sounding)
    ax.legend()
```

Say what the figure shows: the same ascent reached two ways, drawn once, because what comes out of either reader is the same type.

- [ ] **Step 3: Say what `fetch` is for, and why it is not a block here**

Describe :func:`wyoming.fetch(...) <tephpy.io.wyoming.fetch>` as the route for live data, and state plainly that this page does not run it: the documentation build executes every python block, and a build that reaches the network fails for reasons that have nothing to do with the documentation (spec §8.5). `parse` is what `fetch` uses once the body has arrived, so the block above is the same code path minus the request.

- [ ] **Step 4: Index and register**

Add `read-a-sounding` to `docs/src/howtos/index.rst`, in alphabetical position. Add the page to `DOCUMENTED`, `PUBLISHES_FIGURES` and `PUBLISHES`.

- [ ] **Step 5: Build, generate the baseline, read it**

```bash
pixi run docs
pixi run docs-figures
```
Expected: `1 added`. Open it and confirm a single sounding is drawn, not two overlaid.

- [ ] **Step 6: Verify**

Run: `pixi run tests && pixi run lint && pixi run docs`

- [ ] **Step 7: Commit and open the pull request**

```bash
git add docs/src/howtos/read-a-sounding.rst docs/src/howtos/index.rst \
        docs/baseline/read-a-sounding-converged.png \
        tests/test_docs_snippets.py .github/scripts/check_docs_figures.py \
        changelog/<PR>.documentation.rst
git commit -m "Add the archive-reading how-to"
```

The pull request body must state the redistribution position of narrative spec §3.6 rather than leaving the new sample unexplained, and link {issue}`202`.

### Task 8: Close the plan

- [ ] **Step 1: Close what this plan closes**

Close {issue}`189` citing narrative spec §3.8. Comment on {issue}`66` that the user half is delivered and the developer-guide half remains.

- [ ] **Step 2: Mark the roadmap row complete**

In `docs/src/developer/specs/2026-07-22-tephpy-design.md` §10, change Plan 7c's Status cell from `after Plan 8` to `✅ complete (PR …)` naming the tranche pull requests.

- [ ] **Step 3: Freeze this plan**

Per docs spec §3.4 a plan is a point-in-time record: once the last tranche merges, this file is not updated again. Corrections belong in the specification.

---

## Self-Review

**Spec coverage.** §3.2 → Task 4. §3.3 → Task 5. §3.4 → Task 1. §3.5 → Task 2. §3.6 → Tasks 6 and 7. §3.7 (glossary sweep) → a step in each prose task rather than a task of its own, which is what "a constraint on each page rather than a task after them" means. §3.8 → Task 8 Step 1. §4 companion changes → distributed across the tasks that need them. §5 testing → the Global Constraints and each task's verify step. §6 tranches → the three tranche headings.

**Placeholders.** The prose of five pages is deliberately described rather than written out: a plan that dictated the sentences would be writing the documentation, and the spec's sections are what the prose argues from. Every *code* block, command, file path and registration is exact.

**Type consistency.** `samples.path(name)` is introduced in Task 6 and used in Task 7 with the same signature. `samples.sounding(name)` is unchanged throughout. Sample names — `"norman-12z"`, `"camborne-igra-12z"`, `"camborne-wyoming-12z"` — are spelled identically in Tasks 5, 6 and 7.
