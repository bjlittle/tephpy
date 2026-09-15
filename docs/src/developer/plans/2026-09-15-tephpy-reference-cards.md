# Reference Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The reference quadrant's landing page stops listing its pages in a sentence and becomes a grid of seven icon cards, held to its hidden toctree by the same gate that holds the other sections' tables.

**Architecture:** No new extension and no build-time machinery. `tests/test_docs_landing_pages.py` gains a second index shape — `CARD_SECTIONS` beside `TABLE_SECTIONS` — read from each card's `:link:` option, with the API page (which exists only while a build runs) derived by executing `conf.py`. The page is hand-authored reStructuredText using sphinx-design's grid, the icons are hand-authored SVG in the root page's vocabulary, and the root page's card classes are renamed so both pages share one layout rule.

**Tech Stack:** reStructuredText, Sphinx 9.1 with pydata-sphinx-theme, sphinx-design 0.7.0, sphinx-tippy, hand-authored SVG, pytest, pixi, pre-commit. Playwright 1.62.0 for local render checks only — nothing in CI drives a browser for this.

**Spec:** [`../specs/2026-08-27-narrative-quadrants-design.md`](../specs/2026-08-27-narrative-quadrants-design.md) §3.9, the amendment of 2026-09-15 — cited below as `narrative spec §3.9`. Read it alongside this plan; every task argues from it.

## Global Constraints

- Every `.py` file carries the BSD copyright header (ruff `CPY001`). Every SVG carries the same notice as an XML comment above `<svg>`, as `docs/src/_static/cards/*.svg` already do.
- Every pull request adds `changelog/<PR>.<type>.rst` ending with ``(:user:`claude`)``, named once the pull request exists — a number cannot be reserved.
- A GitHub reference is written ``:issue:`N``` or ``:pull:`N``` in reStructuredText, CSS and Python, and ``{issue}`N``` in Markdown — never a bare `#N`, never a hand-written URL.
- **Citations are bare, never inside double backticks, and never split from their prefix by a line break.** Outside a specification always write the prefix: `narrative spec §3.9`, not `§3.9`.
- `pixi run docs` must build clean; the build is fail-on-warning.
- Verify **after** committing, never before: the pre-commit hooks rewrite files.
- Palette, exactly: navy `#1B3A6B` on light and `#8FB8E8` on dark; accent `#E4572E` on both; knock-out halo `#FFFFFF` on light and `#14181e` on dark.
- The grid is `.. grid:: 1 2 2 2` with `:gutter: 2`; the API card is first and carries `:columns: 12`.
- Card classes: `teph-card` on the card, `teph-card-icon` on each image. `teph-quadrant-button` belongs to the topics page and is **not** renamed.
- No `:term:` inside a card. First mentions belong in the prose.
- A card raises no hover tooltip (`sd-stretched-link` is in `tippy_skip_anchor_classes`).

---

## What This Plan Measured Before It Was Written

Established 2026-09-15 on `main` at `e3c1efc` and on the specification branch at `b47b843`, by building throwaway layouts in a worktree, rendering them in Chromium, and discarding them.

**1. Two columns split words on a phone; `1 2 2 2` with a full-width API card does not.** Four layouts of seven cards were built into the real theme and rendered at 360, 600 and 1280px. `.. grid:: 2` — the root page's, two columns at every breakpoint — gave cards about 150px wide at 360px and split "Configuratio / n" in a title and "documentatio / n" in a sentence. `.. grid:: 1 2 2 2` stacked one column at 360px with no split, gave two balanced columns at 600px, and with `:columns: 12` on the first card filled three even rows below it. Three columns squeezed each sentence to four lines. Every layout of seven equal cards left one alone on the last row.

**2. A card has no background of its own.** Walking up from `.sd-card` in the built root page, the first opaque background is `<body>`: `rgb(255, 255, 255)` in light and `rgb(20, 24, 30)` — `#14181e` — in dark, with `data-theme` confirmed to have switched. So an icon's knock-out halo must be `#14181e` in dark to vanish.

**3. The root page's dark halo leaves a ring.** Rendered on `#14181e`, the halo `#20242b` shows as a grey ring round every dot; `#14181e` shows none. Only the *Tutorials* pair carries a halo at all: `grep -c -E "#20242b|#FFFFFF"` over `docs/src/_static/cards/*.svg` counts one in `tutorials-light.svg`, one in `tutorials-dark.svg`, and zero in the other six.

**4. Seven icon drafts were rendered at 56 and 96px on both grounds, and two failed before the third attempt.** The glossary drawn as an orange pill read as a hyperlink icon; a borderless label box vanished on white; a label box with a thin navy border reads as a label on a line in both themes. The changelog with a faint rail read as a bullet list; a solid rail reads as a timeline. Task 3 carries the chosen drawings.

**5. A card raises no tooltip, although its tip is generated.** The built tooltip payload for a card page carries `a[href="cli.html"]` and the rest — but `tippy_skip_anchor_classes` includes `sd-stretched-link`, the class every card link carries, and the extension applies it at runtime. Reading the payload and concluding the card is tipped is the trap `tooltip spec §3.3` records. Task 4 hovers a card on the real page, with a table link as the positive control.

**6. The API page is never on disk outside a build.** `docs/src/reference/generated/` does not exist after `make html`: `autoapi_keep_files = False`, and `.gitignore:73` ignores the directory besides. Page discovery cannot find it; the gate must derive it.

**7. `conf.py` executes in the `test` environment.** Its top level imports only `datetime`, `importlib.metadata`, `pathlib` and `sys`, and reads `tephpy`'s installed version. `tests/test_docs_whatsnew.py` already executes it through `load_path`.

**8. The own-section check lets `..` through.** `(DOCS / "reference" / "../howtos/units.rst").is_file()` is `True` today, so an entry reaching into another section passes `test_every_row_links_to_a_page_in_its_own_quadrant`. Task 1 closes it.

**9. Renaming the four live tests breaks nothing.** Their names appear only in `tests/test_docs_landing_pages.py` and in two frozen plans.

**10. Nothing gates an SVG's header, and no test reads `docs-style.rst`'s *Landing Pages* text.** The scripts that name `docs-style.rst` point at other sections of it.

**11. The root page's own word split is not this plan's.** At 360px its four cards are 148px wide with a 114px text column under `overflow-wrap: break-word`, and "Understanding-" splits. Filed as {issue}`328`.

---

### Task 1: The gate reads cards

Teaches `tests/test_docs_landing_pages.py` the second index shape without any section taking it yet, and closes the `..` hole it would otherwise inherit (`narrative spec §3.9`, *The gate holds the cards as it holds the tables*).

**Files:**
- Modify: `tests/test_docs_landing_pages.py`

