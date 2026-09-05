# tephpy getting started — design specification

```{readingtime}
```

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. The pages it describes cite it by section — `start spec §3.3` and the like —
> so these sections *are* the reasoning behind what those pages say, and where the two ever
> diverge it is the specification that gets corrected. Read it as current.

- **Date:** 2026-09-05 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `start spec §…` — named for `docs/src/start/`, the directory it
  governs, rather than for "getting started", which would collide in prose with the
  ordinary English phrase and read as a description instead of a citation
- **Scope:** the four on-ramp pages, their landing page, the gate changes that bring them
  under the guarantees the quadrants already carry, and the installation page's
  pre-release admonition
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) —
  `spec §8.6`'s documentation layering, which names the four quadrants and says
  nothing about how a reader reaches them
- **Sibling specs:**
  [`2026-08-27-narrative-quadrants-design.md`](2026-08-27-narrative-quadrants-design.md)
  — `narrative spec §3.9`'s landing-page shape, reused here rather than reinvented;
  [`2026-08-25-scope-and-support-design.md`](2026-08-25-scope-and-support-design.md) —
  §3.1's non-goals statement, which §3.2 below summarises and must not fork

(start-spec-1)=
## 1. Purpose

**tephpy tells nobody how to install it.** Not in the documentation, and not in the
`README.md`, whose only heading is *Non-Goals*. Measured 2026-09-05: no `pip install`,
`conda install` or `pixi add` string exists anywhere a reader can see — the only matches
in the repository are inside `docs/src/developer/plans/`, which `conf.py`'s
`exclude_patterns` keeps out of the build. Meanwhile `.github/workflows/ci-wheels.yml`
carries `publish-pypi` and `publish-testpypi` jobs.

That is the gap this specification closes, and it is a stranger one than it sounds. Every
page the narrative quadrants added — two tutorials, two explanation pages, nine how-tos —
opens by assuming the reader has the package. `tutorials/first-tephigram.rst` says "the
only thing you need is `tephpy` installed" and offers no way to do it. The documentation
is complete from the second step onwards.

{issue}`66` asks for this, filed 2026-08-01 as one issue covering three separate things:
an on-ramp, a contributor guide, and a split of the parent specification's §3.2. Its
survey of where tephpy stood is now stale in every row — the quadrants it calls
index-only hold fourteen pages between them — and it files the on-ramp last, under "also
worth having". The measurement above is the reason this specification takes it first.

This document covers the on-ramp alone. The contributor guide and the §3.2 split remain
{issue}`66`'s, and §6 says so.

(start-spec-2)=
## 2. Decisions

1. **A directory, not four top-level pages.** geovista puts `installation`, `overview`,
   `quick_start` and `next_steps` beside its root index, and {issue}`66` compares against
   that. tephpy's gates discover by directory name, so `docs/src/start/` brings the
   section under each of them by adding one string, where four sibling files would need a
   hand-maintained list of four paths in three places — the shape narrative spec §3.9 was
   written to remove from the landing pages.
2. **The section gets a landing page in narrative spec §3.9's shape.** Not a fifth
   convention: the same introduction, two-column table and hidden ordered toctree, held by
   the same gate. It also buys the section one entry in the header rather than four
   (§3.8).
3. **The quick start shows working code and then gets out of the way.** It is a shop
   window, not a lesson: roughly ten lines, one figure, and a handover to
   *Your First Tephigram*, which teaches the same diagram properly. A quick start that
   taught would be a second tutorial competing with the first.
4. **Its code is executed and its figure compared, like every other user page.** This is
   the decision that costs something — three gates are scoped to the Diátaxis quadrants
   and have to widen (§3.6). The alternative was a page whose ten lines are the first
   thing a reader runs and the only user-facing code in the project that nothing checks.
5. **The installation page matches geovista's page in structure, and adopts its icon
   vocabulary.** Three sections — stable, latest, developer — each offering conda, pip,
   pixi and uv in a synced tab-set. `sphinx-design` 0.7.0 is already installed and
   provides `:sync-group:`, so the behaviour costs no dependency; the tool icons cost one,
   `sphinx-iconify`, and §7 records the question that remains open about it.
