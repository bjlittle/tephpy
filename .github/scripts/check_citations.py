#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that every design-specification citation resolves (docs spec §3.6).

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    import types

REPO = Path(__file__).resolve().parents[2]
SPECS = REPO / "docs" / "src" / "developer" / "specs"
GRAMMAR = REPO / "docs" / "src" / "_ext" / "citations.py"
EXCLUDED = ("docs/src/developer/plans/",)


def display(path: Path) -> str:
    """Render ``path`` relative to the repository when it lies inside it.

    Parameters
    ----------
    path : Path
        The path to render.

    Returns
    -------
    str
        The relative path, or the path unchanged when it is outside the repository
        — which is the case under ``tmp_path`` in the tests.

    """
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _grammar() -> types.ModuleType:
    """Load the citation grammar shared with the docs build (docs spec §3.7).

    It lives under ``docs/`` rather than beside this script because ``MANIFEST.in``
    prunes ``.github`` while the rest of ``docs/`` ships, and the Sphinx extension
    that shares it must import from a path an sdist carries. This script only ever
    runs in a checkout, so it is the one that reaches across.

    Returns
    -------
    module
        The loaded ``citations`` module.

    """
    # The file is checked for rather than the ``ModuleSpec``: a spec is returned
    # populated even for a path that does not exist, and the absence surfaces as
    # a ``FileNotFoundError`` out of ``exec_module`` instead — which is the one
    # realistic failure here, and the message below is what it deserves.
    if not GRAMMAR.is_file():
        print(f"cannot load the citation grammar from {display(GRAMMAR)}")
        raise SystemExit(1)
    spec = importlib.util.spec_from_file_location("citations", GRAMMAR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


citations = _grammar()

ANCHOR = citations.ANCHOR
HEADING = citations.HEADING
Anchor = citations.Anchor
read_lines = citations.read_lines
citation_pattern = citations.citation_pattern


def collect_anchors(
    specs: Iterable[Path],
) -> tuple[dict[str, Anchor], dict[Path, str]]:
    """Read the anchor registry, rendering a duplicate the way this gate does.

    The grammar raises rather than reporting, because it is shared with the docs
    build (docs spec §3.7) and has no terminal of its own. The repository root a
    path is rendered against is known here, and not there.

    Parameters
    ----------
    specs : iterable of Path
        The specification documents to read.

    Returns
    -------
    tuple of (dict, dict)
        The anchors keyed by slug, and the owning prefix keyed by path.

    Raises
    ------
    SystemExit
        When two specifications declare the same slug.

    """
    try:
        return citations.collect_anchors(specs)
    except citations.DuplicateAnchorError as duplicate:
        first, second = duplicate.first, duplicate.second
        print(
            f"duplicate anchor '{duplicate.slug}': "
            f"{display(first.path)}:{first.line} and "
            f"{display(second.path)}:{second.line}"
        )
        raise SystemExit(1) from None


@dataclass(frozen=True)
class Violation:
    """One failed assertion, rendered as ``path:line: message``."""

    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        """Render the violation for the terminal.

        Returns
        -------
        str
            The violation as ``path:line: message``, path relative to the repository.

        """
        return f"  {display(self.path)}:{self.line}: {self.message}"


def check_citations(
    paths: Iterable[Path],
    anchors: dict[str, Anchor],
    owners: dict[Path, str],
) -> list[Violation]:
    """Assert that every citation names an anchor that exists.

    A prefix carries only to the end of its run — the comma- or solidus-separated
    compound of docs spec §3.2. Carrying it to the end of the physical line instead
    lets it cross a sentence boundary: a bare ``§N`` opening the next sentence would
    inherit the namespace of a prefixed citation earlier in the line, rather than
    falling back to the containing document as docs spec §3.2 requires.

    Parameters
    ----------
    paths : iterable of Path
        The files to scan.
    anchors : dict
        The anchor registry from :func:`collect_anchors`.
    owners : dict
        The owning prefix of each specification, from :func:`collect_anchors`.

    Returns
    -------
    list of Violation
        One entry per unresolved citation.

    """
    pattern = citation_pattern(anchors)
    violations: list[Violation] = []
    for path in paths:
        own = owners.get(path)
        text = path.read_text(encoding="utf-8")
        for number, line in citations.source_lines(path, text):
            for citation in citations.scan(line, pattern, own):
                if citation.slug is None:
                    violations.append(
                        Violation(
                            path,
                            number,
                            f"'§{citation.number}' has no prefix; "
                            f"write 'spec §{citation.number}'",
                        )
                    )
                elif citation.slug not in anchors:
                    violations.append(
                        Violation(
                            path,
                            number,
                            f"'§{citation.number}' → no anchor '#{citation.slug}'",
                        )
                    )
    return violations


def check_anchors(
    specs: Iterable[Path],
    owners: dict[Path, str],
) -> list[Violation]:
    """Assert that anchors and numbered headings agree.

    Keying: every anchor sits immediately above the heading it is numbered for.
    Coverage: every numbered heading carries an anchor.

    Both directions of the adjacency are walked, because neither alone is enough.
    Reading down from each heading catches one with no anchor, or with the wrong
    one; reading down from each anchor catches one whose heading has been deleted
    from under it. An orphan of that kind is invisible to the heading pass — there
    is no heading left to start from — yet :func:`collect_anchors` still registers
    it, so citations go on resolving to a target that names no section.

    The anchor registry is not consulted. Both properties are local to one
    document — the heading's number and the line above it — and reading them
    from the file rather than the registry is what lets this catch an anchor
    that :func:`collect_anchors` recorded happily but keyed to the wrong
    heading.

    Parameters
    ----------
    specs : iterable of Path
        The specification documents to check.
    owners : dict
        The owning prefix of each specification, from :func:`collect_anchors`.

    Returns
    -------
    list of Violation
        One entry per mis-keyed or unanchored heading.

    """
    violations: list[Violation] = []
    for spec in specs:
        prefix = owners.get(spec)
        if prefix is None:
            violations.append(Violation(spec, 1, "specification declares no anchors"))
            continue
        text = spec.read_text(encoding="utf-8")
        lines = text.splitlines()
        for number, line in read_lines(text):
            heading = HEADING.match(line)
            if heading is None:
                continue
            expected = f"{prefix}-{heading['num'].replace('.', '-')}"
            above = lines[number - 2].strip() if number >= 2 else ""
            match = ANCHOR.match(above)
            if match is None:
                violations.append(
                    Violation(
                        spec,
                        number,
                        f"heading carries no anchor; add ({expected})=",
                    )
                )
            elif f"{match['slug']}-{match['num']}" != expected:
                violations.append(
                    Violation(
                        spec,
                        number,
                        f"anchor '{above}' should be '({expected})='",
                    )
                )
        for number, line in read_lines(text):
            anchor = ANCHOR.match(line)
            if anchor is None:
                continue
            below = lines[number].strip() if number < len(lines) else ""
            if HEADING.match(below) is None:
                slug = f"{anchor['slug']}-{anchor['num']}"
                violations.append(
                    Violation(
                        spec,
                        number,
                        f"anchor '{slug}' names no heading; citations to it "
                        f"resolve to nothing",
                    )
                )
    return violations


def corpus() -> list[Path]:
    """Enumerate the files the citation rule governs.

    The corpus is derived, not declared (docs spec §3.6): every text file the
    repository tracks, less the plans, whose citations are frozen with them
    (docs spec §3.4). Naming the corpus by glob fails the way a hand-maintained
    registry fails — by silently not covering something. It did: a glob of
    ``tests/**/*.py`` left ``tests/fixtures/io/README.md`` and its two citations
    outside the check, along with those in ``pyproject.toml`` and the
    specifications' own ``index.rst``.

    Returns
    -------
    list of Path
        The tracked text files, sorted. A file that is not UTF-8 is not text, and
        is dropped — the baseline images and the fixture archives.

    """
    git = shutil.which("git")
    if git is None:
        print("git is not on PATH, so the corpus cannot be enumerated")
        raise SystemExit(1)
    listing = subprocess.run(  # noqa: S603 -- fixed argv, git resolved off PATH
        [git, "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    paths = []
    for name in listing.split("\0"):
        if not name or name.startswith(EXCLUDED):
            continue
        path = REPO / name
        try:
            path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        paths.append(path)
    return sorted(paths)


def main() -> int:
    """Run the three assertions over the corpus.

    Returns
    -------
    int
        ``0`` when every assertion holds, ``1`` otherwise.

    """
    specs = sorted(SPECS.glob("*.md"))
    if not specs:
        print(f"no specifications found under {SPECS.relative_to(REPO)}")
        return 1
    anchors, owners = collect_anchors(specs)
    paths = corpus()
    groups = {
        "Unresolved citations": check_citations(paths, anchors, owners),
        "Anchor problems": check_anchors(specs, owners),
    }
    total = sum(len(found) for found in groups.values())
    if total == 0:
        print(
            f"citations ok: {len(anchors)} anchors, {len(paths)} files (docs spec §3.6)"
        )
        return 0
    for heading, found in groups.items():
        if found:
            print(f"{heading} ({len(found)}):")
            for violation in found:
                print(violation)
    return 1


if __name__ == "__main__":
    sys.exit(main())
