.. _howto-temp-and-bufr:

Decode TEMP and BUFR with ecCodes
=================================

``tephpy`` does not decode TEMP (TTAA/TTBB) bulletins or BUFR messages, and it
is not going to. The formats are WMO's, the reference decoder is `ecCodes
<https://confluence.ecmwf.int/display/ECC>`__, and a second implementation would
be a worse copy of a maintained one. Whether demand later justifies a
``tephpy[bufr]`` extra is :issue:`82`.

That leaves a seam rather than a gap, and this page is the seam. ecCodes turns a
message into numbers; ``tephpy`` turns numbers into a :term:`tephigram`.

Decode the Message
------------------

ecCodes ships command-line tools, and they are the shortest route in. ``bufr_dump``
prints a message as one ``key=value`` line per key:

.. code-block:: console

    $ bufr_dump -p sounding.bufr

A radiosonde message carries the levels as ``pressure``, ``airTemperature`` and
``dewpointTemperature``, with ``windSpeed`` and ``windDirection`` beside them;
``blockNumber`` and ``stationNumber`` identify the station, and ``year`` through
``minute`` give the launch time. A value the message does not carry prints as the
literal ``MISSING``, which matters below.

Install ecCodes however you install anything — it is on conda-forge as
``eccodes``, and ECMWF publish source and packages. It is not installed by
``tephpy`` and does not need to be: nothing on the rest of this page imports it.

For a TEMP bulletin the same applies one step earlier. ecCodes decodes BUFR, so a
TTAA/TTBB bulletin is converted to BUFR first — most archives distribute BUFR
already, which is why this page leads with it.

Build a Sounding
----------------

What comes out is arrays. What ``tephpy`` wants is a
:class:`Sounding <tephpy.sounding.Sounding>`, which takes bare sequences plus a
``units=`` mapping saying what they are in:

.. plot::
    :context: reset
    :nofigs:

    import tephpy

    pressure = [1000.0, 925.0, 850.0, 700.0, 500.0, 400.0, 300.0, 250.0, 200.0]
    temperature = [22.4, 18.1, 13.6, 4.2, -12.5, -24.1, -39.8, -49.6, -56.2]
    dewpoint = [19.8, 16.4, 11.1, -2.9, -21.0, -34.7, -51.2, -60.1, -66.4]

    sounding = tephpy.Sounding(
        pressure=pressure,
        temperature=temperature,
        dewpoint=dewpoint,
        units={"pressure": "hPa", "temperature": "degC", "dewpoint": "degC"},
        station="72357",
    )

Pressure and temperature are required and everything else is optional, so a
message that carried no humidity still gives a usable sounding — drop the
``dewpoint`` argument and its ``units`` entry together.

Two things the decoder will hand you that need a moment. ecCodes reports
temperatures in kelvin and pressures in pascals; say so in ``units=`` rather than
converting by hand, because a conversion written twice is a conversion that
disagrees with itself once. And a BUFR sounding routinely carries
missing values at some levels — the ``MISSING`` above. Pass those through as
``float("nan")`` and ``tephpy`` treats them as gaps, which is what they are. Pressure is the exception: it must be finite and
monotonic, so drop a level whose pressure is missing rather than passing a NaN.

Draw It
-------

From here it is an ordinary tephigram:

.. plot::
    :context:
    :filename-prefix: temp-and-bufr-sounding

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(sounding)

Where to Go Next
----------------

Reading an archive rather than a single message is what :mod:`tephpy.io` is for,
and the :doc:`gallery <../gallery/index>` shows what the package draws once a
sounding is in hand.
