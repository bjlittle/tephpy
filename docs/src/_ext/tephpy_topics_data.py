# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""The topic taxonomy, shared by the extension, the gate and the report.

One definition of what the vocabulary is, how a tag declaration is read at each of
its two sites, and when a term earns a filter button -- shared by the
``tephpy_topics`` extension (topics spec §3.6), the gate (topics spec §3.7) and the
monthly report (topics spec §3.8). Two copies would agree until one was amended,
and a gate that promoted differently from the page it polices would be checking a
different index than the one published.

Nothing here is imported from outside the standard library, and that is
load-bearing rather than tidy (topics spec §3.5): the vocabulary is asserted by
tests that run in the ``test-py3*`` environments the CI matrix runs, which carry
no Sphinx. A module reachable only behind a Sphinx import would make those
assertions skip exactly where they matter.

The ``tephpy_`` prefix claims a top-level name this repository owns, because
``docs/src/_ext`` sits at ``sys.path[0]`` for the whole build (:issue:`92`). It is
not part of the installed package -- nothing under ``docs/`` is.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

VOCABULARY = frozenset(
    {
        "analysis",
        "barbs",
        "branding",
        "config",
        "data-input",
        "diagram",
        "indices",
        "isopleths",
        "labels",
        "metpy",
        "overlay",
        "parcel",
        "projection",
        "shading",
        "sounding",
        "styling",
        "units",
    }
)
"""The seventeen terms of topics spec §3.3, closed.

Each is defined there by what it covers *and* what it excludes, and that table is
the authority when two people would tag a page differently -- neither spelling of
a disagreement is illegal here, so nothing in this module can see it. A term added
without an entry in that table is the drift the closure exists to prevent, so the
two land together.
"""

#: Topics spec §3.3's bound, inherited unchanged from gallery spec §3.6: one tag
#: files an item under a single button, and a full house files it under every one,
#: either way telling the filter nothing.
MIN_TAGS = 2
MAX_TAGS = 4

#: The first promotion condition (topics spec §3.4). A count rather than a
#: fraction because there are only ever four quadrants.
MIN_QUADRANTS = 2

#: The four quadrants the corpus is drawn from (topics spec §3.1). The reference
#: quadrant and the developer section are out.
QUADRANTS = ("tutorials", "howtos", "explanation", "gallery")

#: The three quadrants whose pages declare tags in page metadata rather than in
#: their own source (topics spec §3.2) -- `QUADRANTS` less the gallery, which
#: declares in `sphinx_gallery_tags` in the example file instead. The one home
#: for the set: the extension, the gate and the report each traverse it
#: differently -- the extension walks `env.found_docs`, the other two the
#: filesystem -- but none of them should own its own copy of which three
#: quadrants those are.
NARRATIVE = ("tutorials", "howtos", "explanation")

#: sphinx-gallery reads exactly this flag and silently discards any other
#: spelling, so this pattern is deliberately as strict as its parser (gallery
#: spec §3.6). Moved here from ``tests/examples/test_examples.py``, which now
#: reads it from this module: the vocabulary and the flag that declares it
#: belong to one taxonomy, and the gallery's gate and the site-wide index were
#: reading two copies of them.
GALLERY_TAGS = re.compile(r"^# sphinx_gallery_tags = (?P<value>\[.*\])$", re.MULTILINE)

#: A narrative page's declaration, anchored to the first byte of the file.
#:
#: The anchor is the whole rule and it was measured rather than assumed. Sphinx
#: lifts a docinfo field list into ``env.metadata`` -- removing it from the
#: doctree, so it renders nothing -- only when it precedes every other piece of
#: markup on the page. A field list written under the title, which is what topics
#: spec §3.2 first proposed, leaves ``env.metadata`` empty and renders a visible
#: definition list at the reader. Being as strict here as Sphinx is what makes the
#: gate fail such a page instead of quietly finding no tags on one that looks
#: tagged.
PAGE_TAGS = re.compile(r"\A:tags:[ \t]*(?P<value>[^\n]*)\n")


def split_tags(value: str) -> list[str]:
    """Split a comma-separated field body into tags.

    Parameters
    ----------
    value : str
        The field body, as ``env.metadata`` hands it over: one string.

    Returns
    -------
    list of str
        The tags, stripped, in the order declared, empty entries dropped.

    """
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def read_gallery_tags(source: str) -> list[str]:
    """Return the tags a gallery example declares.

    Parameters
    ----------
    source : str
        The example module's text.

    Returns
    -------
    list of str
        The declared tags, empty if the file declares none.

    """
    match = GALLERY_TAGS.search(source)
    if match is None:
        return []
    return ast.literal_eval(match.group("value"))


def read_page_tags(source: str) -> list[str]:
    """Return the tags a narrative page declares.

    Parameters
    ----------
    source : str
        The page's reStructuredText.

    Returns
    -------
    list of str
        The declared tags, empty if the page declares none *in the position
        Sphinx reads*.

    """
    match = PAGE_TAGS.match(source)
    if match is None:
        return []
    return split_tags(match.group("value"))


def coverage(
    corpus: Mapping[str, tuple[str, Sequence[str]]],
) -> dict[str, frozenset[str]]:
    """Return the quadrants each term appears in.

    Parameters
    ----------
    corpus : mapping
        Item name to ``(quadrant, tags)``.

    Returns
    -------
    dict
        Term to the quadrants holding it. Terms nothing declares are absent,
        which is what makes an unused vocabulary term visible to the gate.

    """
    found: defaultdict[str, set[str]] = defaultdict(set)
    for quadrant, tags in corpus.values():
        for tag in tags:
            found[tag].add(quadrant)
    return {tag: frozenset(quadrants) for tag, quadrants in found.items()}


def promote(corpus: Mapping[str, tuple[str, Sequence[str]]]) -> frozenset[str]:
    """Return the terms that earn a filter button (topics spec §3.4).

    A term promotes when it appears in two or more quadrants *and* selects fewer
    than half the corpus. Both conditions are needed and the live corpus
    demonstrates each failing alone: ``barbs`` sits in two gallery examples and no
    narrative page, passing the cap and failing the span; ``sounding`` sits in
    twelve of nineteen items across three quadrants, passing the span and failing
    the cap.

    Parameters
    ----------
    corpus : mapping
        Item name to ``(quadrant, tags)``.

    Returns
    -------
    frozenset of str
        The promoted terms.

    Raises
    ------
    ValueError
        If the corpus is empty. An empty result would otherwise mean either "no
        term spans two quadrants" or "the caller assembled nothing", and those
        take different fixes.

    """
    total = len(corpus)
    if not total:
        msg = "the corpus is empty: promotion over nothing promotes nothing"
        raise ValueError(msg)
    quadrants = coverage(corpus)
    counts = Counter(tag for _, tags in corpus.values() for tag in set(tags))
    # `count * 2 < total` rather than `count < total / 2`: the threshold is a
    # strict "fewer than half", and integer arithmetic states that exactly at the
    # boundary an odd corpus never reaches and an even one lands on.
    return frozenset(
        tag
        for tag, count in counts.items()
        if len(quadrants[tag]) >= MIN_QUADRANTS and count * 2 < total
    )
