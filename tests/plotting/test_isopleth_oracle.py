# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Informational cross-validation of the curved families against tephi (§7).

tephi is a corroborating oracle, not the definition of truth. Known,
accepted formulation differences (documented per spec §7 — investigate,
don't widen; both grow toward low pressure, so the tolerances are sized
from the worst case over the fixture grid, with thin headroom that a
future metpy/scipy lockfile bump may consume — expected drift, not a
mystery):

- Pseudoadiabats: tephi integrates its own forward-Euler scheme
  (dp = -5 hPa; Cp = 1004, L = 2.501e6) while tephpy delegates to
  metpy.calc.moist_lapse (ODE integration). Measured divergence at
  theta_w = 20 °C: <= 0.05 °C at 850/700/500 hPa, ~0.44 °C at 300 hPa.
- Mixing-ratio lines: tephi approximates 1/epsilon as 1.6 and omits the
  vapour-pressure correction; MetPy uses the exact formulations. Measured
  divergence: ~0.09 °C at w = 10/850 hPa, ~0.40 °C (w = 1) and ~0.36 °C
  (w = 20) at 300 hPa.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tephpy import transforms
from tephpy.plotting import isopleths

FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "tephi_isopleth_oracle.json").read_text()
)

#: Loose-but-meaningful tolerances (°C), sized from the worst measured
#: formulation differences above (0.44 and 0.40 °C at 300 hPa).
MOIST_ATOL = 0.5
MIXING_ATOL = 0.5

#: A fixture target counts as on our curve only if a vertex lands within
#: half our 5 hPa sampling step of it (mirrors the generator).
ON_CURVE_TOLERANCE = 2.6


def _pressure_temperature(member):
    """Recover (pressure, temperature) vertices from a member polyline."""
    t, theta = transforms.temperature_theta_from_xy(member.xy[:, 0], member.xy[:, 1])
    pressure = transforms.pressure_from_temperature_theta(t, theta)
    return pressure, t


@pytest.mark.parametrize("theta_w", FIXTURE["moist_adiabat_theta_w"])
def test_moist_adiabat_matches_tephi(theta_w):
    """Pseudoadiabats agree with tephi within the documented tolerance."""
    (member,) = isopleths.moist_adiabat_members([theta_w])
    pressure, temperature = _pressure_temperature(member)
    expected = FIXTURE["moist_adiabat_temperature"][str(theta_w)]
    compared = 0
    for target, value in zip(FIXTURE["pressures"], expected, strict=True):
        if value is None:
            continue
        index = int(np.argmin(np.abs(pressure - target)))
        if abs(pressure[index] - target) > ON_CURVE_TOLERANCE:
            continue  # our curve truncated before this target
        assert temperature[index] == pytest.approx(value, abs=MOIST_ATOL)
        compared += 1
    assert compared > 0


@pytest.mark.parametrize("mixing_ratio", FIXTURE["mixing_ratio_values"])
def test_mixing_ratio_matches_tephi(mixing_ratio):
    """Isohume dew points agree with tephi within the documented tolerance."""
    (member,) = isopleths.mixing_ratio_members([mixing_ratio])
    pressure, temperature = _pressure_temperature(member)
    expected = FIXTURE["mixing_ratio_temperature"][str(mixing_ratio)]
    order = np.argsort(pressure)
    for target, value in zip(FIXTURE["pressures"], expected, strict=True):
        # Our 10 hPa sampling grid doesn't land exactly on every target
        # (e.g. 925): interpolate along the member, which spans the full
        # pressure domain.
        interpolated = float(np.interp(target, pressure[order], temperature[order]))
        assert interpolated == pytest.approx(value, abs=MIXING_ATOL)
