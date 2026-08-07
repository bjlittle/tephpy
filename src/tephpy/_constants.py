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

from types import MappingProxyType
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

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
#: corners in hPa / degrees Celsius: bottom-left and top-right of the default
#: view (see ``TephigramAxes.set_extent``).
DEFAULT_EXTENT: Final[tuple[tuple[float, float], tuple[float, float]]] = (
    (1050.0, -40.0),
    (200.0, 40.0),
)

#: Pressure domain the isopleth geometry is computed over (hPa).
PRESSURE_DOMAIN: Final[tuple[float, float]] = (50.0, 1050.0)

#: Temperature domain the isopleth geometry is computed over (°C).
TEMPERATURE_DOMAIN: Final[tuple[float, float]] = (-120.0, 60.0)

#: Potential-temperature domain the isopleth geometry is computed over (°C).
THETA_DOMAIN: Final[tuple[float, float]] = (-100.0, 520.0)

#: Wet-bulb potential-temperature domain for the moist adiabats (°C).
MOIST_ADIABAT_DOMAIN: Final[tuple[float, float]] = (-40.0, 60.0)

#: Vertices per isopleth member polyline.
ISOPLETH_SAMPLES: Final[int] = 101

#: Pressure sampling step for the moist-adiabat integration (hPa).
MOIST_ADIABAT_PRESSURE_STEP: Final[float] = 5.0

#: Temperature below which moist adiabats are truncated (°C) — the curves
#: converge onto the dry adiabats (Met Office Factsheet 13 convention).
MOIST_ADIABAT_TRUNCATION: Final[float] = -50.0

#: Isotherm zoom ladder: (min view width, member interval in °C) pairs,
#: widest first (10 °C at the default view width of ~311 units).
ISOTHERM_STEPS: Final[tuple[tuple[float, float], ...]] = (
    (500.0, 20.0),
    (100.0, 10.0),
    (0.0, 5.0),
)

#: Dry-adiabat zoom ladder (°C of potential temperature); the grid is
#: symmetric with the isotherms.
DRY_ADIABAT_STEPS: Final[tuple[tuple[float, float], ...]] = ISOTHERM_STEPS

#: Isobar zoom ladder (hPa): 50 hPa at the default view width, refining to
#: the 10 hPa printed-chart interval (Met Office Factsheet 13; spec §3.5)
#: at deep zoom.
ISOBAR_STEPS: Final[tuple[tuple[float, float], ...]] = (
    (500.0, 100.0),
    (150.0, 50.0),
    (75.0, 20.0),
    (0.0, 10.0),
)

#: Moist-adiabat zoom ladder (°C of wet-bulb potential temperature).
MOIST_ADIABAT_STEPS: Final[tuple[tuple[float, float], ...]] = (
    (500.0, 10.0),
    (150.0, 5.0),
    (50.0, 2.0),
    (0.0, 1.0),
)

#: Humidity mixing-ratio zoom ladder: (min view width, stride into
#: ``MIXING_RATIO_VALUES``) pairs, widest first.
MIXING_RATIO_STRIDES: Final[tuple[tuple[float, int], ...]] = (
    (500.0, 4),
    (150.0, 2),
    (0.0, 1),
)

#: Humidity mixing-ratio member values (g/kg).
MIXING_RATIO_VALUES: Final[tuple[float, ...]] = (
    0.05,
    0.1,
    0.2,
    0.5,
    1.0,
    1.5,
    2.0,
    3.0,
    4.0,
    5.0,
    7.0,
    10.0,
    14.0,
    20.0,
    28.0,
    40.0,
)

#: Isotherm line colour.
ISOTHERM_COLOR: Final[str] = "dimgrey"

#: Dry-adiabat line colour.
DRY_ADIABAT_COLOR: Final[str] = "darkgrey"

#: Isobar line colour.
ISOBAR_COLOR: Final[str] = "tab:blue"

#: Moist-adiabat line colour.
MOIST_ADIABAT_COLOR: Final[str] = "tab:orange"

#: Humidity mixing-ratio line colour.
MIXING_RATIO_COLOR: Final[str] = "tab:green"

#: Isopleth line width in points.
ISOPLETH_LINEWIDTH: Final[float] = 0.5

