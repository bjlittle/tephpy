# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""What keeps the `tests` package importable however pytest was started.

The tests tree is a real package (spec §8.5) and three modules reach a sibling
through it by dotted name, `tests/pixi_tasks.py` being the one they share. Under
`--import-mode=importlib` that import is not served by the import of the test
module itself: pytest below 8.2 puts a *placeholder* `tests` in `sys.modules`
with no `__path__` on it, so resolving `tests.pixi_tasks` falls back to
`sys.path` -- and whether the repository root is on `sys.path` is decided by how
pytest was started, not by anything this repository declares. `python -m pytest`
puts it there; the `pytest` console script does not.

The two halves of `ci-floors` start it the two ways, which is how a floor that
had been false since :pull:`179` surfaced as one half red and the other green
with the same pytest 8.0.0 (:issue:`185`). Nothing catches it here, where the
lockfile pins a pytest new enough not to need `sys.path` at all.

So the repository declares the path rather than inheriting it, and this module
holds it to that: `pythonpath` naming the root, and a corpus of imports that is
the reason for it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]

#: The tests tree's own name, as `tests/io/__init__.py` is reached by.
PACKAGE = "tests"

#: The modules importing through `PACKAGE` today. The list is asserted on rather
#: than merely counted: a corpus that emptied would leave the declaration below
#: passing with nothing behind it, and the honest reading of an empty scan is
#: that the scan broke -- these three have imported a sibling since :pull:`179`.
IMPORTERS = {
    "test_docs_workflow.py",
    "test_floors.py",
    "test_pixi_tasks.py",
}


def _rooted(name):
    """Whether a dotted name is `tests` or something inside it."""
    return name is not None and (name == PACKAGE or name.startswith(f"{PACKAGE}."))


def _import_module_call(node):
    """Whether a call is `import_module` naming something inside `tests`."""
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
    if name != "import_module":
        return False
    return any(
        isinstance(arg, ast.Constant)
        and isinstance(arg.value, str)
        and _rooted(arg.value)
        for arg in node.args
    )


def _dotted_imports(source):
    """Report every line reaching into the `tests` package by its dotted name.

    Wider than the three lines that need it today, because what the declaration
    below buys is the whole class: `from tests.pixi_tasks import runs` is the
    shape in the tree, but `import tests.pixi_tasks`, `from tests import
    pixi_tasks` and an `import_module` of the same string all resolve through
    the same absent parent, and a detector reading only the first would report
    a corpus of nothing the day someone wrote one of the others.

    A relative import is not reported. None is written here, and one would be a
    different question anyway -- it resolves through `__package__` on the module
    already imported rather than through `sys.path`.
    """
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            if not node.level and _rooted(node.module):
                found.append(node.lineno)
        elif isinstance(node, ast.Import):
            if any(_rooted(alias.name) for alias in node.names):
                found.append(node.lineno)
        elif isinstance(node, ast.Call) and _import_module_call(node):
            found.append(node.lineno)
    return sorted(found)


def test_the_repository_root_is_on_the_path_pytest_builds(pytestconfig):
    # Asked of the running session and not of `pyproject.toml`, so that what is
    # asserted is the configuration in force rather than the file it usually
    # comes from -- and so that the conda half of `ci-floors`, which runs this
    # suite against a manifest the floors generator has rewritten, is reading
    # its own answer (:issue:`155`).
    assert pytestconfig.rootpath in pytestconfig.getini("pythonpath")


def test_the_modules_that_need_that_path_are_still_here():
    # The declaration above is a line in a file; this is what it is for. Were
    # the last dotted import to go, the two would want removing together, and a
    # scan that had quietly stopped matching would say exactly the same thing.
    scanned = sorted((REPO / PACKAGE).rglob("*.py"))
    importers = {
        path.name for path in scanned if _dotted_imports(path.read_text("utf-8"))
    }
    assert importers >= IMPORTERS


@pytest.mark.parametrize(
    ("source", "reaches"),
    [
        ("from tests.pixi_tasks import runs", True),
        ("import tests.pixi_tasks", True),
        ("from tests import pixi_tasks", True),
        ("import tests.pixi_tasks as helpers", True),
        ("importlib.import_module('tests.pixi_tasks')", True),
        ("import_module('tests')", True),
        # Imported inside a function, which is where a test reaching for an
        # optional dependency's helper would naturally put it.
        ("def f():\n    from tests.pixi_tasks import runs", True),
        # The near-misses. A prefix is not a package boundary, and the string
        # only reaches the parent when something imports it: quoted anywhere
        # else it is a path fragment, an id, or a word.
        ("from tests_helper import runs", False),
        ("import contests", False),
        ("from itertools import pairwise", False),
        ("mpl_baseline = 'tests/baseline'", False),
        ("assert name == 'tests.pixi_tasks'", False),
        # A relative import, which the module docstring above rules out.
        ("from . import pixi_tasks", False),
    ],
)
def test_the_detector_reads_each_shape_of_a_tests_rooted_import(source, reaches):
    assert bool(_dotted_imports(source)) is reaches
