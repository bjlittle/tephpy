# Documentation Tooltips Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hover tooltips across the published documentation — every glossary term and every API cross-reference — drawn by `sphinx-tippy`, with its browser runtime vendored rather than fetched, the gallery thumbnails left alone, and a gate holding the four properties whose regression would be silent.

**Architecture:** No new Sphinx extension. `sphinx-tippy` is a conda-forge dependency of the `docs` pixi feature, configured entirely in `docs/src/conf.py`. Its two JavaScript dependencies are committed under `docs/src/_static/js/` and named by `tippy_js`, so no page reaches a CDN. A new build-output gate, `.github/scripts/check_tooltips.py`, reads `docs/_build/html` in the manner of the rendered-citation gate and asserts coverage, the gallery exclusion, the vendoring, and the two runtime guards.

**Tech Stack:** Python 3.12+, Sphinx 8+, `sphinx-tippy` 0.4.3 (conda-forge, `noarch`), tippy.js 6.3.7 and `@popperjs/core` 2.11.8 (vendored UMD bundles), pydata-sphinx-theme, sphinx-design, sphinx-gallery, pixi, pytest, pre-commit.

**Spec:** [`../specs/2026-09-01-tooltips-design.md`](../specs/2026-09-01-tooltips-design.md) — cited below as `tooltip spec §N`. Read it alongside this plan; every task argues from a section of it.

## Global Constraints

- Every source file carries the BSD copyright header (ruff `CPY001`); the exact notice is in `[tool.ruff.lint.flake8-copyright]` in `pyproject.toml`. This applies to `.github/scripts/check_tooltips.py` and `tests/test_tooltips.py`.
- `line-length = 88`; ruff `select = ["ALL"]` with the ignore list in `pyproject.toml`. `.github/scripts/*.py` additionally ignores `FBT001`, `T201` and `INP001` — the scripts print their verdict and are executed by path, not imported as a package.
- ruff isort: `force-sort-within-sections = true`, `required-imports = ["from __future__ import annotations"]`, `known-first-party = ["tephpy"]`.
- numpydoc docstring convention (`[tool.ruff.lint.pydocstyle] convention = "numpy"`). numpydoc *validation* runs over `^src/` only, so a `.github/scripts` module needs docstrings but not the full validated section set. Match the house style of `check_documentation_links.py`: module docstring stating what the gate closes and why, `#:` comments on module constants, then `Parameters`/`Returns` on each function.
- `[tool.pytest.ini_options]` sets `filterwarnings = ["error"]` — a warning in a test is a failure.
- The docs build is `--fail-on-warning --keep-going` (`docs/Makefile:1`). Any Sphinx warning fails `pixi run docs`.
- The gate must fail on an empty search. A gate that passes when it found nothing is a green tick over nothing — the rule `check_citations.py` and `check_github_references.py` both state, and `check_tooltips.py` inherits it.
- `sphinx-tippy` is in the `docs` pixi feature and **not** in `test`. `tests/test_tooltips.py` therefore tests the gate over HTML fixtures it writes itself and imports no Sphinx; it runs on every supported Python.
- Every PR adds `changelog/<PR>.<type>.rst` ending with ``(:user:`claude`)``.
- **Everything in this plan lands together** (tooltip spec §4). The gate ahead of the configuration fails on a build with no tooltips; the configuration ahead of the gate is four properties nothing enforces. Tasks commit individually, but the branch is not mergeable until Task 6.

---

## File Structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | **Modify.** `sphinx-tippy` in the docs feature; the `docs-check-tooltips` task; that task added to `docs`. |
| `requirements/pypi-optional-docs.txt` | **Modify.** The PyPI counterpart of the floor. |
| `pixi.lock` | **Modify.** Re-solved. |
| `docs/src/_static/js/popper.min.js` | **Create.** Vendored `@popperjs/core` 2.11.8 UMD, 20,122 bytes. |
| `docs/src/_static/js/tippy-bundle.umd.min.js` | **Create.** Vendored `tippy.js` 6.3.7 UMD, 25,717 bytes. |
| `.github/scripts/check_citations.py` | **Modify.** `EXCLUDED` gains the vendored directory (tooltip spec §3.2). |
| `docs/src/conf.py` | **Modify.** `sphinx_tippy` in `extensions`, and the configuration block. |
| `.github/scripts/check_tooltips.py` | **Create.** The gate of tooltip spec §3.6. |
| `tests/test_tooltips.py` | **Create.** The gate's four checks, each exercised on a failing fixture. |
| `tests/test_citations.py` | **Modify.** The corpus exemption, from the citation gate's side. |
| `tests/test_github_references.py` | **Modify.** The same exemption, from the side that needed it. |
| `.github/workflows/ci-docs.yml` | **Modify.** The gate's step. |
| `tests/test_docs_workflow.py` | **Modify.** `GATES` gains the task name. |
| `changelog/<PR>.documentation.rst` | **Create.** Fragment. |

Two companion changes of tooltip spec §4 are **already done**, in the commit that added the specification: `docs/src/developer/specs/index.rst` has the `tooltip spec §…` row and its toctree entry. Do not add them again.

### Working-tree state at the time of writing

The design probe left changes in the tree. **Before starting Task 1, reset them** so each task below is exercised rather than assumed:

