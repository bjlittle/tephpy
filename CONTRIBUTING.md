# Contributing to tephpy

Thanks for your interest! Development uses [pixi](https://pixi.sh):

```bash
pixi install
pixi run tests      # run the test suite
pixi run lint       # run pre-commit
pixi run docs-html  # build the docs
pixi run docs       # build the docs, then check the HTML the build produced
pixi run docs-all   # ...and check the browser demo, as CI does
```

`pixi run docs` is the check to reach for. `pixi run docs-all` adds the one
gate it leaves out — a smoke test of the PyScript demo in Chromium, which the
`docs` environment installs Playwright for but does not carry a browser for.
Run it once with `pixi run -e docs playwright install chromium`; on Linux the
browser also needs system libraries pixi does not provide, which
`pixi run -e docs playwright install --with-deps chromium` adds as root. Both
go through pixi because Playwright is installed into the `docs` environment
and is on no other `PATH`. If the browser will not start, the check says which
of the two is missing, and names it the same way.

Tests live in `tests/`, mirroring the `src/tephpy` package layout: tests for
top-level modules sit at the `tests/` root, and each subpackage has a matching
directory (e.g. `tests/plotting/` for `tephpy.plotting`). Please place new
test modules at the level of the module they exercise.

Every pull request adds a `changelog/<PR>.<type>.rst` news fragment, ending
with author attribution via the `:user:` extlink role, e.g.
``(:user:`bjlittle`)``. Titles in documentation follow Chicago Manual of Style
headline style (see `docs/src/developer/docs-style.rst`).
