#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Resolve tephpy's declared dependency floors to pins (floors spec §3.2).

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import argparse
import functools
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
from typing import TYPE_CHECKING
import urllib.parse
import urllib.request

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.tags import compatible_tags, cpython_tags, platform_tags
from packaging.utils import InvalidWheelFilename, parse_wheel_filename
from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from collections.abc import Callable

    from packaging.tags import Tag

    Lookup = Callable[[str, str, Version], list[str]]
    Resolved = dict[str, dict[str, tuple[str, str, str]]]

#: The four dependency tables of floors spec §3.1, by tier.
TABLES: dict[str, tuple[str, ...]] = {
    "core": ("tool", "pixi", "dependencies"),
    "test": ("tool", "pixi", "feature", "test", "dependencies"),
    "docs": ("tool", "pixi", "feature", "docs", "dependencies"),
    "devs": ("tool", "pixi", "feature", "devs", "dependencies"),
}

#: The `pypi-dependencies` table each tier may declare beside the conda one. A
#: pixi feature takes packages from PyPI as well as from the channel, and a
#: floor declared there is one this job resolves like any other -- from PyPI,
#: because that is the index pixi installs it from (:issue:`151`).
PYPI_TABLES: dict[str, tuple[str, ...]] = {
    "core": ("tool", "pixi", "pypi-dependencies"),
    "test": ("tool", "pixi", "feature", "test", "pypi-dependencies"),
    "docs": ("tool", "pixi", "feature", "docs", "pypi-dependencies"),
    "devs": ("tool", "pixi", "feature", "devs", "pypi-dependencies"),
}

#: The same eight tables as they appear as manifest headers, by tier and by the
#: last element of the table's own name.
HEADERS: dict[str, dict[str, str]] = {
    "core": {
        "dependencies": "[tool.pixi.dependencies]",
        "pypi-dependencies": "[tool.pixi.pypi-dependencies]",
    },
    "test": {
        "dependencies": "[tool.pixi.feature.test.dependencies]",
        "pypi-dependencies": "[tool.pixi.feature.test.pypi-dependencies]",
    },
    "docs": {
        "dependencies": "[tool.pixi.feature.docs.dependencies]",
        "pypi-dependencies": "[tool.pixi.feature.docs.pypi-dependencies]",
    },
    "devs": {
        "dependencies": "[tool.pixi.feature.devs.dependencies]",
        "pypi-dependencies": "[tool.pixi.feature.devs.pypi-dependencies]",
    },
}

ENVIRONMENTS = "[tool.pixi.environments]"

#: Any table of one feature: its dependencies, its tasks, or anything added
#: later. The name stops at the first `.` or `]`, so every table of a feature
#: is matched by the feature it belongs to and not by its own kind.
FEATURE = re.compile(r"^\[tool\.pixi\.feature\.(?P<name>[A-Za-z0-9_-]+)[.\]]")

FLOOR = re.compile(r"^>=(?P<version>[0-9][0-9a-zA-Z.*+!-]*)$")
DECLARATION = re.compile(r'^(?P<name>[A-Za-z0-9._-]+) = "(?P<specifier>[^"]+)"$')


class FloorError(Exception):
    """A declaration the generator will not guess at."""


def tool(name: str) -> str:
    """Resolve an executable off ``PATH`` to an absolute path.

    Every ``subprocess`` call in this job passes a fixed argv whose first
    element came from here, which is what makes the ``S603`` waivers below
    honest: nothing user-supplied reaches the shell, and no partial path is
    resolved at spawn time.

    Parameters
    ----------
    name : str
        The executable to find.

    Returns
    -------
    str
        Its absolute path.

    Raises
    ------
    FloorError
        If the executable is not on ``PATH``.

    """
    found = shutil.which(name)
    if found is None:
        msg = f"{name} is not on PATH"
        raise FloorError(msg)
    return found


def admits(depends: list[str], python: Version) -> bool:
    """Whether a build's ``python`` constraint admits the wanted interpreter.

    Parameters
    ----------
    depends : list of str
        The build's ``depends`` entries, as conda-forge writes them.
    python : Version
        The interpreter the floors are being resolved against.

    Returns
    -------
    bool
        True when the build declares no ``python`` constraint, or one that
        contains ``python``.

    """
    for entry in depends:
        parts = entry.split(maxsplit=1)
        if parts[0] != "python":
            continue
        if len(parts) == 1:
            return True
        try:
            spec = SpecifierSet(
                ",".join(
                    piece if piece[0] in "<>=!~" else f"=={piece}"
                    for piece in parts[1].replace(" ", "").split(",")
                )
            )
        except InvalidSpecifier:
            return True
        return spec.contains(python, prereleases=True)
    return True


