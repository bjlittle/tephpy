# tephpy view framing — design specification

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. `src/tephpy/plotting/axes.py`, `src/tephpy/_constants.py` and
> `src/tephpy/_configfile.py` cite it by section — `framing spec §3.1` and the like — so
> these sections *are* the reasoning behind what they do, and where the two ever diverge it
> is the specification that gets corrected. Read it as current.

- **Date:** 2026-08-25 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `framing spec §…` — the question is how a view gets chosen, which is
  neither the extent machinery alone nor the axes class alone
- **Scope:** `TephigramAxes.set_extent`'s signature, the new `TephigramAxes.fit`, the
  `config.diagram` options behind both, and the migration of every caller. The transforms
  are unchanged; so is everything that draws
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) — Plan 8 of
  spec §10, inserted between Plans 7b and 7c
- **Tracked by:** {issue}`184`, which this specification answers in full

(framing-spec-1)=
## 1. Purpose

`set_extent` is the only way to choose a view, and it asks for the wrong thing in the wrong
shape. Five defects follow from one decision — that a view is named by two `(pressure,
temperature)` corners — and all five are measurable rather than aesthetic. Every number
below was produced by running the code on 2026-08-25, not inferred.

**The corner naming is false for ordinary input.** `axes.py` documents the two points as
"bottom-left and top-right corners", then maps both through the transforms and takes
`min`/`max` on each axis independently — the axis-aligned bounding box of two points in a
*rotated* space. Whether the first point lands bottom-left depends on whether the θ
separation outweighs the temperature separation, and on a shallow-pressure, wide-temperature
window it does not:

| extent | where the first named corner actually lands |
|---|---|
| `((900, -65), (200, 5))` — the default | bottom-left |
| `((1000, 30), (900, -10))` | bottom-**right** |
| `((1000, 40), (700, -20))` | bottom-**right** |
| `((950, 25), (850, 0))` | bottom-**right** |

All four are accepted without complaint. The failing shape is a boundary-layer window, which
is the kind `plot_sounding_comparison.py` draws.

**The nested pair is order-ambiguous.** Both members are bare floats, so `(p, T)` against
`(T, p)` is a silent coin-flip. The `pressure > 0` guard catches the transposition only when
a temperature happens to be negative. `set_extent(((20, 1000), (40, 200)))` — written by
someone reading the order as `(T, p)` — is accepted and produces an x range of 2324–3480
where the intended reading gives 1724–1902.

**The cited precedent is not the shape in use.** `axes.py` and spec §3.2 both call this "the
cartopy idiom", but cartopy's `set_extent` takes a flat four-tuple of *ranges*,
`[x0, x1, y0, y1]`. The concept was adopted and the packaging inverted.

**The view can exclude the region the caller named.** This is the defect {issue}`184` did
not find, and it is the worst of them. Mapping *two* corners and taking the extremes gives
the bounding box of those two points — not of the pressure × temperature region they
delimit. The other two corners of that region are simply not consulted, and in a rotated
space they can fall outside the result. For `((1000, 30), (900, -10))`, measured:

| named corner | inside the view it asked for? |
|---|---|
| (1000 hPa, 30 °C) | yes |
| (1000 hPa, −10 °C) | **no** |
| (900 hPa, 30 °C) | **no** |
| (900 hPa, −10 °C) | yes |

Half the named region is outside the view. A caller framing a boundary-layer window can lose
the data they framed it around, silently, and nothing in the API's vocabulary would lead
them to suspect it.

Underneath all four is a fifth problem, which no signature fixes and which the current one
hides: **the caller also gets more than they name.** The view is an axis-aligned rectangle
and pressure is not an axis, so a named region always reaches further than its bounds. For
the default extent the view's other two corners work out to 84.9 hPa / −137.9 °C and
1058.4 hPa / +77.9 °C. Nothing draws there because it is unphysical, but an API that speaks
of corners implies it delivers the corners it was given and no others, and it does not.

