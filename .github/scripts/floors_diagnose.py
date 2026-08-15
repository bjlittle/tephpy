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

#: How each tier is exercised once it resolves (floors spec §3.3), step for step
#: as `ci-floors.yml` runs it. The docs tier is a build *and* its two output
#: gates, and a floor can pass the build and fail a gate -- `sphinx-click 6.0.0`
#: did (:issue:`109`). A probe running the build alone would re-run that leg
#: green and report it unreproduced, which reads as "the floor is fine". `devs`
#: has no entry to run: its packages are linters, and pre-commit at a floor
#: `ruff` reports that version's rule set rather than anything about tephpy.
EXERCISE: dict[str, list[list[str]] | None] = {
    "test": [["pytest"]],
    "docs": [
        ["make", "-C", "docs", "html"],
        ["python", ".github/scripts/check_rendered_citations.py", "docs/_build/html"],
        ["python", ".github/scripts/check_documentation_links.py", "docs/_build/html"],
    ],
    "devs": None,
}

#: tephpy installs editable into every environment, so every probe runs the build
#: backend, and what setuptools-scm makes of a probe is not a version anyone
#: declared: the tree is one this job has rewritten, and no release is tagged yet
#: for the backend to describe from. A build that fails there
#: fails the *build*, not the solve -- so the one relaxation that does resolve
#: looks like another failure and the diagnosis reports nothing attributed, which
#: is indistinguishable from the honest form of that verdict. What version tephpy
#: claims cannot bear on whether a dependency floor resolves, so the probes pin it.
ENVIRONMENT = {**os.environ, "SETUPTOOLS_SCM_PRETEND_VERSION": "0.0.0"}

#: Said when the tier solves and its exercise then passes on re-run, so the
#: failing step was one this script does not reproduce. Last, not first, because
#: `main` keeps the tail of the failure text and a prefix would be trimmed away.
UNREPRODUCED = (
    "NOTE: the tier solved and its exercise passed when re-run here, so the "
    "failure is in a step this script does not reproduce. See the run log."
)

#: How much of an output a finding keeps, counted from its end. A finding can
#: carry two traces now (:issue:`149`), a whole docs build runs to more than the
#: 65536 characters GitHub takes in an issue body, and what a build or a test run
#: says about why it failed it says last.
TAIL = 4000


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
    #: Which table declares the culprit, which is not always the tier that
    #: failed: the core table is resolved into every tier, so a `test` run can
    #: attribute to a package declared in `[tool.pixi.dependencies]`. The issue
    #: names the declaration sites to edit, and the tier would name the wrong
    #: pair (floors spec §3.1, §3.6).
    site: str | None = None
    #: Which of that tier's two tables declares it, `dependencies` or
    #: `pypi-dependencies`. The ladder this scan climbs comes from the index
    #: that table names, and the issue names the table to edit; a package with
    #: releases on both would otherwise be scanned and reported against the
    #: wrong one (:issue:`151`).
    table: str = "dependencies"
    lowest: str | None = None
    scanned: list[str] = dataclasses.field(default_factory=list)
    #: What the highest version tried failed on, empty unless the scan ran out.
    #: The `failure` above is the failure of the floors *as declared*, which is
    #: why the tier is red and the one thing its reader already knows. Where no
    #: candidate passes, what the candidates failed on is the new information,
    #: and the usual reason is a second broken floor the relaxed resolve left in
    #: place: `docs` reported no passing `sphinx-design` of three tried, when
    #: 0.6.1 passes and every candidate was failing on `sphinx-autoapi` instead.
    #: Finding that took a manual resolve-and-build cycle against a trace the
    #: scan had already had in hand and thrown away (:issue:`145`, :issue:`149`).
    blocked: str = ""


def solves(
    probe: Probe,
    root: Path,
    relax: str | None,
    pin: tuple[str, str] | None = None,
) -> tuple[bool, str]:
    """Report whether the tier solves with one floor relaxed or forced.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.
    root : Path
        A scratch copy of the repository.
    relax : str, optional
        The package to return to its declared floor.
    pin : tuple of (str, str), optional
        A package and the exact version to hold it at, applied *after* the
        generator has written the tier's pins. This is how the scan of floors
        spec §3.5 walks a package upward. Writing the pin into the manifest
        beforehand would not survive: the generator rebuilds every declaration
        from its ``>=`` floor, and would refuse the manifest first, an exact
        pin not being a floor it can resolve (floors spec §3.2).

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
    if pin is not None:
        _pin_one(root / "pyproject.toml", *pin)
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
        Whether every step passed, and the output of the first that did not.
        A tier with no exercise passes with no output.

    """
    commands = EXERCISE.get(probe.tier)
    if commands is None:
        return True, ""
    for command in commands:
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
        if out.returncode != 0:
            # The steps run in the workflow's order and each needs the one
            # before it -- both docs gates read what the build wrote -- so a
            # failure stops here rather than reporting the cascade after it.
            return False, out.stdout + out.stderr
    return True, ""


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
    # Each probe carries an installed environment, and this loop makes one per
    # declared floor -- twenty-eight for `docs`. Held to the end they would put
    # the tier's whole package count on a runner's disk at once, so a probe is
    # dropped as soon as it has answered, the scan below keeping the same rule.
    # This one has answered: that it does not solve is why the loop runs.
    shutil.rmtree(baseline, ignore_errors=True)
    for index, package in enumerate(packages):
        root = _copy(probe, f"relax-{index}")
        relaxed, _ = solves(probe, root, package)
        if relaxed:
            # Kept, alone of them: `chosen` reads the resolve out of this one.
            return package, chosen(probe, root, package), output
        shutil.rmtree(root, ignore_errors=True)
    return None, None, output


