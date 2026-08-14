# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Build and stage the documentation's client-side browser demo."""

from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any
from zipfile import ZipFile

DOCS = Path(__file__).resolve().parent
REPOSITORY = DOCS.parent
SOURCE = DOCS / "browser"
DEFAULT_OUTPUT = DOCS / "_build" / "browser"
ASSETS = ("app.css", "browser_demo.py", "example.csv", "main.py")


def _wheel_metadata(wheel: Path) -> tuple[str, str]:
    """Read and minimally validate a built wheel's distribution metadata."""
    with ZipFile(wheel) as archive:
        bad = archive.testzip()
        if bad is not None:
            msg = f"invalid wheel {wheel.name}: corrupt member {bad}"
            raise RuntimeError(msg)
        names = archive.namelist()
        metadata_names = [
            name for name in names if name.endswith(".dist-info/METADATA")
        ]
        wheel_names = [name for name in names if name.endswith(".dist-info/WHEEL")]
        if len(metadata_names) != 1 or len(wheel_names) != 1:
            msg = f"invalid wheel {wheel.name}: expected one METADATA and one WHEEL"
            raise RuntimeError(msg)
        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
    name = metadata.get("Name")
    version = metadata.get("Version")
    if name != "tephpy" or version is None:
        msg = f"built wheel has unexpected identity: {name!r} {version!r}"
        raise RuntimeError(msg)
    return name, version


def _build_wheel(directory: Path) -> Path:
    """Build the current checkout and return its single wheel."""
    subprocess.run(  # noqa: S603 -- fixed interpreter and build frontend
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(directory),
            str(REPOSITORY),
        ],
        check=True,
        cwd=REPOSITORY,
    )
    wheels = tuple(directory.glob("*.whl"))
    if len(wheels) != 1:
        msg = f"expected one tephpy wheel, found {[wheel.name for wheel in wheels]}"
        raise RuntimeError(msg)
    return wheels[0]


def _runtime_manifest(
    lock: dict[str, Any], wheel: Path, version: str
) -> dict[str, Any]:
    """Add the freshly built checkout wheel to the pinned browser lock."""
    manifest = dict(lock)
    manifest["tephpy"] = {
        "version": version,
        "wheel": wheel.name,
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    }
    return manifest


def stage_browser_app(output: Path = DEFAULT_OUTPUT) -> Path:
    """Build the wheel and stage a publishable browser application.

    Parameters
    ----------
    output : pathlib.Path, optional
        Staging root consumed by Sphinx's ``html_extra_path``. The application
        is placed in its ``browser`` child so it publishes at ``/browser/``.

    Returns
    -------
    pathlib.Path
        The staged ``browser`` application directory.
    """
    output = output.resolve()
    protected = {
        Path(output.anchor),
        Path.home().resolve(),
        Path(tempfile.gettempdir()).resolve(),
        REPOSITORY.resolve(),
        DOCS.resolve(),
    }
    if output in protected:
        msg = f"refusing to replace broad browser staging path: {output}"
        raise ValueError(msg)
    app = output / "browser"
    if output.exists():
        shutil.rmtree(output)
    app.mkdir(parents=True)

    lock = json.loads((SOURCE / "runtime-lock.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="tephpy-browser-wheel-") as temporary:
        built_wheel = _build_wheel(Path(temporary))
        _, version = _wheel_metadata(built_wheel)
        staged_wheel = app / built_wheel.name
        shutil.copy2(built_wheel, staged_wheel)

    for asset in ASSETS:
        shutil.copy2(SOURCE / asset, app / asset)

    html = (SOURCE / "index.html").read_text(encoding="utf-8")
    html = html.replace("__PYSCRIPT_CORE_CSS__", lock["pyscript"]["core_css"])
    html = html.replace("__PYSCRIPT_CORE_JS__", lock["pyscript"]["core_js"])
    (app / "index.html").write_text(html, encoding="utf-8")
    (app / "pyscript.toml").write_text(
        f'interpreter = "{lock["pyodide"]["interpreter"]}"\n',
        encoding="utf-8",
    )
    manifest = _runtime_manifest(lock, staged_wheel, version)
    (app / "runtime.json").write_text(
        f"{json.dumps(manifest, indent=2)}\n",
        encoding="utf-8",
    )
    return app


def main() -> None:
    """Stage the browser demo at the requested output path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    app = stage_browser_app(arguments.output)
    print(f"staged browser demo at {app}")


if __name__ == "__main__":
    main()
