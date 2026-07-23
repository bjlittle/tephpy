Glossary
========

Terms are written for scientific software engineers rather than
meteorologists. Each entry states the concept plainly, then how it appears in
``tephpy``. See :doc:`../developer/docs-style` for the entry and
cross-reference rules.

.. glossary::

    tephigram
        A thermodynamic diagram that plots temperature against entropy on a
        rotated coordinate system, so that isotherms and dry adiabats form an
        exactly perpendicular straight-line grid. ``tephpy`` renders it as a
        Matplotlib projection named ``"tephigram"``.

    sounding
        A vertical profile of atmospheric measurements (pressure, temperature,
        dewpoint, wind) from a single ascent. In ``tephpy`` a sounding is
        carried by the ``Sounding`` data model (added in a later release).
