# API Version Stamps, Phase 2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The `versionadded` gate survives a release: released objects keep the version a committed snapshot records, new objects cite the version the next tag will carry, and the release runbook writes the snapshot and merges back through a branch that lets a stamp be fixed — so the v0.1.0 release candidate's merge-back leaves `main` green.

**Architecture:** Everything lives in the existing gate, `.github/scripts/check_api_docstrings.py`. It gains a snapshot reader and writer, a third argument to `check_versionadded`, and a `--write-snapshot` command. No snapshot file is committed by this plan: with none, the rule is exactly today's, and the release candidate's freeze writes the first. The tests in `tests/test_api_docstrings.py` grow to cover each rule, the file, the command, and — through a git repository built in a temporary directory — the version scheme's behaviour the design depends on. The style guide and the runbook say what to do.

**Tech Stack:** Python 3.12+, `argparse`, `packaging.version`, `setuptools_scm` (`semver-pep440-release-branch`), pytest, pixi, pre-commit, reStructuredText.

**Spec:** [`../specs/2026-09-15-api-stamps-design.md`](../specs/2026-09-15-api-stamps-design.md) — cited below as `stamps spec §N`. Read it alongside this plan; every task argues from it.

## Global Constraints

- Every `.py` file carries the BSD copyright header (ruff `CPY001`).
- `line-length = 88`; ruff `select = ["ALL"]`. For `.github/scripts/*.py` only `FBT001`, `T201` and `INP001` are waived, so an exception's message is built in a variable before it is raised (`EM102`). For `tests/*` the waivers are `ANN001`, `ANN003`, `ANN201`, `ANN202`, `DTZ001`, `SLF001` and `D103`; a `subprocess.run` of `git` carries `# noqa: S603` and `# noqa: S607` as `tests/committed.py` does.
- `[tool.pytest.ini_options]` sets `filterwarnings = ["error"]`.
- A test that runs `git` — or a helper that does — carries its own guard naming `.git`, because `tests/test_floors.py::test_every_call_that_shells_out_to_git_is_guarded` requires it.
- A test reads `pyproject.toml` through `tests.committed.committed_manifest()`, never from the working tree (`tests/test_floors.py::test_no_test_reads_the_manifest_the_floors_job_rewrites`).
- **Citations are bare, name leaves, and never split from their prefix by a line break** — not even across two string literals. `stamps spec §3` has subsections, so cite `stamps spec §3.1` to `§3.4`, never `§3`: a container citation outside the specifications is a new row in `tests/test_citations.py`'s census.
- A GitHub reference is ``:issue:`N``` in Python and reStructuredText.
- **Do not commit `.github/api-surface.txt`.** The first snapshot is written at the release candidate's freeze, not here (`stamps spec §7`).
- `pixi run docs` builds clean; the build is fail-on-warning.
- Verify **after** committing: the pre-commit hooks rewrite files.
- **Mutations run after the task's commit**, and are restored with `git checkout --`, which then restores the committed file. Never mutate a file whose new content is not yet committed.

---

## What This Plan Measured Before It Was Written

Established 2026-09-15 on `main` at `b8e5cb1`.

**1. The failure and its timing.** `stamps spec §1`'s table: on `v0.1.x` at and past `v0.1.0rc1` the target stays `0.1.0`; `main` after merging a tag back derives `0.2.0.dev` and three tests fail. This plan's integration test pins that behaviour.

**2. A `pyproject.toml` holding only `[tool.setuptools_scm]` is enough.** In a repository built in a temporary directory with just that table — `local_scheme = "dirty-tag"`, `version_file = "src/tephpy/_version.py"`, `version_scheme = "semver-pep440-release-branch"` — `Configuration.from_file` and `get_version` derived `0.1.0rc1` on an rc tag, and wrote no version file. So Task 3's test needs no `[project]` table.

**3. `main()` takes no arguments today, and two tests call it.** `test_main_reports_the_whole_surface` and `test_the_gate_reports_rather_than_raises` call `gate.main()`. An `argparse` parser reading `sys.argv` would be handed pytest's own arguments there, so `main` takes an explicit `argv` that defaults to empty, and `__main__` passes `sys.argv[1:]`.

**4. Nothing else calls the functions this changes.** `check_api_inventory.py` and `tests/test_docs_api_inventory.py` use `published_objects()` only.

**5. The runbook's task-table test reads table rows only.** `tests/test_contributor_guide.py::test_a_page_with_a_task_table_names_no_task_that_does_not_exist` reads `    * - ``name``` lines, so a `pixi run -e test python …` command in a code block is not read as a task claim.

**6. `MANIFEST.in` prunes `.github`,** so the snapshot never reaches the sdist.

**7. Task 3 moves a quoted count.** Its integration test stands down without a repository, so `floors spec §3.3`'s "Forty-one of the `test` tier's tests guard on a repository" becomes forty-two, as {pull}`325`'s new test did before it. Predicted from `tests/test_floors.py`'s counting; Task 3's Step 6 runs that gate to confirm.

---

### Task 1: The snapshot rule

`stamps spec §3.1` and `stamps spec §3.2`: a recorded object keeps its recorded version, an unrecorded object cites the target, and the snapshot file is read and written by the gate.

**Files:**
- Modify: `.github/scripts/check_api_docstrings.py`
- Modify: `tests/test_api_docstrings.py`

