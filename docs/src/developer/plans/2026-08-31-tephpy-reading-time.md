# Reading Time Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `readingtime` Sphinx directive that estimates a page's reading time from the parsed doctree, and a pytest gate that keeps it on all 29 published pages a reader reads start to finish.

**Architecture:** Two modules under `docs/src/_ext`, split on the Sphinx boundary exactly as `tephpy_citations.py` and `tephpy_citation_xrefs.py` already are. `tephpy_reading.py` is stdlib-only — the rate, the word count, the argument grammar and the page scanner — so it runs in the CI test matrix, which carries no Sphinx. `tephpy_readingtime.py` is the Sphinx half: a directive that returns an unregistered placeholder node, and a `doctree-read` handler that counts the parsed document and replaces the placeholder with the banner. The gate reads page text and imports only the stdlib half, so directive and gate share one definition of what a word is.

**Tech Stack:** Python 3.12+, docutils/Sphinx 8+ (`SphinxDirective`, the `doctree-read` event), pydata-sphinx-theme (Font Awesome 7.2.0, CSS custom properties), pytest, pre-commit.

**Spec:** [`../specs/2026-08-31-reading-time-design.md`](../specs/2026-08-31-reading-time-design.md) — cited below as `reading spec §N`. Read it alongside this plan; every task argues from a section of it.

## Global Constraints

- Every source file carries the BSD copyright header (ruff `CPY001`); the exact notice is in `[tool.ruff.lint.flake8-copyright]` in `pyproject.toml`.
- `line-length = 88`; ruff `select = ["ALL"]` with the ignore list in `pyproject.toml`. `docs/src/_ext/*.py` additionally ignores `INP001` — the directory is a `sys.path` entry, not a package, and must not gain an `__init__.py`.
- ruff isort: `force-sort-within-sections = true`, `required-imports = ["from __future__ import annotations"]`, `known-first-party = ["tephpy"]`.
- numpydoc docstring convention (`[tool.ruff.lint.pydocstyle] convention = "numpy"`). numpydoc *validation* runs over `^src/` only, so `docs/src/_ext` needs docstrings but not the full validated section set. Match the house style of `tephpy_citations.py`: summary, `Parameters`, `Returns`/`Yields`, `Notes` with `.. versionadded:: 0.1.0` last.
- `[tool.pytest.ini_options]` sets `filterwarnings = ["error"]` — a warning in a test is a failure.
- The docs build is `--fail-on-warning --keep-going` (`docs/Makefile:1`). Any Sphinx warning fails `pixi run docs`.
- **The two modules are `tephpy_`-prefixed top-level names**, because `docs/src/_ext` sits at `sys.path[0]` for the whole build ({issue}`92`). `tephpy_readingtime.py` imports its sibling as `import tephpy_reading`, the idiom `tephpy_citation_xrefs.py:39` already uses.
- Sphinx is in the `docs` pixi feature and **not** in `test`. Anything importing Sphinx is guarded with `pytest.importorskip("sphinx")` and skips in the `test-py3*` matrix (reading spec §3.1, decision 4).
- Every PR adds `changelog/<PR>.<type>.rst` ending with ``(:user:`claude`)``.
- **Everything in this plan lands together** (reading spec §4). The gate ahead of the directive fails every page; the directive ahead of the gate is unenforced. Tasks commit individually, but the branch is not mergeable until Task 7.

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/src/_ext/tephpy_reading.py` | **Create.** Stdlib only. `WPM`, `count_words`, `estimate_minutes`, `Argument`/`parse_argument`, and the page scanner (`first_section_line`, `title_line`, `directive_lines`, `carries_reading_time`). |
| `docs/src/_ext/tephpy_readingtime.py` | **Create.** The Sphinx half: `readingtime` placeholder node, `ReadingTimeDirective`, `count_doctree_words`, the `doctree-read` handler, `setup`. |
| `tests/test_docs_readingtime.py` | **Create.** Stdlib only: the rate, the word count, the argument grammar, the page scanner, the corpus and the coverage gate. Runs on every supported Python. |
| `tests/test_readingtime_directive.py` | **Create.** The Sphinx half: the directive, the doctree transform and the banner. `pytest.importorskip("sphinx")` at module level, so the whole module skips in the `test-py3*` matrix — the split `tests/test_citations.py` and `tests/test_citation_xrefs.py` already make, and the reason it is a second file rather than a second section. |
| `docs/src/conf.py` | **Modify.** `tephpy_readingtime` in `extensions`. |
| `docs/src/_static/tephpy.css` | **Modify.** The `.reading-time` rule. |
| `docs/src/refs.bib` | **Modify.** The two entries of reading spec §3.4. |
| `docs/src/developer/docs-style.rst` | **Modify.** A *Reading Time* section after *Published Figures*. |
| 29 published pages | **Modify.** One directive each, in the page lead. |
| `changelog/<PR>.documentation.rst` | **Create.** Fragment. |

One companion change of reading spec §4 is **already done**: `docs/src/developer/specs/index.rst` gained the `reading spec §…` row and its toctree entry in the commit that added the specification. Do not add it again.

### The corpus, measured

Enumerated from `docs/src` on 2026-08-31. **41 published pages: 12 exempt, 29 carrying.**

The 29, with the 1-indexed line the directive goes *after* — the title underline for reStructuredText, the `# ` heading for MyST:

| page | insert after line |
|---|---|
| `developer/docs-style.rst` | 2 |
| `developer/packaging.rst` | 4 |
| `developer/specs/2026-07-22-tephpy-design.md` | 1 |
| `developer/specs/2026-08-01-add-logo-design.md` | 1 |
| `developer/specs/2026-08-03-published-specs-design.md` | 1 |
| `developer/specs/2026-08-07-config-file-design.md` | 1 |
| `developer/specs/2026-08-12-config-domain-validation-design.md` | 1 |
| `developer/specs/2026-08-13-dependency-floors-design.md` | 1 |
| `developer/specs/2026-08-17-published-figures-design.md` | 1 |
| `developer/specs/2026-08-20-examples-gallery-design.md` | 1 |
| `developer/specs/2026-08-25-framing-design.md` | 1 |
| `developer/specs/2026-08-25-scope-and-support-design.md` | 1 |
| `developer/specs/2026-08-27-narrative-quadrants-design.md` | 1 |
| `developer/specs/2026-08-29-api-visibility-design.md` | 1 |
| `developer/specs/2026-08-31-reading-time-design.md` | 1 |
| `explanation/parcel-ascent.rst` | 4 |
| `explanation/rotated-axes.rst` | 4 |
| `howtos/build-a-sounding.rst` | 4 |
| `howtos/configuration.rst` | 4 |
| `howtos/emphasis.rst` | 4 |
| `howtos/framing.rst` | 4 |
| `howtos/label-and-compose.rst` | 4 |
| `howtos/logo.rst` | 4 |
| `howtos/read-a-sounding.rst` | 4 |
| `howtos/temp-and-bufr.rst` | 4 |
| `howtos/units.rst` | 4 |
| `tutorials/analyse-a-sounding.rst` | 4 |
| `tutorials/browser-demo.rst` | 2 |
| `tutorials/first-tephigram.rst` | 4 |

