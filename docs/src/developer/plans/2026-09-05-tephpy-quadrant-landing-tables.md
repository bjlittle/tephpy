# Quadrant Landing Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The tutorials, how-to and explanation landing pages stop summarising their quadrant page by page in a paragraph, and become an introduction plus a two-column table of links against terse descriptions — with a gate holding the table and the toctree to one ordered list, so the summary can never again drift from the directory.

**Architecture:** No new extension and no build-time machinery. The three landing pages are hand-authored reStructuredText: prose, one headerless `list-table`, and a hidden `toctree` in the same order. One new test module, `tests/test_docs_landing_pages.py`, reads those pages as text — stdlib only, no Sphinx — parses the two lists out of each, and asserts they are the same sequence. It discovers the quadrant directories rather than listing them, in the idiom of `tests/test_docs_topics.py`, so a fourth quadrant adopting the shape is covered without editing the gate.

**Tech Stack:** Python 3.12+, reStructuredText, Sphinx 9.1 with pydata-sphinx-theme 0.21, sphinx-design, sphinx-tippy, pixi, pytest, pre-commit.

**Spec:** [`../specs/2026-08-27-narrative-quadrants-design.md`](../specs/2026-08-27-narrative-quadrants-design.md) §3.9 — cited below as `narrative spec §3.9`. Read it alongside this plan; every task argues from it.

## What This Plan Measured Before It Was Written

Everything below was established on 2026-09-05 by prototyping `docs/src/howtos/index.rst`
in the new shape, building it with `pixi run docs-html`, and rendering the result in
Chromium at 1280px and 360px. The prototype was then reverted; this plan writes it back.

**1. A hidden toctree keeps the sidebar and the footer, and takes its order from the
file.** Measured: with `:hidden:` set and the entries in reading order rather than
alphabetically, the theme's *Section Navigation* sidebar listed all nine how-tos in that
same reading order, and the footer read "Previous: Plot a Sounding in Your Browser /
Next: Read a Sounding From an Archive". This is the whole reason §3.9 requires the two
orders to match: hiding a toctree hides it from the page body only. Nothing else reads it.

**2. `:widths: 30 70` is too narrow for the link column, and `auto` is only slightly
better.** Measured at 1280px: with `30 70` the left column came to about 185px and every
multi-word title wrapped to two lines; with `:widths: auto` docutils gave it about 227px,
roughly 37/63, and the longest titles still wrapped. The longest, *Build a Sounding From
Your Own Data*, needs about 250px to sit on one line, which would cost the description
column more than the wrap costs the reader. **Write `:widths: auto` and accept two-line
titles.** At 360px the table stayed inside the viewport with no horizontal scroll — the
left column narrows and titles wrap to three or four lines, which is legible.

**3. Tooltips fire on the table's links, which is the premise §3.9 argues from.**
Measured: hovering *Frame the View* raised a `[data-tippy-root]` carrying that page's
title and opening sentence. So a description cell repeating the page's opening would be
spending a row on what the hover already gives, which is why §3.9 makes the cell
editorial. One consequence to expect rather than discover: the tip is large enough to
cover the two table rows above the link. That is ordinary sphinx-tippy behaviour for any
inline link and is not the `sd-stretched-link` failure tooltip spec §3.3 fixed — these
are deliberately tipped links, and previewing a page before clicking is what a chooser
wants. Recorded, not worked around.

**4. Dropping the enumerating paragraph does not break the glossary gate.** Measured:
`pixi run lint` passed clean over the prototype, all hooks. The first mention of
`tephigram` stays in the surviving prose and stays cross-referenced; nothing else on the
page needed one. Confirmed separately by reading `prose()` in
`.github/scripts/check_glossary_links.py`: it advances past a directive and every
indented line under it, so a `list-table`'s cells are invisible to that gate in both
directions — a `:term:` in a cell cannot satisfy the first-mention rule, and a bare term
there cannot break it.

