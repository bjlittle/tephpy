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
import functools
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

from packaging.version import Version

if TYPE_CHECKING:
    from collections.abc import Iterable
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

#: The same table for the PyPI half, as argv after the probe's own interpreter.
#: Only `core + test` runs anything (floors spec §3.3): the documentation build
#: needs `make`, which the pip declaration deliberately does not carry, and
#: `devs` is linters either way. So a `docs` or `devs` failure on this half is a
#: failure to install, and attribution is the whole of its diagnosis.
PYPI_EXERCISE: dict[str, list[list[str]] | None] = {
    "test": [["-m", "pytest"]],
    "docs": None,
    "devs": None,
}

#: Where the PyPI half declares its floors (floors spec §3.1), by tier. These
#: are the same four files `SITES` in `floors_issue.py` names to whoever reads
#: the issue, and `tests/test_floors.py` holds the two lists together: one of
#: them tells a reader where the floor is, the other is where this script reads
#: it from, and a rename that reached only one would send them to a file the
#: diagnosis was not looking at.
REQUIREMENTS = {
    "core": "requirements/pypi-core.txt",
    "test": "requirements/pypi-optional-test.txt",
    "docs": "requirements/pypi-optional-docs.txt",
    "devs": "requirements/pypi-optional-devs.txt",
}

#: The packages the two declaration sites spell differently, PyPI name to conda
#: name. `matplotlib-base` is conda-forge's matplotlib without the GUI
#: toolkits; `python-build` is `build` under conda-forge's rule for a name the
#: channel already uses. One floor is one issue and the key is tier and package
#: (floors spec §3.6), so without this a floor broken in both halves files two
#: issues for what is one edit to two lines. Names differing only in `_` for `-`
#: are not here: those are the same name under PEP 503, and `_canonical` below
#: settles them.
ALIASES = {"matplotlib": "matplotlib-base", "build": "python-build"}

#: The interpreter a PyPI probe installs into, named as `ci-floors.yml` names
#: the one its own leg installs into. It sits inside the probe's copy so that
#: dropping the copy drops it too, and `_copy` skips any it finds: a virtual
#: environment records the path it was made at, so the failing leg's would have
#: every probe installing into the checkout under diagnosis.
VENV = ".venv-floors"

#: A `name==version` line, as `uv pip compile` and `uv pip freeze` both write it.
#: Anything else -- the header comments, the `# via` lines, an extras marker --
#: does not match, which is the whole of the parsing either output needs.
PINNED = re.compile(r"^(?P<name>[A-Za-z0-9._-]+)==(?P<version>[^\s;]+)")

#: One requirements-file declaration, `name` and everything the line then says
#: about the version. Comments and blank lines match nothing.
REQUIREMENT = re.compile(r"^(?P<name>[A-Za-z0-9._-]+)(?P<specifier>[^\s#]*)")

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

    The five values are invariant across a diagnosis, so they travel
    together rather than through every signature.
    """

    source: Path
    scratch: Path
    tier: str
    python: str
    #: Which declaration site of floors spec §3.1 is being diagnosed. The loop
    #: of floors spec §3.4 and the one of floors spec §3.5 are one
    #: implementation over both halves --
    #: relax one floor, re-solve, and climb from the failure -- and what changes
    #: underneath is the resolver: pixi against the channel, `uv` against the
    #: package index. So this selects the resolver and nothing else, and it
    #: carries the same two words the finding is filed under.
    half: str = "conda"


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
    #: What the *other* declaration site calls this package, empty when the two
    #: agree. `package` above is the key one floor is one issue on, so it is the
    #: manifest's spelling whichever half found it (floors spec §3.6) -- and the
    #: issue sends its reader to both files to make the same edit, where two of
    #: them would find no such line: `matplotlib-base` is `matplotlib` in the
    #: requirements file, and `python-build` is `build`.
    alias: str = ""
    #: The requirements file declaring the floor, where that is not the one the
    #: `site` above pairs with. The two tiers need not agree: `setuptools_scm`
    #: is a `test` requirement on the PyPI side and a core declaration in the
    #: manifest, and one `site` cannot name both files rightly.
    requirements: str = ""


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
        floors have been written. This is how the scan of floors spec §3.5
        walks a package upward.

    Returns
    -------
    tuple of (bool, str)
        Whether it solved, and the solver's combined output.

    """
    if probe.half == "pypi":
        return _pypi_solves(probe, root, relax, pin)
    return _conda_solves(probe, root, relax, pin)


