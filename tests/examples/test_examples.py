# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The gallery examples and the registry over them (gallery spec §3.7)."""

from __future__ import annotations

import ast
from importlib import import_module
from pathlib import Path
import re

import matplotlib.pyplot as plt
import pytest

from tephpy import examples
from tephpy.examples import REGISTRY
from tests.by_path import load_ext

#: The taxonomy of topics spec §3.5. The vocabulary and the flag pattern moved
#: there when the site-wide topic index started reading the same two things: a
#: second copy would agree until one was widened. Loaded by path because
#: `docs/src/_ext` is a `sys.path` entry at build time and not a package
#: (:issue:`92`), and imported here with no `importorskip` guard, because this
#: module holds nothing outside the standard library and these assertions run on
#: every supported Python.
topics = load_ext("tephpy_topics_data")

#: sphinx-gallery's own in-file flag pattern, transcribed from
#: ``py_source_parser.INFILE_CONFIG_PATTERN`` (0.21.0) -- what
#: ``remove_config_comments`` strips from the code a gallery page shows.
#: Transcribed for the reason ``topics.GALLERY_TAGS`` is read from text at all:
#: sphinx-gallery is absent from the ``test-py3*`` environments the CI matrix
#: runs, so a test that imported it to borrow the pattern would skip exactly
#: where it matters. Unlike ``topics.GALLERY_TAGS`` this matches every
#: ``sphinx_gallery_*`` flag and an indented one, because those are stripped too
#: and leave the same gap behind.
_FLAGS = re.compile(
    r"^[ \t]*#\s*sphinx_gallery_([A-Za-z0-9_]+)(\s*=\s*(.+))?[ \t]*\n?",
    re.MULTILINE,
)

#: The blank lines PEP 8 puts before a module-level ``def``, and so the number
#: the published example should show once the flags are gone.
BLANK_LINES = 2

#: The guard of gallery spec §3.3, as ``ast.unparse`` renders its test. The
#: module-level ``if TYPE_CHECKING:`` block is also an ``ast.If``, so the
#: comparison has to be against the test rather than against the node kind.
_GUARD = "__name__ == '__main__'"

#: What the guard calls, in order (gallery spec §3.3). Asserting the calls and
#: not merely the guard is the point: a guard that ran something else, or
#: nothing, would draw no figure for sphinx-gallery to scrape, and the page
#: would publish the ``no_image.png`` placeholder without a warning to fail
#: ``--fail-on-warning`` on.
GUARD_CALLS = ["main", "plt.show"]

#: The figure size of gallery spec §3.5, inherited from plots spec §3.1.
FIGSIZE = (8.0, 4.0)

EXAMPLES = Path(examples.__file__).parent


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


def read_guard(source: str) -> list[str]:
    """Return the calls an example's ``__main__`` guard makes, in order.

    Parameters
    ----------
    source : str
        The example module's text.

    Returns
    -------
    list of str
        The dotted name of each call in the guard's body, empty when the
        module declares no guard at all.
    """
    for node in ast.parse(source).body:
        if not isinstance(node, ast.If) or ast.unparse(node.test) != _GUARD:
            continue
        return [
            ast.unparse(statement.value.func)
            for statement in node.body
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
        ]
    return []


#: The paragraph sphinx-gallery lifts into a thumbnail's ``tooltip=`` attribute,
#: transcribed from ``gen_rst.extract_intro_and_title`` (0.21.0): the docstring
#: split on blank lines, directives dropped, the title taken first and the intro
#: being the paragraph after it. Transcribed rather than imported for the reason
#: ``_FLAGS`` is, and read the same way sphinx-gallery reads it -- newlines
#: joined to spaces before anything looks at the text.
def read_intro(source: str) -> str:
    """Return the paragraph sphinx-gallery renders as the thumbnail tooltip.

    Parameters
    ----------
    source : str
        The example module's text.

    Returns
    -------
    str
        The intro paragraph on one line, or the title where there is no other
        paragraph -- which is the fallback sphinx-gallery itself makes.
    """
    docstring = ast.get_docstring(ast.parse(source), clean=False) or ""
    paragraphs = [
        paragraph
        for paragraph in docstring.lstrip().split("\n\n")
        if paragraph and not paragraph.startswith(".. ")
    ]
    intro = paragraphs[0] if len(paragraphs) < 2 else paragraphs[1]
    return intro.replace("\n", " ")


