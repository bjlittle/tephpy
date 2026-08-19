# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the dependency floor generator (floors spec §5)."""

from __future__ import annotations

import ast
import fnmatch
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

from tests.pixi_tasks import invocations, runs, unsatisfied

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "floors.py"

# `MANIFEST.in` prunes `.github`, so an sdist ships these tests without the
# generator they exercise. Guarding the module rather than the test is deliberate:
# an unguarded import fails *collection* there, taking the rest of the suite with
# it (floors spec §5). The script, not `.git`, is what the guard asks after,
# because the script is what this module needs: it reads `.github` on every test
# and history on four, and a guard naming the index would stand the module down
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


def _load_issue():
    """Import the issue composer by path, to hold it against the diagnosis."""
    path = REPO / ".github" / "scripts" / "floors_issue.py"
    spec = importlib.util.spec_from_file_location("floors_issue", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["floors_issue"] = module
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


#: Enough of the spelling the specifications use to read a figure back out of
#: prose. A word outside this map fails the gate rather than passing it: a
#: figure the gate cannot read is the state it exists to catch, not a reason to
#: wave it through.
_UNITS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50}


def _spelled(word: str) -> int:
    """Return the integer a specification spelled out, ``twenty-five`` included."""
    tens, _, units = word.lower().partition("-")
    if tens in _TENS:
        return _TENS[tens] + (_UNITS.index(units) if units else 0)
    return _UNITS.index(tens)


def _names_the_index(node: ast.AST) -> bool:
    """Whether anything under ``node`` builds the path to the index.

    The constant is compared rather than searched for. This very module holds
    ``.git`` inside a regular expression and ``pytest.skip`` inside a string,
    and a detector matching either as text reads itself as guarded -- the same
    distinction between building a path and mentioning one that the manifest
    gate above draws, and for the same reason.
    """
    return any(
        isinstance(each, ast.Constant) and each.value == ".git"
        for each in ast.walk(node)
    )


def _skips(node: ast.AST) -> bool:
    """Whether anything under ``node`` calls ``pytest.skip``, rather than naming it."""
    return any(
        isinstance(each, ast.Call) and ast.unparse(each.func) == "pytest.skip"
        for each in ast.walk(node)
    )


def _calls(node: ast.AST) -> set[str]:
    """Return the name of everything under ``node`` that is called by plain name."""
    return {
        call.func.id
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
    }


def _guards_itself(node: ast.FunctionDef) -> bool:
    """Whether a test's own body skips on the index, no helper between them.

    Read over the body and not the whole function, a ``skipif`` naming the
    index being a different spelling recognised already -- and over the whole of
    the body rather than statement by statement, because the condition and the
    skip it leads to are as readily written apart as together.
    """
    return any(_skips(each) for each in node.body) and any(
        _names_the_index(each) for each in node.body
    )


