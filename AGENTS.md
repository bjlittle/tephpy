# Agent guidance — tephpy

`tephpy` plots and analyses tephigrams. Layered architecture: `transforms`
(T–ln θ math + Matplotlib projection) ← `plotting` ← (`calc`, `sounding`,
`io`). Thermodynamics is delegated to MetPy; units are pint quantities.

- Environments and tasks: pixi (`pixi run tests`, `pixi run lint`, `pixi run docs`; `pixi run docs-all` adds the browser demo, which needs a Chromium installed by hand).
- The tests tree mirrors the `src/tephpy` package layout (`tests/plotting/` ↔ `tephpy.plotting`; see `tests/AGENTS.md`).
- Every source file carries the BSD copyright header (ruff `CPY001`).
- Every PR adds a `changelog/<PR>.<type>.rst` fragment, ending with ``(:user:`<github-username>`)`` attribution.
- Docs follow Diátaxis; titles use CMOS headline style (`docs/src/developer/docs-style.rst`).
- Design specs and implementation plans live under `docs/src/developer/{specs,plans}` — specs are published in the docs build, plans are excluded by `exclude_patterns` and `MANIFEST.in`. This overrides the superpowers skills' default of `docs/superpowers/{specs,plans}/`; write new specs and plans to the paths above, not to that default.
- Specs are living documents, maintained alongside the code; plans are point-in-time records, frozen once their implementation PR merges (docs spec §3.4). Both conventions are stated in `docs/src/developer/specs/2026-08-03-published-specs-design.md`.