6. **The pre-release note is enforced rather than remembered.** tephpy has no tags and
   reports `0.1.0.dev190`, so "is this released?" is decidable offline from
   `tephpy.__version__` alone. §3.7 makes the admonition's presence a function of that
   rather than of somebody's release checklist.

(start-spec-3)=
## 3. Architecture

(start-spec-3-1)=
### 3.1 The section, and its landing page

Five files in `docs/src/start/`:

| page | what it is |
|---|---|
| `index.rst` | the section's landing page — narrative spec §3.9's shape |
| `overview.rst` | what tephpy is, and what it is not |
| `installation.rst` | how to get it, four ways, three states |
| `quick-start.rst` | ten lines and a diagram |
| `next-steps.rst` | where to go once it works |

The landing page carries an introduction and the two-column table of the other four, and
its toctree is hidden and ordered as the table is. It is exempt from the reading-time
banner on reading spec §3.7's rule, as the four quadrant landing pages are, and for the
same reason: nobody reads an index through.

Naming the landing page's own title *Getting Started* rather than *Start* is deliberate;
the directory is short because it appears in every URL under it, and the title is
explicit because it appears in the header.

*Added 2026-09-06.* Each of the four pages carries an `:iconify:` glyph before its title,
from the `mdi` set and distinct from the four §3.3 already spends on that page's own
sections. This is **local to this section and deliberately not a site rule**: the theme
renders a title's icon in the *Section Navigation* sidebar as well, so one page having one
and three not reads as an omission rather than as emphasis. Either every page in a section
carries one or none does. Nothing gates it, because the cost of getting it wrong is a
slightly ragged sidebar and the cost of a gate is a rule the rest of the documentation
would then have to obey.

A name is checked against the Iconify API before it is written. A name that does not
resolve renders **blank, with no build error** — `mdi:signpost` and `devicon:pixi` were
both reached for here and neither exists.

(start-spec-3-2)=
### 3.2 *Overview*

`docs/src/start/overview.rst`. What tephpy draws, what it delegates, and what it declines.

The non-goals are **summarised and linked, never restated**. `README.md` carries the
canonical list under scope spec §3.1, six entries each with somewhere to go instead, and
a second copy in the documentation is a second thing to keep true — which is
{issue}`193`'s defect in a new place. This page says that tephpy delegates thermodynamics
to MetPy and declines the skew-T, the hodograph and BUFR decoding, and links the README's
list for the rest.

It also does the one thing the README cannot: place tephpy against its neighbours for a
reader who has met neither. MetPy owns the skew-T and the thermodynamic maths; tephi is
the ancestor this package reimplements; tephpy draws the tephigram and reads it.

(start-spec-3-3)=
### 3.3 *Installation*

`docs/src/start/installation.rst`. The page {issue}`66` should have led with.

**Three states, four tools, one synced choice.** The page has three sections — **Stable**,
**Latest** and **Developer** — and each offers the same four tools in a `tab-set` carrying
`:sync-group: install`, so a reader who picks pixi in the first section is still in pixi
in the third. That synchronisation is the feature that makes the page usable and it is
`sphinx-design` 0.7.0's, already installed against a `>=0.6.1` floor that already permits
it.

| section | what it installs |
|---|---|
| Stable | the latest release, from conda-forge or PyPI |
| Latest | the development version, from the `main` branch |
| Developer | a working clone, with the pixi environments this repository defines |

The four tools are **conda, pip, pixi and uv**, in that order, with pixi carrying
`:selected:` because it is what this repository develops with and what every `pixi run`
in the documentation assumes. Each stable tab closes with a link to that tool's own
installation instructions, because a reader who has not got the tool cannot use the tab
that assumes it.

The developer section is tephpy's own, not geovista's transposed: the clone, then
`pixi run tests`, `pixi run lint` and `pixi run docs`, which are the three commands
`AGENTS.md` names and the three a first contribution needs.

