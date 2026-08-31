# Documentation Snippet Executor Implementation Plan

> **Point-in-time record.** This plan captures what was intended before implementation. It
> is not updated afterwards — where the implementation departed from it, the departure is
> recorded in the pull request, and the living design specification in
> [`../specs/`](../specs/) is what describes tephpy as it stands.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the code the user documentation tells a reader to type — every python block
in the three Diátaxis quadrants written for users, as one script per page, in document
order, ending with a draw of every figure the page leaves open — so that a snippet cannot
silently stop working.

**Architecture:** One ordinary pytest module, `tests/test_docs_snippets.py`, in three parts.
A textual extractor reads the `.rst` sources directly, with no Sphinx involved, and returns
each literal block with the line it starts on. A renderer turns a page's python blocks into
a single script that is *line-aligned with the page* — block code at the line numbers it
occupies in the `.rst`, the gaps padded with blank lines — followed by an epilogue that
draws every open figure. A runner executes that script in a fresh interpreter under a
relocated `HOME`, `XDG_CONFIG_HOME` and working directory, so a page that saves a
configuration file or writes a figure cannot reach the contributor's own. Four further
assertions stand apart from the per-page cases and exist to make the gate refuse its own
empty input.

**Tech Stack:** Python 3.12+ standard library only (`re`, `os`, `pathlib`, `subprocess`,
`sys`) plus `pytest` and `matplotlib` — no new dependency, and deliberately no Sphinx, so
the gate runs in every test environment rather than only the docs one.

**Spec:** `docs spec §3.9`, in
[`../specs/2026-08-03-published-specs-design.md`](../specs/2026-08-03-published-specs-design.md).
Decision 8 of `docs spec §2` states the rule; `docs spec §6` states what verifies it.

**Issue:** {issue}`114` — nothing executes the code examples in the how-to guides.

## Global Constraints

- **Every pixi invocation carries `--frozen`.** `pixi run --frozen tests`,
  `pixi run --frozen lint`, `pixi run --frozen docs`. Never let pixi re-solve the
  environment.
- **Every new source file carries the BSD copyright header** — ruff `CPY001` enforces it.
  Copy it verbatim from `tests/conftest.py:1-4`.
- **Line length is 88 columns**, ruff-enforced.
- **Tests mirror the source layout** (spec §8.5). This gate is a contract about the
  repository rather than about a `tephpy` module, so it goes at
  `tests/test_docs_snippets.py` — alongside `tests/test_citations.py` and
  `tests/test_github_references.py`, not in a subdirectory.
- **`numpydoc-validation` runs on `^src/` only**, so the test module needs only ruff's
  numpy-convention pydocstyle. Write one-line docstrings on the helpers anyway; every
  neighbouring test module does.
- **`tests/*` carries per-file ignores** for `ANN001`, `ANN003`, `ANN201`, `ANN202`,
  `DTZ001`, `SLF001` and `D103` (`pyproject.toml:156`). Annotations on the module-level
  helpers are still worth writing and are what the code below uses.
- **`filterwarnings = ["error"]`** is the suite's own setting. The subprocess mirrors it
  with `-W error` on the command line, so a snippet that warns fails exactly as one that
  raises does.
- **The specifications are living documents; the plans are frozen** (docs spec §3.4).
  Nothing under `docs/src/developer/plans/` is edited by this work, including this file
  once its pull request merges.
- **There is no escape hatch** (docs spec §3.9). Do not add a directive option, a comment
  marker, a filename allowlist, or a `skip` for a block that will not run. A block a reader
  is invited to copy and which cannot run is a defect in the page.

---

### Task 1: The extractor and its unit tests

**Files:**
- Create: `tests/test_docs_snippets.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `literal_blocks(text) -> list[tuple[int, str, list[str]]]`,
  `python_blocks(text) -> list[tuple[int, list[str]]]`,
  `page_script(text) -> str | None`, `user_pages() -> list[Path]`,
  `code_pages() -> list[Path]`, and the constants `REPO`, `DOCS`, `QUADRANTS`,
  `DOCUMENTED`, `NEAR_MISS`, `EPILOGUE`. Task 2 adds the runner beneath them and calls
  `page_script`, `user_pages` and `code_pages`.

**Why the extractor is textual and not Sphinx's.** Sphinx is in the `docs` feature and not
in the `test` feature, so a docs-side gate always-skips in the CI test matrix. Reading the
`.rst` as text is what lets this run on 3.12, 3.13 and 3.14 alike. The cost is that the
extractor has to understand two things about reStructuredText literal blocks — directive
options, and where the body ends — and both are pinned by unit tests below.

**What "line-aligned" buys.** A block's code occupies the line numbers it occupies in the
`.rst`. The gaps are blank lines, which is safe because a block's lines are contiguous in
the source too, so padding only ever falls *between* blocks. A traceback then reads
`File ".../logo_snippets.py", line 26` and line 26 of `docs/src/howtos/logo.rst` is the
offending line, with no arithmetic.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_docs_snippets.py`. This is the whole file for Task 1; Task 2 appends to
it.

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Execute the code the user documentation tells a reader to type (docs spec §3.9).

