# Topic Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A published page on which every tutorial, how-to, explanation page and gallery example sits together, labelled with the quadrant it came from and filterable by topic — so a reader who arrives with a subject rather than an intent can see all four quadrants at once.

**Architecture:** Two modules under `docs/src/_ext/`, split on the Sphinx boundary. `tephpy_topics_data.py` imports nothing outside the standard library and holds the vocabulary, the two tag readers and the promotion rule as pure functions, so the gate over it runs in the `test-py3*` environments the CI matrix runs, which carry no Sphinx. `tephpy_topics.py` is the adapter: a `topicindex` directive leaves a placeholder node, and a `doctree-resolved` handler — the first point at which every document's metadata has been read — replaces it with the index. The filter is client-side over `data-topics` attributes and adds no dependency. A monthly scheduled workflow reports promotion changes and the coverage matrix onto one standing issue.

**Tech Stack:** Python 3.12+, Sphinx 8+, docutils, sphinx-gallery 0.21.0, pydata-sphinx-theme, pixi, pytest, pre-commit, `gh` (report only).

**Spec:** [`../specs/2026-09-03-topic-discovery-design.md`](../specs/2026-09-03-topic-discovery-design.md) — cited below as `topics spec §N`. Read it alongside this plan; every task argues from a section of it.

## What This Plan Measured Before It Was Written

Two things were established by experiment on 2026-09-03, and both change what the
specification says. The specification is a living document (docs spec §3.4), so each
task below corrects it where it diverges.

**1. `topics spec §3.2` places the field list in the wrong position.** Its example shows
`:tags:` *under* the title. Measured against a real build in the `docs` pixi environment:
a field list under the title does **not** reach `env.metadata` — it is left in the
doctree and renders on the page as a visible definition list, which is precisely the
failure mode §3.2 named as its own risk. Sphinx lifts a field list into
`env.metadata` only when it *precedes any other markup*. Measured working: the field
list at line 1 of the file, before the `.. _label:` target and before the title. That is
what this plan writes, and it closes the first open item of `topics spec §8` in the
affirmative but at a different position than the specification proposed. `env.metadata`
holds the field body as a **plain string** — `{'tags': 'units, sounding'}` — so the
adapter splits on commas.

**2. The glossary gate breaks on every tagged page, and the specification does not
mention it.** `.github/scripts/check_glossary_links.py` reads a page's lines as
narrative prose and requires the *first* mention of a glossary term to carry `:term:`.
A `:tags:` line at the top of the file is scanned as prose, so the tag list becomes the
first mention and the gate demands a cross-reference that cannot be written inside a
docinfo field list. Measured: adding `:tags: units, sounding` to `howtos/units.rst` and
`tutorials/first-tephigram.rst` produced two failures immediately. Three vocabulary
terms are also glossary spellings — `parcel`, `projection`, `sounding` — and `sounding`
alone is proposed on twelve of the nineteen items, so this is not a corner case. Task 2
teaches `prose()` that a leading docinfo field list is metadata rather than prose, which
is the same category as the rule it already carries for a directive's options and body.

**3. The extension's mechanics were prototyped, not reasoned.** The node, the directive,
the `doctree-resolved` transform and the HTML visitor of Task 3 were built as a throwaway
extension and run against a real three-page project. It builds clean, and emits
`<li class="teph-topic-item" data-topics="[&quot;diagram&quot;, &quot;isopleths&quot;]">`
with working relative links. Three things that could have gone wrong did not, and are
written into the code below rather than left to be discovered: `topicitem` subclasses
`nodes.list_item` because docutils validates a `bullet_list`'s content model; the row is a
`paragraph` because a `list_item` holds body elements and not inlines; and the layout is
styled on that row rather than on the `<li>`, because a `display` on the `<li>` would
out-rank the browser's own `[hidden] { display: none }` and the filter would mark rows
hidden while hiding none of them. The attribute arrives HTML-escaped, which
`JSON.parse(item.dataset.topics)` reads correctly — the DOM unescapes it.

Neither of the first two findings was reachable by reading; all three took a build.
`topics spec §3.2` says the mechanism "is the first thing the implementation establishes"
— it has been established, and the results are above.

## Global Constraints

