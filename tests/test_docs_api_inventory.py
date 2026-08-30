# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The API gate's surface matches what the documentation publishes (:issue:`227`).

``check_api_docstrings.published_objects`` reproduces sphinx-autoapi's
selection without a build, so the gate can run in pre-commit and fail on the
commit that introduces a defect. This test is what earns that shortcut: it
reads the ``objects.inv`` a real build wrote and asserts the two sets are
identical, in both directions.

It is not a formality. The first cut of the enumerator found 156 objects
against the published 94 -- every one of the 62 extra a re-export, because
``vars`` on a module holds its imports too. The rule that settles it (an
object is published by the module that *defines* it) is not something a
reader would derive from the module layout, and neither is
``tephpy.config``: a private module's singleton whose methods are published
while its property is not. Both are pinned here rather than asserted in a
comment, so the day autoapi changes its mind the build says so.
"""

from __future__ import annotations

from pathlib import Path
import re
import zlib

import pytest

REPO = Path(__file__).parents[1]
INVENTORY = REPO / "docs" / "_build" / "html" / "objects.inv"

#: Inventory roles that own a docstring, and so can carry a directive. The
#: roles left out are ``py:attribute`` and ``py:data``: a dataclass field is
#: documented in its class's ``Attributes`` section and a ``#:`` comment is
#: not a docstring, so neither has anywhere to put one.
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
_HEADER_LINES = 4

_ENTRY = re.compile(r"(?P<name>\S+)\s+(?P<role>\S+)\s+-?\d+\s+\S*\s+.*")


def _published_names() -> set[str]:
    """Read the documented ``tephpy`` objects from the built inventory.

    Returns
    -------
    set of str
        Dotted names whose role owns a docstring.
    """
    raw = INVENTORY.read_bytes()
    offset = 0
    for _ in range(_HEADER_LINES):
        offset = raw.index(b"\n", offset) + 1
    body = zlib.decompress(raw[offset:]).decode("utf-8")
    names = set()
    for line in body.splitlines():
        match = _ENTRY.match(line)
        if match is None:
            continue
        name, role = match["name"], match["role"]
        if name.startswith("tephpy") and role in DOCSTRING_ROLES:
            names.add(name)
    return names


needs_build = pytest.mark.skipif(
    not INVENTORY.exists(),
    reason="needs a documentation build; run `pixi run docs-html` first",
)


@needs_build
def test_the_enumerated_surface_is_the_published_surface(gate):
    """Neither set may hold a name the other does not.

    Reported as two assertions rather than one equality so a failure names
    the direction: an extra is the gate inventing API, a missing one is the
    gate letting a published docstring go unchecked.
    """
    enumerated = {entry.name for entry in gate.published_objects()}
    published = _published_names()
    assert sorted(enumerated - published) == [], "enumerated but not published"
    assert sorted(published - enumerated) == [], "published but not enumerated"


@needs_build
def test_the_surface_is_not_accidentally_empty(gate):
    """A gate over nothing passes everything.

    Both sets are read from the same two mechanisms this test compares, so a
    breakage that emptied them would satisfy the equality above in silence.
    """
    assert len(_published_names()) > 50
    assert len(gate.published_objects()) == len(_published_names())
