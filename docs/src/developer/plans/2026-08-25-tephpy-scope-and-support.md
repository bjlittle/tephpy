# Scope and Support Statements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the five `set_extent`-independent items of spec §10's Plan 7b row — the README non-goals statement, the ecCodes recipe, the developer packaging guide carrying the SPEC 0 statement, the lapse rate glossary entry, and the disposal of the doctest residual — and split the roadmap row so the narrative half waits behind {issue}`184`.

**Architecture:** Everything here is documentation and specification text. No `src/tephpy` module changes, no new CI gate, no new dependency. Each deliverable lands inside a gate that already exists: the snippet executor runs the recipe's python, the figure gate compares its one published figure, the link gate resolves the README's new URLs, and the citation gate resolves every `spec §…` written along the way. That "no new gate" property is not incidental — for Task 6 it is the evidence that the doctest residual is superseded rather than skipped.

**Tech Stack:** Sphinx 8 + `pydata-sphinx-theme`, MyST for the Markdown specifications, `matplotlib.sphinxext.plot_directive` for published figures, pixi for every task, pytest for the gates.

**Spec:** `docs/src/developer/specs/2026-08-25-scope-and-support-design.md` (citation prefix `scope spec §…`). Read it alongside this plan; every task below cites the section it implements, and where the two disagree the specification is right and this plan is stale.

## Global Constraints

Copied verbatim from the specifications that bind every task. Violating any of these fails a gate, not a review.

- **Copyright header.** Every source file carries the BSD header (ruff `CPY001`). No file created by this plan is Python, so none needs one — but if you add a script, it does.
- **Changelog.** Every PR adds `changelog/<PR>.<type>.rst` ending with ``(:user:`<github-username>`)``. This plan adds exactly one, of type `documentation` (scope spec §4).
- **Titles.** Chicago Manual of Style headline style for every hand-authored page and section title (spec §8.6). Literal case is preserved for code identifiers, filenames, CLI commands, paths, project names in their own casing (`ecCodes`, `matplotlib`, `pixi`, `tephpy`), acronyms and scientific symbols (`CAPE`, `SPEC 0`, `θ`). Full sentences — captions, admonition bodies, alt text — use sentence case.
- **Specification citations.** Cite as plain text — `spec §8.3`, `docs spec §3.9`, `floors spec §3.3`, `scope spec §3.1`. **A bare `§N` means a section of the document you are writing in.** In a `.rst` page under `docs/src/`, a bare `§N` has no owning document and must not be written; always give the prefix. A citation must sit whole on one line. Verified by `.github/scripts/check_citations.py`.
- **GitHub references.** Write ``:issue:`82``` and ``:pull:`181``` in reStructuredText, `` {issue}`82` `` and `` {pull}`181` `` in the Markdown specifications. Never a bare `#82`, never a hardcoded `https://github.com/bjlittle/tephpy/issues/82`. Keep the word that says which kind it is — ``PR :pull:`181``` (docs spec §3.8). **`README.md` is in this gate's corpus and Markdown has no role**, so the README may not reference an issue at all (scope spec §3.1).
- **Documentation links from `README.md`.** Absolute `https://tephpy.readthedocs.io/en/latest/<page>.html`, written as a Markdown reference link. A fragment must name an `id` that exists on the built page. Verified by `.github/scripts/check_documentation_links.py` against the build, so **the page must exist in the build before the README may link it**.
- **Glossary.** Definitions for software engineers, not meteorologists: the concept in one plain sentence, then how it appears in tephpy. Link *related* terms inside a definition, never the term itself. One canonical spelling per concept, variants as further headwords (spec §8.6).
- **Page shape where figures are published** (plots spec §3.2): on a page that publishes a figure, **every** python block is a `.. plot::`; the first carries `:context: reset`; every later one carries `:context:` or `:context: close-figs`; a block whose picture would add nothing carries `:nofigs:` and still runs; every figure-producing block carries a `:filename-prefix:`; no `.. plot:: script.py` file-argument form.
- **A published block may not leave `tephpy.config` mutated** (plots spec §3.3). No task here touches config, but the rule binds the recipe page.

**Working branch:** `scope-and-support`, already created, already carrying the specification commits. Do not branch again.

**The command you run after almost every task:** `pixi run --frozen --environment docs docs` — builds the HTML and runs the citation, link and figure gates. `pixi run --frozen tests` runs the snippet gate. `pixi run --frozen lint` runs pre-commit, including the citation and GitHub-reference hooks.

---

### Task 1: File the Tracked Issue the Specification Already Cites

scope spec §6 carries an open item whose issue number is the literal placeholder `NNN`. docs spec §3.5 forbids an open item that cites no tracked issue, so this is a defect in a committed document and it is fixed first — before anything else can be reviewed against that specification.

**Files:**
- Modify: `docs/src/developer/specs/2026-08-25-scope-and-support-design.md` (the `**Open** ({issue}`NNN`)` bullet in §6)

**Interfaces:**
- Consumes: nothing.
- Produces: the issue number, referred to below as `<EXAMPLES-ISSUE>`. Task 6 does not need it; no later task does. It exists only to satisfy the §3.5 contract.

- [ ] **Step 1: Confirm the placeholder is really there**

```bash
grep -n "NNN" docs/src/developer/specs/2026-08-25-scope-and-support-design.md
```

Expected: two lines — the bullet and the italic note under it.

- [ ] **Step 2: File the issue**

```bash
gh issue create \
  --title "Decide whether the public API should carry doctested Examples sections" \
  --label "type: documentation" --label "design: open" \
  --body 'The snippet executor of docs spec §3.9 runs every python block in the three
user quadrants. Its corpus stops there: the reference quadrant is excluded because it is
generated from the docstrings and cannot drift from them.

That argument is about drift between a page and its source. It is not about whether a
docstring runs. `src/tephpy` carries no numpydoc `Examples` section today, so there is
nothing unexecuted and no gate is missing — the open question is whether to write them,
and to gate them with `--doctest-modules` over `src/` if so.

Two things make it a real decision rather than a chore:

- Most of the public surface returns matplotlib artists or draws onto an Axes, which is
  an awkward shape for a doctest. What would be asserted is often nothing.
- It collides with #184. `set_extent` is one of the first methods anyone would write an
  example for, and that issue replaces its signature.

Recorded as **Open** in the scope and support statements design specification §6, which
is where the reasoning lives. Tracked per docs spec §3.5.'
```

- [ ] **Step 3: Substitute the number**

Take the issue number `gh` printed. With `186` as an example — **use the real number**:

```bash
sed -i 's/{issue}`NNN`/{issue}`186`/' docs/src/developer/specs/2026-08-25-scope-and-support-design.md
```

Then delete the italic note that told you to do this, which is now spent. Open the file and remove exactly these three lines from the `**Open**` bullet in §6:

```
  *`NNN` is substituted when the issue is filed, which the implementation plan does before
  this document is committed — an open item citing no issue would breach the docs spec §3.5
  contract this section is written under.*
```

- [ ] **Step 4: Verify no placeholder survives**