def candidates(package: str, specifier: str, python: Version) -> list[str]:
    """Every release satisfying ``specifier`` with a build for ``python``.

    Parameters
    ----------
    package : str
        The conda package name.
    specifier : str
        A conda matchspec suffix, such as ``>=8.1``.
    python : Version
        The interpreter the floors are being resolved against.

    Returns
    -------
    list of str
        Version strings in ascending PEP 440 order, lowest first.

    """
    command = [
        tool("pixi"),
        "search",
        f"{package}{specifier}",
        "--platform",
        "linux-64",
        "--json",
    ]
    out = subprocess.run(  # noqa: S603 -- fixed argv, pixi resolved off PATH
        command, capture_output=True, text=True, check=True
    ).stdout
    # `pixi search` prints "Using channels: ..." before the JSON document.
    document = json.loads(out[out.index("{") :])
    keep: dict[str, Version] = {}
    for entries in document.values():
        for entry in entries:
            if entry["name"] != package:
                continue
            if not admits(entry.get("depends", []), python):
                continue
            try:
                keep[entry["version"]] = Version(entry["version"])
            except InvalidVersion:
                continue
    return [text for text, _ in sorted(keep.items(), key=lambda item: item[1])]


@functools.cache
def _targets(major: int, minor: int) -> frozenset[Tag]:
    """Every wheel tag an installer on this runner accepts for one interpreter.

    The interpreter is a parameter and the platform is not: floors are resolved
    for the Python of floors spec §3.3, which is not the one this generator runs
    under, but for the machine it runs on -- the same runner that then solves the
    generated environment.
    """
    platforms = list(platform_tags())
    return frozenset(
        set(cpython_tags(python_version=(major, minor), platforms=platforms))
        | set(
            compatible_tags(
                python_version=(major, minor),
                interpreter=f"cp{major}{minor}",
                platforms=platforms,
            )
        )
    )


def _installable(entry: dict, targets: frozenset[Tag]) -> bool:
    """Whether one uploaded file is something the target could install."""
    kind = entry.get("packagetype")
    if kind == "sdist":
        return True
    if kind != "bdist_wheel":
        return False
    try:
        *_, tags = parse_wheel_filename(entry.get("filename", ""))
    except InvalidWheelFilename:
        # A name this parser cannot read carries no statement of what it is for,
        # and the reading that keeps the two halves of the job together is the
        # one that does not pin a release on a file it cannot place.
        return False
    return bool(tags & targets)


def releases(package: str, specifier: str, python: Version) -> list[str]:
    """Every PyPI release satisfying ``specifier`` with a file for ``python``.

    The PyPI counterpart of :func:`candidates`, for the floors declared in a
    `pypi-dependencies` table. Yanked files are passed over, so a floor lands
    where `uv --resolution lowest-direct` on the other half of the job lands
    and the two halves do not disagree over a release neither would install.

    A release counts only if it carries a file the target could install: an
    sdist, or a wheel whose tags this interpreter and platform accept. pywin32
    311 publishes fifteen non-yanked wheels and no sdist, every one of them for
    Windows; taken on `requires_python` alone it would be pinned on the Linux
    runner, where nothing can install it (measured 2026-08-15).

    Parameters
    ----------
    package : str
        The PyPI project name.
    specifier : str
        A PEP 440 specifier, such as ``>=1.55``.
    python : Version
        The interpreter the floors are being resolved against.

    Returns
    -------
    list of str
        Version strings in ascending PEP 440 order, lowest first.

    Raises
    ------
    FloorError
        If the index cannot be read.

    """
    url = f"https://pypi.org/pypi/{urllib.parse.quote(package)}/json"
    try:
        # The scheme is fixed above and the path is `quote`-escaped from a name
        # this repository's own manifest declares, so nothing user-supplied
        # reaches the opener.
        with urllib.request.urlopen(url, timeout=30) as response:
            document = json.load(response)
    except (OSError, ValueError) as error:
        msg = f"{package}: PyPI did not answer for {url} ({error})"
        raise FloorError(msg) from error
    try:
        floor = SpecifierSet(specifier)
    except InvalidSpecifier as error:
        msg = f"{package} = {specifier!r} is not a PEP 440 specifier"
        raise FloorError(msg) from error
    targets = _targets(python.major, python.minor)
    keep: dict[str, Version] = {}
    for text, files in document.get("releases", {}).items():
        try:
            version = Version(text)
        except InvalidVersion:
            continue
        if not floor.contains(version):
            continue
        for entry in files:
            if entry.get("yanked"):
                continue
            requires = entry.get("requires_python")
            try:
                admitted = requires is None or SpecifierSet(requires).contains(
                    python, prereleases=True
                )
            except InvalidSpecifier:
                admitted = True
            if admitted and _installable(entry, targets):
                keep[text] = version
                break
    return [text for text, _ in sorted(keep.items(), key=lambda item: item[1])]


