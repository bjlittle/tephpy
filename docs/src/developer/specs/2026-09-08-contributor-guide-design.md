# tephpy contributor guide — design specification

```{readingtime}
```

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. The pages it describes cite it by section — `contributor spec §3.5` and the
> like — so these sections *are* the reasoning behind what those pages say, and where the
> two ever diverge it is the specification that gets corrected. Read it as current.

- **Date:** 2026-09-08 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `contributor spec §…` — named for its audience rather than for
  `docs/src/developer/`, the directory it governs, because that directory also holds this
  collection and `developer spec` would read as "the specification about specifications"
- **Scope:** four new pages in the developer guide, the relationship between published
  prose and the agent-facing `AGENTS.md` files, and the two gates that keep both honest
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) —
  `spec §8.6`'s documentation layering, whose **mid** tier is the developer guide
- **Sibling specs:**
  [`2026-09-05-getting-started-design.md`](2026-09-05-getting-started-design.md) — the
  on-ramp, which is {issue}`66`'s first third as this is its second;
  [`2026-08-25-scope-and-support-design.md`](2026-08-25-scope-and-support-design.md) —
  §3.1's `README.md`, one of the surfaces §3.6 below rebalances

(contributor-spec-1)=
## 1. Purpose

**The same rules are already written three times, and none of the copies is published.**
Measured 2026-09-08 across the five governing documents — `CONTRIBUTING.md` (32 lines),
`changelog/README.md` (24), `tests/AGENTS.md` (18), `AGENTS.md` (14), `docs/AGENTS.md`
(15):

| rule | written in |
|---|---|
| the changelog fragment's name and type | `CONTRIBUTING.md`, `AGENTS.md`, `changelog/README.md` |
| `:user:` attribution on every fragment | the same three |
| tests mirror the `src/tephpy` layout | `CONTRIBUTING.md`, `AGENTS.md`, `tests/AGENTS.md` |
| `pixi run tests` | `CONTRIBUTING.md`, `AGENTS.md`, `tests/AGENTS.md` |
| CMOS headline style for titles | `CONTRIBUTING.md`, `AGENTS.md`, `docs/AGENTS.md` |

Five of six rules sampled, three copies each, nothing holding them together. A sixth —
the BSD copyright header — is written once, in `AGENTS.md`, where a human contributor
will never look.

The Sphinx build sees none of it. `docs/src/developer/` publishes `docs-style.rst`,
`packaging.rst` and this collection, so a contributor arriving at the documentation is
told how to write a page and what the distributions carry, and nothing about how to run
the tests.

**And the continuous integration is undocumented entirely.** Thirteen workflows, eighteen
gate scripts, seventeen pixi tasks across seven environments. Only `packaging.rst`
mentions a workflow at all, and only in passing about wheels. Six of the thirteen run on a
schedule, which makes them the one part of this project a contributor meets *involuntarily*
— a red tick they did not cause, a pull request a bot opened, a label that appeared on
their issue. The reasoning exists, spread across nine design specifications and the
workflow headers themselves, in neither of which a contributor would think to look.

{issue}`66` asks for this as its second third. Its own survey is stale in every row —
it counts `CONTRIBUTING.md` at 20 lines and `AGENTS.md` at 11 — and it names geovista's
`codecraft` / `documentation` / `packaging` / `testing` / `towncrier` set as the bar.
That bar is adopted for the shape and departed from for continuous integration, which
geovista does not document and which tephpy's schedule-driven machinery makes unavoidable.

(contributor-spec-2)=
## 2. Decisions

1. **Published prose is canonical; `AGENTS.md` stays directive.** The pages own the
   explanation and the reasoning. The `AGENTS.md` files stay terse and imperative, because
   an agent reads them at session start with no built documentation tree to follow a link
   into. Neither is generated from the other (§3.6).
2. **The literals they share are gated, and only the literals.** A command string, the
   fragment's name pattern, the attribution role: these must agree wherever they appear,
   and a test says so. The prose around them differs by audience, deliberately and without
   a gate (§3.6). This extends `tests/test_docs_workflow.py`'s existing assertion rather
   than inventing a mechanism.
