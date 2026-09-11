# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The plotting tour names code that exists (tour spec §5)."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

import tephpy
from tephpy.plotting import _theme, barbs, isopleths, logo, shading
from tephpy.plotting import axes as axes_module
from tephpy.plotting.axes import TephigramAxes
from tephpy.plotting.barbs import BarbStaff
from tephpy.plotting.isopleths import IsoplethFamily

REPO = Path(__file__).parents[1]
PAGE = REPO / "docs" / "src" / "developer" / "plotting.rst"
PACKAGE = REPO / "src" / "tephpy" / "plotting"

#: What each gate's floor is for, which differs between them. The module map
#: has ground truth on disk, so the set comparison says exactly which module
#: lost its row and the floor need only catch a parser that found *nothing* --
#: a count-based floor front-ran that comparison and blamed the markup for a
#: deleted row (found in review, :pull:`303`). The private helpers have no such
#: ground truth: nothing enumerates the names a page ought to mention, so there
#: the floor is the whole defence and is a count.

#: Public names the page must name and which must resolve. The private
#: helpers are found by pattern instead (they are unambiguous), but a public
#: method is an ordinary word and cannot be, so these are declared.
PUBLIC_SPINE = (
    "TephigramAxes",
    "add_logo",
    "IsoplethFamily",
    "clear",
    "configure",
    "edge_axis",
    "format_coord",
    "plot_barbs",
    "annotate_indices",
)

#: Where a name may resolve. Measured 2026-09-11 against the page's own text:
#: the modules alone are not enough. ``configure`` is a method of
#: ``IsoplethFamily`` and lands on no module, and ``_constants`` is a sibling
#: package of ``plotting`` rather than a name inside it -- so the classes the
#: page names and the ``tephpy`` root both hold names it legitimately mentions.
_HOLDERS = (
    TephigramAxes,
    IsoplethFamily,
    BarbStaff,
    axes_module,
    isopleths,
    shading,
    barbs,
    logo,
    _theme,
    tephpy,
)


def _literals(text: str) -> set[str]:
    """Every ``double backtick`` literal on the page."""
    return set(re.findall(r"``([^`]+)``", text))


def _list_tables(text: str) -> list[str]:
    """Return the body of every ``list-table`` on the page."""
    bodies, body, inside = [], [], False
    for line in text.splitlines():
        if line.startswith(".. list-table::"):
            if inside:
                bodies.append("\n".join(body))
            body, inside = [], True
            continue
        if inside:
            if line and not line.startswith(" "):
                bodies.append("\n".join(body))
                body, inside = [], False
            else:
                body.append(line)
    if inside:
        bodies.append("\n".join(body))
    return bodies


def _module_rows(text: str) -> set[str]:
    """Return the module names the map's own table has a row for.

    Scoped to the table rather than to the page. A module name also appears
    in the prose beneath the table and in the *Where to Look* table, so a
    page-wide scan would report a deleted row as present -- the false green
    a review found on :pull:`303`, reproduced before this was narrowed.
    """
    for body in _list_tables(text):
        if "- Module" in body:
            return {lit for lit in _literals(body) if lit.endswith(".py")}
    return set()


def _private_names(text: str) -> set[str]:
    """Every private helper the page names, e.g. ``_claim_edge``."""
    return {lit for lit in _literals(text) if re.fullmatch(r"_[a-z][a-z0-9_]*", lit)}


def _resolves(name: str) -> bool:
    """Whether `name` is a real attribute of the plotting package."""
    return any(hasattr(holder, name) for holder in _HOLDERS)


def test_every_module_in_the_package_has_a_row():
    rows = _module_rows(PAGE.read_text(encoding="utf-8"))
    assert rows, (
        "the module map parsed no rows at all -- the table's markup, or its "
        "'Module' header, has changed under the parser"
    )
    on_disk = {path.name for path in PACKAGE.glob("*.py")}
    assert not on_disk - rows, f"{sorted(on_disk - rows)} has no row on the map"


def test_the_map_names_no_module_that_is_gone():
    rows = _module_rows(PAGE.read_text(encoding="utf-8"))
    on_disk = {path.name for path in PACKAGE.glob("*.py")}
    assert not rows - on_disk, f"the map names {sorted(rows - on_disk)}, which is gone"


def test_every_private_helper_the_page_names_resolves():
    names = _private_names(PAGE.read_text(encoding="utf-8"))
    assert len(names) >= 3, (
        f"the page names {len(names)} private helpers; the tour describes two flows "
        "through at least three, so the parser has stopped matching"
    )
    missing = sorted(name for name in names if not _resolves(name))
    assert not missing, f"the page names {missing}, which no longer exist"


@pytest.mark.parametrize("name", PUBLIC_SPINE)
def test_each_public_spine_name_is_named_and_resolves(name):
    # Matched on a word boundary rather than as a whole literal: the page names
    # some of these inside a longer expression, e.g. ``ax.edge_axis("top")``.
    page = PAGE.read_text(encoding="utf-8")
    assert re.search(rf"\b{re.escape(name)}\b", page), (
        f"the page no longer names {name!r}"
    )
    assert _resolves(name), f"{name!r} no longer exists in tephpy.plotting"


def test_the_row_parser_finds_nothing_without_the_table():
    # The floor is the point: prove it fails rather than trusting it would.
    assert _module_rows("a page with ``prose`` but no table") == set()


def test_a_module_named_only_in_prose_is_not_a_row():
    # The defect a review found on :pull:`303`: the parser read the whole page,
    # so a module deleted from the table still counted, because the prose
    # beneath the table names the two largest modules.
    page = """
The Modules
-----------

.. list-table::
    :header-rows: 1

    * - Module
      - What it owns
    * - ``isopleths.py``
      - the five families

``axes.py`` and ``isopleths.py`` carry three quarters of the package.
"""
    assert _module_rows(page) == {"isopleths.py"}


def test_the_where_to_look_table_is_not_the_module_map():
    # Two list-tables on the page, and only one of them is the map.
    page = """
.. list-table::
    :header-rows: 1

    * - Changing
      - Read first
    * - a family's labels
      - the ``isopleths.py`` module docstring
"""
    assert _module_rows(page) == set()


def test_the_name_parser_reports_a_helper_that_is_gone():
    assert _private_names("the diagram calls ``_no_such_helper`` on a clear") == {
        "_no_such_helper"
    }
    assert not _resolves("_no_such_helper")
