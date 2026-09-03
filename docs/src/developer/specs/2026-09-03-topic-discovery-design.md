# tephpy topic discovery — design specification

```{readingtime}
```

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. The taxonomy module, the extension, the gate and the report it describes cite
> it by section — `topics spec §3.4` and the like — so these sections *are* the reasoning
> behind what that code does, and where the two ever diverge it is the specification that
> gets corrected. Read it as current.

- **Date:** 2026-09-03 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `topics spec §…` — not `tags spec`, because gallery spec §3.6
  already owns "tags" for sphinx-gallery's own mechanism, and a citation that reads as
  naming that rule while meaning the site-wide taxonomy is the collision plots spec avoided
  when it declined `figures spec`. The subject here is the reader's topic, not the markup
  that records it
- **Scope:** one taxonomy module, one Sphinx extension, one published page, one pytest
  gate, one scheduled report, and a `:tags:` field list on 14 narrative pages; the five
  gallery examples keep the tags they already declare; no change to `src/tephpy/`. The
  amendment to `.github/scripts/check_glossary_links.py`, so the glossary gate skips a
  leading docinfo field list as metadata rather than reading it as prose (§3.2), is not a
  companion change but a prerequisite — a scope line omitting it would describe a change
  that could not have been merged
- **Parent spec:** [`2026-08-20-examples-gallery-design.md`](2026-08-20-examples-gallery-design.md)
  — gallery spec §3.6 is the closed vocabulary this generalises, and gallery spec §7 is
  where the site-wide index was first deferred
- **Sibling spec:** [`2026-08-27-narrative-quadrants-design.md`](2026-08-27-narrative-quadrants-design.md)
  — narrative spec §3.8 rejected this feature on a premise §1 below re-examines, and
  narrative spec §3.1 describes the reader it is for
- **Related:** [`2026-08-31-reading-time-design.md`](2026-08-31-reading-time-design.md) —
  reading spec §3.1's module split is the pattern §3.5 follows, and reading spec §3.7's
  exemption list is one of the registration sites §4 enumerates

(topics-spec-1)=
## 1. Purpose

Diátaxis segregates documentation by the reader's **intent**: learning, working,
understanding, looking up. tephpy's four quadrants are that framework made literal, and the
clarity is real. But a reader does not always arrive with an intent. Often they arrive with
a **topic** — "units", "how do I get my data in", "what is CAPE" — and a topic is
orthogonal to intent. It lands in two, three or four quadrants at once, and the reader has
no way to see that except by visiting each in turn and hoping.

Measured on the corpus of 2026-09-03, `sounding` appears in twelve of nineteen items across
three quadrants; `diagram` and `isopleths` each appear in six items across all four. A
reader following one of those topics currently has to know to look in the tutorials, the
how-tos *and* the gallery. Nothing on the site tells them so.

The alternative on offer is the Read the Docs search box, which is a full-text index over
prose. It answers "which pages contain this word", which is a different and weaker question
than "which pages are *about* this subject", and it cannot say which quadrant an answer
came from.

(topics-spec-1-1)=
### 1.1 The rejection this reopens

This feature was rejected twice. gallery spec §7 rejected the `sphinx-tags` dependency on
2026-08-20 and left the site-wide index as a question for the plan that would own the
narrative quadrants. narrative spec §3.8 then closed it on 2026-08-27:

> After this plan the narrative corpus is about eleven pages across three quadrants, each
> with a landing page and a toctree. A tag index is navigation for a corpus too large to
> browse, and eleven pages is not one.

That reasoning is sound and this document does not contradict it. It reopens the question
for two reasons.

**The premise has moved.** Those three quadrants now hold fourteen pages — tutorials 3,
how-tos 9, explanation 2 — and the tagged corpus including the gallery is nineteen items.
Growth alone does not overturn a decision, but the number it rested on is no longer the
number.

**The question answered was a different one.** narrative spec §3.8 asked whether the corpus
is *too large to browse*. That is a question about volume, and its answer is still arguably
no. This document asks whether the corpus is *organised on an axis orthogonal to how a
reader arrives*, which is a question about structure and is unaffected by volume. A
four-page corpus split across four quadrants has the same problem in miniature. §2 decision
1 is what falls out of taking the second question seriously while conceding the first.