3. **Four pages, one per source document that carries real content, plus continuous
   integration.** `contributing`, `testing`, `changelog`, `ci` (§3.2–§3.5).
4. **The continuous-integration page is held at one altitude: purpose, intent, and what a
   failure means for the reader.** Detail lives in the specifications and in the workflow
   files. A contributor wanting to know *why* the floors gate is shaped as it is reads
   `floors spec §3.4`; the page tells them a bot may file an issue and what to do with it
   (§3.5).
5. **A failure mode is documented when the contributor meets it without having caused it,
   or when the remedy is non-obvious.** Both halves are needed, and the criterion is
   written down because "if it is meaningful" is otherwise decided page by page and reads
   as inconsistency (§3.5).
6. **The pixi task graph goes in `contributing.rst`, not `packaging.rst`.** That page is
   about the product — what tephpy runs on and what its distributions carry. The task
   graph is about the workbench (§3.7).

(contributor-spec-3)=
## 3. Architecture

(contributor-spec-3-1)=
### 3.1 The section, and what each page owns

`docs/src/developer/` grows from three entries to seven:

| page | what it owns |
|---|---|
| `contributing.rst` | the environment, the task graph, and the shape of a pull request |
| `testing.rst` | the tests tree, image comparison, and the no-network rule |
| `changelog.rst` | the fragment: its name, its type, and the roles its prose uses |
| `ci.rst` | what runs, why it exists, and what its failure means |
| `docs-style.rst` | *(exists)* how to write a page |
| `packaging.rst` | *(exists)* what tephpy runs on and what it ships |
| `specs/index.rst` | *(exists)* the design record |

**No landing table, deliberately and for now.** `narrative spec §3.9`'s two-column table
plus hidden toctree governs the four `USER_SECTIONS` — measured: `start`, `tutorials`,
`howtos`, `explanation` in `tests/test_docs_landing_pages.py`, and the same four in
`check_glossary_links.py` and `tests/test_docs_snippets.py`. `developer` is in none of
them, and `narrative spec §7` holds open whether the reference quadrant should take one.

The reason for declining it here is not that the shape would be wrong but that **the
content is still maturing**, and a table commits to a description of each page before
there is a settled page to describe. Simple and clean while the section grows; revisited
once it has stopped moving. `developer/index.rst` therefore keeps its bare toctree and
gains the four entries, and §7 carries the question rather than this section closing it.

**Reading-time banners apply.** `tests/test_docs_readingtime.py` derives its corpus over
the whole tree and exempts `developer/index.rst` and `developer/specs/index.rst` by name
as landing pages. The four new pages are read through, so each carries a banner.

(contributor-spec-3-2)=
### 3.2 *Contributing*

`docs/src/developer/contributing.rst`. Promoted from `CONTRIBUTING.md` and expanded.

What it owns: getting an environment, the task graph of §3.7, and what a pull request is
expected to carry — a changelog fragment, a passing `pixi run docs` where documentation
changed, and prose reviewed against docs-style's *Reviewing Claims*.

It is the page a contributor opens in order to *do* something, which is why the task graph
lands here and not in `packaging.rst`.

(contributor-spec-3-3)=
### 3.3 *Testing*

`docs/src/developer/testing.rst`. Promoted from `tests/AGENTS.md` and expanded.

The tests tree mirrors `src/tephpy`, and `tests/test_layout.py` holds it there, so a
subpackage arriving without its directory fails a test rather than waiting to be noticed.
Image tests use pytest-mpl against `tests/baseline`; `pixi run baselines` regenerates
them, and a lockfile bump that moves matplotlib or freetype is the occasion — re-verified
across all three test environments, which is the non-obvious half.

**No test touches the network.** The reason belongs on this page rather than in a comment:
a suite that reached the University of Wyoming would fail on their outage rather than on
our defect. The cost of that rule — that the archive can move and every gate stays green —
is what `ci-linkcheck`'s endpoint job pays, and §3.5 picks the thread up there.

(contributor-spec-3-4)=
### 3.4 *Changelog*

`docs/src/developer/changelog.rst`. Promoted from `changelog/README.md`.

