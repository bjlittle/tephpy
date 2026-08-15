# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the dependency floor generator (floors spec §5)."""

from __future__ import annotations

import ast
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import textwrap
import tomllib

from packaging.version import Version
import pytest
import yaml

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "floors.py"

# `MANIFEST.in` prunes `.github`, so an sdist ships these tests without the
# generator they exercise. Guarding the module rather than the test is deliberate:
# an unguarded import fails *collection* there, taking the rest of the suite with
# it (floors spec §5). The script, not `.git`, is what the guard asks after,
# because the script is what this module needs: it reads `.github` on every test
# and history on three, and a guard naming the index would stand the module down
# wherever history is absent and the generator is right there.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="not a checkout of the repository"
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


def _committed_manifest():
    """Return the manifest this repository declares, not the one it was given.

    A test that asserts against the real `pyproject.toml` has to read it from
    the index: the conda half of `ci-floors` runs this suite in a checkout
    whose manifest this very generator has rewritten, where every floor is an
    `==` pin and every feature but one is gone (:issue:`155`). The guard is
    here rather than on each caller because this is where the index is needed
    -- an unpacked sdist has none, and there the tests that call this skip.
    """
    if not (REPO / ".git").exists():
        pytest.skip("no index to read the committed manifest from")
    return subprocess.run(
        ["git", "show", "HEAD:pyproject.toml"],  # noqa: S607
        check=True,
        capture_output=True,
        cwd=REPO,
        text=True,
    ).stdout


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


#: The same manifest with the two shapes a `pypi-dependencies` table carries: a
#: floor, and the project itself as a local editable source.
PYPI_MANIFEST = MANIFEST + textwrap.dedent(
    """
    [tool.pixi.pypi-dependencies]
    tephpy = { path = ".", editable = true }

    [tool.pixi.feature.docs.pypi-dependencies]
    playwright = ">=1.55"
    """
)


def _pypi(package, specifier, python):  # noqa: ARG001
    """Stand in for the package index, with a ladder above the declared floor."""
    base = specifier.removeprefix(">=")
    return [f"{base}.0", f"{base}.1"]


def test_a_pypi_floor_is_resolved_from_the_index_and_not_the_channel(tmp_path):
    # pixi installs a `pypi-dependencies` entry from PyPI, and conda-forge
    # carries `playwright` too -- so a lookup that asked the channel would pin a
    # release of a package the tier never installs, and the pin would either
    # fail to solve or float the real one (:issue:`151`).
    floors = _load()
    asked = []

    def _channel(package, specifier, python):
        asked.append(("channel", package))
        return _lookup(package, specifier, python)

    def _index(package, specifier, python):
        asked.append(("index", package))
        return _pypi(package, specifier, python)

    resolved = floors.pins(
        _manifest(tmp_path, PYPI_MANIFEST),
        Version("3.12.0"),
        lookup=_channel,
        pypi=_index,
    )
    assert resolved["docs"]["playwright"] == (">=1.55", "1.55.0", "pypi-dependencies")
    assert resolved["docs"]["sphinx"] == (">=8.0", "8.0.0", "dependencies")
    assert ("index", "playwright") in asked
    assert ("channel", "playwright") not in asked


def test_a_pypi_floor_is_pinned_in_the_table_that_declares_it(tmp_path):
    # The rewrite is line-based over the whole manifest, so a pin has to land in
    # the table the floor was read from -- and the editable source beside it must
    # come through untouched, a pin there installing a release of tephpy over the
    # checkout the job is testing.
    floors = _load()
    resolved = floors.pins(
        _manifest(tmp_path, PYPI_MANIFEST),
        Version("3.12.0"),
        lookup=_lookup,
        pypi=_pypi,
    )
    out = floors.rewrite(PYPI_MANIFEST, resolved)
    assert 'playwright = "==1.55.0"' in out
    assert 'tephpy = { path = ".", editable = true }' in out
    docs = tomllib.loads(out)["tool"]["pixi"]["feature"]["docs"]
    assert docs["pypi-dependencies"]["playwright"] == "==1.55.0"


