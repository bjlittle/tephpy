# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the reading-time directive and its transform (reading spec §6)."""

from __future__ import annotations

import pytest

from tests.by_path import load_ext

# The directive imports Sphinx, which only the `docs` feature installs, so this
# module is unimportable in the `test-py3*` environments the CI matrix runs. It is
# importable in the default environment, which is what `pixi run tests` resolves
# to, so these run for anyone using the project's own test command. The stdlib
# half lives in `tests/test_docs_readingtime.py`, which must not carry this guard.
pytest.importorskip("sphinx", reason="the docs feature is not installed here")
nodes = pytest.importorskip("docutils.nodes")
utils = pytest.importorskip("docutils.utils")
new_document = utils.new_document
frontend = pytest.importorskip("docutils.frontend")
parsers = pytest.importorskip("docutils.parsers.rst")
core = pytest.importorskip("docutils.core")


reading = load_ext("tephpy_reading")
readingtime = load_ext("tephpy_readingtime")

# Registered once, in the plain docutils registry, so `_publish` can drive
# `ReadingTimeDirective.run()` the way an actual `.. readingtime::` in an `.rst`
# page does -- rather than only ever constructing its output node by hand, which
# would leave `run()` itself, and its argument handling, entirely unexercised.
parsers.directives.register_directive("readingtime", readingtime.ReadingTimeDirective)


class _FakeEnv:
    """As much of a Sphinx ``BuildEnvironment`` as ``run()`` reaches for."""

    def note_dependency(self, filename):
        """No-op: what gets tracked is Task 3's business, not this test's."""


def _publish(source: str) -> nodes.document:
    """Parse ``source`` with the real RST parser, ``readingtime`` registered.

    A ``docutils.utils.SystemMessage`` is raised, rather than merely logged, for
    any diagnostic at ``WARNING`` or above -- which is what turns
    ``ReadingTimeDirective.run()`` raising on a bad argument into something a
    test can assert with :func:`pytest.raises`.
    """
    settings_overrides = {"env": _FakeEnv(), "halt_level": 2, "report_level": 5}
    return core.publish_doctree(source, settings_overrides=settings_overrides)


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
    """A malformed directive's diagnostic must not inflate the count.

    ``self.error()`` puts its message in the doctree as a ``system_message``
    (reading spec §3.2), so if it were not in :data:`readingtime.SKIP` a bad
    argument would add its own error text -- roughly twenty words here -- to
    the very estimate it failed to produce.
    """
    raw = nodes.raw("", "<i class='fa-solid fa-clock'></i>", format="html")
    message = nodes.system_message(
        "readingtime: expected no argument, a duration in minutes such as "
        "'30', or a rate such as '200wpm'; got 'thirty'",
        level=3,
        type="ERROR",
        source="<test>",
        line=1,
    )
    doctree = _doctree(_para("one two"), raw, message)
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


def test_run_returns_a_placeholder_carrying_the_parsed_argument():
    """Drives ``ReadingTimeDirective.run()`` itself, not just its output node."""
    doctree = _publish(".. readingtime:: 200wpm\n")
    node = next(doctree.findall(readingtime.readingtime))
    assert node["minutes"] is None
    assert node["wpm"] == 200


def test_run_raises_rather_than_silently_estimating_on_a_bad_argument():
    """Reading spec §3.2: a mistyped argument must fail, not estimate.

    The prior art's silent fallback -- computing an estimate anyway, so a
    typo publishes a number nobody asked for -- is the defect this guards
    against.
    """
    with pytest.raises(utils.SystemMessage):
        _publish(".. readingtime:: thirty\n")


def test_the_handler_replaces_the_placeholder_with_a_banner():
    placeholder = readingtime.readingtime(minutes=None, wpm=reading.WPM)
    doctree = _doctree(placeholder, _para(" ".join(["word"] * 300)))
    readingtime.resolve(None, doctree)
    assert not list(doctree.findall(readingtime.readingtime))
    banner = next(doctree.findall(nodes.container))
    assert "reading-time" in banner["classes"]
    assert "2 minutes" in banner.astext()


def test_two_placeholders_on_one_page_share_one_word_count():
    """The count is a property of the page, taken once (reading spec §3.3).

    If it were instead recomputed once per placeholder, inside the loop, the
    second placeholder's count would include the first placeholder's own
    banner text -- counting the estimate as part of what it is estimating.
    """
    first = readingtime.readingtime(minutes=None, wpm=reading.WPM)
    second = readingtime.readingtime(minutes=None, wpm=reading.WPM)
    doctree = _doctree(first, _para(" ".join(["word"] * 300)), second)
    readingtime.resolve(None, doctree)
    banners = list(doctree.findall(nodes.container))
    assert len(banners) == 2
    assert all("2 minutes" in banner.astext() for banner in banners)


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
    assert metadata["parallel_write_safe"] is True
