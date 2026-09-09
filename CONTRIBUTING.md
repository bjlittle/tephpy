# Contributing to tephpy

The full contributor guide is published with the documentation:

- [Contributing](https://tephpy.readthedocs.io/en/latest/developer/contributing.html) — getting an environment, and what to run
- [Testing](https://tephpy.readthedocs.io/en/latest/developer/testing.html) — the tests tree, and image comparison
- [Changelog fragments](https://tephpy.readthedocs.io/en/latest/developer/changelog.html) — what every pull request adds
- [Continuous integration](https://tephpy.readthedocs.io/en/latest/developer/ci.html) — what runs, and what a failure means

The short version. Development uses [pixi](https://pixi.sh):

```bash
pixi run tests      # run the test suite
pixi run lint       # run pre-commit
pixi run docs       # build the docs, then check the HTML the build produced
pixi run docs-all   # ...and check the browser demo, as CI does
```

`pixi run docs-all` needs a browser pixi does not install. Run
`pixi run -e docs playwright install chromium` once; on Linux the browser also needs
system libraries, which `pixi run -e docs playwright install --with-deps chromium` adds
as root.

Every pull request adds a `changelog/<PR>.<type>.rst` news fragment ending with author
attribution via the `:user:` extlink role.
