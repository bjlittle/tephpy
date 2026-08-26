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

#: The source suffixes Sphinx reads here that this gate does not. ``source_suffix``
#: is unset, so Sphinx reads ``.rst``; myst-nb, loaded to parse the published ``.md``
#: specifications, registers these two as well. A user page written in either would
#: build and publish like any other while the corpus, scoped to ``.rst``, never saw
#: it -- the silent exemption docs spec §3.9 declines to allow.
UNREAD_SUFFIXES = (".md", ".ipynb")

#: The pages known to carry python. Membership, not a count: a count is a figure
#: that has to be re-measured to stay true. This is what fails when the extractor
#: stops recognising a directive, instead of every page passing by not being found.
DOCUMENTED = (
    "howtos/configuration.rst",
    "howtos/emphasis.rst",
    "howtos/framing.rst",
    "howtos/logo.rst",
    "howtos/temp-and-bufr.rst",
)

#: The pages that publish figures (plots spec §3.2). Membership again, and for a
#: sharper reason than above: every page-shape check below iterates these pages,
#: so a converted page that stopped being recognised would not fail those checks
#: -- it would pass all of them, having been asked nothing.
PUBLISHES_FIGURES = (
    "howtos/emphasis.rst",
    "howtos/framing.rst",
    "howtos/logo.rst",
    "howtos/temp-and-bufr.rst",
)

#: Every directive that introduces a literal block carrying a language. The three
#: spellings are recognised together, and the language is judged separately, so
#: that rewriting ``code-block`` as ``code`` cannot quietly empty the corpus.
DIRECTIVE = re.compile(
    r"^(?P<indent>[ ]*)\.\.[ ]+(?:code-block|code|sourcecode)::[ ]*"
    r"(?P<language>\S*)[ ]*$"
)

#: The directive that publishes a figure (plots spec §3.1). It is deliberately not
#: folded into :data:`DIRECTIVE`: that pattern reads a directive's argument as a
#: language, and ``.. plot::`` either takes none or takes a filename, so folding it
#: in would classify an unnamed plot as naming no language -- which
#: :func:`test_no_block_hides_the_language_this_gate_runs` reports -- and would read
#: ``script.py`` as a language nobody executes (plots spec §3.4). Its body is python
#: by definition, so it needs no language to be judged from.
PLOT = re.compile(r"^(?P<indent>[ ]*)\.\.[ ]+plot::[ ]*(?P<argument>\S*)[ ]*$")

#: A directive option -- ``:linenos:``, ``:caption: …`` -- which sits between the
#: directive and its body and is not part of the code.
OPTION = re.compile(r"^[ ]*:[\w-]+:")

#: A directive option with its value, for the options a ``.. plot::`` is judged by
#: (plots spec §3.2). The value is optional: ``:nofigs:`` is a flag and
#: ``:context: reset`` is not.
OPTION_VALUE = re.compile(r"^[ ]*:(?P<name>[\w-]+):[ ]*(?P<value>.*?)[ ]*$")

#: The language this gate executes, compared case-insensitively.
PYTHON = "python"

#: Languages that mean python and are not the spelling above. They are reported
#: rather than skipped: the detector has to be wider than the validator, or a
#: near-miss reads as compliance instead of as something to look at. ``pycon``
#: is here too -- a REPL transcript is still code a reader is invited to copy,
#: and the answer is to rewrite it as a script, not to exempt it.
#:
#: These are the spellings a contributor plausibly reaches for: Pygments' own
#: ``py``/``py3``/``python3``, its console aliases ``pycon``/``python-console``,
#: and IPython's ``ipython``/``ipython3``, which no bundled Pygments lexer
#: claims. It is *not* every alias of Pygments' Python lexer, which also answers
#: to ``bazel``, ``pyi``, ``sage`` and ``starlark`` -- names of other languages
#: that happen to share a lexer, and that nobody writes meaning python. A block
#: spelled one of those four highlights as python and this gate passes over it;
#: the exposure is left standing deliberately rather than by oversight.
#:
#: The widest near miss names no language at all and so cannot be
#: listed here: a directive that omits one, the bare ``::`` marker
#: :func:`implicit_blocks` finds, and the ``>>>`` paragraph
#: :func:`doctest_blocks` finds are reported by their shape instead.
NEAR_MISS = frozenset(
    {"ipython", "ipython3", "py", "py3", "pycon", "python-console", "python3"}
)

