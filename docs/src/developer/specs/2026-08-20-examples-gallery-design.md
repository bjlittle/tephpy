# tephpy examples gallery — design specification

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. `src/tephpy/samples/`, `src/tephpy/examples/`, `src/tephpy/_cli.py` and
> `docs/src/conf.py` cite it by section — `gallery spec §3.2` and the like — so these
> sections *are* the reasoning behind what they do, and where the two ever diverge it is
> the specification that gets corrected. Read it as current.

- **Date:** 2026-08-20 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `gallery spec §…` — not `examples spec`, which would read as naming
  the package `src/tephpy/examples` alone, when half of what follows is about the sample
  data, the command line and the packaging that stand behind it
- **Scope:** the worked examples the package ships, the sounding data they draw on, the
  gallery built from them, and the command that runs them; the APIs they exercise are
  unchanged
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) — delivers
  the first half of spec §10's Plan 7 row and populates the sphinx-gallery provision of
  spec §8.6
- **Sibling spec:** [`2026-08-17-published-figures-design.md`](2026-08-17-published-figures-design.md)
  — plots spec §5 drew the boundary between a gallery entry and a how-to figure, and asked
  that the gallery adopt its configuration rather than re-decide it; §3.5 and §5 below are
  the answer

(gallery-spec-1)=
## 1. Purpose

`sphinx_gallery_conf` has named no example directory since Plan 1 shipped it. The
foundation plan said so in writing — "`examples_dirs`/`gallery_dirs` are empty here; Plan 7
populates the gallery" — so the extension has been loaded and inert for the whole life of
the project, and spec §8.6's "one example per identified use case, scraped from
`src/tephpy/examples`" describes a directory that does not exist.

The consequence is not only an empty page. tephpy ships no data, so every page that wants a
sounding must construct one, and the four §1 use cases that are *about* soundings have
nowhere to be demonstrated end to end. Spec §4 states the package's canonical usage as
fifteen lines of Python against Norman, Oklahoma on the morning of the 2013 Moore EF5
tornado, chosen so that `shade_cape` and `shade_cin` have visible regions to fill — and
that block has never been executed by anything. Spec §7 has always required a composed
figure baseline for it, deferred through five plans because it needs the union of Plans 5
and 6, which merged in {pull}`40` and {pull}`41`.

So this document delivers three things that turn out to be one thing: sample data a user
can load in one line, examples that draw the diagrams the specification has been describing
in prose, and the pinning that keeps the canonical figure honest.

(gallery-spec-2)=
## 2. Decisions

- **The sample data ships in the wheel.** A gallery offers every entry as a download, and a
  downloaded script that reads a file from a checkout fails for the reader who installed
  tephpy rather than cloning it. Data on the docs side would make the download link a lie.
- **The shipped format is IGRA, not Wyoming.** IGRA is a U.S. Government work in the public
  domain, which is the footing redistribution in a wheel needs; the University of Wyoming
  capture is courtesy-attributed and stays what it is today, a test fixture and the *live*
  route a how-to demonstrates. IGRA is also the reader that already selects an ascent by
  time from a multi-sounding file, so two soundings are one file and no new parser (§3.1).
- **One station, two times — 12Z and the 17Z special.** §3.1 records what was measured.
  The pair tells §1 item 4's own story, in the day's own data, rather than illustrating it.
- **An example is a module with a `main()` that returns its figure.** One file then serves
  the gallery, the command line, the image baseline and direct execution, without a second
  construction of the same figure anywhere (§3.3).
- **The registry is a list, written once.** The command line, the gallery's ordering and
  the smoke test all read it. Discovery by glob was rejected: it cannot fail, so an example
  that stops being found is silently absent from all three.
- **The gallery shows what the package draws; getting data in is a how-to.** This extends
  plots spec §5 from a boundary between two mechanisms to a test any candidate example is
  put to (§5).
- **The gallery adopts the published-figure configuration.** plots spec §3.1 settled the
  figure recipe and the format pinning for rendered documentation, and asked to be amended
  rather than duplicated. §3.5 inherits the recipe, and amends where it is applied and how
  much of it is pinned against a baseline.

(gallery-spec-3)=
## 3. Architecture

