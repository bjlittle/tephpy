# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The worked examples tephpy ships (gallery spec §3.2).

Each is a ``plot_*.py`` module with a ``main()`` returning its figure, run
from the command line with ``tephpy examples run <name>``, rendered into
the gallery by sphinx-gallery, and offered there as a download.

`REGISTRY` is the one list of them. The gallery's ordering, the command
line and the tests of gallery spec §3.7 all read it, so an example that
stops being registered is absent from all three at once — which is the
failure discovery by glob could not report.
"""

from __future__ import annotations

__all__ = ["REGISTRY"]

#: Command-line name to module name, in gallery order. The name is the
#: module's with its ``plot_`` prefix removed.
REGISTRY: tuple[tuple[str, str], ...] = (
    ("parcel-analysis", "plot_parcel_analysis"),
    ("tephigram", "plot_tephigram"),
    ("sounding", "plot_sounding"),
    ("sounding-comparison", "plot_sounding_comparison"),
    ("hodograph", "plot_hodograph"),
)
