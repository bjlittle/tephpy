#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Attribute a floors failure to one package (floors spec §3.4, §3.5).

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

from packaging.version import Version

if TYPE_CHECKING:
    from types import ModuleType

SCRIPTS = Path(__file__).parent

#: How each tier is exercised once it resolves (floors spec §3.3). `devs` has no
#: entry to run: its packages are linters, and pre-commit at a floor `ruff`
#: reports that version's rule set rather than anything about tephpy.
EXERCISE: dict[str, list[str] | None] = {
    "test": ["pytest"],
    "docs": ["make", "-C", "docs", "html"],
    "devs": None,
}

#: `_copy` strips `.git`, and tephpy installs editable into every environment, so
#: a probe's build backend has no repository to version from and setuptools-scm
#: raises. That fails the *build*, not the solve -- so the one relaxation that
#: does resolve looks like another failure and the diagnosis reports nothing
#: attributed, which is indistinguishable from the honest form of that verdict.
#: What version tephpy claims cannot bear on whether a dependency floor resolves,
#: so the probes pin it.
ENVIRONMENT = {**os.environ, "SETUPTOOLS_SCM_PRETEND_VERSION": "0.0.0"}

#: Said when the tier solves and its exercise then passes on re-run, so the
#: failing step was one this script does not reproduce. Last, not first, because
#: `main` keeps the tail of the failure text and a prefix would be trimmed away.
UNREPRODUCED = (
    "NOTE: the tier solved and its exercise passed when re-run here, so the "
    "failure is in a step this script does not reproduce. See the run log."
)


def _floors() -> ModuleType:
    """Import the generator beside this script."""
    spec = importlib.util.spec_from_file_location("floors", SCRIPTS / "floors.py")
    if spec is None or spec.loader is None:  # pragma: no cover - import guard
        msg = "floors.py not found beside floors_diagnose.py"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules["floors"] = module
    spec.loader.exec_module(module)
    return module


floors = _floors()


@dataclasses.dataclass(frozen=True)
class Probe:
    """Where and how one tier is exercised.

    The four values are invariant across a diagnosis, so they travel
    together rather than through every signature.
    """

    source: Path
    scratch: Path
    tier: str
    python: str


@dataclasses.dataclass
class Finding:
    """One tier's verdict, as floors spec §3.6 files it."""

    tier: str
    half: str
    failure: str
    package: str | None = None
    declared: str | None = None
    lowest: str | None = None
    scanned: list[str] = dataclasses.field(default_factory=list)


def solves(probe: Probe, root: Path, relax: str | None) -> tuple[bool, str]:
    """Report whether the tier solves with one floor relaxed.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.
    root : Path
        A scratch copy of the repository.
    relax : str, optional
        The package to return to its declared floor.

    Returns
    -------
    tuple of (bool, str)
        Whether it solved, and the solver's combined output.

    """
    command = [
        sys.executable,
        str(SCRIPTS / "floors.py"),
        "--manifest",
        str(root / "pyproject.toml"),
        "--tier",
        probe.tier,
        "--python",
        probe.python,
        "--write",
    ]
    if relax is not None:
        command += ["--relax", relax]
    subprocess.run(  # noqa: S603 -- fixed argv, this interpreter
        command, check=True, capture_output=True, text=True
    )
    out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        [floors.tool("pixi"), "install", "--environment", f"floors-{probe.tier}"],
        cwd=root,
        env=ENVIRONMENT,
        capture_output=True,
        text=True,
        check=False,
    )
    return out.returncode == 0, out.stdout + out.stderr


def exercise(probe: Probe, root: Path) -> tuple[bool, str]:
    """Run the tier's exercise against an environment already installed.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.
    root : Path
        The scratch copy whose environment was installed.

    Returns
    -------
    tuple of (bool, str)
        Whether it passed, and its combined output. A tier with no exercise
        passes with no output.

    """
    command = EXERCISE.get(probe.tier)
    if command is None:
        return True, ""
    out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        [
            floors.tool("pixi"),
            "run",
            "--environment",
            f"floors-{probe.tier}",
            *command,
        ],
        cwd=root,
        env=ENVIRONMENT,
        capture_output=True,
        text=True,
        check=False,
    )
    return out.returncode == 0, out.stdout + out.stderr