(gallery-spec-3-1)=
### 3.1 The sample data

`src/tephpy/samples/`, a package holding one IGRA v2 station file and the accessors over
it. It is `samples` rather than geovista's `pantry`, the standard this project otherwise
mirrors (spec §2): `pantry` names a mechanism — geovista's is a `pooch` cache that
downloads on first use — and tephpy's is a file already on disk, so the borrowed name would
promise machinery that is deliberately absent.

Three functions, name-keyed, matching the way `tephpy.config` and the command line already
address things:

```python
samples.available()             # ("norman-12z", "norman-17z")
samples.sounding("norman-12z")  # -> Sounding
samples.path()                  # -> the shipped IGRA file
```

`sounding` reads through the public `tephpy.io.igra.read(path, time=...)`, so the sample
accessor is a caller of the documented reader rather than a second way in. An unknown name
raises `ValueError` quoting `available()`. A new exception type was rejected: nothing has
failed to read, and a bad literal argument is what `ValueError` is for.

`path` takes no argument because there is one file, and it exists so the reader how-to of
§5 has something local to open.

**The data.** `USM00072357-data-trimmed.txt` — Norman, Oklahoma, 2013-05-20, both ascents
as whole byte-faithful blocks, in the shape `tests/fixtures/io/UKM00003808-data-trimmed.txt`
already established. 17 KB.

IGRA holds no 00Z ascent for that date; Norman ran a 12Z and a 17Z special, released
16:51 UTC, about three hours before the Moore EF5 touched down at 19:56 UTC. That is a
better pair than the diurnal 00Z/12Z first sketched, because the evolution between them is
the reason an operational user overlays two soundings at all. Read through tephpy's own
`calc.indices` (2026-08-20):

| | 12Z | 17Z |
|---|---|---|
| CAPE | 1747.9 J/kg | 4831.6 J/kg |
| CIN | −270.7 J/kg | 0.0 J/kg |
| LCL / LFC / EL | 938.7 / 690.3 / 215.9 hPa | 898.1 / 758.8 / 182.2 hPa |
| Lifted index | −8.2 | −11.4 |
| Levels, winds | 68, present | 71, present |

The 12Z figures land on spec §4's "≈1800 J/kg of CAPE and ≈−270 J/kg of CIN", which is the
first time that claim has been checked against data rather than against the research pass
that produced it. Both ascents carry winds, so the barb and hodograph examples need no
third sounding.

**Provenance** is recorded the way `tests/fixtures/io/README.md` records the fixtures':
source URL, capture date, what was cut, and the NOAA/NCEI attribution with its DOI. It
lives in the `tephpy.samples` module docstring rather than in a `README.md` beside the
data, because that docstring is published by autoapi and a README inside a package is
not — and IGRA's attribution is owed to the reader, not to the repository.
`tests/fixtures/generate_io_fixtures.py` gains the sample as a second destination: one
script already knows the IGRA URL layout and the byte-faithful trimming rule, and two
would drift.

(gallery-spec-3-2)=
### 3.2 The examples package

`src/tephpy/examples/`, holding the five modules of §4, a `GALLERY_HEADER.rst`, and an
`__init__.py` carrying the registry.

Every module is named `plot_*.py`. This is load-bearing rather than cosmetic:
sphinx-gallery's `filename_pattern` defaults to `/plot`, and only a matching file is
*executed* — a file outside the pattern is still rendered, silently, with no figure and no
error (verified against sphinx-gallery 0.21.0, 2026-08-20). A gallery entry that quietly
stops running is exactly the failure this project writes gates against, so the naming
convention is stated here and asserted in §3.7.

`GALLERY_HEADER.rst` is the header sphinx-gallery requires in an examples directory
(`GALLERY_HEADER.[ext]`, or `README.[ext]` for backward compatibility). It ships inside the
package, which is where the extension insists on finding it, and it is the natural place
for the IGRA attribution to appear on the rendered index.

`__init__.py` is not scraped — sphinx-gallery's `ignore_pattern` excludes it by default —
and so is free to hold the registry: an explicit ordered mapping of CLI name to module,
where the CLI name is the module name with its `plot_` prefix removed
(`plot_parcel_analysis.py` → `parcel-analysis`).

