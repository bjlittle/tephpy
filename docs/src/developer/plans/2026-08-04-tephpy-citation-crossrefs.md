# Citation Cross-References Implementation Plan

> **Point-in-time record.** This plan captures what was intended before implementation. It
> is not updated afterwards — where the implementation departed from it, the departure is
> recorded in the pull request, and the living design specification in
> [`../specs/`](../specs/) is what describes tephpy as it stands.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn every `spec §…` citation the documentation renders into a link to the
section it names, without editing a single source file.

**Architecture:** A Sphinx transform walks the doctree during the read phase and replaces
each citation in ordinary prose with a `std:ref` cross-reference resolved against the MyST
anchors of docs spec §3.3. Because it operates on nodes rather than on text, it is
independent of the source format — `.py` docstrings, `.rst`, `.md` and `.ipynb` all link
identically. The grammar that decides what a citation is and where it points is extracted
into one stdlib-only module shared with the existing pre-commit gate, so the two cannot
drift apart. A post-build check asserts the converse of that gate: no citation-shaped text
survives outside a link in the built HTML.

**Tech Stack:** Python 3.12+ standard library only for the grammar (`re`, `json`,
`pathlib`, `dataclasses`); Sphinx (`SphinxTransform`, `addnodes.pending_xref`) and docutils
for the extension; pytest; pre-commit; towncrier; pixi. No new runtime or documentation
dependency.

**Spec:** `docs/src/developer/specs/2026-08-03-published-specs-design.md` — cite it as
`docs spec §N`. Docs spec §3.7 *Rendering citations as cross-references* is the authority
for this plan; docs spec §3.2 defines the citation grammar and the bare-`§N` rule; docs
spec §3.3 defines the anchors; docs spec §3.6 defines the input-side gate this extends.

