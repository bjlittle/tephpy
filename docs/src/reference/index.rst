Reference
=========

The factual material, for looking things up rather than reading through.

The API documentation is generated from the source, so it describes the package
you have installed. Beside it sit the command line, every configuration option and
its default, a glossary, the published sources this documentation cites, and the
changelog.

If you are deciding what to catch, read :mod:`tephpy.exceptions`. Every error
``tephpy`` raises for input you can correct derives from
:class:`TephpyError <tephpy.exceptions.TephpyError>`, so one ``except`` clause
covers the lot, and the module sets out the narrower classes for when that is
too broad.

The glossary is worth knowing about before you need it. ``tephpy``'s audience is
scientific software engineers rather than meteorologists, so each entry gives the
concept in one plain sentence and then says how it appears in the package — the
data it involves, its units, and the API that carries it.

.. toctree::
    :maxdepth: 1

    generated/api/tephpy/index
    cli
    config
    glossary
    references
    changelog
