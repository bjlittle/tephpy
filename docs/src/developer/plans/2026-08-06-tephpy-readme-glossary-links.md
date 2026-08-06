# README Glossary Links Implementation Plan

> **Point-in-time record.** This plan captures what was intended before implementation. It
> is not updated afterwards — where the implementation departed from it, the departure is
> recorded in the pull request, and the living design specification in
> [`../specs/`](../specs/) is what describes tephpy as it stands.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define `parcel ascent` in the glossary, and link the README's thermodynamic
terms to their glossary definitions, so the repository landing page is a second way into
the documentation — with a documentation-build gate that fails when one of those links
stops resolving.

**Architecture:** Three pieces, in dependency order. A new glossary entry names the
process the README already calls "parcel ascent", and the existing `parcel` entry is
trimmed of the clause the new one now carries. The README then links seven terms —
tephigram, parcel ascent, CAPE, CIN, LCL, LFC, EL — as Markdown *reference* links, with
the absolute published URLs collected in a block at the foot of the file. Because the
README is not a Sphinx source, nothing in the build sees those links: `nitpicky` checks
only references the build itself resolved. A new stdlib-only script closes that gap from
the outside — it reads each documentation URL out of the README and looks it up in the
HTML the build just produced, requiring the page to exist and the fragment to be an `id`
on it. It derives no slugs of its own; reading the ids off the built page is what keeps it
from drifting away from Sphinx.

**Tech Stack:** Python 3.12 stdlib only (`re`, `pathlib`, `textwrap`) — no new dependency;
pytest; GitHub Actions (`ci-docs.yml`); Sphinx (glossary + `nitpicky` build); towncrier;
pixi.

**Spec:** None. This is documentation authoring plus a gate over the built output; the
published-specifications design (`docs spec`) is scoped to *design-specification*
citations, so a README/glossary gate does not belong in it. The authoring rule goes in
`docs/src/developer/docs-style.rst`, and the reasoning behind the gate goes in its module
docstring, exactly as `check_rendered_citations.py` does.

**Issue:** None. This arose from a reading of `README.md` against the glossary.

## Global Constraints

- **Every pixi invocation carries `--frozen`.** `pixi run --frozen tests`,
  `pixi run --frozen lint`, `pixi run --frozen docs`. Never let pixi re-solve the
  environment.
- **`pixi run --frozen docs` is already a clean build.** The `docs` task declares
  `depends-on = ["docs-clean"]`, so it runs `make clean` first. Do not build with a bare
  `make -C docs html` when verifying links — an incremental build serves a stale page and
  the gate would then be checking yesterday's ids.
- **`git commit` must run inside the pixi environment.** The `pre-commit` hook binary is
  not on the bare `PATH`; a plain `git commit` fails with ``pre-commit` not found`. Use
  `pixi run --frozen bash -c 'git commit -F <file>'`, or run `pixi shell` first. Run
  `pre-commit install` once in a fresh worktree.
- **Bare `python` is not on `PATH`.** Every ad-hoc Python invocation goes through
  `pixi run --frozen python` (or `--environment docs` when it needs the built docs
  environment).
- **Ruff runs `select = ["ALL", "D212"]` at `line-length = 88`**, numpy docstring
  convention, `force-sort-within-sections = true`, and
  `required-imports = ["from __future__ import annotations"]`. Every new `.py` file must
  satisfy all of it.
- **Every source file carries the BSD copyright header** (ruff `CPY001`) — four comment
  lines, copied verbatim from `.github/scripts/check_rendered_citations.py`.
- **`.github/scripts/*.py` has `per-file-ignores = ["FBT001", "T201"]`**, so `print()` is
  permitted there. It is *not* permitted in `tests/`.
- **A script carrying a shebang must be mode `100755`** — ruff's `EXE001` fails it
  otherwise, and all three existing `.github/scripts/*.py` are executable. `chmod +x`
  *then* `git add`, so the bit is what gets staged.
- **`tests/*` has `per-file-ignores = ["ANN001", "ANN003", "ANN201", "ANN202", "DTZ001",
  "SLF001", "D103"]`.** Test functions therefore need no annotations and no docstrings;
  the module docstring and helper docstrings are still required.
- **mypy (`files = ["src/tephpy"]`) and numpydoc-validation (`files: '^src/'`) do not
  reach `.github/scripts/`.** Do not add type-checking or numpydoc scaffolding for them —
  but do write numpydoc `Parameters`/`Returns` sections, because the neighbouring gate
  does and the file should read like it.