Every python block in the three Diátaxis quadrants written for users is run, as
one script per page and in document order, because a page is a session rather
than a catalogue -- the second block of the ``add_logo`` how-to brands the figure
the first one bound, and executed alone it has nothing to brand.

The corpus is derived rather than declared: every ``.rst`` under the quadrant
directories, so a page is governed from the day it lands. The reference quadrant
is out of scope because it cannot drift, being generated from the docstrings and
the live CLI, and the developer section quotes code as illustration.

The extractor reads reStructuredText as text rather than through Sphinx. Sphinx
is in the ``docs`` pixi feature and not in ``test``, so a docs-side gate would
always-skip in the CI test matrix; this one runs on every Python the project
supports.
"""

from __future__ import annotations

from pathlib import Path
import re

REPO = Path(__file__).parents[1]
DOCS = REPO / "docs" / "src"

#: The Diátaxis quadrants written for users (docs spec §3.9).
QUADRANTS = ("howtos", "tutorials", "explanation")

#: The pages known to carry python. Membership, not a count: a count is a figure
#: that has to be re-measured to stay true. This is what fails when the extractor
#: stops recognising a directive, instead of every page passing by not being found.
DOCUMENTED = ("howtos/configuration.rst", "howtos/emphasis.rst", "howtos/logo.rst")

#: Every directive that introduces a literal block carrying a language. The three
#: spellings are recognised together, and the language is judged separately, so
#: that rewriting ``code-block`` as ``code`` cannot quietly empty the corpus.
DIRECTIVE = re.compile(
    r"^(?P<indent>[ ]*)\.\.[ ]+(?:code-block|code|sourcecode)::[ ]*"
    r"(?P<language>\S*)[ ]*$"
)

#: A directive option -- ``:linenos:``, ``:caption: …`` -- which sits between the
#: directive and its body and is not part of the code.
OPTION = re.compile(r"^[ ]*:[\w-]+:")

#: The language this gate executes, compared case-insensitively.
PYTHON = "python"

#: Languages that mean python and are not the spelling above. They are reported
#: rather than skipped: the detector has to be wider than the validator, or a
#: near-miss reads as compliance instead of as something to look at. ``pycon``
#: is here too -- a REPL transcript is still code a reader is invited to copy,
#: and the answer is to rewrite it as a script, not to exempt it.
NEAR_MISS = frozenset({"ipython", "ipython3", "py", "py3", "pycon", "python3"})


def literal_blocks(text: str) -> list[tuple[int, str, list[str]]]:
    """Extract every literal block, with the line its body starts on.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    list of tuple
        ``(first_line, language, lines)`` per block, ``first_line`` 1-based and
        naming the body's first line, and ``lines`` dedented to column zero.

    """
    lines = text.splitlines()
    found: list[tuple[int, str, list[str]]] = []
    index = 0
    while index < len(lines):
        directive = DIRECTIVE.match(lines[index])
        if directive is None:
            index += 1
            continue
        opening = len(directive["indent"])
        cursor = index + 1
        while cursor < len(lines) and (
            not lines[cursor].strip() or OPTION.match(lines[cursor])
        ):
            cursor += 1
        if cursor >= len(lines):
            break
        body = len(lines[cursor]) - len(lines[cursor].lstrip())
        if body <= opening:
            # The directive has no body -- the next content is a sibling, not a
            # child. Step by one rather than to `cursor`, so that a directive
            # immediately following this one is not stepped over.
            index += 1
            continue
        start = cursor
        while cursor < len(lines):
            line = lines[cursor]
            if line.strip() and len(line) - len(line.lstrip()) < body:
                break
            cursor += 1
        end = cursor
        while end > start and not lines[end - 1].strip():
            end -= 1
        found.append(
            (
                start + 1,
                directive["language"],
                [line[body:] for line in lines[start:end]],
            )
        )
        index = cursor
    return found


def python_blocks(text: str) -> list[tuple[int, list[str]]]:
    """Select the blocks this gate executes.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    list of tuple
        ``(first_line, lines)`` per python block, in document order.

    """
    return [
        (line, code)
        for line, language, code in literal_blocks(text)
        if language.lower() == PYTHON
    ]


def page_script(text: str) -> str | None:
    """Render a page's python blocks as one line-aligned script.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    str or None
        The script, or ``None`` when the page carries no python.

    """
    blocks = python_blocks(text)
    if not blocks:
        return None
    height = max(line + len(code) - 1 for line, code in blocks)
    script = [""] * height
    for line, code in blocks:
        for offset, statement in enumerate(code):
            script[line - 1 + offset] = statement
    return "\n".join(script) + "\n" + EPILOGUE


def user_pages() -> list[Path]:
    """Every page in the user quadrants, whether or not it carries code.

    Returns
    -------
    list of Path
        The ``.rst`` sources, quadrant by quadrant and sorted within each.

    """
    found: list[Path] = []
    for quadrant in QUADRANTS:
        found.extend(sorted((DOCS / quadrant).glob("*.rst")))
    return found


def code_pages() -> list[Path]:
    """The subset of :func:`user_pages` carrying at least one python block.

    Returns
    -------
    list of Path
        The pages with something to run.

    """
    return [
        page for page in user_pages() if python_blocks(page.read_text(encoding="utf-8"))
    ]


def identify(page: Path) -> str:
    """Name a page for a parametrised test id.

    Parameters
    ----------
    page : Path
        A page under :data:`DOCS`.

    Returns
    -------
    str
        The path relative to ``docs/src``, with forward slashes.

    """
    return page.relative_to(DOCS).as_posix()


def test_a_block_is_found_with_its_body_line():
    """The line reported is the body's first line, not the directive's."""
    text = "Prose.\n\n.. code-block:: python\n\n    value = 1\n"
    assert literal_blocks(text) == [(5, "python", ["value = 1"])]


def test_the_body_is_dedented_to_column_zero():
    """A block indented four spaces in the source runs at column zero."""
    text = ".. code-block:: python\n\n    if True:\n        value = 1\n"
    assert literal_blocks(text)[0][2] == ["if True:", "    value = 1"]


def test_a_directive_option_is_not_code():
    """``:linenos:`` sits between the directive and its body."""
    text = ".. code-block:: python\n    :linenos:\n\n    value = 1\n"
    assert literal_blocks(text) == [(4, "python", ["value = 1"])]


def test_the_block_ends_at_the_next_outdented_line():
    """Prose following a block is not swept into it."""
    text = ".. code-block:: python\n\n    value = 1\n\nAnd then some prose.\n"
    assert literal_blocks(text) == [(3, "python", ["value = 1"])]


def test_an_interior_blank_line_stays_in_the_block():
    """A blank line between two statements does not end the body."""
    text = ".. code-block:: python\n\n    first = 1\n\n    second = 2\n"
    assert literal_blocks(text)[0][2] == ["first = 1", "", "second = 2"]


def test_a_trailing_blank_line_is_trimmed():
    """The body ends at its last statement, so the reported height is right."""
    text = ".. code-block:: python\n\n    value = 1\n\n\n"
    assert literal_blocks(text) == [(3, "python", ["value = 1"])]


def test_a_nested_block_is_found():
    """A block inside an admonition is still code a reader would copy."""
    text = ".. note::\n\n    .. code-block:: python\n\n        value = 1\n"
    assert literal_blocks(text) == [(5, "python", ["value = 1"])]


def test_the_three_directive_spellings_are_recognised():
    """Rewriting ``code-block`` as ``code`` cannot quietly empty the corpus."""
    for name in ("code-block", "code", "sourcecode"):
        text = f".. {name}:: python\n\n    value = 1\n"
        assert literal_blocks(text) == [(3, "python", ["value = 1"])], name


def test_a_non_python_language_is_kept_but_not_selected():
    """The extractor reports every language; the selector judges it."""
    text = ".. code-block:: yaml\n\n    key: value\n"
    assert literal_blocks(text) == [(3, "yaml", ["key: value"])]
    assert python_blocks(text) == []


def test_the_language_is_matched_without_regard_to_case():
    """``Python`` is the same language, and must not be skipped in silence."""
    text = ".. code-block:: Python\n\n    value = 1\n"
    assert python_blocks(text) == [(3, ["value = 1"])]


def test_a_directive_with_no_body_is_passed_over():
    """A bare directive is a page defect for Sphinx, and yields no code here."""
    text = ".. code-block:: python\n\nProse at column zero.\n"
    assert literal_blocks(text) == []


def test_two_adjacent_directives_are_both_found():
    """A bodiless directive must not step the reader over its neighbour."""
    text = ".. code-block:: python\n\n.. code-block:: python\n\n    value = 1\n"
    assert literal_blocks(text) == [(5, "python", ["value = 1"])]


def test_the_script_is_line_aligned_with_the_page():
    """Block code sits at the line numbers it occupies in the source."""
    text = "\n".join(["Prose."] * 9 + [".. code-block:: python", "", "    value = 1"])
    script = page_script(text).splitlines()
    assert script[11] == "value = 1"
    assert script[:11] == [""] * 11


def test_a_second_block_keeps_its_own_line_numbers():
    """The gaps between blocks are padding, and the padding is blank lines."""
    text = (
        ".. code-block:: python\n\n    first = 1\n\nProse.\n\n"
        ".. code-block:: python\n\n    second = 2\n"
    )
    script = page_script(text).splitlines()
    assert script[2] == "first = 1"
    assert script[8] == "second = 2"


def test_a_page_with_no_python_renders_no_script():
    """The ordinary case in the explanation quadrant contributes nothing."""
    assert page_script("Prose only.\n") is None


def test_the_script_ends_with_the_draw_epilogue():
    """Execution alone would pass a page whose figure cannot be rendered."""
    script = page_script(".. code-block:: python\n\n    value = 1\n")
    assert script.endswith(EPILOGUE)
    assert "canvas.draw()" in script
```

The `EPILOGUE` constant those last two tests use is defined in Step 3 — Step 2 is where you
watch them fail for exactly that reason.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run --frozen pytest tests/test_docs_snippets.py -v`

Expected: a collection error — `NameError: name 'EPILOGUE' is not defined`, raised from
`page_script` at import. **A collection error is the expected failure here**, not a set of
red test lines, because `page_script` refers to a constant that does not exist yet.

- [ ] **Step 3: Add the epilogue constant**

Insert immediately after the `NEAR_MISS` constant, before `literal_blocks`:

```python
#: Appended to every page's script. Matplotlib defers most of its validation to
#: draw time -- ``emphasis={0.0: {"color": "notacolour"}}`` is accepted without
#: complaint and raises ``ValueError: Invalid RGBA argument`` only when the canvas
#: is drawn -- so a page whose figure cannot be rendered would otherwise reach the
#: last statement and pass (docs spec §3.9). It goes after the last block, where it
#: cannot disturb the line alignment above it, and imports pyplot under a private
#: name because a page need not have imported it at all.
EPILOGUE = """
import matplotlib.pyplot as _tephpy_pyplot

