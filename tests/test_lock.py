# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""What keeps `pixi.lock` telling the truth about the floors this project declares.

The lock records the project's own requirements twice over: once as the resolved
packages an environment installs, and once as the `requires_dist` metadata of the
editable `tephpy` entry -- a copy of what `requirements/pypi-*.txt` declares,
written by whichever `pixi` run last solved. Nothing regenerates it when those
files change, so raising a floor without re-locking leaves the lock asserting the
old one, and a fresh clone installs from the lock.

That is not hypothetical. Measured on `main` at 2026-09-02, before :pull:`251`
happened to re-solve for an unrelated reason, the lock claimed `matplotlib>=3.10`,
`metpy>=1.6`, `pint>=0.24` and `sphinx-autoapi>=3.3` where the manifest had already
moved to `>=3.11`, `>=1.7`, `>=0.24.4` and `>=3.6.1`. Six floors had been raised
without a re-lock and nothing noticed; the correction arrived buried in a pull
request about documentation tooltips, which is the shape of an error that gets
fixed without ever being seen (:issue:`252`).

`ci-floors` holds the *declared* floors to what actually resolves. This module holds
the *lock* to what is declared, which is the half that had no check.

Deliberately not checked here: whether `requirements/pypi-*.txt` agrees with the
`[tool.pixi.*.dependencies]` conda tables. They legitimately differ -- `matplotlib`
against `matplotlib-base`, and `setuptools` and `setuptools-scm` are declared for
pixi alone (:issue:`152`) -- so that is a different contract, and asserting it here
would be asserting a disagreement is an error when it is the design.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tomllib

import pytest

REPO = Path(__file__).parents[1]

# Everything here is read from the index rather than the working tree, and the
# whole module stands down without one. The conda half of `ci-floors` runs this
# suite in a checkout whose `pyproject.toml` the floors generator has rewritten
# and whose lock it has re-solved from that rewrite, so a working-tree read
# compares two files neither of which this repository committed -- passing
# everywhere and failing once a week, hours after the push, in a job that would
# then file an issue about a floor (:issue:`155`, which has happened twice).
# `tests/test_floors.py::test_no_test_reads_the_manifest_the_floors_job_rewrites`
# is what holds this module to it, and caught this module breaking the rule.
#
# The cost is that an uncommitted edit is invisible here: a floor raised in the
# working tree and not yet committed is not reported until it is. That is the
# right side to err on -- the lock is published from what is committed, and this
# asserts a property of the commit.


def committed(path: str) -> str:
    """Return ``path`` as the repository has it committed, not as it is on disk.

    Parameters
    ----------
    path : str
        A repository-relative path.

    Returns
    -------
    str
        The file's contents at ``HEAD``.

    Notes
    -----
    Carries its own index guard rather than leaving one to each caller: an
    unpacked sdist ships this suite and no repository, where `git` does not skip
    but raises. `tests/test_floors.py::test_every_test_that_shells_out_to_git_is_
    guarded_on_the_index` names a helper guarding itself as the way a call shared
    by several tests is guarded once, and holds this module to it.

    """
    if not (REPO / ".git").exists():
        pytest.skip("no index to read the committed files from")
    return subprocess.run(  # noqa: S603
        ["git", "show", f"HEAD:{path}"],  # noqa: S607
        check=True,
        capture_output=True,
        cwd=REPO,
        text=True,
    ).stdout


#: A requirement, split into the name and everything after it. The specifier is
#: kept as written rather than parsed: this asserts that two files say the same
#: thing, and normalising both sides through a parser would let a difference in
#: how they are *written* pass as agreement.
REQUIREMENT = re.compile(r"([A-Za-z0-9_.-]+)(.*)")

#: The clause naming the extra a requirement belongs to. The lock appends it to
#: every requirement of an optional group; a requirements file never carries one,
#: because there the group is decided by which file the line is in.
EXTRA = re.compile(r"^extra\s*==\s*'([^']+)'$")

#: A marker's top-level conjunctions. Splitting on the word rather than parsing
#: the grammar is enough for what markers this project writes, and a marker whose
#: quoted operand contained ``and`` would split wrongly -- which
#: :func:`test_a_marker_survives_the_extra_being_removed` is what would catch.
CONJUNCTION = re.compile(r"\band\b")


