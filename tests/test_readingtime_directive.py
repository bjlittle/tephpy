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


def _doctree(*children: nodes.Node):
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
    """Reading spec §6.

    A section carries its title as a child, and the document carries the
    section -- a walk that counted both would double every heading.
    """
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
    """Reading spec §3.2: the escape hatch quotes, it does not estimate."""
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


def test_setup_registers_the_directive_and_the_transform_but_not_the_node():
    """Reading spec §3.2: a leaked placeholder must fail the build, not publish blank.

    Asserted against what ``setup`` *does*, not against the source text. The
    class docstring says ``app.add_node`` in prose to explain why it is absent,
    so a grep for that name matches the explanation and passes for the wrong
    reason -- and would keep passing if somebody added the real call.
    """
    calls = []

    class FakeApp:
        """As much of the application as ``setup`` reaches for."""

        def add_directive(self, name, cls):  # noqa: ARG002
            calls.append(("add_directive", name))

        def connect(self, event, handler):  # noqa: ARG002
            calls.append(("connect", event))

        def add_node(self, *args, **kwargs):  # noqa: ANN002, ARG002
            calls.append(("add_node", args))

    metadata = readingtime.setup(FakeApp())

    assert ("add_directive", "readingtime") in calls
    assert ("connect", "doctree-read") in calls
    assert not any(call[0] == "add_node" for call in calls), (
        "the placeholder must stay unregistered: an unknown node type is what "
        "fails the build if the transform ever stops firing"
    )
    assert metadata["parallel_read_safe"] is True