for _tephpy_number in _tephpy_pyplot.get_fignums():
    _tephpy_pyplot.figure(_tephpy_number).canvas.draw()
"""
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pixi run --frozen pytest tests/test_docs_snippets.py -v`

Expected: 16 passed. **If any is skipped, stop** — nothing in this module skips, so a skip
means a marker was copied in from a neighbouring file that does.

- [ ] **Step 5: Confirm the extractor sees the live pages**

The unit tests above all use fixtures. Check the extractor against the real corpus before
building anything on it:

```bash
pixi run --frozen python -c "
import sys; sys.path.insert(0, 'tests')
import test_docs_snippets as gate
for page in gate.user_pages():
    text = page.read_text(encoding='utf-8')
    languages = sorted({language for _, language, _ in gate.literal_blocks(text)})
    print(gate.identify(page), len(gate.python_blocks(text)), languages)
"
```

Expected, exactly:

```text
howtos/configuration.rst 2 ['console', 'python', 'text', 'yaml']
howtos/emphasis.rst 6 ['python']
howtos/index.rst 0 []
howtos/logo.rst 8 ['python']
tutorials/index.rst 0 []
explanation/index.rst 0 []
```

A different block count means the extractor and the page disagree — investigate before
continuing. The three `index.rst` files are toctrees and carry no code, which is the
ordinary case the design expects.

- [ ] **Step 6: Confirm the alignment against the real page**

```bash
pixi run --frozen python -c "
import sys; sys.path.insert(0, 'tests')
import test_docs_snippets as gate
page = gate.DOCS / 'howtos' / 'logo.rst'
source = page.read_text(encoding='utf-8').splitlines()
script = gate.page_script(page.read_text(encoding='utf-8')).splitlines()
for number in (20, 22, 25, 34, 46, 62, 79, 80):
    same = source[number - 1].strip() == script[number - 1].strip()
    print(number, 'OK' if same else 'MISALIGNED', script[number - 1].strip())
"
```

Expected: eight `OK` lines, ending with
`80 OK fig.savefig("sounding.png", transparent=True)`.

- [ ] **Step 7: Lint and commit**

```bash
git add tests/test_docs_snippets.py
pixi run --frozen lint
git commit -m "Extract the python blocks from the user documentation"
```

---

### Task 2: The sandbox, the runner, and the per-page cases

**Files:**
- Modify: `tests/test_docs_snippets.py` (append)

**Interfaces:**
- Consumes: `page_script`, `user_pages`, `code_pages`, `identify`, `DOCUMENTED`,
  `QUADRANTS`, `NEAR_MISS`, `literal_blocks` from Task 1.
- Produces: `environment(home) -> dict[str, str]`,
  `run_page(page, tmp_path) -> subprocess.CompletedProcess[str]`, and the five test
  functions below. Nothing later depends on them.

**Why a subprocess, and why a relocated home.** Three properties the configuration how-to
describes exist only in a fresh interpreter: the file is read once, at `import tephpy`, and
inside a test process that import has already happened. The isolation is the same argument
from the other side — `docs/src/howtos/configuration.rst:163` calls `tephpy.config.save()`,
which writes to the user's configuration directory, and `:151` calls `tephpy.config.load()`,
which searches it. This is not hypothetical: a `~/.config/tephpy/tephpyrc.yaml` reading
`isotherms:\n  color: purple` — the exact content that snippet writes — was found on the
development machine while this plan was being written, left behind by running the how-to by
hand. Run in place, the gate would rewrite it and read back whatever a contributor happened
to have.

**The recipe is `tests/test_config_autoload.py:39-56` verbatim**, with `MPLBACKEND` added.
Its docstring carries the full reasoning, and the six lines are repeated rather than
imported because that module's `_environ` is private to it and takes different arguments.
Point at it in a comment rather than restating why `MPLCONFIGDIR` stays put.

**Why the script is named `<stem>_snippets.py`.** `sys.path[0]` is the script's own
directory, so a script named for its page alone would shadow a top-level module of the same
name — a future `io.rst` or `types.rst` would produce an `io.py` that shadows the standard
library. The suffix costs nothing and the traceback still names the page.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_docs_snippets.py`, and extend the import block at the top of the file
so that it reads exactly:

```python
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys

import matplotlib as mpl
import pytest
```

`force-sort-within-sections` sorts by module name regardless of the `import` form, which is
why `from pathlib import Path` sits between `os` and `re` rather than in a group of its own.

```python
def environment(home: Path) -> dict[str, str]:
    """Build the controlled environment a page's script runs under.

    ``HOME`` and ``XDG_CONFIG_HOME`` both move, which empties the user
    configuration directory the discovery cascade searches; ``MPLCONFIGDIR``
    keeps pointing at this process's matplotlib cache, so the relocated home
    does not trigger a font-cache rebuild. ``tests/test_config_autoload.py``
    carries the full reasoning, including what Windows does differently.

    Parameters
    ----------
    home : Path
        The temporary directory standing in for the user's home.

    Returns
    -------
    dict of str to str
        The environment for the subprocess.

    """
    env = dict(os.environ)
    env.pop("TEPHPYRC", None)
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / "config")
    env["MPLCONFIGDIR"] = mpl.get_configdir()
    env["MPLBACKEND"] = "Agg"
    return env


def run_page(page: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Execute one page's snippets in a sandboxed fresh interpreter.

    Parameters
    ----------
    page : Path
        The page to run.
    tmp_path : Path
        The temporary directory to run in; the script, the saved configuration
        and any figure the page writes to a relative path all land here.

    Returns
    -------
    subprocess.CompletedProcess
        The finished process, with ``stdout`` and ``stderr`` captured as text.

    """
    script = page_script(page.read_text(encoding="utf-8"))
    assert script is not None, f"{identify(page)} carries no python to run"
    target = tmp_path / f"{page.stem}_snippets.py"
    target.write_text(script, encoding="utf-8")
    return subprocess.run(  # noqa: S603
        [sys.executable, "-W", "error", str(target)],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
        env=environment(tmp_path),
    )


