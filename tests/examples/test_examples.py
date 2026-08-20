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

#: The guard of gallery spec §3.3, as ``ast.unparse`` renders its test. The
#: module-level ``if TYPE_CHECKING:`` block is also an ``ast.If``, so the
#: comparison has to be against the test rather than against the node kind.
_GUARD = "__name__ == '__main__'"

#: What the guard calls, in order (gallery spec §3.3). Asserting the calls and
#: not merely the guard is the point: a guard that ran something else, or
#: nothing, would draw no figure for sphinx-gallery to scrape, and the page
#: would publish the ``no_image.png`` placeholder without a warning to fail
#: ``--fail-on-warning`` on.
GUARD_CALLS = ["main", "plt.show"]

#: The figure size of gallery spec §3.5, inherited from plots spec §3.1.
FIGSIZE = (8.0, 4.0)

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


def read_guard(source: str) -> list[str]:
    """Return the calls an example's ``__main__`` guard makes, in order.

    Parameters
    ----------
    source : str
        The example module's text.

    Returns
    -------
    list of str
        The dotted name of each call in the guard's body, empty when the
        module declares no guard at all.
    """
    for node in ast.parse(source).body:
        if not isinstance(node, ast.If) or ast.unparse(node.test) != _GUARD:
            continue
        return [
            ast.unparse(statement.value.func)
            for statement in node.body
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
        ]
    return []


@pytest.mark.parametrize("module", [module for _, module in REGISTRY])
def test_example_runs(module):
    """Every registered example builds a figure, at the gallery's size.

    A broken example then fails the test suite across the supported
    Pythons, not only the documentation build. The size is the example's
    own because sphinx-gallery calls ``plt.rcdefaults()`` before each one,
    so nothing outside the file can hold it (gallery spec §3.5).
    """
    figure = import_module(f"tephpy.examples.{module}").main()
    assert figure.axes
    assert tuple(figure.get_size_inches()) == FIGSIZE
    plt.close(figure)


@pytest.mark.parametrize("module", [module for _, module in REGISTRY])
def test_example_guard_draws(module):
    """Every example closes with the guard, calling ``main`` then ``show``.

    Nothing else catches its loss. The suite calls ``main()`` directly, and
    sphinx-gallery executing a file whose guard has gone finds no figure
    and publishes the page with a placeholder image — a supported case it
    emits no warning for, so ``--fail-on-warning`` cannot see it either
    (gallery spec §3.3).
    """
    guard = read_guard((EXAMPLES / f"{module}.py").read_text())
    assert guard == GUARD_CALLS, f"{module} guard calls {guard}"


def test_registry_covers_the_directory():
    """Every ``plot_*.py`` is registered, and every registration exists."""
    found = {path.stem for path in EXAMPLES.glob("plot_*.py")}
    assert found == {module for _, module in REGISTRY}


def test_registry_names_drop_the_prefix():
    """The command-line name is the module's, without ``plot_``."""
    assert all(module == f"plot_{name.replace('-', '_')}" for name, module in REGISTRY)


@pytest.mark.parametrize("module", [module for _, module in REGISTRY])
def test_example_tags_are_declared_and_in_vocabulary(module):
    """Each example declares two to four tags, all from the vocabulary.

    An empty list is the failure a misspelled flag produces: sphinx-gallery
    parses ``sphinx_gallery_tag`` into a differently-keyed entry and
    discards it without a warning, so the documentation build cannot report
    it. Two to four is gallery spec §3.6's own bound: one tag files an
    example under a single button, and a full house of them files it under
    every one, either way telling the index's filter nothing.
    """
    tags = read_tags((EXAMPLES / f"{module}.py").read_text())
    assert tags, f"{module} declares no sphinx_gallery_tags"
    assert 2 <= len(tags) <= 4, f"{module} declares {len(tags)} tags: {tags}"
    assert set(tags) <= VOCABULARY, sorted(set(tags) - VOCABULARY)


@pytest.mark.mpl_image_compare
def test_parcel_analysis_figure():
    """Pin spec §4's composed figure, which spec §7 has always required."""
    return import_module("tephpy.examples.plot_parcel_analysis").main()
