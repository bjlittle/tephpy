# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the citation cross-reference transform (docs spec §3.7)."""

from __future__ import annotations

import logging
from pathlib import Path
import types

import pytest

from tests.by_path import load_ext

REPO = Path(__file__).parents[1]
SRC = REPO / "docs" / "src"

# The transform imports Sphinx, which only the `docs` feature installs, so this
# module is unimportable in the `test-py3*` environments the CI matrix runs. It
# is importable in the default environment, which is what `pixi run tests`
# resolves to, so these run for anyone using the project's own test command.
pytest.importorskip("sphinx", reason="the docs feature is not installed here")

# The doctree the transform reads, from the same packages it reads it with. Neither
# is importable at the top of this module, for the reason the line above is not:
# both arrive with Sphinx.
addnodes = pytest.importorskip("sphinx.addnodes")
nodes = pytest.importorskip("docutils.nodes")
new_document = pytest.importorskip("docutils.utils").new_document

#: A citation that resolves, so that the transform converts it rather than passing
#: over it, and the tests below are about where it sits and not what it says.
CITED = "docs spec §3.7"
TITLED = f"Rendering and {CITED}"


cx = load_ext("tephpy_citation_xrefs")


def app(srcdir):
    """Return as much of a Sphinx application as the registry handler reads."""
    return types.SimpleNamespace(srcdir=srcdir)


def env(*docnames: str, fingerprint=None):
    """Return as much of a build environment as the outdated handler reads."""
    stub = types.SimpleNamespace(found_docs=set(docnames))
    if fingerprint is not None:
        setattr(stub, cx.ENV_FINGERPRINT, fingerprint)
    return stub


def outdated(environment, added=frozenset(), changed=frozenset()):
    """Call the handler the way Sphinx does, which is positionally."""
    return cx._outdated(None, environment, added, changed, frozenset())


def document(*children: nodes.Node):
    """Return as much of a parsed document as the transform reads."""
    doc = new_document("probe.md")
    doc.settings.env = types.SimpleNamespace(docname="probe")
    doc.extend(children)
    return doc


def rewrite(doc):
    """Run the transform over ``doc``, and return the anchors it linked."""
    cx.CitationTransform(doc).apply()
    return [xref["reftarget"] for xref in doc.findall(addnodes.pending_xref)]


class Registrar:
    """Record what ``setup`` asks of the application, which is all it does."""

    def __init__(self) -> None:
        self.connected = {}
        self.transforms = []

    def connect(self, event, handler):
        """Record an event handler."""
        self.connected[event] = handler

    def add_transform(self, transform):
        """Record a transform."""
        self.transforms.append(transform)


@pytest.fixture
def registry():
    """Restore the module globals, which building the registry mutates in place."""
    pattern, owners, fingerprint = cx.PATTERN, dict(cx.OWNERS), cx.FINGERPRINT
    yield
    cx.PATTERN = pattern
    cx.FINGERPRINT = fingerprint
    cx.OWNERS.clear()
    cx.OWNERS.update(owners)


@pytest.fixture
def warned():
    """Collect what the transform reports, without standing up a build to do it.

    Attached to the extension's own logger rather than read from ``caplog``, which
    reaches records through the root: Sphinx stops its namespace propagating there
    the moment any build in the process calls ``sphinx.util.logging.setup``.
    """
    reported = []

    class Collect(logging.Handler):
        """Keep the message, which is the whole of what the assertions read."""

        def emit(self, record):
            """Record one message."""
            reported.append(record.getMessage())

    logger = logging.getLogger(cx.logger.logger.name)
    handler = Collect()
    level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    yield reported
    logger.setLevel(level)
    logger.removeHandler(handler)


@pytest.mark.usefixtures("registry")
def test_a_citation_in_a_section_heading_is_reported(warned):
    """The one place a converted citation is not a link the reader can follow.

    The theme rebuilds its page navigation from the headings, keeping the text and
    dropping the anchor, so the reader is offered the citation as a link to the
    section it is written in. The rendered-citation gate of docs spec §3.7 counts
    an enclosing ``<a>`` and scores that linked, by a limitation it declares, so a
    heading citation reaches the reader unlinked with every gate green
    (:issue:`96`). It is converted all the same: the page renders as it did, and
    the build fails through ``--fail-on-warning`` where the citation is written.
    """
    cx._build_registry(app(SRC))
    heading = nodes.title("", "", nodes.Text(TITLED))
    doc = document(nodes.section("", heading, ids=["rendering"]))

    linked = rewrite(doc)

    assert linked == ["docs-spec-3-7"], "the heading stopped being converted"
    (message,) = warned
    # Naming the heading is not decoration. MyST gives a section title no usable
    # line number -- a document title is located as `index.md::` and a sub-heading
    # was mis-attributed four lines early -- so the location Sphinx prints beside
    # this message is not what an author would find the citation by.
    assert TITLED in message, "the warning does not say which heading it is about"