- Every source file carries the BSD copyright header (ruff `CPY001`); the exact notice is in `[tool.ruff.lint.flake8-copyright]` in `pyproject.toml`. This applies to both `_ext` modules, `.github/scripts/topics_issue.py`, and every new test module.
- `line-length = 88`; ruff `select = ["ALL"]` with the ignore list in `pyproject.toml`. `.github/scripts/*.py` additionally ignores `FBT001`, `T201` and `INP001`.
- ruff isort: `force-sort-within-sections = true`, `required-imports = ["from __future__ import annotations"]`, `known-first-party = ["tephpy"]`.
- numpydoc docstring convention. numpydoc *validation* runs over `^src/` only, so `_ext` and `.github/scripts` modules need docstrings but not the full validated section set. Match the house style: a module docstring saying what the module is for and citing its specification section, `#:` comments on module constants, `Parameters`/`Returns` on each function.
- `[tool.pytest.ini_options]` sets `filterwarnings = ["error"]` — a warning in a test is a failure.
- The docs build is `--fail-on-warning --keep-going` (`docs/Makefile:1`). Any Sphinx warning fails `pixi run docs`.
- **`tephpy_topics_data.py` imports nothing outside the standard library** (topics spec §3.5). This is load-bearing, not stylistic: `tests/test_readingtime_directive.py` guards itself with `pytest.importorskip("sphinx")` and therefore *skips* across the CI test matrix. The tag assertions currently in `tests/examples/test_examples.py` do not skip, because they read the example source as text. Putting the vocabulary behind a Sphinx import would make an existing gate start skipping — weakening a gate as a side effect of extending it.
- Tests import an `_ext` module by path, using the mechanism in `tests/test_docs_readingtime.py:20-37` and **without** the `importorskip`.
- Every citation in a specification is `topics spec §N` in body prose, never in a section heading — a heading citation raises the `check_rendered_citations.py` warning that a citation there does not reach the reader as a link.
- Every PR adds `changelog/<PR>.<type>.rst` ending with ``(:user:`claude`)``.
- **Everything in this plan lands together.** The gate ahead of the tags fails on fourteen untagged pages; the tags ahead of the glossary-gate fix fail pre-commit. Tasks commit individually, but the branch is not mergeable until Task 6.

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/src/_ext/tephpy_topics_data.py` | **Create.** The taxonomy: vocabulary, the two tag readers, the promotion rule and the coverage matrix, all pure and stdlib-only. |
| `docs/src/_ext/tephpy_topics.py` | **Create.** The Sphinx adapter: the `topicindex` node and directive, corpus assembly from `env.metadata` and the example sources, and the `doctree-resolved` builder. |
| `docs/src/topics.rst` | **Create.** The published page: a title, a paragraph, and `.. topicindex::`. |
| `docs/src/_static/topics.js` | **Create.** The client-side filter and the `?topics=` parameter. |
| `docs/src/_static/tephpy.css` | **Modify.** Filter buttons, quadrant badges, item rows. |
| `docs/src/conf.py` | **Modify.** `tephpy_topics` in `extensions`. |
| `docs/src/index.rst` | **Modify.** The toctree entry. |
| `docs/src/{tutorials,howtos,explanation}/*.rst` (14) | **Modify.** A `:tags:` field list at line 1. |
| `tests/test_docs_topics.py` | **Create.** The five gate assertions of topics spec §3.7 and the promotion rule's boundaries. |
| `tests/examples/test_examples.py` | **Modify.** `VOCABULARY` and `_TAGS` move out to the taxonomy module. |
| `tests/test_docs_readingtime.py` | **Modify.** `EXEMPT` gains `topics.rst`. |
| `.github/scripts/check_glossary_links.py` | **Modify.** A leading docinfo field list is metadata, not prose. |
| `tests/test_glossary_links.py` | **Modify.** That rule pinned, in both directions. |
| `.github/scripts/topics_issue.py` | **Create.** The monthly report of topics spec §3.8. |
| `.github/workflows/ci-topics.yml` | **Create.** Its monthly schedule. |
| `tests/test_topics_issue.py` | **Create.** The composer's tests, modelled on `tests/test_floors_issue.py`. |
| `docs/src/developer/specs/2026-09-03-topic-discovery-design.md` | **Modify.** §3.2 corrected, §4 completed, §6.3 recorded, §8 open item closed. |
| `docs/src/developer/specs/2026-08-31-reading-time-design.md` | **Modify.** §3.7's exemption table and count. |
| `docs/src/developer/docs-style.rst` | **Modify.** The vocabulary's new home; a new "Topic Tags" section. |
| `changelog/<PR>.documentation.rst` | **Create.** The fragment. |

---

## Task 1: The Taxonomy Module and the Vocabulary's Single Home

The vocabulary, the two tag readers and the promotion rule, in one stdlib-only module —
and the copy that currently lives in `tests/examples/test_examples.py` removed rather
than duplicated (topics spec §3.5).

**Files:**
- Create: `docs/src/_ext/tephpy_topics_data.py`
- Create: `tests/ext_modules.py`
- Create: `tests/test_docs_topics.py`
- Modify: `tests/examples/test_examples.py:20-41` (the `VOCABULARY` and `_TAGS` block) and `tests/examples/test_examples.py:78-94` (`read_tags`)
- Modify: `tests/test_docs_readingtime.py:20-37` (the private loader, replaced by the shared one)
- Modify: `docs/src/developer/docs-style.rst`, the "Gallery Examples" section's tag paragraph

**Interfaces:**
- Consumes: nothing.
- Produces: `tephpy_topics_data.VOCABULARY: frozenset[str]`; `MIN_TAGS: int = 2`; `MAX_TAGS: int = 4`; `MIN_QUADRANTS: int = 2`; `QUADRANTS: tuple[str, ...]`; `GALLERY_TAGS: re.Pattern`; `PAGE_TAGS: re.Pattern`; `split_tags(value: str) -> list[str]`; `read_gallery_tags(source: str) -> list[str]`; `read_page_tags(source: str) -> list[str]`; `promote(corpus: Mapping[str, tuple[str, Sequence[str]]]) -> frozenset[str]`; `coverage(corpus: Mapping[str, tuple[str, Sequence[str]]]) -> dict[str, frozenset[str]]`. And `tests.ext_modules.load(name: str) -> ModuleType`.

- [ ] **Step 1: Write the shared `_ext` loader**

There are already two hand-written copies of this loader (`tests/test_docs_readingtime.py`
and, in a `.github/scripts` flavour, `tests/test_docs_workflow.py`). This task needs it in
two more places, so it becomes a shared helper beside `tests/pixi_tasks.py`, which is the
existing precedent for a non-test module under `tests/`.

Create `tests/ext_modules.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Import a documentation extension module by path.

``docs/src/_ext`` is a ``sys.path`` entry at build time rather than a package
(:issue:`92`), so a module there resolves its siblings by top-level name and
cannot be imported until that entry exists. Shared rather than copied: three
test modules need it, and a loader that drifts between copies loads different
code in each.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

EXT = Path(__file__).parents[1] / "docs" / "src" / "_ext"


def load(name: str) -> ModuleType:
    """Import an extension module by path.

    Parameters
    ----------
    name : str
        The module's top-level name, without the ``.py`` suffix.

    Returns
    -------
    module
        The executed module.

    """
    if str(EXT) not in sys.path:
        sys.path.insert(0, str(EXT))
    path = EXT / f"{name}.py"
    assert path.is_file(), f"the module is missing from {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
```

- [ ] **Step 2: Write the failing tests for the taxonomy**

Create `tests/test_docs_topics.py`. This file grows a corpus gate in Task 2; for now it
holds the rule, tested from fixtures rather than from the live corpus, so that a
documentation change cannot make a rule test pass or fail for the wrong reason
(topics spec §6.2).

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The topic taxonomy, its corpus and its promotion rule (topics spec §6)."""

from __future__ import annotations

import pytest

from tests.ext_modules import load

topics = load("tephpy_topics_data")


def test_the_vocabulary_is_the_seventeen_terms_the_specification_defines():
    """Topics spec §3.3 is a closed vocabulary with a definition per term."""
    assert len(topics.VOCABULARY) == 17
    assert "sounding" in topics.VOCABULARY
    assert "data-input" in topics.VOCABULARY


def test_the_bounds_are_the_gallery_specification_s_own():
    assert topics.MIN_TAGS == 2
    assert topics.MAX_TAGS == 4
    assert topics.MIN_QUADRANTS == 2


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("units, sounding", ["units", "sounding"]),
        ("units,sounding", ["units", "sounding"]),
        ("  units ,  sounding  ", ["units", "sounding"]),
        ("units", ["units"]),
        ("", []),
        ("units, , sounding", ["units", "sounding"]),
    ],
)
def test_split_tags_reads_a_comma_separated_field_body(value, expected):
    """`env.metadata` hands the adapter the field body as one string."""
    assert topics.split_tags(value) == expected


def test_read_page_tags_reads_a_field_list_at_the_head_of_the_file():
    """Measured: only a field list preceding all other markup reaches metadata."""
    source = ":tags: units, sounding\n\n.. _howto-units:\n\nWork With Units\n===============\n"
    assert topics.read_page_tags(source) == ["units", "sounding"]


def test_read_page_tags_rejects_a_field_list_under_the_title():
    """The position topics spec §3.2 originally proposed, which does not work.

    Measured in a build: a field list under the title is left in the doctree and
    renders as a visible definition list, and `env.metadata` stays empty. The
    reader is as strict as Sphinx so that the gate fails the page rather than the
    reader silently finding no tags on a page that appears to declare them.
    """
    source = "Work With Units\n===============\n\n:tags: units, sounding\n"
    assert topics.read_page_tags(source) == []


def test_read_page_tags_finds_nothing_on_an_untagged_page():
    assert topics.read_page_tags(".. _howto-units:\n\nWork With Units\n") == []


def test_read_gallery_tags_reads_the_flag_sphinx_gallery_reads():
    source = '"""Doc."""\n# sphinx_gallery_tags = ["metpy", "barbs", "sounding"]\n'
    assert topics.read_gallery_tags(source) == ["metpy", "barbs", "sounding"]


def test_read_gallery_tags_rejects_a_misspelled_flag():
    """sphinx-gallery discards `sphinx_gallery_tag` in silence, so the gate must not."""
    source = '"""Doc."""\n# sphinx_gallery_tag = ["metpy", "barbs"]\n'
    assert topics.read_gallery_tags(source) == []


#: A corpus in which every term sits on a documented side of both thresholds.
#: Six items, so "fewer than half" is "fewer than three".
#:
#: Corrected during implementation: item `"c"` was originally in quadrant
#: `"howtos"`, which put `narrow` in two quadrants (`tutorials` and `howtos`)
#: and so promoted it, contradicting `test_a_term_in_one_quadrant_is_held_back`
#: below. Moving `"c"` to `"tutorials"` confines `narrow` to one quadrant, as
#: that test requires.
FIXTURE = {
    "a": ("tutorials", ["spanning", "narrow", "broad"]),
    "b": ("howtos", ["spanning", "broad"]),
    "c": ("tutorials", ["narrow", "broad"]),
    "d": ("explanation", ["halved", "broad"]),
    "e": ("gallery", ["halved", "broad"]),
    "f": ("gallery", ["halved", "solo"]),
}


def test_a_term_in_exactly_two_quadrants_promotes():
    """The lower boundary of the first condition (topics spec §3.4)."""
    assert "spanning" in topics.promote(FIXTURE)


def test_a_term_in_one_quadrant_is_held_back():
    """`barbs` is the live example: two gallery examples, no narrative page."""
    assert "narrow" not in topics.promote(FIXTURE)
    assert "solo" not in topics.promote(FIXTURE)


def test_a_term_selecting_exactly_half_the_corpus_is_held_back():
    """"Fewer than half" is strict: three of six does not promote."""
    assert len(FIXTURE) == 6
    assert sum("halved" in tags for _, tags in FIXTURE.values()) == 3
    assert "halved" not in topics.promote(FIXTURE)


def test_a_term_selecting_more_than_half_the_corpus_is_held_back():
    """`sounding` is the live example: twelve of nineteen items."""
    assert "broad" not in topics.promote(FIXTURE)


def test_promotion_needs_both_conditions_and_the_fixture_proves_each_alone():
    """Neither condition alone would give this answer.

    `narrow` passes the breadth cap and fails the span; `halved` passes the span
    and fails the cap. A rule that dropped either condition would promote one of
    them, so this asserts the conjunction rather than the result.
    """
    assert topics.promote(FIXTURE) == frozenset({"spanning"})


def test_promotion_over_an_empty_corpus_is_an_error():
    """A rule that returns an empty set over nothing reports "no buttons" twice.

    Once for a corpus with no spanning term, and once for a corpus the caller
    failed to assemble -- and those need different fixes.
    """
    with pytest.raises(ValueError, match="corpus"):
        topics.promote({})


def test_coverage_reports_the_quadrants_each_term_appears_in():
    """The matrix of topics spec §3.8, and what `promote` counts its span from."""
    found = topics.coverage(FIXTURE)
    assert found["spanning"] == frozenset({"tutorials", "howtos"})
    assert found["solo"] == frozenset({"gallery"})
    assert set(found) == {"spanning", "narrow", "broad", "halved", "solo"}
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pixi run -e test pytest tests/test_docs_topics.py -q`
Expected: collection error — `tests/ext_modules.py` exists but `tephpy_topics_data.py` does not, so `load` trips its `assert path.is_file()`.

- [ ] **Step 4: Write the taxonomy module**

Create `docs/src/_ext/tephpy_topics_data.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""The topic taxonomy, shared by the extension, the gate and the report.

One definition of what the vocabulary is, how a tag declaration is read at each of
its two sites, and when a term earns a filter button -- shared by the
``tephpy_topics`` extension (topics spec §3.6), the gate (topics spec §3.7) and the
monthly report (topics spec §3.8). Two copies would agree until one was amended,
and a gate that promoted differently from the page it polices would be checking a
different index than the one published.

Nothing here is imported from outside the standard library, and that is
load-bearing rather than tidy (topics spec §3.5): the vocabulary is asserted by
tests that run in the ``test-py3*`` environments the CI matrix runs, which carry
no Sphinx. A module reachable only behind a Sphinx import would make those
assertions skip exactly where they matter.

The ``tephpy_`` prefix claims a top-level name this repository owns, because
``docs/src/_ext`` sits at ``sys.path[0]`` for the whole build (:issue:`92`). It is
not part of the installed package -- nothing under ``docs/`` is.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

VOCABULARY = frozenset(
    {
        "analysis",
        "barbs",
        "branding",
        "config",
        "data-input",
        "diagram",
        "indices",
        "isopleths",
        "labels",
        "metpy",
        "overlay",
        "parcel",
        "projection",
        "shading",
        "sounding",
        "styling",
        "units",
    }
)
"""The seventeen terms of topics spec §3.3, closed.

Each is defined there by what it covers *and* what it excludes, and that table is
the authority when two people would tag a page differently -- neither spelling of
a disagreement is illegal here, so nothing in this module can see it. A term added
without an entry in that table is the drift the closure exists to prevent, so the
two land together.
"""

#: Topics spec §3.3's bound, inherited unchanged from gallery spec §3.6: one tag
#: files an item under a single button, and a full house files it under every one,
#: either way telling the filter nothing.
MIN_TAGS = 2
MAX_TAGS = 4

#: The first promotion condition (topics spec §3.4). A count rather than a
#: fraction because there are only ever four quadrants.
MIN_QUADRANTS = 2

#: The four quadrants the corpus is drawn from (topics spec §3.1). The reference
#: quadrant and the developer section are out.
QUADRANTS = ("tutorials", "howtos", "explanation", "gallery")

#: sphinx-gallery reads exactly this flag and silently discards any other
#: spelling, so this pattern is deliberately as strict as its parser (gallery
#: spec §3.6). Moved here from ``tests/examples/test_examples.py``, which now
#: reads it from this module: the vocabulary and the flag that declares it
#: belong to one taxonomy, and the gallery's gate and the site-wide index were
#: reading two copies of them.
GALLERY_TAGS = re.compile(r"^# sphinx_gallery_tags = (?P<value>\[.*\])$", re.MULTILINE)

#: A narrative page's declaration, anchored to the first byte of the file.
#:
#: The anchor is the whole rule and it was measured rather than assumed. Sphinx
#: lifts a docinfo field list into ``env.metadata`` -- removing it from the
#: doctree, so it renders nothing -- only when it precedes every other piece of
#: markup on the page. A field list written under the title, which is what topics
#: spec §3.2 first proposed, leaves ``env.metadata`` empty and renders a visible
#: definition list at the reader. Being as strict here as Sphinx is what makes the
#: gate fail such a page instead of quietly finding no tags on one that looks
#: tagged.
PAGE_TAGS = re.compile(r"\A:tags:[ \t]*(?P<value>[^\n]*)\n")


def split_tags(value: str) -> list[str]:
    """Split a comma-separated field body into tags.

    Parameters
    ----------
    value : str
        The field body, as ``env.metadata`` hands it over: one string.

    Returns
    -------
    list of str
        The tags, stripped, in the order declared, empty entries dropped.

    """
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def read_gallery_tags(source: str) -> list[str]:
    """Return the tags a gallery example declares.

    Parameters
    ----------
    source : str
        The example module's text.

    Returns
    -------
    list of str
        The declared tags, empty if the file declares none.

    """
    match = GALLERY_TAGS.search(source)
    if match is None:
        return []
    return ast.literal_eval(match.group("value"))


def read_page_tags(source: str) -> list[str]:
    """Return the tags a narrative page declares.

    Parameters
    ----------
    source : str
        The page's reStructuredText.

    Returns
    -------
    list of str
        The declared tags, empty if the page declares none *in the position
        Sphinx reads*.

    """
    match = PAGE_TAGS.match(source)
    if match is None:
        return []
    return split_tags(match.group("value"))


def coverage(
    corpus: Mapping[str, tuple[str, Sequence[str]]],
) -> dict[str, frozenset[str]]:
    """Return the quadrants each term appears in.

    Parameters
    ----------
    corpus : mapping
        Item name to ``(quadrant, tags)``.

    Returns
    -------
    dict
        Term to the quadrants holding it. Terms nothing declares are absent,
        which is what makes an unused vocabulary term visible to the gate.

    """
    found: defaultdict[str, set[str]] = defaultdict(set)
    for quadrant, tags in corpus.values():
        for tag in tags:
            found[tag].add(quadrant)
    return {tag: frozenset(quadrants) for tag, quadrants in found.items()}


def promote(corpus: Mapping[str, tuple[str, Sequence[str]]]) -> frozenset[str]:
    """Return the terms that earn a filter button (topics spec §3.4).

    A term promotes when it appears in two or more quadrants *and* selects fewer
    than half the corpus. Both conditions are needed and the live corpus
    demonstrates each failing alone: ``barbs`` sits in two gallery examples and no
    narrative page, passing the cap and failing the span; ``sounding`` sits in
    twelve of nineteen items across three quadrants, passing the span and failing
    the cap.

    Parameters
    ----------
    corpus : mapping
        Item name to ``(quadrant, tags)``.

    Returns
    -------
    frozenset of str
        The promoted terms.

    Raises
    ------
    ValueError
        If the corpus is empty. An empty result would otherwise mean either "no
        term spans two quadrants" or "the caller assembled nothing", and those
        take different fixes.

    """
    total = len(corpus)
    if not total:
        msg = "the corpus is empty: promotion over nothing promotes nothing"
        raise ValueError(msg)
    quadrants = coverage(corpus)
    counts = Counter(tag for _, tags in corpus.values() for tag in set(tags))
    # `count * 2 < total` rather than `count < total / 2`: the threshold is a
    # strict "fewer than half", and integer arithmetic states that exactly at the
    # boundary an odd corpus never reaches and an even one lands on.
    return frozenset(
        tag
        for tag, count in counts.items()
        if len(quadrants[tag]) >= MIN_QUADRANTS and count * 2 < total
    )
```

`ast.literal_eval` parses the gallery flag's list, exactly as the assertion in
`tests/examples/test_examples.py` did before the pattern moved here.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run -e test pytest tests/test_docs_topics.py -q`
Expected: PASS, 20 tests.

- [ ] **Step 6: Move the vocabulary out of the gallery's gate**

In `tests/examples/test_examples.py`, delete the `VOCABULARY` frozenset (lines 20-34)
and the `_TAGS` pattern (lines 36-41), and replace the body of `read_tags`. Add
`from tests.ext_modules import load` to the imports and, after them:

```python
#: The taxonomy of topics spec §3.5. The vocabulary and the flag pattern moved
#: there when the site-wide topic index started reading the same two things: a
#: second copy would agree until one was widened. Loaded by path because
#: `docs/src/_ext` is a `sys.path` entry at build time and not a package
#: (:issue:`92`), and imported here with no `importorskip` guard, because this
#: module holds nothing outside the standard library and these assertions run on
#: every supported Python.
topics = load("tephpy_topics_data")
```

Then `read_tags` becomes a delegation, keeping its docstring:

```python
def read_tags(source: str) -> list[str]:
    """Return the tags an example declares.

    Parameters
    ----------
    source : str
        The example module's text.

    Returns
    -------
    list of str
        The declared tags, empty if the file declares none.
    """
    return topics.read_gallery_tags(source)
```

And `test_example_tags_are_declared_and_in_vocabulary` reads the bounds and the
vocabulary from the module rather than from local constants:

```python
    tags = read_tags((EXAMPLES / f"{module}.py").read_text())
    assert tags, f"{module} declares no sphinx_gallery_tags"
    assert topics.MIN_TAGS <= len(tags) <= topics.MAX_TAGS, (
        f"{module} declares {len(tags)} tags: {tags}"
    )
    assert set(tags) <= topics.VOCABULARY, sorted(set(tags) - topics.VOCABULARY)
```

Leave `_FLAGS` where it is: it matches *every* `sphinx_gallery_*` flag for the
spacing test, is about `remove_config_comments` rather than about tags, and has no
second reader.

- [ ] **Step 7: Run the gallery's gate**

Run: `pixi run -e test pytest tests/examples -q`
Expected: PASS. The five examples still declare two to four tags each, now checked
against a seventeen-term vocabulary rather than a nine-term one — which is the
widening topics spec §3.3 intends, and no example changes.

- [ ] **Step 8: Retire the private loader in the reading-time gate**

In `tests/test_docs_readingtime.py`, delete `_load` (lines 20-28) and the `sys.path`
insertion (lines 31-37), and replace `reading = _load("tephpy_reading")` with:

```python
from tests.ext_modules import load

reading = load("tephpy_reading")
```

`EXT` is still used by nothing else there; `DOCS` is. Delete `EXT`, and the now
unused `importlib.util` and `sys` imports.

Run: `pixi run -e test pytest tests/test_docs_readingtime.py -q`
Expected: PASS, unchanged count.

- [ ] **Step 9: Point the style guide at the vocabulary's new home**

`docs/src/developer/docs-style.rst`'s "Gallery Examples" section currently lists the
nine terms inline and says widening means editing `tests/examples/test_examples.py`.
Both are now wrong. Replace that paragraph with:

```rst
Tags come from a closed vocabulary of seventeen terms, shared with the site-wide
topic index, two to four per example, declared in the flag sphinx-gallery reads:

.. code-block:: python

    # sphinx_gallery_tags = ["analysis", "shading", "indices", "sounding"]

Each term is defined by what it covers *and* what it excludes in topics spec §3.3,
and that table is the authority when two people would tag a page differently — the
gate cannot see a disagreement, because both spellings are legal. They render on
the page and drive the index's filter buttons, so a ``barb`` beside a ``barbs``
splits the very index the feature exists to build. Widening the vocabulary means
adding the term to ``VOCABULARY`` in ``docs/src/_ext/tephpy_topics_data.py`` *and*
its definition to that table, together. Spell the flag exactly: sphinx-gallery
parses ``sphinx_gallery_tag`` into a differently-keyed entry and discards it in
silence, with no warning to fail the build on — which is why the test reads the
flag out of the source text rather than asking the parser.
```

Do not list the seventeen terms here. The set already lives in the module and in
the specification's table; a third hand-written copy is one that goes stale
silently.

- [ ] **Step 10: Lint and commit**

```bash
pixi run lint
git add docs/src/_ext/tephpy_topics_data.py tests/ext_modules.py \
        tests/test_docs_topics.py tests/examples/test_examples.py \
        tests/test_docs_readingtime.py docs/src/developer/docs-style.rst
git commit -m "Give the tag vocabulary one home and a promotion rule"
```

---

## Task 2: The Fourteen Pages Declare Their Tags

The declaration site, the gate over it, and the two things that have to change first:
the glossary gate, which fails on every tagged page, and topics spec §3.2, which puts the
field list where Sphinx does not read it.

**Files:**
- Modify: `.github/scripts/check_glossary_links.py`, `prose()` at lines 112-147
- Modify: `tests/test_glossary_links.py`
- Modify: 14 pages under `docs/src/{tutorials,howtos,explanation}/`
- Modify: `tests/test_docs_topics.py` (the corpus gate)
- Modify: `docs/src/developer/specs/2026-09-03-topic-discovery-design.md`, §3.2 and §8

**Interfaces:**
- Consumes: `tephpy_topics_data.read_page_tags`, `read_gallery_tags`, `VOCABULARY`, `MIN_TAGS`, `MAX_TAGS` (Task 1).
- Produces: `tests.test_docs_topics.narrative_pages(docs: Path = DOCS) -> list[Path]` and `corpus() -> dict[str, tuple[str, list[str]]]`, keyed `"<quadrant>/<stem>"`. Task 5's report reads the same shape.

- [ ] **Step 1: Write the failing test for the glossary gate**

The gate reads a page's lines as narrative prose. A `:tags:` line at the head of the
file is metadata Sphinx never renders, so it is not prose — the same category as the
rule `prose()` already carries for a directive's options and body. Measured before this
plan was written: adding `:tags: units, sounding` to `howtos/units.rst` and
`tutorials/first-tephigram.rst` produced two failures immediately, both on `sounding`.

Add to `tests/test_glossary_links.py`:

```python
def test_a_leading_field_list_is_metadata_and_not_prose():
    """A `:tags:` declaration is lifted into `env.metadata` and never rendered.

    Scanning it as prose makes the tag list the page's first mention of every
    glossary term it names -- `parcel`, `projection` and `sounding` are all both
    vocabulary terms and glossary spellings -- and demands a `:term:` role that
    cannot be written inside a docinfo field list (topics spec §3.2).
    """
    text = ":tags: units, sounding\n\n.. _howto-units:\n\nWork With Units\n===============\n\nProse.\n"
    assert (1, ":tags: units, sounding") not in gate.prose(text)


def test_a_field_list_below_the_first_line_is_still_prose():
    """The exemption is exactly as wide as the position Sphinx reads.

    A field list anywhere else renders at the reader, so a glossary term in one is
    a first mention like any other. An exemption wider than the mechanism it
    exists for is a hole in the shape of whatever nobody thought of.
    """
    text = "Work With Units\n===============\n\n:tags: units, sounding\n\nProse.\n"
    assert (4, ":tags: units, sounding") in gate.prose(text)
```

Match the module's existing import of the gate; it loads the script by path in the
manner of `tests/test_docs_workflow.py`. Reuse whatever name that module already binds
rather than introducing a second one.

- [ ] **Step 2: Run it to verify it fails**

Run: `pixi run -e test pytest tests/test_glossary_links.py -q -k field_list`
Expected: the first test FAILS (the line is returned as prose); the second PASSES already.

- [ ] **Step 3: Teach `prose()` that a leading field list is metadata**

In `.github/scripts/check_glossary_links.py`, add beside the other patterns:

```python
#: A docinfo field at the head of a page. Sphinx lifts a field list preceding all
#: other markup into `env.metadata` and removes it from the doctree, so it never
#: reaches a reader and cannot carry a `:term:` role -- which makes a glossary
#: term in one a mention of nothing (topics spec §3.2). Anywhere else a field
#: list renders, and is prose like any other line.
FIELD = re.compile(r"^:[^:\s][^:]*:")
```

and open `prose()` with the skip, before the main loop:

```python
    lines = text.splitlines()
    found: list[tuple[int, str]] = []
    index = 0
    # The docinfo field list, if the page opens with one: consecutive field lines
    # and their indented continuations, to the first blank line. A page opening
    # with anything else leaves `index` at 0 on the first comparison, so this
    # costs a page without tags one test.
    while index < len(lines) and lines[index].strip():
        if not FIELD.match(lines[index]) and not lines[index].startswith((" ", "\t")):
            break
        index += 1
    while index < len(lines):
        ...
```

- [ ] **Step 4: Run it to verify it passes**

Run: `pixi run -e test pytest tests/test_glossary_links.py -q`
Expected: PASS, all of them.

- [ ] **Step 5: Declare the tags on the fourteen pages**

Write `:tags:` as **line 1** of each file, followed by a blank line, above the existing
`.. _label:` target where there is one. This position was measured; the position topics
spec §3.2 proposed was measured too, and does not work.

`docs/src/howtos/units.rst` becomes:

```rst
:tags: units, sounding

.. _howto-units:

Work With Units
===============

.. readingtime::
```

The tagging is topics spec §6.1's, which is **a proposal, not a fact** — it was derived
from titles, section headings, `ax.*` calls and `:term:` references, not from reading the
pages. Confirm each against the page as you edit it, using the covers/not table of
topics spec §3.3 to settle the close calls, and revise where the page disagrees. If a
revision changes which terms promote, that is a fact about the corpus and not a defect:
say so in the pull-request description rather than bending a page's tags to preserve the
table in §3.4.

| page | tags |
|---|---|
| `tutorials/first-tephigram.rst` | `diagram, isopleths, sounding` |
| `tutorials/analyse-a-sounding.rst` | `analysis, sounding, shading, indices` |
| `tutorials/browser-demo.rst` | `sounding, data-input` |
| `howtos/build-a-sounding.rst` | `sounding, data-input` |
| `howtos/configuration.rst` | `config, isopleths` |
| `howtos/emphasis.rst` | `isopleths, styling, config` |
| `howtos/framing.rst` | `diagram, sounding, parcel` |
| `howtos/label-and-compose.rst` | `diagram, labels, isopleths` |
| `howtos/logo.rst` | `branding, diagram` |
| `howtos/read-a-sounding.rst` | `sounding, data-input` |
| `howtos/temp-and-bufr.rst` | `sounding, data-input` |
| `howtos/units.rst` | `units, sounding` |
| `explanation/parcel-ascent.rst` | `analysis, parcel, shading, metpy` |
| `explanation/rotated-axes.rst` | `diagram, isopleths, projection` |

Two judgements in that table are contestable and are recorded in topics spec §6.1:
`metpy` is tagged only where MetPy is the subject of a section, not where it is mentioned
in passing, because tagging passing mentions inflates every count in the promotion rule;
and no narrative page is tagged `barbs`, which is what makes `barbs` fail promotion.

`tutorials/browser-demo.rst` has no `.. _label:` target — the field list is simply the
first line, above the title.

- [ ] **Step 6: Write the corpus gate**

Append to `tests/test_docs_topics.py`:

```python
REPO = Path(__file__).parents[1]
DOCS = REPO / "docs" / "src"
EXAMPLES = Path(examples.__file__).parent

#: The three quadrants of topics spec §3.1. The reference quadrant is out -- its
#: pages are lookup surfaces reached by name, and the generated API is ninety-four
#: objects that would dominate any filter built over the same buttons. The
#: developer section is out because :issue:`66` is expected to change which pages
#: exist there, and tagging a set about to be rewritten files the wrong set.
NARRATIVE = ("tutorials", "howtos", "explanation")


def narrative_pages(docs: Path = DOCS) -> list[Path]:
    """Every hand-written page of the three narrative quadrants.

    Discovered rather than listed (topics spec §3.1), so a page added tomorrow
    fails this gate until it declares tags. A hand-maintained list is one a new
    page silently misses.

    Parameters
    ----------
    docs : Path, optional
        The documentation source root. It defaults to this repository's; a test
        passes a tree of its own.

    Returns
    -------
    list of Path
        The quadrants' pages, sorted, without their landing pages.

    """
    found: list[Path] = []
    for quadrant in NARRATIVE:
        found.extend(
            path
            for path in sorted((docs / quadrant).glob("*.rst"))
            if path.name != "index.rst"
        )
    return found


def corpus() -> dict[str, tuple[str, list[str]]]:
    """Return the tagged corpus of topics spec §3.1.

    Returns
    -------
    dict
        ``"<quadrant>/<stem>"`` to ``(quadrant, tags)``.

    """
    found = {
        f"{page.parent.name}/{page.stem}": (
            page.parent.name,
            topics.read_page_tags(page.read_text(encoding="utf-8")),
        )
        for page in narrative_pages()
    }
    found.update(
        {
            f"gallery/{path.stem}": (
                "gallery",
                topics.read_gallery_tags(path.read_text(encoding="utf-8")),
            )
            for path in sorted(EXAMPLES.glob("plot_*.py"))
        }
    )
    return found


def test_the_corpus_is_not_empty():
    """A gate that finds nothing passes by never having looked."""
    assert len(corpus()) > 15


def test_the_corpus_holds_a_member_of_every_quadrant_it_governs():
    """Membership, not a count: a count is a figure that must be re-measured."""
    found = corpus()
    for member in (
        "tutorials/first-tephigram",
        "howtos/units",
        "explanation/rotated-axes",
        "gallery/plot_tephigram",
    ):
        assert member in found, f"{member} is missing from the corpus"


def test_the_corpus_excludes_the_quadrant_landing_pages():
    """A landing page is a toctree, and tagging one files the toctree."""
    assert not any(name.endswith("/index") for name in corpus())


def test_narrative_pages_discovers_a_synthetic_tree_of_its_own(tmp_path):
    """The discovery is exercised directly, not only against this repository.

    Against the real tree every assertion about exclusion passes whether or not
    the rule is applied, because the tree happens not to contain the thing being
    excluded. A tree built here always does.
    """
    for relative in (
        "tutorials/index.rst",
        "tutorials/a-lesson.rst",
        "howtos/index.rst",
        "howtos/a-recipe.rst",
        "explanation/index.rst",
        "explanation/some-background.rst",
        "reference/glossary.rst",
    ):
        page = tmp_path / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("Title\n=====\n", encoding="utf-8")

    found = {path.relative_to(tmp_path).as_posix() for path in narrative_pages(tmp_path)}
    assert found == {
        "tutorials/a-lesson.rst",
        "howtos/a-recipe.rst",
        "explanation/some-background.rst",
    }


@pytest.mark.parametrize("item", sorted(corpus()))
def test_every_item_declares_two_to_four_tags(item):
    """Topics spec §3.7, assertion 1, over a discovered corpus (assertion 4).

    An untagged narrative page fails here from the day it lands, which is the
    whole reason the corpus is discovered rather than listed.
    """
    _, tags = corpus()[item]
    assert tags, (
        f"{item} declares no tags: put `:tags: <two to four terms>` on the FIRST "
        f"line of the file, above the `.. _label:` target, followed by a blank "
        f"line. Sphinx reads a field list into page metadata only where it "
        f"precedes all other markup; under the title it renders at the reader "
        f"instead (topics spec §3.2)."
    )
    assert topics.MIN_TAGS <= len(tags) <= topics.MAX_TAGS, (
        f"{item} declares {len(tags)} tags: {tags}"
    )


@pytest.mark.parametrize("item", sorted(corpus()))
def test_every_declared_tag_is_in_the_vocabulary(item):
    """Topics spec §3.7, assertion 2, and the growth mechanism of §3.3.

    An unknown term fails here, and the fix is to add it to `VOCABULARY` *and* to
    the covers/not table together -- a term with no stated edge is one two people
    apply differently, and nothing here can see that.
    """
    _, tags = corpus()[item]
    unknown = sorted(set(tags) - topics.VOCABULARY)
    assert not unknown, (
        f"{item} declares {unknown}, which is not in the vocabulary of topics "
        f"spec §3.3. Add the term to VOCABULARY in "
        f"docs/src/_ext/tephpy_topics_data.py and its covers/not definition to "
        f"that table, in the same change."
    )


def test_every_vocabulary_term_is_used():
    """Topics spec §3.7, assertion 3: an unused term is a typo or a residue.

    It is the direction the per-item tests cannot check. A term nothing declares
    survives every one of them, and is either a misspelling of a term that is used
    or what a deleted page left behind.
    """
    used = set(topics.coverage(corpus()))
    unused = sorted(topics.VOCABULARY - used)
    assert not unused, f"no item declares {unused}"
```

Add the imports the file now needs: `from pathlib import Path`, `from tephpy import
examples`.

- [ ] **Step 7: Run the gate**

Run: `pixi run -e test pytest tests/test_docs_topics.py -q`
Expected: PASS. Nineteen items, each with two to four known tags, and every one of the
seventeen terms used at least once.

If `test_every_vocabulary_term_is_used` fails, a term the vocabulary defines is declared
nowhere — which under the tagging above can only happen if Step 5 revised a page away
from the last item carrying that term. Either restore it where it belongs or drop the
term from `VOCABULARY` and from the §3.3 table together.

- [ ] **Step 8: Run the glossary gate over the real tree**

Run: `pixi run -e docs python .github/scripts/check_glossary_links.py`
Expected: `glossary links ok: 50 spellings, N pages`. This is the assertion that Step 3
actually covered the fourteen pages Step 5 tagged, rather than the two the measurement
used.

- [ ] **Step 9: Correct topics spec §3.2 and close its open item**

The specification is a living document and this is the section the implementation
falsified. Replace §3.2's narrative-page paragraph and example with:

````markdown
**Narrative pages** declare an rST field list on the **first line of the file**, above
the `.. _label:` target where there is one:

```rst
:tags: units, sounding

.. _howto-units:

Work With Units
===============

.. readingtime::
```

The position is the whole rule, and it was measured rather than reasoned. Sphinx's
metadata collector lifts a docinfo field list into `env.metadata[docname]` and removes it
from the doctree — so it renders nothing, which matters here specifically, because a
rendering directive would have to coexist with the `readingtime` banner at the top of
these same pages. But it does that only for a field list **preceding every other piece of
markup**. A field list written under the title, which this section first proposed, leaves
`env.metadata` empty and renders a visible definition list at the reader: the exact
failure this section named as its risk. Measured on 2026-09-03 against a build in the
`docs` environment, in three placements. `env.metadata` holds the field body as one
string, `{'tags': 'units, sounding'}`, so the adapter splits on commas.

The declaration has one consequence outside Sphinx. `check_glossary_links.py` reads a
page's lines as narrative prose and requires the first mention of a glossary term to
carry `:term:`; a `:tags:` line scanned as prose makes the tag list that first mention,
and demands a role a docinfo field list cannot carry. Three vocabulary terms are also
glossary spellings — `parcel`, `projection`, `sounding` — so this is not a corner case.
`prose()` therefore skips a leading field list, in the same category as the rule it
already carries for a directive's options and body.
````

Then in §8, replace the first open item with:

```markdown
- **Closed** (2026-09-03) — **the field-list metadata mechanism (§3.2).** Established by
  build: a `:tags:` field list reaches `env.metadata` and renders nothing, but only on
  the first line of the file, not under the title as this document first proposed. §3.2
  carries the measurement and the correction. The fallback directive was not needed.
```

- [ ] **Step 10: Lint and commit**

```bash
pixi run lint
git add .github/scripts/check_glossary_links.py tests/test_glossary_links.py \
        docs/src/tutorials docs/src/howtos docs/src/explanation \
        tests/test_docs_topics.py \
        docs/src/developer/specs/2026-09-03-topic-discovery-design.md
git commit -m "Tag the narrative quadrants and gate the corpus"
```

---

## Task 3: The Extension and the Page

The adapter, the published page, and the four registration sites a new published page
touches. No filter yet — this task delivers the list, which topics spec decision 1 says
is the actual feature: "nineteen items fit on one screen, so a filter over them is a
convenience rather than the feature."

**Files:**
- Create: `docs/src/_ext/tephpy_topics.py`
- Create: `docs/src/topics.rst`
- Modify: `docs/src/conf.py`, the `extensions` list
- Modify: `docs/src/index.rst`, the hidden toctree
- Modify: `tests/test_docs_readingtime.py`, `EXEMPT`
- Modify: `docs/src/developer/specs/2026-08-31-reading-time-design.md`, §3.7
- Modify: `docs/src/developer/docs-style.rst`, "Reading Time" prose and a new "Topic Tags" section

**Interfaces:**
- Consumes: `tephpy_topics_data.split_tags`, `read_gallery_tags`, `read_page_tags`, `promote`, `QUADRANTS`.
- Produces: the `topicindex` directive; the built page at `docs/_build/html/topics.html`, one `<li data-topics='[...]'>` per corpus item, and a `<div id="teph-topic-filter" hidden>` carrying one `<button data-topic="...">` per promoted term. Task 4's JavaScript is written against exactly those hooks.

- [ ] **Step 1: Write the extension**

Create `docs/src/_ext/tephpy_topics.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""The topic index page and its filter buttons (topics spec §3.6).

The Sphinx half of the taxonomy. Everything that is a rule rather than an
adapter lives in ``tephpy_topics_data``, which imports nothing outside the
standard library so that the gate over it runs where Sphinx is absent
(topics spec §3.5).

The index is assembled at ``doctree-resolved`` rather than while the page is
read, because it is the first event at which every document's metadata has been
collected -- a directive building the list as its own page is parsed would see
whichever pages happened to be read first.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
import tephpy_topics_data as data

if TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)

#: The three quadrants whose pages declare tags in page metadata. The gallery's
#: five declare in their own source, which is the only spelling sphinx-gallery
#: reads (topics spec §3.2).
NARRATIVE = ("tutorials", "howtos", "explanation")

#: What each quadrant is called on the page. Presentation rather than taxonomy,
#: so it lives here and not in the data module -- nothing in the promotion rule
#: or the gate has an opinion about the word "How-To Guides".
LABELS = {
    "tutorials": "Tutorials",
    "howtos": "How-To Guides",
    "explanation": "Explanation",
    "gallery": "Gallery",
}


class topicindex(nodes.Element):  # noqa: N801
    """Placeholder for the index, replaced once every document has been read."""


class topicitem(nodes.list_item):  # noqa: N801
    """One corpus item, carrying its tags as a ``data-topics`` attribute.

    A ``list_item`` rather than a bare ``Element``: docutils validates a
    ``bullet_list``'s content model, and the custom rendering is the writer's
    business rather than the tree's.
    """


class TopicIndexDirective(SphinxDirective):
    """Mark where the topic index goes."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        """Return the placeholder.

        Returns
        -------
        list of docutils.nodes.Node
            The placeholder, resolved after every document has been read.

        """
        return [topicindex("")]


def examples_dir(app: Sphinx) -> Path:
    """Return the directory sphinx-gallery scrapes its examples from.

    Read from ``sphinx_gallery_conf`` rather than written out again: the path is
    already declared once in ``conf.py``, and a second copy here would keep
    working after the first moved.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.

    Returns
    -------
    Path
        The examples directory.

    """
    return Path(app.srcdir) / app.config.sphinx_gallery_conf["examples_dirs"][0]


def build_corpus(app: Sphinx) -> dict[str, tuple[str, list[str]]]:
    """Assemble the tagged corpus of topics spec §3.1.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.

    Returns
    -------
    dict
        Docname to ``(quadrant, tags)``. A narrative page's docname is already
        ``"<quadrant>/<stem>"``, and sphinx-gallery writes its pages at
        ``"gallery/<stem>"``, so the key is the docname throughout.

    """
    env = app.env
    found: dict[str, tuple[str, list[str]]] = {}
    for docname in sorted(env.found_docs):
        quadrant, _, stem = docname.partition("/")
        if quadrant not in NARRATIVE or not stem or stem == "index":
            continue
        tags = data.split_tags(env.metadata.get(docname, {}).get("tags", ""))
        # The gate reads these declarations out of the source text and this reads
        # them out of Sphinx's metadata, which is two readers of one declaration.
        # They can only disagree by one being wrong, and the page would then show
        # tags the gate never checked -- so the disagreement is the thing worth
        # catching, rather than either reader alone.
        declared = data.read_page_tags(
            Path(env.doc2path(docname)).read_text(encoding="utf-8")
        )
        if declared != tags:
            logger.warning(
                "topic tags disagree: the source declares %s and Sphinx read %s. "
                "A `:tags:` field list reaches page metadata only on the first "
                "line of the file (topics spec §3.2).",
                declared,
                tags,
                location=docname,
                type="topics",
                subtype="declaration",
            )
        if not tags:
            logger.warning(
                "declares no topic tags (topics spec §3.1)",
                location=docname,
                type="topics",
                subtype="missing",
            )
        found[docname] = (quadrant, tags)
    for path in sorted(examples_dir(app).glob("plot_*.py")):
        source = path.read_text(encoding="utf-8")
        found[f"gallery/{path.stem}"] = ("gallery", data.read_gallery_tags(source))
    if not found:
        msg = "the topic corpus is empty: no narrative page and no gallery example"
        raise ValueError(msg)
    return found


def buttons(promoted: frozenset[str]) -> nodes.raw:
    """Return the filter bar for the promoted terms.

    It is emitted ``hidden`` and unhidden by ``topics.js``. A button bar that
    survives with scripting off is a row of controls that do nothing, which is
    worse than the list on its own -- and the list on its own is what topics spec
    decision 1 calls the feature.

    Parameters
    ----------
    promoted : frozenset of str
        The terms that earned a button (topics spec §3.4).

    Returns
    -------
    docutils.nodes.raw
        The bar, as HTML.

    """
    controls = "".join(
        f'<button type="button" class="teph-topic-button" data-topic="{term}">'
        f"{term}</button>"
        for term in sorted(promoted)
    )
    markup = (
        '<div id="teph-topic-filter" class="teph-topic-filter" hidden>'
        f"{controls}"
        '<button type="button" id="teph-topic-clear" class="teph-topic-clear" '
        'hidden>clear</button>'
        "</div>"
    )
    return nodes.raw("", markup, format="html")


def index(app: Sphinx, fromdocname: str) -> list[nodes.Node]:
    """Build the index for one page.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.
    fromdocname : str
        The document the index is being written into, which is what the relative
        links are computed against.

    Returns
    -------
    list of docutils.nodes.Node
        The filter bar and the item list.

    """
    corpus = build_corpus(app)
    order = {quadrant: rank for rank, quadrant in enumerate(data.QUADRANTS)}
    titles = {name: app.env.titles[name].astext() for name in corpus}
    listing = nodes.bullet_list(classes=["teph-topic-list"])
    for docname in sorted(corpus, key=lambda name: (order[corpus[name][0]], titles[name])):
        quadrant, tags = corpus[docname]
        item = topicitem("", topics=sorted(tags))
        link = nodes.reference(
            "",
            "",
            nodes.Text(titles[docname]),
            internal=True,
            refuri=app.builder.get_relative_uri(fromdocname, docname),
        )
        # A paragraph rather than inlines straight into the item: a `list_item`
        # holds body elements, and it is also what gives the row one flex
        # container to lay its three parts out in.
        row = nodes.paragraph(classes=["teph-topic-row"])
        row += nodes.inline("", "", link, classes=["teph-topic-title"])
        row += nodes.inline("", LABELS[quadrant], classes=["teph-topic-quadrant"])
        row += nodes.inline("", " · ".join(sorted(tags)), classes=["teph-topic-tags"])
        item += row
        listing += item
    return [buttons(data.promote(corpus)), listing]


def resolve(app: Sphinx, doctree: nodes.document, fromdocname: str) -> None:
    """Replace every placeholder with the index.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.
    doctree : docutils.nodes.document
        The resolved doctree.
    fromdocname : str
        The document being written.

    """
    for node in list(doctree.findall(topicindex)):
        node.replace_self(index(app, fromdocname))


def visit_topicitem(self, node: topicitem) -> None:  # noqa: ANN001
    """Open the list item, carrying its tags for the filter."""
    self.body.append(
        self.starttag(
            node,
            "li",
            "",
            CLASS="teph-topic-item",
            **{"data-topics": json.dumps(node["topics"])},
        )
    )


def depart_topicitem(self, node: topicitem) -> None:  # noqa: ANN001, ARG001
    """Close the list item."""
    self.body.append("</li>\n")


def setup(app: Sphinx) -> dict[str, object]:
    """Register the directive, the nodes and the transform.

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
    app.add_node(topicitem, html=(visit_topicitem, depart_topicitem))
    app.add_directive("topicindex", TopicIndexDirective)
    app.connect("doctree-resolved", resolve)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
```

`parallel_write_safe` is `True` because `resolve` reads the environment and writes
only into the doctree it was handed. `topicitem` is registered for the HTML builder
alone, which is the only builder this project runs (`docs/Makefile`).

- [ ] **Step 2: Write the page**

Create `docs/src/topics.rst`. It carries no `readingtime` banner — its body is
generated, and Step 5 records that.

```rst
.. _topics:

Browse by Topic
===============

The four quadrants sort these pages by what you came to do: learn, work, understand,
look up. This page sorts them by what they are *about*.

A topic is orthogonal to an intent. "Units", "getting my data in", "what CAPE means" —
each of those lands in two, three or four quadrants at once, and no quadrant's own
index can show you that. Every tutorial, how-to, explanation page and gallery example
is listed below with the quadrant it belongs to, and the buttons narrow the list to a
topic.

.. topicindex::
```

- [ ] **Step 3: Register the extension and the page**

In `docs/src/conf.py`, add `"tephpy_topics"` to `extensions`, after
`"tephpy_readingtime"`.

In `docs/src/index.rst`, add `topics` to the hidden toctree, after `gallery/index`:

```rst
.. toctree::
    :hidden:

    tutorials/index
    howtos/index
    explanation/index
    reference/index
    gallery/index
    topics
    developer/index
```

The page gets no landing-page card. gallery spec §5 ruled that the landing grid is the
four Diátaxis quadrants and that anything sitting in it reads as a fifth; this page is a
way into all four rather than a peer of them (topics spec §3.6).

- [ ] **Step 4: Build**

Run: `pixi run -e docs docs-html`
Expected: `build succeeded`, no warnings. `--fail-on-warning` means a page whose
declaration Sphinx did not read fails here rather than publishing an untagged row.

Then check the output directly:

```bash
grep -o 'data-topics=' docs/_build/html/topics.html | wc -l          # 19
grep -o 'data-topic="[a-z-]*"' docs/_build/html/topics.html | sort -u   # the 8 promoted
```

Expected: nineteen items, and eight buttons — `analysis`, `data-input`, `diagram`,
`indices`, `isopleths`, `metpy`, `parcel`, `shading`. If Step 5 of Task 2 revised the
tagging, this set may legitimately differ; check it against the rule rather than against
this list, and say so in the pull-request description.

- [ ] **Step 5: Register the page as navigated rather than read**

The reading-time exemption set is written out in **three** places, and all three change
together. Missing one is how this project has broken its own gates before.

1. `tests/test_docs_readingtime.py`, `EXEMPT` — add, in the generated-body group:

```python
    "topics.rst",  # the body is generated by the `topicindex` directive
```

2. `docs/src/developer/specs/2026-08-31-reading-time-design.md` §3.7 — the opening
   sentence becomes "**Thirteen pages**, in three groups", and the table gains a row in
   the generated-body group:

```markdown
| `topics.rst` | generated body | the body is generated by the `topicindex` directive of topics spec §3.6 |
```

3. `docs/src/developer/docs-style.rst`, the "Reading Time" section — the sentence
   listing the exempt set reads "the four Diátaxis landing pages, the developer and
   specification indexes, the site root, the glossary, and the four reference pages
   whose body a directive generates". Add the topic index to it.

- [ ] **Step 6: Document the declaration for contributors**

Add a "Topic Tags" section to `docs/src/developer/docs-style.rst`, after "Reading Time"
and before "Gallery Examples" — the two it sits between are the other two things every
narrative page carries.

```rst
Topic Tags
----------

Every page of the tutorials, how-to and explanation quadrants declares two to four
topic tags, on the **first line of the file**:

.. code:: rst

   :tags: units, sounding

Above the ``.. _label:`` target, with a blank line under it. The position is not a
style choice: Sphinx lifts a field list into page metadata, where nothing renders it,
only when it precedes every other piece of markup. Under the title it renders at the
reader as a stray definition list instead (topics spec §3.2).

The terms are the closed vocabulary of topics spec §3.3, shared with the gallery, each
defined there by what it covers *and* what it excludes. Two to four, for the reason a
gallery example takes two to four: one tag files a page under a single button, and a
full house files it under every one.

``tests/test_docs_topics.py`` discovers the quadrants rather than reading a list, so a
new page fails until it declares tags, and an unknown term fails until it is added to
``VOCABULARY`` and to that table together.

A term earns a filter button on :ref:`topics` by appearing in two or more quadrants and
selecting fewer than half the corpus (topics spec §3.4). Both thresholds are relative,
so nobody edits a number as the documentation grows, and a term that earns no button
still tags its pages and still drives the gallery's own filter.

The reference quadrant and the developer section carry no tags. Reference pages are
lookup surfaces reached by name, and the developer section waits on :issue:`66`.
```

- [ ] **Step 7: Rebuild and run the documentation gates**

```bash
pixi run -e docs docs-html
pixi run -e docs --skip-deps docs-check-links
pixi run -e docs --skip-deps docs-check-citations
pixi run -e test pytest tests/test_docs_readingtime.py tests/test_docs_topics.py -q
```

Expected: all pass. `docs-check-citations` is the one that catches a `topics spec §N`
citation naming an anchor that does not exist, which Step 5 and Step 6 both add.

- [ ] **Step 8: Lint and commit**

```bash
pixi run lint
git add docs/src/_ext/tephpy_topics.py docs/src/topics.rst docs/src/conf.py \
        docs/src/index.rst tests/test_docs_readingtime.py \
        docs/src/developer/specs/2026-08-31-reading-time-design.md \
        docs/src/developer/docs-style.rst
git commit -m "Publish the topic index across the quadrants"
```

---

## Task 4: The Filter

Client-side over the `data-topics` attributes Task 3 emits, in the shape sphinx-gallery's
own `sg-tags.js` already demonstrates — no dependency, and the page degrades to the full
list with scripting off (topics spec §3.6).

**Files:**
- Create: `docs/src/_static/topics.js`
- Modify: `docs/src/_static/tephpy.css`
- Modify: `docs/src/_ext/tephpy_topics.py` — `buttons()` gains the empty-result notice; `setup()` registers the script
- Modify: `docs/src/developer/specs/2026-09-03-topic-discovery-design.md`, §6.3

**Interfaces:**
- Consumes: `#teph-topic-filter`, `button.teph-topic-button[data-topic]`, `#teph-topic-clear`, `li.teph-topic-item[data-topics]` (Task 3).
- Produces: nothing another task reads.

- [ ] **Step 1: Emit the empty-result notice**

Filtering is AND over the selected terms, matching sphinx-gallery's own semantics, so an
empty result is reachable — `indices` and `metpy` share no item. A filter that empties the
page with no explanation reads as a broken page. In `buttons()`, extend the markup:

```python
    markup = (
        '<div id="teph-topic-filter" class="teph-topic-filter" hidden>'
        f"{controls}"
        '<button type="button" id="teph-topic-clear" class="teph-topic-clear" '
        'hidden>clear</button>'
        "</div>"
        '<p id="teph-topic-empty" class="teph-topic-empty" hidden>'
        "No page carries every selected topic. Clear one to widen the list."
        "</p>"
    )
```

- [ ] **Step 2: Write the filter**

Create `docs/src/_static/topics.js`:

```javascript
/*
 * Copyright (c) 2026, tephpy Contributors.
 *
 * This file is part of tephpy and is distributed under the 3-Clause BSD license.
 * See the LICENSE file in the package root directory for licensing details.
 */

