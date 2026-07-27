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
# through intersphinx; map tephpy's own short type names to their
# fully-qualified targets, and skip the descriptive connective words.
numpydoc_xref_param_type = True
numpydoc_xref_aliases = {
    "Sounding": "tephpy.sounding.Sounding",
    "Profile": "tephpy.calc.Profile",
    "SoundingIndices": "tephpy.calc.SoundingIndices",
    "FamilySpec": "tephpy.plotting.isopleths.FamilySpec",
    "Member": "tephpy.plotting.isopleths.Member",
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
html_favicon = "_static/brand/favicon.png"
html_theme_options = {
    "github_url": "https://github.com/bjlittle/tephpy",
    "logo": {
        "image_light": "_static/brand/logo-flat-light.svg",
        "image_dark": "_static/brand/logo-flat-dark.svg",
    },
    "navbar_align": "left",
}

nitpicky = False
