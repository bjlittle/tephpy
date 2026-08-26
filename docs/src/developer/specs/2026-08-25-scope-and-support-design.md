# tephpy scope and support statements — design specification

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. `README.md`, `docs/src/developer/packaging.rst`, `docs/src/howtos/temp-and-bufr.rst`
> and `docs/src/reference/glossary.rst` cite it by section — `scope spec §3.1` and the like —
> so these sections *are* the reasoning behind what they say, and where the two ever diverge
> it is the specification that gets corrected. Read it as current.

- **Date:** 2026-08-25 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `scope spec §…` — the statements a package makes about its own
  reach, not the reach itself; nothing here changes what tephpy draws or computes
- **Scope:** the non-goals statement in `README.md`, the ecCodes recipe that answers the
  first of them, the developer packaging guide and the SPEC 0 support statement it carries,
  the glossary sweep that closes spec §8.6's own list, and the disposal of the doctest
  residual
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) — delivers
  five of the seven items in spec §10's Plan 7b row, and splits the remaining two
  out into a plan of their own
- **Sibling spec:** [`2026-08-03-published-specs-design.md`](2026-08-03-published-specs-design.md)
  — docs spec §3.9 rejected `sphinx.ext.doctest` on the merits while shipping the gate that
  replaced it; §3.5 below is that finding applied to the deferral that outlived it

(scope-spec-1)=
## 1. Purpose

Six plans built the package and a seventh gave it a gallery. What is left before a version
number is not another feature: it is the set of sentences a reader needs in order to know
what they have. tephpy today states what it does — in a README paragraph, in five gallery
examples, in a generated API reference — and states almost nothing about what it does not
do, what it runs on, or what to reach for when the answer is "not this package".

Spec §9 settled that question a month ago. It lists six non-goals and says of them, in the
heading itself, that they are "decisions, not omissions — stated in the README". They are
not stated in the README. The README is thirty-nine lines and every one of them is an
affirmative claim, so a reader arriving with a BUFR file, or expecting a skew-T, learns
their answer by reading the API reference and failing to find it. A non-goal a user
discovers by absence is indistinguishable from a gap, which is the thing spec §9's heading was
written to prevent.

The same pattern repeats three more times, each an obligation a section of the parent
specification laid on Plan 7 and nothing has yet discharged:

- **spec §8.3** requires the SPEC 0 support window be enforced by five things, of which four
  exist — the README badge, the CI Python matrix, the per-Python pixi solve-groups, the
  `sp-repo-review` hook. The fifth is "a docs statement in the developer/packaging guide",
  and there is no packaging guide. The support window is therefore checkable by a
  contributor reading `pyproject.toml` and by nobody else.
- **spec §8.6** enumerates the domain jargon that earns a glossary entry. Every term on that
  list has one except lapse rate ({issue}`183`) — the rate the `dry adiabat` and
  `moist adiabat` entries are both really about, and the one whose acronyms, DALR and SALR,
  a reader meets first everywhere outside this project.
- **spec §8.2 and spec §8.7** promise a `doctest` pixi task and a `ci-docs` doctest run. Neither
  exists, and — this is the finding of §3.5 below — neither should.

None of these is blocked on code. All four are statements, and the reason to make them
together is that they are the same statement seen from four sides: this is what tephpy is
for, this is what it runs on, this is what its words mean, and this is how its
documentation is held to account.

(scope-spec-2)=
## 2. Decisions

1. **The non-goals go in the README, in spec §9's own order, each carrying its onward pointer.**
   A non-goal without a destination is a refusal; with one it is advice.
2. **The ecCodes recipe is a how-to, and its ecCodes half is a shell transcript.** ecCodes
   is a non-goal, so it will never be in the `test` feature, and docs spec §3.9's gate
   executes every python block in the user quadrants with no exemption mechanism — by
   design. A `console` block is not a dodge around that gate; it is what the tool actually
   offers.
3. **The packaging guide is a real page, not a mount for one paragraph.** spec §8.3's statement
   sits inside the support story it belongs to — the floors, the tiers, and what the sdist
   and wheel carry.