Separately, `set_extent` answers "make these figures directly comparable". It does not
answer "frame this neatly" — which is what a reader reaches for first — and, without a
pressure clamp beside it, there is no API for that at all. `plot_sounding_comparison.py`
meets that need today by hand-picking a literal `EXTENT` — a worked example demonstrating
the absence of the thing it needs.

Nothing has been released. Both changes are free now and cost a deprecation cycle later,
which is the whole reason this plan sits before v0.1 and before the narrative documentation
of Plan 7c that would otherwise teach the shape being replaced.

(framing-spec-2)=
## 2. Decisions

1. **A view is named by ranges of the quantities a caller thinks in** — `pressure=` and
   `temperature=` — not by points. Keyword-only, both required. Neither is an axis of the
   drawn plane, which is exactly why naming points in them goes wrong.
2. **Each range is sorted internally.** Order within a range carries no meaning, so it is
   not allowed to carry a bug.
3. **`fit` frames whatever it is given**, variadically, over any object the diagram plots.
   One rule, no privileged argument.
4. **Margin is a fraction of the fitted span, applied in the drawn plane**, resolved
   keyword > `config.diagram.margin` > `_constants`.
5. **The configuration follows the API.** One concept, one shape, everywhere.
6. **Both methods disable autoscaling**, because a caller who fixed a window meant it.
7. **The docstrings state what the caller also gets**, since §1's fifth problem survives
   every signature.

(framing-spec-3)=
## 3. Architecture

(framing-spec-3-1)=
### 3.1 `set_extent` by ranges

```python
ax.set_extent(pressure=(900.0, 200.0), temperature=(-65.0, 5.0))
```

Keyword-only, both required. Keyword-only because the whole defect of §1 is two positional
sequences that cannot be told apart; leaving either positional preserves the failure for the
caller who passes one. Both required because `set_extent(pressure=...)` has no defensible
reading for the other axis — "leave temperature as it is" is a different operation from
"fix the view", and mixing them is how a method acquires two jobs.

Each range is sorted before use, so `(900, 200)` and `(200, 900)` are the same window. This
is not leniency: within a range the order is genuinely meaningless, and the old API's
equivalent freedom was the transposition bug of §1 rather than a kindness.

**The implementation changes, and the change is half the fix.** The transforms are the same
— `theta_from_pressure_temperature` then `xy_from_temperature_theta` — but they are applied
to the corners of the named region rather than to the two points a caller happened to write.
That is what makes the view contain the region it names, which §1's fourth defect shows the
current code does not.

**Four corners are not enough, and assuming they were is the same mistake one layer down.**
The review of {pull}`194` found it. Writing `y` out at fixed pressure,

> `y = MA·ln(T + 273.15) + MA·κ·ln(P_REF/p) − T`

gives `dy/dT = MA/(T + 273.15) − 1`, which vanishes at `T + 273.15 = MA` — that is
**T = 26.85 °C** — and `d²y/dT² < 0` there, so it is a *maximum* strictly inside any
temperature range that spans it. A corner-only search misses it. Measured:
`set_extent(pressure=(1000, 900), temperature=(-50, 100))` returned `yhi = 1685.63` while
`(900 hPa, 26.85 °C)` maps to `y = 1693.32`, outside the view that named it.

The extremum is unique and it is the only one. `x = MA·ln(T + 273.15) + MA·κ·ln(P_REF/p) + T`
has `dx/dT = MA/(T + 273.15) + 1 > 0` for every physical temperature, so `x` is strictly
increasing in `T`; and pressure enters both coordinates only through `MA·κ·ln(P_REF/p)`,
monotonic in `p`. So the candidate set is the four corners plus, when
`T* = MA − 273.15` falls strictly inside the temperature range, the two points
`(p_lo, T*)` and `(p_hi, T*)`. Verified numerically across the pressure domain: `argmax y`
sits at `T*` regardless of `p`, and `x` is monotonic throughout.

