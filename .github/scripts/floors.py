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
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
from typing import TYPE_CHECKING

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from collections.abc import Callable

    Lookup = Callable[[str, str, Version], list[str]]
    Resolved = dict[str, dict[str, tuple[str, str]]]

#: The four dependency tables of floors spec §3.1, by tier.
TABLES: dict[str, tuple[str, ...]] = {
    "core": ("tool", "pixi", "dependencies"),
    "test": ("tool", "pixi", "feature", "test", "dependencies"),
    "docs": ("tool", "pixi", "feature", "docs", "dependencies"),
    "devs": ("tool", "pixi", "feature", "devs", "dependencies"),
}

#: The same four tables as they appear as manifest headers.
HEADERS: dict[str, str] = {
    "core": "[tool.pixi.dependencies]",
    "test": "[tool.pixi.feature.test.dependencies]",
    "docs": "[tool.pixi.feature.docs.dependencies]",
    "devs": "[tool.pixi.feature.devs.dependencies]",
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


def pins(manifest: Path, python: Version, lookup: Lookup = candidates) -> Resolved:
    """Resolve every declared floor to a release the channel carries.

    Parameters
    ----------
    manifest : Path
        The ``pyproject.toml`` to read.
    python : Version
        The interpreter the floors are being resolved against.
    lookup : callable, optional
        The candidate source; defaults to :func:`candidates`.

    Returns
    -------
    dict
        Tier to package to ``(declared, resolved)``.

    Raises
    ------
    FloorError
        If a specifier is not a bare ``>=``, if a floor has no build for
        ``python``, or if a tier converts nothing.

    """
    document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    resolved: Resolved = {}
    for tier, path in TABLES.items():
        node: object = document
        for key in path:
            node = node.get(key, {}) if isinstance(node, dict) else {}
        table: dict[str, tuple[str, str]] = {}
        for package, specifier in sorted(dict(node).items()):  # type: ignore[arg-type]
            if not isinstance(specifier, str) or not FLOOR.match(specifier):
                msg = (
                    f"{tier}: {package} = {specifier!r} is not a bare '>=' floor; "
                    "the generator cannot know which release it floors "
                    "(floors spec §3.2)"
                )
                raise FloorError(msg)
            found = lookup(package, specifier, python)
            if not found:
                msg = (
                    f"{tier}: {package}{specifier} has no build for Python "
                    f"{python} on linux-64 (floors spec §3.2)"
                )
                raise FloorError(msg)
            table[package] = (specifier, found[0])
        if not table:
            msg = f"{tier}: no floors converted; the table is empty or renamed"
            raise FloorError(msg)
        resolved[tier] = table
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
    tiers = {header: tier for tier, header in HEADERS.items()}
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
                    _, pin = resolved[tier][package]
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
    nothing behind. Nothing a tier runs is lost with them: a pixi task may only
    ``depends-on`` a task of its own feature or of the environment it runs in.

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


def report(resolved: Resolved, tier: str) -> str:
    """Render one tier as a step-summary table.

    Parameters
    ----------
    resolved : dict
        The mapping :func:`pins` returned.
    tier : str
        The tier to render.

    Returns
    -------
    str
        GitHub-flavoured Markdown.

    """
    lines = [
        f"### Floors resolved — `{tier}`",
        "",
        "| package | declared | resolved |",
        "|---|---|---|",
    ]
    for package, (declared, pin) in resolved[tier].items():
        lines.append(f"| `{package}` | `{declared}` | `{pin}` |")
    lines.append("")
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
    except FloorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(report(resolved, "core"))
    print(report(resolved, args.tier))
    if args.summary is not None:
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(report(resolved, "core"))
            handle.write(report(resolved, args.tier))

    if args.write:
        text = args.manifest.read_text(encoding="utf-8")
        text = rewrite(text, resolved, relax=args.relax)
        text = environments(text, args.tier, args.python)
        text = features(text, args.tier, args.python)
        args.manifest.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