def report(page: Path, result: subprocess.CompletedProcess[str]) -> str:
    """Render a failure so its line numbers are usable.

    Parameters
    ----------
    page : Path
        The page that failed.
    result : subprocess.CompletedProcess
        The finished process.

    Returns
    -------
    str
        The assertion message.

    """
    return (
        f"\n{page.relative_to(REPO)} did not run clean (docs spec §3.9).\n"
        "The traceback's line numbers are this page's line numbers. A frame in "
        f"{page.stem}_snippets.py below the last block means the snippets ran and "
        "a figure could not be drawn.\n\n"
        f"{result.stdout}{result.stderr}"
    )


@pytest.mark.parametrize("page", code_pages(), ids=identify)
def test_the_page_runs(page, tmp_path):
    """A page's blocks run as one script, in order, and its figures draw."""
    result = run_page(page, tmp_path)
    assert result.returncode == 0, report(page, result)


def test_the_quadrant_directories_exist():
    """A renamed quadrant would empty the corpus without touching this file."""
    missing = [name for name in QUADRANTS if not (DOCS / name).is_dir()]
    assert missing == [], (
        f"these user quadrants are not where this gate looks: {missing}. "
        "A gate that checks nothing is a green tick over nothing (docs spec §3.9)"
    )


def test_pages_are_discovered():
    """An empty corpus is a gate failure, not a quiet pass."""
    assert user_pages(), (
        f"no .rst pages found under {DOCS} in {QUADRANTS} (docs spec §3.9)"
    )