def test_the_project_itself_is_reported_rather_than_pinned(tmp_path):
    # A source entry is the one declaration this generator leaves alone, so it is
    # named in the summary: a job that exercises fewer declarations than the
    # manifest makes reads green for a claim it never tested (:issue:`151`).
    floors = _load()
    manifest = _manifest(tmp_path, PYPI_MANIFEST)
    resolved = floors.pins(manifest, Version("3.12.0"), lookup=_lookup, pypi=_pypi)
    assert "tephpy" not in resolved["core"]
    entry = '{ path = ".", editable = true }'
    assert floors.unpinned(manifest) == {"core": {"tephpy": entry}}
    assert f"Not a floor, left alone: `tephpy = {entry}`." in floors.report(
        resolved, "core", floors.unpinned(manifest)["core"]
    )


def test_the_summary_names_the_table_each_floor_was_declared_in(tmp_path):
    # Two tables per tier means the resolved version alone no longer says which
    # declaration moved, and the fix is an edit to one named file and table.
    floors = _load()
    resolved = floors.pins(
        _manifest(tmp_path, PYPI_MANIFEST),
        Version("3.12.0"),
        lookup=_lookup,
        pypi=_pypi,
    )
    text = floors.report(resolved, "docs")
    assert (
        "| `sphinx` | `>=8.0` | `8.0.0` | `[tool.pixi.feature.docs.dependencies]` |"
    ) in text
    assert (
        "| `playwright` | `>=1.55` | `1.55.0` "
        "| `[tool.pixi.feature.docs.pypi-dependencies]` |"
    ) in text


def test_an_entry_that_is_neither_a_floor_nor_a_source_is_refused(tmp_path):
    # pixi takes a table of options there as well -- extras, a marker, an index.
    # Passing one over silently would leave a declared floor unexercised, and
    # pinning its `version` key would drop the rest of the table on the floor.
    floors = _load()
    text = PYPI_MANIFEST.replace(
        'playwright = ">=1.55"',
        'playwright = { version = ">=1.55", extras = ["driver"] }',
    )
    with pytest.raises(floors.FloorError, match="neither a floor"):
        floors.pins(
            _manifest(tmp_path, text), Version("3.12.0"), lookup=_lookup, pypi=_pypi
        )


def test_a_package_declared_in_both_of_a_tiers_tables_is_refused(tmp_path):
    # One name over two tables is one line in the resolved mapping, so the pin
    # would land in whichever table the line-based rewrite reached and the other
    # declaration would keep floating -- a half-pinned tier that reads as pinned.
    floors = _load()
    text = PYPI_MANIFEST.replace(
        "[tool.pixi.feature.docs.pypi-dependencies]\n",
        '[tool.pixi.feature.docs.pypi-dependencies]\nsphinx = ">=8.0"\n',
    )
    with pytest.raises(floors.FloorError, match="docs: sphinx declared in both"):
        floors.pins(
            _manifest(tmp_path, text), Version("3.12.0"), lookup=_lookup, pypi=_pypi
        )


def test_a_second_declaration_naming_a_source_is_refused_as_well(tmp_path):
    # The guard reads what is declared, not what resolved: a source entry is
    # passed over, so a floor in one table and a source of the same name in the
    # other met no guard at all and left the tier taking the package from the
    # channel and the index both.
    floors = _load()
    text = PYPI_MANIFEST.replace(
        "[tool.pixi.pypi-dependencies]\n",
        '[tool.pixi.pypi-dependencies]\nclick = { path = ".", editable = true }\n',
    )
    with pytest.raises(floors.FloorError, match="core: click declared in both"):
        floors.pins(
            _manifest(tmp_path, text), Version("3.12.0"), lookup=_lookup, pypi=_pypi
        )


