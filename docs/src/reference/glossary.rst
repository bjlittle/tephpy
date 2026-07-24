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

    potential temperature
        The temperature an air parcel would have if moved dry-adiabatically
        to the 1000 hPa reference pressure; written θ (theta). In ``tephpy``
        it is the second native coordinate of the tephigram plane —
        ``transforms.theta_from_pressure_temperature`` computes it (°C)
        from pressure (hPa) and temperature (°C).

    dry adiabat
        A line of constant :term:`potential temperature` — the path an
        unsaturated parcel follows when lifted. On a tephigram, dry
        adiabats are straight lines exactly perpendicular to the
        :term:`isotherms <isotherm>`.

    isotherm
        A line of constant temperature. On a tephigram, isotherms are
        straight parallel lines; their exact perpendicularity to the
        :term:`dry adiabats <dry adiabat>` is the diagram's defining
        property and is asserted directly in the test suite.