def chosen(probe: Probe, root: Path, package: str) -> str | None:
    """Return the version an installed environment resolved for one package.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.
    root : Path
        The scratch copy whose environment was installed.
    package : str
        The package to read.

    Returns
    -------
    str or None
        The resolved version, or None when the environment lacks it.

    """
    out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        [
            floors.tool("pixi"),
            "list",
            "--environment",
            f"floors-{probe.tier}",
            "--json",
        ],
        cwd=root,
        env=ENVIRONMENT,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return None
    for entry in json.loads(out.stdout):
        if entry.get("name") == package:
            return str(entry["version"])
    return None


def attribute(probe: Probe) -> tuple[str | None, str | None, str]:
    """Find the one floor whose relaxation lets the tier solve.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.

    Returns
    -------
    tuple of (str or None, str or None, str)
        The culprit package, or None when nothing attributed; the version
        the relaxed solve chose for it, which bounds the scan above
        (floors spec §3.5); and the output that stands as the failure.

    """
    resolved = floors.pins(
        probe.source / "pyproject.toml", Version(f"{probe.python}.0")
    )
    packages = list(resolved["core"]) + list(resolved.get(probe.tier, {}))
    baseline = _copy(probe, "baseline")
    solved, output = solves(probe, baseline, None)
    if solved:
        # Relaxation attributes a *solve* failure (floors spec §3.4). This tier
        # solved, so the failure came from its exercise, and there is nothing for
        # a relaxation to repair: every probe below would solve on its first try
        # and name whichever floor the loop happened to reach first. That is the
        # guess dressed as an attribution the specification rejects, so the tier
        # is reported unattributed with the exercise output that identifies it.
        passed, trace = exercise(probe, baseline)
        if passed:
            return None, None, f"{output}\n\n{UNREPRODUCED}"
        return None, None, trace
    for index, package in enumerate(packages):
        root = _copy(probe, f"relax-{index}")
        relaxed, _ = solves(probe, root, package)
        if relaxed:
            return package, chosen(probe, root, package), output
    return None, None, output


def _copy(probe: Probe, name: str) -> Path:
    """Make a throwaway copy of the checkout."""
    root = probe.scratch / name
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(probe.source, root, ignore=shutil.ignore_patterns(".pixi", ".git"))
    return root


def write_finding(path: Path, finding: Finding) -> None:
    """Write one finding as JSON.

    Parameters
    ----------
    path : Path
        The artifact to write.
    finding : Finding
        The verdict to record.

    """
    path.write_text(json.dumps(dataclasses.asdict(finding), indent=2), "utf-8")


def main() -> int:
    """Diagnose one failing tier.

    Returns
    -------
    int
        Always 0 — a diagnosis is not itself a failure.

    """
    parser = argparse.ArgumentParser(description="Diagnose a floors failure.")
    parser.add_argument("--source", type=Path, default=Path())
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--tier", required=True, choices=["test", "docs", "devs"])
    parser.add_argument("--half", required=True, choices=["conda", "pypi"])
    parser.add_argument("--python", default="3.12")
    parser.add_argument("--failure", default="")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    args.scratch.mkdir(parents=True, exist_ok=True)
    probe = Probe(
        source=args.source.resolve(),
        scratch=args.scratch.resolve(),
        tier=args.tier,
        python=args.python,
    )
    # `_upper` bounds the upward scan of floors spec §3.5, which is not wired in yet.
    package, _upper, failure = attribute(probe)
    finding = Finding(
        tier=args.tier,
        half=args.half,
        failure=args.failure or failure[-4000:],
        package=package,
    )
    if package is not None:
        resolved = floors.pins(
            probe.source / "pyproject.toml", Version(f"{args.python}.0")
        )
        # Only the two tables the attribution drew from: a package declared in
        # more than one tier would otherwise report whichever table came last.
        for tier in ("core", args.tier):
            if package in resolved.get(tier, {}):
                finding.declared = resolved[tier][package][0]
    write_finding(args.out, finding)
    print(f"attributed: {package or 'nothing'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