```bash
git checkout -- pyproject.toml pixi.lock docs/src/conf.py
git rm -r --cached docs/src/_static/js 2>/dev/null || true
rm -rf docs/src/_static/js
```

`docs/src/developer/specs/` and `docs/src/developer/specs/index.rst` are the spec commit and must **not** be reset.

---

## Task 1: Declare the dependency

**Files:**
- Modify: `pyproject.toml` — `[tool.pixi.feature.docs.dependencies]`
- Modify: `requirements/pypi-optional-docs.txt`
- Modify: `pixi.lock` (regenerated, never hand-edited)

**Interfaces:**
- Consumes: nothing.
- Produces: `sphinx_tippy` importable in the `docs` environment. Later tasks rely on the module attribute `sphinx_tippy.__version__` and on the extension name `"sphinx_tippy"`.

- [ ] **Step 1: Add the conda dependency**

In `pyproject.toml`, in `[tool.pixi.feature.docs.dependencies]`, insert between `sphinx-gallery` and `sphinx-togglebutton`:

```toml
sphinx-tippy = ">=0.4.3"
```

`0.4.3` is both floor and ceiling in practice — it is the only release conda-forge carries, and upstream has published nothing since 2024-04-23 (tooltip spec §3.1). Declare it as a floor anyway: `ci-floors` pins floors, and a bare pin here would be a second place for that machinery to disagree with.

- [ ] **Step 2: Add the PyPI counterpart**

In `requirements/pypi-optional-docs.txt`, insert after the `sphinx-gallery` line:

```
sphinx-tippy>=0.4.3
```

- [ ] **Step 3: Re-solve the lock**

```bash
pixi install -e docs
```

Expected: `pixi.lock` gains `sphinx-tippy-0.4.3-pyhcf101f3_0.conda` from `conda-forge/noarch`. Do not edit `pixi.lock` by hand.

- [ ] **Step 4: Verify the extension imports**

```bash
pixi run -e docs python -c "import sphinx_tippy; print(sphinx_tippy.__version__)"
```

Expected: `0.4.3`.

- [ ] **Step 5: Verify the manifest still lints**

```bash
pixi run lint
```

Expected: `Validate pyproject.toml`, `taplo-format` and `check toml` all pass. If `taplo-format` reports "files were modified by this hook", that is it reformatting your insertion — re-run `pixi run lint` and confirm it passes the second time.

`don't commit to branch` fails while you are on `main`; branch before committing.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml requirements/pypi-optional-docs.txt pixi.lock
git commit -m "Declare sphinx-tippy in the docs environment"
```

---

## Task 2: Vendor the browser runtime

The extension's default is `<script src="https://unpkg.com/@popperjs/core@2">` and `<script src="https://unpkg.com/tippy.js@6">` on every page: two floating-major dependencies fetched from a third party by every reader, and no tooltips at all when they are unreachable (tooltip spec §3.2).

**Files:**
- Create: `docs/src/_static/js/popper.min.js`
- Create: `docs/src/_static/js/tippy-bundle.umd.min.js`
- Modify: `.github/scripts/check_citations.py:43`
- Modify: `tests/test_citations.py`
- Modify: `tests/test_github_references.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: the two `_static`-relative paths `js/popper.min.js` and `js/tippy-bundle.umd.min.js`, which Task 3's `tippy_js` names verbatim. `check_citations.EXCLUDED` becomes a two-element tuple.

- [ ] **Step 1: Fetch the two bundles at pinned versions**

```bash
mkdir -p docs/src/_static/js
curl -sSL -o docs/src/_static/js/popper.min.js \
  "https://unpkg.com/@popperjs/core@2.11.8/dist/umd/popper.min.js"
curl -sSL -o docs/src/_static/js/tippy-bundle.umd.min.js \
  "https://unpkg.com/tippy.js@6.3.7/dist/tippy-bundle.umd.min.js"
```

- [ ] **Step 2: Verify what you fetched**

```bash
wc -c docs/src/_static/js/*.js
```

Expected exactly:

```
20122 docs/src/_static/js/popper.min.js
25717 docs/src/_static/js/tippy-bundle.umd.min.js
```

A different size means a different upstream build; do not proceed with one. Both are MIT.

The directory is `_static/js/` and deliberately not `_static/tippy/`, which is where the extension writes its own generated per-page JavaScript, nor `_static/vendor/`, which pydata-sphinx-theme owns for its FontAwesome bundle (tooltip spec §3.2).

- [ ] **Step 3: Stage them, then watch the reference gate fail**

`pre-commit run --all-files` only sees files git knows about, so an unstaged bundle is silently unchecked.

```bash
git add docs/src/_static/js
pixi run lint
```

Expected: `GitHub references are links` **fails** with

```
docs/src/_static/js/tippy-bundle.umd.min.js:1: reference to 333 links to nothing
```

That is `background-color:#333` — tippy's built-in dark theme — read as GitHub issue 333. The script exempts a *quoted* hexadecimal colour, and this is unquoted CSS inside a JavaScript string, so the exemption does not reach it (tooltip spec §3.2).

Every other hook passes on the bundles: `fix end of files`, `trim trailing whitespace`, `mixed line ending`, `codespell`, `check-added-large-files`. None of them needs an exemption.

- [ ] **Step 4: Write the failing tests for the corpus exemption**