The fragment's name, the eight types, the `:user:` attribution, and — the part that is
genuinely editorial rather than mechanical — which role to reach for. `:issue:` at the
point the fragment describes what the issue reported; a Sphinx domain role for any
documented API so the entry links into the reference; a plain double-backtick literal
reserved for names with no documentation target.

That last distinction is the reason this is a page rather than three lines inside §3.2.
It is a judgement a contributor makes on every fragment, and the existing 24 lines are
the closest thing this project has to a style guide for release notes.

(contributor-spec-3-5)=
### 3.5 *Continuous integration*, and the altitude it holds

`docs/src/developer/ci.rst`. Written rather than promoted: no prose source exists.

**The altitude is fixed by decision 4.** Purpose, intent, and consequence. Not what a
workflow's steps are — the file says that, and says it better, because it cannot drift
from itself. Not why a gate is designed as it is — a specification says that. A reader
who wants either is told where to go.

**Organised by when the reader meets it**, which is the distinction that matters to them
and the one neither the file listing nor the specifications make:

| grouping | members |
|---|---|
| on your pull request | `ci-tests`, `ci-docs`, `ci-changelog`, `ci-citation`, `ci-wheels`, `ci-label`, `codeql` |
| on a schedule | `ci-locks`, `ci-floors`, `ci-topics`, `ci-linkcheck`, `ci-stale`, `codeql` |
| on an issue or a first pull request | `ci-first-contribution` |

`codeql` appears twice because it genuinely runs both ways. Alphabetical order would put
`ci-changelog` first and bury the six that arrive unbidden.

**What can go wrong is documented against decision 5's criterion**: the contributor meets
it without having caused it, *or* the remedy is non-obvious. Worked through the members,
that admits four and excludes the rest:

| case | why it qualifies |
|---|---|
| a lock refresh moves matplotlib or freetype, and the bot's pull request goes red on pytest-mpl | both halves — nobody caused it, and `pixi run baselines` re-verified across three environments is not guessable |
| `ci-stale` labels an issue | met without causing; and what it never touches is the non-obvious part |
| `ci-floors`, `ci-linkcheck` or `ci-topics` files a standing issue | met without causing |
| `pixi run docs-all` cannot start a browser | the remedy is a Playwright install through pixi, which is the failure `tests/test_docs_workflow.py` already gates the wording of |

And excludes `ci-tests` going red because the change is wrong, which needs no page.

**The failure half is the half that rots**, because purpose is stable and remedies track
the code. It is therefore confined to *structural* failures — ones that follow from how
the thing is built, not from what it happened to find last week. A page confidently wrong
about a remedy is worse than a page that says nothing, because a contributor believes it.

(contributor-spec-3-6)=
### 3.6 The relationship to `AGENTS.md`, and the literals that are gated

**The published page is canonical for prose; `AGENTS.md` is canonical for nothing and
authoritative for its own audience.** An agent reads `AGENTS.md` at session start, in a
checkout with no built documentation, so it cannot be reduced to a pointer at a page it
cannot open. A human reads the page, and is owed the reasoning an imperative rule omits.

The two are therefore **not** generated from one another, and the duplication of §1 is
resolved by *kind* rather than by deletion: the page carries why, the `AGENTS.md` carries
what, and the literals they both name are held equal by a test.

**The gated literals** are the strings where disagreement is a defect rather than a
difference in voice:

- the pixi task invocations — `pixi run tests`, `lint`, `docs`, `docs-all`, and the
  `pixi run -e docs …` form Playwright needs;
- the changelog fragment's name pattern, `changelog/<PR>.<type>.rst`, and its eight types;
- the attribution role, `:user:`.

`tests/test_docs_workflow.py::test_the_advice_runs_where_it_is_read_and_the_guide_says_the_same`
is the precedent and the mechanism. It already holds `CONTRIBUTING.md` against the
commands the browser-demo check emits on failure, after the two agreed for a while on
`playwright install chromium` — a command neither shell can run ({pull}`177`). The new
assertion is the same shape over a wider corpus.

**`CONTRIBUTING.md` and `changelog/README.md` become pointers**, each keeping only the
gated literals and a link to the page that explains them. This is `start spec §3.9`'s move
on `README.md` applied one surface over, and for the same reason: GitHub puts
`CONTRIBUTING.md` in front of a first-time contributor, so it should send them somewhere
rather than hold a third copy. Both are excluded from the sdist already, so nothing about
the distributions changes.

