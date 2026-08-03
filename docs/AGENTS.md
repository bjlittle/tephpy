# Agent guidance — docs

Diátaxis quadrants under `docs/src/{tutorials,howtos,explanation,reference}`.
Theme is pydata-sphinx-theme. API reference is autoapi-generated — do not
hand-write it. Build with `pixi run docs` (fail-on-warning). Titles: CMOS
headline style; glossary entries are written for software engineers (see
`docs/src/developer/docs-style.rst`).

Design specs and implementation plans live under `docs/src/developer/{specs,
plans}` — not in a quadrant, which is user-facing. Specs are published and
carry `(spec-N)=` anchors keyed to the section number; plans are tracked but
excluded from the build by `exclude_patterns` and from the sdist by
`MANIFEST.in`. Conventions: `docs/src/developer/specs/2026-08-03-published-specs-design.md`.
