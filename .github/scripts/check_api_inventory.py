#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check the API gate's surface is the one published (:issue:`227`).

``check_api_docstrings.py`` reproduces sphinx-autoapi's selection without a
build, so it can run in the test suite and fail on the commit that introduces
a defect. This gate is what earns that shortcut: it reads the ``objects.inv``
a real build wrote and compares the two sets.

Not a formality. The enumerator's first cut found 156 objects against the
published 94 -- every one of the 62 extra a re-export, because ``vars`` on a
module holds its imports too. The rule that settles it (an object is published
by the module that *defines* it) is not one the module layout would suggest,
and neither is ``tephpy.config``: a private module's singleton whose methods
are published while its property is not. Both are held here rather than
asserted in a comment, so the day autoapi changes its mind the build says so.

A script rather than a pytest invocation because the ``docs`` environment
carries no pytest, and because every other documentation gate is a script
taking the build root -- ``check_rendered_citations.py``,
``check_documentation_links.py``, ``check_docs_figures.py``.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING
import zlib

if TYPE_CHECKING:
    import types

REPO = Path(__file__).parents[2]

#: Inventory roles that own a docstring, and so can carry a directive. The two
#: left out are ``py:attribute`` and ``py:data``: a dataclass field is
#: documented in its class's ``Attributes`` section and a ``#:`` comment is not
#: a docstring, so neither has anywhere to put one.
DOCSTRING_ROLES = frozenset(
    {
        "py:module",
        "py:class",
        "py:exception",
        "py:function",
        "py:method",
        "py:property",
    }
)

#: The four plain-text header lines that precede an inventory's zlib stream.
HEADER_LINES = 4

ENTRY = re.compile(r"(?P<name>\S+)\s+(?P<role>\S+)\s+-?\d+\s+\S*\s+.*")


def load_gate() -> types.ModuleType:
    """Import the docstring gate, a sibling script rather than a module.

    Returns
    -------
    types.ModuleType
        ``check_api_docstrings``, executed.
    """
    script = Path(__file__).with_name("check_api_docstrings.py")
    spec = importlib.util.spec_from_file_location("check_api_docstrings", script)
    if spec is None or spec.loader is None:  # pragma: no cover -- defensive
        msg = f"could not load {script}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def published_names(inventory: Path) -> set[str]:
    """Read the documented ``tephpy`` objects from a built inventory.

    Parameters
    ----------
    inventory : pathlib.Path
        The ``objects.inv`` a documentation build wrote.

    Returns
    -------
    set of str
        Dotted names whose role owns a docstring.
    """
    raw = inventory.read_bytes()
    offset = 0
    for _ in range(HEADER_LINES):
        offset = raw.index(b"\n", offset) + 1
    body = zlib.decompress(raw[offset:]).decode("utf-8")
    names = set()
    for line in body.splitlines():
        match = ENTRY.match(line)
        if match is None:
            continue
        if match["name"].startswith("tephpy") and match["role"] in DOCSTRING_ROLES:
            names.add(match["name"])
    return names


def main() -> int:
    """Compare the enumerated surface with the published one.

    Returns
    -------
    int
        ``0`` when the two sets are identical, ``1`` otherwise.
    """
    if len(sys.argv) != 2:
        print("usage: check_api_inventory.py <html-root>")
        return 1
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"no such directory: {root}")
        return 1
    inventory = root / "objects.inv"
    if not inventory.is_file():
        print(f"no inventory at {inventory}")
        return 1

    gate = load_gate()
    enumerated = {entry.name for entry in gate.published_objects()}
    published = published_names(inventory)
    if not published:
        # A gate over nothing passes everything.
        print(f"{inventory} names no tephpy objects")
        return 1

    extra = sorted(enumerated - published)
    missing = sorted(published - enumerated)
    if extra or missing:
        print(
            "the API gate's surface is not the one published "
            "(check_api_docstrings.published_objects, :issue:`227`):\n"
        )
        for name in extra:
            print(f"  enumerated, not published : {name}")
        for name in missing:
            print(f"  published, not enumerated : {name}")
        return 1

    print(
        f"API surface ok: {len(enumerated)} published objects, "
        f"enumerated and published agree"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