def _conda_solves(
    probe: Probe,
    root: Path,
    relax: str | None,
    pin: tuple[str, str] | None,
) -> tuple[bool, str]:
    """Solve the tier from the channel, with the generator writing the pins.

    A pin is written after the generator has run rather than into the manifest
    it reads: the generator rebuilds every declaration from its ``>=`` floor,
    and would refuse the manifest first, an exact pin not being a floor it can
    resolve (floors spec §3.2).
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


def _uv() -> list[str]:
    """Return the argv prefix that runs ``uv``, as `ci-floors.yml` provisions it.

    The PyPI leg installs no `uv` of its own -- it reaches for one through
    `pixi exec` -- and this diagnosis runs in that same job, so it takes its
    `uv` from the same place rather than adding a second way of getting one to
    a job whose whole purpose is to work when the first way has broken.
    """
    return [floors.tool("pixi"), "exec", "--spec", "uv", "uv"]


def _requirements(path: Path) -> dict[str, str]:
    """Every floor one requirements file declares, package to specifier."""
    found = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = REQUIREMENT.match(line.strip())
        if match is not None:
            found[match["name"]] = match["specifier"]
    return found


def _canonical(name: str) -> str:
    """Normalize a distribution name as PEP 503 does."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _same(one: str, other: str) -> bool:
    """Whether two names are one package, under either site's spelling."""
    left, right = _canonical(one), _canonical(other)
    return left == right or ALIASES.get(left) == right or ALIASES.get(right) == left


@functools.cache
def defaults(probe: Probe) -> dict[str, str]:
    """Report what the default resolution installs, by canonical package name.

    This is what a relaxation on the PyPI half pins to (floors spec §3.4), and
    it is one resolution for the whole diagnosis rather than one per relaxed
    floor -- the same question, asked of the same requirements, however many
    probes go on to read the answer. It resolves and does not install, and it
    leaves the project itself out: `requirements/pypi-core.txt` *is*
    ``[project] dependencies``, so tephpy would add nothing to the set but a
    build of it.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.

    Returns
    -------
    dict
        Canonical package name to version, empty where the default resolution
        does not resolve. Empty is a real answer: nothing then has a version to
        be relaxed to, no relaxation is tried, and floors spec §3.4's
        unattributed branch reports the tier with the solver output that got it
        there. A default resolution that fails is not a floor failing anyway --
        it is `pip install tephpy` failing, which the declared floors did not
        cause and no relaxation of them can repair.

    """
    command = [*_uv(), "pip", "compile", "--quiet", "--python-version", probe.python]
    command += [str(probe.source / REQUIREMENTS[site]) for site in ("core", probe.tier)]
    out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        command,
        cwd=probe.source,
        env=ENVIRONMENT,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return {}
    found = {}
    for line in out.stdout.splitlines():
        match = PINNED.match(line)
        if match is not None:
            found[_canonical(match["name"])] = match["version"]
    return found


