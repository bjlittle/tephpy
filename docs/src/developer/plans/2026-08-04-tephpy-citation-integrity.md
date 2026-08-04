# Citation Integrity Implementation Plan

> **Point-in-time record.** This plan captures what was intended before implementation. It
> is not updated afterwards — where the implementation departed from it, the departure is
> recorded in the pull request, and the living design specification in
> [`../specs/`](../specs/) is what describes tephpy as it stands.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pre-commit hook that fails the commit when a design-specification citation
stops resolving, and bring the 36 citations that do not yet meet the rule into line.

**Architecture:** A stdlib-only script reads the MyST anchors out of
`docs/src/developer/specs/*.md` and derives its registry from them — the set of valid
citation prefixes falls out of the anchors themselves, so nothing has to be registered when
a new specification lands. It then asserts three properties over `src/`, `tests/`, the
specifications, `docs/src/conf.py` and `AGENTS.md`: every citation names an anchor that
exists, every anchor sits above the heading it is keyed to, and every numbered heading
carries an anchor. Fenced code blocks are skipped throughout. The script is wired as the
repository's first `repo: local` pre-commit hook, and a pytest repo-invariant runs the same
check in CI for anyone whose hooks are not installed.

**Tech Stack:** Python 3.12 stdlib only (`re`, `pathlib`, `dataclasses`) — no new
dependency; pre-commit (`repo: local`, `language: python`); pytest; towncrier; pixi.

**Spec:** `docs/src/developer/specs/2026-08-03-published-specs-design.md` — cite it as
`docs spec §N`. §3.6 *Citation integrity* is the authority for what the check asserts and
what it deliberately does not; §3.2 defines the citation grammar and the bare-`§N` rule
this plan enforces; §3.3 defines the anchors.

