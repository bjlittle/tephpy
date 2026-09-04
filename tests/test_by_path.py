# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The shared by-path module loader, and the single copy of it (:issue:`265`)."""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

import pytest

from tests.by_path import EXT, SCRIPTS, load_ext, load_path, load_script

REPO = Path(__file__).parents[1]
TESTS = REPO / "tests"

#: The import machinery a by-path loader is made of. Either name is enough to
#: identify a private copy: a module that calls one calls the other.
MACHINERY = frozenset({"spec_from_file_location", "module_from_spec"})


def _called_names(source: str) -> set[str]:
    """Return the name of every function ``source`` calls, however qualified."""
    found = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            found.add(func.attr)
        elif isinstance(func, ast.Name):
            found.add(func.id)
    return found


@pytest.fixture
def registry():
    """Restore ``sys.modules`` and ``sys.path`` around a load."""
    modules, path = dict(sys.modules), list(sys.path)
    yield
    sys.modules.clear()
    sys.modules.update(modules)
    sys.path[:] = path


def test_only_the_shared_helper_imports_by_path():
    # Read as syntax rather than as text: this module names the machinery in
    # `MACHINERY` above, so a grep of the tree would find itself and pass. What
    # the consolidation forbids is a *call* -- naming one in a string, a comment
    # or a docstring is how the convention gets explained, and must stay legal.
    found = sorted(
        path.relative_to(TESTS).as_posix()
        for path in TESTS.rglob("*.py")
        if MACHINERY & _called_names(path.read_text(encoding="utf-8"))
    )
    assert found == ["by_path.py"]


@pytest.mark.usefixtures("registry")
def test_an_extension_module_resolves_its_siblings_by_bare_name():
    # Guarded per-test rather than at module scope: `tephpy_topics` reaches
    # Sphinx, which only the `docs` feature installs, and the gate below must
    # run in the `test-py3*` environments the CI matrix runs.
    pytest.importorskip("sphinx", reason="the docs feature is not installed here")
    # `docs/src/_ext` is a `sys.path` entry at build time rather than a package
    # (:issue:`92`), so `tephpy_topics` reaches `tephpy_topics_data` by
    # top-level name. Loading it is what proves the entry is there: asserting
    # on `sys.path` would pass with the module still unimportable.
    module = load_ext("tephpy_topics")
    assert module.__file__ == str(EXT / "tephpy_topics.py")
    assert module.data.__file__ == str(EXT / "tephpy_topics_data.py")


@pytest.mark.skipif(
    not (SCRIPTS / "bless_docs_figures.py").is_file(),
    reason="not a checkout of the repository",
)
@pytest.mark.usefixtures("registry")
def test_a_script_resolves_its_siblings_by_bare_name():
    # The same property one directory over: `bless_docs_figures` does
    # `from check_docs_figures import ...`, which resolves when Python runs the
    # script -- its directory becomes `sys.path[0]` -- and not otherwise. This
    # is the difference the private copies had drifted apart on.
    module = load_script("bless_docs_figures")
    assert module.__file__ == str(SCRIPTS / "bless_docs_figures.py")
    assert sys.modules["check_docs_figures"].__file__ == str(
        SCRIPTS / "check_docs_figures.py"
    )


@pytest.mark.usefixtures("registry")
def test_a_module_outside_both_directories_loads_under_the_name_it_is_given(
    tmp_path,
):
    source = tmp_path / "source.py"
    source.write_text("VALUE = 42\n", encoding="utf-8")
    module = load_path("aliased", source)
    assert module.VALUE == 42
    assert sys.modules["aliased"] is module


@pytest.mark.usefixtures("registry")
def test_the_primitive_leaves_sys_path_alone(tmp_path):
    # `load_path` serves modules that ask for nothing but themselves, so it
    # adds no import path: a caller that needs one names a directory by
    # reaching for `load_ext` or `load_script` instead.
    source = tmp_path / "source.py"
    source.write_text("VALUE = 42\n", encoding="utf-8")
    load_path("aliased", source)
    assert str(tmp_path) not in sys.path


def test_a_missing_module_names_the_path_it_was_looked_for_at(tmp_path):
    # A `ModuleSpec` comes back populated for a path that does not exist, so a
    # loader checking the spec reports nothing and fails later, somewhere else.
    absent = tmp_path / "absent.py"
    with pytest.raises(AssertionError, match=re.escape(str(absent))):
        load_path("absent", absent)


@pytest.mark.usefixtures("registry")
def test_a_missing_script_names_the_directory_it_was_looked_for_in():
    with pytest.raises(AssertionError, match=re.escape(str(SCRIPTS))):
        load_script("check_nothing_at_all")


@pytest.mark.usefixtures("registry")
def test_a_missing_extension_module_names_the_directory_it_was_looked_for_in():
    with pytest.raises(AssertionError, match=re.escape(str(EXT))):
        load_ext("tephpy_nothing_at_all")
