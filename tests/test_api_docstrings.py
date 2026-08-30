# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The published API docstring gate (:issue:`227`).

The gate's own definition of "the public API" is the thing under test here.
It reproduces sphinx-autoapi's selection without a build, so it can run in
pre-commit; ``tests/test_docs_api_inventory.py`` is what earns that shortcut
by pinning the result against a real build's ``objects.inv``.

The cases below pin the parts of that selection a reader cannot guess from
the module layout: that a private module's singleton contributes published
methods, and that a dataclass field does not.
"""

from __future__ import annotations

import pytest


def test_published_objects_covers_the_documented_modules(gate):
    """The 15 module pages autoapi builds, and no private module."""
    names = {entry.name for entry in gate.published_objects() if entry.role == "module"}
    assert names == {
        "tephpy",
        "tephpy.calc",
        "tephpy.exceptions",
        "tephpy.io",
        "tephpy.io.igra",
        "tephpy.io.wyoming",
        "tephpy.plotting",
        "tephpy.plotting.axes",
        "tephpy.plotting.barbs",
        "tephpy.plotting.isopleths",
        "tephpy.plotting.logo",
        "tephpy.plotting.shading",
        "tephpy.samples",
        "tephpy.sounding",
        "tephpy.transforms",
    }


def test_published_objects_reaches_the_config_singleton(gate):
    """``tephpy.config`` is a private-module instance with published methods.

    ``tephpy._config`` has no API page, but the singleton is reachable from
    ``tephpy``, so autoapi documents ``tephpy.config.load`` and its
    neighbours. An enumerator built from the module list alone would miss
    every one of them.
    """
    names = {entry.name for entry in gate.published_objects()}
    assert "tephpy.config.load" in names
    assert "tephpy.config.reset" in names
    assert not any(name.startswith("tephpy._config") for name in names)


def test_published_objects_excludes_attributes_and_data(gate):
    """A dataclass field carries no docstring, so there is nothing to stamp."""
    names = {entry.name for entry in gate.published_objects()}
    assert "tephpy.calc.Profile" in names
    assert "tephpy.calc.Profile.lcl_pressure" not in names
    assert "tephpy.plotting.isopleths.EDGES" not in names


def test_published_objects_excludes_private_and_examples(gate):
    """The gallery is not API, and neither is anything underscored."""
    names = {entry.name for entry in gate.published_objects()}
    assert not any(".examples" in name for name in names)
    assert not any(part.startswith("_") for name in names for part in name.split("."))


def test_target_version_is_the_base_of_the_scm_version(gate, monkeypatch):
    """The next tag's version, with the development suffix removed."""
    monkeypatch.setattr(gate, "_scm_version", lambda: "0.2.0.dev3")
    assert gate.target_version() == "0.2.0"


@pytest.mark.parametrize(
    ("reported", "expected"),
    [
        ("0.1.0.dev149+dirty", "0.1.0"),  # no tags yet, working tree dirty
        ("0.2.0.dev3", "0.2.0"),  # mid-cycle, after v0.1.0
        ("0.2.0", "0.2.0"),  # exactly on a tag
        ("0.3.0.dev1+g36dd91c", "0.3.0"),  # a node-id local segment
    ],
)
def test_target_version_strips_dev_and_local_segments(
    gate, monkeypatch, reported, expected
):
    monkeypatch.setattr(gate, "_scm_version", lambda: reported)
    assert gate.target_version() == expected


def test_target_version_refuses_a_shallow_checkout(gate, monkeypatch):
    """A shallow clone derives the wrong target, so refuse rather than guess.

    Without tags ``setuptools_scm`` falls back to the first release, so once
    ``v0.1.0`` exists a shallow checkout derives ``0.1.0`` where the answer is
    ``0.2.0`` -- and comparing against a wrong-low target turns correctly
    stamped symbols into failures (:issue:`227`).
    """
    monkeypatch.setattr(gate, "_is_shallow", lambda: True)
    assert gate.target_version() is None


def test_target_version_uses_the_project_version_scheme(gate):
    """The schemes come from ``pyproject.toml``, not from a copy of them.

    ``get_version`` with no configuration reports ``0.1``, not ``0.1.0``,
    because it does not read ``[tool.setuptools_scm]``. Restating
    ``release-branch-semver`` in the gate would work until someone changed it
    in one place, so the gate reads the file the build reads.
    """
    assert gate.target_version() == "0.1.0"