The two reStructuredText pages inserting after line 2 (`docs-style.rst`, `browser-demo.rst`) are the two with no `.. _label:` target above the title. Line numbers are as of 2026-08-31 and are a convenience, not the rule — the rule is "after the title, before the first section heading", and Task 4's gate is what enforces it.

The 12 exempt, which Task 4 hardcodes:

`index.rst`, `tutorials/index.rst`, `howtos/index.rst`, `explanation/index.rst`, `reference/index.rst`, `developer/index.rst`, `developer/specs/index.rst`, `reference/changelog.rst`, `reference/cli.rst`, `reference/config.rst`, `reference/references.rst`, `reference/glossary.rst`.

---

### Task 1: The rate, the word count, and the argument grammar

Reading spec §3.2 and §3.4. Stdlib only, so these run on every supported Python.

**Files:**
- Create: `docs/src/_ext/tephpy_reading.py`
- Create: `tests/test_docs_readingtime.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `WPM: int` (150); `count_words(text: str) -> int`; `estimate_minutes(words: int, wpm: int = WPM) -> int`; a frozen dataclass `Argument` with fields `minutes: int | None` and `wpm: int`; and `parse_argument(argument: str | None) -> Argument`, which raises `ValueError` on anything else. Task 2 adds the scanner to the same module; Task 3 imports all of the above.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_docs_readingtime.py
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the reading-time directive and its coverage gate (reading spec §6)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
DOCS = REPO / "docs" / "src"
EXT = DOCS / "_ext"


def _load(name: str):
    """Import an extension module by path; ``_ext`` is not an importable package."""
    path = EXT / f"{name}.py"
    assert path.is_file(), f"the module is missing from {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# `_ext` is a `sys.path` entry at build time rather than a package, so a module
# there resolves its siblings by top-level name and cannot be imported until that
# entry exists (:issue:`92`).
if str(EXT) not in sys.path:
    sys.path.insert(0, str(EXT))

reading = _load("tephpy_reading")


def test_the_default_rate_is_the_one_the_specification_cites():
    """reading spec §3.4 fixes 150, below Brysbaert's 175 non-fiction floor."""
    assert reading.WPM == 150


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),
        ("one", 1),
        ("one two three", 3),
        # `\w+` splits on punctuation, so a dotted name counts as its parts. The
        # banner and the gate must agree on that, which is why it is pinned.
        ("tephpy.plotting.axes", 3),
        ("hyphen-ated", 2),
        ("   spaced   out   ", 2),
        ("newlines\nare\nwhitespace", 3),
    ],
)
def test_count_words_counts_word_character_runs(text, expected):
    assert reading.count_words(text) == expected


@pytest.mark.parametrize(
    ("words", "wpm", "expected"),
    [
        (0, 150, 1),      # the floor: no page reads in zero minutes
        (1, 150, 1),
        (150, 150, 1),
        (151, 150, 2),    # rounds up, never down
        (300, 150, 2),
        (1500, 150, 10),
        (300, 100, 3),    # the rate is honoured
    ],
)
def test_estimate_minutes_rounds_up_with_a_floor_of_one(words, wpm, expected):
    assert reading.estimate_minutes(words, wpm) == expected


def test_estimate_minutes_defaults_to_the_house_rate():
    assert reading.estimate_minutes(300) == reading.estimate_minutes(300, reading.WPM)


@pytest.mark.parametrize(
    ("argument", "minutes", "wpm"),
    [
        (None, None, 150),      # no argument: count at the house rate
        ("30", 30, 150),        # a literal duration, quoted not counted
        ("1", 1, 150),
        ("200wpm", None, 200),  # a rate override; the count still happens
        ("200WPM", None, 200),  # case-insensitive
        ("90wpm", None, 90),
    ],
)
def test_parse_argument_reads_the_two_documented_shapes(argument, minutes, wpm):
    parsed = reading.parse_argument(argument)
    assert parsed.minutes == minutes
    assert parsed.wpm == wpm


@pytest.mark.parametrize(
    "argument",
    [
        "thirty",       # the prior art computes an estimate here and warns nobody
        "",
        "10 minutes",
        "wpm",
        "0wpm",         # a zero rate would divide by zero
        "0",            # a zero-minute page is not a duration
        "-5",
        "12wpmx",       # anchored at both ends
        "x200wpm",
    ],
)
def test_parse_argument_rejects_anything_else(argument):
    """reading spec §3.2: an argument the directive cannot read stops the build."""
    with pytest.raises(ValueError, match="readingtime"):
        reading.parse_argument(argument)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pixi run -e test pytest tests/test_docs_readingtime.py -x -q`

Expected: collection fails at `_load("tephpy_reading")` with `AssertionError: the module is missing from .../tephpy_reading.py`.

- [ ] **Step 3: Write the minimal implementation**

```python
# docs/src/_ext/tephpy_reading.py
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""The reading-time model, shared by the directive and its gate (reading spec §3.1).

One definition of what a word is, what the rate is, and where the directive is
allowed to sit -- shared by the ``readingtime`` directive (reading spec §3.2) and
the coverage gate (reading spec §3.6). Two copies would agree until one of them
was amended, and a gate that counted differently from the banner it polices would
be checking a different page than the one it published.

Nothing here is imported from outside the standard library, so this module runs in
the CI test matrix, which carries no Sphinx.

The ``tephpy_`` prefix claims a top-level name this repository owns, because
``docs/src/_ext`` sits at ``sys.path[0]`` for the whole build (:issue:`92`). It is
not part of the installed package -- nothing under ``docs/`` is.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re

WPM: int = 150
"""Words-per-minute reading rate for technical documentation (reading spec §3.4).

Below the 175 wpm floor Brysbaert (2019) reports for ordinary non-fiction prose,
because these pages alternate argument with code the reader parses line by line.
"""

WORD = re.compile(r"\w+")
"""What counts as a word. Taken from the prior art, and shared rather than better."""

ARGUMENT = re.compile(r"\A(?:(?P<wpm>[1-9]\d*)wpm|(?P<minutes>[1-9]\d*))\Z", re.IGNORECASE)
"""The directive's two argument shapes, anchored at both ends (reading spec §3.2)."""


@dataclass(frozen=True)
class Argument:
    """A parsed ``readingtime`` argument.

    Attributes
    ----------
    minutes : int or None
        A literal duration to quote, or ``None`` to count the page.
    wpm : int
        The rate to count at.

    Notes
    -----
    .. versionadded:: 0.1.0

    """

    minutes: int | None
    wpm: int


def count_words(text: str) -> int:
    """Count the words in ``text``.

    Parameters
    ----------
    text : str
        The text to count.

    Returns
    -------
    int
        The number of word-character runs.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    return len(WORD.findall(text))


def estimate_minutes(words: int, wpm: int = WPM) -> int:
    """Convert a word count to a reading time in minutes.

    Parameters
    ----------
    words : int
        The number of words on the page.
    wpm : int, optional
        The reading rate. It defaults to :data:`WPM`.

    Returns
    -------
    int
        The estimate, rounded up, and never below one: a page a reader has
        opened costs them a minute even when it is a sentence long.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    return max(1, math.ceil(words / wpm))


def parse_argument(argument: str | None) -> Argument:
    """Read the directive's optional argument.

    Parameters
    ----------
    argument : str or None
        ``None`` when the directive was given no argument, ``"30"`` for a
        literal duration in minutes, or ``"200wpm"`` for a rate override.

    Returns
    -------
    Argument
        The duration to quote, if any, and the rate to count at.

    Raises
    ------
    ValueError
        For any other argument. The prior art falls back to computing an
        estimate here, so ``.. readingtime:: thirty`` publishes a number its
        author did not ask for and never sees a warning. The docs build is
        ``--fail-on-warning``, so refusing is what surfaces the mistake.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    if argument is None:
        return Argument(minutes=None, wpm=WPM)
    match = ARGUMENT.match(argument.strip())
    if match is None:
        msg = (
            f"readingtime: expected no argument, a duration in minutes such as "
            f"'30', or a rate such as '200wpm'; got {argument!r}"
        )
        raise ValueError(msg)
    if match["wpm"] is not None:
        return Argument(minutes=None, wpm=int(match["wpm"]))
    return Argument(minutes=int(match["minutes"]), wpm=WPM)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pixi run -e test pytest tests/test_docs_readingtime.py -q`