(topics-spec-2)=
## 2. Decisions

1. **The index is the deliverable; the filter is an enhancement on it.** Nineteen items fit
   on one screen, so a filter over them is a convenience rather than the feature. What
   solves §1's problem is a single page on which a topic's pages sit together *with their
   quadrants labelled*, which no quadrant landing page can do. The filter earns its keep as
   the corpus grows, and costs almost nothing once the tags exist (§3.6).
2. **One vocabulary, one declaration per item, two declaration sites.** sphinx-gallery
   reads `# sphinx_gallery_tags` from an example's source and nothing else will, so gallery
   tags stay where they are (gallery spec §3.6). Narrative pages declare in page metadata.
   Neither is copied into a registry, because a registry that restates a declaration is a
   second thing to keep true (§3.2).
3. **Promotion is not deletion.** A term earns a *button* by spanning two or more quadrants
   and selecting under half the corpus. A term that earns no button still exists, still
   tags its pages, and still drives the gallery's own filter. Deleting unpromoted terms
   would strip `barbs` and `overlay` from the gallery filter that needs them, and would
   blind the coverage report to exactly the terms whose promotion is the signal worth
   watching (§3.4).
4. **Both thresholds are relative, so the taxonomy tracks the corpus.** Two quadrants is a
   count because there are only ever four; the breadth cap is a fraction. Neither is a
   number anyone edits as the documentation grows, which is what makes the rule survive
   the growth it is designed for.
5. **The rule is gated; its output is not.** Freezing the promoted set as a baseline would
   fail CI on every new page that legitimately changes it, which inverts decision 4. What
   the gate asserts is that the rule was applied correctly (§3.7).
6. **An empty cell in the coverage matrix is a question, not a defect.** Diátaxis does not
   require every topic in every quadrant. The matrix belongs in a report a human reads, and
   never in a gate, because a documentation gate that manufactures work makes the
   documentation worse (§3.8).
7. **No new dependency.** `sphinx-tags` was rejected on 2026-08-20 and stays rejected, for
   a reason that has outlived the premises of the original rejection (§5).

(topics-spec-3)=
## 3. Architecture

(topics-spec-3-1)=
### 3.1 The corpus

Nineteen items: the fourteen narrative pages of the tutorials, how-to and explanation
quadrants, and the five gallery examples.

The reference quadrant is out. Its pages — the glossary, the CLI and configuration
references, the bibliography, the changelog — are lookup surfaces a reader reaches by name,
and the generated API is ninety-four objects that would dominate any filter built over the
same buttons. The developer section is out for the reason its landing cards are: {issue}`66`
is expected to change which pages exist there, and tagging a set about to be rewritten
files the wrong set.

The corpus is **discovered, not listed**. Every published page under the three narrative
quadrants must carry tags, so a page added tomorrow fails the gate until it declares them.
A hand-maintained list is one a new page silently misses, which is the failure mode
reading spec §3.6 already reasons about for its own coverage gate.

(topics-spec-3-2)=
### 3.2 Where tags are declared

**Gallery examples** keep `# sphinx_gallery_tags = [...]` in the example source, unchanged.
gallery spec §3.6 records why that is the single declaration: it is the only spelling
sphinx-gallery reads, a misspelling is discarded in silence, and `remove_config_comments`
keeps the flag off the rendered page.

**Narrative pages** declare an rST field list on the **first line of the file**, above
the `.. _label:` target where there is one:

```rst
:tags: units, sounding

.. _howto-units:

Work With Units
===============

.. readingtime::
```

The position is the whole rule, and it was measured rather than reasoned. Sphinx's
metadata collector lifts a docinfo field list into `env.metadata[docname]` and removes it
from the doctree — so it renders nothing, which matters here specifically, because a
rendering directive would have to coexist with the `readingtime` banner at the top of
these same pages. But it does that only for a field list **preceding every other piece of
markup**. A field list written under the title, which this section first proposed, leaves
`env.metadata` empty and renders a visible definition list at the reader: the exact
failure this section named as its risk. Measured on 2026-09-03 against a build in the
`docs` environment, in three placements. `env.metadata` holds the field body as one
string, `{'tags': 'units, sounding'}`, so the adapter splits on commas.

