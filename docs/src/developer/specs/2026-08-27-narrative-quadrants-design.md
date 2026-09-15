# tephpy narrative quadrants — design specification

```{readingtime}
```

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
5. **Both routes run, and the body that makes the second one possible ships.** The
   alternative was a page demonstrating one of the two things it is about. {issue}`202`
   stays open as a question worth answering and not as a gate: the redistribution risk is
   accepted knowingly, with attribution carried in the package, and §3.6 specifies the
   withdrawal if the answer comes back no.
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
### 3.6 The reader how-to, and the body that makes it whole

`docs/src/howtos/read-a-sounding.rst`. The two supported routes into a `Sounding`:
{func}`igra.read <tephpy.io.igra.read>` and {func}`wyoming.fetch <tephpy.io.wyoming.fetch>`.

**The constraint, and why relocating the subject did not lift it.** docs spec §3.9 runs
every python block in this quadrant, and spec §8.5 forbids live network in CI — a rule this
specification endorses rather than works around, because a documentation build that reaches
the network fails for reasons that have nothing to do with the documentation. `igra.read`
reads a file, so it runs. `wyoming.fetch` opens a URL, so it never can. gallery spec §5
rejected an `io` gallery example partly on this same ground and sent the subject here, but
the how-to quadrant executes python under the same rule: the move changed which gate applies
and nothing else.

**So the body ships — and its IGRA twin with it.** {pull}`203` made `wyoming.parse` public,
which reaches the format without the network; what it lacked was something to parse. The
recorded fixtures already hold the *same physical ascent* in both formats — Camborne,
2026-07-21 12Z — captured that way so the two readers could cross-validate against each
other in the tests. Shipping the pair makes the page's point literally true rather than
rhetorical: `igra.read` over one file and `wyoming.parse` over the other converge on the
same `Sounding` and draw the same diagram. That convergence is the page's actual subject —
two formats, two readers, one type downstream — and it does not survive shipping only the
Wyoming half, because the sample already in the package is a different station in a
different decade.

The IGRA half of the pair carries no redistribution question: NOAA/NCEI, a U.S. Government
work in the public domain, which is the footing the existing sample already stands on.

**The redistribution position, stated rather than assumed.** The University of Wyoming
publishes no terms of use, copyright, licence or redistribution statement for the archive
(checked 2026-08-27), and absence of a stated licence is not a grant of one. Shipping the
body is therefore a considered risk rather than a permission: the data are numeric
measurements rather than authorship, the volume is one thinned ascent, and the attribution
the fixtures already record travels with it into the package. {issue}`202` remains open —
the question is worth an answer, and the archive names a contact — but it does not gate this
plan.

**The withdrawal, specified now so it is cheap later.** If the answer comes back no, the
sample is removed from `tephpy.samples` and the page's Wyoming block reverts to prose naming
`fetch` and `parse` by role, which is the idiom the ecCodes recipe already uses for the same
function (scope spec §3.2). The page must then say plainly that it demonstrates one of the
two routes: showing one of two things while implying both is the quantifier defect
docs-style's *Reviewing Claims* was written for ({issue}`193`).

**What this costs `tephpy.samples`.** The module today is one IGRA station file, and
`sounding()` routes every sample through `igra.read` — "the same documented route a user's
own file takes" (gallery spec §3.1). A second source in a second format ends both
invariants: `path()` is documented as taking no argument *because* there is one file, and
that reasoning expires. The module's shape is the plan's to settle; what this specification
fixes is that a shipped sample keeps routing through a public reader, so that
`samples.sounding(...)` never becomes a private path a user cannot reproduce.

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

*Amended 2026-09-03 (topics spec §1.1).* Reopened, on a premise this paragraph's reasoning
does not dispute: the question topics spec §1.1 asks is not whether the corpus is too large
to browse, which is still arguably no, but whether it is organised on an axis orthogonal to
how a reader arrives, which volume does not settle either way. The corpus had also grown to
nineteen tagged items by then. `topics spec §3.6` builds the index without the sphinx-tags
dependency this section's own reasoning left rejected.

(narrative-spec-3-9)=
### 3.9 The quadrant landing pages

*Added 2026-09-05.*

A quadrant landing page is navigation. Reading spec §3.7 says so already — all four are
exempt from the reading-time banner under the rule that "a page is exempt when it is
navigated rather than read" — and nothing followed that ruling through into what the pages
contain. Each opens with three paragraphs, the middle of which summarises the quadrant's
pages one at a time, in prose the reader has to hold in mind and match against the toctree
below it. On the how-to page the two are not even in the same order: the prose runs by
subject, the toctree by filename, and nothing joins a clause to the link it describes.