def test_the_documented_pages_yield_blocks():
    """Named pages, not a count: a count has to be re-measured to stay true."""
    found = {identify(page) for page in code_pages()}
    assert set(DOCUMENTED) <= found, (
        f"these pages carry python and yielded no block: "
        f"{sorted(set(DOCUMENTED) - found)}. The extractor has stopped "
        "recognising a directive (docs spec §3.9)"
    )


def test_no_block_names_a_near_miss_language():
    """A python block spelled another way is reported, never skipped."""
    offenders = [
        (identify(page), line, language)
        for page in user_pages()
        for line, language, _ in literal_blocks(page.read_text(encoding="utf-8"))
        if language.lower() in NEAR_MISS
    ]
    assert offenders == [], (
        "these blocks name a language this gate does not execute, so they would "
        f"be passed over in silence: {offenders}. Write them as `python` "
        "(docs spec §3.9)"
    )
```

- [ ] **Step 2: Run the tests to verify they behave**

Run: `pixi run --frozen pytest tests/test_docs_snippets.py -v`

Expected: 20 passed — the 16 from Task 1, plus three `test_the_page_runs` cases
(`howtos/configuration.rst`, `howtos/emphasis.rst`, `howtos/logo.rst`) and the four
standing assertions. This is the one step in the plan where the new tests are expected to
pass first time: the pages are correct today, and the point of the gate is to keep them
that way. Steps 4 and 5 are what prove it is not merely green.

- [ ] **Step 3: Prove the sandbox contains the configuration how-to's writes**

The one behaviour that would be silently wrong rather than red. Confirm the real
configuration file is neither read nor written:

```bash
pixi run --frozen python -c "
import sys; sys.path.insert(0, 'tests')
from pathlib import Path
import test_docs_snippets as gate
real = Path.home() / '.config' / 'tephpy' / 'tephpyrc.yaml'
before = real.stat().st_mtime_ns if real.is_file() else None
work = Path('.snippet-sandbox-probe'); work.mkdir(exist_ok=True)
page = gate.DOCS / 'howtos' / 'configuration.rst'
result = gate.run_page(page, work.resolve())
after = real.stat().st_mtime_ns if real.is_file() else None
print('rc', result.returncode)
print('untouched', before == after)
print('saved inside the sandbox', (work / 'config' / 'tephpy' / 'tephpyrc.yaml').is_file())
"
rm -rf .snippet-sandbox-probe
```

Expected: `rc 0`, `untouched True`, `saved inside the sandbox True`. **If `untouched` is
`False`, stop** — the relocation is not taking effect and the gate is editing the
contributor's own configuration.

- [ ] **Step 4: Prove a broken snippet fails its page and no other**

Mutate, confirm, revert. **Commit or stage nothing first** — there is nothing uncommitted
in `docs/` at this point, so `git checkout` restores the page from the index cleanly.

```bash
sed -i '26s/loc="lower right"/placement="x"/' docs/src/howtos/logo.rst
pixi run --frozen pytest tests/test_docs_snippets.py -v
git checkout docs/src/howtos/logo.rst
```

Expected: `test_the_page_runs[howtos/logo.rst]` **FAILS** and the other two pass. The
assertion message must carry `File ".../logo_snippets.py", line 26` — line 26 is
`add_logo(ax, loc="lower right")` in the page, which is the alignment claim made good — and
end in `TypeError: unknown option ['placement']`.

- [ ] **Step 5: Prove the draw epilogue is load-bearing**

A typed-correct value matplotlib rejects only at draw time. Line 97 of the emphasis how-to
is chosen deliberately: it is the last `ax.isotherms` call on the second figure, so no later
block reconfigures the family and undoes the mutation.

```bash
sed -i '97s/ax.isotherms(emphasis={})/ax.isotherms(emphasis={0.0: {"color": "notacolour"}})/' \
  docs/src/howtos/emphasis.rst