The declaration has one consequence outside Sphinx. `check_glossary_links.py` reads a
page's lines as narrative prose and requires the first mention of a glossary term to
carry `:term:`; a `:tags:` line scanned as prose makes the tag list that first mention,
and demands a role a docinfo field list cannot carry. Four vocabulary terms are also
glossary spellings — `isopleths`, `parcel`, `projection`, `sounding` — so this is not a
corner case; measured over the tagged corpus, the unfixed gate reported sixteen unlinked
mentions across thirteen of the fourteen pages, every one of them the `:tags:` line
itself. `prose()` therefore skips a leading field list, in the same category as the rule
it already carries for a directive's options and body.

(topics-spec-3-3)=
### 3.3 The vocabulary

Seventeen terms, closed. Each is defined by what it covers **and what it excludes**,
because the boundary is the part a contributor needs: a term with no stated edge is one two
people apply differently, and the gate of §3.7 cannot see that — both spellings are legal.
This table is the authority when they disagree.

| term | covers | not |
|---|---|---|
| `analysis` | deriving quantities from an ascent: lifting a parcel, computing stability | the named numbers themselves (`indices`), the drawing of the result (`shading`) |
| `barbs` | the wind column drawn deliberately — an explicit `plot_barbs`, or prose about staffs and spacing | a page whose sounding carries wind it never draws or discusses |
| `branding` | the tephpy logo and its placement | general figure decoration (`labels`) |
| `config` | the configuration file, its discovery, precedence and lifecycle | styling done in a call rather than a file (`styling`) |
| `data-input` | getting an ascent *into* tephpy: dataframes, datasets, archives, file formats, decoders | what the resulting object is (`sounding`) |
| `diagram` | the canvas: axes, extent, framing, composition, output | the isopleth families drawn on it (`isopleths`) |
| `indices` | named derived numbers — CAPE, CIN, LCL, LFC, EL — and their display | the computation that produced them (`analysis`) |
| `isopleths` | the five families as such: intervals, emphasis, which are drawn | the coordinate system they live in (`projection`) |
| `labels` | axis titles, edge labels, annotation, legends | the logo (`branding`) |
| `metpy` | where MetPy is the subject — what is delegated to it and why | a page that merely imports it |
| `overlay` | drawing more than one ascent, or one ascent more than once, on shared axes | composing separate axes side by side (`diagram`) |
| `parcel` | the parcel path itself: ascent, Normand's point, the LCL construction | the energies shaded from it (`shading`) |
| `projection` | the T–ln θ coordinate system and the rotation: why the axes sit as they do | the families drawn in it (`isopleths`) |
| `shading` | filled regions between traces — CAPE, CIN — and how they are drawn | the numbers those areas equal (`indices`) |
| `sounding` | the observed ascent as an object: what it holds, how it is labelled and plotted | how it was obtained (`data-input`) |
| `styling` | appearance set through a call: colour, dashes, weight, emphasis tiers | the same set through a file (`config`) |
| `units` | pint quantities at the API boundary: what goes in, what comes back, what is rejected | the physical quantities themselves |

Nine of those are gallery spec §3.6's, unchanged. Eight are new. They name subjects the
narrative quadrants cover; `parcel` is the one that also has gallery content
(`plot_parcel_analysis`), which carries the subject under `analysis` rather than under a
term of its own.

Closed, for gallery spec §3.6's reason, which generalises without amendment: a `barb`
button beside a `barbs` one splits the very index the feature exists to build. The
vocabulary grows deliberately — a contributor writes a page, finds no term fits *against
the table above*, the gate of §3.7 rejects the unknown term, and a term is added with a
decision and a definition behind it. A term added without an entry in that table is the
drift the closure exists to prevent, so the two land together. That is
the growth mechanism, and it is why §3.8's report does not attempt to infer candidate terms
from word frequency.

Each item declares **two to four** tags, gallery spec §3.6's own bound: one tag files an
item under a single button, and a full house files it under every one, either way telling
the filter nothing.

(topics-spec-3-4)=
### 3.4 Promotion

A term earns a button on the discovery page when **both** hold:

- it appears in **two or more quadrants**, and
- it selects **fewer than half** the items in the corpus.

The first is the point of the feature: a term confined to one quadrant describes something
browsing that quadrant already solves. The second is what stops a term so common it
discriminates nothing from presenting itself as a filter.

