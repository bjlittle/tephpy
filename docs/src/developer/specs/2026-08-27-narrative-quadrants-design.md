# tephpy narrative quadrants — design specification

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. The tutorial, explanation and how-to pages it describes cite it by section —
> `narrative spec §3.2` and the like — so these sections *are* the reasoning behind what
> those pages say, and where the two ever diverge it is the specification that gets
> corrected. Read it as current.

- **Date:** 2026-08-27 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `narrative spec §…` — not `docs spec`, which is taken by the
  specification governing how the documentation is *built and checked*, nor `tutorials
  spec`, which would read as covering one quadrant when the point of this document is that
  three of them are written together
- **Scope:** the two tutorials, the two explanation pages they pair with, the reader how-to
  for the supported routes into a `Sounding`, and the glossary sweep around all five
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) — delivers
  spec §10's Plan 7c row, the last row before release execution
- **Sibling spec:** [`2026-08-03-published-specs-design.md`](2026-08-03-published-specs-design.md)
  — docs spec §3.9's snippet gate is what every page here is written against, and §3.6
  below is what happens when a page cannot satisfy it

(narrative-spec-1)=
## 1. Purpose

Four quadrants were built as directories in Plan 1 and two of them are still nearly empty.
`tutorials/` holds a browser demo carrying no python at all, and `explanation/` holds five
lines of prose promising that background "will appear here as the package grows". The other
two are populated: the reference quadrant generates itself, and the how-to quadrant has five
pages, four of them about an option and one about a file format.

What the package does is documented three times over — a gallery of five examples, a
generated API reference, those five how-tos — and every one of them is written for somebody
who already knows what a tephigram is. Spec §8.6's glossary rules name the audience plainly:
scientific software engineers, not meteorologists. For that reader the package currently
offers no way in. There is nothing to follow start to finish, and nothing that explains
why the axes are at 45° rather than saying that they are.

That is the gap Diátaxis exists to name. A how-to serves someone who knows what they want;
a tutorial serves someone who does not yet know what is possible, and an explanation serves
someone who has made it work and wants to know why. tephpy has the first and neither of the
others.

Three obligations converge here, and one constraint arrives with them:

- **spec §8.6** enumerates the explanation quadrant's content — "tephigram theory, the
  T–ln θ construction, parcel/Normand's-point derivations" — and nothing has been written.
- **gallery spec §5** ruled that an `io` example does not belong in the gallery and sent the
  subject to a how-to, which this plan owns. §3.6 records that the relocation moved the
  problem rather than solving it.
- **gallery spec §7** deferred the site-wide tag index to this plan, as the one that would
  own the pages it would span. §3.8 closes it.
- **docs spec §3.9** executes every python block in these three quadrants, as one script per
  page, on every supported Python. That is not a hurdle to clear but the reason this
  documentation can be trusted, and it shapes every page below.

(narrative-spec-2)=
## 2. Decisions

1. **The quadrants are written in pairs, not in sequence.** Each tutorial has exactly one
   explanation page to send a curious reader to, and each explanation page exists because a
   tutorial raises the question it answers. A tutorial that stops to explain becomes a
   lecture; an explanation with no tutorial behind it is a document nobody arrives at.
2. **Two tutorials, not one and not three.** Diátaxis wants a tutorial a reader can finish.
   One page carrying the whole arc from empty axes to a full analysis is too long for a
   sitting; splitting the first into "the diagram" and "a sounding on it" leaves an
   opening page with no data on it, which is the least motivating way to meet a diagram.
3. **Every page is reStructuredText.** Settled by {issue}`198` and spec §8.6 as corrected:
   nothing executes a notebook, and the tutorial quadrant is the one whose reader is least
   able to tell a broken snippet from their own mistake.
4. **The explanation quadrant is where the bibliography earns its place.** A convention this
   package renders is taken from a chart somebody printed, and the reader is entitled to the
   edition rather than to a sentence saying somebody checked. The machinery landed with
   {pull}`201`; this is the work that uses it.
5. **The reader how-to shows one runnable route and says so.** {issue}`202` is unresolved,
   so the Wyoming half cannot execute. §3.6 records why, and the page states the asymmetry
   rather than letting it read as an oversight.
6. **No doctested `Examples` sections, and no site-wide tag index.** Both were live
   questions this plan inherited; §3.8 closes both, and neither is a deferral.

(narrative-spec-3)=
## 3. Architecture

(narrative-spec-3-1)=
### 3.1 The pairing

Five pages, four of them in two pairs:

| tutorial | the question it raises | explanation |
|---|---|---|
| *Your First Tephigram* | why is the grid rotated, and where did the pressure axis go | *Why the Axes Are Rotated* |
| *Analyse a Sounding* | why is CAPE an area rather than a number I could have summed | *Parcel Ascent and Normand's Point* |

The reader how-to stands outside the pairing. Its subject is getting data in, which is not
something a tutorial teaches — a tutorial hands the reader data so the lesson can be about
the diagram — and not something that needs an explanation page, because there is nothing
conceptual about a file format that a reader of this package needs.

