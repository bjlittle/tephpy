# tephpy API visibility — design specification

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. The how-to pages it describes cite it by section — `visibility spec §3.3` and
> the like — so these sections *are* the reasoning behind what those pages say, and where
> the two ever diverge it is the specification that gets corrected. Read it as current.

- **Date:** 2026-08-29 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `visibility spec §…` — the subject is what a reader is *shown*, not
  what exists. `howtos spec` was rejected because §3.5 amends a tutorial too, and `api
  spec` because nothing here changes an API
- **Scope:** three new how-to pages, four amendments to existing user pages, and the
  registration each needs; no change to `src/tephpy/`
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) — §5 is the
  units policy §3.3 finally teaches, and §1 case 4 the vector-output promise §3.4 closes
- **Sibling spec:** [`2026-08-27-narrative-quadrants-design.md`](2026-08-27-narrative-quadrants-design.md)
  — narrative spec §3.6 built the one reader how-to; this specification covers the routes
  into a `Sounding` that do not come from a file
- **Tracked by:** {issue}`212`, which this specification answers except for its Tier 3

(visibility-spec-1)=
## 1. Purpose

An audit of the public API against the user quadrants ({issue}`212`) found capability that
every install pays for and no page advertises. The API reference documents all of it. That
is the distinction this specification is built on: the gap is not in what exists, it is in
what a reader is ever shown.

The counts were taken across `docs/src/{howtos,tutorials,explanation}`,
`src/tephpy/examples` and `README.md`, and re-checked on 2026-08-29 before this document
was written. Files mentioning each symbol:

| symbol | files | note |
|---|---|---|
| `Sounding.from_dataframe` | 0 | pandas is a hard runtime dependency |
| `Sounding.from_dataset` | 0 | xarray is a hard runtime dependency |
| `edge_axis` | 0 | the axis-label story |
| `labels=` edge option | 0 | the prerequisite for `edge_axis` |
| `mixing_ratios` accessor | 0 | against `isotherms` at 5 |
| `moist_adiabats` accessor | 0 | as above |
| `SoundingIndices` | 0 | the tutorial shows the panel, never that fields are readable |
| `samples.available()` | 0 | no documented way to discover sample names |
| `config.source`, `config.reset` | 0 | `load`, `save` and `context` appear once each |
| `units=` | 1 | spec §5 is an entire policy |
| "pint" | 1 | a comment in one gallery example |

Three of these are worse than a thin count.

- **`from_dataframe` and `from_dataset` are the largest gap.** `requirements/pypi-core.txt`
  pins `pandas>=2.3` and `xarray>=2024.10`, so every installed tephpy carries both. Most
  scientific Python users arrive holding a DataFrame, and the page they would check —
  *Read a Sounding From an Archive* — covers only files on disk.
- **Spec §5 is an entire units policy and a reader learns none of it.** Not that pint
  quantities go in directly, not that any pint-parseable unit is accepted, not that what
  comes back is pint on MetPy's registry.
- **Spec §1 case 4 promises "publication-quality (vector) output".** It appears in the
  corpus exactly once, as a commented-out line in `plot_sounding_comparison.py`.

(visibility-spec-2)=
## 2. Decisions

1. **Per theme, not one page.** The how-to quadrant's own index promises that "each page
   answers one question and stops there". A single grab-bag would make a reader holding a
   DataFrame scroll past unit conversion and PDF export to reach their answer, and its
   title could not say what it answers.
2. **Three new pages, not the four {issue}`212` proposed.** Vector output was measured
   before it was scoped (§5) and found to have nothing tephpy-specific to teach. It becomes
   the closing section of §3.4 rather than a page that would only say "call `savefig`".
3. **A tier-2 symbol goes to the page that already owns its subject, not to a new page.**
   `config.reset` belongs beside `config.load`; `samples.available()` belongs where
   `samples.path(...)` is already explained. Routing them to new pages would put two pages
   in the reader's way for one question, which is decision 1 read backwards.
4. **`edge_axis` is a documentation defect and not an API defect.** {issue}`212` suspected
   the `labels=` then `edge_axis` two-step might argue for an API change. It does not, and
   §3.6 records the measurement that settles it.