**Interfaces:**
- Consumes: `REPO`, `STAMPED_ROLES`, `PublicObject`, `cited_version` — all already in the script.
- Produces: `SNAPSHOT: Path`, `SNAPSHOT_HEADER: str`, `SnapshotError(ValueError)`, `read_snapshot(path: Path) -> dict[str, str]`, `render_snapshot(entries: Iterable[PublicObject]) -> str`, and `check_versionadded(entries, target, recorded: dict[str, str] | None = None) -> list[str]`. Task 2's `main` and Task 4's runbook test rely on these names.

- [ ] **Step 1: Write the failing tests**

In `tests/test_api_docstrings.py`, immediately after `test_check_without_a_target_still_requires_presence`, add:

```python
def test_a_recorded_object_keeps_its_recorded_version(gate):
    """Released API is held to its snapshot, not to the target (stamps spec §3.1)."""
    snapshot = {"tephpy.thing": "0.1.0"}
    assert gate.check_versionadded([_entry(gate, GOOD)], "0.2.0", snapshot) == []


def test_a_recorded_object_restamped_is_reported(gate):
    """Re-stamping released API is caught even when it matches the target."""
    snapshot = {"tephpy.thing": "0.1.0"}
    problems = gate.check_versionadded([_entry(gate, WRONG_VERSION)], "0.9.9", snapshot)
    assert len(problems) == 1
    assert "released in 0.1.0" in problems[0]


def test_an_unrecorded_object_copying_an_old_stamp_is_reported(gate):
    """The lazy copy: a new function stamped like the one above it."""
    snapshot = {"tephpy.other": "0.1.0"}
    problems = gate.check_versionadded([_entry(gate, GOOD)], "0.2.0", snapshot)
    assert len(problems) == 1
    assert "expected 0.2.0" in problems[0]


def test_an_unrecorded_object_without_a_target_is_checked_for_presence(gate):
    snapshot = {"tephpy.other": "0.1.0"}
    assert gate.check_versionadded([_entry(gate, WRONG_VERSION)], None, snapshot) == []
    missing = gate.check_versionadded([_entry(gate, NO_DIRECTIVE)], None, snapshot)
    assert len(missing) == 1


def test_a_recorded_object_stays_exact_without_a_target(gate):
    """The snapshot half needs no derived version, so a shallow clone keeps it."""
    snapshot = {"tephpy.thing": "0.1.0"}
    problems = gate.check_versionadded([_entry(gate, WRONG_VERSION)], None, snapshot)
    assert len(problems) == 1


def test_a_recorded_object_no_longer_published_is_ignored(gate):
    snapshot = {"tephpy.thing": "0.1.0", "tephpy.removed": "0.1.0"}
    assert gate.check_versionadded([_entry(gate, GOOD)], "0.1.0", snapshot) == []


def _published(gate, name, role, doc):
    """Build a PublicObject named `name`, in `role`, whose docstring is `doc`."""
    return gate.PublicObject(name, role, type("Stub", (), {"__doc__": doc}))


def test_the_snapshot_round_trips_sorted_under_its_header(gate, tmp_path):
    entries = [
        _published(gate, "tephpy.b", "function", GOOD),
        _published(gate, "tephpy.a", "module", WRONG_VERSION),
    ]
    path = tmp_path / "api-surface.txt"
    path.write_text(gate.render_snapshot(entries), encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    assert text.startswith(gate.SNAPSHOT_HEADER)
    assert text[len(gate.SNAPSHOT_HEADER) :].splitlines() == [
        "tephpy.a\tmodule\t0.9.9",
        "tephpy.b\tfunction\t0.1.0",
    ]
    assert gate.read_snapshot(path) == {"tephpy.a": "0.9.9", "tephpy.b": "0.1.0"}


def test_no_snapshot_reads_as_empty(gate, tmp_path):
    """Before the first release there is none, and the rule is phase 1's."""
    assert gate.read_snapshot(tmp_path / "api-surface.txt") == {}


@pytest.mark.parametrize(
    "line",
    [
        "tephpy.a\tmodule",  # a field missing
        "tephpy.a module 0.1.0",  # spaces, not tabs
        "tephpy.a\tgadget\t0.1.0",  # not a role the gate publishes
        "\tmodule\t0.1.0",  # an empty name
    ],
)
def test_a_malformed_snapshot_line_fails_rather_than_being_skipped(
    gate, tmp_path, line
):
    """A snapshot read as empty would return the gate to phase 1 in silence."""
    path = tmp_path / "api-surface.txt"
    path.write_text(f"{gate.SNAPSHOT_HEADER}{line}\n", encoding="utf-8")
    with pytest.raises(gate.SnapshotError, match=r"api-surface\.txt:4"):
        gate.read_snapshot(path)
```

And change `test_every_published_docstring_is_stamped`'s assertion so the real package is checked against the real snapshot — replace

```python
    problems = gate.check_versionadded(gate.published_objects(), gate.target_version())
```

with

```python
    problems = gate.check_versionadded(
        gate.published_objects(),
        gate.target_version(),
        gate.read_snapshot(gate.SNAPSHOT),
    )
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pixi run -e test pytest tests/test_api_docstrings.py -q --no-cov`
Expected: 13 failed. The six new rule tests FAIL with `TypeError: check_versionadded() takes 2 positional arguments but 3 were given`. The six file tests and `test_every_published_docstring_is_stamped` FAIL with `AttributeError`, naming whichever of `render_snapshot`, `read_snapshot` or `SNAPSHOT_HEADER` each reaches first — `SNAPSHOT_HEADER` for the four malformed-line cases. Every other test passes.

