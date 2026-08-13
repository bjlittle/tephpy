# tephpy — design specification

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. tephpy's source cites it by section — you will find `spec §6` and the like
> throughout `src/` — so these sections *are* the reasoning behind what the code does, and
> where the two ever diverge it is the specification that gets corrected. Read it as current.

- **Date:** 2026-07-22 (originated; maintained since)
- **Status:** living design specification, implemented incrementally by the plans in
  [`docs/src/developer/plans/`](https://github.com/bjlittle/tephpy/tree/main/docs/src/developer/plans)
- **License:** BSD-3-Clause (repo already carries it)
- **Repository:** https://github.com/bjlittle/tephpy (PyPI name `tephpy` verified free on 2026-07-22)
- **Engineering standards baseline:** [bjlittle/geovista](https://github.com/bjlittle/geovista)
  is the minimum bar — pixi-led workflow, SPEC 0 support window, Diátaxis docs, and the
  geovista pre-commit/CI conventions. See §8.

(spec-1)=
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

(spec-2)=
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

(spec-3)=
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

(spec-3-1)=
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
x/y ticks hidden by default — meaningful labelling arrives with Plan 3's isopleths, and
§3.2's edge labelling later reclaims those axes for a family that asks. Out-of-domain
input (p ≤ 0, unphysical T) propagates NaN rather than raising: exception-carrying
validation belongs to the quantified boundaries above (§6). Plan 2 also seeds
`_constants.py` (MA, the θ reference pressure, default extents) per §3.5's
no-hard-coding rule. Oracle fixtures are generated by running tephi 0.4.0.post0 and
recording input/output pairs with a provenance header (generation script and tephi
version) — generated outputs, not copied source.

(spec-3-2)=
### 3.2 `plotting`

> **Extended by a child specification.** Branding — `tephpy.plotting.add_logo`, which places
> the tephpy logo on a figure or an axes — is specified separately in
> [`2026-08-01-add-logo-design.md`](2026-08-01-add-logo-design.md), which inherits this
> document's error-handling (§6), testing (§7) and engineering-standards (§8) rules unchanged.

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
- Isopleth labels place **inline or on the diagram's edges** — the declutter control,
  and the existing `labels=` widened rather than joined by a new option, so the API
  grows no names. A placement is `True` (every member labelled inline — the default,
  unchanged), `False` (none), or an edge name `"bottom"`/`"top"`/`"left"`/`"right"`,
  singly or as a tuple; a bare string and a one-tuple are identical, and a family may
  claim several edges. The rule is one sentence: **listed edges label the members that
  reach them; every member left over is labelled inline.** So
  `ax.isobars(labels=("bottom", "left"))` builds the printed chart's pressure scale, and
  `ax.isotherms(labels=("bottom", "left"))` labels the warm isotherms below the frame and
  the cold ones beside it (the coverage table below).
  Deliberate gaps are not expressible: thinning a family is
  `values`/`interval`'s job, and label placement must not become a second member filter.
  A member meeting a listed edge more than once — a curved isobar leaving and re-entering
  — is ticked at each crossing, and an invisible family (`visible=False`) labels nothing
  and holds no edge.
  Edge labels are **native matplotlib ticks**, not drawn text. Bottom and left claim the
  axes' own `xaxis`/`yaxis` (hidden by default per §3.1); top and right claim a lazily
  created `secondary_xaxis`/`secondary_yaxis` with identity functions — verified
  2026-07-29 to track both the equal-aspect shrunk position and the `axes_grid1` divider.
  Each claimed edge takes a locator/formatter pair: the locator intersects the family's
  currently selected members with the edge segment (the free function `edge_crossings`
  in `isopleths.py` — the module's pure-builder pattern, headlessly testable against the
  analytic case, an isotherm crossing `y = y0` at exactly `x = y0 + 2T`), and the
  formatter reads the member values cached alongside those positions, formatted
  `"{value:g}"` as inline labels already are — no inverse math, no MetPy, exact for all
  five families. Because matplotlib calls the locator on every draw, pan, zoom, resize
  and `set_extent` stay correct with no new refresh machinery, and a tight-bbox
  `savefig`, `tight_layout`, `tick_params` and `set_xlabel` all work unwrapped. The
  crossings are computed twice per draw — once by the locator, once by the family
  filtering its inline remainder — because tick location and artist drawing have no
  guaranteed ordering; it is pure numpy over ~20 short polylines, and correctness beats
  the cache. A claimed edge also takes an axis title and its tick conventions from
  `_constants`; who owns each of those afterwards is the next bullet. **One family per
  edge:** two claimants raise `TypeError` naming both and the edge, checked by the axes
  — which owns all five families and funnels both the accessor and creation paths — so a
  `tephpy.config` conflict surfaces at axes creation rather than at first draw. An
  unknown placement raises `TypeError` naming it and the valid set (the `format_coord`
  style), the bare-string check preventing a silent per-character iteration.
  `TephigramAxes.clear` drops the cached secondary axes alongside its existing
  xaxis/yaxis re-hiding. Not tephi's design: tephi labels inline only.
- **A claimed edge's ticks are stock matplotlib and yours to style.** tephpy stamps its
  tick conventions on an edge axis **once, when that axis is created** — `LABEL_FONTSIZE`,
  the `_constants` tick length and pad, the bottom/left ticks-position pin (the classic
  style mirrors ticks onto the opposite edge, where another family may live), and the
  gridline suppression. That moment is `clear()` for the axes' own xaxis/yaxis and the
  lazy build for a top or right secondary. Thereafter tephpy never touches presentation
  again: the only thing a later claim or sync changes is the tick colour, and only when
  the owning family's own colour or alpha changes. Claiming an edge is then pure
  identity — locator, formatter, visibility, colour, title — and releasing it pure
  teardown. The first implementation re-asserted presentation on every sync, so an
  *unrelated* family's resolve silently reverted a user's `tick_params`, and `ax.grid(True)`
  after a claim survived only until the next resolve (both reproduced 2026-07-30).
  Nothing needed re-asserting: the locator holds a live family reference and recomputes on
  every draw. Matplotlib gives no provenance on `set_tick_params`, so the split has to be
  by *when* rather than by *what the user touched*. Tick colour is the exception because it
  is what ties a tick to the line it labels: the axes remembers the owner and the RGBA it
  last applied to each edge and re-applies only on a difference, so restyling the owning
  family reaches its ticks and nothing else does. That memory survives release, making a
  family visibility toggle a true round trip; the owner is part of the key because a bare
  RGBA memory suppresses a *new* owner's claim whenever its colour matches the last one's,
  stranding the ticks in a colour that ties them to nothing (reproduced 2026-07-30). Grid
  suppression lands at axis creation, which is after
  `Axes.clear` reads `rcParams["axes.grid"]`, so a style still cannot smuggle in gridlines
  of constant data-space x or y — but an explicit `ax.grid(True)` is now the user's call.
  `ax.clear()` is the reset.
- **The axis title splits the same way:** its *text* is identity — from `_constants`, one
  per family, `Temperature (°C)` through `Mixing ratio (g kg⁻¹)` — and its *styling* is
  presentation tephpy never touches. The fill-when-empty guard stands unchanged, but it
  now runs only on a first claim, and that alone makes it honest: a user's `set_xlabel`
  still wins whether it precedes or follows the accessor call, and `set_ylabel("")`
  durably means "ticks, no title" rather than reappearing on the next resolve, because no
  later sync looks at the label again. Releasing clears and forgets tephpy's own title
  while leaving a user's replacement alone, so a reclaim stamps afresh, a new owner
  restamps with its own, and the disable holds for the life of the claim. Nothing richer
  is needed — release always forgets, so a first claim never meets a title tephpy still
  remembers writing, and a provenance check could not differ from the guard.
- **`ax.edge_axis(edge)`** is the uniform public handle on all four edges, returning the
  matplotlib `Axis` that draws that edge's ticks, keyed by the same edge vocabulary
  `labels=` uses. Without it, top and right are reachable only through a private
  `_secondary_axes` or an undifferentiated `child_axes` that must be sniffed to tell one
  from the other. An unknown name raises `TypeError` naming it and the valid set (the
  `format_coord` style); an unlabelled edge raises `ValueError` saying so and how to claim
  one, because probing must not materialise a secondary axes nobody is using and an
  unclaimed edge renders nothing to style.
  Releasing a top or right edge **hides** its secondary axes rather than removing it, so a
  held handle stays live and its ticks and title survive a release/reclaim exactly as
  bottom and left do. It is the whole secondary axes that hides, not merely its `Axis`, or
  its spine would keep drawing; a claim correspondingly shows both, since showing the
  container alone would leave an `Axis` the user had hidden drawing no ticks on an edge
  that has just been claimed; an invisible secondary returns `None` from
  `get_tightbbox` and `Axes.clear` empties `child_axes` (both verified 2026-07-30), so the
  persistence costs nothing in layout and `TephigramAxes.clear` still reaps them.
- **Any member of any family can be emphasised.** `emphasis=` on all five accessors and on
  every `tephpy.config` family section maps a member value to a mapping of style overrides
  — `color`, `linewidth`, `linestyle`, `alpha` — and an omitted key falls back to the
  family's own resolved style, so `ax.isotherms(emphasis={0.0: {}})` is the 0 °C isotherm at
  `EMPHASIS_LINEWIDTH` in the family's own ink, while an empty mapping (`emphasis={}`)
  emphasises nothing and is how a `tephpy.config` emphasis is cleared at the accessor. The
  motivating case is the freezing level, which operational practice singles out everywhere
  and no library provides: MetPy's advanced-sounding example hand-rolls it (`# first, we add
  a matplotlib axvline to highlight the 0-degree isotherm`), SHARPpy labels the 0, −20 and
  −30 °C levels in dark blue, and NWS skew-T training treats the 0 °C crossing as a named
  index (FRZ) — all verified 2026-07-30. On a tephigram that isotherm is *slanted*, so the
  `axvline` escape hatch skew-T users rely on does not exist and a tephpy user today has no
  supported way at all; tephi's documented customisation is whole-family and does not cover
  isotherms at all. It is deliberately **not** a "zero isotherm" feature: −20 °C bounds the
  airframe icing band, a mandatory isobar is the same gesture on another family, and one
  option on the shared `LineOptions` beats five special cases. **Nothing is emphasised by
  default** — every other tephpy default cites a printed-chart convention, and the evidence
  found is operational software rather than Factsheet 13, whose published URL now 404s
  (2026-07-30); defaulting it on would be inventing a convention, and flipping that decision
  later is a one-line change. `EMPHASIS_LINEWIDTH` is the single new constant, because
  emphasis defaults to the monochrome printed-chart idiom — same ink, heavier line — so no
  colour convention is invented and the SHARPpy look stays one keyword away. `linestyle` is
  accepted per member though the family has no family-level `linestyle`: dashing is the
  dominant emphasis idiom, and the wider option can follow without conflict. Malformed
  emphasis raises from `configure` inside its existing rollback — a non-mapping, a key that
  will not convert to float, a member value that is not a mapping, or an unknown style key
  all raise `TypeError` naming the family and listing the four accepted keys; a
  non-positive or non-finite `linewidth`, or an `alpha` outside `[0, 1]`, raises
  `ValueError` mirroring the `interval` check. `color` and `linestyle` are left to
  matplotlib, exactly as the family-level `color` already is.
- **Emphasis forces its member to be drawn**, which is what lets it double as the
  reference-line mechanism rather than needing one: `emphasis` joins the geometry keys, its
  keys union into the candidate values the family builds, and the zoom mask forces them
  true, so `emphasis={-12.0: ..., -18.0: ...}` marks the dendritic growth zone's bounds on a
  10 °C ladder that would never select them. The view mask still applies, so an off-screen
  member stays off screen — which is also why a value outside the family's generous
  `_constants` domain is a no-op rather than an error. That no-op is *silent* on the three
  straight/analytic families; on the curved two the builder can complain before the mask
  ever runs — `moist_adiabats(emphasis={500.0: {}})` emits a MetPy `UserWarning` about an
  undefined saturation mixing ratio and `mixing_ratios(emphasis={0.0: {}})` two numpy
  `RuntimeWarning`s (both verified 2026-07-30). The fragility is the builders', not
  emphasis's — `values=[0.0]` does the same without any emphasis — so it is not a
  regression, but it is why the curved families' accessor docstrings pick an in-domain
  example rather than promising a silence they cannot deliver. Because `_selected_members` is
  shared with `_EdgeLocator`, a forced member gets its edge tick for free; the tick's
  *colour* does not follow, since `set_tick_params` is whole-axis and per-`Tick` styling
  would fight the presentation-stamped-once rule above — a documented limitation, and
  emphasis is a per-member gesture where inline labelling is the common case. Draw order
  stays inside the family: `draw` partitions the selected members base-then-emphasised on
  the single existing `LineCollection`, whose `color`, `linewidth` and `linestyle` all
  accept per-segment sequences (verified on matplotlib 3.11.1, 2026-07-30; the declared
  floor is 3.10). `alpha` is the exception: it takes a per-segment sequence within a single
  call but not *across* redraws, because `LineCollection.set_color` calls
  `to_rgba_array(c, self._alpha)` eagerly, so an array-valued `_alpha` left over from the
  previous draw raises the moment the segment count changes — which is every zoom. Emphasis
  alpha is therefore baked into the RGBA 4-tuple and `_alpha` is held at `None` on that
  path; that is load-bearing, not incidental, and "simplifying" it back to a per-segment
  `set_alpha` reintroduces the crash. An emphasised member therefore wins against its own
  family's neighbours, while the families above it still nick it with a 0.5 pt overpaint at
  each crossing — accepted rather than bought off with a sixth axes-owned artist to create,
  sync and tear down. Inline labels take the same per-member style, being per-member `Text`
  already. The one trap: `mixing_ratios` selects by *stride over member index*, not by
  value, so an emphasis-only addition would shift every later index and silently change
  which members the stride picks at every zoom level; the build therefore records which
  members exist only because emphasis asked for them, and the stride mask is computed over
  the canonical members by their canonical position. The resolved mapping is deep-copied
  when it resolves, for the same reason `values` materialises a generator to a tuple: the
  snapshot must not alias a dict the caller can still mutate.
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
- `ax.plot_barbs(snd, *, x=None, minimum_separation=None, **kwargs)` — the
  sounding's wind barbs on a right-hand gutter staff (Met Office symbology:
  flag 50 kt, full barb 10 kt,
  half barb 5 kt, rounded to 5 kt bins), raising `MissingDataError` when the
  sounding has no wind (§6). The staff is drawn by a zoom-aware artist in
  `plotting/barbs.py` (the `isopleths.py` refresh pattern): each draw selects
  the levels whose isobars cross the current view, thins them to the densest
  subset at least a minimum vertical separation apart — zooming in reveals
  more levels — and places each barb at the y where its level's isobar meets
  the diagram's right edge (the printed-form staff convention, where the
  staff's pressure marks sit where the isobars cross it), interpolated along
  the isobar polyline in pure numpy. Wind speed converts to knots; u/v come
  from `metpy.calc.wind_components` (function-local import — the §3.2/§3.3
  one-source-of-truth idiom). Calm levels render as matplotlib's native small
  circle — which is the Met Office calm symbol (verified at plan drafting,
  2026-07-27). `x` positions the staff
  as a fraction across the gutter and `minimum_separation` sets the thinning
  distance in points (both default to their `_constants` value): overlaid
  soundings pick different positions, separations, and a colour — the
  explicit-styles convention profile overlays already use — within one
  fixed-width gutter. Returns the staff artist; matplotlib kwargs pass
  through to the barbs.
  Gutter width and pad, staff position, minimum separation, and the barb
  increments live in `_constants` with their source conventions cited
  (Factsheet 13) — staff position and minimum separation being the two a
  call overrides, the constants supplying their defaults; like profile lines
  and shading, no `tephpy.config` section at v1.
- `ax.shade_cape(snd, parcel)` / `ax.shade_cin(snd, parcel)` — area fills between
  the environment temperature and the parcel path, bounded exactly as MetPy's
  `cape_cin` integrates so the shading always matches the annotated numbers:
  CAPE is the positive-buoyancy region from the LFC to the EL (to the profile
  top when EL is NaN with CAPE > 0, §6), CIN the negative-buoyancy region from
  the parcel start to the LFC. Pure builders in `plotting/shading.py`
  sample both curves onto their merged pressure grid along the drawn
  polylines — the straight segments in tephigram (x, y) space that
  matplotlib draws between profile levels, so the fill closes on the
  plotted lines at every figure scale (a pressure-space interpolation bows
  away from the drawn chords between levels; issue {issue}`42`) — locate the
  crossings where the drawn segments intersect, and return the region's closed
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
  order is position order; Plan 6 makes call order irrelevant rather than
  enforcing it — a later `plot_barbs` relocates the existing panel outside the
  new gutter (the relayout in the layout contract below).
- `ax.set_extent(...)` — fixed extents from ((p, T), (p, T)) corners so successive
  figures are directly comparable; disables autoscaling so overlays don't drift the
  window. (The cartopy idiom — the earlier `set_anchor` name collided with
  matplotlib's own `Axes.set_anchor`.)
- `ax.format_coord(x, y)` — the interactive cursor readout (the navigation
  toolbar's coordinate text) reports diagram-meaningful values instead of the raw
  rotated data-space (x, y): the cursor position inverts through
  `transforms.temperature_theta_from_xy`, pressure derives via
  `transforms.pressure_from_temperature_theta`, and the configured fields render
  in listed order, e.g. `850 hPa, -4.2 °C, θ 8.6 °C` (whole hPa, one decimal
  for temperatures). Fields name entries in a five-strong registry mirroring the
  isopleth families: `"pressure"`, `"temperature"`, `"theta"` — closed-form, the
  default trio — plus opt-in `"mixing_ratio"` (saturation mixing ratio at the
  point, g/kg, one decimal) and `"theta_w"` (the moist adiabat through the
  point), the latter two via `metpy.calc` with function-local imports (the
  one-source-of-truth idiom above; a user who never lists them never pays for
  them). Selection resolves as instance assignment > `tephpy.config` >
  `_constants`: `config.cursor.fields` is read live on every mouse event — so
  `config.context(cursor={"fields": ...})` scopes cleanly — and full
  customisation stays stock matplotlib: assigning `ax.format_coord = fn`
  shadows the method (documented, not wrapped). Out-of-domain positions (the
  inverse yields NaN) return `""` so the toolbar goes blank rather than showing
  garbage; an unknown field name raises `TypeError` naming it and the valid
  names (the family-`configure` style), surfacing on the first mouse move.
  Headlessly testable — `format_coord` is a plain string-returning method.

Edge coverage decides which pairing suits each family. Measured 2026-07-29 against the
real families at `DEFAULT_EXTENT` (matplotlib 3.11.1) — of the members the zoom ladder
selects, how many reach each edge, and how many reach at least one:

| family | members | bottom | top | left | right | any |
|---|---|---|---|---|---|---|
| isotherms | 19 | 11 | 16 | 8 | 3 | 18 |
| isobars | 19 | 1 | 2 | 18 | 3 | 19 |
| dry adiabats | 35 | 9 | 20 | 7 | 3 | 27 |
| moist adiabats | 21 | 0 | 7 | 1 | 0 | 8 |
| mixing ratios | 8 | 0 | 8 | 1 | 0 | 8 |

No single edge covers a family, which is why placements are a tuple and why the inline
remainder is automatic rather than optional. The pairings the numbers recommend:

- **Isobars `("bottom", "left"), interval=150`** — at the default 50 hPa spacing all 19
  members tick (none doubled, nothing left inline: the left edge carries 150–1000 hPa and
  the bottom edge the 1050 hPa isobar alone), but the left-edge labels crowd; `interval=150`
  gives a legible ~6-label scale. The printed chart's pressure scale.
- **Isotherms `("bottom", "left")`** — 18 of 19, the warm 11 below (−40 to 60 °C) and the
  cold 8 beside (−110 to −40 °C). The two edges are not disjoint: −40 °C passes through
  the corner and is ticked on both, and −120 °C reaches no edge at all and falls to the
  inline remainder. Both rules above, visible in one call.
- **Mixing ratios `"top"`** — 8 of 8, a complete scale from one token.
- **Dry adiabats `("top", "left")`** — 27 of 35; the 8 that reach nothing stay inline.
- **Moist adiabats** — 8 of 21 at best, because they are truncated curves that mostly
  begin and end inside the view. Not an edge family: leave them inline or `labels=False`.

The counts are extent-dependent — `set_extent` changes every one of them — which is
precisely why the crossings are recomputed by the locator on each draw rather than fixed
when the family is built.

Side-of-axes layout contract (decided in Plan 3, built by the consuming plans):
panels beside the diagram are appended with `mpl_toolkits.axes_grid1`'s axes
divider, which tracks the equal-aspect box height — right side, inside-out: Plan 6's
barb gutter, then Plan 5's indices panel. Panel widths join `_constants` with their
plans. All side panels must share **one** cached divider: a second
`make_axes_locatable(self)` call builds a fresh `AxesDivider` and replaces the parent
locator, detaching the earlier panel so it draws over the newcomer. Plan 5 has the
sole panel (`annotate_indices`), so it creates and owns the divider inline; when Plan 6
adds `plot_barbs` it must **reuse** that divider (cache it on the axes and share it
across the side-panel methods), not call `make_axes_locatable` again. (Raised in the
Plan 5 review; deferred here because the two-panel path is only reachable — and
testable — once the barb gutter exists.) *Resolved 2026-07-27 (Plan 6):* the divider
is created once, cached privately on the axes, and shared — `annotate_indices` is
refactored onto it, `plot_barbs` appends the gutter through it, and
`make_axes_locatable` is called exactly once per axes. Call order is made irrelevant
rather than enforced: one relayout helper rebuilds the divider's horizontal stack
(diagram, gutter, indices panel — skipping absent panels) and reassigns every
locator whenever a panel appears, so the inside-out contract holds on every call
path with no panel teardown or re-rendering. (Refined at plan drafting, same day:
axes_grid1's `append_axes` only ever appends to the size stack, so the earlier
remove-and-re-append sketch would leave a stale width slot — a phantom gap;
relayout is the clean mechanism, verified empirically.) The right edge is the one
contested by both features: `BARB_GUTTER_PAD` is 0.1 in, narrower than an 8 pt tick
label, so right-edge isopleth labels would land on the gutter. Rather than forbid the
combination or document a collision, the relayout helper substitutes a wider
`_constants` pad when the right edge carries labels — one lookup in a helper that
already rebuilds the stack on every panel call, and no rule for the user to remember.

(spec-3-3)=
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

(spec-3-4)=
### 3.4 `sounding` + `io`

`Sounding`: a frozen dataclass holding pressure/temperature/dewpoint/wind-speed/
wind-direction arrays as pint quantities. Pressure and temperature are required;
dewpoint and wind are optional (a Sounding without wind plots profiles but raises on
`plot_barbs`; one without dewpoint raises on parcel analysis), and the two wind
fields must arrive together. Inputs are coerced in `__post_init__` — bare arrays
need the §5 `units=` mapping — so a constructed Sounding always holds quantities.

`station` and `time` are optional metadata; `label` is the legend text. An explicit
`label=` stands as-is; otherwise it derives as `"72357 2013-05-20 12Z"` when both
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
`Sounding` objects, so the §6 ingest validation applies to fetched data unchanged;
both keep their network/archive imports function-local (the established idiom,
policed by the import-cost guard test) and `tephpy.io` re-exports eagerly (item 10).

- `wyoming.fetch(station, time, *, timeout=None)` fetches one ascent from the
  University of Wyoming archive over stdlib `urllib` — no new dependency; the
  timeout default lives in `_constants` — and hands the `TEXT:CSV` body to a
  pure, transport-free parser. (`TEXT:CSV` is the post-2024 wsgi interface's
  machine-readable form, bare self-describing CSV; the classic `cgi-bin`
  TEXT:LIST endpoint is gone — probed live 2026-07-27.) The parser reads the
  pressure/temperature/dew-point/wind columns in the header's units (hPa, °C,
  degrees, m/s — the classic knots column no longer exists), blank fields →
  NaN (NaN gaps are data, §3.4), keeps rows only while pressure strictly
  undercuts the running minimum (first occurrence wins; the dense BUFR-era
  ascents must satisfy `Sounding`'s strict monotonicity), and treats an
  entirely-NaN optional field as absent — the wind pair as a unit, so a
  one-sided wind column passes as absent rather than tripping `Sounding`'s
  pairing rule — keeping `MissingDataError`
  meaningful (§6). `station` is the WMO identifier (`"72357"`); `time` is a
  datetime or ISO string, naive read as UTC (the `Sounding` convention).
  Station and time land as metadata, so the legend label derives for free.
  Network failures and HTTP errors — the archive replies 400 "no data at that
  time" / 404 "unknown station" with a one-line plain-text body — raise
  `TephpyIOError` summarising the upstream reply (§6).
- `igra.read(path, *, time=None)` reads one ascent from an IGRA v2 per-station
  file — the as-distributed `.zip` or the extracted `.txt`, sniffed with
  `zipfile.is_zipfile` rather than by suffix. The fixed-width records parse
  with the IGRA sentinels (−9999/−8888) → NaN, dewpoint derived as
  temperature − dewpoint depression, wind converted from tenths of m/s,
  records without a pressure value dropped (`Sounding` requires finite
  pressure), and the same running-minimum monotonicity filter and
  entirely-NaN-optional-field rule as the Wyoming parser applied. `time=`
  selects the ascent and may be omitted only when the file
  holds exactly one sounding (trimmed research subsets, fixtures); an
  ambiguous read raises `TephpyIOError` reporting the file's sounding count
  and time span, an unmatched `time=` reports the nearest ascents (or that
  the file records no nominal launch times), as does malformed input (§6).

(spec-3-5)=
### 3.5 `_constants` + `tephpy.config`

All conventions — 10 °C isotherm interval, 10 mb isobar interval, moist-adiabat
truncation temperature, gutter width, colours — live in `_constants.py` as defaults;
nothing numeric is hard-coded at point of use, and docstrings cite the source
convention (e.g. Met Office Factsheet 13). The mutable runtime layer over them is
`tephpy.config` (`_config.py`): a typed singleton of per-family dataclass sections
plus diagram-wide and cursor sections (e.g. `config.isobars.interval`,
`config.moist_adiabats.truncation`, `config.diagram.extent`,
`config.cursor.fields`), with a `config.context(...)` manager for temporary
overrides. Precedence: accessor kwargs > `tephpy.config` > `_constants`. Config is
read when a family is created or reconfigured; changing it does not retroactively
restyle existing axes (matplotlib rcParams semantics). The cursor readout is the
one exception: `config.cursor` is read live per mouse event (§3.2), so a context
override applies to existing axes for its duration.

(spec-3-6)=
### 3.6 Browser documentation demo

The documentation carries one experimental, entirely client-side tephigram demo. A
reader explicitly launches a lazy-created iframe; only then does it download PyScript
2026.7.3 and Pyodide 314.0.4, install the current checkout's wheel, and render through
matplotlib's WebAgg-derived Pyodide backend. The docs build creates that wheel and stages
it with the application under `docs/_build/browser/`; Sphinx publishes the staging root
through `html_extra_path`. Generated wheels remain build artifacts and are never committed.

The browser runtime has a checked-in lock manifest. MetPy 1.7.1 and Pint 0.25.3, their
resolved pure-Python dependency chain, package hashes, and CDN URLs are exact; compiled
dependencies come from the package lock belonging to the pinned Pyodide runtime. The UI
reports progress throughout installation and exposes a readable, live-region error if any
dependency fails. Chromium is the tested browser; Firefox and Safari are best-effort.

The bundled example plots at startup. A local upload replaces it only after parsing,
`Sounding` construction, and creation of the successor figure succeed, so an invalid file
does not destroy a good plot. Before a successful replacement, the prior figure is closed,
its WebAgg DOM is removed, and its Python callback proxies are destroyed. The resulting
canvas retains matplotlib's pan, zoom, coordinate readout, home/reset, and download tools.
The uploaded filename is both the plot label and title; wind data, when present, is passed
to `plot_barbs`.

The demo CSV contract is deliberately not a package-level reader:

- `pressure_hPa` and `temperature_C` are required.
- `dewpoint_C` is optional.
- `wind_speed_m_s` and `wind_direction_degree` are optional as a pair.
- Blank cells become NaN; an absent optional column becomes `None`.
- Missing or duplicate headers, nonnumeric nonblank cells, empty data, and a one-sided wind
  pair are structural errors. Physical validation remains `Sounding`'s responsibility.

The experiment adds no public Python API. University of Wyoming `wyoming.fetch`, live
archive access, persistent configuration, analysis controls, offline caching, and other
live network data are out of scope. In particular, it does not reverse §9's supported-product
decision against a tephpy GUI or dashboard: this is a documentation example with a small
local-file boundary, not an application surface.

(spec-4)=
## 4. Canonical usage

```python
import matplotlib.pyplot as plt
import tephpy
from tephpy.io import wyoming

snd = wyoming.fetch("72357", "2013-05-20 12:00")  # → Sounding

fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
ax.plot_sounding(snd)  # T + Td, legend "72357 2013-05-20 12Z"
ax.plot_barbs(snd)

parcel = tephpy.calc.parcel_path(snd)
ax.plot_profile(parcel, color="k", linestyle="--")
ax.shade_cape(snd, parcel)
ax.shade_cin(snd, parcel)
ax.annotate_indices(tephpy.calc.indices(snd))

fig.savefig("sounding.pdf")
```

The station/time is deliberate: Norman, Oklahoma on the morning of the 2013
Moore EF5 tornado — a profile with ≈1800 J/kg of CAPE and ≈−270 J/kg of CIN —
so `shade_cape` and `shade_cin` have visible regions to fill and every call in
the example demonstrably renders. A stable profile reduces the shading to
invisible slivers.

Comparing soundings is two `plot_sounding` calls with different styles; `set_extent`
keeps extents identical across figures.

(spec-5)=
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

(spec-6)=
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

(spec-7)=
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
  tolerance-tuned) for each isopleth family, profiles, barbs, shading, the
  printed-chart edge-labelling configuration, member emphasis, and the
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
- **Browser documentation demo:** CPython tests own the CSV boundary and wheel staging;
  a Playwright Chromium test launches the built page, proves the checkout wheel imported
  under the Pyodide backend, exercises the interactive canvas and toolbar, replaces the
  example from a valid local CSV, and confirms an invalid upload reports an accessible
  error without replacing the previous plot. DOM and application state are assertions;
  rendering fidelity remains the responsibility of the existing pytest-mpl baselines.

(spec-8)=
## 8. Engineering standards (geovista as the minimum bar)

geovista is the reference for how this repo is built, tested, documented, and released.
tephpy mirrors it, deviating only where tephpy's matplotlib nature, greenfield status, or a
deliberate documentation-UX preference makes a different choice better (those deviations are
called out explicitly).

(spec-8-1)=
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

(spec-8-2)=
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

(spec-8-3)=
### 8.3 SPEC 0 support policy

- Follows [Scientific Python SPEC 0](https://scientific-python.org/specs/spec-0000/):
  Python **3.12, 3.13, and 3.14** at launch — the full SPEC 0 window as of 2026-07
  (3.11 is outside it). Dependency minimums tracked to the SPEC 0 schedule; the support
  window is revisited at implementation time and on each SPEC 0 rotation.
- Enforced by: README SPEC 0 badge, a docs statement in the developer/packaging guide, the
  CI Python matrix (`py312`/`py313`/`py314`), the per-Python pixi solve-groups, and the
  `sp-repo-review` pre-commit hook.

(spec-8-4)=
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

(spec-8-5)=
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

(spec-8-6)=
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
- The §3.6 browser demo is staged as extra HTML rather than a Sphinx source page. Its
  tutorial launcher is lazy so an ordinary documentation visit downloads no Python
  runtime, and it states both the client-side data boundary and experimental support.

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

(spec-8-7)=
### 8.7 CI/CD (GitHub Actions)

All workflows: SHA-pinned actions, `permissions: {}` default, `persist-credentials: false`,
`concurrency` cancel-in-progress, pixi via `prefix-dev/setup-pixi` with `frozen: true`.

- **v1 core gates:** `ci-tests` (matrix `py312`/`py313`/`py314` on `linux-64`,
  coverage → codecov),
  `ci-docs` (build + doctest), `ci-wheels` (build sdist/wheel, test in pixi envs, publish to
  Test PyPI on main and PyPI on `v*` tags via **Trusted Publishing OIDC**), `ci-changelog`,
  `ci-citation` (validate `CITATION.cff`), **CodeQL**, pre-commit.ci, dependabot
  (github-actions grouped; the `pip` ecosystem is declared but parked at
  `open-pull-requests-limit: 0`, so security updates run and version updates do not —
  `requirements/*.txt` declare floors rather than pins, and a bot raising one is the
  automatic floor raise floors spec §2 rejects).
- `ci-docs` also installs Playwright's pinned Chromium, serves the completed build locally,
  and runs the §7 browser smoke test. CDN or dependency-install failures fail the job; no
  static-image fallback is published.
- **Scheduled, not gating:** `ci-floors` (weekly) resolves every dependency minimum tephpy
  declares — at both declaration sites — exercises what it resolves, and files one issue per
  broken floor, attributed to a single package (floors spec §1). It is deliberately not a
  required check: it solves fresh against a live channel, so it goes red for reasons no pull
  request caused, and a required check like that is one people learn to ignore
  (floors spec §2). It is the lower end of the declaration whose upper end `ci-locks` moves.
- **Fast-follow (documented, not built at v1):** `ci-locks` (weekly lockfile-update bot),
  `ci-tests-lock` (daily fresh-resolve canary), `ci-tests-pypi` (daily pip-only install
  canary), `ci-linkcheck`, `ci-stale`, `ci-first-contribution`, and a JOSS paper build. The
  spec records these so the gap is a deliberate schedule, not an omission.

(spec-8-8)=
### 8.8 Repo hygiene and community files

`CITATION.cff` (validated in CI), `codecov.yml`, `.github/dependabot.yml`,
`CODE_OF_CONDUCT.md` (Contributor Covenant), `CONTRIBUTING.md` (points at the developer
docs), `SECURITY.md`, issue/PR templates, `.github/labeler.yml` (incl. a `spec-0` label
rule), `CODEOWNERS`, and per-directory `AGENTS.md` files (root, `docs/`, `tests/`). SemVer
with a 0.x honesty period.

(spec-9)=
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

(spec-10)=
## 10. Plan roadmap

Seven plans deliver the v1 scope (§9). Each plan gets its own spec-derived implementation
plan in `docs/src/developer/plans/`, and a plan is executed and merged before any plan that
*depends on it* is written. The dependencies form a partial order, not a chain: Plans 5
and 6 are mutually independent and may proceed in parallel once Plan 4 has merged. The
ordering follows the §3 layering (`transforms` ← `plotting` ← (`calc`, `sounding`, `io`)):
geometry first, then the drawing machinery, then the data model, then the analysis and
ingest layers above them. (`calc` itself stays headless per §3 — its pairing with shading
and the indices panel in Plan 5 is delivery convenience, not an import dependency.)

| # | Plan | Scope (spec §) | Depends on | Status |
|---|------|----------------|------------|--------|
| 1 | Foundation & scaffolding | §8 end to end: packaging, pixi, lint/type/test tooling, docs skeleton, CI core gates (residual deferrals: item 15 below) | — | ✅ complete (PR {pull}`1`; SPEC 0 / platform updates PR {pull}`4`, {pull}`5`) |
| 2 | Transforms & the tephigram projection | §3.1: T–ln θ math derived from published sources with tephi as oracle; minimal `TephigramAxes` + `"tephigram"` registration in `plotting/axes.py`; seeds `_constants` (MA, θ reference pressure, default extents); transform tests per §7; wheel-install smoke test in `ci-wheels` (item 15) | 1 | ✅ complete (PR {pull}`9`) |
| 3 | Isopleth plotting | §3.2 grid + five isopleth families as zoom-aware artists, accessor methods, `set_extent`; §3.5 `_constants` + `tephpy.config`; pytest-mpl infrastructure + isopleth baselines (§8.5); vector-output smoke test (§9 "vector output" — PDF/SVG `savefig` of the first real diagram) | 2 | ✅ complete (PR {pull}`15`) |
| 4 | Sounding data model & profile plotting | §3.4 `Sounding` dataclass (validation §6, constructors); the §5 units machinery incl. `TephpyUnitsError` and the shared exception module; `plot_profile` (quantities path), `plot_sounding`, multi-sounding overlay + legends (§1 item 4); profile image baselines | 3 | ✅ complete (PR {pull}`19`) |
| 5 | Thermodynamic analysis | §3.3 `calc`: `parcel_path` (surface + mixed-layer parcels, −25 mb correction), `normand_point`, `indices`; the `Profile` type + its `plot_profile` overload (§3.2); analysis-time §6 errors (`MissingDataError`, `ProfileTooShortError`, `TephpyValidationError`); `shade_cape`/`shade_cin`, `annotate_indices`; shading baselines; worked-example integration test (§7); drop the scipy declaration (§8.1, item 14) | 3, 4 | ✅ complete (PR {pull}`26`) |
| 6 | Wind barbs & data ingest | §3.2 `plot_barbs` (right-hand gutter staff, Met Office symbology); §3.4 `io` (`wyoming`, `igra`) with recorded-fixture tests; `TephpyIOError` (§6); barb baselines | 3, 4 | ✅ complete (PR {pull}`40`; ingest and layout hardening PR {pull}`41`) |
| 7 | Examples gallery & documentation completion | §8.6: sphinx-gallery examples (one per §1 use case, incl. the hodograph composition example from §9), `src/tephpy/examples`, tutorials/how-tos/explanation content, glossary completion, sphinx-tags, doctest task + CI doctest run; composed §4-figure baseline (§7 — needs the union of Plans 5 and 6); README non-goals statement and eccodes recipe how-to (§9) | 2–6 | **next** |

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
  *Verified 2026-08-03:* the RTD project is live — it builds `latest` from `main` and
  reports a `docs/readthedocs.org:tephpy` check on pull requests. Versioned hosting
  (`stable`, `v0.x`) still waits on the first tag, per release execution above.
  The GitHub Discussions link in the issue templates resolves — Discussions are enabled
  and `.github/ISSUE_TEMPLATE/config.yml` carries the contact link. Only the production
  PyPI Trusted Publisher is still genuinely unverified, pending the first `v*` tag.

### Assumptions and open decisions

Enumerated so they are visible decisions, not silent drift. Items 1–2 are decisions this
roadmap makes; the remainder are open questions assigned to the plan that must answer
them, ordered by owning plan.

1. **Resolved** (2026-07-28, PR {pull}`19`, {pull}`26`, {pull}`40`) — **The Plan 4–6 slicing is inferred, not inherited.** Only Plans 1–3 and 7 were anchored
   in writing when Plan 1 shipped ("Plan 3" for image tests, "Plan 7" for the gallery).
   The split above keeps one subsystem per plan along the §3 layering; viable alternatives
   (barbs inside Plan 4; `io` as its own plan; examples accreting per-plan instead of
   batching in Plan 7) were consciously not taken.
2. **Resolved** (2026-07-26, PR {pull}`26`) — **`Profile` is defined in Plan 5 but referenced by Plan 4.** §3.2 says `plot_profile`
   accepts pint quantities *or* a `Profile`; Plan 4 ships the quantities signature, and
   Plan 5 adds the `Profile` overload together with `calc.parcel_path`. *Resolved
   2026-07-26:* `Profile` is a frozen dataclass in `calc` (§3.3); the overload
   dispatches by duck-typing so `plotting` never imports `calc` (§3.2).
3. **Resolved** (2026-07-23, PR {pull}`9`) — **Plan 2 — the TephigramAxes seam.** *Resolved 2026-07-23:* the `"tephigram"`
   projection and a minimal `TephigramAxes` live in `plotting/axes.py` from Plan 2
   (Plan 3 extends the same class in place); `transforms.py` stays pure numpy math.
   §3.1 updated accordingly.
4. **Resolved** (2026-07-23, PR {pull}`9`) — **Plan 2 — units at the transforms boundary.** *Resolved 2026-07-23:* `transforms` is
   the documented exemption to §5 — bare numpy arrays in diagram-native units (hPa/°C),
   because matplotlib's per-draw pipeline consumes bare arrays; every layer above
   converts before calling down. §5 updated accordingly.
5. **Resolved** (2026-07-23, PR {pull}`9`) — **Plan 2 — tephi provenance and attribution.** *Resolved 2026-07-23:* verify-first
   stance — derive each function from the published sources and challenge it per case
   (§7's four-layer battery), with tephi as a recorded oracle rather than a source to
   copy. Attribution attaches only to artifacts actually copied, per case, via a NOTICE
   file if needed. The same stance applies to Plan 3's locator/refresh reimplementation.
6. **Resolved** (2026-07-24, PR {pull}`15`) — **Plan 3 — config object and accessor naming.** The §3.5 `tephpy.rcparams`-style object
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
7. **Resolved** (2026-07-24, PR {pull}`15`) — **Plan 3 — side-of-axes layout seam.** The barb gutter (Plan 6) and the indices panel
   (Plan 5) both need space beside the diagram; Plan 3 decides whether the axes pre-builds
   that layout or each consumer manages its own. *Resolved 2026-07-24:* decide the
   contract, build later — §3.2 fixes the mechanism (`axes_grid1` divider) and the
   right-side inside-out ordering (barb gutter, then indices panel); no layout code
   ships until Plans 5/6 consume it.
8. **Resolved** (2026-07-25, PR {pull}`19`) — **Plan 4 — Sounding contract details.** Label/legend format (§4 hints
   `"72357 2013-05-20 12Z"`), station/time optionality (§3.4 states requiredness only for
   the data arrays), and how forecast-vs-observed overlays of the same station/time stay
   distinguishable in a legend. *Resolved 2026-07-25:* station and time are optional
   metadata — ad-hoc arrays plot without ceremony, operational users get comparable
   legends for free. `label` derives as `"72357 2013-05-20 12Z"` when both are present,
   an explicit `label=` always wins, and with neither there is no legend entry.
   Forecast-vs-observed distinguishability is the label override's job — no dedicated
   field. §3.2/§3.4 updated accordingly.
9. **Refined** (2026-07-26, PR {pull}`19`) — **Plan 4 — pandas/xarray dependency status.** `from_dataframe`/`from_dataset` (§3.4)
   and the §2 ingest decision need pandas/xarray, but §8.1's runtime list omits them
   (today they arrive transitively via MetPy). Decide: direct declaration, optional
   extra, or typing-only treatment. *Resolved 2026-07-25:* declared directly — the
   constructors' public API consumes pandas/xarray types, so leaning on MetPy's
   transitive guarantee would be a silent contract, and the declaration adds no install
   weight. Imported function-locally inside the constructors to keep `import tephpy`
   light. §8.1 updated accordingly. *Refined by Plan 4 (PR {pull}`19`):* the shipped
   constructors are duck-typed over the objects handed to them, so no runtime
   pandas/xarray import exists at all — annotations are `TYPE_CHECKING`-only, and
   the Plan 4 subprocess test enforces it.
10. **Resolved** (2026-07-26, PR {pull}`26`) — **Plan 4/5 — top-level namespace policy.** §4 requires `tephpy.calc.parcel_path` to
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
11. **Resolved** (2026-07-26, PR {pull}`26`) — **Plan 5 — MetPy behaviour verification.** §6 asserts NaN pass-through, but MetPy
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
12. **Resolved** (2026-07-26, PR {pull}`26`) — **Plan 5 — "layer highlights".** The §3 tree comment on `shading.py` names layer
    highlights, but no API, §9 scope item, or plan covers them; treated as not-in-v1
    unless Plan 5's design deliberately includes them. *Resolved 2026-07-26:* not in
    v1 — Plan 5 ships `shade_cape`/`shade_cin` only and the §3 tree comment is
    corrected; layer highlights remain a v1.x candidate.
    The v1.x candidacy is tracked in {issue}`79`.
13. **Resolved** (2026-07-27, PR {pull}`26`, {pull}`40`) — **Plans 2/5/6 — third-party data provenance.** Any tephi artifacts actually copied
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
    profile. *Plan 6 slice resolved 2026-07-27:* the recorded fixtures are one
    captured Wyoming ascent and one trimmed IGRA v2 station file under
    `tests/fixtures/io/`, each with a sidecar provenance note recording source
    URL, capture date and method, and attribution. IGRA is NOAA/NCEI public
    domain; the Wyoming ascent is a single recorded sounding used as test
    facts, with the archive credited in the provenance note.
14. **Resolved** (2026-07-26, PR {pull}`26`) — **scipy is declared but unowned.** §8.1 lists scipy as a runtime dependency, yet no §3
    module names it (plausible first consumers: interpolation in Plan 2 or Plan 5). If
    Plan 5 completes without it, drop the dependency. *Resolved 2026-07-26:* Plan 5's
    design needs no direct scipy (the shading interpolation is plain numpy; MetPy
    keeps scipy transitively), and `src/tephpy` has no scipy import today — the
    direct declaration is dropped in Plan 5 (§8.1 updated; the implementation plan
    also removes scipy from the declared-dependencies tuple in
    `tests/test_import.py`).
15. **Deferred** (Plan 7 — {issue}`76`) — **Residual Plan 1 deferrals**, re-homed: sphinx-tags (§8.6) → Plan 7; `doctest` task +
    `ci-docs` doctest run (§8.2/§8.7) → Plan 7; `tests-clean` task (§8.2) → reconciled
    in Plan 3 (decided 2026-07-24: `tests-clean` removes test artifacts; a `baselines`
    task regenerates the pytest-mpl baselines);
    wheel-install smoke test → Plan 2 (decided 2026-07-23); check-manifest CI gate →
    revisit once the wheel carries domain code; the §8.3 packaging-guide SPEC 0 docs
    statement → Plan 7.

    Per-deferral status:

    - **Deferred** (Plan 7 — {issue}`76`): sphinx-tags (§8.6).
    - **Deferred** (Plan 7 — {issue}`76`): the `doctest` task and the `ci-docs` doctest run (§8.2/§8.7).
    - **Deferred** (Plan 7 — {issue}`76`): the §8.3 packaging-guide SPEC 0 statement.
    - **Resolved** (2026-07-24, PR {pull}`15`): the `tests-clean` task, with `baselines` alongside it.
    - **Resolved** (2026-07-23, PR {pull}`9`): the wheel-install smoke test.
    - **Open** ({issue}`77`): the check-manifest CI gate — nothing runs it, and `MANIFEST.in` has already drifted once.
16. **Resolved** (2026-07-29, PR {pull}`41`) — **matplotlib floor vs. `Artist.get_figure(root=...)`.** §8.1 names matplotlib without
    a version and the pins carried `>=3.9`, but the `root` keyword arrived only in
    matplotlib 3.10, and three zoom-aware artists pass it: `isopleths.py` (Plan 3),
    `barbs.py` (Plan 6), and `axes.py` (Plan 6 hardening). *Resolved 2026-07-29:* floor
    raised to `matplotlib>=3.10` in `requirements/pypi-core.txt` and
    `[tool.pixi.dependencies]`; the call sites keep the explicit `root=`, which is
    load-bearing in `axes.py` — the `Figure.clear` frame check must match the *enclosing*
    (Sub)Figure — and future-proof elsewhere. Verified against real installs: matplotlib
    3.9.4 fails 26 of the 445 tests, every failure the same `TypeError: ... unexpected
    keyword argument 'root'`; 3.10 passes all 445 on unmodified source. 3.10 is also the
    §8.3 SPEC 0 floor, matplotlib 3.9.0 (2024-05-15) having left the 24-month window on
    2026-05-15. No CI job resolves the declared minimums — every workflow is
    `pixi run --frozen` against a lock pinned to 3.11.1, and the wheel smoke test takes
    the newest satisfying release — which is how the wrong floor survived three plans; a
    lowest-direct-resolution gate is re-homed to Plan 7.

    *Residual:* **Deferred** (Plan 7 — {issue}`78`) — the lowest-direct-resolution gate.

(spec-11)=
## 11. Open questions (carried from research)

- **Deferred** (v1.x — {issue}`79`) — Which aviation-specific overlays (icing layers, MINTRA) do operational users
  actually need built in, versus composing themselves? Partly answered: member
  emphasis (§3.2) gives the icing band's 0 °C and −20 °C bounds as isotherms, so
  what remains open is whether the *shaded layer* between them is wanted, which
  belongs with the layer highlights already deferred to v1.x (§10 item 12).
- **Blocked** (on a citable published chart — {issue}`80`) — Whether a current Met Office Factsheet 13 — or a University of Reading blank
  tephigram — shows the 0 °C isotherm drawn distinctively on the printed chart.
  Its published URL 404s (2026-07-30), so member emphasis ships off by default;
  a citation would justify revisiting that.
- **Open** ({issue}`81`) — Which named stability indices beyond the v1 set (Showalter, K-index, Total Totals)
  are worth wrapping, given all are one-line `metpy.calc` calls for users?
- **Deferred** (post-v1, demand-driven — {issue}`82`) — Whether BUFR ingest demand justifies an optional `tephpy[bufr]` extra later.

(spec-12)=
## 12. References

- Met Office Factsheet 13 — Upper air observations (2023)
- Stull, *Practical Meteorology*, ch. 5 (thermo-diagram construction, stability)
- University of Reading tephigram teaching notes
- COMET/UCAR tephigram training module; NWS and HKO operational guides
- SciTools/tephi 0.4.0.dev0 source (transform and isopleth-artist design)