pixi run --frozen pytest "tests/test_docs_snippets.py::test_the_page_runs[howtos/emphasis.rst]" -v
```

Expected: **FAIL**, ending `ValueError: Invalid RGBA argument: 'notacolour'`.

Now delete the epilogue and confirm the same page passes — this is the step that shows the
draw is doing work rather than decorating the script:

```bash
python - <<'PY'
from pathlib import Path
target = Path("tests/test_docs_snippets.py")
text = target.read_text(encoding="utf-8")
target.write_text(text.replace('_tephpy_pyplot.figure(_tephpy_number).canvas.draw()', 'pass'), encoding="utf-8")
PY
pixi run --frozen pytest "tests/test_docs_snippets.py::test_the_page_runs[howtos/emphasis.rst]" -v
```

Expected: **PASS** — the snippet runs to its last statement and the invalid colour is never
looked at. Then revert both:

```bash
git checkout docs/src/howtos/emphasis.rst tests/test_docs_snippets.py
```

**`git checkout` on the test module discards Step 1's work if it is unstaged.** Stage the
module before the mutation above, or re-apply the one-word edit by hand. Confirm the revert
is clean with `pixi run --frozen pytest tests/test_docs_snippets.py -v` — 20 passed.

- [ ] **Step 6: Prove a narrowed extractor fails loudly**

The failure mode the standing assertions exist for. Narrow the directive pattern so nothing
matches, and confirm the gate reports it rather than reporting three vacuous passes:

```bash
sed -i 's/code-block|code|sourcecode/nosuchdirective/' tests/test_docs_snippets.py
pixi run --frozen pytest tests/test_docs_snippets.py -v
git checkout tests/test_docs_snippets.py
```

Expected: `test_the_documented_pages_yield_blocks` **FAILS**, naming all three pages.

Note what `test_the_page_runs` does here: `code_pages()` returns nothing, so pytest reports
one entry — `SKIPPED … got empty parameter set` — rather than three failures. That is
precisely why the standing assertions exist. A gate built only from the parametrised cases
would have gone from three green ticks to a skip, which reads as "nothing to do" rather than
as "the extractor is broken". (The same staging caveat as Step 5 applies to the revert.)

Then the near miss the other three assertions cannot see — a page that keeps all its blocks
and misspells one language:

```bash
sed -i '18s/code-block:: python/code-block:: pycon/' docs/src/howtos/emphasis.rst
pixi run --frozen pytest tests/test_docs_snippets.py -v
git checkout docs/src/howtos/emphasis.rst
```

Expected: `test_no_block_names_a_near_miss_language` **FAILS**, naming
`('howtos/emphasis.rst', 20, 'pycon')`. `test_the_documented_pages_yield_blocks` still
passes — the page has five other python blocks — which is exactly the hole this assertion
fills. `test_the_page_runs[howtos/emphasis.rst]` also fails, because the imports in the
skipped block are what the rest of the page needs; on a page whose first block was not the
imports it would have passed, and the near-miss assertion is what would still have caught
it.

- [ ] **Step 7: Run the whole suite, on every supported Python**

Run: `pixi run --frozen tests`

Expected: the pre-existing count plus 20, all green. Then confirm the gate is not
accidentally 3.14-only:

```bash
pixi run --frozen --environment test-py312 pytest tests/test_docs_snippets.py -q
pixi run --frozen --environment test-py313 pytest tests/test_docs_snippets.py -q
```

Expected: `20 passed` from each. This is the property a docs-build gate could not have —
the docs build has one environment.

- [ ] **Step 8: Lint and commit**

```bash
git add tests/test_docs_snippets.py
pixi run --frozen lint
git commit -m "Execute the python snippets in the user documentation"
```

---

### Task 3: The authoring rules, and the linter directives in the pages

**Files:**
- Modify: `docs/src/developer/docs-style.rst` (new section before `Attribute Documentation`)
- Modify: `docs/src/howtos/logo.rst:22`
- Modify: `docs/src/howtos/emphasis.rst:22`

**Interfaces:**
- Consumes: the gate from Task 2.
- Produces: nothing other tasks depend on.

**Why the style guide gains a section.** The gate binds an author in ways nothing tells
them: a later block may rely on an earlier one's names, so the blocks of a page cannot be
reordered freely; there is no way to mark a block as not for execution; and execution proves
a snippet runs, not that it does what the sentence above it claims — that half is an
authoring rule, and `docs spec §3.9` says the style guide is where it lives.

**Why the `# noqa` comments go.** `docs/src/howtos/logo.rst:22` and
`docs/src/howtos/emphasis.rst:22` both read `import tephpy  # noqa: F401`. Ruff does not
read `.rst`, so the directive suppresses nothing; what it does is tell a reader pasting the
line to appease a linter they are not running, in place of saying why the import is there at
all. Replace it with the reason. This is a fix in the page the gate now executes, which is
where a contained defect belongs.