def _file(filename, *, kind="bdist_wheel", yanked=False, requires=None):
    """One uploaded file, as the PyPI JSON API describes it."""
    return {
        "filename": filename,
        "packagetype": kind,
        "yanked": yanked,
        "requires_python": requires,
    }


def _serve(monkeypatch, floors, document):
    """Answer the release lookup from a canned index rather than from PyPI."""
    # A `BytesIO` is its own context manager and reads as the file the opener
    # hands back, so the stub stands in for the response without a class.
    monkeypatch.setattr(
        floors.urllib.request,
        "urlopen",
        lambda *_, **__: io.BytesIO(json.dumps(document).encode("utf-8")),
    )


def test_a_release_with_no_file_this_target_can_install_is_passed_over(monkeypatch):
    # `requires_python` alone says nothing about where a wheel runs: pywin32 311
    # publishes fifteen non-yanked wheels, all of them for Windows and none of
    # them declaring a Python, and the Linux runner cannot install any of them.
    # A pin there turns a floor the tier declares into a solve failure, and the
    # upward scan climbs releases the tier can never reach.
    floors = _load()
    _serve(
        monkeypatch,
        floors,
        {
            "releases": {
                "1.0": [_file("only-1.0-cp312-cp312-win_amd64.whl")],
                "1.1": [_file("only-1.1-cp39-cp39-manylinux_2_17_x86_64.whl")],
                "1.2": [_file("only-1.2.tar.gz", kind="sdist")],
                "1.3": [_file("only-1.3-py3-none-any.whl")],
            }
        },
    )
    assert floors.releases("only", ">=1.0", Version("3.12.0")) == ["1.2", "1.3"]


def test_a_yanked_release_and_one_this_python_is_shut_out_of_are_passed_over(
    monkeypatch,
):
    # A yank is the index saying not to install the release, and
    # `--resolution lowest-direct` on the other half of the job honours both this
    # and `requires-python` -- so a generator that did not would pin the two
    # halves to different releases and report a floor neither would install.
    floors = _load()
    _serve(
        monkeypatch,
        floors,
        {
            "releases": {
                "1.0": [_file("only-1.0-py3-none-any.whl", yanked=True)],
                "1.1": [_file("only-1.1-py3-none-any.whl", requires=">=3.13")],
                "1.2": [
                    _file("only-1.2-py3-none-any.whl", yanked=True),
                    _file("only-1.2.tar.gz", kind="sdist", requires=">=3.10"),
                ],
            }
        },
    )
    assert floors.releases("only", ">=1.0", Version("3.12.0")) == ["1.2"]


def test_every_floor_the_manifest_declares_in_a_pypi_table_is_resolved(tmp_path):
    # The property that was broken: the generator read the four conda tables and
    # no others, so `playwright` went unpinned and the docs tier ran its floors
    # job against whatever release the solver reached -- green, on a floor it had
    # never tested (:issue:`151`). Asserted against the real manifest, so a table
    # added to `pyproject.toml` tomorrow is covered by the same rule.
    floors = _load()
    text = _committed_manifest()
    document = tomllib.loads(text)
    manifest = _manifest(tmp_path, text)
    resolved = floors.pins(manifest, Version("3.12.0"), lookup=_lookup, pypi=_pypi)
    declared = 0
    for tier, path in floors.PYPI_TABLES.items():
        node = document
        for key in path:
            node = node.get(key, {}) if isinstance(node, dict) else {}
        for package, entry in node.items():
            if not isinstance(entry, str):
                continue
            declared += 1
            assert resolved[tier][package][0] == entry
            assert resolved[tier][package][2] == "pypi-dependencies"
    # Vacuous the day nothing is declared from PyPI, which is a state this
    # repository has been in and could return to.
    assert declared


RESOLVED = {
    "core": {"click": (">=8.1", "8.1.3", "dependencies")},
    "test": {"pytest": (">=8.0", "8.0.0", "dependencies")},
}


