# Contributing to tephpy

Thanks for your interest! Development uses [pixi](https://pixi.sh):

```bash
pixi install
pixi run tests    # run the test suite
pixi run lint     # run pre-commit
pixi run docs     # build the docs
```

Tests live in `tests/`, mirroring the `src/tephpy` package layout: tests for
top-level modules sit at the `tests/` root, and each subpackage has a matching
directory (e.g. `tests/plotting/` for `tephpy.plotting`). Please place new
test modules at the level of the module they exercise.

Every pull request adds a `changelog/<PR>.<type>.rst` news fragment, ending
with author attribution via the `:user:` extlink role, e.g.
``(:user:`bjlittle`)``. Titles in documentation follow Chicago Manual of Style
headline style (see `docs/src/developer/docs-style.rst`).
