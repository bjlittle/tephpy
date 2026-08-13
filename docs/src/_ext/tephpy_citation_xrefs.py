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
:mod:`tephpy_citations`, shared with the pre-commit gate of docs spec §3.6.

The ``tephpy_`` prefix claims a top-level name this repository owns, because
``docs/src/_ext`` sits at ``sys.path[0]`` for the whole build (:issue:`92`). It
is not part of the installed package -- nothing under ``docs/`` is.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx import addnodes
from sphinx.errors import ExtensionError
from sphinx.ext.autosummary import autosummary_table
from sphinx.transforms import SphinxTransform
from sphinx.util import logging
import tephpy_citations

if TYPE_CHECKING:
    import re

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment

logger = logging.getLogger(__name__)

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

#: Digest of the registry above, set alongside it and compared in :func:`_outdated`
#: against the one the environment carries from the previous build.
FINGERPRINT = ""

#: Where that digest is kept between builds. The environment is pickled, so the
#: attribute survives to the next build in the same source tree.
ENV_FINGERPRINT = "tephpy_citation_registry"


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
                heading = _heading(text)
                if heading is not None:
                    logger.warning(
                        "citation in the section heading %r reaches the reader "
                        "unlinked: the theme rebuilds the page navigation from "
                        "the headings, keeping the text and dropping the anchor. "
                        "Cite the specification in the prose below the heading "
                        "instead (docs spec §3.7)",
                        heading.astext(),
                        location=text,
                        type="tephpy",
                        subtype="citation",
                    )
                text.parent.replace(text, replacement)


def _heading(node: nodes.Node) -> nodes.title | None:
    """Return the section heading ``node`` sits in, or ``None`` (:issue:`96`).

    A citation here is converted like any other, so the page reads as it always
    did; what it cannot be is a link the reader can follow. The theme rebuilds
    its "On this page" navigation from the headings, copying the inline markup
    but not the anchor, and wrapping the copy in the navigation's own link -- at
    which point the rendered-citation gate of docs spec §3.7 counts an enclosing
    ``<a>`` and scores it linked. That gate is written not to know one anchor from
    another, so the build has to say so where the citation is written.

    Only a section heading qualifies, and deliberately not every ``title``: the
    caption of a table, an admonition or a topic is not copied into the
    navigation, so a citation in one is a link like any other. Sphinx disables
    the docutils title transforms, so a heading is always a ``title`` directly
    under a ``section``.

    Parameters
    ----------
    node : docutils.nodes.Node
        The text node under consideration.

    Returns
    -------
    docutils.nodes.title or None
        The heading, whose text names the offender for a reader of the warning.
        MyST gives a section title no usable line number, so the message cannot
        rely on the location Sphinx prints beside it.

    """
    parent = node.parent
    while parent is not None:
        if isinstance(parent, nodes.title) and isinstance(parent.parent, nodes.section):
            return parent
        parent = parent.parent
    return None


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
        # and the autoapi module summary lives inside one, so skipping every
        # comment would skip citations a reader does see (docs spec §3.7).
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
    for citation in tephpy_citations.scan(source, PATTERN, owner):
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

    The fingerprint is set here too, from the same read, so that :func:`_outdated`
    can compare this build's registry with the one the cached doctrees were built
    against.

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
    global FINGERPRINT, PATTERN  # noqa: PLW0603
    root = Path(app.srcdir)
    specs = sorted((root / "developer" / "specs").glob("*.md"))
    try:
        anchors, owners = tephpy_citations.collect_anchors(specs)
    except tephpy_citations.DuplicateAnchorError as duplicate:
        first, second = duplicate.first, duplicate.second
        message = (
            f"duplicate citation anchor '{duplicate.slug}': "
            f"{first.path}:{first.line} and {second.path}:{second.line}"
        )
        raise ExtensionError(message) from duplicate
    PATTERN = tephpy_citations.citation_pattern(anchors) if anchors else None
    OWNERS.clear()
    OWNERS.update(
        {
            path.relative_to(root).with_suffix("").as_posix(): prefix
            for path, prefix in owners.items()
        }
    )
    FINGERPRINT = _fingerprint(anchors, OWNERS)


def _fingerprint(
    anchors: dict[str, tephpy_citations.Anchor], owners: dict[str, str]
) -> str:
    """Digest the registry, so that a build can tell it has changed since the last.

    Only what the transform reads is digested. Where an anchor sits is not part of
    it: moving a section within a specification changes no link, and a digest that
    said otherwise would re-read every document for an edit that cannot matter.

    Parameters
    ----------
    anchors : dict
        The anchors keyed by slug, from which the pattern is built.
    owners : dict
        The owning prefix keyed by docname, which is what a section number written
        without one resolves against.

    Returns
    -------
    str
        A digest that changes when, and only when, one of those two does.

    """
    material = "\n".join(
        (
            *sorted(anchors),
            "--",
            *(f"{docname} {prefix}" for docname, prefix in sorted(owners.items())),
        )
    )
    return sha256(material.encode("utf-8")).hexdigest()


def _outdated(
    _app: Sphinx,
    env: BuildEnvironment,
    added: set[str],
    changed: set[str],
    _removed: set[str],
) -> set[str]:
    """Re-read every document when the registry differs from the last build's.

    The transform runs while a document is read, so its decisions are baked into
    the pickled doctree: which characters are a citation, and which anchor each
    one names. Both are read from the registry, which is not a dependency of any
    document -- so adding a specification, renumbering a section or deleting one
    leaves every unedited page cached with the answers the *previous* registry
    gave. Sphinx re-reads nothing, does not rewrite the page, and therefore never
    resolves the reference again: ``refwarn`` cannot fire, and a citation left
    pointing at a section that no longer exists fails no build. A clean build of
    the same tree reports it.

    Nothing else notices either. Such a citation is still a link, so the output
    gate of docs spec §3.7 passes it -- by its own account it cannot tell a right
    target from a wrong one -- and the pre-commit gate of docs spec §3.6 reads
    the source, where nothing is wrong. It is the wrong-but-resolving failure
    that docs spec §3.6 describes, arrived at from the build and not the prose.

    Parameters
    ----------
    _app : Sphinx
        The application. Unread; Sphinx calls this positionally, so the name is
        ours to choose.
    env : sphinx.environment.BuildEnvironment
        The environment, which carries the previous build's digest.
    added : set of str
        Documents new since the last build.
    changed : set of str
        Documents Sphinx has already found to be out of date.
    _removed : set of str
        Documents gone since the last build. Unread.

    Returns
    -------
    set of str
        The documents to re-read on top of those Sphinx found itself.

    """
    if getattr(env, ENV_FINGERPRINT, None) == FINGERPRINT:
        return set()
    setattr(env, ENV_FINGERPRINT, FINGERPRINT)
    # On a first build every document is already in ``added``, so this is empty
    # and the cost is only paid when a registry actually changed under a cache.
    return set(env.found_docs) - added - changed


def setup(app: Sphinx) -> dict[str, object]:
    """Register the transform and the two handlers that keep its registry honest.

    Parameters
    ----------
    app : Sphinx
        The application.

    Returns
    -------
    dict
        The extension metadata. ``env_version`` is part of it because this
        extension now stores something in the environment: raising it discards
        every cached doctree, which is what a change to the shape of what is
        stored requires.

    """
    app.connect("builder-inited", _build_registry)
    app.connect("env-get-outdated", _outdated)
    app.add_transform(CitationTransform)
    return {
        "version": "0.1.0",
        "env_version": 1,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
