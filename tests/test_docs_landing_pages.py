# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""A landing page's index and its toctree are one list (narrative spec §3.9)."""

from __future__ import annotations

from functools import cache
from pathlib import Path, PurePosixPath
import re

import pytest

from tests.by_path import load_path

REPO = Path(__file__).parents[1]
DOCS = REPO / "docs" / "src"
CONF = DOCS / "conf.py"

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
#: The reference quadrant takes cards instead (`CARD_SECTIONS`): its pages are
#: looked up by name, and a card answers that with an icon where a row would offer a
#: choice nobody makes (narrative spec §3.9).
TABLE_SECTIONS = ("start", "tutorials", "howtos", "explanation", "developer")

#: The sections whose landing page carries a grid of cards (narrative spec §3.9).
CARD_SECTIONS: tuple[str, ...] = ("reference",)

#: The directive a card is written with. A card's own options are the ``:name:``
#: lines directly under it, and the first line that is not one ends them.
CARD = ".. grid-item-card::"

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


@cache
def _autoapi() -> tuple[PurePosixPath, str]:
    """Return where autoapi writes the API pages, and the package it documents.

    Read by executing `conf.py`, as `tests/test_docs_whatsnew.py` reads
    ``rst_epilog``: a text scan would pass on a value sitting in a comment. Cached,
    because every section's discovery asks and the answer cannot change in a run.

    Returns
    -------
    tuple of (PurePosixPath, str)
        ``autoapi_root``, relative to the documentation source, and the name of the
        package directory ``autoapi_dirs`` names.

    """
    conf = load_path("tephpy_docs_conf", CONF)
    return PurePosixPath(conf.autoapi_root), PurePosixPath(conf.autoapi_dirs[0]).name


def generated_pages(section: str) -> list[str]:
    """Return the pages a section offers that exist only while a build runs.

    autoapi writes the API reference under ``autoapi_root`` during a build and, with
    ``autoapi_keep_files = False``, removes it afterwards; the directory is
    git-ignored besides. Discovery cannot see a page that is not on disk, so the one
    entry a section's index gives the API is derived instead (narrative spec §3.9).

    Parameters
    ----------
    section : str
        The section's directory name under the documentation source.

    Returns
    -------
    list of str
        ``["generated/api/tephpy/index"]`` for the section ``autoapi_root`` sits in,
        and nothing for any other.

    """
    root, package = _autoapi()
    if root.parts[0] != section:
        return []
    return [str(PurePosixPath(*root.parts[1:], package, "index"))]


def _entries(directory: Path, skip: Path) -> list[Path]:
    """Return the documents one section offers, one path per destination.

    A subdirectory carrying its own ``index.rst`` is a subsection: it
    contributes that landing page and **nothing beneath it**, because from the
    parent's index it is a single destination however many documents sit inside
    it -- the specification collection is one row, not twenty. A subdirectory
    without one is a plain grouping, and its documents belong to the parent.
    Recursion stops at a landing page rather than pruning by name, so a
    subsection nested two deep behaves the same as one nested one deep
    (narrative spec §3.9).

    ``skip`` is autoapi's output directory, passed over wherever a build left it:
    its one page is counted by `generated_pages` instead, and a stale tree would
    otherwise add entries no index names.

    Parameters
    ----------
    directory : Path
        The section directory to read.
    skip : Path
        The directory autoapi writes into.

    Returns
    -------
    list of Path
        One path per destination: a document, or a subsection's landing page.

    """
    found: list[Path] = []
    for path in directory.iterdir():
        if path == skip:
            continue
        if path.is_dir():
            landing_page = path / "index.rst"
            if landing_page.is_file():
                found.append(landing_page)
            else:
                found.extend(_entries(path, skip))
        elif path.suffix == ".rst" and path.name != "index.rst":
            found.append(path)
    return found