/*
 * The topic index's filter (topics spec §3.6).
 *
 * Modelled on sphinx-gallery's `sg-tags.js`, and deliberately not a copy of it:
 * that script discovers its buttons from the tags present on the page, and this
 * one is handed the promoted set the build computed (topics spec §3.4), which is
 * the difference the whole feature turns on. Selection is AND, as it is there.
 *
 * The bar is emitted `hidden` and unhidden here, so a reader with scripting off
 * gets the list rather than a row of controls that do nothing.
 */

(() => {
  const PARAM = "topics";

  const bar = document.getElementById("teph-topic-filter");
  if (bar === null) {
    return;
  }
  const clear = document.getElementById("teph-topic-clear");
  const empty = document.getElementById("teph-topic-empty");
  const buttons = Array.from(bar.querySelectorAll(".teph-topic-button"));
  const items = Array.from(document.querySelectorAll(".teph-topic-item"));
  const selected = new Set();

  const render = () => {
    let shown = 0;
    items.forEach((item) => {
      let tags = [];
      try {
        tags = JSON.parse(item.dataset.topics);
      } catch {
        tags = [];
      }
      const held = new Set(tags);
      const matches = Array.from(selected).every((tag) => held.has(tag));
      item.hidden = !matches;
      if (matches) {
        shown += 1;
      }
    });

    buttons.forEach((button) => {
      const active = selected.has(button.dataset.topic);
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });

    clear.hidden = selected.size === 0;
    empty.hidden = shown > 0;

    const params = new URLSearchParams(window.location.search);
    if (selected.size > 0) {
      params.set(PARAM, Array.from(selected).sort().join(","));
    } else {
      params.delete(PARAM);
    }
    const query = params.toString();
    window.history.replaceState(
      {},
      "",
      query ? `${window.location.pathname}?${query}` : window.location.pathname,
    );
  };

  buttons.forEach((button) => {
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => {
      const tag = button.dataset.topic;
      if (selected.has(tag)) {
        selected.delete(tag);
      } else {
        selected.add(tag);
      }
      render();
    });
  });

  clear.addEventListener("click", () => {
    selected.clear();
    render();
  });

  // Only a term that earned a button is honoured, so a stale or hand-written
  // `?topics=` cannot filter the list down to nothing with no control to undo it.
  const offered = new Set(buttons.map((button) => button.dataset.topic));
  const requested = new URLSearchParams(window.location.search).get(PARAM);
  if (requested) {
    requested
      .split(",")
      .filter((tag) => offered.has(tag))
      .forEach((tag) => selected.add(tag));
  }

  bar.hidden = false;
  render();
})();
```

- [ ] **Step 3: Register the script**

In `tephpy_topics.py`'s `setup()`, before the return:

```python
    # Registered by the extension rather than through `html_js_files` in
    # `conf.py`: the script exists for the page this extension builds and reads
    # the hooks this extension emits, so the two move together. It is inert on
    # every other page -- it returns as soon as the filter bar is absent.
    app.add_js_file("topics.js")