(start-spec-3-4)=
### 3.4 *Quick start*

`docs/src/start/quick-start.rst`. The shop window of decision 3.

The arc is one block: a figure with the tephigram projection, a sample sounding drawn on
it, and the diagram that results. It ends by handing over — *Your First Tephigram* takes
the same diagram apart line by line — so the two pages stand in a stated relationship
rather than competing.

Its python is executed by `tests/test_docs_snippets.py` and its figure compared against a
`docs/baseline/` image, which is what §3.6 widens the gates for. The page joins
`DOCUMENTED`, `PUBLISHES_FIGURES` and `check_docs_figures.py::PUBLISHES`: three membership
lists for one page, which narrative spec §4 already records the cost of.

(start-spec-3-5)=
### 3.5 *Next steps*

`docs/src/start/next-steps.rst`. Where a reader goes once the quick start has worked.

The four quadrants and the gallery, each with the sentence that says who it is for — which
is the same editorial job a landing-table row does, one level up. It is the only page in
the section that is purely signposting, and it is a page rather than a paragraph on the
quick start because a reader who arrives already installed should be able to reach it
without reading the quick start first.

(start-spec-3-6)=
### 3.6 The gates, and the constant that stops being true

Six constants in this repository name the Diátaxis quadrants. **Four widen to include
`start`; two do not**, and the reason differs for each:

| constant | widens | why |
|---|---|---|
| `tests/test_docs_snippets.py::QUADRANTS` | yes | the quick start's code is executed |
| `.github/scripts/check_docs_figures.py::QUADRANTS` | yes | its figure is compared to a baseline |
| `.github/scripts/check_glossary_links.py::QUADRANTS` | yes | its prose names glossary terms |
| `tests/test_docs_landing_pages.py::QUADRANTS` | yes | the section's landing page is `narrative spec §3.9`'s shape |
| `docs/src/_ext/tephpy_topics_data.py::QUADRANTS` | **no** | the on-ramp is the way in, not corpus to browse by topic; its pages declare no `:tags:` |
| `tests/test_glossary_links.py` | **no** | it reads the gate's own tuple, so it follows the *widening* without an edit — though the **rename** touched it, because it names the constant |
| `tests/test_docs_figures.py` | **no** | the same, and this table missed it when first written: it reads `gate.QUADRANTS` too, so the rename touched two mirrors rather than one |

Each of the four is named `QUADRANTS` and documented as the Diátaxis quadrants. A fifth
name makes both the identifier and its comment false, so **each is renamed and its comment
rewritten in the same change**. The four quadrants are not what those gates are about;
what they are about is the pages written for users, which is a set the on-ramp joins.

No test asserts the length of any of these tuples, checked 2026-09-05, so widening them
breaks no count. The gates assert instead that every directory they name exists, which is
the right shape and needs no change.

(start-spec-3-7)=
### 3.7 The pre-release admonition, and the gate that retires it

tephpy has cut no release. The installation page nevertheless documents installing the
released package, because a page that described only the development install would have
to be rewritten rather than edited at v0.1.0.

The page therefore opens with a note saying the commands do not work yet. That note is a
claim about the world, and this project does not leave those to memory: a test reads
`tephpy.__version__` and asserts the note is present exactly while tephpy has never been
released.

*Corrected 2026-09-05 in review.* This section first specified that test as "while the
version carries `.dev`", which answers a different question — whether this checkout sits
exactly on a tag — and deadlocks on the real one. setuptools_scm reports `0.1.0.dev190`
before the first tag, `0.1.0` on it, and `0.1.1.dev1` on the very next commit. A `.dev`
test reads that third state as unreleased and demands the now-false note back, and there
is no commit at which the note could be removed, because removing it happens on a `.dev`
commit too. The signal is therefore a comparison against the first release,
`Version(tephpy.__version__) >= Version("0.1.0")`: `packaging` sorts `0.1.0.dev190` below
it and both `0.1.0` and `0.1.1.dev1` above. `tests/test_docs_installation.py`
parametrises that sequence so the deadlock cannot return.

