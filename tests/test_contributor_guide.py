# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The contributor guide's pages exist and are reachable (contributor spec §3.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]
DEVELOPER = REPO / "docs" / "src" / "developer"
INDEX = DEVELOPER / "index.rst"

#: The pages contributor spec §3.1 adds, in the order contributor spec §4 gives
#: the toctree.
#: Each page task appends its own as it lands, so every commit is green and
#: each keeps its own red-to-green.
PAGES = ("contributing", "testing", "changelog", "ci")


@pytest.mark.parametrize("page", PAGES)
def test_each_new_page_exists(page):
    assert (DEVELOPER / f"{page}.rst").is_file()


@pytest.mark.parametrize("page", PAGES)
def test_each_new_page_is_in_the_toctree(page):
    # A page absent from every toctree is caught by the fail-on-warning build,
    # but an `:orphan:` one builds clean -- the hole tests/test_docs_landing_pages.py
    # closes for the quadrants and this closes here.
    entries = [
        line.strip()
        for line in INDEX.read_text(encoding="utf-8").splitlines()
        if line.startswith("    ") and line.strip() and not line.strip().startswith(":")
    ]
    assert page in entries


@pytest.mark.parametrize("page", PAGES)
def test_each_new_page_carries_a_reading_time_banner(page):
    # Measured 2026-09-08: test_docs_readingtime.py exempts only the two index
    # pages, so a developer page without a banner fails that gate too. Asserted
    # here as well so the failure names the page being written.
    text = (DEVELOPER / f"{page}.rst").read_text(encoding="utf-8")
    assert ".. readingtime::" in text
