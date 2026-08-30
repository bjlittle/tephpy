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
