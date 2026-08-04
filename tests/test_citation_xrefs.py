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


@pytest.fixture
def registry():
    """Restore the module globals, which building the registry mutates in place."""
    pattern, owners = cx.PATTERN, dict(cx.OWNERS)
    yield
    cx.PATTERN = pattern
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