#: Isopleth line and label alpha.
ISOPLETH_ALPHA: Final[float] = 1.0

#: Line width in points for an emphasised isopleth member (spec §3.2). Emphasis
#: follows the monochrome printed-chart idiom -- same ink, heavier line -- so a
#: distinguished member needs no colour convention; a call supplies ``color`` to
#: override that.
EMPHASIS_LINEWIDTH: Final[float] = 1.5

#: Isotherm draw order.
ISOTHERM_ZORDER: Final[float] = 1.1

#: Dry-adiabat draw order.
DRY_ADIABAT_ZORDER: Final[float] = 1.2

#: Isobar draw order.
ISOBAR_ZORDER: Final[float] = 1.3

#: Humidity mixing-ratio draw order.
MIXING_RATIO_ZORDER: Final[float] = 1.4

#: Moist-adiabat draw order.
MOIST_ADIABAT_ZORDER: Final[float] = 1.5

#: Temperature profile line colour (the operational/MetPy convention:
#: temperature red, dewpoint green; spec §3.2).
PROFILE_TEMPERATURE_COLOR: Final[str] = "red"

#: Dewpoint profile line colour (the operational/MetPy convention).
PROFILE_DEWPOINT_COLOR: Final[str] = "green"

#: Profile line width in points.
PROFILE_LINEWIDTH: Final[float] = 1.5

#: Profile draw order: above every isopleth family and above matplotlib's
#: default ``Line2D`` zorder of 2.
PROFILE_ZORDER: Final[float] = 2.5

#: Derived sounding legend label (spec §3.4), e.g. ``"72357 2013-05-20 12Z"``.
SOUNDING_LABEL_FORMAT: Final[str] = "{station} {time:%Y-%m-%d %H}Z"

#: Default interactive cursor readout fields (spec §3.2), in display order;
#: names index the ``plotting.axes`` cursor formatter registry.
CURSOR_FIELDS: Final[tuple[str, ...]] = ("pressure", "temperature", "theta")

#: The operational cloud-base correction to Normand's point, in hPa: UK
#: operational tephigram practice raises the constructed LCL by 25 mb to
#: better match observed convective cloud base (spec §1/§3.3; Met Office
#: forecasting practice). Applied only when explicitly requested via
#: ``cloud_base_correction=``.
CLOUD_BASE_CORRECTION: Final[float] = -25.0

#: CAPE shading fill colour (the operational/MetPy convention: positive
#: buoyancy red, negative blue; spec §3.2).
CAPE_COLOR: Final[str] = "tab:red"

#: CIN shading fill colour (the operational/MetPy convention).
CIN_COLOR: Final[str] = "tab:blue"

#: CAPE/CIN shading fill alpha.
SHADING_ALPHA: Final[float] = 0.3

#: CAPE/CIN shading draw order: above the isopleth families but below every
#: profile line -- including parcel paths drawn via ``plot_profile``, which
#: sets no zorder and so sits at Matplotlib's default ``Line2D`` zorder of 2.
#: Kept strictly below 2 so the shading never renders over a profile line
#: (spec §3.2).
SHADING_ZORDER: Final[float] = 1.75

#: Indices panel width, as an ``axes_grid1`` fraction of the diagram width
#: (spec §3.2).
INDICES_PANEL_WIDTH: Final[str] = "35%"

#: Indices panel padding from the diagram, in inches.
INDICES_PANEL_PAD: Final[float] = 0.1

#: Indices panel text font size in points.
INDICES_PANEL_FONTSIZE: Final[float] = 8.0

#: Indices panel rows, one per ``SoundingIndices`` field, in display order:
#: (field name, display label, pint unit to convert to, display unit,
#: format spec). NaN values render as an em dash (spec §3.2).
INDICES_PANEL_ROWS: Final[tuple[tuple[str, str, str, str, str], ...]] = (
    ("cape", "CAPE", "J/kg", "J/kg", ".0f"),
    ("cin", "CIN", "J/kg", "J/kg", ".0f"),
    ("lcl_pressure", "LCL", "hPa", "hPa", ".0f"),
    ("lcl_temperature", "LCL T", "degC", "°C", ".1f"),
    ("lfc_pressure", "LFC", "hPa", "hPa", ".0f"),
    ("lfc_temperature", "LFC T", "degC", "°C", ".1f"),
    ("el_pressure", "EL", "hPa", "hPa", ".0f"),
    ("el_temperature", "EL T", "degC", "°C", ".1f"),
    ("theta_w", "θw", "degC", "°C", ".1f"),
    ("lifted_index", "LI", "delta_degC", "°C", ".1f"),
)

