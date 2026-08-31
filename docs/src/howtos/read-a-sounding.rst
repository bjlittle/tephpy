.. _howto-read-a-sounding:

Read a Sounding From an Archive
===============================

.. readingtime::

``tephpy`` reads two archive formats: the :term:`IGRA` records published by
NOAA/NCEI, and the ``TEXT:CSV`` bodies the University of Wyoming's archive
serves. Both hand back
a :class:`Sounding <tephpy.sounding.Sounding>`, and everything downstream — the
diagram, the analysis, the gallery — takes it from there without caring which
route it came by.

The package ships one :term:`radiosonde` ascent in both formats so this page can
show that. It is Camborne, 2026-07-21 12Z.

From an IGRA File
-----------------

:func:`igra.read(...) <tephpy.io.igra.read>` takes a path and the nominal launch
time that selects an ascent from it — a station file holds many:

.. plot::
    :context: reset
    :nofigs:

    from tephpy import samples
    from tephpy.io import igra

    from_igra = igra.read(
        samples.path("camborne-igra-12z"), time="2026-07-21 12:00"
    )

For your own data, that path is wherever you downloaded the station file to.
``samples.path(...)`` is only how this page gets hold of one;
:func:`samples.available() <tephpy.samples.available>` lists the names it
accepts. If your data is already in Python rather than in a file,
:ref:`howto-build-a-sounding` is the page you want.

From a Wyoming Body
-------------------

:func:`wyoming.parse(...) <tephpy.io.wyoming.parse>` takes the response body as
text. ``station`` and ``time`` are metadata rather than parsing input — the body
carries neither — so pass them if you know them and the legend label derives:

.. plot::
    :context:
    :nofigs:

    from tephpy.io import wyoming

    body = samples.path("camborne-wyoming-12z").read_text(encoding="utf-8")
    from_wyoming = wyoming.parse(body, station="03808", time="2026-07-21 12:00")

The Same Ascent, Either Way
---------------------------

Both are now :class:`Sounding <tephpy.sounding.Sounding>` objects over the same
balloon flight. Here they are on one diagram:

.. plot::
    :context:
    :filename-prefix: read-a-sounding-converged

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(from_igra)
    ax.plot_sounding(from_wyoming)
    ax.legend()

You cannot pick them apart, and that is the point of this page: the archives and
the readers differ, and what comes out the far end does not. The legend carries two
entries; the traces are one.

Two things about that pair are worth knowing before you compare readings of your
own.

**The archives thin differently.** This IGRA record carries 263 levels and the
Wyoming capture 61, because the Wyoming sample shipped here was thinned to keep it
small. Neither is wrong; they are different samplings of one ascent, so a
level-by-level comparison is not a fair test of either reader.

**They name the station differently.** IGRA identifies it as ``UKM00003808`` — an
eleven-character identifier carrying a country and network code — and the Wyoming
archive as ``03808``, the bare WMO number that the identifier's tail zero-pads.
The legends therefore differ, and neither is a defect.

What agrees is the atmosphere. Both put the surface near 1019 hPa at about
19.6 °C.

Fetching From the Network
-------------------------

:func:`wyoming.fetch(...) <tephpy.io.wyoming.fetch>` does the download for you:
give it a station identifier and a time — ``wyoming.fetch("03808",
"2026-07-21 12:00")`` — and it returns the same
:class:`Sounding <tephpy.sounding.Sounding>` the section above built from a saved
body. It takes an optional ``timeout``, and raises
:class:`TephpyIOError <tephpy.exceptions.TephpyIOError>` for a network failure, an
HTTP error, or a body it cannot read — one of the hierarchy
:mod:`tephpy.exceptions` describes, which ``except TephpyError`` catches
whole.

**That call is described here rather than shown as a block, and the reason is a
feature of these pages.** Every python block in the how-to, tutorial and
explanation guides is executed by the test suite, as one script per page and on
every supported Python version; the blocks that publish a figure, which is all of
them on this page, run again when the documentation is built. That is why you can
trust the ones above. A block calling ``fetch`` would reach the University of
Wyoming in both places — on every test run and every build — and would then fail
for reasons that have nothing to do with ``tephpy``: a rate limit, an outage, a
proxy. So this page runs what it can and says plainly what it cannot.

You lose little by reading it rather than running it. ``fetch`` is ``parse`` with
a download in front: it requests the body and hands it to the same parser the
section above called directly, so a :term:`sounding` you fetch and a sounding you
parse
are built by identical code. If you want to check it against your own network,
that is a Python prompt away.

Where to Go Next
----------------

:ref:`tutorial-first-tephigram` draws a sounding and names everything on it, and
:ref:`howto-temp-and-bufr` covers the formats ``tephpy`` deliberately does not
read — TEMP bulletins and BUFR messages — and what to reach for instead.
