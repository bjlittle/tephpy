# Agent guidance — tests

The tests tree mirrors the `src/tephpy` package layout: tests for top-level
modules live at the `tests/` root, and each subpackage has a matching
directory (e.g. `tests/plotting/` for `tephpy.plotting`). Place new test
modules at the level of the module they exercise; shared `fixtures/` and
`baseline/` stay at the root.

pytest with strict config and `filterwarnings = ["error"]`. Image tests use
pytest-mpl (`@pytest.mark.mpl_image_compare`); CI and `pixi run tests` pass
`--mpl` so comparisons are enforced; baselines live in `tests/baseline` and
regenerate via `pixi run baselines` (regenerate whenever a lockfile bump
changes matplotlib or freetype, then re-verify all three test envs).
`pixi run tests-clean` removes test artifacts. Property tests use hypothesis.