4. **The doctest residual is rejected as superseded, not delivered.** docs spec §3.9 made
   the argument; this specification records the verdict and corrects the two sections that
   still promise it.
5. **Spec §10's Plan 7b row splits, and {issue}`184` sits between the halves.** The reason
   is §3.6: narrative documentation is where a framing API gets taught, and teaching one
   that is already scheduled for replacement is the most expensive way to write it.
6. **Nothing here adds a CI gate.** That is not an accident of scope; for decision 4 it is
   the evidence. A supersession that quietly added machinery would not be one.

(scope-spec-3)=
## 3. Architecture

(scope-spec-3-1)=
### 3.1 The non-goals statement

`README.md` gains a **Non-Goals** section below the status note, reproducing spec §9's six
entries in spec §9's order. The order is not alphabetical and not by importance: it is the
order the parent specification chose, and keeping it means the two can be read side by side
and any drift between them is a diff rather than a search.

Each entry is one sentence of what tephpy does not do, followed by where to go instead.
That second half is the part that makes the section worth a reader's time, and most of them
name what to reach for instead:

| non-goal | onward pointer |
|---|---|
| TEMP (TTAA/TTBB) and BUFR decoding | the ecCodes recipe of §3.2, which carries {issue}`82`'s position on a `tephpy[bufr]` extra |
| skew-T projection | MetPy, which owns that space |
| hodograph | `metpy.plots.Hodograph`, which composes onto the same figure — and the gallery example that insets one |
| GUI or interactive dashboard | none; the browser demo is a documentation exhibit, not a product |
| fog-point and layer-cloud constructions | named v1.x candidates; spec §11 and {issue}`192` carry the state |
| aviation overlays (icing, MINTRA contrail curves) | the same, and {issue}`79` folds them into the general layer-shading question |

**No entry links an issue directly, and that is a constraint rather than a choice.**
docs spec §3.8 forbids a GitHub reference written as a bare `#82` or as a hardcoded
`https://github.com/bjlittle/tephpy/issues/82`, and `check_github_references.py` reads
`README.md` along with every other tracked text file — while Markdown, rendered by GitHub
and PyPI, has no `:issue:` role to write instead. The rule and the format leave no third
option, so the README points at pages and the pages carry the issue pointers: the recipe of
§3.2 states {issue}`82`'s position in reStructuredText, where the role renders, and the
published specification carries the rest.

The reader loses nothing that matters. A non-goal that is genuinely undecided must still
*say* it is undecided — that is the docs spec §3.5 contract read from the user's side,
because "not in v1" and "never" are different promises — and the wording carries that
whether or not it carries a link. What it must not do is imply a decision has been taken
when it has not.

**The links obey the README rule, which is not the rule the rest of the documentation
follows.** docs-style's *Documentation Links* section requires an absolute
`https://tephpy.readthedocs.io/en/latest/<page>.html` URL written as a Markdown reference
link, because `README.md` is rendered by GitHub and by PyPI, neither of which resolves a
Sphinx role. `check_documentation_links.py` reads the built HTML and fails a URL that names
a page some other way, so the new recipe page must exist in the build before the README may
link it — which is why §3.2 and this section land in the same change and not in that order,
and why the recipe is where {issue}`82` is cited.

The section also makes the README's first mention of `hodograph`, which has a glossary entry.
docs-style caps README glossary links at the first mention per term, so it takes a reference
link and no later occurrence does.

**What the section is not.** It is not a competitor list and it does not disparage the
alternatives it names. MetPy is a dependency, not a rival — the README's own subtitle already
says the thermodynamics is MetPy's — so "MetPy owns that space" is an accurate division of
labour and reads as one.

(scope-spec-3-2)=
### 3.2 The ecCodes recipe

`docs/src/howtos/temp-and-bufr.rst` answers the first non-goal at length. Its subject is a
reader who has a TEMP bulletin or a BUFR message and wants a tephigram out of it, and its
answer is in two halves with a seam that has to be honest.