def ladder(package: str, specifier: str, python: Version, table: str) -> list[str]:
    """Every release of one declaration, from the index that declaration names.

    Parameters
    ----------
    package : str
        The package name.
    specifier : str
        Its declared floor.
    python : Version
        The interpreter the floors are being resolved against.
    table : str
        ``dependencies`` or ``pypi-dependencies``, as :func:`pins` recorded it.

    Returns
    -------
    list of str
        Version strings in ascending PEP 440 order, lowest first.

    """
    source = releases if table == "pypi-dependencies" else candidates
    return source(package, specifier, python)


def _inline(value: dict) -> str:
    """Render a table entry as the manifest writes it rather than as JSON."""
    body = ", ".join(f"{key} = {json.dumps(item)}" for key, item in value.items())
    return f"{{ {body} }}"


def _resolve(
    tier: str, node: object, table: str, python: Version, lookup: Lookup
) -> dict[str, tuple[str, str, str]]:
    """Resolve one table's floors, skipping the local paths pixi allows."""
    found: dict[str, tuple[str, str, str]] = {}
    entries = dict(node) if isinstance(node, dict) else {}
    for package, specifier in sorted(entries.items()):
        # A `pypi-dependencies` table also carries the project itself, as a
        # local editable path. That is not a floor and pinning it would install
        # a release of tephpy over the checkout under test.
        if table == "pypi-dependencies" and isinstance(specifier, dict):
            if set(specifier) <= {"path", "editable", "git", "branch", "rev", "tag"}:
                continue
            msg = (
                f"{tier}: {package} = {_inline(specifier)} in {table} is "
                "neither a floor this generator can pin nor a source it can "
                "pass over (floors spec §3.2)"
            )
            raise FloorError(msg)
        if not isinstance(specifier, str) or not FLOOR.match(specifier):
            msg = (
                f"{tier}: {package} = {specifier!r} is not a bare '>=' floor; "
                "the generator cannot know which release it floors "
                "(floors spec §3.2)"
            )
            raise FloorError(msg)
        versions = lookup(package, specifier, python)
        if not versions:
            where = "on PyPI" if table == "pypi-dependencies" else "on linux-64"
            msg = (
                f"{tier}: {package}{specifier} has no build for Python "
                f"{python} {where} (floors spec §3.2)"
            )
            raise FloorError(msg)
        found[package] = (specifier, versions[0], table)
    return found


def _declared(node: object) -> set[str]:
    """Every name one table declares, whatever shape its entry takes."""
    return set(node) if isinstance(node, dict) else set()


def _node(document: dict[str, object], path: tuple[str, ...]) -> object:
    """Walk a dotted table path, yielding an empty table where it stops."""
    node: object = document
    for key in path:
        node = node.get(key, {}) if isinstance(node, dict) else {}
    return node


def declarations(manifest: Path) -> dict[str, dict[str, str]]:
    """Which of a tier's two tables declares each of its packages.

    This reads the manifest and stops. :func:`pins` answers the same question
    on its way past, but only by resolving every floor it meets against a live
    index, and the PyPI half of floors spec §3.1 needs the pixi table a package
    is declared in for one reason alone: to say which line to edit. Paying a
    channel search per floor of the manifest to read a table header back would
    put a network between that half and its own issue body.

    Source entries are reported like any other. What table a package is
    declared in is a fact about the manifest, and a reader sent to edit a floor
    that turns out to be a source entry has been sent to the right table.

    Parameters
    ----------
    manifest : Path
        The ``pyproject.toml`` to read.

    Returns
    -------
    dict
        Tier to package to ``dependencies`` or ``pypi-dependencies``.

    """
    document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    found: dict[str, dict[str, str]] = {}
    for tier, path in TABLES.items():
        tables = (("dependencies", path), ("pypi-dependencies", PYPI_TABLES[tier]))
        found[tier] = {
            package: table
            for table, node in tables
            for package in sorted(_declared(_node(document, node)))
        }
    return found


