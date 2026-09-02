# tephpy documentation tooltips — design specification

```{readingtime}
```

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. The configuration and the gate it describes cite it by section —
> `tooltip spec §3.3` and the like — so these sections *are* the reasoning behind what that
> code does, and where the two ever diverge it is the specification that gets corrected.
> Read it as current.

- **Date:** 2026-09-01 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `tooltip spec §…` — the subject is the thing the reader hovers, not
  the library that draws it. `tippy spec` was rejected for naming a dependency this project
  does not control and may one day replace; the tooltips would survive that swap and the
  prefix should too
- **Scope:** one third-party Sphinx extension, two vendored JavaScript bundles, a
  `conf.py` block, one gate with its pixi task and CI step, and one test module; no change
  to `src/tephpy/`
- **Parent spec:** [`2026-08-03-published-specs-design.md`](2026-08-03-published-specs-design.md)
  — docs spec §3.1 is the layout that decides which pages exist, and docs spec §3.7 is the
  build-output gate this one is modelled on
- **Sibling specs:** [`2026-08-20-examples-gallery-design.md`](2026-08-20-examples-gallery-design.md)
  — gallery spec §3.5 is why the thumbnails exist, and §3.4 below is what they already carry;
  and [`2026-08-31-reading-time-design.md`](2026-08-31-reading-time-design.md), the most
  recent documentation-surface feature, whose §5 records the same divergence problem this
  one meets
- **Prior art:** GeoVista's `docs/src/conf.py`, which adopted `sphinx-tippy` first. §5
  records what was taken, what was corrected, and what could not be carried across

(tooltip-spec-1)=
## 1. Purpose

tephpy's prose is written for scientific software engineers rather than meteorologists
(spec §8.6), and it pays for that audience with jargon. The glossary is the instrument:
158 `:term:` references across the documentation (occurrences, not lines, counted over
every tracked `.rst`/`.md` file under `docs/src` except the unpublished plans), 54 of them
inside the glossary's own definitions. Every one of those is a link that costs the reader
their place on the page — they follow it, read a sentence, and come back, or more often
they do not follow it and carry the unfamiliar word forward.

A tooltip removes that cost for the case where the reader wants a definition rather than a
page. It is a presentation feature and this specification treats it as one: nothing here
changes what the documentation says, only whether a reader has to leave a paragraph to
understand it.

That framing sets the bar for the gate in §3.6. Under the standing rule that this project
gates the correctness of content rather than its presentation, a tooltip that renders
badly is not a build failure. What §3.6 does check is the small set of properties whose
regression would be silent and would reach the reader as something worse than no tooltip
at all.

(tooltip-spec-2)=
## 2. Decisions

1. **`sphinx-tippy`, from conda-forge, not from PyPI.** The extension reached conda-forge
   as `noarch/sphinx-tippy-0.4.3-pyhcf101f3_0.conda` on 2025-11-18, so it is declared in
   `[tool.pixi.feature.docs.dependencies]` beside the other Sphinx extensions rather than in
   the `pypi-dependencies` table where `playwright` sits. The prior art's comment describing
   it as "unavailable on conda-forge", and the `contextlib.suppress(ModuleNotFoundError)`
   guard that comment justifies, are both out of date and neither is carried across.
2. **The browser runtime is vendored and pinned, not fetched.** By default the extension
   emits `<script src="https://unpkg.com/@popperjs/core@2">` and
   `<script src="https://unpkg.com/tippy.js@6">` on every page — two unpinned floating-major
   dependencies, fetched from a third party by every reader. §3.2 replaces both with files
   in this repository.
3. **Everything is tipped except the gallery.** Measured 2026-09-01: every one of the 117
   rendered glossary-term links and all 204 API cross-references carry a tip, as do all but
   5 of the same-page anchors (1,508 of 1,513), with no gate disturbed and about four
   seconds added to a full build. The 5 are the gallery's own execution-times self-links of
   decision 4. A narrower configuration was considered and rejected: there was nothing
   measured to trim.
