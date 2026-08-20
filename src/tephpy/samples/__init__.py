# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Sounding data shipped with tephpy (gallery spec §3.1).

Two radiosonde ascents from Norman, Oklahoma on 2013-05-20, the morning of
the Moore EF5 tornado: the 12Z ascent of the canonical example (spec §4),
and the 17Z special released about three hours before the tornado touched
down. Both are in one IGRA v2 station file, read by name.

.. code-block:: python

    from tephpy import samples

    snd = samples.sounding("norman-12z")

**Provenance.** Captured 2026-08-20 by
``tests/fixtures/generate_io_fixtures.py`` from `NCEI's IGRA v2
period-of-record file for station USM00072357
<https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/
access/data-por/USM00072357-data.txt.zip>`__, keeping the two ascents of
that date as whole byte-faithful blocks — a header record and its declared
level count. The archive is the NOAA/NCEI Integrated Global Radiosonde
Archive version 2, a U.S. Government work in the public domain; cite it as
Durre, I., X. Yin, R. S. Vose, S. Applequist, and J. Arnfield (2016),
doi:10.7289/V5X63K0Q.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tephpy.io import igra

if TYPE_CHECKING:
    from tephpy.sounding import Sounding

__all__ = ["available", "path", "sounding"]

# The shipped IGRA v2 station file, holding every sample below.
_FILE = "USM00072357-data-trimmed.txt"

# Sample name to the nominal launch time that selects its ascent.
_SAMPLES = {
    "norman-12z": "2013-05-20 12:00",
    "norman-17z": "2013-05-20 17:00",
}


def available() -> tuple[str, ...]:
    """Report the sample names :func:`sounding` accepts.

    Returns
    -------
    tuple of str
        The names, in the order the ascents were measured.
    """
    return tuple(_SAMPLES)


def path() -> Path:
    """Return the shipped IGRA v2 station file.

    It holds every sample :func:`available` names, which is why this takes
    no argument. It is a file beside this module rather than an
    :mod:`importlib.resources` traversable: the caller this exists for is a
    reader opening it with :func:`tephpy.io.igra.read`, and a zip-imported
    install would hand them a path that vanishes on the next line.

    Returns
    -------
    pathlib.Path
        The station file.
    """
    return Path(__file__).parent / _FILE


def sounding(name: str) -> Sounding:
    """Read a shipped sounding by name.

    Parameters
    ----------
    name : str
        One of the names :func:`available` reports.

    Returns
    -------
    Sounding
        The ascent, read through :func:`tephpy.io.igra.read` — the same
        documented route a user's own file takes.

    Raises
    ------
    ValueError
        If `name` is not a shipped sample.
    """
    when = _SAMPLES.get(name)
    if when is None:
        msg = f"unknown sample {name!r}; available: {', '.join(available())}"
        raise ValueError(msg)
    return igra.read(path(), time=when)
