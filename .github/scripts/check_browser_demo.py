# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Check the built PyScript demo in Playwright Chromium."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import TYPE_CHECKING, Any

# Deferred rather than imported here, so that importing this module needs only
# the standard library. Playwright belongs to the `docs` feature and is absent
# from the `test` environments `ci-tests` runs, where a module-scope import
# would make every test below a test that skips -- passing, in CI, without ever
# reading a line of this file. `main()` imports what it runs, under the one
# `PLC0415` this module allows itself; every name here is an annotation, which
# `from __future__ import annotations` has already made a string.
if TYPE_CHECKING:
    from playwright.sync_api import ConsoleMessage, Error, Frame, Page

REPOSITORY = Path(__file__).parents[2]
HTML = REPOSITORY / "docs" / "_build" / "html"
#: Milliseconds any single wait below may spend. Five sit on the critical path,
#: and together they have to stay inside what one attempt is given in `ci-docs`:
#: a wait outliving its attempt is killed by the shell, which reports a signal,
#: where this reports the wait that hung and the state the demo reached. The
#: whole script takes about twenty seconds, so this is generous by design -- it
#: is a stall bound, not a performance budget.
TIMEOUT = 75_000

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
    message_box = toolbar.locator(".mpl-message").bounding_box()
    toolbar_box = toolbar.bounding_box()
    assert message_box is not None
    assert toolbar_box is not None
    right_gap = abs(
        message_box["x"]
        + message_box["width"]
        - toolbar_box["x"]
        - toolbar_box["width"]
    )
    assert right_gap < 0.5, f"toolbar message right gap is {right_gap}px"


def _assert_first_mousedown_does_not_scroll(page: Page, frame: Frame) -> None:
    """Keep both documents still while the canvas takes focus on first press."""
    zoom = frame.locator('button img[alt*="Zoom to rectangle"]').locator("..")
    zoom.click()
    iframe = page.locator("#tephpy-browser-demo-frame")
    page.evaluate(
        """() => {
            const frame = document.querySelector('#tephpy-browser-demo-frame');
            window.scrollTo({
                top: window.scrollY + frame.getBoundingClientRect().top - 80,
                behavior: 'instant',
            });
        }"""
    )
    frame.evaluate("window.scrollTo({top: 260, behavior: 'instant'})")
    page.wait_for_timeout(100)

    iframe_box = iframe.bounding_box()
    interaction_layer = frame.locator("canvas.mpl-canvas").locator("..")
    layer_box = interaction_layer.bounding_box()
    assert iframe_box is not None
    assert layer_box is not None
    viewport = page.viewport_size
    assert viewport is not None
    visible_left = max(iframe_box["x"], layer_box["x"], 0.0)
    visible_right = min(
        iframe_box["x"] + iframe_box["width"],
        layer_box["x"] + layer_box["width"],
        float(viewport["width"]),
    )
    visible_top = max(iframe_box["y"], layer_box["y"], 0.0)
    visible_bottom = min(
        iframe_box["y"] + iframe_box["height"],
        layer_box["y"] + layer_box["height"],
        float(viewport["height"]),
    )
    point = (
        (visible_left + visible_right) / 2.0,
        (visible_top + visible_bottom) / 2.0,
    )
    before = page.evaluate("window.scrollY"), frame.evaluate("window.scrollY")

    page.mouse.move(*point)
    page.mouse.down(button="right")
    page.wait_for_timeout(100)
    after = page.evaluate("window.scrollY"), frame.evaluate("window.scrollY")
    page.mouse.up(button="right")

    assert after == before, f"first canvas mousedown scrolled {before} to {after}"
    assert interaction_layer.evaluate(
        "element => document.activeElement === element"
    ), "canvas interaction layer did not retain focus"
    zoom.click()


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
    _assert_first_mousedown_does_not_scroll(page, frame)
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


#: How a Chromium launch fails when something it needs was never installed, what
#: installs it, and what that leaves out. The first wording is Playwright's own,
#: for a browser it never downloaded, and it comes with a box naming the command;
#: the second is the dynamic linker's, for a browser downloaded and unable to
#: start, and it comes with nothing -- forty lines into a browser log. The second
#: is the likelier of the two to be met here, because `playwright install` is a
#: step a contributor may well have run and the system libraries are not
#: something any of this project's environments carries.
MISSING = (
    (
        ("executable doesn't exist", "playwright install"),
        "playwright install chromium",
        "downloads the pinned browser",
    ),
    (
        ("error while loading shared libraries", "cannot open shared object file"),
        "playwright install --with-deps chromium",
        "adds the system libraries it links against, as root",
    ),
)


def _launch_advice(reported: str) -> list[str]:
    """Return the commands that would fix this launch failure, as advice lines.

    Every command comes back when the failure matches none of them. A wording
    this does not recognise is not one it can rule anything out from, and naming
    a command that turns out to have been unnecessary costs the few seconds it
    takes to find that out; naming none costs the page of browser log that this
    exists to put a sentence in front of.
    """
    reported = reported.lower()
    matched = [
        f"{command}  ({why})"
        for markers, command, why in MISSING
        if any(marker in reported for marker in markers)
    ]
    return matched or [f"{command}  ({why})" for _markers, command, why in MISSING]


def main() -> None:
    """Serve the documentation and run the Chromium browser smoke test."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415

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
            try:
                browser = playwright.chromium.launch()
            except Error as exc:
                advice = "\n  ".join(_launch_advice(str(exc)))
                msg = (
                    "Chromium would not start. This check drives the built demo "
                    "in a browser the documentation environment installs "
                    f"Playwright for but does not carry; run:\n  {advice}\n\n{exc}"
                )
                raise RuntimeError(msg) from exc
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
