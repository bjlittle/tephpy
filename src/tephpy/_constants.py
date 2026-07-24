# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Convention defaults for the tephigram diagram.

Values follow the UK tephigram convention (Met Office Factsheet 13) and
standard dry-air thermodynamic constants (Stull, *Practical Meteorology*).
Nothing numeric is hard-coded at point of use elsewhere in tephpy — import
it from here (spec §3.5).
"""

from __future__ import annotations

from typing import Final

#: Offset between degrees Celsius and Kelvin.
KELVIN_ZERO: Final[float] = 273.15

#: Specific gas constant for dry air (J kg^-1 K^-1).
RD: Final[float] = 287.05

#: Specific heat capacity of dry air at constant pressure (J kg^-1 K^-1).
CPD: Final[float] = 1004.68

#: Poisson exponent for dry air, R_d / c_pd (approximately 2/7).
KAPPA: Final[float] = RD / CPD

#: Reference pressure for potential temperature (hPa).
P_REF: Final[float] = 1000.0

#: Rotation scale of the tephigram mapping: x = MA ln(theta_K) + T.
MA: Final[float] = 300.0

#: Default diagram extent as ((pressure, temperature), (pressure, temperature))
#: anchor corners in hPa / degrees Celsius: bottom-left and top-right of the
#: default view. Refined into the full anchoring API by a future release.
DEFAULT_ANCHOR: Final[tuple[tuple[float, float], tuple[float, float]]] = (
    (1050.0, -40.0),
    (200.0, 40.0),
)