**Issue:** [#85](https://github.com/bjlittle/tephpy/issues/85)

## Global Constraints

- Every new source file carries the BSD copyright header (ruff `CPY001`) — copy it verbatim
  from `.github/scripts/check_citations.py:2-5`.
- ruff runs `select = ["ALL", "D212"]` with `preview = true` and
  `explicit-preview-rules = true`, the numpy docstring convention, line-length 88, and
  `required-imports = ["from __future__ import annotations"]`. Every function needs a
  docstring and full type annotations; `tests/*` is exempt from `ANN*` and `D103`. Let
  `pixi run --frozen lint` fix import ordering rather than hand-sorting it.
- `numpydoc-validation` is scoped to `^src/` and mypy to `files = ["src/tephpy"]`, so
  neither runs over the new files. Write the docstrings to the same standard regardless —
  the house style is the house style.
- Every pixi invocation carries `--frozen`.
- `git commit` must run inside the pixi environment (`pixi run --frozen git commit …`) —
  `pre-commit` is not on the bare PATH.
- `docs/src/_ext/citations.py` must import nothing outside the standard library. The CI
  test matrix (`test-py312`, `test-py313`, `test-py314`) carries no Sphinx, so a test that
  imports Sphinx does not run in CI.
- No file under `src/`, `tests/`, or the specifications changes its citation text. If a
  step would edit a `§`, the step is wrong.
- The docs build runs `--fail-on-warning --keep-going` (`docs/Makefile`); a warning is a
  failure. HTML lands in `docs/_build/html`.
- Re-run the input gate after any change to the grammar:
  `pixi run --frozen python .github/scripts/check_citations.py`

## File Structure

| file | responsibility |
|---|---|
| `docs/src/_ext/citations.py` | **new.** The citation grammar: what a citation is, where it points, and which lines of a file it may appear in. Standard library only, so both consumers can import it. |
| `docs/src/_ext/citation_xrefs.py` | **new.** The Sphinx extension: which doctree nodes are eligible, and how a citation becomes a `pending_xref`. Knows Sphinx; knows no regular expressions. |
| `.github/scripts/check_citations.py` | **modified.** Keeps the corpus enumeration, the anchor audit and the reporting; delegates the grammar. |
| `.github/scripts/check_rendered_citations.py` | **new.** The output gate. Shares nothing with the grammar, by design. |
| `docs/src/conf.py` | **modified.** Puts `_ext` on `sys.path` and loads the extension. |
| `tests/test_citation_grammar.py` | **new.** Exercises the grammar over prose, without Sphinx. |
| `docs/src/developer/docs-style.rst` | **modified.** The contributor-facing rule. |

The split between the two `_ext` modules is what makes the grammar testable in a CI
environment that has no Sphinx. Putting them under `docs/` rather than beside the checker
in `.github/` is a packaging constraint: `MANIFEST.in` prunes `.github` while the rest of
`docs/` ships, so an extension importing from `.github` builds in a checkout and fails from
an sdist.

---

### Task 1: Extract the shared citation grammar

The grammar currently lives inside the pre-commit gate. The transform needs the same
grammar, and two copies would drift (docs spec §3.7). Move it to a module both import.

**Files:**
- Create: `docs/src/_ext/citations.py`
- Modify: `.github/scripts/check_citations.py`
- Modify: `pyproject.toml` (ruff `per-file-ignores`)
- Test: `tests/test_citation_grammar.py`

**Interfaces:**
- Consumes: nothing — this is the first task.
- Produces, all from `docs/src/_ext/citations.py`:
  - `Anchor(path: Path, line: int)` — frozen dataclass, moved verbatim.
  - `Citation(start: int, end: int, text: str, number: str, slug: str | None)` — new frozen
    dataclass. `slug` is `None` when a bare `§N` has no owning document.
  - `read_lines(text: str) -> Iterator[tuple[int, str]]` — moved verbatim.
  - `collect_anchors(specs: Iterable[Path]) -> tuple[dict[str, Anchor], dict[Path, str]]` —
    moved verbatim.
  - `citation_pattern(anchors: Iterable[str]) -> re.Pattern[str]` — moved verbatim.
  - `scan(source: str, pattern: re.Pattern[str], owner: str | None) -> Iterator[Citation]`
    — new; the compound-run logic lifted out of `check_citations`.
  - Module constants `ANCHOR`, `HEADING`, `FENCE`, `SEPARATOR`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_citation_grammar.py`. The `@` stands in for the section sign: this file
sits inside the corpus the gate scans (docs spec §3.6), and a literal one in a fixture would
be a citation from a file that owns no sections. The docstrings cite for real, and stay
literal — the same split `tests/test_citations.py` already makes.

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the shared citation grammar (docs spec §3.7)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
MODULE = REPO / "docs" / "src" / "_ext" / "citations.py"

# As in `test_citations.py`: this file sits inside the corpus the checker reads
# (docs spec §3.6), so the fixtures below build the section sign rather than
# writing it. A literal one would be a citation from a file that owns no
# sections, and the checker would be right to reject it. The docstrings cite for
# real, and stay literal.
SECTION = "\N{SECTION SIGN}"


def cite(text):
    """Read ``@`` in a fixture as a section sign."""
    return text.replace("@", SECTION)


def _load():
    """Import the grammar by path; ``docs/src/_ext`` is not an importable package."""
    spec = importlib.util.spec_from_file_location("citations", MODULE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


citations = _load()

ANCHORS = [
    "spec-3-1",
    "spec-3-2",
    "spec-3-3",
    "spec-7",
    "spec-10",
    "logo-spec-1",
    "docs-spec-3-2",
]
PATTERN = citations.citation_pattern(ANCHORS)


def found(source, owner=None):
    """Return ``(text, slug)`` for each citation the grammar finds."""
    return [(c.text, c.slug) for c in citations.scan(cite(source), PATTERN, owner)]


PROSE = """
Draw the isopleth families (spec @3.2), regenerated rather than ported
from tephi (spec @3.1/@10 item 5).  A bare @7 means this document, and
Spec @3.3 may open a sentence.  See spec @3.2, @7 for the pair.
"""


def test_a_block_of_prose_converts_end_to_end():
    """Every form of docs spec §3.2 at once, read as a specification reads it."""
    assert found(PROSE, owner="docs-spec") == [
        (cite("spec @3.2"), "spec-3-2"),
        (cite("spec @3.1"), "spec-3-1"),
        (cite("@10"), "spec-10"),
        (cite("@7"), "docs-spec-7"),
        (cite("Spec @3.3"), "spec-3-3"),
        (cite("spec @3.2"), "spec-3-2"),
        (cite("@7"), "spec-7"),
    ]


@pytest.mark.parametrize(
    ("source", "owner", "expected"),
    [
        ("spec @3.2", None, [("spec @3.2", "spec-3-2")]),
        ("Spec @3.2", None, [("Spec @3.2", "spec-3-2")]),
        ("logo spec @1", None, [("logo spec @1", "logo-spec-1")]),
        ("docs spec @3.2", None, [("docs spec @3.2", "docs-spec-3-2")]),
        ("spec @3.1/@10", None, [("spec @3.1", "spec-3-1"), ("@10", "spec-10")]),
        ("spec @3.1, @10", None, [("spec @3.1", "spec-3-1"), ("@10", "spec-10")]),
        ("@3.2", "docs-spec", [("@3.2", "docs-spec-3-2")]),
        ("@3.2", None, [("@3.2", None)]),
        ("nonspec @3.2", None, [("@3.2", None)]),
        (
            "spec @3.2.  @7 opens a sentence.",
            None,
            [("spec @3.2", "spec-3-2"), ("@7", None)],
        ),
    ],
)
def test_each_citation_form_resolves(source, owner, expected):
    """One form per case, including the two that docs spec §3.2 makes errors."""
    assert found(source, owner) == [(cite(text), slug) for text, slug in expected]


def test_the_span_indexes_the_source():
    """The transform rewrites by span, so the span must address the citation."""
    source = cite("see spec @3.2 now")
    (citation,) = citations.scan(source, PATTERN, None)
    assert source[citation.start : citation.end] == citation.text
    assert citation.number == "3.2"
```

The two `None`-slug cases are the interesting ones: a bare `§3.2` with no owner, and the
`§7` opening a fresh sentence after `spec §3.2.` — the full stop ends the run, so the
prefix must not carry across it.

- [ ] **Step 2: Run the test to verify it fails**

Run: `pixi run --frozen pytest tests/test_citation_grammar.py -q`
Expected: collection error — `docs/src/_ext/citations.py` does not exist.

- [ ] **Step 3: Create the grammar module**

Create `docs/src/_ext/citations.py`. `ANCHOR`, `HEADING`, `FENCE`, `SEPARATOR`, `Anchor`,
`read_lines`, `collect_anchors` and `citation_pattern` move across from
`.github/scripts/check_citations.py` **verbatim, docstrings and comments included** — this
is a move, not a rewrite. The header:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""The design-specification citation grammar (docs spec §3.2).

One definition of what a citation is, shared by the pre-commit gate of docs spec
§3.6 and the cross-reference transform of docs spec §3.7. Two copies would agree
until one of them was amended, and the disagreement would then be silent in both
directions: the gate would pass text the transform declined to link, or the
transform would link text the gate had never audited.

Nothing here is imported from outside the standard library, so this module runs
in the CI test matrix, which carries no Sphinx.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
```

Then the moved definitions, and after `Anchor` the new dataclass:

```python
@dataclass(frozen=True)
class Citation:
    """One citation, located in the string it was found in.

    Attributes
    ----------
    start, end : int
        The half-open span of the citation, so a caller can rewrite the source
        without searching it a second time and risking a different answer.
    text : str
        The citation exactly as written, e.g. ``spec §3.2`` or a bare ``§10``.
        This is what a link displays.
    number : str
        The section number alone, e.g. ``3.2``.
    slug : str or None
        The anchor the citation names, e.g. ``spec-3-2``. ``None`` when a bare
        ``§N`` was written in a file that owns no sections, which docs spec §3.2
        makes an error rather than a reference to the parent specification.

    """

    start: int
    end: int
    text: str
    number: str
    slug: str | None
```

and, last, the new `scan`:

```python
def scan(
    source: str,
    pattern: re.Pattern[str],
    owner: str | None,
) -> Iterator[Citation]:
    """Yield each citation in ``source``, resolved to the anchor it names.

    A prefix carries only to the end of its run — the comma- or solidus-separated
    compound of docs spec §3.2. Carrying it further would let it cross a sentence
    boundary, so that a bare ``§N`` opening the next sentence inherited the
    namespace of a prefixed citation earlier on rather than falling back to the
    containing document.

    Parameters
    ----------
    source : str
        The text to scan: one line for the gate, one text node for the transform.
    pattern : re.Pattern
        The citation pattern from :func:`citation_pattern`.
    owner : str or None
        The prefix of the document ``source`` was written in, or ``None`` when it
        owns no sections — a docstring, a test, a notebook.

    Yields
    ------
    Citation
        One per citation, in the order written. ``slug`` is ``None`` for a bare
        ``§N`` with no owner; the caller decides whether that is a violation to
        report or a citation to leave alone.

    """
    carried: str | None = None
    end = 0
    for match in pattern.finditer(source):
        joined = carried is not None and SEPARATOR.fullmatch(source[end : match.start()])
        end = match.end()
        if match["prefix"] is not None:
            carried = re.sub(r"\s+", "-", match["prefix"].lower())
            number = match["num"]
        elif joined:
            number = match["bare"]
        elif owner is not None:
            carried, number = owner, match["bare"]
        else:
            carried = None
            yield Citation(
                match.start(), match.end(), match.group(0), match["bare"], None
            )
            continue
        yield Citation(
            match.start(),
            match.end(),
            match.group(0),
            number,
            f"{carried}-{number.replace('.', '-')}",
        )
```

Task 2 adds `import json`; leave it out here so lint stays green at this commit.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pixi run --frozen pytest tests/test_citation_grammar.py -q`
Expected: PASS, 12 tests.

- [ ] **Step 5: Repoint the gate at the shared module**

In `.github/scripts/check_citations.py`, delete the eight moved definitions and load the
shared module by path — `.github` is not an importable package and neither is
`docs/src/_ext`, so the `spec_from_file_location` idiom `tests/test_citations.py` already
uses applies here too.

Adjust the imports: add `import importlib.util`, and drop `import re` and the
`Iterator` half of the `TYPE_CHECKING` block — both were used only by the definitions that
just left. Keep `dataclass` (`Violation` stays) and `Iterable` (`check_citations` and
`check_anchors` still annotate with it). Then replace the constant block:

```python
REPO = Path(__file__).resolve().parents[2]
SPECS = REPO / "docs" / "src" / "developer" / "specs"
GRAMMAR = REPO / "docs" / "src" / "_ext" / "citations.py"
EXCLUDED = ("docs/src/developer/plans/",)


def _grammar():
    """Load the citation grammar shared with the docs build (docs spec §3.7).

    It lives under ``docs/`` rather than beside this script because ``MANIFEST.in``
    prunes ``.github`` while the rest of ``docs/`` ships, and the Sphinx extension
    that shares it must import from a path an sdist carries. This script only ever
    runs in a checkout, so it is the one that reaches across.

    Returns
    -------
    module
        The loaded ``citations`` module.

    """
    spec = importlib.util.spec_from_file_location("citations", GRAMMAR)
    if spec is None or spec.loader is None:
        print(f"cannot load the citation grammar from {display(GRAMMAR)}")
        raise SystemExit(1)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


citations = _grammar()

ANCHOR = citations.ANCHOR
HEADING = citations.HEADING
Anchor = citations.Anchor
read_lines = citations.read_lines
collect_anchors = citations.collect_anchors
citation_pattern = citations.citation_pattern
```

`_grammar` calls `display`, so place both after that function's definition rather than in
the constant block at the top of the file.

Re-binding the names at module scope keeps `check_anchors`, `main` and every test in
`tests/test_citations.py` working untouched. Then rewrite the inner loop of
`check_citations` to call `scan`, preserving both message strings character for character:

```python
        for number, line in lines:
            for citation in citations.scan(line, pattern, own):
                if citation.slug is None:
                    violations.append(
                        Violation(
                            path,
                            number,
                            f"'§{citation.number}' has no prefix; "
                            f"write 'spec §{citation.number}'",
                        )
                    )
                elif citation.slug not in anchors:
                    violations.append(
                        Violation(
                            path,
                            number,
                            f"'§{citation.number}' → no anchor '#{citation.slug}'",
                        )
                    )
```

- [ ] **Step 6: Verify the gate is unchanged in behaviour**

Run: `pixi run --frozen python .github/scripts/check_citations.py`
Expected: `citations ok: 55 anchors, 160 files (docs spec §3.6)` — the same line as before
the change, to the digit. A different count means the move changed the grammar.

Run: `pixi run --frozen pytest tests/test_citations.py -q`
Expected: PASS. These tests were not modified; that is the point of re-binding the names.

- [ ] **Step 7: Add the ruff ignore**

`docs/src/_ext/` has no `__init__.py` — a package there would stop Sphinx resolving
`citation_xrefs` as a top-level module — so ruff's implicit-namespace rule fires. Add to
`[tool.ruff.lint.per-file-ignores]` in `pyproject.toml`, immediately after the
`"docs/src/conf.py"` entry:

```toml
# The Sphinx extension directory is a ``sys.path`` entry at build time, not a
# package: an ``__init__.py`` would stop Sphinx resolving ``citation_xrefs`` by
# top-level module name (docs spec §3.7).
"docs/src/_ext/*.py" = ["INP001"]
```

- [ ] **Step 8: Run lint**

Run: `pixi run --frozen lint`
Expected: all hooks pass. If ruff reports `I001`, let it fix the import order.

- [ ] **Step 9: Commit**

```bash
git add docs/src/_ext/citations.py .github/scripts/check_citations.py \
        pyproject.toml tests/test_citation_grammar.py
pixi run --frozen git commit -m "Extract the citation grammar into a shared module"
```

---

### Task 2: Read notebook markdown cells with fences skipped

docs spec §3.6 skips fenced code blocks because docs spec §3.3 illustrates the anchor rule inside a
fence. The gate keys that on the `.md` suffix, so the first notebook to document the
convention would be scanned through its fences and rejected. A fence is a property of
markdown, not of a file extension.

There is no notebook in the repository yet — `git ls-files '*.ipynb'` returns nothing — so
the tests below are the whole exercise. That is deliberate: the gap closes before the first
notebook lands on it, not after.

**Files:**
- Modify: `docs/src/_ext/citations.py`
- Modify: `.github/scripts/check_citations.py`
- Test: `tests/test_citation_grammar.py`

**Interfaces:**
- Consumes: `read_lines` from Task 1.
- Produces:
  - `notebook_lines(text: str) -> Iterator[tuple[int, str]]`
  - `source_lines(path: Path, text: str) -> Iterator[tuple[int, str]]`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_citation_grammar.py`:

```python
NOTEBOOK = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "Prose citing spec @3.2.\n",
                "\n",
                "```python\n",
                "# spec @9999 inside a fence\n",
                "```\n",
            ],
        },
        {
            "cell_type": "code",
            "metadata": {},
            "execution_count": None,
            "outputs": [
                {
                    "name": "stdout",
                    "output_type": "stream",
                    "text": ["generated output naming spec @8888\n"],
                }
            ],
            "source": ["# code comment citing spec @3.1\n", "print('hi')"],
        },
        {"cell_type": "raw", "metadata": {}, "source": ["raw cell spec @7777\n"]},
    ],
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 5,
}


