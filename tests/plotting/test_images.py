# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Image-baseline and vector-output tests for the tephigram diagram (§8.5).

Baselines live in ``tests/baseline`` (pyproject ``mpl-baseline-path``),
generated with ``pixi run baselines`` on the committed lockfile. The
plugin's defaults apply: classic style, savefig dpi 100, RMS tolerance 2 —
output is bit-identical across the pinned py312/py313/py314 environments.
pytest-mpl closes returned figures itself.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from metpy.units import units
import numpy as np
import pytest

# Importing tephpy (via any of its names) registers the "tephigram" projection.
from tephpy import Sounding, calc

FAMILIES = ("isotherms", "isobars", "dry_adiabats", "moist_adiabats", "mixing_ratios")


def _tephigram_figure():
    """Create a small tephigram figure (baselines stay a few tens of KB)."""
    return plt.subplots(figsize=(3.5, 3.5), subplot_kw={"projection": "tephigram"})


def _solo(ax, name):
    """Hide every family except `name`."""
    for family in FAMILIES:
        if family != name:
            getattr(ax, family)(visible=False)


@pytest.mark.mpl_image_compare
def test_default_diagram():
    fig, _ax = _tephigram_figure()
    return fig


@pytest.mark.mpl_image_compare
def test_zoomed_diagram():
    fig, ax = _tephigram_figure()
    ax.set_extent(((1050.0, -10.0), (700.0, 30.0)))
    return fig


@pytest.mark.mpl_image_compare
def test_family_isotherms():
    fig, ax = _tephigram_figure()
    _solo(ax, "isotherms")
    return fig


@pytest.mark.mpl_image_compare
def test_family_isobars():
    fig, ax = _tephigram_figure()
    _solo(ax, "isobars")
    return fig


@pytest.mark.mpl_image_compare
def test_family_dry_adiabats():
    fig, ax = _tephigram_figure()
    _solo(ax, "dry_adiabats")
    return fig


@pytest.mark.mpl_image_compare
def test_family_moist_adiabats():
    fig, ax = _tephigram_figure()
    _solo(ax, "moist_adiabats")
    return fig


@pytest.mark.mpl_image_compare
def test_family_mixing_ratios():
    fig, ax = _tephigram_figure()
    _solo(ax, "mixing_ratios")
    return fig


def test_savefig_vector_formats(tmp_path):
    """The first real diagram exports to PDF and SVG (spec §9, Plan 3 row)."""
    fig, _ax = _tephigram_figure()
    pdf = tmp_path / "tephigram.pdf"
    svg = tmp_path / "tephigram.svg"
    try:
        fig.savefig(pdf)
        fig.savefig(svg)
    finally:
        plt.close(fig)
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert b"</svg>" in svg.read_bytes()


def _reference_sounding(**kwargs):
    """Build a small, plausible mid-latitude sounding for the baselines."""
    return Sounding(
        units.Quantity(
            np.array([1006.0, 925.0, 850.0, 700.0, 500.0, 400.0, 300.0]), "hPa"
        ),
        units.Quantity(np.array([26.0, 20.0, 15.4, 7.0, -8.5, -18.5, -31.0]), "degC"),
        dewpoint=units.Quantity(
            np.array([22.0, 18.0, 14.0, 2.0, -20.0, -35.0, -50.0]), "degC"
        ),
        **kwargs,
    )


@pytest.mark.mpl_image_compare
def test_profile_sounding():
    """One sounding: red temperature and green dewpoint over the grid."""
    fig, ax = _tephigram_figure()
    ax.plot_sounding(_reference_sounding(label="03808 2026-07-21 12Z"))
    ax.legend(loc="upper right", fontsize=6)
    return fig


@pytest.mark.mpl_image_compare
def test_sounding_overlay():
    """Two soundings overlay with distinguishable styles and a legend."""
    fig, ax = _tephigram_figure()
    ax.plot_sounding(_reference_sounding(label="00Z"))
    cooler = Sounding(
        units.Quantity(np.array([1006.0, 850.0, 700.0, 500.0, 300.0]), "hPa"),
        units.Quantity(np.array([18.0, 9.0, 0.0, -16.0, -40.0]), "degC"),
        dewpoint=units.Quantity(np.array([12.0, 6.0, -8.0, -30.0, -55.0]), "degC"),
        label="12Z",
    )
    ax.plot_sounding(cooler, linestyle="--", alpha=0.7)
    ax.legend(loc="upper right", fontsize=6)
    return fig


def _capped_sounding():
    """Build a capped convective sounding with both CAPE and CIN."""
    return Sounding(
        units.Quantity(
            np.array([1000.0, 950.0, 900.0, 850.0, 700.0, 500.0, 300.0, 200.0]), "hPa"
        ),
        units.Quantity(
            np.array([26.0, 24.0, 23.0, 21.0, 10.0, -12.0, -40.0, -55.0]), "degC"
        ),
        dewpoint=units.Quantity(
            np.array([20.0, 17.0, 14.0, 10.0, 2.0, -15.0, -45.0, -60.0]), "degC"
        ),
    )


@pytest.mark.mpl_image_compare
def test_shading_cape_cin():
    """CAPE/CIN shading and the parcel path over a capped sounding."""
    fig, ax = _tephigram_figure()
    snd = _capped_sounding()
    ax.plot_sounding(snd)
    parcel = calc.parcel_path(snd)
    ax.plot_profile(parcel, color="black", linestyle="--", linewidth=1.0)
    ax.shade_cape(snd, parcel)
    ax.shade_cin(snd, parcel)
    return fig


@pytest.mark.mpl_image_compare
def test_indices_panel():
    """The indices panel beside the diagram (the axes_grid1 divider)."""
    fig, ax = plt.subplots(figsize=(5.0, 3.5), subplot_kw={"projection": "tephigram"})
    ax.set_extent(((1050.0, -30.0), (200.0, 40.0)))
    snd = _capped_sounding()
    ax.plot_sounding(snd)
    ax.annotate_indices(calc.indices(snd))
    return fig
