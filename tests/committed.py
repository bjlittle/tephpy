# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Read a file as this repository committed it, not as this tree happens to hold it.

The conda half of ``ci-floors`` runs this suite in a checkout whose
``pyproject.toml`` the floors generator has rewritten: one environment, every
floor an ``==`` pin, and every feature that tier cannot reach dropped outright.
A test asserting against the working tree passes everywhere except there, where
it fails weekly, hours after the push, and takes the tier's whole verdict down
with it -- the job then files an issue about a failure that is no floor. That
has happened twice (:issue:`155`), and
``tests/test_floors.py::test_no_test_reads_the_manifest_the_floors_job_rewrites``
is what now holds the tree to reading the committed file instead.

Shared rather than copied (:issue:`273`), for the reason ``tests/by_path.py``
was: nine sites had grown the same dozen lines, and the wording had already
drifted between them. Every one said it read the file "from the index". None of
them did -- ``git show HEAD:`` reads the **committed tree**, and the index would
be ``git show :pyproject.toml``. The distinction is live rather than pedantic: a
contributor who stages a new pixi task and runs the suite before committing
would get a pass out of a manifest that does not have it.

``.github/scripts/check_version_scheme.py`` keeps a copy of its own. It is run
by path from a directory that is not an importable package and that an exported
tree does not carry at all, so a gate there importing from ``tests/`` would fail
where this one merely skips.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

REPO = Path(__file__).parents[1]

#: The one file the floors generator rewrites, and the reason this module exists.
MANIFEST = "pyproject.toml"


def committed(path: str) -> str:
    """Return ``path`` as this repository has it committed at ``HEAD``.

    Carries the guard rather than leaving one to each caller: an export of the
    committed tree carries this suite and no repository, where ``git`` does not
    skip but raises.
    ``tests/test_floors.py::test_every_call_that_shells_out_to_git_is_guarded``
    names a helper guarding itself as how a call shared by several tests is
    guarded once, and holds this module to it.

    Parameters
    ----------
    path : str
        A repository-relative path.

    Returns
    -------
    str
        The file's contents at ``HEAD``.

    """
    if not (REPO / ".git").exists():
        pytest.skip(f"no repository to read the committed {path} from")
    found = subprocess.run(  # noqa: S603
        ["git", "show", f"HEAD:{path}"],  # noqa: S607
        check=False,
        capture_output=True,
        cwd=REPO,
        text=True,
    )
    if found.returncode:
        # The likeliest cause by far, and worth saying rather than surfacing
        # git's exit status: the file was written and not yet committed, which is
        # the state anyone adding or regenerating one passes through.
        pytest.fail(f"{path} is not committed at HEAD: {found.stderr.strip()}")
    return found.stdout


def committed_manifest() -> str:
    """Return the manifest this repository declares, not the one it was given.

    Returns
    -------
    str
        The committed ``pyproject.toml``.

    """
    return committed(MANIFEST)