It is offline, which spec §8.5 requires — nothing queries PyPI to ask whether the package
is there. It reads the version of the installed package, which in every environment that
runs the suite is this checkout. `packaging` is already a member of the `test` extra, so
the comparison adds no dependency.

The failure it produces on the release commit is the intended behaviour and not a
side effect: the tag is cut, the test fails, the note comes out, and the page is true
again. A comment in the test says so, because a future reader meeting a red test on a
release day should not have to infer it.

(start-spec-3-8)=
### 3.8 Navigation, and why the header decides the shape

pydata-sphinx-theme shows five links in the header and moves the rest into a *More*
dropdown; `header_links_before_dropdown` is unset, so that default stands. Measured on the
built site 2026-09-05: seven top-level entries exist, five are visible — Tutorials,
How-To Guides, Explanation, Reference, Examples Gallery — and *Browse by Topic* and
*Developer Guide* are already in the dropdown.

Four new top-level entries would take that to eleven and push *Reference* and
*Examples Gallery* into the dropdown behind them. The section's landing page limits that
to one new entry, *Getting Started*, first in the root toctree, with the four pages below
it in the sidebar.

*Corrected 2026-09-05 from the implementation.* The landing page **reduces** the
displacement; it does not prevent it. Measured after the section landed: one new entry is
enough to push *Examples Gallery* into the dropdown, because the theme still shows five.
`html_theme_options["header_links_before_dropdown"]` is therefore set to **6**, and all
six section entries stay visible. The landing page remains the right shape — four new
entries would have needed nine, which is a navigation bar rather than a header — but the
number moved with it rather than the gallery being demoted as a side effect.

This is the second reason for the landing page of §3.1, and it is the one that would
survive even if the first were waived.

(start-spec-4)=
## 4. Companion changes

- `docs/src/index.rst` — the root toctree gains `start/index` **first**, so the section
  leads the header and the previous/next chain starts at the on-ramp.
- `pyproject.toml` — `sphinx-iconify` joins the docs feature's `pypi-dependencies`, with
  a floor; it has no conda-forge package. **And `requirements/pypi-optional-docs.txt`**,
  which is what `[project.optional-dependencies].docs` is generated from: the pixi table
  and that file are two parallel lists, as `playwright` already demonstrates, and
  populating only the first leaves `pip install ".[docs]"` without an extension
  `conf.py` imports. Found in review rather than by this specification.
- `docs/src/conf.py` — `sphinx_iconify` joins `extensions`, and
  `html_theme_options["header_links_before_dropdown"]` is set to 6 (§3.8, as corrected).
- `tests/test_docs_readingtime.py` — `start/index.rst` joins `EXEMPT` with its reason;
  the other four pages carry banners and need no entry, because the corpus is derived.
- `docs/src/developer/specs/index.rst` — the prefix table gains a `start spec §…` row,
  **and its toctree the matching entry**. The two are separate hand-written lists on one
  page, and writing the row without the entry fails the build with `document isn't
  included in any toctree` — which is what happened while this specification was being
  written, and is the divergence `narrative spec §3.9`'s gate exists to prevent one
  directory over. §7 records it.
- `narrative spec §3.9` and `docs/src/developer/docs-style.rst`
  — both describe the landing shape as a *quadrant* landing page, which this section makes
  incomplete. Each gains a sentence saying the shape is not quadrant-only and citing
  `start spec §3.1`. The rule does not change; what changes is the set it is stated over.
- `docs/baseline/` — one baseline for the quick start's figure, generated rather than
  hand-written.
- `README.md` — an installation section is **not** part of this specification; §7 records
  the question.

(start-spec-5)=
## 5. Testing

