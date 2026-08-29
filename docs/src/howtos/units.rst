.. _howto-units:

Work With Units
===============

``tephpy`` takes and returns pint quantities throughout (spec §5). Three things
follow, in the order they tend to surprise people.

Quantities Go In Directly
-------------------------

If your arrays already carry units, pass them and say nothing else. There is no
``units=`` argument in this call:

.. plot::
    :context: reset
    :nofigs:

    from metpy.units import units

    from tephpy import Sounding

    snd = Sounding(
        pressure=[1000.0, 925.0, 850.0, 700.0] * units.hPa,
        temperature=[15.4, 15.4, 10.4, 4.4] * units.degC,
        dewpoint=[14.4, 2.4, 3.4, -17.6] * units.degC,
    )

The ``units=`` mapping exists for the other case — bare arrays, which is what a
:class:`pandas.DataFrame` hands you. :ref:`howto-build-a-sounding` is that
route.

Any Unit pint Can Parse
-----------------------

``units=`` is not a shortlist ``tephpy`` maintains. It is handed to pint, so
anything pint parses in the right dimension is accepted, and the field is
stored in that unit rather than converted on the way in:

.. plot::
    :context:
    :nofigs:

    imperial = Sounding(
        pressure=[29.5, 26.0],
        temperature=[68.0, 60.0],
        units={"pressure": "inHg", "temperature": "degF"},
    )

The field is tagged, not rewritten: ``imperial.pressure`` reads back
``[29.5 26.0] inch_Hg``, the numbers you gave. That :term:`sounding` plots
exactly like any other, and where a calculation derives a new quantity it
comes back in ``tephpy``'s own units — ``calc.parcel_path`` on a °F sounding
returns a °C :term:`profile`.

.. note::

    Plotting works in any unit pint accepts. Analysis does not, yet:
    ``calc.parcel_path`` raises ``DimensionalityError`` when a sounding's
    pressure is in ``inHg`` or ``mmHg`` — every other pressure unit checked
    here (``hPa``, ``Pa``, ``kPa``, ``mbar``, ``bar``, ``atm``, ``psi``,
    ``torr``) works. This is a bug in ``tephpy``, not a design decision, and
    it is tracked as :issue:`214`.

What Comes Back Is pint
-----------------------

Every field is a :class:`pint.Quantity` on MetPy's registry, so conversion is a
method call:

.. plot::
    :context:
    :nofigs:

    hpa = imperial.pressure.to("hPa")
    celsius = imperial.temperature.to("degC")

Being on *MetPy's* registry is the part that matters downstream. Quantities out
of ``tephpy`` go straight into MetPy's own calculations with no conversion step
and no registry mismatch:

.. plot::
    :context:
    :nofigs:

    from metpy.calc import dewpoint_from_relative_humidity

    humid = dewpoint_from_relative_humidity(
        snd.temperature, [0.9, 0.8, 0.7, 0.6] * units.dimensionless
    )

Do not check this by comparing registries. ``metpy.units.units`` is an
``ApplicationRegistry`` proxy and the quantities sit on the
:class:`pint.UnitRegistry` it wraps, so an identity test reports ``False`` for a
claim that is true.

When the Units Are Wrong
------------------------

:class:`TephpyUnitsError <tephpy.exceptions.TephpyUnitsError>` covers the whole
of this subject — units missing, ambiguous, unparsable, or in the wrong
dimension. It subclasses
:class:`TephpyError <tephpy.exceptions.TephpyError>`, the root of ``tephpy``'s
hierarchy, so a caller who wants everything can catch that instead.

Where to Go Next
----------------

:ref:`howto-build-a-sounding` puts these units to work on data of your own.
