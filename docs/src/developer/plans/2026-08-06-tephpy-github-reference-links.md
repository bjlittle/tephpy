# GitHub Reference Links Implementation Plan

> **Point-in-time record.** This plan captures what was intended before implementation. It
> is not updated afterwards — where the implementation departed from it, the departure is
> recorded in the pull request, and the living design specification in
> [`../specs/`](../specs/) is what describes tephpy as it stands.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every reference to a tephpy issue or pull request a link the reader can
follow, and keep it that way — 40 of them currently reach a reader of the published
specifications as plain text, and 19 more restate a URL the configuration already holds.

**Architecture:** Three changes, in dependency order. A new pre-commit gate,
`.github/scripts/check_github_references.py`, asserts both halves of the docs spec §3.8
rule over the corpus `check_citations.py` already derives — it loads that script by path
for the corpus, the `Violation` type and the path renderer, rather than restating any of
them. The 59 references are then rewritten as `{issue}`/`{pull}` roles, which is what lets
the gate be wired into `.pre-commit-config.yaml` in the same commit that makes the tree
pass it. Finally `extlinks_detect_hardcoded_links` is enabled, giving Sphinx's own matcher
as an independent second check on the hardcoded half.

**Tech Stack:** Python 3.12 stdlib only (`re`, `pathlib`, `importlib.util`) — no new
dependency; pytest; pre-commit; Sphinx `sphinx.ext.extlinks`; MyST; pixi.

**Spec:** `docs spec §3.8`, in
[`../specs/2026-08-03-published-specs-design.md`](../specs/2026-08-03-published-specs-design.md).
Decision 7 of `docs spec §2` states the rule; `docs spec §6` states what verifies it.

**Issue:** None. The defect was reported directly by the maintainer, who noticed the
unlinked references once the specifications began building on Read the Docs.

## Global Constraints

- **Every pixi invocation carries `--frozen`.** `pixi run --frozen tests`,
  `pixi run --frozen lint`, `pixi run --frozen docs`. Never let pixi re-solve the
  environment.
- **Every new source file carries the BSD copyright header** — ruff `CPY001` enforces it.
  Copy it verbatim from `.github/scripts/check_citations.py:2-5`.
- **Line length is 88 columns**, ruff-enforced.
- **Docstrings are numpydoc**, validated by the `numpydoc-validation` pre-commit hook.
  Every public function needs `Parameters`, `Returns`/`Yields`, and `Raises` where it
  raises. A module docstring ends with a `Notes` section carrying
  `.. versionadded:: 0.1.0`.
- **Tests mirror the source layout.** This gate is repository-wide, not part of the
  `tephpy` package, so its tests go at `tests/test_github_references.py` — alongside
  `tests/test_citations.py` and `tests/test_documentation_links.py`, not in a subdirectory.
- **The specifications are living documents; the plans are frozen** (docs spec §3.4).
  Nothing under `docs/src/developer/plans/` is edited by this work, including this file
  once its pull request merges.
- **Never write a bare `#N` or a `github.com/bjlittle/tephpy` issue URL in prose** while
  implementing this — including in commit messages' bodies, this plan, and the gate's own
  docstring. The gate reads its own source. Where an example of the forbidden form is
  needed, put it in an inline code span, which is exempt.

---

### Task 1: The gate script and its unit tests

**Files:**
- Create: `.github/scripts/check_github_references.py`
- Create: `tests/test_github_references.py`

**Interfaces:**
- Consumes: `.github/scripts/check_citations.py` — `corpus() -> list[Path]`,
  `display(Path) -> str`, `Violation(path, line, message)`, and its already-loaded
  `citations` module attribute, whose `source_lines(path, text) -> Iterator[tuple[int, str]]`
  skips Markdown fences and reads notebooks.
- Produces: `check_unlinked(paths) -> list[Violation]`,
  `check_hardcoded(paths) -> list[Violation]`, `corpus`, `main() -> int`. Task 2's
  repository-contract test calls `main()`.

**Why the corpus is borrowed rather than restated.** `check_citations.corpus()` derives the
file list from `git ls-files`, drops anything that is not UTF-8, and excludes the plans. Its
docstring records that a glob once left `tests/fixtures/io/README.md` outside the check
while it carried two citations. A second copy of that reasoning is a second thing to drift.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_github_references.py`. Model it on `tests/test_citations.py` — the same
copyright header, the same `importlib` load-by-path, and the same skip marker, because
`MANIFEST.in` prunes `.github` and an unpacked sdist ships these tests without the script
they exercise.

Note the `HASH` constant and use it in every fixture. This test file sits inside the corpus
the gate reads, and a literal `#65` written in a multi-line string would be a real
violation of the very rule under test — `tests/test_citations.py` builds its section sign
the same way and for the same reason.

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the GitHub-reference checker (docs spec §3.8)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_github_references.py"

