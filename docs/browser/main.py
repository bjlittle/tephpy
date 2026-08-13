# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Run the documentation's tephpy demo inside PyScript and Pyodide."""

from __future__ import annotations

import asyncio
import importlib
from importlib.metadata import version
import json
from pathlib import Path
from typing import Any

from js import document, window
from pyodide.ffi import create_proxy
from pyodide.http import pyfetch
from pyodide_js import loadPackage

_BACKEND = "module://matplotlib.backends.backend_pyodide"
_PROXIES: list[Any] = []
_EVENT_TASKS: set[Any] = set()
_CURRENT_PLOT: tuple[Any, Any] | None = None
_EXAMPLE_TEXT = ""
_PARSER: Any = None
_PYPLOT: Any = None


def _element(identifier: str) -> Any:
    """Return one required application element."""
    return document.getElementById(identifier)


def _state(name: str, value: str) -> None:
    """Expose application state to accessibility tooling and browser tests."""
    document.documentElement.setAttribute(f"data-{name}", value)


def _status(
    message: str, *, value: int | None = None, maximum: int | None = None
) -> None:
    """Update the live runtime message and its determinate progress bar."""
    _element("runtime-status").textContent = message
    progress = _element("runtime-progress")
    if maximum is not None:
        progress.max = maximum
    if value is not None:
        progress.value = value


def _error(identifier: str, message: str | None) -> None:
    """Show or hide one accessible error message."""
    target = _element(identifier)
    target.hidden = message is None
    target.textContent = "" if message is None else message


async def _text(path: str) -> str:
    """Fetch one UTF-8 application resource relative to this page."""
    response = await pyfetch(path)
    if not response.ok:
        msg = f"could not fetch {path}: HTTP {response.status}"
        raise RuntimeError(msg)
    return await response.string()


