# tephpy — design specification

- **Date:** 2026-07-22
- **Status:** approved design, pre-implementation
- **License:** BSD-3-Clause (repo already carries it)
- **Repository:** https://github.com/bjlittle/tephpy (PyPI name `tephpy` verified free on 2026-07-22)
- **Engineering standards baseline:** [bjlittle/geovista](https://github.com/bjlittle/geovista)
  is the minimum bar — pixi-led workflow, SPEC 0 support window, Diátaxis docs, and the
  geovista pre-commit/CI conventions. See §8.

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
   moist adiabats. All intervals/extents/truncations are conventions and must be
   configurable.
2. **Sounding plotting**: temperature and dewpoint profiles against pressure in
   distinguishable colours, and wind barbs on a right-hand vertical staff using
   standard symbology (flag 50 kt, full barb 10 kt, half barb 5 kt).
3. **Analysis**: parcel ascent (dry adiabat from surface T meets the mixing-ratio line
   from surface Td at Normand's point/LCL, then moist adiabat to the EL), with
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
| Engineering standards | Mirror geovista (§8) | pixi-led, SPEC 0, Diátaxis, geovista pre-commit/ruff/mypy/CI conventions. geovista is the explicit minimum bar |
| Build backend | `setuptools` + `setuptools_scm` | Matches geovista; dynamic version written to `_version.py` (not hatchling as first sketched) |
| CI scope at v1 | Core gates now, maintenance bots as fast-follow | Load-bearing quality gates from day one; lockfile/canary/linkcheck/stale/JOSS bots deferred so a new repo isn't buried in bot noise (§8.6) |

## 3. Architecture

```
src/tephpy/
├── transforms.py     # T–lnθ math (pure numpy)
├── plotting/
│   ├── axes.py       # TephigramAxes + "tephigram" projection registration
│   ├── isopleths.py  # 5 line families as zoom-aware artists
│   ├── barbs.py      # wind-staff gutter, Met Office symbology
│   └── shading.py    # CAPE/CIN area fills
├── calc.py           # tephigram-native wrappers over metpy.calc
├── sounding.py       # Sounding dataclass (data + metadata, pint units)
├── io/
│   ├── wyoming.py    # University of Wyoming text reader
│   └── igra.py       # IGRA v2 reader
├── examples/         # sphinx-gallery sources (one per use case)
├── exceptions.py     # public shared exception hierarchy (§6)
├── _config.py        # tephpy.config: typed runtime configuration (§3.5)
├── _constants.py     # conventions: intervals, extents, colours (overridable)
├── _units.py         # boundary units coercion over MetPy's registry (§5)
└── _version.py       # written by setuptools_scm (not committed)
```

**Dependency rule:** `transforms` ← `plotting`, and `transforms`/`sounding` ←
(`calc`, `io`) — `sounding` sits below the analysis and ingest layers that consume
it. `calc` never imports `plotting` (`plotting` sees `calc`/`sounding` types only
under `TYPE_CHECKING`); indices can be computed headless, and plotting works
without ever touching `calc`.

### 3.1 `transforms`

Pure functions (p, T) ↔ (T, θ) ↔ (x, y) — x = MA·ln θ + T, y = MA·ln θ − T with
MA = 300 — **derived from the published construction** (Met Office Factsheet 13; Stull)
and cross-validated against tephi as an oracle, not ported from it on trust (§7).
Bare numpy arrays in diagram-native units (hPa, °C): the §5 units policy applies to the
user-facing data boundaries above this module, not to the geometry engine matplotlib
calls on every draw. Depends only on numpy; no knowledge of soundings, pint, or MetPy.

The matplotlib **projection** named `"tephigram"` is registered by `plotting/axes.py` —
a minimal `TephigramAxes` ships in Plan 2 and Plan 3 extends it in place — so that
`plt.subplot(projection="tephigram")` works with stock matplotlib idioms while
preserving the layering (`plotting` imports `transforms`, never the reverse).

The Plan 2 minimum: an invertible matplotlib `Transform` wrapping the transform
functions, equal aspect locked (the isotherm ⊥ dry-adiabat invariant must be visually
true), sensible default extents, zoom/pan working through the transform, and native
x/y ticks hidden — meaningful labelling arrives with Plan 3's isopleths. Out-of-domain
input (p ≤ 0, unphysical T) propagates NaN rather than raising: exception-carrying
validation belongs to the quantified boundaries above (§6). Plan 2 also seeds
`_constants.py` (MA, the θ reference pressure, default extents) per §3.5's
no-hard-coding rule. Oracle fixtures are generated by running tephi 0.4.0.post0 and
recording input/output pairs with a provenance header (generation script and tephi
version) — generated outputs, not copied source.

### 3.2 `plotting`

`TephigramAxes` draws the exactly-orthogonal isotherm/dry-adiabat grid and the three
curved families as zoom-aware artists, reimplementing tephi's locator/refresh design
as one custom `IsoplethFamily` artist per family (`plotting/isopleths.py`). Member
polylines are precomputed as bare numpy arrays over a generous physical domain — the
straight families and isobars from `transforms`, moist adiabats and mixing-ratio
lines via `metpy.calc` (function-local imports keep `import tephpy` light; item 10) —
cached on the artist, and rebuilt only when family parameters or the domain change.
Each `draw()` clips the cached geometry to the current view rectangle, selects the
members appropriate to the zoom level, and re-places the family's labels: pure numpy
per draw, with pan/zoom/resize/`set_extent` automatically current because matplotlib
calls `draw` on every render. Computing the curved families with MetPy keeps one
source of moist-thermodynamic truth — the background moist adiabats are exactly the
curves Plan 5's parcel paths follow.

Differences from tephi:

- Background isopleths are **on by default**, individually removable/configurable via
  accessor methods — `ax.isotherms(...)`, `ax.isobars(...)`, `ax.dry_adiabats(...)`,
  `ax.moist_adiabats(...)`, `ax.mixing_ratios(...)`. With no arguments an accessor
  returns the family artist; with kwargs (`values=`/`interval=`, `color=`, `labels=`,
  `visible=`, …) it reconfigures and returns it.
- `ax.plot_profile(pressure, temperature, *, units=None, label=None, **kwargs)`
  accepts pint quantities — or bare arrays with the §5 `units=` mapping — converts
  to diagram-native units, plots through the tephigram transform machinery, and
  returns the `Line2D`; matplotlib kwargs pass through untouched. The same
  signature also accepts a `calc.Profile` (e.g. the return of `calc.parcel_path`)
  as its only positional argument (the first parameter keeps its Plan 4 name;
  the `Profile` form is positional). Dispatch is duck-typed on the `Profile`
  shape — the `temperature` parameter omitted and array
  `pressure`/`temperature` attributes plus `lcl_pressure` present (`Sounding`
  lacks `lcl_pressure`; `SoundingIndices` lacks the arrays) — so `plotting`
  never imports `calc` (the §3 layering; the same `TYPE_CHECKING` trick
  `plot_sounding` uses for `Sounding`), typed with `@overload`. Label
  precedence: `label=` argument > `profile.label` > no entry. Wrong argument
  combinations stay `TypeError`s, never units errors: a `Profile` together
  with `temperature` or `units=`, and equally `temperature` omitted when the
  sole argument is not `Profile`-shaped (a bare pressure array, or a
  `Sounding` passed by mistake). In both forms `plot_profile` sets no style
  defaults — it is the low-level primitive (§4 styles parcel paths explicitly
  at the call site).
- `ax.plot_sounding(snd, *, label=None, **kwargs)` plots temperature plus
  dewpoint-when-present as two profile lines in the conventional colours
  (temperature red, dewpoint green — the operational/MetPy convention; colours,
  linewidth, and a zorder above the isopleth families all live in `_constants`).
  One legend entry per sounding, attached to the temperature line (the dewpoint
  line is `"_nolegend_"`); label precedence is `label=` argument > `snd.label` >
  no entry. Returns `(temperature_line, dewpoint_line | None)`. Legends stay
  stock matplotlib — tephpy sets labels, the user calls `ax.legend()`.
- `ax.plot_barbs(...)` — right-hand gutter staff, Met Office symbology, 5 kt binning.
- `ax.shade_cape(snd, parcel)` / `ax.shade_cin(snd, parcel)` — area fills between
  the environment temperature and the parcel path, bounded exactly as MetPy's
  `cape_cin` integrates so the shading always matches the annotated numbers:
  CAPE is the positive-buoyancy region from the LFC to the EL (to the profile
  top when EL is NaN with CAPE > 0, §6), CIN the negative-buoyancy region from
  the parcel start to the LFC. Pure builders in `plotting/shading.py`
  interpolate both curves onto their merged pressure grid (linear in ln p),
  locate the buoyancy sign-change crossings, and return the region's closed
  polygons in (T, θ) space — plural when the region is interrupted — the
  `isopleths.py` free-builder pattern, headlessly testable. The axes methods
  draw them through the tephigram transform as one compound-path `PathPatch`
  per call; zero area returns `None` — 0 is an answer, not an error (§6).
  Styling is matplotlib kwargs over `_constants` conventions (colours, alpha,
  a zorder between the isopleth families and the profile lines); no
  `tephpy.config` section at v1, matching the profile-line treatment.
- `ax.annotate_indices(indices)` — a text panel of derived parameters beside the
  diagram: the first consumer of the side-of-axes contract below, appended with
  the `axes_grid1` divider, one formatted line per `SoundingIndices` field (NaN
  renders as an em dash); field formats and the panel width live in `_constants`.
  Returns the panel axes so users can restyle; calling it again updates the
  panel in place rather than stacking a second one. With `axes_grid1`, append
  order is position order, so once Plan 6's gutter exists, `plot_barbs` must be
  called before `annotate_indices` for the contracted inside-out order —
  documented in the docstring; enforcement, if ever needed, is Plan 6's call.
- `ax.set_extent(...)` — fixed extents from ((p, T), (p, T)) corners so successive
  figures are directly comparable; disables autoscaling so overlays don't drift the
  window. (The cartopy idiom — the earlier `set_anchor` name collided with
  matplotlib's own `Axes.set_anchor`.)

Side-of-axes layout contract (decided in Plan 3, built by the consuming plans):
panels beside the diagram are appended with `mpl_toolkits.axes_grid1`'s axes
divider, which tracks the equal-aspect box height — right side, inside-out: Plan 6's
barb gutter, then Plan 5's indices panel. Panel widths join `_constants` with their
plans.

### 3.3 `calc`

Physics is delegated to `metpy.calc`; only tephigram-native compositions live
here, and everything returns pint quantities on the shared registry (§5).
Sounding-level functions take a `Sounding` — constructing one is the §3.4
one-liner that already validates units, monotonic pressure, and Td ≤ T, so
`calc` keeps a single validation path — while `normand_point` is the one
quantity-level function. `calc` imports `transforms` and `sounding`, never
`plotting`; MetPy stays behind function-local imports (the established idiom,
policed by the import-cost guard test), so `calc` re-exports eagerly at the
top level and `import tephpy` stays light (item 10). Two frozen dataclasses
(the `Sounding` idiom: coerced and validated at construction) carry results:

- `Profile`: `pressure`/`temperature` quantities for the full ascent
  (surface-first), scalar `lcl_pressure`/`lcl_temperature` (the Normand's
  point the path actually uses — i.e. the corrected one when a correction was
  requested), `parcel` (`"surface"` | `"mixed-layer"`), and `label` (legend
  text; `None` = no entry). Construction mirrors `Sounding`: bare arrays take
  the §5 `units=` mapping, fields are dimension-checked quantities on the
  shared registry, and `__post_init__` validates 1-D equal-length arrays of
  at least two levels with strictly decreasing pressure
  (`TephpyValidationError`), the LCL inside the path's pressure span, and the
  `parcel` literal (`ValueError`). Plain plottable data: `plot_profile` draws
  it and the shading builders consume it, and neither re-derives the LCL.
- `SoundingIndices`: ten scalar quantity fields — `cape`, `cin`,
  `lcl_pressure`, `lcl_temperature`, `lfc_pressure`, `lfc_temperature`,
  `el_pressure`, `el_temperature`, `theta_w`, `lifted_index` — each
  dimension-checked at construction and documented with the §6
  NaN-versus-zero semantics (no cross-field validation: NaN fields are
  answers). `theta_w` is the lifted parcel's wet-bulb potential temperature,
  evaluated at the parcel start (p, T, Td), so it follows the `parcel=`
  option. The v1 set is a decision (§11): Showalter, K-index, and Total
  Totals stay one-line `metpy.calc` calls for users, shown in a docs example
  rather than wrapped.

Functions:

- `parcel_path(snd, *, parcel="surface", cloud_base_correction=None,
  label=None)` → `Profile` (dry adiabat → Normand's point → moist adiabat,
  spanning parcel start pressure to profile top; requires `snd.dewpoint`,
  §6). `parcel` selects the lifted parcel: `"surface"` (default) or
  `"mixed-layer"` (`metpy.calc.mixed_parcel`; its 100 hPa default depth is
  the operational convention); an unknown value is a `ValueError` (bad code,
  not bad data). `cloud_base_correction` is a pressure-dimension quantity
  applied to the LCL only when explicitly requested — the operational −25 mb
  value lives in `_constants` with its source convention cited, and the
  corrected LCL temperature is re-read from the dry adiabat at the corrected
  pressure. The moist leg is integrated with
  `metpy.calc.moist_lapse(..., reference_pressure=p_lcl)` at the background
  family's 5 hPa step — same integrator, same sampling, same anchoring as
  §3.2's moist adiabats — so a parcel whose θw equals a member value lies
  exactly on that background curve; the LCL vertex is spliced in exactly.
  The dry leg samples the same 5 hPa step (a dry adiabat is straight in
  (T, θ), but uniform sampling keeps the §3.2 shading interpolation faithful).
  (θw *reported* by `indices()` uses `wet_bulb_potential_temperature`, whose
  Davies-Jones formulation differs from the ODE by ≲0.1 °C; the path is
  drawn by the integrator, the number by the named function, and the
  divergence is documented.)
- `normand_point(pressure, temperature, dewpoint)` → (p, T) of the LCL —
  scalar quantities (bare values take the §5 `units=` mapping), always the
  uncorrected geometric construction. `parcel_path` composes it.
- `indices(snd, *, parcel="surface", cloud_base_correction=None)` →
  `SoundingIndices`, with the same parcel options as `parcel_path`. The
  mechanism: derive the parcel curve on the environment levels under the
  same parcel-selection and correction rules as `parcel_path`, then feed it
  to the generic `metpy.calc` functions that take a parcel-profile argument
  (`cape_cin`, `lfc`, `el`, `lifted_index`); the `lcl_*` fields report the
  point the path uses (corrected when requested) and `theta_w` the parcel
  start, mirroring `Profile`. With the defaults this reduces to plain
  surface-parcel delegation — which is what §7's field-equality test
  targets — and composition, not thermodynamics, is what tephpy tests (§7).

### 3.4 `sounding` + `io`

`Sounding`: a frozen dataclass holding pressure/temperature/dewpoint/wind-speed/
wind-direction arrays as pint quantities. Pressure and temperature are required;
dewpoint and wind are optional (a Sounding without wind plots profiles but raises on
`plot_barbs`; one without dewpoint raises on parcel analysis), and the two wind
fields must arrive together. Inputs are coerced in `__post_init__` — bare arrays
need the §5 `units=` mapping — so a constructed Sounding always holds quantities.

`station` and `time` are optional metadata; `label` is the legend text. An explicit
`label=` stands as-is; otherwise it derives as `"03808 2026-07-21 12Z"` when both
station and time are present (naive datetimes read as UTC, aware ones converted to
UTC; format string in `_constants` per §3.5), otherwise `None` — and `None` means
no legend entry. Distinguishing forecast-vs-observed overlays of one station/time
is the label override's job; there is no dedicated field for it.

Validation at construction (§6 — fail at ingest, not mid-plot): 1-D equal-length
arrays of at least two levels; finite, strictly monotonic pressure accepted in
either direction and normalized to decreasing (surface-first) storage with all
arrays reversed together, so downstream `metpy.calc` sees one orientation; where
dewpoint and temperature are both non-NaN, Td > T is rejected (equality —
saturation — is physical). NaN gaps are data everywhere except pressure.

Constructors: `Sounding(...)` from quantities or bare arrays + `units=`;
`Sounding.from_dataframe(df, **column_map)` — column names default to field names,
`column_map` overrides, bare columns take the `units=` mapping, and
`pd.Timestamp`/`datetime64` are accepted for `time`;
`Sounding.from_dataset(ds, **var_map)` — units read from each variable's
`attrs["units"]` (the xarray/CF convention) parsed through the registry, `units=`
as the explicit override, `TephpyUnitsError` when neither exists. pandas and
xarray are declared runtime dependencies, but tephpy never imports either at
runtime — the constructors are duck-typed over the objects handed to them, with
`TYPE_CHECKING`-only annotation imports (item 9). `Sounding` re-exports eagerly
at the top level — `from tephpy import
Sounding` (item 10). Readers (`io.wyoming.fetch`, `io.igra.read`) return
`Sounding` objects.

### 3.5 `_constants` + `tephpy.config`

All conventions — 10 °C isotherm interval, 10 mb isobar interval, moist-adiabat
truncation temperature, gutter width, colours — live in `_constants.py` as defaults;
nothing numeric is hard-coded at point of use, and docstrings cite the source
convention (e.g. Met Office Factsheet 13). The mutable runtime layer over them is
`tephpy.config` (`_config.py`): a typed singleton of per-family dataclass sections
plus a diagram-wide section (e.g. `config.isobars.interval`,
`config.moist_adiabats.truncation`, `config.diagram.extent`), with a
`config.context(...)` manager for temporary overrides. Precedence: accessor kwargs >
`tephpy.config` > `_constants`. Config is read when a family is created or
reconfigured; changing it does not retroactively restyle existing axes (matplotlib
rcParams semantics).

## 4. Canonical usage

```python
import matplotlib.pyplot as plt
import tephpy
from tephpy.io import wyoming

snd = wyoming.fetch("03808", "2026-07-21 12:00")  # → Sounding

fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
ax.plot_sounding(snd)  # T + Td, legend "03808 2026-07-21 12Z"
ax.plot_barbs(snd)

parcel = tephpy.calc.parcel_path(snd)
ax.plot_profile(parcel, color="k", linestyle="--")
ax.shade_cape(snd, parcel)
ax.annotate_indices(tephpy.calc.indices(snd))

fig.savefig("sounding.pdf")
```

Comparing soundings is two `plot_sounding` calls with different styles; `set_extent`
keeps extents identical across figures.

## 5. Units policy

Every public boundary accepts pint quantities and converts internally (hPa/°C are the
diagram's native units; K/Pa inputs just work). Bare arrays are accepted **only** with
an explicit `units=` argument — never silently assumed. Return values are always
quantities. This is a deliberate fix for tephi's hard-wired hPa/°C/knots.

One documented exemption: the `transforms` geometry layer (§3.1) trades in bare numpy
arrays in diagram-native units (hPa/°C), because matplotlib's per-draw transform
pipeline consumes bare arrays; every layer above it converts before calling down.

The machinery (`_units.py`, private): tephpy standardizes on **MetPy's pint
registry** — one registry across tephpy, MetPy, and user code, so quantities flow
into `metpy.calc` without cross-registry errors (MetPy imported function-locally to
keep `import tephpy` light). A single boundary helper
`as_quantity(value, *, name, units=None, dimension)` checks a quantity's
dimensionality, wraps a bare array (`units=` required), and raises
`TephpyUnitsError` naming the argument and the one-line fix — for unit-less input,
wrong dimensionality, or the ambiguous quantity-plus-`units=` case alike. At
multi-argument boundaries `units=` is a mapping keyed by argument/field name
(`units={"pressure": "hPa", "temperature": "degC"}`) — one mechanism at every
signature rather than per-signature positional conventions.

## 6. Error handling

- Unit-less input without `units=` → `TephpyUnitsError` naming the argument and the
  one-line fix.
- Physically impossible input (Td > T, non-monotonic pressure) → specific
  exception types identifying the offending levels; `Sounding` validates at
  construction so bad data fails at ingest, not mid-plot. Analysis-time data
  errors (missing dewpoint, a profile too short for the requested parcel
  ascent) raise at the `calc` boundary instead — the earliest point they are
  knowable, since they depend on the `parcel=`/correction options.
- Analysis results distinguish "does not exist" from "zero" (verified against
  MetPy 1.7.1 — item 11): `metpy.calc` returns NaN quantities for a missing
  LFC/EL and `0 J/kg` — never NaN — for zero CAPE/CIN, and tephpy passes both
  through, documented per `SoundingIndices` field. EL can be NaN while
  CAPE > 0 (the parcel is still buoyant at the profile top). A profile topping
  out below 500 hPa makes `lifted_index` NaN *with* a MetPy `UserWarning`;
  tephpy suppresses that specific warning at the call site and returns the NaN
  field — a meteorological answer that keeps `filterwarnings = ["error"]` test
  suites (including tephpy's own) green. Interior NaN gaps in
  temperature/dewpoint pass through to MetPy, which tolerates them.
- Reader failures (network, unrecognised station, malformed archive) → `TephpyIOError`
  with the upstream response summarised.
- The shared hierarchy lives in public `tephpy/exceptions.py` (users catch these):
  `TephpyError` at the root; `TephpyUnitsError`; `TephpyValidationError` carrying
  `levels: tuple[int, ...]` of offending indices, specialized by
  `NonMonotonicPressureError` and `DewpointExceedsTemperatureError` (Plan 4),
  `MissingDataError` — a sounding lacking the field an operation needs, e.g.
  dewpoint for parcel analysis; Plan 6's `plot_barbs` reuses it for absent
  wind — and `ProfileTooShortError` — the profile tops out at or below the
  LCL the path would use (the corrected one when a correction is requested),
  so no moist ascent exists; `parcel_path` and `indices` both raise it, since
  every parcel-derived field would be meaningless (both exceptions Plan 5).
  Plan 6 adds `TephpyIOError`.

## 7. Testing

- **Transforms (verify-first, tephi as oracle):** each function is derived from the
  published construction and challenged per case rather than ported on trust —
  (1) hypothesis round-trip property tests ((p,T) → (x,y) → (p,T) ≡ identity) over the
  physical domain; (2) analytic fixed points whose derivations are recorded alongside
  the test; (3) the isotherm ⊥ dry-adiabat invariant asserted directly in display
  space; (4) cross-checks against recorded tephi outputs for the same inputs, within
  tolerance. Disagreement with the oracle triggers investigation; first principles and
  documented convention win, and divergences are recorded. Attribution attaches only
  where tephi artifacts are actually copied (per case, via a NOTICE file if needed).
- **Plotting:** image-baseline tests via pytest-mpl (small in-repo PNGs,
  tolerance-tuned) for each isopleth family, profiles, barbs, shading, and the
  composed §4 figure. Deliberately not tephi's external image-hash repo, which is a
  contributor-hostile maintenance burden. Curved-family geometry is additionally
  cross-checked against recorded tephi outputs *informationally* — MetPy's and
  tephi's moist-thermo formulations differ, so divergences are investigated and
  documented, not forced to zero.
- **Calc:** test composition, not thermodynamics — parcel path passes through
  Normand's point; `indices()` fields equal direct `metpy.calc` calls on the same
  profile (the uncorrected surface-parcel default; corrected and mixed-layer runs
  assert against the hand-built parcel curve fed to the generic functions); the
  −25 mb correction applies only when requested. One integration test
  against a published worked example with known CAPE/LCL.
- **IO:** recorded-fixture tests (no live network in CI).

## 8. Engineering standards (geovista as the minimum bar)

geovista is the reference for how this repo is built, tested, documented, and released.
tephpy mirrors it, deviating only where tephpy's matplotlib nature, greenfield status, or a
deliberate documentation-UX preference makes a different choice better (those deviations are
called out explicitly).

### 8.1 Packaging and layout

- `src/tephpy/` layout; single `pyproject.toml`; `py.typed` shipped.
- Build backend **`setuptools` + `setuptools_scm`** (`version_scheme = "release-branch-semver"`,
  `local_scheme = "dirty-tag"`, `write_to = "src/tephpy/_version.py"`), matching geovista.
  `.git_archival.txt` + `.gitattributes export-subst` for archive versioning; `MANIFEST.in`
  + `check-manifest` in CI.
- Runtime dependencies: matplotlib, numpy, pint, metpy, pandas, xarray —
  pandas/xarray declared directly because the `Sounding` constructors' public API
  consumes their types (item 9); MetPy already requires both, so the declaration
  adds no install weight. scipy was declared speculatively and dropped in Plan 5
  when no direct consumer materialized (item 14; MetPy keeps it transitively).
  All are conda-forge packages, so pixi resolves them cleanly.
- `requirements/` split mirrors geovista: `pypi-core.txt` + `pypi-optional-{docs,test,devs}.txt`
  feeding `[tool.setuptools.dynamic]`, so PyPI extras and pixi features stay in sync.

### 8.2 pixi-led workflow (leading tool)

pixi is the primary interface for environments, tasks, and CI, configured in
`[tool.pixi.*]` within `pyproject.toml` (no standalone `pixi.toml`).

- **Platforms:** `linux-64` only — the initial platform support, matching geovista.
  tephpy is pure matplotlib with no headless-GL constraint, so it is portable in
  principle; widening to `osx-arm64`, `osx-64`, and `win-64` is a deliberate future
  expansion (revisited once the package has domain functionality), not an omission.
- **Features:** `test`, `docs`, `devs`, plus per-Python `py312`/`py313`/`py314`.
- **Environments / solve-groups:** a `default` group (pinned to the latest supported
  Python, currently 3.14) and per-Python groups (`py312`, `py313`, `py314`), each
  composing `test`/`docs`/`devs` — the geovista pattern.
- **Tasks** (pixi `[tool.pixi.feature.*.tasks]`): `tests` / `tests-clean`, `docs` (build),
  `serve-html`, `doctest`, `lint` (pre-commit run). Matplotlib image baselines are
  regenerated via a `baselines` task (pytest-mpl `--mpl-generate-path`); `tests-clean`
  removes pytest-mpl and coverage artifacts.
- **Lockfile:** `pixi.lock` committed; `.gitattributes` marks it
  `merge=binary linguist-generated=true`; `check-added-large-files` excludes it. All CI and
  RTD invocations use `pixi run --frozen`.

### 8.3 SPEC 0 support policy

- Follows [Scientific Python SPEC 0](https://scientific-python.org/specs/spec-0000/):
  Python **3.12, 3.13, and 3.14** at launch — the full SPEC 0 window as of 2026-07
  (3.11 is outside it). Dependency minimums tracked to the SPEC 0 schedule; the support
  window is revisited at implementation time and on each SPEC 0 rotation.
- Enforced by: README SPEC 0 badge, a docs statement in the developer/packaging guide, the
  CI Python matrix (`py312`/`py313`/`py314`), the per-Python pixi solve-groups, and the
  `sp-repo-review` pre-commit hook.

### 8.4 Code quality (pre-commit + lint + types)

- **Ruff** as linter + formatter: `select = ["ALL"]` with a curated ignore list (the
  geovista set, trimmed to tephpy), numpy docstring convention, isort with
  `required-imports = ["from __future__ import annotations"]`, and **`CPY001` copyright-header
  enforcement** (every source file carries the 4-line BSD header with tephpy's notice regex).
- **mypy `strict`** over `src/tephpy`, `warn_unreachable = true`. The numeric core
  (`transforms`, `calc`) must be clean with no per-module relaxations.
- **numpydoc validation** (same rule-set exceptions as geovista) — all public API carries
  numpy-style docstrings.
- **Pre-commit hooks** (mirroring geovista, same `ci:` block — `autofix_prs: false`,
  weekly `autoupdate`): `validate-pyproject`, `blacken-docs`, `ruff-check` (`--fix`) +
  `ruff-format`, `codespell`, `mypy`, `numpydoc-validation`, the `pre-commit-hooks` battery
  (check-ast/-toml/-yaml, end-of-file-fixer, trailing-whitespace, no-commit-to-branch,
  check-added-large-files, …), `pygrep-hooks`, `check-jsonschema` (dependabot / workflows /
  readthedocs), `sp-repo-review`, `taplo-format`, `sphinx-lint`, and `zizmor` (GitHub Actions
  security audit).

### 8.5 Testing

- **pytest** (`--strict-config --strict-markers --import-mode=importlib`, `xfail_strict`,
  `filterwarnings = ["error", …]`) + **hypothesis** + **pytest-cov** + **codecov** (project
  `target: auto`, `threshold: 5%`, patch off).
- **Test tree mirrors the package** — `tests/` reproduces the `src/tephpy` layout:
  tests for top-level modules live at the `tests/` root (`test_transforms.py`
  through `test_sounding.py` today; `test_calc.py` lands with Plan 5)
  and each subpackage gets a matching directory (`tests/plotting/` today;
  `tests/io/` when that layer lands). New test modules are placed at the level of
  the module they exercise. Shared `tests/fixtures/` and `tests/baseline/` stay at
  the root.
- **Image baselines via pytest-mpl** *(deviation: geovista uses pytest-pyvista for VTK
  scenes; pytest-mpl is the matplotlib equivalent)* — small tolerance-tuned PNGs in-repo for
  each isopleth family, profiles, barbs, shading, and the composed §4 figure.
- Test content per §7 (transforms round-trips, calc composition against `metpy.calc`,
  recorded-fixture IO tests, one worked-example integration test).

### 8.6 Documentation — Diátaxis

- **Sphinx** on **`pydata-sphinx-theme`** *(deviation: geovista uses `sphinx-book-theme`;
  tephpy prefers the pydata theme's top-navbar + section layout for an API-reference-heavy
  scientific library)*, sources under `docs/src/`.
- Four Diátaxis quadrants as real directories with landing `sphinx-design` grid cards:
  `tutorials/` (myst-nb notebooks), `howtos/`, `explanation/` (tephigram theory, the
  T–ln θ construction, parcel/Normand's-point derivations), `reference/` (autoapi API +
  glossary — see "Glossary" below).
- Extensions per geovista: **`sphinx-autoapi`** (API reference generated from `src/`),
  **`numpydoc`**, **`myst-nb`**, **`sphinx-gallery`** (one example per identified use case,
  scraped from `src/tephpy/examples`), `sphinx-design`, `sphinx-copybutton`,
  `sphinx-togglebutton`, `sphinxcontrib-bibtex` (cited meteorology references), `sphinx-tags`.
- **Changelog:** **towncrier** news fragments in `changelog/<PR>.<type>.rst` (same type
  taxonomy as geovista), rendered live via `sphinx_changelog`; assembled into `CHANGELOG.rst`
  at release. A `ci-changelog` check enforces a fragment per PR (escape hatch: `skip-changelog`
  label).
- **ReadTheDocs** versioned hosting, built through `pixi run --frozen --environment docs`.

**Title style.** All hand-authored page and section titles follow Chicago Manual of Style
headline style: capitalize the first and last words and all major words; lowercase articles
(a/an/the), coordinating conjunctions (and/but/or/nor/for/so/yet), prepositions, and the
infinitive "to". Hyphenated compounds capitalize both significant elements ("Wet-Bulb
Potential Temperature", "How-To Guides") while preserving a technical token's literal case
("Skew-T"). Documented exceptions — literal case is preserved even at the start or end of a
title:

- Code and API identifiers, filenames, config keys, CLI commands, env vars, and paths
  (`plot_sounding`, `TephigramAxes`, `pyproject.toml`).
- Project/library names in their own canonical casing (matplotlib, numpy, pint, metpy, pixi,
  tephpy); where such a name would otherwise lead a title, reword rather than re-case it.
- Acronyms, initialisms, and scientific symbols (CAPE, CIN, LCL, WMO, SPEC 0, θ, "T–ln θ").

Fully exempt from the rule: sphinx-autoapi-generated API pages (titles are object names),
numpydoc section headers ("Parameters", "Returns", …), towncrier changelog category and
fragment titles, and anything that is a full sentence — figure captions, admonition body
text, tooltips, alt text, and docstring summary lines — which use sentence case. Bibliography
entries reproduce each source's published title. Enforced by a developer-docs review
checklist; an optional, **non-blocking** `titlecase` wordlist check (encoding the identifier
and project-name exceptions) may assist over hand-authored `.rst`/`.md` headings, but must not
gate the build given the volume of legitimate exceptions.

**Glossary (reference quadrant).** Built with the Sphinx `glossary` directive and cited in
prose with `:term:`. It exists to make the meteorology legible to the package's actual
audience — scientific software engineers — so its rules are audience-first:

- **Audience.** Definitions are written for software engineers, not meteorologists. Each entry
  gives the concept in one plain sentence, then says how it appears in tephpy — the data it
  involves, its units, and the API type or argument that carries it (e.g. "*Sounding* — a
  vertical profile of atmospheric measurements; in tephpy the `Sounding` dataclass holding
  pressure/temperature/dewpoint arrays as pint quantities"). Deeper physics is linked to the
  Explanation quadrant, not derived inline. No thermodynamics background is assumed.
- **What earns an entry.** Domain jargon and project coinages an engineer would not already
  know: tephigram, sounding, radiosonde, parcel, adiabat (dry/moist), lapse rate
  (DALR/SALR), isopleth, isotherm/isobar/isohume, humidity mixing ratio, potential temperature
  (θ), wet-bulb potential temperature, dewpoint, LCL/LFC/EL/CAPE/CIN, Normand's point, wind
  barb — plus any term tephpy uses in a specific sense (e.g. "projection" in the matplotlib
  sense versus a map projection; "profile"). Common software terms are not glossed. Every
  acronym gets an entry and is expanded on first use per page.
- **When to cross-reference.** Link the *first* mention of a term per page (or per major
  section on long pages), not every occurrence. Link only in narrative prose
  (tutorials/how-tos/explanation/narrative reference) — never in titles, code blocks, API
  signatures, or admonition labels. Within a glossary definition, link *related* terms but
  never the term itself. Keep one canonical spelling per concept, with `:term:` aliases for
  plural and variant forms.
- **Sourcing.** An entry may cite an authoritative external reference (e.g. the AMS *Glossary
  of Meteorology*, Met Office) via `sphinxcontrib-bibtex`, but the definition must stand
  alone without following the link.

### 8.7 CI/CD (GitHub Actions)

All workflows: SHA-pinned actions, `permissions: {}` default, `persist-credentials: false`,
`concurrency` cancel-in-progress, pixi via `prefix-dev/setup-pixi` with `frozen: true`.

- **v1 core gates:** `ci-tests` (matrix `py312`/`py313`/`py314` on `linux-64`,
  coverage → codecov),
  `ci-docs` (build + doctest), `ci-wheels` (build sdist/wheel, test in pixi envs, publish to
  Test PyPI on main and PyPI on `v*` tags via **Trusted Publishing OIDC**), `ci-changelog`,
  `ci-citation` (validate `CITATION.cff`), **CodeQL**, pre-commit.ci, dependabot
  (github-actions + pip, grouped).
- **Fast-follow (documented, not built at v1):** `ci-locks` (weekly lockfile-update bot),
  `ci-tests-lock` (daily fresh-resolve canary), `ci-tests-pypi` (daily pip-only install
  canary), `ci-linkcheck`, `ci-stale`, `ci-first-contribution`, and a JOSS paper build. The
  spec records these so the gap is a deliberate schedule, not an omission.

### 8.8 Repo hygiene and community files

`CITATION.cff` (validated in CI), `codecov.yml`, `.github/dependabot.yml`,
`CODE_OF_CONDUCT.md` (Contributor Covenant), `CONTRIBUTING.md` (points at the developer
docs), `SECURITY.md`, issue/PR templates, `.github/labeler.yml` (incl. a `spec-0` label
rule), `CODEOWNERS`, and per-directory `AGENTS.md` files (root, `docs/`, `tests/`). SemVer
with a 0.x honesty period.

## 9. v1 scope

Everything in §1 items 1–3 and the core of item 4: full diagram, profiles, barbs,
multi-sounding overlay + anchoring, parcel path, Normand's point, CAPE/CIN with
shading, LCL/LFC/EL, θw, lifted index, indices panel, Wyoming/IGRA readers, vector
output. Documentation ships all four Diátaxis quadrants with a seeded glossary (§8.6)
covering the domain terms above.

### Non-goals for v1 (decisions, not omissions — stated in the README)

- No TEMP (TTAA/TTBB) or BUFR decoding — recipe docs point at eccodes.
- No skew-T projection — MetPy owns that space.
- No hodograph — MetPy's `Hodograph` composes alongside; a gallery example shows it.
- No GUI or interactive dashboard.
- No fog-point or layer-cloud constructions (v1.x candidates).
- No aviation overlays (icing, MINTRA contrail curves) — flagged open question below.

## 10. Plan roadmap

Seven plans deliver the v1 scope (§9). Each plan gets its own spec-derived implementation
plan in `docs/superpowers/plans/`, and a plan is executed and merged before any plan that
*depends on it* is written. The dependencies form a partial order, not a chain: Plans 5
and 6 are mutually independent and may proceed in parallel once Plan 4 has merged. The
ordering follows the §3 layering (`transforms` ← `plotting` ← (`calc`, `sounding`, `io`)):
geometry first, then the drawing machinery, then the data model, then the analysis and
ingest layers above them. (`calc` itself stays headless per §3 — its pairing with shading
and the indices panel in Plan 5 is delivery convenience, not an import dependency.)

| # | Plan | Scope (spec §) | Depends on | Status |
|---|------|----------------|------------|--------|
| 1 | Foundation & scaffolding | §8 end to end: packaging, pixi, lint/type/test tooling, docs skeleton, CI core gates (residual deferrals: item 15 below) | — | ✅ complete (PR #1; SPEC 0 / platform updates PR #4, #5) |
| 2 | Transforms & the tephigram projection | §3.1: T–ln θ math derived from published sources with tephi as oracle; minimal `TephigramAxes` + `"tephigram"` registration in `plotting/axes.py`; seeds `_constants` (MA, θ reference pressure, default extents); transform tests per §7; wheel-install smoke test in `ci-wheels` (item 15) | 1 | ✅ complete (PR #9) |
| 3 | Isopleth plotting | §3.2 grid + five isopleth families as zoom-aware artists, accessor methods, `set_extent`; §3.5 `_constants` + `tephpy.config`; pytest-mpl infrastructure + isopleth baselines (§8.5); vector-output smoke test (§9 "vector output" — PDF/SVG `savefig` of the first real diagram) | 2 | ✅ complete (PR #15) |
| 4 | Sounding data model & profile plotting | §3.4 `Sounding` dataclass (validation §6, constructors); the §5 units machinery incl. `TephpyUnitsError` and the shared exception module; `plot_profile` (quantities path), `plot_sounding`, multi-sounding overlay + legends (§1 item 4); profile image baselines | 3 | ✅ complete (PR #19) |
| 5 | Thermodynamic analysis | §3.3 `calc`: `parcel_path` (surface + mixed-layer parcels, −25 mb correction), `normand_point`, `indices`; the `Profile` type + its `plot_profile` overload (§3.2); analysis-time §6 errors (`MissingDataError`, `ProfileTooShortError`); `shade_cape`/`shade_cin`, `annotate_indices`; shading baselines; worked-example integration test (§7); drop the scipy declaration (§8.1, item 14) | 3, 4 | **next** |
| 6 | Wind barbs & data ingest | §3.2 `plot_barbs` (right-hand gutter staff, Met Office symbology); §3.4 `io` (`wyoming`, `igra`) with recorded-fixture tests; `TephpyIOError` (§6); barb baselines | 3, 4 | **next** |
| 7 | Examples gallery & documentation completion | §8.6: sphinx-gallery examples (one per §1 use case, incl. the hodograph composition example from §9), `src/tephpy/examples`, tutorials/how-tos/explanation content, glossary completion, sphinx-tags, doctest task + CI doctest run; composed §4-figure baseline (§7 — needs the union of Plans 5 and 6); README non-goals statement and eccodes recipe how-to (§9) | 2–6 | |

Cross-cutting rules (apply to every plan rather than one row):

- **Image baselines ship with their feature.** §7/§8.5 enumerate baselines for the
  isopleth families, profiles, shading, barbs, and the composed §4 figure; each lands in
  the plan that builds the feature (3, 4, 5, 6, and 7 respectively, as tabled above).
- **Glossary entries ship with their terms.** The docs build is fail-on-warning, so a
  `:term:` reference written in Plan N breaks the build unless Plan N seeds the entry;
  "glossary completion" in Plan 7 is a sweep, not the sole delivery.
- **`_constants` accretes per feature.** Plan 2 seeded the module; Plan 3 establishes
  `tephpy.config` over it; later plans add their own conventions (e.g. gutter width
  arrives with Plan 6's barbs).

Outside the roadmap:

- The §8.7 fast-follow CI bots (lockfile updates, resolve/pip canaries, linkcheck, stale,
  first-contribution, JOSS build) are post-v1 continuous work, adopted on need rather than
  assigned to a plan.
- Release execution — towncrier assembly into `CHANGELOG.rst`, the `v0.x` tag that
  triggers PyPI Trusted Publishing, RTD version activation, `CITATION.cff` release
  metadata — follows Plan 7 as release ops, not a plan.
- Service provisioning is operational, not planned. Test PyPI Trusted Publishing,
  codecov, and pre-commit.ci are verified live (green on `main` as of 2026-07-23); the
  production PyPI Trusted Publisher (first exercised by a `v*` tag), the RTD project, and
  the GitHub Discussions link in the issue templates remain to be verified.

### Assumptions and open decisions

Enumerated so they are visible decisions, not silent drift. Items 1–2 are decisions this
roadmap makes; the remainder are open questions assigned to the plan that must answer
them, ordered by owning plan.

1. **The Plan 4–6 slicing is inferred, not inherited.** Only Plans 1–3 and 7 were anchored
   in writing when Plan 1 shipped ("Plan 3" for image tests, "Plan 7" for the gallery).
   The split above keeps one subsystem per plan along the §3 layering; viable alternatives
   (barbs inside Plan 4; `io` as its own plan; examples accreting per-plan instead of
   batching in Plan 7) were consciously not taken.
2. **`Profile` is defined in Plan 5 but referenced by Plan 4.** §3.2 says `plot_profile`
   accepts pint quantities *or* a `Profile`; Plan 4 ships the quantities signature, and
   Plan 5 adds the `Profile` overload together with `calc.parcel_path`. *Resolved
   2026-07-26:* `Profile` is a frozen dataclass in `calc` (§3.3); the overload
   dispatches by duck-typing so `plotting` never imports `calc` (§3.2).
3. **Plan 2 — the TephigramAxes seam.** *Resolved 2026-07-23:* the `"tephigram"`
   projection and a minimal `TephigramAxes` live in `plotting/axes.py` from Plan 2
   (Plan 3 extends the same class in place); `transforms.py` stays pure numpy math.
   §3.1 updated accordingly.
4. **Plan 2 — units at the transforms boundary.** *Resolved 2026-07-23:* `transforms` is
   the documented exemption to §5 — bare numpy arrays in diagram-native units (hPa/°C),
   because matplotlib's per-draw pipeline consumes bare arrays; every layer above
   converts before calling down. §5 updated accordingly.
5. **Plan 2 — tephi provenance and attribution.** *Resolved 2026-07-23:* verify-first
   stance — derive each function from the published sources and challenge it per case
   (§7's four-layer battery), with tephi as a recorded oracle rather than a source to
   copy. Attribution attaches only to artifacts actually copied, per case, via a NOTICE
   file if needed. The same stance applies to Plan 3's locator/refresh reimplementation.
6. **Plan 3 — config object and accessor naming.** The §3.5 `tephpy.rcparams`-style object
   is named but not designed. §3.2 names accessors for only three of the five isopleth
   families, and the spec alternates between "saturated" and "wet" adiabats — pick
   canonical names (the glossary rule: one spelling per concept). *Resolved
   2026-07-24:* the canonical family name is **moist adiabat** — the AMS Glossary
   headword and MetPy's own vocabulary — with saturation/saturated/wet adiabat as
   glossary aliases; the five accessors are `isotherms`/`isobars`/`dry_adiabats`/
   `moist_adiabats`/`mixing_ratios`; the config object is the typed `tephpy.config`
   singleton (§3.5). The fixed-extents API is `set_extent` — the earlier `set_anchor`
   collided with matplotlib's own `Axes.set_anchor` (`DEFAULT_ANCHOR` renames to
   `DEFAULT_EXTENT`). §1/§3.2/§3.5/§4 updated accordingly.
7. **Plan 3 — side-of-axes layout seam.** The barb gutter (Plan 6) and the indices panel
   (Plan 5) both need space beside the diagram; Plan 3 decides whether the axes pre-builds
   that layout or each consumer manages its own. *Resolved 2026-07-24:* decide the
   contract, build later — §3.2 fixes the mechanism (`axes_grid1` divider) and the
   right-side inside-out ordering (barb gutter, then indices panel); no layout code
   ships until Plans 5/6 consume it.
8. **Plan 4 — Sounding contract details.** Label/legend format (§4 hints
   `"03808 2026-07-21 12Z"`), station/time optionality (§3.4 states requiredness only for
   the data arrays), and how forecast-vs-observed overlays of the same station/time stay
   distinguishable in a legend. *Resolved 2026-07-25:* station and time are optional
   metadata — ad-hoc arrays plot without ceremony, operational users get comparable
   legends for free. `label` derives as `"03808 2026-07-21 12Z"` when both are present,
   an explicit `label=` always wins, and with neither there is no legend entry.
   Forecast-vs-observed distinguishability is the label override's job — no dedicated
   field. §3.2/§3.4 updated accordingly.
9. **Plan 4 — pandas/xarray dependency status.** `from_dataframe`/`from_dataset` (§3.4)
   and the §2 ingest decision need pandas/xarray, but §8.1's runtime list omits them
   (today they arrive transitively via MetPy). Decide: direct declaration, optional
   extra, or typing-only treatment. *Resolved 2026-07-25:* declared directly — the
   constructors' public API consumes pandas/xarray types, so leaning on MetPy's
   transitive guarantee would be a silent contract, and the declaration adds no install
   weight. Imported function-locally inside the constructors to keep `import tephpy`
   light. §8.1 updated accordingly. *Refined by Plan 4 (PR #19):* the shipped
   constructors are duck-typed over the objects handed to them, so no runtime
   pandas/xarray import exists at all — annotations are `TYPE_CHECKING`-only, and
   the Plan 4 subprocess test enforces it.
10. **Plan 4/5 — top-level namespace policy.** §4 requires `tephpy.calc.parcel_path` to
    work after `import tephpy`, implying eager subpackage import (and MetPy's import cost)
    or lazy loading; also which names (e.g. `Sounding`) re-export at top level. Plan 3
    keeps MetPy behind function-local imports in the isopleth builders, leaving this
    item open; candidate mechanism: scientific-python `lazy-loader` (SPEC 1), with
    PEP 810 explicit lazy imports as the native successor once the SPEC 0 floor
    reaches Python 3.15. *Plan 4 slice resolved 2026-07-25:* `Sounding` re-exports
    eagerly at the top level — cheap because `sounding.py` keeps MetPy/pandas/xarray
    imports function-local. The lazy-loading mechanism decision stays with Plan 5,
    where `calc` makes the import cost real. *Resolved 2026-07-26:* no lazy-loading
    machinery at all. `calc.py` adds no heavy module-level imports — its internal
    `transforms`/`sounding` imports are cheap by construction, and every
    `metpy.calc` call sites its import function-locally (the idiom the
    import-cost guard test polices) — so `calc` re-exports eagerly alongside
    `Sounding` and `tephpy.calc.parcel_path` works per §4 at no import cost.
    `lazy-loader`/PEP 810 are not adopted; Plan 6 applies the same pattern to `io`.
11. **Plan 5 — MetPy behaviour verification.** §6 asserts NaN pass-through, but MetPy
    returns 0 (not NaN) for zero CAPE and warns on some degenerate profiles — and pytest's
    `filterwarnings = ["error"]` turns those warnings into failures. Verify the §6
    contract and the availability of `wet_bulb_potential_temperature`/`lifted_index`/
    `mixed_parcel` against the pinned floor (`metpy>=1.6`), adjusting §6 or the pin.
    *Resolved 2026-07-26:* verified empirically against the locked metpy 1.7.1 (the
    floor stays `>=1.6`; all three names exist there per the MetPy release history).
    All fourteen functions the design needs exist. Zero CAPE/CIN returns `0 J/kg`,
    never NaN; LFC/EL return NaN quantities; EL can be NaN while CAPE > 0. Warning
    tripwires: duplicate pressure levels (unreachable — `Sounding` enforces strict
    monotonicity) and out-of-bounds interpolation from `lifted_index` on profiles
    topping out below 500 hPa (suppressed at the call site, returning the NaN
    field). §6 amended accordingly. The floor-vs-verified gap is explicit: the
    Plan 5 implementation plan verifies the §6 semantics (not just name
    availability) against a `metpy==1.6.*` resolve and raises the floor if
    they diverge.
12. **Plan 5 — "layer highlights".** The §3 tree comment on `shading.py` names layer
    highlights, but no API, §9 scope item, or plan covers them; treated as not-in-v1
    unless Plan 5's design deliberately includes them. *Resolved 2026-07-26:* not in
    v1 — Plan 5 ships `shade_cape`/`shade_cin` only and the §3 tree comment is
    corrected; layer highlights remain a v1.x candidate.
13. **Plans 2/5/6 — third-party data provenance.** Any tephi artifacts actually copied
    (item 5), the §7
    published worked example (which publication, and is its data redistributable?), and
    recorded Wyoming/IGRA fixtures all embed external data; each owning plan records
    source, capture method, and attribution. *Plan 5 slice:* the worked example's
    primary candidate is a CAPE/LCL example from Stull, *Practical Meteorology*
    (CC BY-NC-SA 4.0 — a handful of fixture numbers with full citation); the final
    source, capture method, and attribution are pinned in the Plan 5 implementation
    plan and recorded alongside the fixture. Redistribution stance: the fixture is
    a few cited numeric values used as facts, not licensed expression; if that
    comfort fails for the pinned source, fall back to a public-domain (NWS/NOAA)
    profile.
14. **scipy is declared but unowned.** §8.1 lists scipy as a runtime dependency, yet no §3
    module names it (plausible first consumers: interpolation in Plan 2 or Plan 5). If
    Plan 5 completes without it, drop the dependency. *Resolved 2026-07-26:* Plan 5's
    design needs no direct scipy (the shading interpolation is plain numpy; MetPy
    keeps scipy transitively), and `src/tephpy` has no scipy import today — the
    direct declaration is dropped in Plan 5 (§8.1 updated; the implementation plan
    also removes scipy from the declared-dependencies tuple in
    `tests/test_import.py`).
15. **Residual Plan 1 deferrals**, re-homed: sphinx-tags (§8.6) → Plan 7; `doctest` task +
    `ci-docs` doctest run (§8.2/§8.7) → Plan 7; `tests-clean` task (§8.2) → reconciled
    in Plan 3 (decided 2026-07-24: `tests-clean` removes test artifacts; a `baselines`
    task regenerates the pytest-mpl baselines);
    wheel-install smoke test → Plan 2 (decided 2026-07-23); check-manifest CI gate →
    revisit once the wheel carries domain code; the §8.3 packaging-guide SPEC 0 docs
    statement → Plan 7.

## 11. Open questions (carried from research)

- Which aviation-specific overlays (icing layers, MINTRA) do operational users
  actually need built in, versus composing themselves?
- Which named stability indices beyond the v1 set (Showalter, K-index, Total Totals)
  are worth wrapping, given all are one-line `metpy.calc` calls for users?
- Whether BUFR ingest demand justifies an optional `tephpy[bufr]` extra later.

## 12. References

- Met Office Factsheet 13 — Upper air observations (2023)
- Stull, *Practical Meteorology*, ch. 5 (thermo-diagram construction, stability)
- University of Reading tephigram teaching notes
- COMET/UCAR tephigram training module; NWS and HKO operational guides
- SciTools/tephi 0.4.0.dev0 source (transform and isopleth-artist design)