Both conditions are needed, and the corpus of 2026-09-03 demonstrates each failing alone.
`barbs` appears in two gallery examples and no narrative page, so it fails the first while
passing the second. `sounding` appears in twelve of nineteen items across three quadrants,
so it passes the first and fails the second — a button returning sixty-three per cent of
the corpus is not a filter.

Measured against the tagging of §6.1, eight terms promote:

| term | items | quadrants |
|---|---|---|
| `diagram` | 6 | all four |
| `isopleths` | 6 | all four |
| `data-input` | 4 | how-tos, tutorials |
| `analysis` | 3 | explanation, gallery, tutorials |
| `shading` | 3 | explanation, gallery, tutorials |
| `indices` | 2 | gallery, tutorials |
| `metpy` | 2 | explanation, gallery |
| `parcel` | 2 | explanation, how-tos |

Nine are held back: `sounding` as too broad, and `barbs`, `branding`, `config`, `labels`,
`overlay`, `projection`, `styling` and `units` as single-quadrant.

That `units` and `config` are held back is a real cost and is recorded as one. "How do I
work with units" is a question a new reader genuinely arrives with, and the rule gives it
no button. The rule is a testable proxy for "is this a useful facet", and on this corpus
the proxy is imperfect at both ends. It is kept because the alternative — an editorially
curated button list — is not testable at all, and because the failure is self-correcting:
`units` promotes itself the moment a tutorial or explanation page touches units, with no
one editing a list.

(topics-spec-3-5)=
### 3.5 Two modules, split on the Sphinx boundary

The taxonomy is data and a pure function; the extension is only the Sphinx adapter. The
split follows reading spec §3.1, and here it is load-bearing for a second reason.

`tests/test_readingtime_directive.py` guards itself with `pytest.importorskip("sphinx")`,
so an extension test *skips* in the `test-py3*` environments the CI matrix runs. The
existing tag assertions do not: gallery spec §3.7 has them read the example source as text
precisely so they run everywhere. Putting the vocabulary inside a Sphinx extension would
therefore make an existing gate start skipping across the matrix — weakening a gate as a
side effect of extending it.

**`docs/src/_ext/tephpy_topics_data.py`** imports nothing outside the standard library. It
holds the vocabulary of §3.3, the `sphinx_gallery_tags` pattern, and the promotion rule of
§3.4 as a pure function over `{item: (quadrant, tags)}`. The vocabulary currently declared
in `tests/examples/test_examples.py` **moves** here rather than being copied, so this
removes a duplication rather than creating one.

**`docs/src/_ext/tephpy_topics.py`** is the adapter: it reads `env.metadata` for narrative
tags, reads the five example sources for gallery tags, computes the promoted set, and emits
the page of §3.6.

Tests import the data module by path, using the mechanism already in
`tests/test_readingtime_directive.py` but without the `importorskip`, so the gate of §3.7
runs on every supported Python. The promotion rule being pure is what allows both of its
boundaries — exactly two quadrants, exactly half the corpus — to be asserted from fixtures
with no documentation build.

(topics-spec-3-6)=
### 3.6 The page

A single published page, reached from the root toctree.

It gets **no landing-page card**. gallery spec §5 ruled that the landing grid is the four
Diátaxis quadrants and that anything sitting in it reads as a fifth; that reasoning
transfers unchanged, and this page is a way into all four rather than a peer of them.

It lists every item in the corpus with its quadrant labelled and its tags shown, and offers
the promoted terms of §3.4 as filter buttons. Filtering is client-side over `data-topics`
attributes — the shape sphinx-gallery's own `sg-tags.js` already demonstrates — so it needs
no dependency and degrades to the full list with scripting off, which is the list that
decision 1 says is the actual feature.

The selection is reflected in a `?topics=` query parameter, mirroring sphinx-gallery's
`?sg-tags=`, so a filtered view can be linked to from an issue or a reply.

(topics-spec-3-7)=
### 3.7 The gate

`tests/test_docs_topics.py`, running on every supported Python:

1. Every page in the corpus of §3.1 declares two to four tags.
2. Every declared tag is in the vocabulary of §3.3.
3. Every vocabulary term is used by at least one item — a term nothing uses is a typo or
   the residue of a deleted page.
4. The corpus is discovered, so a new narrative page with no tags fails (§3.1).
5. The promotion rule is asserted at both boundaries against fixtures (§3.5).