@pytest.mark.usefixtures("registry")
def test_a_citation_in_prose_is_not_reported(warned):
    """Where citations belong, and where every one in the corpus is today.

    A warning here would fail the whole docs build on the ordinary case, which is
    the failure mode of the fix rather than of the defect.
    """
    cx._build_registry(app(SRC))
    doc = document(nodes.paragraph("", "", nodes.Text(TITLED)))

    linked = rewrite(doc)

    assert linked == ["docs-spec-3-7"], "the fixture cites nothing this build links"
    assert warned == []


@pytest.mark.usefixtures("registry")
def test_a_citation_linked_by_hand_in_a_section_heading_is_reported(warned):
    """The same defect reached from the other side, where the skip set hides it.

    A citation inside link text is left plain, so that converting it cannot nest
    one anchor inside another. In a heading that skip used to take the warning
    with it, and the failure is unchanged: Sphinx builds the page navigation with
    docutils' ``ContentsFilter``, whose ``visit_reference`` and
    ``visit_pending_xref`` are both ``ignore_node_but_process_children``, so an
    author's own link is dropped there exactly as the transform's is. Reporting
    it is not conversion -- the citation must still reach the page as written.
    """
    cx._build_registry(app(SRC))
    linkage = nodes.reference("", CITED, refuri="https://example.com/spec")
    heading = nodes.title("", "", nodes.Text("Rendering and "), linkage)
    doc = document(nodes.section("", heading, ids=["rendering"]))

    linked = rewrite(doc)

    assert linked == [], "the citation was converted inside a link it already had"
    (message,) = warned
    assert "Rendering and " + CITED in message, "the warning names no heading"


@pytest.mark.usefixtures("registry")
def test_a_citation_quoted_as_a_literal_in_a_section_heading_is_not_reported(warned):
    """The lookalike the widened check must not catch, and the reason it does not.

    A literal is the one skip the page navigation keeps: ``ContentsFilter`` copies
    it through, so the citation renders as ``<code>`` in the heading and in the
    navigation alike, and the output gate exempts both as literal text. Nothing is
    lost, because nothing was ever offered -- the style guide quotes citations this
    way on purpose, and warning here would fail the build over an example.
    """
    cx._build_registry(app(SRC))
    heading = nodes.title(
        "", "", nodes.Text("Rendering and "), nodes.literal("", CITED)
    )
    doc = document(nodes.section("", heading, ids=["rendering"]))

    linked = rewrite(doc)

    assert linked == [], "a literal citation was converted"
    assert warned == []


@pytest.mark.usefixtures("registry")
def test_a_citation_linked_by_hand_in_prose_is_left_alone(warned):
    """Where the skip set earns its place, and where the widening must not reach.

    In body prose an author's link works: the reader follows it to whatever it
    names, and only the heading copy loses it. So this stays silent, and stays
    unconverted -- an anchor inside an anchor is invalid HTML that browsers
    restructure without saying so.
    """
    cx._build_registry(app(SRC))
    linkage = nodes.reference("", CITED, refuri="https://example.com/spec")
    doc = document(nodes.paragraph("", "", nodes.Text("Rendering and "), linkage))

    linked = rewrite(doc)

    assert linked == [], "the citation was converted inside a link it already had"
    assert warned == []


@pytest.mark.usefixtures("registry")
def test_a_citation_in_a_table_caption_is_not_reported(warned):
    """A ``title`` the theme does not copy anywhere, which is the whole test.

    The check is narrowed to a heading -- a ``title`` under a ``section`` -- and not
    written against ``title`` alone, which is also the caption of a table, a topic
    and an admonition. A citation in one of those is a link like any other, so
    widening the check to every ``title`` would fail the build over a link that
    works.
    """
    cx._build_registry(app(SRC))
    caption = nodes.title("", "", nodes.Text(TITLED))
    doc = document(nodes.table("", caption))

    linked = rewrite(doc)

    assert linked == ["docs-spec-3-7"], "the fixture cites nothing this build links"
    assert warned == []