The pairing is a constraint on both halves. A tutorial may state a fact and link; it may not
derive one. An explanation page may derive freely and shows figures only where a picture
*is* the argument; it never teaches an API.

(narrative-spec-3-2)=
### 3.2 *Your First Tephigram*

`docs/src/tutorials/first-tephigram.rst`. The reader has installed the package and knows no
meteorology. They finish with a tephigram carrying a real ascent, and the vocabulary to say
what is on it.

The arc: an empty diagram; what its five isopleth families are; a
{func}`samples.sounding <tephpy.samples.sounding>` ascent drawn on it; reading the temperature and dewpoint traces
apart; and the freezing level, which is on the diagram already because spec §3.2 emphasises
the 0 °C isotherm by default ({pull}`201`). That last is the page's best moment and it costs
nothing to write: the reader is told what the heavier line is, having already seen it.

The data is `tephpy.samples`, not a file the reader must find. A tutorial that opens with an
acquisition problem has failed before it begins, and the reader how-to of §3.6 is where
acquisition belongs.

(narrative-spec-3-3)=
### 3.3 *Analyse a Sounding*

`docs/src/tutorials/analyse-a-sounding.rst`. Continues from the same sample, so the reader
who did §3.2 is on familiar ground and the reader who did not loses one code block.

The arc: a parcel lifted from the surface; Normand's point and the LCL falling out of the
construction rather than being computed separately; the CAPE and CIN areas shaded; and the
indices panel. It ends where the gallery's parcel-analysis example begins, which is the
handover: the tutorial is how it is built, the gallery is what it looks like finished.

(narrative-spec-3-4)=
### 3.4 *Why the Axes Are Rotated*

`docs/src/explanation/rotated-axes.rst`. Answers §3.2's question and covers the first two
items of spec §8.6's list, which are one argument rather than two: temperature against
entropy, why that pair makes isotherms and dry adiabats exactly perpendicular, why the
diagram is then rotated 45° so pressure runs roughly up the page, and why pressure is a
derived curve rather than an axis.

It is the page that cites. Met Office Factsheet 13 is the source for the isotherm interval,
the 0 °C convention and the printed chart's layout, and it is cited through the bibliography
{pull}`201` built rather than linked inline.

Figures only where the picture is the argument — the rotation itself, and pressure's
curvature. This page is prose that happens to have diagrams, not a gallery entry with
captions.

(narrative-spec-3-5)=
### 3.5 *Parcel Ascent and Normand's Point*

`docs/src/explanation/parcel-ascent.rst`. Answers §3.3's question and covers the third item
of spec §8.6's list: a parcel lifted dry-adiabatically, the mixing-ratio line from its
dewpoint, their intersection at Normand's point, saturated ascent above it, and why the
areas between the parcel and the environment curves are energies — which is what makes CAPE
an area on this diagram and a number in a table anywhere else.

It states where the arithmetic happens. Spec §3.3 delegates the thermodynamics to MetPy, and
a reader deciding whether to trust a CAPE value needs to know that tephpy draws it and MetPy
computes it. The −25 mb operational correction of spec §1 is named here as a convention with
a reason, not a magic number.

(narrative-spec-3-6)=
### 3.6 The reader how-to, and the route it cannot run

`docs/src/howtos/read-a-sounding.rst`. The two supported routes into a `Sounding`:
{func}`igra.read <tephpy.io.igra.read>` and {func}`wyoming.fetch <tephpy.io.wyoming.fetch>`.

**One of them executes and the other cannot.** docs spec §3.9 runs every python block in
this quadrant, and spec §8.5 forbids live network in CI. `igra.read` reads the file
`tephpy.samples` ships, so it runs. `wyoming.fetch` opens a URL, so it cannot. {pull}`203`
made `wyoming.parse` public, which reaches the format offline — but a block that parses
needs a body to parse, and no Wyoming body ships. Whether one may is {issue}`202`, which
turns on a redistribution question the University of Wyoming publishes no answer to.

**This is not a new constraint but a relocated one.** gallery spec §5 rejected an `io`
gallery example partly because "spec §7 forbids live network in CI while sphinx-gallery
executes examples during the build", and sent the subject here. The how-to quadrant executes
python under the same rule, so the move changed which gate applies and nothing else.

**The page states the asymmetry.** It shows `igra.read` as a running block ending in a
drawn sounding, and presents the Wyoming route as prose naming `fetch` and `parse` by role,
with the reason the call is not shown as a block — the same idiom the ecCodes recipe uses
for the same function (scope spec §3.2). What it does not do is present the two routes as
though equally demonstrated. A page that shows one of two things and implies both is the
quantifier defect docs-style's *Reviewing Claims* was written for ({issue}`193`).

If {issue}`202` resolves in favour of shipping, this section is superseded and the page
gains a second running block. That is a change to this specification, not a defect in it.

(narrative-spec-3-7)=
### 3.7 The glossary sweep

The build is fail-on-warning, so a `:term:` whose entry does not exist breaks it — which
makes the sweep a constraint on each page rather than a task after them. A page that reaches
for a new term seeds the entry in the same change, per docs-style's glossary rule.