- **No new runtime, test or docs dependency.** The gate is stdlib-only.
- **Write no literal section sign (`§`) in any new file.** The pre-commit citation gate
  reads the whole source corpus and rejects a bare `§N` in a file that owns no sections. No
  file this plan creates needs one; do not introduce one to "match" the citation gate's
  docstring, which cites `docs spec §3.7` legitimately because that section exists.
- **The plans directory is out of the checked corpus** (docs spec §3.4), and is excluded
  from the docs build by `exclude_patterns` and `MANIFEST.in`. This file is a plan.

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/src/reference/glossary.rst` | **Modify.** Add the `parcel ascent` / `parcel path` entry; trim the `calc.parcel_path` clause out of `parcel` so the two entries do not restate each other. |
| `README.md` | **Modify.** Seven reference links in the summary paragraph, and the link-definition block at the foot of the file. |
| `.github/scripts/check_readme_links.py` | **Create.** The whole gate: URL extraction, id collection from built pages, the two assertions, the report, and the CLI entry point. One file, mirroring `check_rendered_citations.py`. |
| `tests/test_readme_links.py` | **Create.** Unit tests over synthetic READMEs and synthetic built pages. |
| `.github/workflows/ci-docs.yml` | **Modify.** One step, after the build and after the rendered-citation gate. |
| `docs/src/developer/docs-style.rst` | **Modify.** New "Landing Page Links" section recording the authoring rule, between "Specification Citations" and "Attribute Documentation". |
| `changelog/<PR>.documentation.rst` | **Create.** towncrier fragment. |

**Why the gate is a separate script and not an extension of `check_rendered_citations.py`:**
that gate walks every built page looking for text; this one starts from one file outside
the build and looks up specific URLs. They share no traversal, no parser and no failure
vocabulary. Folding them together would mean one script with two unrelated modes and a
`sys.argv` shape that explains neither.

---

### Task 1: The link gate

**Files:**
- Create: `.github/scripts/check_readme_links.py`
- Create: `tests/test_readme_links.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, used by `tests/test_readme_links.py` in this task and by the CI step in Task 3:
  - `BASE: str` — `"https://tephpy.readthedocs.io/en/latest/"`.
  - `LINK: re.Pattern` — matches a documentation link, group 1 the page path, group 2 the
    fragment or `None`.
  - `ID: re.Pattern` — matches an `id="…"` attribute, group 1 its value.
  - `links(text: str) -> list[tuple[str, str]]` — `(page, anchor)` per link, `""` when a
    link names no fragment.
  - `anchors(page: Path) -> set[str]` — every `id` on one built page.
  - `listed(found: list[str]) -> str` — the report's bounded listing.
  - `main() -> int` — CLI entry point, `0` on success and `1` on failure. Reads
    `sys.argv[1]` as the HTML root and optional `sys.argv[2]` as the README, defaulting to
    `Path(__file__).parents[2] / "README.md"`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_readme_links.py`:

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the README documentation-link gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_readme_links.py"

# As in `test_rendered_citations.py`: `MANIFEST.in` prunes `.github`, so an sdist
# ships these tests without the gate they exercise. The guard sits on the module
# and not inside the tests, because an unconditional import would break
# collection there rather than skip.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="not a checkout of the repository"
)

GLOSSARY = "reference/glossary.html"


def _load():
    """Import the gate by path; ``.github`` is not an importable package."""
    assert SCRIPT.is_file(), f"the README link gate is missing from {SCRIPT}"
    spec = importlib.util.spec_from_file_location("check_readme_links", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


crl = _load() if SCRIPT.is_file() else None


def url(page, anchor=""):
    """Build the published URL of ``page``, naming ``anchor`` when given."""
    return crl.BASE + page + (f"#{anchor}" if anchor else "")


def terms(*names: str):
    """Render a glossary page carrying ``names`` as its term anchors."""
    entries = "".join(f'<dt id="{name}">{name}</dt>' for name in names)
    return f"<html><body><dl>{entries}</dl></body></html>"


def build(tmp_path, pages):
    """Write ``{relative page: html}`` under ``tmp_path`` and return the root."""
    root = tmp_path / "html"
    root.mkdir(parents=True, exist_ok=True)
    for relative, html in pages.items():
        page = root / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(html, encoding="utf-8")
    return root


def readme(tmp_path, text):
    """Write a README under ``tmp_path`` and return its path."""
    path = tmp_path / "README.md"
    path.write_text(text, encoding="utf-8")
    return path


def run(monkeypatch, capsys, root, path):
    """Run the gate over ``root`` and ``path``; return its code and output."""
    monkeypatch.setattr(
        crl.sys, "argv", ["check_readme_links.py", str(root), str(path)]
    )
    code = crl.main()
    return code, capsys.readouterr().out


def flat(out):
    """Undo the wrapping, so an assertion can name a phrase and not a line.

    The report wraps its advice to a terminal width. Asserting on a substring of
    the wrapped text would pin where the line breaks fall, and break on a wording
    change that moved nothing but a word onto the next line.
    """
    return " ".join(out.split())


def test_resolving_links_pass(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE", "term-parcel-ascent")})
    path = readme(
        tmp_path,
        f"[CAPE]({url(GLOSSARY, 'term-CAPE')}) and "
        f"[ascent]({url(GLOSSARY, 'term-parcel-ascent')})",
    )
    code, out = run(monkeypatch, capsys, root, path)
    assert code == 0
    assert "2 checked, 2 naming an anchor" in out


def test_missing_anchor_is_reported(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, f"[ascent]({url(GLOSSARY, 'term-parcel-ascent')})")
    code, out = run(monkeypatch, capsys, root, path)
    assert code == 1
    assert "Missing anchors (1)" in out
    assert f"{GLOSSARY}#term-parcel-ascent" in out
    # The two failures need different fixes, so advice written for the other one
    # sends an author to look for a page that is sitting right where it belongs.
    assert "renaming a term moves its anchor" in flat(out)
    assert "Missing pages" not in out


def test_missing_page_is_reported(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, f"[specs]({url('developer/specs/index.html')})")
    code, out = run(monkeypatch, capsys, root, path)
    assert code == 1
    assert "Missing pages (1)" in out
    assert "developer/specs/index.html" in out
    assert "answers with a 404" in flat(out)
    # An absent page carries no ids, so it must not also be read as a broken
    # anchor: one cause, reported once, or the count overstates the damage.
    assert "Missing anchors" not in out


def test_every_missing_anchor_is_listed(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(
        tmp_path,
        f"[a]({url(GLOSSARY, 'term-CIN')}) [b]({url(GLOSSARY, 'term-LCL')}) "
        f"[c]({url(GLOSSARY, 'term-CAPE')})",
    )
    code, out = run(monkeypatch, capsys, root, path)
    assert code == 1
    # Reporting the first and stopping would send an author round the build once
    # per broken link, with a green tick promised at the end of every pass.
    assert "Missing anchors (2)" in out
    assert "term-CIN" in out
    assert "term-LCL" in out


def test_readme_with_no_links_fails(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(tmp_path, "Plot and analyse tephigrams.")
    code, out = run(monkeypatch, capsys, root, path)
    # A gate is worth what it covers. A rewrite that dropped every link would
    # otherwise turn this into a green tick over an empty search.
    assert code == 1
    assert "links into the documentation nowhere" in out
    assert "green tick standing for nothing" in flat(out)


def test_badge_url_is_not_a_page(tmp_path, monkeypatch, capsys):
    root = build(tmp_path, {GLOSSARY: terms("term-CAPE")})
    path = readme(
        tmp_path,
        "[![RTD](https://app.readthedocs.org/projects/tephpy/badge/?version=latest)]"
        "(https://tephpy.readthedocs.io/en/latest/?badge=latest)\n"
        f"[CAPE]({url(GLOSSARY, 'term-CAPE')})",
    )
    code, out = run(monkeypatch, capsys, root, path)
    # The badge names no page. Reading it as one would fail a good README, and
    # the gate that cries wolf is the gate somebody deletes.
    assert code == 0
    assert "1 checked" in out


def test_usage_is_reported(monkeypatch, capsys):
    monkeypatch.setattr(crl.sys, "argv", ["check_readme_links.py"])
    assert crl.main() == 1
    assert "usage: check_readme_links.py" in capsys.readouterr().out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen tests tests/test_readme_links.py -v`