```

- [ ] **Step 4: Style it**

Append to `docs/src/_static/tephpy.css`. The custom properties are
pydata-sphinx-theme's own, so the bar follows the light/dark toggle without a second
palette — the reason the reading-time banner names them rather than borrowing from the
prior art.

```css
/*
 * The topic index and its filter (topics spec §3.6).
 *
 * `.teph-topic-item` is a `<li>` carrying its tags in `data-topics`, hidden by
 * `topics.js` with the `hidden` property rather than an inline `display`, so that
 * nothing here has to out-specify a style attribute to lay the row out.
 */
.teph-topic-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 1.4em;
}

.teph-topic-button,
.teph-topic-clear {
  background: var(--pst-color-surface);
  border: 1px solid var(--pst-color-border);
  border-radius: 999px;
  color: var(--pst-color-text-base);
  cursor: pointer;
  font-size: 0.85rem;
  padding: 0.2em 0.85em;
}

.teph-topic-button:hover,
.teph-topic-clear:hover {
  border-color: var(--pst-color-accent);
}

.teph-topic-button.active {
  background: var(--pst-color-accent);
  border-color: var(--pst-color-accent);
  color: var(--pst-color-background);
}

.teph-topic-clear {
  border-style: dashed;
}

.teph-topic-list {
  list-style: none;
  padding-left: 0;
}

