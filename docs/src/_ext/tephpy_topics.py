# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""The topic index page and its filter buttons (topics spec §3.6).

The Sphinx half of the taxonomy. Everything that is a rule rather than an
adapter lives in ``tephpy_topics_data``, which imports nothing outside the
standard library so that the gate over it runs where Sphinx is absent
(topics spec §3.5).

The index is assembled at ``doctree-resolved`` rather than while the page is
read, because it is the first event at which every document's metadata has been
collected -- a directive building the list as its own page is parsed would see
whichever pages happened to be read first.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
import tephpy_topics_data as data

if TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)

#: What each quadrant is called on the page. Presentation rather than taxonomy,
#: so it lives here and not in the data module -- nothing in the promotion rule
#: or the gate has an opinion about the word "How-To Guides".
LABELS = {
    "tutorials": "Tutorials",
    "howtos": "How-To Guides",
    "explanation": "Explanation",
    "gallery": "Gallery",
}


class topicindex(nodes.Element):  # noqa: N801
    """Placeholder for the index, replaced once every document has been read."""


class topicitem(nodes.list_item):  # noqa: N801
    """One corpus item, carrying its tags as a ``data-topics`` attribute.

    A ``list_item`` rather than a bare ``Element``: docutils validates a
    ``bullet_list``'s content model, and the custom rendering is the writer's
    business rather than the tree's.
    """


