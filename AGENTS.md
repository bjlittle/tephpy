# Agent guidance — tephpy

`tephpy` plots and analyses tephigrams. Layered architecture: `transforms`
(T–ln θ math + Matplotlib projection) ← `plotting` ← (`calc`, `sounding`,
`io`). Thermodynamics is delegated to MetPy; units are pint quantities.

- Environments and tasks: pixi (`pixi run tests`, `pixi run lint`, `pixi run docs`).
- Every source file carries the BSD copyright header (ruff `CPY001`).
- Every PR adds a `changelog/<PR>.<type>.rst` fragment.
- Docs follow Diátaxis; titles use CMOS headline style (`docs/src/developer/docs-style.rst`).
