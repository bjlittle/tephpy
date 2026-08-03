# Published Design Specifications Implementation Plan

> **Point-in-time record.** This plan captures what was intended before implementation. It
> is not updated afterwards — where the implementation departed from it, the departure is
> recorded in the pull request, and the living design specification in
> [`../specs/`](../specs/) is what describes tephpy as it stands.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish tephpy's design specifications in the developer guide with stable section
anchors, so the 333 `spec §…` citations in `src/` and `tests/` resolve to something a
reader can reach, and give every unresolved roadmap item a status tag and a tracked issue.

**Architecture:** `docs/superpowers/{specs,plans}` moves under `docs/src/developer/`, inside
the Sphinx `SOURCEDIR`. The specifications join the build; the plans stay tracked but are
withheld by one `exclude_patterns` entry. Both stay siblings so the relative links between
them keep resolving in a checkout and on GitHub. Every numbered heading gains an explicit
MyST target keyed to its section number, because docutils derives its slugs from heading
*text* and silently collides. Finally the roadmap's open items get a status vocabulary and
`design: open` issues, so a published specification cannot become a place where live work
sits unseen.

**Tech Stack:** Sphinx 8 + myst-nb/myst-parser (Markdown under `SOURCEDIR`),
pydata-sphinx-theme, pixi, setuptools + setuptools_scm (sdist file selection), towncrier,
pre-commit, `gh` CLI.

**Spec:** `docs/src/developer/specs/2026-08-03-published-specs-design.md` — cite it as
`docs spec §N`. It is the authority for every decision here. §5 enumerates the migration
this plan performs; §3.4 governs what may and may not be edited in a plan; §3.5 defines
the status vocabulary. (Named at its post-migration path, which Task 1 creates. Until then
it is at `docs/superpowers/specs/2026-08-03-published-specs-design.md`.)

