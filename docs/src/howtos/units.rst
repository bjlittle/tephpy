:tags: units, sounding

.. _howto-units:

Work With Units
===============

.. readingtime::

``tephpy`` takes and returns pint quantities at every boundary carrying
scientific data (spec §5). Diagram geometry is the documented exception: the
:mod:`transforms <tephpy.transforms>` layer trades in bare arrays in the
diagram's native units, and the options that frame or draw a diagram —
:meth:`ax.set_extent(...) <tephpy.plotting.axes.TephigramAxes.set_extent>`, a
family's ``interval`` — take plain numbers. Three things follow, in the order
they tend to surprise people.

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
``[29.5 26.0] inch_Hg``, the numbers you gave. That :term:`sounding` plots and
analyses exactly like any other, and where a calculation derives a new quantity
it comes back in ``tephpy``'s own units — ``calc.parcel_path`` on a °F sounding
returns a °C :term:`profile`, whatever the pressure was spelled in.

That last part is pinned rather than asserted. ``tests/test_calc.py`` runs the
:term:`parcel ascent` and every stability index over ten pressure units — ``hPa``,
``Pa``, ``kPa``, ``mbar``, ``bar``, ``atm``, ``psi``, ``torr``, ``inHg`` and
``mmHg`` — and requires the answers to agree, not merely the calls to succeed
(:issue:`214`).

What Comes Back Is pint
-----------------------

Every profile field — pressure, temperature, :term:`dewpoint` and the winds — is a
:class:`pint.Quantity` on MetPy's registry, so conversion is a method call:

.. plot::
    :context:
    :nofigs:

    hpa = imperial.pressure.to("hPa")
    celsius = imperial.temperature.to("degC")

A sounding's metadata is not quantified and is not meant to be: ``station``,
``time`` and ``label`` come back as the string and timestamp you gave.

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
hierarchy, so a caller who wants every error ``tephpy`` raises about the data
itself can catch that instead. :mod:`tephpy.exceptions` documents the hierarchy,
and says which mistakes fall outside it and raise a builtin exception instead.

Where to Go Next
----------------

:ref:`howto-build-a-sounding` puts these units to work on data of your own.
