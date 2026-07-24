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
│   └── shading.py    # CAPE/CIN area fills, layer highlights
├── calc.py           # tephigram-native wrappers over metpy.calc
├── sounding.py       # Sounding dataclass (data + metadata, pint units)
├── io/
│   ├── wyoming.py    # University of Wyoming text reader
│   └── igra.py       # IGRA v2 reader
├── examples/         # sphinx-gallery sources (one per use case)
├── _constants.py     # conventions: intervals, extents, colours (overridable)
└── _version.py       # written by setuptools_scm (not committed)
```

**Dependency rule:** `transforms` ← `plotting` ← (`calc`, `sounding`, `io`).
`calc` never imports `plotting`; indices can be computed headless, and plotting works
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
curved families as zoom-aware artists (reimplementing tephi's locator/refresh design: isopleth
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

Comparing soundings is two `plot_sounding` calls with different styles; `set_anchor`
keeps extents identical across figures.

## 5. Units policy

Every public boundary accepts pint quantities and converts internally (hPa/°C are the
diagram's native units; K/Pa inputs just work). Bare arrays are accepted **only** with
an explicit `units=` argument — never silently assumed. Return values are always
quantities. This is a deliberate fix for tephi's hard-wired hPa/°C/knots.

One documented exemption: the `transforms` geometry layer (§3.1) trades in bare numpy
arrays in diagram-native units (hPa/°C), because matplotlib's per-draw transform
pipeline consumes bare arrays; every layer above it converts before calling down.

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
  contributor-hostile maintenance burden.
- **Calc:** test composition, not thermodynamics — parcel path passes through
  Normand's point; `indices()` fields equal direct `metpy.calc` calls on the same
  profile; the −25 mb correction applies only when requested. One integration test
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
- Runtime dependencies: matplotlib, numpy, scipy, pint, metpy. All are conda-forge
  packages, so pixi resolves them cleanly.
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
  `serve-html`, `doctest`, `lint` (pre-commit run). Matplotlib image baselines regenerated
  via a `tests --mpl-generate-path` task.
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
  know: tephigram, sounding, radiosonde, parcel, adiabat (dry/saturated), lapse rate
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
| 2 | Transforms & the tephigram projection | §3.1: T–ln θ math derived from published sources with tephi as oracle; minimal `TephigramAxes` + `"tephigram"` registration in `plotting/axes.py`; seeds `_constants` (MA, θ reference pressure, default extents); transform tests per §7; wheel-install smoke test in `ci-wheels` (item 15) | 1 | **next** |
| 3 | Isopleth plotting | §3.2 grid + five isopleth families as zoom-aware artists, accessor methods, `set_anchor`; §3.5 `_constants` + config object; pytest-mpl infrastructure + isopleth baselines (§8.5); vector-output smoke test (§9 "vector output" — PDF/SVG `savefig` of the first real diagram) | 2 | |
| 4 | Sounding data model & profile plotting | §3.4 `Sounding` dataclass (validation §6, constructors); the §5 units machinery incl. `TephpyUnitsError` and the shared exception module; `plot_profile` (quantities path), `plot_sounding`, multi-sounding overlay + legends (§1 item 4); profile image baselines | 3 | |
| 5 | Thermodynamic analysis | §3.3 `calc`: `parcel_path` (surface + mixed-layer parcels, −25 mb correction), `normand_point`, `indices`; the `Profile` type; analysis-time §6 errors (e.g. profile too short); `shade_cape`/`shade_cin`, `annotate_indices`; shading baselines; worked-example integration test (§7) | 3, 4 | |
| 6 | Wind barbs & data ingest | §3.2 `plot_barbs` (right-hand gutter staff, Met Office symbology); §3.4 `io` (`wyoming`, `igra`) with recorded-fixture tests; `TephpyIOError` (§6); barb baselines | 3, 4 | |
| 7 | Examples gallery & documentation completion | §8.6: sphinx-gallery examples (one per §1 use case, incl. the hodograph composition example from §9), `src/tephpy/examples`, tutorials/how-tos/explanation content, glossary completion, sphinx-tags, doctest task + CI doctest run; composed §4-figure baseline (§7 — needs the union of Plans 5 and 6); README non-goals statement and eccodes recipe how-to (§9) | 2–6 | |

Cross-cutting rules (apply to every plan rather than one row):

- **Image baselines ship with their feature.** §7/§8.5 enumerate baselines for the
  isopleth families, profiles, shading, barbs, and the composed §4 figure; each lands in
  the plan that builds the feature (3, 4, 5, 6, and 7 respectively, as tabled above).
- **Glossary entries ship with their terms.** The docs build is fail-on-warning, so a
  `:term:` reference written in Plan N breaks the build unless Plan N seeds the entry;
  "glossary completion" in Plan 7 is a sweep, not the sole delivery.
- **`_constants` accretes per feature.** Plan 3 establishes the module and config object;
  later plans add their own conventions (e.g. gutter width arrives with Plan 6's barbs).

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
   Plan 5 adds the `Profile` overload together with `calc.parcel_path`.
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
   canonical names (the glossary rule: one spelling per concept).
7. **Plan 3 — side-of-axes layout seam.** The barb gutter (Plan 6) and the indices panel
   (Plan 5) both need space beside the diagram; Plan 3 decides whether the axes pre-builds
   that layout or each consumer manages its own.
8. **Plan 4 — Sounding contract details.** Label/legend format (§4 hints
   `"03808 2026-07-21 12Z"`), station/time optionality (§3.4 states requiredness only for
   the data arrays), and how forecast-vs-observed overlays of the same station/time stay
   distinguishable in a legend.
9. **Plan 4 — pandas/xarray dependency status.** `from_dataframe`/`from_dataset` (§3.4)
   and the §2 ingest decision need pandas/xarray, but §8.1's runtime list omits them
   (today they arrive transitively via MetPy). Decide: direct declaration, optional
   extra, or typing-only treatment.
10. **Plan 4/5 — top-level namespace policy.** §4 requires `tephpy.calc.parcel_path` to
    work after `import tephpy`, implying eager subpackage import (and MetPy's import cost)
    or lazy loading; also which names (e.g. `Sounding`) re-export at top level.
11. **Plan 5 — MetPy behaviour verification.** §6 asserts NaN pass-through, but MetPy
    returns 0 (not NaN) for zero CAPE and warns on some degenerate profiles — and pytest's
    `filterwarnings = ["error"]` turns those warnings into failures. Verify the §6
    contract and the availability of `wet_bulb_potential_temperature`/`lifted_index`/
    `mixed_parcel` against the pinned floor (`metpy>=1.6`), adjusting §6 or the pin.
12. **Plan 5 — "layer highlights".** The §3 tree comment on `shading.py` names layer
    highlights, but no API, §9 scope item, or plan covers them; treated as not-in-v1
    unless Plan 5's design deliberately includes them.
13. **Plans 2/5/6 — third-party data provenance.** Any tephi artifacts actually copied
    (item 5), the §7
    published worked example (which publication, and is its data redistributable?), and
    recorded Wyoming/IGRA fixtures all embed external data; each owning plan records
    source, capture method, and attribution.
14. **scipy is declared but unowned.** §8.1 lists scipy as a runtime dependency, yet no §3
    module names it (plausible first consumers: interpolation in Plan 2 or Plan 5). If
    Plan 5 completes without it, drop the dependency.
15. **Residual Plan 1 deferrals**, re-homed: sphinx-tags (§8.6) → Plan 7; `doctest` task +
    `ci-docs` doctest run (§8.2/§8.7) → Plan 7; `tests-clean` task (§8.2, never
    implemented) → reconcile in Plan 3 when baselines make a clean/regenerate cycle real;
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
