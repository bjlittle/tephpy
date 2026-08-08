# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Pytest configuration: non-interactive backend, pristine configuration.

``tephpy`` auto-loads a configuration file at import, so a developer with
their own ``tephpyrc.yaml`` would otherwise feed it into every image
comparison. The autouse ``_pristine_config`` fixture is what keeps the file
out of every test; the module-scope ``reset()`` covers only what runs
before the first fixture — anything at import time. Importing inside
``catch_warnings`` keeps whatever that import warns about out of
collection, without depending on when pytest installs its own filters. An
unknown key in the file is no longer among those warnings:
``tephpy._autoload_config`` forces tephpy's own configuration warnings to
"always" for the duration of the auto-load, so ``filterwarnings =
["error"]`` can never raise one (configfile spec §6).
"""

from __future__ import annotations

import warnings

import matplotlib as mpl
import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import tephpy

tephpy.config.reset()

mpl.use("Agg")


@pytest.fixture(autouse=True)
def _pristine_config():
    """Reset ``tephpy.config`` around every test.

    Yields
    ------
    None
        Control, with the configuration pristine.
    """
    tephpy.config.reset()
    yield
    tephpy.config.reset()
