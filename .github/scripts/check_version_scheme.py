#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check the declared ``setuptools_scm`` floor knows the version scheme.

``tests/test_api_docstrings.py`` asks the same question of whichever
``setuptools_scm`` is installed, which in a pull request is the lockfile's --
newer than the floor, and where a scheme the floor has never heard of is
registered and passes. The only job installing the declared floor is
``ci-floors``, and that runs weekly or on demand, never as a pull-request
gate. So a scheme rename made without the accompanying floor bump would pass
every check, merge, and leave builds at a supported dependency version broken
until the scheduled job noticed (:issue:`228`).

This closes that window without waiting a week. It resolves the lowest release
satisfying the declared floor, installs exactly that release into a throwaway
environment, and reports whether the configured scheme is among the ones it
registers.

Installed rather than read from the wheel, and the distinction is not
pedantry: from ``setuptools_scm`` 10 the schemes are registered by its
``vcs-versioning`` dependency and not by ``setuptools_scm`` itself, so the
wheel's own ``entry_points.txt`` lists none of them and reading it reports
every scheme as missing. What a floor knows is what that floor *resolves to*,
dependencies included.

Left to itself the mismatch surfaces as a bare ``AssertionError`` raised inside
``setuptools_scm``, naming neither the scheme nor the version that lacks it.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import urllib.request

REPO = Path(__file__).parents[2]

#: The distribution whose floor governs the scheme.
PACKAGE = "setuptools_scm"

#: The entry-point group version schemes are registered under.
GROUP = "setuptools_scm.version_scheme"

#: Printed by the throwaway environment: what it registers, one per line.
_LISTING = (
    "from importlib.metadata import entry_points\n"
    "print(chr(10).join(e.name for e in "
    f"entry_points().select(group={GROUP!r})))"
)

#: PyPI is the only source that knows which releases exist. The floors job
#: reads the same index for the same reason (``floors.py``).
INDEX = "https://pypi.org/pypi/{package}/json"


def committed_manifest() -> str:
    """Return the manifest this repository declares, not the one it was given.

    The conda half of ``ci-floors`` rewrites ``pyproject.toml`` in the checkout
    it runs from, so anything asserting about the declared floors has to read
    them from the index (:issue:`155`).

    Returns
    -------
    str
        The committed ``pyproject.toml``.
    """
    return subprocess.run(
        ["git", "show", "HEAD:pyproject.toml"],  # noqa: S607
        check=True,
        capture_output=True,
        cwd=REPO,
        text=True,
    ).stdout


def declared(manifest: str) -> tuple[str, str]:
    """Return the declared floor specifier and the configured scheme.

    Parameters
    ----------
    manifest : str
        The ``pyproject.toml`` text.

    Returns
    -------
    tuple of str
        The ``setuptools_scm`` requirement from ``[build-system]``, and the
        ``version_scheme`` from ``[tool.setuptools_scm]``.
    """
    parsed = tomllib.loads(manifest)
    requires = parsed["build-system"]["requires"]
    floor = next(
        item for item in requires if item.replace("-", "_").startswith(PACKAGE)
    )
    return floor, parsed["tool"]["setuptools_scm"]["version_scheme"]


def lowest(specifier: str, timeout: float = 30.0) -> tuple[str, str]:
    """Return the lowest release satisfying `specifier`, and its wheel URL.

    Parameters
    ----------
    specifier : str
        A requirement such as ``"setuptools_scm>=10"``.
    timeout : float, optional
        The request timeout in seconds.

    Returns
    -------
    tuple of str
        The version, and the URL of a wheel for it.
    """
    from packaging.requirements import Requirement  # noqa: PLC0415
    from packaging.version import InvalidVersion, Version  # noqa: PLC0415

    requirement = Requirement(specifier)
    url = INDEX.format(package=urllib.request.quote(requirement.name))
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
        releases = json.load(response)["releases"]

    candidates = []
    for raw, files in releases.items():
        try:
            version = Version(raw)
        except InvalidVersion:  # pragma: no cover -- defensive
            continue
        if version.is_prerelease or raw not in requirement.specifier:
            continue
        # A yanked release is not what a resolver reaches for, so it is not
        # what the floor means. `setuptools_scm` 10.0.1 is yanked, and taking
        # it as the floor would report on a release nothing installs.
        wheels = [
            entry
            for entry in files
            if entry["filename"].endswith(".whl") and not entry.get("yanked")
        ]
        if wheels:
            candidates.append((version, raw, wheels[0]["url"]))
    if not candidates:
        msg = f"no release satisfies {specifier!r}"
        raise RuntimeError(msg)
    _, raw, wheel = min(candidates, key=lambda entry: entry[0])
    return raw, wheel


def schemes(version: str, timeout: float = 300.0) -> set[str]:
    """Return the version schemes an installed release registers.

    Installed into a throwaway environment rather than read from the wheel.
    The shortcut of reading ``entry_points.txt`` is wrong here, and wrong in a
    way that reports every scheme as missing: from ``setuptools_scm`` 10 the
    schemes are registered by its ``vcs-versioning`` dependency, not by
    ``setuptools_scm`` itself, so the wheel's own table lists none of them.
    What the floor knows is what the floor *resolves to*, dependencies
    included.

    Parameters
    ----------
    version : str
        The release to install.
    timeout : float, optional
        The install timeout in seconds.

    Returns
    -------
    set of str
        The names registered under :data:`GROUP` by everything installed.
    """
    with tempfile.TemporaryDirectory() as scratch:
        env = Path(scratch) / "venv"
        subprocess.run(  # noqa: S603
            [sys.executable, "-m", "venv", str(env)], check=True, timeout=timeout
        )
        python = env / "bin" / "python"
        subprocess.run(  # noqa: S603
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--quiet",
                f"{PACKAGE}=={version}",
            ],
            check=True,
            timeout=timeout,
        )
        listing = subprocess.run(  # noqa: S603
            [
                str(python),
                "-c",
                _LISTING,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        ).stdout
    return {line.strip() for line in listing.splitlines() if line.strip()}


def main() -> int:
    """Check the declared floor registers the configured scheme.

    Returns
    -------
    int
        ``0`` when it does, ``1`` otherwise.
    """
    floor, scheme = declared(committed_manifest())
    version, _ = lowest(floor)
    registered = schemes(version)
    if not registered:
        print(f"{PACKAGE} {version} registers no {GROUP} entry points")
        return 1
    if scheme not in registered:
        print(
            f"pyproject names version_scheme {scheme!r}, which the declared "
            f"floor does not know.\n\n"
            f"  declared floor : {floor}\n"
            f"  lowest release : {PACKAGE} {version}\n"
            f"  it registers   : {sorted(registered)}\n\n"
            f"Raise the floor to a release that registers {scheme!r}, or keep "
            f"the name that floor knows (:issue:`228`)."
        )
        return 1
    print(
        f"version scheme ok: {scheme!r} is registered by {PACKAGE} {version}, "
        f"the lowest release satisfying {floor!r}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
