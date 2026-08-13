# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the browser demo's CSV contract and wheel staging."""

from __future__ import annotations

from email.parser import BytesParser
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from zipfile import ZipFile

import pytest

from tephpy.exceptions import DewpointExceedsTemperatureError

REPOSITORY = Path(__file__).parents[1]
DEMO_SOURCE = REPOSITORY / "docs" / "browser" / "browser_demo.py"
BUILD_SOURCE = REPOSITORY / "docs" / "build_browser.py"
READ_THE_DOCS_CONFIG = REPOSITORY / ".readthedocs.yml"


def _load(name, path):
    """Import a checkout-only documentation helper by path."""
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


demo = _load("tephpy_browser_demo", DEMO_SOURCE)
builder = _load("tephpy_browser_builder", BUILD_SOURCE)


def test_read_the_docs_stages_browser_app_before_sphinx():
    config = READ_THE_DOCS_CONFIG.read_text(encoding="utf-8")
    stage = "python docs/build_browser.py"
    sphinx = "sphinx-build -T -b html"

    assert stage in config
    assert config.index(stage) < config.index(sphinx)


def test_csv_parser_preserves_optional_columns_and_blank_cells():
    parsed = demo.parse_sounding_csv(
        "pressure_hPa,temperature_C,dewpoint_C,wind_speed_m_s,"
        "wind_direction_degree\n1000,18,14,5,180\n900,10,,8,200\n"
    )

    assert parsed.pressure == (1000.0, 900.0)
    assert parsed.temperature == (18.0, 10.0)
    assert parsed.dewpoint[0] == 14.0
    assert math.isnan(parsed.dewpoint[1])
    assert parsed.wind_speed == (5.0, 8.0)
    assert parsed.wind_direction == (180.0, 200.0)


def test_absent_optional_columns_are_none():
    parsed = demo.parse_sounding_csv("pressure_hPa,temperature_C\n1000,18\n900,10\n")

    assert parsed.dewpoint is None
    assert parsed.wind_speed is None
    assert parsed.wind_direction is None


@pytest.mark.parametrize(
    ("header", "message"),
    [
        ("temperature_C", "missing required CSV header"),
        (
            "pressure_hPa,temperature_C,temperature_C",
            "duplicate CSV header",
        ),
        (
            "pressure_hPa,temperature_C,wind_speed_m_s",
            "wind columns must be supplied together",
        ),
        ("pressure_hPa,,temperature_C", "missing column name"),
    ],
)
def test_invalid_headers_are_rejected(header, message):
    with pytest.raises(demo.DemoCSVError, match=message):
        demo.parse_sounding_csv(f"{header}\n1000,18\n900,10\n")


def test_nonnumeric_nonblank_cell_names_its_location():
    text = "pressure_hPa,temperature_C\n1000,warm\n900,10\n"

    with pytest.raises(
        demo.DemoCSVError,
        match="line 2, column temperature_C: expected a number",
    ):
        demo.parse_sounding_csv(text)


@pytest.mark.parametrize("text", ["", "pressure_hPa,temperature_C\n\n"])
def test_empty_csv_data_is_rejected(text):
    with pytest.raises(demo.DemoCSVError, match=r"empty|no data"):
        demo.parse_sounding_csv(text)


def test_parsed_csv_constructs_a_quantified_sounding():
    parsed = demo.parse_sounding_csv(
        "pressure_hPa,temperature_C,wind_speed_m_s,wind_direction_degree\n"
        "900,10,8,200\n1000,18,5,180\n"
    )

    sounding = parsed.to_sounding(label="upload.csv")

    assert sounding.label == "upload.csv"
    assert sounding.pressure.m_as("hPa").tolist() == [1000.0, 900.0]
    assert sounding.temperature.m_as("degC").tolist() == [18.0, 10.0]
    assert sounding.wind_speed.m_as("m/s").tolist() == [5.0, 8.0]


def test_physical_validation_is_delegated_to_sounding():
    parsed = demo.parse_sounding_csv(
        "pressure_hPa,temperature_C,dewpoint_C\n1000,18,19\n900,10,8\n"
    )

    with pytest.raises(DewpointExceedsTemperatureError):
        parsed.to_sounding(label="unphysical.csv")


def test_staged_app_contains_the_current_valid_wheel_and_manifest(tmp_path):
    app = builder.stage_browser_app(tmp_path / "stage")
    manifest = json.loads((app / "runtime.json").read_text(encoding="utf-8"))
    wheel = app / manifest["tephpy"]["wheel"]

    assert wheel.is_file()
    assert (
        hashlib.sha256(wheel.read_bytes()).hexdigest() == manifest["tephpy"]["sha256"]
    )
    with ZipFile(wheel) as archive:
        assert archive.testzip() is None
        metadata_name = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = BytesParser().parsebytes(archive.read(metadata_name))
        assert "tephpy/__init__.py" in archive.namelist()
    assert metadata["Name"] == "tephpy"
    assert metadata["Version"] == manifest["tephpy"]["version"]

    assert manifest["pyscript"]["version"] == "2026.7.3"
    assert manifest["pyodide"]["version"] == "314.0.4"
    pure = {
        package["name"]: package["version"]
        for package in manifest["pure_python_packages"]
    }
    assert pure["MetPy"] == "1.7.1"
    assert pure["Pint"] == "0.25.3"
    assert (app / "pyscript.toml").read_text(encoding="utf-8") == (
        'interpreter = "https://cdn.jsdelivr.net/pyodide/v314.0.4/full/pyodide.mjs"\n'
    )
    html = (app / "index.html").read_text(encoding="utf-8")
    assert "__PYSCRIPT" not in html
    assert "https://pyscript.net/releases/2026.7.3/core.js" in html