**What is wrong is the arithmetic, not the prose.** {pull}`210` wrote that sentence as six
clauses for six pages, having caught it at five, and recorded the correction. It has since
been extended three times by hand — {pull}`215` for the `DataFrame` route, {pull}`216` for
units, {pull}`220` for labelling and composition — each time in the same commit as the
toctree line it belongs beside. It is nine clauses for nine pages today, and correct only
because no author has yet forgotten. A prose list that has to track a directory is the shape
{issue}`193` is about, and on these pages it is the one claim no gate can see.

**The shape.** A landing page in the tutorials, how-to and explanation quadrants is, in
order: the title; an introduction; one two-column `list-table`; and the `toctree`, hidden.

*Amended 2026-09-05 (`start spec §3.1`).* The shape is not quadrant-only. The
getting-started section takes it too, so `tests/test_docs_landing_pages.py` governs four
sections rather than three — which is why its constant names the audience rather than
Diátaxis.

*Amended 2026-09-11.* **Five sections, and the set is now decided rather than deferred.**
`developer/` takes the shape; the reference quadrant does not. Both were held open — here
for the reference quadrant, and in `contributor spec §7` for the developer guide — on the
question of whether the argument above extends to them. Examined, it extends to neither,
because **the drift this section was written about is absent from both**: the developer
guide's landing page carried no prose at all, a title over a bare toctree, and the
reference quadrant's introduction names two of its six pages as editorial guidance rather
than enumerating them.

What decides it is instead the job a row does — letting a reader tell a page from its
siblings. In the developer guide that job is real and was being done by nothing:
`changelog` there is how to write a news fragment while `changelog` in the reference
quadrant is the release history, and a bare toctree of eight filenames distinguishes
neither. In the reference quadrant the entries are reached by name, so there is nothing to
choose between, and six contrastive sentences would be written for a decision no reader
makes. The introduction it already carries does the guiding that is genuinely wanted.

*Corrected 2026-09-15.* The reference half of that amendment rested on a premise that was
false when written. The introduction did not name two of its six pages rather than
enumerating them: its opening paragraph had enumerated all six since {pull}`210` — "Beside
it sit the command line, every configuration option and its default, a glossary, the
published sources this documentation cites, and the changelog" — and the two pages it named
as guidance were in the paragraphs after it. {pull}`322` then extended that list by hand to
seven, in the same commit as the toctree line it describes: the drift this section was
written about, on the page it had just been declared absent from. The amendment of
2026-09-15 below takes the quadrant in.

Two consequences follow for the gate. Its constant is **`TABLE_SECTIONS`**, not
`USER_SECTIONS`: the developer guide is not a user section, and two other constants of that
name — the glossary sweep's and the snippet gate's — deliberately exclude it, so three
identical-looking tuples that had agreed until now would otherwise invite an edit
harmonising them into two gates this section never asked for. And a **subsection's own
landing page counts as one entry of its parent**: from `developer/` the specification
collection is a single destination, however many documents sit in it. That rule was written
for flat quadrants, where it never arose.

The **introduction** says what the quadrant is for, who it assumes the reader is, what it
guarantees of every page in it, and where to go if this is the wrong quadrant. It says
nothing about an individual page. It keeps the job {pull}`210` gave it rather than taking a
new one: that commit ruled out repeating the root page's canonical Diátaxis one-liners —
"Learning-oriented lessons", "Goal-oriented recipes" — because the grid cards already carry
them, and the ruling stands. The intent of the quadrant is put in the reader's own terms,
not by quoting the framework at them.

The **table** is headerless, a `:doc:` link on the left and one sentence on the right.
Headerless because the reference quadrant already renders this shape: every API page's
summary is a `table.autosummary` with a `tbody` and no `thead`, a link in the left cell and
one sentence in the right. Matching it means the site grows no second table style, and two
columns whose meaning is evident from the first row would spend a header row on every
landing page to say so.

A **row's sentence is editorial rather than descriptive**: it is there so a reader can tell
this page from its siblings, and it is contrastive where two of them are adjacent — an
archive `tephpy` reads, against a format it does not. It is deliberately not the page's
opening line. Tooltip spec §3.3 puts a tip on every internal link inside `article.bd-article`,
so the opening is already what a hover shows, and a cell repeating it would spend a row on
something the reader can have without one.

**The rows and the toctree carry the same order, and it is the order a reader needs rather
than the alphabet.** The toctree being hidden does not make its order private: the sidebar,
the breadcrumb and the previous/next footer all read it. Two orders would set the visible
table against the navigation around it on every page of the quadrant.