Append to `tests/test_citations.py`. Note the `@tracked` marker and the `cc.` handle — both are that module's existing conventions: `tracked` skips where there is no git index to enumerate a corpus from, and `cc` is the loaded checker module:

```python
@tracked
def test_the_corpus_passes_over_the_vendored_runtime():
    """The vendored runtime is not this project's prose (tooltip spec §3.2)."""
    # Asserted alongside the directory being non-empty, because "no corpus path
    # is under a directory that does not exist" is a test that passes for the
    # wrong reason the day the bundles move.
    vendored = REPO / "docs" / "src" / "_static" / "js"
    assert list(vendored.glob("*.js")), "the vendored runtime is missing"
    assert not [path for path in cc.corpus() if vendored in path.parents]
```

Append to `tests/test_github_references.py`. **The number sign must be built from that module's `HASH` constant, never written literally.** This file sits inside the corpus the gate reads, and a literal `#` followed by digits is exactly what the gate exists to reject — it would be right to reject it here. The module's header comment says so, and every fixture in it already does this:

```python
def test_an_unquoted_css_colour_is_still_reported_outside_the_exemption(tmp_path):
    """The exemption is a place, not a pattern (tooltip spec §3.2)."""
    # The vendored bundle is passed over because of where it comes from. The same
    # text in a file this project writes is still judged, which is what keeps the
    # exemption from quietly widening into the colour rule.
    source = tmp_path / "theme.css"
    source.write_text(f"background-color:{HASH}333\n")
    assert gr.check_unlinked([source])
```

No new helper and no new import: `tmp_path` is pytest's, `HASH` and `gr` are already in that module.

- [ ] **Step 5: Run the two tests to verify they fail**

```bash
pixi run -e test pytest tests/test_citations.py::test_the_corpus_passes_over_the_vendored_runtime tests/test_github_references.py::test_an_unquoted_css_colour_is_still_reported_outside_the_vendored_runtime -v
```

Expected: the citations test FAILS (the vendored files are in the corpus); the references test PASSES already (it asserts behaviour the exemption must not remove — it is the guard, not the change).

- [ ] **Step 6: Add the exemption**

In `.github/scripts/check_citations.py`, replace line 43:

```python
EXCLUDED = ("docs/src/developer/plans/",)
```

with:

```python
EXCLUDED = ("docs/src/developer/plans/", "docs/src/_static/js/")
```

In the `corpus()` docstring, after the paragraph ending "…the specifications' own ``index.rst``.", add:

```
    The second exclusion is authorship rather than freezing. ``docs/src/_static/js``
    holds vendored third-party bundles, and docs spec §3.6 and docs spec §3.8 govern
    what this project writes and a reader reads. A minified stylesheet's
    ``background-color:#333`` is not a reference to anything and no prose in it can
    be corrected here (tooltip spec §3.2).
```

- [ ] **Step 7: Run both tests to verify they pass**

```bash
pixi run -e test pytest tests/test_citations.py tests/test_github_references.py -v
```

Expected: PASS, with no other test in either module regressing.

- [ ] **Step 8: Verify the whole hook set is green**

```bash
pixi run lint
```

Expected: everything passes except `don't commit to branch` while on `main`.

- [ ] **Step 9: Commit**

```bash
git add docs/src/_static/js .github/scripts/check_citations.py \
        tests/test_citations.py tests/test_github_references.py
git commit -m "Vendor the tooltip runtime, and exempt it from the corpus"
```

---

## Task 3: Enable and configure the extension

**Files:**
- Modify: `docs/src/conf.py` — the `extensions` list, and a new block before `# -- HTML output`

**Interfaces:**
- Consumes: `sphinx_tippy` from Task 1; the two `_static`-relative paths from Task 2.
- Produces: a build under `docs/_build/html` carrying `_static/tippy/<docname>.<uuid4>.js` per page, each whose first line is `selector_to_html = {…}` — the structure Task 4's gate parses.

- [ ] **Step 1: Register the extension**

In `docs/src/conf.py`, in the `extensions` list, insert between `"sphinx_gallery.gen_gallery",` and `"sphinx_togglebutton",`:

```python
    "sphinx_tippy",
```

- [ ] **Step 2: Add the configuration block**

Immediately before the `# -- HTML output ---` comment in `docs/src/conf.py`, insert:

```python
# -- sphinx-tippy ------------------------------------------------------------
# Hover tooltips over the glossary and the API (tooltip spec §3.3). Every setting
# below changes a default that is wrong here, and the gate of tooltip spec §3.6
# holds four of them.
#
# The three network-reaching sources of tips are off: wiki tips and DOI tips fetch
# while the documentation builds, and `tippy_rtd_urls` fetches each host it names.
# This build does not reach the network, and the cost is recorded rather than
# worked around -- 1,632 external and intersphinx links carry no tooltip
# (tooltip spec §7).
tippy_enable_wikitips = False
tippy_enable_doitips = False
tippy_rtd_urls = []
# pydata-sphinx-theme's article container. Without it the tips reach the navigation
# bar, the sidebar and the breadcrumbs, where a tooltip repeats a link whose
# destination the reader can already read.
tippy_anchor_parent_selector = "article.bd-article"
# `sd-stretched-link` is the extension's own default and must stay. sphinx-design
# builds a card from a zero-size anchor stretched over the card body, so hovering
# anywhere on one of the landing page's four Diátaxis cards is hovering that anchor:
# without this, the *Tutorials* card raises a tooltip that buries the *Explanation*
# card and a third of the viewport. The prior art this block comes from replaces the
# default rather than extending it, which is how that was found (tooltip spec §3.3).
tippy_skip_anchor_classes = ("headerlink", "sd-stretched-link", "sd-sphinx-override")
# Defaults, and `interactive` is the one that matters. A tip is a verbatim copy of
# its target's HTML, so a bare `#fragment` inside it resolves against the page
# *showing* the tip: 781 links in this build point at anchors the host page has not
# got. While the tip cannot be clicked they are unreachable, and setting
# `interactive: True` would turn all 781 into dead links in one line
# (tooltip spec §3.5).
tippy_props = {}
# Vendored and pinned, not fetched from unpkg by every reader of every page. NB not
# `_static/tippy/`, which is where the extension writes its own per-page JavaScript
# (tooltip spec §3.2).
tippy_js = ("js/popper.min.js", "js/tippy-bundle.umd.min.js")
# sphinx-gallery already writes a `tooltip=` on every thumbnail and styles it into a
# hover panel, so without this one hover raises both (tooltip spec §3.4). Two
# patterns because `tippy_skip_urls` is matched with `re.match` -- anchored at the
# start -- against the raw href, which is bare on the gallery index and its
# execution-times page and dotted from anywhere else.
tippy_skip_urls = [
    r"(\.\./)*gallery/plot_\w+\.html",
    r"plot_\w+\.html",
]
```

- [ ] **Step 3: Build the documentation**

```bash
cd docs && pixi run -e docs sphinx-build -b html src _build/html --fail-on-warning --keep-going; cd ..
```

Expected: `build succeeded.`, exit 0, no `WARNING` or `ERROR` lines. The log gains a `Writing tippy data files` phase. A full rebuild costs about four seconds more than before.

- [ ] **Step 4: Verify the four properties by hand, before the gate exists**

```bash
# 1. tips were generated
ls docs/_build/html/_static/tippy/reference/glossary.*.js
# 2. no page reaches a CDN for the runtime
grep -rl "unpkg.com/tippy\|unpkg.com/@popperjs" docs/_build/html --include=*.html | wc -l
# 3. the vendored files are what the pages load
grep -o '<script[^>]*src="[^"]*\(tippy\|popper\)[^"]*"' docs/_build/html/index.html
# 4. the two runtime guards are in the emitted payload
grep -o "interactive: false" docs/_build/html/_static/tippy/index.*.js
grep -o "sd-stretched-link" docs/_build/html/_static/tippy/index.*.js
```

Expected: the glossary payload exists; `0` pages reach a CDN; the script tags name `_static/js/popper.min.js` and `_static/js/tippy-bundle.umd.min.js` with Sphinx's `?v=` cache-busting query; both guards are present.

- [ ] **Step 5: Verify the four existing gates are undisturbed**

```bash
for g in check_api_inventory check_rendered_citations check_docs_figures check_documentation_links; do
  printf "%-28s " "$g"
  pixi run -e docs python .github/scripts/$g.py docs/_build/html >/dev/null 2>&1 && echo PASS || echo FAIL
