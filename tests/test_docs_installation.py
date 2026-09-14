# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Every carrier's pre-release note tracks the version (start spec §3.7)."""

from __future__ import annotations

from pathlib import Path

from packaging.version import Version
import pytest

import tephpy

REPO = Path(__file__).parents[1]

#: The files carrying the pre-release note, relative to the repository root. The
#: installation page states it for a reader of the documentation and ``README.md``
#: for the one arriving by the GitHub or PyPI door instead, which makes it one
#: claim about the world written twice. They are gated together because a release
#: retires it from both at once: a gate over the page alone would go green on the
#: release commit while the README went on saying tephpy had never been published.
CARRIERS = (
    Path("docs") / "src" / "start" / "installation.rst",
    Path("README.md"),
)

#: The sentence each carrier must hold, verbatim. Matched as a substring rather than
#: by shape, so rewording the note is a deliberate act that updates this too -- and
#: one sentence shared by both carriers is one wording to keep true rather than two
#: that can drift into disagreeing about the same fact.
PRERELEASE = "tephpy has not had its first release yet"

#: The first release. The note is about whether tephpy has *ever* been published,
#: which a ``.dev`` suffix cannot answer: setuptools_scm reports ``0.1.0.dev190``
#: before the first tag and ``0.1.1.dev1`` on the commit after it, and both carry
#: the suffix. `packaging` sorts the first below this version and the second above,
#: which is the distinction the note actually rests on.
FIRST_RELEASE = Version("0.1.0")


def _carries(carrier: Path) -> bool:
    """Whether one carrier still states that tephpy has never been released."""
    return PRERELEASE in (REPO / carrier).read_text(encoding="utf-8")


@pytest.mark.parametrize("carrier", CARRIERS, ids=str)
def test_the_prerelease_note_is_gone_once_tephpy_has_been_released(carrier):
    """One-sided: released forbids the note, unreleased does not require it.

    The two-sided rule this replaces deadlocked the release it was written for,
    one turn further on than the ``.dev`` deadlock start spec §3.7 already
    records. The signal changes when the repository is *tagged*; the note is
    removed when a file is *edited*; and those are different commits over the
    same tree. Requiring the note while unreleased therefore forbade removing it
    from the commit that gets tagged -- and that commit is the one that is built,
    with ``README.md`` as the distribution's long description. The published
    ``0.1.0`` would have told every reader of its PyPI page that tephpy had never
    been released, and the correction would have landed in ``0.1.1``.

    A release candidate does not lift it either, which is what makes the window
    unavoidable rather than merely awkward: ``packaging`` sorts ``0.1.0rc1``
    *below* ``0.1.0``, so the whole rehearsal runs with the notes still demanded.

    So the direction that protects a reader is kept and the one that deadlocked
    is dropped. Removing the notes early is now a deliberate edit in a reviewed
    pull request rather than something this refuses; what it still cannot be is
    forgotten, because a released tephpy that claims otherwise fails here.

    Parametrised over the carriers rather than run over their concatenation, so a
    failure names the file still to edit.

    Nothing here reaches the network -- spec §8.5 forbids it, and the installed
    version answers the question offline.
    """
    if Version(tephpy.__version__) < FIRST_RELEASE:
        pytest.skip(f"{tephpy.__version__} predates the first release")
    assert not _carries(carrier), (
        f"tephpy {tephpy.__version__} is released, so {carrier} must not say it "
        f"has never been"
    )


def test_the_carriers_agree_about_the_note():
    # What survives of the two-sided rule, and the part :pull:`284` was actually
    # about: one claim written on two surfaces, so the two must not disagree.
    # Removing the note from the page and leaving it in the README is the shape
    # that gate was written to catch, and it is caught here whether or not
    # anything has been released.
    carried = {str(carrier): _carries(carrier) for carrier in CARRIERS}
    assert len(set(carried.values())) == 1, (
        f"the carriers disagree about the pre-release note: {carried}"
    )


def test_every_carrier_exists():
    # CARRIERS names files by path. A rename that misses this list turns the check
    # above into a FileNotFoundError -- a failure, but not the one anyone is
    # looking for, and one that says nothing about the note it was gating.
    missing = [carrier for carrier in CARRIERS if not (REPO / carrier).is_file()]
    assert missing == []


def test_carriers_names_both_surfaces_the_note_reaches():
    # Membership, not equality: a later surface repeating the note must not break
    # this test, but dropping either of these -- narrowing the gate back to the
    # page alone -- must.
    assert Path("docs") / "src" / "start" / "installation.rst" in CARRIERS
    assert Path("README.md") in CARRIERS


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