Expected: every test SKIPPED — `pytestmark` sees no script, so `crl` is `None` and the
module still imports. That skip *is* the red state here, and it is the reason the next step
comes before any assertion about behaviour. Confirm the skip reason reads
`not a checkout of the repository`; anything else means the guard is wrong.

- [ ] **Step 3: Write the gate**

Create `.github/scripts/check_readme_links.py`:

```python
#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that every documentation link in ``README.md`` resolves in the build.

The README is the repository's landing page and is not a source of the Sphinx
project, so it reaches the documentation by absolute URL. Nothing in the build
sees those links: ``nitpicky`` checks the references Sphinx itself resolved, and
the rendered-citation gate reads only pages the build produced. Meanwhile a
glossary anchor is derived from the term -- Sphinx keeps the case and collapses
each run of non-alphanumeric characters to a single hyphen, so ``Normand's
point`` becomes ``term-Normand-s-point`` -- which makes renaming a term a silent
way to break the landing page, and moving a page another.

This gate closes that gap from the outside. It reads the URLs out of the README
and looks each one up in the HTML the build has just produced: the page must
exist, and a fragment must name an ``id`` on it. Nothing here reproduces the slug
rule, because the ids are read off the built page rather than derived. A
normalisation of our own would be one more thing able to drift from Sphinx, which
is the drift this gate exists to catch.

A README carrying no documentation link at all fails too. A check is worth what it
covers, and a rewrite that dropped every link would otherwise pass in silence.

Two things are deliberately not checked. That a link points at the *right* page is
a question about meaning, not resolution, and no gate can answer it. And an
``en/latest`` URL is checked against the working tree's own build, which is the
only build available -- a link correct here is wrong on the published site until
this branch merges, and that is the ordinary lag of a landing page that names a
moving target.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from pathlib import Path
import re
import sys
import textwrap

#: The published documentation, which is what the README links into.
BASE = "https://tephpy.readthedocs.io/en/latest/"
#: A link into a documentation page, with the fragment it names, if any. Only a
#: path ending in ``.html`` is a page: the Read the Docs badge points at the base
#: with a query string and no path, and names nothing this gate can look up.
LINK = re.compile(re.escape(BASE) + r"([\w./-]+\.html)(?:#([\w.:-]+))?")
#: An ``id`` attribute in the built HTML, which is what a fragment must name.
ID = re.compile(r'\bid="([^"]+)"')
#: How many offenders of one kind to name before counting the rest.
SHOWN = 6
#: What to do about a link naming a page the build did not produce.
MISSING_PAGE = (
    "The build produced no such page. A page that is renamed or moved leaves the "
    "README pointing at a URL Read the Docs answers with a 404, and the build "
    "cannot notice, because the README is not one of its sources. Update the link "
    "to the path the page now has, or restore the page under the path the README "
    "names."
)
#: What to do about a link naming a fragment its page does not carry.
MISSING_ANCHOR = (
    "The page renders, but nothing on it carries that id. A glossary anchor is "
    "derived from the term: Sphinx keeps the case and collapses each run of "
    "non-alphanumeric characters to a single hyphen, so renaming a term moves its "
    "anchor and the README goes on naming where it used to be. Copy the id out of "
    "the built page rather than deriving it by hand."
)
#: What to do about a README that links into the documentation nowhere.
BLIND = (
    "A README with no documentation link is not one this check can check, so it "
    "fails rather than passing on an empty search. If the landing page really "
    "should carry none, retire this check along with them: leaving it is a green "
    "tick standing for nothing."
)


def links(text: str) -> list[tuple[str, str]]:
    """Find every documentation link in the README.

    Parameters
    ----------
    text : str
        The README, as Markdown.

    Returns
    -------
    list of tuple of str
        The page path and fragment of each link, in the order they were written,
        with ``""`` for a link naming no fragment.

    """
    return [(page, anchor or "") for page, anchor in LINK.findall(text)]


def anchors(page: Path) -> set[str]:
    """Collect every id one built page carries.

    Parameters
    ----------
    page : pathlib.Path
        A page of the built HTML.

    Returns
    -------
    set of str
        Its ``id`` attributes, which are the fragments it can answer.

    """
    return set(ID.findall(page.read_text(encoding="utf-8")))


def listed(found: list[str]) -> str:
    """Name the first few offenders, and say how many are not named.

    Parameters
    ----------
    found : list of str
        The offenders of one kind.

    Returns
    -------
    str
        The listing. A report that bounds what it shows says what it dropped;
        a count quietly smaller than the total reads as a smaller problem.

    """
    rest = len(found) - SHOWN
    listing = ", ".join(found[:SHOWN])
    return f"{listing} and {rest} more" if rest > 0 else listing


def main() -> int:
    """Check the README's documentation links against the built HTML.

    Returns
    -------
    int
        ``0`` when every link resolves, ``1`` otherwise.

    """
    if not 2 <= len(sys.argv) <= 3:
        print("usage: check_readme_links.py <html-root> [readme]")
        return 1
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"no such directory: {root}")
        return 1
    default = Path(__file__).parents[2] / "README.md"
    readme = Path(sys.argv[2]) if len(sys.argv) == 3 else default
    if not readme.is_file():
        print(f"no such file: {readme}")
        return 1

    found = links(readme.read_text(encoding="utf-8"))
    if not found:
        print(f"{readme.name} links into the documentation nowhere")
        print(f"\n{textwrap.fill(BLIND)}")
        return 1

    pages: dict[str, set[str] | None] = {}
    for page, _ in found:
        if page not in pages:
            built = root / page
            pages[page] = anchors(built) if built.is_file() else None

    absent = sorted(page for page, ids in pages.items() if ids is None)
    # Keyed by page and fragment together, so one broken anchor named twice in
    # the README is one thing to fix and is reported as one.
    broken = sorted(
        {
            f"{page}#{anchor}"
            for page, anchor in found
            # An absent page carries no ids to miss; it is already reported above.
            if anchor and pages[page] is not None and anchor not in pages[page]
        }
    )
    if not absent and not broken:
        named = sum(1 for _, anchor in found if anchor)
        print(
            f"README links ok: {len(found)} checked, {named} naming an anchor, "
            f"across {len(pages)} pages"
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
    print("\nSee 'Landing Page Links' in docs/src/developer/docs-style.rst.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen tests tests/test_readme_links.py -v`

