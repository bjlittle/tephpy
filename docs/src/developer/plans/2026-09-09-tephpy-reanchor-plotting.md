# Re-anchoring the Plotting Section Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reader following a `spec §3.2` citation out of the code arrives at the subsection that answers it, rather than at 413 lines of undifferentiated prose.

**Architecture:** The parent specification's §3.2 gains seven `#### 3.2.N` headings with their anchors — the collection's first fourth level — and the 168 citations that are references move onto the subsection each means. No paragraph is rewritten; five subsections gain a one-line lead because their cuts land inside a bullet list. No new gate: the existing citation machinery already resolves sub-anchors, and nothing can check that a citation *means* what it names.

**Tech Stack:** MyST Markdown, Sphinx 9.1, pixi, pytest, pre-commit.

**Spec:** [`../specs/2026-09-09-reanchor-plotting-design.md`](../specs/2026-09-09-reanchor-plotting-design.md) — cited below as `anchor spec §N`. Read it alongside this plan; every task argues from a section of it.

## Global Constraints

- **A citation must name the document it means.** A bare `spec §N` is the *parent* specification; the other sixteen carry their own prefix. `check_citations.py` checks that a citation **resolves**, never that it names the section meant.
- **This plan's own text cannot cite the sections it creates.** They do not exist until Task 1 lands, and a bare `§3.2.N` in a specification or plan resolves against that document's own prefix. Where this plan names them it does so inside a fenced block or by title. Plans are dropped from the citation corpus, so only fenced examples matter here — but the same is not true of the specification, which is why `anchor spec §3.1` is a fenced listing.
- Every pull request adds `changelog/<PR>.<type>.rst` ending with ``(:user:`claude`)``.
- Headings follow CMOS headline style (`docs/src/developer/docs-style.rst`).
- `pixi run docs` must build clean; the build is fail-on-warning, and **the gates run after the HTML build** — `build succeeded` is not the check, the exit status is.
- Verify **after** committing, never before: the pre-commit hooks rewrite files.
- Do not touch the other sixteen specifications, whose own `§3.2` citations belong to a different document.

---

## What This Plan Measured Before It Was Written

Established 2026-09-09 on `reanchor-spec` at `57adef1`. One finding corrected the
specification, which is a living document; that correction is committed as `e2fef39` and is
not a task here.

**1. Five of the seven cuts land inside a bullet list.** §3.2's fifteen bullets are one list
introduced by `Differences from tephi:`. Only the first cut (before `` `TephigramAxes` draws
``) and the last (before `` `DEFAULT_EXTENT` is ``) fall on clean boundaries. The
specification claimed all seven did. It now says each interrupted subsection gains a one-line
lead and that the lead-in moves into the first subsection's prose.

**2. One of the 169 citations must not be re-pointed.** `tests/test_citations.py:101` carries
``Spec §3.2`` inside an inline literal as a *grammar fixture* — test data for a sentence that
opens with a citation. Re-pointing it edits the input to a test about citation grammar. It is
the only one: a scan for citations inside inline literals finds exactly this one, so **168 are
re-pointed and one stays**.

**3. Every insertion point is uniquely identifiable by text.** Each of the seven headings goes
immediately above a line that occurs exactly once in the file, so insertion never depends on a
line number that shifts as earlier headings land.

**4. No test asserts a global citation count**, and the citation-grammar tests use *other*
specifications' §3.2 (`docs spec §3.2`, `tooltip spec §3.2`) as examples. Re-pointing the
parent's citations cannot disturb them.

**5. The gates run after the HTML build and are what actually fail.** Writing the
specification, `pixi run docs` printed `build succeeded` and still exited 1, because
`check_rendered_citations.py` rejected a citation in the page title. Grep for `build
succeeded` and you will report a passing build that failed. **Check the exit status.**

---

## File Structure

| file | responsibility |
|---|---|
| `docs/src/developer/specs/2026-07-22-tephpy-design.md` | *modify* — §3.2 gains seven headings, their anchors, and five lead lines |
| `src/tephpy/plotting/axes.py` | *modify* — 46 citations re-pointed |
| `tests/plotting/test_axes.py` | *modify* — 38 |
| `src/tephpy/plotting/isopleths.py` | *modify* — 30 |
| `tests/plotting/test_isopleths.py` | *modify* — 17 |
| `src/tephpy/_constants.py` | *modify* — 16 |
| ten further files | *modify* — 21 re-pointed, one fixture left alone |
| `changelog/<PR>.documentation.rst` | *create* |