Expected: PASS, 30 tests.

- [ ] **Step 5: Lint**

Run: `pixi run -e devs ruff check docs/src/_ext/tephpy_reading.py tests/test_docs_readingtime.py && pixi run -e devs ruff format --check docs/src/_ext/tephpy_reading.py tests/test_docs_readingtime.py`

Expected: no findings. If `ARGUMENT`'s line exceeds 88 characters, wrap the pattern across two implicitly-concatenated strings rather than adding a `noqa` — snippets carry no linter directives.

- [ ] **Step 6: Commit**

```bash
git add docs/src/_ext/tephpy_reading.py tests/test_docs_readingtime.py
git commit -m "Add the reading-time rate, word count and argument grammar"
```

---

### Task 2: The page scanner

Reading spec §3.6. Still stdlib only. This is what the gate uses to decide whether a page carries the directive *in its lead*, and it is the half that cannot reuse `tephpy_citations.read_lines`.

**Files:**
- Modify: `docs/src/_ext/tephpy_reading.py`
- Modify: `tests/test_docs_readingtime.py`

**Interfaces:**
- Consumes: nothing from Task 1 beyond the module it extends.
- Produces: `myst_scan(text: str) -> Iterator[tuple[int, str, str | None]]` yielding `(line_number, line, opening_info)` for column-0 lines outside a fence, where `opening_info` is the stripped info string when the line *opens* a fence and `None` otherwise; `title_line(text: str, suffix: str) -> int | None`; `first_section_line(text: str, suffix: str) -> int | None`; `directive_lines(text: str, suffix: str) -> list[int]`; and `carries_reading_time(text: str, suffix: str) -> bool`. `suffix` is `".rst"` or `".md"`. Task 4 consumes `carries_reading_time`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_docs_readingtime.py`:

```python
RST_PAGE = """\
.. _howto-example:

An Example Page
===============

.. readingtime::

A lead paragraph.

A Section
---------

Body text.
"""

MYST_PAGE = """\
# An Example Specification

```{readingtime}
```

> **Living document.**

(example-spec-1)=
## 1. Purpose

Body text.
"""


def test_the_rst_title_is_the_first_underline():
    assert reading.title_line(RST_PAGE, ".rst") == 4


def test_the_rst_first_section_is_the_second_underline():
    assert reading.first_section_line(RST_PAGE, ".rst") == 11


def test_a_page_with_no_sections_has_no_first_section():
    text = "Only a Title\n============\n\n.. readingtime::\n\nBody.\n"
    assert reading.first_section_line(text, ".rst") is None
    assert reading.carries_reading_time(text, ".rst")


def test_the_myst_title_is_the_first_atx_heading():
    assert reading.title_line(MYST_PAGE, ".md") == 1


def test_the_myst_first_section_is_the_first_level_two_heading():
    assert reading.first_section_line(MYST_PAGE, ".md") == 9


def test_a_directive_in_the_lead_satisfies_the_rule():
    assert reading.carries_reading_time(RST_PAGE, ".rst")
    assert reading.carries_reading_time(MYST_PAGE, ".md")


def test_a_page_without_the_directive_does_not():
    assert not reading.carries_reading_time(RST_PAGE.replace(".. readingtime::\n", ""), ".rst")


def test_a_directive_after_the_first_section_does_not_satisfy_the_rule():
    """reading spec §3.6, decision 5: the banner is for a reader who has not scrolled."""
    moved = RST_PAGE.replace(".. readingtime::\n\n", "").replace(
        "Body text.\n", ".. readingtime::\n\nBody text.\n"
    )
    assert reading.directive_lines(moved, ".rst")
    assert not reading.carries_reading_time(moved, ".rst")


def test_an_indented_directive_is_a_demonstration_and_does_not_count():
    """What lets `docs-style.rst` show the directive and carry a live one."""
    shown = RST_PAGE.replace(".. readingtime::", ".. code::\n\n       .. readingtime::")
    assert reading.directive_lines(shown, ".rst") == []
    assert not reading.carries_reading_time(shown, ".rst")


def test_the_myst_directive_is_found_although_it_is_itself_a_fence():
    """reading spec §3.6: a fence-skipping reader cannot see the opening rail."""
    assert reading.directive_lines(MYST_PAGE, ".md") == [3]


def test_a_directive_quoted_inside_a_myst_fence_does_not_count():
    quoted = MYST_PAGE.replace(
        "Body text.\n",
        "````\n```{readingtime}\n```\n````\n",
    )
    assert reading.directive_lines(quoted, ".md") == [3]


def test_a_heading_inside_a_myst_fence_is_not_a_section():
    """The defect `tephpy_citations.read_lines` documents, in the other direction."""
    fenced = MYST_PAGE.replace("Body text.\n", "```\n## Not a heading\n```\n")
    assert reading.first_section_line(fenced, ".md") == 9


def test_the_myst_scanner_keeps_the_rail_discipline():
    """A four-backtick block may quote a three-backtick one without closing."""
    text = "# Title\n\n````\n```\n## quoted\n```\n````\n\n## 1. Real\n"
    assert reading.first_section_line(text, ".md") == 9
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pixi run -e test pytest tests/test_docs_readingtime.py -q -k "title or section or directive or scanner or fence"`

Expected: FAIL with `AttributeError: module 'tephpy_reading' has no attribute 'title_line'`.

- [ ] **Step 3: Write the minimal implementation**

Add to `docs/src/_ext/tephpy_reading.py`. Extend the `typing` import block at the top with `from typing import TYPE_CHECKING`, and under it `if TYPE_CHECKING: from collections.abc import Iterator`.

```python
FENCE = re.compile(r"\A(?P<rail>`{3,}|~{3,})(?P<info>.*)\Z")
"""A MyST fence at column 0. Indented fences are content, not page structure."""

UNDERLINE = re.compile(r"""\A(?P<char>[=\-~^"'`#*+:.])(?P=char){2,}[ \t]*\Z""")
"""A reStructuredText section underline at column 0, three characters or more."""

RST_DIRECTIVE = re.compile(r"\A\.\. readingtime::")
"""The directive at column 0. Indented, it is a demonstration (reading spec §3.6)."""

MYST_DIRECTIVE = "{readingtime}"
"""The info string of the fence that opens the directive in MyST."""