# `MANIFEST.in` prunes `.github`, so an sdist ships these tests without the checker
# they exercise, and a source archive carries no index for the corpus to be
# enumerated from. The gate is a contract about the repository, and neither of those
# is the repository, so skip there rather than fail collection.
pytestmark = pytest.mark.skipif(
    not (SCRIPT.is_file() and (REPO / ".git").exists()),
    reason="not a git checkout of the repository",
)

# This file sits inside the corpus the gate reads (docs spec §3.8), so the number
# sign is built rather than written in the fixtures below: a literal one followed by
# digits is exactly what the gate exists to reject, and it would be right to reject
# it here. The docstrings refer to the forms in code spans, and stay literal.
HASH = "\N{NUMBER SIGN}"
BASE = "https://github.com/bjlittle/tephpy"


def _load():
    """Import the checker by path; ``.github`` is not an importable package."""
    spec = importlib.util.spec_from_file_location("check_github_references", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gr = _load() if SCRIPT.is_file() else None


def test_a_bare_reference_is_reported(tmp_path):
    """The plain form reaches a reader as text (docs spec §3.8)."""
    source = tmp_path / "spec.md"
    source.write_text(f"Settled in PR {HASH}40 last week.\n")
    violations = gr.check_unlinked([source])
    assert len(violations) == 1
    assert violations[0].line == 1
    assert "40" in violations[0].message


def test_a_role_is_not_a_bare_reference(tmp_path):
    """``{pull}`40``` is the form the rule asks for, and passes."""
    source = tmp_path / "spec.md"
    source.write_text("Settled in PR {pull}`40` last week.\n")
    assert gr.check_unlinked([source]) == []
    assert gr.check_hardcoded([source]) == []


def test_a_hardcoded_url_is_reported(tmp_path):
    """The URL is stated once, in the extlinks configuration (docs spec §3.8)."""
    source = tmp_path / "spec.md"
    source.write_text(f"See [{HASH}65]({BASE}/issues/65) for the rest.\n")
    unlinked = gr.check_unlinked([source])
    hardcoded = gr.check_hardcoded([source])
    assert unlinked == [], "the number is link text, so only the URL is at fault"
    assert len(hardcoded) == 1
    assert "issue" in hardcoded[0].message


def test_the_suggested_role_follows_the_url_path(tmp_path):
    """A pull-request URL is told to use ``pull``, not ``issue``."""
    source = tmp_path / "spec.md"
    source.write_text(f"See [{HASH}73]({BASE}/pull/73).\n")
    violations = gr.check_hardcoded([source])
    assert len(violations) == 1
    assert "pull" in violations[0].message
    assert "issue" not in violations[0].message


def test_another_project_s_issue_is_left_alone(tmp_path):
    """The roles are scoped to this repository (docs spec §3.8)."""
    source = tmp_path / "spec.md"
    other = "https://github.com/Unidata/MetPy/issues/1234"
    source.write_text(f"See [Unidata/MetPy{HASH}1234]({other}).\n")
    assert gr.check_unlinked([source]) == []
    assert gr.check_hardcoded([source]) == []


def test_a_fenced_block_is_skipped(tmp_path):
    """A passage documenting the rule quotes the form it forbids (docs spec §3.6)."""
    fence = "`" * 3
    source = tmp_path / "spec.md"
    source.write_text(f"{fence}\ngh pr create --body 'Closes {HASH}65'\n{fence}\nok\n")
    assert gr.check_unlinked([source]) == []


def test_an_inline_code_span_is_skipped(tmp_path):
    """The specification quotes the bare form as an example of one."""
    source = tmp_path / "spec.md"
    source.write_text(f"Two forms are errors: a bare `{HASH}65`, and a URL.\n")
    assert gr.check_unlinked([source]) == []


def test_a_double_backtick_literal_is_skipped(tmp_path):
    """reStructuredText writes its inline literal with two backticks, not one."""
    source = tmp_path / "guide.rst"
    source.write_text(f"Keep a colour in literal markup -- ``{HASH}808080``.\n")
    assert gr.check_unlinked([source]) == []


def test_a_quoted_colour_is_skipped(tmp_path):
    """``set_facecolor("#101820")`` is a colour, not issue 101820."""
    source = tmp_path / "mod.py"
    source.write_text(f'axes.set_facecolor("{HASH}101820")\n')
    assert gr.check_unlinked([source]) == []


def test_a_hardcoded_url_in_a_code_span_is_skipped(tmp_path):
    """docs spec §3.8 quotes a forbidden URL as an example of one."""
    source = tmp_path / "spec.md"
    source.write_text(f"and a hand-written `{BASE}/issues/65`.\n")
    assert gr.check_hardcoded([source]) == []


def test_a_restructuredtext_hyperlink_keeps_its_url_judged(tmp_path):
    """Backticks with a trailing underscore are a link, not a literal.

    Its text is linked, so the first assertion passes it; its URL is hardcoded, so
    the second must still see it. Blanking every backtick span for both assertions
    would let this one form state a URL that nothing objects to.
    """
    source = tmp_path / "guide.rst"
    source.write_text(f"See `{HASH}65 <{BASE}/issues/65>`_ for the rest.\n")
    assert gr.check_unlinked([source]) == []
    assert len(gr.check_hardcoded([source])) == 1


def test_a_hex_colour_with_a_letter_is_not_a_reference(tmp_path):
    """``#7af461`` never matched, and the test pins that it cannot start to."""
    source = tmp_path / "spec.md"
    source.write_text(f"The label colour is {HASH}7af461 in the workflow.\n")
    assert gr.check_unlinked([source]) == []


def test_a_near_miss_is_reported_rather_than_skipped(tmp_path):
    """The detector is wider than the validator (docs spec §3.8)."""
    source = tmp_path / "spec.md"
    source.write_text(f"Landed in {HASH}101 after review.\n")
    assert len(gr.check_unlinked([source])) == 1


def test_the_corpus_excludes_the_plans_and_covers_the_specifications():
    """The plans are frozen with their references (docs spec §3.4)."""
    paths = set(gr.corpus())
    specs = REPO / "docs" / "src" / "developer" / "specs"
    assert specs / "2026-07-22-tephpy-design.md" in paths
    assert specs / "2026-08-03-published-specs-design.md" in paths
    assert REPO / "tests" / "plotting" / "test_shading.py" in paths
    frozen = "the plans are point-in-time records (docs spec §3.4)"
    assert not any("plans" in path.parts for path in paths), frozen
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_github_references.py -v`

Expected: collection fails — `check_github_references.py` does not exist, so `SCRIPT.is_file()`
is false, `gr` is `None`, and `pytestmark` skips every test. **A skip is not a failure.**
Confirm the tests are genuinely skipped and not silently passing, then treat step 4 as the
step that proves they run.

- [ ] **Step 3: Write the gate**

Create `.github/scripts/check_github_references.py`, executable (`chmod +x`), with the
copyright header from the Global Constraints.

```python
#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that every GitHub reference is written as a link (docs spec §3.8).

A reference to an issue or pull request is written with the ``issue`` or ``pull``
extlink role, so that the URL is stated once in ``docs/src/conf.py`` and the caption
is generated from the same value that builds the link. Two forms are therefore
errors, and this gate asserts both over the corpus ``check_citations.py`` derives:

1. **Unlinked.** A bare reference that no role produced, which reaches a reader of
   the published page as plain text.
2. **Hardcoded.** A hand-written ``github.com/bjlittle/tephpy`` issue or
   pull-request URL, which restates what the configuration already holds.

The two partition the failures rather than overlapping. A number that is already the
display text of a link is left to the second assertion, which reports it once if the
link is this repository's and not at all if it is another project's -- the roles are
scoped here, so an issue elsewhere stays an ordinary link with its own URL.

Detection is wider than validation, deliberately. The patterns look for any ``#``
followed by digits, and any URL under this repository's ``issues/`` or ``pull/``
path, rather than for the exact forms the rule forbids. One pattern doing both jobs
could not report a near-miss: a form it failed to match would be neither judged nor
mentioned, so a ``# 65`` written with a space, or a ``pulls/65`` typo, would read as
compliance rather than as something to look at.

Three things are not references, and each is blanked before a line is judged --
blanked rather than dropped, so that the report still names the column the reader
will find the offender in. Fenced code blocks, skipped by the shared reader for the
reason docs spec §3.6 gives: the specification passage stating this rule quotes the
bare form it forbids. Inline code spans and quoted string literals, which is where a
hexadecimal colour is written -- ``#808080`` in the add_logo specification, and the
one in the logo tests whose six digits would otherwise read as an issue number. And
link text, so that a number already carrying a link is not reported as carrying none.

One exemption differs between the two assertions, and it is reStructuredText's
hyperlink. It is delimited by backticks like an inline literal, and only the trailing
underscore tells them apart. The first assertion blanks it, because the number in it
is link text; the second does not, because the URL in it is real and hardcoded. A
literal with no underscore is blanked by both, which is what lets the specification
and the style guide quote a forbidden URL as an example of one.

**What this cannot catch.** A reference written with the wrong role of the two, where
the number is a pull request and the ``issue`` role names it, is well formed, renders
identically, and resolves -- GitHub redirects between the two paths, so the reader
still arrives where they should, and only the source misnames the kind. Settling it
would mean asking GitHub which each number is, and a hook that needs the network
fails offline and is rate-limited in CI. Review is what narrows that one.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    import types

REPO = Path(__file__).resolve().parents[2]
CITATIONS = REPO / ".github" / "scripts" / "check_citations.py"


def _citations() -> types.ModuleType:
    """Load the citation gate, for the corpus and the reporting it already derives.

    The corpus is a derived list -- every tracked text file, less the plans (docs
    spec §3.6) -- and its docstring records that a glob once left a citation-bearing
    README outside the check. Restating that reasoning here would give it a second
    place to drift from.

    Returns
    -------
    module
        The loaded ``check_citations`` module.

    Raises
    ------
    SystemExit
        When the citation gate is not where this script expects it.

    """
    if not CITATIONS.is_file():
        print(f"cannot load the citation gate from {CITATIONS}")
        raise SystemExit(1)
    spec = importlib.util.spec_from_file_location("check_citations", CITATIONS)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _citations()

corpus = gate.corpus
display = gate.display
Violation = gate.Violation
source_lines = gate.citations.source_lines

#: A run of backticks and everything up to its matching rail. The rail is remembered
#: rather than counted, for the reason the fence reader gives: a span opened with two
#: backticks may quote a single one, and reStructuredText writes its inline literal
#: with two where Markdown writes one.
SPAN = r"(?P<{name}>`+)(?:(?!(?P={name})).)*(?P={name})"
#: What the unlinked assertion does not judge: an inline literal or a
#: reStructuredText hyperlink, a quoted string literal, and Markdown link text --
#: recognised by the parenthesis that follows it, which is what separates a link from
#: a reference-style bracket.
UNLINKED_EXEMPT = re.compile(
    SPAN.format(name="literal") + r"|\"[^\"]*\"|'[^']*'|\[[^\]\n]*\](?=\()"
)
#: What the hardcoded assertion does not judge: an inline literal, and not a
#: reStructuredText hyperlink -- the trailing underscore says its URL is real.
HARDCODED_EXEMPT = re.compile(SPAN.format(name="literal") + r"(?!__?)")
#: Any ``#`` immediately followed by digits, wherever it is written. The preceding
#: character is excluded from the word characters and from ``/``, ``&`` and ``#`` so
#: that a URL fragment, an HTML entity and a Markdown heading are not read as one.
BARE = re.compile(r"(?<![\w&/#-])#(?P<number>\d+)\b")
#: Any URL under this repository's issue or pull-request path.
URL = re.compile(
    r"https://github\.com/bjlittle/tephpy/(?P<kind>issues|pull)/(?P<number>\d+)"
)
#: The role each URL path is written with instead.
ROLE = {"issues": "issue", "pull": "pull"}


def blank(match: re.Match[str]) -> str:
    """Replace a matched span with spaces, so the rest of the line keeps its columns.

    Parameters
    ----------
    match : re.Match
        The span to remove.

    Returns
    -------
    str
        As many spaces as the span had characters.

    """
    return " " * len(match.group(0))


def advice(number: str, role: str) -> str:
    """Render the role to write, in both syntaxes.

    Parameters
    ----------
    number : str
        The issue or pull-request number.
    role : str
        The extlink role name, ``issue`` or ``pull``.

    Returns
    -------
    str
        The MyST and reStructuredText forms, as a single phrase.

    """
    return f"write {{{role}}}`{number}` in Markdown, :{role}:`{number}` elsewhere"


def check_unlinked(paths: Iterable[Path]) -> list[Violation]:
    """Assert that no GitHub reference is written as plain text.

    Parameters
    ----------
    paths : iterable of Path
        The files to scan.

    Returns
    -------
    list of Violation
        One entry per reference that links to nothing.

    """
    violations: list[Violation] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for number, line in source_lines(path, text):
            for match in BARE.finditer(UNLINKED_EXEMPT.sub(blank, line)):
                found = match["number"]
                violations.append(
                    Violation(
                        path,
                        number,
                        f"reference to {found} links to nothing; "
                        f"{advice(found, 'issue')} -- or the pull role, "
                        f"if {found} is a pull request",
                    )
                )
    return violations


def check_hardcoded(paths: Iterable[Path]) -> list[Violation]:
    """Assert that no GitHub reference is written as a URL.

    Parameters
    ----------
    paths : iterable of Path
        The files to scan.

    Returns
    -------
    list of Violation
        One entry per hand-written issue or pull-request URL.

    """
    violations: list[Violation] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for number, line in source_lines(path, text):
            for match in URL.finditer(HARDCODED_EXEMPT.sub(blank, line)):
                role = ROLE[match["kind"]]
                violations.append(
                    Violation(
                        path,
                        number,
                        f"hardcoded link to {match['number']}; "
                        f"{advice(match['number'], role)}",
                    )
                )
    return violations


def main() -> int:
    """Run both assertions over the corpus.

    Returns
    -------
    int
        ``0`` when both hold, ``1`` otherwise.

    """
    paths = corpus()
    if not paths:
        print(
            "the corpus is empty, so nothing was checked; a gate that passes on "
            "an empty search is a green tick over nothing (docs spec §3.8)"
        )
        return 1
    groups = {
        "Unlinked references": check_unlinked(paths),
        "Hardcoded links": check_hardcoded(paths),
    }
    total = sum(len(found) for found in groups.values())
    if total == 0:
        print(f"github references ok: {len(paths)} files (docs spec §3.8)")
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

Run: `pixi run --frozen pytest tests/test_github_references.py -v`

Expected: 14 passed, 0 skipped. **If any test is skipped, stop** — `SCRIPT.is_file()` is
false, meaning the script is not at the path the test names.

- [ ] **Step 5: Run the gate over the tree and confirm what it finds**

Run: `.github/scripts/check_github_references.py`

Expected: exit 1, with `Unlinked references (40):` and `Hardcoded links (19):`. The counts
are the point of this step — they are what `docs spec §6` records, and a different number
means either the gate or the count is wrong. Investigate before continuing.

The 40 unlinked are distributed: 31 in `2026-07-22-tephpy-design.md`, 3 in
`2026-08-01-add-logo-design.md`, 5 in `2026-08-03-published-specs-design.md`, and 1 in
`tests/plotting/test_shading.py`. The 19 hardcoded are 11, 2 and 6 across the three
specifications.

- [ ] **Step 6: Verify the gate refuses an empty corpus**

A gate that passes on nothing is worse than no gate. Prove this one does not:

Run: `pixi run --frozen python -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('g', '.github/scripts/check_github_references.py')
g = importlib.util.module_from_spec(spec); sys.modules['g'] = g; spec.loader.exec_module(g)
g.corpus = lambda: []
print('exit', g.main())
"`

Expected: the empty-corpus message, and `exit 1`.

- [ ] **Step 7: Lint and commit**

```bash
git add .github/scripts/check_github_references.py tests/test_github_references.py
pixi run --frozen lint
git commit -m "Add a gate for unlinked GitHub references"
```

The gate is **not** wired into `.pre-commit-config.yaml` yet — the tree does not pass it,
and wiring it here would block this commit. Task 2 wires it.

---

### Task 2: Convert the 59 references and wire the hook

**Files:**
- Modify: `docs/src/developer/specs/2026-07-22-tephpy-design.md` (42 references)
- Modify: `docs/src/developer/specs/2026-08-01-add-logo-design.md` (5)
- Modify: `docs/src/developer/specs/2026-08-03-published-specs-design.md` (11)
- Modify: `tests/plotting/test_shading.py:206` (1)
- Modify: `.pre-commit-config.yaml`
- Modify: `tests/test_github_references.py` (add the repository-contract test)

**Interfaces:**
- Consumes: `main()` from Task 1.
- Produces: a tree the gate passes, and a hook that keeps it that way.

**The kind of every number referenced.** Resolved against the GitHub API; the `issue` and
`pull` paths redirect to each other, so a wrong choice still reaches the reader and nothing
in the build objects. Get them right from this table rather than from the surrounding prose:

| role | numbers |
|---|---|
| `pull` | 1, 4, 5, 9, 15, 19, 26, 40, 41, 43, 69, 71, 73, 89, 90 |
| `issue` | 42, 65, 72, 76, 77, 78, 79, 80, 81, 82, 85, 86 |

Those 27 numbers are the complete set appearing in the corpus. A number outside the table
means the corpus has changed since this plan was written — resolve it with
`gh api repos/bjlittle/tephpy/issues/<n> --jq 'if .pull_request then "pull" else "issue" end'`
before writing the role.

**The two rewrites.** Both are mechanical, and the surrounding prose is left exactly as it
stands — including the word `PR` or `issue` where it already appears, which is what tells a
reader which kind of page the link opens (docs spec §3.8).

| before | after |
|---|---|
| `PR #19` | ``PR {pull}`19` `` |
| `issue #42` | ``issue {issue}`42` `` |
| `#73` | ``{pull}`73` `` |
| `[#65](https://github.com/bjlittle/tephpy/issues/65)` | ``{issue}`65` `` |
| `[#79](https://github.com/bjlittle/tephpy/issues/79)` | ``{issue}`79` `` |

Worked examples covering every shape in the corpus, so that none has to be invented:

```markdown
- **Issue:** {issue}`65`

| 1 | Foundation & scaffolding | … | — | ✅ complete ({pull}`1`; SPEC 0 / platform updates {pull}`4`, {pull}`5`) |

1. **Resolved** (2026-07-28, PR {pull}`19`, {pull}`26`, {pull}`40`) — **The Plan 4–6 slicing …**

15. **Deferred** (Plan 7 — {issue}`76`) — **Residual Plan 1 deferrals**, re-homed: …

- **Deferred** (v1.x — {issue}`79`) — Which aviation-specific overlays …

- {issue}`65` — publish the design specifications
```

And the one outside the specifications, in a reStructuredText docstring:

```python
    the strictly-decreasing grid (PR :pull:`43` review).
```

- [ ] **Step 1: Rewrite `2026-07-22-tephpy-design.md`**

42 references on these lines. Work down the list; `git diff` after each block.

- Prose: 375 (`issue #42`).
- The plan table: 986 (`#1`, `#4`, `#5`), 987 (`#9`), 988 (`#15`), 989 (`#19`), 990 (`#26`),
  991 (`#40`, `#41`).
- The open-item ledger: 1031 (`#19`, `#26`, `#40`), 1036, 1041, 1045, 1049, 1054, 1065,
  1071, 1080, 1087, 1091, 1107, 1123, 1129 (`#26`, `#40`), 1146, 1167, 1168, 1170.
- Already-linked, converted from URL to role: 1128, 1154, 1164, 1165, 1166, 1169, 1186,
  1191, 1196, 1200, 1202.

**Watch the table rows.** Lines 986–991 are Markdown table cells. A role works in a cell,
but a `|` inside one would end it — none of these carry one, and none should be introduced.

- [ ] **Step 2: Rewrite `2026-08-01-add-logo-design.md`**

5 references: 9 (`#71`), 17 (`#69`), 54 (URL, `#72`), 353 (URL, `#72`), 383 (`#69`).

**Do not touch line 220.** It reads `` `#808080` `` — a colour in a code span, exempt by
docs spec §3.8 and correct as it stands.

- [ ] **Step 3: Rewrite `2026-08-03-published-specs-design.md`**

11 references: 10 (URL), 30 (URL), 37, 84, 168, 563, 568, and the four in §8 References
(577–580, all URLs).

**Do not touch §3.8 or the §6 verification bullet** — they already comply. §3.8 contains
four role occurrences and only the one on line 410 is live; the three on lines 416, 424 and
470 sit inside code spans, where they are examples of the form rather than uses of it.

- [ ] **Step 4: Rewrite `tests/plotting/test_shading.py:206`**

The docstring reads `the strictly-decreasing grid (PR #43 review).` Make it
`the strictly-decreasing grid (PR :pull:`43` review).` — reStructuredText, because it is a
Python docstring. Nothing renders this file today (autoapi reads `src/tephpy` only), and it
is converted anyway: the rule is corpus-wide, exactly as the `spec §N` citations in `tests/`
are, and a rule with a carve-out for "wherever it happens not to render" is one nobody can
apply without checking the build configuration first.

- [ ] **Step 5: Run the gate and confirm it is clean**

Run: `.github/scripts/check_github_references.py`

Expected: `github references ok: 172 files (docs spec §3.8)`, exit 0. If any violation
remains, it is named with its file and line — fix and re-run.

- [ ] **Step 6: Add the repository-contract test**

Append to `tests/test_github_references.py`. This is the test that catches a reference
broken by someone who bypassed the hook, which is why it exists alongside the hook rather
than instead of it.

```python
def test_the_repository_satisfies_the_reference_contract(capsys):
    """The live tree passes both assertions (docs spec §3.8).

    The pre-commit hook is the primary gate, but hooks are not installed in a fresh
    clone, so this is what catches a reference broken by someone who bypassed them.
    """
    assert gr.main() == 0, capsys.readouterr().out
```

- [ ] **Step 7: Run the full test suite**

Run: `pixi run --frozen pytest tests/test_github_references.py tests/test_citations.py -v`

Expected: 15 passed in the new file, and `test_citations.py` unchanged and green — the
conversions touched files that gate reads, and a role written across a line break could
strand a `spec §N` citation that shared the line.

- [ ] **Step 8: Wire the pre-commit hook**

Add to `.pre-commit-config.yaml`, immediately after the `check-citations` hook, keeping its
comment style — the comment says why the hook runs over the whole tree rather than the
staged files:

```yaml
      # A reference written as plain text or as a URL is a link the reader cannot
      # follow, or a URL that has left the configuration behind (docs spec §3.8).
      # Editing conf.py's extlinks changes what every file should say, so this runs
      # over the whole tree, not the staged files.
      - id: check-github-references
        name: GitHub references are links
        entry: .github/scripts/check_github_references.py
        language: python
        always_run: true
        pass_filenames: false
```

- [ ] **Step 9: Prove the hook fails on a violation**

A hook that is wired but inert passes silently. Mutate, confirm, revert:

Line 577 is the first entry of §8 References, and step 3 left it reading
``- {issue}`65` — publish the design specifications``. Substitutions do not change the line
count, so the address still holds.

**Stage the conversions before mutating.** `git checkout <path>` restores from the index,
not from the last commit, and steps 1–4 are still unstaged at this point — so reverting
without staging first discards all 11 conversions in that file along with the mutation.

```bash
git add -A
sed -i '577s/{issue}`65`/#65/' \
  docs/src/developer/specs/2026-08-03-published-specs-design.md
pixi run --frozen pre-commit run check-github-references --all-files
git checkout docs/src/developer/specs/2026-08-03-published-specs-design.md
```

Expected: the middle command **fails**, naming that file and line 577 under
`Unlinked references (1):`. If it passes, the hook is not running the script.

- [ ] **Step 10: Lint and commit**

```bash
git add -A
pixi run --frozen lint
git commit -m "Link every GitHub reference in the design specifications"
```

---

### Task 3: Enable Sphinx's own check on hardcoded links

**Files:**
- Modify: `docs/src/conf.py:58-63`

**Interfaces:**
- Consumes: a tree with no hardcoded links (Task 2).
- Produces: nothing other tasks depend on.

**Why this is a second implementation and not a shared one.** The gate and Sphinx look for
the same defect with different code. A bug in the gate's `URL` pattern is exactly what an
independent matcher catches, and Sphinx's reports at the moment a documentation author is
looking at the build, naming the role to write instead (docs spec §3.8).

- [ ] **Step 1: Re-confirm the guard this depends on exists at the declared floor**

`pyproject.toml:310` declares `sphinx = ">=8.0"`, and every environment resolves with
`--frozen`, so the floor is never actually built (see the dependency-floors caveat: a
declared minimum is untested unless someone tests it by hand). This setting is only safe
because Sphinx declines to suggest a replacement when the captured value contains a
solidus — without that guard, the `user` role's `https://github.com/%s` matches every link
to another project's repository, and the build, under `--fail-on-warning`, fails on the
geovista, MetPy and tephi links already in the corpus.

This was checked while writing the plan: the guard is present in the pinned Sphinx 9.1.0
and in Sphinx 8.0.2, the oldest release the floor admits. Re-run both, because a plan is a
record of what was true when it was written, not a substitute for the check:

```bash
pixi run --frozen python -c "
import inspect, sphinx
from sphinx.ext import extlinks
src = inspect.getsource(extlinks.ExternalLinksChecker)
print(sphinx.__version__, \"'/' not in\" in src)
"
pixi exec --spec 'sphinx==8.0.*' --spec 'python=3.12' -- python -c "
import inspect, sphinx
from sphinx.ext import extlinks
src = inspect.getsource(extlinks.ExternalLinksChecker)
print(sphinx.__version__, \"'/' not in\" in src)
"
```

Expected: `9.1.0 True` and `8.0.2 True`. **If either prints `False`, stop and report it** —
the floor would have to be raised to the first Sphinx carrying the guard before this
setting could be enabled, and that is a `pyproject.toml` change this plan does not make.

- [ ] **Step 2: Enable the setting**

In `docs/src/conf.py`, directly beneath the `extlinks` dict:

```python
# Sphinx's own check on the docs spec §3.8 rule, and deliberately a second
# implementation of it rather than one shared with the pre-commit gate: a bug in
# that gate's pattern is what an independent matcher catches. It is safe to enable
# only because Sphinx declines to suggest a replacement when the captured value
# carries a solidus -- without that guard the `user` role's bare `%s` matches every
# link to another project's repository, and this build fails on warnings.
extlinks_detect_hardcoded_links = True
```

- [ ] **Step 3: Build the docs**

Run: `pixi run --frozen docs`

Expected: `build succeeded.` — Task 2 removed every hardcoded link, so there is nothing
left for the new setting to report.

- [ ] **Step 4: Prove the setting is not inert**

A clean build proves nothing about a check that has nothing to find. Mutate, confirm,
revert:

```bash
sed -i '577s|{issue}`65`|[#65](https://github.com/bjlittle/tephpy/issues/65)|' \
  docs/src/developer/specs/2026-08-03-published-specs-design.md
pixi run --frozen docs 2>&1 | grep -i "hardcoded link"
git checkout docs/src/developer/specs/2026-08-03-published-specs-design.md
```

Expected: a warning reading `hardcoded link '…/issues/65' could be replaced by an extlink
(try using ':issue:`65`' instead)`, and a failing build. Then confirm the revert builds
clean again with `pixi run --frozen docs`.

**Do not commit the mutated file.** It reintroduces exactly the form Task 2's hook rejects,
so the revert is what lets the next commit through.

- [ ] **Step 5: Confirm the other-project links are untouched**

The whole risk of this setting is that it fires on links it should not. Confirm the six
kinds present in the corpus survive:

Run: `grep -rn "github.com/SciTools\|github.com/Unidata\|github.com/bjlittle/geovista" docs/src --include=*.md --include=*.rst`

Each of those built without a warning in step 3. Record that in the commit message.

- [ ] **Step 6: Commit**

```bash
git add docs/src/conf.py
pixi run --frozen lint
git commit -m "Let Sphinx report a hardcoded GitHub link"
```

---

### Task 4: Changelog fragment

**Files:**
- Create: `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

The type is `documentation`: the reader-facing change is that the published specifications
now carry links. `internal` would understate it — the gate is the smaller half.

- [ ] **Step 1: Open the pull request to learn its number**

The fragment is named for the pull request, so it cannot be written before the pull request
exists. Push the branch and open it, then take the number.

- [ ] **Step 2: Write the fragment**

Create `changelog/<PR>.documentation.rst`. One short entry, ending with `:user:` attribution
per `changelog/README.md`. No issue is cited — this closes none.

```rst
Every reference to a tephpy issue or pull request in the design specifications is
now a link the reader can follow: 59 of them were plain text or a hand-written URL,
and each is written with the ``:issue:`` or ``:pull:`` extlink role instead, so the
URL is stated once in the documentation configuration. A pre-commit gate and
Sphinx's own ``extlinks_detect_hardcoded_links`` keep it that way. (:user:`claude`)
```

- [ ] **Step 3: Lint and commit**

```bash
git add changelog/
pixi run --frozen lint
git commit -m "Add the changelog fragment"
```

- [ ] **Step 4: Verify the fragment renders**

Run: `pixi run --frozen docs` and open `docs/_build/html/whatsnew/latest.html` (or wherever
`sphinx_changelog` renders the unreleased fragments). Confirm the ``:issue:``/``:pull:``
literals show as literals and that `:user:`claude`` renders as a link. The clean-build
caveat is already handled — the `docs` task declares `depends-on = ["docs-clean"]`, so
every build is from clean and no stale draft can be served.

---

## Verification

The whole change, end to end, before the pull request is marked ready:

- [ ] `pixi run --frozen lint` — clean, including both citation and reference hooks.
- [ ] `pixi run --frozen tests` — green.
- [ ] `pixi run --frozen docs` from clean — `build succeeded.`, no warnings.
- [ ] `.github/scripts/check_github_references.py` — `github references ok`, exit 0.
- [ ] `.github/scripts/check_citations.py` — still `citations ok`, with the anchor count up
  by one from the §3.8 anchor.
- [ ] Spot-check the built HTML: every converted reference is an `<a>` whose text is the
  number with a leading `#`, and whose `href` is the GitHub URL.

  Run: `grep -c 'class="extlink-\(issue\|pull\)' docs/_build/html/developer/specs/*.html`
  Expected: 42 for `2026-07-22-tephpy-design`, 5 for `2026-08-01-add-logo-design`, and 12
  for `2026-08-03-published-specs-design` — the per-file totals from Task 2, plus the one
  role §3.8 already contains outside a code span.

- [ ] Read the three specification pages on the Read the Docs pull-request preview,
  `https://tephpy--<PR>.org.readthedocs.build/en/<PR>/developer/specs/`, and follow three
  links: one from the plan table, one from the open-item ledger, one from §8 References.
  Read the Docs skips commits, so a missing status is not the same as no build.

## Constraints this work must not break

- **`tests/plotting/test_shading.py` still passes.** The edit is inside a docstring, and a
  docstring edit that breaks the module is a syntax error, not a subtle one — but the
  numpydoc-validation hook reads it, and a role in the summary line is a different shape
  from prose. The reference is in the extended description, not the summary.
- **`check_citations.py` keeps its exit codes.** Task 1 imports it for its corpus; importing
  a module runs it top to bottom, and it is written to be importable (the `main()` call sits
  under `if __name__ == "__main__"`). Nothing in this plan edits it.
- **The specifications' rendered anchors do not move.** A role replaces text inside a
  paragraph; no heading, and no `(docs-spec-N)=` target, is touched.
