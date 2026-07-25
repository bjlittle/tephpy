# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Generate the tephi isopleth oracle fixture (one-shot; not run in CI).

Run in a THROWAWAY environment so tephi never touches the project envs
(the venv is created from the pixi interpreter because the system python3
may lack ensurepip):

    pixi run --frozen python -m venv /tmp/tephi-oracle
    /tmp/tephi-oracle/bin/pip install "tephi==0.4.0.post0"
    /tmp/tephi-oracle/bin/python tests/fixtures/generate_tephi_isopleth_oracle.py

Writes ``tephi_isopleth_oracle.json`` beside this script: tephi's
pseudoadiabat temperatures (its own forward-Euler scheme, dp = -5 hPa) and
mixing-ratio dew points at fixed pressure targets, plus provenance. The
values are OUTPUTS of running tephi (BSD-3-Clause), not copied source
(spec §3.1/§10 items 5 and 13).

tephi's ``WetAdiabat._generate_points`` only touches ``data`` (theta_w),
``bounds``, and ``_delta_pressure``, so it is driven here without a
``TephiAxes`` via ``__new__`` (verified against tephi 0.4.0.post0; if a
different tephi version moves these internals, inspect the class with
``inspect.getsource(tephi.isopleths.WetAdiabat)`` and adapt — the fixture
format itself must not change).
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import numpy as np
import tephi
from tephi import isopleths
from tephi import transforms as ttr
from tephi.constants import default

THETA_WS = [0.0, 10.0, 20.0, 30.0]
MIXING_RATIOS = [1.0, 5.0, 10.0, 20.0]
PRESSURES = [1000.0, 925.0, 850.0, 700.0, 500.0, 400.0, 300.0]

#: A target counts as on-curve only if a vertex lands within half of
#: tephi's 5 hPa integration step of it.
ON_CURVE_TOLERANCE = 2.6


def wet_adiabat_temperatures(theta_w: float) -> list[float | None]:
    """Drive tephi's pseudoadiabat integration and sample it at PRESSURES.

    Parameters
    ----------
    theta_w : float
        The wet-bulb potential temperature (degrees Celsius) labelling the
        pseudoadiabat.

    Returns
    -------
    list of float or None
        tephi's temperature at each target pressure, or None where the
        curve was truncated before reaching the target.
    """
    adiabat = isopleths.WetAdiabat.__new__(isopleths.WetAdiabat)
    adiabat.data = theta_w
    adiabat.bounds = isopleths.BOUNDS(
        default["wet_adiabat_min_temperature"], default["wet_adiabat_max_pressure"]
    )
    adiabat._delta_pressure = isopleths._SATURATION_ADIABAT_PRESSURE_DELTA
    points = adiabat._generate_points()
    pressure = np.asarray(points.pressure, dtype=float)
    temperature = np.asarray(points.temperature, dtype=float)
    out: list[float | None] = []
    for target in PRESSURES:
        index = int(np.argmin(np.abs(pressure - target)))
        if abs(pressure[index] - target) > ON_CURVE_TOLERANCE:
            out.append(None)
        else:
            out.append(float(temperature[index]))
    return out


def main() -> None:
    """Evaluate tephi's curved-family maths and write the fixture."""
    moist = {str(theta_w): wet_adiabat_temperatures(theta_w) for theta_w in THETA_WS}
    mixing = {
        str(w): [float(t) for t in ttr.convert_pw2T(np.asarray(PRESSURES), w)]
        for w in MIXING_RATIOS
    }
    fixture = {
        "provenance": {
            "generator": "tests/fixtures/generate_tephi_isopleth_oracle.py",
            "generated": datetime.now(UTC).isoformat(),
            "tephi_version": tephi.__version__,
            "note": (
                "Values are outputs of executing tephi (BSD-3-Clause), "
                "recorded as an informational cross-validation oracle for "
                "the curved isopleth families; no tephi source or data "
                "files are copied."
            ),
        },
        "pressures": PRESSURES,
        "moist_adiabat_theta_w": THETA_WS,
        "moist_adiabat_temperature": moist,
        "mixing_ratio_values": MIXING_RATIOS,
        "mixing_ratio_temperature": mixing,
    }
    out = Path(__file__).parent / "tephi_isopleth_oracle.json"
    out.write_text(json.dumps(fixture, indent=2) + "\n")
    print(
        f"wrote {out} ({len(THETA_WS)} pseudoadiabats, {len(MIXING_RATIOS)} isohumes)"
    )


if __name__ == "__main__":
    main()