def _needs_the_index(path: Path) -> set[str]:
    """Return the tests in one module that stand down without a repository.

    Four spellings, because the guard is written wherever it reads best: a
    ``skipif`` naming the index on the test, the same through a module-level
    alias -- which unparses to the alias, not to what it holds, so the
    assignment is what has to be read -- a call to a helper that skips on its
    own, that being how a condition shared by several tests is written once,
    and the same condition inline in the test that needs it.

    That third spelling is followed as far as it goes. A helper calling a
    helper that skips skips too, so the set of them is closed under calling
    before the tests are read against it: stopping at the direct callers would
    fail *open*, pytest skipping a test one wrapper away from the guard while
    the count here omits it and the prose it holds stays believed.

    Two spellings are *not* recognised, neither of them written in this suite:
    a helper imported from another module, and a fixture that skips, which
    arrives as a parameter name rather than as a call and lives in a
    ``conftest`` this reads nothing of. Both fail open the same silent way, so
    the appearance of either is the signal to stop widening this and ask the
    only oracle that cannot miss a spelling -- the five guarded modules run in
    a copy with no index, counting what pytest reports skipped. That costs
    about nine seconds against a suite of seventy, and retires this function
    whole rather than growing a fifth branch onto it.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    aliases: set[str] = set()
    helpers: dict[str, ast.FunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if "skipif" in ast.unparse(node.value) and _names_the_index(node.value):
                aliases |= {
                    target.id for target in node.targets if isinstance(target, ast.Name)
                }
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("test_"):
            helpers[node.name] = node
    skippers = {
        name
        for name, node in helpers.items()
        if _skips(node) and _names_the_index(node)
    }
    while reached := {
        name
        for name, node in helpers.items()
        if name not in skippers and _calls(node) & skippers
    }:
        skippers |= reached
    found = set()
    for node in tree.body:
        if not (isinstance(node, ast.FunctionDef) and node.name.startswith("test_")):
            continue
        called = _calls(node)
        worn = {each.id for each in node.decorator_list if isinstance(each, ast.Name)}
        if (
            any(_names_the_index(each) for each in node.decorator_list)
            or worn & aliases
            or called & skippers
            or _guards_itself(node)
        ):
            found.add(node.name)
    return found


def test_the_specification_quotes_the_number_of_index_guarded_tests():
    # Spec §3.3 says how many of this tier's tests stand down without an index,
    # to say what a probe copied without one stops running. The number is prose
    # in one directory about test bodies in another, and it went stale the day
    # :pull:`164` routed one more test through `_committed_manifest` -- reported
    # by nothing, a skip not being a failure (:pull:`167`).
    #
    # Counted as *tests*, which is what the sentence says and not what the
    # source shows: four of the ten functions below are parametrised, and
    # reading the count off the definitions would say ten. So the count comes
    # from pytest, the only thing that knows what a module collects.
    guarded = {
        path: names
        for path in sorted((REPO / "tests").rglob("test_*.py"))
        if (names := _needs_the_index(path))
    }
    assert guarded, "no test in the suite guards on the index"
    listing = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:randomly",
            "-p",
            "no:cacheprovider",
            *(str(path) for path in guarded),
        ],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=True,
    ).stdout
    collected = 0
    for line in listing.splitlines():
        item = re.match(r"(\S+\.py)::(\w+)", line)
        if item and item[2] in guarded.get(REPO / item[1], ()):
            collected += 1
    assert collected, "pytest collected none of the guarded tests"
    prose = (
        REPO / "docs" / "src" / "developer" / "specs"
    ) / "2026-08-13-dependency-floors-design.md"
    # `[\w-]` rather than `\w`: `_spelled` reads a hyphenated number and says so,
    # but this could not hand it one -- `\w` stops at the hyphen, so `twenty-one`
    # arrived as `one` and the gate reported the count as off by twenty. Every
    # number the suite had reached until it crossed twenty was a single word, so
    # the finder was narrower than the reader for as long as nothing tested it.
    (quoted,) = re.findall(
        r"([\w-]+) of the `test` tier's tests guard on a repository",
        prose.read_text(encoding="utf-8"),
    )
    assert _spelled(quoted) == collected


@pytest.mark.parametrize(
    ("source", "guarded"),
    [
        # The three spellings the suite actually uses, which the count above
        # exercises end to end -- it reaches fourteen only if all three are read.
        (
            """
            @pytest.mark.skipif(not (REPO / ".git").exists(), reason="no index")
            def test_x():
                pass
            """,
            True,
        ),
        (
            """
            needs = pytest.mark.skipif(not (REPO / ".git").exists(), reason="no")

            @needs
            def test_x():
                pass
            """,
            True,
        ),
        (
            """
            def _read():
                if not (REPO / ".git").exists():
                    pytest.skip("no index")

            def test_x():
                _read()
            """,
            True,
        ),
        # The two the count cannot exercise, nothing in the suite being written
        # either way -- so this table is the only thing holding them up. A
        # wrapper between the test and the helper that skips, which the count
        # read as unguarded until the closure went in, and the condition inline
        # in the test, which it read as unguarded until `_guards_itself` did.
        (
            """
            def _read():
                if not (REPO / ".git").exists():
                    pytest.skip("no index")

            def _wrapped():
                return _read()

            def test_x():
                _wrapped()
            """,
            True,
        ),
        (
            """
            def test_x():
                if not (REPO / ".git").exists():
                    pytest.skip("no index")
            """,
            True,
        ),
        # Inline, but with the condition bound first. Read statement by
        # statement the skip and the index it turns on are in different ones,
        # and the guard would go unseen for being written the way most of this
        # suite's conditions are.
        (
            """
            def test_x():
                index = REPO / ".git"
                if not index.exists():
                    pytest.skip("no index")
            """,
            True,
        ),
        # A test that guards on nothing, without which every case above passes
        # for a detector that simply says yes.
        (
            """
            def test_x():
                assert True
            """,
            False,
        ),
        # Naming the index is not standing down on it. This is the shape of
        # `test_a_probe_copy_carries_the_index_the_exercise_reads`, which builds
        # a `.git` in a copy it makes: counted here, the number would exceed the
        # prose and the gate would go red over a test that never skips.
        (
            """
            def test_x(tmp_path):
                (tmp_path / ".git").mkdir()
                assert (tmp_path / ".git").is_dir()
            """,
            False,
        ),
        # Standing down is not standing down on the *index*, and the sentence
        # this count holds up is about a probe copied without one.
        (
            """
            def test_x():
                if not shutil.which("pixi"):
                    pytest.skip("no pixi")
            """,
            False,
        ),
    ],
)
def test_the_detector_reads_a_guard_however_it_is_spelled(tmp_path, source, guarded):
    # `_needs_the_index` is read by one caller, which turns what it finds into a
    # single number. A spelling it cannot see therefore lowers that number in
    # silence -- the guarded test still skips, the prose still says fourteen,
    # and the two agree about a suite neither of them describes. Only the three
    # spellings in use are exercised by that caller, so the two added since are
    # held up here or nowhere.
    path = tmp_path / "test_probe.py"
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    assert _needs_the_index(path) == ({"test_x"} if guarded else set())


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
    # Fourteen of the `test` tier's tests guard on a repository being there,
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


def _docs_steps():
    """Return each documentation-tier step of the conda job, by the name it reports.

    Selected on the condition the job itself branches on, not on what a step
    happens to run: a step added to this tier and running something unexpected
    is the state to report, and a selector keyed on the task names would drop it
    instead of failing on it.
    """
    job = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["conda"]
    return {
        step.get("name", f"step {index}"): step["run"]
        for index, step in enumerate(job["steps"])
        if "run" in step and step.get("if") == "matrix.tier == 'docs'"
    }


def _docs_tasks():
    """Return the `docs` feature's pixi tasks, as this repository declares them."""
    manifest = tomllib.loads(_committed_manifest())
    return manifest["tool"]["pixi"]["feature"]["docs"]["tasks"]


