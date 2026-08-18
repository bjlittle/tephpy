# tephpy published figures — design specification

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. `docs/src/conf.py`, the user quadrant pages, `tests/test_docs_snippets.py`
> and `.github/scripts/check_docs_figures.py` cite it by section — `plots spec §3.2` and
> the like — so these sections *are* the reasoning behind what they do, and where the two
> ever diverge it is the specification that gets corrected. Read it as current.

- **Date:** 2026-08-17 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `plots spec §…` — not `figures spec`, which would collide with the
  other sense of the word already load-bearing in this collection: docs spec §4 governs a
  *figure* as a number quoted in prose, and a citation that reads as naming that rule while
  meaning a rendered diagram is worse than a longer prefix
- **Scope:** rendering the user documentation's python as diagrams on the page, and pinning
  what gets published; the code those pages show is theirs to choose, and the API they
  exercise is unchanged
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) — adds an
  extension to spec §8.6's list and inherits its Diátaxis quadrants and title style
- **Sibling spec:** [`2026-08-03-published-specs-design.md`](2026-08-03-published-specs-design.md)
  — docs spec §3.9 executes the same blocks this renders, and §3.4 of this document is what
  changes there

(plots-spec-1)=
## 1. Purpose

The two how-to guides that teach a *visual* API showed no picture. "Emphasise a Reference
Isopleth" describes a member drawn in the same ink at a heavier weight, and "Add the tephpy
Logo" describes three forms at two themes in nine placements, and a reader of either had to
build the diagram themselves to find out what the page was talking about. These are the shop
window for a plotting package.

