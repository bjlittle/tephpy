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

from tests.by_path import SCRIPTS, load_script

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


@pytest.fixture(scope="session")
def gate():
    """Import the API docstring gate, a script rather than an installed module.

    Skipped where ``.github`` is absent -- an export, or a copy taken without
    its dotted directories -- rather than left to raise. A fixture that raises
    reports an *error* on every test asking for it, and fifty-two errors say
    the suite is broken where fifty-two skips say the gate is not here to run
    (floors spec §5 makes the same distinction for a module-level guard).

    Returns
    -------
    module
        ``.github/scripts/check_api_docstrings.py``, executed.
    """
    script = SCRIPTS / "check_api_docstrings.py"
    if not script.is_file():
        pytest.skip("not a checkout of the repository")
    return load_script("check_api_docstrings")
