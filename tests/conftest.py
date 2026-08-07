# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Pytest configuration: non-interactive backend, pristine configuration.

``tephpy`` auto-loads a configuration file at import, so a developer with
their own ``tephpyrc.yaml`` would otherwise feed it into every image
comparison — and with ``filterwarnings = ["error"]`` a single unknown key in
it would become a collection error. Importing inside ``catch_warnings`` and
resetting immediately removes both, without depending on when pytest
installs its own filters (configfile spec §6).
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
