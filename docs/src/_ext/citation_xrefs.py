# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Render design-specification citations as cross-references (docs spec §3.7).

The transform runs on the doctree, after parsing, so it never sees a source
format -- only nodes. A citation therefore links identically from a docstring, a
``.rst`` page, a ``.md`` specification and a notebook markdown cell, and no source
is edited to make it so: ``spec §3.2`` in a docstring stays the characters it has
always been.

What a citation is, and which anchor it names, is not decided here. That is
:mod:`citations`, shared with the pre-commit gate of docs spec §3.6.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import citations
from docutils import nodes
from sphinx import addnodes
from sphinx.errors import ExtensionError
from sphinx.ext.autosummary import autosummary_table
from sphinx.transforms import SphinxTransform

if TYPE_CHECKING:
    import re

    from sphinx.application import Sphinx

#: Text inside any of these stays plain (docs spec §3.7). ``reference`` and
#: ``pending_xref`` are on the list because a citation appearing in link text
#: would otherwise nest one anchor inside another, which is invalid HTML.
SKIP = (
    nodes.literal,
    nodes.literal_block,
    nodes.comment,
    nodes.raw,
    nodes.reference,
    addnodes.desc_signature,
    addnodes.pending_xref,
)

#: Derived once per build from the anchors on disk, and read by every transform.
#: Populated by :func:`_build_registry` on ``builder-inited``, which runs before
#: Sphinx forks its parallel readers, so each child inherits the pair.
PATTERN: re.Pattern[str] | None = None
OWNERS: dict[str, str] = {}


class CitationTransform(SphinxTransform):
    """Replace each citation in ordinary prose with a reference to its anchor."""

    default_priority = 400

    def apply(self, **kwargs: object) -> None:  # noqa: ARG002
        """Rewrite every eligible text node in the document."""
        if PATTERN is None:
            return
        owner = OWNERS.get(self.env.docname)
        for text in list(self.document.findall(nodes.Text)):
            if _skipped(text):
                continue
            replacement = _convert(str(text), owner, self.env.docname)
            if replacement is not None:
                text.parent.replace(text, replacement)


def _skipped(node: nodes.Node) -> bool:
    """Report whether ``node`` sits inside something that must stay plain.

    Parameters
    ----------
    node : docutils.nodes.Node
        The text node under consideration.

    Returns
    -------
    bool
        Whether to leave the node alone.

    """
    parent = node.parent
    while parent is not None:
        # ``autosummary_table`` subclasses ``comment`` but is a rendered table,
        # and the autoapi module summary -- 17 citations -- lives inside one.
        if not isinstance(parent, autosummary_table) and isinstance(parent, SKIP):
            return True
        parent = parent.parent
    return False


def _convert(source: str, owner: str | None, docname: str) -> list[nodes.Node] | None:
    """Split ``source`` into runs of text and the references between them.

    Parameters
    ----------
    source : str
        The text node's contents.
    owner : str or None
        The citation prefix of the document, or ``None`` if it owns no sections.
    docname : str
        The document being read, recorded on each reference for its warnings.

    Returns
    -------
    list of docutils.nodes.Node or None
        The replacement nodes, or ``None`` when nothing here is a citation.

    """
    out: list[nodes.Node] = []
    cursor = 0
    for citation in citations.scan(source, PATTERN, owner):
        if citation.slug is None:
            # A bare section number with nothing to be relative to. The gate of
            # docs spec §3.6 rejects it on commit; here, leave it as written.
            continue
        out.append(nodes.Text(source[cursor : citation.start]))
        out.append(_xref(docname, citation.slug, citation.text))
        cursor = citation.end
    if not out:
        return None
    out.append(nodes.Text(source[cursor:]))
    return out


def _xref(docname: str, slug: str, shown: str) -> addnodes.pending_xref:
    """Build a ``std:ref`` cross-reference to ``slug``, displaying ``shown``.

    Parameters
    ----------
    docname : str
        The referring document.
    slug : str
        The MyST anchor of docs spec §3.3, e.g. ``spec-3-2``.
    shown : str
        The citation as written, which is what the link displays.

    Returns
    -------
    sphinx.addnodes.pending_xref
        Resolved later by the standard domain.

    Notes
    -----
    ``refwarn`` is set rather than the anchor being checked here, so that a
    citation which stops resolving fails the build through the Makefile's
    ``--fail-on-warning`` even when the pre-commit gate was bypassed.

    """
    inner = nodes.inline(shown, shown, classes=["std", "std-ref"])
    return addnodes.pending_xref(
        "",
        inner,
        refdoc=docname,
        refdomain="std",
        reftype="ref",
        reftarget=slug,
        refexplicit=True,
        refwarn=True,
    )


def _build_registry(app: Sphinx) -> None:
    """Derive the citation pattern and the owner map from the anchors on disk.

    The prefixes are nowhere declared (docs spec §3.6): adding a specification
    adds its prefix, and no list needs updating to match.

    Finding no anchors leaves ``PATTERN`` as ``None``, which makes the transform
    a no-op. Building a pattern from an empty registry would be worse than doing
    nothing: there are no prefixes to alternate, so nothing a citation could name
    exists, and every cross-reference emitted would be one the standard domain
    cannot resolve.

    Parameters
    ----------
    app : Sphinx
        The application, read for its source directory.

    Raises
    ------
    sphinx.errors.ExtensionError
        When two specifications declare the same anchor. Reported as a build
        error rather than escaping this event handler as a ``SystemExit``.

    """
    global PATTERN  # noqa: PLW0603
    root = Path(app.srcdir)
    specs = sorted((root / "developer" / "specs").glob("*.md"))
    try:
        anchors, owners = citations.collect_anchors(specs)
    except citations.DuplicateAnchorError as duplicate:
        first, second = duplicate.first, duplicate.second
        message = (
            f"duplicate citation anchor '{duplicate.slug}': "
            f"{first.path}:{first.line} and {second.path}:{second.line}"
        )
        raise ExtensionError(message) from duplicate
    if not anchors:
        PATTERN = None
        OWNERS.clear()
        return
    PATTERN = citations.citation_pattern(anchors)
    OWNERS.clear()
    OWNERS.update(
        {
            path.relative_to(root).with_suffix("").as_posix(): prefix
            for path, prefix in owners.items()
        }
    )


def setup(app: Sphinx) -> dict[str, object]:
    """Register the transform.

    Parameters
    ----------
    app : Sphinx
        The application.

    Returns
    -------
    dict
        The extension metadata.

    """
    app.connect("builder-inited", _build_registry)
    app.add_transform(CitationTransform)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