5. **No new sample files.** §3.2's page constructs its own DataFrame inline. A reader whose
   data is already in Python does not need tephpy to ship them a file, and the shipped
   samples exist to serve pages about acquisition.
6. **Tier 3 is not in scope.** The exception taxonomy is reference-quadrant material, and
   §7 files it rather than dropping it.

(visibility-spec-3)=
## 3. Architecture

(visibility-spec-3-1)=
### 3.1 The routing rule

Three new pages and four amendments. The rule that separates them: a **new page** is
warranted when the question has no existing owner and a reader would search for it by name;
an **amendment** is right when a page already answers the neighbouring question and the
symbol is the sentence it is missing.

| page | title | question |
|---|---|---|
| `howtos/build-a-sounding.rst` | *Build a Sounding From Your Own Data* | my data is already in Python |
| `howtos/units.rst` | *Work With Units* | what units does it want, and what do I get back |
| `howtos/label-and-compose.rst` | *Label and Compose the Diagram* | how do I title it, or put it beside something else |

(visibility-spec-3-2)=
### 3.2 *Build a Sounding From Your Own Data*

`docs/src/howtos/build-a-sounding.rst`. The reader holds a DataFrame or a Dataset and wants
a {class}`Sounding <tephpy.sounding.Sounding>`.

The arc is three escalating calls on the pandas side — column names that already match the
field names, names that need the keyword mapping (`pressure="p"`, `temperature="T"`,
`dewpoint="Td"`), and what happens when a required column is absent — then the xarray half,
then one figure proving the result plots like any other sounding.

**The page's substance is the asymmetry between the two constructors**, which is invisible
from their signatures and is why this page is worth more than its examples:

- `from_dataframe` reads bare arrays out of the columns. Nothing carries a unit, so the
  `units=` mapping is **required** for every field present.
- `from_dataset` reads each variable's `attrs["units"]` by the xarray/CF convention, and
  treats `units=` as the **override**. A CF-compliant Dataset needs no `units=` at all; a
  variable with neither raises {class}`TephpyUnitsError <tephpy.exceptions.TephpyUnitsError>`
  naming the field, the variable and the fix.

Both take `station=`, `time=` and `label=`, and both raise `KeyError` for a missing required
or explicitly mapped column, and `TypeError` for a mapping keyword that names no field.

The data is a ~10-level DataFrame built inline with literal arrays, its levels taken from
the shipped Camborne ascent so the atmosphere is real. Decision 5 explains why it is not a
file.

(visibility-spec-3-3)=
### 3.3 *Work With Units*

`docs/src/howtos/units.rst`. Spec §5's policy, taught in the order a reader is surprised by
it. Every statement below was executed on 2026-08-29 before it was written down, except
where a correction below says otherwise.

1. **Pint quantities go in directly, with no `units=` at all.**
   `Sounding(pressure=[1000., 900.] * units.hPa, ...)` is accepted as-is.
2. **Any pint-parseable unit is accepted, not a tephpy shortlist, and tephpy then works in
   it.** `units={"pressure": "inHg", "temperature": "degF"}` is accepted, and the field is
   *tagged* rather than converted: `sounding.pressure` reads back `[29.5 26.0] inch_Hg`,
   the magnitudes unchanged. Conversion is on demand — `.to("hPa")` gives 998.98 hPa and
   `.to("degC")` gives 20.0 °C. A sounding in those units plots and analyses without
   complaint, and derived quantities come back in tephpy's canonical units rather than the
   input's:
   `calc.parcel_path` on a degF *sounding* returns a degree_Celsius `Profile`. (The
   input is a `Sounding`; "profile" names what comes back, and §3.3's page was corrected
   for the same confusion.)

   **Corrected 2026-08-29, before the page shipped.** This section previously said the data
   was "stored converted, not merely tagged". That was false, and it was false because the
   check behind it called `.to()` and read the converted output as evidence about storage.
   Task 2's implementer caught it. The rule this cost is worth restating: a claim about what
   a value *is* must be checked by reading the value, not by reading a conversion of it.

   **Corrected again 2026-08-29, in final review, and restored once the bug behind it was
   fixed.** This section said the sounding "plots and analyses without complaint"; the
   "analyses" half was never executed and was false at the time, because `calc.parcel_path`
   raised `DimensionalityError` when pressure was `inHg` or `mmHg`. That was a `tephpy` bug
   rather than a design decision — three `dry_lapse` call sites passed a reference pressure
   in the sounding's own unit while the array beside it had been rebuilt in hPa — and it is
   fixed ({issue}`214`). The claim is restored, and is now pinned by a parametrised test over
   ten pressure units that requires the *answers* to agree rather than the calls to succeed.
   The episode is left recorded rather than tidied away: the false half survived because the
   sentence was written from the section's gist, and the narrower claim beside it
   (`parcel_path` returning degC) was true, which is what made the wider one look safe.
