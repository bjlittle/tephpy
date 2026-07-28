# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Data ingest readers returning :class:`~tephpy.sounding.Sounding` (spec §3.4).

Light readers over the University of Wyoming sounding archive
(:mod:`tephpy.io.wyoming`) and NCEI's Integrated Global Radiosonde Archive
version 2 (:mod:`tephpy.io.igra`). Reader failures raise
:class:`~tephpy.exceptions.TephpyIOError`; the returned soundings pass the
ordinary ingest validation (spec §6). TEMP/BUFR decoding is out of scope —
the documentation points at eccodes.
"""

from __future__ import annotations