def notebook(tmp_path):
    """Write the fixture notebook the way ``nbformat`` would, and return its path."""
    path = tmp_path / "probe.ipynb"
    path.write_text(cite(json.dumps(NOTEBOOK, indent=1)), encoding="utf-8")
    return path


def read(path):
    """Return the lines the citation rule governs, joined."""
    text = path.read_text(encoding="utf-8")
    return "\n".join(line for _number, line in citations.source_lines(path, text))


def test_a_notebook_is_read_as_markdown_and_as_code(tmp_path):
    """A notebook is read the way each of its cells is written (docs spec §3.6)."""
    body = read(notebook(tmp_path))
    assert cite("spec @3.2") in body  # markdown prose is read
    assert cite("spec @3.1") in body  # a code cell is read as a .py is


def test_a_notebook_hides_fences_output_and_raw_cells(tmp_path):
    """A fence is markdown; output and raw cells are not authored prose."""
    body = read(notebook(tmp_path))
    assert cite("@9999") not in body  # a fence inside a markdown cell
    assert cite("@8888") not in body  # generated output
    assert cite("@7777") not in body  # a raw cell renders as nothing


def test_a_notebook_citation_reports_its_own_file_line(tmp_path):
    """A violation must point where an editor will open the file."""
    path = notebook(tmp_path)
    raw = path.read_text(encoding="utf-8").splitlines()
    located = [
        number
        for number, line in citations.source_lines(path, "\n".join(raw))
        if cite("@3.2") in line
    ]
    assert len(located) == 1
    assert cite("@3.2") in raw[located[0] - 1]


