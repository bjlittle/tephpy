# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Cross-validation against recorded tephi outputs (spec §7, layer 4).

tephi is a corroborating oracle, not the definition of truth: agreement
within tolerance corroborates both implementations; disagreement beyond it
means STOP and investigate (first principles win, divergences get
documented here).

Known, accepted divergence: none yet. If regeneration or investigation
reveals one (e.g. a differing kappa), document it in this docstring with
the affected tolerance.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tephpy import transforms

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "tephi_oracle.json").read_text()
)

# The x-y mapping shares MA and KELVIN exactly with tephi: tight tolerance.
XY_RTOL = 1e-10
# Poisson's equation involves each library's kappa; small constant
# differences amplify through the exponent. Loose-but-meaningful tolerance;
# tighten after investigation if tephi's kappa matches ours.
THETA_RTOL = 2e-3


@pytest.mark.parametrize(
    ("case", "expected"),
    list(
        zip(
            FIXTURE["pressure_temperature_grid"],
            FIXTURE["theta_from_pressure_temperature"],
            strict=True,
        )
    ),
)
def test_theta_matches_tephi(case, expected):
    """Theta agrees with tephi within the documented tolerance."""
    pressure, temperature = case
    ours = float(transforms.theta_from_pressure_temperature(pressure, temperature))
    # Compare in Kelvin so the tolerance is meaningful near 0 degC.
    assert ours + 273.15 == pytest.approx(expected + 273.15, rel=THETA_RTOL)


@pytest.mark.parametrize(
    ("case", "expected"),
    list(
        zip(
            FIXTURE["temperature_theta_grid"],
            FIXTURE["xy_from_temperature_theta"],
            strict=True,
        )
    ),
)
def test_xy_matches_tephi(case, expected):
    """The x-y mapping agrees with tephi essentially exactly."""
    temperature, theta = case
    x, y = transforms.xy_from_temperature_theta(temperature, theta)
    np.testing.assert_allclose([float(x), float(y)], expected, rtol=XY_RTOL)