**The two formats get different answers, and the page says which is which.** ecCodes decodes
BUFR and GRIB. It does not decode a traditional code form, so `bufr_dump` will not read a
TTAA/TTBB bulletin, and there is no maintained converter to send the holder of one to: WMO's
`synop2bufr` encodes FM-12 SYNOP rather than TEMP, and re-encoding a bulletin is discouraged
where it is done at all, the result lacking the radiosonde type and drift a native message
carries and recovering no precision the code form never had. A page titled for both formats
and naming one tool therefore promised a decode that cannot be performed, which is what the
review of {pull}`191` found. The BUFR half stays a recipe; the TEMP half becomes a section
of its own that says plainly what does not work and gives three things that do — ask the
source for the BUFR, which most can issue after WMO's migration; call
`io.wyoming.fetch` for a station and a time and skip the page; or decode the bulletin by
whatever means and rejoin at *Build a Sounding*, which takes numbers and does not care what
produced them. That last is the load-bearing one: the page's second half was never
ecCodes-specific, and saying so is what keeps the page useful to a TEMP reader without
promising them a tool.

**The decode is not tephpy's, so it is not shown as python.** ecCodes ships command-line
tools — `bufr_dump`, `grib_ls` and their relatives — and the recipe uses one, in a
`code-block:: console` block that shows the invocation and nothing else. Producing genuine
output proved impossible — ecCodes ships no sample sounding message, and encoding one fails
on a delayed-replication array-size mismatch — and inventing output nobody produced would
present a fabricated record as real. The key names a reader will see and the `MISSING`
sentinel a missing value prints as are described in prose beneath the block instead. This is
the shape the gate of docs spec §3.9 requires, and the requirement is a feature rather than
a constraint to work around. That gate executes every python block under `howtos/`,
`tutorials/` and `explanation/` as one script per page, and it has no exemption mechanism on
purpose: its own source says that where a block will not run, "the answer is to rewrite it
as a script, not to exempt it". A python block calling `eccodes` could not run, because
ecCodes is a non-goal and so is never in the `test` feature, on any Python, in any tier. A
`console` block is the truthful rendering of a command-line tool and is passed over by an
extractor that judges language rather than intent.

**The assembly is tephpy's, so it is shown as python, and it runs.** Once the decode has
produced pressure, temperature, dewpoint and wind as ordinary sequences, the rest is
`Sounding(...)` and `ax.plot_sounding(...)` — tephpy's own API over literal arrays standing
in for what a decode produces. That block executes under the docs spec §3.9 gate like every
other, which means the recipe's tephpy half is checked on every supported Python while its
ecCodes half is checked by review. The seam between the two is exactly the seam between what
this project maintains and what it points at, and drawing it in the page's markup rather
than only in its prose is the point.

The page registers in four places: `docs/src/howtos/index.rst`;
`tests/test_docs_snippets.py::DOCUMENTED`; `tests/test_docs_snippets.py::PUBLISHES_FIGURES`,
because the page publishes one figure, prefixed `temp-and-bufr-sounding`; and
`.github/scripts/check_docs_figures.py::PUBLISHES`, the sibling list the documentation-side
figure gate reads. Every list past the toctree is membership rather than a count
(docs spec §3.9): each is what fails when its extractor stops recognising the page, instead
of the page passing by never having been found.

**Title.** *Decode BUFR with ecCodes* — CMOS headline style per spec §8.6, with `ecCodes`
keeping its published casing as a project name, which is the documented exception rather
than an oversight. It names the format the tool decodes and no other, the whole of the
defect above having been a title that named two. The file keeps the slug `temp-and-bufr`,
because the page still answers both of the reader's questions and a TEMP holder searching
for one should find it; a title states a capability, a slug states a subject, and here they
are honestly different.

(scope-spec-3-3)=
### 3.3 The packaging guide

`docs/src/developer/packaging.rst` is new, and joins `docs-style` and `specs/index` in the
developer section's toctree. It carries four things, of which spec §8.3's statement is the first
and the reason the page exists.