def test_markdown_and_plain_files_are_unaffected(tmp_path):
    """The suffix branch is new; the two behaviours it subsumes are not."""
    md = tmp_path / "probe.md"
    md.write_text(cite("prose spec @3.2\n\n```\nspec @9999\n```\n"), encoding="utf-8")
    assert cite("@3.2") in read(md)
    assert cite("@9999") not in read(md)

    py = tmp_path / "probe.py"
    py.write_text(cite('"""spec @3.2."""\n'), encoding="utf-8")
    assert cite("@3.2") in read(py)


def test_a_malformed_notebook_is_read_as_nothing(tmp_path):
    """An unparsable notebook is a problem for the build, not for this gate."""
    path = tmp_path / "broken.ipynb"
    path.write_text("{not json", encoding="utf-8")
    assert read(path) == ""
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pixi run --frozen pytest tests/test_citation_grammar.py -k "notebook or unaffected" -q`
Expected: FAIL — `AttributeError: module 'citations' has no attribute 'source_lines'`.

- [ ] **Step 3: Implement the notebook reader**

Add `import json` to `docs/src/_ext/citations.py` (Task 1 deferred it), then add both
functions:

```python
def notebook_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield the authored lines of a notebook, with markdown fences skipped.

    A notebook is read the way its cells are written (docs spec §3.6): markdown
    cells as markdown, so a fenced illustration of the anchor rule is skipped
    exactly as it is in a ``.md`` file; code cells as Python is read, so a
    citation in a comment is still checked; and outputs not at all, being
    generated rather than authored. A raw cell renders as nothing and is read as
    nothing.

    Line numbers are numbers in the ``.ipynb`` file itself, so a violation points
    where an editor will open. Each source line is located by searching forward
    for its JSON-encoded form, which ``nbformat`` writes one to a physical line.
    The cursor only ever moves forward, so a line repeated across cells resolves
    to its own occurrence; a line that cannot be located at all is reported
    against the last one that could, rather than silently ending the scan.

    Parameters
    ----------
    text : str
        The notebook file contents.

    Yields
    ------
    tuple of (int, str)
        The 1-indexed line number within the file, and the authored line.

    """
    try:
        notebook = json.loads(text)
    except json.JSONDecodeError:
        return
    if not isinstance(notebook, dict):
        return
    raw = text.splitlines()
    cursor = 0
    for cell in notebook.get("cells", []):
        kind = cell.get("cell_type")
        if kind not in {"markdown", "code"}:
            continue
        source = cell.get("source", "")
        lines = (
            source.splitlines()
            if isinstance(source, str)
            else [line.rstrip("\n") for line in source]
        )
        located: list[tuple[int, str]] = []
        for line in lines:
            encoded = json.dumps(line)[1:-1]
            at = cursor
            while at < len(raw) and encoded not in raw[at]:
                at += 1
            if at < len(raw):
                cursor = at + 1
                located.append((at + 1, line))
            else:
                located.append((max(cursor, 1), line))
        if kind == "markdown":
            body = "\n".join(line for _number, line in located)
            for number, line in read_lines(body):
                yield located[number - 1][0], line
        else:
            yield from located


def source_lines(path: Path, text: str) -> Iterator[tuple[int, str]]:
    """Yield the lines of ``text`` that the citation rule governs.

    Parameters
    ----------
    path : Path
        The file the text came from; only its suffix is read.
    text : str
        The file contents.

    Yields
    ------
    tuple of (int, str)
        The 1-indexed line number, and the line.

    """
    if path.suffix == ".md":
        yield from read_lines(text)
    elif path.suffix == ".ipynb":
        yield from notebook_lines(text)
    else:
        yield from enumerate(text.splitlines(), start=1)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pixi run --frozen pytest tests/test_citation_grammar.py -q`
Expected: PASS, 17 tests.

- [ ] **Step 5: Use it in the gate**

In `.github/scripts/check_citations.py`, `check_citations` currently chooses its line source
with a suffix branch of its own. Delete that branch and call the shared helper:

```python
        text = path.read_text(encoding="utf-8")
        for number, line in citations.source_lines(path, text):
```

- [ ] **Step 6: Verify the gate is still clean**

Run: `pixi run --frozen python .github/scripts/check_citations.py`
Expected: `citations ok: 55 anchors, 160 files (docs spec §3.6)`

Run: `pixi run --frozen pytest tests/test_citations.py tests/test_citation_grammar.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add docs/src/_ext/citations.py .github/scripts/check_citations.py \
        tests/test_citation_grammar.py
pixi run --frozen git commit -m "Read notebook markdown cells with fences skipped"
```

---

### Task 3: The cross-reference transform

**Files:**
- Create: `docs/src/_ext/citation_xrefs.py`
- Modify: `docs/src/conf.py`

**Interfaces:**
- Consumes: `collect_anchors`, `citation_pattern` and `scan` from Task 1.
- Produces: an extension loadable as `citation_xrefs`, whose `setup(app)` returns
  `{"version": …, "parallel_read_safe": True, "parallel_write_safe": True}`.

- [ ] **Step 1: Write the extension**

Create `docs/src/_ext/citation_xrefs.py`. The registry is a module global rather than an
attribute on the application because `builder-inited` fires before Sphinx forks its
parallel readers, so the children inherit a populated one.

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Render design-specification citations as cross-references (docs spec §3.7).

The transform runs on the doctree, after parsing, so it never sees a source
format -- only nodes. A citation therefore links identically from a docstring, a
``.rst`` page, a ``.md`` specification and a notebook markdown cell, and no source
is edited to make it so: ``spec §3.2`` in a docstring stays the characters it has
always been.

What a citation is, and which anchor it names, is not decided here. That is
:mod:`citations`, shared with the pre-commit gate of docs spec §3.6.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import citations
from docutils import nodes
from sphinx import addnodes
from sphinx.ext.autosummary import autosummary_table
from sphinx.transforms import SphinxTransform

if TYPE_CHECKING:
    import re

    from sphinx.application import Sphinx

#: Text inside any of these stays plain (docs spec §3.7). ``reference`` and
#: ``pending_xref`` are on the list because a citation appearing in link text
#: would otherwise nest one anchor inside another, which is invalid HTML.
SKIP = (
    nodes.literal,
    nodes.literal_block,
    nodes.comment,
    nodes.raw,
    nodes.reference,
    addnodes.desc_signature,
    addnodes.pending_xref,
)

#: Derived once per build from the anchors on disk, and read by every transform.
#: Populated by :func:`_build_registry` on ``builder-inited``, which runs before
#: Sphinx forks its parallel readers, so each child inherits the pair.
PATTERN: re.Pattern[str] | None = None
OWNERS: dict[str, str] = {}


class CitationTransform(SphinxTransform):
    """Replace each citation in ordinary prose with a reference to its anchor."""

    default_priority = 400

    def apply(self, **kwargs: object) -> None:  # noqa: ARG002
        """Rewrite every eligible text node in the document."""
        if PATTERN is None:
            return
        owner = OWNERS.get(self.env.docname)
        for text in list(self.document.findall(nodes.Text)):
            if _skipped(text):
                continue
            replacement = _convert(str(text), owner, self.env.docname)
            if replacement is not None:
                text.parent.replace(text, replacement)


def _skipped(node: nodes.Node) -> bool:
    """Report whether ``node`` sits inside something that must stay plain.

    Parameters
    ----------
    node : docutils.nodes.Node
        The text node under consideration.

    Returns
    -------
    bool
        Whether to leave the node alone.

    """
    parent = node.parent
    while parent is not None:
        # ``autosummary_table`` subclasses ``comment`` but is a rendered table,
        # and the autoapi module summary -- 17 citations -- lives inside one.
        if not isinstance(parent, autosummary_table) and isinstance(parent, SKIP):
            return True
        parent = parent.parent
    return False


def _convert(source: str, owner: str | None, docname: str) -> list[nodes.Node] | None:
    """Split ``source`` into runs of text and the references between them.

    Parameters
    ----------
    source : str
        The text node's contents.
    owner : str or None
        The citation prefix of the document, or ``None`` if it owns no sections.
    docname : str
        The document being read, recorded on each reference for its warnings.

    Returns
    -------
    list of docutils.nodes.Node or None
        The replacement nodes, or ``None`` when nothing here is a citation.

    """
    out: list[nodes.Node] = []
    cursor = 0
    for citation in citations.scan(source, PATTERN, owner):
        if citation.slug is None:
            # A bare section number with nothing to be relative to. The gate of
            # docs spec §3.6 rejects it on commit; here, leave it as written.
            continue
        out.append(nodes.Text(source[cursor : citation.start]))
        out.append(_xref(docname, citation.slug, citation.text))
        cursor = citation.end
    if not out:
        return None
    out.append(nodes.Text(source[cursor:]))
    return out


def _xref(docname: str, slug: str, shown: str) -> addnodes.pending_xref:
    """Build a ``std:ref`` cross-reference to ``slug``, displaying ``shown``.

    Parameters
    ----------
    docname : str
        The referring document.
    slug : str
        The MyST anchor of docs spec §3.3, e.g. ``spec-3-2``.
    shown : str
        The citation as written, which is what the link displays.

    Returns
    -------
    sphinx.addnodes.pending_xref
        Resolved later by the standard domain.

    Notes
    -----
    ``refwarn`` is set rather than the anchor being checked here, so that a
    citation which stops resolving fails the build through the Makefile's
    ``--fail-on-warning`` even when the pre-commit gate was bypassed.

    """
    inner = nodes.inline(shown, shown, classes=["std", "std-ref"])
    return addnodes.pending_xref(
        "",
        inner,
        refdoc=docname,
        refdomain="std",
        reftype="ref",
        reftarget=slug,
        refexplicit=True,
        refwarn=True,
    )


def _build_registry(app: Sphinx) -> None:
    """Derive the citation pattern and the owner map from the anchors on disk.

    The prefixes are nowhere declared (docs spec §3.6): adding a specification
    adds its prefix, and no list needs updating to match.

    Parameters
    ----------
    app : Sphinx
        The application, read for its source directory.

    """
    global PATTERN  # noqa: PLW0603
    root = Path(app.srcdir)
    specs = sorted((root / "developer" / "specs").glob("*.md"))
    anchors, owners = citations.collect_anchors(specs)
    PATTERN = citations.citation_pattern(anchors)
    OWNERS.clear()
    OWNERS.update(
        {
            path.relative_to(root).with_suffix("").as_posix(): prefix
            for path, prefix in owners.items()
        }
    )


def setup(app: Sphinx) -> dict[str, object]:
    """Register the transform.

    Parameters
    ----------
    app : Sphinx
        The application.

    Returns
    -------
    dict
        The extension metadata.

    """
    app.connect("builder-inited", _build_registry)
    app.add_transform(CitationTransform)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
```

- [ ] **Step 2: Wire it into the build**

In `docs/src/conf.py`, extend the import block (currently lines 7–9) with the path insert:

```python
from __future__ import annotations

from importlib.metadata import version as _dist_version
from pathlib import Path
import sys

# ``docs/src/_ext`` holds the citation cross-reference extension (docs spec §3.7)
# and the grammar it shares with the pre-commit gate of docs spec §3.6. It is a
# ``sys.path`` entry rather than a package: Sphinx resolves an extension by
# top-level module name.
sys.path.insert(0, str(Path(__file__).parent / "_ext"))
```

Then add the extension to `extensions`, first in the list so it loads before autoapi:

```python
extensions = [
    "citation_xrefs",
    "autoapi.extension",
    ...
]
```

- [ ] **Step 3: Build the documentation**

Run:

```bash
pixi run --frozen --environment docs make -C docs clean
pixi run --frozen --environment docs make -C docs html
```

Expected: `build succeeded.` with no warnings — `SPHINXOPTS` carries `--fail-on-warning`.

A warning of the form `undefined label: 'spec-N'` means a citation names a section that does
not exist. Fix the citation, not the transform: that the build *can* report it is
`refwarn=True` working as designed.

- [ ] **Step 4: Verify the links landed**

Run:

```bash
pixi run --frozen python - <<'PY'
import pathlib, re
root = pathlib.Path("docs/_build/html")
total = sum(
    len(re.findall(r'<span class="std std-ref">[^<]*§', page.read_text()))
    for page in root.rglob("*.html")
    if "_modules" not in page.as_posix()
)
print("citation links:", total)
PY
```

Expected: `citation links: 297`, the figure docs spec §6 records. A materially different
number means the transform is reaching more or less than it should — Task 4 will say which
pages. In particular, if the count is near 280 the `autosummary_table` carve-out in
`_skipped` is not working and the autoapi module summaries have been skipped as comments.

- [ ] **Step 5: Commit**

```bash
git add docs/src/_ext/citation_xrefs.py docs/src/conf.py
pixi run --frozen git commit -m "Render specification citations as cross-references"
```

---

### Task 4: The post-build gate

docs spec §3.6 asserts every citation in the source resolves to an anchor. This asserts the
converse, on the output. It deliberately shares no code with the grammar: a check that
asked the grammar what to look for would go blind in the same instant the grammar did, and
would then pass by finding nothing.

**Files:**
- Create: `.github/scripts/check_rendered_citations.py`
- Modify: `.github/workflows/ci-docs.yml`

**Interfaces:**
- Consumes: the HTML built in Task 3.
- Produces: a script taking the HTML root as `argv[1]`, exiting 0 or 1.

- [ ] **Step 1: Write the checker**

Create `.github/scripts/check_rendered_citations.py`:

```python
#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that every rendered citation became a link (docs spec §3.7).

This is the converse of the pre-commit gate of docs spec §3.6. That one asserts
every citation in the *source* resolves to an anchor; this one asserts every
citation in the *output* became a link. Each is blind where the other sees: the
input gate cannot tell whether the extension ran at all, and the output gate
cannot tell a right target from a wrong one.

The pattern below is deliberately looser than the shared grammar, and shares no
code with it. A check that asked the grammar what to look for would go blind in
the same instant the grammar did, and pass by finding nothing.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import sys

CITATION = re.compile(r"§\s*\d+(?:\.\d+)*")
#: Text inside these is never linked, by design (docs spec §3.7).
EXEMPT = {"code", "pre", "script", "style"}
#: ``viewcode`` renders verbatim source; its section signs are Python, not prose.
SKIP_PAGES = ("_modules/",)
#: Elements that never close, so must never be pushed onto the stack.
VOID = {"br", "col", "hr", "img", "input", "link", "meta", "source", "wbr"}


class Scan(HTMLParser):
    """Collect every citation in one page, classified by where it sits."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.linked = 0
        self.exempt = 0
        self.bare: list[str] = []
        self.nested: list[str] = []

    # The unused overrides take underscored names so ruff reads them as
    # deliberate: ``HTMLParser`` calls these positionally, so the names are ours.
    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        """Push ``tag`` unless it is void."""
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, _tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        """Ignore a self-closing tag; it encloses nothing."""

    def handle_endtag(self, tag: str) -> None:
        """Pop back to ``tag``, tolerating elements left unclosed."""
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass

    def handle_data(self, data: str) -> None:
        """Classify each citation in a run of text."""
        hits = CITATION.findall(data)
        if not hits:
            return
        anchors = self.stack.count("a")
        if any(tag in EXEMPT for tag in self.stack):
            self.exempt += len(hits)
        elif anchors > 1:
            self.nested.extend(hits)
        elif anchors == 1:
            self.linked += len(hits)
        else:
            self.bare.extend(hits)


