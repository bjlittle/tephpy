Reference
=========

.. The cards are the visible index and the toctree below is the navigation; the two
   are one list, held by tests/test_docs_landing_pages.py (narrative spec §3.9).

   Each icon is drawn in the root page's vocabulary, as that page's comment sets it
   out: API, a module tree with one entry found; Command Line, a shell prompt at its
   cursor; Configuration Options, two options on their scales with one set;
   Glossary, a line and the label that names it; References, a printed page with its
   source marked; What's New, a spark; Changelog, a run of entries with the newest
   marked. Light and dark differ only in the navy and the knock-out halo, and live in
   _static/cards/reference/.

The factual material, for looking things up rather than reading through.

.. grid:: 1 2 2 2
    :gutter: 2

    .. grid-item-card:: API
        :link: generated/api/tephpy/index
        :link-type: doc
        :class-card: teph-card sd-rounded-3
        :columns: 12

        .. image:: ../_static/cards/reference/api-light.svg
            :class: only-light teph-card-icon
            :alt: a module tree, one entry found

        .. image:: ../_static/cards/reference/api-dark.svg
            :class: only-dark teph-card-icon
            :alt: a module tree, one entry found

        Generated from the source, so it describes the version you have installed.

    .. grid-item-card:: Command Line
        :link: cli
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/cli-light.svg
            :class: only-light teph-card-icon
            :alt: a shell prompt, its cursor marked

        .. image:: ../_static/cards/reference/cli-dark.svg
            :class: only-dark teph-card-icon
            :alt: a shell prompt, its cursor marked

        What to type at a shell.

    .. grid-item-card:: Configuration Options
        :link: config
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/config-light.svg
            :class: only-light teph-card-icon
            :alt: two options on their scales, one of them set

        .. image:: ../_static/cards/reference/config-dark.svg
            :class: only-dark teph-card-icon
            :alt: two options on their scales, one of them set

        What to set, in Python or in a file.

    .. grid-item-card:: Glossary
        :link: glossary
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/glossary-light.svg
            :class: only-light teph-card-icon
            :alt: a line, and the label that names it

        .. image:: ../_static/cards/reference/glossary-dark.svg
            :class: only-dark teph-card-icon
            :alt: a line, and the label that names it

        What a word means here, and where the API carries it.

    .. grid-item-card:: References
        :link: references
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/references-light.svg
            :class: only-light teph-card-icon
            :alt: a printed page, its source marked

        .. image:: ../_static/cards/reference/references-dark.svg
            :class: only-dark teph-card-icon
            :alt: a printed page, its source marked

        Where a convention or definition came from.

    .. grid-item-card:: What's New
        :link: whatsnew/index
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/whatsnew-light.svg
            :class: only-light teph-card-icon
            :alt: a spark, marking what is new

        .. image:: ../_static/cards/reference/whatsnew-dark.svg
            :class: only-dark teph-card-icon
            :alt: a spark, marking what is new

        A release, in the few things worth knowing.

    .. grid-item-card:: Changelog
        :link: changelog
        :link-type: doc
        :class-card: teph-card sd-rounded-3

        .. image:: ../_static/cards/reference/changelog-light.svg
            :class: only-light teph-card-icon
            :alt: a run of entries, the newest marked

        .. image:: ../_static/cards/reference/changelog-dark.svg
            :class: only-dark teph-card-icon
            :alt: a run of entries, the newest marked

        A release, one entry per pull request.

If you are deciding what to catch, read :mod:`tephpy.exceptions`. What
``tephpy`` raises about your data — its units, its physical consistency, the
source it came from, the configuration file in force — derives from
:class:`TephpyError <tephpy.exceptions.TephpyError>`, so one ``except`` clause
covers that subject, and the module sets out the narrower classes for when it
is too broad. Ordinary argument mistakes stay outside the hierarchy and raise
the builtin exceptions instead.

The glossary is worth knowing about before you need it. ``tephpy``'s audience is
scientific software engineers rather than meteorologists, so each entry gives the
concept in one plain sentence and then says how it appears in the package — the
data it involves, its units, and the API that carries it.

.. toctree::
    :hidden:
    :maxdepth: 1

    generated/api/tephpy/index
    cli
    config
    glossary
    references
    whatsnew/index
    changelog
