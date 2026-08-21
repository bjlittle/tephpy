# Ingest-Reader Fixtures

Recorded captures for the `tephpy.io` tests — no live network in CI
(spec §7); provenance recorded per spec §10 item 13. Regenerate both files
with `pixi run python tests/fixtures/generate_io_fixtures.py` (network
required) and update the capture dates below.

Both fixtures record the **same physical ascent** — Camborne, nominal
2026-07-21 12Z, released 11:17 UTC — so the two readers cross-validate
against each other in the tests.

That script writes a third file, which is **not** a fixture:
`src/tephpy/samples/USM00072357-data-trimmed.txt`, the sounding data tephpy
ships and the gallery draws (gallery spec §3.1). It is the same IGRA capture
by the same method, so it is generated here rather than by a second script
that would drift from this one; its provenance is recorded in the
`tephpy.samples` docstring, which the API documentation publishes. Running
the script rewrites it too — update that docstring's capture date as well.

## wyoming-03808-2026-07-21-12Z.csv

- **Source:** <https://weather.uwyo.edu/wsgi/sounding?datetime=2026-07-21%2012:00:00&id=03808&type=TEXT:CSV>
- **Captured:** 2026-07-27, thinned to every 40th data row plus the first
  and last (kept rows are byte-faithful; the header row is complete).
- **Attribution:** sounding data courtesy of the University of Wyoming,
  College of Engineering, Department of Atmospheric Science
  (<https://weather.uwyo.edu/upperair/sounding.shtml>). One recorded
  ascent, used as test facts.

## UKM00003808-data-trimmed.txt

- **Source:** <https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/access/data-y2d/UKM00003808-data-beg2026.txt.zip>
- **Captured:** 2026-07-27; the 2026-07-21 00Z and 12Z ascents as whole
  byte-faithful blocks (header record plus its declared level count).
- **Attribution:** NOAA/NCEI Integrated Global Radiosonde Archive (IGRA)
  version 2, a U.S. Government work in the public domain. Durre, I.,
  X. Yin, R. S. Vose, S. Applequist, and J. Arnfield (2016):
  doi:10.7289/V5X63K0Q.