def main() -> int:
    """Scan the built HTML.

    Returns
    -------
    int
        ``0`` when every rendered citation is a link, ``1`` otherwise.

    """
    if len(sys.argv) != 2:
        print("usage: check_rendered_citations.py <html-root>")
        return 1
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"no such directory: {root}")
        return 1

    linked = exempt = pages = 0
    unlinked: dict[str, list[str]] = {}
    nested: dict[str, list[str]] = {}
    for page in sorted(root.rglob("*.html")):
        relative = page.relative_to(root).as_posix()
        if relative.startswith(SKIP_PAGES):
            continue
        pages += 1
        scan = Scan()
        scan.feed(page.read_text(encoding="utf-8"))
        linked += scan.linked
        exempt += scan.exempt
        if scan.bare:
            unlinked[relative] = scan.bare
        if scan.nested:
            nested[relative] = scan.nested

    if not pages:
        print(f"no HTML pages under {root}")
        return 1
    if not linked:
        print(
            f"no citation became a link across {pages} pages -- is 'citation_xrefs' "
            "still first in conf.py's extensions?"
        )
        return 1
    if not unlinked and not nested:
        print(
            f"rendered citations ok: {linked} linked, {exempt} literal, "
            f"{pages} pages (docs spec §3.7)"
        )
        return 0
    for heading, offenders in (("Unlinked", unlinked), ("Nested in a link", nested)):
        if offenders:
            total = sum(len(hits) for hits in offenders.values())
            print(f"{heading} ({total}):")
            for relative, hits in sorted(offenders.items()):
                print(f"  {relative}: {', '.join(hits[:8])}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

The `if not linked` branch is the one no fixture test can supply: it catches the extension
being dropped from `conf.py`, or a future Sphinx breaking the transform outright. Without
it, a build that linked nothing would report nothing unlinked either — a citation that is
never recognised is never counted — and the check would pass while doing nothing at all.

- [ ] **Step 2: Verify it passes on a good build**

Run: `pixi run --frozen python .github/scripts/check_rendered_citations.py docs/_build/html`
Expected: `rendered citations ok: 297 linked, 19 literal, <N> pages (docs spec §3.7)`

- [ ] **Step 3: Prove the gate is not vacuous**

Comment out `"citation_xrefs",` in `docs/src/conf.py`, then:

```bash
pixi run --frozen --environment docs make -C docs clean
pixi run --frozen --environment docs make -C docs html
pixi run --frozen python .github/scripts/check_rendered_citations.py docs/_build/html
```

Expected: exit 1, reporting `no citation became a link across <N> pages`. Restore the line,
rebuild, and confirm the check passes again. **Do not skip this step** — a gate that has
never been seen to fail has not been shown to be a gate.

- [ ] **Step 4: Wire it into CI**

`.github/workflows/ci-docs.yml` uses bare `- run:` steps with no `name:`. Match that, and
add the check immediately after the build step:

```yaml
      - run: pixi run --frozen --environment docs make -C docs html
      - run: >
          pixi run --frozen --environment docs
          python .github/scripts/check_rendered_citations.py docs/_build/html
```

- [ ] **Step 5: Commit**

```bash
git add .github/scripts/check_rendered_citations.py .github/workflows/ci-docs.yml
pixi run --frozen git commit -m "Assert every rendered citation became a link"
```

---

### Task 5: The contributor-facing rule and the changelog

`docs/src/developer/docs-style.rst` states the house rule for every other kind of
cross-reference and says nothing about citations — the gap that let each of the seven
`design: open` issues foot the wrong document.

**Files:**
- Modify: `docs/src/developer/docs-style.rst`
- Create: `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

- [ ] **Step 1: Add the citation rule**

Insert a new section in `docs/src/developer/docs-style.rst` after *Cross-References* — which
ends `…add a numpydoc_xref_aliases entry or write the full dotted name.` — and before
*Attribute Documentation*. The title is CMOS headline style, and the anchor matches the
`.. _cross-references:` target on its neighbour.

```rst
.. _specification-citations:

Specification Citations
-----------------------

Cite a design specification as plain text — ``spec §3.2``, ``logo spec §1``,
``docs spec §3.6`` — and never as a hand-written role. The build turns each one
into a link to the section it names, so writing the role yourself is not an
improvement but a hazard: a role carries a second string that can disagree with
its display text, and

.. code-block:: rst

   :ref:`spec §3.2 <logo-spec-3-2>`

has the right text against the wrong document while resolving perfectly cleanly,
so neither the citation checker nor a nitpicky build has anything to object to.
Writing the citation once means the text and the target cannot disagree.

The prefix names the document and is load-bearing. A bare ``§N`` means *this*
document's §N, which makes it safe inside a specification and an error anywhere
else — a docstring owns no sections. Where several sections are cited together,
the prefix carries across the run, so ``spec §3.3, §10`` and ``spec §3.1/§10``
each name two sections of the parent specification; the run ends at any other
punctuation, so a bare ``§N`` opening the next sentence falls back to the
containing document rather than inheriting.

A pre-commit hook checks that every citation names an anchor that exists, and the
documentation build checks that every rendered citation became a link. Both are
specified in the published specifications design: docs spec §3.6 covers the hook,
and docs spec §3.7 covers the build.
```

Keep each citation whole on one line. The checker reads line by line, so a prefix
left on one line with its ``§N`` wrapped onto the next is read as a bare citation, and
rejected.

- [ ] **Step 2: Verify the input gate accepts the new prose**

Run: `pixi run --frozen python .github/scripts/check_citations.py`
Expected: `citations ok: 55 anchors, 160 files (docs spec §3.6)`. This page owns no
sections, so every citation in it must carry a prefix — which is why the closing sentence
writes `docs spec §3.6 and docs spec §3.7` rather than leaning on the run: `and` is not a
run separator. If the gate reports `'§3.7' has no prefix`, that sentence lost its second
prefix.

- [ ] **Step 3: Verify it builds and renders**

```bash
pixi run --frozen --environment docs make -C docs clean
pixi run --frozen --environment docs make -C docs html
pixi run --frozen python .github/scripts/check_rendered_citations.py docs/_build/html
```

Expected: `build succeeded.`, then the rendered-citation check passes with a `linked` count
slightly above what Task 4 recorded — this section adds citations of its own. The `:ref:`
inside the `code-block` must land in the `literal` tally rather than `linked`; it is an
illustration of the wrong way, and a working link there would be absurd.

- [ ] **Step 4: Add the changelog fragment**

Open the pull request first to learn its number, then create
`changelog/<PR>.documentation.rst`:

```rst
Design specification citations such as ``spec §3.2`` now render as links to the
section they name, throughout the documentation and the API reference. The
citations themselves are unchanged: a Sphinx transform resolves them while the
doctree is built, so nothing under ``src/`` was edited and the written form is
still the plain text it always was. A companion check asserts that every rendered
citation became a link — the converse of the existing citation-integrity hook.
(:issue:`85`, :user:`bjlittle`)
```

- [ ] **Step 5: Verify the fragment renders**

```bash
pixi run --frozen --environment docs make -C docs clean
pixi run --frozen --environment docs make -C docs html
grep -rl 'issues/85' docs/_build/html
```

Expected: `build succeeded.`, and the changelog page listed — proof that `:issue:` and
`:user:` resolved through `extlinks`.

- [ ] **Step 6: Run everything**

```bash
pixi run --frozen lint
pixi run --frozen tests
pixi run --frozen python .github/scripts/check_citations.py
pixi run --frozen --environment docs make -C docs clean
pixi run --frozen --environment docs make -C docs html
pixi run --frozen python .github/scripts/check_rendered_citations.py docs/_build/html
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add docs/src/developer/docs-style.rst changelog/
pixi run --frozen git commit -m "Document the citation rule and add the changelog fragment"
```

---

## Verification

Beyond the per-task steps, the change is done when:

- `pixi run --frozen python .github/scripts/check_citations.py` exits 0, reporting 55
  anchors over 160 files.
- A clean docs build succeeds under `--fail-on-warning`, and roughly 297 citations render
  as links.
- `check_rendered_citations.py` reports zero unlinked and zero nested.
- Commenting `citation_xrefs` out of `conf.py` makes that check fail (Task 4, Step 3).
- `git diff --stat main -- src tests/plotting tests/io tests/calc` is empty — no source
  file's citation text was touched.
- `pixi run --frozen tests` passes in the CI matrix, which has no Sphinx: every new test
  imports only the stdlib grammar module.

One claim of docs spec §3.7 is **not** re-verified here: that `.md` and `.ipynb` sources
link identically. It was established during design with throwaway probe fixtures across
every markdown construct and notebook cell type, and it follows from the transform running
on the doctree rather than on syntax. The repository has no notebook to verify it against
today, and permanent probe pages would publish fixtures on the site to prove a property
the architecture already guarantees. The day a notebook lands, the build verifies it.
