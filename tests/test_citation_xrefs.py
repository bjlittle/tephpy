# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the citation cross-reference transform (docs spec §3.7)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import pytest

REPO = Path(__file__).parents[1]
SRC = REPO / "docs" / "src"
EXT = SRC / "_ext"

# The transform imports Sphinx, which only the `docs` feature installs, so this
# module is unimportable in the `test-py3*` environments the CI matrix runs. It
# is importable in the default environment, which is what `pixi run tests`
# resolves to, so these run for anyone using the project's own test command.
pytest.importorskip("sphinx", reason="the docs feature is not installed here")

# `_ext` is a `sys.path` entry at build time rather than a package, so the module
# resolves its sibling `citations` by top-level name and cannot be imported until
# that entry exists.
if str(EXT) not in sys.path:
    sys.path.insert(0, str(EXT))


def _load():
    """Import the transform by path; ``_ext`` is not an importable package."""
    path = EXT / "citation_xrefs.py"
    assert path.is_file(), f"the citation transform is missing from {path}"
    spec = importlib.util.spec_from_file_location("citation_xrefs", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cx = _load()


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
