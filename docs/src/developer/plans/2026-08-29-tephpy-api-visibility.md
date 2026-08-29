# API Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show readers the public API the documentation never advertises — the DataFrame and Dataset constructors, the units policy of spec §5, edge axis labels, figure composition and vector output — as three new how-to pages and four amendments, answering {issue}`212` Tiers 1 and 2.

**Architecture:** Documentation only. No change to `src/tephpy/` except one commented-out line in a gallery example. Three new pages go in `docs/src/howtos/`; four tier-2 symbols are routed to pages that already own their subject rather than to new pages. Every page is carried by machinery that already exists — the snippet gate, the figure gate, the citation gate and the glossary gate — so the work is to satisfy them, not to extend them.

**Tech Stack:** reStructuredText, Sphinx with `matplotlib.sphinxext.plot_directive`, MyST for the specifications, pandas, xarray, pint (via MetPy's registry), pytest, pixi for every task.

**Spec:** `docs/src/developer/specs/2026-08-29-api-visibility-design.md` (citation prefix `visibility spec §…`). Read it alongside this plan. Where the two disagree the specification is right and this plan is stale.

## Global Constraints

- **Changelog.** One `changelog/<PR>.documentation.rst` fragment per pull request, ending ``(:user:`bjlittle`)``. Cite the issue where the fragment describes what it reported: ``(:issue:`212`)``.
- **Specification citations** are plain text with a document prefix — `visibility spec §3.2`, `spec §5`, `docs spec §3.9`. **A bare `§N` means a section of the document you are writing in.** Never share one prefix across a list: a bare `§5` trailing `Spec §1` resolves against the wrong document, silently, whenever the current document also has a §5 ({issue}`197`). Verified by `.github/scripts/check_citations.py`.
- **A citation must never appear inside a section heading** (docs spec §3.7).
- **GitHub references** use ``:issue:`212``` in reStructuredText, `` {issue}`212` `` in the Markdown specifications. Never a bare `#212`, never a hardcoded URL.
- **Titles** use Chicago Manual of Style headline style (spec §8.6, `docs/src/developer/docs-style.rst`). Preserve literal case for API identifiers and for library names in their own casing (matplotlib, numpy, pandas, pint, xarray).
- **Glossary.** Cross-reference the *first* mention of a glossary term per page with `:term:`, in narrative prose only — never in titles, code blocks, or directive options. The build is fail-on-warning, so a `:term:` with no entry breaks it: a page reaching for a new term adds the entry in the same change. Verified by `.github/scripts/check_glossary_links.py`. Terms already defined include `tephigram`, `sounding`, `isopleth`, `isotherm`, `isobar`, `dry adiabat`, `moist adiabat`, `mixing ratio`, `radiosonde`, `parcel`, `potential temperature`.
- **API cross-references** use the matching Sphinx domain role — `:class:`, `:func:`, `:meth:`, `:mod:`, `:obj:` — with the accessor idiom as display text, e.g. ``:meth:`ax.edge_axis(...) <tephpy.plotting.axes.TephigramAxes.edge_axis>```. Third-party APIs resolve through intersphinx (matplotlib, metpy, numpy, pandas, pint, xarray). Reserve plain double-backtick literals for names with **no** documentation target — `ApplicationRegistry` is one, verified: pint's inventory publishes `pint.UnitRegistry` and `pint.Quantity` and nothing for it (visibility spec §3.3).
- **Page shape where figures are published** (plots spec §3.2): every python block on such a page is a `.. plot::`; the first carries `:context: reset`; later blocks carry `:context:` or `:context: close-figs`; a block whose picture adds nothing carries `:nofigs:` and **no** `:filename-prefix:`; every figure-producing block carries a `:filename-prefix:` unique across the whole documentation.
- **No network in any block.** Every python block is executed by the test suite on every supported Python and again at build time (docs spec §3.9). A block that reaches a remote archive fails for reasons that are not tephpy's.
- **No new sample files** (visibility spec decision 5). Pages that need data either construct it inline or use `tephpy.samples`.

**Working branch:** `docs/api-visibility-spec`, already created, already carrying the specification commit. Each task below is one pull request off it; do not branch again inside a task.

**Commands:**
- Full suite: `pixi run --frozen tests`
- Focused page run: `pixi run --frozen tests -- tests/test_docs_snippets.py -k "build-a-sounding" -v` (test ids are the page path, e.g. `test_the_page_runs[howtos/build-a-sounding.rst]`)
- Docs build plus the three gates: `pixi run --frozen --environment docs docs`
- Re-bless figure baselines from the build: `pixi run --frozen --environment docs docs-figures`
- Lint: `pixi run --frozen lint`

---

### Task 1: *Build a Sounding From Your Own Data*

Implements visibility spec §3.2, and the `samples.available()` row of §3.5. The largest gap in {issue}`212`: pandas and xarray are hard runtime dependencies (`requirements/pypi-core.txt` pins `pandas>=2.3` and `xarray>=2024.10`), and neither constructor is mentioned anywhere outside the generated API reference.

**Files:**
- Create: `docs/src/howtos/build-a-sounding.rst`
- Modify: `docs/src/howtos/index.rst` (toctree, and the opening paragraph that enumerates the quadrant's subjects)
- Modify: `docs/src/howtos/read-a-sounding.rst:33-34` (the `samples.path(...)` sentence)
- Create: `changelog/<PR>.documentation.rst`
- Create: `docs/baseline/build-a-sounding-plotted.png` (via `docs-figures`)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: the label `_howto-build-a-sounding`, referenced by Task 2's *Where to Go Next*. The figure prefix `build-a-sounding-plotted`, which must stay unique.

All five snippets below were executed against the working tree on 2026-08-29 and behave exactly as shown.

- [ ] **Step 1: Write the page**

Create `docs/src/howtos/build-a-sounding.rst`:

```rst
.. _howto-build-a-sounding:

Build a Sounding From Your Own Data
===================================

:doc:`read-a-sounding` covers the archives ``tephpy`` reads. This page covers
the other way in: your data is already in Python, in a
:class:`pandas.DataFrame` or an :class:`xarray.Dataset`, and you want a
:class:`Sounding <tephpy.sounding.Sounding>` out of it.

Both libraries are hard dependencies, so both routes are available in every
install with no extra to enable.

From a DataFrame
----------------

:meth:`Sounding.from_dataframe(...) <tephpy.sounding.Sounding.from_dataframe>`
reads bare arrays out of the columns. Nothing in a DataFrame carries a unit, so
the ``units=`` mapping is required for every field present:

.. plot::
    :context: reset
    :nofigs:

    import pandas as pd

    from tephpy import Sounding

    df = pd.DataFrame(
        {
            "pressure": [1000.0, 925.0, 850.0, 700.0, 607.0,
                         500.0, 400.0, 300.0, 250.0, 200.0],
            "temperature": [15.4, 15.4, 10.4, 4.4, -1.9,
                            -11.9, -22.1, -39.1, -47.9, -55.7],
            "dewpoint": [14.4, 2.4, 3.4, -17.6, -24.9,
                         -37.9, -43.1, -50.1, -57.9, -71.7],
        }
    )
    units = {"pressure": "hPa", "temperature": "degC", "dewpoint": "degC"}
    from_frame = Sounding.from_dataframe(df, units=units)

Ten levels of the Camborne ascent, enough to draw. Column names that already
match the field names need no mapping at all.

Naming Your Own Columns
-----------------------

When they do not match, name them. Each keyword is a *field*, and its value is
the *column*:

.. plot::
    :context:
    :nofigs:

    renamed = df.rename(
        columns={"pressure": "p", "temperature": "T", "dewpoint": "Td"}
    )
    from_renamed = Sounding.from_dataframe(
        renamed, units=units, pressure="p", temperature="T", dewpoint="Td"
    )

Note which name ``units`` is keyed by. It is the **field**, not the column, so
the same mapping serves both calls above. ``pressure`` and ``temperature`` are
required; a missing or mistyped column raises :class:`KeyError` naming both
names — mistype the ``renamed`` frame's temperature column above as
``"Temp"`` rather than ``"T"``, and it raises:

.. code-block:: text

    KeyError: "column 'Temp' (field 'temperature') is not in the DataFrame"

Any keyword that names no known field raises :class:`TypeError` instead,
naming the unknown field and the fields it does know. The catch-all
parameter that absorbs it is called ``column_map`` here, ``var_map`` on
:meth:`~tephpy.sounding.Sounding.from_dataset`:

.. code-block:: text

    TypeError: unknown field(s) ['bogus']; expected ['dewpoint', 'pressure',
    'temperature', 'wind_direction', 'wind_speed']

From a Dataset
--------------

:meth:`Sounding.from_dataset(...) <tephpy.sounding.Sounding.from_dataset>`
differs in one way worth knowing, because it is invisible from the signature.
An :class:`xarray.Dataset` *can* carry units, in each variable's
``attrs["units"]``, and the constructor reads them by that convention. Here
``units=`` is the override rather than the requirement, and a CF-compliant
dataset needs none:

.. plot::
    :context:
    :nofigs:

    import xarray as xr

    ds = xr.Dataset(
        {
            "temperature": (
                "level", df["temperature"].to_numpy(), {"units": "degC"}
            ),
            "dewpoint": (
                "level", df["dewpoint"].to_numpy(), {"units": "degC"}
            ),
        },
        coords={
            "level": ("level", df["pressure"].to_numpy(), {"units": "hPa"})
        },
    )
    from_dataset = Sounding.from_dataset(ds, pressure="level")

Coordinates count as variables, which is why ``pressure="level"`` reaches one.
A missing required or explicitly mapped variable raises :class:`KeyError`,
just as a missing column does for
:meth:`~tephpy.sounding.Sounding.from_dataframe`:

.. code-block:: text

    KeyError: "variable 'temperature' (field 'temperature') not in the Dataset"

A field with neither ``attrs["units"]`` nor a ``units=`` entry raises
:class:`TephpyUnitsError <tephpy.exceptions.TephpyUnitsError>`, and the message
carries the fix:

.. code-block:: text

    'temperature' (variable 'temperature') has no attrs['units'] and no
    override: add units={"temperature": "<unit>"}

Naming the Ascent
-----------------

Both constructors take ``station=``, ``time=`` and ``label=``. Give the first
two and the legend label derives, exactly as it does for a
:term:`sounding` read from an archive:

.. plot::
    :context:
    :nofigs:

    named = Sounding.from_dataframe(
        df,
        units=units,
        station="03808",
        time=pd.Timestamp("2026-07-21 12:00"),
    )

``time`` here is stricter than the readers of :doc:`read-a-sounding`, which
parse a string. This one wants a real timestamp —
:class:`pandas.Timestamp`, :class:`numpy.datetime64` or
:class:`datetime.datetime` — and a string raises :class:`TypeError`. ``label=``
overrides the derived text outright.

Plotted Like Any Other
----------------------

What comes out is a :class:`Sounding <tephpy.sounding.Sounding>`, and nothing
downstream can tell it was built rather than read:

.. plot::
    :context:
    :filename-prefix: build-a-sounding-plotted

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(named)
    ax.legend()

Where to Go Next
----------------

:ref:`howto-read-a-sounding` is the other route in, for data still in a file.
```

The unit strings above get a page of their own in Task 2, which adds the
forward reference to it. **Do not add it here** — a `:ref:` to a label that does
not exist yet breaks the fail-on-warning build, and this task must land green on
its own.

- [ ] **Step 2: Run the page through the snippet gate, and watch it fail on the missing label**

Run: `pixi run --frozen tests -- tests/test_docs_snippets.py -k "build-a-sounding" -v`

Expected: PASS. The page is discovered by directory, with no registration.

Then confirm the figure gate is red because no baseline exists yet:

Run: `pixi run --frozen --environment docs docs`
Expected: FAIL from `check_docs_figures.py`, reporting `build-a-sounding-plotted` as declared but having no baseline.

- [ ] **Step 3: Bless the baseline**

Run: `pixi run --frozen --environment docs docs-figures`

This writes `docs/baseline/build-a-sounding-plotted.png` from the build. Open it and confirm it shows a temperature and a dewpoint trace with a legend reading `03808 2026-07-21 12Z`. A blessed baseline is an approval, so look at it before you accept it.

- [ ] **Step 4: Register the page**

In `docs/src/howtos/index.rst`, add `build-a-sounding` to the toctree in alphabetical position (first, before `configuration`). Then extend the opening paragraph, which currently enumerates the quadrant's subjects and would otherwise describe a smaller quadrant than it indexes. Replace:

```rst
question and stops there: getting data in from an archive, or out of a format
``tephpy`` does not read; framing the view on the region you care about;
```

with:

```rst
question and stops there: getting data in from an archive, out of a format
``tephpy`` does not read, or straight out of a :class:`pandas.DataFrame`;
framing the view on the region you care about;
```

- [ ] **Step 5: Amend `read-a-sounding.rst` for `samples.available()`**

At `docs/src/howtos/read-a-sounding.rst:33-34`, replace:

```rst
For your own data, that path is wherever you downloaded the station file to.
``samples.path(...)`` is only how this page gets hold of one.
```

with:

```rst
For your own data, that path is wherever you downloaded the station file to.
``samples.path(...)`` is only how this page gets hold of one;
:func:`samples.available() <tephpy.samples.available>` lists the names it
accepts. If your data is already in Python rather than in a file,
:ref:`howto-build-a-sounding` is the page you want.
```

- [ ] **Step 6: Run the full gates**

Run: `pixi run --frozen tests`
Expected: PASS.

Run: `pixi run --frozen --environment docs docs`
Expected: PASS, **zero warnings**, and `published figures ok: 27 compared` — one more than the 26 before this task.

Run: `pixi run --frozen lint`
Expected: PASS, including the citation and glossary hooks.

- [ ] **Step 7: Changelog and commit**

Create `changelog/<PR>.documentation.rst`, substituting the real pull request number for `<PR>`:

```rst
Added :ref:`howto-build-a-sounding`, a how-to for the
:meth:`Sounding.from_dataframe <tephpy.sounding.Sounding.from_dataframe>` and
:meth:`Sounding.from_dataset <tephpy.sounding.Sounding.from_dataset>`
constructors, which the user documentation had never shown despite pandas and
xarray both being hard runtime dependencies (:issue:`212`). Also documented
:func:`samples.available() <tephpy.samples.available>` on
:ref:`howto-read-a-sounding`. (:user:`bjlittle`)
```

```bash
git add docs/src/howtos/build-a-sounding.rst docs/src/howtos/index.rst \
        docs/src/howtos/read-a-sounding.rst docs/baseline/build-a-sounding-plotted.png \
        changelog/
git commit -m "Show the reader holding a DataFrame the way in (#212)"
```

---

### Task 2: *Work With Units*

Implements visibility spec §3.3. Spec §5 is an entire units policy, and before this page `units=` appeared in one user file and "pint" in one gallery comment.

**Files:**
- Create: `docs/src/howtos/units.rst`
- Modify: `docs/src/howtos/index.rst` (toctree)
- Modify: `docs/src/howtos/build-a-sounding.rst` (*Where to Go Next*, the forward reference Task 1 left out)
- Create: `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: the label `_howto-build-a-sounding` from Task 1. This task must land after Task 1.
- Produces: the label `_howto-units`. Task 1 deliberately does **not** reference it — Step 4 below adds that reference back into Task 1's page, once the label exists.

Every numeric claim below was executed on 2026-08-29.

- [ ] **Step 1: Write the page**

Create `docs/src/howtos/units.rst`. **Every block is `.. plot::` with `:nofigs:` and no `:filename-prefix:`** — not `.. code-block:: python`. Both forms are legal for a page that renders nothing (`configuration.rst` uses `code-block`), and this page takes the stronger one: a `:nofigs:` plot is executed by the snippet gate *and* again by the documentation build, whereas a plain block runs only in the gate. This page's entire subject is that its claims about units are true, so it should be proved twice.

Checked against the gate before this plan was written: `figure_pages()` is every page carrying at least one `.. plot::`, and the per-block checks allow a page whose plots are all `:nofigs:` — `test_every_published_figure_is_named` requires a prefix only on a block *without* `:nofigs:`, and `test_a_suppressed_figure_is_not_also_named` requires that a `:nofigs:` block have *no* prefix. `PUBLISHES_FIGURES` is a subset assertion over pages that must yield plots, so a new page never needs adding to it.

```rst
.. _howto-units:

Work With Units
===============

``tephpy`` takes and returns pint quantities throughout (spec §5). Three things
follow, in the order they tend to surprise people.

Quantities Go In Directly
-------------------------

If your arrays already carry units, pass them and say nothing else. There is no
``units=`` argument in this call:

.. plot::
    :context: reset
    :nofigs:

    from metpy.units import units

    from tephpy import Sounding

    snd = Sounding(
        pressure=[1000.0, 925.0, 850.0, 700.0] * units.hPa,
        temperature=[15.4, 15.4, 10.4, 4.4] * units.degC,
        dewpoint=[14.4, 2.4, 3.4, -17.6] * units.degC,
    )

The ``units=`` mapping exists for the other case — bare arrays, which is what a
:class:`pandas.DataFrame` hands you. :ref:`howto-build-a-sounding` is that
route.

Any Unit pint Can Parse
-----------------------

``units=`` is not a shortlist ``tephpy`` maintains. It is handed to pint, so
anything pint parses in the right dimension is accepted, and the field is
stored in that unit rather than converted on the way in:

.. plot::
    :context:
    :nofigs:

    imperial = Sounding(
        pressure=[29.5, 26.0],
        temperature=[68.0, 60.0],
        units={"pressure": "inHg", "temperature": "degF"},
    )

The field is tagged, not rewritten: ``imperial.pressure`` reads back
``[29.5 26.0] inch_Hg``, the numbers you gave. That :term:`sounding` plots
exactly like any other, and where a calculation derives a new quantity it
comes back in ``tephpy``'s own units — ``calc.parcel_path`` on a °F sounding
returns a °C :term:`profile`.

.. note::

    Plotting works in any unit pint accepts. Analysis does not, yet:
    ``calc.parcel_path`` raises ``DimensionalityError`` when a sounding's
    pressure is in ``inHg`` or ``mmHg`` — every other pressure unit checked
    here (``hPa``, ``Pa``, ``kPa``, ``mbar``, ``bar``, ``atm``, ``psi``,
    ``torr``) works. This is a bug in ``tephpy``, not a design decision, and
    it is tracked as :issue:`214`.

What Comes Back Is pint
-----------------------

Every field is a :class:`pint.Quantity` on MetPy's registry, so conversion is a
method call:

.. plot::
    :context:
    :nofigs:

    hpa = imperial.pressure.to("hPa")
    celsius = imperial.temperature.to("degC")

Being on *MetPy's* registry is the part that matters downstream. Quantities out
of ``tephpy`` go straight into MetPy's own calculations with no conversion step
and no registry mismatch:

.. plot::
    :context:
    :nofigs:

    from metpy.calc import dewpoint_from_relative_humidity

    humid = dewpoint_from_relative_humidity(
        snd.temperature, [0.9, 0.8, 0.7, 0.6] * units.dimensionless
    )

Do not check this by comparing registries. ``metpy.units.units`` is an
``ApplicationRegistry`` proxy and the quantities sit on the
:class:`pint.UnitRegistry` it wraps, so an identity test reports ``False`` for a
claim that is true.

When the Units Are Wrong
------------------------

:class:`TephpyUnitsError <tephpy.exceptions.TephpyUnitsError>` covers the whole
of this subject — units missing, ambiguous, unparsable, or in the wrong
dimension. It subclasses
:class:`TephpyError <tephpy.exceptions.TephpyError>`, the root of ``tephpy``'s
hierarchy, so a caller who wants everything can catch that instead.

Where to Go Next
----------------

:ref:`howto-build-a-sounding` puts these units to work on data of your own.
```

- [ ] **Step 2: Run the page**

Run: `pixi run --frozen tests -- tests/test_docs_snippets.py -k "units" -v`
Expected: PASS for `test_the_page_runs[howtos/units.rst]`.

- [ ] **Step 3: Confirm the page declares no figure**

Run: `pixi run --frozen tests -- tests/test_docs_snippets.py -k "publishes_figures" -v`
Expected: PASS. `test_a_page_publishes_figures_or_it_does_not` is the check that a page with no `:filename-prefix:` also builds no figure; a `:nofigs:` block that forgot its option fails here.

- [ ] **Step 4: Register the page, and close the forward reference**

Add `units` to the `docs/src/howtos/index.rst` toctree, after `temp-and-bufr`. Extend the opening paragraph's list with `; what units it takes and what it hands back`.

Then add the reference Task 1 left out. In `docs/src/howtos/build-a-sounding.rst`, replace the *Where to Go Next* body:

```rst
:ref:`howto-read-a-sounding` is the other route in, for data still in a file.
```

with:

```rst
:ref:`howto-units` covers what those unit strings may say, and what you get
back. :ref:`howto-read-a-sounding` is the other route in, for data still in a
file.
```

- [ ] **Step 5: Run the full gates**

Run: `pixi run --frozen tests`, then `pixi run --frozen --environment docs docs`, then `pixi run --frozen lint`.
Expected: all PASS, zero warnings. The figure count stays at 27 — this page adds none.

- [ ] **Step 6: Changelog and commit**

```rst
Added :ref:`howto-units`, documenting the units policy of spec §5: pint
quantities are accepted directly, any pint-parseable unit string is accepted
and tagged in that unit rather than converted, and every field comes back as
a :class:`pint.Quantity` on MetPy's registry. Also notes that
``calc.parcel_path`` does not yet work for every accepted pressure unit —
raising ``DimensionalityError`` for ``inHg`` and ``mmHg`` — a ``tephpy`` bug
tracked as :issue:`214` (:issue:`212`). (:user:`bjlittle`)
```

```bash
git add docs/src/howtos/units.rst docs/src/howtos/index.rst \
        docs/src/howtos/build-a-sounding.rst changelog/
git commit -m "Say what units tephpy takes, and what it hands back (#212)"
```

---

### Task 3: *Label and Compose the Diagram*

Implements visibility spec §3.4 and §3.6. Carries the finding that is not in {issue}`212`: a tephigram placed beside a plain axes shrinks inside its slot.

**Files:**
- Create: `docs/src/howtos/label-and-compose.rst`
- Modify: `docs/src/howtos/index.rst` (toctree)
- Modify: `tests/test_docs_snippets.py` (`DOCUMENTED` ~line 50, `PUBLISHES_FIGURES` ~line 67)
- Modify: `.github/scripts/check_docs_figures.py` (`PUBLISHES` ~line 73)
- Modify: `src/tephpy/examples/plot_sounding_comparison.py` (the commented-out vector line)
- Create: `changelog/<PR>.documentation.rst`
- Create: `docs/baseline/label-and-compose-{labelled,naive,balanced}.png` (via `docs-figures`)

**Three registries name the pages, and a new figure-publishing page belongs in all three.**
Learned in Task 1, where the original file list omitted them: `PUBLISHES` in
`.github/scripts/check_docs_figures.py` is compared for *equality* by
`tests/test_docs_figures.py:708`, so omitting it turns the suite red; `DOCUMENTED` and
`PUBLISHES_FIGURES` in `tests/test_docs_snippets.py` are *subset* assertions, so omitting
them leaves the suite green while the new page goes unpinned by every page-shape check —
the silent gap those tuples' own docstrings warn about. Add the page to all three, in
alphabetical position. Task 4 needs none of this: it adds a figure to `emphasis.rst`, which
is already in all three.

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: the label `_howto-label-and-compose`. Three figure prefixes: `label-and-compose-labelled`, `label-and-compose-naive`, `label-and-compose-balanced`.

Verified on 2026-08-29: no edge is claimed by default (`ax._edge_owners` is empty on a fresh axes), and `ax.isobars(labels="left")` alone yields an axis whose `get_label_text()` is already `'Pressure (hPa)'`.

- [ ] **Step 1: Write the page**

Create `docs/src/howtos/label-and-compose.rst`:

```rst
.. _howto-label-and-compose:

Label and Compose the Diagram
=============================

A fresh :term:`tephigram` carries no axis titles, because no
:term:`isopleth` family has asked for an edge. This page claims one, then puts
the diagram beside something else, then writes it out.

Move the Labels to an Edge
--------------------------

Every family labels its own lines inline by default — that is ``labels=True``.
Naming an edge instead *moves* those labels there, and claiming an edge brings
its axis title with it:

.. plot::
    :context: reset
    :filename-prefix: label-and-compose-labelled

    import matplotlib.pyplot as plt

    import tephpy

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.isobars(labels="left")
    ax.isotherms(labels="bottom")

That is the whole gesture. The left axis is titled "Pressure (hPa)" and the
bottom "Temperature (°C)" with nothing further asked for, because a family that
claims an edge supplies that edge's title.

One family per edge. Asking for one another family already holds raises
:class:`TypeError`, naming the holder.

Retitle an Edge
---------------

:meth:`ax.edge_axis(...) <tephpy.plotting.axes.TephigramAxes.edge_axis>` is how
you reach a claimed edge to *override* what it says. It hands back a plain
:class:`matplotlib.axis.Axis`, so everything matplotlib offers applies:

.. plot::
    :context:
    :nofigs:

    ax.edge_axis("left").set_label_text("pressure (hPa)")

An edge nothing has claimed has no axis to hand back, and asking for one raises
:class:`ValueError` telling you to claim it first. That ordering is the point:
``labels=`` first, ``edge_axis`` second.

Beside Another Axes
-------------------

A tephigram holds a fixed aspect ratio, which is what keeps its geometry
honest. Put one in a subplot beside a plain axes and it shrinks inside its slot
while the neighbour fills its own:

.. plot::
    :context: close-figs
    :filename-prefix: label-and-compose-naive

    from tephpy import samples

    snd = samples.sounding("camborne-igra-12z")

    fig = plt.figure(figsize=(9.0, 4.5))
    ax = fig.add_subplot(1, 2, 1, projection="tephigram")
    ax.plot_sounding(snd)
    other = fig.add_subplot(1, 2, 2)
    other.plot(snd.temperature.magnitude, snd.pressure.magnitude)
    other.invert_yaxis()

Nothing is wrong, and the pair reads as though something is. Give the tephigram
the wider share of the figure, constrain the layout, and ask the neighbour for a
square box:

.. plot::
    :context: close-figs
    :filename-prefix: label-and-compose-balanced

    fig, (left, right) = plt.subplots(
        1, 2, figsize=(11.0, 5.0), width_ratios=(1.4, 1.0), layout="constrained"
    )
    left.remove()
    ax = fig.add_subplot(1, 2, 1, projection="tephigram")
    ax.plot_sounding(snd)
    ax.isobars(labels="left")
    ax.isotherms(labels="bottom")
    right.plot(snd.temperature.magnitude, snd.pressure.magnitude)
    right.invert_yaxis()
    right.set_box_aspect(1.0)

:func:`matplotlib.pyplot.subplot_mosaic` reaches the same place through
``per_subplot_kw={"a": {"projection": "tephigram"}}``, if you would rather name
your axes than count them.

Write It Out as Vector
----------------------

``savefig`` is matplotlib's and needs nothing from ``tephpy``:
``fig.savefig("sounding.pdf")`` and ``fig.savefig("sounding.svg")`` both
produce true vector output. Every line, label and shaded area comes out as
drawing instructions rather than pixels — an SVG of a full ascent carries
several hundred ``<path>`` elements and no embedded raster at all — so the
figure survives whatever a publisher scales it to.
```

- [ ] **Step 2: Run the page**

Run: `pixi run --frozen tests -- tests/test_docs_snippets.py -k "label-and-compose" -v`
Expected: PASS.

- [ ] **Step 3: Build, then bless the three baselines**

Register the page in `docs/src/howtos/index.rst` first — the fail-on-warning build rejects an unregistered page ("not included in any toctree") before pixi's task graph ever reaches the figure gates, so Step 4's toctree edit has to precede this build. Then:

Run: `pixi run --frozen --environment docs docs`
Expected: FAIL, three declared figures with no baseline.

Run: `pixi run --frozen --environment docs docs-figures`

Then **look at all three**. `label-and-compose-naive` must actually show the defect the prose claims — a visibly smaller tephigram beside a full-height plain axes — and `label-and-compose-balanced` must show it resolved. A baseline that does not show what its paragraph says is the failure the figure gate exists to prevent, and only a human eye catches it here.

- [ ] **Step 4: Register the page**

Add `label-and-compose` to the `docs/src/howtos/index.rst` toctree, after `framing`. Extend the opening paragraph's list with `; labelling its edges and setting it beside another figure`.

- [ ] **Step 5: Uncomment the vector line in the gallery example**

In `src/tephpy/examples/plot_sounding_comparison.py`, the commented-out `savefig` line is the corpus's only mention of vector output (visibility spec §3.4). Delete it. The subject now has a documented home, and a commented-out line is the half-statement this task exists to end. Check the surrounding docstring does not reference it before deleting.

- [ ] **Step 6: Run the full gates**

Run: `pixi run --frozen tests`, then `pixi run --frozen --environment docs docs`, then `pixi run --frozen lint`.
Expected: all PASS, zero warnings, `published figures ok: 30 compared` — three more than Task 1 left.

- [ ] **Step 7: Changelog and commit**

```rst
Added :ref:`howto-label-and-compose`, covering the ``labels=`` edge option and
:meth:`ax.edge_axis(...) <tephpy.plotting.axes.TephigramAxes.edge_axis>`,
setting a tephigram beside another axes without it shrinking in its slot, and
vector output for publication (:issue:`212`). (:user:`bjlittle`)
```

```bash
git add docs/src/howtos/label-and-compose.rst docs/src/howtos/index.rst \
        src/tephpy/examples/plot_sounding_comparison.py docs/baseline/ changelog/
git commit -m "Title the axes, place the diagram, ship it as vector (#212)"
```

---

### Task 4: What the Five Family Accessors Share

Implements visibility spec §3.7 and the `emphasis.rst` row of §3.5. `mixing_ratios` and `moist_adiabats` are the two families named in no user page.

**Files:**
- Modify: `docs/src/howtos/emphasis.rst` (after *Every Family, Every Tier*, ~line 105)
- Create: `changelog/<PR>.documentation.rst`
- Create: `docs/baseline/emphasis-least-shown.png` (via `docs-figures`)

**Interfaces:**
- Consumes: nothing.
- Produces: the figure prefix `emphasis-least-shown`.

**The claim this task must not make.** "All five accessors take the same options" is false, and checking it against one family is how it would get written anyway. Verified against the signatures on 2026-08-29: the shared core is seven keyword-only options — `values`, `color`, `linewidth`, `alpha`, `labels`, `emphasis`, `visible` — and two families depart from it. `mixing_ratios` has **no** `interval`, because its ladder is `(0.05, 0.1, 0.2, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 14.0, 20.0, 28.0, 40.0)` and unequally spaced throughout, so there is no interval to name. `moist_adiabats` adds `truncation`, which no other family has.

The page's existing sentence "The option is the same on all five families" is about `emphasis` specifically, which *is* in the shared core. Leave it: it is true as written.

- [ ] **Step 1: Add the section**

In `docs/src/howtos/emphasis.rst`, after the *Every Family, Every Tier* section and before *Configure It Once*, insert:

```rst
The Two Least-Shown Families
----------------------------

:meth:`ax.mixing_ratios(...) <tephpy.plotting.axes.TephigramAxes.mixing_ratios>`
and
:meth:`ax.moist_adiabats(...) <tephpy.plotting.axes.TephigramAxes.moist_adiabats>`
answer to the same seven options every family does — ``values``, ``color``,
``linewidth``, ``alpha``, ``labels``, ``emphasis`` and ``visible``:

.. plot::
    :context: close-figs
    :filename-prefix: emphasis-least-shown

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.mixing_ratios(emphasis={4.0: {"color": "tab:green", "linewidth": 2.0}})
    ax.moist_adiabats(emphasis={20.0: {"color": "tab:red", "linewidth": 2.0}})

Beyond those seven the families are not interchangeable, and the two
differences are worth knowing before you go looking for an option that is not
there:

``mixing_ratios`` takes no ``interval``
    The other four do. A :term:`mixing ratio` ladder runs
    ``0.05, 0.1, 0.2, 0.5, 1, 1.5, 2, 3, 4, 5, 7, 10, 14, 20, 28, 40``
    g kg⁻¹ — wider apart the higher it climbs — so there is no single interval
    to name. Give ``values`` instead.

``moist_adiabats`` takes a ``truncation``
    No other family has one, and it is a *temperature* rather than a pressure:
    the value in °C below which the curves stop being drawn, because below it
    they have converged onto the dry adiabats. It defaults to −50 °C, the Met
    Office's own convention.

    **Corrected during implementation.** This paragraph said "the pressure
    below which". `MOIST_ADIABAT_TRUNCATION` is `-50.0` °C and the accessor's
    own docstring reads "Temperature (°C) below which the curves are
    truncated". Written from the option's name rather than from its
    definition.
```

- [ ] **Step 2: Run the page**

Run: `pixi run --frozen tests -- tests/test_docs_snippets.py -k "emphasis" -v`
Expected: PASS.

- [ ] **Step 3: Build and bless**

Run: `pixi run --frozen --environment docs docs` — expect the missing-baseline failure — then `pixi run --frozen --environment docs docs-figures`, then look at `emphasis-least-shown.png` and confirm one green mixing-ratio line and one red moist adiabat stand out from their families.

- [ ] **Step 4: Run the full gates**

Run: `pixi run --frozen tests`, then `pixi run --frozen --environment docs docs`, then `pixi run --frozen lint`.
Expected: all PASS, zero warnings, `published figures ok: 31 compared`.

- [ ] **Step 5: Changelog and commit**

```rst
Documented the two isopleth families no user page had shown, and the two places
the family accessors stop being interchangeable: ``mixing_ratios`` takes no
``interval`` and ``moist_adiabats`` takes a ``truncation`` (:issue:`212`).
(:user:`bjlittle`)
```

```bash
git add docs/src/howtos/emphasis.rst docs/baseline/emphasis-least-shown.png changelog/
git commit -m "Show the two families no page had drawn (#212)"
```

---

### Task 5: The Configuration and Indices Amendments

Implements the remaining two rows of visibility spec §3.5. Both are small and neither publishes a figure.

**Files:**
- Modify: `docs/src/howtos/configuration.rst` (after *Saving From Python*, ~line 212)
- Modify: `docs/src/tutorials/analyse-a-sounding.rst` (the *Put the Numbers On* prose, ~line 98)
- Create: `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing later tasks rely on.

Verified 2026-08-29: `config.source` is a property returning `pathlib.Path | None`, `None` when no file was found, none was loaded, or the load failed. `config.reset()` restores every option in every section to `None`. `tephpy.calc.SoundingIndices` is a dataclass exported from `tephpy.calc.__all__` with ten fields: `cape`, `cin`, `lcl_pressure`, `lcl_temperature`, `lfc_pressure`, `lfc_temperature`, `el_pressure`, `el_temperature`, `theta_w`, `lifted_index`.

**`source` has no cross-reference target, and `reset` does.** Checked against `docs/_build/html/objects.inv`: `tephpy.config` publishes `context`, `load`, `reset` and `save` as `py:method`, plus every section attribute such as `tephpy.config.moist_adiabats.truncation` — and nothing for `source`. So ``:meth:`tephpy.config.reset` `` resolves and ``:attr:`tephpy.config.source` `` would break the fail-on-warning build. Write `source` as a plain double-backtick literal, which is what `docs-style.rst` prescribes for a name with no documentation target. That the property is absent from the generated reference at all is a separate defect; note it on the pull request rather than fixing it here, because widening a generated reference is not this plan's scope.

- [ ] **Step 1: Amend `configuration.rst`**

Append after the *Saving From Python* section:

```rst
Which File Is In Force
----------------------

``tephpy.config.source`` names the file the current configuration came
from, as a :class:`pathlib.Path`. It is ``None`` when no file was found, when
none was loaded, and when a load failed — so it answers "did my file take
effect?" without guessing from the options:

.. code-block:: python

    import tephpy

    tephpy.config.load()
    print(tephpy.config.source)

Back to the Defaults
--------------------

:meth:`tephpy.config.reset` puts every option in every section back to ``None``,
falling through to the shipped conventions, and clears
``tephpy.config.source`` with them:

.. code-block:: python

    tephpy.config.reset()

Reach for it in a notebook that has drifted, or between tests. Remember that a
family reads the configuration when its axes is created, so a ``reset`` applies
to diagrams you draw after it, not to one already on screen.
```

- [ ] **Step 2: Amend `analyse-a-sounding.rst`**

The tutorial passes `calc.indices(snd)` straight into the panel and never says the result is readable. Narrative spec §3.1 lets a tutorial state a fact and link, so this is one sentence. After the paragraph beginning "The panel names the two shaded areas", add:

```rst
That panel is a rendering of an object you can read yourself.
:func:`calc.indices(...) <tephpy.calc.indices>` returns a
:class:`SoundingIndices <tephpy.calc.SoundingIndices>`, whose ten fields —
``cape``, ``cin``, the pressure and temperature of each of the three levels,
``theta_w`` and ``lifted_index`` — are pint quantities you can pull out and use
like any other number.
```

- [ ] **Step 3: Run the pages**

Run: `pixi run --frozen tests -- tests/test_docs_snippets.py -k "configuration or analyse-a-sounding" -v`
Expected: PASS. Note that the `configuration.rst` additions are `.. code-block::` rather than `.. plot::`, matching the sections above them — the snippet gate does not execute those, and `tephpy.config.load()` reading a user's real file is why that page uses them.

- [ ] **Step 4: Run the full gates**

Run: `pixi run --frozen tests`, then `pixi run --frozen --environment docs docs`, then `pixi run --frozen lint`.
Expected: all PASS, zero warnings, figure count unchanged at 31.

- [ ] **Step 5: Changelog and commit**

```rst
Documented ``tephpy.config.source`` and :meth:`tephpy.config.reset` on
:ref:`configure-from-a-file`, and said in :ref:`tutorial-analyse-a-sounding`
that :func:`calc.indices(...) <tephpy.calc.indices>` returns a readable
:class:`SoundingIndices <tephpy.calc.SoundingIndices>` rather than only a panel
(:issue:`212`). (:user:`bjlittle`)
```

```bash
git add docs/src/howtos/configuration.rst docs/src/tutorials/analyse-a-sounding.rst changelog/
git commit -m "Name the file in force, and the indices you can read (#212)"
```

---

## After the Plan

Close {issue}`212` on the last merge, noting that its Tier 3 moved to {issue}`213` rather than being dropped (visibility spec §7). That issue covers the exception-taxonomy table in the reference quadrant: the seven public types no user page names, the two-level shape that makes `except TephpyError` and `except TephpyValidationError` useful, and the fact that `TephpyConfigWarning` subclasses `UserWarning` and sits outside the hierarchy entirely.