#: Every spelling that means python on a page, written out rather than derived
#: from :data:`PYTHON` and :data:`NEAR_MISS`. It is the oracle
#: :func:`test_the_two_language_checks_compose` is measured against, and an
#: oracle assembled from the constants it checks would agree with them by
#: construction rather than by being right.
PYTHON_SPELLINGS = (
    "ipython",
    "ipython3",
    "py",
    "py3",
    "pycon",
    "python",
    "python-console",
    "python3",
)

#: Opens a doctest block, which needs no directive and no marker to be rendered
#: as a python console session (docs spec §3.9).
PROMPT = ">>>"

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
        plot = PLOT.match(lines[index]) if directive is None else None
        if directive is None and plot is None:
            index += 1
            continue
        opening = len((directive or plot)["indent"])
        cursor = index + 1
        if (
            cursor < len(lines)
            and lines[cursor].strip()
            and OPTION.match(lines[cursor])
        ):
            # The option block is consumed whole, to the blank line
            # reStructuredText requires before the content -- a directive
            # carrying an argument or an option and no blank line under it is a
            # docutils error. Taking it line by line instead would stop at the
            # continuation of a wrapped ``:caption:``, which matches no option
            # and would be read as the first line of the code.
            while cursor < len(lines) and lines[cursor].strip():
                cursor += 1
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
        start = cursor
        while cursor < len(lines):
            line = lines[cursor]
            if line.strip() and len(line) - len(line.lstrip()) <= opening:
                break
            cursor += 1
        end = cursor
        while end > start and not lines[end - 1].strip():
            end -= 1
        if end == start:
            # The directive has no body -- the next content is a sibling, not a
            # child. Step by one rather than to `cursor + 1`, where the scan
            # resumes after a block with a body, because that would step over a
            # directive immediately following this one.
            index += 1
            continue
        # The body is dedented by the least-indented line rather than by the
        # first, which is what docutils does: a block opening deeper than it
        # ends keeps that opening indentation, and measuring from the first line
        # would end the block early and drop everything under the outdent.
        body = min(
            len(line) - len(line.lstrip()) for line in lines[start:end] if line.strip()
        )
        found.append(
            (
                start + 1,
                directive["language"] if directive else PYTHON,
                [line[body:] for line in lines[start:end]],
            )
        )
        index = cursor
    return found


def block_lines(text: str) -> set[int]:
    """Collect every line already spoken for as a directive block's content.

    A block's body is free to contain anything, including the shapes the two
    marker-free detectors below look for -- a ``code-block:: text`` may end a
    line in ``::`` or open one with ``>>>`` -- so both of them subtract this.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    set of int
        The 1-based line numbers, body lines only.

    """
    return {
        number
        for first, _, body in literal_blocks(text)
        for number in range(first, first + len(body))
    }


def implicit_blocks(text: str) -> list[int]:
    """Find every literal block introduced by a bare ``::`` marker.

    reStructuredText's other code-block form -- a paragraph ending in ``::``, a
    blank line, then an indented body -- names no language, so Sphinx renders it
    with whatever ``highlight_language`` says, and the default is python. Such a
    block is python on the page and is reported rather than run, which is what a
    directive naming no language already gets (docs spec §3.9).

    A candidate is a line whose stripped form ends in ``::`` with a blank line
    and then a strictly more-indented body under it. The body is what keeps an
    ordinary sentence out: a marker with nothing indented after it is a docutils
    error rather than a block. The blank line is what keeps a definition list
    out: written without one, ``term::`` over an indented line is a definition
    and ``:field::`` over one is a field body, and docutils renders neither as
    code. A line opening ``..`` is a directive or a comment -- both
    ``.. note::`` and a language-less ``.. code-block::`` end in ``::``, and the
    second is :func:`literal_blocks`'s to report. A line already inside a block
    that function returned is that block's content, which the body of a
    ``code-block:: text`` is free to end with.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    list of int
        The 1-based first line of each such block's body, in document order,
        so that a report of one reads like a report of the others.

    """
    lines = text.splitlines()
    claimed = block_lines(text)
    found: list[int] = []
    for index, line in enumerate(lines):
        marker = line.strip()
        if not marker.endswith("::") or marker.startswith(".."):
            continue
        if index + 1 in claimed:
            continue
        cursor = index + 1
        if cursor >= len(lines) or lines[cursor].strip():
            # The blank line is what makes this a literal block. Without it
            # docutils reads the indented lines below as a definition or as a
            # field body, and neither is rendered as code.
            continue
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
        if cursor >= len(lines):
            continue
        body = len(lines[cursor]) - len(lines[cursor].lstrip())
        if body > len(line) - len(line.lstrip()):
            found.append(cursor + 1)
    return found