What the gate deliberately does **not** assert is which terms are promoted. Recording that
set as a baseline would fail CI on every page that legitimately changes it — write a units
tutorial and the build breaks because `units` newly qualifies — which inverts decision 4.

That cuts against this project's habit, and the difference is worth stating. plots spec §3.5
freezes the figure baselines so that a change is visible in review. Those freeze things that change *unintentionally*. A promotion
change is always downstream of deliberate editorial work and is reported by §3.8 in any
case, so freezing it would buy visibility that already exists at the price of a false
failure.

(topics-spec-3-8)=
### 3.8 The report

`.github/scripts/topics_issue.py`, run by a scheduled workflow, modelled on
`floors_issue.py` and `ci-floors.yml` — including the `MARKER` dedupe, so a standing
finding updates its issue instead of filing another one each run.

It carries two things:

- **Promotion changes** since the last run: terms newly promoted, terms newly held back.
  This is what makes §3.4's relative thresholds observable rather than merely correct.
- **The coverage matrix**: for each term, which quadrants hold it and which do not.

The matrix is the report's second job and arguably its better one. On the corpus of
2026-09-03 it already says something actionable: `analysis` and `shading` both appear in
tutorials, explanation and the gallery and in **no how-to**, which is conspicuous in a
project whose how-to quadrant is its largest at nine pages.

Two limits are recorded here so the report is not read for more than it says. An empty cell
is a candidate for editorial judgement and not a defect (decision 6). And the matrix can
only see gaps *between subjects already written about*: the vocabulary is closed, so a
topic nobody has documented carries no term and appears nowhere. The instrument for that
gap is user demand, not coverage — {issue}`261` tracks Read the Docs search analytics,
whose zero-result queries are the complement to this matrix.

**Monthly**, not weekly. A documentation corpus moves on pull-request timescales, and a
weekly report that says nothing most weeks is one nobody reads.

(topics-spec-4)=
## 4. Companion changes

The page is a new published page, and this project keeps one set in several hand-written
places. The registration sites are enumerated here so the set is visible in one place:

| File | What it gains |
|---|---|
| `docs/src/index.rst` | the toctree entry |
| `tests/test_docs_readingtime.py` | an `EXEMPT` entry — the page is navigated, not read |
| the reading-time specification | reading spec §3.7's exemption table, and its carrying-page count |
| `docs/src/developer/specs/index.rst` | the `topics spec §…` row and the toctree entry |
| `tests/examples/test_examples.py` | its `VOCABULARY` moves out to the module of §3.5 |
| `docs/src/_static/tephpy.css` | the filter button and badge styling |
| `docs/src/conf.py` | the extension in `extensions` |
| `docs/src/_static/topics.js` | the filter, registered by the extension rather than by `conf.py` |
| `docs/src/developer/docs-style.rst` | the "Topic Tags" section, the vocabulary's new home in "Gallery Examples", and the topic index in the "Reading Time" exemption sentence |
| `.github/scripts/check_glossary_links.py` | a leading docinfo field list is metadata, not prose (§3.2) |
| `tests/ext_modules.py` | the shared `_ext` loader, so the vocabulary's move does not add a third copy of it |
| `tests/test_floors.py` | its `GUARDED` tuple, so `tests/test_topics_issue.py`'s sdist guard is checked the same way the other `.github`-script tests' are |

The reading-time exemption set (reading spec §3.7) is written in **four** places, not
three: `tests/test_docs_readingtime.py`'s `EXEMPT` tuple, reading spec §3.7's exemption
table, reading spec §3.7's own carrying-page count — the "That leaves … pages carrying
the directive" sentence, which restates the same set as arithmetic and does not update
itself when the table does — and `docs-style.rst`'s "Reading Time" prose.

The fourteen narrative pages each gain a `:tags:` field list. The five example files are
untouched.

(topics-spec-5)=
## 5. Alternatives considered

