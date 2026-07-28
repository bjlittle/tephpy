# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Capture and trim the ingest-reader fixtures (one-shot; not run in CI).

Run with network access from the repo root:

    pixi run python tests/fixtures/generate_io_fixtures.py

Writes into ``tests/fixtures/io/``:

- ``wyoming-03808-2026-07-21-12Z.csv`` — the University of Wyoming
  ``TEXT:CSV`` body for Camborne (WMO 03808) at 2026-07-21 12Z, thinned to
  every 40th data row (plus the first and last) so the fixture stays a few
  KB; the kept rows are byte-faithful.
- ``UKM00003808-data-trimmed.txt`` — the 2026-07-21 00Z and 12Z ascents
  from NCEI's IGRA v2 year-to-date file for Camborne (UKM00003808),
  byte-faithful whole blocks (header + declared level count).

Both captures record the same physical ascent (2026-07-21 12Z, released
11:17 UTC), so the two readers cross-validate. Provenance — source URLs,
capture date, method, attribution — is kept in ``io/README.md`` beside the
fixtures and must be updated when this script is re-run.
"""

from __future__ import annotations

import io
from pathlib import Path
from urllib.request import urlopen
import zipfile

WYOMING = (
    "https://weather.uwyo.edu/wsgi/sounding"
    "?datetime=2026-07-21%2012:00:00&id=03808&type=TEXT:CSV"
)
IGRA = (
    "https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/"
    "access/data-y2d/UKM00003808-data-beg2026.txt.zip"
)
KEPT_HEADERS = (" 2026 07 21 00 ", " 2026 07 21 12 ")
STRIDE = 40

out = Path(__file__).parent / "io"
out.mkdir(exist_ok=True)

with urlopen(WYOMING, timeout=60) as response:
    rows = response.read().decode("utf-8").splitlines()
kept = [rows[0], *rows[1::STRIDE]]
if rows[-1] != kept[-1]:
    kept.append(rows[-1])
(out / "wyoming-03808-2026-07-21-12Z.csv").write_text("\n".join(kept) + "\n")
print(f"wyoming: kept {len(kept) - 1} of {len(rows) - 1} data rows")

with urlopen(IGRA, timeout=120) as response:
    payload = response.read()
with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
    (member,) = bundle.namelist()
    lines = bundle.read(member).decode("ascii").splitlines()
blocks: list[str] = []
index = 0
while index < len(lines):
    line = lines[index]
    if line.startswith("#") and any(stamp in line for stamp in KEPT_HEADERS):
        levels = int(line[32:36])
        blocks.extend(lines[index : index + 1 + levels])
        index += 1 + levels
    else:
        index += 1
(out / "UKM00003808-data-trimmed.txt").write_text("\n".join(blocks) + "\n")
ascents = sum(1 for block in blocks if block.startswith("#"))
print(f"igra: kept {ascents} ascents, {len(blocks)} lines")
