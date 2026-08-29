# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Sounding data shipped with tephpy (gallery spec §3.1).

Four samples from two stations, each read by name through a public reader.

.. code-block:: python

    from tephpy import samples

    snd = samples.sounding("norman-12z")

**Norman, Oklahoma, 2013-05-20** — the morning of the Moore EF5 tornado: the
12Z ascent of the canonical example (spec §4), and the 17Z special released
about three hours before the tornado touched down. Both are in one IGRA v2
station file.

**Camborne, 2026-07-21 12Z** — one ascent, shipped twice: as the IGRA record
and as the University of Wyoming ``TEXT:CSV`` body. The pair exists so the
reader how-to can show both supported routes into a
:class:`~tephpy.sounding.Sounding` converging on the same profile
(narrative spec §3.6), which needs the same physical ascent on both sides.

**Provenance.** All four captured by
``tests/fixtures/generate_io_fixtures.py``.

- The Norman file, 2026-08-20, from `NCEI's IGRA v2 period-of-record file for
  station USM00072357 <https://www.ncei.noaa.gov/data/
  integrated-global-radiosonde-archive/access/data-por/
  USM00072357-data.txt.zip>`__, keeping the two ascents of that date as whole
  byte-faithful blocks — a header record and its declared level count.
- The Camborne IGRA file, 2026-07-27, the same way from that station's
  year-to-date file.
- The Camborne Wyoming body, 2026-07-27, from the `University of Wyoming
  sounding archive <https://weather.uwyo.edu/upperair/sounding.shtml>`__,
  thinned to every 40th data row plus the first and last; kept rows are
  byte-faithful and the header row is complete.

**Attribution.** The IGRA files are from the NOAA/NCEI Integrated Global
Radiosonde Archive version 2, a U.S. Government work in the public domain;
cite it as Durre, I., X. Yin, R. S. Vose, S. Applequist, and J. Arnfield
(2016), doi:10.7289/V5X63K0Q. The Wyoming body is sounding data courtesy of
the University of Wyoming, College of Engineering, Department of Atmospheric
Science. That archive publishes no redistribution terms, so it travels here
as a considered risk rather than a granted permission — narrative spec §3.6
states the position and :issue:`202` carries the question.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from tephpy.io import igra, wyoming

if TYPE_CHECKING:
    from tephpy.sounding import Sounding

__all__ = ["available", "path", "sounding"]


class _Sample(NamedTuple):
    """One shipped ascent: the file holding it, and how to read it."""

    file: str
    reader: str
    time: str
    station: str | None = None


# Every shipped sample, in the order the ascents were measured. ``reader``
# names a public function of ``tephpy.io``, because a sample a user cannot
# reproduce by the documented route proves nothing about that route. The
# Wyoming body carries ``station`` too: an IGRA record identifies its station
# and a ``TEXT:CSV`` body does not, so the identifier is supplied here to get
# the same metadata on both halves of the Camborne pair.
_SAMPLES = {
    "norman-12z": _Sample("USM00072357-data-trimmed.txt", "igra", "2013-05-20 12:00"),
    "norman-17z": _Sample("USM00072357-data-trimmed.txt", "igra", "2013-05-20 17:00"),
    "camborne-igra-12z": _Sample(
        "UKM00003808-data-trimmed.txt", "igra", "2026-07-21 12:00"
    ),
    "camborne-wyoming-12z": _Sample(
        "wyoming-03808-2026-07-21-12Z.csv", "wyoming", "2026-07-21 12:00", "03808"
    ),
}


def available() -> tuple[str, ...]:
    """Report the sample names :func:`sounding` accepts.

    Returns
    -------
    tuple of str
        The names, in the order the ascents were measured.
    """
    return tuple(_SAMPLES)


def _select(name: str) -> _Sample:
    """Look one sample up, or say what the caller could have asked for.

    Parameters
    ----------
    name : str
        A candidate sample name.

    Returns
    -------
    _Sample
        The entry for `name`.

    Raises
    ------
    ValueError
        If `name` is not a shipped sample.
    """
    sample = _SAMPLES.get(name)
    if sample is None:
        msg = f"unknown sample {name!r}; available: {', '.join(available())}"
        raise ValueError(msg)
    return sample


def path(name: str) -> Path:
    """Return the file a shipped sample is read from.

    Two formats ship, so there is no one file to return without being asked
    — this took no argument while the package carried a single IGRA station
    file. It is a file beside this module rather than an
    :mod:`importlib.resources` traversable: the caller this exists for is a
    reader opening it with :func:`igra.read <tephpy.io.igra.read>` or
    :func:`wyoming.parse <tephpy.io.wyoming.parse>`, and a zip-imported
    install would hand them a path that vanishes on the next line.

    Note that one file may hold several samples: both Norman ascents are in
    one IGRA station record, so two names give the same path and differ only
    in the ascent they select from it.

    Parameters
    ----------
    name : str
        One of the names :func:`available` reports.

    Returns
    -------
    pathlib.Path
        The file holding that sample.

    Raises
    ------
    ValueError
        If `name` is not a shipped sample.
    """
    return Path(__file__).parent / _select(name).file


def sounding(name: str) -> Sounding:
    """Read a shipped sounding by name.

    Every sample goes through a public reader — :func:`igra.read
    <tephpy.io.igra.read>` or :func:`wyoming.parse
    <tephpy.io.wyoming.parse>` — which is the same documented route a user's
    own file takes. A sample reached by a private path would demonstrate
    nothing a reader could repeat.

    Parameters
    ----------
    name : str
        One of the names :func:`available` reports.

    Returns
    -------
    Sounding
        The ascent.

    Raises
    ------
    ValueError
        If `name` is not a shipped sample.
    """
    sample = _select(name)
    if sample.reader == "wyoming":
        body = path(name).read_text(encoding="utf-8")
        return wyoming.parse(body, station=sample.station, time=sample.time)
    return igra.read(path(name), time=sample.time)
