# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Generate the tephi oracle fixture (one-shot; not run in CI).

Run in a THROWAWAY environment so tephi never touches the project envs:

    python3 -m venv /tmp/tephi-oracle
    /tmp/tephi-oracle/bin/pip install "tephi==0.4.0.post0"
    /tmp/tephi-oracle/bin/python tests/fixtures/generate_tephi_oracle.py

Writes ``tephi_oracle.json`` beside this script: input grids, tephi's
outputs for the equivalent conversions, and provenance.
The values are OUTPUTS of running tephi (BSD-3-Clause), not copied source;
provenance is recorded in the fixture (spec §3.1/§10 item 5).
"""

from __future__ import annotations

from datetime import UTC, datetime
import itertools
import json
from pathlib import Path

import tephi
import tephi.transforms as ttr

PRESSURES = [1050.0, 1000.0, 850.0, 700.0, 500.0, 300.0, 200.0, 100.0]
TEMPERATURES = [-80.0, -40.0, -20.0, 0.0, 15.0, 30.0, 45.0]
THETAS = [-40.0, 0.0, 20.0, 40.0, 80.0, 150.0, 300.0]


def main() -> None:
    """Evaluate tephi's transforms on the grids and write the fixture."""
    pt_grid = list(itertools.product(PRESSURES, TEMPERATURES))
    tt_grid = list(itertools.product(TEMPERATURES, THETAS))

    # tephi's transform API (verify against the installed version if these
    # names have moved): convert_pT2Tt maps (pressure, temperature) to
    # (temperature, theta); convert_Tt2xy and convert_xy2Tt map between
    # (temperature, theta) and display (x, y).
    theta_out = [float(ttr.convert_pT2Tt([p], [t])[1][0]) for p, t in pt_grid]
    xy_out = [[float(v[0]) for v in ttr.convert_Tt2xy([t], [th])] for t, th in tt_grid]

    fixture = {
        "provenance": {
            "generator": "tests/fixtures/generate_tephi_oracle.py",
            "generated": datetime.now(UTC).isoformat(),
            "tephi_version": tephi.__version__,
            "note": (
                "Values are outputs of executing tephi (BSD-3-Clause), "
                "recorded as a cross-validation oracle; no tephi source "
                "or data files are copied."
            ),
        },
        "pressure_temperature_grid": pt_grid,
        "theta_from_pressure_temperature": theta_out,
        "temperature_theta_grid": tt_grid,
        "xy_from_temperature_theta": xy_out,
    }
    out = Path(__file__).parent / "tephi_oracle.json"
    out.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"wrote {out} ({len(pt_grid)} p/T cases, {len(tt_grid)} T/theta cases)")


if __name__ == "__main__":
    main()