- [ ] **Step 3: Add the snapshot's constants and error**

In `.github/scripts/check_api_docstrings.py`, immediately after the line `STAMPED_ROLES = ("module", "class", "exception", "function", "method", "property")`, add:

```python

#: The published API as the last release recorded it (stamps spec §3.2). Written
#: at each release's freeze by ``--write-snapshot``: an object it records keeps
#: the version recorded there, and an object it does not cites the target.
SNAPSHOT = REPO / ".github" / "api-surface.txt"

#: The comment that opens :data:`SNAPSHOT`. The reader skips a line starting ``#``.
SNAPSHOT_HEADER = (
    "# The published API as the last release recorded it (stamps spec §3.2).\n"
    "# Written by check_api_docstrings.py --write-snapshot at each release freeze,\n"
    "# never by hand. One line per object: dotted name, role, cited version.\n"
)


class SnapshotError(ValueError):
    """A snapshot line the reader cannot parse.

    Raised rather than skipped, because a snapshot read as empty would return the
    gate to its phase-1 rule without a word (stamps spec §3.2).
    """
```

- [ ] **Step 4: Add the reader and writer, and give the rule its third argument**

Replace the whole of `check_versionadded` — from `def check_versionadded(` to its `return problems` — with:

```python
def _stamp(entry: PublicObject) -> str | None:
    """Return the version an entry's docstring cites.

    Parameters
    ----------
    entry : PublicObject
        The published object.

    Returns
    -------
    str or None
        What :func:`cited_version` reads from its docstring.
    """
    return cited_version(inspect.getdoc(entry.obj) or "")


def read_snapshot(path: Path) -> dict[str, str]:
    """Read the snapshot of the published API (stamps spec §3.2).

    Parameters
    ----------
    path : Path
        The snapshot file.

    Returns
    -------
    dict of str to str
        Each recorded object's dotted name, mapped to the version it was released
        with. Empty when there is no file, which is the case until the first
        release writes one.

    Raises
    ------
    SnapshotError
        When a line is not a dotted name, a published role and a version,
        separated by tabs.
    """
    if not path.is_file():
        return {}
    recorded: dict[str, str] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split("\t")
        if (
            len(fields) != 3
            or not all(field.strip() for field in fields)
            or fields[1] not in STAMPED_ROLES
        ):
            msg = (
                f"{path.name}:{number}: expected a dotted name, a role and a "
                f"version separated by tabs, got {line!r}"
            )
            raise SnapshotError(msg)
        recorded[fields[0]] = fields[2]
    return recorded


def render_snapshot(entries: Iterable[PublicObject]) -> str:
    """Render the snapshot of the published API (stamps spec §3.2).

    Parameters
    ----------
    entries : iterable of PublicObject
        The published objects, each already carrying a ``versionadded``.

    Returns
    -------
    str
        :data:`SNAPSHOT_HEADER`, then one tab-separated line per object -- dotted
        name, role, cited version -- sorted by dotted name.
    """
    ordered = sorted(entries, key=lambda item: item.name)
    lines = [f"{entry.name}\t{entry.role}\t{_stamp(entry)}\n" for entry in ordered]
    return SNAPSHOT_HEADER + "".join(lines)


def check_versionadded(
    entries: Iterable[PublicObject],
    target: str | None,
    recorded: dict[str, str] | None = None,
) -> list[str]:
    """Check each entry carries the directive, citing the version it should.

    An object the snapshot records must cite the version recorded there, which
    needs no derived target and so holds in a shallow clone too; any other object
    must cite `target`, the version the next tag will carry (stamps spec §3.1).
    Before the first release there is no snapshot, so every object must cite the
    target.

    Parameters
    ----------
    entries : iterable of PublicObject
        The published objects to check.
    target : str or None
        The base version the next tag will carry, or ``None`` to check an
        unrecorded object's presence only (see :func:`target_version`).
    recorded : dict of str to str, optional
        The snapshot, from :func:`read_snapshot`. An object it records that is no
        longer published is ignored.

    Returns
    -------
    list of str
        One line per violation, empty when the corpus is clean.
    """
    recorded = recorded or {}
    problems = []
    for entry in entries:
        cited = _stamp(entry)
        if cited is None:
            problems.append(
                f"{entry.name} ({entry.role}): no versionadded directive in a "
                f"Notes section"
            )
        elif entry.name in recorded:
            if cited != recorded[entry.name]:
                problems.append(
                    f"{entry.name} ({entry.role}): versionadded cites {cited}, but "
                    f"it was released in {recorded[entry.name]}; released API keeps "
                    f"its stamp"
                )
        elif target is not None and cited != target:
            problems.append(
                f"{entry.name} ({entry.role}): versionadded cites {cited}, "
                f"expected {target}"
            )
    return problems
```

- [ ] **Step 5: Have `main` read the snapshot**

In `main`, replace

```python
    stamps = check_versionadded(entries, target)
```

with

