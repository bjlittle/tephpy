Plot a Sounding in Your Browser
================================

This experimental demo runs tephpy and matplotlib entirely in your browser. It
starts with a bundled example :term:`sounding` and lets you replace it with a
local CSV file. Your file is not uploaded to tephpy or to a live-data service.

.. note::

    The first launch downloads PyScript, Pyodide, and the scientific Python
    packages needed by tephpy. It can take a few minutes. Chromium is tested;
    Firefox and Safari support are best-effort.

Launch the Demo
---------------

The runtime is loaded only after you choose **Launch browser demo**.

.. raw:: html

    <button id="tephpy-browser-demo-launch" type="button"
            aria-controls="tephpy-browser-demo-container">
      Launch browser demo
    </button>
    <div id="tephpy-browser-demo-container"></div>
    <script>
    // Copyright (c) 2026, tephpy Contributors. BSD-3-Clause.
    (() => {
      const button = document.getElementById("tephpy-browser-demo-launch");
      const container = document.getElementById("tephpy-browser-demo-container");
      button.addEventListener("click", () => {
        if (document.getElementById("tephpy-browser-demo-frame")) return;
        const frame = document.createElement("iframe");
        frame.id = "tephpy-browser-demo-frame";
        frame.src = "../browser/index.html";
        frame.title = "Interactive tephpy browser demo";
        frame.style.width = "100%";
        frame.style.height = "64rem";
        frame.style.border = "0";
        frame.setAttribute("allow", "clipboard-write");
        container.appendChild(frame);
        button.hidden = true;
      }, {once: true});
    })();
    </script>

Prepare a CSV File
------------------

The demo's CSV format is intentionally small. It is an input contract for this
page, not a package-level reader.

.. list-table:: CSV columns
    :header-rows: 1

    * - Column
      - Requirement
    * - ``pressure_hPa``
      - Required; pressure in hectopascals.
    * - ``temperature_C``
      - Required; temperature in degrees Celsius.
    * - ``dewpoint_C``
      - Optional; dewpoint in degrees Celsius.
    * - ``wind_speed_m_s`` and ``wind_direction_degree``
      - Optional, but supplied together; speed in metres per second and
        direction in degrees.

Blank cells become ``NaN``. An absent optional column becomes ``None``. The
demo reports missing or duplicate headers, a nonnumeric nonblank cell, empty
data, and a one-sided wind pair before plotting. tephpy's
:class:`~tephpy.sounding.Sounding` then performs the usual physical validation,
including pressure ordering and dewpoint bounds.

Use the matplotlib toolbar below the canvas to pan, zoom, inspect cursor
coordinates, restore the original view, or download the figure. Uploading an
invalid file leaves the previous plot in place so you can correct the data and
try again.

Experimental Scope
------------------

The demo deliberately has no University of Wyoming ``wyoming.fetch`` access,
persistent configuration, thermodynamic-analysis controls, offline caching, or
live network data. Those are outside this experiment; only local CSV plotting
is included.
