# Re-anchoring the Plotting Section — Design Specification

```{readingtime}
```

This specification covers the parent specification's `spec §3.2`, the `plotting`
section, and the 170 citations that land on it.

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. Where it and the tree diverge it is the specification that gets corrected.
> Read it as current.

- **Date:** 2026-09-09 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `anchor spec §…` — named for the work, re-anchoring one section, and
  not for the anchor machinery in general, which is `docs spec §3.6`'s
- **Scope:** giving the parent specification's §3.2 an internal structure, and moving the
  170 citations that land on it onto the subsection each means
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) — §3.2 is
  the section this restructures
- **Sibling specs:**
  [`2026-08-03-published-specs-design.md`](2026-08-03-published-specs-design.md) —
  `docs spec §3.6`'s anchor/heading contract, which decides the shape available here;
  [`2026-09-08-contributor-guide-design.md`](2026-09-08-contributor-guide-design.md) —
  `contributor spec §3.8`'s practice of recording what a gate cannot hold

(anchor-spec-1)=
## 1. Purpose

**Nearly half the citations of the parent specification land on one section, and that
section has nowhere specific to land.** Measured 2026-09-09 on `main` at `e2bd346`:

| | |
|---|---|
| `spec §3.2`'s size | **413 lines** (126–538), 28% of a 1465-line document |
| citations of it in `src/` and `tests/` | **170 of 401** — **42%** |
| files carrying them | 15, of which five carry 87% |
| citations naming a subsection of it | **0** — there are no subsections to name |
| of the 170, references to re-point | **164**; six stay on the container (§3.3) |
| internal structure | 15 top-level bullets and ~90 lines of discrete topics, under **no subheadings at all** |

So §3.2 absorbs 42% of the citations in 28% of the text, and each of the 170 resolves to the
same 413-line target. A reader following one arrives at a section and must then find the
paragraph themselves.

**The counts exclude the other sixteen specifications' own §3.2**, whose prefixes are derived
from each document's first anchor slug rather than hand-listed. A first pass using a naive
pattern under-reported by eight, discarding citations preceded by an ordinary word — "as
described in spec §3.2". The derivation is recorded because the number is the argument.

{issue}`293` carries the measurement; {issue}`66`'s third part is what it was taken for.

(anchor-spec-2)=
## 2. Decisions

1. **Seven subsections, cut thematically rather than per bullet.** §3.2's fifteen bullets run
   from one line to 63; a heading per bullet would give a one-line bullet its own citable
   number and produce a set too fine to stay stable. The anchors are an interface 170
   citations depend on, and fewer, larger, topic-shaped anchors survive editing (§3.1).
2. **§3.2 gains headings, because anchors cannot exist without them.**
   `check_citations.py`'s `check_anchors` asserts in both directions that every anchor sits
   immediately above the numbered heading it is numbered for, and that every numbered heading
   carries an anchor. So this is not "sprinkle anchors on a wall of prose"; it is giving §3.2
   the structure it has never had (§3.2).
3. **Every one of the 170 citations is considered, and 164 are re-pointed**, in six batches
   by file. Adding anchors
   while leaving the citations on the container would make the section navigable and leave
   untouched the thing {issue}`293` was filed about (§3.3).
4. **The tool is a worksheet, not an oracle.** Measured: keyword matching over a citation's
   surrounding prose classifies about half, and gets *worse* with more context — 49% at 120
   characters, 41% at 400, 27% at 900 — because a wider window matches more topics.
   Clustering by enclosing symbol gives 125 groups, 105 of them singletons.
   Neither makes the work small, and a tool presenting confident proposals for half of them
   would invite rubber-stamping exactly where attention is needed (§3.4).
5. **Meaning is reviewed, not gated, and the limit is written down.** The gate checks that a
   citation *resolves*; nothing can check that it names the section meant (§3.5).

(anchor-spec-3)=
## 3. Architecture

(anchor-spec-3-1)=
### 3.1 The seven cuts

