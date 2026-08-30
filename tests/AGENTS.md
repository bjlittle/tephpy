# Agent guidance — tests

The tests tree mirrors the `src/tephpy` package layout: tests for top-level
modules live at the `tests/` root, and every subpackage has a matching
directory (`tests/plotting/` ↔ `tephpy.plotting`) however few modules it
carries — `tephpy.samples` is a lone `__init__.py` and still has
`tests/samples/`. Place new test modules at the level of the module they
exercise; shared `fixtures/` and `baseline/` stay at the root.
`tests/test_layout.py` holds the tree to this, so a subpackage arriving
without its directory fails a test rather than waiting to be noticed
(spec §8.5).

pytest with strict config and `filterwarnings = ["error"]`. Image tests use
pytest-mpl (`@pytest.mark.mpl_image_compare`); CI and `pixi run tests` pass
`--mpl` so comparisons are enforced; baselines live in `tests/baseline` and
regenerate via `pixi run baselines` (regenerate whenever a lockfile bump
changes matplotlib or freetype, then re-verify all three test envs).
`pixi run tests-clean` removes test artifacts. Property tests use hypothesis.