def unpinned(manifest: Path) -> dict[str, dict[str, str]]:
    """Every `pypi-dependencies` entry naming a source rather than a version.

    Reported rather than left implicit: a floors job that exercises fewer
    declarations than are declared reads green for a claim it never tested
    (:issue:`151`).

    Parameters
    ----------
    manifest : Path
        The ``pyproject.toml`` to read.

    Returns
    -------
    dict
        Tier to package to the entry as the manifest writes it.

    """
    document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = {}
    for tier, path in PYPI_TABLES.items():
        node = _node(document, path)
        entries = dict(node) if isinstance(node, dict) else {}
        skipped = {
            package: _inline(value)
            for package, value in sorted(entries.items())
            if isinstance(value, dict)
        }
        if skipped:
            out[tier] = skipped
    return out


def pins(
    manifest: Path,
    python: Version,
    lookup: Lookup = candidates,
    pypi: Lookup = releases,
) -> Resolved:
    """Resolve every declared floor to a release its index carries.

    Parameters
    ----------
    manifest : Path
        The ``pyproject.toml`` to read.
    python : Version
        The interpreter the floors are being resolved against.
    lookup : callable, optional
        The conda candidate source; defaults to :func:`candidates`.
    pypi : callable, optional
        The PyPI candidate source; defaults to :func:`releases`.

    Returns
    -------
    dict
        Tier to package to ``(declared, resolved, table)``.

    Raises
    ------
    FloorError
        If a specifier is not a bare ``>=``, if a floor has no build for
        ``python``, if a tier converts nothing, or if one package is declared
        in both of a tier's tables.

    """
    document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    resolved: Resolved = {}
    for tier, path in TABLES.items():
        conda_table = _node(document, path)
        wheel_table = _node(document, PYPI_TABLES[tier])
        # One name over two tables is one line in this mapping, and the pin
        # would land on whichever of the two the rewrite reached -- so it is
        # refused rather than resolved by ordering. The guard reads the
        # declarations rather than what they resolved to, because `_resolve`
        # passes a source entry over: a package declared as a floor in one table
        # and as a source in the other would otherwise meet no guard at all, and
        # leave the tier taking it from the channel and the index both.
        both = sorted(_declared(conda_table) & _declared(wheel_table))
        if both:
            msg = (
                f"{tier}: {', '.join(both)} declared in both dependency tables; "
                "the generator cannot tell which of the two the tier installs "
                "from (floors spec §3.1)"
            )
            raise FloorError(msg)
        conda = _resolve(tier, conda_table, "dependencies", python, lookup)
        if not conda:
            msg = f"{tier}: no floors converted; the table is empty or renamed"
            raise FloorError(msg)
        wheels = _resolve(tier, wheel_table, "pypi-dependencies", python, pypi)
        resolved[tier] = conda | wheels
    return resolved


def rewrite(text: str, resolved: Resolved, relax: str | None = None) -> str:
    """Replace each declared floor with its resolved pin.

    Parameters
    ----------
    text : str
        The manifest source.
    resolved : dict
        The mapping :func:`pins` returned.
    relax : str, optional
        A package left at its declared ``>=`` floor (floors spec §3.4).

    Returns
    -------
    str
        The rewritten manifest source.

    """
    # Both of a tier's tables, because both declare floors and one mapping holds
    # them: :func:`pins` refuses a name declared in both, so the tier alone says
    # which pin a matched line takes.
    tiers = {
        header: tier for tier, headers in HEADERS.items() for header in headers.values()
    }
    out: list[str] = []
    tier: str | None = None
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("["):
            tier = tiers.get(stripped)
        if tier is not None:
            match = DECLARATION.match(stripped)
            if match is not None and match["name"] in resolved[tier]:
                package = match["name"]
                if package != relax:
                    _, pin, _ = resolved[tier][package]
                    out.append(f'{package} = "=={pin}"\n')
                    continue
        out.append(line)
    return "".join(out)


def environments(text: str, tier: str, python: str) -> str:
    """Replace the environment table with the one this tier needs.

    pixi solves every environment a manifest declares, so a manifest carrying
    all of them would let one tier's conflict block another (floors spec §3.3).

    Parameters
    ----------
    text : str
        The manifest source.
    tier : str
        One of ``test``, ``docs``, ``devs``.
    python : str
        The interpreter minor version, such as ``3.12``.

    Returns
    -------
    str
        The rewritten manifest source.

    Raises
    ------
    FloorError
        If the manifest declares no environment table.

    """
    tag = python.replace(".", "")
    name = f"floors-{tier}"
    entry = (
        f'{name} = {{ features = ["{tier}", "py{tag}"], solve-group = "{name}" }}\n\n'
    )
    out: list[str] = []
    inside = False
    seen = False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if inside:
            if not stripped.startswith("["):
                continue
            inside = False
        if stripped == ENVIRONMENTS:
            out.append(line)
            out.append(entry)
            inside, seen = True, True
            continue
        out.append(line)
    if not seen:
        msg = f"{ENVIRONMENTS} not found; the manifest layout has changed"
        raise FloorError(msg)
    return "".join(out)