def _pin_requirement(path: Path, package: str, pin: str) -> None:
    """Rewrite one requirement to an exact pin, leaving the rest alone."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        match = REQUIREMENT.match(line.strip())
        if match is not None and _canonical(match["name"]) == _canonical(package):
            out.append(f"{match['name']}=={pin}\n")
            continue
        out.append(line)
    path.write_text("".join(out), encoding="utf-8")


def _pypi_solves(
    probe: Probe,
    root: Path,
    relax: str | None,
    pin: tuple[str, str] | None,
) -> tuple[bool, str]:
    """Install the tier from the package index, one requirement rewritten.

    There is no pin here to return to a ``>=``, because
    ``--resolution lowest-direct`` puts every direct requirement at its floor
    with nothing written down -- and it is a flag over the whole resolution,
    with no per-package escape. So a relaxation rewrites that one requirement
    to pin the version the default resolution would have chosen. Dropping its
    lower bound instead would not relax it at all: unconstrained under
    ``lowest-direct`` it resolves *lower*, to the oldest release the index
    carries (floors spec §3.4).
    """
    files = [root / REQUIREMENTS[site] for site in ("core", probe.tier)]
    rewrites = []
    if relax is not None:
        version = defaults(probe).get(_canonical(relax))
        if version is None:
            # A package the default resolution does not install has no version
            # for this half to relax it to. Reported as a probe that did not
            # solve, which is what it is: nothing was tried, so nothing is
            # attributed to it, and a guessed pin would report an attribution
            # against a resolve the resolver never made.
            return False, ""
        rewrites.append((relax, version))
    if pin is not None:
        rewrites.append(pin)
    for package, version in rewrites:
        for path in files:
            _pin_requirement(path, package, version)
    made = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        [*_uv(), "venv", "--python", probe.python, str(root / VENV)],
        cwd=root,
        env=ENVIRONMENT,
        capture_output=True,
        text=True,
        check=False,
    )
    if made.returncode != 0:  # pragma: no cover - the interpreter is the job's own
        return False, made.stdout + made.stderr
    command = [
        *_uv(),
        "pip",
        "install",
        "--python",
        str(root / VENV),
        "--resolution",
        "lowest-direct",
    ]
    for path in files:
        command += ["-r", str(path)]
    command.append(str(root))
    out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        command,
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
    if probe.half == "pypi":
        return _run_steps(
            probe, root, PYPI_EXERCISE, [str(root / VENV / "bin" / "python")]
        )
    return _run_steps(
        probe,
        root,
        EXERCISE,
        [floors.tool("pixi"), "run", "--environment", f"floors-{probe.tier}"],
    )


def _run_steps(
    probe: Probe,
    root: Path,
    table: dict[str, list[list[str]] | None],
    prefix: list[str],
) -> tuple[bool, str]:
    """Run one half's exercise for the tier, step by step, stopping at a failure."""
    commands = table.get(probe.tier)
    if commands is None:
        return True, ""
    for command in commands:
        out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
            [*prefix, *command],
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
    if probe.half == "pypi":
        return _pypi_chosen(root, package)
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


def _pypi_chosen(root: Path, package: str) -> str | None:
    """Read one package's version out of a probe's virtual environment."""
    out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        [*_uv(), "pip", "freeze", "--python", str(root / VENV)],
        cwd=root,
        env=ENVIRONMENT,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return None
    for line in out.stdout.splitlines():
        match = PINNED.match(line)
        if match is not None and _canonical(match["name"]) == _canonical(package):
            return match["version"]
    return None


