# Citation Machinery Housekeeping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close {issue}`91`, {issue}`92` and {issue}`93` — the three residuals left by {pull}`89` and {pull}`90`, all of which touch the citation machinery and none of which changes what it does.

**Architecture:** Three independent changes to the same set of files. The two Sphinx extension modules move off generic top-level names onto `tephpy_`-prefixed ones. The two output gates that today run only in `ci-docs.yml` become part of `pixi run docs`, via a `docs-html` build task the gates depend on. Seven facts established during {pull}`90` and surviving nowhere in the tree get written into the files they govern — each re-established by mutation before it is written, because a wrong fact beside the code is worse than no fact.

**Tech Stack:** Sphinx 9, pixi tasks, `importlib.util.spec_from_file_location`, ruff, pre-commit.

## Global Constraints

- **pixi is always `--frozen`.** `pixi run --frozen <task>`. Never let pixi re-solve the lockfile.
- **Every source file carries the BSD copyright header** (ruff `CPY001`). The renamed modules keep theirs verbatim.
- **88 columns** (ruff `E501`) in Python sources.
- **No comment line may begin `# type `.** The pre-commit type-annotations hook matches on that prefix, so wrapped prose whose continuation line starts with the word "type" fails it. Rewrap instead.
- **Citations of the published-specs document use the qualified form `docs spec §N`.** A bare `spec §N` means the *parent* design spec, and resolves silently to the wrong section. The pre-commit gate of docs spec §3.6 checks this; it cannot check a wrong-but-resolving citation, so write the qualified form deliberately.
- **This plan is a point-in-time record** (docs spec §3.4) — frozen once its pull request merges. It is excluded from the docs build by `exclude_patterns` and from the sdist by `MANIFEST.in`.
- **The changelog fragment is written last**, after the pull request is opened, so its number cannot collide with an issue filed in the meantime.

---

### Task 1: Rename the extension modules off `sys.path[0]`

Closes {issue}`92`. `docs/src/conf.py` puts `docs/src/_ext` at `sys.path[0]` for the whole `sphinx-build` process, ahead of `PYTHONPATH` and site-packages, because Sphinx resolves an extension by top-level module name. `citations` and `citation_xrefs` are names a third party could plausibly claim. `tephpy_citations` and `tephpy_citation_xrefs` are names this repository owns.

Nothing is shadowed today — this is prevention. Both gates and both test loaders import **by path**, so none of them breaks on the rename; only the declared name changes.

**Files:**
- Rename: `docs/src/_ext/citations.py` → `docs/src/_ext/tephpy_citations.py`
- Rename: `docs/src/_ext/citation_xrefs.py` → `docs/src/_ext/tephpy_citation_xrefs.py`
- Modify: `docs/src/conf.py:26` — the first `extensions` entry
- Modify: `docs/src/_ext/tephpy_citation_xrefs.py:15,29` — the `:mod:` reference and `import citations`
- Modify: `.github/scripts/check_citations.py:31,67,77` — `GRAMMAR` path, the `_grammar` docstring, the loader name
- Modify: `.github/scripts/check_rendered_citations.py:109,260` — two failure messages that name the module to the reader
- Modify: `tests/test_citation_grammar.py:19,40` — `MODULE` path and the loader name
- Modify: `tests/test_citation_xrefs.py:28,36,38` — the sibling-resolution comment, the path, the loader name
- Modify: `pyproject.toml:151` — the ruff `INP001` per-file-ignore comment

**Interfaces:**
- Consumes: nothing.
- Produces: the module name `tephpy_citations`, imported by `tephpy_citation_xrefs` and loaded by path under that name by `check_citations.py` and `tests/test_citation_grammar.py`; the module name `tephpy_citation_xrefs`, named in `conf.py`'s `extensions` and loaded by path by `tests/test_citation_xrefs.py`. Task 4 edits `tephpy_citations.py` under its new name.

- [ ] **Step 1: Rename both files with git, preserving history**

```bash
git mv docs/src/_ext/citations.py docs/src/_ext/tephpy_citations.py
git mv docs/src/_ext/citation_xrefs.py docs/src/_ext/tephpy_citation_xrefs.py
```

- [ ] **Step 2: Prove the build now fails, so the rename is self-pinning**

Run: `pixi run --frozen --environment docs make -C docs html 2>&1 | tail -5`

Expected: FAIL. Sphinx cannot import `citation_xrefs`, because `conf.py` still names it and no such module is on `sys.path` any more. This is the step that shows `conf.py` cannot silently drift out of step with the filenames — record the error text, it is the evidence for the commit message.

- [ ] **Step 3: Point `conf.py` at the new name**

In `docs/src/conf.py`, the `extensions` list:

```python
extensions = [
    "tephpy_citation_xrefs",
```

