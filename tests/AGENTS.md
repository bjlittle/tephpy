# Agent guidance — tests

pytest with strict config and `filterwarnings = ["error"]`. Image tests use
pytest-mpl (`@pytest.mark.mpl_image_compare`); baselines regenerate via
`pixi run tests-mpl-generate`. Property tests use hypothesis.