@pytest.mark.usefixtures("registry")
def test_the_registry_is_built_from_the_specifications_on_disk():
    """Nothing declares the prefixes: the anchors in the tree are the registry."""
    cx._build_registry(app(SRC))

    assert cx.PATTERN is not None
    assert "developer/specs/2026-08-03-published-specs-design" in cx.OWNERS


@pytest.mark.usefixtures("registry")
def test_a_build_finding_no_anchors_clears_the_previous_registry(tmp_path):
    """Two builds share a process, and the second must not inherit the first.

    The handler runs on ``builder-inited``, so a registry left populated is one a
    later build reads as its own -- resolving that build's citations against a
    specification tree it never saw. Populating first is the point of the test:
    asserting on the cleared state alone would pass against a registry that was
    never filled.
    """
    cx._build_registry(app(SRC))
    assert cx.PATTERN is not None, "the fixture asserts nothing unless this holds"
    assert cx.OWNERS, "the fixture asserts nothing unless this holds"

    cx._build_registry(app(tmp_path))

    assert cx.PATTERN is None
    assert cx.OWNERS == {}


@pytest.mark.usefixtures("registry")
def test_the_fingerprint_follows_the_specifications_on_disk(tmp_path):
    """A registry the transform would read differently must digest differently."""
    specs = tmp_path / "developer" / "specs"
    specs.mkdir(parents=True)
    (specs / "parent.md").write_text("(spec-1)=\n\n## 1. Parent\n", encoding="utf-8")
    cx._build_registry(app(tmp_path))
    before = cx.FINGERPRINT

    (specs / "logo.md").write_text("(logo-spec-1)=\n\n## 1. Logo\n", encoding="utf-8")
    cx._build_registry(app(tmp_path))

    assert before != cx.FINGERPRINT, "adding a prefix left the registry looking equal"

    cx._build_registry(app(tmp_path))

    assert before != cx.FINGERPRINT, "the digest must depend on the tree, not the call"


@pytest.mark.usefixtures("registry")
def test_an_unchanged_registry_re_reads_nothing(tmp_path):
    """The digest is compared so that the ordinary edit stays incremental.

    A handler that invalidated unconditionally would be correct and useless: every
    build would re-read every document, which is the cost the cache exists to
    avoid.
    """
    cx._build_registry(app(tmp_path))

    unchanged = env("index", "guide", fingerprint=cx.FINGERPRINT)

    assert outdated(unchanged) == set()


@pytest.mark.usefixtures("registry")
def test_a_changed_registry_re_reads_the_documents_sphinx_would_not(tmp_path):
    """Which is the defect: the registry is a hidden input to every doctree.

    The transform bakes its answers into the pickled doctree, so a page nobody
    edited keeps the anchor the *previous* registry named. Sphinx re-reads it only
    if told to, and nothing else notices -- the page is not rewritten, so the
    reference is never resolved again and ``refwarn`` cannot fire.
    """
    cx._build_registry(app(tmp_path))
    stale = env("index", "guide", "prose", fingerprint="the previous build's digest")

    assert outdated(stale) == {"index", "guide", "prose"}
    assert getattr(stale, cx.ENV_FINGERPRINT) == cx.FINGERPRINT


@pytest.mark.usefixtures("registry")
def test_a_first_build_re_reads_nothing_extra(tmp_path):
    """An environment with no digest is a cold cache, where every document is new.

    Sphinx has already listed them as added, so naming them again would be noise;
    the handler still records the digest, which is what makes the *next* build able
    to tell that this one happened.
    """
    cx._build_registry(app(tmp_path))
    cold = env("index", "guide")

    assert outdated(cold, added={"index", "guide"}) == set()
    assert getattr(cold, cx.ENV_FINGERPRINT) == cx.FINGERPRINT


def test_setup_registers_every_handler_the_transform_relies_on():
    """Which nothing else here covers: the rest call the functions directly.

    A build that stopped connecting one of them would pass every other test in
    this module. ``env-get-outdated`` is the one worth naming: without it the
    registry goes back to being a hidden input to every cached doctree, which is
    the defect it was written for.
    """
    registrar = Registrar()

    metadata = cx.setup(registrar)

    assert registrar.connected["builder-inited"] is cx._build_registry
    assert registrar.connected["env-get-outdated"] is cx._outdated
    assert registrar.transforms == [cx.CitationTransform]
    # Sphinx reads a pickled environment back whatever wrote it, so storing on it
    # without declaring a version is how an older shape is read as this one's.
    assert metadata["env_version"]