def features(text: str, tier: str, python: str) -> str:
    """Drop the feature tables the generated environment does not reference.

    :func:`environments` leaves one environment behind, so every feature the
    tier does not carry is defined and used by nothing, and pixi warns once for
    each. That block runs ahead of the solver output in a log the diagnosis
    quotes verbatim into the issue it files, where it is the first thing a
    reader sees and none of it is about tephpy (:issue:`150`). The tables are
    dropped rather than the warning suppressed: the generated manifest is a
    throwaway, and silencing the warning would silence it for the manifest's
    real defects too.

    Every table of a dropped feature goes, not only its dependencies, so a
    feature that gains a table this generator has never heard of still leaves
    nothing behind. No task is left naming one that went with them: pixi
    resolves ``depends-on`` over every task the environment carries, so a task
    of one feature may name a task of another and that reference would dangle
    here. Every one in this manifest names a task of its own feature, which
    ``test_the_generated_manifest_leaves_no_task_naming_a_dropped_one`` holds.

    Parameters
    ----------
    text : str
        The manifest source.
    tier : str
        One of ``test``, ``docs``, ``devs``.
    python : str
        The interpreter minor version, such as ``3.12``.

    Returns
    -------
    str
        The rewritten manifest source.

    """
    keep = {tier, f"py{python.replace('.', '')}"}
    out: list[str] = []
    # A table's leading comments and blank line are held back until its header
    # is judged, so a dropped table takes the comments written about it with it
    # rather than leaving them above the table that follows.
    pending: list[str] = []
    dropping = False
    dropped = False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("["):
            match = FEATURE.match(stripped)
            dropping = match is not None and match["name"] not in keep
            if dropping:
                pending.clear()
                dropped = True
                continue
            if dropped and out and out[-1].strip():
                out.append("\n")
            dropped = False
            out.extend(pending)
            pending.clear()
            out.append(line)
            continue
        if dropping:
            continue
        if not stripped or stripped.startswith("#"):
            pending.append(line)
            continue
        out.extend(pending)
        pending.clear()
        out.append(line)
    out.extend(pending)
    return "".join(out)


def report(resolved: Resolved, tier: str, skipped: dict[str, str] | None = None) -> str:
    """Render one tier as a step-summary table.

    Parameters
    ----------
    resolved : dict
        The mapping :func:`pins` returned.
    tier : str
        The tier to render.
    skipped : dict, optional
        The tier's entry in what :func:`unpinned` returned.

    Returns
    -------
    str
        GitHub-flavoured Markdown.

    """
    lines = [
        f"### Floors resolved — `{tier}`",
        "",
        "| package | declared | resolved | declared in |",
        "|---|---|---|---|",
    ]
    for package, (declared, pin, table) in resolved[tier].items():
        header = HEADERS[tier][table]
        lines.append(f"| `{package}` | `{declared}` | `{pin}` | `{header}` |")
    lines.append("")
    for package, entry in (skipped or {}).items():
        # Named rather than passed over quietly: this is the one shape of
        # declaration the generator leaves alone, and a reader of the summary
        # should not have to infer which lines it did not pin (:issue:`151`).
        lines += [f"Not a floor, left alone: `{package} = {entry}`.", ""]
    return "\n".join(lines)


def main() -> int:
    """Run the generator.

    Returns
    -------
    int
        The process exit status.

    """
    parser = argparse.ArgumentParser(description="Resolve tephpy's floors.")
    parser.add_argument("--manifest", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--tier", required=True, choices=["test", "docs", "devs"])
    parser.add_argument("--python", default="3.12")
    parser.add_argument("--relax")
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    python = Version(f"{args.python}.0")
    try:
        resolved = pins(args.manifest, python)
        skipped = unpinned(args.manifest)
    except FloorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    rendered = [
        report(resolved, tier, skipped.get(tier)) for tier in ("core", args.tier)
    ]
    for text in rendered:
        print(text)
    if args.summary is not None:
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.writelines(rendered)

    if args.write:
        text = args.manifest.read_text(encoding="utf-8")
        text = rewrite(text, resolved, relax=args.relax)
        text = environments(text, args.tier, args.python)
        text = features(text, args.tier, args.python)
        args.manifest.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