**Interfaces:**
- Consumes: `load_path(name: str, path: Path) -> ModuleType` from `tests/by_path.py`; `conf.autoapi_root` and `conf.autoapi_dirs` from `docs/src/conf.py`.
- Produces: `CARD_SECTIONS: tuple[str, ...]`, `CARD: str`, `card_targets(source: str) -> list[str | None]`, `generated_pages(section: str) -> list[str]`, `index_targets(section: str, source: str) -> list[str | None]`; `pages(quadrant, docs=DOCS)` keeps its signature. `toctree_entries` is unchanged — `tests/test_docs_whatsnew.py` imports it.

- [ ] **Step 1: Write the failing tests**

Append after `test_a_subdirectory_without_a_landing_page_gives_up_its_documents`:

```python
def test_card_targets_reads_each_cards_link_in_order():
    source = (
        "    .. grid-item-card:: API\n"
        "        :link: generated/api/tephpy/index\n"
        "        :link-type: doc\n"
        "        :columns: 12\n\n"
        "        Generated.\n\n"
        "    .. grid-item-card:: Command Line\n"
        "        :link-type: doc\n"
        "        :link: cli\n\n"
        "        What to type.\n"
    )
    assert card_targets(source) == ["generated/api/tephpy/index", "cli"]


def test_card_targets_reports_a_card_that_links_nowhere():
    """Reported rather than skipped, as a table row is."""
    source = (
        "    .. grid-item-card:: Glossary\n"
        "        :class-card: teph-card sd-rounded-3\n\n"
        "        .. image:: glossary-light.svg\n"
        "            :class: only-light teph-card-icon\n"
    )
    assert card_targets(source) == [None]


def test_card_targets_reads_only_the_cards_own_options():
    """A ``:link:`` after the option block is body text, not the card's link."""
    source = (
        "    .. grid-item-card:: Command Line\n"
        "        :link-type: doc\n\n"
        "        :link: cli\n"
    )
    assert card_targets(source) == [None]


def test_the_api_page_is_derived_for_the_section_autoapi_writes_into():
    """It exists only while a build runs, so discovery cannot find it."""
    assert generated_pages("reference") == ["generated/api/tephpy/index"]
    assert generated_pages("howtos") == []


def test_discovery_passes_over_a_generated_tree_a_build_left_behind(tmp_path):
    """A stale autoapi tree must not add pages the index is then asked to list."""
    section = tmp_path / "reference"
    (section / "generated" / "api" / "tephpy").mkdir(parents=True)
    (section / "index.rst").touch()
    (section / "cli.rst").touch()
    (section / "generated" / "api" / "index.rst").touch()
    (section / "generated" / "api" / "tephpy" / "index.rst").touch()
    assert pages("reference", docs=tmp_path) == ["cli"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pixi run -e test pytest tests/test_docs_landing_pages.py -q --no-cov`
Expected: the three `card_targets` tests and the `generated_pages` test FAIL with `NameError`; `test_discovery_passes_over_a_generated_tree_a_build_left_behind` FAILS with `['cli', 'generated/api/index'] == ['cli']`. Every existing test still passes.

- [ ] **Step 3: Change the module docstring and the imports**

Replace the module docstring and import block with:

```python
"""A landing page's index and its toctree are one list (narrative spec §3.9)."""

from __future__ import annotations

from functools import cache
from pathlib import Path, PurePosixPath
import re

import pytest

from tests.by_path import load_path

REPO = Path(__file__).parents[1]
DOCS = REPO / "docs" / "src"
CONF = DOCS / "conf.py"
```

- [ ] **Step 4: Add `CARD_SECTIONS` and `CARD`**

Replace the last paragraph of the `TABLE_SECTIONS` comment — the one beginning *The reference quadrant is out, decided rather than deferred* — with:

```python
#: The reference quadrant takes cards instead (`CARD_SECTIONS`): its pages are
#: looked up by name, and a card answers that with an icon where a row would offer a
#: choice nobody makes (narrative spec §3.9).
```

Immediately after the `TABLE_SECTIONS = (...)` line, add:

```python
#: The sections whose landing page carries a grid of cards (narrative spec §3.9).
#: Empty until the reference page takes the shape: every check below reads the live
#: page, so a section joins in the commit that gives it the cards.
CARD_SECTIONS: tuple[str, ...] = ()

#: The directive a card is written with. A card's own options are the ``:name:``
#: lines directly under it, and the first line that is not one ends them.
CARD = ".. grid-item-card::"
```

- [ ] **Step 5: Teach discovery to pass over autoapi's output**

Replace `_entries` and `pages` with:

```python
@cache
def _autoapi() -> tuple[PurePosixPath, str]:
    """Return where autoapi writes the API pages, and the package it documents.

    Read by executing `conf.py`, as `tests/test_docs_whatsnew.py` reads
    ``rst_epilog``: a text scan would pass on a value sitting in a comment. Cached,
    because every section's discovery asks and the answer cannot change in a run.

    Returns
    -------
    tuple of (PurePosixPath, str)
        ``autoapi_root``, relative to the documentation source, and the name of the
        package directory ``autoapi_dirs`` names.

    """
    conf = load_path("tephpy_docs_conf", CONF)
    return PurePosixPath(conf.autoapi_root), PurePosixPath(conf.autoapi_dirs[0]).name


def generated_pages(section: str) -> list[str]:
    """Return the pages a section offers that exist only while a build runs.

    autoapi writes the API reference under ``autoapi_root`` during a build and, with
    ``autoapi_keep_files = False``, removes it afterwards; the directory is
    git-ignored besides. Discovery cannot see a page that is not on disk, so the one
    entry a section's index gives the API is derived instead (narrative spec §3.9).

    Parameters
    ----------
    section : str
        The section's directory name under the documentation source.

    Returns
    -------
    list of str
        ``["generated/api/tephpy/index"]`` for the section ``autoapi_root`` sits in,
        and nothing for any other.

    """
    root, package = _autoapi()
    if root.parts[0] != section:
        return []
    return [str(PurePosixPath(*root.parts[1:], package, "index"))]


def _entries(directory: Path, skip: Path) -> list[Path]:
    """Return the documents one section offers, one path per destination.

    A subdirectory carrying its own ``index.rst`` is a subsection: it
    contributes that landing page and **nothing beneath it**, because from the
    parent's index it is a single destination however many documents sit inside
    it -- the specification collection is one row, not twenty. A subdirectory
    without one is a plain grouping, and its documents belong to the parent.
    Recursion stops at a landing page rather than pruning by name, so a
    subsection nested two deep behaves the same as one nested one deep
    (narrative spec §3.9).

    ``skip`` is autoapi's output directory, passed over wherever a build left it:
    its one page is counted by `generated_pages` instead, and a stale tree would
    otherwise add entries no index names.

    Parameters
    ----------
    directory : Path
        The section directory to read.
    skip : Path
        The directory autoapi writes into.

    Returns
    -------
    list of Path
        One path per destination: a document, or a subsection's landing page.

    """
    found: list[Path] = []
    for path in directory.iterdir():
        if path == skip:
            continue
        if path.is_dir():
            landing_page = path / "index.rst"
            if landing_page.is_file():
                found.append(landing_page)
            else:
                found.extend(_entries(path, skip))
        elif path.suffix == ".rst" and path.name != "index.rst":
            found.append(path)
    return found


def pages(quadrant: str, docs: Path = DOCS) -> list[str]:
    """Return every page on disk in a section, as its landing index would name it.

    A `:doc:` target on a landing page is relative to the section, so that is
    what these are made relative to. The section's own ``index.rst`` is a landing
    page rather than an entry in one and is left out; a subsection's is both, and
    counts as one entry of its parent. A page only a build writes is not on disk,
    and `generated_pages` supplies it.

    Parameters
    ----------
    quadrant : str
        The section's directory name under ``docs``.
    docs : Path, optional
        The documentation source root.

    Returns
    -------
    list of str
        The section's pages, sorted.

    """
    root = docs / quadrant
    skip = docs / _autoapi()[0]
    return sorted(
        path.relative_to(root).with_suffix("").as_posix()
        for path in _entries(root, skip)
    )
```