class TopicIndexDirective(SphinxDirective):
    """Mark where the topic index goes."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        """Return the placeholder.

        Returns
        -------
        list of docutils.nodes.Node
            The placeholder, resolved after every document has been read.

        """
        return [topicindex("")]


def examples_dir(app: Sphinx) -> Path:
    """Return the directory sphinx-gallery scrapes its examples from.

    Read from ``sphinx_gallery_conf`` rather than written out again: the path is
    already declared once in ``conf.py``, and a second copy here would keep
    working after the first moved.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.

    Returns
    -------
    Path
        The examples directory.

    """
    return Path(app.srcdir) / app.config.sphinx_gallery_conf["examples_dirs"][0]


def build_corpus(app: Sphinx) -> dict[str, tuple[str, list[str]]]:
    """Assemble the tagged corpus of topics spec §3.1.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.

    Returns
    -------
    dict
        Docname to ``(quadrant, tags)``. A narrative page's docname is already
        ``"<quadrant>/<stem>"``, and sphinx-gallery writes its pages at
        ``"gallery/<stem>"``, so the key is the docname throughout.

    """
    env = app.env
    found: dict[str, tuple[str, list[str]]] = {}
    for docname in sorted(env.found_docs):
        quadrant, _, stem = docname.partition("/")
        if quadrant not in data.NARRATIVE or not stem or stem == "index":
            continue
        tags = data.split_tags(env.metadata.get(docname, {}).get("tags", ""))
        # The gate reads these declarations out of the source text and this reads
        # them out of Sphinx's metadata, which is two readers of one declaration.
        # They can only disagree by one being wrong, and the page would then show
        # tags the gate never checked -- so the disagreement is the thing worth
        # catching, rather than either reader alone.
        declared = data.read_page_tags(
            Path(env.doc2path(docname)).read_text(encoding="utf-8")
        )
        if declared != tags:
            logger.warning(
                "topic tags disagree: the source declares %s and Sphinx read %s. "
                "A `:tags:` field list reaches page metadata only on the first "
                "line of the file (topics spec §3.2).",
                declared,
                tags,
                location=docname,
                type="topics",
                subtype="declaration",
            )
        if not tags:
            logger.warning(
                "declares no topic tags (topics spec §3.1)",
                location=docname,
                type="topics",
                subtype="missing",
            )
        found[docname] = (quadrant, tags)
    for path in sorted(examples_dir(app).glob("plot_*.py")):
        source = path.read_text(encoding="utf-8")
        found[f"gallery/{path.stem}"] = ("gallery", data.read_gallery_tags(source))
    if not found:
        msg = "the topic corpus is empty: no narrative page and no gallery example"
        raise ValueError(msg)
    return found


def buttons(promoted: frozenset[str]) -> nodes.raw:
    """Return the filter bar for the promoted terms.

    It is emitted ``hidden`` and unhidden by ``topics.js``. A button bar that
    survives with scripting off is a row of controls that do nothing, which is
    worse than the list on its own -- and the list on its own is what topics spec
    decision 1 calls the feature.

    Parameters
    ----------
    promoted : frozenset of str
        The terms that earned a button (topics spec §3.4).

    Returns
    -------
    docutils.nodes.raw
        The bar, as HTML.

    """
    controls = "".join(
        f'<button type="button" class="teph-topic-button" data-topic="{term}">'
        f"{term}</button>"
        for term in sorted(promoted)
    )
    markup = (
        '<div id="teph-topic-filter" class="teph-topic-filter" hidden>'
        f"{controls}"
        '<button type="button" id="teph-topic-clear" class="teph-topic-clear" '
        "hidden>clear</button>"
        "</div>"
        '<p id="teph-topic-empty" class="teph-topic-empty" hidden>'
        "No page carries every selected topic. Clear one to widen the list."
        "</p>"
    )
    return nodes.raw("", markup, format="html")


def index(app: Sphinx, fromdocname: str) -> list[nodes.Node]:
    """Build the index for one page.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.
    fromdocname : str
        The document the index is being written into, which is what the relative
        links are computed against.

    Returns
    -------
    list of docutils.nodes.Node
        The filter bar and the item list.

    """
    corpus = build_corpus(app)
    order = {quadrant: rank for rank, quadrant in enumerate(data.QUADRANTS)}
    titles = {name: app.env.titles[name].astext() for name in corpus}
    listing = nodes.bullet_list(classes=["teph-topic-list"])
    for docname in sorted(
        corpus, key=lambda name: (order[corpus[name][0]], titles[name])
    ):
        quadrant, tags = corpus[docname]
        item = topicitem("", topics=sorted(tags))
        link = nodes.reference(
            "",
            "",
            nodes.Text(titles[docname]),
            internal=True,
            refuri=app.builder.get_relative_uri(fromdocname, docname),
        )
        # A paragraph rather than inlines straight into the item: a `list_item`
        # holds body elements, and it is also what gives the row one flex
        # container to lay its three parts out in.
        row = nodes.paragraph(classes=["teph-topic-row"])
        row += nodes.inline("", "", link, classes=["teph-topic-title"])
        row += nodes.inline("", LABELS[quadrant], classes=["teph-topic-quadrant"])
        row += nodes.inline("", " · ".join(sorted(tags)), classes=["teph-topic-tags"])
        item += row
        listing += item
    return [buttons(data.promote(corpus)), listing]


def resolve(app: Sphinx, doctree: nodes.document, fromdocname: str) -> None:
    """Replace every placeholder with the index.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.
    doctree : docutils.nodes.document
        The resolved doctree.
    fromdocname : str
        The document being written.

    """
    for node in list(doctree.findall(topicindex)):
        node.replace_self(index(app, fromdocname))


def visit_topicitem(self, node: topicitem) -> None:  # noqa: ANN001
    """Open the list item, carrying its tags for the filter."""
    self.body.append(
        self.starttag(
            node,
            "li",
            "",
            CLASS="teph-topic-item",
            **{"data-topics": json.dumps(node["topics"])},
        )
    )


def depart_topicitem(self, node: topicitem) -> None:  # noqa: ANN001, ARG001
    """Close the list item."""
    self.body.append("</li>\n")


def setup(app: Sphinx) -> dict[str, object]:
    """Register the directive, the nodes and the transform.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.

    Returns
    -------
    dict
        The extension metadata.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    app.add_node(topicitem, html=(visit_topicitem, depart_topicitem))
    app.add_directive("topicindex", TopicIndexDirective)
    app.connect("doctree-resolved", resolve)
    # Registered by the extension rather than through `html_js_files` in
    # `conf.py`: the script exists for the page this extension builds and reads
    # the hooks this extension emits, so the two move together. It is inert on
    # every other page -- it returns as soon as the filter bar is absent.
    app.add_js_file("topics.js")
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
