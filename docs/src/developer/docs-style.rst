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

Third-party objects (matplotlib, numpy, …) resolve the same way through
intersphinx. Reserve plain double-backtick literals for names with no
documentation target: private members, dataclass fields already reachable
through their linked owner, external tools without an intersphinx inventory
(metpy), option strings, and keyword arguments. This mirrors the changelog
fragment convention documented in ``changelog/README.md``.