#: The aggregate a contributor runs, which is what this tier is measured against.
FAST = "docs"

#: What the floors job leaves out of it, and why the omission is written down
#: rather than derived: the figure gate compares the published figures against
#: baselines blessed under the matplotlib the lockfile pins, by the same RMS
#: measure `pytest-mpl` applies to `tests/baseline`, so at a floor matplotlib it
#: reports the distance between the two rather than anything about the floor --
#: and that distance grows on its own as the lock moves. Derived from the
#: workflow instead, every later omission would look like this intended one.
EXCLUDED = {"docs-check-figures"}


def test_the_docs_leg_runs_every_gate_but_the_one_it_leaves_out():
    # Spelled out step by step, this job ran two of the three gates `pixi run
    # docs` runs: `docs-check-figures` joined that task in :issue:`172` and the
    # copy here heard nothing about it, while floors spec §3.3 went on calling
    # the exercise `pixi run docs` -- three spellings of one list, two of them
    # wrong (:issue:`178`). Naming the tasks leaves the manifest as the only
    # place the commands are written, and this holds the job to the same set.
    #
    # The total alone would not say it, which is why the split is asserted in
    # both directions: what the job omits, and that it omits nothing else. A
    # gate added to `docs` and not here would otherwise be a gate this tier
    # silently stops exercising, which is the state that was already true.
    tasks = _docs_tasks()
    named = {
        invocation.target
        for script in _docs_steps().values()
        for invocation in invocations(script)
        if invocation.target in tasks
    }
    assert runs([FAST], tasks) - runs(named, tasks) == EXCLUDED
    assert not runs(named, tasks) - runs([FAST], tasks)


def test_no_docs_step_skips_a_dependency_no_earlier_step_ran():
    # `--skip-deps` is here because every gate depends on `docs-html`, and pixi
    # deduplicates a shared dependency within one invocation and not across
    # several -- so without it each gate would rebuild the documentation first,
    # at a floor Sphinx, three times over.
    #
    # What the flag skips, though, is *every* dependency and not the one the
    # preceding step happens to have supplied, so a second dependency added to a
    # gate later is dropped here with nothing in the diff to say so. The same
    # accounting `ci-docs.yml` is held to, and it matters more in this job: this
    # one runs weekly, and a gate reading a build that never had what it needed
    # reports a broken floor.
    steps = _docs_steps()
    # Nothing to complain about is the answer to be sure of here: the selector
    # reads the `if:` of each step, and a tier written some other way -- through
    # an expression, or a job of its own -- leaves this gate with no input and
    # an empty list of complaints about it.
    assert steps, "no documentation-tier step found in the floors workflow"
    complaints = unsatisfied(steps, _docs_tasks())
    assert not complaints, "\n".join(
        f"{step}: `{target}` skips {missing}, which no earlier step has run"
        for step, target, missing in complaints
    )


def test_the_docs_probe_runs_every_gate_the_workflow_does():
    # The docs leg is a build and its output gates, and a floor can pass the
    # build and fail a gate -- `sphinx-click 6.0.0` did (:issue:`109`). A probe
    # that runs the build alone re-runs that leg green and reports it
    # unreproduced, which reads as "the floor is fine" (floors spec §3.3). The
    # workflow is the source of the list, so a gate added there and not here is
    # a failure rather than a step nobody notices is missing.
    #
    # Both sides go through the same reader, and what is compared is a list: the
    # gates read what the build wrote, so the order is part of the claim, and
    # `--skip-deps` is part of it too -- a probe that skipped what the workflow
    # builds would exercise the gates against no build at all.
    diagnose = _load_diagnose()
    named = [
        invocation
        for script in _docs_steps().values()
        for invocation in invocations(script)
    ]
    probed = [
        invocation
        for command in diagnose.EXERCISE["docs"]
        for invocation in invocations(f"pixi run {' '.join(command)}")
    ]
    assert named
    assert named == probed


def test_the_exercise_reports_the_step_that_failed_and_stops(monkeypatch, tmp_path):
    # The gates read what the build wrote, so running on past a failure reports
    # a cascade of missing-output errors in place of the failure that caused
    # them -- and that text is what the issue quotes verbatim (floors spec §3.6).
    diagnose = _load_diagnose()
    ran = []

    def _run(command, **_):
        ran.append(command[-1])
        code = 1 if command[-1] == "docs-html" else 0
        return subprocess.CompletedProcess(command, code, "build failed", "")

    monkeypatch.setattr(diagnose.subprocess, "run", _run)
    monkeypatch.setattr(diagnose.floors, "tool", lambda name: f"/usr/bin/{name}")
    probe = diagnose.Probe(
        source=tmp_path, scratch=tmp_path, tier="docs", python="3.12"
    )
    passed, output = diagnose.exercise(probe, tmp_path)
    assert not passed
    assert output.startswith("build failed")
    assert ran == ["docs-html"]


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
        index = len(tried) - 1
        return passes(index), f"{LADDER[index]} failed on sphinx-autoapi"

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
    lowest, scanned, blocked = diagnose.scan(
        probe, "matplotlib-base", ">=3.10", "3.11.0"
    )
    assert lowest == "3.10.3"
    assert scanned == ["3.10.0", "3.10.1", "3.10.3"]
    # And it carries no trace: every probe leaves one, so returning the last
    # regardless would report the passing version as having failed on it.
    assert blocked == ""