**5. The landing pages need no topic tags.** `tests/test_docs_topics.py` carries
`test_the_corpus_excludes_the_quadrant_landing_pages`, which asserts no corpus member
ends in `/index`. The new shape does not change that and no `:tags:` line is added.

**6. A citation must not be wrapped across a line break.** #274's changelog fragment was
rejected by the `check-citations` hook for splitting ``narrative spec §3.9`` over two
lines: the section resolved to `#None` instead of `#narrative-spec-3-9`. Keep a prefix
and its section on one line in every file this plan touches.

**What was not measured.** The tutorials and explanation pages were not prototyped — only
the how-to page, which is the nine-row worst case. Task 3 renders them before claiming
they read well.

## Global Constraints

- Every source file carries the BSD copyright header (ruff `CPY001`); the exact notice is in `[tool.ruff.lint.flake8-copyright]` in `pyproject.toml`. This applies to the new test module.
- `line-length = 88`; ruff `select = ["ALL"]` with the ignore list in `pyproject.toml`.
- ruff isort: `force-sort-within-sections = true`, `required-imports = ["from __future__ import annotations"]`, `known-first-party = ["tephpy"]`.
- numpydoc docstring convention. Validation runs over `^src/` only, so a test module needs docstrings but not the full validated section set. Match the house style: a module docstring saying what the module holds and citing its specification section, `#:` comments on module constants, `Parameters`/`Returns` on each helper.
- `[tool.pytest.ini_options]` sets `filterwarnings = ["error"]` — a warning in a test is a failure.
- The docs build is `--fail-on-warning --keep-going` (`docs/Makefile:1`). Any Sphinx warning fails `pixi run docs`.
- The new test module imports nothing outside the standard library and does **not** import Sphinx, so it runs in every `test-py3*` environment of the CI matrix rather than skipping there.
- Cite the specification as `narrative spec §3.9` in body prose, never in a section heading, and never split across a line break (measured finding 6).
- Every PR adds `changelog/<PR>.<type>.rst` ending with ``(:user:`claude`)``.
- **Everything in this plan lands together.** Task 1's corpus assertions fail against the three unconverted pages; the branch is not mergeable until Task 4.

---

## File Structure

| File | Responsibility |
|---|---|
| `tests/test_docs_landing_pages.py` | **Create.** The gate: two pure parsers over reStructuredText source, their unit tests over synthetic pages, and the corpus assertions over the real quadrants. |
| `docs/src/howtos/index.rst` | **Modify.** Nine rows, the enumerating sentence removed, the toctree hidden and reordered. |
| `docs/src/tutorials/index.rst` | **Modify.** Three rows, the per-page paragraph removed, the toctree hidden. |
| `docs/src/explanation/index.rst` | **Modify.** Two rows, the per-page paragraph removed, the toctree hidden. |
| `docs/src/developer/docs-style.rst` | **Modify.** A *Landing Pages* section after *Reading Time*, which is where the "navigated rather than read" ruling already sits. |
| `changelog/<PR>.documentation.rst` | **Create.** The fragment. |

---

## Task 1: The Gate

