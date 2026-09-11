# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""A landing page's table and its toctree are one list (narrative spec §3.9)."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

REPO = Path(__file__).parents[1]
DOCS = REPO / "docs" / "src"

#: The sections whose landing page carries a table (narrative spec §3.9).
#:
#: **Not the same set as the two constants named ``USER_SECTIONS``**, which is why this
#: one is not called that either. ``check_glossary_links.py`` names the sections the
#: glossary serves and ``tests/test_docs_snippets.py`` those whose python is executed;
#: both are audience questions and neither governs `developer`, whose pages are written
#: for a contributor and whose code blocks are illustrative (:issue:`302`). The three
#: held the same four values until 2026-09-11, and a later edit harmonising them on that
#: appearance would put the developer guide inside two gates that deliberately exclude
#: it.
#:
#: The reference quadrant is out, decided rather than deferred: its entries are reached
#: by name rather than chosen between, its introduction already guides a reader to the
#: two pages that need it, and it carries no prose list tracking a directory -- which is
#: the defect narrative spec §3.9 exists to close.
TABLE_SECTIONS = ("start", "tutorials", "howtos", "explanation", "developer")

#: A ``:doc:`` role, with the explicit target that wins over the display text when
#: one is written -- the same two-part shape ``check_glossary_links.py`` reads a
#: ``:term:`` in.
DOC = re.compile(r":doc:`([^`<]+?)(?:\s*<([^>]+)>)?`")


def _body(source: str, directive: str) -> list[str]:
    """Return the indented body of the one named directive on a page.

    Parameters
    ----------
    source : str
        The reStructuredText source of one page.
    directive : str
        The directive line to find, e.g. ``.. toctree::``.

    Returns
    -------
    list of str
        Every line under it, to the first line that is neither blank nor indented.

    """
    lines = source.splitlines()
    heads = [index for index, line in enumerate(lines) if line.strip() == directive]
    assert len(heads) == 1, f"expected one {directive} on the page, found {len(heads)}"
    body: list[str] = []
    for line in lines[heads[0] + 1 :]:
        if line.strip() and not line.startswith((" ", "\t")):
            break
        body.append(line)
    return body


def toctree_entries(source: str) -> list[str]:
    """Return the documents a page's toctree names, in order.

    Parameters
    ----------
    source : str
        The reStructuredText source of one page.

    Returns
    -------
    list of str
        Each entry, without its indentation. Directive options are not entries.

    """
    return [
        line.strip()
        for line in _body(source, ".. toctree::")
        if line.strip() and not line.strip().startswith(":")
    ]


def toctree_options(source: str) -> list[str]:
    """Return the options a page's toctree declares.

    `toctree_entries` drops these, because an option is not a document. They are
    read back here so the one option narrative spec §3.9 requires can be asserted.

    Parameters
    ----------
    source : str
        The reStructuredText source of one page.

    Returns
    -------
    list of str
        Each option line, stripped, e.g. ``:hidden:``.

    """
    return [
        line.strip()
        for line in _body(source, ".. toctree::")
        if line.strip().startswith(":")
    ]


def _entries(directory: Path) -> list[Path]:
    """Return the documents one section offers, one path per destination.

    A subdirectory carrying its own ``index.rst`` is a subsection: it
    contributes that landing page and **nothing beneath it**, because from the
    parent's table it is a single destination however many documents sit inside
    it -- the specification collection is one row, not twenty. A subdirectory
    without one is a plain grouping, and its documents belong to the parent.
    Recursion stops at a landing page rather than pruning by name, so a
    subsection nested two deep behaves the same as one nested one deep
    (narrative spec §3.9).

    Parameters
    ----------
    directory : Path
        The section directory to read.

    Returns
    -------
    list of Path
        One path per destination: a document, or a subsection's landing page.

    """
    found: list[Path] = []
    for path in directory.iterdir():
        if path.is_dir():
            landing_page = path / "index.rst"
            if landing_page.is_file():
                found.append(landing_page)
            else:
                found.extend(_entries(path))
        elif path.suffix == ".rst" and path.name != "index.rst":
            found.append(path)
    return found