.teph-topic-item {
  border-bottom: 1px solid var(--pst-color-border);
  padding: 0.5em 0;
}

/*
 * `topics.js` hides a row with the `hidden` property, and a `display` on the
 * element itself would out-rank the browser's own `[hidden] { display: none }`
 * -- the filter would then mark rows hidden and hide none of them. The layout
 * therefore sits on the row inside, and this states the rule the JavaScript
 * depends on rather than leaving it to the absence of a declaration above.
 */
.teph-topic-item[hidden] {
  display: none;
}

.teph-topic-row {
  align-items: baseline;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-bottom: 0;
}

.teph-topic-title {
  flex: 1 1 18rem;
}

.teph-topic-quadrant {
  background: var(--pst-color-surface);
  border-radius: 4px;
  color: var(--pst-color-text-muted);
  font-size: 0.75rem;
  padding: 0.1em 0.5em;
  white-space: nowrap;
}

.teph-topic-tags {
  color: var(--pst-color-text-muted);
  font-size: 0.8rem;
}

.teph-topic-empty {
  color: var(--pst-color-text-muted);
}
```

- [ ] **Step 5: Build and check it by hand**

Topics spec §6.3 is explicit that the filter's *behaviour* is not gated — whether a
button works is a browser question, and this project gates correctness of content rather
than of presentation. The build asserts the page exists and carries one `data-topics`
attribute per item; the rest is checked here, once, and recorded.

```bash
pixi run -e docs docs-html
pixi run -e docs --skip-deps docs-check-links
```

Then open `docs/_build/html/topics.html` in a browser and confirm, in both themes:

1. The filter bar appears, with one button per promoted term.
2. Clicking a button narrows the list and marks the button active.
3. Two buttons narrow it further — AND, not OR.
4. A pair sharing no item shows the empty notice rather than a blank page.
5. `clear` appears with the first selection and restores the full list.
6. The URL gains `?topics=…`, and reloading that URL restores the selection.
7. A hand-written `?topics=nonsense` is ignored rather than emptying the list.
8. With JavaScript disabled the bar does not appear and every item is listed.

There is a Chromium in this repository's workflow — `pixi run docs-all` runs
`check_browser_demo.py` through Playwright — but it needs a browser installed by hand
(`AGENTS.md`). If the sandboxed Chromium fails to start for want of system libraries, the
libraries can be borrowed from a sibling pixi environment on the same machine with
`LD_LIBRARY_PATH`; that is a local workaround, not a project mechanism, and belongs in no
committed file.

- [ ] **Step 6: Record the hand-check**

In topics spec §6.3, replace "checked by hand at implementation and recorded here as
having been" with what was actually done: the date, the browser and version, and the
eight behaviours above as a list. A record that says a check happened without saying what
it covered is not a record.

- [ ] **Step 7: Lint and commit**

```bash
pixi run lint
git add docs/src/_static/topics.js docs/src/_static/tephpy.css \
        docs/src/_ext/tephpy_topics.py \
        docs/src/developer/specs/2026-09-03-topic-discovery-design.md