```python
    stamps = check_versionadded(entries, target, read_snapshot(SNAPSHOT))
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `pixi run -e test pytest tests/test_api_docstrings.py tests/test_docs_api_inventory.py -q --no-cov`
Expected: PASS. `.github/api-surface.txt` does not exist, so the real package is checked exactly as before.

- [ ] **Step 7: Lint, commit, and verify after the commit**

```bash
pixi run -e devs pre-commit run --files .github/scripts/check_api_docstrings.py tests/test_api_docstrings.py
git add .github/scripts/check_api_docstrings.py tests/test_api_docstrings.py
git commit -m "Hold released API to a snapshot of its stamps"
pixi run -e test pytest tests/test_api_docstrings.py tests/test_citations.py -q --no-cov
git status --short
```

Expected: every hook passes; the tests pass on the committed tree; `git status --short` prints nothing.

- [ ] **Step 8: Prove each half by mutation**

Each block from a clean, committed tree:

```bash
# (a) the snapshot half removed
sed -i 's/        elif entry.name in recorded:/        elif False:/' .github/scripts/check_api_docstrings.py
pixi run -e test pytest tests/test_api_docstrings.py -q --no-cov -k recorded
git checkout -- .github/scripts/check_api_docstrings.py
```
Expected: 3 failed, 3 passed — `test_a_recorded_object_keeps_its_recorded_version`, `test_a_recorded_object_restamped_is_reported` and `test_a_recorded_object_stays_exact_without_a_target` FAIL; the other three tests `recorded` selects pass.

```bash
# (b) the target half weakened to "no newer than"
sed -i 's/        elif target is not None and cited != target:/        elif target is not None and cited > target:/' .github/scripts/check_api_docstrings.py
pixi run -e test pytest tests/test_api_docstrings.py -q --no-cov -k copying
git checkout -- .github/scripts/check_api_docstrings.py
```
Expected: `test_an_unrecorded_object_copying_an_old_stamp_is_reported` FAILS.

```bash
# (c) a malformed line skipped instead of reported
sed -i 's/            raise SnapshotError(msg)/            continue/' .github/scripts/check_api_docstrings.py
pixi run -e test pytest tests/test_api_docstrings.py -q --no-cov -k malformed
git checkout -- .github/scripts/check_api_docstrings.py
```
Expected: all four `test_a_malformed_snapshot_line_fails_rather_than_being_skipped` cases FAIL.

Finish with `git status --short` printing nothing.

---

### Task 2: The `--write-snapshot` command

`stamps spec §3.2`: the gate writes the snapshot, and refuses while any stamp fails or no target can be derived.

**Files:**
- Modify: `.github/scripts/check_api_docstrings.py`
- Modify: `tests/test_api_docstrings.py`

**Interfaces:**
- Consumes: Task 1's `SNAPSHOT`, `SNAPSHOT_HEADER`, `SnapshotError`, `read_snapshot`, `render_snapshot`, `check_versionadded`.
- Produces: `parser() -> argparse.ArgumentParser`, `write_snapshot(entries, target, stamps) -> int`, and `main(argv: Sequence[str] = ()) -> int`. Task 4's runbook test reads `parser()`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_api_docstrings.py`, immediately after `test_a_malformed_snapshot_line_fails_rather_than_being_skipped`, add:

```python
def test_write_snapshot_records_each_object_and_its_version(
    gate, tmp_path, monkeypatch
):
    """The release freeze's command (stamps spec §3.2)."""
    path = tmp_path / "api-surface.txt"
    monkeypatch.setattr(gate, "SNAPSHOT", path)
    monkeypatch.setattr(gate, "published_objects", lambda: [_entry(gate, GOOD)])
    monkeypatch.setattr(gate, "target_version", lambda: "0.1.0")
    assert gate.main(["--write-snapshot"]) == 0
    assert gate.read_snapshot(path) == {"tephpy.thing": "0.1.0"}


def test_write_snapshot_refuses_while_a_stamp_fails(
    gate, tmp_path, monkeypatch, capsys
):
    """A snapshot never records a stamp the rule did not accept."""
    path = tmp_path / "api-surface.txt"
    path.write_text("# an existing snapshot\n", encoding="utf-8")
    monkeypatch.setattr(gate, "SNAPSHOT", path)
    monkeypatch.setattr(
        gate, "published_objects", lambda: [_entry(gate, WRONG_VERSION)]
    )
    monkeypatch.setattr(gate, "target_version", lambda: "0.1.0")
    assert gate.main(["--write-snapshot"]) == 1
    assert path.read_text(encoding="utf-8") == "# an existing snapshot\n"
    assert "snapshot not written" in capsys.readouterr().out


def test_write_snapshot_refuses_without_a_target(gate, tmp_path, monkeypatch, capsys):
    """Unrecorded stamps went unchecked, so they are not recorded."""
    path = tmp_path / "api-surface.txt"
    monkeypatch.setattr(gate, "SNAPSHOT", path)
    monkeypatch.setattr(gate, "published_objects", lambda: [_entry(gate, GOOD)])
    monkeypatch.setattr(gate, "target_version", lambda: None)
    assert gate.main(["--write-snapshot"]) == 1
    assert not path.exists()
    assert "no version could be derived" in capsys.readouterr().out


def test_the_gate_reads_the_snapshot(gate, tmp_path, monkeypatch, capsys):
    """Run plainly, a recorded object is held to its recorded version."""
    path = tmp_path / "api-surface.txt"
    record = "tephpy.thing\tfunction\t0.0.1\n"
    path.write_text(gate.SNAPSHOT_HEADER + record, encoding="utf-8")
    monkeypatch.setattr(gate, "SNAPSHOT", path)
    monkeypatch.setattr(gate, "published_objects", lambda: [_entry(gate, GOOD)])
    monkeypatch.setattr(gate, "target_version", lambda: "0.1.0")
    assert gate.main() == 1
    assert "released in 0.0.1" in capsys.readouterr().out


def test_the_gate_reports_an_unreadable_snapshot(gate, tmp_path, monkeypatch, capsys):
    """Reported rather than raised, like every other failure of this gate."""
    path = tmp_path / "api-surface.txt"
    path.write_text(gate.SNAPSHOT_HEADER + "not a record\n", encoding="utf-8")
    monkeypatch.setattr(gate, "SNAPSHOT", path)
    monkeypatch.setattr(gate, "published_objects", lambda: [_entry(gate, GOOD)])
    monkeypatch.setattr(gate, "target_version", lambda: "0.1.0")
    assert gate.main() == 1
    assert "cannot read the API snapshot" in capsys.readouterr().out
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pixi run -e test pytest tests/test_api_docstrings.py -q --no-cov`
Expected: the three `write_snapshot` tests FAIL with `TypeError: main() takes 0 positional arguments but 1 was given`; `test_the_gate_reports_an_unreadable_snapshot` FAILS with `SnapshotError` raised out of `main`. `test_the_gate_reads_the_snapshot` passes already — Task 1 made `main` read the snapshot — and every other test passes.

