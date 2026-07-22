# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Smoke tests for the tephpy package skeleton."""

from __future__ import annotations

import tephpy


def test_package_imports() -> None:
    """tephpy imports and exposes a non-empty version string."""
    assert isinstance(tephpy.__version__, str)
    assert tephpy.__version__


def test_version_is_pep440() -> None:
    """The setuptools_scm version parses as a PEP 440 version."""
    from packaging.version import Version

    Version(tephpy.__version__)


def test_runtime_dependencies_importable() -> None:
    """The declared runtime dependencies import."""
    import matplotlib  # noqa: F401
    import metpy  # noqa: F401
    import numpy  # noqa: F401
    import pint  # noqa: F401
    import scipy  # noqa: F401
