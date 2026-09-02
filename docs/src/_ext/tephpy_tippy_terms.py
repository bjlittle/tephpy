# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Give every ``<dt>`` of a shared-definition group its own tooltip definition.

Docutils renders two different constructs the same way: a glossary entry
defining several terms with one shared definition, and a Python directive
documenting several call signatures with one shared description --
``py:function:: spam(a)`` and a second line ``spam(a, b)``, or the
``@overload`` shape autoapi emits. Both become a run of consecutive ``<dt>``
elements followed by a single ``<dd>``.
``sphinx_tippy.create_id_to_tip_html`` copies the ``<dd>`` into a term's tip
only when the ``<dd>`` is that term's *immediate* next sibling::

    if (next_sibling := next_sibling_tag(tag)) and next_sibling.name == "dd":

so only the last ``<dt>`` of a group is ever given the definition.

An earlier version of this module fixed the glossary shape by *donating* the
last term's already-generated, already-trimmed tip to every earlier term in
its group. That does not reach the signature shape: there, the only ``<dt>``
carrying an ``id`` -- the first signature; sphinx-autodoc's own convention,
verified against `tephpy.plotting.axes.TephigramAxes.plot_profile`, which
this documentation already renders this way -- is never adjacent to the
``<dd>`` and so is never given one to donate. There is no donor.

This version instead pre-processes the parsed page **before** calling the
original function: it finds every run of consecutive ``<dt>`` siblings
terminated by a ``<dd>``, and inserts a *copy* of that ``<dd>`` immediately
after every ``<dt>`` in the run that is not already adjacent to it. The
original function's own adjacency check then succeeds for every ``<dt>``, and
its own trimming (at most five ``<p>`` children kept) runs once per ``<dt>``,
unmodified -- this module never re-derives or duplicates that logic, which
was the point of the donor idea and is kept here by construction. Group
membership does not require an ``id``: the id-less second signature of an
overloaded method is still part of its group, even though only the id-bearing
``<dt>`` ends up with a tip to show.

Mutating the parsed page this way is safe because of how
``sphinx_tippy.collect_tips`` builds it: at ``sphinx_tippy.py:261``,
``body = BeautifulSoup(context["body"], "html.parser")`` parses a *copy* of
the page's HTML string. Mutating ``body`` cannot reach back into
``context["body"]``, and nothing renders from ``body`` after
``create_id_to_tip_html`` returns -- a future reader changing how
``collect_tips`` uses ``body`` should recheck this before relying on it again.

Filed upstream as
`sphinx-extensions2/sphinx-tippy#35 <https://github.com/sphinx-extensions2/sphinx-tippy/issues/35>`_.
Upstream has had no release since ``0.4.3`` in April 2024 (tooltip spec §3.1), so
this project vendors the correction rather than waiting for it.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import copy
from functools import wraps
from typing import TYPE_CHECKING

import sphinx_tippy

if TYPE_CHECKING:
    from bs4 import BeautifulSoup, Tag
    from sphinx.application import Sphinx
    from sphinx_tippy import TippyConfig


def _duplicate_definitions(body: BeautifulSoup) -> None:
    """Give every ``<dt>`` of a shared-definition group its own following ``<dd>``.

    Parameters
    ----------
    body : bs4.BeautifulSoup
        The page's rendered body, mutated in place. The same soup
        :func:`sphinx_tippy.create_id_to_tip_html` goes on to read.

    Notes
    -----
    Walks every ``<dt>`` in document order, grouping each into the run of
    consecutive ``<dt>`` siblings it belongs to -- regardless of whether any
    of them carries an ``id`` -- and skips a run not terminated by a ``<dd>``
    entirely, leaving it untouched. A ``<dt>`` already immediately followed by
    the group's ``<dd>`` is left alone, so an already-correct group, and a
    group this function has already processed, gets no second copy inserted.

    .. versionadded:: 0.1.0

    """
    seen: set[int] = set()
    for dt in body.find_all("dt"):
        if id(dt) in seen:
            continue
        chain = [dt]
        seen.add(id(dt))
        sibling = sphinx_tippy.next_sibling_tag(dt)
        while sibling is not None and sibling.name == "dt":
            chain.append(sibling)
            seen.add(id(sibling))
            sibling = sphinx_tippy.next_sibling_tag(sibling)
        if sibling is None or sibling.name != "dd":
            continue
        definition: Tag = sibling
        for term in chain:
            if sphinx_tippy.next_sibling_tag(term) is definition:
                continue
            term.insert_after(copy.copy(definition))


def _wrap(
    original: object,
) -> object:
    """Wrap ``create_id_to_tip_html`` to fix up shared-definition groups first.

    Parameters
    ----------
    original : callable
        ``sphinx_tippy.create_id_to_tip_html``, called second and unmodified,
        once :func:`_duplicate_definitions` has run.

    Returns
    -------
    callable
        A function of the same ``(config, body)`` signature.

    Notes
    -----
    .. versionadded:: 0.1.0

    """

    @wraps(original)
    def wrapper(config: TippyConfig, body: BeautifulSoup) -> dict[str | None, str]:
        _duplicate_definitions(body)
        return original(config, body)

    return wrapper


def setup(app: Sphinx) -> dict[str, object]:  # noqa: ARG001
    """Patch ``sphinx_tippy.create_id_to_tip_html`` in place.

    Parameters
    ----------
    app : sphinx.application.Sphinx
        The application. Unread: nothing here is configurable, and there is no
        event to connect to -- ``sphinx_tippy.collect_tips`` looks up
        ``create_id_to_tip_html`` as a module global at call time, so
        patching the attribute here, during ``setup()``, reaches every call
        the ``html-page-context`` handler makes later in the build.

    Returns
    -------
    dict
        The extension metadata.

    Notes
    -----
    .. versionadded:: 0.1.0

    """
    sphinx_tippy.create_id_to_tip_html = _wrap(sphinx_tippy.create_id_to_tip_html)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