MYST_HEADING = "## "
"""The first section heading in a specification, whose title is a single ``#``."""


def myst_scan(text: str) -> Iterator[tuple[int, str, str | None]]:
    """Yield the column-0 lines of ``text`` that sit outside a fenced block.

    A MyST directive *is* a fence, and its opening rail carries the info string
    naming it -- so unlike ``tephpy_citations.read_lines``, which skips a fence
    whole, this reader yields the opening rail and reports its info string. A
    reader that skipped it could not see the thing the gate looks for.

    The rail discipline is the one that module documents: a block opened with
    four backticks may quote a three-backtick block, so a fence closes only on a
    rail of the same character, at least as long, carrying no info string.

    Parameters
    ----------
    text : str
        The file contents.

    Yields
    ------
    tuple of (int, str, str or None)
        The 1-indexed line number, the line, and -- when the line opens a fence
        -- its stripped info string.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    rail: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        fence = FENCE.match(line)
        if fence is not None:
            found, info = fence["rail"], fence["info"].strip()
            if rail is None:
                rail = found
                yield number, line, info
                continue
            if found[0] == rail[0] and len(found) >= len(rail) and not info:
                rail = None
                continue
        if rail is None:
            yield number, line, None


def _underlines(text: str) -> list[int]:
    """Return the 1-indexed lines that underline a title or section heading."""
    lines = text.splitlines()
    found: list[int] = []
    for number, line in enumerate(lines, start=1):
        if UNDERLINE.match(line) is None:
            continue
        # A transition -- four dashes on their own -- underlines nothing. A real
        # underline sits under text and is at least as long as it.
        above = lines[number - 2].rstrip() if number >= 2 else ""
        if above and len(line.rstrip()) >= len(above):
            found.append(number)
    return found


def title_line(text: str, suffix: str) -> int | None:
    """Return the 1-indexed line of the page title.

    Parameters
    ----------
    text : str
        The page source.
    suffix : str
        ``".rst"`` or ``".md"``.

    Returns
    -------
    int or None
        The title underline for reStructuredText, the ``# `` heading for MyST,
        or ``None`` for a page with no title.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    if suffix == ".md":
        for number, line, _ in myst_scan(text):
            if line.startswith("# "):
                return number
        return None
    underlines = _underlines(text)
    return underlines[0] if underlines else None


def first_section_line(text: str, suffix: str) -> int | None:
    """Return the 1-indexed line of the first section heading below the title.

    Parameters
    ----------
    text : str
        The page source.
    suffix : str
        ``".rst"`` or ``".md"``.

    Returns
    -------
    int or None
        ``None`` when the page has a title and no sections, in which case the
        whole page is its lead.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    if suffix == ".md":
        for number, line, _ in myst_scan(text):
            if line.startswith(MYST_HEADING):
                return number
        return None
    underlines = _underlines(text)
    return underlines[1] if len(underlines) > 1 else None


def directive_lines(text: str, suffix: str) -> list[int]:
    """Return the 1-indexed lines carrying the directive at column 0.

    Parameters
    ----------
    text : str
        The page source.
    suffix : str
        ``".rst"`` or ``".md"``.

    Returns
    -------
    list of int
        Every occurrence, in document order. Column 0 is what excludes a
        demonstration inside a literal block (reading spec §3.6).

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    if suffix == ".md":
        return [
            number
            for number, _, info in myst_scan(text)
            if info == MYST_DIRECTIVE
        ]
    return [
        number
        for number, line in enumerate(text.splitlines(), start=1)
        if RST_DIRECTIVE.match(line) is not None
    ]


