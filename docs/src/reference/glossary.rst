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
        :term:`dewpoint`, wind) from a single ascent. In ``tephpy`` a sounding
        is carried by the ``Sounding`` dataclass — pressure and temperature
        arrays (plus optional dewpoint and wind) held as pint quantities with
        station/time metadata — and drawn with ``ax.plot_sounding(...)`` as
        red temperature and green dewpoint :term:`profiles <profile>`.

    dewpoint
        The temperature air must cool to, at constant pressure and moisture
        content, to become saturated; it is never above the air temperature
        (equality means saturation). In ``tephpy`` it is the optional
        ``dewpoint`` field of a ``Sounding`` (°C internally, any pint
        temperature unit accepted), plotted green alongside the red
        temperature line.

    profile
        One curve of a temperature-like quantity against pressure — a
        :term:`sounding`'s temperature or dewpoint trace, or a computed
        parcel path (added in a later release). ``ax.plot_profile(pressure,
        temperature)`` draws one through the tephigram transform machinery.

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

    isopleth
        A line along which one quantity is constant. The tephigram
        background is five isopleth families — :term:`isotherms
        <isotherm>`, :term:`isobars <isobar>`, :term:`dry adiabats
        <dry adiabat>`, :term:`moist adiabats <moist adiabat>`, and lines
        of constant :term:`humidity mixing ratio` — each drawn by one
        zoom-aware Matplotlib artist (``IsoplethFamily``) that selects
        the members appropriate to the current view.

    isobar
        A line of constant pressure. Pressure is not an axis of the
        tephigram, so each isobar is a gentle curve across the
        temperature/:term:`potential temperature` grid; ``tephpy`` labels
        isobars in hPa and reconfigures them via ``ax.isobars(...)``.

    moist adiabat
    saturation adiabat
    saturated adiabat
    wet adiabat
        The path a saturated air parcel follows when lifted: heat released
        by condensation makes it cool more slowly than a :term:`dry
        adiabat`. Each curve is labelled by its :term:`wet-bulb potential
        temperature` — the temperature where it crosses 1000 hPa.
        ``tephpy`` computes moist adiabats with ``metpy.calc.moist_lapse``
        and truncates them at low temperature where they converge onto
        the dry adiabats; "moist adiabat" is the canonical name, matching
        the AMS Glossary headword and MetPy's vocabulary.

    wet-bulb potential temperature
        The temperature a parcel would have if brought saturated along a
        :term:`moist adiabat` to the 1000 hPa reference pressure; written
        θw (theta-w). It is conserved along a moist adiabat, which is why
        ``tephpy`` uses it (°C) as the member value labelling each moist
        adiabat.

    humidity mixing ratio
    mixing ratio
    isohume
        The mass of water vapour per mass of dry air, in g/kg. On a
        tephigram, a line of constant *saturation* mixing ratio (an
        isohume) marks where air of a given moisture content saturates;
        ``tephpy`` computes these lines with MetPy and labels them in
        g/kg via ``ax.mixing_ratios(...)``.