**The support window.** Python 3.12, 3.13 and 3.14, per Scientific Python SPEC 0, with the
window revisited on each SPEC 0 rotation. spec §8.3 names five enforcement points and the page
names all five, because the value of the statement is not the version list — that is in
`pyproject.toml` — but the account of what would fail if the list and the reality diverged:
the README badge and this page are assertions, while the `py312`/`py313`/`py314` CI matrix,
the per-Python pixi solve-groups and the `sp-repo-review` hook are mechanisms. Saying which
are which is what stops a reader trusting a badge.

**The floors.** The support window fixes the Python versions; the dependency floors fix
everything else, and they are enforced by a workflow of their own rather than by the test
matrix. The page states the policy and defers the machinery to floors spec — the two
declaration sites, the three tiers `ci-floors` runs (`test`, `docs`, `devs`), and the issue
contract that files a finding against a tier and a package. It does not restate them.
A developer guide that duplicated a specification would be a second copy to drift, which is
docs spec §3.1's whole argument for publishing the specifications in the first place.

**What ships.** The sdist and the wheel do not carry the same tree, and the asymmetry is
load-bearing in one place that has already bitten. `MANIFEST.in` prunes
`docs/src/developer/plans` while `docs/src/conf.py` excludes the same directory from the
HTML build, so a plan is tracked in the repository, absent from the sdist, and unpublished
on the site — deliberately, because a plan is a point-in-time record and a specification is
not (docs spec §3.1). The page also records what the wheel carries beyond the code: the
sample soundings and the gallery header of gallery spec §3.7, `py.typed`, and the logo
masters.

**check-manifest.** Declared in `[tool.pixi.feature.devs.dependencies]` and run by nothing —
no task, no hook, no workflow step. The page says so and points at {issue}`77`, including
that issue's own observation that `MANIFEST.in` has already gone stale once, when
`prune docs/superpowers` stopped matching a directory that had moved and only a hand-run
`python -m build --sdist` caught it. Stating an unrun check as unrun is the alternative to
either adopting it here — out of scope, and {issue}`77` is where that argument belongs — or
leaving a reader to infer from a dependency declaration that something is being checked.

(scope-spec-3-4)=
### 3.4 The glossary sweep

Spec §8.6 enumerates the terms that earn an entry. {issue}`183` established that every one
of them now has one except lapse rate, and that no prose currently uses the term — so the
fail-on-warning build is green and nothing is broken. The cost is entirely to the reader,
and it is a specific one: `moist adiabat` explains that a saturated parcel "cool[s] more
slowly than a dry adiabat", and the *rate* that sentence is about has nowhere to be looked
up.

The entry settles two things the existing entries leave open.

**Canonical spelling.** The headword is **lapse rate** — the general concept, the rate at
which temperature falls with height — because that is the word a reader arrives with, it is
what spec §8.6 and {issue}`183` both call the gap, and the two adiabatic rates are cases of it
rather than rivals to it. The entry defines both inside itself and stacks their names as
further headwords, which is the shape `moist adiabat` already uses for its four:
`dry adiabatic lapse rate` and `DALR`, then `moist adiabatic lapse rate` with
`saturated adiabatic lapse rate` and `SALR` beside it. spec §8.6 requires every acronym to have
an entry, which those give.

Where {issue}`183`'s spelling question actually bites is the saturated rate, and there the
entry agrees with its neighbour rather than reopening the choice: the glossary already
picked `moist adiabat` as canonical over the wet, saturation and saturated variants and said
so in the entry, so `moist adiabatic lapse rate` leads and the rest follow it. The AMS
headword differs; so does what `metpy.calc.moist_lapse` integrates, which is strictly the
pseudoadiabatic rate. Both are worth a clause in the entry and neither is worth a competing
headword.

**The "how it appears in tephpy" clause.** spec §8.6 requires each entry to say how the concept
surfaces in the package, and here the honest answer is that it does not surface as an API at
all: the dry rate is implicit in every constant-θ line the diagram draws, and the saturated
rate is MetPy's, reached through `metpy.calc.moist_lapse` where tephpy computes a moist
adiabat. The entry says that. Manufacturing a citation to satisfy the rule would make the
glossary less useful in exactly the way the rule exists to prevent, and spec §8.6's own audience
clause — definitions for software engineers, saying what carries the concept — is served by
"nothing carries it, here is why" when that is the case.