git commit -m "Filter the topic index in the browser"
```

---

## Task 5: The Monthly Report

Promotion changes and the coverage matrix, onto one standing issue (topics spec §3.8).
Modelled on `floors_issue.py` and `ci-floors.yml`, including the `MARKER` dedupe.

**Files:**
- Create: `.github/scripts/topics_issue.py`
- Create: `.github/workflows/ci-topics.yml`
- Create: `tests/test_topics_issue.py`

**Interfaces:**
- Consumes: `tephpy_topics_data.promote`, `coverage`, `read_page_tags`, `read_gallery_tags`, `VOCABULARY`, `QUADRANTS`.
- Produces: nothing another task reads.

- [ ] **Step 1: Decide what the report does with an unchanged month, and write that down**

The specification chose monthly over weekly because "a weekly report that says nothing
most weeks is one nobody reads". The same argument applies within the month, so the
report separates the two things it carries:

- The **issue body** always holds the current picture — the promoted set and the coverage
  matrix — and is rewritten each run. It is a dashboard, and it is never noise.
- A **comment** is posted only when the promoted set changed. That is the notification,
  and a month in which nothing moved produces none.

The previous promoted set is read back out of the body, from a machine-readable marker
the body carries. That round trip is the report's one real failure mode: if the marker
cannot be read, every month reports every term as newly promoted. Step 4 pins it.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_topics_issue.py`, modelled on `tests/test_floors_issue.py` — read that
file first and follow its loader and its guard, since `MANIFEST.in` prunes `.github` and
an sdist ships these tests without the script they read.