def carries_reading_time(text: str, suffix: str) -> bool:
    """Report whether the page carries the directive in its lead.

    Parameters
    ----------
    text : str
        The page source.
    suffix : str
        ``".rst"`` or ``".md"``.

    Returns
    -------
    bool
        ``True`` when at least one column-0 directive sits after the title and
        before the first section heading.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    title = title_line(text, suffix)
    if title is None:
        return False
    section = first_section_line(text, suffix)
    return any(
        number > title and (section is None or number < section)
        for number in directive_lines(text, suffix)
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pixi run -e test pytest tests/test_docs_readingtime.py -q`

Expected: PASS.

- [ ] **Step 5: Lint, then commit**

```bash
pixi run -e devs ruff check docs/src/_ext/tephpy_reading.py tests/test_docs_readingtime.py
pixi run -e devs ruff format --check docs/src/_ext/tephpy_reading.py tests/test_docs_readingtime.py
git add docs/src/_ext/tephpy_reading.py tests/test_docs_readingtime.py
git commit -m "Add the reading-time page scanner"
```

---

### Task 3: The directive, the transform, and the banner

Reading spec §3.2, §3.3 and §3.5. This task is Sphinx-side, so its tests are guarded and skip in the CI matrix.

**Files:**
- Create: `docs/src/_ext/tephpy_readingtime.py`
- Create: `tests/test_readingtime_directive.py`
- Modify: `docs/src/conf.py`
- Modify: `docs/src/_static/tephpy.css`

> **Why a second test module.** `pytest.importorskip` at module level skips the module it is
> in. Putting the Sphinx guard inside `tests/test_docs_readingtime.py` would therefore skip
> Task 1, 2, 4 and 5's tests too, in exactly the environments — the `test-py3*` matrix —
> that the stdlib half exists to run in. The repository already splits for this reason:
> `tests/test_citations.py` runs everywhere and `tests/test_citation_xrefs.py` guards.

**Interfaces:**
- Consumes: `tephpy_reading.parse_argument`, `.count_words`, `.estimate_minutes`, `.WPM` from Task 1.
- Produces: the `readingtime` node class; `ReadingTimeDirective`; `count_doctree_words(doctree) -> int`; `resolve(app, doctree) -> None`, the `doctree-read` handler; `setup(app) -> dict`. Nothing later consumes these directly — Task 5's pages consume the *directive name*, `readingtime`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_readingtime_directive.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the reading-time directive and its transform (reading spec §6)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
EXT = REPO / "docs" / "src" / "_ext"

# The directive imports Sphinx, which only the `docs` feature installs, so this
# module is unimportable in the `test-py3*` environments the CI matrix runs. It is
# importable in the default environment, which is what `pixi run tests` resolves
# to, so these run for anyone using the project's own test command. The stdlib
# half lives in `tests/test_docs_readingtime.py`, which must not carry this guard.
pytest.importorskip("sphinx", reason="the docs feature is not installed here")
nodes = pytest.importorskip("docutils.nodes")
new_document = pytest.importorskip("docutils.utils").new_document
frontend = pytest.importorskip("docutils.frontend")
parsers = pytest.importorskip("docutils.parsers.rst")

if str(EXT) not in sys.path:
    sys.path.insert(0, str(EXT))


def _load(name: str):
    """Import an extension module by path; ``_ext`` is not an importable package."""
    path = EXT / f"{name}.py"
    assert path.is_file(), f"the module is missing from {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


reading = _load("tephpy_reading")
readingtime = _load("tephpy_readingtime")


def _doctree(*children):
    """Return as much of a parsed document as the transform reads."""
    settings = frontend.get_default_settings(parsers.Parser)
    document = new_document("<test>", settings)
    document += list(children)
    return document


def _para(text):
    para = nodes.paragraph()
    para += nodes.Text(text)
    return para


def test_the_transform_counts_the_text_a_reader_sees():
    """Prose and code count; a comment does not (reading spec §3.3)."""
    comment = nodes.comment()
    comment += nodes.Text("eight words that nobody reads at all here")
    doctree = _doctree(
        _para("one two three four five"),
        nodes.literal_block(text="alpha = beta"),
        comment,
    )
    # five prose words, plus `alpha`, `beta` from the code block.
    assert readingtime.count_doctree_words(doctree) == 7


def test_the_transform_skips_raw_and_system_message_text():
    raw = nodes.raw("", "<i class='fa-solid fa-clock'></i>", format="html")
    doctree = _doctree(_para("one two"), raw)
    assert readingtime.count_doctree_words(doctree) == 2


def test_a_title_is_counted_once_and_not_twice():
    """reading spec §6. A section carries its title as a child, and the document
    carries the section -- a walk that counted both would double every heading."""
    section = nodes.section()
    title = nodes.title()
    title += nodes.Text("one two three")
    section += title
    section += _para("four five")
    doctree = _doctree(section)
    assert readingtime.count_doctree_words(doctree) == 5


def test_the_directive_returns_an_unresolved_placeholder():
    node = readingtime.readingtime(minutes=None, wpm=200)
    assert node["minutes"] is None
    assert node["wpm"] == 200


def test_the_handler_replaces_the_placeholder_with_a_banner():
    placeholder = readingtime.readingtime(minutes=None, wpm=reading.WPM)
    doctree = _doctree(placeholder, _para(" ".join(["word"] * 300)))
    readingtime.resolve(None, doctree)
    assert not list(doctree.findall(readingtime.readingtime))
    banner = next(doctree.findall(nodes.container))
    assert "reading-time" in banner["classes"]
    assert "2 minutes" in banner.astext()


def test_a_literal_duration_is_quoted_and_the_page_is_not_counted():
    """reading spec §3.2: the escape hatch quotes, it does not estimate."""
    placeholder = readingtime.readingtime(minutes=45, wpm=reading.WPM)
    doctree = _doctree(placeholder, _para("three short words"))
    readingtime.resolve(None, doctree)
    banner = next(doctree.findall(nodes.container))
    assert "45 minutes" in banner.astext()


def test_a_one_minute_page_is_singular():
    placeholder = readingtime.readingtime(minutes=1, wpm=reading.WPM)
    doctree = _doctree(placeholder)
    readingtime.resolve(None, doctree)
    banner = next(doctree.findall(nodes.container))
    assert "1 minute" in banner.astext()
    assert "minutes" not in banner.astext()


def test_the_placeholder_node_is_not_registered_with_sphinx():
    """reading spec §3.2: a leaked placeholder must fail the build, not publish blank."""
    source = (EXT / "tephpy_readingtime.py").read_text(encoding="utf-8")
    assert "add_node" not in source
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pixi run pytest tests/test_readingtime_directive.py -q`

Expected: FAIL at `_load("tephpy_readingtime")`.

- [ ] **Step 3: Write the minimal implementation**

```python
# docs/src/_ext/tephpy_readingtime.py
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Publish an estimated reading time on a documentation page (reading spec §3.2).

The count comes from the parsed doctree rather than from the page source, so
directive options, comment blocks and MyST front matter are not counted as words
a reader reads, and a page body generated by another directive is (reading spec
§3.3). That is why the work happens on ``doctree-read`` and not in ``run()``:
the directive returns a placeholder, and the handler below fills it in once the
document it is measuring exists.

The rate, the word pattern and the argument grammar live in ``tephpy_reading``,
which the gate of reading spec §3.6 imports too. Keeping them there is what makes
them testable: the CI test matrix has no Sphinx.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes
from sphinx.util.docutils import SphinxDirective

import tephpy_reading

if TYPE_CHECKING:
    from sphinx.application import Sphinx

SKIP = (nodes.system_message, nodes.comment, nodes.raw)
"""Doctree text a reader never reads (reading spec §3.3)."""

ICON = '<i class="fa-solid fa-clock"></i>'
"""The clock, as pydata-sphinx-theme's own markup for a Font Awesome glyph.

Raw HTML rather than a CSS ``::before`` glyph, because the CSS route would need
``font-family: "Font Awesome 7 Free"`` written into this project's stylesheet and
would break silently on a theme upgrade to Font Awesome 8. The theme emits this
same element throughout the built site, so it costs no assets (reading spec §3.5).
"""


class readingtime(nodes.Element):  # noqa: N801
    """A placeholder standing where the banner goes until the document is parsed.

    Deliberately **not** registered with ``app.add_node``. If the handler below
    ever fails to fire, Sphinx reports ``unknown node type`` and exits non-zero,
    which ``--fail-on-warning`` turns into a build failure -- where a registered
    node would publish a blank space quietly (reading spec §3.2).

    Notes
    -----
    .. versionadded:: 0.1.0

    """


class ReadingTimeDirective(SphinxDirective):
    """Emit a reading-time banner for the page it appears on.

    Notes
    -----
    .. versionadded:: 0.1.0

    """

    has_content = False
    optional_arguments = 1
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        """Return the placeholder the ``doctree-read`` handler resolves.

        Returns
        -------
        list of docutils.nodes.Node
            A single unresolved :class:`readingtime` element.

        Raises
        ------
        docutils.parsers.rst.states.MarkupError
            When the argument matches neither documented shape.

        Notes
        -----
        .. versionadded:: 0.1.0

        """
        argument = self.arguments[0] if self.arguments else None
        try:
            parsed = tephpy_reading.parse_argument(argument)
        except ValueError as error:
            raise self.error(str(error)) from error
        return [readingtime(minutes=parsed.minutes, wpm=parsed.wpm)]


def count_doctree_words(doctree: nodes.document) -> int:
    """Count the words a reader reads on the parsed page.

    Parameters
    ----------
    doctree : docutils.nodes.document
        The parsed document.

    Returns
    -------
    int
        The words in every text node not descended from :data:`SKIP`.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    total = 0
    for text in doctree.findall(nodes.Text):
        node = text.parent
        while node is not None and not isinstance(node, SKIP):
            node = node.parent
        if node is None:
            total += tephpy_reading.count_words(text.astext())
    return total


def banner(minutes: int) -> nodes.container:
    """Build the banner for a page of ``minutes`` minutes.

    Parameters
    ----------
    minutes : int
        The estimate to publish.

    Returns
    -------
    docutils.nodes.container
        Real docutils nodes rather than a raw HTML block, so a non-HTML builder
        and text extraction both see the estimate (reading spec §3.5).

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    plural = "" if minutes == 1 else "s"
    paragraph = nodes.paragraph()
    paragraph += nodes.raw("", ICON, format="html")
    paragraph += nodes.Text(f" Estimated reading time: {minutes} minute{plural}")
    container = nodes.container(classes=["reading-time"])
    container += paragraph
    return container


def resolve(app: Sphinx, doctree: nodes.document) -> None:  # noqa: ARG001
    """Replace each placeholder on this page with its banner.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application. Unread: the count is a property of the page alone.
    doctree : docutils.nodes.document
        The parsed document, counted once however many placeholders it carries.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    placeholders = list(doctree.findall(readingtime))
    if not placeholders:
        return
    words = count_doctree_words(doctree)
    for node in placeholders:
        minutes = node["minutes"]
        if minutes is None:
            minutes = tephpy_reading.estimate_minutes(words, node["wpm"])
        node.replace_self(banner(minutes))


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the directive and its transform.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.

    Returns
    -------
    dict
        The extension metadata.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    app.add_directive("readingtime", ReadingTimeDirective)
    app.connect("doctree-read", resolve)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
