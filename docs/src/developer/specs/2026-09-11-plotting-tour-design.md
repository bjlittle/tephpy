# A Tour of the Plotting Package — Design Specification

```{readingtime}
```

This specification covers one new developer page: a map of `tephpy.plotting` for
someone about to change it. It is {issue}`66`'s mid layer — between the explanation
quadrant, which is written for a reader who has never opened the source, and the
docstrings, which are already strong.

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. Where it and the tree diverge it is the specification that gets corrected.
> Read it as current.

- **Date:** 2026-09-11 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `tour spec §…` — named for the page, a tour of one package, and
  not for the package itself, whose specification is the parent's `spec §3.2`
- **Scope:** `docs/src/developer/plotting.rst` — its placement, its sections, the
  direction its citations run, and the two gates that keep it describing code that exists
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) — `spec §3.2`
  specifies the package this page maps
- **Sibling specs:**
  [`2026-09-08-contributor-guide-design.md`](2026-09-08-contributor-guide-design.md) —
  `contributor spec §3.1` owns the developer section this page joins, and
  `contributor spec §3.8` the
  practice of recording what a gate cannot hold;
  [`2026-09-09-reanchor-plotting-design.md`](2026-09-09-reanchor-plotting-design.md) —
  `anchor spec §7`'s container census, which this page's citations are counted by

(tour-spec-1)=
## 1. Purpose

**The package is documented twice at the extremes and not at all in the middle.** Measured
2026-09-11 on `main` at `d4ecde6`:

| | |
|---|---|
| `tephpy.plotting` | **7 modules, 5,447 lines** |
| carried by two of them | `axes.py` 2,168 + `isopleths.py` 1,820 — **73%** |
| public names | **2** — `TephigramAxes`, `add_logo` |
| `spec §…` citations inside the package | **134** |
| of those, on `§3.2`'s seven leaves | **80** |
| `spec §3.2` itself | **462 lines**, 30.5% of a 1,513-line document |

The low layer is in good repair: 124 docstrings across the package, most citing the
specification section that decides it, and two module docstrings — `axes.py`'s in
particular — already carrying a paragraph of orientation. The high layer is
specified at length. What no file owns is the layer between them: **the order things
happen in, and who owns what.**

Two flows show the gap, and both span modules:

- **Edge ownership.** A family resolve reaches `_sync_edge_labels` from two sites —
  the `on_change` hook armed on all five families, and the end of `clear` — and from
  there to `_claim_edge` or `_release_edge`. Each docstring on that path describes its
  own step correctly. None of them gives the order, because no one of them is the place
  to.
- **The side panels.** `_relayout_side_panels` is called from three sites: a right-edge
  change in `_sync_edge_labels`, `plot_barbs`, and `annotate_indices`. Its contract —
  one divider, shared, rebuilt rather than torn down — is what makes the call order of
  those three irrelevant, which is precisely the kind of property a reader cannot infer
  from any single docstring.

A contributor changing either flow today reads `spec §3.2`'s 462 lines to find out what
they must not break. That is the section doing a job it was not written for, and
{issue}`66` says so.

(tour-spec-2)=
## 2. Decisions

1. **A map, not an account.** Every mechanism is stated once in the tree and cited here,
   never restated. The page carries what no docstring and no specification section owns:
   sequence, ownership, and where to look next (§3.6).
2. **`spec §3.2` is not touched.** Its prose stays whole and its anchors stay put, three
   days after `anchor spec` re-pointed 164 citations onto them. Relocating the
   "how it works now" half of it — the split {issue}`66` actually describes — is a
   separate thread, {issue}`299`, carried in §7.
3. **One page, the whole package.** Four of the seven modules are small, and a paragraph
   each in one table serves them better than a page each. A map that omits more than
   half of what it maps is not a map (§3.3).
4. **Citations run out only, and land on leaves.** The page cites specification
   subsections and sibling pages; nothing cites the page. Naming `spec §3.2` rather than
   `spec §3.2.3` would both send a reader hunting and fail `anchor spec §7`'s census, so the
   rule enforces itself (§3.5).
5. **The gates hold names, not prose.** Whether a paragraph is still *true* is not
   gateable; whether it still names code that *exists* is. Two gates, both on names,
   both with a floor under what they found (§5).