def _copy(probe: Probe, name: str) -> Path:
    """Make a throwaway copy of the checkout.

    A probe is the failing leg run again, so what the leg had it has: the tree
    is copied whole, index included. Thirteen of the `test` tier's tests guard
    on a repository being there -- the one that builds a wheel from
    `git archive HEAD` among them -- and a probe without one runs a thinner
    suite than the leg it is diagnosing, then reports the leg's failure as a
    step it could not reproduce when the failing step is a test it skipped
    (:issue:`154`). `.git` was dropped here for its size, which does not
    survive measuring the repository this job actually checks out: every
    workflow in this repository sets `fetch-depth: 0`, and all of that history
    is 3.2 MB of objects over 105 commits, against a working tree of 5.6 MB
    that has always been copied. The whole copy takes 0.03 s where the tree
    alone takes 0.02 s, beside a probe that then installs an environment
    (measured 2026-08-15). What multiplies is the number of probes, not what
    each one holds, and `attribute` below drops each as it answers.

    What the failing leg left behind is dropped, though. The diagnosis runs after
    that leg ran in this same checkout, so `__pycache__` holds byte-code whose
    code objects name the checkout and not the copy, and `docs/_build` makes
    the probe's build an incremental one over pages it did not write. Both
    make the exercise report the state of the run being diagnosed rather than
    its own: a warning attributed to the checkout's path fails a test that
    compares it to `__file__`, whatever the floors resolved to.
    """
    root = probe.scratch / name
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(
        probe.source,
        root,
        ignore=shutil.ignore_patterns(
            ".pixi", "__pycache__", ".pytest_cache", "_build"
        ),
    )
    return root


def _pin_one(manifest: Path, package: str, pin: str) -> None:
    """Rewrite one declaration to an exact pin, leaving the rest alone."""
    text = manifest.read_text(encoding="utf-8")
    out = []
    for line in text.splitlines(keepends=True):
        match = floors.DECLARATION.match(line.strip())
        if match is not None and match["name"] == package:
            out.append(f'{package} = "=={pin}"\n')
            continue
        out.append(line)
    manifest.write_text("".join(out), encoding="utf-8")


def _probe_pin(probe: Probe, root: Path, package: str, pin: str) -> tuple[bool, str]:
    """Report whether the tier resolves and passes its exercise at one pin.

    Returns
    -------
    tuple of (bool, str)
        Whether the pin passed, and what it failed on: the solver's output
        where it did not resolve, the exercise's where it resolved and the
        exercise then failed. Empty when it passed.

    """
    solved, output = solves(probe, root, None, pin=(package, pin))
    if not solved:
        return False, output
    return exercise(probe, root)


def scan(
    probe: Probe,
    package: str,
    specifier: str,
    upper: str | None,
    table: str = "dependencies",
) -> tuple[str | None, list[str], str]:
    """Find the lowest version of ``package`` that passes the tier's exercise.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.
    package : str
        The culprit :func:`attribute` named.
    specifier : str
        Its declared floor, such as ``>=3.10``.
    upper : str or None
        The version the relaxed solve chose, which bounds the scan above
        (floors spec §3.5); None scans the whole ladder.
    table : str, optional
        The table declaring ``package``, which is the index its ladder comes
        from; defaults to the conda ``dependencies`` table.

    Returns
    -------
    tuple of (str or None, list of str, str)
        The lowest passing version, or None; every version tried; and what
        the last of them failed on, which is the highest and so the one whose
        failure is not already the tier's. Empty when a version passed
        (floors spec §3.5).

    """
    rungs = floors.ladder(package, specifier, Version(f"{probe.python}.0"), table)
    if upper is not None:
        ceiling = Version(upper)
        rungs = [pin for pin in rungs if Version(pin) <= ceiling]
    tried: list[str] = []
    blocked = ""
    for pin in rungs:
        root = _copy(probe, f"scan-{len(tried)}")
        tried.append(pin)
        passed, blocked = _probe_pin(probe, root, package, pin)
        if passed:
            return pin, tried, ""
        # Every probe is a whole environment, so keeping them all would grow the
        # scan's disk with the ladder on a runner that has little to spare. Its
        # output is read out first: the probe is what nothing reads again, and
        # the trace was thrown away with it before (:issue:`149`).
        shutil.rmtree(root, ignore_errors=True)
    return None, tried, blocked


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
    package, upper, failure = attribute(probe)
    finding = Finding(
        tier=args.tier,
        half=args.half,
        failure=args.failure or failure[-TAIL:],
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
                finding.site = tier
                finding.table = resolved[tier][package][2]
    if package is not None and finding.declared is not None:
        finding.lowest, finding.scanned, blocked = scan(
            probe, package, finding.declared, upper, finding.table
        )
        # Trimmed as the baseline failure is, and from the same end: what a
        # build or a test run says about why it failed is the last thing it
        # says, and an issue body has a size the whole of a docs build exceeds.
        finding.blocked = blocked[-TAIL:]
    write_finding(args.out, finding)
    print(f"attributed: {package or 'nothing'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