#: Wind-barb gutter width, as an ``axes_grid1`` fraction of the diagram
#: width (spec §3.2).
BARB_GUTTER_WIDTH: Final[str] = "15%"

#: Wind-barb gutter padding from the diagram, in inches.
BARB_GUTTER_PAD: Final[float] = 0.1

#: Default staff position, as a fraction across the gutter; overlaid
#: soundings pick other positions via ``plot_barbs(..., x=...)``.
BARB_STAFF_POSITION: Final[float] = 0.5

#: Default minimum vertical separation between drawn barbs, in points; the
#: staff keeps the densest subset at least this far apart, so zooming in
#: reveals more levels. A call picks another separation via
#: ``plot_barbs(..., minimum_separation=...)`` (spec §3.2).
BARB_MIN_SEPARATION: Final[float] = 18.0

#: Wind-barb speed increments in knots — half barb 5 kt, full barb 10 kt,
#: flag 50 kt, with speeds rounded to the nearest increment (5 kt binning):
#: the Met Office/WMO symbology (Met Office Factsheet 13; spec §1, §3.2).
BARB_INCREMENTS: Final[dict[str, float]] = {"half": 5.0, "full": 10.0, "flag": 50.0}

#: Wind-barb glyph length in points.
BARB_LENGTH: Final[float] = 6.0

#: University of Wyoming sounding request (spec §3.4): the post-2024 wsgi
#: interface's machine-readable form — ``type=TEXT:CSV`` returns bare,
#: self-describing CSV (verified 2026-07-27; the classic ``cgi-bin``
#: TEXT:LIST endpoint now 404s).
WYOMING_URL: Final[str] = (
    "https://weather.uwyo.edu/wsgi/sounding?datetime={datetime}&id={station}"
    "&type=TEXT:CSV"
)

#: Default timeout for a University of Wyoming request, in seconds.
WYOMING_TIMEOUT: Final[float] = 30.0

#: IGRA v2 missing-value sentinels (NCEI ``igra2-data-format.txt``): -9999
#: throughout; -8888 additionally flags a removed-by-QA value.
IGRA_MISSING: Final[tuple[int, ...]] = (-9999, -8888)

#: Isopleth label font size in points.
LABEL_FONTSIZE: Final[float] = 8.0

#: Isopleth label box style.
LABEL_BOXSTYLE: Final[str] = "round,pad=0.3"

#: Isopleth label box colour.
LABEL_BOX_COLOR: Final[str] = "white"

#: Isopleth label box alpha.
LABEL_BOX_ALPHA: Final[float] = 0.6

#: Axis titles for edge-labelled isopleth families, keyed by accessor name.
#: A claimed edge takes its family's title only when the axis has none, so a
#: user's ``set_xlabel`` wins whichever side of the accessor call it lands on,
#: and releasing the edge clears the title again (spec §3.2).
EDGE_AXIS_TITLES: Final[dict[str, str]] = {
    "isotherms": "Temperature (°C)",
    "isobars": "Pressure (hPa)",
    "dry_adiabats": "Potential temperature (°C)",
    "moist_adiabats": "Wet-bulb potential temperature (°C)",
    "mixing_ratios": "Mixing ratio (g kg⁻¹)",
}

#: Edge tick mark length in points.
EDGE_TICK_LENGTH: Final[float] = 3.0

#: Edge tick label padding from the tick mark, in points.
EDGE_TICK_PAD: Final[float] = 2.0

#: Side-panel padding substituted for the pad of the panel nearest the
#: diagram when its right edge carries isopleth ticks, in inches. Both panel
#: pads (0.1 in) are narrower than an 8 pt tick label, so right-edge labels
#: would land on whichever panel abuts the diagram. Measured 2026-07-29: a
#: right axis needs 0.479 in for its ticks, labels and title, so this leaves
#: 0.07 in of clearance (spec §3.2).
EDGE_LABEL_GUTTER_PAD: Final[float] = 0.55