```python
def test_the_corpus_matches_the_gate_s(): ...
def test_the_matrix_names_every_used_term_and_every_quadrant(): ...
def test_an_empty_cell_is_rendered_as_a_gap_and_not_omitted(): ...
def test_the_state_marker_round_trips(): ...
def test_changes_reports_a_newly_promoted_term(): ...
def test_changes_reports_a_newly_held_back_term(): ...
def test_changes_is_none_when_the_promoted_set_is_unchanged(): ...
def test_reading_a_body_with_no_marker_is_an_error(): ...
```

Write them with real assertions, not names. The two that carry the weight:

```python
def test_the_state_marker_round_trips():
    """The report's one real failure mode, pinned.

    "Newly promoted since the last run" is computed by reading the previous
    promoted set back out of the issue body. A marker that cannot be read makes
    every month report every term as new, and the report would look like it was
    working -- it would be full of findings.
    """
    promoted = frozenset({"analysis", "diagram", "isopleths"})
    text = report.body(FIXTURE, promoted, run_url="https://example.invalid/1")
    assert report.read_state(text) == promoted


def test_the_corpus_matches_the_gate_s():
    """Two readers of one corpus, and the report is the one nobody looks at.

    The gate assembles the corpus to check it and this script assembles it to
    report on it. They read the same declarations with the same functions, so a
    divergence here is a bug in one of the two assemblies -- and it would show up
    as a report quietly describing a different corpus than the one published.
    """
    from tests.test_docs_topics import corpus as gated

    assert report.corpus(REPO) == gated()
```

- [ ] **Step 3: Run them to verify they fail**

Run: `pixi run -e test pytest tests/test_topics_issue.py -q`
Expected: collection error — the script does not exist.

- [ ] **Step 4: Write the report**

Create `.github/scripts/topics_issue.py`. The shape, with the parts that carry a decision
written out:

```python
#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Report topic promotion changes and the coverage matrix (topics spec §3.8).

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

MARKER = "topic-coverage"

#: The issue this report keeps. One standing issue, edited in place, in the
#: manner of the floors report's dedupe: a monthly finding that filed a new issue
#: each run would bury the one before it.
TITLE = "Topic coverage"

#: The current promoted set, carried in the body so the next run can say what
#: changed. An HTML comment, so it is invisible to a reader and unambiguous to
#: the parser -- a set recovered by scraping the rendered table would break the
#: moment the table's wording changed.
STATE = re.compile(r"<!-- topics-state: (?P<value>\{.*?\}) -->", re.DOTALL)
```

