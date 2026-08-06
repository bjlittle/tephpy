<p align="center">
    <picture>
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/bjlittle/tephpy/main/docs/src/_static/brand/svg/stacked-tiera-light.svg">
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/bjlittle/tephpy/main/docs/src/_static/brand/svg/stacked-tiera-dark.svg">
    <img alt="tephpy" src="https://raw.githubusercontent.com/bjlittle/tephpy/main/docs/src/_static/brand/png/stacked-256-light.png" width="180">
    </picture>
</p>

<h3 align="center">
    Tephigram rendering with <a href="https://unidata.github.io/MetPy/latest/">MetPy</a>-powered thermodynamic analysis
</h3>

----

[![SPEC 0 — Minimum Supported Dependencies](https://img.shields.io/badge/SPEC-0-green?labelColor=%23004811&color=%235CB85C)](https://scientific-python.org/specs/spec-0000/)
[![pixi Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)
[![codecov](https://codecov.io/gh/bjlittle/tephpy/graph/badge.svg?token=SEEKTK92JU)](https://codecov.io/gh/bjlittle/tephpy)
[![RTD](https://app.readthedocs.org/projects/tephpy/badge/?version=latest)](https://tephpy.readthedocs.io/en/latest/?badge=latest)

Plot and analyse [tephigrams][tephigram]. `tephpy` renders tephigrams on a rotated
temperature-entropy coordinate system and delegates thermodynamic analysis
([parcel ascent][parcel-ascent], [CAPE][cape], [CIN][cin],
[LCL][lcl]/[LFC][lfc]/[EL][el]) to [MetPy](https://github.com/Unidata/MetPy).

Successor to [SciTools/tephi](https://github.com/SciTools/tephi).

> [!NOTE]
> **Status:** early development — the plotting and analysis API is being built
> out plan by plan for the [design][specs].

[tephigram]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-tephigram
[parcel-ascent]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-parcel-ascent
[cape]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-CAPE
[cin]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-CIN
[lcl]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-LCL
[lfc]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-LFC
[el]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-EL
[specs]: https://tephpy.readthedocs.io/en/latest/developer/specs/index.html