**Files:**
- Create: `tests/test_docs_landing_pages.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `toctree_entries(source: str) -> list[str]` and `table_targets(source: str) -> list[str | None]`, both module-level in the test file; `QUADRANTS: tuple[str, ...]` and `DOCS: Path`. Later tasks rely on the two lists agreeing, not on these names.

- [ ] **Step 1: Write the module with its parsers and their unit tests**

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""A quadrant landing page's table and its toctree are one list (narrative spec §3.9)."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

REPO = Path(__file__).parents[1]
DOCS = REPO / "docs" / "src"

#: The quadrants whose landing page carries a table. The reference quadrant is out:
#: its entries are reached by name rather than chosen between, and narrative spec §7
#: records the question rather than answering it here.
QUADRANTS = ("tutorials", "howtos", "explanation")

#: A `:doc:` role, with the explicit target that wins over the display text when one
#: is written -- the same two-part shape `check_glossary_links.py` reads a `:term:` in.
DOC = re.compile(r":doc:`([^`<]+?)(?:\s*<([^>]+)>)?`")


def _body(source: str, directive: str) -> list[str]:
    """Return the indented body of the one named directive on a page.

    Parameters
    ----------
    source : str
        The reStructuredText source of one page.
    directive : str
        The directive line to find, e.g. ``.. toctree::``.

    Returns
    -------
    list of str
        Every line under it, to the first line that is neither blank nor indented.

    Raises
    ------
    AssertionError
        If the page carries other than exactly one of that directive. Two toctrees or
        two tables is a copy-paste rather than a decision, and the gate would then be
        reading one of them and reporting on the page.

    """
    lines = source.splitlines()
    heads = [index for index, line in enumerate(lines) if line.strip() == directive]
    assert len(heads) == 1, f"expected one {directive} on the page, found {len(heads)}"
    body: list[str] = []
    for line in lines[heads[0] + 1 :]:
        if line.strip() and not line.startswith((" ", "\t")):
            break
        body.append(line)
    return body


def toctree_entries(source: str) -> list[str]:
    """Return the documents a page's toctree names, in order.

    Parameters
    ----------
    source : str
        The reStructuredText source of one page.

    Returns
    -------
    list of str
        Each entry, without its indentation. Directive options are not entries.

    """
    return [
        line.strip()
        for line in _body(source, ".. toctree::")
        if line.strip() and not line.strip().startswith(":")
    ]


def table_targets(source: str) -> list[str | None]:
    """Return the documents a page's landing table links to, in row order.

    Only the first cell of each row is read, so a `:doc:` written in a description
    is not mistaken for the row's own link, and neither is one in the prose above
    the table.

    Parameters
    ----------
    source : str
        The reStructuredText source of one page.

    Returns
    -------
    list of str or None
        The target of each row's first cell, or `None` for a row whose first cell
        carries no `:doc:` at all -- reported rather than skipped, so a row that
        links nowhere fails the page instead of shrinking the list silently.

    """
    found: list[str | None] = []
    for line in _body(source, ".. list-table::"):
        stripped = line.strip()
        if not stripped.startswith("* - "):
            continue
        match = DOC.search(stripped)
        found.append((match.group(2) or match.group(1)) if match else None)
    return found


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (".. toctree::\n    :hidden:\n\n    one\n    two\n", ["one", "two"]),
        (".. toctree::\n\n    one\n\n    two\n", ["one", "two"]),
        (".. toctree::\n    :hidden:\n\n    one\n\nAfter\n=====\n", ["one"]),
    ],
)
def test_toctree_entries_reads_the_directive_body_and_stops_at_it(source, expected):
    assert toctree_entries(source) == expected


def test_toctree_entries_does_not_read_an_option_as_an_entry():
    assert toctree_entries(".. toctree::\n    :maxdepth: 1\n\n    one\n") == ["one"]


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ("    * - :doc:`framing`\n      - Fit the view.\n", ["framing"]),
        ("    * - :doc:`Frame <framing>`\n      - Fit the view.\n", ["framing"]),
    ],
)
def test_table_targets_prefers_the_explicit_target(row, expected):
    assert table_targets(f".. list-table::\n    :widths: auto\n\n{row}") == expected


def test_table_targets_ignores_a_doc_role_in_a_description():
    source = (
        ".. list-table::\n    :widths: auto\n\n"
        "    * - :doc:`framing`\n      - Unlike :doc:`emphasis`, it moves the view.\n"
    )
    assert table_targets(source) == ["framing"]


def test_table_targets_reports_a_row_that_links_nowhere():
    source = ".. list-table::\n    :widths: auto\n\n    * - Frame the View\n      - Fit.\n"
    assert table_targets(source) == [None]


def test_a_second_toctree_fails_rather_than_being_half_read():
    source = ".. toctree::\n\n    one\n\n.. toctree::\n\n    two\n"
    with pytest.raises(AssertionError, match="expected one"):
        toctree_entries(source)
