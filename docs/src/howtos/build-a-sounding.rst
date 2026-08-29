.. _howto-build-a-sounding:

Build a Sounding From Your Own Data
===================================

:doc:`read-a-sounding` covers the archives ``tephpy`` reads. This page covers
the other way in: your data is already in Python, in a
:class:`pandas.DataFrame` or an :class:`xarray.Dataset`, and you want a
:class:`Sounding <tephpy.sounding.Sounding>` out of it.

Both libraries are hard dependencies, so both routes are available in every
install with no extra to enable.

From a DataFrame
----------------

:meth:`Sounding.from_dataframe(...) <tephpy.sounding.Sounding.from_dataframe>`
reads bare arrays out of the columns. Nothing in a DataFrame carries a unit, so
the ``units=`` mapping is required for every field present:

.. plot::
    :context: reset
    :nofigs:

    import pandas as pd

    from tephpy import Sounding

    df = pd.DataFrame(
        {
            "pressure": [1000.0, 925.0, 850.0, 700.0, 607.0,
                         500.0, 400.0, 300.0, 250.0, 200.0],
            "temperature": [15.4, 15.4, 10.4, 4.4, -1.9,
                            -11.9, -22.1, -39.1, -47.9, -55.7],
            "dewpoint": [14.4, 2.4, 3.4, -17.6, -24.9,
                         -37.9, -43.1, -50.1, -57.9, -71.7],
        }
    )
    units = {"pressure": "hPa", "temperature": "degC", "dewpoint": "degC"}
    from_frame = Sounding.from_dataframe(df, units=units)

Ten levels of the Camborne ascent, enough to draw. Column names that already
match the field names need no mapping at all.

Naming Your Own Columns
-----------------------

When they do not match, name them. Each keyword is a *field*, and its value is
the *column*:

.. plot::
    :context:
    :nofigs:

    renamed = df.rename(
        columns={"pressure": "p", "temperature": "T", "dewpoint": "Td"}
    )
    from_renamed = Sounding.from_dataframe(
        renamed, units=units, pressure="p", temperature="T", dewpoint="Td"
    )

Note which name ``units`` is keyed by. It is the **field**, not the column, so
the same mapping serves both calls above. ``pressure`` and ``temperature`` are
required; a missing or mistyped column raises :class:`KeyError` naming both
names — mistype the ``renamed`` frame's temperature column above as
``"Temp"`` rather than ``"T"``, and it raises:

.. code-block:: text

    KeyError: "column 'Temp' (field 'temperature') is not in the DataFrame"

Any keyword that names no known field raises :class:`TypeError` instead,
naming the unknown field and the fields it does know. The catch-all
parameter that absorbs it is called ``column_map`` here, ``var_map`` on
:meth:`~tephpy.sounding.Sounding.from_dataset`:

.. code-block:: text

    TypeError: unknown field(s) ['bogus']; expected ['dewpoint', 'pressure',
    'temperature', 'wind_direction', 'wind_speed']

From a Dataset
--------------

:meth:`Sounding.from_dataset(...) <tephpy.sounding.Sounding.from_dataset>`
differs in one way worth knowing, because it is invisible from the signature.
An :class:`xarray.Dataset` *can* carry units, in each variable's
``attrs["units"]``, and the constructor reads them by that convention. Here
``units=`` is the override rather than the requirement, and a CF-compliant
dataset needs none:

.. plot::
    :context:
    :nofigs:

    import xarray as xr

    ds = xr.Dataset(
        {
            "temperature": (
                "level", df["temperature"].to_numpy(), {"units": "degC"}
            ),
            "dewpoint": (
                "level", df["dewpoint"].to_numpy(), {"units": "degC"}
            ),
        },
        coords={
            "level": ("level", df["pressure"].to_numpy(), {"units": "hPa"})
        },
    )
    from_dataset = Sounding.from_dataset(ds, pressure="level")

Coordinates count as variables, which is why ``pressure="level"`` reaches one.
A missing required or explicitly mapped variable raises :class:`KeyError`,
just as a missing column does for
:meth:`~tephpy.sounding.Sounding.from_dataframe`:

.. code-block:: text

    KeyError: "variable 'temperature' (field 'temperature') not in the Dataset"

A field with neither ``attrs["units"]`` nor a ``units=`` entry raises
:class:`TephpyUnitsError <tephpy.exceptions.TephpyUnitsError>`, and the message
carries the fix:

.. code-block:: text

    'temperature' (variable 'temperature') has no attrs['units'] and no
    override: add units={"temperature": "<unit>"}

Naming the Ascent
-----------------

Both constructors take ``station=``, ``time=`` and ``label=``. Give the first
two and the legend label derives, exactly as it does for a
:term:`sounding` read from an archive:

.. plot::
    :context:
    :nofigs:

    named = Sounding.from_dataframe(
        df,
        units=units,
        station="03808",
        time=pd.Timestamp("2026-07-21 12:00"),
    )

``time`` here is stricter than the readers of :doc:`read-a-sounding`, which
parse a string. This one wants a real timestamp —
:class:`pandas.Timestamp`, :class:`numpy.datetime64` or
:class:`datetime.datetime` — and a string raises :class:`TypeError`. ``label=``
overrides the derived text outright.

Plotted Like Any Other
----------------------

What comes out is a :class:`Sounding <tephpy.sounding.Sounding>`, and nothing
downstream can tell it was built rather than read:

.. plot::
    :context:
    :filename-prefix: build-a-sounding-plotted

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(named)
    ax.legend()

Where to Go Next
----------------

:ref:`howto-units` covers what those unit strings may say, and what you get
back. :ref:`howto-read-a-sounding` is the other route in, for data still in a
file.