```bash
grep -n "NNN" docs/src/developer/specs/2026-08-25-scope-and-support-design.md
```

Expected: no output, exit 1.

- [ ] **Step 5: Verify the reference gates**

```bash
python3 .github/scripts/check_citations.py
python3 .github/scripts/check_github_references.py
```

Expected: both report `ok`.

- [ ] **Step 6: Commit**

```bash
git add docs/src/developer/specs/2026-08-25-scope-and-support-design.md
git commit -m "Cite the docstring-Examples issue the specification opened

scope spec §6 shipped its open item with a placeholder issue number,
which breaches the docs spec §3.5 contract it is written under: an item
that is not Resolved, Refined or Rejected must cite a tracked issue.
Files it and substitutes the number.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: The Developer Packaging Guide

Implements scope spec §3.3. Discharges the fifth of spec §8.3's five enforcement points — "a docs statement in the developer/packaging guide" — which has been the only one without a home.

**Files:**
- Create: `docs/src/developer/packaging.rst`
- Modify: `docs/src/developer/index.rst` (toctree)
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md` (spec §8.3's fifth bullet)

**Interfaces:**
- Consumes: nothing.
- Produces: the Sphinx label `_developer-packaging`, and the built page `developer/packaging.html`. Nothing else in this plan links it; spec §8.3 points at it in prose.

- [ ] **Step 1: Write the page**

Create `docs/src/developer/packaging.rst` with exactly this content:

```rst
.. _developer-packaging:

Packaging and Support
=====================

What ``tephpy`` runs on, what holds it there, and what its distributions carry.

Supported Pythons
-----------------

``tephpy`` follows `Scientific Python SPEC 0
<https://scientific-python.org/specs/spec-0000/>`__. The supported window is
**Python 3.12, 3.13 and 3.14**, and it is revisited on each SPEC 0 rotation
(spec §8.3).

Five things enforce that window, and it is worth knowing which are which:

.. list-table::
    :header-rows: 1
    :widths: 40 15 45

    * - Where
      - Kind
      - What it does
    * - the SPEC 0 badge in ``README.md``
      - assertion
      - states the policy to a reader arriving at the repository
    * - this page
      - assertion
      - states the window, and this table
    * - the ``py312``/``py313``/``py314`` matrix in ``ci-tests``
      - mechanism
      - runs the whole suite on each supported Python
    * - the per-Python pixi solve-groups
      - mechanism
      - resolves a separate environment for each, so a dependency
        that has dropped one is a solve failure
    * - the ``sp-repo-review`` pre-commit hook
      - mechanism
      - reports a packaging declaration that has drifted from the
        Scientific Python conventions

The distinction matters. An assertion is a sentence someone has to keep true; a
mechanism fails on its own when it stops being true. ``requires-python`` and the
trove classifiers in ``pyproject.toml`` sit between the two — an installer
enforces them for a user, and nothing enforces them here — so treat them as
assertions when you change the window, and change all of them together.

Dependency Floors
-----------------

The support window fixes the Python versions. Every other lower bound is a
*dependency floor*, and floors are tested by a workflow of their own rather than
by the test matrix: ``ci-floors`` resolves an environment pinned at the declared
floors and runs the tier that depends on them, so a floor that no longer works
fails with a package name attached instead of surfacing as a mystery on somebody
else's machine.

Three tiers run — ``test``, ``docs`` and ``devs``. The machinery behind them is
floors spec: the two declaration sites (floors spec §3.1), the pin generator
(floors spec §3.2), the attribution scan that names the culprit (floors spec
§3.4), and the issue contract that files one finding per tier and package
(floors spec §3.6). None of it is restated here, deliberately — a developer
guide that copied a specification would be a second copy to drift from it.

Raise a floor when ``tephpy`` starts using something the older version does not
have, and say so in the changelog fragment. Lower one only with a reason.

What the Distributions Carry
----------------------------

The sdist and the wheel do not carry the same tree, and one asymmetry between
them is load-bearing.

``MANIFEST.in`` prunes ``docs/src/developer/plans``, and ``docs/src/conf.py``
excludes the same directory from the HTML build. So an implementation plan is
tracked in the repository, absent from the sdist, and unpublished on the site.
That is deliberate: a specification is a living document and a plan is a
point-in-time record of what was intended before implementation (docs spec
§3.1). The two exclusions are written differently — Sphinx compiles ``*`` to a
pattern that does not cross a solidus, so the ``exclude_patterns`` entry needs
``**`` to match what ``prune`` matches recursively — and the direction that
asymmetry would fail in is the leaking one, which is why both are spelled out
in ``conf.py``'s comment.

Beyond the code itself, the wheel carries the sample soundings and the gallery
header of gallery spec §3.7, the ``py.typed`` marker, and the logo masters under
``src/tephpy/plotting/_static``. Each has a line in ``MANIFEST.in``.

check-manifest
--------------

``check-manifest`` is declared in ``[tool.pixi.feature.devs.dependencies]`` and
run by nothing — no pixi task, no pre-commit hook, no workflow step. Adopting it
is :issue:`77`.

It is worth knowing that this is a real gap rather than a theoretical one.
``MANIFEST.in`` has already gone stale once: a ``prune`` entry silently stopped
matching when the directory it named moved, and only a hand-run ``python -m
build --sdist`` caught it before the affected files shipped. A declared
dependency that nothing runs looks from the outside exactly like a check that
passes.
```

- [ ] **Step 2: Add it to the developer toctree**

In `docs/src/developer/index.rst`, the toctree becomes:

```rst
.. toctree::
    :maxdepth: 1

    docs-style
    packaging
    specs/index
```

- [ ] **Step 3: Point spec §8.3 at the page it now has**

In `docs/src/developer/specs/2026-07-22-tephpy-design.md`, find the second bullet of §8.3:

```
- Enforced by: README SPEC 0 badge, a docs statement in the developer/packaging guide, the
  CI Python matrix (`py312`/`py313`/`py314`), the per-Python pixi solve-groups, and the
  `sp-repo-review` pre-commit hook.
```

Replace it with:

```
- Enforced by: README SPEC 0 badge, the support statement in the developer packaging guide
  (`docs/src/developer/packaging.rst`, delivered by scope spec §3.3, which also records
  which of the five are assertions and which are mechanisms), the CI Python matrix
  (`py312`/`py313`/`py314`), the per-Python pixi solve-groups, and the `sp-repo-review`
  pre-commit hook.
```

- [ ] **Step 4: Build and run the gates**

```bash
pixi run --frozen --environment docs docs
```

Expected: `build succeeded.`, then three `ok` lines. The rendered-citation count rises — the new page's `spec §8.3`, `floors spec §3.1`, `floors spec §3.2`, `floors spec §3.4`, `floors spec §3.6`, `docs spec §3.1` and `gallery spec §3.7` all become links.

If the build fails with `undefined label: 'packaging-...'`, you wrote a bare `§N` somewhere on the page. Give it its prefix.

- [ ] **Step 5: Run lint**

```bash
pixi run --frozen lint
```

Expected: all hooks pass. `Sphinx Lint` and the three `rst` hooks read the new page.

- [ ] **Step 6: Commit**

```bash
git add docs/src/developer/packaging.rst docs/src/developer/index.rst \
        docs/src/developer/specs/2026-07-22-tephpy-design.md
git commit -m "Give the SPEC 0 support statement the guide it was promised

spec §8.3 names five things that enforce the support window. Four exist.
The fifth is 'a docs statement in the developer/packaging guide', and
there has been no packaging guide since Plan 1 wrote the sentence -- so
the window has been checkable by a contributor reading pyproject.toml and
by nobody else.

Adds the guide, and gives it more than the one paragraph it owes: the
window and which of its five enforcement points are assertions and which
are mechanisms, the dependency-floor policy with the machinery left to
floors spec, what the sdist and the wheel each carry and why the plans
are pruned from both, and check-manifest's position (issue #77).

Implements scope spec §3.3.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: The Lapse Rate Glossary Entry

Implements scope spec §3.4 and closes {issue}`183`. The last term on spec §8.6's own enumerated list without an entry.

**Files:**
- Modify: `docs/src/reference/glossary.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: the glossary terms `lapse rate`, `dry adiabatic lapse rate`, `DALR`, `moist adiabatic lapse rate`, `saturated adiabatic lapse rate`, `SALR` — all six resolvable by `:term:` from any page.

- [ ] **Step 1: Decide where it goes**

Order the glossary by concept, not alphabetically — it already is. The entry belongs immediately after `moist adiabat` and before `wet-bulb potential temperature`, because it is the rate the two adiabat entries are both about and it reads as their continuation.

- [ ] **Step 2: Write the entry**

In `docs/src/reference/glossary.rst`, insert this **after** the `moist adiabat` entry (the block ending `matching the AMS Glossary headword and MetPy's vocabulary.`) and **before** `wet-bulb potential temperature`:

```rst
    lapse rate
    dry adiabatic lapse rate
    DALR
    moist adiabatic lapse rate
    saturated adiabatic lapse rate
    SALR
        The rate at which temperature falls with height. Two of them matter
        on a tephigram, and they are the rates the two adiabat families
        draw: the **dry adiabatic lapse rate** (DALR), which an unsaturated
        :term:`parcel` cools at, and the **moist adiabatic lapse rate**
        (SALR, for *saturated*), which a saturated one cools at — more
        slowly, because condensation releases heat into the parcel as it
        rises. Which of the two a lifted parcel is following, and where it
        changes over, is the whole content of a :term:`parcel ascent`.
        "Moist" leads here for the same reason it leads in
        :term:`moist adiabat`: one canonical spelling per concept, and that
        entry chose it. ``tephpy`` has no lapse-rate API of its own. The dry
        rate is implicit in every :term:`dry adiabat` the diagram draws, and
        the saturated rate is MetPy's — :func:`metpy.calc.moist_lapse` is
        what a moist adiabat is integrated from, and what it integrates is
        strictly the *pseudoadiabatic* rate, which differs from the
        reversible saturated rate by an amount no tephigram resolves.
```

Three things to notice about that text, because they are the rules and not the prose:

1. It links `parcel`, `parcel ascent`, `moist adiabat` and `dry adiabat` — *related* terms — and never links any of its own six headwords. That is spec §8.6.
2. It ends with how the concept appears in tephpy, as spec §8.6 requires, and the honest answer is that it does not appear as an API. Do not manufacture a citation to satisfy the rule.
3. `metpy.calc.moist_lapse` takes the `:func:` role, so intersphinx resolves it. `SALR` and `DALR` are acronyms and get entries, as spec §8.6 requires of every acronym.

- [ ] **Step 3: Build**

```bash
pixi run --frozen --environment docs docs-html
```

Expected: `build succeeded.` A dangling `:term:` is an error under fail-on-warning, so a typo in any of the four links fails here.

- [ ] **Step 4: Verify all six headwords became targets**

```bash
grep -o 'id="term-[A-Za-z0-9-]*"' docs/_build/html/reference/glossary.html | sort -u | grep -iE "lapse|DALR|SALR"
```

Expected: six ids — `term-lapse-rate`, `term-dry-adiabatic-lapse-rate`, `term-DALR`, `term-moist-adiabatic-lapse-rate`, `term-saturated-adiabatic-lapse-rate`, `term-SALR`.

- [ ] **Step 5: Run the remaining gates**

```bash
pixi run --frozen --environment docs docs
pixi run --frozen lint
```

Expected: three `ok` lines, then all hooks pass.

- [ ] **Step 6: Commit and close the issue**

```bash
git add docs/src/reference/glossary.rst
git commit -m "Add the lapse rate glossary entry

spec §8.6 enumerates the domain jargon that earns an entry. Every term on
that list had one except lapse rate -- the rate the dry adiabat and moist
adiabat entries are both really about, and whose acronyms DALR and SALR
are what a reader meets first everywhere outside this project.

The headword is the general concept, because that is the word a reader
arrives with and the two adiabatic rates are cases of it. Where issue
#183's spelling question actually bites is the saturated rate, and there
the entry agrees with its neighbour rather than reopening the choice.
It says outright that tephpy has no lapse-rate API, which is true and is
more use than a manufactured citation.

Implements scope spec §3.4. Closes #183.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

The `Closes #183` trailer is a commit message, not tracked source, so the GitHub-reference gate does not read it. Leave the bare `#183` exactly as written — GitHub needs that form to close the issue.

---

### Task 4: The ecCodes Recipe

Implements scope spec §3.2. Answers the first non-goal, and is the page Task 5's README section links — so it lands first.

This is the only task in the plan that publishes a figure, which brings plots spec §3.2's page shape with it and three membership tuples that must all learn about the page.

**Files:**
- Create: `docs/src/howtos/temp-and-bufr.rst`
- Create: `docs/baseline/temp-and-bufr-sounding.png` (generated, not hand-written — Step 6)
- Modify: `docs/src/howtos/index.rst` (toctree)
- Modify: `tests/test_docs_snippets.py` (`DOCUMENTED` and `PUBLISHES_FIGURES`)
- Modify: `.github/scripts/check_docs_figures.py` (`PUBLISHES`)

**Interfaces:**
- Consumes: nothing.
- Produces: the built page `howtos/temp-and-bufr.html`, which Task 5's README reference link `[temp-and-bufr]` resolves against. The figure prefix `temp-and-bufr-sounding` is project-wide unique and `check_output_base_name` enforces that.

- [ ] **Step 1: Understand why this page shows no output transcript**

**Do not invent tool output.** A page that shows what a command prints, when nobody ran it, is a fabricated record presented as genuine. This step exists so you do not reach for one.

The controller already tried, with ecCodes 2.48.0 installed via `pixi exec --spec eccodes`. The result:

- ecCodes ships **no sample sounding message** — `share/eccodes/samples/` holds only `BUFR*.tmpl` templates, which are not soundings.
- Encoding a valid radiosonde message from the template (WMO sequence 3 09 052) got as far as a real, dumpable BUFR file, but populating its delayed-replication level arrays failed on an array-size mismatch. A synthetic message is also not what the page is about.

**What was verified**, from genuine `bufr_dump -p` output, and what the page may therefore state as fact:

- The key names a radiosonde message carries: `pressure`, `airTemperature`, `dewpointTemperature`, `windSpeed`, `windDirection`; `blockNumber` and `stationNumber` for the station; `year`, `month`, `day`, `hour`, `minute` for the launch; `latitude`, `longitude`.
- `bufr_dump -p` prints one `key=value` line per key.
- An absent value prints as the literal `MISSING`.

So the page shows the **invocation** and describes the output in prose. Everything it claims above is checked. Nothing is invented.

If you happen to have a real BUFR sounding to hand and want to include genuine output, you may — but it must be output you actually produced, pasted unedited. Do not synthesise one to fill the block.

- [ ] **Step 2: Write the page**

Create `docs/src/howtos/temp-and-bufr.rst`. Substitute your real transcript into the `console` block; everything else is as written:

```rst
.. _howto-temp-and-bufr:

Decode BUFR with ecCodes
========================

``tephpy`` does not decode TEMP (TTAA/TTBB) bulletins or BUFR messages, and it
is not going to. The formats are WMO's, the reference decoder for BUFR is
`ecCodes <https://confluence.ecmwf.int/display/ECC>`__, and a second
implementation would be a worse copy of a maintained one. Whether demand later
justifies a ``tephpy[bufr]`` extra is :issue:`82`.

That leaves a seam rather than a gap, and this page is the seam. ecCodes turns a
BUFR message into numbers; ``tephpy`` turns numbers into a :term:`tephigram`. A
TEMP bulletin is a different problem, and gets its own section below.

Decode the Message
------------------

ecCodes ships command-line tools, and they are the shortest route in. ``bufr_dump``
prints a message as one ``key=value`` line per key:

.. code-block:: console

    $ bufr_dump -p sounding.bufr

A radiosonde message carries the levels as ``pressure``, ``airTemperature`` and
``dewpointTemperature``, with ``windSpeed`` and ``windDirection`` beside them;
``blockNumber`` and ``stationNumber`` identify the station, and ``year`` through
``minute`` give the launch time. A value the message does not carry prints as the
literal ``MISSING``, which matters below.

Install ecCodes however you install anything — it is on conda-forge as
``eccodes``, and ECMWF publish source and packages. It is not installed by
``tephpy`` and does not need to be: nothing on the rest of this page imports it.

If You Have a TEMP Bulletin
---------------------------

``bufr_dump`` will not read one. ecCodes decodes BUFR and GRIB, the binary WMO
formats, and a TTAA/TTBB bulletin is neither — it is traditional alphanumeric
code, and nothing above applies to it as it stands.

Nor is there a converter to send you to. WMO's `synop2bufr
<https://github.com/World-Meteorological-Organization/synop2bufr>`__ encodes
FM-12 SYNOP rather than TEMP, and re-encoding is discouraged where it is done at
all: a converted bulletin still lacks what a native message carries, the
radiosonde type and the balloon's drift among it, and cannot recover precision
the code form never had.

What works is not converting. The bulletin and the message carry the same
ascent, and WMO's migration away from the traditional code forms means most
sources can issue the BUFR, so ask yours for that rather than for the bulletin.
For a station and a time, :func:`wyoming.fetch <tephpy.io.wyoming.fetch>`
returns a :class:`Sounding <tephpy.sounding.Sounding>` from the University of
Wyoming archive and skips this page entirely. And if you do decode the bulletin,
by whatever your centre uses, the rest of this page is unchanged: what follows
takes numbers and does not care what produced them.

Build a Sounding
----------------

What comes out is arrays. What ``tephpy`` wants is a
:class:`Sounding <tephpy.sounding.Sounding>`, which takes bare sequences plus a
``units=`` mapping saying what they are in:

.. plot::
    :context: reset
    :nofigs:

    import tephpy

    pressure = [1000.0, 925.0, 850.0, 700.0, 500.0, 400.0, 300.0, 250.0, 200.0]
    temperature = [22.4, 18.1, 13.6, 4.2, -12.5, -24.1, -39.8, -49.6, -56.2]
    dewpoint = [19.8, 16.4, 11.1, -2.9, -21.0, -34.7, -51.2, -60.1, -66.4]

    sounding = tephpy.Sounding(
        pressure=pressure,
        temperature=temperature,
        dewpoint=dewpoint,
        units={"pressure": "hPa", "temperature": "degC", "dewpoint": "degC"},
        station="72357",
    )

Pressure and temperature are required and everything else is optional, so a
message that carried no humidity still gives a usable sounding — drop the
``dewpoint`` argument and its ``units`` entry together.

Two things the decoder will hand you that need a moment. ecCodes reports
temperatures in kelvin and pressures in pascals; say so in ``units=`` rather
than converting by hand, because a conversion written twice is a conversion
that disagrees with itself once. And a BUFR sounding routinely carries missing
values at some levels — the ``MISSING`` above. Pass those through as
``float("nan")`` and ``tephpy`` treats them as gaps, which is what they are.
Pressure is the exception: it must be finite and monotonic, so drop a level
whose pressure is missing rather than passing a NaN.

Draw It
-------

From here it is an ordinary tephigram:

.. plot::
    :context:
    :filename-prefix: temp-and-bufr-sounding

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(sounding)

Where to Go Next
----------------

Reading an archive rather than a single message is what :mod:`tephpy.io` is for,
and the :doc:`gallery <../gallery/index>` shows what the package draws once a
sounding is in hand.
```

- [ ] **Step 3: Register the page in the how-to toctree**

`docs/src/howtos/index.rst` becomes:

```rst
How-To Guides
=============

Task-focused recipes.

.. toctree::
    :maxdepth: 1

    configuration
    emphasis
    logo
    temp-and-bufr
```

- [ ] **Step 4: Teach the snippet gate the page**

In `tests/test_docs_snippets.py`, both membership tuples gain it. `DOCUMENTED` becomes:

```python
DOCUMENTED = (
    "howtos/configuration.rst",
    "howtos/emphasis.rst",
    "howtos/logo.rst",
    "howtos/temp-and-bufr.rst",
)
```

and `PUBLISHES_FIGURES` becomes:

```python
PUBLISHES_FIGURES = (
    "howtos/emphasis.rst",
    "howtos/logo.rst",
    "howtos/temp-and-bufr.rst",
)
```

Both are membership rather than counts, and the docstrings above them say why — leave those comments alone.

- [ ] **Step 5: Teach the figure gate the page**

In `.github/scripts/check_docs_figures.py`, `PUBLISHES` becomes:

```python
PUBLISHES = ("howtos/emphasis.rst", "howtos/logo.rst", "howtos/temp-and-bufr.rst")
```

- [ ] **Step 6: Run the snippet gate, and expect it to pass before any figure exists**

```bash
pixi run --frozen tests -- tests/test_docs_snippets.py -v
```

Expected: PASS. This runs the page's two python blocks as one script — so it proves the `Sounding` construction and the `plot_sounding` call actually work, on every supported Python, before any baseline exists. If the `Sounding` constructor rejects your arrays, it fails **here**, which is the point of running this step before the build.

- [ ] **Step 7: Build, and expect the figure gate to fail**

```bash
pixi run --frozen --environment docs docs
```

Expected: the build succeeds, the citation and link gates pass, and **the figure gate fails** reporting `temp-and-bufr-sounding` as having no baseline. That failure is correct — there is no baseline yet. Read the message; it names the blessing command.

- [ ] **Step 8: Bless the baseline, then look at it**

```bash
pixi run --frozen --environment docs docs-figures
```

This writes `docs/baseline/temp-and-bufr-sounding.png`. **Open it.** Blessing approves a regression exactly as quietly as it approves a correct figure (plots spec §3.6), so the diff it writes is the thing to read before committing. You are checking that a tephigram appears with a red temperature trace and a green dewpoint trace, both plausibly shaped, inside the frame rather than off it.

- [ ] **Step 9: Re-run the full gate set**

```bash
pixi run --frozen --environment docs docs
pixi run --frozen tests
pixi run --frozen lint
```

Expected: `published figures ok: 13 compared` (twelve existing plus the new one), everything else `ok` or passing.

- [ ] **Step 10: Commit**

```bash
git add docs/src/howtos/temp-and-bufr.rst docs/src/howtos/index.rst \
        docs/baseline/temp-and-bufr-sounding.png \
        tests/test_docs_snippets.py .github/scripts/check_docs_figures.py
git commit -m "Add the ecCodes recipe for TEMP and BUFR

spec §9 rules TEMP and BUFR decoding out of v1 and says the how-to guides
point at ecCodes instead. They have not, so the first of the project's
non-goals has been a gap rather than a decision for anyone who met it.

The page is written along the seam it describes. The decode is ecCodes'
and is shown as a console transcript; the assembly is tephpy's and is
shown as python that runs -- so the half this project maintains is
executed by the snippet gate of docs spec §3.9 on every supported Python,
and the half it points at is checked by review. A python block calling
eccodes could not run at all: it is a non-goal, so it is in no test
environment, and that gate has no exemption mechanism by design.

Implements scope spec §3.2.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: The README Non-Goals Statement

Implements scope spec §3.1. spec §9's heading has said these are "stated in the README" since the roadmap was written; this makes that true.

Depends on Task 4: the link gate resolves `howtos/temp-and-bufr.html` against the build, so the page must already exist.

**Files:**
- Modify: `README.md`
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md` (spec §9's non-goals heading)

**Interfaces:**
- Consumes: the built page `howtos/temp-and-bufr.html` from Task 4, and the glossary anchor `term-hodograph`, which already exists.
- Produces: nothing later tasks use.

- [ ] **Step 1: Check the anchors you are about to name actually exist**

```bash
grep -o 'id="term-hodograph"' docs/_build/html/reference/glossary.html
ls docs/_build/html/howtos/temp-and-bufr.html docs/_build/html/gallery/index.html
```

Expected: the id prints, and both files exist. If `temp-and-bufr.html` is missing, Task 4 is not finished or the build is stale — rebuild before continuing.

- [ ] **Step 2: Add the section**

In `README.md`, insert this **after** the `> [!NOTE]` status block and **before** the reference-link definitions at the foot of the file:

```markdown
## Non-Goals

Decisions, not omissions — each with somewhere to go instead.

- **No TEMP (TTAA/TTBB) or BUFR decoding.** Decode BUFR with ecCodes and build a
  `Sounding` from the arrays; the [recipe][temp-and-bufr] shows both halves, and
  says where a TEMP bulletin leaves you instead.
- **No skew-T projection.** [MetPy](https://unidata.github.io/MetPy/latest/) owns
  that space.
- **No [hodograph][hodograph].** MetPy's `Hodograph` composes onto the same
  figure, and the [gallery][gallery] insets one over a tephigram.
- **No GUI or interactive dashboard.** The browser demo in the documentation is
  an exhibit, not a product.
- **No fog-point or layer-cloud constructions.** Candidates for v1.x.
- **No aviation overlays** (icing, MINTRA contrail curves). Also v1.x — though
  [member emphasis][emphasis] already distinguishes the icing band's 0 °C and
  −20 °C bounds, which is most of what the overlay would draw.
```

Then add these four reference-link definitions alongside the existing ones at the foot of the file, keeping them in the order the links appear above:

```markdown
[temp-and-bufr]: https://tephpy.readthedocs.io/en/latest/howtos/temp-and-bufr.html
[hodograph]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-hodograph
[gallery]: https://tephpy.readthedocs.io/en/latest/gallery/index.html
[emphasis]: https://tephpy.readthedocs.io/en/latest/howtos/emphasis.html
```

**Do not add an issue link to any of these entries.** `check_github_references.py` reads `README.md`, and Markdown has no `:issue:` role — scope spec §3.1 has the full reasoning. The issue-level state lives on the pages the README points at.

`hodograph` is the README's first and only mention of that term, so it takes the glossary link and no later occurrence does (docs-style, *Documentation Links*).

- [ ] **Step 3: Close the loop in spec §9 — in prose, never in the heading**

**Leave the heading exactly as it is.** An earlier draft of this step put the citation in
the heading, and that is forbidden: docs spec §3.7 reports a citation inside a section
heading, and `--fail-on-warning` turns the report into a build failure. The reason is
mechanical rather than stylistic — the theme rebuilds its "On this page" navigation out of
the heading text, keeps the words, drops the anchor, and wraps the copy in the navigation's
own link. The citation would then be a link to the section it sits in rather than to the
section it names, and no check on the built HTML can tell the two anchors apart. Writing
the link by hand does not help; the navigation strips an author's link the same way.

So cite it in the prose below. In `docs/src/developer/specs/2026-07-22-tephpy-design.md`,
insert one sentence between the heading and its bullet list, leaving both untouched:

```
### Non-goals for v1 (decisions, not omissions — stated in the README)

`README.md` carries these as its **Non-Goals** section, in the order below and each with an
onward pointer (scope spec §3.1).

- No TEMP (TTAA/TTBB) or BUFR decoding — recipe docs point at eccodes.
```

The last line above is the existing first bullet, shown so you can see where the new
sentence goes. Do not retype the bullets.

- [ ] **Step 4: Run the link gate**

```bash
pixi run --frozen --environment docs docs
```

Expected: `Documentation links ok: 13 checked across 2 sources` — the nine existing plus the four added. If it reports a URL "written some other way", you have used a preview host or dropped `en/latest`; only the canonical form can be looked up.

- [ ] **Step 5: Run lint**

```bash
pixi run --frozen lint
```

Expected: all hooks pass, including `GitHub references are links`. If that hook fails on `README.md`, you added an issue reference — remove it.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/src/developer/specs/2026-07-22-tephpy-design.md
git commit -m "State the non-goals in the README, as spec §9 says they are

spec §9's heading has read 'decisions, not omissions -- stated in the
README' since the roadmap was written, and the README has been
thirty-nine lines of affirmative claim. A non-goal a user discovers by
absence is indistinguishable from a gap, which is the thing that heading
was written to prevent.

Adds the six, in spec §9's order so the two can be diffed rather than
searched, each with an onward pointer. None links an issue: docs spec
§3.8 forbids the bare and hardcoded forms, this file is in that gate's
corpus, and Markdown has no role to write instead -- so the entries point
at pages and the pages carry the issue state.

Implements scope spec §3.1.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Dispose of the Doctest Residual and Split the Roadmap Row

Implements scope spec §3.5 and scope spec §3.6. Both touch spec §10, so they are one task — split across two, the second would rewrite the first's lines.

**Files:**
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md` (§8.2 task list, §8.7 `ci-docs` description, §10 lead sentence, §10 Plan 7b row, §10 item 15)
- Modify: `docs/src/developer/specs/2026-08-20-examples-gallery-design.md` (§7 open items)

**Interfaces:**
- Consumes: nothing.
- Produces: nothing later tasks use. Task 7 writes the changelog fragment that covers all of it.

- [ ] **Step 1: Correct §8.2's task list**

Find in §8.2:

```
- **Tasks** (pixi `[tool.pixi.feature.*.tasks]`): `tests` / `tests-clean`, `docs` (build),
  `serve-html`, `doctest`, `lint` (pre-commit run). Matplotlib image baselines are
  regenerated via a `baselines` task (pytest-mpl `--mpl-generate-path`); `tests-clean`
  removes pytest-mpl and coverage artifacts.
```

Replace with:

```
- **Tasks** (pixi `[tool.pixi.feature.*.tasks]`): `tests` / `tests-clean`, `docs` (build plus
  the gates that read its output), `docs-all`, `serve-html`, `lint` (pre-commit run).
  Matplotlib image baselines are regenerated via a `baselines` task (pytest-mpl
  `--mpl-generate-path`); `tests-clean` removes pytest-mpl and coverage artifacts. There is
  no `doctest` task: the snippet executor of docs spec §3.9 runs the documentation's python
  as an ordinary test module, which reaches every supported Python where a docs-build gate
  reaches one (scope spec §3.5).
```

- [ ] **Step 2: Correct §8.7's `ci-docs` description**

Find in §8.7:

```
  `ci-docs` (build + doctest), `ci-wheels` (build sdist/wheel, test in pixi envs, publish to
```

Replace with:

```
  `ci-docs` (build, then the four gates that read it — rendered citations, documentation
  links, published figures, browser demo), `ci-wheels` (build sdist/wheel, test in pixi envs, publish to
```

- [ ] **Step 3: Retag item 15**

Item 15's lead paragraph is line-wrapped, and the string `→ Plan 7b` occurs **twice** in it —
once for the doctest residual and once for the SPEC 0 statement. They get different
replacements, so match on the whole line, not on the fragment. A blind
`sed 's/→ Plan 7b/.../'` corrupts one of them.

The two lines to change, quoted exactly as they appear:

```
    `ci-docs` doctest run (§8.2/§8.7) → Plan 7b; `tests-clean` task (§8.2) → reconciled
```

becomes:

```
    `ci-docs` doctest run (§8.2/§8.7) → rejected in Plan 7b; `tests-clean` task (§8.2) → reconciled
```

and:

```
    statement → Plan 7b.
```

becomes:

```
    statement → delivered in Plan 7b.
```

That second one is the tail of `the §8.3 packaging-guide SPEC 0 docs` on the line above it.
Leave the `sphinx-tags (§8.6) → rejected in Plan 7a;` fragment on the first line alone.

Then in the per-deferral list, replace these two lines:

```
    - **Deferred** (Plan 7b — {issue}`76`): the `doctest` task and the `ci-docs` doctest run (§8.2/§8.7).
    - **Deferred** (Plan 7b — {issue}`76`): the §8.3 packaging-guide SPEC 0 statement.
```

with:

```
    - **Rejected** (2026-08-25, scope spec §3.5): the `doctest` task and the `ci-docs`
      doctest run (§8.2/§8.7) — superseded. docs spec §3.9's snippet executor already runs
      every python block in the three user quadrants as a page session, on every supported
      Python; `sphinx.ext.doctest` would rewrite each block as `testcode::` and maintain a
      second execution path in the one environment the docs feature has, for the same
      coverage. Its one advantage, output checking, applies only to the CLI transcripts,
      which `tests/test_cli.py` already pins. §8.2 and §8.7 are corrected accordingly.
    - **Resolved** (2026-08-25, scope spec §3.3): the §8.3 packaging-guide SPEC 0 statement,
      delivered in `docs/src/developer/packaging.rst`.
```

With that, item 15's own status tag can change too: its six residuals are now one **Rejected** (sphinx-tags), one **Rejected** (doctest), three **Resolved**, and one **Open** ({issue}`77`). Change the item's leading tag from:

```
15. **Deferred** (Plan 7b — {issue}`76`) — **Residual Plan 1 deferrals**, re-homed:
```

to:

```
15. **Open** ({issue}`77`) — **Residual Plan 1 deferrals**, re-homed. Five of the six are
    settled; the check-manifest gate is the one still open, and {issue}`76` closed with the
    other two of its trio:
```

- [ ] **Step 4: Split the Plan 7b row**

In §10's table, replace the single row:

```
| 7b | Documentation completion | §8.6: tutorials/how-tos/explanation content, glossary completion, `doctest` task + CI doctest run; README non-goals statement, the eccodes recipe and the reader how-to (§9, gallery spec §5); §8.3's SPEC 0 packaging statement (item 15) | 7a | **next** |
```

with these three:

```
| 7b | Scope and support statements | scope spec: the §9 README non-goals statement, the ecCodes recipe answering the first of them, the developer packaging guide carrying §8.3's SPEC 0 statement, the lapse rate entry closing §8.6's list, and the disposal of the `doctest` residual (item 15) | 7a | ✅ complete (PR {pull}`NNN`) |
| 8 | Framing by ranges and by data | {issue}`184`: `set_extent` keyword ranges in place of corner pairs, and `ax.fit(...)` for data-driven framing — before v0.1, while both are still free | 3 | **next** |
| 7c | Narrative quadrants | §8.6: tutorials (myst-nb) and explanation content, the glossary sweep around them, and the reader how-to (gallery spec §5) | 7b, 8 | after Plan 8 |
```

Substitute this pull request's own number for `NNN` in the 7b row when you open it — Task 7 revisits this.

Then add this paragraph immediately below the table, before "Cross-cutting rules":

```
Plan 7b's row was one row describing four unrelated deliverables, and {issue}`184` cuts
through it: that issue replaces `set_extent`'s corner pairs with keyword ranges and adds
`ax.fit(...)`, before v0.1, and the tutorials and explanation quadrants are where framing
gets taught. Measured on 2026-08-25, `set_extent` appeared in no page of the four user
quadrants — so writing them first would have multiplied that issue's migration into prose,
where a signature change is not a mechanical edit because the sentence around the call
explains the argument. The rows above therefore sit in execution order rather than in
numerical order, which §10's partial-order note already permits, and Plan 8 is numbered
rather than lettered because it is a plotting-layer change and not documentation completion.
scope spec §3.6 carries the full argument.
```

- [ ] **Step 5: Correct the count in §10's lead**

The first sentence of §10 reads `Seven plans deliver the v1 scope (§9).` Replace with:

```
Nine plans deliver the v1 scope (§9) — seven as first numbered, plus the two the Plan 7 row
split into and the framing change of {issue}`184` that landed between them.
```

- [ ] **Step 6: Retag gallery spec §7's open items**

In `docs/src/developer/specs/2026-08-20-examples-gallery-design.md` §7, replace:

```
- **Deferred** (7b — {issue}`76`) — **the doctest task and its `ci-docs` run, and
  spec §8.3's SPEC 0 packaging statement.** Two of the three residuals spec §10 item 15
  re-homed to Plan 7; the third, sphinx-tags, is rejected below.
```

with:

```
- **Resolved** (2026-08-25, scope spec §3.3 and scope spec §3.5) — **the doctest task and
  its `ci-docs` run, and spec §8.3's SPEC 0 packaging statement.** Plan 7b delivered the
  packaging statement and rejected the doctest task as superseded by docs spec §3.9's
  snippet executor. With sphinx-tags rejected below, all three of spec §10 item 15's
  re-homed residuals are settled and {issue}`76` is closed.
```

- [ ] **Step 6c: Correct one over-claim in the §9 prose Task 5 added**

Task 5 added a sentence below spec §9's non-goals heading saying the README carries them
"each with an onward pointer". Two of the six carry no link — the GUI entry and the
fog-point entry point at prose, not at a page. Replace:

```
`README.md` carries these as its **Non-Goals** section, in the order below and each with an
onward pointer (scope spec §3.1).
```

with:

```
`README.md` carries these as its **Non-Goals** section, in the order below, most of them
naming what to reach for instead (scope spec §3.1).
```

Found by the Task 5 review. It is one sentence in a published specification, and a
specification that overstates what a file contains is the defect this project corrects
rather than tolerates.

- [ ] **Step 6b: Re-point the two stale "7b" references the split leaves behind**

Splitting 7b into 7b and 7c makes two existing sentences wrong. Both say a question about
tagging the narrative documentation belongs to 7b; after the split the tutorials and
explanation quadrants are 7c's, so the question moves with them.

In `docs/src/developer/specs/2026-08-20-examples-gallery-design.md` §7, in the
**Rejected** sphinx-tags entry, replace:

```
  site-wide tag index spanning the narrative documentation — is a question for 7b, which
  owns the tutorials and explanation quadrants that would be tagged.
```

with:

```
  site-wide tag index spanning the narrative documentation — is a question for 7c, which
  owns the tutorials and explanation quadrants that would be tagged.
```

And in `docs/src/developer/specs/2026-07-22-tephpy-design.md` §10 item 15, in the
**Rejected** sphinx-tags entry, replace:

```
      narrative documentation are 7b's question.
```

with:

```
      narrative documentation are 7c's question.
```

Neither is a citation, so no gate catches these — they are stale cross-references that only
reading finds. Confirm both with:

```bash
grep -rn "7b's question\|question for 7b" docs/src/developer/specs/
```

Expected: no output.

and replace:

```
- **Deferred** (7b — {issue}`66`) — **the reader how-to and the eccodes recipe.** §5 sends
  the `io` example there, and {issue}`66`'s quadrant build-out is where it lands.
```

with:

```
- **Deferred** (7c — {issue}`66`) — **the reader how-to.** §5 sends the `io` example there.
  The eccodes recipe beside it landed in Plan 7b (scope spec §3.2); the reader how-to did
  not, because it is where `ax.fit(...)` would be taught and {issue}`184` has not landed
  yet (scope spec §3.6).
```

- [ ] **Step 7: Run the citation gate and the build**

```bash
python3 .github/scripts/check_citations.py
pixi run --frozen --environment docs docs
```

Expected: `citations ok`, then `build succeeded.` and three `ok` lines. Both specifications are published pages, so a citation you broke while editing fails here.

- [ ] **Step 8: Verify nothing still promises a doctest task**

```bash
grep -rn "doctest" docs/src/developer/specs/2026-07-22-tephpy-design.md
```

Expected: only the two new **Rejected** mentions and the §8.2 sentence that says there is no such task. No line should still read as a promise.

```bash
grep -rn "doctest" pyproject.toml .github/workflows/
```

Expected: no output. There was never a task or a step; this confirms none was added by accident.

- [ ] **Step 9: Run lint**

```bash
pixi run --frozen lint
```

- [ ] **Step 10: Commit, then close the issue**

```bash
git add docs/src/developer/specs/2026-07-22-tephpy-design.md \
        docs/src/developer/specs/2026-08-20-examples-gallery-design.md
git commit -m "Reject the doctest residual and split the Plan 7b row

spec §8.2 lists a doctest task and spec §8.7 describes ci-docs as
'build + doctest'. Both were written in Plan 1, before there was any
documentation to test, and both were overtaken: docs spec §3.9 rejected
sphinx.ext.doctest on the merits and shipped the snippet executor, which
runs every python block in the three user quadrants as a page session on
every supported Python -- where a docs-build gate reaches the one
environment the docs feature has. Its one advantage, output checking,
applies to the CLI transcripts alone, which tests/test_cli.py pins.

That is the same finding PR #181 made against sphinx-tags, and it closes
issue #76: all three of its residuals are now settled.

The row splits at the same time, because issue #184 cuts through it. That
issue replaces set_extent's corner pairs with keyword ranges before v0.1,
and set_extent appears in no page of the four user quadrants today -- so
the tutorials and explanation content the row also asks for is exactly
what would multiply its migration, into prose, which is the worst place
to migrate a signature.

Implements scope spec §3.5 and scope spec §3.6.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Then comment and close {issue}`76`:

```bash
gh issue comment 76 --body "All three residuals are now settled.

- **sphinx-tags** — rejected as superseded in #181. sphinx-gallery ships native tags with the index filter that was the reason to want them.
- **the \`doctest\` task and its \`ci-docs\` run** — rejected as superseded. docs spec §3.9 had already argued this in the section that chose the snippet executor: \`sphinx.ext.doctest\` would mean rewriting every \`code-block:: python\` as \`testcode::\` and maintaining a second execution path in the one environment the docs feature has, for the same coverage. The snippet gate is an ordinary test module, so it runs on every supported Python, and it already recognises bare \`>>>\` blocks. Output checking is doctest's real advantage and applies only to the CLI transcripts, which \`tests/test_cli.py\` pins. spec §8.2 and spec §8.7 are corrected to say what actually runs. Recorded in the scope and support statements design specification §3.5 and §6, and in spec §10 item 15.
- **the SPEC 0 packaging statement** — delivered in \`docs/src/developer/packaging.rst\`.

One question this raises is filed separately: docstring \`Examples\` sections are the one surface the snippet gate does not reach, and there are none today."

gh issue close 76
```

---

### Task 7: The Changelog Fragment, and Final Verification

One fragment covers the whole change (scope spec §4). This task also closes the loop on the two places that need this pull request's own number.

**Files:**
- Create: `changelog/<PR>.documentation.rst`
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md` (the `{pull}` number in the new Plan 7b row)

**Interfaces:**
- Consumes: the pull request number, which does not exist until you open the PR.
- Produces: nothing.

- [ ] **Step 1: Open the pull request**

```bash
git push -u origin scope-and-support
gh pr create --title "State what tephpy does not do, what it runs on, and what its words mean" --body "$(cat <<'BODY'
Plan 7b of the roadmap, less the half that waits behind #184.

Spec §9 has said since the roadmap was written that the non-goals are
"stated in the README". They were not. Spec §8.3 names five things that
enforce the SPEC 0 support window, and the fifth — a statement in the
developer packaging guide — had no guide to live in. Spec §8.6 enumerates
the terms that earn a glossary entry and every one had an entry except
lapse rate. And spec §8.2 and §8.7 promised a doctest task that later work
had already made redundant.

This is those four, plus the roadmap surgery that splits the row.

## What is here

- **README non-goals** — spec §9's six, in its order, each with an onward pointer.
- **The ecCodes recipe** — written along the seam it describes: the decode is
  ecCodes' and is a console transcript, the assembly is tephpy's and is python
  that the snippet gate executes on every supported Python.
- **The developer packaging guide** — the SPEC 0 window and which of its five
  enforcement points are assertions and which are mechanisms, the dependency-floor
  policy, what the distributions carry, and check-manifest's position (#77).
- **The lapse rate glossary entry** — closes #183, and with it spec §8.6's own list.
- **The doctest residual, rejected as superseded** — closes #76.

## What is not here

The tutorials and explanation quadrants and the reader how-to. They are Plan
7c, and they wait on #184: `set_extent` appears in no page of the four user
quadrants today, and those are the pages that would change that.

## Verification

`pixi run docs`, `pixi run tests` and `pixi run lint`, all green. No new CI
gate — which for the doctest item is the evidence rather than an omission.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_017fz9nNazC5nuiYk69iGL1k
BODY
)"
```

- [ ] **Step 2: Write the fragment**

Create `changelog/<PR>.documentation.rst` — this branch's is `changelog/191.documentation.rst`:

```rst
Stated the project's scope and support in the places a reader looks for them:
the six non-goals of the design specification now appear in ``README.md`` with
somewhere to go instead, a new how-to shows how to decode BUFR with ecCodes and
build a :class:`~tephpy.sounding.Sounding` from the result, a new developer
packaging guide carries the SPEC 0 support window and the dependency-floor
policy, and the glossary gained its lapse rate entry. The how-to also says where
a TEMP bulletin leaves you, ecCodes decoding no traditional code form and there
being no maintained converter to point at. (:user:`bjlittle`)
```

Replace `bjlittle` with your own GitHub username if you are not the maintainer.

- [ ] **Step 3: Fill in the roadmap row's PR number**

In `docs/src/developer/specs/2026-07-22-tephpy-design.md`, the Plan 7b row Task 6 added ends `✅ complete (PR {pull}`NNN`)`. Substitute the real number:

```bash
sed -i 's/✅ complete (PR {pull}`NNN`)/✅ complete (PR {pull}`191`)/' \
    docs/src/developer/specs/2026-07-22-tephpy-design.md
grep -n "NNN" docs/src/developer/specs/2026-07-22-tephpy-design.md
```

Expected: the grep prints nothing.

- [ ] **Step 3b: Fix the plan count in §10's lead sentence**

Task 6 wrote a sentence that does not add up. `docs/src/developer/specs/2026-07-22-tephpy-design.md`
currently opens §10 with:

```
Nine plans deliver the v1 scope (§9) — seven as first numbered, plus the two the Plan 7 row
split into and the framing change of {issue}`184` that landed between them.
```

Three additive clauses — seven, plus two, plus one — read as ten, not nine, and the table
does have ten rows. The arithmetic that is actually true is six first-numbered rows (Plans
1 to 6), the three the Plan 7 row split into (7a, 7b, 7c), and Plan 8. Replace the sentence
with:

```
Ten rows deliver the v1 scope (§9) — six as first numbered, the three the Plan 7 row split
into, and the framing change of {issue}`184` that landed between them.
```

Confirm the count against the table itself:

```bash
grep -cE '^\| [0-9]' docs/src/developer/specs/2026-07-22-tephpy-design.md
```

Expected: `10`.

This step does not need the pull request number, so it can be done before or after Step 3.

- [ ] **Step 4: Run everything**

```bash
pixi run --frozen tests
pixi run --frozen --environment docs docs
pixi run --frozen lint
```

Expected, and check each rather than skimming:

- `tests` — full suite passes; `tests/test_docs_snippets.py` runs the new page.
- `docs` — `build succeeded.`; `rendered citations ok`; `Documentation links ok: 13 checked across 2 sources`; `published figures ok: 13 compared within RMS 2, across 3 pages`.
- `lint` — every hook passes, including `design specification citations resolve` and `GitHub references are links`.

- [ ] **Step 5: Confirm the workflow gate is genuinely untouched**

```bash
git diff --stat main -- .github/workflows/ tests/test_docs_workflow.py pyproject.toml
```

Expected: no output. scope spec §2 decision 6 says nothing here adds a CI gate, and for scope spec §3.5 that is the evidence that the doctest residual was superseded rather than skipped. If this diff is non-empty, something in Task 6 went further than the plan.

- [ ] **Step 6: Commit and push**

```bash
git add changelog/ docs/src/developer/specs/2026-07-22-tephpy-design.md
git commit -m "Add the changelog fragment and cite this PR in the roadmap

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push
```

- [ ] **Step 7: Watch CI**

```bash
gh pr checks --watch
```

Expected: `ci-docs`, `ci-tests` across py312/py313/py314, `ci-changelog`, `ci-citation`, CodeQL, pre-commit.ci and the Read the Docs build all green.

---

## Self-Review Record

Run against the specification after the plan was written.

**Spec coverage.** Every section maps to a task: scope spec §3.1 → Task 5; §3.2 → Task 4; §3.3 → Task 2; §3.4 → Task 3; §3.5 → Task 6; §3.6 → Task 6; §4 companion changes → Tasks 2, 4, 5, 6, 7 between them, with the `specs/index.rst` row already committed ahead of the plan; §5 testing → the gate runs closing each task and Task 7 Step 4; §6's `NNN` placeholder → Task 1. No gap found.

**Placeholder scan.** Three deliberate substitutions remain, each with a step that performs it and a `grep` that proves it happened: the issue number in Task 1, the PR number in Task 7, and the ecCodes transcript in Task 4. The transcript is the only one that cannot be verified mechanically, which is why Task 4 Step 1 says outright not to invent it and gives an honest fallback.

**Type consistency.** The three membership tuples the recipe must join are named differently in the two files they live in — `DOCUMENTED` and `PUBLISHES_FIGURES` in `tests/test_docs_snippets.py`, `PUBLISHES` in `.github/scripts/check_docs_figures.py`. Task 4 Steps 4 and 5 give each its own step and its real name. The figure prefix `temp-and-bufr-sounding` is written identically in the page, the baseline filename and the expected gate output.