def test_the_scan_never_goes_above_the_bound(monkeypatch, tmp_path):
    # The bound is what makes the scan terminate. Without it a floor that nothing
    # fixes walks the package's whole release history, and only a case where
    # nothing passes tells the two apart -- a scan that finds an answer would
    # return the same one either way.
    diagnose, probe = _rigged(monkeypatch, tmp_path, lambda _index: False)
    lowest, scanned, _ = diagnose.scan(probe, "matplotlib-base", ">=3.10", "3.10.3")
    assert lowest is None
    assert scanned == ["3.10.0", "3.10.1", "3.10.3"]


def test_the_scan_keeps_what_its_highest_candidate_failed_on(monkeypatch, tmp_path):
    # A scan that finds nothing used to report only the baseline failure, which
    # is the failure of the floors as declared -- what the reader came in
    # knowing. What each candidate failed on went into the probe's `rmtree`,
    # and with it the name of the second broken floor that was stopping them:
    # `docs` reported no passing `sphinx-design`, of a package whose 0.6.1 is
    # sound (:issue:`145`, :issue:`149`). The highest is the one kept: it is the
    # candidate furthest from the floor already known to be broken.
    diagnose, probe = _rigged(monkeypatch, tmp_path, lambda _index: False)
    lowest, scanned, blocked = diagnose.scan(
        probe, "matplotlib-base", ">=3.10", "3.10.3"
    )
    assert lowest is None
    assert blocked == f"{scanned[-1]} failed on sphinx-autoapi"


def test_a_candidate_reports_the_step_that_stopped_it(monkeypatch, tmp_path):
    # Solve and exercise are two different failures and the reader needs to
    # know which one they are reading: a candidate that never resolved says
    # nothing about the exercise, and one that resolved and failed the exercise
    # says the floors are solvable at that version (floors spec §3.5).
    diagnose = _load_diagnose()
    monkeypatch.setattr(diagnose, "exercise", lambda *_: (False, "the exercise"))
    monkeypatch.setattr(diagnose, "solves", lambda *_, **__: (False, "the solver"))
    probe = diagnose.Probe(
        source=tmp_path, scratch=tmp_path, tier="docs", python="3.12"
    )
    assert diagnose._probe_pin(probe, tmp_path, "sphinx-design", "0.6.1") == (
        False,
        "the solver",
    )
    monkeypatch.setattr(diagnose, "solves", lambda *_, **__: (True, "solved"))
    assert diagnose._probe_pin(probe, tmp_path, "sphinx-design", "0.6.1") == (
        False,
        "the exercise",
    )