- [ ] **Step 3: Import what the command needs**

In the import block, add `import argparse` immediately above `import ast`, and change `from collections.abc import Iterable` under `if TYPE_CHECKING:` to `from collections.abc import Iterable, Sequence`.

- [ ] **Step 4: Add the parser and the writer, and give `main` its arguments**

Replace this opening of `main`:

```python
def main() -> int:
    """Run the gate over the published API.

    Returns
    -------
    int
        ``0`` when clean, ``1`` when any rule reports a violation.
    """
    entries = published_objects()
    target = target_version()
    # Two rules, reported separately: the versionadded rule is total and
    # exact, the raises rule is narrow by design (:issue:`224`). Folding them
    # into one verdict would let the narrower one argue for switching off the
    # other.
    stamps = check_versionadded(entries, target, read_snapshot(SNAPSHOT))
```

with:

```python
def parser() -> argparse.ArgumentParser:
    """Build the gate's command line.

    Returns
    -------
    argparse.ArgumentParser
        The parser :func:`main` reads its arguments with.
    """
    command = argparse.ArgumentParser(
        description="Check the published API docstrings carry what policy requires."
    )
    command.add_argument(
        "--write-snapshot",
        action="store_true",
        help=(
            "record every published object and the version it cites in "
            ".github/api-surface.txt, as the release freeze does; refused while "
            "a stamp fails or no version can be derived (stamps spec §3.2)"
        ),
    )
    return command


def write_snapshot(
    entries: list[PublicObject], target: str | None, stamps: list[str]
) -> int:
    """Write :data:`SNAPSHOT`, or refuse and say why (stamps spec §3.2).

    Refused while any stamp fails, so a snapshot never records a stamp the rule
    did not accept; and where no target can be derived, because the stamps of the
    objects the last release did not record then went unchecked. A refusal
    leaves an existing snapshot as it was.

    Parameters
    ----------
    entries : list of PublicObject
        The published objects.
    target : str or None
        The base version the next tag will carry.
    stamps : list of str
        The ``versionadded`` rule's violations for `entries`.

    Returns
    -------
    int
        ``0`` when written, ``1`` when refused.
    """
    if stamps:
        print(
            f"snapshot not written: {len(stamps)} of {len(entries)} published API "
            f"objects fail the versionadded rule:\n"
        )
        for line in stamps:
            print(f"  {line}")
        return 1
    if target is None:
        print(
            "snapshot not written: no version could be derived to check the stamps "
            "against -- a shallow clone, or an export carrying no tag"
        )
        return 1
    SNAPSHOT.write_text(render_snapshot(entries), encoding="utf-8")
    print(f"snapshot written: {len(entries)} published objects, in {SNAPSHOT.name}")
    return 0


def main(argv: Sequence[str] = ()) -> int:
    """Run the gate over the published API, or record it.

    Parameters
    ----------
    argv : sequence of str, optional
        The command-line arguments, without the program name. Empty by default,
        so a test calling ``main()`` is not handed pytest's own arguments.

    Returns
    -------
    int
        ``0`` when clean or when the snapshot was written, ``1`` otherwise.
    """
    arguments = parser().parse_args(list(argv))
    entries = published_objects()
    target = target_version()
    try:
        recorded = read_snapshot(SNAPSHOT)
    except SnapshotError as error:
        print(f"cannot read the API snapshot: {error}")
        return 1
    # Two rules, reported separately: the versionadded rule is total and
    # exact, the raises rule is narrow by design (:issue:`224`). Folding them
    # into one verdict would let the narrower one argue for switching off the
    # other.
    stamps = check_versionadded(entries, target, recorded)
    if arguments.write_snapshot:
        return write_snapshot(entries, target, stamps)
```

and at the end of the file replace

```python
    sys.exit(main())
```

with

```python
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run -e test pytest tests/test_api_docstrings.py tests/test_docs_api_inventory.py -q --no-cov`
Expected: PASS.

- [ ] **Step 6: Run the command for real, without writing**

```bash
pixi run -e test python .github/scripts/check_api_docstrings.py
pixi run -e test python .github/scripts/check_api_docstrings.py --help
```