done
```

Expected: four `PASS`. The extension injects markup into every page, so this is the check that it injects nothing the other gates read.

- [ ] **Step 6: Commit**

```bash
git add docs/src/conf.py
git commit -m "Enable and configure sphinx-tippy"
```

---

## Task 4: The gate

**Files:**
- Create: `.github/scripts/check_tooltips.py`
- Test: `tests/test_tooltips.py`

**Interfaces:**
- Consumes: a build produced by Task 3.
- Produces: module-level names `pages(root) -> list[Path]`, `payloads(root) -> dict[str, dict[str, str]]`, `tipped(payload) -> set[str]`, `article_links(html) -> list[str]`, `check_glossary(root)`, `check_gallery(root)`, `check_vendored(root)`, `check_guards(root)` and `main() -> int`. The four `check_*` return a `list[str]` of violations, empty when the property holds. `tests/test_tooltips.py` loads the module by path and calls the four checks and `main`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tooltips.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the tooltip gate of tooltip spec §3.6."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_tooltips.py"

# `MANIFEST.in` prunes `.github`, so an sdist ships this test without the gate it
# exercises. The gate is a contract about the repository, and that is not the
# repository, so skip there rather than fail collection -- the guard
# `tests/test_citations.py` and `tests/test_github_references.py` both carry.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="not a checkout of the repository"
)


def _load():
    """Load the gate from its path, which is not an importable package."""
    spec = importlib.util.spec_from_file_location("check_tooltips", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load() if SCRIPT.is_file() else None


PAGE = """<html><body><article class="bd-article">{body}</article>
{scripts}</body></html>"""
RUNTIME = (
    '<script defer="defer" src="{popper}"></script>'
    '<script defer="defer" src="{tippy}"></script>'
)
VENDORED = {
    "popper": "_static/js/popper.min.js?v=a8c9358f",
    "tippy": "_static/js/tippy-bundle.umd.min.js?v=37ef8ba7",
}
GUARDS = "placement: 'auto-start', maxWidth: 500, interactive: false,"
SKIPS = '["headerlink", "sd-stretched-link", "sd-sphinx-override"]'


def build(tmp_path, pages, payloads, *, runtime=None, guards=GUARDS, skips=SKIPS):
    """Write a minimal build tree and return its root.

    ``pages`` maps a docname to the HTML of its article body; ``payloads`` maps a
    docname to ``{href: tip html}``. Anything absent gets the passing default.
    """
    runtime = RUNTIME.format(**(runtime or VENDORED))
    for docname, body in pages.items():
        page = tmp_path / f"{docname}.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(PAGE.format(body=body, scripts=runtime), encoding="utf-8")
    for docname, tips in payloads.items():
        js = tmp_path / "_static" / "tippy" / f"{docname}.0123abcd.js"
        js.parent.mkdir(parents=True, exist_ok=True)
        entries = ", ".join(
            f'"a[href=\\"{href}\\"]": "{html}"' for href, html in tips.items()
        )
        js.write_text(
            f"selector_to_html = {{{entries}}}\n"
            f"skip_classes = {skips}\n"
            f"tippy(link, {{ content: tip_html, {guards} }});\n",
            encoding="utf-8",
        )
    return tmp_path


TERM = '<a href="reference/glossary.html#term-tephigram">tephigram</a>'
THUMB = '<a href="gallery/plot_sounding.html">A Sounding</a>'


def test_a_glossary_link_with_a_tip_passes(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {"reference/glossary.html#term-tephigram": "<dd>a diagram</dd>"}},
    )
    assert gate.check_glossary(root) == []


def test_a_glossary_link_without_a_tip_is_reported(tmp_path):
    root = build(tmp_path, {"index": TERM}, {"index": {}})
    found = gate.check_glossary(root)
    assert found
    assert "term-tephigram" in found[0]


def test_a_build_with_no_glossary_link_at_all_is_reported(tmp_path):
    # The positive assertion of tooltip spec §3.6. A build in which the extension
    # silently produced nothing satisfies every other check most completely.
    root = build(tmp_path, {"index": "<p>no links here</p>"}, {"index": {}})
    found = gate.check_glossary(root)
    assert found
    assert "no glossary" in found[0].lower()


def test_a_tipped_gallery_link_is_reported(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM + THUMB},
        {
            "index": {
                "reference/glossary.html#term-tephigram": "<dd>a diagram</dd>",
                "gallery/plot_sounding.html": "<h1>A Sounding</h1>",
            }
        },
    )
    found = gate.check_gallery(root)
    assert found
    assert "plot_sounding" in found[0]


def test_an_untipped_gallery_link_passes(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM + THUMB},
        {"index": {"reference/glossary.html#term-tephigram": "<dd>a diagram</dd>"}},
    )
    assert gate.check_gallery(root) == []


def test_a_page_loading_the_runtime_from_a_cdn_is_reported(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {}},
        runtime={
            "popper": "https://unpkg.com/@popperjs/core@2",
            "tippy": "https://unpkg.com/tippy.js@6",
        },
    )
    found = gate.check_vendored(root)
    assert found
    assert "index.html" in found[0]


def test_a_page_loading_the_vendored_runtime_passes(tmp_path):
    root = build(tmp_path, {"index": TERM}, {"index": {}})
    assert gate.check_vendored(root) == []


def test_this_specification_naming_the_cdn_is_not_a_violation(tmp_path):
    # tooltip spec §6: check 3 must look for the runtime script, not for the
    # string. The specification is a published page and names `unpkg.com` in
    # prose, so a gate that swept the build for it would fail on the document
    # that told it to exist.
    root = build(
        tmp_path,
        {"developer/specs/tooltips": "<p>the default is https://unpkg.com/tippy.js@6</p>"},
        {},
    )
    assert gate.check_vendored(root) == []


def test_an_interactive_payload_is_reported(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {}},
        guards="placement: 'auto-start', maxWidth: 500, interactive: true,",
    )
    found = gate.check_guards(root)
    assert found
    assert "interactive" in found[0]


def test_a_payload_that_dropped_the_stretched_link_class_is_reported(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {}},
        skips='["headerlink", "sd-sphinx-override"]',
    )
    found = gate.check_guards(root)
    assert found
    assert "sd-stretched-link" in found[0]


def test_a_payload_carrying_both_guards_passes(tmp_path):
    root = build(tmp_path, {"index": TERM}, {"index": {}})
    assert gate.check_guards(root) == []


def test_a_build_with_no_payloads_at_all_fails(tmp_path):
    # Every check but the first is satisfied by an empty build.
    root = build(tmp_path, {"index": TERM}, {})
    assert gate.check_guards(root)


@pytest.mark.parametrize("argv", [[], ["a", "b"]])
def test_the_gate_requires_exactly_one_argument(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["check_tooltips.py", *argv])
    assert gate.main() == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pixi run -e test pytest tests/test_tooltips.py -v
```

Expected: every test SKIPS, with reason `not a checkout of the repository` — `.github/scripts/check_tooltips.py` does not exist yet, so `pytestmark` takes the module out. That is the guard working, not the tests passing: `pytest -v` shows `SKIPPED`, never `PASSED`. If you see a pass here, the gate already exists and you are not writing it.

- [ ] **Step 3: Write the gate**

Create `.github/scripts/check_tooltips.py`:

```python
#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that the documentation's tooltips were generated, and stayed scoped.

Tooltips are presentation, and this project gates the correctness of content
rather than its presentation, so nothing here judges how a tooltip looks: not its
palette, its placement, its size, nor whether its text wrapped well. What it
checks is the small set of properties whose regression would be *silent* and
would reach the reader as something worse than no tooltip at all (tooltip
spec §3.6).

Four of them. Every ``:term:`` link on a published page has a tip, and there is at
least one -- the positive assertion, without which a build where the extension
produced nothing passes the other three most completely. No gallery example link
is tipped, because sphinx-gallery already puts a tooltip on those thumbnails and
two of them fire on one hover (tooltip spec §3.4). No page loads the tooltip
runtime from a third party, because ``tippy_js`` is one deleted line away from its
unpkg default and nothing else would say so (tooltip spec §3.2). And the emitted
payload still carries ``interactive: false`` and ``sd-stretched-link``: the first
keeps 781 dead in-tip fragment links unreachable (tooltip spec §3.5), the second
keeps the landing page's four cards from raising a tooltip that buries a third of
the viewport (tooltip spec §3.3). Neither fails a build when it is lost.

The check for the runtime looks for a *script element* whose source is absolute,
not for the string ``unpkg.com``. This gate's own specification is a published
page and names that host in prose, so a sweep for the text would fail on the
document that asked for the gate.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

#: Where the extension writes one JavaScript payload per page, named with a
#: ``uuid4`` -- so the file is found by glob and never by name.
TIPPY = Path("_static") / "tippy"
#: The uuid the extension appends, stripped back to the docname it belongs to.
STAMP = re.compile(r"\.[0-9a-f-]{36}\.js$")
#: A payload's first line, which is the selector map. The rest of the file is the
#: loader, and `json` reads the map once the assignment is removed.
ASSIGNED = re.compile(r"^\s*selector_to_html\s*=\s*")
#: One ``a[href="…"]`` selector, which is the only shape the map's keys take here.
SELECTOR = re.compile(r'a\[href="(.*)"\]$')
#: Links inside the article container -- the same scope `tippy_anchor_parent_selector`
#: gives the extension, so the two agree about which links are in question.
ARTICLE = re.compile(
    r'<article class="bd-article">(.*?)</article>', re.DOTALL
)
#: An anchor's href within that scope.
HREF = re.compile(r'<a\b[^>]*\bhref="([^"]*)"')
#: A glossary term link, by the anchor Sphinx derives from the term.
TERM = re.compile(r"glossary\.html#term-")
#: A gallery example page, bare from the gallery index and dotted from elsewhere.
GALLERY = re.compile(r"(\.\./)*(gallery/)?plot_\w+\.html")
#: A script element and the source it loads.
SCRIPT = re.compile(r'<script\b[^>]*\bsrc="([^"]*)"')
#: The runtime this gate is about, by the file each URL ends in.
RUNTIME = re.compile(r"(tippy|popper)", re.IGNORECASE)
#: A URL that leaves this site.
ABSOLUTE = re.compile(r"^[a-z][a-z0-9+.-]*:|^//", re.IGNORECASE)
#: The two guards of tooltip spec §3.3 and §3.5, as the payload spells them.
GUARDS = ("interactive: false", "sd-stretched-link")


def pages(root: Path) -> list[Path]:
    """Return every published HTML page under ``root``.

    Parameters
    ----------
    root : Path
        The build directory.

    Returns
    -------
    list of Path
        The pages, sorted. The staged browser application is not documentation
        this build wrote, and is passed over.

    """
    return sorted(p for p in root.rglob("*.html") if "browser" not in p.parts)


def payloads(root: Path) -> dict[str, dict[str, str]]:
    """Return each page's selector map, keyed by docname.

    Parameters
    ----------
    root : Path
        The build directory.

    Returns
    -------
    dict
        ``{docname: {selector: tip html}}``.

    """
    found = {}
    for js in (root / TIPPY).rglob("*.js"):
        docname = STAMP.sub("", js.relative_to(root / TIPPY).as_posix())
        first = js.read_text(encoding="utf-8").splitlines()[0]
        found[docname] = json.loads(ASSIGNED.sub("", first).strip().rstrip(";"))
    return found


def tipped(payload: dict[str, str]) -> set[str]:
    """Return the hrefs a payload generates a tip for.

    Parameters
    ----------
    payload : dict
        One page's selector map.

    Returns
    -------
    set of str
        The hrefs, with the selector syntax removed.

    """
    return {m[1] for selector in payload if (m := SELECTOR.match(selector))}


def article_links(html: str) -> list[str]:
    """Return every href inside the article container of ``html``.

    Parameters
    ----------
    html : str
        A rendered page.

    Returns
    -------
    list of str
        The hrefs, in document order. Empty when the page has no article.

    """
    body = ARTICLE.search(html)
    return HREF.findall(body[1]) if body else []


def check_glossary(root: Path) -> list[str]:
    """Report every glossary link with no tip, and a build with no link at all."""
    found, seen = [], 0
    maps = payloads(root)
    for page in pages(root):
        docname = page.relative_to(root).with_suffix("").as_posix()
        has = tipped(maps.get(docname, {}))
        for href in article_links(page.read_text(encoding="utf-8")):
            if not TERM.search(href):
                continue
            seen += 1
            if href not in has:
                found.append(f"{docname}: no tip for the glossary link {href}")
    if not seen:
        found.append(
            "no glossary link was found in the build, so nothing was checked; "
            "a gate that passes on an empty search is a green tick over nothing"
        )
    return found


def check_gallery(root: Path) -> list[str]:
    """Report every gallery example link that carries a tip (tooltip spec §3.4)."""
    found = []
    for docname, payload in payloads(root).items():
        for href in sorted(tipped(payload)):
            if GALLERY.fullmatch(href.split("#")[0]):
                found.append(
                    f"{docname}: {href} is tipped, and sphinx-gallery already "
                    f"puts a tooltip on that thumbnail"
                )
    return found


def check_vendored(root: Path) -> list[str]:
    """Report every page loading the tooltip runtime from off-site."""
    found = []
    for page in pages(root):
        for src in SCRIPT.findall(page.read_text(encoding="utf-8")):
            if RUNTIME.search(src) and ABSOLUTE.match(src):
                found.append(
                    f"{page.relative_to(root)}: loads the tooltip runtime from "
                    f"{src}; tippy_js must name the vendored bundles"
                )
    return found


def check_guards(root: Path) -> list[str]:
    """Report every payload that lost one of the two runtime guards."""
    found = []
    maps = payloads(root)
    if not maps:
        return ["the build wrote no tooltip payload at all"]
    for js in sorted((root / TIPPY).rglob("*.js")):
        text = js.read_text(encoding="utf-8")
        for guard in GUARDS:
            if guard not in text:
                found.append(
                    f"{js.relative_to(root)}: the payload no longer carries "
                    f"{guard!r}"
                )
    return found


def main() -> int:
    """Run the four checks over a build.

    Returns
    -------
    int
        ``0`` when all four hold, ``1`` otherwise.

    """
    if len(sys.argv) != 2:
        print("usage: check_tooltips.py <build directory>")
        return 1
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"{root} is not a directory")
        return 1
    groups = {
        "Glossary links with no tooltip": check_glossary(root),
        "Gallery links that were tipped": check_gallery(root),
        "Pages loading the runtime off-site": check_vendored(root),
        "Payloads missing a runtime guard": check_guards(root),
    }
    total = sum(len(found) for found in groups.values())
    if total == 0:
        counted = sum(len(tipped(p)) for p in payloads(root).values())
        print(
            f"tooltips ok: {counted} tips across {len(payloads(root))} pages "
            f"(tooltip spec §3.6)"
        )
        return 0
    for heading, found in groups.items():
        if found:
            print(f"{heading} ({len(found)}):")
            for violation in found:
                print(f"  {violation}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pixi run -e test pytest tests/test_tooltips.py -v
```

