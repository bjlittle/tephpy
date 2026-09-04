# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Import a module that lives outside any importable package, by path.

Two directories hold modules this suite exercises and cannot import normally.
``docs/src/_ext`` is a ``sys.path`` entry at documentation-build time rather
than a package (:issue:`92`), and ``.github/scripts`` is executed by path and
pruned from the sdist by ``MANIFEST.in``. A module in either resolves its
siblings by top-level name, which is why each directory goes on ``sys.path``
before the module is executed; `load_path` serves the modules that need no
such entry, under a name that need not be the file's own.

Shared rather than copied (:issue:`265`): a loader that drifts between copies
loads different code in each, and the copies had drifted over exactly that
``sys.path`` insertion. ``tests/test_by_path.py`` holds the tree to one copy.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

REPO = Path(__file__).parents[1]
EXT = REPO / "docs" / "src" / "_ext"
SCRIPTS = REPO / ".github" / "scripts"


def load_path(name: str, path: Path) -> ModuleType:
    """Import the module at ``path``, executing it under ``name``.

    Adds nothing to ``sys.path``, so a module that resolves a sibling by
    top-level name needs `load_ext` or `load_script` instead.

    Parameters
    ----------
    name : str
        The name to execute and register the module under. It need not be the
        file's stem: a module staged into the documentation build is named for
        where it ends up rather than where it is written.
    path : Path
        The module's location.

    Returns
    -------
    module
        The executed module.

    """
    # The file is asserted on rather than the `ModuleSpec`: a spec comes back
    # populated even for a path that does not exist, so the checks it invites
    # are dead, and the module fails later and somewhere else instead.
    assert path.is_file(), f"the module is missing from {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_from(directory: Path, name: str) -> ModuleType:
    """Import ``name`` from ``directory``, which its siblings resolve through."""
    path = directory / f"{name}.py"
    # Verified before `sys.path` is touched, so a mistyped name leaves the
    # import path as it found it.
    assert path.is_file(), f"the module is missing from {path}"
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
    return load_path(name, path)


def load_ext(name: str) -> ModuleType:
    """Import a documentation extension module from ``docs/src/_ext``.

    Parameters
    ----------
    name : str
        The module's top-level name, without the ``.py`` suffix.

    Returns
    -------
    module
        The executed module.

    """
    return _load_from(EXT, name)


def load_script(name: str) -> ModuleType:
    """Import a repository script from ``.github/scripts``.

    A tree without that directory -- a copy taken without its dotted
    directories, say -- has nothing to load, so a module calling this at import
    time guards itself for it, since the failure would otherwise be a collection
    error taking the rest of the suite with it. See ``tests/test_floors.py``.

    Parameters
    ----------
    name : str
        The script's name, without the ``.py`` suffix.

    Returns
    -------
    module
        The executed module.

    """
    return _load_from(SCRIPTS, name)