**Glossary terms stay out of the cells.** `check_glossary_links.py`'s `prose()` skips a
directive and everything indented under it, so a `list-table`'s cells are invisible to the
first-mention rule: a `:term:` there is neither required nor able to satisfy that rule for
the page, and a term first appearing in a cell without one loses its link with nothing
reporting it. First mentions belong in the introduction, and a cell takes the plain word.

**The gate.** `tests/test_docs_landing_pages.py` names the sections it governs and discovers
the pages inside each, so a page is governed from the day it lands, and asserts for each
section that the sequence of `toctree` entries is the sequence of `:doc:` targets in the
table. A page added to one and not the other fails; a row pointing outside its own quadrant
fails; the two orders drifting apart fails. What it holds is that a quadrant's visible index
and its navigation are one list — which is the thing the prose sentence never was and could
not have been. *Corrected 2026-09-15:* this paragraph said the gate discovers the quadrant
directories rather than listing them. It lists them, in the two constants this section
names, and discovers the pages.

*Amended 2026-09-15.* **Six sections, two shapes.** The reference quadrant takes a landing
page of its own shape — a grid of cards, where the other five sections carry a table. Of the
two premises that kept it out, the first was false when written (above). The second, that
its entries are reached by name, is answered by a card rather than contradicted by one: a
card is a named destination a reader recognises by its icon, which is how a lookup is found,
and its sentence separates the pairs that do blur side by side — *What's New* against the
*Changelog*, the *Command Line* against the *Configuration Options*. The root page already
reaches its four quadrants the same way.

In order, the page carries the title; an introduction saying what the quadrant is for; the
card grid; two guidance paragraphs — where a caller deciding what to catch should look, and
whom the glossary is written for; and the `toctree`, hidden. The guidance follows the grid
rather than preceding it, because the cards are what the page is for and those paragraphs are
advice for a particular need. `tests/test_docs_snippets.py` requires the first of them.

- **The grid** is `.. grid:: 1 2 2 2`: one column below 576px and two above, with the API
  card leading at full width (`:columns: 12`) and the other six paired in three rows.
  Measured 2026-09-15 in Chromium at 360, 600 and 1280px. At 360px two columns — the root
  page's `.. grid:: 2`, which is two columns at every breakpoint — broke words mid-word, as
  "Configuratio / n" in a title and "documentatio / n" in a sentence, where one column broke
  none. Seven cards in two columns also leave the last row half empty, which the full-width
  lead removes.
- **A card's title** is its page's title, except the API card's: that page is titled by the
  package name, `tephpy`, which on a card tells a reader nothing.
- **A card's sentence** is contrastive, as a row's is, but the rule against repeating the
  page's opening does not carry over, because a card raises no tooltip. sphinx-design builds
  a card from a zero-size anchor stretched over it, and tooltip spec §3.3 keeps
  `sd-stretched-link` in `tippy_skip_anchor_classes` so that a hover buries nothing. The tip
  is generated and never attached, so the generated data carries one and the page shows
  none. Beside the title and the icon, the sentence is all a reader has before choosing.
- **Each card carries an icon** in the root page's vocabulary: the 45° lattice at 20%
  opacity, bold navy strokes, one orange accent on the thing pointed at, and no drawing used
  twice. Light and dark are one drawing. The dark file swaps the navy for `#8FB8E8` and the
  knock-out halo for `#14181e` — the ground measured behind a card, which sets no background
  of its own. The root page's dark *Tutorials* icon used `#20242b`, which leaves a visible
  ring on that ground, and is corrected with them.
- **Glossary terms stay out of the cards**, for the reason they stay out of the cells: a card
  is a directive, and `prose()` skips its body.

**The gate holds the cards as it holds the tables.** `CARD_SECTIONS` sits beside
`TABLE_SECTIONS`, and for each card section the same four things are asserted: the cards'
targets are the toctree's entries, as a sequence; every card links to a page in its own
section; the cards cover every page the section holds; and the toctree is hidden. A section
belongs to one constant, and a page carries one index. The API card is the one entry
discovery cannot see — `autoapi_keep_files = False` and a git-ignored directory mean
`generated/api/tephpy/index` exists only while a build runs — so the gate derives it from the
`autoapi_root` and `autoapi_dirs` that `conf.py` sets, read by executing the file as
`tests/test_docs_whatsnew.py` does, and page discovery passes over the generated directory.
Titles, sentences, icons and which card leads are presentation, and are not gated.

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
- `tephpy.samples` gains the Camborne pair of §3.6 — the Wyoming body and its IGRA twin —
  with the attribution the fixtures already record, and
  `[tool.setuptools.package-data]` gains the glob that carries the second format:
  `samples/*.txt` names text alone today.

*Added 2026-09-05 (§3.9).*

- `docs/src/tutorials/index.rst`, `docs/src/howtos/index.rst` and
  `docs/src/explanation/index.rst` take the shape of §3.9, and their toctrees become hidden
  and reordered to match their tables.