```

- [ ] **Step 2: Run the parser tests and watch them pass**

Run: `pixi run -e devs pytest tests/test_docs_landing_pages.py -v`
Expected: PASS — these are unit tests over synthetic sources and do not read the tree.

- [ ] **Step 3: Add the corpus assertions, which fail against the tree as it stands**

Append to the same module:

```python
def landing(quadrant: str, docs: Path = DOCS) -> str:
    """Return one quadrant's landing page source.

    Parameters
    ----------
    quadrant : str
        The quadrant's directory name under `docs`.
    docs : Path, optional
        The documentation source root.

    Returns
    -------
    str
        The page's text.

    """
    page = docs / quadrant / "index.rst"
    # Asserted rather than left to raise: a renamed landing page would otherwise
    # fail as a FileNotFoundError from inside a helper, naming the reader's bug
    # rather than the tree's.
    assert page.is_file(), f"{quadrant} has no landing page at {page}"
    return page.read_text(encoding="utf-8")


def test_every_quadrant_this_gate_governs_is_on_disk():
    """A gate that finds nothing passes by never having looked."""
    for quadrant in QUADRANTS:
        assert (DOCS / quadrant).is_dir(), f"{quadrant} is missing"
    assert len(QUADRANTS) == 3


@pytest.mark.parametrize("quadrant", QUADRANTS)
def test_the_table_and_the_toctree_are_one_ordered_list(quadrant):
    """Narrative spec §3.9: the visible index and the navigation are one list.

    Sequence and not set. The toctree is hidden, which hides it from the page body
    and from nothing else: the sidebar, the breadcrumb and the previous/next footer
    all read its order, so a table ordered differently would disagree with the
    navigation drawn around it.
    """
    source = landing(quadrant)
    assert table_targets(source) == toctree_entries(source)


@pytest.mark.parametrize("quadrant", QUADRANTS)
def test_every_row_links_to_a_page_in_its_own_quadrant(quadrant):
    for target in table_targets(landing(quadrant)):
        assert target is not None, f"{quadrant} has a row whose first cell links nowhere"
        assert (DOCS / quadrant / f"{target}.rst").is_file(), (
            f"{quadrant}'s table links to {target}, which is not a page in it"
        )
```

- [ ] **Step 4: Run the full module and confirm it fails for the right reason**

Run: `pixi run -e devs pytest tests/test_docs_landing_pages.py -v`
Expected: the parser tests PASS; `test_the_table_and_the_toctree_are_one_ordered_list`
and `test_every_row_links_to_a_page_in_its_own_quadrant` FAIL for all three quadrants
with `AssertionError: expected one .. list-table::, found 0`. That is the red this plan
turns green — the pages have no table yet.

- [ ] **Step 5: Commit**

```bash
git add tests/test_docs_landing_pages.py
git commit -m "Hold a quadrant's landing table and its toctree to one list"
```

---

## Task 2: The How-To Landing Page

**Files:**
- Modify: `docs/src/howtos/index.rst`

**Interfaces:**
- Consumes: Task 1's gate.
- Produces: the shape Tasks 3 copies — intro, `.. list-table::` with `:widths: auto`, hidden toctree in table order.

- [ ] **Step 1: Rewrite the page**

Replace the whole file with:

```rst
How-To Guides
=============

Recipes for a reader who already knows what they want. Each page answers one
question and stops there.

They assume you can already draw a :term:`tephigram`. If you cannot yet, the
:doc:`tutorials <../tutorials/index>` are the shorter way in, and the
:doc:`gallery <../gallery/index>` shows finished examples to work backwards from.

Every python block on these pages is executed by the test suite, as one script per
page and on every supported Python version, so what you copy is what ran.