Expected: 7 passed, 0 skipped.

- [ ] **Step 5: Prove the tests are load-bearing**

A prose-heavy gate is easy to test vacuously — an assertion on a phrase that survives the
bug it was written to catch guards nothing. Apply each mutation to
`.github/scripts/check_readme_links.py`, run `pixi run --frozen tests
tests/test_readme_links.py`, confirm the named test fails, then revert it with
`git checkout -- .github/scripts/check_readme_links.py`.

| # | Mutation | Must fail |
|---|---|---|
| M1 | In `main`, truncate the listing: `broken = sorted({...})[:1]` | `test_every_missing_anchor_is_listed` |
| M2 | In `main`, make the empty case pass: replace the `if not found:` body with `return 0` | `test_readme_with_no_links_fails` |
| M3 | Swap the two advice strings: `MISSING_PAGE, MISSING_ANCHOR = MISSING_ANCHOR, MISSING_PAGE` immediately after they are defined | `test_missing_anchor_is_reported` **and** `test_missing_page_is_reported` |
| M4 | Relax the page pattern: `LINK = re.compile(re.escape(BASE) + r"([\w./-]*)(?:#([\w.:-]+))?")` | `test_badge_url_is_not_a_page` |

If a mutation leaves every test green, the tests do not yet pin that behaviour — add the
assertion that pins it before moving on. M3 is the one that matters most: the two failures
have different fixes, and advice attached to the wrong one is worse than no advice.

