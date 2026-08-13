# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the dependency floor generator (floors spec §5)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import textwrap

from packaging.version import Version
import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "floors.py"

# `MANIFEST.in` prunes `.github`, so an sdist ships these tests without the
# generator they exercise. Guarding the module rather than the test is deliberate:
# an unguarded import fails *collection* there, taking the rest of the suite with
# it (floors spec §5).
pytestmark = pytest.mark.skipif(
    not (SCRIPT.is_file() and (REPO / ".git").exists()),
    reason="not a git checkout of the repository",
)


def _load():
    """Import the generator by path; ``.github`` is not an importable package."""
    spec = importlib.util.spec_from_file_location("floors", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MANIFEST = textwrap.dedent(
    """\
    [tool.pixi.dependencies]
    click = ">=8.1"

    [tool.pixi.feature.test.dependencies]
    pytest = ">=8.0"

    [tool.pixi.feature.docs.dependencies]
    sphinx = ">=8.0"

    [tool.pixi.feature.devs.dependencies]
    ruff = ">=0.15"
    """
)


def _manifest(tmp_path, text=MANIFEST):
    path = tmp_path / "pyproject.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _lookup(package, specifier, python):  # noqa: ARG001
    """Stand in for the channel: the floor plus two releases above it."""
    base = specifier.removeprefix(">=")
    return [f"{base}.0", f"{base}.1", f"{base}.2"]


def test_a_specifier_that_is_not_a_bare_floor_is_reported(tmp_path):
    # A range floors a version the generator cannot name, and one that quietly
    # converted most of a tier would make the run a weaker claim than it looks.
    floors = _load()
    text = MANIFEST.replace('click = ">=8.1"', 'click = ">=8.1,<9"')
    with pytest.raises(floors.FloorError, match="not a bare"):
        floors.pins(_manifest(tmp_path, text), Version("3.12.0"), lookup=_lookup)


def test_a_tier_that_converts_nothing_fails(tmp_path):
    # A table emptied or renamed would otherwise exit 0 having pinned nothing, and
    # a green run that checked nothing reads exactly like one that checked all.
    floors = _load()
    text = MANIFEST.replace('sphinx = ">=8.0"', "")
    with pytest.raises(floors.FloorError, match="docs: no floors converted"):
        floors.pins(_manifest(tmp_path, text), Version("3.12.0"), lookup=_lookup)


def test_a_floor_with_no_build_for_the_python_fails(tmp_path):
    # An empty candidate list means the pin would be unsolvable, so the run must
    # fail on the declaration rather than later on the generator's arithmetic.
    floors = _load()
    with pytest.raises(floors.FloorError, match="no build for Python"):
        floors.pins(
            _manifest(tmp_path),
            Version("3.12.0"),
            lookup=lambda package, specifier, python: [],  # noqa: ARG005
        )
