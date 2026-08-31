# tephpy reading time — design specification

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. The extension, the gate and the style rule it describes cite it by section —
> `reading spec §3.4` and the like — so these sections *are* the reasoning behind what that
> code does, and where the two ever diverge it is the specification that gets corrected.
> Read it as current.

- **Date:** 2026-08-31 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `reading spec §…` — the subject is the reader's time, not the
  banner. `readingtime spec` was rejected for naming the directive rather than the
  convention, and `time spec` for reading as though it were about datetimes, of which this
  package has several
- **Scope:** one Sphinx extension in two modules, one stylesheet rule, one pytest gate, two
  bibliography entries, a `docs-style` section, and the directive added to 29 published
  pages; no change to `src/tephpy/`
- **Parent spec:** [`2026-08-03-published-specs-design.md`](2026-08-03-published-specs-design.md)
  — docs spec §3.1 is the layout that decides which pages exist, and docs spec §3.9 is the
  gate this one is modelled on
- **Sibling spec:** [`2026-08-27-narrative-quadrants-design.md`](2026-08-27-narrative-quadrants-design.md)
  — narrative spec §3.1 is why a tutorial is read start to finish, which is the reader this
  banner is for
- **Prior art:** GeoVista [#2307](https://github.com/bjlittle/geovista/pull/2307) and
  [#2313](https://github.com/bjlittle/geovista/pull/2313), which introduced the directive this one is
  descended from. §5 records what was taken and what was not

(reading-spec-1)=
## 1. Purpose

A reader arriving on a tephpy page cannot tell what it will cost them. *Your First
Tephigram* and the parent design specification are both "a page"; one is a sitting and the
other is an afternoon, and nothing on either says so. The reader most affected is the one
narrative spec §3.1 was written for — someone who does not yet know what is possible, and
who is deciding whether to start.

The estimate is cheap to produce and the decision it supports is real, so the question is
not whether to show it but whether it can be trusted. Two things make an untrustworthy
estimate worse than none: counting something other than what the reader reads, and
appearing on some pages but not others, so that a page with no banner is ambiguous between
"short" and "nobody got round to it".

This specification answers both. §3.3 counts the parsed document rather than its source,
and §3.6 makes the banner's absence a build-time failure rather than an omission, with
§3.7's exemptions named and defended one at a time.

(reading-spec-2)=
## 2. Decisions

1. **The count comes from the parsed doctree, not the source file.** The prior art reads
   the `.rst` off disk and counts `\w+`. On tephpy that counts `:context: reset`,
   `:filename-prefix:`, comment blocks and MyST front matter as words the reader reads.
   Measured on 2026-08-31 with the prior art's own `\w+` pattern, it reports **87** words
   for `reference/config.rst` against **1,715** in the body that page generates — a
   twentyfold understatement. §3.3 records the mechanism and what it was measured doing.
2. **One rate for prose and code alike, at 150 wpm.** §3.4 gives the authority. A split
   rate was considered and rejected: the prose half would be citable and the code half
   would be a judgement call wearing a number, and two knobs would have to be documented,
   tested and defended instead of one.
3. **Every page carries it, or is named as not carrying it.** The exemption list is
   explicit and short, and each entry states its reason (§3.7). A rule with a silent
   escape hatch is the failure mode docs spec §3.9 names when it declines to allow a page
   to opt out of snippet execution.
4. **The gate is a pytest module reading text, not a Sphinx build hook.** Sphinx is in the
   `docs` pixi feature and not in `test`, so a build-time check would always-skip in the CI
   matrix. This is the same reasoning `tests/test_docs_snippets.py` records, and it is why
   §3.1 splits the extension in two.
5. **Placement is part of the rule.** The banner sits in the page's lead, before the first
   section heading, because a reader deciding whether to start has not scrolled yet. A
   presence-only rule would let it drift to wherever an author typed it.
6. **The banner is built from docutils nodes, not raw HTML.** The prior art returns a
   single `nodes.raw`, which no non-HTML builder and no text extraction can see. §3.5 keeps
   raw HTML for the icon alone, where it buys something.

(reading-spec-3)=
## 3. Architecture

(reading-spec-3-1)=
### 3.1 Two modules, split on the Sphinx boundary

```
docs/src/_ext/
├── tephpy_reading.py       stdlib only: the rate, the counting, the page scanner
└── tephpy_readingtime.py   the Sphinx directive, the doctree transform, setup()
```

The split is the one `tephpy_citations.py` and `tephpy_citation_xrefs.py` already make, for
the reason that module's docstring states: nothing in the lower half is imported from
outside the standard library, so it runs in the CI test matrix, which carries no Sphinx.

What that buys here is that decision 4's gate and the directive share one definition of
what a word is and what the default rate is. Two copies would agree until one was amended,
and a gate that counted differently from the banner it polices would be checking a
different page than the one it published.

`tephpy_reading.py` holds `WPM`, `count_words(text)`, `estimate_minutes(words, wpm)`, the
argument grammar of §3.2 and the page scanner of §3.6. `tephpy_readingtime.py` holds the
directive, the `doctree-read` handler and `setup()`, and is registered in
`docs/src/conf.py` beside `tephpy_config_reference`.

The `tephpy_` prefix on both claims a top-level name this repository owns, because
`docs/src/_ext` sits at `sys.path[0]` for the whole build ({issue}`92`).

(reading-spec-3-2)=
### 3.2 The directive and its argument

```rst
.. readingtime::
.. readingtime:: 30
.. readingtime:: 200wpm
```

One optional argument, in one of two shapes:

- **`<N>`** — a literal duration in minutes. The page quotes it and nothing is counted.
  This is the escape hatch for a page whose estimate is wrong for a reason the counter
  cannot see: a tutorial whose reader stops to run every snippet takes longer than its
  words suggest.
- **`<N>wpm`** — a rate override for this page only. The count still happens.

The grammar is anchored at both ends, and an argument matching neither shape is a directive
error rather than a silent fallback. The prior art falls back to computing an estimate when
`int()` raises, so `.. readingtime:: thirty` publishes a number the author did not ask for
and never sees a warning. The docs build is `--fail-on-warning`, so an error here stops the
build, which is the correct treatment of a page whose author asked for something the
directive did not understand.

`run()` returns a single placeholder element carrying the parsed argument and no text. It
is **deliberately not registered** with `app.add_node()`. Measured on 2026-08-31 against a
minimal project: with the transform disconnected, the leaked placeholder produces
`WARNING: unknown node type: <readingtime: >` and Sphinx exits non-zero, which
`--fail-on-warning` turns into a build failure. Registering the node would buy a blank
where the banner should be, published quietly.

(reading-spec-3-3)=
### 3.3 What gets counted

A `doctree-read` handler finds the placeholders, counts the document, and replaces each
with the banner of §3.5. The event fires once per document after it is parsed, so the count
is of the whole page and nothing crosses a document boundary.

Counted: every `nodes.Text` in the parsed document. Skipped: text descended from
`system_message`, `comment` or `raw`. The word pattern is `\w+`, taken from the prior art
and kept because a shared definition matters more than a better one — §3.6's gate does not
count words, but §6's tests pin this one.

Three consequences of counting the doctree that the source-file approach does not have, and
all three are why decision 1 went this way:

- **Directive markup is not words.** Option lines, `:term:` role syntax and comment blocks
  are structure the reader never sees.
- **Generated content is counted.** `reference/config.rst` is 87 words of source and a
  1,715-word options reference once `tephpy-config-options` has run (measured 2026-08-31;
  both figures track the option tables and are quoted as a ratio, not as a target). That
  page is exempt under §3.7 for a different reason, but the how-to pages carrying
  `.. plot::` blocks are not, and their rendered source listings are part of what a reader
  works through.
- **`.. include::` is resolved.** Included text is in the doctree and would be invisible to
  a reader of the source file. No page uses it today; the point is that adding one would
  not silently shrink its estimate.

Verified on 2026-08-31 against a probe page whose reader-visible words number exactly
twenty — a title, a sentence of ten, a three-name code block, a section heading and a
closing line of three, plus an eight-word `..` comment. The handler returned **20**: the
comment excluded, the code included, the title counted once and not twice.

Per-page minute figures are deliberately not tabulated here. They track the prose, and
docs spec §4 rules out a figure that has to be re-measured to stay true.

(reading-spec-3-4)=
### 3.4 The rate, and the authority behind it

`WPM = 150`, and it is not an invented number.

| source | figure | what it measures |
|---|---|---|
| Brysbaert (2019) | 238 wpm for non-fiction; most adults 175–300 | silent reading of English by adults; meta-analysis of 190 studies and 18,573 participants |
| Carver (1982) | ~300 wpm | the *most efficient* rate for typical college students reading prose |

Both figures describe the same thing: unbroken prose, read for comprehension, with no code
and no figures in it. Brysbaert's 238 is where ordinary adults actually land — the
measurement that displaced the 250–300 numbers repeated in popular writing — and its lower
bound of **175** is the floor for ordinary non-fiction. Carver's ~300 is the rate at which
comprehension per unit time is best, which is faster still.

150 therefore sits below the floor of the range a meta-analysis of 190 studies reports for
ordinary non-fiction prose, and that gap is the whole justification. These pages are not
ordinary non-fiction prose: they alternate argument with matplotlib the reader parses line
by line, and decision 2 counts both at one rate rather than inventing a second. A default
under the floor is the conservative direction to be wrong in — an estimate that overruns
costs a reader a page they would have started, and one that underruns costs them the
sitting they had budgeted.

Where 150 is wrong for a particular page, §3.2's two overrides are the remedy. They are
per-page, so using one is a visible choice in the source rather than a silent adjustment.

**What this section deliberately does not claim.** Carver is widely cited for a set of rate
"gears" — 300 wpm rauding, 200 learning, 138 memorizing — and an earlier draft of this
document rested the 150 default on the 200 figure, as the rate for reading in order to use
the material. That attribution did not survive checking. The secondary source making it
cites `Reading Research Quarterly` 18, 56–58, where the paper runs 56–88; and a second
account of the same paper reports that it differentiates rauding from studying and
memorizing **without giving words-per-minute figures for them**. The gears are most likely
from Carver's later rauding-theory work rather than the 1982 paper, and this specification
does not cite a number to a source it could not read. `refs.bib` carries the two rows of
the table above and nothing else.

Both entries go into `docs/src/refs.bib` and render on the References page. This is what
the bibliography is for: docs-style's rule is to reach for it *where a convention needs an
authority*, and a default deciding a number printed on 29 pages is exactly that. The
`:all:` on the bibliography directive means both render although only `docs-style.rst`
cites them.

(reading-spec-3-5)=
### 3.5 The banner and its styling

The handler emits a `container` with class `reading-time`, holding one paragraph: a raw
HTML `<i class="fa-solid fa-clock">` followed by the text. Rendered, measured on
2026-08-31:

```html
<div class="reading-time docutils container">
<p><i class="fa-solid fa-clock"></i>Estimated reading time: 1 minute</p>
</div>
```

The text carries no leading space of its own: on a non-HTML builder the `raw`
icon node drops out, and a literal space would then open the paragraph with a
stray character. The icon gets its spacing from `.reading-time i { margin-right:
0.5em; }` in the stylesheet instead.

The icon is the one thing that stays raw HTML. pydata-sphinx-theme vendors Font Awesome
Free 7.2.0 as a webfont and emits `<i class="fa-solid …">` elements throughout the built
site, so the tag costs no assets and needs no configuration. The alternative — a CSS
`::before` carrying the glyph — would need `font-family: "Font Awesome 7 Free"` written
into this project's stylesheet, and would break silently on a theme upgrade to Font
Awesome 8. The `<i>` form is version-agnostic and is what the theme itself uses.

The rule lands in `docs/src/_static/tephpy.css`, which is already the site-wide stylesheet,
and colours the banner with **`--pst-color-surface`**, **`--pst-color-accent`** — the left
border — and **`--pst-color-text-muted`**. All three are defined by the theme and all three
follow the light/dark toggle.

That choice is a correction of the prior art rather than a preference. GeoVista's
`readingtime.css` styles the banner with `var(--article-info-bg)` and
`var(--article-info-fg)`; neither variable is defined in any of that project's four
stylesheets, nor anywhere in pydata-sphinx-theme, checked on 2026-08-31. The background
therefore falls back to transparent and the colour to inherited, and only the padding,
border, radius and weight take effect. A CSS custom property that resolves to nothing fails
silently, which is why this specification names the three it uses and says where they come
from.

(reading-spec-3-6)=
### 3.6 The coverage gate

`tests/test_docs_readingtime.py`, modelled on `tests/test_docs_snippets.py` and sharing its
constraint: it reads text, and imports only `tephpy_reading` and the standard library, so it
runs on every Python the project supports.

**The corpus is derived, not declared.** Every `.rst` and `.md` under `docs/src`, less:

| excluded | why |
|---|---|
| `_static/**` | Sphinx adds `html_static_path` to `exclude_patterns` itself; these are assets, not documents |
| `developer/plans/**` | tracked but unpublished (docs spec §3.1) — there is no page to carry a banner |
| `gallery/**` | generated by sphinx-gallery from `src/tephpy/examples` and untracked |
| `reference/generated/**` | generated by autoapi |
| `**/sg_execution_times.rst` | sphinx-gallery timing pages, generated |

The generated trees are excluded because they are not hand-written, which is a different
thing from being exempt: nobody could add the directive to them, and §3.7's list is for
pages an author could have written it on and should not. A companion test asserts that
`developer/plans/**` is genuinely in `conf.py`'s `exclude_patterns`, so the exclusion
tracks the build rather than restating a claim about it.

**The rule.** A page in the corpus and not in §3.7's list must carry at least one
occurrence of the directive at column 0 — `.. readingtime::` in reStructuredText,
a `{readingtime}` fence in MyST — after the page title and before the first section
heading.

Column 0 is load-bearing in both directions. It is what lets `docs-style.rst` demonstrate
the directive inside a `.. code::` block, indented, while carrying a live one in its lead;
and it is what stops a page passing on a mention of the directive it never invokes.

**The MyST half needs its own scanner, and cannot reuse `tephpy_citations.read_lines`.**
That function yields the lines outside a fenced block and consumes the opening rail — but a
MyST directive *is* a fence, and its opening rail is the line carrying `{readingtime}`. A
fence-skipping reader is structurally unable to see the thing this gate looks for. The
scanner in `tephpy_reading.py` therefore tracks fences itself, in order to report a
directive fence at column 0 rather than to skip past one. It keeps the rail discipline
`read_lines` documents: a fence closes only on a rail of the same character, at least as
long, carrying no info string.

**Finding the first section heading.** In MyST, the first line matching `^## `. In
reStructuredText, the second underline: the first marks the page title, and a page with no
sections at all has only one, in which case anywhere after the title qualifies.

(reading-spec-3-7)=
### 3.7 The exemptions

Twelve pages, in three groups. The rule behind the list is one sentence: **a page is exempt
when it is navigated rather than read.**

| exempt | group | reason |
|---|---|---|
| `index.rst` | landing | the site landing page: a card grid and a toctree |
| `tutorials/index.rst` | landing | quadrant landing page |
| `howtos/index.rst` | landing | quadrant landing page |
| `explanation/index.rst` | landing | quadrant landing page |
| `reference/index.rst` | landing | quadrant landing page |
| `developer/index.rst` | landing | section landing page: a heading and a toctree |
| `developer/specs/index.rst` | landing | the specification collection's toctree and prefix table |
| `reference/changelog.rst` | generated body | the page is a `sphinx_changelog` directive |
| `reference/cli.rst` | generated body | the body is generated by `sphinx-click` |
| `reference/config.rst` | generated body | the body is generated by the `tephpy-config-options` directive of configfile spec §3.6 |
| `reference/references.rst` | generated body | the body is generated by a `bibliography` directive |
| `reference/glossary.rst` | lookup | a lookup table: substantial, and not read in order |

The **landing** group is decision 5 read backwards: a banner is for a reader deciding
whether to start, and nobody decides whether to start an index.

The **generated body** group is exempt for a reason the counter cannot fix. §3.3 would
count these pages correctly, because the doctree holds what the directive generated — but
the number would be honest and still useless. Nobody reads a changelog or an options
reference from the top; they arrive looking for one entry.

`reference/glossary.rst` is the one judgement call, and the alternative is recorded in §5.

A test asserts every entry still resolves to a file. A renamed page whose exemption stayed
behind would be silently exempt, which is the failure mode decision 3 exists to prevent.
The list is checked for staleness, not for length: it is expected to grow.

That leaves **29 pages carrying the directive**, out of 41 published: the nine how-tos,
three tutorials, two explanation pages, `developer/docs-style.rst`,
`developer/packaging.rst`, and the thirteen published specifications, this document among
them. The counts are stated because §6 pins them by enumeration, not by arithmetic.

(reading-spec-4)=
## 4. Companion changes

- **`docs/src/conf.py`** — `tephpy_readingtime` added to `extensions`.
- **`docs/src/_static/tephpy.css`** — the `.reading-time` rule of §3.5. The file's opening
  comment describes it as site-wide styling as against the page-specific
  `browser-toolbar.css`, and this is the second site-wide rule it carries.
- **`docs/src/refs.bib`** — the two entries of §3.4, each with the `note` field
  docs-style requires: a citation is provenance, and provenance without a consulted date
  ages into a claim about a document that may since have changed.
- **`docs/src/developer/docs-style.rst`** — a **Reading Time** section stating the rule,
  the two overrides, the exemption list's existence and the rate with its citations. It
  sits after *Published Figures*, with the other rules about what a page must carry.
- **`docs/src/developer/specs/index.rst`** — the `reading spec §…` row and the toctree
  entry.
- **`changelog/`** — one `<PR>.documentation.rst` fragment per pull request, ending with
  ``(:user:`claude`)``.
- **This document** — one of the 29 pages in §3.7's carrying set. It receives its own
  banner in the
  implementation change, not before: the directive does not exist yet, and a
  `{readingtime}` fence in a published specification would fail the `--fail-on-warning`
  build on an unknown directive.

That last point generalises into a sequencing constraint. **The extension, the 29 page
edits and the gate land together.** The gate ahead of the directive fails every page in the
corpus; the directive ahead of the gate is a convention nothing enforces, which is the state
decision 3 exists to leave behind.

(reading-spec-5)=
## 5. Alternatives considered

- **Porting the prior art unchanged.** GeoVista [#2307](https://github.com/bjlittle/geovista/pull/2307) and [#2313](https://github.com/bjlittle/geovista/pull/2313) are where this
  directive comes from, and the argument grammar of §3.2 is theirs. What is not carried over
  is the source-file count (decision 1), the raw-HTML banner (decision 6), the silent
  fallback on an unparsable argument (§3.2), and the two undefined CSS variables (§3.5).
  Divergence has a cost — two projects, one maintainer, two behaviours — and it is accepted
  here because three of the four differences are things measured to be wrong rather than
  matters of taste.
- **Stripping markup out of the source with regular expressions.** Keeps the whole
  extension stdlib-only, so the counting would run in the CI matrix instead of needing the
  default environment. Rejected because it re-implements a slice of the reStructuredText
  and MyST parsers, and a second parser drifts from the first — the same reasoning
  `tephpy_citations.py` records when it declines to keep two copies of the citation grammar.
- **A split rate: prose at one figure, literal blocks at a slower one.** The fidelity the
  doctree walk actually makes available. Rejected by decision 2: no reading-rate study
  found offers a words-per-minute figure for source code, so the second number would be a
  judgement call presented as a measurement, sitting in this document beside two real
  citations and borrowing their credibility.
- **120 wpm, the prior art's default.** Chosen there partly to offset a source-file count
  that inflates the word total; §3.3 removes the inflation, so keeping the low rate would
  double-count the same conservatism.
- **A Sphinx `build-finished` check instead of a pytest gate.** It would see the real
  document set, including generated pages, with no corpus derivation to maintain. Rejected
  by decision 4: it would never run in the CI matrix.
- **Presence-only, with placement left to prose in `docs-style.rst`.** A smaller gate and
  no section-heading detection. Rejected by decision 5 — an unenforced placement rule is
  the convention drifting one page at a time, and `docs-style.rst` would be describing
  something no longer true.
- **Exempting the whole developer section**, specifications included. Reading time is a
  courtesy to someone deciding whether to start, and a contributor opening a specification
  has decided. Rejected because these are the longest pages the site publishes — the parent
  design specification by a wide margin — and the reader who most needs to be told what a
  page costs is the one about to open that.
- **Requiring the glossary to carry it.** It is a substantial page rather than a stub, and a
  glossary written for software engineers rather than meteorologists (spec §8.6) may well
  be read through by someone new. Rejected because the banner would measure something
  almost nobody does: a glossary is a lookup table, and putting a duration on it invites a
  reader to treat it as a chapter.

(reading-spec-6)=
## 6. Testing

Two files, one per half of §3.1, at the level each half can be reached. `pytest.importorskip`
at module level skips the module it is in, so a single file would skip the stdlib half in
the very matrix — `test-py3*` — it exists to run in; the repository already splits for this
reason, `tests/test_citations.py` and `tests/test_citation_xrefs.py`.

**`tests/test_docs_readingtime.py`. Runs everywhere, importing `tephpy_reading` only.**

- `count_words` and `estimate_minutes` against fixed inputs, including the `max(1, …)`
  floor and the minute/minutes plural.
- The argument grammar of §3.2: bare minutes, a `wpm` override, case insensitivity, and the
  rejection of an argument matching neither shape.
- The page scanner: a directive at column 0 accepted; the same line indented inside a
  literal block rejected; a MyST directive fence found where a fence-skipping reader would
  miss it (§3.6); an occurrence after the first section heading rejected.
- The corpus derivation, against the real `docs/src`: every exclusion of §3.6 excludes
  something that exists, and `developer/plans/**` is in `conf.py`'s `exclude_patterns`.
- The coverage rule itself, over the derived corpus.
- Every entry in the exemption list resolves to a file.

**Membership, not counts.** The corpus tests name members — at least one page per quadrant,
`developer/docs-style.rst`, and one published specification — following
`test_docs_snippets.DOCUMENTED` and for the reason recorded there: a count is a figure that
has to be re-measured to stay true, and a scanner that quietly stops recognising the
directive would otherwise pass by finding nothing.

**`tests/test_readingtime_directive.py`. Needs the default environment**, guarded with
`pytest.importorskip("sphinx")` exactly as `tests/test_citation_xrefs.py` is, and skipped
whole in the `test-py3*` matrix:

- The directive returns a placeholder carrying the parsed argument.
- The `doctree-read` handler replaces the placeholder, and counts a constructed doctree
  correctly: a comment excluded, a literal block included, the title counted once.
- A literal-duration argument publishes that number and does not count.

The leak guard of §3.2 is not a test. It is a property of not registering the node, and
what it produces is a Sphinx build failure, which `pixi run docs` already surfaces.

(reading-spec-7)=
## 7. Scope

**In scope.** The two modules of §3.1, the stylesheet rule, the gate, the two bibliography
entries, the `docs-style` section, and the directive on the 29 pages of §3.7 — landing in
one change, per §4.

**Out of scope.** Any change under `src/tephpy/`. This is documentation machinery, and it
imports nothing from the package.

**Explicitly not attempted.** A site-wide reading-time index, a per-quadrant total, and any
persistence of the estimate between builds. The number is derived from the page each time
the page is read, which is the only version of it that cannot go stale.

(reading-spec-8)=
## 8. Open items

- **Open** — the estimate does not know that a tutorial's reader stops to run the snippets.
  §3.2's literal-duration override is the remedy where it matters, used deliberately and
  visible in the source. Whether any of the three tutorials should use one is a judgement
  for the change that adds their banners, not a decision this document makes for them.
- **Open** — the divergence from GeoVista recorded in §5. Three of the four differences are
  corrections rather than preferences, and each is measured; whether they travel back
  upstream is that project's call.

(reading-spec-9)=
## 9. References

- Brysbaert, M. (2019). How many words do we read per minute? A review and meta-analysis of
  reading rate. *Journal of Memory and Language*, 109, 104047.
- Carver, R. P. (1982). Optimal rate of reading prose. *Reading Research Quarterly*, 18(1),
  56–88.
- GeoVista [#2307](https://github.com/bjlittle/geovista/pull/2307) and
  [#2313](https://github.com/bjlittle/geovista/pull/2313) — the prior art, in `bjlittle/geovista`.
- Docs spec §3.1 (the layout, and the plans exclusion). Docs spec §3.9 (the snippet gate
  this gate is modelled on, and its no-opt-out rule). Docs spec §4 (why a figure that must
  be re-measured is not quoted).
- Narrative spec §3.1 (the reader a tutorial is written for).
- Configfile spec §3.6 (the generated options reference).
- Spec §8.6 (the glossary's audience).

Each citation above repeats its prefix rather than sharing one across a list. A bare
`§4` trailing `Docs spec §3.9` resolves against *this* document, which has a §4 of its
own, so the list would silently cite the wrong specification ({issue}`197`).