3. **What comes back is pint, on MetPy's registry.** So `.to("hPa")` works, and the
   quantities feed MetPy's own calc functions without conversion. `metpy.units.units` is an
   `ApplicationRegistry` proxy — a plain literal, because pint's inventory publishes
   {class}`pint.UnitRegistry` and {class}`pint.Quantity` and carries no
   `ApplicationRegistry` target — and the quantities sit on the {class}`pint.UnitRegistry`
   it wraps. The page states that consequence and does not invite the reader to test
   registry identity: comparing against `metpy.units.units` compares against the proxy and
   reports `False`, which is the misleading way to check a claim that is true.

The page closes on {class}`TephpyUnitsError <tephpy.exceptions.TephpyUnitsError>` — the one
member of the exception hierarchy whose subject *is* units. It is named, not tabulated:
the taxonomy is §7's, and a how-to that grew an exception table would have stopped
answering one question.

(visibility-spec-3-4)=
### 3.4 *Label and Compose the Diagram*

`docs/src/howtos/label-and-compose.rst`. Three sections, in the order a figure is finished.

**Labels.** `labels` defaults to `True`, which draws each family's labels inline along its
own isopleths. `labels="left"` *moves* them to that edge, and claiming an edge supplies its
axis title from `EDGE_AXIS_TITLES` — `ax.isobars(labels="left")` alone yields an axis
titled "Pressure (hPa)". {meth}`ax.edge_axis(...) <tephpy.plotting.axes.TephigramAxes.edge_axis>`
appears second, as the override it actually is, together with the fact that no edge is
claimed by default: a fresh tephigram carries no axis titles because no family has asked
for an edge.

**Composition.** The section that earns the page its length, and the finding that is not in
{issue}`212`. `TephigramAxes.clear` sets `aspect=1.0, adjustable="box"`, so a tephigram
placed with `fig.add_subplot(1, 2, 1, projection="tephigram")` shrinks inside its slot
while a plain neighbour fills its own, and the pair reads as a mistake. Two figures, before
and after; the remedy is `width_ratios` on the subplots, `layout="constrained"`, and
`set_box_aspect(1.0)` on the neighbour. `subplot_mosaic(..., per_subplot_kw=...)` is noted
as the second route to a mixed figure.

**Vector output.** Three sentences and no figure, per decision 2. `savefig(..., format=
"pdf")` and `.svg` are matplotlib's, they work, and the page says what was measured: an SVG
of a full ascent comes out as several hundred `<path>` elements and **zero** `<image>` —
nothing is rasterised — and the PDF is a real `%PDF-`. The path count is not quoted: it
tracks the isopleth intervals and the extent, so a figure drawn differently reports a
different number and a page naming one would be making a claim about a figure it is not
showing. `plot_sounding_comparison.py`'s commented-out
line is uncommented or removed in the same change, so the corpus stops half-saying it.

(visibility-spec-3-5)=
### 3.5 The four amendments

Each is a section or a sentence on a page that already answers the neighbouring question
(decision 3).

