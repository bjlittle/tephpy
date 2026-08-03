# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Sphinx configuration for the tephpy documentation."""

from __future__ import annotations

from importlib.metadata import version as _dist_version

project = "tephpy"
author = "tephpy Contributors"
copyright = "2026, tephpy Contributors"
release = _dist_version("tephpy")
version = ".".join(release.split(".")[:2])

extensions = [
    "autoapi.extension",
    "myst_nb",
    "numpydoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_changelog",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_gallery.gen_gallery",
    "sphinx_togglebutton",
    "sphinxcontrib.bibtex",
]

# -- autoapi -----------------------------------------------------------------
autoapi_type = "python"
autoapi_dirs = ["../../src/tephpy"]
autoapi_root = "reference/generated/api"
autoapi_ignore = ["*/_version.py", "*/examples/*"]
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]
autoapi_add_toctree_entry = (
    False  # nav is the five Diátaxis entries; API lives under Reference
)
autoapi_keep_files = False
suppress_warnings = ["autoapi.python_import_resolution"]

# -- extlinks ----------------------------------------------------------------
extlinks = {
    "issue": ("https://github.com/bjlittle/tephpy/issues/%s", "#%s"),
    "pull": ("https://github.com/bjlittle/tephpy/pull/%s", "#%s"),
    "user": ("https://github.com/%s", "@%s"),
}

# -- numpydoc ----------------------------------------------------------------
numpydoc_show_class_members = False
# Cross-reference parameter/return types (see developer/docs-style). Full
# dotted names (``pint.Quantity``, ``numpy.ndarray``, ``metpy.calc.*``) resolve
# through intersphinx; map short type names — numpy's ``ArrayLike`` typing
# alias and tephpy's own classes — to their fully-qualified targets, and skip
# the descriptive connective words.
numpydoc_xref_param_type = True
numpydoc_xref_aliases = {
    "ArrayLike": "numpy.typing.ArrayLike",
    "Sounding": "tephpy.sounding.Sounding",
    "Profile": "tephpy.calc.Profile",
    "SoundingIndices": "tephpy.calc.SoundingIndices",
    "FamilySpec": "tephpy.plotting.isopleths.FamilySpec",
    "IsoplethFamily": "tephpy.plotting.isopleths.IsoplethFamily",
    "Member": "tephpy.plotting.isopleths.Member",
    "TephpyError": "tephpy.exceptions.TephpyError",
    "TephpyUnitsError": "tephpy.exceptions.TephpyUnitsError",
    "TephpyValidationError": "tephpy.exceptions.TephpyValidationError",
    "NonMonotonicPressureError": "tephpy.exceptions.NonMonotonicPressureError",
    "DewpointExceedsTemperatureError": (
        "tephpy.exceptions.DewpointExceedsTemperatureError"
    ),
    "MissingDataError": "tephpy.exceptions.MissingDataError",
    "ProfileTooShortError": "tephpy.exceptions.ProfileTooShortError",
    "TephpyIOError": "tephpy.exceptions.TephpyIOError",
    "BarbStaff": "tephpy.plotting.barbs.BarbStaff",
}
numpydoc_xref_ignore = {"default", "mapping", "of", "optional", "or", "to"}

# -- bibtex ------------------------------------------------------------------
bibtex_bibfiles = ["refs.bib"]

# -- sphinx-gallery ----------------------------------------------------------
sphinx_gallery_conf = {
    "examples_dirs": [],
    "gallery_dirs": [],
}

# -- myst-nb -----------------------------------------------------------------
nb_execution_mode = "off"

# -- intersphinx -------------------------------------------------------------
intersphinx_mapping = {
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "metpy": ("https://unidata.github.io/MetPy/latest/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "pint": ("https://pint.readthedocs.io/en/stable/", None),
    "python": ("https://docs.python.org/3/", None),
    "xarray": ("https://docs.xarray.dev/en/stable/", None),
}

# -- HTML output -------------------------------------------------------------
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
# The brand asset bundle and its README are repository files, not site content.
# Sphinx already keeps ``html_static_path`` out of *document* discovery, so this
# is purely to stop ``copy_html_static_files`` publishing a 270 KiB zip nothing
# links to.  The pattern is deliberately not prefixed ``_static/``: static
# copying matches each entry relative to the ``html_static_path`` root, so an
# ``_static/``-prefixed pattern silently matches nothing and the zip ships.
# ``developer/plans/*`` is the second entry for a different reason: the plans are
# tracked in the repository but deliberately unpublished (docs spec §3.1) — a plan
# is a point-in-time record, not a living document.
exclude_patterns = ["brand/assets/*", "developer/plans/**"]
html_favicon = "_static/brand/favicon-48x48.png"
html_theme_options = {
    "github_url": "https://github.com/bjlittle/tephpy",
    "logo": {
        "image_light": "_static/brand/svg/lockup-tiera-light.svg",
        "image_dark": "_static/brand/svg/lockup-tiera-dark.svg",
    },
    "navbar_align": "left",
}

# -- nitpicky ----------------------------------------------------------------
# Fail the build on any unresolved cross-reference (see developer/docs-style;
# enforced through the docs Makefile's --fail-on-warning). The entries below
# are the irreducible exceptions that no config can resolve: autoapi renders
# these annotation types as ``py:class`` xrefs, but numpy publishes them as
# ``py:data``/``py:attribute`` (a role mismatch); ``Ellipsis`` is the ``...``
# in variadic tuples, which has no target; and ``MOIST_ADIABAT_TRUNCATION`` is
# a parameter default from the private ``_constants`` module, which is not part
# of the rendered API.
nitpicky = True
nitpick_ignore = [
    ("py:class", "numpy.typing.ArrayLike"),
    ("py:class", "numpy.typing.NDArray"),
    ("py:class", "numpy.float64"),
    ("py:class", "numpy.bool_"),
    ("py:class", "Ellipsis"),
    ("py:obj", "MOIST_ADIABAT_TRUNCATION"),
]