#: A cross-reference role written with an explicit title, ``:term:`title
#: <target>```. sphinx-gallery's ``_sanitize_rst`` mangles exactly this form in
#: the intro paragraph, in three different ways. Where the title is a single word
#: it publishes the *target* instead of the title; where the title is two or more
#: words it publishes the raw ``<target>`` markup at the reader, because the rule
#: that would have handled it needs a single-word title and the rule catching the
#: remainder keeps its content verbatim; and where the role is domain-qualified it
#: publishes a fragment of the role itself, ``:py:class:`Sounding <...>``` leaving
#: ``:pySounding`` (:issue:`253`, sphinx-gallery/sphinx-gallery#1644).
#:
#: The role name is docutils' own grammar for one, ``Inliner.simplename``
#: transcribed from ``docutils/parsers/rst/states.py`` (0.22.4). Narrowing it by
#: hand is what a guard like this must not do: an earlier ``:[a-z0-9+_-]+:`` here
#: missed ``:TERM:`profile <sounding>``` and ``:my.role:`title <target>```, both
#: of which Sphinx accepts and renders as ordinary links -- measured, they build
#: clean under ``--fail-on-warning`` -- and both of which the sanitiser mangles.
#: A guard narrower than the grammar it guards is a guard with a hole in the
#: shape of whatever its author did not think of.
#:
#: Transcribed rather than imported for the reason ``topics.GALLERY_TAGS`` and
#: ``_FLAGS`` are:
#: docutils is absent from the ``test-py3*`` environments the CI matrix runs, so
#: an importing test would skip exactly where it matters.
_SIMPLENAME = r"(?:(?!_)\w)+(?:[-._+:](?:(?!_)\w)+)*"

#: The bare and ``~`` forms are unaffected by any of this, which is why the
#: pattern requires the ``<``.
_TITLED_ROLE = re.compile(rf":{_SIMPLENAME}:`[^`<>]+<[^`<>]+>`")


@pytest.mark.parametrize("module", [module for _, module in REGISTRY])
def test_example_runs(module):
    """Every registered example builds a figure, at the gallery's size.

    A broken example then fails the test suite across the supported
    Pythons, not only the documentation build. The size is the example's
    own because sphinx-gallery calls ``plt.rcdefaults()`` before each one,
    so nothing outside the file can hold it (gallery spec §3.5).
    """
    figure = import_module(f"tephpy.examples.{module}").main()
    assert figure.axes
    assert tuple(figure.get_size_inches()) == FIGSIZE
    plt.close(figure)


@pytest.mark.parametrize("module", [module for _, module in REGISTRY])
def test_example_guard_draws(module):
    """Every example closes with the guard, calling ``main`` then ``show``.

    Nothing else catches its loss. The suite calls ``main()`` directly, and
    sphinx-gallery executing a file whose guard has gone finds no figure
    and publishes the page with a placeholder image — a supported case it
    emits no warning for, so ``--fail-on-warning`` cannot see it either
    (gallery spec §3.3).
    """
    guard = read_guard((EXAMPLES / f"{module}.py").read_text())
    assert guard == GUARD_CALLS, f"{module} guard calls {guard}"


def test_registry_covers_the_directory():
    """Every ``plot_*.py`` is registered, and every registration exists."""
    found = {path.stem for path in EXAMPLES.glob("plot_*.py")}
    assert found == {module for _, module in REGISTRY}


def test_registry_names_drop_the_prefix():
    """The command-line name is the module's, without ``plot_``."""
    assert all(module == f"plot_{name.replace('-', '_')}" for name, module in REGISTRY)


@pytest.mark.parametrize("module", [module for _, module in REGISTRY])
def test_example_tags_are_declared_and_in_vocabulary(module):
    """Each example declares two to four tags, all from the vocabulary.

    An empty list is the failure a misspelled flag produces: sphinx-gallery
    parses ``sphinx_gallery_tag`` into a differently-keyed entry and
    discards it without a warning, so the documentation build cannot report
    it. Two to four is gallery spec §3.6's own bound: one tag files an
    example under a single button, and a full house of them files it under
    every one, either way telling the index's filter nothing.
    """
    tags = read_tags((EXAMPLES / f"{module}.py").read_text())
    assert tags, f"{module} declares no sphinx_gallery_tags"
    assert topics.MIN_TAGS <= len(tags) <= topics.MAX_TAGS, (
        f"{module} declares {len(tags)} tags: {tags}"
    )
    assert set(tags) <= topics.VOCABULARY, sorted(set(tags) - topics.VOCABULARY)