This is worth stating rather than merely fixing, because it is §1's own error recurring:
§1 records that mapping two points and taking extremes assumes the extremes live at those
points, and mapping four corners assumes the same thing about a rectangle whose image is
not a rectangle. `T*` is a property of the projection — it is `MA` expressed in Celsius —
so it belongs beside `MA` in `_constants` rather than as a literal in the geometry.

Measured on 2026-08-25, the two agree on the default extent and differ on every one of §1's
three mis-named cases — the same cases, because both defects have the same cause. So the
change is observable, and §6 pins it. What it does *not* do is move a shipped figure: both
`plot_tephigram.py` and `plot_sounding_comparison.py` use extents on which two-corner and
four-corner mapping agree, so no gallery baseline shifts under this change alone.

**Validation.** A non-finite bound, or a pressure at or below zero, raises `ValueError` as
today; the message names the offending keyword rather than reprinting a nested tuple. A
range whose two bounds are equal is degenerate and refused, as the current
`x[0] == x[1] or y[0] == y[1]` test refuses its equivalent.

**The docstring carries §1's fifth problem.** It says outright that the view is an
axis-aligned rectangle in a rotated space, so the pressures and temperatures reachable
inside it exceed those named, and it gives the default extent's other two corners — 84.9 hPa
/ −137.9 °C and 1058.4 hPa / +77.9 °C — as the worked instance. An API that stopped claiming
false corners without saying what it does produce would have traded one silence for another.

(framing-spec-3-2)=
### 3.2 `fit` by data

```python
ax.fit(sounding, pressure=(950, 300))     # one ascent, over the layer of interest
ax.fit(sounding, parcel, pressure=(950, 300))   # environment and the path it is read against
ax.fit(*ascents, pressure=(1000, 200))    # a station's day, every panel framed alike
```

Variadic over anything the diagram plots — `Sounding` and `Profile` today — with one rule:
frame everything you were given. The alternative shapes were considered and rejected in §5.

**What `fit` promises, stated exactly.** *Nothing you gave it falls outside the frame.* It
does **not** promise a neat-looking diagram, and an earlier draft of this section said it
did. That was written without rendering a single figure, and rendering one falsifies it: a
radiosonde ascent does not stop at the tropopause. Measured over the two shipped samples,
an unclamped fit spans `pressure=(966.4, 10.2)` — into the mid-stratosphere — and θ grows
fast enough up there that the resulting view is a narrow diagonal band of isopleths in a
mostly empty rectangle. The temperature range is barely implicated: clamping to
`(1000, 200)` hPa changes the fitted temperature only from `(-79.4, 27.5)` to
`(-72.3, 27.5)`, and turns an unusable figure into a conventional one.

**So `fit` takes a `pressure=` clamp**, and it is the parameter that makes the method
useful rather than merely correct. Given one, the view's pressure range is the clamp and the
temperature range is fitted to the data *inside* it. This is the meteorological selection a
reader actually makes — a layer — and it is why `pressure` is clamped and temperature is
not: a pressure band names a part of the atmosphere, a temperature band names nothing.

**There is deliberately no default clamp.** `fit(sounding)` frames the whole ascent, which
is wide and is *correct* — it is the honest answer to "frame all of this". A default would
have to pick a pressure silently, and silently discarding the stratospheric half of an
ascent is a worse failure than a wide view, because it is invisible. §5 records this.

**What bounds the view.** Pressure, temperature and dewpoint. Those are the diagram's
coordinates; wind is not, because `plot_barbs` draws into the right-hand gutter rather than
into the plane, so a sounding's winds cannot fall outside a view that contains its profile.
Dewpoint is optional on `Sounding` and absent from `Profile`, so it contributes where it
exists.