def sources() -> dict[str | None, str]:
    """Return each requirements file, against the extra whose dependencies it declares.

    Returns
    -------
    dict
        ``{extra: filename}``, with ``None`` for ``[project] dependencies``,
        which carries no extra clause in the lock.

    Notes
    -----
    Read from ``[tool.setuptools.dynamic]`` rather than written out here. That
    table is what decides the mapping, and a copy of it in this module would be a
    second place to maintain: an optional group added there and not here would be
    declared by the project, unread by :func:`declared`, and so outside all four
    assertions below -- its floors free to drift with nothing watching. The one
    enumeration this module keeps is the assertion that the derived mapping is
    not empty.

    """
    manifest = tomllib.loads(committed("pyproject.toml"))
    dynamic = manifest["tool"]["setuptools"]["dynamic"]
    found = {None: Path(dynamic["dependencies"]["file"][0]).name}
    for extra, entry in dynamic.get("optional-dependencies", {}).items():
        found[extra] = Path(entry["file"][0]).name
    return found


def split(requirement: str) -> tuple[str, str | None, str]:
    """Split one requirement into what the two sides are compared by.

    Parameters
    ----------
    requirement : str
        A requirement as either file writes it, with or without a marker.

    Returns
    -------
    tuple of (str, str or None, str)
        The normalised name, the extra it belongs to if its marker names one,
        and the specifier with every part of the marker that is *not* the extra
        clause put back on it.

    Notes
    -----
    Both sides go through this, which is the point. An earlier version dropped
    the whole marker from the lock's side while keeping it on the requirements'
    side, so a requirement carrying any other condition --
    ``foo>=1 ; python_version < "3.14"`` -- could never agree however often it
    was re-locked. The failure that produces is worse than a missed drift: a
    report demanding an action that cannot fix it.

    """
    body, _, condition = requirement.partition(";")
    match = REQUIREMENT.match(body.strip())
    extra, kept = None, []
    for part in (p.strip() for p in CONJUNCTION.split(condition) if p.strip()):
        if found := EXTRA.match(part):
            extra = found[1]
        else:
            kept.append(part)
    specifier = match[2].strip()
    if kept:
        specifier = f"{specifier} ; {' and '.join(kept)}".strip()
    return normalise(match[1]), extra, specifier


def normalise(name: str) -> str:
    """Return ``name`` in the form PEP 503 compares by.

    Parameters
    ----------
    name : str
        A distribution name as either file writes it.

    Returns
    -------
    str
        Lower-cased, with runs of the separators folded to a hyphen -- so
        ``setuptools_scm`` in the requirements and ``setuptools-scm`` in the lock
        are the one package they name, and a difference of spelling alone is not
        reported as drift.

    """
    return re.sub(r"[-_.]+", "-", name).lower()


def declared() -> dict[tuple[str, str | None], str]:
    """Return the requirements the project declares, by name and extra.

    Returns
    -------
    dict
        ``{(name, extra): specifier}``, the specifier as written.

    """
    found = {}
    for extra, filename in sources().items():
        for line in committed(f"requirements/{filename}").splitlines():
            entry = line.strip()
            if not entry or entry.startswith("#"):
                continue
            name, own, specifier = split(entry)
            # A requirements file names no extra of its own; the file it is in
            # decides that. Were one to, it would be the line's own claim about
            # where it belongs, and disagreeing with the file is a defect worth
            # surfacing rather than quietly preferring one of the two.
            assert own is None, f"{filename} names an extra in {entry!r}"
            found[(name, extra)] = specifier
    return found


def recorded() -> dict[tuple[str, str | None], str]:
    """Return the requirements the lock records for the editable entry.

    Returns
    -------
    dict
        ``{(name, extra): specifier}``, read from the ``requires_dist`` block of
        the ``pypi: ./`` package.

    Notes
    -----
    The block is located by the package that owns it, and both halves of that are
    load-bearing. The lock writes ``- pypi: ./`` once per environment near the top
    of the file as well, in the list of what that environment installs, where it
    is a reference carrying no metadata -- so the entry wanted is the one in
    ``packages:`` that also names ``tephpy``. And ``requires_dist:`` is not unique
    either: `playwright` and `pyee` each carry one in this lock today. Reading the
    first block found rather than this package's compared the project's
    requirements against `playwright`'s dependencies, which was caught by
    renaming the key and watching the wrong two assertions fail.

    """
    lines = committed("pixi.lock").splitlines()
    found: dict[tuple[str, str | None], str] = {}
    editable = False
    for index, line in enumerate(lines):
        if line.startswith(("- pypi:", "- conda:")):
            editable = line.strip() == "- pypi: ./"
            continue
        if not editable or line.strip() != "requires_dist:":
            continue
        for entry in lines[index + 1 :]:
            if not entry.startswith("  - "):
                break
            name, extra, specifier = split(entry[4:])
            found[(name, extra)] = specifier
        return found
    return found