The worksheet of `anchor spec §3.4` is scaffolding written to the scratchpad. It is not
committed.

---

### Task 1: The seven headings, their anchors, and the worksheet

**Files:**
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md`

**Interfaces:**
- Consumes: nothing.
- Produces: anchors `(spec-3-2-1)=` through `(spec-3-2-7)=`, which every later task cites; and `<scratchpad>/worksheet.md`, which every later task reads.

This lands alone. Until the anchors exist there is nothing to re-point at, and landing them
separately gives the six batches a stable target.

- [ ] **Step 1: Confirm the section still begins where this plan expects**

Run:

```bash
sed -n '126,133p' docs/src/developer/specs/2026-07-22-tephpy-design.md
```

Expected: line 126 is ``### 3.2 `plotting` ``, lines 128–131 a `>` blockquote about branding
being specified in a child specification, and line 133 beginning `` `TephigramAxes` draws ``.
If the file has moved on, find the seven anchor lines by their text — each occurs exactly
once — rather than by number.

- [ ] **Step 2: Insert the seven headings**

Each heading goes **immediately above** the line quoted below, with the anchor immediately
above the heading and a blank line either side. The blockquote stays under `### 3.2`, before
the first subsection.

```
(spec-3-2-1)=
#### 3.2.1 The Diagram, and What Is Drawn by Default
    above:  `TephigramAxes` draws the exactly-orthogonal

(spec-3-2-2)=
#### 3.2.2 Isopleth Labels: Inline or on the Edges
    above:  - Isopleth labels place **inline or on

(spec-3-2-3)=
#### 3.2.3 Claimed Edges, Their Ticks and the Title
    above:  - **A claimed edge's ticks are stock

(spec-3-2-4)=
#### 3.2.4 Emphasis
    above:  - **Any member of any family can be emphasised.**

(spec-3-2-5)=
#### 3.2.5 The Plotting Accessors
    above:  - `ax.plot_profile(pressure, temperature,

(spec-3-2-6)=
#### 3.2.6 The Cursor Readout
    above:  - `ax.format_coord(x, y)`

(spec-3-2-7)=
#### 3.2.7 Extent, Edge Coverage and the Panel Layout
    above:  `DEFAULT_EXTENT` is `pressure=(900.0,
```

- [ ] **Step 3: Re-site the list's lead-in and add the five leads**

`Differences from tephi:` currently introduces all fifteen bullets and would be left
introducing only the first. Move it into §3.2.1's prose so it reads as introducing the bullet
that stays with it, and give each interrupted subsection a one-line lead so a reader arriving
at a heading is not dropped into an unintroduced list.

Use exactly these leads. **Do not edit any bullet, and do not edit any paragraph** — the
constraint `anchor spec §6` states is that nothing inside a bullet or paragraph changes.

```
3.2.2   Where a label goes, and what it does to the diagram it sits on:
3.2.3   What claiming an edge takes over, and what it hands back:
3.2.4   Singling a member out, on every accessor that draws one:
3.2.5   The methods that put a sounding on the diagram:
3.2.6   What the toolbar shows as the pointer moves:
```

- [ ] **Step 4: Commit, then verify**

```bash
git add docs/src/developer/specs/2026-07-22-tephpy-design.md
git commit -m "Give the plotting section the structure its citations need"
pixi run docs; echo "exit: $?"
```

Expected: **exit 0**. `build succeeded` alone is not the check — the five gates run after the
HTML build and are what fail. Report the `rendered citations ok:` and `citations ok:` lines.

- [ ] **Step 5: Prove the anchors resolve**

Run:

```bash
pixi run --environment devs python - <<'PY'
import subprocess, sys
sys.path.insert(0, "docs/src/_ext")
from pathlib import Path
import tephpy_citations as c
anchors, owners = c.collect_anchors(sorted(Path("docs/src/developer/specs").glob("*.md")))
missing = [f"spec-3-2-{n}" for n in range(1, 8) if f"spec-3-2-{n}" not in anchors]
print("missing:", missing or "none — all seven resolve")
PY
```

Expected: `missing: none — all seven resolve`. If any is absent, its anchor is not sitting
immediately above its heading.

- [ ] **Step 6: Generate the worksheet**

Write it to the scratchpad, **not** into the repository:

```bash
pixi run --environment test python - <<'PY'
import ast, re, pathlib, os
prefixes = set()
for p in pathlib.Path("docs/src/developer/specs").glob("*.md"):
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\((?P<slug>[a-z][a-z-]*?)-\d+(?:-\d+)*\)=\s*$", line)
        if m:
            prefixes.add(m["slug"].replace("-spec", "").replace("-", " "))
            break
prefixes.discard("spec")
CITE = re.compile(r"(?:(?P<prefix>[\w-]+) )?[Ss]pec §3\.2\b")
LITERAL = re.compile(r"``[^`]*``")
BATCH = {
    "src/tephpy/plotting/axes.py": 1, "tests/plotting/test_axes.py": 2,
    "src/tephpy/plotting/isopleths.py": 3, "tests/plotting/test_isopleths.py": 4,
    "src/tephpy/_constants.py": 5,
}
rows = []
for root in ("src", "tests"):
    for p in sorted(pathlib.Path(root).rglob("*.py")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "spec §3.2" not in text and "Spec §3.2" not in text:
            continue
        tree, spans = ast.parse(text), [m.span() for m in LITERAL.finditer(text)]
        for m in CITE.finditer(text):
            if (m["prefix"] or "").lower() in prefixes:
                continue
            line = text[:m.start()].count("\n") + 1
            sym = "<module>"
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.lineno <= line <= (node.end_lineno or node.lineno):
                        sym = node.name
            fixture = any(a <= m.start() < b for a, b in spans)
            ctx = text.splitlines()[line - 1].strip()[:90]
            rows.append((BATCH.get(p.as_posix(), 6), p.as_posix(), line, sym, fixture, ctx))
out = pathlib.Path(os.environ.get("SCRATCH", "/tmp")) / "worksheet.md"
with out.open("w", encoding="utf-8") as fh:
    fh.write(f"# {len(rows)} citations of spec §3.2\n\n")
    for batch in sorted({r[0] for r in rows}):
        fh.write(f"\n## Batch {batch}\n\n")
        for _, path, line, sym, fixture, ctx in sorted(r for r in rows if r[0] == batch):
            tag = "  **FIXTURE — do not re-point**" if fixture else ""
            fh.write(f"- [ ] `{path}:{line}` in `{sym}`{tag}\n      {ctx}\n      -> §3.2.__\n")
print(f"{len(rows)} rows -> {out}")
PY
```

Expected: `169 rows`, with exactly one marked **FIXTURE**. If the count differs from 169, the
tree has moved since this plan was measured — reconcile before continuing.

---

### Task 2: Batch 1 — `src/tephpy/plotting/axes.py` (46 citations)

**Files:**
- Modify: `src/tephpy/plotting/axes.py`

**Interfaces:**
- Consumes: the seven anchors from Task 1; the worksheet's Batch 1 section.
- Produces: nothing later tasks read.

- [ ] **Step 1: Decide each citation**

Work down the worksheet's Batch 1 rows. For each, read the claim the citation sits beside and
choose the subsection that answers it. The seven, by what they cover:

```
§3.2.1  the grid, the five families, what is drawn by default
§3.2.2  label placement, the declutter control, the inline box
§3.2.3  claiming and releasing an edge, its ticks, the split axis title, edge_axis
§3.2.4  emphasis, and emphasis forcing its member to be drawn
§3.2.5  plot_profile, plot_sounding, plot_barbs, shade_cape/shade_cin,
        annotate_indices, set_extent
§3.2.6  format_coord, the field registry, NaN rendering
§3.2.7  DEFAULT_EXTENT, the dead corner, per-family edge coverage, the panel layout
```

**A citation that genuinely spans the section stays as `spec §3.2`.** The container anchor
remains, and forcing a subsection on a claim that does not have one is worse than leaving it.
Record which you left and why in your report.

- [ ] **Step 2: Apply the decisions**

Edit each cited line, changing `spec §3.2` to `spec §3.2.N`. Change nothing else — not the
wording around it, not the code.

- [ ] **Step 3: Commit, then verify**

```bash
git add src/tephpy/plotting/axes.py
git commit -m "Point axes.py's citations at the subsection each means"
pixi run --environment devs python .github/scripts/check_citations.py
pixi run --environment test pytest tests/plotting/test_axes.py -q
```

Expected: `citations ok:` and the tests passing. A citation naming a subsection that does not
exist fails the first; nothing checks that it names the one you meant, which is why the diff
is reviewed beside the code.

---

### Task 3: Batch 2 — `tests/plotting/test_axes.py` (38 citations)

**Files:**
- Modify: `tests/plotting/test_axes.py`

**Interfaces:**
- Consumes: the seven anchors from Task 1; the worksheet's Batch 2 section.
- Produces: nothing later tasks read.

- [ ] **Step 1: Decide each citation**

As Task 2's Step 1, over the worksheet's Batch 2 rows. The seven subsections, by what they
cover:

```
§3.2.1  the grid, the five families, what is drawn by default
§3.2.2  label placement, the declutter control, the inline box
§3.2.3  claiming and releasing an edge, its ticks, the split axis title, edge_axis
§3.2.4  emphasis, and emphasis forcing its member to be drawn
§3.2.5  plot_profile, plot_sounding, plot_barbs, shade_cape/shade_cin,
        annotate_indices, set_extent
§3.2.6  format_coord, the field registry, NaN rendering
§3.2.7  DEFAULT_EXTENT, the dead corner, per-family edge coverage, the panel layout
```

A test's citation usually names what the test asserts, which is a stronger signal than the
prose around it. A citation that genuinely spans the section stays as `spec §3.2`.

- [ ] **Step 2: Apply the decisions**

Edit each cited line, changing `spec §3.2` to `spec §3.2.N`. Change no assertion and no test.

- [ ] **Step 3: Commit, then verify**

```bash
git add tests/plotting/test_axes.py
git commit -m "Point test_axes.py's citations at the subsection each means"
pixi run --environment devs python .github/scripts/check_citations.py
pixi run --environment test pytest tests/plotting/test_axes.py -q
```

Expected: `citations ok:` and the tests passing, with the same count as before your change —
a citation is a comment, so the suite's behaviour must not move.

---

### Task 4: Batch 3 — `src/tephpy/plotting/isopleths.py` (30 citations)

**Files:**
- Modify: `src/tephpy/plotting/isopleths.py`

**Interfaces:**
- Consumes: the seven anchors from Task 1; the worksheet's Batch 3 section.
- Produces: nothing later tasks read.

- [ ] **Step 1: Decide each citation**

As Task 2's Step 1, over the worksheet's Batch 3 rows. The seven subsections, by what they
cover:

```
§3.2.1  the grid, the five families, what is drawn by default
§3.2.2  label placement, the declutter control, the inline box
§3.2.3  claiming and releasing an edge, its ticks, the split axis title, edge_axis
§3.2.4  emphasis, and emphasis forcing its member to be drawn
§3.2.5  plot_profile, plot_sounding, plot_barbs, shade_cape/shade_cin,
        annotate_indices, set_extent
§3.2.6  format_coord, the field registry, NaN rendering
§3.2.7  DEFAULT_EXTENT, the dead corner, per-family edge coverage, the panel layout
```

This file is where the families live, so expect §3.2.1 through §3.2.4 to carry most of it —
but decide each on its own claim rather than on that expectation.

- [ ] **Step 2: Apply the decisions**

Edit each cited line, changing `spec §3.2` to `spec §3.2.N`. Change nothing else.

- [ ] **Step 3: Commit, then verify**

```bash
git add src/tephpy/plotting/isopleths.py
git commit -m "Point isopleths.py's citations at the subsection each means"
pixi run --environment devs python .github/scripts/check_citations.py
pixi run --environment test pytest tests/plotting/test_isopleths.py -q
```

Expected: `citations ok:` and the tests passing.

---

### Task 5: Batch 4 — `tests/plotting/test_isopleths.py` (17 citations)

**Files:**
- Modify: `tests/plotting/test_isopleths.py`

**Interfaces:**
- Consumes: the seven anchors from Task 1; the worksheet's Batch 4 section.
- Produces: nothing later tasks read.

- [ ] **Step 1: Decide each citation**

As Task 2's Step 1, over the worksheet's Batch 4 rows. The seven subsections, by what they
cover:

```
§3.2.1  the grid, the five families, what is drawn by default
§3.2.2  label placement, the declutter control, the inline box
§3.2.3  claiming and releasing an edge, its ticks, the split axis title, edge_axis
§3.2.4  emphasis, and emphasis forcing its member to be drawn
§3.2.5  plot_profile, plot_sounding, plot_barbs, shade_cape/shade_cin,
        annotate_indices, set_extent
§3.2.6  format_coord, the field registry, NaN rendering
§3.2.7  DEFAULT_EXTENT, the dead corner, per-family edge coverage, the panel layout
```

- [ ] **Step 2: Apply the decisions**

Edit each cited line, changing `spec §3.2` to `spec §3.2.N`. Change no assertion and no test.

- [ ] **Step 3: Commit, then verify**

```bash
git add tests/plotting/test_isopleths.py
git commit -m "Point test_isopleths.py's citations at the subsection each means"
pixi run --environment devs python .github/scripts/check_citations.py
pixi run --environment test pytest tests/plotting/test_isopleths.py -q
```

Expected: `citations ok:` and the tests passing, with the same count as before.

---

### Task 6: Batch 5 — `src/tephpy/_constants.py` (16 citations)

**Files:**
- Modify: `src/tephpy/_constants.py`

**Interfaces:**
- Consumes: the seven anchors from Task 1; the worksheet's Batch 5 section.
- Produces: nothing later tasks read.

- [ ] **Step 1: Decide each citation**

As Task 2's Step 1, over the worksheet's Batch 5 rows. The seven subsections, by what they
cover:

```
§3.2.1  the grid, the five families, what is drawn by default
§3.2.2  label placement, the declutter control, the inline box
§3.2.3  claiming and releasing an edge, its ticks, the split axis title, edge_axis
§3.2.4  emphasis, and emphasis forcing its member to be drawn
§3.2.5  plot_profile, plot_sounding, plot_barbs, shade_cape/shade_cin,
        annotate_indices, set_extent
§3.2.6  format_coord, the field registry, NaN rendering
§3.2.7  DEFAULT_EXTENT, the dead corner, per-family edge coverage, the panel layout
```

Every citation here sits on a constant's `#:` comment, so the constant's own name and value
are the signal — `EMPHASIS_LINEWIDTH` is §3.2.4, the cursor field registry is §3.2.6.

- [ ] **Step 2: Apply the decisions**

Edit each cited line, changing `spec §3.2` to `spec §3.2.N`. Change no constant and no value.

- [ ] **Step 3: Commit, then verify**

```bash
git add src/tephpy/_constants.py
git commit -m "Point _constants.py's citations at the subsection each means"
pixi run --environment devs python .github/scripts/check_citations.py
pixi run --environment test pytest tests/test_constants.py -q
```

Expected: `citations ok:` and the tests passing.

---

### Task 7: Batch 6 — the remaining ten files (21 re-pointed, one fixture left)

**Files:**
- Modify: `src/tephpy/plotting/shading.py`, `tests/plotting/test_shading.py`,
  `src/tephpy/_config.py`, `src/tephpy/plotting/barbs.py`, `tests/plotting/test_barbs.py`,
  `tests/plotting/test_images.py`, `src/tephpy/plotting/_theme.py`, `tests/test_constants.py`,
  `tests/test_config.py`
- Leave alone: `tests/test_citations.py`

**Interfaces:**
- Consumes: the seven anchors from Task 1; the worksheet's Batch 6 section.
- Produces: nothing later tasks read.

- [ ] **Step 1: Decide each citation, and leave the fixture alone**

As Task 2's Step 1, over the worksheet's Batch 6 rows. The seven subsections, by what they
cover:

```
§3.2.1  the grid, the five families, what is drawn by default
§3.2.2  label placement, the declutter control, the inline box
§3.2.3  claiming and releasing an edge, its ticks, the split axis title, edge_axis
§3.2.4  emphasis, and emphasis forcing its member to be drawn
§3.2.5  plot_profile, plot_sounding, plot_barbs, shade_cape/shade_cin,
        annotate_indices, set_extent
§3.2.6  format_coord, the field registry, NaN rendering
§3.2.7  DEFAULT_EXTENT, the dead corner, per-family edge coverage, the panel layout
```

**`tests/test_citations.py:101` is not re-pointed.** Its ``Spec §3.2`` sits inside an inline
literal and is a grammar fixture — test data for a sentence that opens with a citation. The
worksheet marks it. Re-pointing it edits the input to a test about citation grammar.

- [ ] **Step 2: Apply the decisions**

Edit each cited line, changing `spec §3.2` to `spec §3.2.N`. Leave the fixture untouched.

- [ ] **Step 3: Add the changelog fragment**

Create `changelog/<PR>.documentation.rst`, substituting the real pull-request number:

```rst
The parent design specification's ``plotting`` section now has an internal
structure, and the citations that land on it name the part they mean. It was 413
lines under no subheadings, absorbing **169 of the 364** citations of that
specification in ``src`` and ``tests`` — 46% of them, every one resolving to the
same target. It gains seven subsections and 168 citations move onto the one each
means; the one that stays is a grammar fixture rather than a reference
(``anchor spec §…``). (:user:`claude`)
```

- [ ] **Step 4: Commit, then verify everything**

```bash
git add -A
git commit -m "Point the remaining citations at the subsection each means"
pixi run --environment devs python .github/scripts/check_citations.py
pixi run tests
pixi run docs; echo "exit: $?"
pixi run lint
```

Expected: `citations ok:`; the suite passing with the same count as before this branch; `docs`
**exit 0**, not merely `build succeeded`; lint clean.

- [ ] **Step 5: Confirm nothing was missed**

Run:

```bash
pixi run --environment test python - <<'PY'
import re, pathlib
prefixes = set()
for p in pathlib.Path("docs/src/developer/specs").glob("*.md"):
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\((?P<slug>[a-z][a-z-]*?)-\d+(?:-\d+)*\)=\s*$", line)
        if m:
            prefixes.add(m["slug"].replace("-spec", "").replace("-", " "))
            break
prefixes.discard("spec")
BARE = re.compile(r"(?:(?P<prefix>[\w-]+) )?[Ss]pec §3\.2(?!\.)")
left = []
for root in ("src", "tests"):
    for p in sorted(pathlib.Path(root).rglob("*.py")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        for m in BARE.finditer(text):
            if (m["prefix"] or "").lower() in prefixes:
                continue
            left.append(f"{p.as_posix()}:{text[:m.start()].count(chr(10)) + 1}")
print(f"still on the container: {len(left)}")
for entry in left:
    print(f"  {entry}")
PY
```

Expected: the fixture at `tests/test_citations.py:101`, plus any citation you deliberately
left on the container. **Every entry must be one you decided to leave** — an entry you do not
recognise is one the batches missed. Name them all in your report.

---

## Self-Review

**Spec coverage.** `anchor spec §3.1`'s seven cuts and five leads → Task 1 Steps 2 and 3.
§3.2's headings-carry-anchors requirement → Task 1 Steps 2 and 5. §3.3's six batches → Tasks
2–7, in its order, with the fixture exclusion in Task 7. §3.4's worksheet → Task 1 Step 6,
written to the scratchpad and uncommitted as the section requires. §3.5's "reviewed, not
gated" → every batch's Step 3 runs the resolution gate and leaves meaning to review. §4's
companion changes: the specification index was updated when the specification landed; the
parent specification is Task 1.

**Placeholders.** None. The one substitution is Task 7's pull-request number, unknowable
before the branch is pushed. The seven-subsection legend is repeated in full in every batch
task rather than cross-referenced, because an implementer may read tasks out of order.

**Type consistency.** Anchor names are `spec-3-2-1` through `spec-3-2-7` throughout, and the
citations they back are written `spec §3.2.1` through `spec §3.2.7`. Task 1 Step 5 asserts
exactly those seven slugs.

**One risk carried deliberately.** The counts in this plan — 46, 38, 30, 17, 16, 22 — were
measured on `57adef1`. If a batch's worksheet section holds a different number, the tree has
moved and the discrepancy is worth understanding before continuing rather than reconciling
silently.