- [ ] **Step 6: Make the gate executable, then lint**

```bash
chmod +x .github/scripts/check_readme_links.py
git add .github/scripts/check_readme_links.py tests/test_readme_links.py
pixi run --frozen lint
```

Expected: pass. Three things will otherwise bite:

- **The mode is load-bearing.** Ruff's `EXE001` fails a file that carries a shebang
  without the executable bit, and every script in `.github/scripts/` is mode `100755`.
  `git add` after `chmod`, so the bit is what gets staged.
- **`pixi run --frozen lint` does not see untracked files**, so the `git add` above is not
  optional — an unstaged new file lints clean by not being looked at.
- **`pre-commit` may not be installed in a fresh worktree.** Run `pre-commit install`
  first if so.

Ruff was run against exactly this source while the plan was written: `tests/*` ignores
`ANN001`/`ANN201`/`ANN202` but *not* `ANN002`, which is why the `terms(*names: str)`
helper is annotated where the plain test functions are not.

- [ ] **Step 7: Commit**

```bash
pixi run --frozen bash -c 'git commit -m "Add a gate for the README documentation links"'
```

Confirm the mode landed: `git show --stat HEAD` should list the script as a new file with
mode `100755`.

---

### Task 2: The glossary entry and the README links

**Files:**
- Modify: `README.md:21-23` (the summary paragraph) and the foot of the file
- Modify: `docs/src/reference/glossary.rst:109-118` (the `parcel` entry, and the new entry
  after it)