def doctest_blocks(text: str) -> list[int]:
    """Find every doctest block, the third shape python takes on a page.

    A paragraph opening with ``>>>`` is a doctest block. It needs no directive
    and no ``::`` marker, and docutils renders it as one whatever the prose
    around it says, so Sphinx highlights it as a python console session. That
    is the same transcript ``pycon`` names, and it is reported for the same
    reason: a reader is still invited to copy it, and the answer is to rewrite
    it as a script rather than to exempt it (docs spec §3.9).

    The paragraph is what makes it a block, so only a ``>>>`` line opening one
    is reported -- under a line of prose the same text is that paragraph's
    content. A line already inside a directive's block belongs to that block,
    which is how a ``code-block:: text`` may quote a session unmolested.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    list of int
        The 1-based first line of each such block, in document order.

    """
    lines = text.splitlines()
    claimed = block_lines(text)
    return [
        index + 1
        for index, line in enumerate(lines)
        if line.strip().startswith(PROMPT)
        and index + 1 not in claimed
        and not (index and lines[index - 1].strip())
    ]


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


def plot_directives(text: str) -> list[tuple[int, str, dict[str, str]]]:
    """Every ``.. plot::`` on a page, with its argument and its options.

    Separate from :func:`literal_blocks`, which reports what to *run*: the page
    shape of plots spec §3.2 is judged from what a directive declares, including
    a directive that renders no figure and one given a filename instead of a
    body, neither of which contributes a line of code.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    list of tuple
        ``(line, argument, options)`` per directive, in document order, ``line``
        1-based and naming the directive itself. ``argument`` is the empty string
        for the body form. ``options`` maps each option to its value, which is the
        empty string for a flag such as ``:nofigs:``.

    """
    lines = text.splitlines()
    # A ``.. plot::`` written *inside* another block's body is that block's
    # content -- the style guide quotes the directive it documents -- and is not
    # a directive this page declares.
    inside = block_lines(text)
    found: list[tuple[int, str, dict[str, str]]] = []
    for index, line in enumerate(lines):
        plot = PLOT.match(line)
        if plot is None or index + 1 in inside:
            continue
        options: dict[str, str] = {}
        cursor = index + 1
        while cursor < len(lines) and lines[cursor].strip():
            option = OPTION_VALUE.match(lines[cursor])
            if option is None:
                break
            options[option["name"]] = option["value"]
            cursor += 1
        found.append((index + 1, plot["argument"], options))
    return found


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


def user_pages(docs: Path = DOCS) -> list[Path]:
    """Every page in the user quadrants, whether or not it carries code.

    The search descends: a tutorial series is the thing that gets a directory of
    its own, and a page inside one is governed from the day it lands like any
    other (docs spec §3.9).

    Parameters
    ----------
    docs : Path, optional
        The documentation source root holding the quadrant directories. It
        defaults to this repository's, which is what the gate reads; a test
        passes a tree of its own to show that the descent happens.

    Returns
    -------
    list of Path
        The ``.rst`` sources, quadrant by quadrant and sorted within each.

    """
    found: list[Path] = []
    for quadrant in QUADRANTS:
        found.extend(sorted((docs / quadrant).rglob("*.rst")))
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


def test_a_wrapped_option_is_not_code():
    """A ``:caption:`` running onto a second line is still the option.

    Its continuation matches no option and is indented past the code, so
    reading the option block line by line would take the continuation for the
    body and drop ``value = 1`` -- running caption prose as python, and
    executing none of the snippet the page is really showing.
    """
    text = (
        ".. code-block:: python\n    :caption: a very long caption\n"
        "        wrapped onto here\n\n    value = 1\n"
    )
    assert literal_blocks(text) == [(5, "python", ["value = 1"])]


def test_a_body_is_dedented_by_its_least_indented_line():
    """A block opening deeper than it ends keeps that opening indentation.

    docutils measures the block from its least-indented line, so both lines
    below are content. Measuring from the first would end the block at the
    outdent and drop every statement under it, unexecuted and unreported.
    """
    text = ".. code-block:: python\n\n        first = 1\n    second = 2\n"
    assert literal_blocks(text) == [(3, "python", ["    first = 1", "second = 2"])]


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


