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

#: The modules the map must have a row for. Seven today; the floor below is
#: what makes a parser that matched nothing fail rather than pass.
MODULE_FLOOR = 7

#: Public names the page must name and which must resolve. The private
#: helpers are found by pattern instead (they are unambiguous), but a public
#: method is an ordinary word and cannot be, so these are declared.
PUBLIC_SPINE = (
    "TephigramAxes",
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


def _module_rows(text: str) -> set[str]:
    """Return the module names the map has a row for."""
    return {lit for lit in _literals(text) if lit.endswith(".py")}


def _private_names(text: str) -> set[str]:
    """Every private helper the page names, e.g. ``_claim_edge``."""
    return {lit for lit in _literals(text) if re.fullmatch(r"_[a-z][a-z0-9_]*", lit)}


def _resolves(name: str) -> bool:
    """Whether `name` is a real attribute of the plotting package."""
    return any(hasattr(holder, name) for holder in _HOLDERS)


def test_every_module_in_the_package_has_a_row():
    rows = _module_rows(PAGE.read_text(encoding="utf-8"))
    assert len(rows) >= MODULE_FLOOR, (
        f"the module map parsed {len(rows)} rows, fewer than the {MODULE_FLOOR} "
        "modules that exist -- the table's markup has changed under the parser"
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


def test_the_name_parser_reports_a_helper_that_is_gone():
    assert _private_names("the diagram calls ``_no_such_helper`` on a clear") == {
        "_no_such_helper"
    }
    assert not _resolves("_no_such_helper")