def declared(probe: Probe) -> dict[str, tuple[str, str, str]]:
    """Every floor the failing tier declares, in the order relaxation tries them.

    The tier's own table and the core one resolved into it, in that order --
    core first because that is where a `test` failure most often comes from
    (floors spec §3.1) -- read from whichever of the two declaration sites this
    half installs from.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.

    Returns
    -------
    dict
        Package to ``(specifier, site, table)``: the floor as declared, the
        tier whose table declares it, and the table itself — which is the
        index the scan of floors spec §3.5 reads its candidates from, and so
        is the package index throughout on the PyPI half.

    """
    if probe.half == "pypi":
        return {
            package: (specifier, site, "pypi-dependencies")
            for site in ("core", probe.tier)
            for package, specifier in _requirements(
                probe.source / REQUIREMENTS[site]
            ).items()
        }
    resolved = floors.pins(
        probe.source / "pyproject.toml", Version(f"{probe.python}.0")
    )
    return {
        package: (entry[0], site, entry[2])
        for site in ("core", probe.tier)
        for package, entry in resolved.get(site, {}).items()
    }


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
    packages = list(declared(probe))
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
    compares it to `__file__`, whatever the floors resolved to. The installed
    environments go with them, and for the same reason twice over: `.pixi` and
    the PyPI leg's `VENV` are both large and both record the path they were
    made at, so a copied one would have the probe reading, and installing into,
    the checkout it is supposed to be standing apart from.
    """
    root = probe.scratch / name
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(
        probe.source,
        root,
        ignore=shutil.ignore_patterns(
            ".pixi", VENV, "__pycache__", ".pytest_cache", "_build"
        ),
    )
    return root


def spellings(probe: Probe, package: str) -> tuple[str, str]:
    """Return the manifest's name for one package, and the requirements file's.

    Parameters
    ----------
    probe : Probe
        The tier being exercised.
    package : str
        The package as the resolver that found it names it.

    Returns
    -------
    tuple of (str, str)
        The name the manifest writes, and the one the requirements file
        writes where the two differ — empty where they agree.

    Notes
    -----
    One floor is one issue and the key is tier and package (floors spec §3.6),
    so both halves have to arrive at the same one of the two names or a floor
    broken in both files two issues for what is a single edit to two lines. The
    manifest's is the one kept, for no reason beyond its being the half that
    has been filing. The other is carried beside it because the issue sends its
    reader to both files, and `matplotlib-base` appears in neither requirements
    file.

    """
    manifest = floors.declarations(probe.source / "pyproject.toml")
    conda = _match(
        package,
        (name for site in ("core", probe.tier) for name in manifest.get(site, {})),
    )
    wheel = _match(
        package,
        (
            name
            for site in ("core", probe.tier)
            for name in _requirements(probe.source / REQUIREMENTS[site])
        ),
    )
    conda = conda or package
    return conda, "" if wheel is None or wheel == conda else wheel


def _match(package: str, names: Iterable[str]) -> str | None:
    """Find one package among the names the other declaration site writes."""
    return next((name for name in names if _same(name, package)), None)


def _pixi_site(probe: Probe, package: str, fallback: str) -> tuple[str, str]:
    """Return the tier and table whose pixi declaration the issue should name.

    The PyPI half reads its floors from the requirements files, and the tier
    that declares one there need not be the tier that declares it in the
    manifest: `setuptools_scm` is a `test` requirement and a core declaration.
    So the manifest is asked directly rather than the site being carried over,
    and `fallback` stands where no table declares it at all.
    """
    manifest = floors.declarations(probe.source / "pyproject.toml")
    found = (fallback, "dependencies")
    for site in ("core", probe.tier):
        if package in manifest.get(site, {}):
            found = (site, manifest[site][package])
    return found


def _pypi_site(probe: Probe, package: str) -> str:
    """Return the requirements file declaring one floor, empty where none does.

    The mirror of `_pixi_site` above, and asked for the same reason: the tier a
    package is floored in at one site need not be the tier it is floored in at
    the other, so neither can be read off the other. Both halves ask, because
    both file (:issue:`142`) and one issue names both lines.

    Empty is a real answer and not a lookup that failed. The manifest declares
    packages the pip requirements have no counterpart for -- `make`, which
    drives the documentation build (floors spec §3.1) -- and an issue that named
    a requirements file for one of those would send its reader to a file with no
    such line, which reads exactly like a line they failed to find.
    """
    found = ""
    for site in ("core", probe.tier):
        if _match(package, _requirements(probe.source / REQUIREMENTS[site])):
            found = REQUIREMENTS[site]
    return found


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
        half=args.half,
    )
    package, upper, failure = attribute(probe)
    finding = Finding(
        tier=args.tier,
        half=args.half,
        failure=args.failure or failure[-TAIL:],
        package=package,
    )
    # The table the ladder is read from, which the PyPI half reports as the
    # index and the issue then reports as a pixi table -- two different
    # questions of the same word, and the scan wants the first.
    ladder = "dependencies"
    if package is not None:
        floors_of = declared(probe)
        if package in floors_of:
            finding.declared, site, ladder = floors_of[package]
            finding.package, finding.alias = spellings(probe, package)
            # Each site is asked where it declares this floor, rather than one
            # being read off the other: the two need not agree on the tier any
            # more than on the name (floors spec §3.1), and the issue names both
            # lines whichever half found it -- so a half that filled in only its
            # own would send half its readers to a file with no such line.
            finding.site, finding.table = _pixi_site(probe, finding.package, site)
            finding.requirements = _pypi_site(probe, finding.package)
    if package is not None and finding.declared is not None:
        # `package` and not `finding.package`: the scan pins and installs, so it
        # wants the name the resolver knows, where the finding carries the name
        # the issue is keyed on (floors spec §3.6).
        finding.lowest, finding.scanned, blocked = scan(
            probe, package, finding.declared, upper, ladder
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