**The reduction is nan-aware.** Spec §3.4 makes NaN gaps data everywhere except pressure, so
a level with no dewpoint is a level whose dewpoint does not bound anything, not a level that
poisons the result. That rule is about *finiteness*, not about the clamp, and the two are
not the same failure. **An argument carrying no finite data at all is a caller error**,
checked per argument before any clamp is applied, and raises `MissingDataError` naming which
one. **An argument whose finite data simply falls outside the `pressure=` clamp is
different**: it contributes nothing, silently, and that is fine — a caller framing a layer
may legitimately pass a sounding that does not reach it. Only when nothing survives the
clamp across every argument does `fit` raise, exactly as it does with no clamp at all.

**The type dispatch is one small internal function** rather than `isinstance` chains at each
use, and it is the only place `fit` knows what a `Sounding` or a `Profile` is. Adding a
third plottable later means teaching that function, not editing `fit`.

**Why the parcel matters enough to be an argument.** `calc.parcel_path` returns a `Profile`
over the sounding's own pressure span, but a parcel is warmer than its environment through
the CAPE region — so fitting to the sounding alone clips the very path the parcel analysis
exists to show. Making the parcel just another argument dissolves the problem rather than
documenting it, and §6 pins the case with a test, because a defect an API was built to
prevent is the one worth asserting.

(framing-spec-3-3)=
### 3.3 Margin

A fraction of the fitted span, applied symmetrically in the drawn x/y plane. Fractional
because it is then scale-free — the same value frames a boundary-layer window and a
full-troposphere one — and applied in the drawn plane because isotropic padding there is
what "neatly framed" means to the eye. Padding in pressure and temperature instead would be
anisotropic once transformed, and would need two numbers to say one thing.

Resolution is keyword > `config.diagram.margin` > `_constants`, which is the order every
tunable in this project already uses. `margin` earns a configuration entry where the
wind-barb gutter did not, because `DiagramOptions` already exposes `extent`: how the view is
framed is established as a user preference, and a house framing style set once is the same
kind of wish as a preferred default view.

`margin=0` is legal and fits exactly. It is the right answer for a caller composing panels
whose frames must agree to the pixel. A negative or non-finite margin is not legal by any
route. The configuration file has always refused one; the review of {pull}`194` found that
the `margin=` keyword and a programmatic `config.diagram.margin` did not, so a negative
value silently shrank the limits and clipped the data `fit` exists to contain, and a
non-finite one failed later inside matplotlib with a message about axis limits. The check
belongs where the value is resolved, so every route reaches it.

Margin is applied after the clamp of §3.2, so `pressure=` names the layer and `margin=`
decides how tightly it is drawn. A clamp with `margin=0` gives exactly the named band.

(framing-spec-3-4)=
### 3.4 The configuration, reshaped

`config.diagram.extent` carries the corner-pair shape in six coupled places, and decision 5
moves all of them together:

| where | today | after |
|---|---|---|
| `_config.py` | `Extent = tuple[tuple[float, float], tuple[float, float]]` | a mapping of two named ranges |
| `_config.py` | `DiagramOptions.extent` | unchanged in name, new in shape; joined by `margin` |
| `_constants.py` | `DEFAULT_EXTENT` as two corners | the same window as two ranges |
| `_configfile.py` | `_as_extent`, expecting a list of two corners | expecting a mapping of two ranges |
| `_configfile.py` | `_domain_extent`, iterating corners | iterating ranges |
| `_configfile.py` | the template text, "Default view corners as `[[pressure, temperature], …]`" | the range form |

In a configuration file that reads:

```yaml
diagram:
  extent: {pressure: [900, 200], temperature: [-65, 5]}
  margin: 0.05
```

The shape is better YAML as well as better API. {issue}`128` records that YAML spells a
tuple as a list and that the difference bites; nested bare pairs are exactly the shape that
makes it bite, and a mapping of two named ranges is a thing YAML expresses natively and a
reader can check by eye. `extent` stays one key that is set or unset rather than splitting
into two that must agree, which keeps `Extent | None` meaning what it says.