**Interfaces:**
- Consumes from Task 1: `.github/scripts/check_readme_links.py`, run as
  `python .github/scripts/check_readme_links.py docs/_build/html`.
- Produces: the anchor `term-parcel-ascent` on `reference/glossary.html`, and seven
  README links, all of which Task 3's CI step then guards.

- [ ] **Step 1: Add the README links, without the glossary entry**

This is the red step, and the order is the point: the README names an anchor the glossary
does not yet carry, so the gate must fail on the real repository and not only on the
fixtures of Task 1.

Replace `README.md:21-23`:

```markdown
Plot and analyse [tephigrams][tephigram]. `tephpy` renders tephigrams on a rotated
temperature-entropy coordinate system and delegates thermodynamic analysis
([parcel ascent][parcel-ascent], [CAPE][cape], [CIN][cin],
[LCL][lcl]/[LFC][lfc]/[EL][el]) to [MetPy](https://github.com/Unidata/MetPy).
```

Append to the foot of `README.md`, after the Status note, separated by a blank line:

```markdown
[tephigram]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-tephigram
[parcel-ascent]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-parcel-ascent
[cape]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-CAPE
[cin]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-CIN
[lcl]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-LCL
[lfc]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-LFC
[el]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-EL
```

The link labels are lowercase because Markdown reference labels are case-insensitive and a
lowercase label reads as a label rather than as the term; the *fragments* keep the case
Sphinx gave them, which is the term's own — `term-CAPE`, not `term-cape`. Getting that
backwards is exactly the failure Task 1's gate reports.

- [ ] **Step 2: Build the docs and run the gate — expect it to fail**

```bash
pixi run --frozen docs
pixi run --frozen --environment docs \
  python .github/scripts/check_readme_links.py docs/_build/html
```

Expected: exit 1, with

```
Missing anchors (1):
  reference/glossary.html#term-parcel-ascent
```

followed by the `MISSING_ANCHOR` paragraph. If it reports `Missing pages` instead, the
build did not produce `reference/glossary.html` — check the build succeeded before
reading the gate's verdict. If it reports more than one missing anchor, one of the six
existing fragments was mistyped; the built ids are the authority:

```bash
grep -o 'id="term-[^"]*"' docs/_build/html/reference/glossary.html | sort -u
```

- [ ] **Step 3: Add the glossary entry and trim `parcel`**

In `docs/src/reference/glossary.rst`, replace the `parcel` entry at lines 109-118 with the
trimmed entry followed by the new one, leaving `lifting condensation level` where it is.
The order is narrative and not alphabetical, as the rest of the file already is: parcel →
parcel ascent → LCL → LFC → EL → CAPE → CIN.

```rst
    parcel
    air parcel
        An imagined small mass of air lifted through the surrounding
        environment without mixing with it — the tephigram's basic tool
        for reasoning about stability. Its :term:`parcel ascent` is what
        the diagram plots; in ``tephpy`` the ``parcel=`` option selects
        which parcel starts one: ``"surface"`` or ``"mixed-layer"`` (the
        lowest 100 hPa averaged).

    parcel ascent
    parcel path
        The path a lifted :term:`parcel` traces on the diagram:
        dry-adiabatically from its start level to the :term:`LCL`, then
        along a :term:`moist adiabat` above it. Comparing that path
        against the environment :term:`sounding` is what yields
        :term:`CAPE`, :term:`CIN`, and the :term:`LFC` and :term:`EL`
        levels — the ascent is the construction, they are its readings.
        :func:`calc.parcel_path(...) <tephpy.calc.parcel_path>` computes
        it as a :class:`calc.Profile <tephpy.calc.Profile>`.
```

Three conventions are being followed here, all from `docs/src/developer/docs-style.rst`:
the `calc.parcel_path` clause moves rather than being duplicated, because a definition
that restates its neighbour makes the neighbour's edits silently incomplete; the API is
cross-referenced with `:func:`/`:class:` keeping the accessor idiom as the link text; and
`parcel` links forward to `parcel ascent` because within a definition related terms are
linked, never the term itself.

- [ ] **Step 4: Rebuild and run the gate — expect it to pass**

```bash
pixi run --frozen docs
pixi run --frozen --environment docs \
  python .github/scripts/check_readme_links.py docs/_build/html
```