Verified as a partition: 413 of 413 lines, no gaps and no overlaps.

```text
§3.2.1  The diagram, and what is drawn by default      126-153   28 lines
        TephigramAxes, the grid, the five families, differences from tephi

§3.2.2  Isopleth labels: inline or on the edges        154-208   55 lines
        placement, the declutter control, the inline box's tint and clearance

§3.2.3  Claimed edges, their ticks and the title       209-260   52 lines
        claiming and releasing, stock ticks, the split axis title, edge_axis

§3.2.4  Emphasis                                       261-343   83 lines
        emphasis= on every accessor, and emphasis forcing its member drawn

§3.2.5  The plotting accessors                         344-429   86 lines
        plot_profile, plot_sounding, plot_barbs, shade_cape/shade_cin,
        annotate_indices, set_extent

§3.2.6  The cursor readout                             430-451   22 lines
        format_coord, the field registry, NaN rendering

§3.2.7  Extent, edge coverage and the panel layout     452-538   87 lines
        DEFAULT_EXTENT, the dead corner, the per-family coverage table,
        the side-of-axes contract
```

**The listing is fenced deliberately, and the prose below names these subsections by
title rather than by number.** They do not exist yet, so citing one would resolve to
nothing and fail `check_citations.py` — and `read_lines` skips fenced blocks, which is
the same allowance `docs spec §3.3` relies on to show an anchor that is an example
rather than a reference. This specification cannot cite the sections it is proposing.

**The cursor readout stands alone at 22 lines**, which is smaller than the others and
deliberate: nine of the citations carrying an unambiguous topic signal are about the
cursor readout, and the field registry is exactly the kind of specific target this work
exists to provide. Folding it into the accessors would put those citations back on an
108-line section.

*Corrected 2026-09-09, while the plan was being written.* This section first said the cuts
fall on existing paragraph boundaries and that no prose is rewritten. **That is true of two
of the seven.** Measured: the first cut and the last fall on clean boundaries; the other five land
*inside a bullet list* — the fifteen bullets are one list introduced by `Differences from
tephi:`, and a heading between two of them splits that list into six, orphaning bullets from
their lead-in.

The granularity stands and the constraint narrows: **no paragraph is rewritten, and each
interrupted subsection gains a lead line.** The five open with a one-line lead naming what
they cover, so a reader arriving at a heading is not dropped into an unintroduced list.
Nothing inside a bullet is edited.

*Corrected 2026-09-09, at implementation.* This paragraph first said that
`Differences from tephi:` is re-sited into the first subsection's prose. It needs no move:
the first cut falls above it, so it already sits inside `spec §3.2.1`, introducing the
bullets that stay with it. Verified after the fact by diffing §3.2 against `main` with the
anchors and the seven headings removed: **22 lines added, none removed** — the five leads
and their spacing, and no sentence deleted or duplicated.

The alternative was cutting only on clean boundaries — about three subsections, leaving
citations on a ~300-line list, which is barely better than today and would not have justified
the work.

*A second correction.* The cursor-readout cut was first sized at ~63 lines.
That figure came from a flat bullet scan that measured `format_coord`'s bullet to the next
`- ` line, which lies beyond the section boundary — the true extent is 22. The partition
above is measured from the boundaries themselves.

(anchor-spec-3-2)=
### 3.2 Headings, and the collection's first fourth level

`docs spec §3.6`'s contract is enforced by `check_anchors`, which reads each document twice:
down from every numbered heading, catching one with no anchor or the wrong one; and down from
every anchor, catching one whose heading has been deleted from under it. **An anchor without a
heading fails.** So the seven anchors arrive as seven `#### 3.2.N` headings.

Every one of the collection's 132 headings is `###` today, so these are its first fourth-level
headings. `HEADING` in `tephpy_citations.py` already matches `#{2,6}`, and the citation
grammar's `\d+(?:-\d+)*` already admits `(spec-3-2-1)=`, so no machinery changes. What is
untested is presentation — how a fourth level renders in the theme's secondary sidebar, and
whether the specification's own reading-time banner and page length change materially. §7
carries that.