`corpus(repo)` reads the same three quadrants and the same example directory the gate
does, through the same two readers, and returns the same `{docname: (quadrant, tags)}`
shape. Do not re-derive the discovery rule here: import `tephpy_topics_data` by path, in
the manner of `tests/ext_modules.py`, and mirror `tests/test_docs_topics.narrative_pages`
exactly. The test of Step 2 asserts the two agree.

`matrix(corpus)` renders one row per **used** term and one column per quadrant, with a
mark for present and an em dash for absent. Every quadrant gets a column even where the
term appears in none of them, because an empty cell is the report's entire second job:

```markdown
| term | tutorials | how-tos | explanation | gallery |
|---|---|---|---|---|
| `analysis` | ✓ | — | ✓ | ✓ |
```

`body(corpus, promoted, run_url)` composes: a sentence saying what the report is and
what it is not, the promoted table, the matrix, the two recorded limits from topics spec
§3.8 — an empty cell is a candidate for editorial judgement and not a defect, and the
matrix can only see gaps between subjects already written about — the link to
{issue}`261` as the complementary demand signal, the run URL, and the `STATE` marker.

`changes(previous, promoted)` returns a short markdown paragraph naming terms newly
promoted and terms newly held back, or `None` when the two sets are equal.

`main()` takes `--run-url` and `--dry-run`. With `--dry-run` it prints the body and
exits 0, touching no network: that is how the report is checked by hand before the first
scheduled run, and how a reviewer sees what a month's output looks like. Otherwise it
finds the standing issue by `MARKER` label, creates it with the body when there is none,
and otherwise edits the body and — only when `changes` returned something — posts it as
a comment.

Guard the empty case: `promote` raises on an empty corpus, and `main` should let that
propagate rather than filing a report saying nothing is promoted. A report that files
successfully having read nothing is worse than one that fails.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run -e test pytest tests/test_topics_issue.py -q`
Expected: PASS.

- [ ] **Step 6: Look at a month's output**

Run: `python3 .github/scripts/topics_issue.py --run-url https://example.invalid/1 --dry-run`

Read it. On the corpus of 2026-09-03 the matrix should already say something actionable:
`analysis` and `shading` both appear in tutorials, explanation and the gallery and in **no
how-to**, which is conspicuous in a project whose how-to quadrant is its largest at nine
pages (topics spec §3.8). If the report does not make that visible at a glance, the
matrix is rendered wrong, not the corpus.

- [ ] **Step 7: Write the workflow**

Create `.github/workflows/ci-topics.yml`:

```yaml
name: ci-topics

# The coverage report of topics spec §3.8. Scheduled and never a pull-request
# gate: what it reports is editorial judgement, and decision 6 is explicit that
# an empty cell in the matrix is a question rather than a defect. A documentation
# gate that manufactures work makes the documentation worse.
#
# Monthly, not weekly. A documentation corpus moves on pull-request timescales.

on:
  schedule:
    - cron: "23 5 1 * *"
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions: {}

jobs:
  report:
    runs-on: ubuntu-latest
    permissions:
      issues: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false
      - name: File or update the report
        env:
          GH_TOKEN: ${{ github.token }}
          RUN_URL: >-
            ${{ github.server_url }}/${{ github.repository
            }}/actions/runs/${{ github.run_id }}
        # The runner's interpreter rather than a pinned one, for the reason
        # `ci-floors.yml`'s filing job uses it: this script imports nothing
        # outside the standard library and shells out to `gh`, which is on the
        # image, so a pinned interpreter would buy a live download for nothing.
        run: python3 .github/scripts/topics_issue.py --run-url "$RUN_URL"
```

Pin the `actions/checkout` SHA to whatever `ci-floors.yml` currently uses rather than the
one written above — a stale pin here is a second copy that drifts. Confirm the label
`MARKER` names exists in the repository, or have the first run create the issue without
it and add the label by hand; `gh issue create --label` fails on a label that does not
exist, and that failure would be the first scheduled run.

- [ ] **Step 8: Gate the workflow**

Add to `tests/test_topics_issue.py`, following `tests/test_floors.py`'s workflow tests:
the file parses as YAML; its schedule is monthly (`cron` has a day-of-month field and a
wildcard month); the report job grants `issues: write` and the workflow's top-level
`permissions` is empty; and the `run:` step names the script this module tests. The last
is the one that matters — a workflow calling a script that has been renamed fails once a
month, in a run nobody is watching.

- [ ] **Step 9: Lint and commit**

```bash
pixi run lint
git add .github/scripts/topics_issue.py .github/workflows/ci-topics.yml \
        tests/test_topics_issue.py
git commit -m "Report topic coverage once a month"
```

---

## Task 6: The Companion Changes, the Fragment, and the Sweep

**Files:**
- Modify: `docs/src/developer/specs/2026-09-03-topic-discovery-design.md`, §4 and the Scope line
- Create: `changelog/<PR>.documentation.rst`

- [ ] **Step 1: Complete the companion table**

Topics spec §4 exists so "the set is visible in one place", and it is currently short by
four rows. Writing them in is the point of the section; leaving them out is the defect it
was written to prevent. Add:

| File | What it gains |
|---|---|
| `docs/src/_static/topics.js` | the filter, registered by the extension rather than by `conf.py` |
| `docs/src/developer/docs-style.rst` | the "Topic Tags" section, the vocabulary's new home in "Gallery Examples", and the topic index in the "Reading Time" exemption sentence |
| `.github/scripts/check_glossary_links.py` | a leading docinfo field list is metadata, not prose (§3.2) |
| `tests/ext_modules.py` | the shared `_ext` loader, so the vocabulary's move does not add a third copy of it |

And correct the reading-time row: the exemption set is written in **three** places, not
two — `tests/test_docs_readingtime.py`, reading spec §3.7's table, and `docs-style.rst`'s
"Reading Time" prose.

Then amend the Scope line at the head of the document, which currently reads "one
taxonomy module, one Sphinx extension, one published page, one pytest gate, one scheduled
report, and a `:tags:` field list on 14 narrative pages". Add the glossary gate's
amendment: it is not a companion change but a prerequisite, and a scope line that omits it
describes a change that could not have been merged.

- [ ] **Step 2: Write the changelog fragment**

Create `changelog/<PR>.documentation.rst`, where `<PR>` is this pull request's number:

```rst
Added a topic index at :ref:`topics`, listing every tutorial, how-to, explanation
page and gallery example with the quadrant it belongs to, and filterable by topic.
Diátaxis sorts the documentation by the reader's intent; this sorts it by subject,
which is orthogonal to intent and lands in two, three or four quadrants at once.
The seventeen-term vocabulary is shared with the gallery's own tags, and a term
earns a filter button by spanning two or more quadrants while selecting fewer than
half the corpus.
(:user:`claude`)
```

- [ ] **Step 3: Commit, then sweep**

In that order. The pre-commit hooks rewrite files, so a suite run before committing
measures a tree that no longer exists.

```bash
git add changelog docs/src/developer/specs/2026-09-03-topic-discovery-design.md
git commit -m "Record the companion changes and the fragment"
```

Then:

```bash
pixi run lint
pixi run tests
pixi run docs
```

`pixi run docs` runs the five documentation gates (`docs-check-api`,
`docs-check-citations`, `docs-check-figures`, `docs-check-links`,
`docs-check-tooltips`). Expected: all green.

- [ ] **Step 4: Check the things that pass for the wrong reason**

Each of these has a way of passing without having looked. Run them deliberately:

```bash
# The corpus gate found nineteen items, not zero.
pixi run -e test pytest tests/test_docs_topics.py -q --collect-only | tail -3

# The page carries an item per corpus member and a button per promoted term.
# `grep -o | wc -l` counts occurrences; `grep -c` counts lines, and would agree
# with it only for as long as the writer keeps one item to a line.
grep -o 'data-topics=' docs/_build/html/topics.html | wc -l
grep -o 'data-topic="' docs/_build/html/topics.html | wc -l

# The glossary gate ran over the tagged pages rather than skipping them.
pixi run -e docs python .github/scripts/check_glossary_links.py

# The report reads the same corpus the gate does, and its state round-trips.
python3 .github/scripts/topics_issue.py --run-url https://example.invalid/1 --dry-run
```

- [ ] **Step 5: Open the pull request**

Say in the description which of topics spec §6.1's proposed tags were revised on contact
with the pages, and whether that changed the promoted set. The specification records that
tagging as a proposal and not a fact; the pull request is where it becomes one.

---

## Self-Review Notes

**Spec coverage.** Every section of topics spec has a task. §1 and §1.1 are argument and
need no code. §2's seven decisions: 1 is Task 3 (the list ships before the filter), 2 is
Tasks 1-2, 3 is Task 1's `promote` returning a set rather than filtering the vocabulary,
4 is Task 1's relative thresholds, 5 is Task 2's gate asserting the rule and not its
output, 6 is Task 5's report never becoming a gate, 7 is the absence of any dependency
change anywhere in this plan. §3.1 Task 2; §3.2 Task 2; §3.3 Task 1; §3.4 Task 1; §3.5
Tasks 1 and 3; §3.6 Tasks 3 and 4; §3.7 Tasks 1 and 2; §3.8 Task 5; §4 Tasks 3 and 6; §5
is alternatives; §6.1 Task 2; §6.2 Tasks 1 and 2; §6.3 Task 4; §7 Task 6; §8 Task 2
closes the first open item and the other four stay open.

**What this plan adds that the spec does not have.** The glossary-gate prerequisite
(measured, Task 2), the shared `_ext` loader (so the vocabulary's move removes a
duplication instead of adding one, Task 1), the empty-result notice (AND filtering makes
an empty result reachable, Task 4), the body/comment split in the report (so an unchanged
month is silent, Task 5), and the source-versus-metadata cross-check in the extension
(two readers of one declaration, Task 3).

**What is deliberately not gated.** The filter's behaviour (topics spec §6.3, hand-checked
in Task 4 Step 5 and recorded in Step 6). The promoted set itself (topics spec §3.7:
freezing it would fail CI on every page that legitimately changes it, which inverts
decision 4).

**The one number to watch.** `promote` is a rule over a corpus, so every count in this
plan — nineteen items, eight buttons — is a measurement of the corpus of 2026-09-03 and
not a requirement. If Task 2 Step 5 revises a page's tags on contact with the page, these
numbers move, and the correct response is to say so, not to bend the tags back.