The comment above `sys.path.insert` at `:13-17` explains the directory, not the module names, so it stays as written.

- [ ] **Step 4: Point the transform at its renamed sibling**

In `docs/src/_ext/tephpy_citation_xrefs.py`, the import at `:29`:

```python
import tephpy_citations
```

Every use of `citations.` in the module body becomes `tephpy_citations.`. The docstring reference at `:15` becomes:

```
:mod:`tephpy_citations`, shared with the pre-commit gate of docs spec §3.6.
```

Add one sentence to the module docstring of *each* renamed file, disclaiming the obvious misreading. The prefix names the repository that owns the name; it does not mean the module ships:

```
The ``tephpy_`` prefix claims a top-level name this repository owns, because
``docs/src/_ext`` sits at ``sys.path[0]`` for the whole build (:issue:`92`). It
is not part of the installed package -- nothing under ``docs/`` is.
```

Write that as reStructuredText in `tephpy_citation_xrefs.py`, whose docstring is reST. Check `tephpy_citations.py`'s docstring conventions before writing there and match them.

- [ ] **Step 5: Point the input gate at the renamed grammar**

In `.github/scripts/check_citations.py`:

```python
GRAMMAR = REPO / "docs" / "src" / "_ext" / "tephpy_citations.py"
```

```python
    spec = importlib.util.spec_from_file_location("tephpy_citations", GRAMMAR)
```

and in the `_grammar` docstring's `Returns` section, `The loaded ``tephpy_citations`` module.`

Leave the module-level binding `citations = _grammar()` at `:84` and the `citations.` attribute reads below it exactly as they are. That name is a local in the gate's own namespace and claims nothing on `sys.path`; renaming it would churn a dozen lines for no gain.

- [ ] **Step 6: Update the two reader-facing failure messages**

In `.github/scripts/check_rendered_citations.py`, the `BODY` advice at `:109` and the no-link failure at `:260` each name the module to whoever reads the failure. Both become `'tephpy_citation_xrefs'`. Keep them inside 88 columns; rewrap the surrounding string literal if the extra seven characters push a line over.

- [ ] **Step 7: Update both test loaders**

In `tests/test_citation_grammar.py`:

```python
MODULE = REPO / "docs" / "src" / "_ext" / "tephpy_citations.py"
```

```python
    spec = importlib.util.spec_from_file_location("tephpy_citations", MODULE)
```

In `tests/test_citation_xrefs.py`, the comment at `:28` and the loader at `:36-38`:

```python
# `_ext` is a `sys.path` entry at build time rather than a package, so the module
# resolves its sibling `tephpy_citations` by top-level name and cannot be imported
# until that entry exists.
```

```python
    path = EXT / "tephpy_citation_xrefs.py"
    assert path.is_file(), f"the citation transform is missing from {path}"
    spec = importlib.util.spec_from_file_location("tephpy_citation_xrefs", path)
```

- [ ] **Step 8: Update the ruff per-file-ignore comment**

In `pyproject.toml`, the comment above `"docs/src/_ext/*.py" = ["INP001"]`:

```toml
# The Sphinx extension directory is a ``sys.path`` entry at build time, not a
# package: an ``__init__.py`` would stop Sphinx resolving ``tephpy_citation_xrefs``
# by top-level module name (docs spec §3.7).
```

- [ ] **Step 9: Prove no bare module name survives**

Run:

```bash
git grep -nE "spec_from_file_location\(\"citation|^import citations$|\"citation_xrefs\"|:mod:\`citations\`" -- . ':!docs/src/developer/plans'
```

Expected: no output. The plans are excluded because they are frozen point-in-time records (docs spec §3.4) and go on naming what they named.

Then confirm the surviving hits are only the ones that should survive:

```bash
git grep -n "citation_xrefs\|citations" -- .github tests docs/src/_ext docs/src/conf.py pyproject.toml | grep -v tephpy_
```

Expected: only prose uses of the English word "citations", the `citations = _grammar()` local binding and its attribute reads, and the `check-citations` pre-commit hook id. Read every line and confirm each is one of those.

- [ ] **Step 10: Run the suite and the build**

Run: `pixi run --frozen tests`
Expected: PASS, 1120 tests. `tests/test_citation_grammar.py`, `tests/test_citation_xrefs.py` and `tests/test_rendered_citations.py` all load their module by path, so a rename they had not been told about would fail collection.

Run: `pixi run --frozen --environment docs make -C docs html 2>&1 | tail -5`
Expected: `build succeeded.` — the same command that failed at Step 2.