(tour-spec-3)=
## 3. Architecture

(tour-spec-3-1)=
### 3.1 Placement

`docs/src/developer/plotting.rst`, titled **A Tour of the Plotting Package**.

`developer/index.rst` grows from seven entries to eight, with the new page third:

| position | page | why there |
|---|---|---|
| 1 | `contributing` | how to contribute |
| 2 | `testing` | how to test what you changed |
| **3** | **`plotting`** | **what the code you are changing is** |
| 4 | `changelog` | |
| 5 | `docs-style` | |
| 6 | `packaging` | |
| 7 | `ci` | |
| 8 | `specs/index` | |

The two workflow pages come first because a contributor needs an environment before a
map; the process pages follow because they are consulted rather than read through.

**No landing table**, still. `contributor spec §3.1` declined one for the developer
section on the grounds that the content was maturing and a table commits to a
description of each page before there is a settled page to describe. Adding an eighth
page is not the event that changes that; `contributor spec §7` carries the question.

The page is read through, so it carries a reading-time banner — `reading spec`'s corpus
is derived over the whole tree and exempts only the two index pages by name, so the
banner is required rather than optional.

(tour-spec-3-2)=
### 3.2 The seven sections

| § | section | what it owns |
|---|---|---|
| 1 | lead | what `plotting` is, its two public names, and what sits under it (`transforms`) and beside it (`calc`, `sounding`) |
| 2 | the module map | seven rows: module → what it owns → where its rules are specified (§3.3) |
| 3 | the drawing model | zoom-aware artists — geometry precomputed over a generous domain and cached on the artist, clipped and re-labelled per `draw`, which is why pan, zoom, resize and `set_extent` are all automatically current |
| 4 | `clear` is the constructor | matplotlib calls it from `Axes.__init__` *and* on `ax.clear()`, and both paths rebuild every piece of projection-owned state; the five families are built before the first sync sees any; the extent lands last |
| 5 | edge ownership | resolve → `_check_label_edges` → `_sync_edge_labels` → `_claim_edge` / `_release_edge` (§3.4) |
| 6 | the side panels | one cached divider, shared; relayout rather than teardown; the pad that widens when the right edge carries ticks; and who removes the panels on a clear (§3.4) |
| 7 | where to look | "changing X? read Y" — a short table into specification leaves and docstrings |

Sections 5 and 6 are what earn the page. They span `axes` and `isopleths`, no docstring
owns either, and both are where a change that looks local is not.

(tour-spec-3-3)=
### 3.3 The module map

One table, seven rows, one per module in `src/tephpy/plotting/`:

| module | what it owns |
|---|---|
| `__init__.py` | the package's two public names |
| `axes.py` | the projection, the transforms, the accessors, edge ownership, the panel layout |
| `isopleths.py` | the five families, their option resolution, and the zoom ladder |
| `shading.py` | the CAPE and CIN regions |
| `barbs.py` | the wind-barb gutter and its staff |
| `logo.py` | the branding artist, specified separately in `logo spec` |
| `_theme.py` | the shipped styles |

Each row's third column names the specification section that decides the module, so the
table doubles as the page's index into `spec §3.2`'s leaves.

**The table is gated in both directions** (§5): a module arriving without a row fails a
test, and a row naming a module that has gone fails the same test. This is the one part
of the page that *must* change when the package does, so it is the one part a test holds.

(tour-spec-3-4)=
### 3.4 The spine, and the invariants it carries

Sections 5 and 6 of the page describe one flow each, in order, with each step's
mechanism cited rather than restated. What they add beyond the sequence is the set of
properties a reader would otherwise have to reconstruct:

**Edge ownership** (`spec §3.2.2, §3.2.3`):

- Ownership conflicts are rejected *before* anything is applied — the axes is the only
  object that can see a collision, so validation is handed to each family as a hook and
  runs inside the family's own rollback.
- A claim installs **identity** only: locator, formatter, visibility, colour, title.
  **Presentation is the user's from the claim onwards** — tephpy stamps its tick
  conventions once, when the edge axis is created, and never re-asserts them.