def pages(quadrant: str, docs: Path = DOCS) -> list[str]:
    """Return every page in a quadrant, as a landing table would name it.

    A `:doc:` target on a landing page is relative to the quadrant, so that is
    what these are made relative to. The section's own ``index.rst`` is a landing
    page rather than an entry in one and is left out; a subsection's is both, and
    counts as one entry of its parent.

    Parameters
    ----------
    quadrant : str
        The quadrant's directory name under ``docs``.
    docs : Path, optional
        The documentation source root.

    Returns
    -------
    list of str
        The quadrant's pages, sorted.

    """
    root = docs / quadrant
    return sorted(
        path.relative_to(root).with_suffix("").as_posix() for path in _entries(root)
    )


def table_targets(source: str) -> list[str | None]:
    """Return the documents a page's landing table links to, in row order.

    Only the first cell of each row is read, so a ``:doc:`` written in a description
    is not mistaken for the row's own link, and neither is one in the prose above
    the table.

    Parameters
    ----------
    source : str
        The reStructuredText source of one page.

    Returns
    -------
    list of str or None
        The target of each row's first cell, or ``None`` for a row whose first cell
        carries no ``:doc:`` at all -- reported rather than skipped, so a row that
        links nowhere fails the page instead of shrinking the list silently.

    """
    found: list[str | None] = []
    for line in _body(source, ".. list-table::"):
        stripped = line.strip()
        if not stripped.startswith("* - "):
            continue
        match = DOC.search(stripped)
        found.append((match.group(2) or match.group(1)) if match else None)
    return found


def landing(quadrant: str, docs: Path = DOCS) -> str:
    """Return one quadrant's landing page source.

    Parameters
    ----------
    quadrant : str
        The quadrant's directory name under ``docs``.
    docs : Path, optional
        The documentation source root.

    Returns
    -------
    str
        The page's text.

    """
    # Asserted rather than left to raise: a renamed landing page would otherwise
    # fail as a FileNotFoundError from inside a helper, naming the reader's bug
    # rather than the tree's.
    page = docs / quadrant / "index.rst"
    assert page.is_file(), f"{quadrant} has no landing page at {page}"
    return page.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (".. toctree::\n    :hidden:\n\n    one\n    two\n", ["one", "two"]),
        (".. toctree::\n\n    one\n\n    two\n", ["one", "two"]),
        (".. toctree::\n    :hidden:\n\n    one\n\nAfter\n=====\n", ["one"]),
    ],
)
def test_toctree_entries_reads_the_directive_body_and_stops_at_it(source, expected):
    assert toctree_entries(source) == expected


def test_toctree_entries_does_not_read_an_option_as_an_entry():
    assert toctree_entries(".. toctree::\n    :maxdepth: 1\n\n    one\n") == ["one"]


def test_toctree_options_reads_the_options_the_entries_drop():
    source = ".. toctree::\n    :hidden:\n    :maxdepth: 1\n\n    one\n"
    assert toctree_options(source) == [":hidden:", ":maxdepth: 1"]


def test_toctree_options_finds_none_on_a_bare_directive():
    assert toctree_options(".. toctree::\n\n    one\n") == []


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ("    * - :doc:`framing`\n      - Fit the view.\n", ["framing"]),
        ("    * - :doc:`Frame <framing>`\n      - Fit the view.\n", ["framing"]),
    ],
)
def test_table_targets_prefers_the_explicit_target(row, expected):
    assert table_targets(f".. list-table::\n    :widths: auto\n\n{row}") == expected


def test_table_targets_ignores_a_doc_role_in_a_description():
    """A description may cite a sibling; the row's link is its first cell."""
    source = (
        ".. list-table::\n    :widths: auto\n\n"
        "    * - :doc:`framing`\n      - Unlike :doc:`emphasis`, it moves the view.\n"
    )
    assert table_targets(source) == ["framing"]


