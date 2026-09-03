# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Import a documentation extension module by path.

``docs/src/_ext`` is a ``sys.path`` entry at build time rather than a package
(:issue:`92`), so a module there resolves its siblings by top-level name and
cannot be imported until that entry exists. Shared rather than copied: three
test modules need it, and a loader that drifts between copies loads different
code in each.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

EXT = Path(__file__).parents[1] / "docs" / "src" / "_ext"


def load(name: str) -> ModuleType:
    """Import an extension module by path.

    Parameters
    ----------
    name : str
        The module's top-level name, without the ``.py`` suffix.

    Returns
    -------
    module
        The executed module.

    """
    if str(EXT) not in sys.path:
        sys.path.insert(0, str(EXT))
    path = EXT / f"{name}.py"
    assert path.is_file(), f"the module is missing from {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