(contributor-spec-3-7)=
### 3.7 The pixi task graph, and why it is not in `packaging.rst`

Seventeen tasks across three features, resolved into seven environments. A contributor
runs about five of them; the rest are steps the graph runs on their behalf:

```
docs-clean ─→ docs-html ─→ docs-check-api        ─┐
                        ─→ docs-check-citations   │
                        ─→ docs-check-figures     ├─→ docs ─┐
                        ─→ docs-check-links       │         ├─→ docs-all
                        ─→ docs-check-tooltips   ─┘         │
                        ─→ docs-browser-test ────────────────┘
```

**The shape is the content.** A flat list of seventeen would be worse than nothing: it
would read as seventeen things to learn, when the fact worth carrying away is that `docs`
is the one to reach for, `docs-all` adds the browser check CI runs, and everything under
`docs-html` is a step rather than a command.

Two further facts are load-bearing: `pixi run <task>` selects the environment, and the one
exception is Playwright, which lives only in the `docs` environment and is on no other
`PATH` — hence `pixi run -e docs …`.

**Not `packaging.rst`.** That page opens "what `tephpy` runs on, what holds it there, and
what its distributions carry": supported Pythons, dependency floors, sdist and wheel
contents, the manifest gate. It is about the product. Measured: it mentions pixi twice,
both incidentally. Filing the most-trodden interface in the project under the
least-visited heading would bury it.

(contributor-spec-3-8)=
### 3.8 The two gates

Both exist because a page that silently stops being a complete map is worse than one that
was never claimed to be complete.

**Workflow coverage.** Every `.github/workflows/*.yml` is named on `ci.rst`, and every
workflow named on `ci.rst` exists. Derived from the directory rather than from a list, so
a fourteenth workflow fails the gate rather than quietly going undocumented. This is
`one set, many lists` in its usual shape — the same reasoning that gives
`tests/test_docs_landing_pages.py` its corpus assertion.

**Task coverage.** Every task in `pyproject.toml` is either named on `contributing.rst` or
reachable from a named one through `depends-on`. In the other direction, nothing the
Task Graph table names is absent from `pyproject.toml` — the table, not the whole page:
it is the one place the page asserts "this is a task", where a whole-page scan would read
a bare word like ```` ``tephpy`` ```` or a `pixi run` target that names a real external
command rather than a task (```` ``playwright`` ````, in the browser-demo prose) as a false
claim. The gap this leaves is real and recorded rather than hidden: a bogus task name
written into the page's prose, outside the table, is not caught. `tests/pixi_tasks.py`
already reads the manifest for `tests/test_docs_workflow.py` and the `ci-floors` gate, so
the reader exists and this adds a third consumer rather than a second parser.

*Corrected 2026-09-08, before implementation.* This section first said "or carries an
explicit internal marker in the gate", which would have been a hand-written list of
exemptions — the very shape these gates exist to remove. `tests/pixi_tasks.py` already
exports `closure(names, tasks)`, which walks `depends-on`, so the exemption derives itself:
a task the page does not name is excused exactly when running something the page *does*
name runs it.

*Corrected 2026-09-08, again, against the implementation.* The paragraph above measured
the wrong page: "nine tasks reach the other eight" was projected from a draft naming set,
not from what `contributing.rst` shipped with. The page that landed spells out all
seventeen tasks directly — nine in the Task Graph table, the other eight in the ASCII
diagram above it (`docs-clean`, `docs-html`, and the five `docs-check-*` gates among
them) — so today `closure()` excuses nothing: every task is already named, and the
reachable-but-unnamed set is empty. The mechanism stays regardless, held to a synthetic
graph in `tests/test_contributor_guide.py` rather than to the manifest, because that is
what keeps the gate from breaking should the diagram ever be redrawn without spelling out
every task, or a task ever be added that only something named depends on.

Both assert in **both directions**. A gate checking only that the page names nothing false
passes over a page that names half the set.

(contributor-spec-4)=
## 4. Companion changes