**Issue:** [#65](https://github.com/bjlittle/tephpy/issues/65)

## Global Constraints

- **Every pixi invocation carries `--frozen`.** `pixi run --frozen tests`,
  `pixi run --frozen lint`, `pixi run --frozen docs`. Never let pixi re-solve the
  environment.
- **There is no bare `python` on PATH.** Use `pixi run --frozen python`.
- **Never commit to `main`.** The `no-commit-to-branch` pre-commit hook enforces this.
  Work happens on the branch this plan is executed from.
- **Never pass `--no-verify` to `git commit`.** If a hook fails, fix the cause.
- **Run `pixi run --frozen pre-commit install` once** before the first commit — hooks are
  not installed in a fresh clone or worktree, and `pre-commit` is not on `PATH` outside the
  pixi environment — then `pixi run --frozen lint` before pushing. Note that the
  trailing-whitespace hook rewrites files and aborts the commit; re-`git add` and commit
  again when it does.
- **A bare `pixi run --frozen mypy` is wrong** — it reports ~57 pre-existing errors.
  `pixi run --frozen lint` is the only correct type check.
- **`pixi run --frozen docs`** is `docs-clean` + `make html`, with
  `SPHINXOPTS = --fail-on-warning --keep-going` and `nitpicky = True`. A clean exit 0 is
  the gate for every task that touches the docs tree. It takes roughly three minutes.
- **New reStructuredText titles use CMOS headline style** (`docs/src/developer/docs-style.rst`).
- **A plan's content is never edited; only its pointers are** (docs spec §3.4). A repository
  path in a plan may be corrected when the thing it names moves. A path inside a fenced code
  block that reproduces a file's contents, a PR body, or an issue body is a record of what
  was written, not a pointer — leave it exactly as it is.
- **The specifications' technical content is not edited** (docs spec §7). Tasks 5 and 6 add
  status tags and issue pointers; they do not rewrite the reasoning. Every edit to §10 and
  §11 is purely additive — existing prose is preserved verbatim.
- **Two pull requests, following the repository's convention** (#58 → #59, #61 → #62): the
  specification and this plan land first in a planning PR labelled `skip-changelog`, and
  Tasks 1-6 then execute on a separate implementation branch. Task 6 is that second PR, and
  it carries the changelog fragment.
- **This plan file moves in Task 1.** It starts at
  `docs/superpowers/plans/2026-08-03-tephpy-published-specs.md` and ends at
  `docs/src/developer/plans/2026-08-03-tephpy-published-specs.md`. Re-open it at the new
  path from Task 2 onwards.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `docs/src/developer/specs/` (moved) | The three published specifications | 1 |
| `docs/src/developer/plans/` (moved) | The thirteen plans — tracked, unpublished | 1 |
| `docs/src/conf.py` | `exclude_patterns` withholds the plans from the build | 1 |
| `MANIFEST.in` | `prune` withholds the plans from the sdist | 1 |
| `docs/src/developer/specs/index.rst` (new) | Toctree + the living-document and citation-namespace statement | 1 |
| `docs/src/developer/index.rst` | Adds `specs/index` to the developer toctree | 1 |
| `AGENTS.md` | Records the superpowers spec/plan path preference | 1 |
| `docs/src/developer/specs/2026-07-22-tephpy-design.md` | 25 anchors; header link; §10 path; §10/§11 status tags | 1, 2, 3, 5 |
| `docs/src/developer/specs/2026-08-01-add-logo-design.md` | 15 anchors | 2 |
| `docs/src/developer/plans/*.md` | 13 spec pointers repointed | 3 |
| `README.md` | The design link becomes the published page | 3 |
| `changelog/<PR>.documentation.rst` (new) | Towncrier fragment | 6 |

---

### Task 1: Move the documents into the docs source tree

Moves both directories inside `SOURCEDIR`, joins the specifications to the build, and
withholds the plans from both the build and the sdist. Ends with a clean docs build in
which all three specification pages render and no plan page exists.

**Files:**
- Move: `docs/superpowers/specs/` → `docs/src/developer/specs/`
- Move: `docs/superpowers/plans/` → `docs/src/developer/plans/`
- Modify: `docs/src/conf.py:118`
- Modify: `MANIFEST.in:7`
- Create: `docs/src/developer/specs/index.rst`
- Modify: `docs/src/developer/index.rst`
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md:9-10`
- Modify: `AGENTS.md`

**Interfaces:**
- Produces: the built page paths later tasks verify against —
  `docs/_build/html/developer/specs/2026-07-22-tephpy-design.html`,
  `docs/_build/html/developer/specs/2026-08-01-add-logo-design.html`,
  `docs/_build/html/developer/specs/2026-08-03-published-specs-design.html`.
- Produces: the new document root `docs/src/developer/specs/` and
  `docs/src/developer/plans/`, which Tasks 2, 3 and 5 operate on.

- [ ] **Step 1: Confirm the specification pages are absent from the build today**

This is the check Task 1 has to flip. Run it before changing anything so you have watched
it report absence:

```bash
ls docs/_build/html/developer/specs/ 2>&1
find docs/src -name '2026-07-22-tephpy-design.md' 2>&1
```

Expected: `No such file or directory` from the first (whether or not `_build` exists), and
no output from the second — the specification is not under `docs/src`, so Sphinx never sees
it.

- [ ] **Step 2: Confirm `docs/superpowers` holds nothing but the two directories**

```bash
find docs/superpowers -maxdepth 1 | sort
```

Expected exactly:

```
docs/superpowers
docs/superpowers/plans
docs/superpowers/specs
```

If anything else appears, stop and report it — the move below would strand it.

- [ ] **Step 3: Move both directories**

`docs/src/developer` already exists (it holds `docs-style.rst` and `index.rst`), so this is
two moves and a rmdir. Use `git mv` so git records renames rather than a delete plus an add.

```bash
git mv docs/superpowers/specs docs/src/developer/specs
git mv docs/superpowers/plans docs/src/developer/plans
rmdir docs/superpowers
git status --short | head -40
```

Expected: a list of `R  docs/superpowers/... -> docs/src/developer/...` rename entries and
nothing else. **This plan file moved too** — it is now
`docs/src/developer/plans/2026-08-03-tephpy-published-specs.md`.

- [ ] **Step 4: Withhold the plans from the docs build**

In `docs/src/conf.py`, extend `exclude_patterns`. The existing entry and its long comment
above it stay exactly as they are; only the list changes.

Replace:

```python
exclude_patterns = ["brand/assets/*"]
```

with:

```python
# ``developer/plans/*`` is the second entry for a different reason: the plans are
# tracked in the repository but deliberately unpublished (docs spec §3.1) — a plan
# is a point-in-time record, not a living document.
exclude_patterns = ["brand/assets/*", "developer/plans/*"]
```

- [ ] **Step 5: Withhold the plans from the sdist**

`MANIFEST.in:7` currently reads `prune docs/superpowers`. That line is load-bearing:
setuptools_scm puts every git-tracked file into the sdist, and the rest of `docs/` ships, so
without it the plans would be published to PyPI. After the move it silently stops matching.

Replace:

```
prune docs/superpowers
```

with:

```
prune docs/src/developer/plans
```

The specifications ship from here on, which is correct — they are published documentation
like every other page under `docs/src/`.

- [ ] **Step 6: Create the specifications index**

Create `docs/src/developer/specs/index.rst`. This page carries the two things docs spec
§3.2 requires a reader to be told and cannot infer from any single document: that these are
living documents, and that the citation prefix identifies which one.

```rst
Design Specifications
=====================

These are tephpy's design specifications. Each is a **living document**: maintained
alongside the code it describes, not archived behind it. Where the code and a
specification diverge, it is the specification that gets corrected — so read these as
current, and report a divergence as a specification defect.

tephpy's source cites them by section. You will meet ``spec §3.2`` and ``logo spec §3.5``
in comments and docstrings throughout ``src/`` and ``tests/``, and each resolves to a
section on one of the pages below. The prefix identifies the document, and it is
load-bearing rather than decorative: ``logo spec §3.6`` names a section that has no
counterpart in the parent specification.

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Citation
      - Document
    * - ``spec §…``
      - :doc:`2026-07-22-tephpy-design`
    * - ``logo spec §…``
      - :doc:`2026-08-01-add-logo-design`
    * - ``docs spec §…``
      - :doc:`2026-08-03-published-specs-design`

A new specification chooses a prefix unique across this collection and declares it in its
own header banner.

The implementation plans derived from these specifications are tracked in the repository
under `docs/src/developer/plans/
<https://github.com/bjlittle/tephpy/tree/main/docs/src/developer/plans>`__, but are
deliberately not published here. Unlike a specification, a plan records what was intended
before implementation and is not updated afterwards.

.. toctree::
    :maxdepth: 1

    2026-07-22-tephpy-design
    2026-08-01-add-logo-design
    2026-08-03-published-specs-design
```

Docs spec §3.2 also requires each specification to declare its own prefix in its header
banner. All three already do — the parent names `spec §6`, the `add_logo` specification
names `logo spec §3.5`, and the new one names `docs spec §…`. No edit is needed; verify
rather than add.

- [ ] **Step 7: Add the index to the developer toctree**

In `docs/src/developer/index.rst`, replace:

```rst
.. toctree::
    :maxdepth: 1

    docs-style
```

with:

```rst
.. toctree::
    :maxdepth: 1

    docs-style
    specs/index
```

- [ ] **Step 8: Repoint the parent specification's header link to the plans**

`docs/src/developer/specs/2026-07-22-tephpy-design.md` lines 9-10 link to `../plans/`. That
link is the docs build's only warning, and it fails precisely *because* the plans are
deliberately unpublished — Sphinx will not link to a page it was told not to build. An
absolute GitHub URL keeps the affordance for a reader of the published page, who has no
checkout to fall back on.

Replace:

```markdown
- **Status:** living design specification, implemented incrementally by the plans in
  [`../plans/`](../plans/)
```

with:

```markdown
- **Status:** living design specification, implemented incrementally by the plans in
  [`docs/src/developer/plans/`](https://github.com/bjlittle/tephpy/tree/main/docs/src/developer/plans)
```

- [ ] **Step 9: Record the path preference in `AGENTS.md`**

The superpowers skills default to writing specifications and plans under
`docs/superpowers/`, and their own instructions state that a user preference overrides the
default. Record the preference once, at the repository root. Append to the bullet list in
`AGENTS.md` (after the Diátaxis line):

```markdown
- Design specs and implementation plans live under `docs/src/developer/{specs,plans}` — specs are published in the docs build, plans are excluded by `exclude_patterns` and `MANIFEST.in`.
```

- [ ] **Step 10: Build the docs and verify they are clean**

```bash
pixi run --frozen docs 2>&1 | tail -25
```

Expected: `build succeeded.` with no warnings, exit 0. Roughly three minutes.

If the build reports a warning about `../plans/`, Step 8 was missed. If it reports an
unknown document under `developer/plans`, something outside the specifications links into
the plans — report it rather than working around it.

- [ ] **Step 11: Verify the three specifications published and no plan did**

```bash
ls docs/_build/html/developer/specs/
test ! -e docs/_build/html/developer/plans && echo "OK: no plan pages built"
```

Expected: the listing contains `index.html`, `2026-07-22-tephpy-design.html`,
`2026-08-01-add-logo-design.html` and `2026-08-03-published-specs-design.html`; and
`OK: no plan pages built`.

- [ ] **Step 12: Verify the sdist carries the specifications and not the plans**

```bash
rm -rf /tmp/sdist-check
pixi run --frozen python -m build --sdist --no-isolation --outdir /tmp/sdist-check 2>&1 | tail -3
tar tzf /tmp/sdist-check/*.tar.gz | grep 'docs/src/developer/specs/'
tar tzf /tmp/sdist-check/*.tar.gz | grep 'docs/src/developer/plans/' || echo "no plans in the sdist"
```

Expected: `Successfully built …`; then five lines for the specifications — the directory
entry itself plus `index.rst` and the three `.md` documents (the tarball carries directory
entries as well as files) — and then `no plans in the sdist`.

- [ ] **Step 13: Commit**

```bash
pixi run --frozen pre-commit install
git add -A
git commit -m "Publish the design specifications in the developer guide

Moves docs/superpowers/{specs,plans} under docs/src/developer so Sphinx
reads the specifications natively, and withholds the plans from both the
docs build (exclude_patterns) and the sdist (MANIFEST.in prune, which
stopped matching when the directory moved).

Refs #65."
```

---

### Task 2: Add explicit section anchors to both specifications

Gives every numbered heading a stable HTML `id` keyed to its section number. Without this,
publication alone lands all 149 `spec §3.2` citations at the top of a 180 KB page, and the
prose-derived slugs collide silently — §7 *Testing* and §8.5 *Testing* both slugify to
`testing`, and docutils disambiguates the second to `id1`, which becomes `id2` the moment a
heading is inserted above it.

**Files:**
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md` (25 headings)
- Modify: `docs/src/developer/specs/2026-08-01-add-logo-design.md` (15 headings)

**Interfaces:**
- Consumes: the moved paths and built-page paths Task 1 produced.
- Produces: the anchors `spec-1` … `spec-12` (including `spec-3-1` … `spec-3-5` and
  `spec-8-1` … `spec-8-8`) and `logo-spec-1` … `logo-spec-9` (including `logo-spec-3-1` …
  `logo-spec-3-6`). No later task consumes them; they are the deliverable.

- [ ] **Step 1: Write the anchor verification check and watch it fail**

Create the check first, so you have seen it fail for the right reason. Run it against the
build Task 1 produced:

```bash
pixi run --frozen python - <<'PY'
import sys
from pathlib import Path

CHECKS = {
    "docs/_build/html/developer/specs/2026-07-22-tephpy-design.html": [
        "spec-1", "spec-2", "spec-3", "spec-3-1", "spec-3-2", "spec-3-3", "spec-3-4",
        "spec-3-5", "spec-4", "spec-5", "spec-6", "spec-7", "spec-8", "spec-8-1",
        "spec-8-2", "spec-8-3", "spec-8-4", "spec-8-5", "spec-8-6", "spec-8-7",
        "spec-8-8", "spec-9", "spec-10", "spec-11", "spec-12",
    ],
    "docs/_build/html/developer/specs/2026-08-01-add-logo-design.html": [
        "logo-spec-1", "logo-spec-2", "logo-spec-3", "logo-spec-3-1", "logo-spec-3-2",
        "logo-spec-3-3", "logo-spec-3-4", "logo-spec-3-5", "logo-spec-3-6",
        "logo-spec-4", "logo-spec-5", "logo-spec-6", "logo-spec-7", "logo-spec-8",
        "logo-spec-9",
    ],
}

missing = [
    f"{path} #{anchor}"
    for path, anchors in CHECKS.items()
    for anchor in anchors
    if f'id="{anchor}"' not in Path(path).read_text()
]
for entry in missing:
    print("MISSING", entry)
print("OK — all 40 anchors present" if not missing else f"{len(missing)} missing")
sys.exit(1 if missing else 0)
PY
```

Expected: 40 `MISSING` lines and `40 missing`, exit 1. That is the failing state this task
fixes. Save the script — Step 4 re-runs it verbatim.

- [ ] **Step 2: Insert the anchors**

Each numbered heading gets an explicit MyST target on the line immediately above it, keyed
to the section number with dots replaced by hyphens and prefixed by the document's slug:

```markdown
(spec-3-2)=
### 3.2 `plotting`
```

The heading regex matters. `^(#{2,3}) (\d+(?:\.\d+)?)\. ?(.*)` looks right and is wrong:
against `### 3.2 \`plotting\`` the trailing `\.` consumes the dot, leaving group 2 as `3`,
so every `X.Y` heading is silently mis-keyed. The form below requires whitespace after the
optional trailing dot, which forces the number to be captured whole.

```bash
pixi run --frozen python - <<'PY'
import re
from pathlib import Path

TARGETS = {
    "docs/src/developer/specs/2026-07-22-tephpy-design.md": "spec",
    "docs/src/developer/specs/2026-08-01-add-logo-design.md": "logo-spec",
}
HEADING = re.compile(r"^(#{2,3}) (\d+(?:\.\d+)*)\.? +\S")

for path, prefix in TARGETS.items():
    p = Path(path)
    out, added = [], 0
    for line in p.read_text().splitlines(keepends=True):
        match = HEADING.match(line)
        if match:
            out.append(f"({prefix}-{match.group(2).replace('.', '-')})=\n")
            added += 1
        out.append(line)
    p.write_text("".join(out))
    print(f"{path}: {added} anchors")
PY
```

Expected exactly:

```
docs/src/developer/specs/2026-07-22-tephpy-design.md: 25 anchors
docs/src/developer/specs/2026-08-01-add-logo-design.md: 15 anchors
```

Any other counts mean the regex matched the wrong set — stop and diff before continuing.

- [ ] **Step 3: Rebuild the docs**

```bash
pixi run --frozen docs 2>&1 | tail -25
```

Expected: `build succeeded.`, exit 0, no warnings. In particular **no duplicate label
warnings** — Sphinx `std` domain labels are global, which is why the `spec-` and
`logo-spec-` prefixes exist.

- [ ] **Step 4: Re-run the anchor check and watch it pass**

Run the Step 1 script again, unchanged.

Expected: `OK — all 40 anchors present`, exit 0.

- [ ] **Step 5: Verify every citation in the codebase resolves**

Docs spec §6 asks for a one-off check that every distinct citation written in `src/` and
`tests/` names a section that exists.

```bash
pixi run --frozen python - <<'PY'
import subprocess
import sys
from pathlib import Path

found = subprocess.run(
    ["grep", "-rhoE", r"(logo )?spec §[0-9]+(\.[0-9]+)?", "src", "tests"],
    capture_output=True, text=True, check=True,
).stdout

html = {
    "spec": Path(
        "docs/_build/html/developer/specs/2026-07-22-tephpy-design.html"
    ).read_text(),
    "logo spec": Path(
        "docs/_build/html/developer/specs/2026-08-01-add-logo-design.html"
    ).read_text(),
}
slug = {"spec": "spec-", "logo spec": "logo-spec-"}

citations = sorted({line for line in found.splitlines() if line})
unresolved = []
for citation in citations:
    document, _, section = citation.partition(" §")
    anchor = slug[document] + section.replace(".", "-")
    if f'id="{anchor}"' not in html[document]:
        unresolved.append(f"{citation!r} -> #{anchor}")

for entry in unresolved:
    print("UNRESOLVED", entry)
print(f"{len(citations)} distinct citations checked, {len(unresolved)} unresolved")
sys.exit(1 if unresolved else 0)
PY
```

Expected: `21 distinct citations checked, 0 unresolved`, exit 0. The 21 are 12 parent-spec
sections (§1, §3.1–§3.5, §4, §5, §6, §7, §9, §10) and 9 `add_logo` sections (§2, §3.2–§3.6,
§5, §6, §8).

- [ ] **Step 6: Spot-check one anchor by hand**

```bash
grep -o 'id="spec-3-2"[^>]*' docs/_build/html/developer/specs/2026-07-22-tephpy-design.html
grep -o 'id="spec-8-5"[^>]*' docs/_build/html/developer/specs/2026-07-22-tephpy-design.html
```

Expected: one match each. `spec-8-5` is the one that previously collided with §7 and became
`id1`; seeing it named proves the collision is gone.

- [ ] **Step 7: Commit**

```bash
git add docs/src/developer/specs/
git commit -m "Anchor every numbered specification section

docutils slugifies a heading from its text and discards the number, so
'### 3.2 plotting' was addressable only as #plotting — and 149 citations
point at that one section of a 180 KB page. Worse, §7 Testing and §8.5
Testing collided into #id1, an anchor that shifts on any insertion above
it. Explicit MyST targets keyed to the section number fix both.

Refs #65."
```

---

### Task 3: Correct the pointers the move invalidated

Three classes of reference name the old path. Docs spec §3.4 permits correcting a *pointer*
in a plan while forbidding any other edit — and the distinction does real work here, because
five of the eighteen occurrences are inside fenced code blocks that reproduce a file's
contents or a PR or issue body already published. Those record what was written; changing
them would falsify the record.

**Files:**
- Modify: `docs/src/developer/plans/*.md` (13 pointer lines across 12 plans)
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md` (§10, one path)
- Modify: `README.md:28`

**Interfaces:**
- Consumes: the moved paths from Task 1.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Inventory every remaining occurrence and watch the audit fail**

Two files legitimately hold the old path and must be excluded from both the audit and the
rewrite: `2026-08-03-published-specs-design.md` names it three times in prose *describing*
the migration, and this plan quotes it throughout for the same reason. `docs/_build` is a
build artifact. So:

```bash
grep -rn "docs/superpowers" README.md MANIFEST.in \
  docs/src/developer/specs/2026-07-22-tephpy-design.md \
  docs/src/developer/specs/2026-08-01-add-logo-design.md \
  docs/src/developer/plans/ 2>/dev/null \
  | grep -v 2026-08-03-tephpy-published-specs.md
```

Expected: 20 hits — 13 prose pointers across twelve plans, 5 inside fenced code blocks,
plus `README.md:28` and the parent specification's §10 line. (`MANIFEST.in` should not
appear; Task 1 fixed it.) The five that must survive untouched are:

| File | What the code block reproduces |
|---|---|
| `2026-07-22-tephpy-foundation.md` (`prune docs/superpowers`) | the `MANIFEST.in` as written at Plan 1 |
| `2026-07-22-tephpy-foundation.md` (`See \`docs/superpowers/specs/\` for the design.`) | the `README.md` text as written at Plan 1 |
| `2026-07-29-tephpy-edge-labels.md` | a `gh pr create --body` already published |
| `2026-07-29-tephpy-cursor-readout.md` | a `gh pr create --body` already published |
| `2026-08-01-tephpy-add-logo.md` (`--body '…'`) | the body of issue #72, already filed |

- [ ] **Step 2: Repoint the plans' specification pointers**

A blanket `sed` is wrong here: `2026-07-22-tephpy-foundation.md` contains
`` `docs/superpowers/specs/` `` inside the README code block, and `sed` cannot tell that
from a pointer. Track fence state instead and rewrite only outside fences — and skip this
plan, whose prose and commands quote the old path deliberately.

```bash
pixi run --frozen python - <<'PY'
import re
from pathlib import Path

OLD, NEW = "docs/superpowers/specs/", "docs/src/developer/specs/"
FENCE = re.compile(r"^\s*(```|~~~)")
SKIP = {"2026-08-03-tephpy-published-specs.md"}

total = 0
for path in sorted(Path("docs/src/developer/plans").glob("*.md")):
    if path.name in SKIP:
        continue
    lines = path.read_text().splitlines(keepends=True)
    inside, changed = False, 0
    for index, line in enumerate(lines):
        if FENCE.match(line):
            inside = not inside
            continue
        if not inside and OLD in line:
            lines[index] = line.replace(OLD, NEW)
            changed += 1
    if changed:
        path.write_text("".join(lines))
        print(f"{path.name}: {changed}")
    total += changed
print(f"total {total}")
PY
```

Expected: `total 13`, from twelve plans — `2026-08-01-tephpy-add-logo.md` reports `2`
(its Global Constraints name both specifications) and the other eleven report `1` each.

- [ ] **Step 3: Repoint §10 of the parent specification**

§10 names the plans directory in prose. Replace:

```markdown
plan in `docs/superpowers/plans/`, and a plan is executed and merged before any plan that
```

with:

```markdown
plan in `docs/src/developer/plans/`, and a plan is executed and merged before any plan that
```

- [ ] **Step 4: Repoint the README**

`README.md:28` links to the specifications directory on GitHub, which will 404 after the
move. Point it at the *published* page, not at the new tree path (docs spec §5 item 6):
the Read the Docs project is live and builds `latest` from `main`, so the rendered
collection index exists as soon as this branch merges. Use `/en/latest/`, not `/en/stable/`
— there is no tagged release yet, and `stable` 404s until one exists.

Replace:

```markdown
> out plan by plan for the [design](https://github.com/bjlittle/tephpy/tree/main/docs/superpowers/specs).
```

with:

```markdown
> out plan by plan for the [design](https://tephpy.readthedocs.io/en/latest/developer/specs/index.html).
```

- [ ] **Step 5: Re-run the audit and confirm only the five records remain**

Re-run the Step 1 audit command unchanged.

Expected: exactly 5 hits, all in `docs/src/developer/plans/`, all inside fenced code
blocks, matching the table in Step 1. Any hit in `README.md` or in
`2026-07-22-tephpy-design.md` means a step was missed.

- [ ] **Step 6: Rebuild the docs**

```bash
pixi run --frozen docs 2>&1 | tail -10
```

Expected: `build succeeded.`, exit 0. The specification changed, so the build must stay
clean.

- [ ] **Step 7: Commit**

```bash
git add README.md docs/src/developer/
git commit -m "Repoint the references the specification move invalidated

Corrects the thirteen plan pointers, the parent specification's §10 path
and the README link. Deliberately untouched: five occurrences inside
fenced blocks that reproduce a file's contents or a PR or issue body
already published — those record what was written, not where a document
lives (docs spec §3.4).

Refs #65."
```

---

### Task 4: Create the `design: open` label and file the open-item issues

Docs spec §3.5 sets the contract: any item in §10 or §11 that is not `Resolved` or
`Rejected` must cite a tracked issue. The issues have to exist before Task 5 can cite them.

The `design: open` label makes the contract checkable in both directions — every pointer in
a specification must resolve to an issue, and every issue carrying the label must be cited
by a specification. A one-directional check lets an issue be closed while the specification
still claims the item is open.

**Files:** none — this task is entirely `gh` CLI work against the GitHub repository.

**Interfaces:**
- Produces: seven issue numbers, recorded in the table in Step 10. Task 5 cites them by
  number, referring to them below as issues **A** through **G**.

> **This task is outward-facing.** It creates a label and seven public issues on
> `bjlittle/tephpy`. Confirm with your human partner before running any command in this
> task, and confirm the issue granularity — seven issues is a judgement call, not a
> derivation.

- [ ] **Step 1: Confirm the label name does not collide**

```bash
gh label list --limit 100 | grep -i "design\|spec"
```

Expected: one hit, `type: spec-0` (the scientific-python SPEC 0 support policy). That is the
collision `design: open` was chosen to avoid — a `spec: *` family would read as SPEC 0.
No `design: *` label should exist.

- [ ] **Step 2: Create the label**

The colour is deliberately outside the existing families: `#fbca04` is `type: *`, `#d6a5fe`
is `diátaxis: *`, `#7af461` is `new: *`.

```bash
gh label create "design: open" \
  --description "An unresolved item tracked from a design specification (§10/§11)" \
  --color "006B75"
```

- [ ] **Step 3: File issue A — the Plan 7 residuals**

```bash
gh issue create --label "design: open" --label "type: documentation" \
  --title "Plan 7 residuals: sphinx-tags, the doctest gate, and the SPEC 0 packaging statement" \
  --body 'Three residual Plan 1 deferrals were re-homed to Plan 7 by spec §10 item 15 and
are still outstanding:

- `sphinx-tags` for the examples gallery (spec §8.6)
- a `doctest` pixi task and the `ci-docs` doctest run (spec §8.2, §8.7)
- the SPEC 0 support-policy statement in the packaging guide (spec §8.3)

Verified absent on 2026-08-03: no `sphinx_tags` extension in `docs/src/conf.py`, no
`doctest` task in `pyproject.toml`, no doctest step under `.github/workflows/`.

Tracked per spec §3.5 — the specification carries the pointer, this issue carries the
state.'
```

- [ ] **Step 4: File issue B — the check-manifest gate**

```bash
gh issue create --label "design: open" --label "type: ci" \
  --title "Adopt a check-manifest CI gate once the wheel carries domain code" \
  --body '`check-manifest>=0.49` is declared in `[tool.pixi.feature.devs.dependencies]` but
nothing runs it — no pixi task, no pre-commit hook, no workflow step. Spec §10 item 15 put
the gate on hold pending the wheel carrying domain code.

Worth revisiting sooner than that condition implies. `MANIFEST.in` went stale during the
specification publication work: `prune docs/superpowers` silently stopped matching when the
directory moved, and only a hand-run `python -m build --sdist` caught it before the plans
shipped to PyPI. That is precisely the drift check-manifest exists to catch.

Tracked per spec §3.5.'
```

- [ ] **Step 5: File issue C — the dependency floor gate**

```bash
gh issue create --label "design: open" --label "type: ci" \
  --title "Add a lowest-direct-resolution CI gate for the declared dependency floors" \
  --body 'No CI job resolves tephpy'"'"'s declared minimum dependency versions. Every
workflow runs `pixi run --frozen` against a lockfile, and the wheel smoke test installs the
newest satisfying release, so a wrong floor is invisible.

That is how `matplotlib>=3.9` survived three plans while three modules passed
`Artist.get_figure(root=...)`, a keyword that arrived only in matplotlib 3.10 — spec §10
item 16, corrected in #41 after 3.9.4 was found to fail 26 of 445 tests.

Spec §10 item 16 re-homes the gate to Plan 7.

Tracked per spec §3.5.'
```

- [ ] **Step 6: File issue D — layer highlights and the aviation band**

```bash
gh issue create --label "design: open" --label "type: enhancement" \
  --title "Layer highlights and the aviation icing band (v1.x candidate)" \
  --body 'Two specification items converge on one feature:

- Spec §10 item 12 — layer highlights are named in the §3 module-tree comment but ship in no
  v1 API; Plan 5 shipped `shade_cape`/`shade_cin` only, and layer highlights were deferred
  to v1.x.
- Spec §11 — member emphasis (§3.2) already draws the icing band'"'"'s 0 °C and −20 °C
  bounds as distinguished isotherms, so what remains open is whether the *shaded layer*
  between them is wanted.

Both want the same mechanism: a general layer-shading API in `plotting/shading.py` alongside
the CAPE/CIN shading.

Tracked per spec §3.5.'
```

- [ ] **Step 7: File issue E — the printed-chart citation**

```bash
gh issue create --label "design: open" --label "type: documentation" \
  --title "Find a citable printed tephigram that draws the 0 °C isotherm distinctively" \
  --body 'Spec §11 asks whether a current Met Office Factsheet 13 — or a University of
Reading blank tephigram — shows the 0 °C isotherm drawn distinctively on the printed chart.
The published Factsheet 13 URL 404s (checked 2026-07-30), so member emphasis ships off by
default.

Blocked on a citation. A current published chart showing the convention would justify
revisiting that default.

Tracked per spec §3.5.'
```

- [ ] **Step 8: File issue F — stability indices beyond v1**

```bash
gh issue create --label "design: open" --label "type: enhancement" \
  --title "Decide which stability indices beyond the v1 set are worth wrapping" \
  --body 'Spec §11 asks which named stability indices beyond the v1 set are worth wrapping
in `tephpy.calc` — Showalter, K-index and Total Totals are the candidates — given each is a
one-line `metpy.calc` call for a user who wants it.

Open: no decision taken, no work started. The answer wants operational user input rather
than a design argument, so it is a good candidate to revisit after the first release.

Tracked per spec §3.5.'
```

- [ ] **Step 9: File issue G — the BUFR extra**

```bash
gh issue create --label "design: open" --label "type: enhancement" \
  --title "Assess demand for BUFR ingest as a tephpy[bufr] extra" \
  --body 'Spec §2 and §9 rule TEMP and BUFR decoding out of v1 — the how-to guides point at
eccodes instead. Spec §11 asks whether demand later justifies an optional `tephpy[bufr]`
extra.

Deferred post-v1 and demand-driven: revisit if users ask for it. Nothing to do before the
first release.

Tracked per spec §3.5.'
```

- [ ] **Step 10: Record the issue numbers**

```bash
gh issue list --label "design: open" --state open --limit 20
```

Expected: seven issues. Write the numbers into this table — Task 5 cites them, and every
one of them must be cited or the bidirectional check fails.

| Ref | Issue | Number |
|---|---|---|
| A | Plan 7 residuals | `#___` |
| B | check-manifest gate | `#___` |
| C | dependency floor gate | `#___` |
| D | layer highlights / icing band | `#___` |
| E | printed-chart citation | `#___` |
| F | stability indices | `#___` |
| G | BUFR extra | `#___` |

---

### Task 5: Apply the status vocabulary to §10 and §11

Establishes the true status of §10's sixteen items and §11's four questions and tags each
one, and appends one verification note to §10's service-provisioning bullet. Every edit is
**purely additive** — a leading status tag is prefixed to the item, and where an item's
parts differ a tagged sub-list is appended. No existing prose is reworded, reordered or
deleted (docs spec §7).

The statuses below were established against the repository on 2026-08-03: the plan-to-PR map
is Plan 1 → #1, Plan 2 → #9, Plan 3 → #15, Plan 4 → #19, Plan 5 → #26, Plan 6 → #40 with
hardening in #41.

**Files:**
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md` (§10 items 1-16, §10's
  service-provisioning bullet, §11's four questions)

**Interfaces:**
- Consumes: issue numbers **A**-**G** from Task 4's Step 10 table.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Tag §10 items 1-14**

The form is: status tag, then an em dash, then the item's existing bold title and prose
**verbatim**. Prefix each item with the tag below, leaving everything after the title
untouched.

| Item | Prefix to insert before the existing bold title |
|---|---|
| 1 | `**Resolved** (2026-07-27, PR #19, #26, #40) — ` |
| 2 | `**Resolved** (2026-07-26, PR #26) — ` |
| 3 | `**Resolved** (2026-07-23, PR #9) — ` |
| 4 | `**Resolved** (2026-07-23, PR #9) — ` |
| 5 | `**Resolved** (2026-07-23, PR #9) — ` |
| 6 | `**Resolved** (2026-07-24, PR #15) — ` |
| 7 | `**Resolved** (2026-07-24, PR #15) — ` |
| 8 | `**Resolved** (2026-07-25, PR #19) — ` |
| 9 | `**Refined** (2026-07-25, PR #19) — ` |
| 10 | `**Resolved** (2026-07-26, PR #26) — ` |
| 11 | `**Resolved** (2026-07-26, PR #26) — ` |
| 12 | `**Resolved** (2026-07-26, PR #26) — ` |
| 13 | `**Resolved** (2026-07-27, PR #26, #40) — ` |
| 14 | `**Resolved** (2026-07-26, PR #26) — ` |

So item 3 becomes:

```markdown
3. **Resolved** (2026-07-23, PR #9) — **Plan 2 — the TephigramAxes seam.** *Resolved
   2026-07-23:* the `"tephigram"` projection and a minimal `TephigramAxes` live in
```

Item 9 is `Refined`, not `Resolved`, because its own text records the revision: declared
directly on 2026-07-25, then superseded when the shipped constructors turned out to be
duck-typed with no runtime pandas/xarray import at all.

Item 12 stays `Resolved` — layer highlights are settled as *not in v1*. The v1.x candidacy
its text mentions is tracked by issue **D**; append to the end of item 12:

```markdown
    The v1.x candidacy is tracked in [#D](https://github.com/bjlittle/tephpy/issues/D).
```

Item 11's resolution is complete: Plan 5 re-verified the §6 semantics on a fresh
`metpy=1.6` resolve (1.6.3) at plan-writing time on 2026-07-26 and recorded it in that
plan's Global Constraints, so the floor stays `metpy>=1.6`. No issue is needed.

Item 13's Plan 5 slice landed with the Stull *Practical Meteorology* ch. 14 fixture
attributed in `tests/test_calc.py`; the Plan 6 slice landed with
`tests/fixtures/io/README.md`. Both verified present on 2026-08-03.

- [ ] **Step 2: Tag §10 item 15 and append its per-deferral breakdown**

Item 15 bundles six deferrals with genuinely different statuses, so a single tag would
misreport five of them. Lead with the weakest status and append the breakdown. The item's
opening line becomes:

```markdown
15. **Deferred** (Plan 7 — [#A](https://github.com/bjlittle/tephpy/issues/A)) — **Residual Plan 1 deferrals**, re-homed: sphinx-tags (§8.6) → Plan 7; `doctest` task +
```

and append, at the item's four-space continuation indent, after the existing text ends
with `statement → Plan 7.`:

```markdown

    Per-deferral status:

    - **Deferred** (Plan 7 — [#A](https://github.com/bjlittle/tephpy/issues/A)): sphinx-tags (§8.6).
    - **Deferred** (Plan 7 — [#A](https://github.com/bjlittle/tephpy/issues/A)): the `doctest` task and the `ci-docs` doctest run (§8.2/§8.7).
    - **Deferred** (Plan 7 — [#A](https://github.com/bjlittle/tephpy/issues/A)): the §8.3 packaging-guide SPEC 0 statement.
    - **Resolved** (2026-07-24, PR #15): the `tests-clean` task, with `baselines` alongside it.
    - **Resolved** (2026-07-23, PR #9): the wheel-install smoke test.
    - **On hold** ([#B](https://github.com/bjlittle/tephpy/issues/B)): the check-manifest CI gate — restarts when the wheel carries domain code.
```

- [ ] **Step 3: Tag §10 item 16 and append its residual**

The matplotlib floor question itself is settled. What its text re-homes to Plan 7 — a
lowest-direct-resolution gate — is not. Item 16's opening line becomes:

```markdown
16. **Resolved** (2026-07-29, PR #41) — **matplotlib floor vs. `Artist.get_figure(root=...)`.** §8.1 names matplotlib without
```

and append, at the item's four-space continuation indent:

```markdown

    *Residual:* **Deferred** (Plan 7 — [#C](https://github.com/bjlittle/tephpy/issues/C)) — the lowest-direct-resolution gate.
```

- [ ] **Step 4: Record the Read the Docs project as verified**

§10's *Outside the roadmap* service-provisioning bullet — the last bullet before
`### Assumptions and open decisions` — says "the production PyPI Trusted Publisher (first
exercised by a `v*` tag), the RTD project, and the GitHub Discussions link in the issue
templates remain to be verified." The RTD project is no longer unverified: it builds
`latest` from `main`, `https://tephpy.readthedocs.io/en/latest/` returns 200, and pull
requests carry a `docs/readthedocs.org:tephpy` check. Leaving that clause standing on a
page this change publishes tells a reader the site they are reading does not exist yet.

The bullet is prose, not a tagged item, so it takes an appended verification note in the
spec's existing inline-marker style rather than a status tag — and appending keeps Step 9's
additive check honest. Do **not** reword the existing sentence. Append, at the bullet's
two-space continuation indent, immediately after `remain to be verified.`:

```markdown
  *Verified 2026-08-03:* the RTD project is live — it builds `latest` from `main` and
  reports a `docs/readthedocs.org:tephpy` check on pull requests. Versioned hosting
  (`stable`, `v0.x`) still waits on the first tag, per release execution above.
```

- [ ] **Step 5: Tag §11's four questions**

Each is a top-level bullet. Prefix each with its tag, leaving the question text verbatim:

| Question opens | Prefix to insert |
|---|---|
| `Which aviation-specific overlays (icing layers, MINTRA)…` | `**Deferred** (v1.x — [#D](https://github.com/bjlittle/tephpy/issues/D)) — ` |
| `Whether a current Met Office Factsheet 13…` | `**Blocked** (on a citable published chart — [#E](https://github.com/bjlittle/tephpy/issues/E)) — ` |
| `Which named stability indices beyond the v1 set…` | `**Open** ([#F](https://github.com/bjlittle/tephpy/issues/F)) — ` |
| `Whether BUFR ingest demand justifies…` | `**Deferred** (post-v1, demand-driven — [#G](https://github.com/bjlittle/tephpy/issues/G)) — ` |

So the third becomes:

```markdown
- **Open** ([#F](https://github.com/bjlittle/tephpy/issues/F)) — Which named stability
  indices beyond the v1 set (Showalter, K-index, Total Totals)
  are worth wrapping, given all are one-line `metpy.calc` calls for users?
```

- [ ] **Step 6: Verify the contract holds in both directions**

```bash
pixi run --frozen python - <<'PY'
import re
import subprocess
import sys
from pathlib import Path

spec = Path("docs/src/developer/specs/2026-07-22-tephpy-design.md").read_text()
section = spec[spec.index("### Assumptions and open decisions"):spec.index("## 12. References")]

cited = {int(n) for n in re.findall(r"github\.com/bjlittle/tephpy/issues/(\d+)", section)}

labelled = {
    int(n) for n in subprocess.run(
        ["gh", "issue", "list", "--label", "design: open", "--state", "open",
         "--limit", "50", "--json", "number", "--jq", ".[].number"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
}

print("cited by the specification:", sorted(cited))
print("carrying design: open:     ", sorted(labelled))
print("cited but unlabelled:", sorted(cited - labelled) or "none")
print("labelled but uncited:", sorted(labelled - cited) or "none")
sys.exit(0 if cited == labelled else 1)
PY
```

Expected: the two sets are identical (the seven numbers from Task 4), both difference lines
read `none`, exit 0. A `cited but unlabelled` entry means a placeholder `A`-`G` was left
unresolved; a `labelled but uncited` entry means an issue was filed that no item points at.

- [ ] **Step 7: Confirm no placeholder survived**

```bash
grep -n "issues/[A-G]" docs/src/developer/specs/2026-07-22-tephpy-design.md
```

Expected: no output. Every `#A`-`#G` must have become a real number.

- [ ] **Step 8: Rebuild the docs**

```bash
pixi run --frozen docs 2>&1 | tail -10
```

Expected: `build succeeded.`, exit 0.

- [ ] **Step 9: Confirm the edits were additive**

```bash
git diff --stat docs/src/developer/specs/2026-07-22-tephpy-design.md
git diff docs/src/developer/specs/2026-07-22-tephpy-design.md | grep -c '^-[^-]'
```

Expected: the second command reports only the count of *modified* lines — the item-opening
lines that gained a prefix and nothing else. Read the diff and confirm every `-` line has a
matching `+` line that contains the original text unchanged after the inserted tag. Any `-`
line with no such counterpart is prose that was deleted, which docs spec §7 forbids.

- [ ] **Step 10: Commit**

```bash
git add docs/src/developer/specs/2026-07-22-tephpy-design.md
git commit -m "Tag the status of every open roadmap item

Applies the docs spec §3.5 vocabulary to §10's sixteen items and §11's
four questions, and points every item that is not Resolved or Rejected at
a design: open issue. A published specification that quietly holds live
work is worse than an unpublished one, because publication invites a
reader to trust it.

Refs #65."
```

---

### Task 6: Changelog fragment, lint, and the pull request

**Files:**
- Create: `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: everything Tasks 1-5 committed.

- [ ] **Step 1: Run the full lint suite**

```bash
pixi run --frozen lint
```

Expected: every hook passes. Note that `pixi run --frozen mypy` on its own is **not** a
valid check — it reports roughly 57 pre-existing errors; `lint` is the correct gate.

- [ ] **Step 2: Run the test suite**

Nothing in this plan touches `src/` or `tests/`, so this is a regression check rather than a
verification of new behaviour.

```bash
pixi run --frozen tests 2>&1 | tail -15
```

Expected: all tests pass.

- [ ] **Step 3: Push the branch and open the pull request**

```bash
git push -u origin HEAD
gh pr create \
  --title "Publish the design specifications in the developer guide" \
  --body 'Closes #65.

`src/` and `tests/` carry 333 `spec §…` citations, and until now the documents they cite
never entered the docs build — so a reader on Read the Docs met a reference to something
that, from where they were standing, did not exist, on twelve published API reference
pages.

- `docs/superpowers/{specs,plans}` moves under `docs/src/developer/`, inside the Sphinx
  `SOURCEDIR`. The specifications join the build; the plans stay tracked but withheld, by
  one `exclude_patterns` entry and a `MANIFEST.in` prune.
- Every numbered section in both existing specifications carries an explicit MyST target
  keyed to its number. Without them, publication alone would land all 149 `spec §3.2`
  citations at the top of a 180 KB page — and the prose-derived slugs already collided
  silently, §7 *Testing* and §8.5 *Testing* both becoming `#testing`/`#id1`.
- §10 and §11 gain the status vocabulary from the new `docs spec §3.5`, and every item that
  is not Resolved or Rejected now cites a `design: open` issue.

The conventions behind all of this are written up as a third specification,
`2026-08-03-published-specs-design.md`, which is published alongside the other two.'
```

- [ ] **Step 4: Add the changelog fragment**

Read the PR number from the `gh pr create` output and create
`changelog/<PR>.documentation.rst`:

```rst
Published tephpy's design specifications in the developer guide
(:issue:`65`). The ``spec §…`` citations throughout ``src/`` and ``tests/``
now resolve to a section a reader can reach: every numbered section carries
a stable anchor keyed to its number, rather than the slug docutils derives
from the heading text — which discarded the number and silently collided
where two sections shared a title. The implementation plans stay tracked in
the repository but are deliberately unpublished. Every unresolved item in
the roadmap now carries a status tag and a tracked issue. (:user:`claude`)
```

- [ ] **Step 5: Commit and push the fragment**

```bash
git add changelog/
git commit -m "Add the changelog fragment"
git push
```

- [ ] **Step 6: Confirm CI is green**

```bash
gh pr checks --watch
```

Expected: all checks pass. The PR should carry `type: documentation` from both the
`docs/` path rule in `.github/labeler.yml` and the `docs/*` branch prefix rule in
`ci-label.yml`.