**The sweep.** Beyond the entry, a pass over spec §8.6's list confirming that nothing else has
gone missing as the package grew, and over the aliases confirming that plural and variant
forms resolve. This is the "glossary completion" of spec §10's cross-cutting rule read as
what that rule says it is — a sweep, not the sole delivery, because entries have been
shipping with their terms since Plan 3.

(scope-spec-3-5)=
### 3.5 The doctest residual, and why it is superseded

Spec §10 item 15 re-homed three Plan 1 deferrals to Plan 7. {pull}`181` rejected the first,
sphinx-tags, as superseded: sphinx-gallery had grown native tags with the filter UI that was
the reason to want them, so taking the dependency would have duplicated an installed feature.
The second residual has the same shape and the same disposal.

**What was promised.** spec §8.2 lists `doctest` among the pixi tasks and spec §8.7 describes
`ci-docs` as "build + doctest". Both sentences were written in Plan 1, before any
documentation existed to test, and they name the obvious mechanism of the time —
`sphinx.ext.doctest`, run by `make doctest` in the docs environment.

**What was built instead.** docs spec §3.9 shipped the snippet executor:
`tests/test_docs_snippets.py` runs every python block under `howtos/`, `tutorials/` and
`explanation/` as one script per page, in document order, because a page is a session rather
than a catalogue. Its corpus is derived rather than declared, so a page is governed from the
day it lands. It recognises `code-block`, `code` and `sourcecode`, the `.. plot::` directive
of plots spec §3.1, and — `test_a_doctest_block_is_found` pins this — a bare `>>>` paragraph,
which docutils renders as a console session whether or not anything declares it.

**Why the promise should not now be kept.** docs spec §3.9 already argued this in the
section that made the choice, and the argument has only strengthened since:

- **It is the same coverage by a second path.** Adopting `sphinx.ext.doctest` means
  rewriting every `code-block:: python` as `testcode::`, adding per-page `testsetup::`
  blocks to carry the session a page's blocks form, and maintaining two execution paths in
  a documentation set whose blocks already execute.
- **It would cover less, not more.** The snippet gate is an ordinary test module, so it runs
  in every test environment on every Python the project supports. A docs-build gate has one
  environment, because the docs feature has one.
- **Its one real advantage does not apply here.** Output checking is what doctest adds over
  execution, and the only blocks with output are the CLI transcripts, whose markers
  `tests/test_cli.py` already pins.
- **It would gate an empty corpus.** There is no `>>>` anywhere in `src/` or in the built
  documentation today. A gate that passes because it found nothing is the failure this
  repository has already met and legislated against — `pixi run docs` depends on all three
  output gates precisely because "a build that linked no citation at all exits 0".

**The verdict.** **Rejected — superseded by docs spec §3.9.** spec §8.2's task list drops
`doctest` and spec §8.7's `ci-docs` description is corrected to name what the job actually runs.
Spec §10 item 15 and its per-deferral status are retagged from **Deferred** to **Rejected**
with this section cited, and {issue}`76` is commented and closed: its three residuals are
then sphinx-tags rejected in {pull}`181`, doctest rejected here, and the SPEC 0 statement
delivered by §3.3.

**What the verdict does not cover, and where it goes.** The snippet gate's corpus is the
three user quadrants; the reference quadrant is out of scope there because it is generated
from the docstrings and cannot drift. That argument is about drift between a page and its
source, not about whether a docstring's `Examples` section *runs* — and nothing would run
one. tephpy has no `Examples` section in any docstring today, so there is nothing unexecuted
and no gate is missing; what is open is whether to write them and gate them with
`--doctest-modules`. That is a content question of real size over figure-returning API, and
it collides with {issue}`184` — `set_extent`'s examples are precisely what that issue
rewrites — so it is filed as a tracked issue of its own rather than folded in here. This is
the docs spec §3.5 contract: the specification carries the pointer, the issue carries the
state.

(scope-spec-3-6)=
### 3.6 The roadmap split, and where {issue}`184` sits