def _root(tmp_path, name):
    """Stand in for a probe copy: a directory that exists until someone drops it."""
    root = tmp_path / name
    root.mkdir(exist_ok=True)
    return root


def _rig(monkeypatch, tmp_path, solves):
    """Replace the solver and the checkout copier; return the module and a probe."""
    diagnose = _load_diagnose()
    monkeypatch.setattr(diagnose.floors, "pins", lambda *_: RESOLVED)
    # The copier is replaced but still makes the directory, so what a caller
    # does with a probe once it has answered is visible to a test.
    monkeypatch.setattr(diagnose, "_copy", lambda _probe, name: _root(tmp_path, name))
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


def test_a_probe_is_dropped_once_it_has_answered(monkeypatch, tmp_path):
    # Attribution makes a probe per declared floor, each carrying an installed
    # environment -- twenty-eight of them for `docs`, against the little disk a
    # runner has. Only the relaxation that solves is read again, by `chosen`,
    # so it is the one that must survive: dropping probes wholesale would take
    # that resolve with it, and the diagnosis would report no bounding version
    # for a scan that has a culprit (floors spec §3.4).
    diagnose, probe = _rig(
        monkeypatch, tmp_path, lambda *args: (args[2] == "pytest", "conflict")
    )
    assert diagnose.attribute(probe)[0] == "pytest"
    assert not (tmp_path / "baseline").exists()
    assert not (tmp_path / "relax-0").exists()
    assert (tmp_path / "relax-1").is_dir()


def test_the_probes_pin_a_version_for_the_editable_build(monkeypatch, tmp_path):
    # tephpy installs editable into every environment, so every probe runs the
    # build backend over a tree this job has rewritten, in a repository with no
    # release tagged yet. A build that fails there fails the build rather
    # than the solve, which turns the one relaxation that *does* resolve into
    # another failure and every diagnosis into "nothing attributed" -- the same
    # verdict an honestly unattributable failure gets (floors spec §3.4).
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


WORKFLOW = REPO / ".github" / "workflows" / "ci-floors.yml"


def test_no_job_reaches_for_a_tool_it_does_not_install():
    # This workflow runs weekly and on dispatch, never on a pull request, so a
    # step calling something its job never installed is a failure nobody meets
    # until the week it matters -- and the first live run met it: `file` called
    # `pixi exec`, installs no pixi, and so filed nothing for two floors that
    # had been diagnosed correctly. Every other gate this repository has would
    # have run that job a hundred times before it mattered; this one would not.
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    for name, job in jobs.items():
        steps = job["steps"]
        if any("setup-pixi" in (step.get("uses") or "") for step in steps):
            continue
        for step in steps:
            command = step.get("run") or ""
            assert "pixi" not in command, f"{name}: {step.get('name')} needs pixi"


#: The modules that exercise the `.github` scripts, and so carry a guard for the
#: sdist that ships them without it. The `test` tier's exercise is this suite, so
#: what their guard skips is what a diagnosis cannot see.
GUARDED = (
    "test_floors.py",
    "test_floors_issue.py",
    "test_citations.py",
    "test_github_references.py",
)


@pytest.mark.parametrize("name", GUARDED)
def test_no_module_a_probe_runs_is_guarded_on_the_index(name):
    # A module-level `skipif` keyed on the index stands the whole module down
    # wherever history is absent -- silently, a skip being not a failure -- and
    # history is not what any of these modules is missing. It is `.github` that
    # an sdist prunes, so that is what the guard asks after. The narrower
    # condition still has a use: the two citation modules enumerate their corpus
    # with `git ls-files`, and mark the tests that do.
    # The floors probes carry an index now (:issue:`154`), so this no longer
    # holds a module up in one; it holds each guard to naming what it needs.
    source = (REPO / "tests" / name).read_text(encoding="utf-8")
    tree = ast.parse(source)
    guards = [
        ast.get_source_segment(source, node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "pytestmark"
            for target in node.targets
        )
    ]
    assert len(guards) == 1, "the module must stay guarded for the sdist"
    # `.github` starts with `.git`, so the index is matched as a whole word: a
    # guard written out inline rather than through `SCRIPT` names the directory
    # this test wants to see, and a substring test would read it as the index.
    assert not re.search(r"\.git\b", guards[0])