Expected: exit 0, `README links ok: 8 checked, 7 naming an anchor, across 2 pages`.

Eight and not seven: the Status note already links `developer/specs/index.html`, which
names no fragment, and that link is now checked too. If the count differs, read what the
gate lists rather than adjusting the expectation.

The build itself must also be clean. `nitpicky` plus the Makefile's `--fail-on-warning`
means a `:term:` or `:func:` that does not resolve fails `pixi run --frozen docs` outright,
so a successful build is the proof that the six cross-references in the new entry land.

- [ ] **Step 5: Read the rendered page**

```bash
pixi run --frozen serve-html
```

Open `http://localhost:11000/reference/glossary.html` and check three things a passing gate
cannot: that `parcel ascent` reads as a definition and not as a restatement of `parcel`;
that `parcel` still stands on its own after the trim; and that each README link, followed
by hand from `http://localhost:11000/`, lands on the entry it names rather than merely on
the page. Then stop the server.

- [ ] **Step 6: Run the full suite and lint**

```bash
pixi run --frozen tests
pixi run --frozen lint
```

Expected: 812 passed plus the 7 from Task 1, and a clean lint.

- [ ] **Step 7: Commit**

```bash
git add README.md docs/src/reference/glossary.rst
pixi run --frozen bash -c 'git commit -m "Define parcel ascent and link the README to the glossary"'
```

---

### Task 3: Wiring, the authoring rule, and the changelog

**Files:**
- Modify: `.github/workflows/ci-docs.yml:28-30`
- Modify: `docs/src/developer/docs-style.rst` — new section after "Specification Citations"
  (ends at line 154) and before "Attribute Documentation" (line 156)
- Create: `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes from Task 1: `.github/scripts/check_readme_links.py`.
- Consumes from Task 2: a README whose links all resolve, so the new CI step is green the
  moment it is added.
- Produces: nothing later tasks rely on. This is the last task.

- [ ] **Step 1: Add the CI step**

Append to the `steps:` list in `.github/workflows/ci-docs.yml`, after the existing
`check_rendered_citations.py` step:

```yaml
      - run: >
          pixi run --frozen --environment docs
          python .github/scripts/check_readme_links.py docs/_build/html
```

It goes in the `docs` job and nowhere else: the gate needs built HTML, which only this job
has. It goes *after* the rendered-citation gate so that when the build itself is broken,
the first failure a reader sees is the one about the build.

- [ ] **Step 2: Verify the step as CI will run it**

```bash
pixi run --frozen --environment docs \
  python .github/scripts/check_readme_links.py docs/_build/html
echo "exit: $?"
```

Expected: `exit: 0`. This runs the same command the workflow does, from the repository
root, which is the working directory GitHub Actions uses. It also exercises the README
default — no second argument, so the gate resolves `Path(__file__).parents[2] / "README.md"`
— which the unit tests of Task 1 never do, because they always pass the path.

- [ ] **Step 3: Record the authoring rule**

Insert into `docs/src/developer/docs-style.rst`, between the "Specification Citations"
section and "Attribute Documentation":

```rst
.. _landing-page-links:

Landing Page Links
------------------

``README.md`` is outside the Sphinx project, so a link from it into the
documentation is an absolute URL to the published site, and is invisible to
everything that checks the rest: ``nitpicky`` sees only the references the build
resolved. Write such a link as a Markdown reference — ``[CAPE][cape]`` in the
prose, with the target defined in the block at the foot of the file — so the
prose stays readable and each URL is stated once:

.. code-block:: markdown

    [cape]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-CAPE

Link the *first* mention of a glossary term in the README and no more, as on a
documentation page. Take the fragment from the built page rather than deriving
it: a glossary anchor is ``term-`` followed by the term with its case preserved
and each run of non-alphanumeric characters collapsed to a single hyphen, so
``CAPE`` gives ``term-CAPE`` and ``Normand's point`` gives
``term-Normand-s-point``. Label the reference in lower case — Markdown labels are
case-insensitive, and a lowercase label is hard to mistake for the fragment,
which is not.

