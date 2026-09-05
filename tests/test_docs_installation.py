# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The installation page's pre-release note tracks the version (start spec §3.7)."""

from __future__ import annotations

from pathlib import Path

from packaging.version import Version
import pytest

import tephpy

REPO = Path(__file__).parents[1]
PAGE = REPO / "docs" / "src" / "start" / "installation.rst"

#: The sentence the note must carry, verbatim. Matched as a substring rather than
#: by shape, so rewording the note is a deliberate act that updates this too.
PRERELEASE = "tephpy has not had its first release yet"

#: The first release. The note is about whether tephpy has *ever* been published,
#: which a ``.dev`` suffix cannot answer: setuptools_scm reports ``0.1.0.dev190``
#: before the first tag and ``0.1.1.dev1`` on the commit after it, and both carry
#: the suffix. `packaging` sorts the first below this version and the second above,
#: which is the distinction the note actually rests on.
FIRST_RELEASE = Version("0.1.0")


def test_the_prerelease_note_is_present_exactly_while_the_version_is_a_dev_version():
    """The note is a claim about the world, so it is not left to memory.

    The question is whether tephpy has ever been released, not whether this
    checkout sits exactly on a tag. Testing for a ``.dev`` suffix answers the
    second, and deadlocks on the first: after ``v0.1.0`` the next commit reports
    ``0.1.1.dev1``, which carries the suffix, so a suffix test would demand the
    now-false note return -- and there is no commit at which it could be removed,
    since removing it after tagging happens on a ``.dev`` commit too. Comparing
    against the first release has neither problem: ``0.1.0.dev190`` sorts below
    it, ``0.1.0`` and ``0.1.1.dev1`` above.

    Nothing here reaches the network -- spec §8.5 forbids it, and the installed
    version answers the question offline.
    """
    released = Version(tephpy.__version__) >= FIRST_RELEASE
    carries = PRERELEASE in PAGE.read_text(encoding="utf-8")
    assert carries is not released, (
        f"version {tephpy.__version__} is "
        f"{'released' if released else 'a development version'}, so the page "
        f"{'must not' if released else 'must'} carry the pre-release note"
    )


@pytest.mark.parametrize(
    ("version", "released"),
    [
        # Before the first tag, which is where this project sits today.
        ("0.1.0.dev190", False),
        ("0.1.0.dev190+g1234567", False),
        # On it.
        ("0.1.0", True),
        # The commit after it. A `.dev` test reads this as unreleased and demands
        # the note back, which is the deadlock this parametrisation exists to pin.
        ("0.1.1.dev1", True),
        ("0.1.1.dev1+g89abcde", True),
        # And onwards.
        ("0.2.0", True),
        ("1.0.0", True),
    ],
)
def test_the_release_signal_reads_the_sequence_a_dev_suffix_cannot(version, released):
    """Has tephpy ever been released -- not, is this checkout exactly a tag."""
    assert (Version(version) >= FIRST_RELEASE) is released