(gallery-spec-3-3)=
### 3.3 The shape of an example

```python
def main() -> Figure:
    ...
    return fig


if __name__ == "__main__":
    main()
    plt.show()
```

`main` builds the figure and returns it. The guard shows it. Four consumers then share one
construction:

- **sphinx-gallery** executes the file in a module it builds with
  `spec_from_loader("__main__", None)`, so `__name__` is `"__main__"` and the guard runs
  (verified 2026-08-20). `plt.show()` under the Agg backend emits no warning, checked
  under `-W error::UserWarning` with a figure open.
- **`tephpy examples run`** imports the module, calls `main()`, then shows — §3.4.
- **`pytest-mpl`** decorates a function returning a figure, which is precisely `main`'s
  signature, so the baseline of §3.7 pins the example itself rather than a re-creation of
  it.
- **`python plot_parcel_analysis.py`**, which is what the gallery's download link hands the
  reader, runs the guard and draws.

Returning the figure rather than showing inside `main` is what makes the third of those
possible. An example that called `plt.show()` in `main` would have to be re-implemented in
the test to be pinned, and the pinned figure would then be a claim about the test rather
than about what was published.

**The module docstring is not a docstring.** It is sphinx-gallery's title block — an RST
section heading and the page's opening prose, rendered above the figure — so it carries no
numpydoc summary line and never will. The two checks that read it as one are therefore
switched off for `plot_*.py`: ruff's `D205` and `D400`, in `pyproject.toml`'s
per-file-ignores, and the `numpydoc-validation` pre-commit hook, by exclusion. An inline
`numpydoc ignore=SS01` would silence the hook and keep `main()` validated, and was rejected
— `docs/src/developer/docs-style.rst` rules linter directives out of code a reader is
invited to copy, and the gallery hands them the file. `main`'s own docstring is an ordinary
numpydoc one, and ruff's pydocstyle rules still cover both.

Being page prose rather than a docstring also settles where the glossary rule of spec §8.6
bites. An example's docstring, and `GALLERY_HEADER.rst`, are narrative prose: the first
mention of a term on each gets a `:term:`, exactly as a how-to page would. The `# %%` block
comments and `main`'s numpydoc are not, and take none. Sweeping the five against the
glossary on 2026-08-21 is what added `projection`, `cap`, `special sounding` and `hodograph`
to it — a gallery page is often where a term first reaches a reader in prose, because the
rest of the documentation meets it inside a code block.

The cost is the notebook. sphinx-gallery's reST-to-markdown converter special-cases `:math:`
and `:ref:` and passes every other role through verbatim (`rst2md`, 0.21), so a downloaded
`.ipynb` shows ``:term:`dewpoint` `` where the page shows a link. That was already true of
the `:class:` reference this section's own example carries, and the alternatives are worse:
`pypandoc` converts properly but takes a pandoc binary into the documentation environment
for the sake of one cell's cosmetics, and writing the prose role-free would cost the HTML
page — the artefact almost every reader actually meets — to tidy the one they download. So
the rule is applied as written, and the density is kept honest instead: link the terms a
sentence leans on, not every term it contains. `plot_sounding.py` leaves "profiles"
unlinked for exactly that reason, the `sounding` entry it links two lines later having
already defined them.

**An example is typed the way a user writes one.** A projection is registered at runtime, so
`plt.subplots(subplot_kw={"projection": "tephigram"})` is typed `Axes` and every tephigram
method called on it is an `attr-defined` error. That is matplotlib's projection registry and
not a tephpy defect — cartopy's `GeoAxes` types the same way — and the answer for library
code is a `cast`. The examples are not library code: they are what a user writes, published
for a user to copy, and a `cast` in a file offered for download is machinery the reader has
to see past. So that one error code is disabled for `tephpy.examples.*` in `pyproject.toml`'s
mypy overrides, and everything else mypy checks about them still applies.

Every example that loads data takes it from `tephpy.samples`; `plot_tephigram.py` draws the
bare diagram and loads none. None reaches the network — spec §7 rules live network out of
CI, and sphinx-gallery executes examples during the documentation build.