```

> **Note on `# noqa`.** Two are unavoidable and are code, not documentation snippets: `N801` because the node class name is the directive name, which docutils convention lowercases, and `ARG001` because `doctree-read` passes `app` positionally. If ruff's configured ignore list already covers either, drop that `noqa` — `python-check-blanket-noqa` requires the rule code, and an unused one is itself a finding.

- [ ] **Step 4: Register the extension**

In `docs/src/conf.py`, add `"tephpy_readingtime",` to `extensions`, immediately after `"tephpy_config_reference",`:

```python
    "tephpy_config_reference",
    "tephpy_readingtime",
]
```

- [ ] **Step 5: Add the stylesheet rule**

Append to `docs/src/_static/tephpy.css`:

```css

/*
 * The reading-time banner (reading spec §3.5).
 *
 * The three custom properties are pydata-sphinx-theme's own and follow its
 * light/dark toggle. They are named here rather than borrowed from the prior
 * art because a CSS custom property that resolves to nothing fails silently:
 * GeoVista's `readingtime.css` styles this banner with `--article-info-bg` and
 * `--article-info-fg`, which are defined neither there nor in the theme, so its
 * background falls back to transparent and its colour to inherited.
 */
.reading-time {
  align-items: center;
  background: var(--pst-color-surface);
  border-left: 4px solid var(--pst-color-accent);
  border-radius: 4px;
  color: var(--pst-color-text-muted);
  display: flex;
  gap: 0.6em;
  margin-bottom: 1.2em;
  padding: 0.6em 1em;
}

.reading-time p {
  margin: 0;
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `pixi run pytest tests/test_readingtime_directive.py tests/test_docs_readingtime.py -q`

Expected: PASS. Then run `pixi run -e test-py312 pytest tests/test_readingtime_directive.py tests/test_docs_readingtime.py -q` and confirm that `test_readingtime_directive.py` **skips whole** while `test_docs_readingtime.py` **runs**. That asymmetry is the split of reading spec §3.1, and this is the only place it is observable.

- [ ] **Step 7: Verify the directive renders, end to end**

Add `.. readingtime::` to a scratch page and build. The fastest honest check is the real build:

```bash
pixi run docs
grep -o 'reading-time[^<]*<[^>]*>[^<]*' docs/_build/html/howtos/logo.html
```

Expected at this point: the build succeeds and the grep finds **nothing**, because no page carries the directive yet. That is the correct result for this task — the extension is registered and inert. Task 5 is where the banner appears.

- [ ] **Step 8: Commit**

```bash
pixi run -e devs ruff check docs/src/_ext/tephpy_readingtime.py tests/test_readingtime_directive.py
pixi run -e devs ruff format --check docs/src/_ext/tephpy_readingtime.py tests/test_readingtime_directive.py
git add docs/src/_ext/tephpy_readingtime.py docs/src/conf.py \
        docs/src/_static/tephpy.css tests/test_readingtime_directive.py
git commit -m "Add the readingtime directive and its doctree transform"
```

---

### Task 4: The corpus and the exemption list

Reading spec §3.6 and §3.7. This task builds the gate's view of the documentation and the exemption list, but **not yet** the coverage assertion — that is Task 5, where it can pass.

**Files:**
- Modify: `tests/test_docs_readingtime.py`

**Interfaces:**
- Consumes: `reading.carries_reading_time` from Task 2.
- Produces: module-level `EXCLUDED_DIRS`, `EXEMPT` and `published_pages() -> list[Path]` inside the test module. Task 5 consumes `published_pages` and `EXEMPT`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_docs_readingtime.py`:

```python
#: Trees that carry no hand-written page, so no author could add the directive to
#: them. This is a different thing from an exemption (reading spec §3.6): `EXEMPT`
#: below is for pages somebody could have written it on and should not.
EXCLUDED_DIRS = (
    "_static",           # Sphinx excludes `html_static_path` from document discovery
    "developer/plans",   # tracked but unpublished (docs spec §3.1)
    "gallery",           # generated by sphinx-gallery, and untracked
    "reference/generated",  # generated by autoapi
)

#: sphinx-gallery writes one beside each gallery it builds, including at the root.
GENERATED_PAGES = ("sg_execution_times.rst",)

#: The pages that are navigated rather than read (reading spec §3.7). Each entry
#: states why, because a list with a silent escape hatch is what decision 3 exists
#: to prevent.
EXEMPT = (
    "index.rst",                    # the site landing page: a card grid and a toctree
    "tutorials/index.rst",          # quadrant landing page
    "howtos/index.rst",             # quadrant landing page
    "explanation/index.rst",        # quadrant landing page
    "reference/index.rst",          # quadrant landing page
    "developer/index.rst",          # section landing page: a heading and a toctree
    "developer/specs/index.rst",    # the specification toctree and prefix table
    "reference/changelog.rst",      # the page is a `sphinx_changelog` directive
    "reference/cli.rst",            # the page is a `sphinx-click` directive
    "reference/config.rst",         # the page is `tephpy-config-options`
    "reference/references.rst",     # the page is a `bibliography` directive
    "reference/glossary.rst",       # a lookup table, not read in order
)


def published_pages(docs: Path = DOCS) -> list[Path]:
    """Every hand-written page Sphinx publishes.

    Derived rather than declared (reading spec §3.6), so a page is governed from
    the day it lands.

    Parameters
    ----------
    docs : Path, optional
        The documentation source root. It defaults to this repository's, which is
        what the gate reads; a test passes a tree of its own.

    Returns
    -------
    list of Path
        The `.rst` and `.md` sources, sorted.

    """
    found: list[Path] = []
    for path in sorted([*docs.rglob("*.rst"), *docs.rglob("*.md")]):
        relative = path.relative_to(docs).as_posix()
        if any(relative.startswith(f"{name}/") for name in EXCLUDED_DIRS):
            continue
        if path.name in GENERATED_PAGES:
            continue
        found.append(path)
    return found


def identify(page: Path) -> str:
    """Name a page for a parametrised test id."""
    return page.relative_to(DOCS).as_posix()


def test_the_corpus_is_not_empty():
    """A gate that finds nothing passes by never having looked."""
    assert len(published_pages()) > 30


def test_the_corpus_holds_a_member_of_every_quadrant_it_governs():
    """Membership, not a count: a count is a figure that must be re-measured."""
    found = {identify(page) for page in published_pages()}
    for member in (
        "howtos/logo.rst",
        "tutorials/first-tephigram.rst",
        "explanation/rotated-axes.rst",
        "developer/docs-style.rst",
        "developer/specs/2026-08-31-reading-time-design.md",
    ):
        assert member in found, f"{member} is missing from the corpus"


def test_the_corpus_excludes_the_generated_and_unpublished_trees():
    found = {identify(page) for page in published_pages()}
    assert not any(name.startswith("developer/plans/") for name in found)
    assert not any(name.startswith("gallery/") for name in found)
    assert not any(name.startswith("_static/") for name in found)
    assert "sg_execution_times.rst" not in found


@pytest.mark.parametrize("name", EXCLUDED_DIRS)
def test_every_excluded_tree_exists(name):
    """An exclusion naming nothing is an exclusion that stopped excluding."""
    if name in {"gallery", "reference/generated"}:
        pytest.skip(f"{name} exists only after a docs build")
    assert (DOCS / name).is_dir(), f"{name} is not a directory under {DOCS}"


def test_the_plans_are_excluded_by_the_build_and_not_only_by_this_gate():
    """The exclusion tracks `conf.py` rather than restating a claim about it."""
    conf = (DOCS / "conf.py").read_text(encoding="utf-8")
    assert '"developer/plans/**"' in conf


@pytest.mark.parametrize("name", EXEMPT)
def test_every_exempt_page_still_exists(name):
    """A renamed page whose exemption stayed behind would be silently exempt."""
    assert (DOCS / name).is_file(), f"{name} is exempt but is not a page"


def test_the_exempt_pages_are_all_in_the_corpus():
    """An exemption for a page the corpus never had is exempting nothing."""
    found = {identify(page) for page in published_pages()}
    assert set(EXEMPT) <= found
```