`_domain_extent`'s docstring currently says its rule is "Lifted from
`axes.TephigramAxes.set_extent`". That coupling is real and is preserved: the validator
keeps testing finiteness and pressure positivity, against ranges instead of corners, and the
docstring keeps saying where the rule comes from.

(framing-spec-3-5)=
### 3.5 Autoscaling

Both methods call `set_autoscale_on(False)`. `set_extent` does today, and the reason given
in its docstring — that later overlays never drift a window the caller fixed — applies
identically to `fit`. A `fit` that left autoscaling on would be undone by the next
`plot_sounding`, which is the one thing a caller who just framed their data did not ask for.

(framing-spec-4)=
## 4. Migration

Nothing is released, so there is no deprecation path, no alias and no shim. Every caller
moves in the same change.

- **29 `set_extent` occurrences** across `src/` and `tests/`, counted 2026-08-25.
- **`src/tephpy/examples/plot_tephigram.py`** takes the new keywords.
- **`src/tephpy/examples/plot_sounding_comparison.py`** drops its literal `EXTENT` for
  `ax.fit(...)` over both soundings. {issue}`184` names this example as exactly what `fit`
  is for, and an example that hand-picks a window to demonstrate comparison is evidence the
  API was missing. Its gallery figure changes with it; it carries no baseline of its own
  (§6).
- **Five design specifications** mention `set_extent` — spec §3.2 and spec §3.4,
  domain spec §3.3, plots spec, gallery spec and scope spec. {issue}`184` counted
  four; the scope specification landed after it was written. The parent, domain and
  gallery specs are corrected in place, alongside the config-file spec's template,
  which this count does not name; the plots spec needs no correction, and the scope
  spec's own stale count and quotation are corrected in place with it. The frozen
  implementation plans are not (docs spec §3.1).
- **The generated configuration reference** re-renders from the reshaped template.

(framing-spec-5)=
## 5. Alternatives considered

- **A flat four-tuple, cartopy's actual shape** — `set_extent([p0, p1, t0, t1])`. It fixes
  the corner lie but keeps every other defect: four bare floats in a sequence are more
  order-ambiguous than two pairs, not less, and nothing in the call says which two are
  pressures. Rejected: the precedent §1 cites is worth abandoning rather than adopting
  correctly.
- **`fit(soundings, parcel=None)`** — a named parameter for the parcel. More discoverable in
  the signature, but it privileges one composition, has no reading for two parcels, and
  needs a second rule the moment several soundings arrive. Rejected in favour of decision 3.
- **`fit` fitting the environment only, documented** — simplest to specify and to test, and
  rejected because it ships the clipping defect of §3.2 in the API whose one promise is that
  nothing given to it falls outside the frame. Documenting a footgun is not the same as not
  having one.
- **Absolute margin in pressure and temperature** — domain-meaningful and predictable, but
  two numbers for one idea, anisotropic once transformed, and needing revision every time
  the fitted span changes. Rejected in favour of §3.3.
- **A default `pressure` clamp on `fit`** — tempting, because the unclamped view is poor for
  every real radiosonde and `fit(snd)` is the first thing anyone types. Rejected: any default
  is an arbitrary number that silently drops the data above it, and an invisible omission is
  worse than a visibly wide view. The how-to of §7 carries the burden instead, by making the
  clamp the second thing a reader meets.
- **A `temperature=` clamp beside `pressure=`, for symmetry with `set_extent`** — rejected as
  speculative. A pressure band selects a layer of the atmosphere; a temperature band selects
  nothing a reader is thinking in. Symmetry with a method that *names* a view is not a
  reason for a method that *derives* one.
- **Dropping `config.diagram.extent` once `fit` exists** — considered because `fit` answers
  the common case. Rejected: a preferred default view is a legitimate standing preference,
  and `fit` needs data, which a freshly created axes does not have.