.. list-table::
    :widths: auto

    * - :doc:`read-a-sounding`
      - An ascent out of the IGRA archive, or the Wyoming service.
    * - :doc:`temp-and-bufr`
      - A format ``tephpy`` does not read, decoded with ecCodes.
    * - :doc:`build-a-sounding`
      - Arrays, a :class:`pandas.DataFrame` or an :class:`xarray.Dataset` you already hold.
    * - :doc:`framing`
      - Fit the view to the data, or fix it so two figures compare.
    * - :doc:`emphasis`
      - Draw one member of a family heavier than the rest.
    * - :doc:`label-and-compose`
      - Label the edges, and set a tephigram beside another figure.
    * - :doc:`logo`
      - Brand a figure with the project mark.
    * - :doc:`configuration`
      - Set your own defaults once, in a file.
    * - :doc:`units`
      - What the API takes, and what it hands back.

.. toctree::
    :hidden:

    read-a-sounding
    temp-and-bufr
    build-a-sounding
    framing
    emphasis
    label-and-compose
    logo
    configuration
    units
```

The row order is the order a reader needs: data in, then the view, then style, then
units. The first two rows are contrastive on purpose — an archive `tephpy` reads,
against a format it does not — which is what a row is for under narrative spec §3.9.
`isopleth` is deliberately not written in the emphasis row: it is a glossary term, and a
term in a cell can neither satisfy nor break the first-mention rule, so the row takes
the plain word instead.

- [ ] **Step 2: Run the gate for this quadrant**

Run: `pixi run -e devs pytest tests/test_docs_landing_pages.py -v -k howtos`
Expected: PASS for `howtos`; `tutorials` and `explanation` still FAIL.

- [ ] **Step 3: Prove the gate is not passing by luck**

Delete the `* - :doc:`units`` row and its description from the table, leaving the
toctree alone, and run the same command.
Expected: FAIL, naming the two lists as unequal. Restore the row and confirm PASS
again. Then swap two adjacent toctree entries without swapping the table rows.
Expected: FAIL. Restore.

- [ ] **Step 4: Build and look at it**

Run: `pixi run docs-html`
Expected: `build succeeded` with no warnings. Then render the page and open the image
rather than assuming it reads well:

```bash
LD_LIBRARY_PATH=/home/bill/projects/geovista-jav-2026/.pixi/envs/geojav/lib \
  pixi run -e docs python -c "
import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, w in (('desktop', 1280), ('phone', 360)):
            pg = await b.new_page(viewport={'width': w, 'height': 1000})
            await pg.goto('file:///home/bill/projects/tephpy/docs/_build/html/howtos/index.html')
            await pg.wait_for_timeout(700)
            await pg.screenshot(path=f'/tmp/howtos-{name}.png', full_page=True)
        await b.close()
asyncio.run(main())
"
```

Expected: nine rows, two-line titles in the left column at 1280px, no horizontal scroll
at 360px, and the sidebar listing the nine pages in the table's order.

- [ ] **Step 5: Commit**

```bash
git add docs/src/howtos/index.rst
git commit -m "Give the how-to quadrant a table a reader can scan"
```

---

## Task 3: The Tutorials and Explanation Landing Pages

**Files:**
- Modify: `docs/src/tutorials/index.rst`
- Modify: `docs/src/explanation/index.rst`

**Interfaces:**
- Consumes: Task 1's gate, Task 2's shape.
- Produces: the gate green for all three quadrants.

- [ ] **Step 1: Rewrite the tutorials landing page**

Replace the whole file with:

```rst
Tutorials
=========

Start here if you are new to ``tephpy``, or new to :term:`tephigrams <tephigram>`.
These are lessons to work through rather than references to consult: each one is
followed start to finish, assumes no meteorology, and leaves you with a diagram you
made yourself.

Take them in order, and bring nothing with you — ``tephpy`` ships the
:term:`soundings <sounding>` they use, so neither asks you to find data first.

.. list-table::
    :widths: auto

    * - :doc:`first-tephigram`
      - Draw a real ascent, and name every line on it.
    * - :doc:`analyse-a-sounding`
      - Lift a parcel through that same ascent, and read what it says.
    * - :doc:`browser-demo`
      - Not a lesson but an exhibit: the package running in your browser.