Expected: PASS, every test.

`ARTICLE` matches the exact string `<article class="bd-article">`, which is what pydata-sphinx-theme 0.20 emits on every page of this build — verified across all 81 of them, with no second variant. It is deliberately not loosened: should a theme upgrade add an attribute, `article_links` returns nothing for every page, and check 1 fails with "no glossary link was found in the build" rather than passing on an empty search. The narrow pattern is what makes that failure loud.

- [ ] **Step 5: Run the gate against the real build**

```bash
pixi run -e docs python .github/scripts/check_tooltips.py docs/_build/html
```

Expected: exit 0 and a line of the shape `tooltips ok: 2544 tips across 64 pages (tooltip spec §3.6)`. The counts move with the documentation and must not be asserted in a test.

- [ ] **Step 6: Prove the gate can fail on the real build**

Temporarily comment out the two `tippy_skip_urls` patterns in `docs/src/conf.py`, rebuild, and re-run the gate.

Expected: `Gallery links that were tipped (10):` — five on the gallery index and five on its execution-times page. **Restore the patterns and rebuild before continuing.** A gate only ever seen passing has not been seen working.

- [ ] **Step 7: Verify lint**

```bash
pixi run lint
```

Expected: `ruff check`, `ruff format`, `codespell` and the copyright rule all pass on both new files.

- [ ] **Step 8: Commit**

```bash
git add .github/scripts/check_tooltips.py tests/test_tooltips.py
git commit -m "Add the tooltip gate"
```

---

## Task 5: Wire the gate into pixi and CI

**Files:**
- Modify: `pyproject.toml` — a new task, and the `docs` aggregate
- Modify: `.github/workflows/ci-docs.yml`
- Modify: `tests/test_docs_workflow.py:249-255`

**Interfaces:**
- Consumes: `.github/scripts/check_tooltips.py` from Task 4.
- Produces: the pixi task name `docs-check-tooltips`, which `GATES` and the workflow both name.

- [ ] **Step 1: Write the failing test**

In `tests/test_docs_workflow.py`, add `"docs-check-tooltips"` to the `GATES` set (line 249-255), after `"docs-check-figures"`:

```python
GATES = {
    "docs-html",
    "docs-check-api",
    "docs-check-citations",
    "docs-check-links",
    "docs-check-figures",
    "docs-check-tooltips",
    "docs-browser-test",
}
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pixi run -e test pytest tests/test_docs_workflow.py -v -k "gates or aggregates"
```

Expected: `test_the_workflow_runs_the_documentation_gates_by_task_name` FAILS — the workflow names five tasks, `GATES` now has six. `test_the_local_aggregates_run_every_gate_the_workflow_runs` FAILS too.

- [ ] **Step 3: Declare the pixi task**

In `pyproject.toml`, after the `docs-check-figures` task block, add:

```toml
[tool.pixi.feature.docs.tasks.docs-check-tooltips]
cmd = "python .github/scripts/check_tooltips.py docs/_build/html"
depends-on = ["docs-html"]
description = "Check that the tooltips were generated and stayed scoped"
```

- [ ] **Step 4: Add it to the fast aggregate**

In the `[tool.pixi.feature.docs.tasks.docs]` block, add `"docs-check-tooltips"` to `depends-on`, keeping the list alphabetical:

```toml
depends-on = [
  "docs-check-api",
  "docs-check-citations",
  "docs-check-figures",
  "docs-check-links",
  "docs-check-tooltips",
]
```

It belongs in `docs` and not only in `docs-all`: `EXEMPT` in `tests/test_docs_workflow.py` holds `docs-browser-test` alone, because that gate needs a Chromium no environment here installs. This one needs nothing the build does not already have.

- [ ] **Step 5: Add the workflow step**

In `.github/workflows/ci-docs.yml`, after the `Check the API gate's surface` step:

```yaml
      - name: Check the tooltips
        run: pixi run --frozen --environment docs --skip-deps docs-check-tooltips
```

`--skip-deps` is correct here for the reason the block comment above those steps gives: every gate depends on `docs-html`, which the first step already ran, and without the flag this step would clean and rebuild the documentation in full. `test_no_step_skips_a_dependency_no_earlier_step_ran` holds that.

- [ ] **Step 6: Run the tests to verify they pass**

```bash
pixi run -e test pytest tests/test_docs_workflow.py tests/test_pixi_tasks.py -v
```

Expected: PASS, every test in both modules.

- [ ] **Step 7: Run the aggregate end to end**

```bash
pixi run docs
```

Expected: the build, then five gates, all passing. This is the command `CONTRIBUTING.md` and the pull-request template name, and it now runs the tooltip gate.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .github/workflows/ci-docs.yml tests/test_docs_workflow.py
git commit -m "Run the tooltip gate from pixi and ci-docs"
```

---

## Task 6: Changelog, and the whole-branch check

**Files:**
- Create: `changelog/<PR>.documentation.rst`

- [ ] **Step 1: Write the fragment**

Create `changelog/<PR>.documentation.rst`, where `<PR>` is this pull request's number:

```rst
Added hover tooltips across the documentation, drawn by `sphinx-tippy
<https://github.com/chrisjsewell/sphinx-tippy>`_. Every glossary term and every
API cross-reference now shows its definition on hover, without leaving the page.
The tooltip runtime is vendored rather than fetched from a CDN, so the tooltips
work offline and no page reaches a third party. (:user:`claude`)
```

Attribution goes to `:user:`claude``, per the project's convention.

- [ ] **Step 2: Verify the changelog gate**

`ci-changelog.yml` runs the gate from `.github/scripts`, passing the pull request number and the comma-separated list of changed fragment paths. Reproduce it locally with the same two arguments:

```bash
cd .github/scripts && \
  pixi run -e devs python changelog.py <PR> changelog/<PR>.documentation.rst; \
  cd ../..
```

Expected: exit 0. The gate checks that the fragment is named for its pull request, carries a recognised towncrier type, and ends with the `:user:` attribution.

- [ ] **Step 3: Run the full test suite**

```bash
pixi run tests
```

Expected: PASS, with no regression anywhere. This is the run that catches a corpus change in Task 2 breaking a test that counted files.

- [ ] **Step 4: Run the full lint**

```bash
pixi run lint
```

Expected: everything passes except `don't commit to branch` if you are still on `main`.

- [ ] **Step 5: Run the full documentation check**

```bash
pixi run docs
```

Expected: build clean under `--fail-on-warning`, then five gates passing.

- [ ] **Step 6: Confirm the reader-facing behaviour by hand**

The gate does not judge how a tooltip looks, and tooltip spec §7 records that as a standing limit rather than a deferral. Before opening the pull request, serve the build and look:

```bash
pixi run serve-html
```

Then, at `http://localhost:11000`:

1. Hover a glossary term in a tutorial — a tooltip with the definition appears.
2. Hover a card on the landing page — **no** tooltip appears.
3. Hover a gallery thumbnail — sphinx-gallery's own tooltip only, with no second panel over it.
4. Switch the theme light to dark — the tooltip is legible in both. It is the library's built-in dark in each; it does not follow the theme, and tooltip spec §5 records why.

- [ ] **Step 7: Commit**

```bash
git add changelog/
git commit -m "Add the changelog fragment for the documentation tooltips"
```

---

## What this plan does not do

Each of these is recorded in the specification as a limit rather than a gap. None is a task here, and none should be added to this plan without amending the spec first.

- **Tooltips on external and intersphinx links.** All three sources of them reach the network at build time. 1,632 links carry no tooltip as a result (tooltip spec §7).
- **Fixing the 781 dead fragment links inside tip bodies.** They are unreachable while `interactive` is `false`, which Task 4's fourth check enforces. Upstream [#33](https://github.com/chrisjsewell/sphinx-tippy/pull/33) is the fix (tooltip spec §3.5, §8).
- **Making the build byte-reproducible.** The extension names each payload with a `uuid4` (tooltip spec §7).
- **The five mangled sphinx-gallery thumbnail tooltips.** A pre-existing defect in a different component, filed separately (tooltip spec §8).