Spec §10's Plan 7b row is one row describing four unrelated deliverables, and {issue}`184`
cuts through the middle of it.

That issue replaces `set_extent`'s `((p, T), (p, T))` corner pairs with keyword ranges and
adds `ax.fit(...)` for data-driven framing, before v0.1, on the argument that nothing has
been released so both are free now and cost a deprecation cycle later. It counts its own
migration at twenty-nine occurrences across `src/` and `tests/` plus a line in four
specifications.

**Narrative documentation is what makes that count grow, and grow in the most expensive
place.** Measured on 2026-08-25, `set_extent` appeared in zero pages of the four user
quadrants; the two examples that frame a view were the whole of its user-facing surface.
That count is no longer zero — the how-to of framing spec §7 shipped alongside this
section and calls both `set_extent` and `fit` — but it is the how-to quadrant that grew,
on purpose and early, for exactly the reason this section gives. The tutorials and
explanation quadrants are still where framing is taught next, so writing them first would
mean writing new call sites into prose, into the published-figure baselines behind that
prose, and into the sessions the docs spec §3.9 gate executes. Prose is the worst of those
to migrate, because a signature change there is not a mechanical edit: the sentence around
the call explains the argument.

**It is also the wrong lesson.** {issue}`184` says of `fit` that it answers "frame this
neatly", "which is what a reader reaches for first, and there is no API for that at all
today" — a promise framing spec §3.2 later qualifies with a pressure clamp, not the
unclamped method itself. A tutorial written now would teach corner pairs — a shape the issue
shows is misnamed for ordinary input and silently order-ambiguous — and would not mention
the API its reader actually wants.

**So the row splits on that seam**, and the split falls cleanly because the dependency does:

| # | Plan | Scope | Depends on |
|---|---|---|---|
| 7b | Scope and support statements | this specification: §3.1 README non-goals, §3.2 ecCodes recipe, §3.3 packaging guide and the spec §8.3 SPEC 0 statement, §3.4 glossary sweep, §3.5 doctest supersession | 7a |
| 8 | Framing by ranges and by data | {issue}`184`: `set_extent` keyword ranges, `ax.fit(...)` | 3 |
| 7c | Narrative quadrants | spec §8.6 tutorials (myst-nb) and explanation content; the reader how-to of gallery spec §5 | 7b, 8 |

Not one item in 7b touches `set_extent`. Every item in 7c does, or would. The rows sit in
execution order and the numbering is not monotonic, which spec §10's lead paragraph already
permits — "the dependencies form a partial order, not a chain" — and which is preferable to
numbering a plotting-layer API change as though it were a documentation plan.

(scope-spec-4)=
## 4. Companion changes

- **spec §8.2** drops `doctest` from its task list and names, in its place, the snippet
  gate of docs spec §3.9 (§3.5).
- **spec §8.7** corrects `ci-docs` from "build + doctest" to what the job runs: the build
  and its four gates — citations, links, figures, browser demo.
- **spec §8.3** gains the pointer to `docs/src/developer/packaging.rst` now that the guide
  its fifth enforcement point names exists (§3.3).
- **spec §9** gains, under the non-goals heading, the pointer to where they are now stated,
  closing the loop its own heading opened.
- **spec §10's Plan 7b row** splits into the three rows of §3.6, and the lead sentence
  "Seven plans deliver the v1 scope" is corrected to match.
- **spec §10 item 15** retags the doctest residual **Deferred → Rejected** (§3.5), and marks
  the SPEC 0 packaging statement delivered.
- **gallery spec §3.6, gallery spec §5 and gallery spec §7** re-point their "7b" references
  to 7c now that the row has split, and gallery spec §7's two open items retag: the doctest
  and SPEC 0 deferral resolves here, and the reader how-to deferral moves to 7c.
- **`docs/src/developer/specs/index.rst`** gains the `scope spec §…` row and the toctree
  entry.
- **`docs/src/howtos/index.rst`** and **`docs/src/developer/index.rst`** gain their new
  pages.