#: Points per inch, the typographic unit matplotlib sizes text and offsets in.
POINTS_PER_INCH: Final[float] = 72.0

#: Logo height in inches for each ``(form, size)`` preset of ``add_logo``.
#: The presets are per-form because the forms give the wordmark different
#: shares of their height — 44.1% for the lockup, 17.8% for the stacked
#: form — so a shared pair would leave one of them illegible (logo spec §3.3).
LOGO_SIZES: Final[dict[str, dict[str, float]]] = {
    "icon": {"small": 0.40, "large": 0.70},
    "lockup": {"small": 0.30, "large": 0.55},
    "stacked": {"small": 0.70, "large": 1.15},
}

#: Default gap in points between the logo and its target's edge: a comfortable
#: inset a shade wider than the legend's ``borderaxespad`` of 5.0 pt (0.5
#: font-size units at the 10 pt default font).
LOGO_PAD: Final[float] = 6.0

#: Default logo draw order: above lines (2), text (3) and legends (5).
LOGO_ZORDER: Final[float] = 100.0

#: sRGB luma (Rec. 709 weights over gamma-encoded channels) below which
#: ``theme="auto"`` calls a background dark.
LOGO_LUMINANCE_THRESHOLD: Final[float] = 0.5

#: Rec. 709 luma weights for the red, green and blue channels.
LOGO_LUMINANCE_WEIGHTS: Final[tuple[float, float, float]] = (0.2126, 0.7152, 0.0722)

#: Effective default for every ``tephpy.config`` option — what a user gets
#: when they set nothing (configfile spec §3.4).
#:
#: Read only by the configuration-file template generator. The plotting path
#: resolves its own defaults in ``IsoplethFamily._resolve``, and
#: ``tests/test_config_defaults.py`` gates the two against each other. Entries
#: name the conventions above rather than restating their values, so the gate
#: guards the structure — which option exists, and which convention it draws
#: on — rather than a second copy of every literal.
#:
#: A ``None`` records an option with **no** default: leaving ``interval`` and
#: ``values`` unset is what enables the zoom-adaptive selection ladder, so the
#: template must never print a number for them.
CONFIG_DEFAULTS: Final[Mapping[str, Mapping[str, object]]] = MappingProxyType(
    {
        "isotherms": MappingProxyType(
            {
                "color": ISOTHERM_COLOR,
                "linewidth": ISOPLETH_LINEWIDTH,
                "alpha": ISOPLETH_ALPHA,
                "labels": True,
                "visible": True,
                "emphasis": {},
                "values": None,
                "interval": None,
            }
        ),
        "isobars": MappingProxyType(
            {
                "color": ISOBAR_COLOR,
                "linewidth": ISOPLETH_LINEWIDTH,
                "alpha": ISOPLETH_ALPHA,
                "labels": True,
                "visible": True,
                "emphasis": {},
                "values": None,
                "interval": None,
            }
        ),
        "dry_adiabats": MappingProxyType(
            {
                "color": DRY_ADIABAT_COLOR,
                "linewidth": ISOPLETH_LINEWIDTH,
                "alpha": ISOPLETH_ALPHA,
                "labels": True,
                "visible": True,
                "emphasis": {},
                "values": None,
                "interval": None,
            }
        ),
        "moist_adiabats": MappingProxyType(
            {
                "color": MOIST_ADIABAT_COLOR,
                "linewidth": ISOPLETH_LINEWIDTH,
                "alpha": ISOPLETH_ALPHA,
                "labels": True,
                "visible": True,
                "emphasis": {},
                "values": None,
                "interval": None,
                "truncation": MOIST_ADIABAT_TRUNCATION,
            }
        ),
        "mixing_ratios": MappingProxyType(
            {
                "color": MIXING_RATIO_COLOR,
                "linewidth": ISOPLETH_LINEWIDTH,
                "alpha": ISOPLETH_ALPHA,
                "labels": True,
                "visible": True,
                "emphasis": {},
                "values": None,
            }
        ),
        "diagram": MappingProxyType({"extent": DEFAULT_EXTENT}),
        "cursor": MappingProxyType({"fields": CURSOR_FIELDS}),
    }
)
