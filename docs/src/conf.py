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

# -- numpydoc ----------------------------------------------------------------
numpydoc_show_class_members = False

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
    "numpy": ("https://numpy.org/doc/stable/", None),
    "python": ("https://docs.python.org/3/", None),
}

# -- HTML output -------------------------------------------------------------
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_title = "tephpy"
html_theme_options = {
    "github_url": "https://github.com/bjlittle/tephpy",
    "navbar_align": "left",
}

nitpicky = False
