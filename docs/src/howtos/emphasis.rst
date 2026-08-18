.. _howto-emphasis:

Emphasise a Reference Isopleth
==============================

Forecasters read a tephigram against a handful of reference lines — the 0 °C
isotherm for the freezing level, −20 °C for the cold limit of the airframe
icing band, a mandatory pressure level. The ``emphasis`` option distinguishes
any member of any isopleth family.

The Freezing Level
------------------

Map the member value to an empty style. The member keeps its family's colour and
draws at 1.5 pt instead of the usual 0.5 pt — the printed-chart idiom of same
ink, heavier line:

.. plot::
    :context: reset
    :filename-prefix: emphasis-freezing-level

    import matplotlib.pyplot as plt

    import tephpy  # registers the "tephigram" projection

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.isotherms(emphasis={0.0: {}})

Colour and Dashes
-----------------

Any of ``color``, ``linewidth``, ``linestyle`` and ``alpha`` overrides that
default, so the airframe icing band's bounds can carry their own styling:

.. plot::
    :context:
    :filename-prefix: emphasis-colour-and-dashes

    ax.isotherms(
        emphasis={
            0.0: {"color": "tab:cyan"},
            -20.0: {"color": "tab:cyan", "linestyle": "--"},
        }
    )

An omitted key falls back to the family's own style, so
``{0.0: {"linestyle": "--"}}`` is a dashed member in the family's colour at the
emphasis width.

Values the Interval Never Lands On
----------------------------------

An emphasised member is always drawn, whatever the zoom ladder would select, so
the dendritic growth zone's −12 °C and −18 °C bounds appear even though no
isotherm interval includes them:

.. plot::
    :context:
    :filename-prefix: emphasis-off-interval

    ax.isotherms(
        emphasis={
            -12.0: {"color": "tab:purple"},
            -18.0: {"color": "tab:purple"},
        }
    )

A value outside the diagram's domain is a no-op — it is simply never in view.
That is silent on the analytic families (isotherms, dry adiabats and isobars);
the curved moist adiabats and mixing ratios build through MetPy, which can warn
about a far-out value before the diagram ever gets to ignore it, so emphasise a
value those families actually cover.

Every Family, Every Tier
------------------------

The option is the same on all five families, so a mandatory pressure level is
the same gesture:

.. plot::
    :context: close-figs
    :filename-prefix: emphasis-every-family

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.isobars(emphasis={500.0: {}})

and it takes the usual precedence — the accessor keyword over
``tephpy.config`` over the convention default.

Configure It Once
-----------------

A family reads ``tephpy.config`` when the axes is created, and re-reads it on
``ax.clear()``, so the configuration has to be in force before the diagram it
should apply to exists. :meth:`tephpy.config.context` scopes it to exactly
that:

.. plot::
    :context: close-figs
    :filename-prefix: emphasis-from-config

    with tephpy.config.context(isotherms={"emphasis": {0.0: {"color": "tab:red"}}}):
        fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})

Setting ``tephpy.config.isotherms.emphasis`` directly does the same thing and
keeps doing it, for every axes created afterwards, until something puts it back.
Reach for that where a house style is the point — a configuration file
(:ref:`configure-from-a-file`) is the tidier home for one — and for a single
diagram prefer the accessor keyword the sections above use.

Passing an empty mapping at the accessor emphasises nothing, which is how one
diagram opts out of a configured emphasis:

.. plot::
    :context:
    :filename-prefix: emphasis-opt-out

    ax.isotherms(emphasis={})

.. note::

    Emphasis reaches a member's line and its inline label. Where a family labels
    a diagram edge instead, that edge's tick marks and tick labels take one
    colour for the whole family — matplotlib styles ticks per axis, not per
    tick — so an emphasised member's edge tick is placed but not recoloured.