def _runtime_packages(
    manifest: dict[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Split manifest packages between Pyodide's lock and external wheels."""
    locked = list(manifest["pyodide_packages"])
    pure = manifest["pure_python_packages"]
    locked.extend(package for package in pure if package["source"] == "pyodide")
    external = [package for package in pure if package["source"] == "pypi"]
    return locked, external


async def _install(manifest: dict[str, Any]) -> None:
    """Install and verify every pinned runtime dependency and the checkout wheel."""
    locked, external = _runtime_packages(manifest)
    total = len(locked) + len(external) + 3
    completed = 0
    _status("Loading Pyodide's package installer…", value=completed, maximum=total)
    await loadPackage("micropip")
    completed += 1

    for package in locked:
        _status(
            f"Loading {package['name']} {package['version']} from Pyodide…",
            value=completed,
        )
        await loadPackage(package["name"].lower())
        completed += 1

    import micropip  # noqa: PLC0415 -- available only after loadPackage above

    for package in external:
        _status(
            f"Installing {package['name']} {package['version']}…",
            value=completed,
        )
        await micropip.install(package["url"], deps=False)
        completed += 1

    wheel = manifest["tephpy"]["wheel"]
    base = str(window.location.href).rsplit("/", maxsplit=1)[0]
    _status(f"Installing this checkout ({wheel})…", value=completed)
    await micropip.install(f"{base}/{wheel}", deps=False)
    completed += 1

    _status("Verifying installed package versions…", value=completed)
    for package in (*locked, *external):
        installed = version(package["name"])
        if installed != package["version"]:
            msg = (
                f"{package['name']} version mismatch: expected "
                f"{package['version']}, installed {installed}"
            )
            raise RuntimeError(msg)
    installed_tephpy = version("tephpy")
    if installed_tephpy != manifest["tephpy"]["version"]:
        msg = (
            "tephpy wheel version mismatch: expected "
            f"{manifest['tephpy']['version']}, installed {installed_tephpy}"
        )
        raise RuntimeError(msg)
    completed += 1
    _status("Preparing the interactive backend…", value=completed)


async def _load_parser() -> Any:
    """Fetch the shared parser into Pyodide's filesystem and import it."""
    source = await _text("./browser_demo.py")
    Path("browser_demo.py").write_text(source, encoding="utf-8")
    importlib.invalidate_caches()
    return importlib.import_module("browser_demo")


def _initialize_backend() -> None:
    """Initialize Pyodide's WebAgg assets against one global ``mpl`` object.

    Pyodide 314.0.4's backend JavaScript creates ``window.mpl`` but then
    populates a bare ``mpl`` binding. Module-based PyScript does not alias those
    reliably, so normalize the pinned bootstrap before the first figure manager
    runs it.
    """
    from matplotlib.backends import backend_pyodide  # noqa: PLC0415
    from matplotlib.backends.backend_webagg_core import (  # noqa: PLC0415
        FigureManagerWebAgg,
    )
    from pyodide.code import run_js  # noqa: PLC0415

    application = backend_pyodide.PyodideApplication
    if application.initialized:
        return
    css_path = Path(backend_pyodide.__file__).parent / "web_backend" / "css" / "mpl.css"
    style = document.createElement("style")
    style.textContent = css_path.read_text(encoding="utf-8")
    document.head.appendChild(style)

    javascript = FigureManagerWebAgg.get_javascript(pyodide=True)
    javascript = javascript.replace("mpl.", "window.mpl.").replace(
        "window.window.mpl.", "window.mpl."
    )
    set_toolbar_image = run_js(javascript)
    # WebAgg writes a long tooltip into the toolbar on mouseover. Because that
    # status span shares a flex row with the buttons, the new text moves the
    # button out from under the pointer. Keep backend messages such as the
    # coordinate readout, but suppress only these hover-generated tooltips.
    run_js(
        "window.mpl.figure.prototype.toolbar_button_onmouseover = "
        "function (_tooltip) {};\nvoid 0;"
    )
    toolbar_proxy = create_proxy(application.get_toolbar_image)
    _PROXIES.append(toolbar_proxy)
    set_toolbar_image(toolbar_proxy)
    application.initialized = True


def _cleanup(record: tuple[Any, Any] | None) -> None:
    """Release a figure's DOM, WebAgg callback proxies, and Python manager."""
    if record is None:
        return
    figure, target = record
    manager = figure.canvas.manager
    for socket in tuple(manager.web_sockets):
        socket.on_close()
    js_figure = getattr(manager, "js_fig", None)
    if js_figure is not None:
        js_figure.resizeObserverInstance.disconnect()
        js_figure.root.remove()
        del manager.js_fig
    _PYPLOT.close(figure)
    target.remove()


def _new_figure(sounding: Any, *, label: str) -> tuple[Any, Any]:
    """Build and show a new WebAgg-derived canvas, preserving the old one on error."""
    figure = None
    target = document.createElement("div")
    target.classList.add("plot-instance")
    _element("plot").appendChild(target)
    try:
        figure, axes = _PYPLOT.subplots(
            figsize=(7.2, 7.2),
            subplot_kw={"projection": "tephigram"},
        )
        axes.plot_sounding(sounding, label=label)
        if sounding.wind_speed is not None:
            axes.plot_barbs(sounding)
        axes.legend(loc="upper right")
        axes.set_title(label)
        document.pyodideMplTarget = target
        manager = figure.canvas.manager
        manager.show()
        figure.canvas.draw_idle()
    except Exception:
        if figure is not None:
            _cleanup((figure, target))
        else:
            target.remove()
        raise
    return figure, target


def _replace_plot(sounding: Any, *, label: str) -> None:
    """Replace the displayed plot only after its successor was created successfully."""
    global _CURRENT_PLOT  # noqa: PLW0603 -- the browser owns one active canvas

    replacement = _new_figure(sounding, label=label)
    previous = _CURRENT_PLOT
    _CURRENT_PLOT = replacement
    _cleanup(previous)
    generation = int(document.documentElement.getAttribute("data-plot-generation") or 0)
    _state("plot-generation", str(generation + 1))
    _state("plot-label", label)


async def _upload(file_input: Any) -> None:
    """Parse and plot a locally selected CSV without replacing a good plot on error."""
    try:
        if file_input.files.length == 0:
            return
        uploaded = file_input.files.item(0)
        try:
            parsed = _PARSER.parse_sounding_csv(await uploaded.text())
            sounding = parsed.to_sounding(label=uploaded.name)
            _replace_plot(sounding, label=uploaded.name)
        except Exception as exc:
            _error(
                "plot-error",
                f"Could not plot {uploaded.name}: {exc}. "
                "The previous plot is unchanged.",
            )
        else:
            _error("plot-error", None)
            _status(f"Showing {uploaded.name}.")
    finally:
        file_input.value = ""
        _state("upload-state", "complete")


async def _reset() -> None:
    """Restore the bundled example sounding."""
    try:
        parsed = _PARSER.parse_sounding_csv(_EXAMPLE_TEXT)
        sounding = parsed.to_sounding(label="Bundled example")
        _replace_plot(sounding, label="Bundled example")
    except Exception as exc:
        _error("plot-error", f"Could not restore the bundled example: {exc}")
    else:
        _error("plot-error", None)
        _status("Showing the bundled example.")


def _schedule_event(coroutine: Any) -> None:
    """Schedule one async DOM callback and retain it through completion."""
    task = asyncio.create_task(coroutine)
    _EVENT_TASKS.add(task)
    task.add_done_callback(_EVENT_TASKS.discard)


def _on_upload(event: Any) -> None:
    """Schedule the file-input callback from a synchronous DOM proxy."""
    generation = int(
        document.documentElement.getAttribute("data-upload-generation") or 0
    )
    _state("upload-generation", str(generation + 1))
    _state("upload-state", "running")
    _schedule_event(_upload(event.currentTarget))


def _on_reset(_event: Any) -> None:
    """Schedule the reset callback from a synchronous DOM proxy."""
    _schedule_event(_reset())


def _wire_controls() -> None:
    """Create and retain the browser-to-Python event proxies."""
    upload_proxy = create_proxy(_on_upload)
    reset_proxy = create_proxy(_on_reset)
    _PROXIES.extend((upload_proxy, reset_proxy))
    file_input = _element("csv-file")
    reset = _element("reset-example")
    file_input.addEventListener("change", upload_proxy)
    reset.addEventListener("click", reset_proxy)
    file_input.disabled = False
    reset.disabled = False


async def _start() -> None:
    """Install the runtime and render the example sounding."""
    global _EXAMPLE_TEXT, _PARSER, _PYPLOT  # noqa: PLW0603 -- application state

    try:
        manifest = json.loads(await _text("./runtime.json"))
        _EXAMPLE_TEXT = await _text("./example.csv")
        await _install(manifest)

        import matplotlib as mpl  # noqa: PLC0415 -- installed dynamically above

        mpl.use(_BACKEND)
        import matplotlib.pyplot as plt  # noqa: PLC0415 -- backend must be selected first

        _PYPLOT = plt
        _initialize_backend()
        _PARSER = await _load_parser()
        parsed = _PARSER.parse_sounding_csv(_EXAMPLE_TEXT)
        sounding = parsed.to_sounding(label="Bundled example")
        _replace_plot(sounding, label="Bundled example")
        _wire_controls()

        _state("backend", mpl.get_backend())
        _state("wheel-file", manifest["tephpy"]["wheel"])
        _state("wheel-version", manifest["tephpy"]["version"])
        _state("ready", "true")
        _status("Ready. Showing the bundled example.", value=1, maximum=1)
    except Exception as exc:
        _state("install-error", str(exc))
        _error("runtime-error", f"The browser runtime could not start: {exc}")
        _status("Runtime initialization failed.", value=1, maximum=1)
        raise


_TASK = asyncio.create_task(_start())