- [ ] **Step 2: Run the tests to verify they pass**

Run: `pixi run -e test pytest tests/test_docs_readingtime.py -q -k "corpus or exempt or excluded or plans"`

Expected: PASS. These describe the tree as it already is, so unlike the other tasks there is no red phase — the deliverable is the derivation, and the assertions are what pin it.

- [ ] **Step 3: Verify the derivation against the specification's own count**

Run:

```bash
pixi run -e test python -c "
import sys; sys.path.insert(0, 'tests')
import test_docs_readingtime as t
pages = t.published_pages()
carry = [p for p in pages if t.identify(p) not in t.EXEMPT]
print(f'published {len(pages)}, exempt {len(t.EXEMPT)}, carrying {len(carry)}')
"
```

Expected: `published 41, exempt 12, carrying 29` — the figures reading spec §3.7 states. A mismatch means either a page was added since 2026-08-31 or the derivation is wrong; find out which before continuing.

- [ ] **Step 4: Lint, then commit**

```bash
pixi run -e devs ruff check tests/test_docs_readingtime.py
pixi run -e devs ruff format --check tests/test_docs_readingtime.py
git add tests/test_docs_readingtime.py
git commit -m "Derive the reading-time corpus and name its exemptions"
```

---

### Task 5: The coverage gate, and the 29 banners

Reading spec §3.6. The gate goes in **first** and fails; the 29 pages are what make it pass.

**Files:**
- Modify: `tests/test_docs_readingtime.py`
- Modify: the 29 pages listed in **The corpus, measured** above

**Interfaces:**
- Consumes: `published_pages`, `EXEMPT`, `identify` from Task 4; `reading.carries_reading_time` from Task 2.
- Produces: nothing later tasks consume.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_docs_readingtime.py`:

```python
def carrying_pages() -> list[Path]:
    """The published pages a reader reads start to finish (reading spec §3.7)."""
    return [page for page in published_pages() if identify(page) not in EXEMPT]


@pytest.mark.parametrize("page", carrying_pages(), ids=identify)
def test_every_page_a_reader_reads_carries_a_reading_time(page):
    """reading spec §3.6: absence is a failure, not an omission.

    A page with no banner would otherwise be ambiguous between "short" and
    "nobody got round to it", which is the reason the rule is gated at all.
    """
    text = page.read_text(encoding="utf-8")
    assert reading.carries_reading_time(text, page.suffix), (
        f"{identify(page)} carries no `readingtime` directive in its lead: put one "
        f"after the title and before the first section heading, at column 0, or add "
        f"the page to EXEMPT with the reason it is navigated rather than read"
    )


@pytest.mark.parametrize("page", carrying_pages(), ids=identify)
def test_no_page_carries_more_than_one_reading_time(page):
    """Two banners on one page is a copy-paste, not a decision.

    `docs-style.rst` is the exception the rule allows for: the demonstrations in
    its Reading Time section sit inside literal blocks, indented, so they are not
    directives at column 0 and do not count here.
    """
    text = page.read_text(encoding="utf-8")
    assert len(reading.directive_lines(text, page.suffix)) == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pixi run -e test pytest tests/test_docs_readingtime.py -q -k carries`

Expected: FAIL, 58 failures — 29 pages × 2 tests, each naming the page that has no banner.

- [ ] **Step 3: Add the directive to the 17 reStructuredText pages**

For each `.rst` page in the table, insert a blank line, the directive, and a blank line **after the title underline** — before the lead paragraph and before any `.. _label:`-free content. `howtos/logo.rst` becomes:

```rst
.. _howto-logo:

Add the tephpy Logo
===================

.. readingtime::

:func:`~tephpy.plotting.logo.add_logo` brands a figure or an axes in one call.
```

`developer/docs-style.rst` and `tutorials/browser-demo.rst` have no label above the title, so the directive still follows the underline:

```rst
Documentation Style
===================

.. readingtime::

...
```

- [ ] **Step 4: Add the directive to the 13 MyST specifications**

Insert the fence immediately after the `# ` title, before the Living-document blockquote, so the banner is the first block under the title on every page in the corpus:

````markdown
# tephpy reading time — design specification

```{readingtime}
```

> **Living document.** This specification is maintained alongside the code, not archived
````

- [ ] **Step 5: Run the gate to verify it passes**

Run: `pixi run -e test pytest tests/test_docs_readingtime.py -q`

Expected: PASS, every test. If a page still fails, read the message: it names the page and the rule.

- [ ] **Step 6: Build the documentation and look at a banner**

```bash
pixi run docs
python - <<'EOF'
import pathlib, re
for name in ("howtos/logo", "tutorials/first-tephigram",
             "developer/specs/2026-08-31-reading-time-design"):
    html = pathlib.Path(f"docs/_build/html/{name}.html").read_text()
    found = re.search(r'<div class="reading-time[^"]*">.*?</div>', html, re.S)
    print(name, "->", found.group(0).replace("\n", " ") if found else "MISSING")
EOF
```

Expected: three banners, each of the shape `<div class="reading-time docutils container"><p><i class="fa-solid fa-clock"></i> Estimated reading time: N minutes</p></div>`, with `N` plausible for the page's length. A `MISSING` here with a passing gate means the gate and the directive disagree about what a page carries — stop and reconcile them before continuing.

- [ ] **Step 7: Commit**

```bash
git add tests/test_docs_readingtime.py \
        docs/src/howtos docs/src/tutorials docs/src/explanation \
        docs/src/developer/docs-style.rst docs/src/developer/packaging.rst \
        docs/src/developer/specs
git commit -m "Gate the reading-time banner, and add it to the 29 pages that carry it"
```

---

### Task 6: The bibliography and the style rule

Reading spec §3.4 and §4. The default rate becomes citable, and the convention becomes something a contributor can look up.