None writes a file either, for the same reason: the build executes them, so a `savefig`
call leaves an artefact in the generated tree on every build. Spec §1 item 4 asks for
publication-quality vector output and spec §4's canonical block ends on
`fig.savefig("sounding.pdf")`, so the line has to appear somewhere — it appears in an
example's prose, shown and not executed. That is not a weaker demonstration than running
it: spec §10's Plan 3 row already pins vector output with a `savefig` smoke test over
PDF and SVG, and an example that wrote a PDF nobody opens would prove nothing the test
does not.

(gallery-spec-3-4)=
### 3.4 The command line

`tephpy examples`, a second subgroup beside `tephpy config` in `src/tephpy/_cli.py`:

- `tephpy examples list` — the registry names, in order.
- `tephpy examples run <name>` — one example.
- `tephpy examples run --all` — every example, in registry order.

The examples ship in the wheel, so without this a user who installed tephpy has five
scripts they can neither find nor run. geovista, the standard of spec §2, ships the same
capability; `docs/src/reference/cli.rst` documents the group through `sphinx-click` with
`:nested: full`, so the page needs no edit.

It honours `_cli.py`'s own rule that "the command line is never the only way to do
something" — `tephpy.examples` is importable, and every example is a file the gallery
offers for download.

There are no `--save`, `--output-dir`, `--format` or filtering options, and no backend
handling: `run` calls `main()` and then `plt.show()`, inheriting whatever backend is in
force. Each of those flags is a script the user can write in three lines against an API
that returns them a `Figure`, and together they would turn a discovery aid into a rendering
tool with its own configuration surface.

(gallery-spec-3-5)=
### 3.5 The gallery and its configuration

`examples_dirs` points out of the documentation tree at `src/tephpy/examples`;
`gallery_dirs` points at `docs/src/gallery`, inside the Sphinx source tree because
sphinx-gallery writes there, and git-ignored because everything in it is generated —
alongside `docs/src/sg_execution_times.rst`, which `.gitignore` already covers for the same
reason.

The gallery is a top-level section: its own toctree entry, sibling to the four Diátaxis
quadrants rather than inside one. Diátaxis has no gallery quadrant, and browsing
thumbnails is neither a lesson nor a recipe; spec §8.6 itself lists sphinx-gallery
separately from the four directories. Filing it under `tutorials/` was rejected — it would
put browse-by-thumbnail beside the browser demo lesson, and compete with the tutorials that
7b writes for that index.

It gets **no landing-page card**. A fifth card was built and rejected (2026-08-21): the
landing grid is the four Diátaxis quadrants, so anything sitting in it reads as a fifth
quadrant, which is exactly what the gallery is not. The toctree entry is the way in, and
the gallery's own thumbnails are what a reader browses once there.

**Ordering is the registry's.** `within_subsection_order` defaults to
`NumberOfCodeLinesSortKey`, which sorts by length and would bury the canonical figure —
the longest example and the one that should lead — at the bottom of the page. A sort key
that reads the registry replaces it, so registry order is gallery order is `run --all`
order, and there is one place to change it. Numbering the filenames was rejected: those
names are imported by users and printed by `examples list`.

It is named as a **dotted string**, `"tephpy_gallery_order.RegistryOrder"`, resolved by
sphinx-gallery's own importer, and the class lives in `docs/src/_ext/` beside the two
extensions already there. Assigning the class object directly is the obvious spelling and
it breaks the build: a class in `sphinx_gallery_conf` makes the value unpickleable, Sphinx
warns `cannot cache unpickleable configuration value` under `config.cache`, and this
project builds with `--fail-on-warning`. Both spellings were built to confirm which
(2026-08-20).

**What is inherited from plots spec §3.1.** The figure recipe — `figure.figsize` of
`(8.0, 4.0)` on the full five-family diagram, matplotlib's default `savefig.bbox` — and the
single `png` format. A gallery entry and a how-to figure are different things (§5), but
they are the same picture of the same diagram, and two recipes would drift into two house
styles.