- The tick-colour memory is keyed by **owner and RGBA together**. A bare colour
  comparison would suppress a new owner's claim whenever its colour happened to match
  the previous owner's, leaving ticks in a colour that ties them to nothing.
- The sync is re-entrancy guarded, structurally rather than by assumption about
  matplotlib's internals.

**The side panels** (`spec §3.2.7`):

- **One divider per axes**, created once, cached, shared. A second
  `make_axes_locatable` call builds a fresh divider and detaches the earlier panel.
- Relayout, not teardown: the horizontal stack is rebuilt and every locator reassigned
  whenever a panel appears, so the inside-out order holds **regardless of call order**.
  `append_axes` only ever appends, so a remove-and-re-append would leave a phantom gap.
- The panel nearest the diagram takes a wider pad while the right edge carries isopleth
  ticks, which are wider than the 0.1 in gutter convention.
- **Who removes the panels on a clear depends on who called `clear`** — the diagram on a
  direct `ax.clear()`, the figure on a figure clear, told apart by the calling frame
  because the figure's state is identical either way.

Each of the above is one or two sentences on the page, each followed by its citation.
Where a reader needs the argument rather than the rule, the citation is the argument.

(tour-spec-3-5)=
### 3.5 Citations run out, and land on leaves

The page cites in one direction. It names specification sections in the plain-text form
`docs spec §3.6` resolves into links, and siblings with `:doc:`. It declares **no
anchors**, takes **no citation prefix**, and appears in no citation register: nothing in
`src/`, `tests/` or the specifications points at it.

**Bare, not in literals.** Measured 2026-09-11 against the build: the transform rewrites
a bare citation into a link and leaves a citation inside ``double backticks`` as a
rendered literal — still *validated* by the citation checker, but not navigable. So the
page writes `spec §3.2.3 decides this`, not ``` ``spec §3.2.3`` ```, and reserves the
literal form for quoting the citation form itself, which is what `docs-style.rst` does in
its own *Specification Citations* section. Of the developer section's pages only
`docs-style.rst` cites specifications in prose today — 26 bare citations — so the tour
is the second, and the convention is worth stating rather than inferring.

That is what keeps it free to be rewritten as the code moves, which a living map must be
and a citation target is not.

**Every citation names a leaf.** `spec §3.2.1`–`spec §3.2.7`, never `spec §3.2`. A container
citation sends a reader to a 462-line section to find the paragraph, and it is also a new
key in `anchor spec §7`'s census — `CONTAINER_CITATIONS` in `tests/test_citations.py` is
keyed by file and anchor, so the first one fails
`test_the_container_census_is_what_was_recorded` by name. The discipline is therefore
enforced by a gate that already exists, rather than by remembering.

(tour-spec-3-6)=
### 3.6 Map, account, and the line between them

The distinction §2 item 1 rests on, stated so a later editor can apply it:

| the page may say | the page may not say |
|---|---|
| that a property holds, in a sentence | *why* it holds, at length — that is the specification's |
| the order steps run in | what a step does internally — that is the docstring's |
| which module owns a concern | how the concern is implemented |
| where to read next | what the reader will find when they get there |

The test to apply when editing: **if this sentence and the specification disagreed
tomorrow, which one would be wrong?** If the answer is "the page", the sentence is an
account and belongs behind a citation instead.

(tour-spec-4)=
## 4. Companion changes

- `docs/src/developer/index.rst` — the toctree entry, third (§3.1).
- `tests/test_contributor_guide.py` — `"plotting"` joins `PAGES`, which gives the page
  the exists / in-the-toctree / reading-time trio. That tuple's comment currently reads
  "the pages contributor spec §3.1 adds" and must be re-worded: it will carry two
  specifications' pages.
- A changelog fragment, `documentation` type.
- {issue}`66` stays open. This closes its mid layer only.

(tour-spec-5)=
## 5. Testing

`tests/test_plotting_tour.py`, plus the three structural checks inherited from `PAGES`
above.