- `docs/src/developer/index.rst` — the toctree gains `contributing`, `testing`,
  `changelog` and `ci`. Ordered as a contributor meets them, not alphabetically:
  contributing, testing, changelog, docs-style, packaging, ci, specs.
- `CONTRIBUTING.md` — reduced to the gated literals and a pointer (§3.6).
- `changelog/README.md` — the same.
- `AGENTS.md`, `tests/AGENTS.md`, `docs/AGENTS.md` — unchanged in kind, edited only where
  a rule they state is wrong or absent; the BSD-header rule of §1 gains a home on a
  published page for the first time.
- `docs/src/developer/specs/index.rst` — the prefix table gains a `contributor spec §…`
  row **and its toctree the matching entry**. Two hand-written lists over one set; writing
  one without the other is a mistake made before.

(contributor-spec-5)=
## 5. Testing

| what lands | what holds it |
|---|---|
| every workflow named on `ci.rst`, and nothing false | a new assertion, §3.8 |
| every pixi task named on `contributing.rst` or reachable from one that is, and nothing the task table names absent | a new assertion, §3.8 |
| the shared literals agreeing across page and `AGENTS.md` | `tests/test_docs_workflow.py`, widened (§3.6) |
| the four pages carrying a reading-time banner | `tests/test_docs_readingtime.py`, already derived over the tree |
| every `contributor spec §…` citation | the pre-commit anchor check and `check_rendered_citations.py` |
| the prose | review, against docs-style's *Reviewing Claims* |

Two new assertions and one widened. The pages are otherwise held by machinery that already
exists and that they join by being in the tree.

(contributor-spec-6)=
## 6. Scope

**In scope.** The four pages of §3.2–§3.5, the relationship and gated literals of §3.6,
the task graph of §3.7, the two gates of §3.8, and the companion changes of §4.

**Out of scope.** {issue}`66`'s third part — splitting the parent specification's §3.2
into a `plotting` tour — which is separately scoped and is the largest of the three.
A landing table for `developer/`, which `narrative spec §7` holds open for the reference
quadrant and which this section will not settle in passing. Any change to what the
`AGENTS.md` files are *for*.

**Tranches.** The gates cannot precede the pages they read: both assert against a page on
disk, and either would fail with the page absent. So each gate lands with its page.
`ci.rst` is the one page written rather than promoted, and is the natural last tranche.

(contributor-spec-7)=
## 7. Open items

Tagged per docs spec §3.5.

- **Open** — whether a `codecraft` page follows, covering the BSD header, the ruff
  configuration, numpydoc validation and the citation conventions. geovista has one, and
  the material exists here but is scattered across `AGENTS.md` and
  `.pre-commit-config.yaml` rather than sitting in one document. Not taken now because it
  is the only one of geovista's five with no prose source at all, and `ci.rst` already
  spends this section's budget for written-from-scratch pages.
- **Open, not blocking** — whether `ci.rst` should name the six scheduled workflows' cron
  times. They are a fact a contributor occasionally wants and a seventh hand-written copy
  of something the workflow files state; the workflow-coverage gate of §3.8 checks
  membership, not schedule, and widening it to schedules would mean parsing cron in a test
  to compare against prose.
- **Open** — whether `packaging.rst` should cross-reference §3.7's task graph now that the
  two pages sit beside each other. It names `pixi run manifest` today without saying where
  the task table is documented.
- **Deferred 2026-09-08, deliberately** — whether `developer/` takes a landing table in
  `narrative spec §3.9`'s shape. Declined for now because the section's content is still
  maturing and a table fixes a one-line description of each page before the page has
  settled: the bias while a section grows is toward simple and clean. Revisit once the
  four pages have stopped moving, alongside `narrative spec §7`'s open question about the
  reference quadrant — the two are one decision about which sections the shape governs,
  and answering them separately is how a rule ends up stated over a set nobody chose.

(contributor-spec-8)=
## 8. References

- {issue}`66` — populate the Diátaxis quadrants and build out a developer/contributor guide
- {pull}`177` — the guide and the failure message agreed on a command neither shell could run
- `spec §8.6` — the documentation layering whose mid tier this section is
- `start spec §3.9` — the pointer-not-a-copy move, applied to `README.md` first
- `narrative spec §3.9` — the landing-page shape, and why this section does not adopt it