def test_the_lock_records_the_requirements_it_is_read_for():
    """Both sides are non-empty, so agreement below is agreement about something.

    The failure this guards is not drift but a reader that stopped reading: the
    lock's format shifting, or the anchor of :func:`recorded` matching the wrong
    ``pypi: ./``. Either leaves every assertion below comparing an empty mapping
    with itself and passing, which is a green tick over an empty search.
    """
    assert declared(), "no requirement was read from requirements/"
    assert recorded(), "no requirement was read from the lock's requires_dist"


def test_the_lock_agrees_with_every_declared_floor():
    """No requirement is specified one way in the manifest and another in the lock."""
    source, lock = declared(), recorded()
    differs = {
        key: (lock[key], source[key])
        for key in sorted(lock.keys() & source.keys())
        if lock[key] != source[key]
    }
    assert not differs, (
        "pixi.lock records a different specifier from the one declared "
        f"(lock, declared): {differs} -- re-solve with `pixi install`"
    )


def test_the_lock_records_every_declared_requirement():
    """Nothing the project declares is missing from the lock's own copy of it."""
    missing = sorted(declared().keys() - recorded().keys())
    assert not missing, (
        f"declared in requirements/ but absent from pixi.lock: {missing} "
        "-- re-solve with `pixi install`"
    )


def test_the_lock_records_nothing_the_project_does_not_declare():
    """The lock carries no requirement the project has since stopped declaring.

    The other direction of the test above, and the one a removal breaks: dropping
    a dependency from ``requirements/`` without re-locking leaves the lock still
    asking for it, and only this assertion says so.
    """
    extra = sorted(recorded().keys() - declared().keys())
    assert not extra, (
        f"recorded in pixi.lock but no longer declared: {extra} "
        "-- re-solve with `pixi install`"
    )


def test_every_group_the_project_declares_is_read():
    """The mapping is derived, non-empty, and every file it names is there.

    The check :func:`sources` removes is a copy of ``[tool.setuptools.dynamic]``
    kept in this module. What replaces it is this: a group added to that table
    reaches :func:`declared` on its own, and a table this reader could not
    understand fails here rather than silently yielding fewer groups.
    """
    mapping = sources()
    assert mapping, "no requirements file was derived from [tool.setuptools.dynamic]"
    assert None in mapping, "[project] dependencies names no file"
    unreadable = []
    for name in sorted(mapping.values()):
        try:
            committed(f"requirements/{name}")
        except subprocess.CalledProcessError:
            unreadable.append(name)
    assert not unreadable, (
        f"named in [tool.setuptools.dynamic] but not committed: {unreadable}"
    )


def test_a_marker_survives_the_extra_being_removed():
    """Only the extra clause is taken off a marker; the rest is compared.

    The lock writes an optional group's requirement with ``extra == '...'``
    appended, and the requirements file it came from carries no such clause. Any
    *other* condition belongs to the requirement itself and has to survive, on
    both sides, or it reads as a disagreement no re-lock can settle.
    """
    assert split("foo>=1") == ("foo", None, ">=1")
    assert split("foo>=1 ; extra == 'docs'") == ("foo", "docs", ">=1")
    assert split('foo>=1 ; python_version < "3.14"') == (
        "foo",
        None,
        '>=1 ; python_version < "3.14"',
    )
    assert split("foo>=1 ; python_version < \"3.14\" and extra == 'docs'") == (
        "foo",
        "docs",
        '>=1 ; python_version < "3.14"',
    )
    assert split("foo>=1 ; extra == 'docs' and python_version < \"3.14\"") == (
        "foo",
        "docs",
        '>=1 ; python_version < "3.14"',
    )
