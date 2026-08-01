# Brand assets

`logo-bundle.zip` is the complete generated brand asset set. The files alongside
it under `docs/src/_static/brand/` are the subset tephpy actually ships — every
one of them is byte-identical to its counterpart inside the bundle, so the
bundle is the source of truth and `brand/` is a published extract of it.

The bundle carries its own `bundle/README.md` documenting the design decisions:
the three size tiers, the palette, why the type is outlined rather than
webfont-linked, and how to regenerate everything. Read that before changing any
artwork. What follows is only the mapping between the two.

## What is published

tephpy publishes **tier A only**, in light and dark. Tier A is the full-lattice
drawing, intended for 48px and above — which is every context tephpy renders a
logo in.

| Published under `brand/` | From the bundle | Used by |
|---|---|---|
| `svg/lockup-tiera-{light,dark}.svg` | `bundle/svg/` | `docs/src/conf.py` — `html_theme_options["logo"]` |
| `svg/stacked-tiera-{light,dark}.svg` | `bundle/svg/` | root `README.md` banner (`<picture>` sources) |
| `svg/icon-tiera-{light,dark}.svg` | `bundle/svg/` | unused; kept as the square-format mark |
| `png/lockup-{179,358}-{light,dark}.png` | `bundle/png/` | raster fallback, @1x/@2x of the native 179×64 |
| `png/stacked-{64,128,256}-{light,dark}.png` | `bundle/png/` | `stacked-256-light.png` is the root `README.md` `<img>` fallback |
| `png/icon-{64,128}-{light,dark}.png` | `bundle/png/` | unused; raster square mark |
| `favicon-48x48.png` | `bundle/favicon/` | `docs/src/conf.py` — `html_favicon` |
| `favicon.ico` | `bundle/favicon/` | unused; multi-resolution 16/32/48 |

Filenames encode the rendered pixel width, and the three forms have fixed
aspect ratios: icon 1:1 (64×64), lockup 179:64, stacked 64:90. So
`stacked-256-light.png` is 256×360, and `lockup-358-dark.png` is 358×128.

## What the wheel ships

`tephpy.plotting.add_logo` draws from six masters copied into the package under
`src/tephpy/plotting/_static/`, so the function works from a wheel with no docs
tree and no network:

| In the package | From the bundle |
|---|---|
| `icon-512-{light,dark}.png` | `bundle/png/` |
| `lockup-716-{light,dark}.png` | `bundle/png/` |
| `stacked-512-{light,dark}.png` | `bundle/png/` |

These are the largest raster of each form, downscaled at draw time to the height
in inches the caller asks for. Like everything else here they are byte-identical
to the bundle, and `tests/plotting/test_logo.py` hashes them against it — the
snippet below covers `brand/` only, because it matches on basename within that
directory.

## What the bundle has that `brand/` does not

- **Tiers B and C** — reduced-lattice and no-lattice drawings for 24–32px and
  20px and below. Nothing tephpy renders is that small, except the favicon,
  which takes its per-tier art pre-composited inside `favicon.ico`.
- **Mono variants** — single `currentColor`, the only files that are genuinely
  background-independent. Reach for these before recolouring a light or dark
  file, whose halos assume a background value.
- **Larger sizes** — icon at 256. The 512/716 masters are not published under
  `brand/`; they ship inside the wheel instead (see below).
- **The rest of the favicon set** — 16/32px PNGs, a theme-aware `favicon.svg`,
  `apple-touch-icon.png` and `site.webmanifest`. `html_favicon` accepts one
  file, so shipping the others would need a custom `layout.html`.
- **The generator scripts** — `build_bundle.py`, `build_stacked.py`,
  `fix_mono.py`, `mkword.py`. SVG paths are machine-generated: change the
  wordmark by re-running the build, never by hand-editing a published file.

## Verifying the extract

Published files should stay byte-identical to the bundle. To check after any
change:

```python
import hashlib, pathlib, zipfile

brand = pathlib.Path("docs/src/_static/brand")
live = {
    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
    for p in brand.rglob("*")
    if p.is_file() and "assets" not in p.parts
}
with zipfile.ZipFile(brand / "assets/logo-bundle.zip") as zf:
    zipped = {
        pathlib.Path(i.filename).name: hashlib.sha256(zf.read(i)).hexdigest()
        for i in zf.infolist()
        if not i.is_dir()
    }
for name, digest in sorted(live.items()):
    assert zipped.get(name) == digest, f"{name} has drifted from the bundle"
```

## Sphinx

This directory is kept out of the built site by `exclude_patterns` in
`docs/src/conf.py`. Sphinx never treats these files as *pages* — it feeds
`html_static_path` into the document-discovery exclusion matcher, so a `.md`
here is not parsed and does not need an `:orphan:` marker. Without the
exclusion it would simply be **copied verbatim** into the built HTML, publishing
this README and a 270 KiB zip that nothing links to.

The pattern is `brand/assets/*`, with no `_static/` prefix: static-file copying
matches each entry relative to the `html_static_path` root, so
`_static/brand/assets/*` matches nothing and the zip ships anyway.