| what lands | what holds it |
|---|---|
| the quick start's python | `tests/test_docs_snippets.py`, once §3.6 widens its sweep — one script, on every supported Python |
| the quick start's figure | `check_docs_figures.py` against its `docs/baseline/` baseline within RMS 2 |
| the landing page's table against its toctree | `tests/test_docs_landing_pages.py`, once §3.6 widens its sweep |
| every `:term:` on the four pages | `check_glossary_links.py`, once §3.6 widens its sweep |
| the four read pages carrying a reading-time banner | `tests/test_docs_readingtime.py`, already derived over the whole tree |
| the pre-release note matching the version | a new assertion, §3.7 |
| every `start spec §…` citation | the pre-commit anchor check and `check_rendered_citations.py` |
| the prose | review, against docs-style's *Reviewing Claims* |

One new assertion, and four existing gates widened. That ratio is the point of decision 1:
the section is held by machinery that already exists, and joins it by naming a directory.

(start-spec-6)=
## 6. Scope

**In scope.** The five pages of §3.1–§3.5, the quick start's baseline, the gate changes
and renames of §3.6, the admonition and its assertion of §3.7, the navigation change of
§3.8, and the companion changes of §4.

**Out of scope.** {issue}`66`'s other two halves: the developer and contributor guide, and
the split of the parent specification's §3.2 into a `plotting` tour. Both are separately
scoped and neither is a prerequisite of this one. The reference quadrant's landing page,
which narrative spec §7 holds open. Any change to the non-goals themselves, which are
scope spec §3.1's.

**Tranches.** *Corrected 2026-09-05 from the implementation.* The **rename** goes first
and alone, which is what is provably behaviour-preserving: 2177 tests passed before it and
2177 after. The **widening** cannot precede the pages — `tests/test_docs_landing_pages.py`
and `tests/test_glossary_links.py` each assert every section they name is a directory on
disk, and widening either before `docs/src/start/` exists fails with `start is missing`.
So each widening lands with the pages it governs, and the section's landing table grows a
row as each page arrives rather than naming pages that do not yet exist.

(start-spec-7)=
## 7. Open items

Tagged per docs spec §3.5.

- **Closed 2026-09-05** — `sphinx-iconify` does **not** embed its icons. Measured against
  a probe build and then against this project's own: it emits `<iconify-icon>` elements —
  the built installation page carries 52 of them and no inline `<svg>` — and adds one
  script tag, `https://code.iconify.design/iconify-icon/3.0.1/iconify-icon.min.js`. Loaded
  in Chromium with every request captured, a page with two icons made three external
  calls: that script, and one `api.iconify.design` request per icon collection. So the
  installation page costs each reader a third-party script and per-collection data
  fetches, at read time. That is a departure from tooltip spec §3.3, which switched off
  tippy's three network-reaching sources so this documentation neither builds nor reads
  over the network — made knowingly, for parity with the page {issue}`66` names as the
  bar. `iconify_script_url` is a configuration value defaulting to that CDN, so the script
  could be vendored into `_static`; the data fetches belong to the web component and the
  extension exposes no control over them. Revisit if the cost proves unwelcome.
- **Open, not blocking** — whether the specification collection's own index should be
  held by `tests/test_docs_landing_pages.py`. It carries a hand-written prefix table and a
  hand-written toctree over the same sixteen documents, and they can disagree: writing one
  without the other is a mistake made once already, during this specification. The build
  catches the direction that leaves a document unreachable and says nothing about a table
  row naming a document the toctree omits. Not taken here because the gate's rows are
  `:doc:` links and the prefix table's second column is one, which may or may not survive
  contact with the parser.
- **Open** — whether `README.md` gains an installation section pointing at this page. It
  is the same reader arriving by a different door, and the README currently sends them
  nowhere. Out of scope above because the README is scope spec §3.1's surface and this
  specification should not edit it in passing.

(start-spec-8)=
## 8. References

- {issue}`66` — populate the Diátaxis quadrants and build out a developer guide
- {issue}`193` — documentation states capabilities that nothing verifies
- [geovista's installation page](https://github.com/bjlittle/geovista/blob/main/docs/src/installation.rst)
  — the structure §3.3 matches: three states, four tools, one synced group
- [Diátaxis](https://diataxis.fr/) — the framework spec §8.6 adopts