**The container anchor stays.** `(spec-3-2)=` remains on the `### 3.2` heading, so
`spec §3.2` goes on resolving. A claim that genuinely spans the section keeps somewhere to
point, and nothing outside this work breaks on the day the headings land.

(anchor-spec-3-3)=
### 3.3 Re-pointing, in six batches

Five files carry 87% of the citations, so the work batches into reviewable units — one file,
one commit, one review:

| batch | file | citations | cumulative |
|---|---|---|---|
| 1 | `src/tephpy/plotting/axes.py` | 46 | 27% |
| 2 | `tests/plotting/test_axes.py` | 38 | 50% |
| 3 | `src/tephpy/plotting/isopleths.py` | 30 | 67% |
| 4 | `tests/plotting/test_isopleths.py` | 17 | 78% |
| 5 | `src/tephpy/_constants.py` | 17 | 87% |
| 6 | the remaining ten files | 22 | 100% |

**Six of the 170 are not re-pointed.** One is a *grammar fixture*:
`tests/test_citations.py` carries ``Spec §3.2`` inside an inline literal as test data
demonstrating a sentence that opens with a citation, not a reference to the design.
Re-pointing it would edit the input to a test about citation grammar. The other five make a
claim that genuinely spans the subsections — a module's scope line, a test file's section
heading, a `Raises` list, a note on the keyword-only signatures, and the teardown a figure
clear stands down from — and the container is what such a claim is for (§3.2). So 164 move
and six stay.

*Corrected 2026-09-09, at implementation.* This section first said 169 citations, of which
168 move and one stays. Both figures were wrong, for two independent reasons. The inventory
was one short because the scan that produced it required the word `spec` beside the section
number, so it missed `src/tephpy/_constants.py`'s `BARB_INCREMENTS`, which cites the section
second in a compound run. Counting is now done with the project's own citation grammar — the
resolver `check_citations.py` itself uses — which no compound run, capitalisation or prefix
fallback can hide from; the same flaw undercounted §1's denominator, 364 against a true 401,
and `spec §6`'s citations, 45 against 47. The second reason is not a measurement error at
all: **"one stays" assumed the fixture would be the only exception**, when §3.2 above had
already provided for claims that span the section. Five turned out to be of that kind, each
upheld under review.

Batch order is by size and not by dependency: the batches are independent, because a citation
is a comment and re-pointing one cannot affect another. Ordering by size front-loads the
attention while it is freshest, and gets the two hardest files reviewed first.

**A batch is not split across commits.** A file half re-pointed is a file where the reader
cannot tell which citations have been considered.

(anchor-spec-3-4)=
### 3.4 The worksheet

A throwaway script emits every citation with its file, line, enclosing symbol and surrounding
context, ordered by batch. It exists for **completeness** — 170 sites is more than anyone
holds in their head, and the failure to design against is a citation nobody looked at, not a
citation looked at and got wrong.

**It proposes nothing it cannot justify.** Where a keyword signal is unambiguous the row may
carry it as a clearly-labelled hint; where it is not, the row says so. Decision 4 records why:
the measurement says such a signal is right about half the time at best, and a column of
confident-looking guesses is worse than an empty one, because it converts review into
assent.

It is scaffolding and is not committed. What is committed is the re-pointed citations and
this specification.

(anchor-spec-3-5)=
### 3.5 What is checked, and what is not

**Checked.** `check_citations.py` resolves every citation against the anchor registry, so a
a citation naming a subsection that does not exist fails, as does an anchor whose heading has gone. The
existing gates need no change.

**Not checked, and this is the honest limit.** Nothing verifies that a citation names the
section it *means*. A citation of the accessors subsection resolves whether or not the claim beside it is about the
accessors. This project has met the distinction repeatedly: {pull}`290` shipped a citation
that resolved to a different document's section and passed every gate until review caught it.