def test_a_bare_marker_block_is_found():
    """``::`` ending a paragraph opens a block Sphinx highlights as python."""
    text = "At the prompt::\n\n    value = 1\n"
    assert implicit_blocks(text) == [3]


def test_a_marker_inside_a_block_body_is_not_a_block():
    """A ``text`` block may end a line in ``::``; that line is its content."""
    text = ".. code-block:: text\n\n    At the prompt::\n\n        value = 1\n"
    assert implicit_blocks(text) == []


def test_a_directive_is_not_a_bare_marker():
    """``.. note::`` ends in ``::`` and opens an admonition, not a block."""
    text = ".. note::\n\n    Prose inside the admonition.\n"
    assert implicit_blocks(text) == []


def test_a_marker_with_no_indented_body_is_not_a_block():
    """Nothing indented under it is a docutils error, not code to report."""
    text = "At the prompt::\n\nProse at column zero.\n"
    assert implicit_blocks(text) == []


def test_a_marker_with_no_blank_line_is_not_a_block():
    """Without the blank line docutils renders a definition, not code."""
    assert implicit_blocks("term::\n    The definition of the term.\n") == []
    assert implicit_blocks(":Some Field::\n    The field's body.\n") == []


def test_a_doctest_block_is_found():
    """A paragraph opening ``>>>`` is a console session, marker or not."""
    text = "Prose.\n\n>>> raise RuntimeError('boom')\n"
    assert doctest_blocks(text) == [3]


def test_a_prompt_under_prose_is_not_a_doctest_block():
    """The paragraph is the block; inside one the same text is content."""
    text = "Prose that runs on\n>>> and mentions the prompt.\n"
    assert doctest_blocks(text) == []


def test_a_prompt_inside_a_block_body_is_not_a_doctest_block():
    """A ``text`` block may quote a session; that line is its content."""
    text = ".. code-block:: text\n\n    >>> raise RuntimeError('boom')\n"
    assert doctest_blocks(text) == []


def test_the_console_lexer_alias_is_a_near_miss():
    """``python-console`` is Pygments' other name for ``pycon``."""
    text = ".. code-block:: python-console\n\n    >>> value = 1\n"
    assert python_blocks(text) == []
    assert literal_blocks(text)[0][1] in NEAR_MISS


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


def test_a_page_in_a_subdirectory_is_found(tmp_path):
    """A quadrant's pages are every page under it, not its top level only."""
    nested = []
    for quadrant in QUADRANTS:
        page = tmp_path / quadrant / "series" / "index.rst"
        page.parent.mkdir(parents=True)
        page.write_text("Prose.\n", encoding="utf-8")
        nested.append(page)
    assert user_pages(tmp_path) == nested


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


