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
        Matplotlib :term:`projection` named ``"tephigram"``.

    projection
        Matplotlib's name for a custom Axes class registered under a string,
        selected with
        :func:`plt.subplots(subplot_kw={"projection": ...}) <matplotlib.pyplot.subplots>`
        — nothing to do with a map projection. Importing ``tephpy`` registers
        :class:`TephigramAxes <tephpy.plotting.axes.TephigramAxes>` under
        ``"tephigram"``, which is why every example imports the package even
        where it names nothing from it.

    sounding
        A vertical profile of atmospheric measurements (pressure, temperature,
        :term:`dewpoint`, wind) from a single ascent. In ``tephpy`` a sounding
        is carried by the :class:`Sounding <tephpy.sounding.Sounding>`
        dataclass — pressure and temperature arrays (plus optional dewpoint and
        wind) held as pint quantities with station/time metadata — and drawn
        with :meth:`ax.plot_sounding(...) <tephpy.plotting.axes.TephigramAxes.plot_sounding>`
        as red temperature and green dewpoint :term:`profiles <profile>`.

    dewpoint
        The temperature air must cool to, at constant pressure and moisture
        content, to become saturated; it is never above the air temperature
        (equality means saturation). In ``tephpy`` it is the optional
        ``dewpoint`` field of a :class:`Sounding <tephpy.sounding.Sounding>`
        (°C internally, any pint temperature unit accepted), plotted green
        alongside the red temperature line.

    profile
        One curve of a temperature-like quantity against pressure — a
        :term:`sounding`'s temperature or dewpoint trace, or a computed
        :term:`parcel path` (the :class:`calc.Profile <tephpy.calc.Profile>`
        dataclass).
        :meth:`ax.plot_profile(...) <tephpy.plotting.axes.TephigramAxes.plot_profile>`
        draws it through the tephigram transform machinery.

    potential temperature
        The temperature an air parcel would have if moved dry-adiabatically
        to the 1000 hPa reference pressure; written θ (theta). In ``tephpy``
        it is the second native coordinate of the tephigram plane —
        :func:`transforms.theta_from_pressure_temperature <tephpy.transforms.theta_from_pressure_temperature>`
        computes it (°C) from pressure (hPa) and temperature (°C).

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
        zoom-aware Matplotlib artist
        (:class:`IsoplethFamily <tephpy.plotting.isopleths.IsoplethFamily>`)
        that selects the members appropriate to the current view.

    isobar
        A line of constant pressure. Pressure is not an axis of the
        tephigram, so each isobar is a gentle curve across the
        temperature/:term:`potential temperature` grid; ``tephpy`` labels
        isobars in hPa and reconfigures them via
        :meth:`ax.isobars(...) <tephpy.plotting.axes.TephigramAxes.isobars>`.

    moist adiabat
    saturation adiabat
    saturated adiabat
    wet adiabat
        The path a saturated air parcel follows when lifted: heat released
        by condensation makes it cool more slowly than a :term:`dry
        adiabat`. Each curve is labelled by its :term:`wet-bulb potential
        temperature` — the temperature where it crosses 1000 hPa.
        ``tephpy`` computes moist adiabats with
        :func:`metpy.calc.moist_lapse`
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
        g/kg via
        :meth:`ax.mixing_ratios(...) <tephpy.plotting.axes.TephigramAxes.mixing_ratios>`.

    parcel
    air parcel
        An imagined small mass of air lifted through the surrounding
        environment without mixing with it — the tephigram's basic tool
        for reasoning about stability. Its :term:`parcel ascent` is what
        the diagram plots; in ``tephpy`` the ``parcel=`` option of
        :func:`calc.parcel_path <tephpy.calc.parcel_path>` chooses where
        that ascent begins: ``"surface"`` or ``"mixed-layer"`` (the
        lowest 100 hPa averaged).

    parcel ascent
    parcel path
        The path a lifted :term:`parcel` traces on the diagram:
        dry-adiabatically from its start level to the :term:`LCL`, then
        along a :term:`moist adiabat` above it. Comparing that path
        against the environment :term:`sounding` is what yields
        :term:`CAPE`, :term:`CIN`, and the :term:`LFC` and :term:`EL`
        levels — the ascent is the construction, they are its readings.
        :func:`calc.parcel_path(...) <tephpy.calc.parcel_path>` computes
        it as a :class:`calc.Profile <tephpy.calc.Profile>`.

    lifting condensation level
    LCL
    Normand's point
        The level where a lifted, unsaturated :term:`parcel` first
        saturates — on a tephigram it is Normand's construction: the
        :term:`dry adiabat` through the parcel's temperature meets the
        :term:`humidity mixing ratio` line through its :term:`dewpoint`.
        :func:`calc.normand_point(...) <tephpy.calc.normand_point>` returns
        it as scalar (pressure, temperature) pint quantities,
        :func:`calc.parcel_path <tephpy.calc.parcel_path>` splices it
        into the ascent exactly, and the operational -25 mb cloud-base
        correction is applied only when requested via
        ``cloud_base_correction=``.

    level of free convection
    LFC
        The level above which a lifted :term:`parcel` becomes warmer than
        its environment and rises freely. In ``tephpy`` it is the
        ``lfc_pressure``/``lfc_temperature`` fields of
        :class:`calc.SoundingIndices <tephpy.calc.SoundingIndices>` — NaN
        quantities when the parcel never becomes positively buoyant ("does
        not exist" is an answer, not an error).

    equilibrium level
    EL
        The level above the :term:`LFC` where a rising :term:`parcel`
        cools back to the environment temperature — roughly the anvil
        top of a thunderstorm. The ``el_pressure``/``el_temperature``
        fields of :class:`calc.SoundingIndices <tephpy.calc.SoundingIndices>`;
        NaN when the parcel is still buoyant at the profile top
        (:term:`CAPE` can be positive with no EL).

    CAPE
    convective available potential energy
        The energy per unit mass (J/kg) available to a :term:`parcel`
        between the :term:`LFC` and the :term:`EL`, where it is warmer
        than the environment — the fuel gauge for deep convection.
        :func:`calc.indices(...) <tephpy.calc.indices>` reports it
        (``0 J/kg`` — never NaN — when there is none) and
        :meth:`ax.shade_cape(snd, parcel) <tephpy.plotting.axes.TephigramAxes.shade_cape>`
        shades the region.

    CIN
    convective inhibition
        The energy per unit mass (J/kg, non-positive) a :term:`parcel`
        must be given to reach its :term:`LFC` through the layers where
        it is cooler than the environment — the :term:`cap` that must
        break before :term:`CAPE` is released. Reported by
        :func:`calc.indices(...) <tephpy.calc.indices>` and shaded by
        :meth:`ax.shade_cin(snd, parcel) <tephpy.plotting.axes.TephigramAxes.shade_cin>`.

    cap
    capping inversion
        The warm, stable layer above the surface that holds a lifted
        :term:`parcel` down until something breaks it — the physical thing
        :term:`CIN` measures, which is why forecasters quote a cap in J/kg
        and speak of it eroding through the day. ``tephpy`` reports the
        number as the ``cin`` field of
        :class:`calc.SoundingIndices <tephpy.calc.SoundingIndices>`.

    lifted index
        The environment-minus-parcel temperature difference at 500 hPa
        (°C); large negative values mean instability. The
        ``lifted_index`` field of
        :class:`calc.SoundingIndices <tephpy.calc.SoundingIndices>`; NaN when
        the profile tops out below 500 hPa.

    radiosonde
        The instrument package a weather balloon carries aloft,
        transmitting pressure, temperature, humidity, and wind as it
        rises — the source of most real :term:`soundings <sounding>`.
        ``tephpy`` ingests radiosonde archives through the ``tephpy.io``
        readers.

    special sounding
    special
        A :term:`radiosonde` release outside a station's scheduled times —
        00Z and 12Z, where the Z is UTC — made when the weather warrants an
        extra look. The 17Z ascent that :mod:`tephpy.samples` ships is one,
        sent up about three hours before the Moore tornado of 2013-05-20.

    IGRA
    Integrated Global Radiosonde Archive
        NCEI's quality-controlled archive of the global
        :term:`radiosonde` record, distributed as one fixed-width file
        per station (version 2).
        :func:`igra.read(...) <tephpy.io.igra.read>` reads one ascent
        from such a file into a
        :class:`Sounding <tephpy.sounding.Sounding>`.

    wind barb
        A glyph giving the wind at one level: the shaft points toward
        the direction the wind comes from, and its feathers sum to the
        speed — half barb 5 kt, full barb 10 kt, flag 50 kt, rounded to
        5 kt bins; a bare circle is calm.
        :meth:`ax.plot_barbs(snd) <tephpy.plotting.axes.TephigramAxes.plot_barbs>`
        draws a :term:`sounding`'s barbs on a staff in the right-hand
        gutter, each level at the height where its isobar meets the
        diagram's edge.

    hodograph
        A plot of a :term:`sounding`'s winds as vectors from a common
        origin, joined in height order, so that the shape of the curve is
        how the wind turns and strengthens with height. It answers what a
        tephigram cannot: the diagram carries the thermodynamics, and its
        :term:`wind barbs <wind barb>` give one level at a time. ``tephpy``
        draws no hodograph — MetPy's :class:`metpy.plots.Hodograph` composes
        onto the same figure, and the :ref:`gallery` insets one over a
        tephigram.