Expected: the first prints `api docstrings ok: 94 published objects …` and exits 0; the second lists `--write-snapshot`. Do not run `--write-snapshot` against the repository — it would create the snapshot this plan must not commit.

- [ ] **Step 7: Lint, commit, and verify after the commit**

```bash
pixi run -e devs pre-commit run --files .github/scripts/check_api_docstrings.py tests/test_api_docstrings.py
git add .github/scripts/check_api_docstrings.py tests/test_api_docstrings.py
git commit -m "Let the stamp gate write the release snapshot"
pixi run -e test pytest tests/test_api_docstrings.py tests/test_citations.py -q --no-cov
git status --short
```

Expected: every hook passes; the tests pass; `git status --short` prints nothing.

- [ ] **Step 8: Prove the refusal by mutation**

```bash
sed -i 's/^    if stamps:$/    if False:/' .github/scripts/check_api_docstrings.py
pixi run -e test pytest tests/test_api_docstrings.py -q --no-cov -k refuses_while
git checkout -- .github/scripts/check_api_docstrings.py
```

Expected: `test_write_snapshot_refuses_while_a_stamp_fails` FAILS. Finish with `git status --short` printing nothing.

---

### Task 3: The version test, and the scheme it depends on

`stamps spec §1`, `stamps spec §3.4`, `stamps spec §6`.

**Files:**
- Modify: `tests/test_api_docstrings.py`
- Modify: `docs/src/developer/specs/2026-08-13-dependency-floors-design.md` (one word)

**Interfaces:**
- Consumes: `gate.REPO`, `gate.target_version` — unchanged by Tasks 1 and 2.
- Produces: nothing a later task reads.

- [ ] **Step 1: Import what the tests need**

In `tests/test_api_docstrings.py`, add `import subprocess` immediately below `from pathlib import Path`, and `from packaging.version import Version` immediately above `import pytest`.

- [ ] **Step 2: Stop the version test asserting one version**

In `test_target_version_uses_the_project_version_scheme`, insert this paragraph into the docstring, directly after its first paragraph (the one ending "so the gate reads the file the build reads."):

```python

    Asserted as a three-component release rather than as ``0.1.0``, which was
    true only until a merge-back moved the target to ``0.2.0`` (stamps spec §1).
```

and replace its last line

```python
    assert gate.target_version() == "0.1.0"
```

with

```python
    target = gate.target_version()
    assert len(Version(target).release) == 3, target
```

- [ ] **Step 3: Write the scheme test**

Append to `tests/test_api_docstrings.py`:

```python
def _git(repo, *args: str):
    """Run ``git`` in `repo` with a throwaway identity and signing turned off.

    Carries its own guard, as ``tests/test_floors.py`` requires of every function
    that runs ``git``: an export of the committed tree has no repository, and there
    this stands down rather than fails.
    """
    if not (REPO / ".git").exists():
        pytest.skip("no repository here, so no git to measure the scheme with")
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=stamps",
            "-c",
            "user.email=stamps@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "tag.gpgsign=false",
            *args,
        ],
        check=True,
        capture_output=True,
    )


def test_the_target_moves_where_the_release_runbook_expects(
    gate, tmp_path, monkeypatch
):
    """The measured version tables of stamps spec §1 and stamps spec §3.4, pinned.

    The design rests on how ``semver-pep440-release-branch`` reads a repository:
    a release branch keeps its target through a release candidate, ``main`` moves
    to the next minor version once a tag is merged back, and a branch whose name
    carries a version is read as a release branch. A ``setuptools_scm`` release
    changing any of the three would break the release runbook without a word, and
    this fails in an ordinary pull request instead.
    """
    scm = tomllib.loads(committed_manifest())["tool"]["setuptools_scm"]
    repo = tmp_path / "repository"
    repo.mkdir()
    table = "".join(f'{key} = "{value}"\n' for key, value in scm.items())
    (repo / "pyproject.toml").write_text(
        f"[tool.setuptools_scm]\n{table}", encoding="utf-8"
    )
    monkeypatch.setattr(gate, "REPO", repo)

    _git(repo, "init", "--initial-branch=main")
    _git(repo, "add", "pyproject.toml")
    _git(repo, "commit", "-m", "start")
    _git(repo, "switch", "-c", "v0.1.x")
    _git(repo, "commit", "--allow-empty", "-m", "release preparation")
    _git(repo, "tag", "-a", "v0.1.0rc1", "-m", "v0.1.0rc1")
    assert gate.target_version() == "0.1.0", "on the release candidate's tag"

    _git(repo, "switch", "main")
    _git(repo, "commit", "--allow-empty", "-m", "a new object on main")
    assert gate.target_version() == "0.1.0", "main, before the merge-back"

    _git(repo, "switch", "-c", "merge-back-v0.1.x", "v0.1.x")
    _git(repo, "merge", "--no-ff", "main", "-m", "merge main in")
    assert gate.target_version() == "0.1.0", (
        "a versioned name reads as the release line"
    )

    _git(repo, "switch", "-c", "merge-back", "v0.1.x")
    _git(repo, "merge", "--no-ff", "main", "-m", "merge main in")
    assert gate.target_version() == "0.2.0", "a versionless name agrees with CI"

    _git(repo, "switch", "main")
    _git(repo, "merge", "--no-ff", "merge-back", "-m", "merge back")
    assert gate.target_version() == "0.2.0", "main, after the merge-back"
```

- [ ] **Step 4: Run the tests**