The glossary already covers the meteorology of the diagram. What the explanation pages
will want and what is not there is the vocabulary of the *construction* — entropy, and the terms §3.4 and §3.5 need to say why the
coordinates are what they are. Those are seeded with the pages that use them; this
specification deliberately does not enumerate them in advance, because a list written before
the prose is a list that will be wrong, and {issue}`94` records what happens to counts
recorded in a specification.

(narrative-spec-3-8)=
### 3.8 Two questions closed

**No doctested `Examples` sections** ({issue}`189`). Most of the public surface returns
matplotlib artists or draws onto an `Axes`, so what a doctest would assert is often nothing;
`--doctest-modules` over `src/` is a second execution path beside the snippet gate, which
docs spec §3.9 already runs over every documented sequence; and the worked sequences are
exactly what this plan writes. A docstring cross-references the tutorial or how-to that
shows the call in context. The blocker {issue}`189` recorded — a collision with
{issue}`184`'s `set_extent` signature — cleared with {pull}`194`, so this is a decision on
the merits rather than a deferral repeated.

**No site-wide tag index** (gallery spec §7). After this plan the narrative corpus is about
eleven pages across three quadrants, each with a landing page and a toctree. A tag index is
navigation for a corpus too large to browse, and eleven pages is not one. sphinx-gallery's
own tags continue to serve the gallery, which is the surface that has enough entries to need
filtering.

(narrative-spec-4)=
## 4. Companion changes

- `docs/src/tutorials/index.rst` and `docs/src/explanation/index.rst` gain toctree entries.
  The explanation index has no toctree at all today, only a sentence promising content, and
  that sentence goes.
- `docs/src/howtos/index.rst` gains the reader how-to.
- Each page carrying python joins `tests/test_docs_snippets.py::DOCUMENTED`; each publishing
  figures joins `PUBLISHES_FIGURES` and `.github/scripts/check_docs_figures.py::PUBLISHES`.
  Four membership lists per page, which {issue}`193` records the cost of getting wrong.
- A baseline in `docs/baseline/` per published figure, generated rather than hand-written.
- `refs.bib` gains the sources §3.4 and §3.5 cite.

(narrative-spec-5)=
## 5. Testing

| what lands | what holds it |
|---|---|
| every python block on every page | `tests/test_docs_snippets.py` — one script per page, on every supported Python |
| every published figure | `check_docs_figures.py` against its `docs/baseline/` baseline within RMS 2 |
| the page-shape rules on figure pages | the page-shape checks of `tests/test_docs_snippets.py`, each proven additive by mutation ({pull}`200`) |
| the pages being reStructuredText | `test_no_user_page_is_written_in_a_format_this_gate_cannot_read` ({pull}`199`) |
| every new `:term:` | the fail-on-warning build; a dangling reference is an error |
| every `narrative spec §…` citation | the pre-commit anchor check and `check_rendered_citations.py` |
| the prose | review, against docs-style's *Reviewing Claims* ({pull}`195`) |

No new gate. The machinery that holds this plan's output was built by the four plans before
it, and needing none is the evidence that those plans were the right shape.

(narrative-spec-6)=
## 6. Scope

**In scope.** The five pages of §3.2–§3.6, their figures and baselines, the glossary entries
they seed, the bibliography entries they cite, the index and membership-list registrations
of §4, and the two closures of §3.8.

**Out of scope.** The developer and contributor guide half of {issue}`66`, which is a
different audience and a different quadrant. Release execution, which follows this plan.
Any API change: an example wanting an API tephpy does not have is a defect report, not a
scope question (gallery spec §7), and {pull}`203` was exactly that report acted on before
this plan started rather than inside it.

**Tranches.** Explanation first — it has the fewest gate surfaces, no session continuity to
maintain, and the tutorials link into it. Tutorials second, on top of pages they can cite.
The reader how-to last, by which time {issue}`202` may have an answer and §3.6 may be
superseded before it is ever written.

(narrative-spec-7)=
## 7. Open items

Tagged per docs spec §3.5.

- **Blocked** (on a redistribution answer — {issue}`202`) — whether the reader how-to's
  Wyoming half becomes a running block. §3.6 specifies the page either way; this decides
  which of the two it is.
- **Open** ({issue}`66`) — the developer and contributor guide. This plan closes the user
  half of that issue and leaves the developer half open, which is the honest split: the two
  share an issue and not an audience.

(narrative-spec-8)=
## 8. References

- {issue}`66` — populate the Diátaxis quadrants
- {issue}`189` — doctested `Examples` sections, closed by §3.8
- {issue}`193` — documentation states capabilities that nothing verifies
- {issue}`198` — the tutorial quadrant's execution coverage, closed by {pull}`199`
- {issue}`202` — shipping a Wyoming sounding needs permission
- {pull}`199` — the quadrants are reStructuredText, and a test holds them there
- {pull}`201` — the 0 °C isotherm default, and the bibliography
- {pull}`203` — `wyoming.parse`
- [Diátaxis](https://diataxis.fr/) — the framework spec §8.6 adopts