- **`tests/test_docs_snippets.py`** gains the recipe in `DOCUMENTED` and in
  `PUBLISHES_FIGURES`, and **`.github/scripts/check_docs_figures.py`** gains it in
  `PUBLISHES` (§3.2) — the recipe publishes one figure, prefixed `temp-and-bufr-sounding`.
- **`docs/baseline/temp-and-bufr-sounding.png`** is the new baseline the figure gate pins
  the recipe's figure against (§5).
- **{issue}`76`** is commented and closed; **{issue}`183`** is closed by §3.4; a new issue is
  filed for the docstring-`Examples` question of §3.5.

One changelog fragment, `documentation` type: nothing here is user-visible as behaviour, and
the README non-goals statement is the only entry a user reads without opening the
documentation.

(scope-spec-5)=
## 5. Testing

Nothing in this specification adds a gate, and §2 decision 6 explains why that is the
result rather than a gap. What it does add is corpus, and every item lands inside a gate
that already exists:

| what lands | what holds it |
|---|---|
| the recipe's python block | `tests/test_docs_snippets.py` — executed as a page session, on every supported Python |
| the recipe's `console` block | review; it is a non-python language and is passed over by design (§3.2) |
| the recipe's published figure | `check_docs_figures.py` — compared against its `docs/baseline/` baseline within RMS 2 |
| the README's new links | `check_documentation_links.py` over the built HTML — a page named by a URL must exist |
| the packaging guide's `spec §…` and `floors spec §…` citations | the pre-commit anchor check and `check_rendered_citations.py` |
| the lapse rate entry and its aliases | the fail-on-warning build; a dangling `:term:` is an error |
| the new pages' titles | review, against docs-style's *Reviewing Claims* checklist (spec §8.6 CMOS) |

`pixi run docs` is therefore the whole local check, and `pixi run tests` covers the snippet
gate. `tests/test_docs_workflow.py` and `.github/workflows/ci-docs.yml` are untouched —
which, for §3.5, is the evidence rather than an omission: a supersession that added a gate
would not be one.

(scope-spec-6)=
## 6. Scope

**In scope.** The README non-goals statement; the ecCodes recipe; the developer packaging
guide and the SPEC 0 support statement it carries; the lapse rate entry and the sweep around
it; the disposal of the doctest residual and the specification corrections it implies; the
split of spec §10's Plan 7b row.

**Out of scope.** The tutorials and explanation quadrants and the reader how-to — 7c, and
behind {issue}`184`. {issue}`66`'s wider developer build-out — the promoted contributor
pages and the top-level on-ramp — which that issue marks post-release; §3.3 seeds one page
of it and claims no more. Adopting check-manifest ({issue}`77`) and adopting a BUFR extra
({issue}`82`): this specification states each position, and states it as the position of the
issue that owns it.

**Open items**, tagged per docs spec §3.5.

- **Rejected** (2026-08-25) — **the `doctest` task and its `ci-docs` run.** Superseded by
  the snippet executor of docs spec §3.9, which covers the same blocks in more environments;
  §3.5 gives the full argument. The last of spec §10 item 15's three residuals to be
  disposed of, and the second of the three rejected as already delivered by other means.

- **Deferred** (7c — {issue}`66`) — **the reader how-to and the tutorials and explanation
  quadrants.** Not for want of material but for sequence: §3.6 shows that every one of them
  teaches framing, and {issue}`184` changes what framing looks like.

- **Open** ({issue}`189`) — **docstring `Examples` sections and a
  `--doctest-modules` gate over `src/`.** The one surface the docs spec §3.9 gate does not reach.
  There is nothing unexecuted today, because there are no such sections; the question is
  whether to write them. It waits on {issue}`184` for the same reason 7c does.

- **Deferred** ({issue}`77`) — **check-manifest.** §3.3 states its position in the packaging
  guide and adopts nothing. The guide is where a reader would look for it, which is why the
  position is worth stating there rather than left in a dependency declaration.

- **Deferred** ({issue}`82`) — **a `tephpy[bufr]` extra.** §3.1 and §3.2 state the non-goal
  and point at the recipe; whether demand later justifies the extra is that issue's
  question, and the recipe is what makes the current answer usable in the meantime.
