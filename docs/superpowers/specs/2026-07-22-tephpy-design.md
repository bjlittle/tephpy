# tephpy — design specification

- **Date:** 2026-07-22
- **Status:** approved design, pre-implementation
- **License:** BSD-3-Clause (repo already carries it)
- **Repository:** https://github.com/bjlittle/tephpy (PyPI name `tephpy` verified free on 2026-07-22)

## 1. Purpose

`tephpy` is a greenfield Python package for plotting and analysing tephigrams. It draws
on the proven core of [SciTools/tephi](https://github.com/SciTools/tephi) — the
T–ln θ coordinate transform and zoom-aware isopleth artists — and adds the layer tephi
never had: parcel analysis and derived thermodynamic parameters, delegated to MetPy.

The requirements come from a verified research pass (2026-07-22) over Met Office
Factsheet 13, Stull's *Practical Meteorology*, University of Reading teaching material,
COMET/UCAR training, and NWS/HKO operational guides, cross-checked against the tephi
0.4.0.dev0 codebase. In summary, tephigram users need:

1. **The diagram**: true rotated temperature–entropy axes (isotherms and dry adiabats
   exactly perpendicular; pressure a derived curve, not an axis) with five isopleth
   families — isotherms, isobars, humidity mixing-ratio lines, dry adiabats,
   saturated adiabats. All intervals/extents/truncations are conventions and must be
   configurable.
2. **Sounding plotting**: temperature and dewpoint profiles against pressure in
   distinguishable colours, and wind barbs on a right-hand vertical staff using
   standard symbology (flag 50 kt, full barb 10 kt, half barb 5 kt).
3. **Analysis**: parcel ascent (dry adiabat from surface T meets the mixing-ratio line
   from surface Td at Normand's point/LCL, then saturated adiabat to the EL), with
   automatic CAPE, CIN, LCL, LFC, EL, wet-bulb potential temperature, and stability
   indices; the −25 mb operational cloud-base correction available explicitly.
4. **Operational practice**: overlaying multiple soundings (times, forecast vs
   observed) with distinguishable styles, legends carrying station identifier and UTC
   time, fixed comparable plot extents, indices displayed alongside the diagram, and
   publication-quality (vector) output.

tephi covers (1), (2) and much of (4); it has none of (3), no units handling, and only
bespoke text-file ingest. tephpy exists to cover all four.

## 2. Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Relationship to tephi | Greenfield successor (new repo, new API) | The analysis layer, units handling, and ingest are a scope expansion that would break tephi's plotting-only philosophy and API anyway |
| Name | `tephpy` | Owner's choice; PyPI name free |
| Thermodynamics | `metpy.calc` as a **required** dependency | One unconditional API; inherited, community-validated parcel math; coherent pint units story. Accepted cost: heavier install, coupling to MetPy releases |
| Data ingest | Arrays + light readers | Core accepts numpy/pandas/xarray with pint units; small `io` module for University of Wyoming and IGRA v2. No TEMP/BUFR decoding — documented recipes point at eccodes |
| Primary audience | Research scientists | Jupyter/scripting-first, composable API, publication output. Forecaster features are built as capabilities, not the organizing principle |
| Architecture | Layered library around a matplotlib projection | See §3. Chosen over a sounding-centric god object and over a MetPy-`SkewT`-style figure manager |

## 3. Architecture

```
tephpy/
├── transforms.py     # T–lnθ math + matplotlib "tephigram" projection
├── plotting/
│   ├── axes.py       # TephigramAxes (the projection's axes class)
│   ├── isopleths.py  # 5 line families as zoom-aware artists
│   ├── barbs.py      # wind-staff gutter, Met Office symbology
│   └── shading.py    # CAPE/CIN area fills, layer highlights
├── calc.py           # tephigram-native wrappers over metpy.calc
├── sounding.py       # Sounding dataclass (data + metadata, pint units)
├── io/
│   ├── wyoming.py    # University of Wyoming text reader
│   └── igra.py       # IGRA v2 reader
└── _constants.py     # conventions: intervals, extents, colours (overridable)
```

**Dependency rule:** `transforms` ← `plotting` ← (`calc`, `sounding`, `io`).
`calc` never imports `plotting`; indices can be computed headless, and plotting works
without ever touching `calc`.

### 3.1 `transforms`

Pure functions (p, T) ↔ (T, θ) ↔ (x, y), ported from tephi's validated
`transforms.py` (x = MA·ln θ + T, y = MA·ln θ − T with MA = 300), plus registration of
a matplotlib **projection** named `"tephigram"` so that
`plt.subplot(projection="tephigram")` works with stock matplotlib idioms. Depends only
on numpy and matplotlib; no knowledge of soundings or MetPy.

### 3.2 `plotting`

`TephigramAxes` draws the exactly-orthogonal isotherm/dry-adiabat grid and the three
curved families as zoom-aware artists (porting tephi's locator/refresh design: isopleth
geometry intersected with the view polygon each draw, labels re-placed on zoom).
Differences from tephi:

- Background isopleths are **on by default**, individually removable/configurable via
  accessor methods (`ax.isobars(...)`, `ax.wet_adiabats(...)`, `ax.mixing_ratios(...)`).
- `ax.plot_profile(...)` accepts either (pressure, temperature) pint quantities or a
  `Profile` object (e.g. the return of `calc.parcel_path`);
  `ax.plot_sounding(snd)` plots T + Td with conventional colours and a legend entry
  of station + UTC time.
- `ax.plot_barbs(...)` — right-hand gutter staff, Met Office symbology, 5 kt binning.
- `ax.shade_cape(env, parcel)` / `ax.shade_cin(env, parcel)` — area fills between
  environment and parcel curves.
- `ax.annotate_indices(indices)` — a text panel of derived parameters beside the plot.
- `ax.set_anchor(...)` — fixed extents so successive figures are directly comparable.

### 3.3 `calc`

Every function takes and returns pint quantities and delegates physics to
`metpy.calc`. Only tephigram-native compositions live here:

- `parcel_path(sounding_or_arrays, *, parcel="surface", cloud_base_correction=None)`
  → plottable `Profile` (dry adiabat → Normand's point → saturated adiabat).
  `parcel` selects the lifted parcel: `"surface"` (default) or `"mixed-layer"`
  (mean properties of the lowest 100 hPa, per operational practice). The −25 mb
  operational cloud-base correction is applied only when explicitly requested.
  `indices()` takes the same `parcel` option.
- `normand_point(pressure, temperature, dewpoint)` → (p, T) of the LCL.
- `indices(sounding)` → typed `SoundingIndices` dataclass: CAPE, CIN, LCL, LFC, EL,
  θw, lifted index. Fields are pint quantities; "does not exist" cases (e.g. no LFC)
  are NaN with the meaning documented per field — a meteorological answer, not an
  error.

### 3.4 `sounding` + `io`

`Sounding`: a frozen dataclass holding pressure/temperature/dewpoint/wind-speed/
wind-direction arrays as pint quantities, plus `station`, `time`, and a derived
`label` used for legends. Pressure and temperature are required; dewpoint and wind
are optional (a Sounding without wind plots profiles but raises on `plot_barbs`;
one without dewpoint raises on parcel analysis). Constructors: `Sounding(...)` from quantities,
`Sounding.from_dataframe(df, **column_map)`, `Sounding.from_dataset(ds, **var_map)`.
Validation at construction (§6). Readers (`io.wyoming.fetch`, `io.igra.read`) return
`Sounding` objects.

### 3.5 `_constants`

All conventions — 10 °C isotherm interval, 10 mb isobar interval, wet-adiabat
truncation temperature, gutter width, colours — live here as defaults, overridable
per-call and via a `tephpy.rcparams`-style config object. Nothing numeric is
hard-coded at point of use; docstrings cite the source convention (e.g. Met Office
Factsheet 13).

## 4. Canonical usage

```python
import matplotlib.pyplot as plt
import tephpy
from tephpy.io import wyoming

snd = wyoming.fetch("03808", "2026-07-21 12:00")      # → Sounding

fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
ax.plot_sounding(snd)                                  # T + Td, legend "03808 2026-07-21 12Z"
ax.plot_barbs(snd)

parcel = tephpy.calc.parcel_path(snd)
ax.plot_profile(parcel, color="k", linestyle="--")
ax.shade_cape(snd, parcel)
ax.annotate_indices(tephpy.calc.indices(snd))

fig.savefig("sounding.pdf")
```

Comparing soundings is two `plot_sounding` calls with different styles; `set_anchor`
keeps extents identical across figures.

## 5. Units policy

Every public boundary accepts pint quantities and converts internally (hPa/°C are the
diagram's native units; K/Pa inputs just work). Bare arrays are accepted **only** with
an explicit `units=` argument — never silently assumed. Return values are always
quantities. This is a deliberate fix for tephi's hard-wired hPa/°C/knots.

## 6. Error handling

- Unit-less input without `units=` → `TephpyUnitsError` naming the argument and the
  one-line fix.
- Physically impossible input (Td > T, non-monotonic pressure, profile too short for
  parcel analysis) → specific exception types identifying the offending levels.
  `Sounding` validates at construction so bad data fails at ingest, not mid-plot.
- MetPy NaN results (no LFC, zero CAPE) pass through as NaN, documented per field.
- Reader failures (network, unrecognised station, malformed archive) → `TephpyIOError`
  with the upstream response summarised.

## 7. Testing

- **Transforms:** hypothesis round-trip property tests ((p,T) → (x,y) → (p,T) ≡
  identity), fixed known values cross-checked against tephi's test data, and a direct
  assertion of the isotherm ⊥ dry-adiabat invariant in display space.
- **Plotting:** image-baseline tests via pytest-mpl (small in-repo PNGs,
  tolerance-tuned) for each isopleth family, profiles, barbs, shading, and the
  composed §4 figure. Deliberately not tephi's external image-hash repo, which is a
  contributor-hostile maintenance burden.
- **Calc:** test composition, not thermodynamics — parcel path passes through
  Normand's point; `indices()` fields equal direct `metpy.calc` calls on the same
  profile; the −25 mb correction applies only when requested. One integration test
  against a published worked example with known CAPE/LCL.
- **IO:** recorded-fixture tests (no live network in CI).

## 8. Tooling and packaging

- `pyproject.toml`-only; hatchling backend; `src/` layout; SPEC 0 support window
  (Python 3.11+ at launch).
- Required dependencies: matplotlib, numpy, scipy, pint, metpy.
- Ruff (lint + format); mypy strict on `transforms` and `calc`; full type hints with
  `py.typed`; pre-commit mirroring CI.
- pytest + hypothesis + pytest-mpl; coverage gate in CI.
- GitHub Actions: test matrix (3 Python versions × oldest-pinned/latest MetPy), docs
  build, trusted-publishing wheel/sdist release on tag.
- Docs: Sphinx + pydata-sphinx-theme + MyST; sphinx-gallery with one example per
  identified use case; ReadTheDocs versioned hosting.
- SemVer with a 0.x honesty period; CHANGELOG from day one.

## 9. v1 scope

Everything in §1 items 1–3 and the core of item 4: full diagram, profiles, barbs,
multi-sounding overlay + anchoring, parcel path, Normand's point, CAPE/CIN with
shading, LCL/LFC/EL, θw, lifted index, indices panel, Wyoming/IGRA readers, vector
output.

### Non-goals for v1 (decisions, not omissions — stated in the README)

- No TEMP (TTAA/TTBB) or BUFR decoding — recipe docs point at eccodes.
- No skew-T projection — MetPy owns that space.
- No hodograph — MetPy's `Hodograph` composes alongside; a gallery example shows it.
- No GUI or interactive dashboard.
- No fog-point or layer-cloud constructions (v1.x candidates).
- No aviation overlays (icing, MINTRA contrail curves) — flagged open question below.

## 10. Open questions (carried from research)

- Which aviation-specific overlays (icing layers, MINTRA) do operational users
  actually need built in, versus composing themselves?
- Which named stability indices beyond the v1 set (Showalter, K-index, Total Totals)
  are worth wrapping, given all are one-line `metpy.calc` calls for users?
- Whether BUFR ingest demand justifies an optional `tephpy[bufr]` extra later.

## 11. References

- Met Office Factsheet 13 — Upper air observations (2023)
- Stull, *Practical Meteorology*, ch. 5 (thermo-diagram construction, stability)
- University of Reading tephigram teaching notes
- COMET/UCAR tephigram training module; NWS and HKO operational guides
- SciTools/tephi 0.4.0.dev0 source (transform and isopleth-artist design)