**Where the recipe is applied differs.** plots spec §3.1 sets the figure size through
`plot_rcparams`, which is a `plot_directive` setting and reaches nothing here. Nor can
`conf.py` set it globally: sphinx-gallery resets matplotlib *before every example*
(`reset_modules` defaults to `("matplotlib", "seaborn")` and `reset_modules_order` to
`"before"`, and its reset calls `plt.rcdefaults()`), so a configured `figure.figsize` is
discarded before the first line of an example runs. Each example therefore passes
`figsize=(8.0, 4.0)` at its own `subplots` or `figure` call. That is not a workaround but
the better placement: the downloaded script is the published figure's only reproduction, and
a size that lived in `conf.py` would not travel with it.

**What is not.** `plot_directive`'s settings are directive options and do not reach
sphinx-gallery; the equivalents are set in `sphinx_gallery_conf`. And the pinning differs:
plots spec §3.5 compares every published figure against a baseline in `docs/baseline/`,
because a how-to's picture is subordinate to prose that claims something about it. A
gallery entry claims nothing beyond itself, so §3.7 pins one figure — the canonical one
spec §7 has always required — and lets the build's own execution failure catch the rest.
Pinning five would add four baselines to regenerate on every styling change, and styling
has moved repeatedly.

(gallery-spec-3-6)=
### 3.6 Tags

Tags are sphinx-gallery's own, not a new extension. The installed sphinx-gallery 0.21.0
reads a `# sphinx_gallery_tags = [...]` flag from an example's source, renders the tags on
its page, and — because `gen_gallery.setup` registers `sg-tags.js` unconditionally — gives
the gallery index a tag filter that narrows the thumbnails and records the selection in a
`?sg-tags=` query parameter. All five example pages and their five `data-sgtags` thumbnails
were built and inspected to confirm it (2026-08-20).

That retires `sphinx-tags`, which spec §8.6 has listed since Plan 1 and {issue}`76` still
tracks. It was specified before sphinx-gallery had tags of its own, and it solves a
different problem — per-tag pages across the whole site, not a filter over one gallery. A
five-example gallery does not need site-wide tag pages, and taking the dependency would
leave two tag mechanisms live at once with nothing to say which an example's tags feed.
Tagging the tutorials and how-tos is 7c's question, and the one that would earn it.

Tags come from a closed vocabulary — `diagram`, `isopleths`, `sounding`, `barbs`,
`analysis`, `shading`, `indices`, `overlay`, `metpy` — of two to four per example. An open
vocabulary was rejected for the reason a glossary has one canonical spelling per concept
(spec §8.6): a `barb` filter button beside a `barbs` one splits the very index the feature
exists to build.

The flag is the single declaration, because it is the only one sphinx-gallery reads; the
registry (§3.2) holds names and order, not tags. That places the vocabulary outside the
registry's reach, so §3.7 asserts it from the source. It has to: a misspelled flag —
`sphinx_gallery_tag` for `sphinx_gallery_tags` — parses to a differently-keyed entry and is
discarded in silence, with no warning to fail the build on (verified against the real
parser, 2026-08-20). That is the same silent absence §2 rejects glob discovery for.

The flag stays visible in the published source. sphinx-gallery's
`sphinx_gallery_start_ignore` block would hide it from the page and was tested working, but
plots spec §3.1 set `plot_include_source = True` on the reasoning that "the source is the
point, so it is shown", and hiding lines from a page whose purpose is showing source
contradicts it — for a saving of one self-explanatory line on the page, at a cost of three
lines of machinery in the file the reader downloads and runs.

(gallery-spec-3-7)=
### 3.7 Packaging and gates

`tephpy.examples` and `tephpy.samples` are picked up by the existing
`[tool.setuptools.packages.find]` glob. Their non-Python files — the IGRA sample and
`GALLERY_HEADER.rst` — need a `package-data` entry beside the existing
`plotting/_static/*.png`, and `MANIFEST.in` a matching `recursive-include`, or the wheel
carries importable modules with nothing to read.

`ci-wheels`' install smoke test gains `tephpy examples list`. It is the one check that
exercises the installed artifact rather than the checkout, so it is the only one that can
catch a `package-data` miss — the failure mode this whole section exists to prevent.

Three things are asserted, all of them off the registry:

1. **Every example runs, at the gallery's size, and closes with its guard.** Parametrised
   over the registry: `main()` is called and the figure's size read back off it, and the
   guard is read out of the source as an AST — the calls it makes, not merely its presence.
   A broken example then fails `pixi run tests` across the supported Pythons, not only the
   documentation build. The other two are checks nothing else makes. §3.5 puts the figure
   size inside each file, so no configuration outside it can hold it there. And the suite
   calls `main()` directly, so a guard that went missing would break nothing here, while
   sphinx-gallery would execute the file, find no figure, and publish the page with its
   `no_image.png` placeholder — a supported case it emits no warning for, so
   `--fail-on-warning` would not catch it either. That is the one silent failure this
   section has left.
2. **The registry, the directory and the vocabulary agree.** Every `plot_*.py` is
   registered, every registered module exists, and every example declares two to four tags
   drawn from §3.6's vocabulary. This is what makes the registry a single source of
   truth rather than a second list to keep in step.

   The tags are read from the source text, not from a `sphinx_gallery` import: the flag is
   a comment, so importing the module cannot see it, and sphinx-gallery is absent from the
   `test-py3*` environments CI runs the matrix in — a test that skipped without it would
   always skip where it matters. Reading the text also makes the assertion the one §3.6
   needs, because a test that asked the real parser for the tags of a file spelling the
   flag `sphinx_gallery_tag` would be told there are none and could not tell that from an
   example that declared none.
3. **The canonical figure is pinned.** `pytest-mpl` over
   `tephpy.examples.plot_parcel_analysis.main`, satisfying spec §7's composed-figure baseline —
   the last outstanding baseline of the roadmap, and the one that has been waiting for
   Plans 5 and 6 together.

That third test is a `tests/` one rather than a documentation-side one because the
documentation-side figure gate cannot see the gallery at all. `docs-check-figures` builds
its expected set from the `:filename-prefix:` each `plot_directive` declares on a page,
deliberately rather than by globbing the build's `_images/` (plots spec §3.5); sphinx-gallery
writes its figures through its own scraper and declares no prefix, so the gate stays at the
twelve figures of two how-to pages and every gallery figure is invisible to it.
`docs-check-links` is scoped the same way and is likewise unaffected. Of the post-build
gates only `docs-check-citations` sees the new pages, because it walks all of them.

So the gallery's five figures are covered by one baseline and the build's own execution of
the other four — an example that stops drawing fails, an example that draws something else
does not. Widening that is a matter of adding `mpl_image_compare` tests, not of configuring
a gate that was never pointed here.

`docs-clean` removes `docs/src/gallery` and `docs/src/sg_execution_times.rst` alongside the
build tree it already clears. `docs-all` additionally runs `docs-browser-test`, which needs a
hand-installed Chromium and has nothing to do with the gallery.

(gallery-spec-4)=
## 4. The example set

One per §1 use case, plus the composition spec §9 promises when it rules a hodograph out of
scope. Four of the five draw from `tephpy.samples`; `plot_tephigram.py` needs no data.

| Module | CLI name | Shows | §1 | Tags |
|---|---|---|---|---|
| `plot_tephigram.py` | `tephigram` | The bare diagram: five isopleth families, the default extent, `set_extent` | 1 | diagram, isopleths |
| `plot_sounding.py` | `sounding` | 12Z temperature and dewpoint, wind barbs on the gutter staff | 2 | sounding, barbs |
| `plot_parcel_analysis.py` | `parcel-analysis` | spec §4's figure: parcel path, CAPE and CIN shading, the indices panel (which reports the LCL) | 3 | analysis, shading, indices, sounding |
| `plot_sounding_comparison.py` | `sounding-comparison` | 12Z against 17Z on fixed extents, distinguishable styles, legends carrying station and time; the vector-output line in prose (§3.3) | 4 | overlay, sounding |
| `plot_hodograph.py` | `hodograph` | MetPy's `Hodograph` inset on a tephigram from the same `Sounding` | spec §9 | metpy, barbs, sounding |

`plot_parcel_analysis.py` leads the gallery (§3.5) and is the baseline of §3.7. It is the
package's shop window, and it is the one example whose figure the specification already
describes in words. It is spec §4's block call for call, with four deliberate divergences:

- `wyoming.fetch` becomes `samples.sounding("norman-12z")` — the network of §3.3.
- The closing `savefig` is dropped, appearing instead in `plot_sounding_comparison.py`'s
  prose — the file write of §3.3.
- `subplots` gains `figsize=(8.0, 4.0)`, because §3.5's recipe cannot be configured for a
  gallery sphinx-gallery resets matplotlib in front of.
- `ax.legend()` is added, because spec §3.4 keeps legends stock matplotlib: tephpy sets the
  labels and the user draws them, so a block that never calls it publishes none.

The first two are properties of the build and the third of the page, not of the diagram; the
fourth renders a label spec §4's own comment already claims for it. So the picture the
example draws is the one spec §4 specifies.

`plot_hodograph.py` **insets** the hodograph rather than setting it beside the diagram. Two
`1, 2` subplots was the first build and it was rejected in review (2026-08-21): at the
§3.5 figure size each panel gets four inches, and a tephigram at four inches wide is
illegible — the isopleth labels collide and the thumbnail shows a smudge. An
`inset_axes((0.02, 0.55, 0.31, 0.43))` in axes fractions puts the hodograph over the top
left of the view — the cold, low-θ corner no ascent reaches, so the inset hides background
isopleths and no part of the profile — and leaves the tephigram the figure's full width.
MetPy plots pint quantities, so matplotlib labels both inset axes `meter/second`; the
example clears them and states the unit once in the inset title.

`plot_sounding_comparison.py` is where the 12Z/17Z pair earns its place: across five hours
the cap erodes from −271 J/kg to nothing while CAPE nearly triples, so the two profiles are
visibly different and the comparison has a subject. Two arbitrary soundings would show the
API and teach nothing. Its `EXTENT` is a quarter narrower than the default view and clips
both ascents near 250 hPa: the difference the example is about is in the lower troposphere,
far below that, and a frame closer than the default is also what keeps the `set_extent` call
from restating what `plot_tephigram.py` already shows. The prose says so in those words
rather than "below the cap", which the same paragraph has just used for the inversion.

(gallery-spec-5)=
## 5. What belongs in the gallery

plots spec §5 distinguished a gallery entry — "a standalone worked example, reached by
browsing thumbnails, answering *show me what this package makes*" — from a how-to figure,
"subordinate to a paragraph, answering *what does this option do*". That was written to
keep two rendering mechanisms apart. It also answers a question this document has to
settle repeatedly, so it is promoted here to a test:

**The gallery shows what the package draws. Everything else is a how-to.**

The candidate it was first applied to was an `io` example — the two supported routes into a
`Sounding`, `wyoming.fetch` and `igra.read`. It fails on both limbs. Its subject is not a
picture, and nobody browses thumbnails to learn how to open a file; and spec §7 forbids
live network in CI while sphinx-gallery executes examples during the build, so the Wyoming
half could only be shown without running, in a surface whose entire affordance is the
thumbnail it would not have.

Its home is a how-to, beside the eccodes recipe that answers the adjacent question — what
about TEMP and BUFR — which spec §10 already assigns to the same tranche of work. The
eccodes recipe is 7b's and the reader how-to itself is 7c's (§7).

The same test rules out a configuration example, an installation example, and anything else
whose figure would be incidental to its point. It does not rule out an example that
happens to load data; `plot_sounding_comparison.py` reads two soundings. The subject is what
is tested, not the API surface touched.

(gallery-spec-6)=
## 6. Companion changes

- **spec §8.6** describes sphinx-gallery as scraping `src/tephpy/examples` and lists
  sphinx-tags among the extensions. The first becomes true here; the second is deleted,
  because §3.6 tags the examples with sphinx-gallery's own mechanism and takes no second
  dependency to do it. The section also gains the gallery's place in the navigation, which
  it did not previously state.
- **spec §10's Plan 7 row** splits. This document is 7a. The row is rewritten to name the
  two halves and mark 7a delivered, with 7b — tutorials, explanation, the glossary sweep,
  the README non-goals statement, the eccodes and reader how-tos, the doctest gate and the
  SPEC 0 packaging statement — carried forward as the remainder.
