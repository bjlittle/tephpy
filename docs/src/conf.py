# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Sphinx configuration for the tephpy documentation."""

from __future__ import annotations

from importlib.metadata import version as _dist_version
from pathlib import Path
import sys

# ``docs/src/_ext`` holds the citation cross-reference extension (docs spec §3.7)
# and the grammar it shares with the pre-commit gate of docs spec §3.6. It is a
# ``sys.path`` entry rather than a package: Sphinx resolves an extension by
# top-level module name.
sys.path.insert(0, str(Path(__file__).parent / "_ext"))

project = "tephpy"
author = "tephpy Contributors"
copyright = "2026, tephpy Contributors"
release = _dist_version("tephpy")
version = ".".join(release.split(".")[:2])

extensions = [
    "tephpy_citation_xrefs",
    "autoapi.extension",
    "matplotlib.sphinxext.plot_directive",
    "myst_nb",
    "numpydoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_changelog",
    "sphinx_click",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_gallery.gen_gallery",
    "sphinx_togglebutton",
    "sphinxcontrib.bibtex",
    "tephpy_config_reference",
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
# Sphinx's own check on the docs spec §3.8 rule, and deliberately a second
# implementation of it rather than one shared with the pre-commit gate: a bug in that
# gate's pattern is what an independent matcher catches. It is safe to enable only
# because Sphinx declines to suggest a replacement when the captured value carries a
# solidus -- without that guard the `user` role's bare `%s` matches every link to
# another project's repository, and this build fails on warnings.
extlinks_detect_hardcoded_links = True

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

# -- plot_directive ----------------------------------------------------------
# Renders the how-to snippets as figures (plots spec §3.1). Each setting below
# changes a default that is wrong for a page whose subject is the picture: the
# source is the point, so it is shown; and the source link and the format links
# both offer a download of something already on the page.
plot_include_source = True
plot_html_show_source_link = False
plot_html_show_formats = False
# One format, because the two settings above leave `hires.png` and `pdf`
# unlinked. The trailing dpi is the figure's, matching `tests/baseline`.
plot_formats = [("png", 100)]
# The figure size half of the recipe in plots spec §4. A tephigram's axes is a
# wide, short parallelogram, so at matplotlib's square default most of the
# canvas is empty and an emphasised member is lost in the five-family grid.
# Deliberately *not* `savefig.bbox: "tight"`, which plots spec §4 also names:
# an `add_logo(fig, ...)` logo is a figure-anchored `AnnotationBbox`, outside
# the axes it measures, and is invisible to matplotlib's tight-bbox
# calculation -- rendering the logo how-to's figure-anchored section both
# ways shows that logo cropped away entirely under `"tight"`, while an
# axes-anchored logo survives. The logo how-to's first section teaches
# exactly that figure placement, so `plot_rcparams` carries the figure size
# only.
plot_rcparams = {"figure.figsize": (8.0, 4.0)}
# Restores those rcParams between blocks, so a page that sets a matplotlib style
# cannot leak it into the next page built. It covers matplotlib state only --
# `tephpy.config` is module state and survives it, which is why a published block
# may not leave it mutated (plots spec §3.3).
plot_apply_rcparams = True
# Without this the directive runs each block from the *page's own source
# directory*, so a snippet that writes a file -- `fig.savefig("sounding.png")`,
# say -- writes into the checked-out documentation tree, where the next build
# then finds it. Redirect the writes to a scratch directory under the
# git-ignored build tree instead. It is also prepended to `sys.path`; keeping
# it empty of modules is why it is a dedicated directory rather than `_build`
# itself.
_plot_scratch = Path(__file__).parent.parent / "_build" / "plot-scratch"
_plot_scratch.mkdir(parents=True, exist_ok=True)
plot_working_directory = str(_plot_scratch)

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
html_css_files = ["browser-toolbar.css"]
# The docs Makefile builds the current checkout's wheel and stages the complete
# browser application one directory above the Sphinx source tree. Sphinx copies
# that staging root verbatim, making its ``browser`` child available at
# ``/browser/`` without committing any generated wheel.
html_extra_path = ["../_build/browser"]
# The brand asset bundle and its README are repository files, not site content.
# Sphinx already keeps ``html_static_path`` out of *document* discovery, so this
# is purely to stop ``copy_html_static_files`` publishing a 270 KiB zip nothing
# links to.  The pattern is deliberately not prefixed ``_static/``: static
# copying matches each entry relative to the ``html_static_path`` root, so an
# ``_static/``-prefixed pattern silently matches nothing and the zip ships.
# ``developer/plans/**`` is the second entry for a different reason: the plans are
# tracked in the repository but deliberately unpublished (docs spec §3.1) — a plan
# is a point-in-time record, not a living document.  It is ``**`` rather than ``*``
# because Sphinx compiles ``*`` to ``[^/]*``, which does not cross a ``/``, while
# ``MANIFEST.in``'s ``prune docs/src/developer/plans`` is recursive: under ``*`` a
# plan filed in a subdirectory would be pruned from the sdist yet published on the
# site — the asymmetry, in the direction that leaks.
exclude_patterns = ["brand/assets/*", "developer/plans/**"]
html_favicon = "_static/brand/favicon-48x48.png"
# pydata-sphinx-theme 0.20 reads ``default_mode`` as a template context value
# (not a theme option). Without it the freshly loaded page logs an invalid empty
# mode before a reader has chosen and persisted one.
html_context = {"default_mode": "auto"}
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