(framing-spec-6)=
## 6. Testing

Per spec §7, and weighted towards the defects this change exists to remove.

| what | how |
|---|---|
| a range pair yields the window the corner pair used to, where the two agree | equivalence test over the default extent |
| **the view contains the whole region it names** | the four corners of the named region all fall inside the resulting limits — the §1 case where two of them did not is asserted directly |
| **the interior temperature extremum is bounded** | a range spanning `T* = MA − 273.15` contains `y(p, T*)` at both pressure bounds — the `(1000, 900) × (−50, 100)` case of §3.1, which a corner-only search excludes |
| the resolved margin is validated wherever it arrives | keyword and `config.diagram.margin` are checked like a configuration file's, not only at file load |
| order within a range is irrelevant | property test: `(a, b)` and `(b, a)` give identical limits |
| the §1 transposition is now unwritable | the old call shape raises `TypeError`, being neither keyword |
| a degenerate or unphysical range is refused | `ValueError`, message naming the keyword |
| `fit` over one sounding, over several, over sounding-plus-parcel | limits contain every finite datum of every argument |
| **the parcel-clipping case** | `fit(snd)` clips a parcel that `fit(snd, parcel)` contains — asserted directly, because it is the defect `fit` exists to prevent |
| a NaN-gapped dewpoint bounds nothing and poisons nothing | fit over a sounding whose dewpoint is partly NaN |
| an argument with no finite data at all raises, naming it | checked per argument, before any clamp is applied |
| an argument whose finite data falls entirely outside the `pressure=` clamp | contributes nothing, silently — not an error |
| nothing survives the clamp across every argument | raises `MissingDataError`, as with no clamp at all |
| `margin` resolution order | keyword beats config beats constant; `margin=0` fits exactly |
| autoscaling is off after both calls | and a later `plot_sounding` does not move the window |
| the reshaped configuration round-trips | file → `config.diagram.extent` → applied view |
| the framing how-to's figures | `docs/baseline`, via the published-figure gate (plots spec §3.5) |

Five new image baselines, one per figure the how-to of §7 publishes:
`framing-fit-unclamped`, `framing-fit-clamped`, `framing-fit-parcel`, `framing-set-extent`
and `framing-margin`. `plot_sounding_comparison` carries no baseline of its own — the only
`mpl_image_compare` in `tests/examples/` covers `plot_parcel_analysis`, which this change
does not touch — so its gallery figure changes with no baseline to update.

(framing-spec-7)=
## 7. Documentation

A framing how-to under `docs/src/howtos/`, publishing figures. Its spine is the contrast of
§3.2: `ax.fit(sounding)` unclamped, which frames a whole ascent into the stratosphere and
looks it, beside the same call with `pressure=` — the defect that shaped this section, used
as the thing it teaches. Then the parcel case as the reason `fit` takes more than a
sounding, and `set_extent` for "make these figures directly comparable". It ships here rather than waiting for Plan 7c because 7c owns
tutorials and explanation, and because shipping new API undocumented until a later plan is
how the gaps Plan 7b spent itself closing came to exist.

The configuration how-to's mention of "a preferred extent" gains the new shape. The glossary
needs no new term: `profile`, `parcel ascent` and `sounding` already carry what the page
says.

(framing-spec-8)=
## 8. Scope

**In scope.** `set_extent`'s signature and validation; `fit` and its reduction; the
`config.diagram` reshape and the new `margin`; the constants behind both; the migration of
§4; the tests of §6; the how-to of §7.

**Out of scope.** Everything Plan 7c owns. Layer shading ({issue}`79`), which is a drawing
feature and not a framing one. The transforms, which are unchanged — this specification
changes which numbers reach them, never what they compute.

**Open items**, tagged per docs spec §3.5.

- **Resolved** (2026-08-25, PR {pull}`194`) — **the whole of this specification.**
  {issue}`184` closes with it.