Nothing in the project rendered a figure from source. `matplotlib.sphinxext.plot_directive`
was not among the extensions and `sphinx_gallery_conf` named no example directory, both
deliberately: the plan that wrote the emphasis how-to
([`2026-07-30-tephpy-member-emphasis.md`](https://github.com/bjlittle/tephpy/blob/main/docs/src/developer/plans/2026-07-30-tephpy-member-emphasis.md),
Step 5) recorded "do not add a Sphinx extension as part of this work", correctly, because
adding one is a documentation-wide decision and not a step in a feature. This document was
that decision.

What is *not* the problem here is the code going stale. docs spec §3.9 already executes every
python block in the three user quadrants, as one script per page and in document order, on
every supported Python. A snippet that stops working already fails. What a rendered page adds
is a second failure this does not cover — a snippet that still runs and no longer *shows* what
its prose claims — and §3.5 is the answer to that one.

(plots-spec-2)=
## 2. Decisions

- **The page's own snippet is the figure's source.** One block, shown and executed, is what
  the reader copies and what the picture came from. A figure built by a script beside the page
  is a second construction that agrees with the prose until someone edits one of them.
- **One figure per point, not per block.** These pages are sessions in which a later block
  supersedes an earlier one — docs spec §3.9 cites three blocks of the emphasis how-to calling
  `ax.isotherms(...)` on the same axes — so a picture after every block would sometimes show
  a state the surrounding prose has stopped describing. A section making two distinct points
  publishes two (§3.2).
- **A page publishes figures or it does not; the two forms never mix.** A `code-block:: python`
  between two `.. plot::` blocks runs in the test gate and not in the build, so the build's
  namespace silently loses whatever it bound (§3.2). The rule is per page because the page is
  the unit docs spec §3.9 already reasons about.
- **The comparison lives on the docs side.** What is worth pinning is the artifact that ships,
  and it exists only in the build. Re-rendering the same code in the test environment and
  comparing *that* would pin a second render whose agreement with the published one rests on
  four settings staying aligned, with nothing checking the alignment (§3.5).
- **Nothing a published block does may outlive it.** `plot_directive` executes every block in
  the Sphinx process, so module state set by one page is inherited by every page built
  afterwards, in an order nobody controls (§3.3).
- **The gate works from what the pages declare, not from what the build emitted.** `_images/`
  already holds files that are not plots, and a glob over it cannot tell the difference (§3.4).

(plots-spec-3)=
## 3. Architecture

(plots-spec-3-1)=
### 3.1 The directive and its configuration

`matplotlib.sphinxext.plot_directive` joins the extension list. It adds no dependency —
matplotlib is a hard requirement — and it is preferred to the two extensions already loaded
for this purpose: myst-nb executes notebooks and the user quadrants are reStructuredText
(docs spec §3.9 scopes itself to `.rst` for the same reason), and sphinx-gallery renders a
catalogue of standalone examples, which is spec §8.6's Plan 7 and not a how-to (§5).

Six settings, each of which changes a default that is wrong here:

| Setting | Value | Why the default is wrong |
|---|---|---|
| `plot_include_source` | `True` | Defaults to `False`, which publishes a picture with the code that made it hidden — the opposite of the point |
| `plot_html_show_source_link` | `False` | A download link to a `.py` extracted from the page, beside the page |
| `plot_html_show_formats` | `False` | Format links, of which there is one |
| `plot_formats` | `[("png", 100)]` | Defaults to also building `hires.png` and `pdf`, neither of which is linked once the two settings above are off |
| `plot_rcparams` | `{"figure.figsize": (8.0, 4.0)}` | §4 |
| `plot_working_directory` | a scratch directory under the git-ignored build tree | Defaults to the page's own source directory, so `howtos/logo.rst`'s `fig.savefig("sounding.png", ...)` would write into the checked-out documentation tree, where the next build finds it as a source file |

`plot_apply_rcparams` stays `True`, which is what restores those rcParams between blocks; a
page that sets a matplotlib style therefore cannot leak it into the next one. It is only
matplotlib state that this covers — see §3.3.

(plots-spec-3-2)=
### 3.2 Page shape

On a page that publishes figures, every python block is a `.. plot::`, and carries options
by these rules:

1. **The first block on the page carries `:context: reset`.** Without it the page opens with
   whatever the previously-built page left behind. This was measured: a two-page probe whose
   second page printed a name bound only on the first built clean, exit `0` (2026-08-17).
   Build order is not a property any page controls, so a page that builds only because of its
   neighbour is a defect that appears when someone rebuilds one file.
2. **Every later block carries `:context:` or `:context: close-figs`.** A block with no
   `:context:` at all runs in a fresh namespace, which breaks the session model docs spec §3.9
   requires — the second block of the logo how-to is `add_logo()` with no argument, and alone
   it has nothing to brand. `close-figs` is what opens a section that starts its own figure.
   The two values do not combine: `plot_directive` accepts exactly one of nothing, `reset` or
   `close-figs`, so the page's first block resets and its sections close figures.
3. **A block whose picture would add nothing, or should not be published, carries
   `:nofigs:`.** It still runs, so the chain is unbroken. This is the reason plain
   `code-block:: python` is not the answer for such a block — the logo how-to's
   `dark_background` block is the second case: its picture would add plenty, and it is
   suppressed because the figure around it is defective, not because it teaches nothing.
4. **Every figure-producing block carries a `:filename-prefix:`.** Unnamed, the image takes a
   per-document counter, so inserting a section renumbers every image after it and every
   baseline with them. Named, `check_output_base_name` also rejects a collision project-wide.
5. **No file-argument form.** `.. plot:: script.py` renders a figure from a file, and the code
   a reader is invited to copy has to be on the page.

A page that publishes no figure is untouched: its python stays `code-block:: python` and
docs spec §3.9 goes on executing it. `howtos/configuration.rst` is that page today, and §3.3
is why it is not merely that it has nothing worth drawing.

(plots-spec-3-3)=
### 3.3 What a published block may not do

`plot_directive` runs every block in the Sphinx process, with `sys.modules` shared across the
whole build. `:context: reset` clears the namespace the blocks execute in; it does not touch
module state, and there is no hook that would.

So a published block may not leave `tephpy.config` mutated. Written as a bare assignment —

```python
tephpy.config.isotherms.emphasis = {0.0: {}}
```

— the setting applies to every axes created afterwards, on that page and on every page built
after it, because a family reads the configuration when its axes is created. Demonstrate
configuration with the context manager instead, which restores prior values on exit and on
error:

```python
with tephpy.config.context(isotherms={"emphasis": {0.0: {}}}):
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
```

This is a better page as well as a safe one: the ordering the prose is making — the family
reads the configuration when the axes is created — is now visible in the indentation, and the
reader is shown a scope rather than a global.

The same reasoning is what keeps `howtos/configuration.rst` out of the build's interpreter
altogether, and there the consequence is not a tinted diagram. `tephpy.config.save()` defaults
to `_configfile.user_config_path()`, so that page's second block, executed in a docs build,
would write a configuration file into the home directory of whoever ran it. docs spec §3.9
runs it under a relocated `HOME` and `XDG_CONFIG_HOME`; `plot_directive` has no such sandbox
and is not going to grow one. A page whose subject is global, persistent configuration is a
page that publishes no figures.

(plots-spec-3-4)=
### 3.4 The snippet gate learns the directive

`tests/test_docs_snippets.py` recognised `code-block`, `code` and `sourcecode`, and nothing
else. The moment a page converted, its blocks stopped being found — and
`test_the_documented_pages_yield_blocks` failed, by name, saying the extractor had stopped
recognising a directive. That was the gate working, and it is why the extractor was extended
in the same change rather than after it.

The extension is not a widened `DIRECTIVE`. That pattern reads the directive's argument as a
language, and `.. plot::` either takes none or takes a filename; folding it in would classify
an unnamed plot as "names no language" — which `test_no_block_hides_the_language_this_gate_runs`
reports — and would read `script.py` as a language nobody executes. `plot` gets a pattern of
its own, its body joins the page's script exactly as a `code-block:: python` body does, and
the near-miss detector learns to leave it alone.

Rules 1–5 of §3.2, and the choice between the two page forms, each become an assertion here
rather than a line in the style guide. This is the gate that can see them: it already reads
every user page as text, and it runs in the test matrix, where Sphinx is absent. The existing
refusals — the quadrant directories exist, the corpus is non-empty, the `DOCUMENTED` pages
yield blocks — carry over unchanged and keep governing both page forms. A fourth joins them:
`test_the_figure_pages_are_recognised` asserts that every page named in `PUBLISHES_FIGURES`
still yields a `.. plot::`, on the same principle as `DOCUMENTED` above it — every page-shape
check below iterates this set, so a page that dropped out of it would be asked nothing rather
than failed.

(plots-spec-3-5)=
### 3.5 The figure gate

`.github/scripts/check_docs_figures.py`, beside `check_rendered_citations.py` and
`check_documentation_links.py`, wired into `pixi run docs` and `ci-docs.yml` the way both of
those already are.

It does not glob the build's `_images/`. That directory already holds six SVG files, copied
there from the browser demo's toolbar icons, and a glob cannot tell a plot from an icon —
adding one non-plot image would turn the gate red for a file it was never meant to judge, and
a plot silently *not* built is the failure it exists to catch. The expected set comes instead
from the `:filename-prefix:` values parsed out of the user pages, which makes the declaration
on the page the registry, and all three of these checkable:

- every figure a page declares was built;
- every baseline is claimed by a declaration, so a renamed section leaves no orphan behind;
- every declared/built pair compares within tolerance, by
  `matplotlib.testing.compare.compare_images` — matplotlib's own comparator, already in the
  documentation environment, and the same RMS measure `pytest-mpl` applies to
  `tests/baseline`.

An empty declared set fails. A gate that finds nothing to check and exits `0` reports a green
tick over nothing, which is the failure docs spec §3.9's own corpus refusals were written
against.

Two more refusals guard this gate the same way. `PUBLISHES` names the pages this gate expects
to declare a figure — `howtos/emphasis.rst` and `howtos/logo.rst` today — and a page listed
there that declares none is reported by name rather than passing every check below in
silence, each of which reads only what pages *do* declare. And `CANDIDATE` is `DECLARATION`,
widened rather than narrowed: any indentation character and a value read whole rather than
restricted to word characters, dots and dashes. What it catches that `DECLARATION` does not
is reported as a near miss instead of a declaration nothing here ever saw — the same
detection-wider-than-validation shape docs spec §3.9's own near-miss detector uses.

What this gate does *not* do is judge whether the figure is a good illustration. It pins what
was published against what was approved; a diagram that draws correctly and teaches nothing is
review's to catch.

**This does not overturn docs spec §3.9.** That section rules image comparison out of the
*snippet* gate, and it stays out: §3.4 gains no baselines. It gives three reasons, and this
gate is a different gate precisely because each one is a statement about where that gate runs
rather than about the idea:

- *`pytest-mpl` is a decorator on an in-process function returning one figure, which is not
  the shape of a subprocess running a page.* This gate is not `pytest-mpl`. It compares files
  already on disk with `compare_images`, and never holds a figure.
- *Baselines are sensitive to the freetype and matplotlib versions, so they are pinned in one
  environment while that gate runs in every one.* This gate runs in the documentation
  environment only — the one that builds what ships — so the baselines are pinned in the
  single environment that produces them.
- *A page's figures are anonymous and positional, so a baseline could only be keyed on figure
  order and would break when an author inserts a snippet.* This is what §3.2's rule 4 exists
  to answer: `:filename-prefix:` makes every published figure named, and a name survives the
  insertion of a section above it.

The sentence those reasons support — "what a how-to's figures should look like is already
pinned by `tests/plotting/test_images.py`, against the APIs the pages call" — remains true and
remains the reason this gate is narrow. `test_images.py` pins the *constructions*, in the test
matrix, across every supported Python. This pins the *artifacts*, once, where they are built.

(plots-spec-3-6)=
### 3.6 Baselines

`docs/baseline/`, outside `SOURCEDIR` so Sphinx never discovers or publishes them, and beside
the documentation they belong to rather than in `tests/baseline`, which is `pytest-mpl`'s and
is keyed by test name.

Regenerated by a `docs-figures` pixi task that copies the built images over the baselines,
so re-blessing an intended change is one command and a diff to read, not a hand copy per file.

`MANIFEST.in` prunes them, beside the `prune docs/src/developer/plans` that docs spec §5 put
there. They are build-verification artifacts rather than documentation content, and the gate
that reads them lives in `.github/scripts/`, which the sdist already prunes — so an unpacked
sdist could not run this check whether the baselines were there or not. The weight is the
second reason and the smaller one: `tests/baseline` held 16 images in 760 KB when this was
decided (2026-08-17), and a published figure is the larger of the two kinds, being a wider
canvas at a comparable density.

(plots-spec-4)=
## 4. The figure recipe

`figure.figsize` of `(8.0, 4.0)`, on the full five-family diagram, at the default extent,
with nothing hidden.

That was measured against the alternative when the decision was taken (2026-08-17). At
matplotlib's default figure size the tephigram's axes — a wide, short parallelogram — sits
in a square canvas with most of the height empty. At `(8.0, 4.0)` an emphasised member reads
immediately: the emphasis width against the ordinary isopleth is a large enough ratio to
survive the five-family grid, which it does not at the `(3.5, 3.5)` the image baselines use.

`savefig.bbox` of `"tight"` was part of the original recipe and is withdrawn (2026-08-18).
Its rationale was measured against matplotlib's *default*, square figure size, where the same
empty height above was what `"tight"` cropped away — and once `figure.figsize` is
`(8.0, 4.0)` that empty height is already gone, so the setting was answering a problem the
other one had already solved. What it costs instead was measured directly: a tephigram
rendered at `(8.0, 4.0)` with `add_logo(ax, loc="lower right")` and
`add_logo(fig, loc="upper left")`, saved once plain and once with `bbox_inches="tight"` — the
figure-anchored logo is present in the first image and absent from the second, while the
axes-anchored one survives both. `"tight"` crops the canvas to the drawn axes, and the margin
it removes is exactly where `howtos/logo.rst`'s first section puts a logo. The trade it
settles is a cosmetic white margin against a how-to whose picture does not show what its
prose describes, and `plot_rcparams` stays at matplotlib's default `savefig.bbox`.

Hiding the other four families was tried and rejected. It is clearer, and it costs more than
the clarity is worth: the diagram stops being a tephigram, the snippet teaches a gesture the
guide is not about, and three lines of hiding crowd out the one option the section exists to
show.

Zooming was tried and rejected for the same kind of reason: `set_extent` is another page's
subject, and the reader who copies a block without it should see what the page showed.

Rendering cost is not a constraint on any of this. A figure took 0.27 s once the first import
had warmed (2026-08-17), against a documentation build already measured in minutes.

(plots-spec-5)=
## 5. Boundary with the examples gallery

spec §8.6 provisions sphinx-gallery, scraped from `src/tephpy/examples`, and the roadmap's
Plan 7 delivers it. This is not that, and neither replaces the other.

A gallery entry is a standalone worked example, reached by browsing thumbnails, answering
"show me what this package makes". A how-to figure is subordinate to a paragraph, answering
"what does *this option* do". The same rendering machinery could serve both, and the gallery
should not re-decide §3.1's configuration or §3.5's pinning when it lands — it should adopt
them, or amend this document.

`sphinx_gallery_conf` keeps its empty directories. Nothing here populates them.

(plots-spec-6)=
## 6. Companion changes

Four documents stated what this one changed, and each became wrong the moment the first page
converted:

- **docs spec §3.9** described the corpus it executed as `code-block` and its near-miss set as
  the languages around python. It gained the directive, and the "deliberately out of scope"
  paragraph gained the pointer to §3.5 — the reasoning there stays as it is, because §3.5 does
  not contradict it.
- **`docs/src/developer/docs-style.rst`** gained "Published Figures", between "Code
  Examples" and "Attribute Documentation": the two page forms, the one-picture-per-point
  cadence, the five options of §3.2, the module-state rule of §3.3, and how to re-bless a
  changed figure. The gate in §3.4 enforces them; the style guide is where an author reads
  them before writing.
- **spec §8.6** lists the documentation extensions. `plot_directive` joined the list, and the
  sentence recording that nothing rendered a figure from source stopped being true.
- **`docs/src/developer/plans/2026-07-30-tephpy-member-emphasis.md`** is *not* corrected. Its
  "do not add a Sphinx extension as part of this work" was right when written, and a plan is a
  point-in-time record (docs spec §3.4). This document supersedes it; it does not edit it.

A changelog fragment covers the user-visible half — the how-tos gain figures — under the
`documentation` type.

(plots-spec-7)=
## 7. Scope

**In scope.** The user quadrant pages that publish figures; the extension and its
configuration; the two gates; the baselines and their regeneration.

**Out of scope.** The gallery (§5). The API any page exercises. `docs/src/tutorials/` and
`docs/src/explanation/` carry no python today and are governed by §3.2 from the day one of
them does, without amendment here.

**Open items**, tagged per docs spec §3.5.

- **Rejected** (2026-08-17) — **a dark-theme variant of every published figure.**
  `pydata-sphinx-theme` serves a dark mode, and a figure rendered on a white background stays
  white in it. The alternatives both cost more than the mismatch: a second render per figure
  doubles the images, the baselines and the gate's work, and a CSS inversion would invert a
  diagram whose colours carry meaning. What the reader sees is what their own `plt.show()`
  gives them. The logo how-to's `dark_background` block is not a counterexample: it carries
  `:nofigs:` and publishes no figure at all, for a reason of its own that has nothing to do
  with dark-theme variants — the inline isopleth labels are unreadable on a dark canvas
  today, which `howtos/logo.rst` records in prose beside the block.