**Issue:** [#86](https://github.com/bjlittle/tephpy/issues/86)

## Global Constraints

- **Every pixi invocation carries `--frozen`.** `pixi run --frozen tests`,
  `pixi run --frozen lint`, `pixi run --frozen docs`. Never let pixi re-solve the
  environment.
- **`git commit` must run inside the pixi environment.** The `pre-commit` hook binary is
  not on the bare `PATH`; a plain `git commit` fails with ``pre-commit` not found`. Use
  `pixi run --frozen bash -c 'git commit -F <file>'`, or run `pixi shell` first.
- **Ruff runs `select = ["ALL", "D212"]` at `line-length = 88`**, numpy docstring
  convention, `force-sort-within-sections = true`, and `required-imports =
  ["from __future__ import annotations"]`. Every new `.py` file must satisfy all of it.
- **Every source file carries the BSD copyright header** (ruff `CPY001`) — four comment
  lines, copied verbatim from `.github/scripts/changelog.py`.
- **`.github/scripts/*.py` already has `per-file-ignores = ["FBT001", "T201"]`**, so
  `print()` is permitted there. It is *not* permitted in `tests/`.
- **mypy (`files = ["src/tephpy"]`) and numpydoc-validation (`files: '^src/'`) do not
  reach `.github/scripts/`.** Do not add type-checking or numpydoc scaffolding for them.
- **No new runtime or test dependency.** The checker is stdlib-only by design; adding one
  would put a dependency in front of `git commit`.
- **The plans directory is out of the checked corpus.** Plans are point-in-time records
  (docs spec §3.4), so their citations are frozen with them. This file is a plan, and its
  own citations are therefore not checked.

---

## File Structure

| File | Responsibility |
|---|---|
| `.github/scripts/check_citations.py` | **Create.** The whole checker: anchor collection, citation parsing, the three assertions, and the CLI entry point. One file because the three assertions share the anchor registry and the fence-skipping reader; splitting them would mean passing the same two structures across a module boundary for no gain. |
| `.github/scripts/README.md` | **Modify.** Widen the one-line purpose so it covers a script run by pre-commit rather than only by a workflow. |
| `tests/test_citations.py` | **Create.** Parser unit tests on synthetic input, plus the repo-invariant that runs the checker over the live tree. |
| `.pre-commit-config.yaml` | **Modify.** Add the first `repo: local` block. |
| `src/tephpy/calc.py`, `src/tephpy/plotting/axes.py`, `tests/test_units.py`, `tests/plotting/test_images.py`, `tests/plotting/test_axes.py`, `tests/plotting/test_isopleth_oracle.py`, `tests/plotting/test_barbs.py` | **Modify.** Ten sites carrying a bare `§N` in a file that owns no sections. |
| `docs/src/developer/specs/2026-08-01-add-logo-design.md` | **Modify.** Five lines where a bare `§N` means the parent's section. |
| `docs/src/developer/specs/2026-08-03-published-specs-design.md` | **Modify.** Eleven such lines, plus the §7 status flip. |
| `changelog/<PR>.internal.rst` | **Create.** towncrier fragment. |

---

### Task 1: The checker

**Files:**
- Create: `.github/scripts/check_citations.py`
- Create: `tests/test_citations.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, all imported by `tests/test_citations.py` in this task and Task 4:
  - `Violation` — frozen dataclass, fields `path: Path`, `line: int`, `message: str`.
  - `read_lines(text: str) -> Iterator[tuple[int, str]]` — 1-indexed lines outside fences.
  - `collect_anchors(specs: Iterable[Path]) -> tuple[dict[str, Anchor], dict[Path, str]]`
    — the global anchor registry keyed by slug (e.g. `"logo-spec-3-5"`), and each spec's
    owning prefix.
  - `Anchor` — frozen dataclass, fields `path: Path`, `line: int`.
  - `citation_pattern(anchors: Iterable[str]) -> re.Pattern[str]` — the citation regular
    expression, built from the discovered prefixes.
  - `display(path: Path) -> str` — a repository-relative path for messages.
  - `check_anchors(specs, anchors, owners) -> list[Violation]` — keying and coverage.
  - `check_citations(paths, anchors, owners) -> list[Violation]` — resolution.
  - `main() -> int` — returns the process exit status.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_citations.py`. The script is not importable as a module — `.github` is
not a package — so it is loaded by path.

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the citation-integrity checker (docs spec §3.6)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_citations.py"


def _load():
    """Import the checker by path; ``.github`` is not an importable package."""
    spec = importlib.util.spec_from_file_location("check_citations", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cc = _load()


def test_fenced_blocks_are_skipped():
    """docs spec §3.3 illustrates the anchor rule inside a fence (docs spec §3.6)."""
    fence = "`" * 3
    text = (
        f"(spec-1)=\n{fence}markdown\n(spec-3-2)=\n"
        f"### 3.2 `plotting`\n{fence}\n## 1. Purpose\n"
    )
    assert [n for n, _ in cc.read_lines(text)] == [1, 6]


def test_fence_state_survives_a_tilde_fence():
    """MyST accepts ``~~~`` as well as backticks; both must toggle the same state."""
    text = "a\n~~~\nhidden\n~~~\nb\n"
    assert [line for _, line in cc.read_lines(text)] == ["a", "b"]


def test_a_prefixed_citation_resolves_to_its_own_namespace(tmp_path):
    """The prefix selects the document: ``logo spec §3`` is not ``spec §3``."""
    spec = tmp_path / "logo.md"
    spec.write_text("(logo-spec-3)=\n### 3. Sizing\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text('"""Doc (logo spec §3)."""\n')
    assert cc.check_citations([src], anchors, owners) == []
    src.write_text('"""Doc (spec §3)."""\n')
    assert len(cc.check_citations([src], anchors, owners)) == 1


def test_a_compound_citation_inherits_the_head_prefix(tmp_path):
    """``spec §3.3, §10`` and ``spec §3.1/§10`` each name two parent sections."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-3-1)=\n### 3.1 A\n\n(spec-10)=\n## 10. B\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text('"""A (spec §3.1/§10) and B (spec §3.1, §10)."""\n')
    assert cc.check_citations([src], anchors, owners) == []


def test_a_compound_citation_reports_the_unresolvable_member(tmp_path):
    """The continuation is checked, not just the head."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-3-1)=\n### 3.1 A\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text('"""A (spec §3.1/§10)."""\n')
    violations = cc.check_citations([src], anchors, owners)
    assert len(violations) == 1
    assert "spec-10" in violations[0].message


def test_the_word_spec_is_matched_without_regard_to_case(tmp_path):
    """A sentence may open with ``Spec §3.2`` (docs spec §3.2)."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-3-2)=\n### 3.2 A\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text('"""Spec §3.2 covers this."""\n')
    assert cc.check_citations([src], anchors, owners) == []


def test_a_bare_reference_in_a_spec_means_that_spec(tmp_path):
    """Inside a specification the bare form points at a neighbour (docs spec §3.2)."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-3-1)=\n### 3.1 A\n\nSee §3.1.\n")
    anchors, owners = cc.collect_anchors([spec])
    assert cc.check_citations([spec], anchors, owners) == []


def test_a_bare_reference_outside_the_specs_is_an_error(tmp_path):
    """``src/`` owns no sections, so a bare ``§N`` has nothing to be relative to."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-6)=\n## 6. Errors\n")
    anchors, owners = cc.collect_anchors([spec])
    src = tmp_path / "mod.py"
    src.write_text('"""Fails inside the §6 taxonomy."""\n')
    violations = cc.check_citations([src], anchors, owners)
    assert len(violations) == 1
    assert "no prefix" in violations[0].message


def test_a_heading_without_an_anchor_is_a_coverage_violation(tmp_path):
    """Every numbered heading carries a target (docs spec §3.3)."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-1)=\n## 1. A\n\n## 2. B\n")
    anchors, owners = cc.collect_anchors([spec])
    violations = cc.check_anchors([spec], anchors, owners)
    assert len(violations) == 1
    assert violations[0].line == 4


def test_an_anchor_keyed_to_the_wrong_heading_is_a_keying_violation(tmp_path):
    """An anchor that drifts still resolves, so keying is checked separately."""
    spec = tmp_path / "parent.md"
    spec.write_text("(spec-1)=\n## 1. A\n\n(spec-9)=\n## 2. B\n")
    anchors, owners = cc.collect_anchors([spec])
    violations = cc.check_anchors([spec], anchors, owners)
    assert len(violations) == 1
    assert "spec-2" in violations[0].message


def test_a_duplicate_anchor_is_reported(tmp_path):
    """Sphinx labels are global, so two specs cannot share a slug (docs spec §3.3)."""
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("(spec-1)=\n## 1. A\n")
    b.write_text("(spec-1)=\n## 1. B\n")
    with pytest.raises(SystemExit):
        cc.collect_anchors([a, b])
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
pixi run --frozen tests tests/test_citations.py -v
```

Expected: collection fails — `FileNotFoundError` from `spec_from_file_location`, because
`.github/scripts/check_citations.py` does not exist yet.

- [ ] **Step 3: Write the checker**

Create `.github/scripts/check_citations.py`:

```python
#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that every design-specification citation resolves (docs spec §3.6).

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[2]
SPECS = REPO / "docs" / "src" / "developer" / "specs"
CORPUS = (
    "src/**/*.py",
    "tests/**/*.py",
    "docs/src/developer/specs/*.md",
    "docs/src/conf.py",
    "AGENTS.md",
)
ANCHOR = re.compile(r"^\((?P<slug>[a-z][a-z-]*?)-(?P<num>\d+(?:-\d+)*)\)=\s*$")
HEADING = re.compile(r"^#{2,6}\s+(?P<num>\d+(?:\.\d+)*)\.?\s+\S")
FENCE = re.compile(r"^\s*(?:`{3}|~{3})")


def display(path: Path) -> str:
    """Render ``path`` relative to the repository when it lies inside it.

    Parameters
    ----------
    path : Path
        The path to render.

    Returns
    -------
    str
        The relative path, or the path unchanged when it is outside the repository
        — which is the case under ``tmp_path`` in the tests.

    """
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


@dataclass(frozen=True)
class Anchor:
    """Where a MyST target was declared."""

    path: Path
    line: int


@dataclass(frozen=True)
class Violation:
    """One failed assertion, rendered as ``path:line: message``."""

    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        """Render the violation for the terminal.

        Returns
        -------
        str
            The violation as ``path:line: message``, path relative to the repository.

        """
        return f"  {display(self.path)}:{self.line}: {self.message}"


def read_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield the 1-indexed lines of ``text`` that sit outside a fenced code block.

    docs spec §3.3 illustrates the anchor rule with a literal target and heading
    inside a fence, so a reader that does not skip fences finds a duplicate anchor
    and a heading in the wrong document (docs spec §3.6).

    Parameters
    ----------
    text : str
        The file contents.

    Yields
    ------
    tuple of (int, str)
        The line number and the line, without its terminator.

    """
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            yield number, line


def collect_anchors(
    specs: Iterable[Path],
) -> tuple[dict[str, Anchor], dict[Path, str]]:
    """Read the anchor registry and each specification's owning prefix.

    Parameters
    ----------
    specs : iterable of Path
        The specification documents to read.

    Returns
    -------
    tuple of (dict, dict)
        The anchors keyed by slug, and the owning prefix keyed by path.

    """
    anchors: dict[str, Anchor] = {}
    owners: dict[Path, str] = {}
    for spec in specs:
        for number, line in read_lines(spec.read_text(encoding="utf-8")):
            match = ANCHOR.match(line)
            if match is None:
                continue
            slug = f"{match['slug']}-{match['num']}"
            if slug in anchors:
                first = anchors[slug]
                print(
                    f"duplicate anchor '{slug}': "
                    f"{display(first.path)}:{first.line} and "
                    f"{display(spec)}:{number}"
                )
                raise SystemExit(1)
            anchors[slug] = Anchor(spec, number)
            owners.setdefault(spec, match["slug"])
    return anchors, owners


def citation_pattern(anchors: Iterable[str]) -> re.Pattern[str]:
    """Build the citation regular expression from the discovered prefixes.

    The registry is derived, not declared (docs spec §3.6): the citation forms are
    the anchor prefixes with hyphens read back as whitespace. Longest first, so
    ``logo spec`` matches before ``spec``.

    Parameters
    ----------
    anchors : iterable of str
        The anchor slugs, e.g. ``logo-spec-3-5``.

    Returns
    -------
    re.Pattern
        A pattern with ``prefix``, ``num`` and ``bare`` groups.

    """
    prefixes = set()
    for slug in anchors:
        parts = slug.split("-")
        digits = next(i for i, part in enumerate(parts) if part.isdigit())
        prefixes.add("-".join(parts[:digits]))
    forms = sorted(prefixes, key=len, reverse=True)
    alternation = "|".join(form.replace("-", r"\s+") for form in forms)
    return re.compile(
        rf"(?P<prefix>{alternation})\s*§(?P<num>\d+(?:\.\d+)*)"
        rf"|§(?P<bare>\d+(?:\.\d+)*)",
        flags=re.IGNORECASE,
    )


def check_citations(
    paths: Iterable[Path],
    anchors: dict[str, Anchor],
    owners: dict[Path, str],
) -> list[Violation]:
    """Assert that every citation names an anchor that exists.

    Parameters
    ----------
    paths : iterable of Path
        The files to scan.
    anchors : dict
        The anchor registry from :func:`collect_anchors`.
    owners : dict
        The owning prefix of each specification, from :func:`collect_anchors`.

    Returns
    -------
    list of Violation
        One entry per unresolved citation.

    """
    pattern = citation_pattern(anchors)
    violations: list[Violation] = []
    for path in paths:
        own = owners.get(path)
        text = path.read_text(encoding="utf-8")
        lines = (
            read_lines(text)
            if path.suffix == ".md"
            else enumerate(text.splitlines(), start=1)
        )
        for number, line in lines:
            carried: str | None = None
            for match in pattern.finditer(line):
                if match["prefix"] is not None:
                    carried = re.sub(r"\s+", "-", match["prefix"].lower())
                    number_text = match["num"]
                elif carried is not None:
                    number_text = match["bare"]
                elif own is not None:
                    carried, number_text = own, match["bare"]
                else:
                    violations.append(
                        Violation(
                            path,
                            number,
                            f"'§{match['bare']}' has no prefix; "
                            f"write 'spec §{match['bare']}'",
                        )
                    )
                    continue
                slug = f"{carried}-{number_text.replace('.', '-')}"
                if slug not in anchors:
                    violations.append(
                        Violation(
                            path,
                            number,
                            f"'§{number_text}' → no anchor '#{slug}'",
                        )
                    )
    return violations


def check_anchors(
    specs: Iterable[Path],
    anchors: dict[str, Anchor],
    owners: dict[Path, str],
) -> list[Violation]:
    """Assert that anchors and numbered headings agree.

    Keying: every anchor sits immediately above the heading it is numbered for.
    Coverage: every numbered heading carries an anchor.

    Parameters
    ----------
    specs : iterable of Path
        The specification documents to check.
    anchors : dict
        The anchor registry from :func:`collect_anchors`.
    owners : dict
        The owning prefix of each specification, from :func:`collect_anchors`.

    Returns
    -------
    list of Violation
        One entry per mis-keyed or unanchored heading.

    """
    violations: list[Violation] = []
    for spec in specs:
        prefix = owners.get(spec)
        if prefix is None:
            violations.append(Violation(spec, 1, "specification declares no anchors"))
            continue
        text = spec.read_text(encoding="utf-8")
        lines = text.splitlines()
        for number, line in read_lines(text):
            heading = HEADING.match(line)
            if heading is None:
                continue
            expected = f"{prefix}-{heading['num'].replace('.', '-')}"
            above = lines[number - 2].strip() if number >= 2 else ""
            match = ANCHOR.match(above)
            if match is None:
                violations.append(
                    Violation(spec, number, f"heading carries no anchor; add ({expected})=")
                )
            elif f"{match['slug']}-{match['num']}" != expected:
                violations.append(
                    Violation(
                        spec,
                        number,
                        f"anchor '{above}' should be '({expected})='",
                    )
                )
    return violations


def main() -> int:
    """Run the three assertions over the corpus.

    Returns
    -------
    int
        ``0`` when every assertion holds, ``1`` otherwise.

    """
    specs = sorted(SPECS.glob("*.md"))
    if not specs:
        print(f"no specifications found under {SPECS.relative_to(REPO)}")
        return 1
    anchors, owners = collect_anchors(specs)
    paths = sorted({path for pattern in CORPUS for path in REPO.glob(pattern)})
    groups = {
        "Unresolved citations": check_citations(paths, anchors, owners),
        "Anchor problems": check_anchors(specs, anchors, owners),
    }
    total = sum(len(found) for found in groups.values())
    if total == 0:
        print(
            f"citations ok: {len(anchors)} anchors, {len(paths)} files "
            f"(docs spec §3.6)"
        )
        return 0
    for heading, found in groups.items():
        if found:
            print(f"{heading} ({len(found)}):")
            for violation in found:
                print(violation)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pixi run --frozen tests tests/test_citations.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Run the checker over the live tree and record the RED state**

```bash
pixi run --frozen python .github/scripts/check_citations.py; echo "exit=$?"
```

Expected: `exit=1`, with `Unresolved citations (22):` and **no** entries under
*Anchor problems* — the anchors are already complete and correctly keyed (54 anchors, 54
numbered headings). If any anchor problem is reported, stop: something regressed in the
specifications and Tasks 2 and 3 are not the fix.

**22, not 36.** The checker sees a citation only when it fails to resolve: the eleven
prefix-less ones in `src/` and `tests/`, and the eleven in the published-specifications
document that name `§10`, `§11` or `§8.5`, which that document does not have. The other 14
— nine in the `add_logo` specification and five here — mean the parent but land on a
section of the same number in the child, so they resolve and stay invisible. That is the
limitation docs spec §3.6 records, seen from the inside. Task 3 corrects all 25 by reading;
only 11 of them will show up in this output.

- [ ] **Step 6: Lint and commit**

```bash
pixi run --frozen lint
pixi run --frozen bash -c 'git add .github/scripts/check_citations.py tests/test_citations.py && git commit -m "Add the citation-integrity checker (docs spec §3.6)"'
```

If ruff objects to a line, fix it rather than adding a `noqa`: `PGH004` and the blanket-noqa
hook both reject unqualified suppressions.

---

### Task 2: Prefix the ten bare citations in `src/` and `tests/`

Ten sites carry a bare `§N` in a file that owns no sections (docs spec §3.2). Each gains
`spec `. Every edited line stays inside ruff's 88-character limit — the longest reaches 87
— so nothing needs rewrapping.

**Files:**
- Modify: `src/tephpy/calc.py:514`, `src/tephpy/plotting/axes.py:160,198,202`
- Modify: `tests/test_units.py:53`, `tests/plotting/test_images.py:5`,
  `tests/plotting/test_axes.py:268,281`, `tests/plotting/test_isopleth_oracle.py:5`,
  `tests/plotting/test_barbs.py:280`

**Interfaces:**
- Consumes: `.github/scripts/check_citations.py` from Task 1, used as the test.
- Produces: no new symbols.

- [ ] **Step 1: Confirm the checker reports exactly these ten sites**

```bash
pixi run --frozen python .github/scripts/check_citations.py | grep "has no prefix"
```

Expected: 11 lines (`src/tephpy/plotting/axes.py:202` carries two, `§3.2` and `§3.3`).

- [ ] **Step 2: Apply the ten edits**

Replace the left text with the right text. These are the whole citation, not whole lines.

| File:line | From | To |
|---|---|---|
| `src/tephpy/calc.py:514` | `instead of the §6 hierarchy.` | `instead of the spec §6 hierarchy.` |
| `src/tephpy/plotting/axes.py:160` | `through the cursor point (§3.2).` | `through the cursor point (spec §3.2).` |
| `src/tephpy/plotting/axes.py:198` | `through the cursor point (§3.2).` | `through the cursor point (spec §3.2).` |
| `src/tephpy/plotting/axes.py:202` | `member value (the §3.2/§3.3` | `member value (the spec §3.2/§3.3` |
| `tests/test_units.py:53` | `fail inside the §6 taxonomy.` | `fail inside the spec §6 taxonomy.` |
| `tests/plotting/test_images.py:5` | `for the tephigram diagram (§8.5).` | `for the tephigram diagram (spec §8.5).` |
| `tests/plotting/test_axes.py:268` | `on an existing axes (§3.5).` | `on an existing axes (spec §3.5).` |
| `tests/plotting/test_axes.py:281` | `shadows the method (§3.2).` | `shadows the method (spec §3.2).` |
| `tests/plotting/test_isopleth_oracle.py:5` | `against tephi (§7).` | `against tephi (spec §7).` |
| `tests/plotting/test_barbs.py:280` | `rebuilt inside-out (§3.2).` | `rebuilt inside-out (spec §3.2).` |

`axes.py:160` and `axes.py:198` are two different methods whose docstrings share the
closing phrase; edit both, and confirm with the count in Step 3 rather than assuming one
replacement covered them.

- [ ] **Step 3: Verify no prefix-less citation remains**

```bash
pixi run --frozen python .github/scripts/check_citations.py | grep -c "has no prefix"
```

Expected: `0`. The overall run still exits 1 — 25 unresolved citations remain in the two
child specifications, which Task 3 fixes.

- [ ] **Step 4: Confirm nothing else moved**

```bash
pixi run --frozen tests
pixi run --frozen lint
```

Expected: the suite passes and lint is clean. These are docstring and comment edits, so a
failure means a line was broken, not a behaviour change.

- [ ] **Step 5: Commit**

```bash
pixi run --frozen bash -c 'git add src tests && git commit -m "Prefix the bare section references in src and tests"'
```

---

### Task 3: Prefix the 25 parent-meaning citations in the child specifications

In a specification a bare `§N` means *that document's* §N (docs spec §3.2). Both child
specifications break this: they use the bare form for the parent's sections, and because
each child has its own section of the same number, the reference resolves silently to the
wrong document. The `add_logo` banner's "extends §3.2 `plotting`" lands on the logo
specification's own §3.2, *Bundled assets and packaging*.

**Files:**
- Modify: `docs/src/developer/specs/2026-08-01-add-logo-design.md` — 5 lines, 9 references
- Modify: `docs/src/developer/specs/2026-08-03-published-specs-design.md` — 11 lines,
  16 references

**Interfaces:**
- Consumes: `.github/scripts/check_citations.py` from Task 1.
- Produces: no new symbols.

The line numbers below are the file's numbers *before* any edit in this task. Match on the
**From** text rather than seeking to a line number, or work bottom-up — rewrapping an early
paragraph shifts everything beneath it.

**The checker cannot verify most of this task.** Only 11 of these 25 references fail to
resolve; the other 14 land on a section of the same number in the child document and look
correct to any syntactic check (docs spec §3.6). So `exit=0` at Step 3 confirms the eleven
dangling ones are gone — it does not confirm the other 14 were found. Work from the tables
below, which are the enumeration, and treat the checker as the backstop rather than the
oracle. Every line listed here was classified by reading the surrounding sentence.

- [ ] **Step 1: Edit the `add_logo` specification**

| Line | From | To |
|---|---|---|
| 12 | `§3.2 \`plotting\` with a branding artist and inherits its error-handling (§6), testing (§7)` | `spec §3.2 \`plotting\` with a branding artist and inherits its error-handling (spec §6), testing (spec §7)` |
| 13 | `and engineering-standards (§8) rules unchanged` | `and engineering-standards (spec §8) rules unchanged` |
| 94 | `are numeric conventions, and the parent spec's §3.5 rule is that nothing numeric is` | `are numeric conventions, and the parent spec §3.5 rule is that nothing numeric is` |
| 372 | `(2026-07-22-tephpy-design.md), §3.2` | `(2026-07-22-tephpy-design.md), spec §3.2` |
| 373 | `(\`plotting\`), §6 (error handling), §7 (testing), §8 (engineering standards)` | `(\`plotting\`), spec §6 (error handling), spec §7 (testing), spec §8 (engineering standards)` |

Line 12 exceeds 95 columns once `spec ` is inserted three times; rewrap lines 12–13 to the
file's prose width. Line 373 likewise — rewrap 372–373. Markdown prose has no hard limit,
but the surrounding text wraps at about 95, and `sphinx-lint` is indifferent either way.

Leave every other bare reference in this file alone. Lines 49, 54, 104, 106, 238, 268, 296,
309, 332, 351 and 355 are genuine self-references: §3.3 *Sizing*, §8 *Scope*, §3.4
*Placement*, §6 *Testing*, §3.1 *Public API*, §5 *Error handling*, §3 *Architecture* and
§3.5 *Theme resolution* all exist in this document and are what the prose means.

- [ ] **Step 2: Edit the published-specifications specification**

| Line | From | To |
|---|---|---|
| 39 | `for users. Specification content — §7 testing, §8 engineering standards, §10 roadmap —` | `for users. Specification content — spec §7 testing, spec §8 engineering standards, spec §10 roadmap —` |
| 137 | `addresses §3.2 directly.` | `addresses spec §3.2 directly.` |
| 143 | `resolved. Second, prose-derived slugs collide silently: §7 *Testing* and §8.5 *Testing*` | `resolved. Second, prose-derived slugs collide silently: spec §7 *Testing* and spec §8.5 *Testing*` |
| 176 | `trail continues. Every item in a specification's open-item sections — the parent's §10` | `trail continues. Every item in a specification's open-item sections — the parent's spec §10` |
| 177 | `*Assumptions and open decisions* and §11 *Open questions* — therefore carries a leading` | `*Assumptions and open decisions* and spec §11 *Open questions* — therefore carries a leading` |
| 206 | `The parent specification is not the only document this governs. A specification with no §10` | `The parent specification is not the only document this governs. A specification with no spec §10` |
| 207 | `or §11 — the \`add_logo\` specification, or this one — records its unsettled items in its` | `or spec §11 — the \`add_logo\` specification, or this one — records its unsettled items in its` |
| 262 | `developer guide to *Design specifications*, and lands on §3.2 of the parent document by` | `developer guide to *Design specifications*, and lands on spec §3.2 of the parent document by` |
| 270 | `§10 or §11 in the parent, §Scope elsewhere — with a status tag, filed as an issue labelled` | `spec §10 or spec §11 in the parent, §Scope elsewhere — with a status tag, filed as an issue labelled` |
| 294 | `6. Correct the stale repository paths (§3.4): §10 of the parent specification names` | `6. Correct the stale repository paths (§3.4): spec §10 of the parent specification names` |
| 303 | `7. Audit §10's sixteen items and §11's four questions, establish the true status of each,` | `7. Audit spec §10's sixteen items and spec §11's four questions, establish the true status of each,` |

Two cautions. On line 294 the first reference, `(§3.4)`, is a genuine self-reference to this
document's §3.4 and must stay bare; only `§10` changes. And `§Scope` on line 270 is not a
numbered citation — the checker never matches it, because the pattern requires digits.

Rewrap each edited paragraph to the file's ~95-column prose width afterwards.

Leave the remaining bare references alone: lines 47, 48, 149, 217, 234, 241, 247, 254, 302,
304, 315, 317, 330, 333, 336 and 340 all point at this document's own sections.

- [ ] **Step 3: Verify the corpus is clean**

```bash
pixi run --frozen python .github/scripts/check_citations.py; echo "exit=$?"
```

Expected: `exit=0` and `citations ok: 54 anchors, 50 files (docs spec §3.6)`. This is the
first moment all three assertions hold.

- [ ] **Step 4: Confirm the rendered specifications still build**

```bash
pixi run --frozen docs
```

Expected: `build succeeded` with no warnings — the build runs `--fail-on-warning`, and
`pixi run docs` depends on `docs-clean`, so it is clean by construction.

- [ ] **Step 5: Commit**

```bash
pixi run --frozen bash -c 'git add docs/src/developer/specs && git commit -m "Name the parent specification in the child specs cross-references"'
```

---

### Task 4: Wire the gate

**Files:**
- Modify: `.pre-commit-config.yaml`
- Modify: `tests/test_citations.py`
- Modify: `.github/scripts/README.md`
- Modify: `docs/src/developer/specs/2026-08-03-published-specs-design.md` (§7)
- Create: `changelog/<PR>.internal.rst`

**Interfaces:**
- Consumes: `main()` and the module-level `_load()` helper from Task 1.
- Produces: no new symbols.

- [ ] **Step 1: Add the repo-invariant test**

Append to `tests/test_citations.py`. Hooks are not installed in a fresh clone or worktree,
so CI needs its own copy of the ratchet (docs spec §3.6).

```python
def test_the_repository_satisfies_the_citation_contract(capsys):
    """The live tree passes all three assertions (docs spec §3.6).

    The pre-commit hook is the primary gate, but hooks are not installed in a fresh
    clone, so this is what catches a citation broken by someone who bypassed them.
    """
    assert cc.main() == 0, capsys.readouterr().out
```

- [ ] **Step 2: Run it**

```bash
pixi run --frozen tests tests/test_citations.py -v
```

Expected: 12 passed. If it fails, the assertion message carries the checker's own output.

- [ ] **Step 3: Register the hook**

Add to `.pre-commit-config.yaml`, as the last block. This is the repository's first
`repo: local` hook.

```yaml
  - repo: local
    hooks:
      # Citations name a section by number, so renumbering strands them silently
      # (docs spec §3.6). Editing a spec heading breaks citations in files the
      # commit never touches, so this runs over the whole tree, not the staged
      # files.
      - id: check-citations
        name: design specification citations resolve
        entry: .github/scripts/check_citations.py
        language: python
        always_run: true
        pass_filenames: false
```

- [ ] **Step 4: Verify the hook runs and passes**

```bash
pixi run --frozen lint
```

Expected: every hook passes, including `design specification citations resolve`.

- [ ] **Step 5: Verify the hook actually fails on a broken citation**

A gate that cannot fail is not a gate. Break one deliberately, confirm the failure, restore
it.

```bash
sed -i 's/^(spec-3-2)=$/(spec-3-9)=/' docs/src/developer/specs/2026-07-22-tephpy-design.md
pixi run --frozen bash -c 'pre-commit run check-citations --all-files'; echo "exit=$?"
git checkout docs/src/developer/specs/2026-07-22-tephpy-design.md
```

Expected: `exit=1`, reporting both an *Anchor problems* entry (`spec-3-9` sits above the
heading numbered 3.2) and a long list of *Unresolved citations* for every `spec §3.2` in the
tree. Confirm the working tree is clean again with `git status`.

- [ ] **Step 6: Widen the scripts README**

`.github/scripts/README.md` currently reads "This directory contains utility scripts used by
GHAs defined within the `.github/workflows`." Replace that sentence with:

```markdown
This directory contains utility scripts used by the repository's automation — the GHAs
defined within `.github/workflows`, and the `pre-commit` hooks defined within
`.pre-commit-config.yaml`.
```

- [ ] **Step 7: Flip the specification's own status**

In `docs/src/developer/specs/2026-08-03-published-specs-design.md` §7, replace the
**Deferred** entry for #86 with a **Resolved** one. Per docs spec §3.5 a **Resolved** item
carries the date the decision was taken and the pull request that settled it. Substitute the
real PR number:

```markdown
- **Resolved** (2026-08-04, PR #NN) — **the citation-integrity hook of §3.6 is in place.**
  The 36 citations that did not meet the §3.2 rule were corrected with it: eleven in `src/`
  and `tests/` that carried a bare `§N` in a file owning no sections, and 25 in the two
  child specifications where a bare `§N` meant the *parent's* section and resolved silently
  to the child's own.
```

- [ ] **Step 8: Add the changelog fragment**

`changelog/<PR>.internal.rst`, where `<PR>` is the pull-request number. It must end with
``(:user:`<github-username>`)`` attribution, and cite #86 with the `:issue:` role.

```rst
Added a ``pre-commit`` hook that fails the commit when a design-specification
citation stops resolving (:issue:`86`). Citations name a section by number, so
renumbering one stranded every reference to it silently — a stale citation is
still a well-formed sentence. The hook also found 36 citations that did not meet
the rule, including the ``add_logo`` specification's own banner, which cited the
parent's ``plotting`` section but resolved to its own §3.2. (:user:`claude`)
```

- [ ] **Step 9: Full gate**

```bash
pixi run --frozen lint
pixi run --frozen tests
pixi run --frozen docs
```

Expected: all three clean.

- [ ] **Step 10: Commit**

```bash
pixi run --frozen bash -c 'git add .pre-commit-config.yaml tests/test_citations.py .github/scripts/README.md docs/src/developer/specs changelog && git commit -m "Wire the citation-integrity hook into pre-commit"'
```

---

## Verification

The change is done when all of the following hold:

- `pixi run --frozen python .github/scripts/check_citations.py` exits 0 and reports
  `54 anchors, 50 files`.
- `pixi run --frozen lint` passes with `design specification citations resolve` among the
  hooks.
- `pixi run --frozen tests` passes, including
  `test_the_repository_satisfies_the_citation_contract`.
- `pixi run --frozen docs` builds clean under `--fail-on-warning`.
- Renaming any anchor makes the hook exit 1 (Task 4, Step 5).
- docs spec §7 records #86 as **Resolved** with the PR number.
- The pull request carries a `changelog/<PR>.internal.rst` fragment.

## Out of scope

- **Converting citations into Sphinx cross-references** — tracked as
  [#85](https://github.com/bjlittle/tephpy/issues/85), and deliberately after this. Once
  citations become `:ref:` roles, the checker's pattern must learn that form; doing it in
  the other order would mean writing the pattern twice.
- **Checking the plans.** They are point-in-time records (docs spec §3.4).
- **Reconciling `design: open` issues against the specifications.** The bidirectional check
  described in docs spec §3.5 needs network access, which a pre-commit hook must not.
- **Asserting the citation counts in docs spec §3.2.** The table is accurate today, but
  locking it would fail the commit of anyone adding a single citation until they also edited
  a specification table — friction out of proportion to the drift it prevents.
- **Catching a citation that resolves but names the wrong section.** Out of reach by
  construction, and stated as such in docs spec §3.6.