- [ ] **Step 1: Rewrite the two import comments**

`docs/src/howtos/logo.rst:22` and `docs/src/howtos/emphasis.rst:22`, both currently:

```python
    import tephpy  # noqa: F401
```

Both become:

```python
    import tephpy  # registers the "tephigram" projection
```

Substitution in place — the line count does not change, so the gate's alignment and the
line numbers named in Task 2's mutation steps still hold.

**Do not touch `docs/src/howtos/emphasis.rst:87`.** It reads a bare `import tephpy` and the
block below it uses the name directly, so there is nothing to explain.

- [ ] **Step 2: Add the style-guide section**

In `docs/src/developer/docs-style.rst`, insert immediately before the
`Attribute Documentation` heading at line 240:

```rst
Code Examples
-------------

Every python block in the how-to, tutorial and explanation quadrants is executed
by ``tests/test_docs_snippets.py``, as one script per page and in document order,
ending with a draw of every figure the page leaves open. Four rules follow, and
the rule is specified in docs spec §3.9.

A page is a session, not a catalogue. A later block may rely on a name an earlier
one bound — ``add_logo()`` with no argument brands the figure the block above it
created — so the blocks of a page cannot be reordered freely, and a block that
would not run after the ones above it is a page defect rather than a gate problem.

There is no way to mark a block as not for execution. A block a reader is invited
to copy and which cannot run is the defect; the answer is to fix the snippet, or
to stop presenting it as one. A REPL transcript is code too — write it as a script
in a ``python`` block rather than as ``pycon``, which the gate reports rather than
skips.

Snippets carry no linter directives. ``# noqa`` and ``# type: ignore`` suppress
nothing in a ``.rst`` file, and they ask a reader pasting the line to satisfy
tooling they are not running. Where an import looks unused, say why it is there
instead — ``import tephpy  # registers the "tephigram" projection``.

Where a snippet's surrounding prose makes a behavioural promise, a test pins the
promise. Execution and truth fail independently: :pull:`113` fixed a passage whose
snippet ran perfectly and whose prose was wrong, and the gate would have passed it.
Name the test in the pull request that adds the prose, so the connection is on the
record.
```

**Watch the citation form.** This is reStructuredText, so the roles are `:pull:` and
`:issue:` with single colons, not the MyST `{pull}` used in the Markdown specifications. A
bare `spec §N` in this file means the *parent* specification, so `docs spec §3.9` carries
its prefix — the pre-commit citation hook rejects a bare `§3.9` here, and would resolve a
wrongly-prefixed one silently.

- [ ] **Step 3: Confirm the pages still run and the docs still build**

```bash
pixi run --frozen pytest tests/test_docs_snippets.py -v
pixi run --frozen docs
```

Expected: 20 passed, and `build succeeded.` with no warnings. The `docs` task declares
`depends-on = ["docs-clean"]`, so the build is from clean and no stale draft is served.

- [ ] **Step 4: Read the rendered section**

Open `docs/_build/html/developer/docs-style.html` and confirm the new section appears in the
page's local contents, that `:pull:`113`` rendered as a link reading `#113`, and that
`docs spec §3.9` rendered as a cross-reference into the specification rather than as plain
text.

```bash
grep -o 'Code Examples' docs/_build/html/developer/docs-style.html | head -2
grep -o 'extlink-pull[^>]*>#113' docs/_build/html/developer/docs-style.html
```

Expected: at least one `Code Examples` (the heading, plus its toc entry) and one
`#113` link. **If the `#113` grep returns nothing, the role did not render** — check the
colon form.

- [ ] **Step 5: Lint and commit**

```bash
git add docs/src/developer/docs-style.rst docs/src/howtos/logo.rst docs/src/howtos/emphasis.rst
pixi run --frozen lint
git commit -m "State the code-example rules in the documentation style guide"
```

---

