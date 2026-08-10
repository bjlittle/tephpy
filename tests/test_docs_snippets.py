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

import os
from pathlib import Path
import re
import subprocess
import sys

import matplotlib as mpl
import pytest

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
    """Select the subset of :func:`user_pages` carrying at least one python block.

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


def test_no_block_hides_the_language_this_gate_runs():
    """A python block spelled another way, or not spelled at all, is reported."""
    offenders = [
        (identify(page), line, language)
        for page in user_pages()
        for line, language, _ in literal_blocks(page.read_text(encoding="utf-8"))
        if language.lower() in NEAR_MISS or not language
    ]
    assert offenders == [], (
        "these blocks do not name a language this gate executes, so they would "
        f"be passed over in silence: {offenders}. A block with no language is "
        "highlighted using Sphinx's `highlight_language` and can be python on "
        "the page; write them all as `python` (docs spec §3.9)"
    )
