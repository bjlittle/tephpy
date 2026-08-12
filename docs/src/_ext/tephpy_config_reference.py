# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Publish the ``tephpy.config`` options reference (configfile spec §3.6).

The directive owns no prose of its own. Everything it emits comes from
``tephpy._configfile.render_reference``, which is rendered from the same tables
the configuration template is rendered from, so a new option reaches both
renderings or neither. Keeping the renderer in the package rather than here is
what makes its output testable: ``pixi run tests`` has no Sphinx.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles

import tephpy
from tephpy import _configfile

if TYPE_CHECKING:
    from sphinx.application import Sphinx


class ConfigOptionsDirective(SphinxDirective):
    """Emit a documented target for every ``tephpy.config`` option."""

    has_content = False

    def run(self) -> list[nodes.Node]:
        """Parse the rendered reference into the calling document.

        Returns
        -------
        list of docutils.nodes.Node
            One section per configuration section, plus the methods section.
        """
        # The rendered text is not a source file Sphinx knows to watch, so an
        # incremental build would serve the previous options until this page's
        # own source changed.
        self.env.note_dependency(_configfile.__file__)
        text = _configfile.render_reference(tephpy.config)
        lines = StringList(
            text.splitlines(), source="tephpy._configfile.render_reference"
        )
        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, lines, node)
        return node.children


def setup(app: Sphinx) -> dict[str, Any]:
    """Register the directive.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application.

    Returns
    -------
    dict
        The extension metadata.
    """
    app.add_directive("tephpy-config-options", ConfigOptionsDirective)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