@pytest.mark.parametrize("module", [module for _, module in REGISTRY])
def test_stripping_the_flags_leaves_the_spacing_pep8_wrote(module):
    """The published example shows two blank lines before ``def main``.

    ``remove_config_comments`` strips the ``# sphinx_gallery_*`` lines and
    preserves the blank lines around them (gallery spec §3.6), so a flag
    written with a blank line above it leaves that line on the page: three
    before ``def main`` where PEP 8 wrote two. This reproduces the removal
    and reads the result, rather than asserting where the flag sits --
    that would be a proxy, and one that a second flag, or an indented one,
    could satisfy while the gap came back. Nothing else catches it: a
    blank line raises no Sphinx warning for ``--fail-on-warning``, and the
    removal is silent by design.
    """
    source = (EXAMPLES / f"{module}.py").read_text()
    assert _FLAGS.search(source), f"{module} declares no sphinx_gallery flag"
    rendered = _FLAGS.sub("", source)
    match = re.search(r"\n(\n*)def main", rendered)
    assert match, f"{module} has no module-level `def main` to space away from"
    blanks = len(match.group(1))
    assert blanks == BLANK_LINES, (
        f"{module} would publish {blanks} blank lines before `def main`, not "
        f"{BLANK_LINES}: a flag goes flush under the line above it, so that "
        "stripping it from the page leaves the spacing PEP 8 wrote"
    )


def test_the_tephigram_example_restates_the_default_extent():
    """``plot_tephigram`` frames the diagram exactly as the default does.

    The example writes the corners out literally, because showing
    ``set_extent`` is half of what it is for (gallery spec §4). That makes
    them a second copy of ``DEFAULT_EXTENT``, and a change to that default
    would otherwise leave the example framing the diagram the old way while
    the gallery page claims it shows the default.
    """
    figure = import_module("tephpy.examples.plot_tephigram").main()
    default, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    try:
        assert figure.axes[0].viewLim.bounds == ax.viewLim.bounds
    finally:
        plt.close(figure)
        plt.close(default)


@pytest.mark.mpl_image_compare
def test_parcel_analysis_figure():
    """Pin spec §4's composed figure, which spec §7 has always required."""
    return import_module("tephpy.examples.plot_parcel_analysis").main()


@pytest.mark.parametrize("name", [name for name, _ in REGISTRY])
def test_no_intro_paragraph_writes_a_role_with_an_explicit_title(name):
    """The thumbnail tooltip is plain text, so its paragraph writes plain roles.

    sphinx-gallery strips the intro paragraph with regular expressions rather
    than by parsing it, and an explicit-title role survives that as either the
    wrong words or as raw markup (:issue:`253`). The rule is scoped to the intro
    paragraph because that is the only part lifted into the attribute: the rest
    of the docstring is rendered by Sphinx, where the same form is correct and
    used.
    """
    source = (EXAMPLES / f"plot_{name.replace('-', '_')}.py").read_text(
        encoding="utf-8"
    )
    intro = read_intro(source)
    found = _TITLED_ROLE.findall(intro)
    assert not found, (
        f"{name}: the thumbnail tooltip is built from this paragraph by pattern, "
        f"and these reach the reader mangled: {found}. Write the bare role."
    )


@pytest.mark.parametrize(
    "text",
    [
        "a :term:`wind barbs <wind barb>` role",
        "a :py:class:`Sounding <tephpy.sounding.Sounding>` role",
        "a :std:doc:`the guide <howtos/index>` role",
        "a :TERM:`profile <sounding>` role",
        "a :my.role:`title <target>` role",
    ],
)
def test_the_titled_role_pattern_reads_the_whole_role(text):
    """A domain-qualified role is caught, and reported whole.

    ``:[a-z]+:`` detects one anyway by matching from its inner part, so the
    weaker pattern would pass this file's other test while naming ``:class:``
    where the source says ``:py:class:``. Asserting the *reported* text is what
    tells the two apart.
    """
    found = _TITLED_ROLE.findall(text)
    assert found, f"no explicit-title role found in {text!r}"
    assert found[0] in text
    assert text.startswith(f"a {found[0]} role")


@pytest.mark.parametrize(
    "text",
    ["a :term:`dewpoint` role", "a :class:`~tephpy.sounding.Sounding` role"],
)
def test_the_titled_role_pattern_leaves_the_bare_forms_alone(text):
    """The bare and ``~`` forms sanitise correctly, so they are not the defect."""
    assert not _TITLED_ROLE.findall(text)