Recording the limit rather than implying coverage follows `contributor spec §3.8`. It is also
why decision 3 batches by file: a wrong anchor is most visible in the diff beside the code it
describes, which is where a reviewer is already looking.

(anchor-spec-4)=
## 4. Companion changes

- `docs/src/developer/specs/index.rst` — the prefix table gains an `anchor spec §…` row **and
  its toctree the matching entry**. Two hand-written lists over one set.
- `docs/src/developer/specs/2026-07-22-tephpy-design.md` — §3.2 gains seven `#### 3.2.N`
  headings and their anchors. **No prose is rewritten**; the cuts fall on existing paragraph
  boundaries.

(anchor-spec-5)=
## 5. Testing

| what lands | what holds it |
|---|---|
| every citation resolving, including the new sub-anchors | `check_citations.py`, unchanged |
| every new anchor sitting above its heading, and every heading carrying one | `check_anchors`, unchanged |
| the specification rendering with a fourth heading level | `pixi run docs`, fail-on-warning |
| each citation naming the section it *means* | review, per batch (§3.5) |

No new gate. The existing ones already cover everything mechanically checkable here, and §3.5
says plainly what they do not.

(anchor-spec-6)=
## 6. Scope

**In scope.** The seven subsections of §3.1, their headings and anchors, the re-pointing of
all 170 citations, and the companion changes of §4.

**Out of scope.** {issue}`66`'s third part — the `plotting` tour in the developer guide — which
this unblocks rather than performs. Any rewrite of §3.2's paragraphs: this is re-anchoring, not
re-drafting. Each subsection gains a lead line and `Differences from tephi:` moves, as §3.1
records; nothing inside a bullet or a paragraph is edited, and a cut that needed more than a
lead line to work would be the wrong cut. Any
change to the other sixteen specifications, whose §3.2 citations are a different document's.

**Tranches.** The headings and anchors land first and alone, in one commit: until they exist
there is nothing to re-point at, and landing them separately means the six batches each have a
stable target. The batches then land in the order of §3.3.

(anchor-spec-7)=
## 7. Open items

Tagged per docs spec §3.5.

- **Resolved** (2026-09-09, at implementation) — how a fourth heading level renders. Both
  halves measured against the built HTML. The theme carries it: all seven subsections appear
  in the parent specification page's secondary sidebar, nested under `3.2 plotting`, at the
  existing depth — no theme option changes. The banner reads **107 minutes** and is computed
  rather than literal; the branch added 137 words to a 16,072-word document, which at the
  extension's 150 wpm is at most one minute. Not material.
- **Open** — `src/tephpy/plotting/axes.py:602` makes a claim no section states. Its
  docstring says the side panels are the diagram's to remove on a direct `ax.clear()` and
  the figure's on a figure clear, so the teardown stands down. No §3.2 subsection carries
  that rule, and the nearest statement is `spec §10` item 16, where it is an aside about why
  `root=` is load-bearing rather than a specification of the ownership. It stays on the
  container here, because re-pointing it at `spec §10` would trade one misdirection for
  another; the fix is to state the rule in `spec §3.2.7`, which is parent-specification
  authorship this work deliberately does not do (§6).
- **Open** — whether §3.2's *container* citations should eventually be discouraged. Once the
  subsections exist, a bare `spec §3.2` is sometimes right and sometimes laziness, and no gate
  can tell them apart. Left alone deliberately; revisit if the container starts accumulating
  citations again.
- **Deferred** — whether the other heavily-cited sections deserve the same treatment. `spec §6`
  takes 47 citations and `spec §3.4` takes 31; neither approaches §3.2's 170, and the same
  measurement should be made before assuming the same answer.

(anchor-spec-8)=
## 8. References

- {issue}`293` — this work, with the measurements that motivated it
- {issue}`66` — populate the Diátaxis quadrants and build out a developer guide; §3.2's split
  is its third part
- `docs spec §3.6` — the anchor and heading contract this works within
- `contributor spec §3.8` — recording what a gate cannot hold, the practice §3.5 follows
