.. _start-overview:

:iconify:`mdi:map-outline` Overview
===================================

.. readingtime::

``tephpy`` plots and analyses :term:`tephigrams <tephigram>` — the chart a
forecaster reads a :term:`radiosonde` ascent from. It draws the diagram, puts
your data on it, and reads the standard quantities off it.

It draws, and delegates the physics. The five :term:`isopleth` families, the rotated
coordinate system and the edge labelling are ``tephpy``'s; :term:`parcel` ascent,
:term:`CAPE`, :term:`CIN` and the rest come from
`MetPy <https://unidata.github.io/MetPy/latest/>`__, so there is one source of
thermodynamic truth and it is not this package.

It also declines things, deliberately. There is no skew-T — MetPy owns that
space — no :term:`hodograph`, and no TEMP or BUFR decoding. Each has somewhere
to go instead, and the
`non-goals <https://github.com/bjlittle/tephpy#non-goals>`__ say where.

Where it comes from: ``tephpy`` reimplements
`tephi <https://github.com/SciTools/tephi>`__ on a Matplotlib :term:`projection`,
with
the thermodynamics delegated rather than reimplemented.