Run: `pixi run -e test pytest tests/test_api_docstrings.py -q --no-cov -k "scheme or target_moves"`
Expected: 3 passed, no skip — `test_target_version_uses_the_project_version_scheme` and `test_the_target_moves_where_the_release_runbook_expects`, plus the existing `test_the_configured_version_scheme_is_registered`, which `scheme` also selects.

- [ ] **Step 5: Lint, commit, and verify after the commit**

```bash
pixi run -e devs pre-commit run --files tests/test_api_docstrings.py
git add tests/test_api_docstrings.py
git commit -m "Pin the version scheme the release runbook depends on"
pixi run -e test pytest tests/test_api_docstrings.py -q --no-cov
git status --short
```

Expected: every hook passes; the module passes; `git status --short` prints nothing.

- [ ] **Step 6: Move the quoted count, measured**

Run: `pixi run -e test pytest "tests/test_floors.py::test_the_specification_quotes_the_number_of_repository_guarded_tests" -q --no-cov`
Expected: FAIL with `the specification says Forty-one; 42 stand down`, the listing including `tests.test_api_docstrings::test_the_target_moves_where_the_release_runbook_expects`. **If it passes instead, stop and report — the prediction in this plan's measured section is wrong, and the spec's count must not be changed on a guess.**

Then:

```bash
sed -i 's/Forty-one of the `test` tier/Forty-two of the `test` tier/' docs/src/developer/specs/2026-08-13-dependency-floors-design.md
git diff --stat
pixi run -e test pytest "tests/test_floors.py::test_the_specification_quotes_the_number_of_repository_guarded_tests" -q --no-cov
```

Expected: one line changed in the floors specification; the gate PASSES.

- [ ] **Step 7: Commit, and verify after the commit**

```bash
pixi run -e devs pre-commit run --files docs/src/developer/specs/2026-08-13-dependency-floors-design.md
git add docs/src/developer/specs/2026-08-13-dependency-floors-design.md
git commit -m "Count the scheme test among the repository-guarded tests"
git status --short
```

Expected: every hook passes; `git status --short` prints nothing.

---

### Task 4: The policy and the runbook

`stamps spec §3.3` and `stamps spec §4`: the style guide says which version to write, and the runbook writes the snapshot and merges back through `merge-back`.

**Files:**
- Modify: `docs/src/developer/docs-style.rst`
- Modify: `docs/src/developer/release.rst`
- Modify: `tests/test_api_docstrings.py`

**Interfaces:**
- Consumes: Task 1's `SNAPSHOT`; Task 2's `parser()`.
- Produces: nothing a later task reads.

- [ ] **Step 1: Write the failing tests**

In `tests/test_api_docstrings.py`, add two lines at the end of `test_the_policy_is_written_down`:

```python
    assert ".github/api-surface.txt" in style
    assert "--write-snapshot" in style
```

and immediately after that test, add:

```python
def test_the_runbook_writes_the_snapshot_the_gate_reads(gate):
    """The release-day command is one the gate accepts (stamps spec §3.3).

    A runbook step naming a flag the script had since renamed would fail on the
    one commit that gets tagged.
    """
    runbook = (REPO / "docs" / "src" / "developer" / "release.rst").read_text(
        encoding="utf-8"
    )
    assert "check_api_docstrings.py --write-snapshot" in runbook
    assert "--write-snapshot" in gate.parser().format_help()
    assert gate.SNAPSHOT.name in runbook
    assert "git switch -c merge-back " in runbook
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pixi run -e test pytest tests/test_api_docstrings.py -q --no-cov -k "policy or runbook"`
Expected: 2 failed, 1 passed — `test_the_policy_is_written_down` and `test_the_runbook_writes_the_snapshot_the_gate_reads` FAIL, because the style guide names neither the snapshot nor the flag and the runbook names none of the four; Task 3's `test_the_target_moves_where_the_release_runbook_expects`, which `runbook` also selects, passes.

- [ ] **Step 3: Write the policy**

In `docs/src/developer/docs-style.rst`, insert this paragraph immediately before the paragraph that begins ``` ``.github/scripts/check_api_docstrings.py`` is the gate. ```, followed by a blank line:

```rst
Which version to write depends on whether the object has been released. A new
object cites the version the next release will carry, which is the one the gate
names when it fails. An object an earlier release published keeps the version it
was released with, so never re-stamp released API. The gate tells the two apart
by ``.github/api-surface.txt``, the snapshot of the published API that each
release writes with ``check_api_docstrings.py --write-snapshot`` and that no
contributor edits by hand (stamps spec §3.1).
```

- [ ] **Step 4: Write the runbook's step 4**

In `docs/src/developer/release.rst`, replace the whole of step 4:

```rst
4. **Fill in the release metadata.** ``CITATION.cff`` takes ``version`` and
   ``date-released`` (``YYYY-MM-DD``). ``ci-citation`` validates the file, and
   it runs only when that file changes — so this step is the only thing that
   will ever check it.
```

with:

```rst
4. **Fill in the release metadata.** ``CITATION.cff`` takes ``version`` and
   ``date-released`` (``YYYY-MM-DD``). ``ci-citation`` validates the file, and
   it runs only when that file changes — so this step is the only thing that
   will ever check it.

   Then record the published API, which the stamp gate holds every released
   object to from here on (stamps spec §3.3):

   .. code-block:: console

      $ pixi run -e test python .github/scripts/check_api_docstrings.py --write-snapshot

   Commit ``.github/api-surface.txt`` with the metadata. The command refuses to
   write while any published object fails its ``versionadded`` stamp, or where
   no version can be derived — a shallow clone — so a snapshot never records a
   stamp the gate did not accept. A patch release rewrites it the same way.
```

