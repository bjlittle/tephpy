# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Exercise the built PyScript demo in Playwright Chromium."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Any

from playwright.sync_api import ConsoleMessage, Error, Frame, Page, sync_playwright

REPOSITORY = Path(__file__).parents[2]
HTML = REPOSITORY / "docs" / "_build" / "html"
TIMEOUT = 600_000

VALID_CSV = b"""pressure_hPa,temperature_C,dewpoint_C
1000,17,12
900,9,4
800,2,-3
700,-6,-12
600,-15,-22
500,-25,-34
400,-38,-48
300,-51,-61
200,-56,-66
100,-49,-62
"""
INVALID_CSV = b"pressure_hPa,temperature_C\n1000,not-a-number\n900,10\n"


class QuietHandler(SimpleHTTPRequestHandler):
    """Serve the built documentation without per-request terminal noise."""

    def log_message(self, _format: str, *args: object) -> None:
        """Suppress the base class's access log."""


def _record_console(errors: list[str], message: ConsoleMessage) -> None:
    """Record uncaught browser-console errors for the final assertion."""
    if message.type == "error":
        errors.append(f"console: {message.text}")


def _record_page_error(errors: list[str], error: Error) -> None:
    """Record an uncaught JavaScript or Python page error."""
    errors.append(f"page: {error}")


def _assert_toolbar(frame: Frame) -> None:
    """Check toolbar tools and ensure dynamic messages cannot move them."""
    toolbar = frame.locator(".mpl-toolbar")
    assert toolbar.count() == 1
    toolbar_labels = {
        toolbar.locator("button img").nth(index).get_attribute("alt")
        for index in range(toolbar.locator("button img").count())
    }
    assert "Reset original view" in toolbar_labels
    assert "Download plot" in toolbar_labels
    assert any(label is not None and "pans" in label for label in toolbar_labels)
    assert any(
        label is not None and "Zoom to rectangle" in label for label in toolbar_labels
    )
    pan = toolbar.locator('button img[alt*="Left button pans"]')
    before = pan.bounding_box()
    assert before is not None
    pan.hover()
    frame.wait_for_timeout(100)
    message = toolbar.locator(".mpl-message").text_content() or ""
    assert "Left button pans" not in message
    after = pan.bounding_box()
    assert after is not None
    assert abs(after["x"] - before["x"]) < 0.5

    interaction_layer = frame.locator("canvas.mpl-canvas").locator("..")
    assert interaction_layer.get_attribute("tabindex") == "0"
    interaction_layer.scroll_into_view_if_needed()
    before_coordinates = pan.bounding_box()
    assert before_coordinates is not None
    interaction_layer.hover()
    frame.wait_for_function(
        "document.querySelector('.mpl-message').textContent.length > 0"
    )
    with_coordinates = pan.bounding_box()
    assert with_coordinates is not None
    shift = abs(with_coordinates["x"] - before_coordinates["x"])
    assert shift < 0.5, f"toolbar control shifted by {shift}px"


def _assert_data_table(
    frame: Frame,
    *,
    label: str,
    levels: int,
    columns: tuple[tuple[str, str], ...],
    expanded: bool,
) -> None:
    """Check the normalized table paired with the current plot."""
    panel = frame.locator("#data-panel")
    assert panel.count() == 1
    assert panel.evaluate("element => element.open") is expanded
    summary = panel.locator("summary").inner_text()
    assert summary == f"Plotted data — {label} — {levels} levels"
    table = panel.locator("#data-table")
    actual_headings = tuple(
        text.split("(", maxsplit=1)[0].strip()
        for text in table.locator("thead th").all_text_contents()
    )
    assert actual_headings == tuple(heading for heading, _value in columns)
    assert table.locator("tbody tr").count() == levels
    values = tuple(table.locator("tbody tr").first.locator("td").all_text_contents())
    assert values == tuple(value for _heading, value in columns)