### Task 4: Changelog fragments

**Files:**
- Create: `changelog/<PR>.internal.rst`
- Create: `changelog/<PR>.documentation.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

Two fragments, because the change has two audiences. The gate is `internal` — a reader gains
nothing directly from a test existing. The style-guide section and the corrected import
comments are `documentation`.

- [ ] **Step 1: Open the pull request to learn its number**

The fragment is named for the pull request, so it cannot be written before the pull request
exists. Push the branch and open it, then take the number. An issue filed in the meantime
takes the next number, so do not guess it from {issue}`114`.

Write the pull-request body with bare `#114`, not a role — GitHub renders `{issue}` and
`:issue:` literally, and nothing scans a pull-request body.

- [ ] **Step 2: Write the fragments**

`changelog/<PR>.internal.rst` — cite the issue where the fragment describes what it
reported, per `changelog/README.md`:

```rst
Every python code example in the how-to, tutorial and explanation documentation is
now executed by the test suite, as one script per page and in document order, so
that a snippet cannot silently stop working (:issue:`114`). Each page's figures are
drawn as well as built, because :mod:`matplotlib` defers most of its validation to
draw time. (:user:`claude`)
```

`changelog/<PR>.documentation.rst`:

```rst
Added a Code Examples section to the documentation style guide, stating what an
author may rely on across the blocks of a page, and replaced the ``# noqa`` comment
in two how-to snippets with the reason the import is there. (:user:`claude`)
```

- [ ] **Step 3: Lint and commit**

```bash
git add changelog/
pixi run --frozen lint
git commit -m "Add the changelog fragments"
```

- [ ] **Step 4: Verify the fragments render**

Run `pixi run --frozen docs` and open the unreleased-fragment page. Confirm `:issue:`114``
is a link reading `#114`, `:mod:`matplotlib`` resolves through intersphinx, and
`:user:`claude`` is a link. A cross-reference that fails to resolve is a build warning, and
the build fails on warnings — so a clean build is most of this check, and the eye is for the
link *text*.

---

## Verification

The whole change, end to end, before the pull request is marked ready:

- [ ] `pixi run --frozen lint` — clean, including the citation and GitHub-reference hooks.
- [ ] `pixi run --frozen tests` — green, with 20 more tests than before.
- [ ] `pixi run --frozen --environment test-py312 pytest tests/test_docs_snippets.py -q` and
  the same for `test-py313` — `20 passed` from each. The gate's whole advantage over a
  docs-build check is that it runs in every environment; a plan that never checks two of
  them has not verified that claim.
- [ ] `pixi run --frozen docs` from clean — `build succeeded.`, no warnings.
- [ ] The three mutations of Task 2 (steps 4, 5 and 6), each reverted. These are what
  `docs spec §6` records, and a green suite proves none of them on its own.
- [ ] The sandbox probe of Task 2 step 3 — the real `~/.config/tephpy/tephpyrc.yaml` is
  neither read nor written.
- [ ] Confirm the sdist ships the pages the gate asserts exist, since the module asserts
  rather than skips:

  ```bash
  pixi run --frozen python -m build --sdist --outdir /tmp/snippet-sdist
  tar -tzf /tmp/snippet-sdist/*.tar.gz | grep -c "docs/src/howtos/.*\.rst"
  tar -tzf /tmp/snippet-sdist/*.tar.gz | grep -c "docs/src/developer/plans"
  ```

  Expected: `4` and `0`. setuptools_scm includes every tracked file less the `MANIFEST.in`
  prunes, and `prune docs/src/developer/plans` is the only one touching `docs/`. **If the
  first is `0`, stop and report it** — the quadrant assertion would fail on an unpacked
  sdist, and the fix is a `MANIFEST.in` change this plan does not make.
- [ ] Read `docs-style.rst` on the Read the Docs pull-request preview,
  `https://tephpy--<PR>.org.readthedocs.build/en/<PR>/developer/docs-style.html`, and follow
  the `docs spec §3.9` cross-reference into the specification. Read the Docs skips commits,
  so a missing status is not the same as no build.

## Constraints this work must not break

- **`tests/conftest.py` stays as it is.** Its autouse `_pristine_config` fixture resets
  `tephpy.config` around every test, which is what keeps a contributor's own configuration
  file out of the image comparisons. This gate runs its pages out-of-process, so the fixture
  neither helps nor hinders it, and nothing here needs the fixture changed.
- **`tests/test_config_autoload.py` keeps its own `_environ`.** The six lines are repeated
  in the new module rather than shared. Refactoring that module to export them is a separate
  change, and doing it here would put an unrelated file in this pull request's diff.
- **No new dependency.** The gate is standard library, pytest and matplotlib. In particular
  it must not import Sphinx, docutils or myst-parser — that is what would confine it to the
  `docs` environment.
- **The line numbers in the how-to pages do not move.** Task 3 substitutes within two lines
  and adds none. A change that inserted a line would invalidate the mutation steps' `sed`
  addresses, which are the record of how the gate was proved.
- **`pytest-mpl` is untouched.** Comparing a page's figures against a baseline image is
  deliberately out of scope (docs spec §3.9); no baseline is added, and
  `tests/plotting/test_images.py` remains what pins appearance.