- **spec §10 item 15 and {issue}`76`** list three residuals. The sphinx-tags residual is
  closed as superseded — §3.6 delivers what it asked for, tagged examples with a filter,
  without it; the doctest task with its `ci-docs` run, and spec §8.3's SPEC 0 statement,
  stay open and move to 7b. The issue is updated rather than closed, and the update records
  the supersession so a reader does not re-adopt the dependency.
- **spec §7's composed §4-figure baseline** is delivered by §3.7, and spec §10's
  cross-cutting rule that "image baselines ship with their feature" is satisfied for the
  last row of the table.
- **plots spec §5** ends "`sphinx_gallery_conf` keeps its empty directories. Nothing here
  populates them." That sentence is now false and is amended to point here, which is what
  that section invited. Its §3.1 is unchanged: §3.5 above adopts it.
- **`docs/src/developer/docs-style.rst`** gains "Gallery Examples" beside "Published
  Figures": the `plot_` prefix and why it is load-bearing, the `main()`-returns-a-figure
  shape, the tag vocabulary, and §5's test for what belongs.
- **`docs/src/developer/specs/index.rst`** gains the `gallery spec §…` row and the toctree
  entry.
- **`tests/fixtures/io/README.md`** records that its generator now writes a second
  destination under `src/`.

Changelog fragments cover the two user-visible halves: `feature` for `tephpy.samples` and
the `tephpy examples` command, and `documentation` for the gallery itself. There is no
`dependency` fragment — the documentation extensions are unchanged, which is the point of
§3.6.

(gallery-spec-7)=
## 7. Scope

**In scope.** The sample data and its accessors; the five examples; the `tephpy examples`
command; the gallery, its configuration, ordering and tags; the packaging that carries all
of it into the wheel; the three gates of §3.7 and the composed-figure baseline.

**Out of scope.** Everything spec §10's Plan 7 row assigns to documentation *completion*,
which is 7b: the tutorials and explanation quadrants, the glossary sweep, the README
non-goals statement, the eccodes recipe, the reader how-to of §5, the doctest task and its
CI run, and spec §8.3's SPEC 0 packaging statement. The APIs any example calls are unchanged;
an example that wants an API tephpy does not have is a defect report, not a scope question.

**Open items**, tagged per docs spec §3.5.

- **Resolved** (2026-08-25, scope spec §3.3 and scope spec §3.5) — **the doctest task and
  its `ci-docs` run, and spec §8.3's SPEC 0 packaging statement.** Plan 7b delivered the
  packaging statement and rejected the doctest task as superseded by docs spec §3.9's
  snippet executor. With sphinx-tags rejected below, all three of spec §10 item 15's
  re-homed residuals are settled and {issue}`76` is closed.

- **Rejected** (2026-08-20) — **the sphinx-tags dependency.** spec §8.6 and {issue}`76`
  committed to it before sphinx-gallery had tags of its own. It now does, with the filter
  UI that was the whole reason to want them (§3.6), so adopting sphinx-tags would add a
  dependency to duplicate a feature already installed. What it offers beyond that — a
  site-wide tag index spanning the narrative documentation — is a question for 7c, which
  owns the tutorials and explanation quadrants that would be tagged.

- **Deferred** (7c — {issue}`66`) — **the reader how-to.** §5 sends the `io` example there.
  The eccodes recipe beside it landed in Plan 7b (scope spec §3.2); the reader how-to did
  not, because it is where `ax.fit(...)` would be taught and {issue}`184` has not landed
  yet (scope spec §3.6).

- **Rejected** (2026-08-20) — **a sixth, `io` example.** §5 gives the reasoning: its
  subject is not a picture, and the network constraint makes the misfit mechanical as well
  as conceptual.

- **Rejected** (2026-08-20) — **`backreferences_dir` mini-galleries on the API pages.**
  sphinx-gallery can add an "Examples using `plot_sounding`" block to each autoapi page.
  With five examples the blocks would be near-identical and mostly empty, and it couples
  the generated API reference to the example set. Worth revisiting if the gallery grows
  past a screenful.

- **Open** ({issue}`77`) — **the check-manifest CI gate.** It was deferred until "the wheel
  carries domain code"; §3.7 now puts data files in it too, and `MANIFEST.in` has already
  drifted once. Nothing here fixes it, and the case for it is stronger than when the
  deferral was written.