def pages(quadrant: str, docs: Path = DOCS) -> list[str]:
    """Return every page on disk in a section, as its landing index would name it.

    A `:doc:` target on a landing page is relative to the section, so that is
    what these are made relative to. The section's own ``index.rst`` is a landing
    page rather than an entry in one and is left out; a subsection's is both, and
    counts as one entry of its parent. A page only a build writes is not on disk,
    and `generated_pages` supplies it.

    Parameters
    ----------
    quadrant : str
        The section's directory name under ``docs``.
    docs : Path, optional
        The documentation source root.

    Returns
    -------
    list of str
        The section's pages, sorted.

    """
    root = docs / quadrant
    skip = docs / _autoapi()[0]
    return sorted(
        path.relative_to(root).with_suffix("").as_posix()
        for path in _entries(root, skip)
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


def card_targets(source: str) -> list[str | None]:
    """Return the documents a page's landing cards link to, in card order.

    Only a card's own option block is read -- the ``:name: value`` lines directly
    under ``.. grid-item-card::`` -- so an option of an image nested in the card, or
    a field in its body, is not mistaken for the card's link.

    Parameters
    ----------
    source : str
        The reStructuredText source of one page.

    Returns
    -------
    list of str or None
        Each card's ``:link:``, or ``None`` for a card carrying none -- reported
        rather than skipped, so a card that links nowhere fails the page instead of
        shrinking the list silently.

    """
    lines = source.splitlines()
    found: list[str | None] = []
    for index, line in enumerate(lines):
        if not line.strip().startswith(CARD):
            continue
        link = None
        for option in lines[index + 1 :]:
            stripped = option.strip()
            if not stripped.startswith(":"):
                break
            name, _, value = stripped[1:].partition(":")
            if name == "link":
                link = value.strip()
        found.append(link)
    return found


def index_targets(section: str, source: str) -> list[str | None]:
    """Return a landing page's index, read in the shape its section takes.

    Parameters
    ----------
    section : str
        The section's directory name.
    source : str
        The reStructuredText source of its landing page.

    Returns
    -------
    list of str or None
        What `card_targets` reads for a card section, and `table_targets` otherwise.

    """
    return card_targets(source) if section in CARD_SECTIONS else table_targets(source)


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


def test_card_targets_reads_each_cards_link_in_order():
    source = (
        "    .. grid-item-card:: API\n"
        "        :link: generated/api/tephpy/index\n"
        "        :link-type: doc\n"
        "        :columns: 12\n\n"
        "        Generated.\n\n"
        "    .. grid-item-card:: Command Line\n"
        "        :link-type: doc\n"
        "        :link: cli\n\n"
        "        What to type.\n"
    )
    assert card_targets(source) == ["generated/api/tephpy/index", "cli"]


def test_card_targets_reports_a_card_that_links_nowhere():
    """Reported rather than skipped, as a table row is."""
    source = (
        "    .. grid-item-card:: Glossary\n"
        "        :class-card: teph-card sd-rounded-3\n\n"
        "        .. image:: glossary-light.svg\n"
        "            :class: only-light teph-card-icon\n"
    )
    assert card_targets(source) == [None]


def test_card_targets_reads_only_the_cards_own_options():
    """A ``:link:`` after the option block is body text, not the card's link."""
    source = (
        "    .. grid-item-card:: Command Line\n"
        "        :link-type: doc\n\n"
        "        :link: cli\n"
    )
    assert card_targets(source) == [None]


def test_the_api_page_is_derived_for_the_section_autoapi_writes_into():
    """It exists only while a build runs, so discovery cannot find it."""
    assert generated_pages("reference") == ["generated/api/tephpy/index"]
    assert generated_pages("howtos") == []


def test_discovery_passes_over_a_generated_tree_a_build_left_behind(tmp_path):
    """A stale autoapi tree must not add pages the index is then asked to list."""
    section = tmp_path / "reference"
    (section / "generated" / "api" / "tephpy").mkdir(parents=True)
    (section / "index.rst").touch()
    (section / "cli.rst").touch()
    (section / "generated" / "api" / "index.rst").touch()
    (section / "generated" / "api" / "tephpy" / "index.rst").touch()
    assert pages("reference", docs=tmp_path) == ["cli"]


def test_every_section_this_gate_governs_is_on_disk():
    """A gate that finds nothing passes by never having looked."""
    for section in TABLE_SECTIONS + CARD_SECTIONS:
        assert (DOCS / section).is_dir(), f"{section} is missing"


def test_a_section_takes_one_shape():
    """Two constants naming one section would put two indexes on its page."""
    assert not set(TABLE_SECTIONS) & set(CARD_SECTIONS)


@pytest.mark.parametrize("section", TABLE_SECTIONS + CARD_SECTIONS)
def test_a_landing_page_carries_one_index(section):
    """A table page carries no cards, and a card page no table (narrative spec §3.9)."""
    other = ".. list-table::" if section in CARD_SECTIONS else CARD
    assert other not in landing(section)


@pytest.mark.parametrize("section", TABLE_SECTIONS + CARD_SECTIONS)
def test_the_index_and_the_toctree_are_one_ordered_list(section):
    """Narrative spec §3.9: the visible index and the navigation are one list.

    Sequence and not set. The toctree is hidden, which hides it from the page body
    and from nothing else: the sidebar, the breadcrumb and the previous/next footer
    all read its order, so an index ordered differently would disagree with the
    navigation drawn around it.
    """
    source = landing(section)
    assert index_targets(section, source) == toctree_entries(source)


@pytest.mark.parametrize("section", TABLE_SECTIONS + CARD_SECTIONS)
def test_every_entry_links_to_a_page_in_its_own_section(section):
    """A target is a page of the section, or the one page a build generates there.

    ``..`` is refused outright: ``DOCS / section / "../howtos/units.rst"`` names a
    file that exists, so without it an entry pointing into another section would
    pass as a page of this one.
    """
    generated = generated_pages(section)
    for target in index_targets(section, landing(section)):
        assert target is not None, f"{section} has an entry that links nowhere"
        assert ".." not in PurePosixPath(target).parts, (
            f"{section}'s index links to {target}, outside the section"
        )
        assert target in generated or (DOCS / section / f"{target}.rst").is_file(), (
            f"{section}'s index links to {target}, which is not a page in it"
        )


@pytest.mark.parametrize("section", TABLE_SECTIONS + CARD_SECTIONS)
def test_the_index_lists_every_page_in_the_section(section):
    """The index is the section's index, so it indexes the section.

    The ordered comparison above holds the index and the toctree to each other and
    would not notice a page missing from both, which is how a page goes unlisted:
    one commit that adds a page and neither list. The fail-on-warning build catches
    the ordinary case -- Sphinx reports a document in no toctree -- but not an
    `:orphan:` page, which builds clean and would sit in the section unreachable
    from its own landing page.
    """
    listed = sorted(
        target for target in index_targets(section, landing(section)) if target
    )
    assert listed == sorted(pages(section) + generated_pages(section))


@pytest.mark.parametrize("section", TABLE_SECTIONS + CARD_SECTIONS)
def test_the_toctree_is_hidden(section):
    """Narrative spec §3.9: the index is the visible one, and it is the only one.

    Without this the page renders the same list twice, the index and the toctree
    under it, which is the duplication the shape exists to remove.
    """
    assert ":hidden:" in toctree_options(landing(section))
