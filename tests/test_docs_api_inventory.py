# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The API surface gate (:issue:`227`).

``check_api_docstrings.published_objects`` reproduces sphinx-autoapi's
selection without a build, so it can run in the test suite and fail on the
commit that introduces a defect. ``check_api_inventory.py`` is what earns that
shortcut: it reads the ``objects.inv`` a real build wrote and compares the two
sets.

It is not a formality. The enumerator's first cut found 156 objects against
the published 94 -- every one of the 62 extra a re-export. The rule that
settles it, and the ``tephpy.config`` singleton whose methods are published
while its property is not, are held by the build comparison below rather than
asserted in a comment.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import zlib

import pytest

REPO = Path(__file__).parents[1]
GATE = REPO / ".github" / "scripts" / "check_api_inventory.py"
INVENTORY = REPO / "docs" / "_build" / "html" / "objects.inv"


def _load():
    """Import the gate, which is a script rather than an installed module."""
    spec = importlib.util.spec_from_file_location("check_api_inventory", GATE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


inventory_gate = _load()


def _write_inventory(path, entries):
    """Write a minimal Sphinx inventory holding `entries`.

    Parameters
    ----------
    path : pathlib.Path
        The ``objects.inv`` to write.
    entries : iterable of tuple of str
        ``(name, role)`` pairs.
    """
    body = "".join(f"{name} {role} 1 reference/x.html#$ -\n" for name, role in entries)
    header = (
        b"# Sphinx inventory version 2\n"
        b"# Project: tephpy\n"
        b"# Version: 0.1.0\n"
        b"# The remainder of this file is compressed using zlib.\n"
    )
    path.write_bytes(header + zlib.compress(body.encode("utf-8")))


def test_usage_without_a_root_fails(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["check_api_inventory.py"])
    assert inventory_gate.main() == 1
    assert "usage" in capsys.readouterr().out


def test_a_missing_directory_fails(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "argv", ["x", str(tmp_path / "nope")])
    assert inventory_gate.main() == 1
    assert "no such directory" in capsys.readouterr().out


def test_a_missing_inventory_fails(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "argv", ["x", str(tmp_path)])
    assert inventory_gate.main() == 1
    assert "no inventory" in capsys.readouterr().out


def test_an_inventory_naming_nothing_fails(monkeypatch, capsys, tmp_path):
    """A gate over nothing passes everything.

    Both sides come from mechanisms that could break together, so an empty
    published set has to be a failure rather than a silent agreement.
    """
    _write_inventory(tmp_path / "objects.inv", [("other.thing", "py:function")])
    monkeypatch.setattr(sys, "argv", ["x", str(tmp_path)])
    assert inventory_gate.main() == 1
    assert "names no tephpy objects" in capsys.readouterr().out


def test_a_divergence_is_reported_in_both_directions(monkeypatch, capsys, tmp_path):
    """The report names the direction, because they mean different things.

    An extra is the gate inventing API; a missing one is the gate letting a
    published docstring go unchecked.
    """
    _write_inventory(
        tmp_path / "objects.inv",
        [("tephpy.calc", "py:module"), ("tephpy.nowhere", "py:function")],
    )
    monkeypatch.setattr(sys, "argv", ["x", str(tmp_path)])
    assert inventory_gate.main() == 1
    out = capsys.readouterr().out
    assert "published, not enumerated : tephpy.nowhere" in out
    assert "enumerated, not published : tephpy.sounding.Sounding" in out


def test_attributes_are_not_expected_to_be_enumerated(monkeypatch, tmp_path, capsys):
    """A ``py:attribute`` is outside the compared set, not a missing name.

    104 of the 207 entries a build publishes are dataclass fields, documented
    in their class's ``Attributes`` section. Were they compared, the gate
    would demand a directive on something with no docstring to hold one.
    """
    entries = [(entry.name, "py:function") for entry in _enumerated()]
    entries.append(("tephpy.calc.Profile.lcl_pressure", "py:attribute"))
    _write_inventory(tmp_path / "objects.inv", entries)
    monkeypatch.setattr(sys, "argv", ["x", str(tmp_path)])
    assert inventory_gate.main() == 0
    assert "API surface ok" in capsys.readouterr().out


def _enumerated():
    """Return the enumerated published objects."""
    return inventory_gate.load_gate().published_objects()


@pytest.mark.skipif(
    not INVENTORY.exists(),
    reason="needs a documentation build; run `pixi run docs-html` first",
)
def test_the_enumerated_surface_is_the_published_surface(monkeypatch, capsys):
    """The claim the whole design rests on, against a real build."""
    monkeypatch.setattr(sys, "argv", ["x", str(INVENTORY.parent)])
    assert inventory_gate.main() == 0
    assert "API surface ok" in capsys.readouterr().out