Run: `pixi run --frozen --environment docs python .github/scripts/check_rendered_citations.py docs/_build/html`
Expected: `rendered citations ok: <N> linked, <M> literal, <P> pages (docs spec §3.7)`, exit 0. This is the proof the transform is still loaded under its new name — if `conf.py` and the filename had drifted apart the build would have failed at the previous step, and if the transform had loaded but stopped linking, this gate is what catches it.

- [ ] **Step 11: Run lint**

Run: `pixi run --frozen lint`
Expected: PASS. The `check-citations` hook reads the corpus, which now includes two renamed files; a citation in either that stopped resolving would fail here.

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "Rename the citation extension modules off sys.path[0]"
```

---

### Task 2: Fold both output gates into `pixi run docs`

Closes {issue}`91`. Both gates run in exactly one place, `ci-docs.yml`. Appending one node class to the transform's `SKIP` — the edit someone makes when a citation renders somewhere it should not — makes the transform link nothing while `pixi run docs`, `pixi run lint` and `pixi run tests` all stay green. The contributor finds out after pushing, from a job whose wall time is about 45 s, for a check costing a tenth of a second.

Neither gate touches the network: each reads the HTML the build has just produced. So folding them in costs no wall time worth measuring.

**Files:**
- Modify: `pyproject.toml` — `[tool.pixi.feature.docs.tasks]`
- Modify: `docs/src/developer/specs/2026-08-03-published-specs-design.md` — the opening of §6

**Interfaces:**
- Consumes: nothing from Task 1 (the gates are invoked by path, and their filenames do not change).
- Produces: the pixi tasks `docs-html`, `docs-check-citations`, `docs-check-links`, and `docs` as an alias depending on the two checks. Task 5 runs `pixi run --frozen docs` as the final verification.

- [ ] **Step 1: Confirm pixi accepts a `depends-on`-only task**

Before restructuring, establish the one assumption the shape rests on. Add a throwaway task to `pyproject.toml`:

```toml
[tool.pixi.feature.docs.tasks.probe-alias]
depends-on = ["docs-clean"]
description = "Throwaway: does pixi accept a task with no cmd?"
```

Run: `pixi run --frozen probe-alias`

Expected: it runs `docs-clean` and exits 0. If pixi rejects a task with no `cmd`, abandon the alias shape and instead give `docs` the citations gate as its `cmd` with `depends-on = ["docs-check-links"]`, and note the change in the commit message. Either way, delete `probe-alias` before moving on.

- [ ] **Step 2: Restructure the docs tasks**

Replace the existing `docs` task in `[tool.pixi.feature.docs.tasks]`. `docs-clean` is unchanged and stays where it is. The two gates run from the manifest root — pixi's default working directory — so `docs/_build/html` resolves; only `docs-html` keeps `cwd = "docs"`.

```toml
[tool.pixi.feature.docs.tasks.docs-html]
cmd = "make html"
cwd = "docs"
depends-on = ["docs-clean"]
description = "Build the HTML documentation"

# The two gates of docs spec §3.6-§3.7 read the build's output, and until now ran
# only in `ci-docs.yml`. Neither is visible to `pixi run tests` or `pixi run lint`,
# and a build that linked no citation at all exits 0 -- so `docs` depends on both,
# and a contributor reproduces a `ci-docs` failure without pushing (:issue:`91`).
[tool.pixi.feature.docs.tasks.docs-check-citations]
cmd = "python .github/scripts/check_rendered_citations.py docs/_build/html"
depends-on = ["docs-html"]
description = "Check that every rendered citation became a link"

[tool.pixi.feature.docs.tasks.docs-check-links]
cmd = "python .github/scripts/check_documentation_links.py docs/_build/html"
depends-on = ["docs-html"]
description = "Check that every documentation link resolves in the build"

[tool.pixi.feature.docs.tasks.docs]
depends-on = ["docs-check-citations", "docs-check-links"]
description = "Build the HTML documentation and check its output"
```

Separate tasks rather than one `cmd` chaining both with `&&`, for two reasons. Each gate stays independently re-runnable after a failure. And a newline inside a pixi `cmd` separates commands the way `;` does, not the way `&&` does — so a chained form that lost its `&&` in a later edit would report only the *last* gate's exit code, and a citation failure would pass in silence. That is the failure mode this task exists to close, and it should not be reintroduced in the fix.

- [ ] **Step 3: Confirm the build still happens exactly once**

Run: `pixi run --frozen docs 2>&1 | tee /tmp/docs-run.log | tail -20`

Expected: `build succeeded.`, then both gates' ok lines, exit 0.

Run: `grep -c "reading sources" /tmp/docs-run.log`

Expected: `1`. Both checks depend on `docs-html`, and pixi must deduplicate the shared dependency rather than building twice. If this is `2`, the tasks are being re-run per dependent — drop `docs-check-links`'s `depends-on` and have `docs` depend on `["docs-check-citations", "docs-check-links"]` with the links check depending on the citations check instead, serialising them behind one build.

- [ ] **Step 4: Prove the gate is load-bearing inside `docs`**

This is the mutation {issue}`91` describes. Append a node class to the transform's skip set so it links nothing:

In `docs/src/_ext/tephpy_citation_xrefs.py`, add `nodes.document` to `SKIP`.

`nodes.document` specifically, because `_skipped` walks `node.parent` upward and returns `True` on the first ancestor matching `SKIP` — and every text node's ancestor chain terminates at the document. Adding `nodes.Text` instead would be a silent no-op: a `Text` node's ancestors are elements, never `Text`, so nothing would match and the step would prove nothing.

Run: `pixi run --frozen docs 2>&1 | tail -5`

Expected: FAIL, exit non-zero, `no citation became a link across <N> pages -- is 'tephpy_citation_xrefs' still first in conf.py's extensions?`

