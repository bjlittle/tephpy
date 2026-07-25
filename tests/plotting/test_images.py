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
import pytest

import tephpy  # noqa: F401 -- registers the "tephigram" projection

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
