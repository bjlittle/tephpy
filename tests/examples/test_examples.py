# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The gallery examples and the registry over them (gallery spec §3.7)."""

from __future__ import annotations

import ast
from importlib import import_module
from pathlib import Path
import re

import matplotlib.pyplot as plt
import pytest

from tephpy import examples
from tephpy.examples import REGISTRY

#: The tag vocabulary of gallery spec §3.6. A tag outside it splits the
#: gallery's own filter, which is the whole reason the tags exist.
VOCABULARY = frozenset(
    {
        "analysis",
        "barbs",
        "diagram",
        "indices",
        "isopleths",
        "metpy",
        "overlay",
        "shading",
        "sounding",
    }
)

#: sphinx-gallery reads exactly this flag and silently discards any other
#: spelling, so this pattern is deliberately as strict as its parser
#: (gallery spec §3.6). Reading the text rather than importing
#: sphinx_gallery is what makes the assertion run in CI: the test
#: environments have no documentation dependencies.
_TAGS = re.compile(r"^# sphinx_gallery_tags = (?P<value>\[.*\])$", re.MULTILINE)

EXAMPLES = Path(examples.__file__).parent


def read_tags(source: str) -> list[str]:
    """Return the tags an example declares.

    Parameters
    ----------
    source : str
        The example module's text.

    Returns
    -------
    list of str
        The declared tags, empty if the file declares none.
    """
    match = _TAGS.search(source)
    if match is None:
        return []
    return ast.literal_eval(match.group("value"))


@pytest.mark.parametrize("module", [module for _, module in REGISTRY])
def test_example_runs(module):
    """Every registered example builds a figure.

    A broken example then fails the test suite across the supported
    Pythons, not only the documentation build.
    """
    figure = import_module(f"tephpy.examples.{module}").main()
    assert figure.axes
    plt.close(figure)


def test_registry_covers_the_directory():
    """Every ``plot_*.py`` is registered, and every registration exists."""
    found = {path.stem for path in EXAMPLES.glob("plot_*.py")}
    assert found == {module for _, module in REGISTRY}


def test_registry_names_drop_the_prefix():
    """The command-line name is the module's, without ``plot_``."""
    assert all(module == f"plot_{name.replace('-', '_')}" for name, module in REGISTRY)


@pytest.mark.parametrize("module", [module for _, module in REGISTRY])
def test_example_tags_are_declared_and_in_vocabulary(module):
    """Each example declares tags, all of them from the vocabulary.

    An empty list is the failure a misspelled flag produces: sphinx-gallery
    parses ``sphinx_gallery_tag`` into a differently-keyed entry and
    discards it without a warning, so the documentation build cannot report
    it (gallery spec §3.6).
    """
    tags = read_tags((EXAMPLES / f"{module}.py").read_text())
    assert tags, f"{module} declares no sphinx_gallery_tags"
    assert set(tags) <= VOCABULARY, sorted(set(tags) - VOCABULARY)


@pytest.mark.mpl_image_compare
def test_parcel_analysis_figure():
    """Pin spec §4's composed figure, which spec §7 has always required."""
    return import_module("tephpy.examples.plot_parcel_analysis").main()