**Files:**
- Modify: `docs/src/refs.bib`
- Modify: `docs/src/developer/docs-style.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: the bibliography keys `brysbaert2019` and `carver1982`, cited by `docs-style.rst`.

- [ ] **Step 1: Add the two entries**

Append to `docs/src/refs.bib`. Titles are braced because pybtex lowercases an unbraced one, and each carries the consulted date docs-style requires:

```bibtex
@article{brysbaert2019,
  author  = {Brysbaert, Marc},
  title   = {{How many words do we read per minute? A review and meta-analysis of reading rate}},
  journal = {Journal of Memory and Language},
  volume  = {109},
  pages   = {104047},
  year    = {2019},
  doi     = {10.1016/j.jml.2019.104047},
  note    = {Accessed 2026-08-31}
}

@article{carver1982,
  author  = {Carver, Ronald P.},
  title   = {{Optimal Rate of Reading Prose}},
  journal = {Reading Research Quarterly},
  volume  = {18},
  number  = {1},
  pages   = {56--88},
  year    = {1982},
  note    = {ERIC accession EJ271095; accessed 2026-08-31}
}
```

> **Do not add a DOI to the Carver entry.** One was not verified when this plan was written, and a fabricated identifier is worse than an absent one — a citation is provenance (docs-style, *Bibliography*).

- [ ] **Step 2: Add the style rule**

Insert a new section in `docs/src/developer/docs-style.rst`, after *Published Figures* and before *Gallery Examples*:

```rst
Reading Time
------------

Every page a reader reads start to finish opens with a reading-time banner,
placed after the title and before the first section:

.. code:: rst

   .. readingtime::

In a specification, which is Markdown, it is the equivalent fence.

The estimate is counted from the *parsed* page rather than from its source, so
directive options, comment blocks and front matter are not counted as words and a
body another directive generated is. The rate is 150 words per minute
:cite:`brysbaert2019` :cite:`carver1982` — below the 175 wpm floor Brysbaert
reports for ordinary non-fiction prose, because these pages alternate argument
with code the reader parses line by line.

Two per-page overrides exist, and both are deliberate marks in the source rather
than silent adjustments. A literal duration is quoted instead of counted:

.. code:: rst

   .. readingtime:: 45

and a rate replaces the default for that page alone:

.. code:: rst

   .. readingtime:: 200wpm

Anything else is a build error. There is no way to spell an argument the
directive half-understands.

A page that is *navigated* rather than read carries no banner: the four Diátaxis
landing pages, the developer and specification indexes, the site root, the
glossary, and the four reference pages whose body a directive generates. These
are named in ``EXEMPT`` in ``tests/test_docs_readingtime.py``, with the reason
beside each, and ``test_every_page_a_reader_reads_carries_a_reading_time``
fails for any other page that omits one. Adding a page means adding the banner
or adding the reason.
```

- [ ] **Step 3: Build and check the citations resolved**

```bash
pixi run docs
grep -c "Brysbaert" docs/_build/html/reference/references.html
grep -o 'href="[^"]*references.html#id[0-9]*"' docs/_build/html/developer/docs-style.html | head -2
```

Expected: the References page names Brysbaert (the `:all:` on the bibliography directive renders both entries), and `docs-style.html` carries two links into it. A `--fail-on-warning` build that succeeds has already proven the keys resolve; this confirms they *render*.

- [ ] **Step 4: Run the gate again**

Run: `pixi run -e test pytest tests/test_docs_readingtime.py -q`

Expected: PASS. `docs-style.rst` now shows the directive three times inside `.. code:: rst` blocks — indented, therefore not directives at column 0 — and still carries exactly one live banner. `test_no_page_carries_more_than_one_reading_time` is what proves the distinction holds.

- [ ] **Step 5: Commit**

```bash
git add docs/src/refs.bib docs/src/developer/docs-style.rst
git commit -m "Cite the reading rate, and state the reading-time rule"
```

---

### Task 7: The changelog fragment and the full verification

**Files:**
- Create: `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

- [ ] **Step 1: Replace the specification's placeholder fragment**

`changelog/240.documentation.rst` was written with the specification and says the work is *not yet implemented*. If the implementation lands as a separate pull request, add a second fragment named for it; if it lands in the same one, rewrite that file. Either way the final text must not still claim the directive does not exist:

```rst
Documentation pages now open with an estimated reading time. A custom
``readingtime`` Sphinx directive counts the words in the *parsed* page — so
directive options, comments and front matter are not counted and a generated
page body is — and divides by 150 words per minute, a rate below the floor
Brysbaert (2019) reports for ordinary non-fiction prose. A page may quote a
literal duration instead, or override the rate for itself. A gate keeps the
banner on all 29 published pages a reader reads start to finish, against a
named list of twelve exemptions for the pages that are navigated instead.
(:user:`claude`)
```

- [ ] **Step 2: Run the whole test suite**

Run: `pixi run tests`

Expected: PASS. Then `pixi run -e test-py312 pytest tests/test_docs_readingtime.py tests/test_readingtime_directive.py -q` and confirm `test_docs_readingtime.py` **runs** while `test_readingtime_directive.py` **skips whole** — the split reading spec §3.1 exists for.

- [ ] **Step 3: Run the linters**

Run: `pixi run lint`

Expected: PASS, including `codespell`, `sphinx-lint`, and the three `local` documentation hooks.

- [ ] **Step 4: Build the documentation**

Run: `pixi run docs`

Expected: PASS under `--fail-on-warning`. Then confirm the leak guard is live rather than assumed:

```bash
python - <<'EOF'
import pathlib
p = pathlib.Path("docs/src/_ext/tephpy_readingtime.py")
source = p.read_text()
p.write_text(source.replace('app.connect("doctree-read", resolve)', "pass"))
EOF
pixi run docs; echo "exit=$?"
git checkout docs/src/_ext/tephpy_readingtime.py
```

Expected: the build **fails** with `WARNING: unknown node type: <readingtime: >`. That non-zero exit is the guarantee reading spec §3.2 buys by not registering the node; a build that succeeded here would mean a silent blank was possible. `git checkout` restores the file — confirm with `git status` that it is clean before committing.

- [ ] **Step 5: Check the light and dark rendering**

Open `docs/_build/html/howtos/logo.html` in a browser and toggle the theme. The banner must stay legible in both: `--pst-color-surface` and `--pst-color-text-muted` follow the toggle, which is the whole reason they were chosen over the prior art's undefined properties (reading spec §3.5). Fix the stylesheet if either state is wrong, and re-run `pixi run docs`.

- [ ] **Step 6: Commit**

```bash
git add changelog
git commit -m "Add the reading-time changelog fragment"
```

---

## Verification Checklist

Run before opening the pull request. Every line is a command with an expected result, not a judgement.

| check | command | expected |
|---|---|---|
| The suite | `pixi run tests` | pass |
| The matrix split | `pixi run -e test-py312 pytest tests/test_docs_readingtime.py tests/test_readingtime_directive.py -q` | the stdlib module runs, the directive module skips whole |
| Linters and hooks | `pixi run lint` | pass |
| The docs | `pixi run docs` | pass under `--fail-on-warning` |
| The corpus figures | Task 4, Step 3 | `published 41, exempt 12, carrying 29` |
| The banners | Task 5, Step 6 | three banners, none `MISSING` |
| The leak guard | Task 7, Step 4 | build fails with `unknown node type` |
| Dark mode | Task 7, Step 5 | legible in both themes |
