# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The installation page's pre-release note tracks the version (start spec §3.7)."""

from __future__ import annotations

from pathlib import Path

import tephpy

REPO = Path(__file__).parents[1]
PAGE = REPO / "docs" / "src" / "start" / "installation.rst"

#: The sentence the note must carry, verbatim. Matched as a substring rather than
#: by shape, so rewording the note is a deliberate act that updates this too.
PRERELEASE = "tephpy has not had its first release yet"


def test_the_prerelease_note_is_present_exactly_while_the_version_is_a_dev_version():
    """The note is a claim about the world, so it is not left to memory.

    setuptools_scm reports a ``.dev`` version until the first tag. On the release
    commit this test fails, and that is the intended behaviour rather than a side
    effect: the tag is cut, this fails, the note comes out, and the page is true
    again. Nothing here reaches the network -- spec §8.5 forbids it, and the
    installed version answers the question offline.
    """
    released = ".dev" not in tephpy.__version__
    carries = PRERELEASE in PAGE.read_text(encoding="utf-8")
    assert carries is not released, (
        f"version {tephpy.__version__} is "
        f"{'released' if released else 'a development version'}, so the page "
        f"{'must not' if released else 'must'} carry the pre-release note"
    )