- `tests/test_docs_landing_pages.py` holds them there.
- `docs/src/developer/docs-style.rst` gains the rule, beside its *Reading Time* section —
  which is where reading spec §3.7's "navigated rather than read" already stands, and where
  a page author looks.

*Added 2026-09-15 (§3.9).*

- `docs/src/reference/index.rst` takes the card shape, and `docs/src/_static/cards/reference/`
  gains a light and a dark icon for each of its seven cards.
- The root page's card classes become `teph-card` and `teph-card-icon`, since the cards are no
  longer only quadrants and `teph-quadrant-button` already names the topic page's filter. Its
  dark *Tutorials* icon takes the `#14181e` halo.
- `tests/test_docs_landing_pages.py` gains `CARD_SECTIONS`. The docstring of
  `tests/test_docs_snippets.py`'s signpost test stops describing the listing sentence, and
  its assertion stands.
- `docs/src/developer/docs-style.rst`'s *Landing Pages* rule gains the card shape, and loses
  two stale claims: that §3.9 leaves the reference quadrant's question open, and a list of the
  sections it governs that omits `developer/`.

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
| the shipped Wyoming sample | `tests/test_samples.py` — it reads through a public reader and yields a `Sounding`, like every other sample |
| the prose | review, against docs-style's *Reviewing Claims* ({pull}`195`) |
| a section's landing table or card grid against its toctree (§3.9) | `tests/test_docs_landing_pages.py` — the two are one ordered list, or neither is |

The five pages of §3.2–§3.6 needed no new gate. The machinery that holds them was built by
the four plans before it, and needing none is the evidence that those plans were the right
shape.

§3.9 is the exception, and the reason is worth stating rather than waiving: what it holds is
not a property of a page's content, which the gates above already cover, but an agreement
between two lists on one page. Nothing that existed could see it, and three PRs kept that
agreement by hand.

(narrative-spec-6)=
## 6. Scope

**In scope.** The five pages of §3.2–§3.6, their figures and baselines, the glossary entries
they seed, the bibliography entries they cite, the index and membership-list registrations
of §4, the shipped Wyoming sample and the `tephpy.samples` changes it forces, and the two
closures of §3.8.

**Out of scope.** The developer and contributor guide half of {issue}`66`, which is a
different audience and a different quadrant. Release execution, which follows this plan.
Any API change: an example wanting an API tephpy does not have is a defect report, not a
scope question (gallery spec §7), and {pull}`203` was exactly that report acted on before
this plan started rather than inside it.

**Tranches.** Explanation first — it has the fewest gate surfaces, no session continuity to
maintain, and the tutorials link into it. Tutorials second, on top of pages they can cite.
The reader how-to last, carrying the shipped Wyoming sample and the `tephpy.samples`
changes §3.6 describes, so the package change and the page that justifies it land together.

(narrative-spec-7)=
## 7. Open items

Tagged per docs spec §3.5.

- **Open, not blocking** ({issue}`202`) — whether the recorded Wyoming ascent may be
  redistributed in the wheel. Decided 2026-08-28 to ship on accepted risk rather than wait,
  the alternative being a page that demonstrates one of the two things it is about. §3.6
  states the position and specifies the withdrawal, so an answer of no costs a sample and a
  paragraph rather than a redesign. *Shipped 2026-08-29* ({pull}`210`): the sample is in
  `tephpy.samples` and in the wheel, with its attribution, so the question is now live
  rather than hypothetical.
- **Refined** (2026-09-15, §3.9) — whether the reference quadrant's landing page takes the
  table of §3.9 too. Closed on 2026-09-11 as no, while `developer/` took the table, settling
  this bullet and `contributor spec §7`'s together as the one decision they always were. It
  rested on two premises: that the quadrant's entries are reached by name rather than chosen
  between, and that its introduction named two of the six pages as guidance rather than
  enumerating them. The second was false when written — the opening paragraph had listed all
  six since {pull}`210` — and {pull}`322` extended that list to seven. Refined on 2026-09-15
  to a shape of its own: a grid of cards held by the same gate, which answers the first
  premise rather than contradicting it. §3.9 carries the correction, the shape and the gate.
- **Closed** (2026-09-11, {issue}`66`) — the developer and contributor guide. This plan
  closed the user half of that issue and left the developer half open, which was the honest
  split: the two share an issue and not an audience. The developer half followed as
  `contributor spec` and `tour spec`, and the issue's last item — the explanation-level
  account of where the diagram's scales live — landed as a section of
  *Why the Axes Are Rotated* rather than a third page, because decision 1 above pairs each
  explanation page with the tutorial that raises its question and none raises this one.

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