The documentation build checks these links. ``check_readme_links.py`` reads each
URL out of the README and looks it up in the HTML just built, failing when the
page is absent or the fragment names no ``id``. Renaming a glossary term or
moving a page therefore fails the build, rather than leaving the landing page
pointing into a 404 that nobody notices.
```

The heading text must match the gate's closing line, which sends the reader to
``'Landing Page Links' in docs/src/developer/docs-style.rst``. If the heading is reworded,
reword `check_readme_links.py`'s final `print` with it.

- [ ] **Step 4: Add the changelog fragment**

Find the number this PR will take — one past the highest issue or pull request:

```bash
gh api 'repos/bjlittle/tephpy/issues?state=all&per_page=1' --jq '.[0].number'
```

Create `changelog/<that number plus one>.documentation.rst`:

```rst
The glossary now defines :term:`parcel ascent`, the process the landing page has
always named, and the README links its thermodynamic terms — tephigram, parcel
ascent, CAPE, CIN, LCL, LFC and EL — to those definitions, so the repository
front page is a second way into the documentation. The documentation build checks
those links resolve, which nothing else could: the README is not one of its
sources. (:user:`bjlittle`)
```

Attribute to whoever authors the pull request. Rename the fragment if the predicted number
turns out wrong — the number must be the PR's, not the issue's.

- [ ] **Step 5: Rebuild and run everything**

```bash
pixi run --frozen docs
pixi run --frozen --environment docs \
  python .github/scripts/check_readme_links.py docs/_build/html
pixi run --frozen --environment docs \
  python .github/scripts/check_rendered_citations.py docs/_build/html
pixi run --frozen tests
pixi run --frozen lint
```

Expected: a clean build, both gates exit 0, the suite green, lint clean. The rebuild is not
optional — the fragment's `:term:` cross-reference is checked by `nitpicky`, and a stale
build would not have read it.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci-docs.yml docs/src/developer/docs-style.rst changelog/
pixi run --frozen bash -c 'git commit -m "Check the README documentation links in CI"'
```

- [ ] **Step 7: Open the pull request**

Branch prefix `docs/` so `ci-label.yml` applies the `type: documentation` label. Verify the
changelog fragment carries the pull request's own number once it exists, and rename it if
not. Then check the Read the Docs preview at `tephpy--<PR>.org.readthedocs.build` — follow
each README link against `en/latest` by hand once more, because the README's URLs name the
*published* site and the preview is the closest thing to it this branch has.

---

## Notes for the implementer

**What was verified while this plan was written**, against `main` at `04851c3`, with every
scratch file removed afterwards:

- Both Python blocks pass `ruff check` and `ruff format --diff` under the repository's own
  configuration, run from the paths they will occupy so the per-file-ignores apply. The
  `EXE001` and `ANN002` findings that first came out of that run are why Task 1 Step 6 is
  worded as it is.
- The 7 tests of Task 1 pass against the gate of Task 1 — 7 passed, 0 skipped.
- Every mutation in the table kills exactly the tests named beside it, and no others: M1
  and M2 one each, M3 both of the advice tests, M4 the badge test.
- The link extraction over a README carrying Task 2's edits finds 8 links across 2 pages,
  7 naming an anchor — which is where Step 4's expected line comes from — and against the
  glossary *as it stands today* exactly one fragment is absent, `term-parcel-ascent`,
  which is Step 2's expected failure.
- The paragraph Task 2 Step 1 replaces matches `README.md:21-23` verbatim.

What was **not** verified: that a clean build produces `developer/specs/index.html`. The
local build predates the specifications being published, so the page is absent from it, and
the "2 pages" expectation rests on `docs/src/developer/specs/index.rst` existing and not
being excluded — which it is and is not. Read what the gate lists at Step 4 rather than
assuming the count.


**Why the gate reads ids rather than deriving slugs.** The obvious implementation
normalises the term the way Sphinx does and compares strings. That version has to be kept
in step with Sphinx forever, and it fails in the one direction that matters: when Sphinx's
rule changes, the reimplementation agrees with the README and both disagree with the built
page, so the gate passes over a broken link. Reading `id="…"` out of the page the build
just wrote has no such failure mode — there is only one authority and the gate consults it.

**Why not a pre-commit hook.** It was considered and rejected. The `check-citations` hook
runs under `language: python` with no `additional_dependencies`, which means a stdlib-only
isolated environment where Sphinx is not importable and no build output exists. A
pre-commit version would therefore have to derive slugs, which is the failure mode above.
The docs job already has both the environment and the build.

**What this does not check.** That a link points at the *right* term — `[CAPE][cin]` is
wrong and resolves perfectly. Nothing automatic can catch it, which is why Task 2's Step 5
follows each link by hand once.