| page | symbol | where it lands |
|---|---|---|
| `howtos/read-a-sounding.rst` | `samples.available()` | the sentence already explaining that `samples.path(...)` is only how the page gets hold of a file |
| `howtos/emphasis.rst` | `mixing_ratios`, `moist_adiabats` | the page exercises `isotherms` and `isobars`; the missing claim is the shared core of §3.7, and the two places it does not hold |
| `howtos/configuration.rst` | `config.source`, `config.reset` | beside the existing `load` and `save` sections |
| `tutorials/analyse-a-sounding.rst` | `SoundingIndices` | `calc.indices(snd)` is currently passed straight into the panel; one sentence and a link that its fields are readable |

The tutorial amendment is deliberately one sentence. Narrative spec §3.1 constrains a
tutorial to state a fact and link rather than derive one, and "the object you just passed to
the panel has fields you can read" is a fact.

(visibility-spec-3-6)=
### 3.6 The `edge_axis` finding, and why it is not an API change

{issue}`212` reported the two-step as "a finding nobody would guess" and asked whether it
argued for an API change. Measured on 2026-08-29, it does not:

```python
ax.isobars(labels="left")
ax.edge_axis("left").get_label_text()   # 'Pressure (hPa)'
```

The title is already correct, supplied from `EDGE_AXIS_TITLES` when the family claims the
edge. `edge_axis` is needed only to *override* it, or to reach the stock matplotlib the
docstring already offers from the claim onwards. The one-step gets a reader a labelled
pressure axis, so what was missing was a page saying so.

What remains true is that {meth}`edge_axis <tephpy.plotting.axes.TephigramAxes.edge_axis>`
raises `ValueError` on an unclaimed edge, and that its message is currently the only place
the sequence is explained. §3.4 moves that explanation onto a page, which is the correct
home for it; the message stays as it is, because an error a reader meets at the prompt
should still teach.

(visibility-spec-3-7)=
### 3.7 What the five family accessors actually share

The `emphasis.rst` amendment of §3.5 rests on a claim that has to be stated precisely,
because the obvious version of it is wrong. Checked against the signatures on 2026-08-29,
all five accessors — `isotherms`, `isobars`, `dry_adiabats`, `moist_adiabats`,
`mixing_ratios` — share a core of seven keyword-only options: `values`, `color`,
`linewidth`, `alpha`, `labels`, `emphasis`, `visible`.

Two do not stop there, and this is the part a reader cannot guess:

- **`mixing_ratios` has no `interval`.** The other four take one. A mixing-ratio ladder is
  not evenly spaced, so there is no interval to name.
- **`moist_adiabats` adds `truncation`.** No other family has it.

"All five take the same options" is therefore the sentence the page must *not* write. The
amendment states the shared core, names both exceptions, and draws one figure using
`mixing_ratios` and `moist_adiabats` so the two least-shown families appear at least once
in the corpus.

(visibility-spec-4)=
## 4. Companion changes

- **`docs/src/howtos/index.rst`** — three toctree entries, and its opening paragraph
  extended to name the new questions. That paragraph currently enumerates the quadrant's
  subjects and would otherwise describe a smaller quadrant than the one it indexes.
- **`docs/src/developer/specs/index.rst`** — the `visibility spec §…` row and the toctree
  entry. A new specification declares a prefix unique across the collection.
- **`docs/baseline/`** — one approved PNG per published figure, named by the figure's
  `:filename-prefix:`.
- **`src/tephpy/examples/plot_sounding_comparison.py`** — the commented-out vector line,
  per §3.4.
- **`changelog/`** — one `<PR>.documentation.rst` fragment per pull request, ending with
  ``(:user:`bjlittle`)``.

(visibility-spec-5)=
## 5. Alternatives considered

- **A fourth page, *Save a Figure for Publication*** — {issue}`212`'s own table proposed it
  and its own note doubted it. Measuring settled the doubt: `savefig` is matplotlib's, and
  nothing tephpy-specific goes wrong — no rasterisation, no glyph loss, a real PDF. A page
  whose honest content is "this works" is a page a reader opens for nothing.
- **One page, *Beyond the Archives*, carrying all of it** — cheaper to write and cheaper to
  register, and rejected by decision 1. The title could not say what the page answers.
- **Absorbing every tier-2 symbol into the three new pages** — {issue}`212`'s table implies
  it. Rejected because it would leave `configuration.rst` still not mentioning
  `config.reset` while a *different* page did, which is worse than either page alone.