Before this task that command exited 0. Record both outputs; they are the evidence the task is worth anything.

- [ ] **Step 5: Revert the mutation and confirm green**

```bash
git checkout docs/src/_ext/tephpy_citation_xrefs.py
```

**Stage Task 1's work first if it is not already committed** — `git checkout <path>` restores from the index, so an uncommitted rename would be discarded along with the mutation. Task 1 Step 12 committed, so the index is clean here; check `git status` before running it regardless.

Run: `pixi run --frozen docs 2>&1 | tail -5`
Expected: `build succeeded.` and both gates ok, exit 0.

- [ ] **Step 6: Amend docs spec §6**

The Verification section opens:

> The docs build runs with `--fail-on-warning --keep-going` and nitpicky cross-references, so a clean `pixi run docs` exiting 0 is the primary gate. Beyond it:

That is now false in a way that matters: the rendered-citation property and the documentation-link property are listed among the things "beyond" `pixi run docs`, and both are now *inside* it. This is a living document (docs spec §3.4), so correct it in place:

> The docs build runs with `--fail-on-warning --keep-going` and nitpicky cross-references, and `pixi run docs` now runs the output gates of §3.7 and of the documentation-link check after it, so a clean `pixi run docs` exiting 0 is the primary gate. Beyond it:

Then re-read the bullets that follow and check each is still accurately placed relative to that sentence — the sweep a living spec needs whenever it is touched, not just the sentence you came for. The bullets covering `_build/html/developer/plans/`, the sdist contents, the rendered specification pages and the §3.3 anchors are properties no gate runs, and stay where they are.

- [ ] **Step 7: Verify the spec edit renders and its citations resolve**

Run: `pixi run --frozen lint`
Expected: PASS — the `check-citations` hook reads the spec and would reject a citation the edit broke.