def test_table_targets_reports_a_row_that_links_nowhere():
    """Reported rather than skipped: a shorter list would pass by saying less."""
    source = (
        ".. list-table::\n    :widths: auto\n\n    * - Frame the View\n      - Fit.\n"
    )
    assert table_targets(source) == [None]


def test_a_second_toctree_fails_rather_than_being_half_read():
    source = ".. toctree::\n\n    one\n\n.. toctree::\n\n    two\n"
    with pytest.raises(AssertionError, match="expected one"):
        toctree_entries(source)


def test_a_subsection_is_one_entry_and_its_documents_are_not(tmp_path):
    """A directory with its own landing page contributes that page alone.

    The live tree cannot exercise this: `developer/specs/` holds one `.rst`, its
    own index, so a walk that failed to prune would produce the same answer
    (found in review, :pull:`306`).
    """
    section = tmp_path / "developer"
    (section / "specs").mkdir(parents=True)
    (section / "index.rst").touch()
    (section / "contributing.rst").touch()
    (section / "specs" / "index.rst").touch()
    (section / "specs" / "2026-01-01-a-design.rst").touch()
    assert pages("developer", docs=tmp_path) == ["contributing", "specs/index"]


def test_a_subdirectory_without_a_landing_page_gives_up_its_documents(tmp_path):
    """A plain grouping is not a subsection, so its documents are the parent's."""
    section = tmp_path / "howtos"
    (section / "advanced").mkdir(parents=True)
    (section / "index.rst").touch()
    (section / "advanced" / "tuning.rst").touch()
    assert pages("howtos", docs=tmp_path) == ["advanced/tuning"]


def test_every_section_this_gate_governs_is_on_disk():
    """A gate that finds nothing passes by never having looked."""
    for quadrant in TABLE_SECTIONS:
        assert (DOCS / quadrant).is_dir(), f"{quadrant} is missing"


@pytest.mark.parametrize("quadrant", TABLE_SECTIONS)
def test_the_table_and_the_toctree_are_one_ordered_list(quadrant):
    """Narrative spec §3.9: the visible index and the navigation are one list.

    Sequence and not set. The toctree is hidden, which hides it from the page body
    and from nothing else: the sidebar, the breadcrumb and the previous/next footer
    all read its order, so a table ordered differently would disagree with the
    navigation drawn around it.
    """
    source = landing(quadrant)
    assert table_targets(source) == toctree_entries(source)


@pytest.mark.parametrize("quadrant", TABLE_SECTIONS)
def test_every_row_links_to_a_page_in_its_own_quadrant(quadrant):
    for target in table_targets(landing(quadrant)):
        assert target is not None, (
            f"{quadrant} has a row whose first cell links nowhere"
        )
        assert (DOCS / quadrant / f"{target}.rst").is_file(), (
            f"{quadrant}'s table links to {target}, which is not a page in it"
        )


@pytest.mark.parametrize("quadrant", TABLE_SECTIONS)
def test_the_table_lists_every_page_in_the_quadrant(quadrant):
    """The table is the quadrant's index, so it indexes the quadrant.

    The ordered comparison above holds the table and the toctree to each other and
    would not notice a page missing from both, which is how a page goes unlisted:
    one commit that adds a page and neither list. The fail-on-warning build catches
    the ordinary case -- Sphinx reports a document in no toctree -- but not an
    `:orphan:` page, which builds clean and would sit in the quadrant unreachable
    from its own landing page.
    """
    listed = sorted(target for target in table_targets(landing(quadrant)) if target)
    assert listed == pages(quadrant)


@pytest.mark.parametrize("quadrant", TABLE_SECTIONS)
def test_the_toctree_is_hidden(quadrant):
    """Narrative spec §3.9: the table is the visible index, and it is the only one.

    Without this the page renders the same list twice, the table and the toctree
    under it, which is the duplication the shape exists to remove.
    """
    assert ":hidden:" in toctree_options(landing(quadrant))