- [ ] **Step 5: Write the runbook's step 10**

Replace step 10's opening paragraph and its command block:

```rst
10. **Merge the release branch back into main** — with a **merge commit**, not
    a squash. The pull request carries ``CHANGELOG.rst``, the citation metadata,
    and any fix the release was made for.

    .. code-block:: console

       $ git fetch origin
       $ gh pr create --base main --head vA.B.x \
             --title "Merge back vA.B.x" --label skip-changelog
```

with:

```rst
10. **Merge the release branch back into main** — with a **merge commit**, not
    a squash, and through a branch of its own. The pull request carries
    ``CHANGELOG.rst``, the citation metadata, the API snapshot, and any fix the
    release was made for.

    .. code-block:: console

       $ git fetch origin
       $ git switch -c merge-back origin/vA.B.x
       $ git merge --no-ff origin/main -m "Merge main into merge-back"
       $ pixi run tests
       $ git push -u origin merge-back
       $ gh pr create --base main --head merge-back \
             --title "Merge back vA.B.x" --label skip-changelog

    **The branch is what makes a stamp fixable.** An object merged into ``main``
    after ``vA.B.x`` was cut cites the version ``main`` targeted then. Once the
    release's tag is an ancestor, ``main`` targets the next minor version instead,
    so the stamp gate fails that object on ``merge-back``, and ``pixi run tests``
    names the version to write. Re-stamp it there and commit. A pull request from
    ``vA.B.x`` itself could not, because the release branch does not contain the
    object (stamps spec §3.3). Name the branch ``merge-back``, with no version in
    it: ``semver-pep440-release-branch`` reads a versioned name as a release
    branch, and a local run there disagrees with the pull request's checks
    (stamps spec §3.4).
```

Then, in the same step, replace

```rst
    **Do not delete the release branch** when the pull request merges. The next
    patch release for this minor version is prepared on it.
```

with

```rst
    **Do not delete the release branch** when the pull request merges. The next
    patch release for this minor version is prepared on it. Delete
    ``merge-back`` instead; it has done its job.
```

- [ ] **Step 6: Replace the note the specification retires**

Replace everything from the line `**Two gates will move at the first tag**, and neither is a defect:` to the end of the file with:

```rst
**The first release writes the first API snapshot.** Until step 4 has run once
there is no ``.github/api-surface.txt``, and the stamp gate holds every published
object to the version the next tag will carry. From then on it reads the
snapshot: a released object keeps the version recorded there, and only new
objects are held to the next tag (stamps spec §3.1). Rehearsing with a release
candidate writes the snapshot too, which is what keeps ``main`` green when the
candidate is merged back.
```

- [ ] **Step 7: Run the tests and the documentation build**

```bash
pixi run -e test pytest tests/test_api_docstrings.py tests/test_contributor_guide.py tests/test_citations.py tests/test_github_references.py -q --no-cov
pixi run docs
```

Expected: the tests PASS; `pixi run docs` builds clean with every gate passing.

- [ ] **Step 8: Lint, commit, and verify after the commit**

```bash
pixi run -e devs pre-commit run --files docs/src/developer/docs-style.rst docs/src/developer/release.rst tests/test_api_docstrings.py
git add docs/src/developer/docs-style.rst docs/src/developer/release.rst tests/test_api_docstrings.py
git commit -m "Write the snapshot and the merge-back branch into the runbook"
pixi run -e test pytest tests/test_api_docstrings.py -q --no-cov
git status --short
```

Expected: every hook passes; the module passes; `git status --short` prints nothing.

- [ ] **Step 9: Prove the runbook check by mutation**

```bash
sed -i 's/"--write-snapshot",/"--record-snapshot",/' .github/scripts/check_api_docstrings.py
pixi run -e test pytest tests/test_api_docstrings.py -q --no-cov -k runbook
git checkout -- .github/scripts/check_api_docstrings.py
```

Expected: 1 failed, 1 passed — `test_the_runbook_writes_the_snapshot_the_gate_reads` FAILS; `test_the_target_moves_where_the_release_runbook_expects`, which `runbook` also selects, passes. Finish with `git status --short` printing nothing.

---

### Task 5: Verify the branch

**Files:** none.

**Interfaces:**
- Consumes: everything above.
- Produces: the evidence the pull request carries.

- [ ] **Step 1: Run every gate on the committed tree**

```bash
git status --short
pixi run tests
pixi run lint
pixi run docs
test ! -e .github/api-surface.txt && echo "no snapshot committed"
```

Expected: `git status --short` prints nothing; the suite passes; every hook passes; `pixi run docs` builds clean with every gate passing; the last line prints `no snapshot committed`.

- [ ] **Step 2: Hand over for the finish**

These are the controller's, after the whole-branch review, not an implementer's: file one issue for migrating `versionadded` to `version-added` once the Sphinx floor passes 9.0 and for suggesting `version-added` to numpydoc's `DIRECTIVES` — the two items {issue}`227` carries past phase 2 — and repoint `stamps spec §8`'s **Deferred** item to cite it; open the pull request with `Closes #227`; and add `changelog/<PR>.internal.rst` once the pull request exists.