- [ ] **Step 6: Add the card reader**

Immediately after `table_targets`, add:

```python
def card_targets(source: str) -> list[str | None]:
    """Return the documents a page's landing cards link to, in card order.

    Only a card's own option block is read -- the ``:name: value`` lines directly
    under ``.. grid-item-card::`` -- so an option of an image nested in the card, or
    a field in its body, is not mistaken for the card's link.

    Parameters
    ----------
    source : str
        The reStructuredText source of one page.

    Returns
    -------
    list of str or None
        Each card's ``:link:``, or ``None`` for a card carrying none -- reported
        rather than skipped, so a card that links nowhere fails the page instead of
        shrinking the list silently.

    """
    lines = source.splitlines()
    found: list[str | None] = []
    for index, line in enumerate(lines):
        if not line.strip().startswith(CARD):
            continue
        link = None
        for option in lines[index + 1 :]:
            stripped = option.strip()
            if not stripped.startswith(":"):
                break
            name, _, value = stripped[1:].partition(":")
            if name == "link":
                link = value.strip()
        found.append(link)
    return found


def index_targets(section: str, source: str) -> list[str | None]:
    """Return a landing page's index, read in the shape its section takes.

    Parameters
    ----------
    section : str
        The section's directory name.
    source : str
        The reStructuredText source of its landing page.

    Returns
    -------
    list of str or None
        What `card_targets` reads for a card section, and `table_targets` otherwise.

    """
    return card_targets(source) if section in CARD_SECTIONS else table_targets(source)
```

- [ ] **Step 7: Generalise the live checks**

Replace everything from `def test_every_section_this_gate_governs_is_on_disk` to the end of the file with:

```python
def test_every_section_this_gate_governs_is_on_disk():
    """A gate that finds nothing passes by never having looked."""
    for section in TABLE_SECTIONS + CARD_SECTIONS:
        assert (DOCS / section).is_dir(), f"{section} is missing"


def test_a_section_takes_one_shape():
    """Two constants naming one section would put two indexes on its page."""
    assert not set(TABLE_SECTIONS) & set(CARD_SECTIONS)


@pytest.mark.parametrize("section", TABLE_SECTIONS + CARD_SECTIONS)
def test_a_landing_page_carries_one_index(section):
    """A table page carries no cards, and a card page no table (narrative spec §3.9)."""
    other = ".. list-table::" if section in CARD_SECTIONS else CARD
    assert other not in landing(section)


@pytest.mark.parametrize("section", TABLE_SECTIONS + CARD_SECTIONS)
def test_the_index_and_the_toctree_are_one_ordered_list(section):
    """Narrative spec §3.9: the visible index and the navigation are one list.

    Sequence and not set. The toctree is hidden, which hides it from the page body
    and from nothing else: the sidebar, the breadcrumb and the previous/next footer
    all read its order, so an index ordered differently would disagree with the
    navigation drawn around it.
    """
    source = landing(section)
    assert index_targets(section, source) == toctree_entries(source)


@pytest.mark.parametrize("section", TABLE_SECTIONS + CARD_SECTIONS)
def test_every_entry_links_to_a_page_in_its_own_section(section):
    """A target is a page of the section, or the one page a build generates there.

    ``..`` is refused outright: ``DOCS / section / "../howtos/units.rst"`` names a
    file that exists, so without it an entry pointing into another section would
    pass as a page of this one.
    """
    generated = generated_pages(section)
    for target in index_targets(section, landing(section)):
        assert target is not None, f"{section} has an entry that links nowhere"
        assert ".." not in PurePosixPath(target).parts, (
            f"{section}'s index links to {target}, outside the section"
        )
        assert target in generated or (DOCS / section / f"{target}.rst").is_file(), (
            f"{section}'s index links to {target}, which is not a page in it"
        )


@pytest.mark.parametrize("section", TABLE_SECTIONS + CARD_SECTIONS)
def test_the_index_lists_every_page_in_the_section(section):
    """The index is the section's index, so it indexes the section.

    The ordered comparison above holds the index and the toctree to each other and
    would not notice a page missing from both, which is how a page goes unlisted:
    one commit that adds a page and neither list. The fail-on-warning build catches
    the ordinary case -- Sphinx reports a document in no toctree -- but not an
    `:orphan:` page, which builds clean and would sit in the section unreachable
    from its own landing page.
    """
    listed = sorted(
        target for target in index_targets(section, landing(section)) if target
    )
    assert listed == sorted(pages(section) + generated_pages(section))


@pytest.mark.parametrize("section", TABLE_SECTIONS + CARD_SECTIONS)
def test_the_toctree_is_hidden(section):
    """Narrative spec §3.9: the index is the visible one, and it is the only one.

    Without this the page renders the same list twice, the index and the toctree
    under it, which is the duplication the shape exists to remove.
    """
    assert ":hidden:" in toctree_options(landing(section))
```

- [ ] **Step 8: Run the gate and its one importer**

Run: `pixi run -e test pytest tests/test_docs_landing_pages.py tests/test_docs_whatsnew.py -q --no-cov`
Expected: PASS. `CARD_SECTIONS` is empty, so every live check runs over the five table sections exactly as before, under its new name.

- [ ] **Step 9: Prove the `..` refusal by mutation**

```bash
sed -i 's|:doc:`units`|:doc:`../howtos/units`|' docs/src/howtos/index.rst
pixi run -e test pytest tests/test_docs_landing_pages.py -q --no-cov -k "own_section and howtos"
git checkout -- docs/src/howtos/index.rst
```

Expected: `test_every_entry_links_to_a_page_in_its_own_section[howtos]` FAILS with `howtos's index links to ../howtos/units, outside the section`. Then confirm the tree is clean: `git status --short docs/` prints nothing.