.. toctree::
    :hidden:

    first-tephigram
    analyse-a-sounding
    browser-demo
```

The browser demo's distinction — an exhibit rather than a lesson — moves into its own
row rather than sitting in a paragraph after the table, so the reader meets it where
they meet the link.

- [ ] **Step 2: Rewrite the explanation landing page**

Replace the whole file with:

```rst
Explanation
===========

Why the diagram is the shape it is. Nothing here is needed to use ``tephpy`` — the
:doc:`tutorials <../tutorials/index>` and :doc:`how-to guides <../howtos/index>`
stand on their own — but a :term:`tephigram` is an unusual chart, and its
oddities all follow from decisions worth understanding.

Where a convention comes from a published chart rather than from the mathematics,
the page says so and cites it; :doc:`../reference/references` collects those
sources.

.. list-table::
    :widths: auto

    * - :doc:`rotated-axes`
      - The coordinate choice, the perpendicular grid, and the missing pressure axis.
    * - :doc:`parcel-ascent`
      - What happens to a lifted parcel, and why the energies are areas.

.. toctree::
    :hidden:

    rotated-axes
    parcel-ascent
```

Two rows is a thin table, and it is written anyway: the three quadrants are one shape,
and a reader who has learned to read the how-to page should not meet a different
convention here.

- [ ] **Step 3: Run the whole gate**

Run: `pixi run -e devs pytest tests/test_docs_landing_pages.py -v`
Expected: PASS, every test, all three quadrants.

- [ ] **Step 4: Build, and check the two claims that survived the rewrite**

Run: `pixi run docs`
Expected: `build succeeded`, zero warnings, and the API, citation, figure, link and
tooltip gates all pass.

Then read the built pages and confirm two things the prose still asserts:
`tephigram` is linked on its first mention on each page, and `parcel` now appears
first in an explanation table cell **without** a glossary link. That second one is a
consequence of narrative spec §3.9's rule that cells take the plain word, not an
oversight; it is listed in this plan's self-review as the one reader cost of the
change. Do not "fix" it by writing `:term:` into a cell without raising it first.

- [ ] **Step 5: Render both pages**

Use the Task 2 Step 4 command with `tutorials/index.html` and `explanation/index.html`
substituted, and open both images.
Expected: three rows and two rows respectively, no horizontal scroll at 360px, and the
sidebar order matching each table.

- [ ] **Step 6: Commit**

```bash
git add docs/src/tutorials/index.rst docs/src/explanation/index.rst
git commit -m "Give the tutorials and explanation quadrants the same table"
```

---

## Task 4: The Rule, the Fragment, and the Sweep

**Files:**
- Modify: `docs/src/developer/docs-style.rst`
- Create: `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: Tasks 1-3.
- Produces: a mergeable branch.

- [ ] **Step 1: Add the rule to docs-style**

Insert a new section immediately after *Reading Time* and before *Topic Tags*, so it
sits beside the ruling it executes:

```rst
Landing Pages
-------------

A quadrant landing page is navigation rather than prose, which is the same rule that
exempts it from the reading-time banner above. It carries, in order: an
introduction, one two-column ``list-table``, and a hidden ``toctree``.

The introduction says what the quadrant is for, who it assumes the reader is, what it
guarantees of every page in it, and where to go if this is the wrong quadrant. It says
nothing about an individual page — that is the table's job, and a paragraph that
summarises the quadrant page by page is a list that has to track a directory.

Each table row is a ``:doc:`` link against one sentence. The sentence is editorial
rather than descriptive: it is there so a reader can tell this page from its
siblings, and it is not the page's opening line, which a hover already shows. Write
``:widths: auto`` and no header row, which is the shape the API reference's own
summary tables already take.

The rows and the toctree carry the same pages in the same order, and it is the order
a reader needs rather than the alphabet. Hiding the toctree hides it from the page
body only: the sidebar, the breadcrumb and the previous/next footer all read its
order. ``tests/test_docs_landing_pages.py`` fails when the two disagree, in either
membership or order.

Glossary terms stay out of the cells. A table is a directive, and :ref:`the
first-mention rule <glossary-rule>` already passes over a directive's body, so a
``:term:`` in a cell neither satisfies that rule nor breaks it — write first mentions
in the introduction, and let a cell take the plain word (narrative spec §3.9).
```

