# tephpy `add_logo` — design specification

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. `src/tephpy/plotting/logo.py` cites it by section — `logo spec §3.5` and the
> like — so these sections *are* the reasoning behind what the code does, and where the two
> ever diverge it is the specification that gets corrected. Read it as current.

- **Date:** 2026-08-01 (originated; maintained since)
- **Status:** living design specification, implemented in #71
- **Scope:** one new public function, `tephpy.plotting.add_logo`, plus six bundled PNG masters
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) — this extends
  spec §3.2 `plotting` with a branding artist and inherits its error-handling (spec §6),
  testing (spec §7) and engineering-standards (spec §8) rules unchanged
- **Prior art:** MetPy's
  [`add_metpy_logo`](https://github.com/Unidata/MetPy/blob/v1.7.1/src/metpy/plots/_util.py#L106-L131)
- **Brand assets:** `docs/src/_static/brand/assets/logo-bundle.zip`, catalogued by
  `docs/src/_static/brand/assets/README.md` (PR #69)

(logo-spec-1)=
## 1. Purpose

Give users a one-call way to brand a figure:

```python
tephpy.plotting.add_logo(ax)
```

MetPy proved the demand for this and the shape of the API. It also shows the two things not
to copy. `add_metpy_logo` uses `Figure.figimage`, which places the image in **device pixels**
— so the same call yields a logo a third the relative size at 300 dpi that it had at 100 dpi,
and there is no way to ask for "half an inch tall". And it offers a single dark-on-light
raster, so on a dark figure the mark disappears into the background.

tephpy has richer inputs to work with: three logo forms (icon, lockup, stacked) each in a
light-background and a dark-background variant, all published in the brand bundle. The design
below spends those inputs on a dpi-independent, theme-aware placement built from
`AnnotationBbox`, whose positioning vocabulary users already know from `legend`.

(logo-spec-2)=
## 2. Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Artist | `AnnotationBbox(OffsetImage(...))` | Sizes in **points**, so a request in inches renders identically at every dpi. `figimage` (MetPy's choice) sizes in device pixels and cannot honour an inch request |
| Sizing units | Height in **inches**; width follows the master's aspect | One number per form; the caller never reasons about pixels or aspect ratios |
| Masters shipped | The **largest** of each form (icon 512, lockup 716, stacked 512), light and dark | 128.3 KiB for six files. One master per (form, variant) downscales to every size; shipping the smaller rungs too would add weight and a second thing to keep in sync |
| Positioning vocabulary | `legend`'s `loc=` — ten strings or an `(x, y)` tuple | Zero new vocabulary. `'best'` is deliberately excluded: it promises collision detection this artist does not do |
| What the position is relative to | The **target** — a `Figure` anchors in figure fraction, an `Axes` in axes fraction | Same rule as `legend`: the thing you call it on defines the box. No separate `relative_to=` kwarg |
| Default form | `"lockup"` | It carries the wordmark at the smallest height of the three (§3.3), so the brand is legible in the least plot area. A bare icon is meaningless to anyone who does not already know the brand |
| Theme selection | `theme="auto"` from target facecolor luminance | Correct without being asked on both the default white figure and a `dark_background` style. `"light"`/`"dark"` name the **background**, matching the asset filenames |
| Asset packaging | Copies under `src/tephpy/plotting/_static/`, declared in `[tool.setuptools.package-data]` and `MANIFEST.in` | The function must work from a wheel with no docs tree and no network. **Measured:** while the files are git-tracked, `include-package-data` (on by default) plus the setuptools_scm file finder already ships them — the declaration is belt-and-braces that survives losing either, not the load-bearing mechanism, and the spec does not pretend otherwise |
| Asset drift | A test hashes the six copies against `logo-bundle.zip` | The zip is the source of truth; the copies are derived. Without the guard they diverge silently on the next rebrand |
| Return value | The `AnnotationBbox` | The caller can restyle or `.remove()` it. Matches matplotlib's artist-returning convention |
| Tinted mono variant (`color=`) | **Deferred** ([#72](https://github.com/bjlittle/tephpy/issues/72)) | Needs the mono SVGs rasterised offline; the light masters cannot serve as an alpha mask because they are three-tone with substantial white knockout (§8) |

(logo-spec-3)=
## 3. Architecture

```
src/tephpy/plotting/
├── logo.py                     # add_logo + the three lookup tables
└── _static/
    ├── icon-512-light.png      # 512 x 512
    ├── icon-512-dark.png
    ├── lockup-716-light.png    # 716 x 256
    ├── lockup-716-dark.png
    ├── stacked-512-light.png   # 512 x 720
    └── stacked-512-dark.png
```

One new module, one new package-data directory, one new public name. `logo.py` imports
nothing from tephpy beyond `_constants`; it does not touch `transforms`, `axes` or
`isopleths`, and nothing imports it back. `tephpy.plotting.__init__` grows
`from tephpy.plotting.logo import add_logo` and the matching `__all__` entry.

(logo-spec-3-1)=
### 3.1 Public API

```python
def add_logo(
    target: Figure | Axes | None = None,
    *,
    form: str = "lockup",
    size: str | float = "small",
    theme: str = "auto",
    loc: str | tuple[float, float] = "lower left",
    pad: float | None = None,
    zorder: float | None = None,
    **kwargs: Any,
) -> AnnotationBbox:
```

`pad` and `zorder` take `None` sentinels rather than literals because their values
are numeric conventions, and the rule in spec §3.5 is that nothing numeric is
hard-coded at point of use — a signature default is a point of use. They resolve to
`LOGO_PAD` (6.0) and `LOGO_ZORDER` (100.0) from `_constants`. The string defaults stay
literal: they are API vocabulary, not conventions, and reading them off the signature
is worth more than routing them through a constant.

| Parameter | Accepts | Meaning |
|---|---|---|
| `target` | `Figure`, `Axes`, `None` | What to brand, and what the position is relative to. `None` → the current figure (`plt.gcf()`) |
| `form` | `"lockup"`, `"icon"`, `"stacked"` | Which logo |
| `size` | `"small"`, `"large"`, or a float | Preset (§3.3) or an explicit **height in inches** |
| `theme` | `"auto"`, `"light"`, `"dark"` | Which variant; the name is the **background** the logo is drawn on |
| `loc` | ten `legend` strings, or `(x, y)` | Where (§3.4) |
| `pad` | float, `None` | Points between the logo and the target edge; `None` takes `LOGO_PAD`. Ignored when `loc` is a tuple |
| `zorder` | float, `None` | Draw order; `None` takes `LOGO_ZORDER`, which sits above lines (2), text (3) and legends (5) |
| `**kwargs` | `alpha`, `interpolation`, `resample`, `filternorm`, `filterrad` | Forwarded to `OffsetImage` |

`target=None` resolves through `plt.gcf()`, so `add_logo()` on its own brands the current
figure — the MetPy-equivalent zero-argument call.

The artist is attached with `fig.add_artist(ab)` for a `Figure` target and `ax.add_artist(ab)`
for an `Axes` target; the latter is what makes `xycoords="axes fraction"` resolvable.

(logo-spec-3-2)=
### 3.2 Bundled assets and packaging

The six masters are byte-for-byte copies of `bundle/png/` members of
`docs/src/_static/brand/assets/logo-bundle.zip`. They are resolved through one table so a
third variant can be added without touching the call site:

```python
_MASTERS = {
    ("icon", "light"): "icon-512-light.png",
    ("icon", "dark"): "icon-512-dark.png",
    ("lockup", "light"): "lockup-716-light.png",
    ("lockup", "dark"): "lockup-716-dark.png",
    ("stacked", "light"): "stacked-512-light.png",
    ("stacked", "dark"): "stacked-512-dark.png",
}
```

Loading is lazy, via `importlib.resources.files("tephpy.plotting") / "_static" / name`, read
with `matplotlib.image.imread`. Nothing is read at import time, so `import tephpy` costs
nothing extra and the module honours the existing import-discipline test at
`tests/plotting/test_isopleths.py:186`.

Packaging is declared explicitly:

```toml
[tool.setuptools.package-data]
tephpy = ["py.typed", "plotting/_static/*.png"]
```

`py.typed` is listed alongside because it currently ships with no declaration at all,
relying on the setuptools_scm file finder — the same implicit mechanism this table replaces
for the PNGs.

(logo-spec-3-3)=
### 3.3 Sizing

`size` is a **height in inches**. Width follows from the master's aspect ratio, so a form is
never distorted and the caller supplies one number.

| `form` | Master | Aspect (w/h) | `"small"` | `"large"` | Rendered at `"small"` |
|---|---|---|---|---|---|
| `lockup` | 716 × 256 | 2.797 | 0.30 in | 0.55 in | 0.84 × 0.30 in |
| `stacked` | 512 × 720 | 0.711 | 0.70 in | 1.15 in | 0.50 × 0.70 in |
| `icon` | 512 × 512 | 1.000 | 0.40 in | 0.70 in | 0.40 × 0.40 in |

The presets differ per form because the forms place the wordmark differently. Measured on the
light masters, the wordmark occupies **44.1%** of the lockup's height but only **17.8%** of
the stacked form's. Setting the `"small"` presets so the wordmark clears ~12 px at dpi 100
gives 13.2 px for the lockup at 0.30 in and 12.4 px for the stacked form at 0.70 in — the
stacked form needs 2.3× the height for the same legibility. A single shared preset would
either shrink the stacked wordmark to mush or make the lockup gratuitously large. `"large"`
is 1.6–1.8× `"small"` in each case. The icon carries no wordmark and so has no legibility
floor to meet; its presets sit between the other two forms'.

(logo-spec-3-4)=
### 3.4 Placement

`loc` takes matplotlib's `legend` vocabulary minus `'best'`: `'upper right'`, `'upper left'`,
`'lower left'`, `'lower right'`, `'right'`, `'center left'`, `'center right'`,
`'lower center'`, `'upper center'`, `'center'`. As in `legend`, `'right'` is a synonym for
`'center right'`, so the ten strings name nine positions. `'best'` is rejected with a message
saying so — this artist does no collision detection and silently aliasing it to a corner
would be a lie.

One table drives all of them: each string maps to an anchor in target-fraction coordinates, a
`box_alignment`, and the sign of the padding offset.

| `loc` | anchor `xy` | `box_alignment` | offset (points) |
|---|---|---|---|
| `lower left` | (0, 0) | (0, 0) | (+`pad`, +`pad`) |
| `lower right` | (1, 0) | (1, 0) | (−`pad`, +`pad`) |
| `upper left` | (0, 1) | (0, 1) | (+`pad`, −`pad`) |
| `upper right` | (1, 1) | (1, 1) | (−`pad`, −`pad`) |
| `lower center` | (0.5, 0) | (0.5, 0) | (0, +`pad`) |
| `upper center` | (0.5, 1) | (0.5, 1) | (0, −`pad`) |
| `center left` | (0, 0.5) | (0, 0.5) | (+`pad`, 0) |
| `center right`, `right` | (1, 0.5) | (1, 0.5) | (−`pad`, 0) |
| `center` | (0.5, 0.5) | (0.5, 0.5) | (0, 0) |

Anchoring the box's own corner to the matching target corner is what keeps the gap constant:
because `box_alignment` tracks the anchor, the offset is a pure inward push and never depends
on the logo's rendered size.

A tuple `loc=(x, y)` places the logo's **lower-left corner** at that point in target-fraction
coordinates — the same meaning `legend(loc=(x, y))` has — via `box_alignment=(0, 0)` and a
zero offset. `pad` is ignored in this case, and that is documented on the parameter rather
than raised as an error: the caller who gave exact coordinates has already said where they
want it.

`pad` defaults to 6.0 points, a shade wider than `legend`'s `borderaxespad` of 5.0 pt (0.5
font-size units at the 10 pt default font).

(logo-spec-3-5)=
### 3.5 Theme resolution

`theme="light"` and `theme="dark"` name the **background** the logo will sit on, which is
also how the asset filenames are named, so there is one vocabulary and no inversion to
remember.

`theme="auto"` reads the target's facecolor and picks by Rec. 709 luma over the
gamma-encoded sRGB channels (0.2126 R + 0.7152 G + 0.0722 B), choosing `dark` below 0.5
and `light` at or above it. This is luma, not relative luminance: the latter applies the
same weights but linearises each channel first, which scores mid grey `#808080` at 0.216
instead of 0.502 and so pulls the crossover well into the light half of the range.
Weighting the encoded values keeps the threshold where a reader would put it by eye,
which is all it has to do to choose between two artwork files. An
An `Axes` target is read from `ax.get_facecolor()` and a `Figure` from `fig.get_facecolor()`.
Because either may be translucent, they are alpha-composited back to front — an assumed white
page, then the figure, then the axes — and the luma is measured on the result, so the test
matches what shows through rather than what a layer's own channels say. Judging a layer alone
would score 10% black over a white figure at 0.0 and pick the dark mark for a background the
reader sees as near-white. The two ends of that range are the behaviour named above: a fully
transparent axes — `facecolor="none"` — contributes nothing and so falls through to the
figure, and if the figure is also transparent the assumed white page carries the answer,
`light`. A fully opaque layer hides everything under it exactly as before.

**Documented limitation:** `savefig(transparent=True)` does not change any facecolor; it
overrides alpha at draw time. `auto` therefore still sees white and picks `light`, which is
the right answer for a figure destined for a white page and the wrong one for a dark page.
Callers in that position pass `theme=` explicitly. Closing this properly is the deferred
`color=` work (§8).

(logo-spec-3-6)=
### 3.6 Rendering

```python
zoom = size_inches * 72 / master_height_px

AnnotationBbox(
    OffsetImage(arr, zoom=zoom, **image_kwargs),
    xy=anchor,
    xycoords="figure fraction",      # or "axes fraction"
    xybox=offset,
    boxcoords="offset points",
    box_alignment=alignment,
    frameon=False,
    pad=0.0,
    zorder=zorder,
    annotation_clip=False,
)
```

`OffsetImage`'s `zoom` is points-per-pixel, so `size_inches * 72 / master_height_px` renders
the master at exactly the requested height at any dpi. Verified at dpi 100/300/600: a 0.30 in
lockup measures 0.8391 × 0.3000 in every time, with the corner gap exactly 6.00 pt.

**`pad=0.0` is mandatory, not cosmetic.** `AnnotationBbox`'s default `pad=0.4` is in
font-size units — 4 pt per side at the 10 pt default — which inflates the rendered box by a
constant 0.111 in regardless of dpi or requested size. Left at the default, a `"small"`
lockup measures 0.411 in instead of 0.300 in and a `"large"` one 0.661 in instead of 0.550 in.
This is the single most easily reintroduced bug in the module and §6 pins it with a
regression test.

(logo-spec-4)=
## 4. Canonical usage

```python
import matplotlib.pyplot as plt
import tephpy
from tephpy.plotting import add_logo

fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
ax.plot(sounding.pressure, sounding.temperature)

add_logo(ax)                                        # lockup, small, auto theme, lower left
add_logo(fig, form="icon", loc="upper right")       # figure corner, not the plot's
add_logo(ax, size="large", loc=(0.35, 0.02))        # exact placement, pad ignored
add_logo(ax, theme="dark", alpha=0.6)               # explicit variant, watermark weight
```

(logo-spec-5)=
## 5. Error handling

The plotting layer raises builtin exceptions; `TephpyError` and its subclasses are for
user-correctable *data* input (parent spec §6) and are not used here.

- Unknown keyword → `TypeError` whose message contains `"unknown option"`, matching the
  convention asserted at `tests/plotting/test_isopleths.py:363`. `**kwargs` is validated
  against the allow-list in §3.1 **before** forwarding, because matplotlib's own failure for
  a bad `OffsetImage` kwarg is an `AttributeError` reading
  `BboxImage.set() got an unexpected keyword argument ...` — the wrong type and a message
  that names an artist the caller never mentioned.
- Unknown `form`, `theme`, or `loc` string → `ValueError` naming the valid set. `loc="best"`
  says explicitly that it is unsupported because no collision detection is performed.
- A `size` that is neither a preset name nor a positive finite float → `ValueError`.
- A `loc` that is neither a string nor a two-element sequence of floats → `TypeError`; a
  two-element sequence holding a non-finite value → `ValueError`. Coordinates outside
  `[0, 1]` are **allowed** — they place the logo outside the target box, which
  `annotation_clip=False` renders and which `legend` permits for the same reason.
- A `target` that is neither a `Figure` nor an `Axes` → `TypeError`. An `Axes` whose
  `.figure` is a `SubFigure` also raises `TypeError`: `SubFigure` is out of scope
  (§8), and saying so beats returning something typed `Figure` that is not one.

(logo-spec-6)=
## 6. Testing

Tests live in `tests/plotting/test_logo.py`, mirroring the source layout.

- **Tables:** every `_LOC` entry, every `(form, size)` preset, and every `theme` resolution
  is asserted, including `'right'` resolving identically to `'center right'`.
- **Sizing:** the rendered `AnnotationBbox` window extent equals the requested height in
  inches, asserted at dpi 100, 300 and 600 — the property MetPy's `figimage` approach
  cannot hold.
- **`pad=0.0` regression:** an explicit test pinning the exact rendered inches, which fails
  by a constant 0.111 in if the `pad=0.0` argument is ever dropped.
- **Placement:** corner gaps measure `pad` points exactly, across dpi and figsize; a tuple
  `loc` puts the lower-left corner where asked and ignores `pad`.
- **Target semantics:** an `Axes` target anchors to the axes box and a `Figure` target to the
  figure box, distinguishable because the two boxes differ.
- **Asset drift:** the six shipped PNGs hash equal to their `logo-bundle.zip` counterparts.
- **Packaging:** the six PNGs are present in a built wheel — the failure mode a source-tree
  test cannot see. It guards the *outcome*, not the mechanism: the mutation that fails it is
  removing an asset from the source tree, not deleting the `package-data` line, which
  `include-package-data` would cover for.
- **Errors:** each case in §5.
- **Import discipline:** `logo.py` reads no asset at import time.
- **Image baseline:** one `pytest-mpl` comparison, per parent spec §7.

(logo-spec-7)=
## 7. Documentation

- A how-to under `docs/src/howtos/`, added to that `toctree`, covering the default call, the
  three forms, dark figures, and exact placement.
- `add_logo` joins the API reference automatically through autoapi; its numpydoc docstring
  documents every parameter, the return, and each `raise`, per the repo's
  `numpydoc-validation` hook.
- `docs/src/_static/brand/assets/README.md` gains a line recording that six bundle members
  are also shipped inside the wheel at `tephpy/plotting/_static/`, so a future rebrand knows
  to update both.

(logo-spec-8)=
## 8. Scope

**In scope:** everything in §3.

**Deferred** ([#72](https://github.com/bjlittle/tephpy/issues/72)) — a `color=` kwarg tinting
a monochrome mark to an arbitrary colour. This is the honest fix for the
transparent-background case in §3.5 and for figures whose background is neither light nor
dark. It is deferred because it needs `lockup-tiera-mono.svg` and its siblings rasterised
**offline** into a third variant — tephpy cannot rasterise SVG at runtime (Pillow does not,
and the bundle's own generators emit SVG rather than consume it). The light masters cannot
substitute as an alpha mask:
measured, they are three-tone with substantial white knockout (19.2% of `icon-512-light.png`
is pure white), so flattening them by alpha collapses the mark.

**Rejected** (2026-08-01) — explicitly not in scope: collision detection (`loc="best"`),
animation, `SubFigure` targets, per-artist logo placement on subplots other than through
repeated calls, a `tephpy.config` section (this work adds exactly one public name), and any
change to the published brand assets. Each is a deliberate omission rather than an unbuilt
intention, so none carries an issue (docs spec §3.5).

(logo-spec-9)=
## 9. References

- Parent spec: [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md), spec §3.2
  (`plotting`), spec §6 (error handling), spec §7 (testing), spec §8
  (engineering standards)
- MetPy `add_metpy_logo`:
  <https://github.com/Unidata/MetPy/blob/v1.7.1/src/metpy/plots/_util.py#L106-L131>
- matplotlib `AnnotationBbox`:
  <https://matplotlib.org/stable/api/_as_gen/matplotlib.offsetbox.AnnotationBbox.html>
- matplotlib `OffsetImage`:
  <https://matplotlib.org/stable/api/_as_gen/matplotlib.offsetbox.OffsetImage.html>
- matplotlib `legend` `loc` vocabulary:
  <https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.legend.html>
- Brand assets and their provenance: `docs/src/_static/brand/assets/README.md` (PR #69)
