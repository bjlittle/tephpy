# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Pytest configuration: force the non-interactive Agg backend."""

from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")
