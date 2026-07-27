Documentation Style
====================

Title Style
-----------

Hand-authored page and section titles use Chicago Manual of Style headline
style: capitalize the first and last words and all major words; lowercase
articles, coordinating conjunctions, prepositions, and the infinitive "to".

Preserve literal case for: code and API identifiers, filenames, config keys,
CLI commands, and paths; project and library names in their own casing
(matplotlib, numpy, pint, metpy, pixi, tephpy); and acronyms and scientific
symbols (CAPE, CIN, LCL, WMO, SPEC 0). The rule does not apply to
autoapi-generated API pages, numpydoc section headers, changelog entries, or
anything that is a full sentence (captions, admonition text, docstring
summaries), which use sentence case. Bibliography entries reproduce the
source's published title.

Glossary
--------

The glossary is written for software engineers, not meteorologists. Each entry
gives the concept in one plain sentence, then how it appears in ``tephpy`` (the
data, its units, the API type that carries it), and links deeper physics to the
Explanation quadrant.

Cross-reference the *first* mention of a glossary term per page with
``:term:``, in narrative prose only — never in titles, code blocks, API
signatures, or admonition labels. Within a definition, link related terms but
never the term itself. Keep one canonical spelling per concept.

When a definition names a documented API, cross-reference it with the matching
Sphinx domain role — ``:class:``, ``:func:``, ``:meth:``, ``:mod:``, or
``:obj:`` — so the reader can follow the link straight into the API
documentation, rather than quoting the name as a plain double-backtick literal.
Keep the accessor idiom the entry reads in as the link's display text, so
``calc.parcel_path`` and ``ax.shade_cape`` stay legible:

.. code-block:: rst

    avoid:   ``calc.parcel_path(...)`` computes a parcel's ascent
    prefer:  :func:`calc.parcel_path(...) <tephpy.calc.parcel_path>` computes a parcel's ascent

Third-party objects (matplotlib, metpy, numpy, pandas, pint, xarray) resolve
the same way through intersphinx — see :ref:`cross-references` below. Reserve
plain double-backtick literals for names with no documentation target: private
members, dataclass fields already reachable through their linked owner,
external tools without an intersphinx inventory (pixi), option strings, and
keyword arguments. This mirrors the changelog fragment convention documented in
``changelog/README.md``.

.. _cross-references:

Cross-References
----------------

Third-party APIs resolve through intersphinx. Every third-party package the
documentation names — matplotlib, metpy, numpy, pandas, pint, xarray — has its
inventory registered in ``intersphinx_mapping`` in ``docs/src/conf.py``, so a
domain role such as :func:`metpy.calc.moist_lapse` or :class:`pint.Quantity`
links straight into that project's documentation. When you first cite an API
from a package that is not yet mapped, add its ``objects.inv`` location there in
the same change, so the reference resolves rather than rendering as plain text.

Parameter and return *types* are cross-referenced automatically. With
``numpydoc_xref_param_type`` enabled, numpydoc turns each type in a
``Parameters``/``Returns`` block into a link: fully-qualified names
(``pint.Quantity``, ``numpy.ndarray``) resolve through intersphinx, tephpy's own
short type names (``Sounding``, ``Profile``, the ``Tephpy*Error`` exceptions) are
mapped to their targets in ``numpydoc_xref_aliases``, and descriptive connective
words (``optional``,
``of``) are listed in ``numpydoc_xref_ignore``. Write the type as its plain
qualified name — ``pint.Quantity``, not a hand-written role — and let the
configuration link it.

``nitpicky`` is enabled, so an unresolved cross-reference is a warning and — via
the docs Makefile's ``--fail-on-warning`` — fails the build. A reference that
does not resolve is therefore caught automatically; a clean build is proof the
links land. The only sanctioned exceptions live in ``nitpick_ignore`` in
``conf.py``: annotation types autoapi emits as ``py:class`` xrefs while numpy
publishes them as ``py:data``/``py:attribute`` (``numpy.typing.ArrayLike``,
``numpy.typing.NDArray``, ``numpy.float64``), the ``Ellipsis`` in variadic
tuples, and parameter defaults from the private ``_constants`` module. Do not
extend that list to silence a reference you can instead make resolve — add a
``numpydoc_xref_aliases`` entry or write the full dotted name.