def _shells_out_to_git(source: str) -> list[ast.FunctionDef]:
    """Return every function in one module whose argv starts with a literal ``git``.

    Every function, not every test: a call moved into a helper is the same call
    from the probe's point of view, and a detector that only read tests would go
    quiet on the refactor rather than on the guard being dropped.
    """
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef):
            continue
        for call in ast.walk(node):
            argv = call.args[0] if isinstance(call, ast.Call) and call.args else None
            if isinstance(argv, ast.List) and argv.elts:
                head = argv.elts[0]
                if isinstance(head, ast.Constant) and head.value == "git":
                    found.append(node)
                    break
    return found


def _guard(node: ast.FunctionDef) -> str:
    """One function's decorators and statements, less its docstring and comments.

    What a guard is asserted against has to be code: the source segment of this
    very function mentions ``.git`` in prose, and matched raw it would report
    itself guarded.
    """
    statements = node.body
    first = statements[0] if statements else None
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        statements = statements[1:]
    return "\n".join(ast.unparse(part) for part in [*node.decorator_list, *statements])


def test_every_test_that_shells_out_to_git_is_guarded_on_the_index():
    # An unpacked sdist ships this suite and no repository, so a `git` call
    # there does not skip -- it raises, and with `check=True` it fails, on a
    # condition that says nothing about the release under test. The literal form
    # is what is matched, so a call built some other way is caught by that run
    # going red rather than here.
    # The guard may be a `skipif` on the test or a `pytest.skip` in the function
    # itself, a helper carrying its own being the only way one shared by several
    # tests is guarded once.
    unguarded = []
    for path in sorted((REPO / "tests").rglob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        unguarded += [
            f"{path.name}::{node.name}"
            for node in _shells_out_to_git(source)
            if ".git" not in _guard(node)
        ]
    assert not unguarded


def test_a_probe_copy_drops_what_the_failing_leg_left_behind(tmp_path):
    # The diagnosis runs after that leg ran in this same checkout, so a copied
    # `__pycache__` gives the probe code objects naming the checkout rather than
    # the copy -- which fails `test_a_warning_blames_the_caller_not_tephpy`, that
    # test comparing a warning's filename to `__file__` -- and a copied
    # `docs/_build` makes the probe's documentation build an incremental one over
    # pages it did not write. Either way the exercise reports the state of the
    # run being diagnosed instead of its own (floors spec §3.3).
    diagnose = _load_diagnose()
    source = tmp_path / "checkout"
    (source / "tests" / "__pycache__").mkdir(parents=True)
    (source / "tests" / "__pycache__" / "test_x.pyc").write_bytes(b"stale")
    (source / "docs" / "_build" / "html").mkdir(parents=True)
    (source / "docs" / "_build" / "html" / "index.html").write_text("stale")
    (source / "tests" / "test_x.py").write_text("# kept\n")
    probe = diagnose.Probe(
        source=source, scratch=tmp_path / "scratch", tier="test", python="3.12"
    )
    (tmp_path / "scratch").mkdir()
    root = diagnose._copy(probe, "baseline")
    assert (root / "tests" / "test_x.py").is_file()
    assert not (root / "tests" / "__pycache__").exists()
    assert not (root / "docs" / "_build").exists()


def test_a_probe_copy_carries_the_index_the_exercise_reads(tmp_path):
    # Thirteen of the `test` tier's tests guard on a repository being there,
    # among them the one that builds a wheel from `git archive HEAD` -- and that
    # is the test the `conda (test)` leg failed on in run 31848921992, on
    # `packaging` at its floor. The probe skipped it, found nothing to reproduce,
    # and filed :issue:`152` saying the failure was in a step it does not run.
    # The step was a test it had (:issue:`154`).
    diagnose = _load_diagnose()
    source = tmp_path / "checkout"
    (source / ".git" / "objects").mkdir(parents=True)
    (source / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (source / "tests").mkdir()
    (source / "tests" / "test_x.py").write_text("# kept\n")
    probe = diagnose.Probe(
        source=source, scratch=tmp_path / "scratch", tier="test", python="3.12"
    )
    (tmp_path / "scratch").mkdir()
    root = diagnose._copy(probe, "baseline")
    assert (root / ".git" / "HEAD").is_file()


def test_the_docs_probe_runs_every_gate_the_workflow_does():
    # The docs leg is a build and two output gates, and a floor can pass the
    # build and fail a gate -- `sphinx-click 6.0.0` did (:issue:`109`). A probe
    # that runs the build alone re-runs that leg green and reports it
    # unreproduced, which reads as "the floor is fine" (floors spec §3.3). The
    # workflow is the source of the list, so a gate added there and not here is
    # a failure rather than a step nobody notices is missing.
    diagnose = _load_diagnose()
    workflow = (REPO / ".github" / "workflows" / "ci-floors.yml").read_text(
        encoding="utf-8"
    )
    gates = set(re.findall(r"\.github/scripts/check_\w+\.py", workflow))
    probed = {word for command in diagnose.EXERCISE["docs"] for word in command}
    assert gates
    assert gates <= probed
    assert ["make", "-C", "docs", "html"] in diagnose.EXERCISE["docs"]


def test_the_exercise_reports_the_step_that_failed_and_stops(monkeypatch, tmp_path):
    # The gates read what the build wrote, so running on past a failure reports
    # a cascade of missing-output errors in place of the failure that caused
    # them -- and that text is what the issue quotes verbatim (floors spec §3.6).
    diagnose = _load_diagnose()
    ran = []

    def _run(command, **_):
        ran.append(command[-1])
        code = 1 if command[-1] == "html" else 0
        return subprocess.CompletedProcess(command, code, "build failed", "")

    monkeypatch.setattr(diagnose.subprocess, "run", _run)
    monkeypatch.setattr(diagnose.floors, "tool", lambda name: f"/usr/bin/{name}")
    probe = diagnose.Probe(
        source=tmp_path, scratch=tmp_path, tier="docs", python="3.12"
    )
    passed, output = diagnose.exercise(probe, tmp_path)
    assert not passed
    assert output.startswith("build failed")
    assert ran == ["html"]


def test_the_forced_pin_is_written_after_the_generator_runs(monkeypatch, tmp_path):
    # The generator rebuilds every declaration from its `>=` floor, so a pin
    # written before it runs does not survive -- and worse, is refused, an exact
    # pin not being a floor it can resolve. With `check=True` on that call, the
    # refusal raises, and the scan dies on its first candidate having established
    # nothing (floors spec §3.2, §3.5).
    diagnose = _load_diagnose()
    order = []

    def _run(command, **_):
        first = "generate" if command[1].endswith("floors.py") else command[1]
        order.append(first)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(diagnose.subprocess, "run", _run)
    monkeypatch.setattr(diagnose.floors, "tool", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(diagnose, "_pin_one", lambda *_: order.append("pin"))
    probe = diagnose.Probe(
        source=tmp_path, scratch=tmp_path, tier="test", python="3.12"
    )
    diagnose.solves(probe, tmp_path, None, pin=("matplotlib-base", "3.10.3"))
    assert order == ["generate", "pin", "install"]


LADDER = ["3.10.0", "3.10.1", "3.10.3", "3.11.0", "3.11.1"]


def _rigged(monkeypatch, tmp_path, passes):
    """Replace the solver and the channel; return the module, a probe and the log."""
    diagnose = _load_diagnose()
    tried = []

    def _probe(_probe_arg, root, _package, _pin):
        tried.append(root.name)
        return passes(len(tried) - 1)

    monkeypatch.setattr(diagnose, "_probe_pin", _probe)
    monkeypatch.setattr(diagnose, "_copy", lambda _probe_arg, name: tmp_path / name)
    monkeypatch.setattr(diagnose.floors, "candidates", lambda *_: LADDER)
    probe = diagnose.Probe(
        source=tmp_path, scratch=tmp_path, tier="test", python="3.12"
    )
    return diagnose, probe


def test_the_scan_stops_at_the_first_version_that_passes(monkeypatch, tmp_path):
    # Ascending and linear, so the first pass is by construction the lowest that
    # works, with no assumption about the pass/fail boundary (floors spec §3.5).
    diagnose, probe = _rigged(monkeypatch, tmp_path, lambda index: index == 2)
    lowest, scanned = diagnose.scan(probe, "matplotlib-base", ">=3.10", "3.11.0")
    assert lowest == "3.10.3"
    assert scanned == ["3.10.0", "3.10.1", "3.10.3"]


def test_the_scan_never_goes_above_the_bound(monkeypatch, tmp_path):
    # The bound is what makes the scan terminate. Without it a floor that nothing
    # fixes walks the package's whole release history, and only a case where
    # nothing passes tells the two apart -- a scan that finds an answer would
    # return the same one either way.
    diagnose, probe = _rigged(monkeypatch, tmp_path, lambda _index: False)
    lowest, scanned = diagnose.scan(probe, "matplotlib-base", ">=3.10", "3.10.3")
    assert lowest is None
    assert scanned == ["3.10.0", "3.10.1", "3.10.3"]


def test_the_scan_climbs_the_index_the_declaring_table_names(monkeypatch, tmp_path):
    # The scan walks upwards from the declared floor, and where that ladder comes
    # from is a property of the table, not of the package: conda-forge carries
    # `playwright` as well, so a scan that always asked the channel would report
    # a lowest-passing version out of a set the tier never installs from
    # (:issue:`151`). The tests above hold the other direction, `candidates`
    # being the one they stub.
    diagnose, probe = _rigged(monkeypatch, tmp_path, lambda index: index == 1)
    monkeypatch.setattr(diagnose.floors, "releases", lambda *_: ["1.55.0", "1.56.0"])
    lowest, scanned = diagnose.scan(
        probe, "playwright", ">=1.55", None, "pypi-dependencies"
    )
    assert lowest == "1.56.0"
    assert scanned == ["1.55.0", "1.56.0"]


def test_the_environment_table_is_replaced_not_appended():
    # pixi solves every environment a manifest declares, so a leftover `default`
    # would let one tier's conflict fail another tier's run (floors spec §3.3).
    floors = _load()
    text = MANIFEST + "\n[tool.pixi.environments]\ndefault = { features = [] }\n"
    out = floors.environments(text, "test", "3.12")
    assert "floors-test" in out
    assert "default = " not in out


def test_a_feature_the_generated_environment_cannot_reach_is_dropped():
    # One environment survives generation, so every other feature is defined and
    # used by nothing, and pixi says so once per orphan -- ahead of the solver
    # output, in text the diagnosis quotes into the issue it files (:issue:`150`).
    floors = _load()
    text = MANIFEST + '\n[tool.pixi.feature.py312.dependencies]\npython = "3.12.*"\n'
    out = floors.features(text, "test", "3.12")
    assert "[tool.pixi.dependencies]" in out
    assert "[tool.pixi.feature.test.dependencies]" in out
    assert "[tool.pixi.feature.py312.dependencies]" in out
    assert "[tool.pixi.feature.docs.dependencies]" not in out
    assert "[tool.pixi.feature.devs.dependencies]" not in out


def test_a_dropped_feature_takes_every_table_and_comment_it_owns():
    # A feature is more than its dependencies: dropping the one table this
    # generator knows by name would leave the tasks behind, and pixi warns on the
    # feature, not on the table. The comment above a table was written about that
    # table, so leaving it behind would caption the next one instead.
    floors = _load()
    text = MANIFEST + textwrap.dedent(
        """
        [tool.pixi.feature.test.tasks.tests]
        cmd = "pytest"

        # Why the documentation is built this way.
        [tool.pixi.feature.docs.tasks.docs-html]
        cmd = "make html"

        [tool.pixi.feature.docs.pypi-dependencies]
        playwright = ">=1.55"
        """
    )
    out = floors.features(text, "test", "3.12")
    assert "[tool.pixi.feature.test.tasks.tests]" in out
    assert "docs-html" not in out
    assert "playwright" not in out
    assert "Why the documentation is built this way." not in out
    # The kept table follows a dropped one, so the blank line between the two is
    # dropped with it and the header would otherwise butt against the table above.
    assert "\n\n[tool.pixi.feature.test.tasks.tests]" in out
    assert tomllib.loads(out)["tool"]["pixi"]["feature"]["test"]["tasks"]["tests"]


def test_the_tier_keeps_the_tables_that_are_not_dependencies():
    # The docs tier declares `playwright` in a `pypi-dependencies` table and
    # builds through its own tasks. A prune keyed on the dependency table alone
    # would take both, and the tier would install and then fail to run.
    floors = _load()
    text = MANIFEST + textwrap.dedent(
        """
        [tool.pixi.feature.docs.pypi-dependencies]
        playwright = ">=1.55"

        [tool.pixi.feature.docs.tasks.docs]
        cmd = "make html"
        """
    )
    out = floors.features(text, "docs", "3.12")
    assert "playwright" in out
    assert "[tool.pixi.feature.docs.tasks.docs]" in out


@pytest.mark.parametrize("tier", ["test", "docs", "devs"])
def test_the_generated_manifest_defines_no_feature_it_does_not_use(tier):
    # The property the warning block reports on, asserted against the real
    # manifest rather than a fixture: a feature added to `pyproject.toml`
    # tomorrow is dropped by the same rule, and one the generated environment
    # does reference is never dropped by it.
    floors = _load()
    text = _committed_manifest()
    out = floors.features(floors.environments(text, tier, "3.12"), tier, "3.12")
    pixi = tomllib.loads(out)["tool"]["pixi"]
    used = {
        feature
        for environment in pixi["environments"].values()
        for feature in environment["features"]
    }
    assert set(pixi["feature"]) == used
    assert tier in used


@pytest.mark.parametrize("tier", ["test", "docs", "devs"])
def test_the_generated_manifest_leaves_no_task_naming_a_dropped_one(tier):
    # The prune takes whole features, and pixi resolves `depends-on` over every
    # task an environment carries -- so a task naming one of another feature is
    # allowed, and a manifest that grew one would generate a dangling reference.
    # Every `depends-on` in `pyproject.toml` names a task of its own feature
    # today; this is what notices the day one does not.
    floors = _load()
    text = _committed_manifest()
    out = floors.features(floors.environments(text, tier, "3.12"), tier, "3.12")
    pixi = tomllib.loads(out)["tool"]["pixi"]
    tasks = dict(pixi.get("tasks", {}))
    for feature in pixi["feature"].values():
        tasks.update(feature.get("tasks", {}))
    named = {
        entry["task"] if isinstance(entry, dict) else entry
        for task in tasks.values()
        if isinstance(task, dict)
        for entry in task.get("depends-on", [])
    }
    assert named <= set(tasks)
    # The `docs` tier is the only one declaring a `depends-on` today, so the
    # assertion above holds vacuously for the other two: fail here rather than
    # let all three go quiet the day that table moves.
    assert bool(named) is (tier == "docs")
