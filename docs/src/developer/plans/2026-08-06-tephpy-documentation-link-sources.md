# Documentation Link Sources Implementation Plan

> **Point-in-time record.** This plan captures what was intended before implementation. It
> is not updated afterwards — where the implementation departed from it, the departure is
> recorded in the pull request, and the living design specification in
> [`../specs/`](../specs/) is what describes tephpy as it stands.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the README link gate to check every file in an explicit list of tracked
sources — starting with `.github/scripts/changelog.py`, which sends a contributor to the
documentation style guide by absolute URL and would go on doing so after that page moved.

**Architecture:** Four changes to one gate, in dependency order. It is renamed
`check_documentation_links.py`, because it no longer checks only the README. Its URL
*detector* gains the quote characters in its terminator set, so a URL written as a Python
string literal ends at the closing quote instead of swallowing it — without that, the one
file this work exists to cover is reported non-canonical the moment it is added. A
`SOURCES` constant then names the files to read, `main()` loops over them, and the report
aggregates: one set of counts, and each offender attributed to the source it came from when
more than one was checked. Finally `changelog.py` joins the list and
`docs/src/developer/docs-style.rst` records the rule for the next file that needs one.

**Tech Stack:** Python 3.12 stdlib only (`re`, `pathlib`, `textwrap`, `typing.NamedTuple`)
— no new dependency; pytest; GitHub Actions (`ci-docs.yml`); Sphinx; towncrier; pixi.

**Spec:** None. This extends a gate over built output and one authoring rule in
`docs/src/developer/docs-style.rst`; the published-specifications design (`docs spec`) is
scoped to *design-specification* citations and does not cover it. The reasoning behind the
gate stays where it already lives — its module docstring — exactly as
`check_rendered_citations.py` does.

