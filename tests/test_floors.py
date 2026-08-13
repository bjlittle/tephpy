# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the dependency floor generator (floors spec §5)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
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


def _load_diagnose():
    """Import the diagnosis script by path."""
    path = REPO / ".github" / "scripts" / "floors_diagnose.py"
    spec = importlib.util.spec_from_file_location("floors_diagnose", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["floors_diagnose"] = module
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


def test_relaxing_one_package_leaves_the_others_pinned(tmp_path):
    # Attribution reads exactly one package off its floor (floors spec §3.4), so a
    # relaxation that also loosened its neighbours would prove nothing about which.
    floors = _load()
    resolved = floors.pins(_manifest(tmp_path), Version("3.12.0"), lookup=_lookup)
    text = floors.rewrite(MANIFEST, resolved, relax="click")
    assert 'click = ">=8.1"' in text
    assert 'pytest = "==8.0.0"' in text


RESOLVED = {
    "core": {"click": (">=8.1", "8.1.3")},
    "test": {"pytest": (">=8.0", "8.0.0")},
}


def _rig(monkeypatch, tmp_path, solves):
    """Replace the solver and the checkout copier; return the module and a probe."""
    diagnose = _load_diagnose()
    monkeypatch.setattr(diagnose.floors, "pins", lambda *_: RESOLVED)
    monkeypatch.setattr(diagnose, "_copy", lambda _probe, name: tmp_path / name)
    monkeypatch.setattr(diagnose, "solves", solves)
    monkeypatch.setattr(diagnose, "chosen", lambda *_: "8.1.8")
    probe = diagnose.Probe(
        source=tmp_path, scratch=tmp_path, tier="test", python="3.12"
    )
    return diagnose, probe


def test_a_tier_that_solves_is_not_attributed_by_relaxation(monkeypatch, tmp_path):
    # Relaxation attributes a *solve* failure (floors spec §3.4). Where the tier
    # solves and its exercise fails, every relaxation solves too, so a loop that
    # ran anyway would name whichever floor it reached first -- the guess dressed
    # as an attribution the specification rejects. `test` is in exactly this state
    # today, on matplotlib's deprecated `pyparsing.oneOf` call (floors spec §1).
    diagnose, probe = _rig(monkeypatch, tmp_path, lambda *_: (True, "solved"))
    monkeypatch.setattr(diagnose, "exercise", lambda *_: (False, "'oneOf' deprecated"))
    package, upper, failure = diagnose.attribute(probe)
    assert package is None
    assert upper is None
    assert "oneOf" in failure


def test_a_solve_failure_is_still_attributed(monkeypatch, tmp_path):
    # The other direction: the guard above must not have switched attribution off.
    # Only relaxing `pytest` solves here, so `pytest` is the culprit -- and `click`,
    # which the loop reaches first, is not.
    diagnose, probe = _rig(
        monkeypatch, tmp_path, lambda *args: (args[2] == "pytest", "conflict")
    )
    package, upper, failure = diagnose.attribute(probe)
    assert package == "pytest"
    assert upper == "8.1.8"
    assert failure == "conflict"


def test_the_probes_pin_a_version_for_the_editable_build(monkeypatch, tmp_path):
    # `_copy` strips `.git`, and tephpy installs editable into every environment,
    # so a probe's build backend has nothing to version from. That fails the build
    # rather than the solve, which turns the one relaxation that *does* resolve
    # into another failure and every diagnosis into "nothing attributed" -- the
    # same verdict an honestly unattributable failure gets (floors spec §3.4).
    diagnose = _load_diagnose()
    seen = {}

    def _run(command, **kwargs):
        seen[command[1]] = kwargs.get("env") or {}
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(diagnose.subprocess, "run", _run)
    monkeypatch.setattr(diagnose.floors, "tool", lambda name: f"/usr/bin/{name}")
    probe = diagnose.Probe(
        source=tmp_path, scratch=tmp_path, tier="test", python="3.12"
    )
    diagnose.solves(probe, tmp_path, None)
    diagnose.exercise(probe, tmp_path)
    assert seen["install"].get("SETUPTOOLS_SCM_PRETEND_VERSION")
    assert seen["run"].get("SETUPTOOLS_SCM_PRETEND_VERSION")


def test_the_environment_table_is_replaced_not_appended():
    # pixi solves every environment a manifest declares, so a leftover `default`
    # would let one tier's conflict fail another tier's run (floors spec §3.3).
    floors = _load()
    text = MANIFEST + "\n[tool.pixi.environments]\ndefault = { features = [] }\n"
    out = floors.environments(text, "test", "3.12")
    assert "floors-test" in out
    assert "default = " not in out
