# Agent guidance — tests

pytest with strict config and `filterwarnings = ["error"]`. Image tests use
pytest-mpl (`@pytest.mark.mpl_image_compare`); CI and `pixi run tests` pass
`--mpl` so comparisons are enforced; baselines live in `tests/baseline` and
regenerate via `pixi run baselines` (regenerate whenever a lockfile bump
changes matplotlib or freetype, then re-verify all three test envs).
`pixi run tests-clean` removes test artifacts. Property tests use hypothesis.