- [ ] **Step 10: Lint, commit, and verify after the commit**

```bash
pixi run -e devs pre-commit run --files tests/test_docs_landing_pages.py
git add tests/test_docs_landing_pages.py
git commit -m "Teach the landing-page gate to read cards"
pixi run -e test pytest tests/test_docs_landing_pages.py tests/test_docs_whatsnew.py -q --no-cov
```

Expected: every hook passes; the tests pass again on the committed tree.

---

### Task 2: Rename the card classes

Behaviour-preserving. The classes stop saying *quadrant* before a page whose cards are not quadrants uses them (`narrative spec §3.9`, §4's 2026-09-15 companion changes).

**Files:**
- Modify: `docs/src/index.rst` (four `:class-card:` lines, eight `:class:` lines)
- Modify: `docs/src/_static/tephpy.css` (two selectors)

**Interfaces:**
- Consumes: nothing.
- Produces: `teph-card` and `teph-card-icon`, which Task 4's page uses.

- [ ] **Step 1: Write the layout probe**

Create `/tmp/measure_cards.py` — outside the repository; it is a check, not a file this plan commits:

```python
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

page_path = Path(sys.argv[1]).resolve().as_uri()
probe = """() => [...document.querySelectorAll('article.bd-article .sd-card')].map(card =>
  Math.round([...card.querySelectorAll('.sd-card-body p')].pop().getBoundingClientRect().width))"""
with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (360, 576, 1280):
        page = browser.new_page(viewport={"width": width, "height": 800})
        page.goto(page_path)
        page.wait_for_load_state("networkidle")
        print(width, page.evaluate(probe))
        page.close()
    browser.close()
```

Where Chromium cannot find its system libraries, supply them through `LD_LIBRARY_PATH`; Playwright's own error names the missing ones.

- [ ] **Step 2: Measure the root page before**

```bash
pixi run docs-html
pixi run -e docs python /tmp/measure_cards.py docs/_build/html/index.html
```

Expected: `360 [114, 114, 114, 114]` and `576 [154, 154, 154, 154]`. Record the 1280 line exactly. The 576 line is the one that discriminates: if the icon rule stops matching, the icon falls back above the text and the column widens to 222px.

- [ ] **Step 3: Rename**

```bash
sed -i -e 's/teph-quadrant-icon/teph-card-icon/g' \
       -e 's/:class-card: teph-quadrant sd-rounded-3/:class-card: teph-card sd-rounded-3/' \
       docs/src/index.rst
sed -i -e 's/^\.teph-quadrant-icon {$/.teph-card-icon {/' \
       -e 's/^  \.teph-quadrant \.sd-card-body {$/  .teph-card .sd-card-body {/' \
       -e 's/^  \.teph-quadrant-icon {$/  .teph-card-icon {/' \
       docs/src/_static/tephpy.css
```

- [ ] **Step 4: Check nothing was missed and nothing extra was touched**

```bash
git grep -n -E "teph-quadrant(-icon)?\b" -- docs/src | grep -v teph-quadrant-button
git grep -c "teph-quadrant-button" -- docs/src
git grep -c -E "teph-card(-icon)?\b" -- docs/src/index.rst docs/src/_static/tephpy.css
```

Expected: the first prints nothing. The second still counts `docs/src/_ext/tephpy_topics.py:1`, `docs/src/_static/tephpy.css:4`, `docs/src/_static/topics.js:1`. The third counts `docs/src/index.rst:12` and `docs/src/_static/tephpy.css:3`.

- [ ] **Step 5: Measure the root page after**

```bash
pixi run docs-html
pixi run -e docs python /tmp/measure_cards.py docs/_build/html/index.html
```

Expected: all three lines identical to Step 2.

- [ ] **Step 6: Commit**

```bash
git add docs/src/index.rst docs/src/_static/tephpy.css
git commit -m "Name the landing cards' classes for cards, not quadrants"
```

---

### Task 3: The seven icons, and the Tutorials halo

**Files:**
- Create: `docs/src/_static/cards/reference/{api,cli,config,glossary,references,whatsnew,changelog}-{light,dark}.svg`
- Modify: `docs/src/_static/cards/tutorials-dark.svg` (one colour)

**Interfaces:**
- Consumes: nothing.
- Produces: fourteen files at the paths above, with the `aria-label` texts below, which Task 4's `:alt:` options repeat verbatim.

| file stem | `aria-label` and `:alt:` |
|---|---|
| `api` | a module tree, one entry found |
| `cli` | a shell prompt, its cursor marked |
| `config` | two options on their scales, one of them set |
| `glossary` | a line, and the label that names it |
| `references` | a printed page, its source marked |
| `whatsnew` | a spark, marking what is new |
| `changelog` | a run of entries, the newest marked |

- [ ] **Step 1: Write the seven light drawings**

Each file opens with this notice, exactly:

```xml
<!--
  Copyright (c) 2026, tephpy Contributors.

  This file is part of tephpy and is distributed under the 3-Clause BSD license.
  See the LICENSE file in the package root directory for licensing details.
-->
```

followed by its `<svg>`. The lattice group is the root page's, copied exactly.

`docs/src/_static/cards/reference/api-light.svg`:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="a module tree, one entry found">
  <title>a module tree, one entry found</title>
  <g stroke="#1B3A6B" stroke-width="1.6" stroke-linecap="round" opacity="0.20">
    <path d="M-2 14 L50 66"/><path d="M12 0 L64 52"/><path d="M26 -14 L78 38"/>
    <path d="M66 14 L14 66"/><path d="M52 0 L0 52"/><path d="M38 -14 L-14 38"/>
  </g>
  <g fill="none" stroke="#1B3A6B" stroke-width="4.4" stroke-linecap="round">
    <path d="M18 12 L18 50"/><path d="M18 22 L36 22"/><path d="M18 42 L36 42"/>
  </g>
  <circle cx="44" cy="22" r="7.6" fill="#FFFFFF"/><circle cx="44" cy="22" r="5" fill="#1B3A6B"/>
  <circle cx="44" cy="42" r="7.6" fill="#FFFFFF"/><circle cx="44" cy="42" r="5" fill="#E4572E"/>
</svg>
```

`docs/src/_static/cards/reference/cli-light.svg`:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="a shell prompt, its cursor marked">
  <title>a shell prompt, its cursor marked</title>
  <g stroke="#1B3A6B" stroke-width="1.6" stroke-linecap="round" opacity="0.20">
    <path d="M-2 14 L50 66"/><path d="M12 0 L64 52"/><path d="M26 -14 L78 38"/>
    <path d="M66 14 L14 66"/><path d="M52 0 L0 52"/><path d="M38 -14 L-14 38"/>
  </g>
  <path d="M13 20 L25 32 L13 44" fill="none" stroke="#1B3A6B" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M32 44 L51 44" fill="none" stroke="#E4572E" stroke-width="5" stroke-linecap="round"/>
</svg>
```

`docs/src/_static/cards/reference/config-light.svg`:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="two options on their scales, one of them set">
  <title>two options on their scales, one of them set</title>
  <g stroke="#1B3A6B" stroke-width="1.6" stroke-linecap="round" opacity="0.20">
    <path d="M-2 14 L50 66"/><path d="M12 0 L64 52"/><path d="M26 -14 L78 38"/>
    <path d="M66 14 L14 66"/><path d="M52 0 L0 52"/><path d="M38 -14 L-14 38"/>
  </g>
  <g fill="none" stroke="#1B3A6B" stroke-width="3" stroke-linecap="round" opacity="0.55">
    <path d="M10 22 L54 22"/><path d="M10 42 L54 42"/>
  </g>
  <circle cx="22" cy="22" r="8.2" fill="#FFFFFF"/><circle cx="22" cy="22" r="5.6" fill="#1B3A6B"/>
  <circle cx="40" cy="42" r="8.2" fill="#FFFFFF"/><circle cx="40" cy="42" r="5.6" fill="#E4572E"/>
</svg>
```

`docs/src/_static/cards/reference/glossary-light.svg`:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="a line, and the label that names it">
  <title>a line, and the label that names it</title>
  <g stroke="#1B3A6B" stroke-width="1.6" stroke-linecap="round" opacity="0.20">
    <path d="M-2 14 L50 66"/><path d="M12 0 L64 52"/><path d="M26 -14 L78 38"/>
    <path d="M66 14 L14 66"/><path d="M52 0 L0 52"/><path d="M38 -14 L-14 38"/>
  </g>
  <path d="M4 56 C20 44 30 28 60 10" fill="none" stroke="#1B3A6B" stroke-width="4" stroke-linecap="round"/>
  <rect x="16" y="20" width="32" height="18" rx="3.5" fill="#FFFFFF" stroke="#1B3A6B" stroke-width="2.6"/>
  <path d="M22.5 29 L41.5 29" fill="none" stroke="#E4572E" stroke-width="4.4" stroke-linecap="round"/>
</svg>
```

`docs/src/_static/cards/reference/references-light.svg`:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="a printed page, its source marked">
  <title>a printed page, its source marked</title>
  <g stroke="#1B3A6B" stroke-width="1.6" stroke-linecap="round" opacity="0.20">
    <path d="M-2 14 L50 66"/><path d="M12 0 L64 52"/><path d="M26 -14 L78 38"/>
    <path d="M66 14 L14 66"/><path d="M52 0 L0 52"/><path d="M38 -14 L-14 38"/>
  </g>
  <path d="M15 10 L39 10 L50 21 L50 54 L15 54 Z" fill="none" stroke="#1B3A6B" stroke-width="3.6" stroke-linejoin="round"/>
  <path d="M39 10 L39 21 L50 21" fill="none" stroke="#1B3A6B" stroke-width="3" stroke-linejoin="round"/>
  <path d="M22 10 L22 32 L27.5 26.5 L33 32 L33 10 Z" fill="#E4572E"/>
</svg>
```

`docs/src/_static/cards/reference/whatsnew-light.svg`:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="a spark, marking what is new">
  <title>a spark, marking what is new</title>
  <g stroke="#1B3A6B" stroke-width="1.6" stroke-linecap="round" opacity="0.20">
    <path d="M-2 14 L50 66"/><path d="M12 0 L64 52"/><path d="M26 -14 L78 38"/>
    <path d="M66 14 L14 66"/><path d="M52 0 L0 52"/><path d="M38 -14 L-14 38"/>
  </g>
  <path d="M38 10 Q40.5 23.5 54 26 Q40.5 28.5 38 42 Q35.5 28.5 22 26 Q35.5 23.5 38 10 Z" fill="#E4572E"/>
  <path d="M17 38 Q18.2 44.8 25 46 Q18.2 47.2 17 54 Q15.8 47.2 9 46 Q15.8 44.8 17 38 Z" fill="#1B3A6B" opacity="0.55"/>
</svg>
```

`docs/src/_static/cards/reference/changelog-light.svg`:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="a run of entries, the newest marked">
  <title>a run of entries, the newest marked</title>
  <g stroke="#1B3A6B" stroke-width="1.6" stroke-linecap="round" opacity="0.20">
    <path d="M-2 14 L50 66"/><path d="M12 0 L64 52"/><path d="M26 -14 L78 38"/>
    <path d="M66 14 L14 66"/><path d="M52 0 L0 52"/><path d="M38 -14 L-14 38"/>
  </g>
  <path d="M19 15 L19 51" fill="none" stroke="#1B3A6B" stroke-width="3.4" stroke-linecap="round"/>
  <g fill="none" stroke="#1B3A6B" stroke-width="4" stroke-linecap="round">
    <path d="M30 15 L51 15"/><path d="M30 33 L46 33"/><path d="M30 51 L49 51"/>
  </g>
  <circle cx="19" cy="15" r="7.2" fill="#FFFFFF"/><circle cx="19" cy="15" r="4.6" fill="#E4572E"/>
  <circle cx="19" cy="33" r="7.2" fill="#FFFFFF"/><circle cx="19" cy="33" r="4.6" fill="#1B3A6B"/>
  <circle cx="19" cy="51" r="7.2" fill="#FFFFFF"/><circle cx="19" cy="51" r="4.6" fill="#1B3A6B"/>
</svg>
```

- [ ] **Step 2: Derive the dark twins**

The dark file is the light file with two colours swapped and nothing else (`narrative spec §3.9`):

```bash
cd docs/src/_static/cards/reference
for stem in api cli config glossary references whatsnew changelog; do
  sed -e 's/#1B3A6B/#8FB8E8/g' -e 's/#FFFFFF/#14181e/g' "$stem-light.svg" > "$stem-dark.svg"
done
cd -
```

- [ ] **Step 3: Correct the root page's Tutorials halo**

```bash
sed -i 's/fill="#20242b"/fill="#14181e"/' docs/src/_static/cards/tutorials-dark.svg
```

- [ ] **Step 4: Check the files mechanically**

```bash
grep -l -E "#1B3A6B|#FFFFFF" docs/src/_static/cards/reference/*-dark.svg
grep -L "#8FB8E8" docs/src/_static/cards/reference/*-dark.svg
grep -rn "#20242b" docs/src/_static/cards
pixi run -e test python -c "
import xml.etree.ElementTree as ET
from pathlib import Path
files = sorted(Path('docs/src/_static/cards/reference').glob('*.svg'))
assert len(files) == 14, len(files)
for f in files:
    root = ET.parse(f).getroot()
    assert root.get('aria-label'), f
print('14 well-formed, all labelled')
"
```

Expected: the three `grep`s print nothing, and the last prints `14 well-formed, all labelled`.

- [ ] **Step 5: Render the drawings and look at them**

Create `/tmp/render_icons.py`:

```python
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

cards = Path("docs/src/_static/cards/reference").resolve()
stems = ["api", "cli", "config", "glossary", "references", "whatsnew", "changelog"]
out = Path(sys.argv[1]).resolve()


def cells(theme):
    return "".join(
        f'<figure><img src="{(cards / f"{s}-{theme}.svg").as_uri()}" width="56">'
        f'<img src="{(cards / f"{s}-{theme}.svg").as_uri()}" width="96">'
        f"<figcaption>{s}</figcaption></figure>"
        for s in stems
    )


html = (
    "<style>body{margin:0;font:13px sans-serif}"
    "div{display:flex;flex-wrap:wrap;gap:12px;padding:12px}"
    "figure{margin:0;display:flex;flex-direction:column;align-items:center;gap:6px}</style>"
    f'<div style="background:#ffffff;color:#222">{cells("light")}</div>'
    f'<div style="background:#14181e;color:#ddd">{cells("dark")}</div>'
)
sheet = out.with_suffix(".html")
sheet.write_text(html, encoding="utf-8")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1000, "height": 400})
    page.goto(sheet.as_uri())
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(out), full_page=True)
    browser.close()
print("wrote", out)
```

Run: `pixi run -e docs python /tmp/render_icons.py /tmp/reference-icons.png`, and open the image.
Expected, checked by eye at 56px on both grounds: each drawing reads as its label; exactly one orange element per icon; no grey ring round any dot or the glossary's label box on the dark ground. If a drawing fails, redraw it here and record why in the pull request — do not carry a failed drawing into Task 4.

- [ ] **Step 6: Commit**

```bash
git add docs/src/_static/cards/reference docs/src/_static/cards/tutorials-dark.svg
git commit -m "Draw the reference cards' icons, and knock out the Tutorials halo"
```

---

### Task 4: The reference landing page

**Files:**
- Modify: `docs/src/reference/index.rst` (whole file)
- Modify: `tests/test_docs_landing_pages.py` (`CARD_SECTIONS`)
- Modify: `docs/src/_static/tephpy.css` (two comments)

**Interfaces:**
- Consumes: `CARD_SECTIONS`, `card_targets`, `generated_pages` (Task 1); `teph-card`, `teph-card-icon` (Task 2); the fourteen icons and their labels (Task 3).
- Produces: the page `tests/test_docs_snippets.py::test_the_reference_index_sends_a_caller_to_the_hierarchy` reads, which Task 5 touches.

- [ ] **Step 1: Put the reference quadrant under the gate**

In `tests/test_docs_landing_pages.py`, replace the `CARD_SECTIONS` block with:

```python
#: The sections whose landing page carries a grid of cards (narrative spec §3.9).
CARD_SECTIONS: tuple[str, ...] = ("reference",)
```

- [ ] **Step 2: Run the gate to verify it fails**

Run: `pixi run -e test pytest tests/test_docs_landing_pages.py -q --no-cov`
Expected: exactly three FAIL, all `[reference]` — `test_the_index_and_the_toctree_are_one_ordered_list` (`[] == [...seven entries...]`), `test_the_index_lists_every_page_in_the_section`, and `test_the_toctree_is_hidden`. `test_every_entry_links_to_a_page_in_its_own_section[reference]` passes vacuously, because the page has no cards yet — that is why Step 5 mutates it.

- [ ] **Step 3: Write the page**

Replace the whole of `docs/src/reference/index.rst` with:

```rst
Reference
=========

.. The cards are the visible index and the toctree below is the navigation; the two
   are one list, held by tests/test_docs_landing_pages.py (narrative spec §3.9).

   Each icon is drawn in the root page's vocabulary, as that page's comment sets it
   out: API, a module tree with one entry found; Command Line, a shell prompt at its
   cursor; Configuration Options, two options on their scales with one set;
   Glossary, a line and the label that names it; References, a printed page with its
   source marked; What's New, a spark; Changelog, a run of entries with the newest
   marked. Light and dark differ only in the navy and the knock-out halo, and live in
   _static/cards/reference/.

The factual material, for looking things up rather than reading through.

.. grid:: 1 2 2 2
    :gutter: 2

    .. grid-item-card:: API
        :link: generated/api/tephpy/index
        :link-type: doc
        :class-card: teph-card sd-rounded-3
        :columns: 12

        .. image:: ../_static/cards/reference/api-light.svg
            :class: only-light teph-card-icon
            :alt: a module tree, one entry found

        .. image:: ../_static/cards/reference/api-dark.svg
            :class: only-dark teph-card-icon
            :alt: a module tree, one entry found

        Generated from the source, so it describes the version you have installed.

    .. grid-item-card:: Command Line
        :link: cli
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/cli-light.svg
            :class: only-light teph-card-icon
            :alt: a shell prompt, its cursor marked

        .. image:: ../_static/cards/reference/cli-dark.svg
            :class: only-dark teph-card-icon
            :alt: a shell prompt, its cursor marked

        What to type at a shell.

    .. grid-item-card:: Configuration Options
        :link: config
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/config-light.svg
            :class: only-light teph-card-icon
            :alt: two options on their scales, one of them set

        .. image:: ../_static/cards/reference/config-dark.svg
            :class: only-dark teph-card-icon
            :alt: two options on their scales, one of them set

        What to set, in Python or in a file.

    .. grid-item-card:: Glossary
        :link: glossary
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/glossary-light.svg
            :class: only-light teph-card-icon
            :alt: a line, and the label that names it

        .. image:: ../_static/cards/reference/glossary-dark.svg
            :class: only-dark teph-card-icon
            :alt: a line, and the label that names it

        What a word means here, and where the API carries it.

    .. grid-item-card:: References
        :link: references
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/references-light.svg
            :class: only-light teph-card-icon
            :alt: a printed page, its source marked

        .. image:: ../_static/cards/reference/references-dark.svg
            :class: only-dark teph-card-icon
            :alt: a printed page, its source marked

        Where a convention or definition came from.

    .. grid-item-card:: What's New
        :link: whatsnew/index
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/whatsnew-light.svg
            :class: only-light teph-card-icon
            :alt: a spark, marking what is new

        .. image:: ../_static/cards/reference/whatsnew-dark.svg
            :class: only-dark teph-card-icon
            :alt: a spark, marking what is new

        A release, in the few things worth knowing.

    .. grid-item-card:: Changelog
        :link: changelog
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/changelog-light.svg
            :class: only-light teph-card-icon
            :alt: a run of entries, the newest marked

        .. image:: ../_static/cards/reference/changelog-dark.svg
            :class: only-dark teph-card-icon
            :alt: a run of entries, the newest marked

        A release, one entry per pull request.

If you are deciding what to catch, read :mod:`tephpy.exceptions`. What
``tephpy`` raises about your data — its units, its physical consistency, the
source it came from, the configuration file in force — derives from
:class:`TephpyError <tephpy.exceptions.TephpyError>`, so one ``except`` clause
covers that subject, and the module sets out the narrower classes for when it
is too broad. Ordinary argument mistakes stay outside the hierarchy and raise
the builtin exceptions instead.

The glossary is worth knowing about before you need it. ``tephpy``'s audience is
scientific software engineers rather than meteorologists, so each entry gives the
concept in one plain sentence and then says how it appears in the package — the
data it involves, its units, and the API that carries it.

.. toctree::
    :hidden:
    :maxdepth: 1

    generated/api/tephpy/index
    cli
    config
    glossary
    references
    whatsnew/index
    changelog
```

`:maxdepth: 1` stays because the toctree it sits on is unchanged apart from hiding it — the sidebar reads the same directive.

- [ ] **Step 4: Run the gate and the signpost test**

Run: `pixi run -e test pytest tests/test_docs_landing_pages.py "tests/test_docs_snippets.py::test_the_reference_index_sends_a_caller_to_the_hierarchy" -q --no-cov`
Expected: PASS.

- [ ] **Step 5: Prove each check by mutation**

*Corrected 2026-09-15, during implementation:* the restores below originally used ``git checkout --``, which restores the page this task replaces.

Run each block from a clean tree, read the failure, and restore before the next.

```bash
# Step 3's page is not committed until Step 8, so `git checkout --` would restore
# the page this task replaces. Restore from this copy instead.
cp docs/src/reference/index.rst "${TMPDIR:-/tmp}/reference-index.rst"
```

```bash
# (a) order: swap What's New and Changelog in the toctree only
sed -i -e 's|^    whatsnew/index$|    SWAP|' -e 's|^    changelog$|    whatsnew/index|' -e 's|^    SWAP$|    changelog|' docs/src/reference/index.rst
pixi run -e test pytest tests/test_docs_landing_pages.py -q --no-cov -k reference
cp "${TMPDIR:-/tmp}/reference-index.rst" docs/src/reference/index.rst
diff "${TMPDIR:-/tmp}/reference-index.rst" docs/src/reference/index.rst && echo restored
```
Expected: `test_the_index_and_the_toctree_are_one_ordered_list[reference]` FAILS.

```bash
# (b) reach outside the section
sed -i 's|^        :link: cli$|        :link: ../howtos/units|' docs/src/reference/index.rst
pixi run -e test pytest tests/test_docs_landing_pages.py -q --no-cov -k reference
cp "${TMPDIR:-/tmp}/reference-index.rst" docs/src/reference/index.rst
diff "${TMPDIR:-/tmp}/reference-index.rst" docs/src/reference/index.rst && echo restored
```
Expected: three FAIL, all `[reference]`. `test_every_entry_links_to_a_page_in_its_own_section` fails with `reference's index links to ../howtos/units, outside the section` — the check this mutation is for. `test_the_index_and_the_toctree_are_one_ordered_list` fails because the card no longer matches the toctree's `cli`, and `test_the_index_lists_every_page_in_the_section` because `cli` is no longer listed.

```bash
# (c) an orphan page neither list names
printf ':orphan:\n\nStray\n=====\n' > docs/src/reference/stray.rst
pixi run -e test pytest tests/test_docs_landing_pages.py -q --no-cov -k reference
rm docs/src/reference/stray.rst
```
Expected: `test_the_index_lists_every_page_in_the_section[reference]` FAILS, naming `stray`.

```bash
# (d) the toctree shown
sed -i '/^    :hidden:$/d' docs/src/reference/index.rst
pixi run -e test pytest tests/test_docs_landing_pages.py -q --no-cov -k reference
cp "${TMPDIR:-/tmp}/reference-index.rst" docs/src/reference/index.rst
diff "${TMPDIR:-/tmp}/reference-index.rst" docs/src/reference/index.rst && echo restored
```
Expected: `test_the_toctree_is_hidden[reference]` FAILS.

```bash
# (e) a missing icon, against the build rather than the gate
mv docs/src/_static/cards/reference/api-light.svg /tmp/api-light.svg
pixi run docs-html; echo "exit=$?"
mv /tmp/api-light.svg docs/src/_static/cards/reference/api-light.svg
```
Expected: the fail-on-warning build exits non-zero, naming `api-light.svg`. **If it exits 0, do not add a gate:** record in the pull request that a missing icon builds clean, per `narrative spec §3.9` (presentation is ungated).

Finish with the final `diff` printing `restored` and `git status --short` printing only this task's intended changes.

- [ ] **Step 6: Update the stylesheet's comments**

In `docs/src/_static/tephpy.css`, replace the comment line

```css
 * The four Diátaxis quadrant cards on the landing page.
```

with

```css
 * The landing pages' cards: the root page's four Diátaxis quadrants, and the
 * reference quadrant's seven (narrative spec §3.9).
```

and in the comment above `@media (min-width: 576px)`, replace

```css
 * `.. grid:: 2` is two columns at *every* breakpoint -- the emitted row carries
```

with

```css
 * The root page's `.. grid:: 2` is two columns at *every* breakpoint -- the
 * emitted row carries
```

then, immediately before that comment's closing ` */`, add:

```css
 *
 * The reference quadrant's `.. grid:: 1 2 2 2` is one column below 576px, so its
 * cards never meet that width. Above the icon, the root page's longest segment
 * still splits at 360px (:issue:`328`).
```

- [ ] **Step 7: Build, render, and hover**

Create `/tmp/render_reference.py`:

```python
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

html = Path("docs/_build/html").resolve()
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    for scheme in ("light", "dark"):
        for width in (360, 600, 1280):
            page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
            page.goto((html / "reference" / "index.html").as_uri())
            page.wait_for_load_state("networkidle")
            page.locator("article.bd-article").screenshot(path=str(out / f"{scheme}-{width}.png"))
            page.close()
    for label, path, selector in (
        ("a card", "reference/index.html", ".sd-card:has-text('Command Line')"),
        ("a table link (control)", "howtos/index.html", "article.bd-article table a.reference.internal"),
    ):
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto((html / path).as_uri())
        page.wait_for_load_state("networkidle")
        page.locator(selector).first.hover()
        page.wait_for_timeout(800)
        print(label, "raised", page.locator("[data-tippy-root]").count(), "tooltips")
        page.close()
    browser.close()
```

```bash
pixi run docs
pixi run -e docs python /tmp/render_reference.py /tmp/reference-page
```

Expected: `pixi run docs` passes every gate. The script prints `a card raised 0 tooltips` and `a table link (control) raised 1 tooltips` — if the control raises 0, the probe is broken and the card's 0 means nothing; fix the probe before believing it. By eye, in all six images: no word split mid-word; one column at 360px; the API card spanning both columns at 600 and 1280px; three even rows beneath it; no ring round any dot on the dark ground.

- [ ] **Step 8: Commit, and verify after the commit**

```bash
git add docs/src/reference/index.rst tests/test_docs_landing_pages.py docs/src/_static/tephpy.css
git commit -m "Give the reference quadrant a landing page of cards"
pixi run -e test pytest tests/test_docs_landing_pages.py tests/test_docs_snippets.py tests/test_citations.py tests/test_github_references.py -q --no-cov
```

Expected: every hook passes, and the tests pass on the committed tree.

---

### Task 5: The style guide's rule, and the signpost test's docstring

The rule a page author reads, rewritten for two shapes; it loses two stale claims on the way (`narrative spec §3.9`, §4's 2026-09-15 companion changes).

**Files:**
- Modify: `docs/src/developer/docs-style.rst` (the *Landing Pages* section)
- Modify: `tests/test_docs_snippets.py` (one docstring)

**Interfaces:**
- Consumes: the page and the gate as Tasks 1–4 left them.
- Produces: nothing a later task reads.

- [ ] **Step 1: Rewrite the section**

In `docs/src/developer/docs-style.rst`, replace everything from the `Landing Pages` heading up to, but not including, the `Topic Tags` heading with:

```rst
Landing Pages
-------------

A section landing page is navigation rather than prose, which is the rule above read
forwards: it carries no reading-time banner because nobody reads it through. Six
sections take one of two shapes, and both end in a hidden ``toctree``.

**A table**, in :doc:`getting started <../start/index>`, the tutorials, how-to and
explanation quadrants, and this developer guide. The page carries, in order, an
introduction, one two-column ``list-table``, and the ``toctree``.

The introduction says what the section is for, who it assumes the reader is, what
it guarantees of every page in it, and where to go if this is the wrong section.
It says nothing about an individual page. A paragraph that summarises the section
page by page is a list that has to track a directory, and the how-to page's grew
from six clauses to nine by hand before this rule existed.

Each row is a ``:doc:`` link against one sentence. The sentence is editorial rather
than descriptive: it is there so a reader can tell this page from its siblings, and
it is deliberately not the page's opening line, which a hover already shows. Write
``:widths: auto`` and no header row, which is the shape the API reference's own
summary tables already take.

**A grid of cards**, in the reference quadrant, whose pages are looked up by name
rather than chosen between. The page carries, in order, a one-sentence
introduction, a ``.. grid:: 1 2 2 2`` of cards, the guidance paragraphs, and the
``toctree``. The API card comes first and spans the row with ``:columns: 12``. One
column below 576px is not a matter of taste: two columns at that width split words
mid-word, which narrative spec §3.9 records measuring.

Each card takes its page's title — the API card excepted, because that page is
titled by the package name — a light and a dark icon from
``_static/cards/reference/``, and one sentence that tells it from the card beside
it. A card raises no hover tooltip, so its sentence may say what the page opens
with where that is clearest. Draw an icon in the root page's vocabulary; its dark
file differs from the light one only in the navy, ``#8FB8E8`` for ``#1B3A6B``, and
the knock-out halo, ``#14181e`` for ``#FFFFFF``.

The index and the toctree carry the same pages in the same order, and it is the
order a reader needs rather than the alphabet. Hiding a toctree hides it from the
page body only: the sidebar, the breadcrumb and the previous and next footer all
read its order. ``tests/test_docs_landing_pages.py`` fails when the two disagree,
in membership or in order; when an entry links outside its section; when the index
omits a page the section holds, which an ``:orphan:`` page would otherwise do
silently, since the build's own toctree check never sees one; and when the toctree
is not hidden, which would publish the same list twice. It reads a row's first
cell and a card's ``:link:``, and derives the API card's page from ``conf.py``,
since that page exists only while a build runs.

Glossary terms stay out of the cells and the cards. Both are directives, and
:ref:`the first-mention rule <glossary-rule>` already passes over a directive's
body, so a ``:term:`` in either neither satisfies that rule nor breaks it. Write
first mentions in the prose, and let a cell or a card take the plain word.
```

- [ ] **Step 2: Correct the signpost test's docstring**

In `tests/test_docs_snippets.py`, replace the docstring of `test_the_reference_index_sends_a_caller_to_the_hierarchy` with:

```python
    """The quadrant's own landing page otherwise omits the subject entirely.

    Its cards name what the reference holds, and none of them is the exception
    hierarchy, so without this paragraph a reader deciding what to catch has
    nothing to follow (:issue:`213`).
    """
```

- [ ] **Step 3: Lint and test**

```bash
pixi run -e devs pre-commit run --files docs/src/developer/docs-style.rst tests/test_docs_snippets.py
pixi run -e test pytest "tests/test_docs_snippets.py::test_the_reference_index_sends_a_caller_to_the_hierarchy" tests/test_citations.py -q --no-cov
```

Expected: every hook passes, including `design specification citations resolve`; the tests pass.

- [ ] **Step 4: Commit**

```bash
git add docs/src/developer/docs-style.rst tests/test_docs_snippets.py
git commit -m "Write the card shape into the landing-page rule"
```

---

### Task 6: Verify the branch and open the pull request

**Files:**
- Create: `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: everything above.
- Produces: the pull request.

- [ ] **Step 1: Run every gate on the committed tree**

```bash
git status --short
pixi run tests
pixi run lint
pixi run docs
```

Expected: `git status` prints nothing; the suite passes, and its count is higher than `main`'s by the new unit tests and the `[reference]` parametrisations; every hook passes; `pixi run docs` builds clean with every gate passing.

- [ ] **Step 2: Push and open the pull request**

Open it against `main` with the labels `type: documentation` and `type: testing`. Its description says what changed, what Step 7 of Task 4 printed for the two hovers, which way mutation (e) of Task 4 went, and any drawing redrawn in Task 3 and why. Attach the six renders from `/tmp/reference-page` and the icon sheet from Task 3.

- [ ] **Step 3: Add the fragment, named for the pull request**

Create `changelog/<PR>.documentation.rst`:

```rst
The reference quadrant's landing page is now a grid of seven cards, each with an
icon drawn in the root page's vocabulary, in place of an introduction that listed
its pages by hand (narrative spec §3.9). ``tests/test_docs_landing_pages.py``
holds the cards to the page's hidden toctree as it holds the other sections'
tables, and now refuses an entry that reaches outside its section with ``..``.
The root page's cards share the renamed ``teph-card`` classes, and its dark
*Tutorials* icon no longer rings its accent on the dark ground. (:user:`claude`)
```

```bash
git add changelog/<PR>.documentation.rst
git commit -m "Add the changelog fragment"
git push
```

Expected: the hooks pass, and `pixi run changelog --version 0.1.0 --draft` shows the entry under Documentation without writing or deleting anything.