def _exercise(page: Page, url: str, manifest: dict[str, Any]) -> None:
    """Launch the iframe and exercise initialization and both upload outcomes."""
    page.goto(f"{url}/tutorials/browser-demo.html", wait_until="domcontentloaded")
    assert page.locator("#tephpy-browser-demo-frame").count() == 0
    page.locator("#tephpy-browser-demo-launch").click()
    iframe = page.locator("#tephpy-browser-demo-frame")
    iframe.wait_for(state="attached")
    element = iframe.element_handle()
    assert element is not None
    frame = element.content_frame()
    assert frame is not None

    frame.wait_for_function(
        "document.documentElement.dataset.ready === 'true' || "
        "document.documentElement.dataset.installError !== undefined",
        timeout=TIMEOUT,
    )
    root = frame.locator("html")
    install_error = root.get_attribute("data-install-error")
    assert install_error is None, f"runtime initialization failed: {install_error}"
    assert root.get_attribute("data-ready") == "true"
    assert root.get_attribute("data-wheel-file") == manifest["tephpy"]["wheel"]
    assert root.get_attribute("data-wheel-version") == manifest["tephpy"]["version"]
    assert root.get_attribute("data-backend") == (
        "module://matplotlib.backends.backend_pyodide"
    )

    frame.locator("canvas.mpl-canvas").wait_for(state="visible", timeout=TIMEOUT)
    _assert_toolbar(frame)
    _assert_data_table(
        frame,
        label="Bundled example",
        levels=19,
        columns=(
            ("Pressure", "1000"),
            ("Temperature", "18"),
            ("Dewpoint", "14"),
            ("Wind speed", "5"),
            ("Wind direction", "180"),
        ),
        expanded=False,
    )
    frame.locator("#data-panel summary").click()

    generation = int(root.get_attribute("data-plot-generation"))
    upload = frame.locator("#csv-file")
    upload_generation = int(root.get_attribute("data-upload-generation") or 0)
    upload.set_input_files(
        {"name": "uploaded.csv", "mimeType": "text/csv", "buffer": VALID_CSV}
    )
    frame.wait_for_function(
        f"document.documentElement.dataset.uploadGeneration === "
        f"'{upload_generation + 1}' && "
        "document.documentElement.dataset.uploadState === 'complete'",
        timeout=TIMEOUT,
    )
    upload_error = frame.locator("#plot-error")
    assert upload_error.is_hidden(), upload_error.inner_text()
    assert root.get_attribute("data-plot-label") == "uploaded.csv"
    assert int(root.get_attribute("data-plot-generation")) == generation + 1
    assert frame.locator("canvas.mpl-canvas").count() == 1
    _assert_data_table(
        frame,
        label="uploaded.csv",
        levels=10,
        columns=(("Pressure", "1000"), ("Temperature", "17"), ("Dewpoint", "12")),
        expanded=True,
    )

    good_generation = int(root.get_attribute("data-plot-generation"))
    good_table = frame.locator("#data-panel").inner_text()
    upload_generation += 1
    upload.set_input_files(
        {"name": "invalid.csv", "mimeType": "text/csv", "buffer": INVALID_CSV}
    )
    frame.wait_for_function(
        f"document.documentElement.dataset.uploadGeneration === "
        f"'{upload_generation + 1}' && "
        "document.documentElement.dataset.uploadState === 'complete'",
        timeout=TIMEOUT,
    )
    alert = frame.locator("#plot-error")
    alert.wait_for(state="visible", timeout=TIMEOUT)
    assert "previous plot is unchanged" in alert.inner_text().lower()
    assert int(root.get_attribute("data-plot-generation")) == good_generation
    assert frame.locator("canvas.mpl-canvas").count() == 1
    assert frame.locator("#data-panel").inner_text() == good_table


def main() -> None:
    """Serve the documentation and run the Chromium browser smoke test."""
    if not (HTML / "tutorials" / "browser-demo.html").is_file():
        msg = f"built tutorial not found under {HTML}; build the documentation first"
        raise FileNotFoundError(msg)
    manifest = json.loads(
        (HTML / "browser" / "runtime.json").read_text(encoding="utf-8")
    )
    handler = partial(QuietHandler, directory=str(HTML))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.on("console", partial(_record_console, errors))
            page.on("pageerror", partial(_record_page_error, errors))
            _exercise(page, url, manifest)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    if errors:
        msg = "uncaught browser errors:\n" + "\n".join(errors)
        raise RuntimeError(msg)
    print("browser demo smoke test passed")


if __name__ == "__main__":
    main()