def test_no_user_page_is_written_in_a_format_this_gate_cannot_read():
    """The .rst boundary is a mechanism here rather than an argument elsewhere."""
    unread = sorted(
        str(path.relative_to(DOCS))
        for quadrant in QUADRANTS
        for suffix in UNREAD_SUFFIXES
        for path in (DOCS / quadrant).rglob(f"*{suffix}")
    )
    assert unread == [], (
        f"these user pages are in a format this gate does not read: {unread}. "
        "The user quadrants are reStructuredText (spec §8.6, plots spec §3.1), "
        "and the corpus is scoped to .rst for that reason (docs spec §3.9). A "
        "page in another format builds and publishes with nothing executing it"
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
    offenders: list[tuple[str, int, str]] = []
    for page in user_pages():
        text = page.read_text(encoding="utf-8")
        offenders.extend(
            (identify(page), line, language)
            for line, language, _ in literal_blocks(text)
            if language.lower() in NEAR_MISS or not language
        )
        offenders.extend((identify(page), line, "") for line in implicit_blocks(text))
        offenders.extend(
            (identify(page), line, PROMPT) for line in doctest_blocks(text)
        )
    assert offenders == [], (
        "these blocks do not name a language this gate executes, so they would "
        f"be passed over in silence: {offenders}. A block with no language is "
        "highlighted using Sphinx's `highlight_language` and can be python on "
        "the page, whether it is a directive that names none or a paragraph "
        "ending in `::`, and a paragraph opening `>>>` is a console session "
        "whatever the page says; write them all as `python` (docs spec §3.9)"
    )


def figure_pages() -> list[Path]:
    """Select the user pages that publish figures.

    Returns
    -------
    list of Path
        The pages carrying at least one ``.. plot::`` (plots spec §3.2).

    """
    return [
        page
        for page in user_pages()
        if plot_directives(page.read_text(encoding="utf-8"))
    ]


def test_the_figure_pages_are_recognised():
    """Every check below iterates these pages; unrecognised, they are unasked."""
    # Proven additive by mutation: `plot_directives` returning `[]` fails this
    # test and nothing else. Every other figure check then iterates an empty
    # corpus and passes having been asked nothing -- which is the silence this
    # test exists to break. `literal_blocks` reads `PLOT` separately, so the
    # python corpus is untouched and the snippet checks stay green.
    found = {identify(page) for page in figure_pages()}
    assert set(PUBLISHES_FIGURES) <= found, (
        "these pages publish figures and yielded no `.. plot::`: "
        f"{sorted(set(PUBLISHES_FIGURES) - found)}. Every page-shape check in "
        "this module would pass them in silence (plots spec §3.2)"
    )


def test_a_page_publishes_figures_or_it_does_not():
    """The two block forms never mix on one page (plots spec §3.2)."""
    offenders: list[tuple[str, int]] = []
    for page in figure_pages():
        text = page.read_text(encoding="utf-8")
        inside = block_lines(text)
        offenders.extend(
            (identify(page), number)
            for number, line in enumerate(text.splitlines(), start=1)
            if number not in inside
            and (match := DIRECTIVE.match(line)) is not None
            and match["language"].lower() == PYTHON
        )
    assert offenders == [], (
        "these pages publish figures and still carry a plain python block: "
        f"{offenders}. Such a block runs in this gate and not in the "
        "documentation build, so the build's namespace silently loses whatever "
        "it bound; give it `.. plot::` with `:nofigs:` if its picture would add "
        "nothing (plots spec §3.2)"
    )


def test_the_two_language_checks_compose():
    """Neither check covers the spellings alone, and nothing pinned that they do."""
    # Proven additive by mutation: dropping `python3` from `NEAR_MISS` fails this
    # test and nothing else. No page spells a language that way, so the page scan
    # of `test_no_block_hides_the_language_this_gate_runs` stays green -- which is
    # the point, the hole opening in the rule rather than in today's corpus.
    caught_by_mixing = [
        spelling for spelling in PYTHON_SPELLINGS if spelling.lower() == PYTHON
    ]
    caught_by_near_miss = [
        spelling for spelling in PYTHON_SPELLINGS if spelling.lower() in NEAR_MISS
    ]
    uncaught = sorted(
        set(PYTHON_SPELLINGS) - set(caught_by_mixing) - set(caught_by_near_miss)
    )
    assert uncaught == [], (
        f"these spellings mean python and no check reports them: {uncaught}. "
        "`test_a_page_publishes_figures_or_it_does_not` compares the language "
        "for equality with `PYTHON`, so every other spelling reaches "
        "`test_no_block_hides_the_language_this_gate_runs` through `NEAR_MISS` "
        "or reaches nothing at all (plots spec §3.2, docs spec §3.9)"
    )
    # The division of labour itself, which is the part that was undocumented:
    # the mixing check on a figure page sees exactly one spelling, and the other
    # seven are the near-miss check's alone. Tightening either -- narrowing the
    # equality, or dropping a member of `NEAR_MISS` -- opens a hole that the
    # `uncaught` assertion above then reports.
    assert caught_by_mixing == ["python"]
    assert len(caught_by_near_miss) == len(PYTHON_SPELLINGS) - 1


def test_the_first_plot_on_a_page_resets_the_context():
    """A page that opens without `reset` inherits the page built before it."""
    offenders: list[tuple[str, int, str]] = []
    for page in figure_pages():
        line, _, options = plot_directives(page.read_text(encoding="utf-8"))[0]
        if options.get("context") != "reset":
            offenders.append((identify(page), line, options.get("context", "")))
    assert offenders == [], (
        "these pages open with a plot that does not carry `:context: reset`: "
        f"{offenders}. Build order is not a property any page controls, so a "
        "page that builds only because of its neighbour breaks the moment "
        "someone rebuilds one file (plots spec §3.2)"
    )


def test_every_later_plot_continues_the_session():
    """A block with no `:context:` runs in a fresh namespace (plots spec §3.2)."""
    # Proven additive by mutation: dropping `:context:` from the second plot of
    # `howtos/framing.rst` fails this test and nothing else. The snippet gate
    # runs a page's blocks as one script whatever they declare, so the failure
    # this catches is invisible to `test_the_page_runs`.
    offenders: list[tuple[str, int]] = []
    for page in figure_pages():
        for line, _, options in plot_directives(page.read_text(encoding="utf-8"))[1:]:
            if options.get("context", None) not in ("", "close-figs"):
                offenders.append((identify(page), line))
    assert offenders == [], (
        "these plots neither continue the page's session nor open a figure of "
        f"their own: {offenders}. Each must carry `:context:` or `:context: "
        "close-figs` -- `reset` belongs to the first block alone, and a block "
        "with no `:context:` at all runs in a namespace where the page's "
        "imports never happened (plots spec §3.2)"
    )


def test_every_published_figure_is_named():
    """An unnamed image takes a counter, which renumbers on an insertion."""
    offenders: list[tuple[str, int]] = []
    for page in figure_pages():
        for line, _, options in plot_directives(page.read_text(encoding="utf-8")):
            if "nofigs" not in options and "filename-prefix" not in options:
                offenders.append((identify(page), line))
    assert offenders == [], (
        "these plots publish a figure under a per-document counter: "
        f"{offenders}. Inserting a section renumbers every image after it, and "
        "every baseline with it; give each one a `:filename-prefix:` "
        "(plots spec §3.2)"
    )


def test_a_suppressed_figure_is_not_also_named():
    """A name the build never produces is a baseline that can never match."""
    # Proven additive by mutation: adding `:nofigs:` to a plot that already
    # carries `:filename-prefix:` fails this test and nothing else. The
    # mutation has to run in that direction. Adding a *prefix* to a `:nofigs:`
    # plot declares a figure with no committed baseline, which fails
    # `test_docs_figures.py::test_every_committed_baseline_is_claimed_by_a_page`
    # as well and so proves nothing about this test alone.
    offenders: list[tuple[str, int]] = []
    for page in figure_pages():
        for line, _, options in plot_directives(page.read_text(encoding="utf-8")):
            if "nofigs" in options and "filename-prefix" in options:
                offenders.append((identify(page), line))
    assert offenders == [], (
        "these plots carry both `:nofigs:` and `:filename-prefix:`: "
        f"{offenders}. The name is a declaration that the figure gate then "
        "looks for, and Sphinx collects only the images a page references, so "
        "the pair can only ever fail as declared-but-not-built "
        "(plots spec §3.5)"
    )


def test_a_figure_name_is_unique_across_the_documentation():
    """Two sections sharing a prefix share one image, and one baseline."""
    seen: dict[str, tuple[str, int]] = {}
    collisions: list[tuple[str, str, str]] = []
    for page in figure_pages():
        for line, _, options in plot_directives(page.read_text(encoding="utf-8")):
            prefix = options.get("filename-prefix")
            if prefix is None:
                continue
            if prefix in seen:
                collisions.append(
                    (
                        prefix,
                        f"{seen[prefix][0]}:{seen[prefix][1]}",
                        f"{identify(page)}:{line}",
                    )
                )
            seen[prefix] = (identify(page), line)
    assert collisions == [], (
        f"these figure names are declared more than once: {collisions}. "
        "The images land in one flat directory, so a shared name is one image "
        "published under both sections (plots spec §3.2)"
    )


def test_no_plot_renders_from_a_file():
    """`.. plot:: script.py` puts the code a reader copies off the page."""
    # Proven additive by mutation: giving a plot a filename argument fails this
    # test and nothing else. `PLOT` captures the argument without disturbing the
    # body, so the block still runs and the page-shape checks around it stay
    # green -- the defect is in what the page declares, not in what it does.
    offenders: list[tuple[str, int, str]] = []
    for page in figure_pages():
        offenders.extend(
            (identify(page), line, argument)
            for line, argument, _ in plot_directives(page.read_text(encoding="utf-8"))
            if argument
        )
    assert offenders == [], (
        "these plots render from a file rather than from a block on the page: "
        f"{offenders}. The page's own snippet is the figure's source -- a "
        "figure built from a script beside the page is a second construction "
        "that agrees with the prose until someone edits one of them "
        "(plots spec §2)"
    )