**Issue:** [#100](https://github.com/bjlittle/tephpy/issues/100). Note that the issue's
written implementation path is wrong, and this plan does not follow it: it says the gate
can be pointed at `changelog.py` as it stands, but doing so reports that file's URL as
non-canonical, because `DOCS`'s terminator set does not stop at a quote. Task 2 is that
correction, and it comes before the file is added.

## Global Constraints

- **Every pixi invocation carries `--frozen`.** `pixi run --frozen tests`,
  `pixi run --frozen lint`, `pixi run --frozen docs`. Never let pixi re-solve the
  environment.
- **`pixi run --frozen docs` is already a clean build.** The `docs` task declares
  `depends-on = ["docs-clean"]`, so it runs `make clean` first. Do not verify links against
  a bare `make -C docs html` — an incremental build serves a stale page and the gate would
  then be checking yesterday's ids.
- **`git commit` must run inside the pixi environment.** The `pre-commit` hook binary is
  not on the bare `PATH`; a plain `git commit` fails with ``pre-commit` not found`. Use
  `pixi run --frozen bash -c 'git commit -F <file>'`, or run `pixi shell` first. Run
  `pre-commit install` once in a fresh worktree.
- **Bare `python` is not on `PATH`.** Every ad-hoc Python invocation goes through
  `pixi run --frozen python` (or `--environment docs` when it needs the docs environment).
- **Ruff runs `select = ["ALL", "D212"]` at `line-length = 88`**, numpy docstring
  convention, `force-sort-within-sections = true`, and
  `required-imports = ["from __future__ import annotations"]`.
- **Every source file carries the BSD copyright header** (ruff `CPY001`) — the four comment
  lines already at the top of both files this plan touches. `git mv` keeps them.
- **`.github/scripts/*.py` has `per-file-ignores = ["FBT001", "T201"]`**, so `print()` and a
  boolean positional argument are permitted there. Neither is permitted in `tests/`.
- **A script carrying a shebang must be mode `100755`** — ruff's `EXE001` fails it
  otherwise. `git mv` preserves the bit; a `cp`/`rm` pair does not.
- **`tests/*` has `per-file-ignores = ["ANN001", "ANN003", "ANN201", "ANN202", "DTZ001",
  "SLF001", "D103"]`.** Test functions need no annotations and no docstrings; module and
  helper docstrings are still required. Note `ANN002` is *not* ignored, so a `*args`
  parameter in a test helper must be annotated.
- **mypy (`files = ["src/tephpy"]`) and numpydoc-validation (`files: '^src/'`) do not reach
  `.github/scripts/`.** Do not add type-checking scaffolding for them — but do write
  numpydoc `Parameters`/`Returns` sections, because the neighbouring gate does and the file
  should read like it.
- **No new runtime, test or docs dependency.** The gate stays stdlib-only.
- **Write no literal section sign (`§`) in any file under `.github/`, `src/`, `tests/` or
  `docs/src/**` other than this plan.** The pre-commit citation gate reads the source corpus
  and rejects a bare `§N` in a file that owns no sections.
- **The plans directory is out of the checked corpus** (docs spec §3.4), and is excluded
  from the docs build by `exclude_patterns` and `MANIFEST.in`. This file is a plan.
- **Ruff format may re-quote a string you write.** Run `pixi run --frozen lint` after every
  edit and accept its normalisation rather than fighting it.

---

## File Structure

| File | Responsibility |
|---|---|
| `.github/scripts/check_readme_links.py` → `.github/scripts/check_documentation_links.py` | **Rename and modify.** The whole gate. Gains `SOURCES`, a per-source `scan()` returning a `Report`, aggregate reporting with source attribution, and a `plural()` helper. |
| `tests/test_readme_links.py` → `tests/test_documentation_links.py` | **Rename and modify.** Existing coverage retargeted at the new name and success line, plus tests for the quoted URL, the source list, aggregation, attribution, per-source blindness and the singular page count. |
| `.github/workflows/ci-docs.yml` | **Modify.** One line: the script name. The invocation is otherwise unchanged — the source list lives in the script, not in the workflow. |
| `docs/src/developer/docs-style.rst` | **Modify.** Generalise the "Landing Page Links" section to "Documentation Links", covering any absolute documentation URL in tracked source, and naming `SOURCES` as where a new one is registered. |
| `changelog/<PR>.internal.rst` | **Create.** towncrier fragment. |

**Why an explicit list and not repository-wide discovery:** a sweep would check whatever
happened to be quoted in a test fixture, a changelog fragment, or this plan — and a plan is
a point-in-time record that is *supposed* to go on naming the URL it named. A short list
says what the project means to keep working, and a file that stops needing to be on it
fails loudly rather than dropping out in silence.

**Why the source label and not `Path.name`:** `SOURCES` holds repository-relative paths, so
`.github/scripts/changelog.py` in a failure report is the path to open. A basename would
be shorter and would go ambiguous the first time two sources share one.

---

### Task 1: Rename the gate

Pure rename. No behaviour changes, and the test suite must be green on the same 15 tests
before and after.

**Files:**
- Rename: `.github/scripts/check_readme_links.py` → `.github/scripts/check_documentation_links.py`
- Rename: `tests/test_readme_links.py` → `tests/test_documentation_links.py`
- Modify: `.github/workflows/ci-docs.yml`
- Modify: `docs/src/developer/docs-style.rst:188`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, relied on by every later task:
  - The module path `.github/scripts/check_documentation_links.py`.
  - The test module `tests/test_documentation_links.py`, importing the gate under the
    module alias `gate` (was `crl`).

- [ ] **Step 1: Move both files with `git mv`**

```bash
git mv .github/scripts/check_readme_links.py .github/scripts/check_documentation_links.py
git mv tests/test_readme_links.py tests/test_documentation_links.py
```

`git mv` preserves mode `100755` on the script. Confirm it did:

```bash
git ls-files -s .github/scripts/check_documentation_links.py
```

Expected: a line beginning `100755`.

- [ ] **Step 2: Update the script's usage line**

In `.github/scripts/check_documentation_links.py`, inside `main()`:

```python
        print("usage: check_documentation_links.py <html-root> [readme]")
```

Nothing else in the script changes in this task — its docstring still describes a
README-only gate, which is still what it is.

- [ ] **Step 3: Update the test module**

In `tests/test_documentation_links.py`, change the docstring, the script path, the import
name, the assertion message, the alias, and the two argv strings:

```python
"""Tests for the documentation-link gate."""
```

```python
SCRIPT = REPO / ".github" / "scripts" / "check_documentation_links.py"
```

```python
def _load():
    """Import the gate by path; ``.github`` is not an importable package."""
    assert SCRIPT.is_file(), f"the documentation link gate is missing from {SCRIPT}"
    spec = importlib.util.spec_from_file_location("check_documentation_links", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load() if SCRIPT.is_file() else None
```

Then rename every remaining `crl.` to `gate.` — there are occurrences in `url()`, `run()`
and `test_usage_is_reported`. In `run()`:

```python
def run(monkeypatch, capsys, root, path):
    """Run the gate over ``root`` and ``path``; return its code and output."""
    monkeypatch.setattr(
        gate.sys, "argv", ["check_documentation_links.py", str(root), str(path)]
    )
    code = gate.main()
    return code, capsys.readouterr().out
```

And in `test_usage_is_reported`:

```python
    assert "usage: check_documentation_links.py" in capsys.readouterr().out
```

Check nothing was missed:

```bash
grep -rn 'check_readme_links\|\bcrl\b' tests/ .github/ src/ README.md \
  docs/src/developer/docs-style.rst
```

Expected after Step 4: no output. The two plans under `docs/src/developer/plans/` name the
old script throughout and must go on doing so — a plan is a point-in-time record of what
was intended then, so it is deliberately outside this sweep.

- [ ] **Step 4: Update the two references outside the gate**

`.github/workflows/ci-docs.yml`, the last step:

```yaml
      - run: >
          pixi run --frozen --environment docs
          python .github/scripts/check_documentation_links.py docs/_build/html
```

`docs/src/developer/docs-style.rst:188`:

```rst
The documentation build checks these links. ``check_documentation_links.py`` reads
each URL out of the README and looks it up in the HTML just built, failing when the
```

Keep the paragraph's remaining lines as they are; only the script name and the line
wrapping change. Re-wrap the paragraph to fit within the file's existing width.

- [ ] **Step 5: Run the tests**

```bash
pixi run --frozen tests tests/test_documentation_links.py -v
```

Expected: 15 passed. A rename that changed behaviour shows up here.

- [ ] **Step 6: Lint and commit**

```bash
pixi run --frozen lint
pixi run --frozen bash -c 'git add -A && git commit -m "Rename the README link gate to the documentation link gate"'
```

---

### Task 2: Read a URL written in a quoted string

The gate's `DOCS` detector stops a URL at whitespace, `)` or `]` — the characters that end
a Markdown link. A URL written as a Python string literal ends at its quote instead, and
the quote is currently swallowed into the match, so `LINK.fullmatch` rejects it and the
gate reports a perfectly good link as non-canonical. This is the defect that blocks
issue #100's stated approach, and it is fixed before any new source is added.

**Files:**
- Modify: `.github/scripts/check_documentation_links.py:65-74`
- Modify: `tests/test_documentation_links.py`

**Interfaces:**
- Consumes: the renamed module and the `gate` alias from Task 1.
- Produces: `DOCS` matching a URL that ends at `'` or `"`. Task 4 relies on this; nothing
  else in the module changes signature.

- [ ] **Step 1: Write the failing test**

Add a page constant beside the existing two, at the top of
`tests/test_documentation_links.py`:

```python
STYLE = "developer/docs-style.html"
```

Then add this test after `test_an_http_url_is_not_canonical`:

```python
def test_a_quoted_url_is_a_link(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {STYLE: "<html><body></body></html>"})
    text = f'URL = "{gate.BASE}{STYLE}"\n'
    source = tmp_path / "changelog.py"
    source.write_text(text, encoding="utf-8")
    code, out = run(monkeypatch, capsys, root, source)
    # A URL in a script ends at the closing quote, not at a Markdown ")" or "]".
    # Leave the quote out of the terminator set and it is swallowed into the URL,
    # so the page path stops matching and a good link is reported non-canonical --
    # the gate crying wolf at the one kind of source it is being extended to cover.
    assert gate.links(text) == [(STYLE, "")]
    assert gate.strays(text) == []
    assert code == 0
    assert "1 checked" in out
```

- [ ] **Step 2: Run it to make sure it fails**

```bash
pixi run --frozen tests tests/test_documentation_links.py::test_a_quoted_url_is_a_link -v
```

Expected: FAIL on `assert gate.links(text) == [(STYLE, "")]`, with the actual value `[]` —
the URL matched by `DOCS` carries a trailing `"` that `LINK.fullmatch` will not accept.

- [ ] **Step 3: Widen the terminator set**

In `.github/scripts/check_documentation_links.py`, replace the `DOCS` comment and pattern:

```python
#: Any URL onto a documentation host of this project -- the published site, or a
#: per-pull-request Read the Docs preview. The match stops before whitespace, ``)``,
#: ``]`` and either quote, which is where a URL ends in the two kinds of source
#: checked here: a Markdown inline link or reference definition, and a string
#: literal in a script. A character missing from this set is swallowed into the
#: URL, which turns a good link into a reported one. Either scheme matches,
#: deliberately: this pattern decides what gets *judged*, so narrowing it to
#: ``https`` would make a plaintext link invisible to the gate instead of
#: non-canonical.
DOCS = re.compile(
    r"https?://(?:tephpy\.readthedocs\.io"
    r"|tephpy--[\w.-]+?\.org\.readthedocs\.build)[^\s)\]'\"]*"
)
```

- [ ] **Step 4: Run the whole module**

```bash
pixi run --frozen tests tests/test_documentation_links.py -v
```

Expected: 16 passed. In particular `test_a_preview_host_url_is_not_canonical` and
`test_text_after_the_page_is_not_canonical` must still fail their URLs — widening the
terminator set must not narrow what gets judged.

- [ ] **Step 5: Prove the test guards the fix**

Revert the pattern to `[^\s)\]]*`, run the module, and confirm exactly one test fails —
`test_a_quoted_url_is_a_link`. Restore the fix.

- [ ] **Step 6: Lint and commit**

```bash
pixi run --frozen lint
pixi run --frozen bash -c 'git add -A && git commit -m "Stop a documentation URL at the quote that closes it"'
```

---

### Task 3: Check a list of sources

The gate reads one file named by `argv[2]` or defaulted to the README. This task replaces
that with a `SOURCES` list, a per-source scan, and a report that aggregates across sources.
`SOURCES` holds only `README.md` here, so CI behaviour is unchanged and every existing
test stays meaningful; Task 4 adds the second entry.

**Files:**
- Modify: `.github/scripts/check_documentation_links.py`
- Modify: `tests/test_documentation_links.py`

**Interfaces:**
- Consumes: the renamed module (Task 1) and the widened `DOCS` (Task 2).
- Produces, relied on by Task 4 and by the tests in this task:
  - `SOURCES: tuple[str, ...]` — repository-relative paths, checked when the command line
    names none.
  - `Report` — a `NamedTuple` with fields `found: list[tuple[str, str]]`,
    `absent: list[str]`, `broken: list[str]`, `stray: list[str]`, `pages: set[str]`.
  - `scan(text: str, root: Path) -> Report`.
  - `plural(count: int, noun: str) -> str`.
  - `gathered(picked: dict[str, list[str]], *, tagged: bool) -> list[str]`.
  - CLI: `check_documentation_links.py <html-root> [source ...]`. With no source named,
    `SOURCES` is checked; with one or more named, exactly those are.

- [ ] **Step 1: Write the failing tests**

Change the `run()` helper to take any number of sources — note the `*paths: Path`
annotation, because `tests/*` does not ignore `ANN002`:

```python
def run(monkeypatch, capsys, root, *paths: Path):
    """Run the gate over ``root`` and ``paths``; return its code and output."""
    argv = ["check_documentation_links.py", str(root), *(str(path) for path in paths)]
    monkeypatch.setattr(gate.sys, "argv", argv)
    code = gate.main()
    return code, capsys.readouterr().out
```

Every existing call passes exactly one path and keeps working.

Add a helper beside `readme()`, for a source that is a script rather than Markdown:

```python
def script(tmp_path, *targets: str):
    """Write a Python source naming each target the way a script does."""
    path = tmp_path / "changelog.py"
    body = "".join(f'URL = "{gate.BASE}{target}"\n' for target in targets)
    path.write_text(body, encoding="utf-8")
    return path
```

Then update the two tests that assert the old success line:

```python
    assert "2 checked across 1 source, 2 naming an anchor" in out
```

in `test_resolving_links_pass`, and:

```python
    assert "2 checked across 1 source, 1 naming an anchor, across 2 pages" in out
```

in `test_the_success_line_counts_anchors_and_pages`.

Update the blindness test, which now names its source and carries new advice:

```python
def test_a_source_with_no_links_fails(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, "# tephpy\n\nNo links here.\n")
    code, out = run(monkeypatch, capsys, root, path)
    # A source that has lost its links is a search this gate no longer makes, and
    # a check that passes on an empty search is a green tick over nothing. It is
    # named, because with several sources "nowhere" does not say which one.
    assert code == 1
    assert "README.md links into the documentation nowhere" in out
    assert "Remove it from SOURCES, or restore the link" in flat(out)
```

Rename the old `test_readme_with_no_links_fails` out of existence — this replaces it.

Then add six new tests at the end of the module:

```python
def test_two_sources_are_both_checked(tmp_path, monkeypatch, capsys):
    root = build(
        tmp_path,
        {GLOSSARY: terms("term-CAPE"), STYLE: "<html><body></body></html>"},
    )
    first = readme(tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')})")
    second = script(tmp_path, STYLE)
    code, out = run(monkeypatch, capsys, root, first, second)
    # The counts are of the whole check, not of whichever source came last.
    assert code == 0
    assert "2 checked across 2 sources, 1 naming an anchor, across 2 pages" in out


def test_a_failure_names_its_source(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    first = readme(tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')})")
    second = script(tmp_path, SPECS)
    code, out = run(monkeypatch, capsys, root, first, second)
    # With more than one source checked, a bare page path does not say which file
    # to open, and the reader is sent hunting through every source for the URL.
    assert code == 1
    assert "Missing pages (1)" in out
    assert f"{SPECS} (" in out
    assert "changelog.py)" in out


def test_one_source_is_not_attributed(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, f"[specs]({url(SPECS)})")
    code, out = run(monkeypatch, capsys, root, path)
    # One source names itself in the invocation, so attributing its entries to it
    # is noise on every line of the report.
    assert code == 1
    assert f"{SPECS}\n" in out
    assert f"{SPECS} (" not in out


def test_a_single_page_is_singular(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, f"[CAPE]({url(GLOSSARY, 'term-CAPE')})")
    code, out = run(monkeypatch, capsys, root, path)
    # "across 1 pages" reads as a line nobody has looked at, which is an odd thing
    # for a report whose whole job is to be believed.
    assert code == 0
    assert "1 checked across 1 source, 1 naming an anchor, across 1 page" in out
    assert "1 pages" not in out


def test_the_defaults_come_from_sources(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    monkeypatch.setattr(gate, "SOURCES", ("nowhere/missing.md",))
    code, out = run(monkeypatch, capsys, root)
    # With no source named on the command line the gate checks SOURCES. Were it to
    # fall back to the README instead, adding a file to that list would change
    # nothing and no run would say so.
    assert code == 1
    assert "no such file" in out
    assert "nowhere/missing.md" in out


def test_every_listed_source_exists():
    # SOURCES names files by path. A rename that misses this list turns the check
    # into "no such file" on the next run -- a failure, but not the one anyone is
    # looking for, and one that hides whatever the run was meant to catch.
    missing = [name for name in gate.SOURCES if not (REPO / name).is_file()]
    assert missing == []
```

- [ ] **Step 2: Run them to make sure they fail**

```bash
pixi run --frozen tests tests/test_documentation_links.py -v
```

Expected: `test_two_sources_are_both_checked`, `test_a_failure_names_its_source`,
`test_a_single_page_is_singular`, `test_the_defaults_come_from_sources`,
`test_every_listed_source_exists`, `test_a_source_with_no_links_fails`,
`test_resolving_links_pass` and `test_the_success_line_counts_anchors_and_pages` all fail.
`test_one_source_is_not_attributed` passes already — it pins behaviour the rewrite must not
lose, so it earns its place as a guard rather than as a driver.

- [ ] **Step 3: Rewrite the module docstring**

The gate no longer checks only the README, and the docstring is where its reasoning lives.
Replace the docstring in `.github/scripts/check_documentation_links.py` with:

```python
"""Check that every documentation link in tracked source resolves in the build.

A few tracked files reach the documentation by absolute URL, because they are not
sources of the Sphinx project and have no role to write instead: ``README.md`` is
the repository's landing page, and a script that fails a contributor sends them to
the page that explains why. Nothing in the build sees those links -- ``nitpicky``
checks the references Sphinx itself resolved, and the rendered-citation gate reads
only pages the build produced. Meanwhile a glossary anchor is derived from the term
-- Sphinx keeps the case and collapses each run of non-alphanumeric characters to a
single hyphen, so ``Normand's point`` becomes ``term-Normand-s-point`` -- which
makes renaming a term a silent way to break the landing page, and moving a page
another.

This gate closes that gap from the outside. ``SOURCES`` names the files it reads:
an explicit list rather than a sweep of the repository, because a sweep would judge
whatever happened to be quoted in a test fixture or a frozen implementation plan,
and a plan is meant to go on naming the URL it named. Each URL is looked up in the
HTML the build has just produced: the page must exist, and a fragment must name an
``id`` on it. Nothing here reproduces the slug rule, because the ids are read off
the built page rather than derived. A normalisation of our own would be one more
thing able to drift from Sphinx, which is the drift this gate exists to catch.

Only the canonical ``en/latest`` URL can be looked up that way, so a link onto a
documentation host of this project written any other way is reported rather than
skipped in silence. A per-pull-request preview is where a documentation change is
verified and the wrong place to link from tracked source, because Read the Docs
deletes it when the pull request closes; and ``latest`` is the only version this
project publishes.

A listed source carrying no documentation link at all fails too. A check is worth
what it covers, and a rewrite that dropped every link from one source would
otherwise pass in silence while that source quietly left the check behind.

Three things are deliberately not checked. That a link points at the *right* page
is a question about meaning, not resolution, and no gate can answer it. An
``en/latest`` URL is checked against the working tree's own build, which is the
only build available -- a link correct here is wrong on the published site until
this branch merges, and that is the ordinary lag of source that names a moving
target. And a URL on a documentation host of this project whose path never says
``.html`` is passed over rather than judged: it is how the Read the Docs badge,
which points at the base with a query string, stays out of the report, and it lets
through a directory-style URL, which Read the Docs does resolve and which carries
no page or anchor to look up.

Notes
-----
.. versionadded:: 0.1.0

"""
```

- [ ] **Step 4: Add the import, the source list and the reworded advice**

The import block gains `typing`, which sorts last under `force-sort-within-sections`:

```python
from pathlib import Path
import re
import sys
import textwrap
from typing import NamedTuple
```

Add `SOURCES` immediately after `BASE`:

```python
#: The tracked files this gate reads, relative to the repository root. A file earns
#: a place here by writing an absolute documentation URL somewhere no Sphinx build
#: can see it. Keep the list short and deliberate: it is the statement of which
#: links the project means to keep working, and everything not on it is unchecked.
SOURCES = ("README.md",)
```

Replace `BLIND`, which spoke only of the README:

```python
#: What to do about a listed source that links into the documentation nowhere.
BLIND = (
    "A source with no documentation link is not one this check can check, so it "
    "fails rather than passing on an empty search. Each source is listed because "
    "it writes a documentation URL where no Sphinx build can see it; one that no "
    "longer does has nothing left to go wrong and no reason to stay listed. "
    "Remove it from SOURCES, or restore the link."
)
```

- [ ] **Step 5: Retarget the two extraction docstrings**

`links()` and `strays()` say "the README" and take "the README, as Markdown". They now take
any source. In `links()`:

```python
def links(text: str) -> list[tuple[str, str]]:
    """Find every canonically written documentation link in one source.

    Parameters
    ----------
    text : str
        The source file's text.
```

and in `strays()`:

```python
def strays(text: str) -> list[str]:
    """Find every documentation link one source writes non-canonically.

    Parameters
    ----------
    text : str
        The source file's text.
```

Leave the `Returns` and `Notes` sections of both alone, except that `strays()`'s `Returns`
says "the README" once — make it "one source". Likewise `path()`'s parameter description,
"A documentation URL, as the README writes it", becomes "A documentation URL, as a source
writes it".

- [ ] **Step 6: Add `Report`, `scan()`, `plural()` and `gathered()`**

Put `Report` directly after the advice constants, before `links()`:

```python
class Report(NamedTuple):
    """What one checked source's documentation links came to."""

    found: list[tuple[str, str]]
    absent: list[str]
    broken: list[str]
    stray: list[str]
    pages: set[str]
```

Put `scan()`, `plural()` and `gathered()` after `listed()` and before `main()`:

```python
def scan(text: str, root: Path) -> Report:
    """Look every documentation link in one source up in the built HTML.

    Parameters
    ----------
    text : str
        The source file's text.
    root : pathlib.Path
        The root of the HTML the build produced.

    Returns
    -------
    Report
        What that source's links came to, with the pages named rather than
        counted, so several sources naming one page count it once.

    """
    found = links(text)
    ids: dict[str, set[str] | None] = {}
    for page, _ in found:
        if page not in ids:
            built = root / page
            ids[page] = anchors(built) if built.is_file() else None
    return Report(
        found=found,
        absent=sorted(page for page, carried in ids.items() if carried is None),
        # Keyed by page and fragment together, so one broken anchor named twice in
        # one source is one thing to fix and is reported as one.
        broken=sorted(
            {
                f"{page}#{anchor}"
                for page, anchor in found
                # An absent page carries no ids to miss; it is reported as absent.
                if anchor and ids[page] is not None and anchor not in ids[page]
            }
        ),
        stray=strays(text),
        pages=set(ids),
    )


def plural(count: int, noun: str) -> str:
    """Give ``noun`` the ending ``count`` calls for.

    Parameters
    ----------
    count : int
        How many of the thing there are.
    noun : str
        Its singular form.

    Returns
    -------
    str
        ``noun`` written for that count. A report that says "1 pages" reads as one
        nobody has looked at, which invites the reader to distrust the number
        beside it.

    """
    return noun if count == 1 else f"{noun}s"


def gathered(picked: dict[str, list[str]], *, tagged: bool) -> list[str]:
    """Collect one kind of offender from every source, once each.

    Parameters
    ----------
    picked : dict of (str, list of str)
        The offenders of one kind, keyed by the source they were found in, named
        as it was given.
    tagged : bool
        Whether to name the source each offender came from.

    Returns
    -------
    list of str
        The offenders, sorted, and once each: the same thing wrong twice in one
        source is one entry, and untagged, the same thing wrong in two sources is
        one entry too -- which is right, because untagged means one source.

    """
    return sorted(
        {
            f"{entry} ({name})" if tagged else entry
            for name, entries in picked.items()
            for entry in entries
        }
    )
```

- [ ] **Step 7: Rewrite `main()`**

Replace `main()` in full:

```python
def main() -> int:
    """Check each source's documentation links against the built HTML.

    Returns
    -------
    int
        ``0`` when every link resolves, ``1`` otherwise.

    """
    if len(sys.argv) < 2:
        print("usage: check_documentation_links.py <html-root> [source ...]")
        return 1
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"no such directory: {root}")
        return 1
    repo = Path(__file__).parents[2]
    # Named as given, so a listed source is reported by the path that finds it in
    # the repository rather than by a basename two sources could share.
    named = [(name, Path(name)) for name in sys.argv[2:]]
    sources = named or [(name, repo / name) for name in SOURCES]

    reports: dict[str, Report] = {}
    for name, source in sources:
        if not source.is_file():
            print(f"no such file: {source}")
            return 1
        reports[name] = scan(source.read_text(encoding="utf-8"), root)

    # A source linking only non-canonically does link into the documentation, so
    # it is told what is wrong with those links rather than that it has none.
    blind = [
        name for name, report in reports.items() if not report.found and not report.stray
    ]
    if blind:
        for name in blind:
            print(f"{name} links into the documentation nowhere")
        print(f"\n{textwrap.fill(BLIND)}")
        return 1

    # One source names itself in the invocation, so attributing every entry to it
    # is noise; more than one, and a bare page path does not say which file to open.
    tagged = len(reports) > 1
    absent = gathered(
        {name: report.absent for name, report in reports.items()}, tagged=tagged
    )
    broken = gathered(
        {name: report.broken for name, report in reports.items()}, tagged=tagged
    )
    stray = gathered(
        {name: report.stray for name, report in reports.items()}, tagged=tagged
    )

    if not absent and not broken and not stray:
        checked = sum(len(report.found) for report in reports.values())
        anchored = sum(
            1 for report in reports.values() for _, anchor in report.found if anchor
        )
        pages = {page for report in reports.values() for page in report.pages}
        print(
            f"Documentation links ok: {checked} checked across "
            f"{len(reports)} {plural(len(reports), 'source')}, "
            f"{anchored} naming an anchor, across "
            f"{len(pages)} {plural(len(pages), 'page')}"
        )
        return 0
    if absent:
        print(f"Missing pages ({len(absent)}):")
        print(f"  {listed(absent)}")
        print(f"\n{textwrap.fill(MISSING_PAGE)}")
    if broken:
        print(f"\nMissing anchors ({len(broken)}):")
        print(f"  {listed(broken)}")
        print(f"\n{textwrap.fill(MISSING_ANCHOR)}")
    if stray:
        print(f"\nNon-canonical URLs ({len(stray)}):")
        print(f"  {listed(stray)}")
        print(f"\n{textwrap.fill(NOT_CANONICAL)}")
    print("\nSee 'Documentation Links' in docs/src/developer/docs-style.rst.")
    return 1
```

Two details worth naming. The closing pointer now says `'Documentation Links'`, which is
the section title Task 4 gives that part of `docs-style.rst`; leaving it as "Landing Page
Links" would send the reader to a heading that no longer exists. And two advice constants
still speak only of the README — replace them with:

```python
#: What to do about a link naming a page the build did not produce.
MISSING_PAGE = (
    "The build produced no such page. A page that is renamed or moved leaves the "
    "source pointing at a URL Read the Docs answers with a 404, and the build "
    "cannot notice, because the source is not one of its inputs. Update the link "
    "to the path the page now has, or restore the page under the path the source "
    "names."
)
#: What to do about a link naming a fragment its page does not carry.
MISSING_ANCHOR = (
    "The page renders, but nothing on it carries that id. A glossary anchor is "
    "derived from the term: Sphinx keeps the case and collapses each run of "
    "non-alphanumeric characters to a single hyphen, so renaming a term moves its "
    "anchor and the source goes on naming where it used to be. Copy the id out of "
    "the built page rather than deriving it by hand."
)
```

`NOT_CANONICAL` names no file and is left alone.

- [ ] **Step 8: Run the whole module**

```bash
pixi run --frozen tests tests/test_documentation_links.py -v
```

Expected: 22 passed.

- [ ] **Step 9: Prove the machinery is guarded**

Three mutations, each run against the whole module, each expected to fail exactly the tests
named and no others. Restore after each.

1. In `main()`, set `tagged = False` unconditionally →
   `test_a_failure_names_its_source` fails.
2. In `plural()`, `return f"{noun}s"` unconditionally →
   `test_a_single_page_is_singular` fails.
3. In `main()`, replace `sources = named or [...]` with
   `sources = named or [("README.md", repo / "README.md")]` →
   `test_the_defaults_come_from_sources` fails.

- [ ] **Step 10: Lint and commit**

```bash
pixi run --frozen lint
pixi run --frozen bash -c 'git add -A && git commit -m "Check a list of documentation-link sources rather than the README alone"'
```

---

### Task 4: Add the changelog script, and record the rule

**Files:**
- Modify: `.github/scripts/check_documentation_links.py` (`SOURCES`)
- Modify: `docs/src/developer/docs-style.rst:156-193`
- Create: `changelog/<PR>.internal.rst`

**Interfaces:**
- Consumes: `SOURCES` (Task 3), and the quote-terminated `DOCS` (Task 2) — without which
  this task's one-line change fails the build.
- Produces: nothing later depends on.

- [ ] **Step 1: Add the source**

In `.github/scripts/check_documentation_links.py`:

```python
SOURCES = ("README.md", ".github/scripts/changelog.py")
```

`.github/scripts/changelog.py:31` holds
`URL = "https://tephpy.readthedocs.io/en/latest/developer/docs-style.html"`, which is the
page a contributor is sent to when their changelog fragment fails. Its other URL constant,
`PULL`, points at GitHub and is not a documentation host, so `DOCS` never sees it.

- [ ] **Step 2: Verify against a real build**

```bash
pixi run --frozen docs
pixi run --frozen --environment docs python .github/scripts/check_documentation_links.py docs/_build/html
```

Expected: exit 0, and a line reading
`Documentation links ok: 9 checked across 2 sources, 7 naming an anchor, across 3 pages`.
Those are the README's eight canonical URLs — seven glossary terms and the specifications
index, the Read the Docs badge being passed over for naming no page — plus this task's one.
If the numbers differ because the README has moved on, what must still hold is that the
source count is 2, that the checked count is one more than the README alone reports, and
that the page count includes `developer/docs-style.html`. If the run reports
`developer/docs-style.html` as a non-canonical URL, Task 2's fix is missing or reverted.

- [ ] **Step 3: Generalise the docs-style section**

Replace `docs/src/developer/docs-style.rst:156-193` — the label, the title and the whole
section — with:

```rst
.. _documentation-links:

Documentation Links
-------------------

A few tracked files link into the documentation by absolute URL, because they are
outside the Sphinx project and have no role to write instead: ``README.md``, the
repository's landing page, and a script that sends a contributor to the page
explaining why it failed them. Such a link is invisible to everything that checks
the rest — ``nitpicky`` sees only the references the build resolved.

Write the URL as ``https://tephpy.readthedocs.io/en/latest/<page>.html``,
optionally with a fragment, and in no other form. A per-pull-request preview host
(``tephpy--<pr>.org.readthedocs.build``) is where a documentation change is
verified rather than where a link belongs — Read the Docs deletes the preview when
the pull request closes — and ``latest`` is the only version published, so
``en/stable`` and a path that drops the version alike resolve nowhere.

In ``README.md``, write the link as a Markdown reference — ``[CAPE][cape]`` in the
prose, with the target defined in the block at the foot of the file — so the prose
stays readable and each URL is stated once:

.. code-block:: markdown

    [cape]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-CAPE

Link the *first* mention of a glossary term in the README and no more, as on a
documentation page. Take the fragment from the built page rather than deriving it:
a glossary anchor is ``term-`` followed by the term with its case preserved and
each run of non-alphanumeric characters collapsed to a single hyphen, so ``CAPE``
gives ``term-CAPE`` and ``Normand's point`` gives ``term-Normand-s-point``. Label
the reference in lower case — Markdown labels are case-insensitive, and a lowercase
label is hard to mistake for the fragment, which is not.

The documentation build checks these links. ``check_documentation_links.py`` reads
each URL out of every file named in its ``SOURCES`` constant and looks it up in the
HTML just built, failing when the URL is written some other way, when the page is
absent, or when the fragment names no ``id``. Renaming a glossary term or moving a
page therefore fails the build, rather than leaving a link pointing into a 404 that
nobody notices.

A new file that writes such a URL is checked only once it is added to ``SOURCES``;
the gate reads that list and not the repository, so that a URL quoted in a test
fixture or frozen into an implementation plan is left alone. A file that stops
carrying a documentation link fails the gate rather than dropping out of it in
silence, so removing the last link means removing the entry too.
```

Nothing in the documentation cross-references the old ``landing-page-links`` label —
confirm that before committing:

```bash
grep -rn 'landing-page-links\|Landing Page Links' .github/ src/ tests/ README.md \
  changelog/ docs/src --exclude-dir=plans
```

Expected: no output.

- [ ] **Step 4: Build the documentation clean and check the section renders**

```bash
pixi run --frozen docs
```

Expected: no warnings about an undefined label or a duplicate one, and
`docs/_build/html/developer/docs-style.html` carrying `id="documentation-links"`:

```bash
grep -c 'id="documentation-links"' docs/_build/html/developer/docs-style.html
```

Expected: `1`.

- [ ] **Step 5: Write the changelog fragment**

The fragment is named for this branch's pull request number. If the pull request is not
yet open, take the next number:

```bash
gh pr list --state all --limit 1 --json number --jq '.[0].number'
```

Create `changelog/<PR>.internal.rst`:

```rst
The documentation-link gate now checks every file named in its ``SOURCES`` list
rather than ``README.md`` alone, and reads a URL written inside a quoted string
(:issue:`100`) — so ``.github/scripts/changelog.py``, which sends a contributor to
the documentation style guide by absolute URL, fails the build when that page moves
rather than pointing at a 404 nobody notices. The gate is renamed
``check_documentation_links.py`` to match what it now checks. (:user:`claude`)
```

- [ ] **Step 6: Run the full suite and lint**

```bash
pixi run --frozen tests
pixi run --frozen lint
```

Expected: 834 passed (827 at the branch point, plus this plan's 7 new tests), 0 failures;
lint clean.

- [ ] **Step 7: Commit**

```bash
pixi run --frozen bash -c 'git add -A && git commit -m "Check the documentation link in the changelog script"'
```

---

## Verification Checklist

Run once, after Task 4, before opening the pull request.

- [ ] `pixi run --frozen tests` — full suite green.
- [ ] `pixi run --frozen lint` — clean, including `EXE001` on the renamed script.
- [ ] `pixi run --frozen docs` — clean build, no new warnings.
- [ ] `pixi run --frozen --environment docs python .github/scripts/check_documentation_links.py docs/_build/html`
      — exit 0, reporting 2 sources.
- [ ] `git ls-files -s .github/scripts/check_documentation_links.py` begins `100755`.
- [ ] `grep -rn 'check_readme_links\|landing-page-links' .github/ src/ tests/ changelog/
      README.md docs/src --exclude-dir=plans` — no output. The plans keep their references;
      they record what was intended when they were written.
- [ ] A `changelog/<PR>.internal.rst` fragment exists, citing `:issue:`100`` and ending
      ``(:user:`claude`)``.