**`sphinx-tags`.** Rejected on 2026-08-20 (gallery spec §7) on two premises that have since
changed: that it duplicated a feature already installed, and that a five-example gallery did
not need site-wide tag pages. There is now a genuine cross-quadrant corpus. It stays
rejected on a premise that has *not* changed: sphinx-gallery locks its tags into the example
source, so sphinx-tags would need a second declaration on the gallery pages, leaving two tag
mechanisms live at once with nothing to say which an item's tags feed — the precise
objection gallery spec §3.6 raised. It also produces per-tag *pages* rather than one
filtered index, and the rule of §3.4 is not expressible in it. **This was reasoned rather
than probed**; §8 records that.

**A script generating a static page.** Simpler, with no Sphinx API surface. Rejected
because it writes source into the tree, which this project avoids deliberately — `gallery/`
is generated *and* untracked so that nobody hand-edits it — and because a generator the
build then reads is a build-ordering constraint in the Makefile. It saves less than it
appears to, since the filter needs client-side code either way.

**Freezing the promoted set as a baseline.** Rejected in §3.7.

**Inferring candidate vocabulary terms from word frequency.** Considered for §3.8 and cut.
It needs stopword and stemming heuristics to be anything but noise, and it is redundant
with the growth mechanism of §3.3, where the gate rejects an unknown term and a human adds
it deliberately.

**Curating the button list editorially.** Considered when §3.4's proxy was found imperfect
at both ends. Rejected because it replaces a testable rule with a judgement nothing checks,
and because the proxy's failures are self-correcting as the corpus grows.

(topics-spec-6)=
## 6. Testing

(topics-spec-6-1)=
### 6.1 The tagging this document is measured against

The eight-term promoted set of §3.4 is computed from a tagging proposed on 2026-09-03 by
reading each page's title, section headings, `ax.*` calls and glossary references, and
**confirmed on 2026-09-03**: the gallery's five rows are the tags those files already
declare, and the fourteen narrative rows were checked against the covers/not table of
§3.3 as each page gained its `:tags:` field list, revising none of them. The promoted set
of §3.4 therefore now rests on a measurement of the tagged pages rather than on this
table's original proposal.

| quadrant | item | tags |
|---|---|---|
| tutorials | `first-tephigram` | diagram, isopleths, sounding |
| tutorials | `analyse-a-sounding` | analysis, sounding, shading, indices |
| tutorials | `browser-demo` | sounding, data-input |
| how-tos | `build-a-sounding` | sounding, data-input |
| how-tos | `configuration` | config, isopleths |
| how-tos | `emphasis` | isopleths, styling, config |
| how-tos | `framing` | diagram, sounding, parcel |
| how-tos | `label-and-compose` | diagram, labels, isopleths |
| how-tos | `logo` | branding, diagram |
| how-tos | `read-a-sounding` | sounding, data-input |
| how-tos | `temp-and-bufr` | sounding, data-input |
| how-tos | `units` | units, sounding |
| explanation | `parcel-ascent` | analysis, parcel, shading, metpy |
| explanation | `rotated-axes` | diagram, isopleths, projection |
| gallery | `plot_tephigram` | diagram, isopleths |
| gallery | `plot_sounding` | sounding, barbs |
| gallery | `plot_sounding_comparison` | overlay, sounding |
| gallery | `plot_hodograph` | metpy, barbs, sounding |
| gallery | `plot_parcel_analysis` | analysis, shading, indices, sounding |

Two judgements in that table are worth recording because they are contestable. `metpy` is
tagged only on `parcel-ascent`, where MetPy is the subject of a section; it is mentioned in
`units` and `emphasis` in passing and tagging on passing mentions would inflate every count
in §3.4. And no narrative page is tagged `barbs`, because the string does not appear in any
of them — which is what makes `barbs` fail promotion.

(topics-spec-6-2)=
### 6.2 What the gate asserts

The five assertions of §3.7, plus unit tests of the promotion function at both boundaries
from fixtures rather than from the live corpus, so that a documentation change cannot make
a rule test pass or fail for the wrong reason.

(topics-spec-6-3)=
### 6.3 What is not gated

The page's rendering. Whether the filter buttons work is a browser question, and this
project gates correctness of content rather than of presentation. Nothing asserts that the
page carries one `data-topics` attribute per item — that is a property of how `tephpy_topics.py`
constructs the page, not something checked. What the build does assert, at `doctree-resolved`:
`build_corpus` raises if the corpus is empty, and — because the build runs
`--fail-on-warning` — it fails if a narrative page declares no tags, or if its source
declaration disagrees with what Sphinx read into `env.metadata`. The filter itself was
checked by hand on 2026-09-03, against `docs/_build/html/topics.html` loaded as a
`file://` URL, in Chrome for Testing 151.0.7922.34 driven through Playwright. Checked,
and observed to hold:

1. The filter bar appeared with one button per promoted term (eight: `analysis`,
   `data-input`, `diagram`, `indices`, `isopleths`, `metpy`, `parcel`, `shading`), in both
   themes.
2. Clicking a button narrowed the nineteen-item list and marked the button active.
3. A second button narrowed the list further rather than widening it — AND, not OR.
4. `analysis` and `data-input` together, which share no item, showed the empty notice
   rather than a blank list.
5. `clear` appeared on the first selection and restored the full list of nineteen items
   when clicked.
6. Selecting a topic added `?topics=…` to the URL, and reloading that URL restored the
   selection.
7. A hand-written `?topics=nonsense` was ignored: every item stayed listed, no button
   showed as active, and the unrecognised parameter was stripped from the address bar —
   `topics.js` runs `params.delete(PARAM)` whenever the selection is empty, which an
   unrecognised term leaves it.
8. With JavaScript disabled (`browser.new_context(java_script_enabled=False)`), the filter
   bar did not appear and every item was listed.

The check also caught a defect the implementation fixed before this record was written:
Sphinx places an `add_js_file` script in `<head>`, undeferred — the same place it puts
sphinx-gallery's own `sg-tags.js` — so the script runs before `<body>` is parsed. A bare
top-level filter, run at that point, finds `#teph-topic-filter` absent and returns
immediately, forever; `sg-tags.js` avoids this by deferring its own work to
`DOMContentLoaded`, and `topics.js` now does the same.

(topics-spec-7)=
## 7. Scope

**In scope.** The taxonomy module and its vocabulary; the Sphinx extension; the published
page and its filter; the `:tags:` field list on fourteen narrative pages; the pytest gate;
the scheduled report and its script; the companion changes of §4.

**Out of scope.** The reference quadrant and the generated API (§3.1); the developer
section, which waits on {issue}`66`; any change to sphinx-gallery's own filter, which keeps
all seventeen terms including the unpromoted ones; Read the Docs search analytics, tracked
separately as {issue}`261`; and the five example files, whose tags are already correct.

(topics-spec-8)=
## 8. Open items

Tagged per docs spec §3.5.

- **Closed** (2026-09-03) — **the field-list metadata mechanism (§3.2).** Established by
  build: a `:tags:` field list reaches `env.metadata` and renders nothing, but only on
  the first line of the file, not under the title as this document first proposed. §3.2
  carries the measurement and the correction. The fallback directive was not needed.

- **Open** — **`sphinx-tags` was reasoned about rather than probed (§5).** The rejection
  rests on sphinx-gallery locking its tags into the example source, which is documented
  behaviour, but no build was run to confirm sphinx-tags cannot read a generated gallery
  tree. Worth ten minutes if the decision is ever challenged.

- **Open** — **`sounding` returns as a button if the corpus outgrows it.** At twelve of
  nineteen it fails the breadth cap; at twelve of twenty-five it would pass. Whether a term
  that broad is wanted as a button at any corpus size is a judgement §3.8's report will
  surface rather than settle.

- **Deferred** ({issue}`66`) — **the developer section.** Its pages are expected to change,
  and tagging a set about to be rewritten files the wrong set.

- **Deferred** ({issue}`261`) — **Read the Docs search analytics.** The demand signal
  complementing §3.8's coverage matrix, and perishable at ninety days on the Community
  plan, so it is triggered by the announcement rather than by this plan.

(topics-spec-9)=
## 9. References

- gallery spec §3.6 — the closed vocabulary, the flag, and why a registry does not hold tags
- gallery spec §5 — why a way into the quadrants gets no landing-page card
- gallery spec §7 — the original `sphinx-tags` rejection
- narrative spec §3.8 — the rejection §1.1 re-examines
- reading spec §3.1 — the module split of §3.5
- reading spec §3.6, §3.7 — the discovered-corpus gate and the exemption list
- plots spec §3.5 — the frozen baseline §3.7 declines to imitate
- {issue}`66` — the developer and contributor guide
- {issue}`261` — Read the Docs search analytics as an editorial signal
