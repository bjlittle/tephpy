# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The tests tree held against the package it mirrors (spec §8.5).

`tests/` reproduces the `src/tephpy` layout: tests for top-level modules at the
`tests/` root, and each subpackage a matching directory. That rule was stated in
three places and enforced in none, so it drifted. `tephpy.samples` arrived in
:pull:`181` with its tests at the root; the examples-gallery plan wrote that
placement down as though it were the rule; and the audit in :pull:`233` found
`tests/AGENTS.md` claiming the directory rule while the tree disobeyed it, then
resolved the disagreement towards the tree. Spec §8.5 had said "each subpackage
gets a matching directory" throughout, and the spec is the authority a plan
records against, so the tree moved instead (:issue:`234`).

What made that possible is that no test could tell. A rule only prose asserts is
a rule the next subpackage silently breaks, and the breakage surfaces whenever
somebody happens to audit -- nine days later, here. So the mapping is asserted:
every subpackage has a directory, every directory has a subpackage, and each one
is a package rather than a bare directory of modules.
"""

from __future__ import annotations

from pathlib import Path

import pytest

#: The repository root, from `tests/test_layout.py`.
REPO = Path(__file__).parents[1]

#: The package the tests tree mirrors.
SOURCE = REPO / "src" / "tephpy"

#: The tests tree itself.
TESTS = Path(__file__).parent

#: Directories under `tests/` that mirror nothing, because they hold shared
#: assets rather than tests (spec §8.5). Named rather than inferred: a directory
#: is excused from the mapping by being one of these, not by the accident of
#: holding no test module today.
SHARED = {"baseline", "fixtures"}

#: Prefixes of the directories nobody wrote -- `__pycache__`, and the dot
#: directories pytest, coverage and hypothesis leave behind. Excluded by prefix
#: rather than by name because which tools drop one here is not ours to
#: enumerate, and a cache is not a claim about the tree's shape.
GENERATED = (".", "__")

#: The subpackages of `tephpy`, as the scan below should find them. Declared so
#: that a scan which broke fails here rather than passing over an empty set --
#: every mapping test below is satisfied vacuously by finding nothing.
SUBPACKAGES = {"examples", "io", "plotting", "samples"}


def subpackages():
    """Report the subpackages of `tephpy`, by name."""
    return {path.name for path in SOURCE.iterdir() if (path / "__init__.py").is_file()}


def mirrors():
    """Collect the directories under `tests/` that claim to mirror a subpackage.

    Every directory takes part except the shared ones and the caches. Asking
    also for a `test_*.py` beside them would be the inference `SHARED` exists
    to avoid, and would excuse the three shapes worth catching: a directory
    holding nothing, one holding only nested tests, and one whose subpackage
    was deleted out from under it. Each is a defect this module reports, and a
    scan reading their contents could report none of them.
    """
    return {
        path.name
        for path in TESTS.iterdir()
        if path.is_dir()
        and not path.name.startswith(GENERATED)
        and path.name not in SHARED
    }


def test_the_scan_finds_the_declared_subpackages():
    """A broken scan fails here, not by making the mapping vacuously true."""
    assert subpackages() == SUBPACKAGES, (
        "the subpackages found under src/tephpy are not the declared ones; "
        "add the new subpackage to SUBPACKAGES, with the tests/ directory "
        "spec §8.5 asks of it"
    )


@pytest.mark.parametrize("name", sorted(SUBPACKAGES))
def test_every_subpackage_has_a_test_directory(name):
    """`tephpy.<name>` is tested from `tests/<name>/` (spec §8.5)."""
    assert (TESTS / name).is_dir(), (
        f"tephpy.{name} has no tests/{name}/ directory; the tests tree mirrors "
        "the package, so its tests belong there rather than at the tests root"
    )


@pytest.mark.parametrize("name", sorted(mirrors()))
def test_every_test_directory_mirrors_a_subpackage(name):
    """Nothing under `tests/` mirrors a subpackage that is not there."""
    assert name in subpackages(), (
        f"tests/{name}/ mirrors no subpackage; either tephpy.{name} was removed "
        f"and its tests outlived it, or tests/{name}/ holds shared assets and "
        "belongs in SHARED"
    )


@pytest.mark.parametrize("name", sorted(mirrors()))
def test_every_mirror_is_a_package(name):
    """The tests tree is a package all the way down (:issue:`185`)."""
    assert (TESTS / name / "__init__.py").is_file(), (
        f"tests/{name}/ has no __init__.py; the tests tree is a package and "
        "the sibling imports through it depend on every level being one"
    )