- **Round-tripping an existing `Sounding` through a DataFrame in §3.2** — gives a
  full-resolution figure for free, and is circular: a reader with their own data has no
  `Sounding` to start from, so the page would demonstrate its premise by assuming it away.
- **Reading the shipped Camborne CSV with `pandas.read_csv`** — real and full-resolution,
  and rejected because *Read a Sounding From an Archive* tells the reader to use
  `wyoming.parse` for exactly that file. The page would teach the worse route to the one
  file for which a better route is documented.
- **Changing `edge_axis` to claim an edge implicitly** — considered under §3.6 and rejected.
  A getter with a side effect that builds a secondary axes is a worse API than a raise, and
  the docstring's stated reason for the raise still holds.

(visibility-spec-6)=
## 6. Testing

No new test module. Every page here is carried by machinery that already exists, and the
work is to satisfy it rather than extend it.

- **docs spec §3.9's snippet gate** executes every python block on each new page, as one
  script per page, on every supported Python. The pages are written against it: no network,
  no file the reader must find, and every name a later block uses defined in an earlier one.
- **plots spec §3.1/§3.5** — the first plot directive on a page takes `:context: reset` and
  every later one `:context:`; each published figure declares a `:filename-prefix:` unique
  across the documentation, and `.github/scripts/check_docs_figures.py` compares the built
  image against its baseline.
- **The glossary gate** ({pull}`211`) — first mention of a glossary term per page carries
  `:term:`. Any term these pages reach for that has no entry is added in the same change,
  because the build is fail-on-warning.
- **`tests/test_docs_snippets.py`** discovers pages by directory, so the three new pages are
  collected without registration; `test_a_page_publishes_figures_or_it_does_not` and
  `test_a_figure_name_is_unique_across_the_documentation` are the two most likely to catch a
  mistake here.

(visibility-spec-7)=
## 7. Scope

**In scope.** {issue}`212`'s Tier 1 and Tier 2 in full: three new how-to pages, four
amendments, and the registration and baselines they need.

**Out of scope, and filed rather than dropped.** {issue}`212`'s Tier 3 — seven of the ten
public exception types appear on no user page: `TephpyError`, `TephpyUnitsError`,
`MissingDataError`, `ProfileTooShortError`, `TephpyValidationError`,
`NonMonotonicPressureError`, `DewpointExceedsTemperatureError`. Spec §6 designed the
hierarchy so a caller can catch precisely, and nothing tells a caller it exists. That is
reference-quadrant material, belonging beside the generated configuration options rather
than in a how-to, and it is tracked by {issue}`213`. §3.3 names `TephpyUnitsError` in passing; that
is the whole of this specification's contact with the taxonomy.

**Explicitly not changed.** Nothing under `src/tephpy/` except
`plot_sounding_comparison.py`'s commented line. §3.6 records why the one API change this
work might have argued for is not warranted.

(visibility-spec-8)=
## 8. Open items

- **Open** ({issue}`66`) — the developer and contributor guide. This specification closes
  the user-facing half of the how-to quadrant's coverage gap and leaves that untouched.
- **Open** ({issue}`206`) — prose that names a function makes an unchecked claim about it.
  Every page here names functions heavily, so the review question that issue asks for would
  apply to them; it is not a gate on this work.

(visibility-spec-9)=
## 9. References

- {issue}`212` — the audit this specification answers, with the method and the counts.
- Spec §1 case 4 (vector output). Spec §5 (the units policy). Spec §6 (the exception
  hierarchy). Spec §8.6 (the quadrants and the glossary audience).
- Narrative spec §3.1 (what a tutorial may and may not do). Narrative spec §3.6 (the
  reader how-to).
- Docs spec §3.9 (the snippet gate). Plots spec §3.1 and plots spec §3.5 (published
  figures).

Each citation above repeats its prefix rather than sharing one across a list. A bare
`§5` trailing `Spec §1` resolves against *this* document, which has a §5 of its own, so
the list would silently cite the wrong specification ({issue}`197`).