4. **The gallery thumbnails are skipped, because they already have tooltips.**
   sphinx-gallery writes a `tooltip=` attribute on all five `sphx-glr-thumbcontainer`
   elements. §3.4 records what the collision looked like.
5. **`sd-stretched-link` stays in the skip classes.** This is the one place the prior art's
   configuration is wrong for this project rather than merely inapplicable, and §3.3
   records what it does to the landing page.
6. **The tips are not interactive, and that is load-bearing.** §3.5 gives the reason, which
   is not a preference about hover behaviour.

(tooltip-spec-3)=
## 3. Architecture

(tooltip-spec-3-1)=
### 3.1 A dependency, not a module

Every other documentation surface this project has added — the citation cross-reference
extension of docs spec §3.7, the configuration reference, the reading-time banner of
reading spec §3.1 — is a module under `docs/src/_ext/`, written here because nothing
existing did the job. Tooltips are the opposite case: `sphinx-tippy` does the job, and the
work is configuration rather than code.

The cost of that choice is recorded rather than hidden. Upstream is dormant: `0.4.3`
released 2024-04-23 is the latest, seven pull requests stand unmerged, and one of them
([#33](https://github.com/chrisjsewell/sphinx-tippy/pull/33)) fixes a defect this project
meets, described in §3.5. The declared floor `>=0.4.3` is therefore also the ceiling in
practice, and `ci-floors` will pin it to `==0.4.3` because that is the only release
conda-forge carries.

What makes the dependency acceptable despite that is the size of the retreat. The
extension contributes a `conf.py` block, two vendored files and one gate; nothing in
`src/tephpy/` imports it, no page's source mentions it, and no rendered text depends on it.
Removing it is deleting the block.

(tooltip-spec-3-2)=
### 3.2 The runtime, vendored and pinned

`tippy_js` defaults to a pair of unpkg URLs. Three things are wrong with that default here:
the versions float on a major (`@2`, `@6`), so the documentation's behaviour can change
without any commit to this repository; every reader of every page makes two requests to a
third party; and with those requests blocked the documentation has no tooltips at all —
measured 2026-09-01 by serving the build with `unpkg.com` routed to failure: hovering a
glossary link on `tutorials/first-tephigram.html` raised no tooltip, where the same hover
raises one with the vendored runtime in place.

The two bundles are therefore committed under `docs/src/_static/js/`:

| file | upstream | bytes |
|---|---|---|
| `popper.min.js` | `@popperjs/core` 2.11.8, UMD | 20,122 |
| `tippy-bundle.umd.min.js` | `tippy.js` 6.3.7, UMD | 25,717 |

Both are MIT. `tippy_js` names them by `_static`-relative path, and Sphinx's `add_js_file`
emits them with its own cache-busting query. The directory is `_static/js/` and
deliberately **not** `_static/tippy/`, which is where the extension writes its own
generated per-page JavaScript; nor `_static/vendor/`, which pydata-sphinx-theme already owns
for its FontAwesome bundle.

`setuptools_scm` sweeps tracked files into the sdist, so `MANIFEST.in` needs no entry for
either file. Every pre-commit hook that rewrites text — end-of-file, trailing whitespace,
mixed line endings — leaves both bundles untouched, and `codespell` passes over them, so
none of them needs an exemption.

One gate does not. `check_github_references.py` reads
`background-color:#333` in the minified stylesheet the tippy bundle carries — the very
default dark theme §5 records the prior art failing to override — and reports it as an
unlinked reference to GitHub issue 333. The script already exempts a *quoted* hexadecimal
colour, and this one is unquoted CSS inside a JavaScript string, so the exemption does not
reach it.

The correction goes in `corpus()` in `check_citations.py`, which both that gate and the
citation gate of docs spec §3.6 share: `docs/src/_static/js/` joins the plans as a
directory the corpus passes over. That corpus is deliberately *derived* rather than
declared, because a glob under-covers silently, so subtracting from it needs a reason that
is about the files rather than about the failure. The reason is authorship. Docs spec §3.6
and docs spec §3.8 govern what this project writes and a reader reads; a vendored third-party
bundle is neither, and no prose in it can be corrected here. Nothing else in the tree is
covered by that exemption today, and the alternative — teaching the colour rule to
recognise unquoted CSS — is rejected in §5.

(tooltip-spec-3-3)=
### 3.3 The anchor scope, and the classes that must be skipped

`tippy_anchor_parent_selector` is `article.bd-article`, pydata-sphinx-theme's article
container. Without it the extension tips the navigation bar, the sidebar and the
breadcrumbs, where a tooltip repeats a link whose destination the reader can already read.

`tippy_skip_anchor_classes` is `("headerlink", "sd-stretched-link", "sd-sphinx-override")`.
The prior art sets `("headerlink", "sd-sphinx-override")`, which *replaces* the extension's
default rather than extending it, and the default it drops is `sd-stretched-link`.

That matters here specifically. tephpy's landing page is four Diátaxis cards, and
sphinx-design builds a card from a zero-size anchor stretched over the card body by a
`::after` rule. Hovering anywhere on the card is therefore hovering the anchor. Rendered
2026-09-01 with the prior art's classes, hovering the *Tutorials* card raised a tooltip
carrying that page's opening two paragraphs, which covered the *Explanation* card entirely
and about a third of the viewport. With `sd-stretched-link` restored the same hover raises
none.

The extension applies these classes at *runtime*, in the emitted JavaScript, rather than
when it collects tips. A tip is still generated for each of the four cards and simply never
attached. Any measurement of coverage taken from the generated data therefore counts four
tips a reader can never see, and §6 says which of the two things each assertion reads.

(tooltip-spec-3-4)=
### 3.4 The gallery, which already had tooltips

sphinx-gallery writes a `tooltip=` attribute on every `sphx-glr-thumbcontainer` and styles
it into a hover panel that replaces the thumbnail in place. The extension knows nothing
about this and tips the same five links.

Rendered together on 2026-09-01, one hover produced both: the thumbnail image replaced by
sphinx-gallery's truncated docstring text, and simultaneously a large panel above it
carrying the example page's title and opening paragraphs. Redundant, and the larger of the
two obscured the neighbouring thumbnails.

`tippy_skip_urls` therefore carries two patterns:

```python
tippy_skip_urls = [
    r"(\.\./)*gallery/plot_\w+\.html",
    r"plot_\w+\.html",
]
```

Two rather than one because the extension matches these with `re.match` — anchored at the
start — against the raw `href` as it appears in the page, and that href is bare
(`plot_hodograph.html`) on the gallery index and its execution-times page, but dotted
(`../gallery/plot_hodograph.html`) from anywhere else. A single pattern for either shape
silently misses the other. Measured, the pair takes the five gallery links from tipped to
untipped and additionally catches five links to the same targets from
`gallery/sg_execution_times.html`.

The direction of the decision — skip the extension's tips rather than suppress
sphinx-gallery's — follows from which is removable. sphinx-gallery offers no setting to
withhold the attribute.

(tooltip-spec-3-5)=
### 3.5 Why the tips are not interactive

`tippy_props` is left empty, so `interactive` keeps its default of `False`: the tip
dismisses when the pointer leaves the link, and its contents cannot be clicked. That is not
a preference about hover behaviour. It is what makes a known upstream defect unreachable.

The extension builds a tip by copying the target's rendered HTML verbatim. A bare
`#fragment` link inside that HTML stays a bare fragment, and so resolves against whatever
page is *showing* the tip rather than the page it came from. Measured across the whole
build on 2026-09-01: about **790** links inside tip bodies point at anchors that do not
exist on the host page (788 on this build; the count moves with the prose), **151** of
them inside glossary tips — a tip for `#term-tephigram` shown on the landing page carries a
link to `#term-projection`, which the landing page has not got. Every one of them is a bare
fragment; relative paths are rebased correctly and none of those break.

While `interactive` is `False` a reader cannot reach any of them. They render as link-styled
text inside a panel that disappears before it can be clicked — misleading, but not a broken
journey. Setting `interactive: True` would convert every one of them into a dead link in
one line, which is why §3.6 asserts the value rather than trusting the default,
and why upstream [#32](https://github.com/chrisjsewell/sphinx-tippy/issues/32) and
[#33](https://github.com/chrisjsewell/sphinx-tippy/pull/33) are cited in §8 as the thing to
watch.

(tooltip-spec-3-6)=
### 3.6 The gate

`.github/scripts/check_tooltips.py` reads the built HTML and the generated JavaScript, in
the manner of docs spec §3.7's rendered-citation gate, and is wired as the pixi task
`docs-check-tooltips` and a step in `ci-docs.yml`.

It asserts four things, and the choice of four is the proportionality argument of §1
applied one property at a time:

1. **Every glossary link this project owns, on a page rendered from a source document,
   has a generated tip that carries the definition, not merely a tip, and there is at
   least one.** The positive assertion. A build in which the extension silently produced
   nothing — a failed import behind a suppression, a selector that stopped matching a
   themed container — otherwise passes every other check in this list, because all three
   of those are satisfied most completely by an empty build; a tip that is merely present
   but bare, the defect §3.7 records, passes just as completely without the "carries the
   definition" half. Measured on the current build: 117 links, on pages rendered from a
   source document, are checked and every one carries a tip with a definition. 55 more are
   out of scope — 50 on `genindex`, which Sphinx's builder generates rather than rendering
   from a source document and which the extension never processes, and 5 external,
   intersphinx-resolved links to Python's own glossary, which §7 already records as
   carrying no tooltip by design.
2. **No gallery example link is tipped.** §3.4's collision, which is visible to a reader
   and invisible to every existing gate.
3. **The vendored runtime is there, and only there.** Three sub-checks, in this order. No
   page loads it off-site — tested first, on the raw `src` text, against every script
   matching the runtime pattern, so an off-site URL that happens to contain the generated
   payload loader's own path (`_static/tippy/`) is still caught rather than mistaken for
   it. Every page carrying a tippy payload references at least one *other* local runtime
   script, because a page with a payload and a stripped `<script>` tag fails silently in
   exactly the way the off-site check alone cannot see; the payload loader itself is told
   apart from the two vendored bundles by an anchored test of where it resolves, not by a
   substring of its `src` text. And every remaining local script — the `?v=...`
   cache-busting query stripped first, and a root-relative `src` resolved against the build
   root rather than the page, since `Path.__truediv__` discards the page side of that join
   when the right operand is absolute — resolves to a file *inside* the build root,
   because `resolve()` normalises a traversal but does not confine it: a bundle renamed or
   deleted at either end is neither absent nor off-site, and neither is one resolving
   outside the tree entirely, and Sphinx does not warn on a missing static asset either
   (`_file_checksum_inner` swallows the `FileNotFoundError`). The two failure shapes are
   reported with different text — "escapes the build root" against "does not exist under
   the build root" — because a reader needs to know which one they have.
4. **The emitted JavaScript carries `interactive: false` and lists `sd-stretched-link`.**
   The two guards of §3.5 and §3.3, both of which are one word away from being lost and
   neither of which fails a build when it is.

What the gate deliberately does not check is how any tooltip looks: its palette, its
placement, its size, or whether its text wrapped well. That is presentation, this project
does not gate presentation, and the standing limit recorded in reading spec §7 applies here
unchanged — a defect of that shape would ship.

(tooltip-spec-3-7)=
### 3.7 Shared-definition groups, and the `<dt>`s upstream starves

Two different constructs render the same way. A glossary entry may define several
terms with one shared definition:

```rst
.. glossary::

    lapse rate
    dry adiabatic lapse rate
    DALR
    moist adiabatic lapse rate
    saturated adiabatic lapse rate
    SALR
        ...
```

and a Python directive may document several call signatures with one shared
description — `py:function:: spam(a)` and a second signature line `spam(a, b)`, or the
`@overload` shape autoapi emits. Both become a run of consecutive `<dt>` elements
followed by one `<dd>`, and `sphinx_tippy.create_id_to_tip_html` copies the `<dd>` into
a `<dt>`'s tip only when the `<dd>` is that `<dt>`'s *immediate* next sibling:

```python
if (next_sibling := next_sibling_tag(tag)) and next_sibling.name == "dd":
```

**The glossary shape.** Every `<dt>` in the group is given its own bare tip earlier in
the same function — the loop above it copies `str(tag)` for each one unconditionally —
but only the *last* `<dt>` of a group ever satisfies the sibling check, so only it is
given the `<dd>`. Hovering `DALR` shows the word "DALR"; hovering `SALR`, the last term
of the same group, shows the full definition. tephpy's glossary is 29 entries defining
50 terms; 13 of the entries define more than one term, 21 of the 50 terms are starved by
this rule, and — measured on the built site before the correction below — 30 of the 117
glossary tips §3.6 checks carry no definition (26%).

**The signature shape.** Sphinx's own convention only ever puts an `id` on the *first*
`<dt>` of a multi-signature group — confirmed against this documentation's own build,
not assumed: `tephpy.plotting.axes.TephigramAxes.plot_profile`, an `@overload`-shaped
method accepting either a pressure/temperature pair or a `calc.Profile`, renders as an
id-bearing `<dt>` for its first signature, a second `<dt>` with **no** `id` at all, and
one `<dd>`. The first `<dt>` is never adjacent to the `<dd>` — the id-less second `<dt>`
sits between them — so it is never given one either, and it is the only `<dt>` of the
group whose tip is ever shown: measured before the fix, the tip stored for it was 2,238
bytes, the first signature's `<dt>` alone, with no `<dd>` at all. The corpus contains
exactly one such group today; the shape is one more `@overload` away, and the fix below
covers it regardless of count.

Filed upstream as
[sphinx-extensions2/sphinx-tippy#35](https://github.com/sphinx-extensions2/sphinx-tippy/issues/35);
§3.1 already records upstream as dormant since `0.4.3` in April 2024, so this is vendored
rather than waited for, in the same shape as the interactive-tips correction §8 keeps open.

**The correction, and why it is not donor-reuse.** A first design fixed the glossary
shape by *donating* the last term's already-generated, already-trimmed tip to every
earlier term in its group — reusing `create_id_to_tip_html`'s own trimmed `<dd>` rather
than re-deriving it, since that function's copy is not a plain `str(dd)`: it keeps at
most five `<p>` children and drops everything else, silently, and reimplementing that
trim would need tracking forever against upstream drift. That design does not reach the
signature shape: donation needs some `<dt>` in the group to already hold the `<dd>` it
can lend, and here none does — the only `<dt>` with an `id` is never adjacent to the
`<dd>`, so there is no donor.

`docs/src/_ext/tephpy_tippy_terms.py` instead **pre-processes the parsed page before**
calling the original function. `_duplicate_definitions` walks the same `BeautifulSoup`
body the original goes on to read, finds every run of consecutive `<dt>` siblings —
`id` or no `id` — terminated by a `<dd>`, and inserts a *copy* of that `<dd>` immediately
after every `<dt>` in the run not already adjacent to it. `create_id_to_tip_html`'s own
adjacency check then succeeds for every `<dt>`, and its own trimming runs once per
`<dt>`, unmodified — the correction still never re-derives or duplicates that logic,
which was the point of the donor idea and is kept here by construction; it is simply
applied one layer earlier, to the input rather than the output. A `<dt>` whose group has
no trailing `<dd>` at all is left untouched — nothing to insert and no donor either way.

Mutating the parsed page this way is safe because of how `sphinx_tippy.collect_tips`
builds it: at `sphinx_tippy.py:261`, `body = BeautifulSoup(context["body"], "html.parser")`
parses a *copy* of the page's HTML string, and nothing renders from `body` after
`create_id_to_tip_html` returns — verified by reading `collect_tips`, not assumed, and
recorded in the module's own docstring so a future reader relying on it again can recheck
it against whatever `collect_tips` does then.

(tooltip-spec-4)=
## 4. Companion changes

- **`pyproject.toml`** — `sphinx-tippy >=0.4.3` in `[tool.pixi.feature.docs.dependencies]`;
  the `docs-check-tooltips` task; that task added to the `docs` task's `depends-on`.
- **`requirements/pypi-optional-docs.txt`** — the PyPI counterpart of the same floor.
- **`pixi.lock`** — re-solved.
- **`docs/src/conf.py`** — `sphinx_tippy` in `extensions`, and the configuration block of
  §3.2 to §3.5; `tephpy_tippy_terms` immediately after it, for §3.7.
- **`docs/src/_static/js/`** — the two vendored bundles of §3.2, new directory.
- **`docs/src/_ext/tephpy_tippy_terms.py`** — the shared-definition-group correction of
  §3.7, new module.
- **`tests/test_tippy_terms.py`** — §3.7's own tests, new module.
- **`.github/scripts/check_citations.py`** — the shared corpus of §3.2 passes over the
  vendored directory. The citation gate's own verdict is unchanged by it; the
  GitHub-reference gate's is what needed it.
- **`tests/test_citations.py`** and **`tests/test_github_references.py`** — the corpus
  exemption, asserted from both sides: a vendored file is passed over, and a file
  elsewhere carrying the same text is still reported.
- **`.github/workflows/ci-docs.yml`** — the gate's step, beside the four it already runs.
- **`tests/test_docs_workflow.py`** — holds the pixi `docs` task and the `ci-docs` job to
  each other, so it changes whenever the set of gates does ({issue}`171`).
- **`tests/test_tooltips.py`** — §6.
- **`docs/src/developer/specs/index.rst`** — the `tooltip spec §…` row and the toctree
  entry.
- **`changelog/`** — one `<PR>.documentation.rst` fragment, ending with ``(:user:`claude`)``.

The extension, the vendored runtime and the gate land together. The gate ahead of the
extension fails on a build with no tooltips in it; the extension ahead of the gate is four
properties nothing enforces, which is the state decision 6 exists to leave behind.

(tooltip-spec-5)=
## 5. Alternatives considered

- **`sphinx-hoverxref`.** Archived 2025-04-09. Read the Docs deprecated it in favour of a
  dashboard setting, so it is not a candidate whatever its merits were.
- **Read the Docs' *Link previews* addon.** The successor to `sphinx-hoverxref`, enabled
  from the project dashboard with no dependency, no configuration and nothing to maintain.
  Rejected because it exists only on the published site: it is absent from `pixi run
  serve-html`, absent from `docs/_build/html`, and therefore unreachable by every gate this
  project has. It also covers internal links only, where §3.3's scope covers the glossary,
  the API and same-page anchors alike. The trade is a real one and this decision is the one
  place in this document where a maintainer might reasonably choose differently — the cost
  of §3.1's dormant upstream is paid entirely to keep the feature inside the repository.
- **Porting the prior art unchanged.** GeoVista's configuration is where this comes from and
  most of it transfers. Four things do not. Its `contextlib.suppress` import guard and the
  `pypi-dependencies` placement it implies are obsolete (decision 1). Its
  `tippy_skip_anchor_classes` drops `sd-stretched-link` and breaks this project's landing
  page (§3.3). Its `tippy_props = {"theme": "light"}` is a no-op: no light-theme stylesheet
  is ever emitted, so the rendered tooltip is the library's built-in dark
  (`rgb(51, 51, 51)` on white text) in *both* colour schemes — measured under
  `prefers-color-scheme` light and dark on 2026-09-01, identical in each. And its two
  `tippy_skip_urls.extend(...)` calls feed on `sphinx-tags` and a GeoVista-local helper,
  neither of which exists here, so §3.4 derives its own patterns.
- **Teaching the colour rule to read unquoted CSS,** rather than exempting the vendored
  directory from the corpus (§3.2). Rejected because it widens a rule whose purpose is to
  avoid *false negatives* in prose: every character it learns to ignore is a place a real
  `#123` could hide. The exemption in `corpus()` is narrower, and states the true
  principle — the corpus governs what this project writes.
- **A narrower tooltip surface — glossary and API only.** The original recommendation,
  abandoned on measurement. The broader configuration disturbs no gate, adds about four
  seconds, and the classes that would have been trimmed cost nothing to keep.

(tooltip-spec-6)=
## 6. Testing

`tests/test_tooltips.py` tests the gate the way `tests/test_rendered_citations.py` tests
its own: over fixtures, so the assertions are exercised on a failing build as well as a
passing one. Each of §3.6's four checks gets a fixture that violates it — a page whose
`:term:` link has no tip, a tipped gallery link, and an emitted payload with
`interactive: true` — and the gate must fail on each. Check 3's three sub-checks each get
their own fixture in turn: a page carrying an `unpkg.com` script, a page with a tippy
payload and no runtime script at all, and a page whose runtime `src` names a file that is
not under the build root. A gate only ever exercised against a green build asserts nothing
about the red one.

Two distinctions the fixtures must preserve, because both are places a plausible test
passes for the wrong reason:

- Checks 1 and 2 read the *generated* tip data; check 4 reads the emitted JavaScript, which
  is where the runtime skip classes live. §3.3's four landing-page cards have generated tips
  and no attached ones, so a fixture that conflates the two will report coverage a reader
  does not get.
- Check 3 must look for the runtime scripts, not for the string `unpkg.com`. This
  specification contains that string, is a published page, and would fail a naïve gate that
  swept the build for it.

The one thing no fixture reaches is whether a tooltip appears when a pointer is over a
link. That was established by driving Chromium during design — for the landing-page card of
§3.3, the gallery collision of §3.4, and the CDN-blocked case of §3.2 — and is not
automated here, for the reason §3.6 gives.

(tooltip-spec-7)=
## 7. Scope

**In scope.** The dependency, the two vendored bundles, the `conf.py` block, the gate with
its task and CI step, and the test module — landing in one change, per §4.

**Out of scope.** Any change under `src/tephpy/`. This is documentation machinery and
imports nothing from the package.

**Explicitly not attempted.** Tooltips on external and intersphinx links. The extension can
produce them, from Wikipedia, from Crossref DOIs, and by fetching Read the Docs pages
named in `tippy_rtd_urls`; all three reach the network while the documentation builds, and
this project's build does not. The measured consequence is that about 1,650 external links
— every matplotlib, numpy, MetPy, pint and Python reference in the documentation — carry
no tooltip (1,645 measured 2026-09-01; the count moves with every reference the prose
adds). That is the largest single gap in the feature and it is deliberate.

**A standing limit, not a deferral.** The extension names each generated file with a
`uuid4()`, so the published site is not byte-reproducible across builds: two builds of an
unchanged tree differ in every `_static/tippy/*.js` filename. `docs-clean` runs ahead of
`docs-html`, so stale files do not accumulate in the ordinary task, but an incremental
build accumulates one set per run. Nothing here fixes that, and no gate detects it.

**A standing limit on check 3, not a deferral.** §3.6's third check now asserts both that a
page carrying a tippy payload references a vendored runtime script and that every such
script resolves to a file under the build root, which closes the two regressions found in
review: a stripped `<script>` tag, and a renamed or deleted bundle. It does not close a
third: if `tippy_js` named only one of the two bundles — Popper dropped, Tippy kept, say —
the surviving script still resolves, the page still carries *a* runtime script, and the
gate stays quiet, even though the extension needs both to function. Nothing here fixes
that, and no gate detects it.

(tooltip-spec-8)=
## 8. Open items

- **Open** — the dead in-tip fragment links of §3.5 (about 790). They are unreachable
  today and remain so while `interactive` is `False`, which check 4 enforces. Upstream
  [#33](https://github.com/chrisjsewell/sphinx-tippy/pull/33) is the fix; it has stood
  unmerged since 2025-12-16, and if it stays that way the alternative is to vendor the
  correction as a small `docs/src/_ext/` post-processing step. Not attempted here, because
  the defect has no reader-visible consequence under the current configuration.
- **Open** — the shared-definition-group defect of §3.7, filed upstream as
  [sphinx-extensions2/sphinx-tippy#35](https://github.com/sphinx-extensions2/sphinx-tippy/issues/35).
  If upstream fixes it, `create_id_to_tip_html` starts giving every `<dt>` of a group its
  `<dd>` on its own, so every `<dt>` `_duplicate_definitions` visits is already adjacent to
  its `<dd>` and it inserts nothing — the pre-processing step becomes a no-op walk over
  every page rather than a correction. At that point it is removable: delete
  `tephpy_tippy_terms.py`, its `tests/test_tippy_terms.py`, and the two `conf.py` lines, and
  re-measure §3.7's counts.
- **Open** — citation tooltips resolve for 3 of the 10 links into `reference/references.html`.
  Observed on 2026-09-01 and not diagnosed. The bibliography is small enough that the gap
  has not been worth the investigation, and no gate depends on the number.
- **Open** — §3.1's dormant upstream. If `sphinx-tippy` acquires a maintainer the pinned
  ceiling lifts on its own; if it does not, §5's Read the Docs alternative is the retreat,
  and the cost of taking it is this document.
- **Open** — the divergences from GeoVista recorded in §5, one of which (§3.3) is a defect
  rather than a difference of taste. Whether they travel upstream is that project's call.
- **Not this specification's** — sphinx-gallery renders all five thumbnail tooltips from
  the docstring by pattern rather than by parsing, so ``:term:`dry adiabats <dry adiabat>``
  reaches the reader as `dry adiabats <dry adiabat>` and ``:term:`soundings <sounding>``
  as `Two sounding`. That is a pre-existing defect in a different component, filed
  separately, and untouched by anything here.

(tooltip-spec-9)=
## 9. References

- [`sphinx-tippy`](https://github.com/chrisjsewell/sphinx-tippy) — the extension, at
  `0.4.3`. Issue [#32](https://github.com/chrisjsewell/sphinx-tippy/issues/32) and pull
  request [#33](https://github.com/chrisjsewell/sphinx-tippy/pull/33) are the defect of
  §3.5. Issue
  [sphinx-extensions2/sphinx-tippy#35](https://github.com/sphinx-extensions2/sphinx-tippy/issues/35)
  is the multi-term glossary defect of §3.7.
- [`sphinx-hoverxref`](https://github.com/readthedocs/sphinx-hoverxref) — archived
  2025-04-09, carrying the deprecation notice that names Read the Docs' *Link previews* as
  its successor (§5).
- Docs spec §3.1 (the layout that decides which pages exist). Docs spec §3.7 (the
  build-output gate §3.6 is modelled on).
- Gallery spec §3.5 (why the thumbnails exist, and what §3.4 collides with).
- Reading spec §3.1 (the extension-as-module pattern §3.1 departs from). Reading spec §7
  (the standing limit on rendered-geometry assertions, which §3.6 inherits).
- Spec §8.6 (the glossary's audience, which is §1's premise).

Each citation above repeats its prefix rather than sharing one across a list. A bare
`§3.1` trailing `Docs spec §3.7` resolves against *this* document, which has a §3.1 of its
own — so the list would silently cite the wrong specification ({issue}`197`).