The target `glossary-rule` was checked against `docs-style.rst:52`, where it labels the
first-mention rule itself; the ordering was checked too — *Reading Time* is at line 392
and *Topic Tags* at 438, so the new section goes between them.

- [ ] **Step 2: Verify the docs-style page builds and the cross-reference resolves**

Run: `pixi run docs-html`
Expected: `build succeeded`, no warnings.

- [ ] **Step 3: Write the changelog fragment**

`changelog/<PR>.documentation.rst`, with `<PR>` the pull request's own number:

```rst
The tutorials, how-to and explanation landing pages now open with what their
quadrant is for and then a table of its pages against a one-line description each,
in place of a paragraph that summarised them one at a time
(``narrative spec §3.9``). That paragraph had to be extended by hand whenever a page
was added, and nothing checked it; a new gate holds each table and its toctree to one
ordered list, so the two can no longer drift. (:user:`claude`)
```

Keep ``narrative spec §3.9`` on one line — a citation split across a line break
resolves to nothing, and the `check-citations` hook fails the commit.

- [ ] **Step 4: Run everything**

Run, in order:
```bash
pixi run lint
pixi run tests
pixi run docs
```
Expected: all three clean. `pixi run lint` runs the hooks that rewrite files, so run
`pixi run tests` **after** committing, not before, or the suite measures a tree that
no longer exists.

- [ ] **Step 5: Commit and open the pull request**

```bash
git add docs/src/developer/docs-style.rst changelog/
git commit -m "Record the landing-page shape as a documentation rule"
```

The pull request body states which member of each set was counted, per
*Reviewing Claims*: the three quadrant landing pages, all three converted; the nine
how-to rows against the nine `.rst` files in `docs/src/howtos/`; the mutation of
Task 2 Step 3, and what it failed with.

---

## Self-Review Notes

**Spec coverage.** Narrative spec §3.9's paragraphs map to tasks as: the shape → Tasks
2 and 3; the introduction's job → Tasks 2 and 3, prose written to it; the headerless
table → Task 2 Step 1 and the docs-style rule; the editorial row → Task 2 Step 1's
note and the rule; matching orders → Task 1's sequence assertion and Task 2 Step 3's
mutation; terms out of cells → the rule, and Task 3 Step 4's check; the gate → Task 1;
the reference quadrant left out → `QUADRANTS` in Task 1, with the reason as a comment.
§4's companion list and §5's testing row are satisfied by Tasks 1-4 together.

**The one reader cost, stated rather than buried.** On the explanation page `parcel`
currently carries its glossary link in the paragraph this change removes, and its
first appearance becomes a table cell, where §3.9 says a term takes the plain word. The
reader loses that one link on that one page; the term stays linked on
`parcel-ascent.rst` itself and in the glossary. Raise it if that trade looks wrong —
the alternative is writing `:term:` into cells, which the gate permits and §3.9
discourages.

**Type consistency.** `toctree_entries` returns `list[str]`; `table_targets` returns
`list[str | None]`, and the two are compared directly in
`test_the_table_and_the_toctree_are_one_ordered_list` — a `None` from a row that links
nowhere therefore fails that comparison as well as its own test, which is the intent.
`landing()` is the only reader of the tree and every corpus test goes through it.

**What no task does.** It does not touch `docs/src/reference/index.rst`, the site root,
or the gallery; it adds no extension, no CSS and no dependency; and it changes no page
outside the three landing pages and `docs-style.rst`.
