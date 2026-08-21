# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Order the gallery by :data:`tephpy.examples.REGISTRY` (gallery spec §3.5).

sphinx-gallery's default sorts a subsection by code length, which buries
the canonical figure -- the longest example, and the one that should lead.

This is named in ``conf.py`` as the dotted string
``"tephpy_gallery_order.RegistryOrder"``, not as the class itself:
sphinx-gallery imports either, but a class in ``sphinx_gallery_conf`` makes
that value unpickleable, and Sphinx then warns ``cannot cache unpickleable
configuration value`` -- which this project's ``--fail-on-warning`` build
turns into a failure.
"""

from __future__ import annotations

from tephpy.examples import REGISTRY

_ORDER = {f"{module}.py": index for index, (_, module) in enumerate(REGISTRY)}


class RegistryOrder:
    """Sort key placing gallery entries in registry order."""

    def __init__(self, src_dir: str) -> None:
        """Record the directory being sorted.

        Parameters
        ----------
        src_dir : str
            The examples directory sphinx-gallery is sorting. Unused: one
            registry covers every example, and sphinx-gallery constructs
            the key per directory regardless.
        """
        self.src_dir = src_dir

    def __call__(self, filename: str) -> int:
        """Return ``filename``'s position in the registry.

        Parameters
        ----------
        filename : str
            An example's basename, as sphinx-gallery found it.

        Returns
        -------
        int
            Its registry index.

        Raises
        ------
        KeyError
            If the file is not registered. The test of gallery spec §3.7
            reports that first; this is the build's own backstop.
        """
        return _ORDER[filename]