| gate | what it holds |
|---|---|
| module map completeness | every `src/tephpy/plotting/*.py` has a row **in the map's own table**, and every module that table names exists |
| symbol liveness | every `plotting` symbol the page names — the private helpers `_check_label_edges`, `_sync_edge_labels`, `_claim_edge`, `_release_edge`, `_relayout_side_panels`, `_figure_is_clearing`, found by pattern, and the declared public names `TephigramAxes`, `add_logo`, `IsoplethFamily`, `clear`, `configure`, `edge_axis`, `format_coord`, `plot_barbs`, `annotate_indices` — resolves by import and `getattr` |

**The map gate reads the table, not the page.** Corrected 2026-09-11 after review of
:pull:`303` found the first form green against a deleted row: a module name appears in the
prose beneath the table and again in the *Where to Look* table, so a page-wide scan cannot
tell a row that is present from a name that is merely mentioned. The parser takes the
`list-table` whose header names `Module`, and a page whose table it cannot find yields
nothing rather than everything.

**Each gate asserts a floor before it asserts its property, and the two floors do
different jobs.** A parser that silently matches nothing otherwise passes green — the
failure mode `contributor spec §3.8` records, and the one that has cost this repository
the most: a check whose own machinery is absent reports success.

- The module map **has ground truth on disk**, so the set comparison names exactly which
  module lost its row, and the floor need only catch the parser finding *nothing*. A
  count-based floor was tried first and rejected in the same review: at six rows of seven
  it front-ran the comparison and blamed the table's markup for what was a deleted row.
- The private helpers **have no ground truth** — nothing enumerates the names a page ought
  to mention — so there the floor is the whole defence, and it is a count.

Each floor is exercised by a test that feeds the parser input it must find nothing in, and
both failure directions of the map gate were run and seen to fail before the page landed.

**What these gates do not hold**, recorded rather than implied:

- whether a sentence is still *true*. A rename goes red; a mechanism that changes shape
  under a name that survives does not. Nothing cheap closes that, and the honest mitigation
  is that the page is short enough to re-read when `spec §3.2` changes.
- whether a citation points at the *right* leaf. `docs spec §3.6` holds that each one
  resolves, and `anchor spec §7` that it is not a container. Neither can say that
  `spec §3.2.3` was the apt one of the seven.

(tour-spec-6)=
## 6. Scope

In: one page, its toctree entry, its two gates, a changelog fragment.

Out, each with its thread:

| not doing | where it lives |
|---|---|
| relocating `spec §3.2`'s "how it works now" prose | §7, filed as {issue}`299` |
| the explanation-quadrant account — what a tephigram *is* | {issue}`66`'s high layer, closed 2026-09-11 by a section of *Why the Axes Are Rotated* |
| any diagram of the spine | {issue}`291` — the mermaid read-time network cost is undecided |
| a `developer/` landing table | `contributor spec §7` |
| docstring changes | none needed; the low layer is in good repair (§1) |

(tour-spec-7)=
## 7. Open items

1. **Relocating §3.2's living half.** This specification's option (c): the page maps and
   the specification keeps its prose. {issue}`66` describes option (b) — §3.2 shrinks to
   dated decisions and the page becomes the account of record. That is the larger and
   more honest split, and it rewrites sections 164 citations were re-pointed onto three
   days ago. Filed as {issue}`299`; the evidence it should be decided on is whether this
   page, once written, leaves `spec §3.2` visibly carrying prose no one reads. Revisit
   when the page has settled.
2. **Whether the tour should become a citation target.** §3.5 says no, so that it stays
   free to move. If `src/` comments start wanting to point at "the tour's edge-ownership
   section", that is evidence the page has become an account and item 1 is overdue.
3. **A second page, later.** §3.2 of this specification is seven sections in one page. If
   edge ownership and the panel layout outgrow it, the cut is a module map page plus a
   deep page — not a page per module.

(tour-spec-8)=
## 8. References

- {issue}`66` — populate the Diátaxis quadrants and build out a developer guide; this is
  its mid layer, and the issue closed on 2026-09-11 once its high layer landed
- {issue}`291` — mermaid, and the read-time network cost that defers any diagram here
- {issue}`299` — the relocation this specification declined, and what to measure first
- `spec §3.2.1`–`spec §3.2.7` — the package's specification, and this page's citation targets
- `contributor spec §3.1, §3.8` — the developer section, and recording what a gate
  cannot hold
- `anchor spec §7` — the container census that keeps this page's citations on leaves