def test_the_scan_climbs_the_index_the_declaring_table_names(monkeypatch, tmp_path):
    # The scan walks upwards from the declared floor, and where that ladder comes
    # from is a property of the table, not of the package: conda-forge carries
    # `playwright` as well, so a scan that always asked the channel would report
    # a lowest-passing version out of a set the tier never installs from
    # (:issue:`151`). The tests above hold the other direction, `candidates`
    # being the one they stub.
    diagnose, probe = _rigged(monkeypatch, tmp_path, lambda index: index == 1)
    monkeypatch.setattr(diagnose.floors, "releases", lambda *_: ["1.55.0", "1.56.0"])
    lowest, scanned, _ = diagnose.scan(
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


def _sites(tmp_path):
    """Build a checkout whose two declaration sites disagree, as this one's do.

    Every divergence of floors spec §3.1 is here: a package under two names, a
    package the two sites floor in different tiers, and one the manifest
    declares that the pip requirements have no counterpart for.
    """
    (tmp_path / "requirements").mkdir()
    (tmp_path / "requirements" / "pypi-core.txt").write_text(
        "# The core floors.\nmatplotlib>=3.11\n\nclick>=8.1\n", encoding="utf-8"
    )
    (tmp_path / "requirements" / "pypi-optional-test.txt").write_text(
        "pytest>=8.0\nsetuptools_scm>=8\nbuild>=1.5\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """\
            [tool.pixi.dependencies]
            matplotlib-base = ">=3.11"
            click = ">=8.1"
            setuptools-scm = ">=8"

            [tool.pixi.feature.test.dependencies]
            pytest = ">=8.0"
            python-build = ">=1.5"
            make = ">=4.4"

            [tool.pixi.feature.test.pypi-dependencies]
            playwright = ">=1.55"
            """
        ),
        encoding="utf-8",
    )
    return tmp_path


def _probe(diagnose, source, tier="test", half="pypi"):
    """Build a probe reading one checkout, for the half under test."""
    return diagnose.Probe(
        source=source, scratch=source, tier=tier, python="3.12", half=half
    )


def test_each_half_reads_its_floors_from_the_site_it_installs_from(
    monkeypatch, tmp_path
):
    # One relax-and-re-solve loop over two resolvers (floors spec §3.4), so the
    # floors it walks have to come from the site that half installs from: the
    # manifest for conda, the requirements files for PyPI (:issue:`142`). A PyPI
    # diagnosis reading the manifest would relax `matplotlib-base` -- a name the
    # package index has never heard of -- and attribute nothing, every week.
    diagnose = _load_diagnose()
    source = _sites(tmp_path)
    assert diagnose.declared(_probe(diagnose, source)) == {
        "matplotlib": (">=3.11", "core", "pypi-dependencies"),
        "click": (">=8.1", "core", "pypi-dependencies"),
        "pytest": (">=8.0", "test", "pypi-dependencies"),
        "setuptools_scm": (">=8", "test", "pypi-dependencies"),
        "build": (">=1.5", "test", "pypi-dependencies"),
    }
    monkeypatch.setattr(diagnose.floors, "pins", lambda *_: RESOLVED)
    assert diagnose.declared(_probe(diagnose, source, half="conda")) == {
        "click": (">=8.1", "core", "dependencies"),
        "pytest": (">=8.0", "test", "dependencies"),
    }


def test_a_pypi_relaxation_pins_the_version_the_default_resolution_chose(
    monkeypatch, tmp_path
):
    # `--resolution lowest-direct` is a flag over the whole resolution with no
    # per-package escape, so there is no pin here to return to a `>=` the way the
    # conda half does. Dropping the lower bound instead would not relax the
    # requirement at all: unconstrained under `lowest-direct` it resolves
    # *lower*, to the oldest release the index carries, and the loop would then
    # report every floor as unattributable (floors spec §3.4).
    diagnose = _load_diagnose()
    source = _sites(tmp_path)
    monkeypatch.setattr(diagnose, "defaults", lambda _probe: {"click": "8.4.2"})
    monkeypatch.setattr(
        diagnose.subprocess,
        "run",
        lambda command, **_: subprocess.CompletedProcess(command, 0, "", ""),
    )
    assert diagnose.solves(_probe(diagnose, source), source, "click") == (True, "")
    text = (source / "requirements" / "pypi-core.txt").read_text(encoding="utf-8")
    assert "click==8.4.2\n" in text
    # And only that line: a relaxation says nothing about the other floors, and
    # rewriting them too would attribute the failure to whichever was relaxed
    # last (floors spec §3.4).
    assert "matplotlib>=3.11\n" in text


def test_a_package_the_default_resolution_skips_is_not_pinned_to_a_guess(
    monkeypatch, tmp_path
):
    # The version to relax to is read off the default resolution, so a package
    # that resolution does not install -- an extra that this Python or this
    # platform excludes -- has no version to be relaxed to. That is reported as a
    # probe that did not solve, and the loop moves on: pinning it to whatever the
    # index carries latest would attribute the failure to a resolve nobody makes.
    diagnose = _load_diagnose()
    source = _sites(tmp_path)
    monkeypatch.setattr(diagnose, "defaults", lambda _probe: {})
    ran = []
    monkeypatch.setattr(diagnose.subprocess, "run", lambda *_, **__: ran.append(1))
    assert diagnose.solves(_probe(diagnose, source), source, "click") == (False, "")
    assert ran == []
    assert "click>=8.1\n" in (source / "requirements" / "pypi-core.txt").read_text(
        encoding="utf-8"
    )


def test_the_pypi_exercise_runs_the_interpreter_the_probe_installed_into(
    monkeypatch, tmp_path
):
    # The tier is installed into a virtual environment inside the probe, so the
    # exercise has to run *that* interpreter: the one this script runs under has
    # the versions the diagnosis job resolved, not the floors under test, and a
    # suite green there is green about the wrong environment (floors spec §3.3).
    diagnose = _load_diagnose()
    seen = []

    def _run(command, **_):
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(diagnose.subprocess, "run", _run)
    assert diagnose.exercise(_probe(diagnose, tmp_path), tmp_path) == (True, "")
    assert seen == [[str(tmp_path / diagnose.VENV / "bin" / "python"), "-m", "pytest"]]
    # `docs` and `devs` run nothing on this half. The documentation build needs
    # `make`, which the pip declaration does not carry (floors spec §3.1), and
    # the linters report their own rule sets -- so attribution is the whole of
    # their diagnosis, and the exercise passes with nothing to say.
    for tier in ("docs", "devs"):
        assert diagnose.exercise(_probe(diagnose, tmp_path, tier=tier), tmp_path) == (
            True,
            "",
        )
    assert len(seen) == 1


def test_one_floor_keys_on_one_name_where_the_two_sites_spell_it_two_ways(tmp_path):
    # One floor is one issue: the dedupe key is tier and package and it omits
    # the half (floors spec §3.6), so a floor broken in both halves raises one
    # issue for one edit to two lines. Two packages here are spelled
    # differently at the two sites, so
    # the halves reach that key from `matplotlib` and from `matplotlib-base` --
    # without this they file two issues, each sending its reader to the other's
    # file as well.
    diagnose = _load_diagnose()
    source = _sites(tmp_path)
    for half, package in (("pypi", "matplotlib"), ("conda", "matplotlib-base")):
        probe = _probe(diagnose, source, half=half)
        assert diagnose.spellings(probe, package) == ("matplotlib-base", "matplotlib")
    probe = _probe(diagnose, source)
    assert diagnose.spellings(probe, "build") == ("python-build", "build")
    # A name the two sites agree on carries no alias, and the issue then says
    # nothing about how the second file spells it.
    assert diagnose.spellings(probe, "pytest") == ("pytest", "")
    # Nor is a name differing only by PEP 503 normalization a second package:
    # `setuptools_scm` is `setuptools-scm`, and the alias exists to send a reader
    # to a line they can find, not to declare a divergence.
    assert diagnose.spellings(probe, "setuptools_scm") == (
        "setuptools-scm",
        "setuptools_scm",
    )


def test_every_package_the_two_sites_spell_differently_is_reconciled(tmp_path):
    # The alias table is written by hand, and a package added under two names
    # would not announce itself: the halves would simply file two issues the week
    # that floor broke, months from now, and one fix would close one of them. So
    # the divergence is computed from the declarations themselves. Only this
    # direction is a gate -- a manifest declaration with no requirements line is
    # legitimate, `make` being a build tool the pip declaration does not carry
    # (floors spec §3.1) -- and it is the direction that matters, a PyPI finding
    # needing a manifest name to be keyed on.
    diagnose = _load_diagnose()
    # The committed manifest, not the working tree's: the conda half of
    # `ci-floors` runs this suite in a checkout the generator has rewritten,
    # where every feature but the tier's own is gone and half these
    # declarations with it (:issue:`155`).
    manifest = diagnose.floors.declarations(_manifest(tmp_path, _committed_manifest()))
    for tier, path in diagnose.REQUIREMENTS.items():
        names = {**manifest["core"], **manifest.get(tier, {})}
        unmatched = [
            package
            for package in diagnose._requirements(REPO / path)
            if diagnose._match(package, names) is None
        ]
        assert unmatched == [], f"{path}: no manifest declaration"


def test_the_pixi_table_named_is_the_manifest_s_not_the_requirement_s_tier(tmp_path):
    # The two sites need not floor a package in the same tier: `setuptools_scm`
    # is a `test` requirement on the PyPI side and a core declaration in the
    # manifest. Carrying the requirements file's tier over would send the reader
    # to `[tool.pixi.feature.test.dependencies]`, where the edit is to add a
    # second declaration -- and the manifest would then floor it twice.
    diagnose = _load_diagnose()
    probe = _probe(diagnose, _sites(tmp_path))
    assert diagnose._pixi_site(probe, "setuptools-scm", "test") == (
        "core",
        "dependencies",
    )
    assert diagnose._pixi_site(probe, "pytest", "test") == ("test", "dependencies")
    # And the table, which the manifest also answers: a tier declares from the
    # channel and from the package index both, and the issue names the one that
    # carries the floor.
    assert diagnose._pixi_site(probe, "playwright", "test") == (
        "test",
        "pypi-dependencies",
    )


def test_a_probe_copy_leaves_the_leg_s_virtual_environment_behind(tmp_path):
    # A virtual environment records the path it was made at, so a copied one
    # would have the probe reading, and `uv` installing into, the checkout under
    # diagnosis rather than its own copy -- and every probe would then report on
    # the same environment, whatever it had just pinned. Each makes its own, and
    # dropping the copy drops it.
    diagnose = _load_diagnose()
    source = tmp_path / "checkout"
    (source / diagnose.VENV / "bin").mkdir(parents=True)
    (source / diagnose.VENV / "bin" / "python").write_text("#!/bin/sh\n")
    (source / "requirements").mkdir()
    (source / "requirements" / "pypi-core.txt").write_text("click>=8.1\n")
    (tmp_path / "scratch").mkdir()
    probe = diagnose.Probe(
        source=source, scratch=tmp_path / "scratch", tier="test", python="3.12"
    )
    root = diagnose._copy(probe, "baseline")
    assert (root / "requirements" / "pypi-core.txt").is_file()
    assert not (root / diagnose.VENV).exists()


def test_both_scripts_name_the_same_requirements_files():
    # The diagnosis reads the floors from these files and the issue tells its
    # reader to edit them, and the two lists are written out separately -- the
    # composer imports nothing, running as it does on a runner interpreter in the
    # one job that has to work when everything it reports on is red. A rename
    # reaching one and not the other sends the reader to a file the diagnosis was
    # never looking at.
    diagnose, issue = _load_diagnose(), _load_issue()
    assert {
        tier: site["requirements"] for tier, site in issue.SITES.items()
    } == diagnose.REQUIREMENTS
    for name in diagnose.REQUIREMENTS.values():
        assert (REPO / name).is_file()


def test_the_two_halves_run_the_same_tier_names():
    # The dedupe key is tier and package (floors spec §3.6), so a half naming the
    # same tier something else -- `core-test` against `test`, as this workflow
    # did -- files a second issue for one broken floor and one fix. The name is
    # the whole of what joins the halves there, neither carrying the other's
    # spelling of anything.
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    conda = set(jobs["conda"]["strategy"]["matrix"]["tier"])
    pypi = {entry["tier"] for entry in jobs["pypi"]["strategy"]["matrix"]["include"]}
    assert conda == pypi
    diagnose = _load_diagnose()
    assert conda == set(diagnose.EXERCISE) == set(diagnose.PYPI_EXERCISE)


def test_each_half_diagnoses_the_tier_it_ran_and_uploads_what_it_diagnosed():
    # The filing job reads artifacts, so a half that diagnoses and does not
    # upload reaches it with nothing, and one uploading under a name the download
    # pattern misses does the same. Both are silent: the leg is red in its own
    # log, and the issue explaining it never appears (floors spec §3.6).
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    download = next(
        step
        for step in jobs["file"]["steps"]
        if "download-artifact" in (step.get("uses") or "")
    )
    pattern = download["with"]["pattern"]
    for half in ("conda", "pypi"):
        steps = jobs[half]["steps"]
        diagnosed = [s for s in steps if "floors_diagnose.py" in (s.get("run") or "")]
        uploads = [s for s in steps if "upload-artifact" in (s.get("uses") or "")]
        assert len(diagnosed) == 1, f"{half}: diagnoses {len(diagnosed)} times"
        assert f"--half {half}" in diagnosed[0]["run"]
        assert len(uploads) == 1, f"{half}: uploads {len(uploads)} artifacts"
        name = uploads[0]["with"]["name"]
        assert fnmatch.fnmatch(name.replace("${{ matrix.tier }}", "test"), pattern)
        assert half in name


def test_the_filing_job_runs_when_either_half_fails():
    # Both halves produce a finding now (:issue:`142`), and this gate is what
    # decides whether either is read: under a gate naming one half, a PyPI-only
    # failure went red in its own log and filed nothing, having diagnosed
    # nothing. The `always()` is what lets a job needing two failed ones run at
    # all, `needs` being a success condition otherwise.
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    gate = " ".join(jobs["file"]["if"].split())
    assert "always()" in gate
    for half in ("conda", "pypi"):
        assert f"needs.{half}.result == 'failure'" in gate
        assert half in jobs["file"]["needs"]


def test_both_halves_record_the_same_two_lines_to_edit(monkeypatch, tmp_path):
    # The issue names both declaration sites, and it names them off the one
    # finding it was handed -- which for a floor broken in both halves is the
    # conda one, `group` sorting that half first. So a half that filled in only
    # its own site would leave the other's read off a fallback, and for
    # `setuptools_scm` -- a `test` requirement and a core declaration -- the
    # fallback is `requirements/pypi-core.txt`, which declares no such line.
    # Neither site can be read off the other, so both are asked on both halves.
    diagnose = _load_diagnose()
    source = _sites(tmp_path)
    monkeypatch.setattr(
        diagnose.floors,
        "pins",
        lambda *_: {"core": {"setuptools-scm": (">=8", "8.0.0", "dependencies")}},
    )
    monkeypatch.setattr(
        diagnose,
        "attribute",
        lambda probe: (
            "setuptools_scm" if probe.half == "pypi" else "setuptools-scm",
            None,
            "the failure",
        ),
    )
    monkeypatch.setattr(diagnose, "scan", lambda *_: (None, [], ""))
    found = {}
    for half in ("conda", "pypi"):
        out = tmp_path / f"{half}.json"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "floors_diagnose.py",
                "--source",
                str(source),
                "--scratch",
                str(tmp_path / "scratch"),
                "--tier",
                "test",
                "--half",
                half,
                "--out",
                str(out),
            ],
        )
        assert diagnose.main() == 0
        found[half] = json.loads(out.read_text(encoding="utf-8"))
    for half, finding in found.items():
        assert (finding["site"], finding["table"]) == ("core", "dependencies"), half
        assert finding["requirements"] == "requirements/pypi-optional-test.txt", half
        # And on one name, so the two arrive at the filing job under one key.
        assert (finding["package"], finding["alias"]) == (
            "setuptools-scm",
            "setuptools_scm",
        ), half


def test_a_floor_the_pip_requirements_do_not_carry_names_no_file(tmp_path):
    # `make` drives the documentation build and has no PyPI counterpart worth
    # declaring (floors spec §3.1). Naming its tier's requirements file anyway
    # would send the reader to a file with no such line, which reads exactly
    # like a line they failed to find -- so the empty answer is kept, and the
    # issue says the floor is declared once rather than naming a second site.
    diagnose = _load_diagnose()
    probe = _probe(diagnose, _sites(tmp_path), half="conda")
    assert diagnose._pypi_site(probe, "make") == ""
    assert diagnose._pypi_site(probe, "click") == "requirements/pypi-core.txt"
    # Under either site's spelling, the requirements file being the half that
    # writes `build` where the manifest writes `python-build`.
    for name in ("python-build", "build"):
        assert diagnose._pypi_site(probe, name) == "requirements/pypi-optional-test.txt"


def _roots(tree):
    """Return every name a module binds to the repository root.

    Read from the module rather than assumed, because the name is a local
    choice and a fixed list is a guess about other people's files:
    `tests/test_browser_demo.py` calls its root `REPOSITORY`, so a detector
    holding only `REPO` would have waved that module's manifest reads through
    while reporting the identical line here. Anything derived from `__file__`
    by walking up is a root, however the module spells it.
    """
    roots = {"REPO", "ROOT", "REPOSITORY"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        parts = list(ast.walk(node.value))
        if not any(
            isinstance(part, ast.Name) and part.id == "__file__" for part in parts
        ):
            continue
        if not any(
            isinstance(part, ast.Attribute) and part.attr in {"parent", "parents"}
            for part in parts
        ):
            continue
        roots.update(
            target.id for target in node.targets if isinstance(target, ast.Name)
        )
    return roots


def _manifest_path(node, roots):
    """Whether an expression builds a path to the repository's own manifest."""
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
        return False
    if not isinstance(node.right, ast.Constant) or node.right.value != "pyproject.toml":
        return False
    return any(
        (isinstance(part, ast.Name) and part.id in roots)
        or (isinstance(part, ast.Attribute) and part.attr in roots)
        for part in ast.walk(node.left)
    )


def _reads_manifest(source):
    """Report every line building a path to the repository's own manifest.

    Building it is what is reported, rather than any particular use of it: a
    path is passed to a call, but it is equally the receiver of one, bound to a
    name three lines above the call, returned by a helper or closed over. An
    argument-only detector waves all but the first of those through, and the
    shape it misses is the ordinary one -- `(REPO / "pyproject.toml").read_text()`
    (:pull:`164`). Reporting construction needs no dataflow to follow an alias,
    because the line that makes the alias is itself the report.

    The single exempt use is an operand of a comparison, which names the path
    without opening it -- `test_citations` asserts the manifest is among the
    files `git ls-files` tracks. The exemption is that operand and not the
    comparison, so a genuine read inside one is still reported.
    """
    tree = ast.parse(source)
    roots = _roots(tree)
    named = {
        id(operand)
        for node in ast.walk(tree)
        for operand in (
            [node.left, *node.comparators] if isinstance(node, ast.Compare) else []
        )
    }
    return [
        node.lineno
        for node in ast.walk(tree)
        if _manifest_path(node, roots) and id(node) not in named
    ]


def test_no_test_reads_the_manifest_the_floors_job_rewrites():
    # The conda half of `ci-floors` runs this suite in a checkout whose
    # `pyproject.toml` the generator has rewritten: one environment, every floor
    # an `==` pin, and every feature the tier cannot reach dropped outright. A
    # test reading it from the working tree passes everywhere but there, where
    # it fails once a week, hours after the push that broke it, and takes the
    # tier's whole verdict down with it -- the job then files an issue about a
    # failure that is not a floor. That has now happened twice (:issue:`155`),
    # the second time to the test that reconciles the two sites' names above.
    # `_committed_manifest` reads it from the index instead.
    scanned = sorted((REPO / "tests").rglob("*.py"))
    offenders = [
        f"{path.name}:{line}"
        for path in scanned
        for line in _reads_manifest(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
    # A gate whose corpus emptied would pass having read nothing, and this one
    # globs for its own.
    assert len(scanned) > 1


@pytest.mark.parametrize(
    ("source", "reads"),
    [
        ('floors.declarations(REPO / "pyproject.toml")', True),
        ('floors.pins(cc.REPO / "pyproject.toml", version)', True),
        ('read(text=REPO / "pyproject.toml")', True),
        # The two shapes an argument-only detector missed: the manifest read as
        # the receiver of the call rather than its argument, and the path bound
        # to a name first, which is where most of this suite's file reads would
        # naturally be written.
        ('(REPO / "pyproject.toml").read_text()', True),
        ('manifest = REPO / "pyproject.toml"', True),
        ('tomllib.loads((cc.ROOT / "pyproject.toml").read_text())', True),
        # Naming the path is not reading it: `test_citations` asserts the
        # manifest is in the citation corpus, which is a list of what `git
        # ls-files` tracks and so says nothing about the file's contents. A gate
        # that flagged this would be one the next reader turns off.
        ('assert cc.REPO / "pyproject.toml" in paths', False),
        # A comparison exempts the operand, not everything under it, or the
        # rule would be off wherever a read is asserted on -- which is most of
        # the ways one would be written.
        ('assert (REPO / "pyproject.toml").read_text() == expected', True),
        # The two shapes that are already right, and have to stay unflagged or
        # the fix for an offender is itself an offence.
        ("floors.declarations(_manifest(tmp_path, _committed_manifest()))", False),
        ('floors.declarations(tmp_path / "pyproject.toml")', False),
        ('(tmp_path / "pyproject.toml").write_text(text)', False),
        # And it is this file that is rewritten, not everything beside it.
        ('read(REPO / "requirements" / "pypi-core.txt")', False),
        # The root is whatever the module calls it. `test_browser_demo` says
        # `REPOSITORY`, and a name this gate had not been told about would have
        # made its manifest reads invisible rather than reported.
        ('tomllib.loads((REPOSITORY / "pyproject.toml").read_text())', True),
        (
            (
                "HERE = Path(__file__).parents[1]\n"
                'floors.declarations(HERE / "pyproject.toml")'
            ),
            True,
        ),
        (
            (
                "HERE = Path(__file__).parent.parent\n"
                'assert HERE / "pyproject.toml" in paths'
            ),
            False,
        ),
    ],
)
def test_the_manifest_gate_reads_a_build_and_not_a_mention(source, reads):
    # Widening a detector invites false positives, and the legitimate lookalike
    # here is already in the tree -- so both directions are probed, rather than
    # the gate above being trusted because the corpus it reads happens to pass.
    assert bool(_reads_manifest(source)) is reads