Run: `pixi run --frozen docs`
Expected: `build succeeded.` and both gates ok. The spec is a built page, so a malformed edit fails under `--fail-on-warning`.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml docs/src/developer/specs/2026-08-03-published-specs-design.md
git commit -m "Run the documentation output gates from pixi run docs"
```

---

### Task 3: Record the four load-bearing facts in the two gate scripts

The first four of {issue}`93`'s seven. Each is re-established here before it is written — the issue's line numbers have all drifted since it was filed, so its claims are treated as leads, not as findings.

**Files:**
- Modify: `.github/scripts/check_rendered_citations.py` — the module docstring, and `handle_startendtag` at `:149-152`
- Modify: `.github/scripts/check_citations.py` — `EXCLUDED` at `:32`, and `corpus()` at `:288`

**Interfaces:**
- Consumes: Task 1's renamed modules only insofar as the messages already updated there stay correct.
- Produces: nothing any later task reads.

- [ ] **Step 1: Establish fact 1 — the gate fails open on an unclosed `<a>`**

`handle_endtag` pops back to a matching tag, so an `<a>` a theme leaves unclosed stays on the stack and every later bare citation on that page counts as linked. Prove it before writing it:

```bash
pixi run --frozen python -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('g', '.github/scripts/check_rendered_citations.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
s = m.Scan(); s.feed('<p><a href=\"#x\">spec §3.2</a><p>spec §3.1</p>')
print('linked', s.linked, 'bare', s.bare)
s2 = m.Scan(); s2.feed('<p><a href=\"#x\">spec §3.2<p>spec §3.1</p>')
print('unclosed: linked', s2.linked, 'bare', s2.bare)
"
```

Expected: the closed case reports one linked and one bare; the unclosed case reports two linked and none bare. That second result is the gate reporting success while doing nothing — the exact failure mode the module docstring at `:15-17` exists to rule out. If the numbers come out otherwise, write what actually happened and say so in the commit.

- [ ] **Step 2: Write fact 1 into the module docstring**

The docstring already records the sibling limitation — a citation inside an *unrelated* hyperlink — at `:19-26`. This one belongs beside it, and matters more, because it fails in the opposite direction. Add after that paragraph:

```
A second limitation runs the other way, and is the one that matters. ``handle_endtag``
pops back to a matching tag, so an ``<a>`` a theme template leaves unclosed is never
popped, and every later bare citation on that page counts as linked -- the gate
reporting success while doing nothing, which is what the paragraph above says it exists
to rule out. The inverse, an ``<a>`` nested inside an ``<a>``, fails closed. Sphinx
output is well-formed, so this is theoretical today; a theme upgrade is the change that
would introduce it.
```

- [ ] **Step 3: Establish fact 2 — the `handle_startendtag` override is defensive**

The override sits at `:149-152`. **Do this step before Step 2, or commit Step 2 first** — the revert below restores the whole file from the index and would take the docstring paragraph with it.

Delete `handle_startendtag` from `.github/scripts/check_rendered_citations.py`, then:

Run: `pixi run --frozen pytest tests/test_rendered_citations.py -q`

Expected: PASS — all 25 tests, including `test_a_self_closing_tag_encloses_nothing` at `:239`. `HTMLParser`'s default `handle_startendtag` calls `handle_starttag` then `handle_endtag`, which is net-neutral for a stack-and-pop model. If any test fails, the override *is* load-bearing and the fact is wrong — write what is true instead.

Restore it:

```bash
git checkout .github/scripts/check_rendered_citations.py
```

Then confirm with `git diff` that Step 2's docstring paragraph is either still present or not yet written — whichever the ordering you chose implies. Losing it silently is the failure mode here.

- [ ] **Step 4: Write fact 2 at the override**

```python
def handle_startendtag(self, _tag: str, _attrs: list[tuple[str, str | None]]) -> None:
    """Ignore a self-closing tag; it encloses nothing.

    Defensive, not load-bearing: deleting this leaves every test in
    ``tests/test_rendered_citations.py`` passing, because ``HTMLParser``
    defaults to ``handle_starttag`` then ``handle_endtag``, which is
    net-neutral for a stack-and-pop model. The test pins the behaviour, not
    the override, and no test can distinguish the two. It stops being
    redundant the moment the classification stops being stack-and-pop.
    """
```

Do not write the test count into that docstring. It was 15 when {issue}`93` was filed and is 25 now; a number nothing checks is a number that drifts, which is fact 3's whole point.

- [ ] **Step 5: Establish fact 3 — the file count is not an invariant**

Read `corpus()` at `:288` and confirm it derives the corpus from `git ls-files` rather than from a declared list, and that the summary at `:353` prints `len(paths)` as its second figure.

```bash
pixi run --frozen python .github/scripts/check_citations.py | tail -1
git ls-files | wc -l
```

Expected: the printed file count moves with the tracked-file count, and this branch has already changed it — the plan document you are reading is a new tracked file. Note the value before and after.

- [ ] **Step 6: Write fact 3 into `corpus()`**

Append to the `corpus()` docstring, after the existing paragraph:

```
The count this feeds the summary line is therefore not an invariant. It moves with
every tracked text file any pull request adds -- it moved from 160 to 166 across
{pull}`90`'s branch alone -- so it must not be asserted in a test or quoted in a
review. The drift is the healthy half of deriving the corpus: a file is governed the
moment it is tracked. The anchor count beside it is the figure that pins the grammar.
```

Write `{pull}` as a literal there only if this file's other prose uses Sphinx roles; it is a `.github/scripts` module and is not built by Sphinx, so check the surrounding docstrings first and match them — plain `PR #90` if the file has no roles anywhere.

- [ ] **Step 7: Establish fact 4 — one citation sits where neither gate can see it**

```bash
sed -n '532,533p' docs/src/developer/plans/2026-08-03-tephpy-published-specs.md
```

Expected: line 532 ends `... 9 \`add_logo\` sections (§2, §3.2–§3.6,` and line 533 opens `§5, §6, §8).` — a compound run wrapping after its comma, whose continuation reads as that document's own sections rather than as `add_logo`'s. Confirm both that `EXCLUDED` at `:32` drops `docs/src/developer/plans/` and that the docs build excludes plans, so neither gate sees it.

- [ ] **Step 8: Write fact 4 at `EXCLUDED`**

```python
#: The plans are dropped because their citations are frozen with them (docs spec
#: §3.4). One consequence is worth knowing before copying prose out of a plan: a
#: compound run that wraps after its comma survives in
#: ``docs/src/developer/plans/2026-08-03-tephpy-published-specs.md``, where the
#: continuation reads as that document's own sections rather than as ``add_logo``'s.
#: The docs build excludes plans too, so no gate sees it and it stays. Re-check the
#: citations of any prose moved from a plan into a governed file.
EXCLUDED = ("docs/src/developer/plans/",)
```

Check whether `EXCLUDED` already carries a comment and fold this into it rather than stacking a second block. Do not quote the plan's line numbers — the plan is frozen, but a line number is exactly the kind of figure fact 3 warns about.

- [ ] **Step 9: Run the suite, the gates and lint**

Run: `pixi run --frozen pytest tests/test_rendered_citations.py tests/test_citations.py tests/test_citation_grammar.py -q`
Expected: PASS.

Run: `pixi run --frozen lint`
Expected: PASS. Watch specifically for the type-annotations hook: none of the comment lines written above may begin `# type `.

Run: `pixi run --frozen docs`
Expected: `build succeeded.` and both gates ok.

- [ ] **Step 10: Commit**

```bash
git add .github/scripts/check_rendered_citations.py .github/scripts/check_citations.py
git commit -m "Record the gates' load-bearing details beside the code"
```

---

### Task 4: Record the three remaining facts in the grammar module and the tests

The last three of {issue}`93`. One of them corrects a published claim in a frozen plan, which is why it belongs beside the test rather than in the plan.

**Files:**
- Modify: `docs/src/_ext/tephpy_citations.py:298` — the `ensure_ascii=False` call
- Modify: `tests/test_citation_grammar.py:154-158` — the `#:` comment above `PIECES`
- Modify: `tests/test_rendered_citations.py:404` — `test_the_gate_fails_when_no_citation_became_a_link`

**Interfaces:**
- Consumes: Task 1's rename — the grammar module is at its new path.
- Produces: nothing any later task reads.

- [ ] **Step 1: Establish fact 5 — `ensure_ascii=False` is load-bearing**

`json.dumps` by default encodes `§` as `§`, which never matches the literal `§` that `nbformat` writes, so every citation-bearing notebook line would fail to locate and fall back to file line 1. Mutate it:

In `docs/src/_ext/tephpy_citations.py:298`, change `json.dumps(line, ensure_ascii=False)` to `json.dumps(line)`.

Run: `pixi run --frozen pytest tests/test_citation_grammar.py tests/test_citations.py -q`

Expected: FAIL — `test_a_notebook_citation_reports_its_own_file_line`. If it passes, the fact is wrong: report that and do not write it. Then revert:

```bash
git checkout docs/src/_ext/tephpy_citations.py
```

- [ ] **Step 2: Write fact 5 at the call**

```python
            # ``ensure_ascii=False`` is load-bearing, not style. The default
            # encodes ``§`` as a ``\uXXXX`` escape, which never matches the
            # literal character ``nbformat`` writes, so every citation-bearing
            # notebook line would fail to locate and fall back to file line 1.
            # ``test_a_notebook_citation_reports_its_own_file_line`` catches the
            # revert -- but only for someone who runs the suite before deciding.
            encoded = json.dumps(line, ensure_ascii=False)[1:-1]
```

Write the escape as `\\uXXXX` inside a docstring if the enclosing scope is one; here it is inline code, so a `#` comment carries it literally. Confirm `pixi run --frozen lint` does not read `\u` in a comment as an invalid escape.

- [ ] **Step 3: Establish fact 6 — the `repeat=5` floor was found by mutation**

The `#:` comment at `:154-158` states the floor and its reason. It does not say that the first version of the test used `repeat=4` and was vacuous for the very case it was written to catch. Re-run both mutations named in {issue}`93` to confirm the floor still holds:

For each of the two mutations — `SEPARATOR` widened to `\s*[,/]\s*`, and the prefix gap widened to `\s` — in `docs/src/_ext/tephpy_citations.py`:

```bash
pixi run --frozen pytest tests/test_citation_grammar.py -q -k segmented
```

Expected with `repeat=5`: FAIL under each mutation. Then edit `tests/test_citation_grammar.py:179` to `repeat=4` and re-run under each mutation.

Expected with `repeat=4`: PASS under both — the test goes vacuous. Revert both the mutation and the `repeat` change after each pair:

```bash
git checkout docs/src/_ext/tephpy_citations.py tests/test_citation_grammar.py
```

If `repeat=4` also fails, the search space has grown since and the floor is no longer 5 — record the value that actually goes vacuous and write *that*.

- [ ] **Step 4: Write fact 6 into the existing comment**

Extend the `#:` block above `PIECES`, rather than adding a second one:

```python
#: Enough grammar to build every construction that has bitten so far -- a
#: multi-word prefix, a one-word prefix, two section numbers, both run
#: separators, a word that is not one, and the wrap itself. Five of these
#: compose the compound-run divergence (prefix, number, separator, wrap,
#: number), so nothing shorter than ``repeat=5`` can express it.
#:
#: The floor was found by mutation, not by reading. The first version of
#: ``test_a_scan_is_indifferent_to_how_its_source_is_segmented`` used
#: ``repeat=4`` and passed under both known mutations -- vacuous for the very
#: case it was written to catch. Lowering ``repeat`` reads as a performance
#: tidy-up and silently empties the only test guarding the defect class rather
#: than one instance of it. Do not lower it without re-running both mutations:
#: ``SEPARATOR`` widened to ``\s*[,/]\s*``, and the prefix gap widened to ``\s``.
PIECES = ["logo spec", "spec", "@3.2", "@1", ",", "/", " and ", "\n"]
```

The `\s` sequences are inside a comment, not a string, so no escaping is needed — but confirm with lint.

- [ ] **Step 5: Establish fact 7 — the plan's untestable-branch claim is wrong**

`docs/src/developer/plans/2026-08-04-tephpy-citation-crossrefs.md:1228` states "The `if not linked` branch is the one no fixture test can supply". Confirm it is reachable and covered:

Run: `pixi run --frozen pytest tests/test_rendered_citations.py::test_the_gate_fails_when_no_citation_became_a_link -q`
Expected: PASS.

Then confirm the test genuinely reaches that branch by mutating it: in `.github/scripts/check_rendered_citations.py`, change `if not linked:` at `:258` to `if False:`.

Run: same command.
Expected: FAIL. Revert with `git checkout .github/scripts/check_rendered_citations.py` — and check `git status` first, because Task 3 committed its edits to that file and an uncommitted change would be discarded.

- [ ] **Step 6: Write fact 7 beside the test**

Extend the docstring of `test_the_gate_fails_when_no_citation_became_a_link`:

```python
def test_the_gate_fails_when_no_citation_became_a_link(monkeypatch, capsys, tmp_path):
    """Total blindness -- the extension unloaded -- is reported as its own failure.

    The implementation plan for docs spec §3.7 states that this branch "is the one
    no fixture test can supply". That is wrong, and the correction belongs here
    because a plan is a frozen point-in-time record (docs spec §3.4). The branch is
    unreachable only against the real build; against a ``tmp_path`` tree of pages
    carrying citations and no links it fires directly, which is what this test does.
    Left uncorrected, the document a maintainer reads to understand the gate argues
    for a coverage hole that does not exist -- in the one branch that catches the
    extension being dropped from ``conf.py``.
    """
```

- [ ] **Step 7: Run everything**

Run: `pixi run --frozen tests`
Expected: PASS, 1120 tests.

Run: `pixi run --frozen lint`
Expected: PASS.

Run: `pixi run --frozen docs`
Expected: `build succeeded.` and both gates ok.

- [ ] **Step 8: Commit**

```bash
git add docs/src/_ext/tephpy_citations.py tests/test_citation_grammar.py tests/test_rendered_citations.py
git commit -m "Record the grammar and test details beside the code"
```

---

### Task 5: Plan, changelog fragment, and final verification

**Files:**
- Create: `changelog/<PR>.internal.rst`
- Add: `docs/src/developer/plans/2026-08-11-tephpy-citation-machinery-housekeeping.md` (this document)

**Interfaces:**
- Consumes: the pull request number, which does not exist until the branch is pushed and the pull request opened.
- Produces: nothing.

- [ ] **Step 1: Commit the plan and push the branch**

```bash
git add docs/src/developer/plans/2026-08-11-tephpy-citation-machinery-housekeeping.md
git commit -m "Add the citation machinery housekeeping plan"
git push -u origin debt-citation-machinery-housekeeping
```

- [ ] **Step 2: Open the pull request and read back its number**

The number must come from the opened pull request, not be guessed: an issue filed in the meantime takes the next number, and a fragment named for it would then be wrong. Write the body with bare `#N` references — Sphinx `{issue}`/`{pull}` roles render literally on GitHub.

- [ ] **Step 3: Write the fragment**

`changelog/<PR>.internal.rst`, where `<PR>` is the number from Step 2. `internal` because none of the three is user-visible: the rename is build-internal, the pixi task is contributor-facing, and the facts are comments.

```rst
The two Sphinx extension modules behind the design-specification citation
cross-references were renamed to ``tephpy_citations`` and
``tephpy_citation_xrefs``, so that no generic top-level name is claimed on
``sys.path`` during a documentation build (:issue:`92`). ``pixi run docs`` now
runs the two output gates that check the build it just produced, which until now
ran only in CI (:issue:`91`). The details that govern how the citation gates and
the shared grammar behave are recorded beside the code they govern
(:issue:`93`). (:user:`bjlittle`)
```

Confirm the `:issue:` and `:user:` roles are the extlinks this repository defines, by checking `extlinks` in `docs/src/conf.py` before writing.

- [ ] **Step 4: Verify the fragment renders with working cross-references**

Run: `pixi run --frozen docs`

This is a clean build — `docs` depends on `docs-html`, which depends on `docs-clean` — so the changelog draft it renders is not a stale one. Open `docs/_build/html/whatsnew/latest.html` (or wherever the unreleased fragments render) and confirm all four roles became links, and that the two gates passed.

- [ ] **Step 5: Full verification**

```bash
pixi run --frozen tests
pixi run --frozen lint
pixi run --frozen docs
```

Expected: 1120 tests pass; all pre-commit hooks pass; `build succeeded.` and both gates ok.

Then confirm the branch closes what it claims:

```bash
git grep -nE "spec_from_file_location\(\"citation|^import citations$|\"citation_xrefs\"" -- . ':!docs/src/developer/plans'
pixi run --frozen pixi task list | grep docs
```

Expected: no output from the first; `docs`, `docs-check-citations`, `docs-check-links`, `docs-clean`, `docs-html` and `serve-html` from the second.

- [ ] **Step 6: Commit and push**

```bash
git add changelog/
git commit -m "Add the changelog fragment"
git push
```

---

## Corrections

Eight claims in the tasks above turned out to be false when the code was executed
during implementation and again during the branch's own review. The task text is
left exactly as it was written: this document is a point-in-time record
(docs spec §3.4), and what it records is what was *planned*, mistakes included.
This section exists because nothing else can flag them — a plan is excluded from
the docs build, from the sdist, and from every gate, so a false claim inside one
survives indefinitely. The branch spent one of its seven facts correcting a claim
of exactly this kind in an earlier plan; the point of writing these down is not to
leave eight more behind. In each case the code carries the true statement, and it
is the code that should be copied out, not the step.

- **Task 2 Step 2** names §3.6 as one of the two gates folded into `pixi run docs`.
  It is not: the gate of docs spec §3.6 reads the *sources*, not the build's
  output, and already ran under `pixi run lint`. What `pixi run docs` gained is the
  gate of docs spec §3.7 and the documentation-link check. The committed comment in
  `pyproject.toml` says so.
- **Task 2 Step 3** expects `grep -c "reading sources"` to print `1` as evidence
  that the shared dependency built once. Sphinx logs that line once per source file
  when its output is not a TTY — 33 times in this build — so the expectation could
  never hold, whatever the task graph did. Build-once was established instead by
  `grep -c "build succeeded"` and `grep -c "^Running Sphinx"`, each of which is 1.
- **Task 3 Step 1** gives the tolerant pop in `handle_endtag` as the reason an
  unclosed `<a>` survives on the stack. It is the reason it does *not*: the pop
  unwinds the whole run down to the tag it matches, and takes the stray `<a>` with
  it. The fail-open window therefore ends at the enclosing element's end tag rather
  than running to the end of the page. The module docstring of
  `check_rendered_citations.py` states the mechanism as it was measured.
- **Task 3 Step 5** expects the corpus count to have moved on this branch because
  "the plan document you are reading is a new tracked file". Plans are dropped by
  `EXCLUDED`, so this document is not in the corpus and cannot move the count. The
  count is 195 at the branch point and 195 at its head.
- **Task 3 Step 6** gives the corpus count as moving from 160 to 166 across
  {pull}`90`'s branch. It moved from 160 to 167, which is the figure written into
  `corpus()`.
- **Task 3 Step 7** describes the citation run surviving in
  `2026-08-03-tephpy-published-specs.md` as breaking *because* it wraps after its
  comma. The run is unprefixed on both physical lines, so the wrap changes nothing:
  scanning the two lines whole and scanning them one at a time agree. The step also
  treats `add_logo` as a citation prefix form. It is not one — it is a function name
  written in prose, and the logo specification's prefix is `logo spec`. Fact 4, as
  committed at `EXCLUDED`, says both of these correctly.
- **Task 4 Step 2** has a notebook line that fails to locate falling back to file
  line 1. It falls back to the previous located line, `max(cursor, 1)`, and reaches
  line 1 only when nothing has been located yet. The committed comment at the
  `json.dumps` call and the `notebook_lines` docstring both say so.
- **Task 4 Step 3** says the first version of
  `test_a_scan_is_indifferent_to_how_its_source_is_segmented` used `repeat=4` and
  "passed under both known mutations". It passes under the `SEPARATOR` mutation
  only; the prefix-to-sign mutation is caught from `repeat=3` upward and so says
  nothing about the floor. `repeat=4` is also not in the history: the test landed at
  `1665bd8` already at `repeat=5`, so no commit ever carried the vacuous version.
