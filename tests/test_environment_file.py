# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""What keeps `requirements/tephpy.yml` a true rendering of the manifest.

The environment file is a convenience for people outside pixi: `conda env create
-f requirements/tephpy.yml` gives them the `default` environment, the full stack
against the newest Python this project supports. `ci-locks` regenerates it weekly
beside the lock, but nothing regenerates it when the manifest changes between
those runs, so it is a derived copy of the dependency set with the same standing
as the lock's own -- free to drift, and wrong in the interval (:issue:`252`).

This is asserted by regenerating rather than by parsing, which is the whole
difference between this module and `tests/test_lock.py`. That one has to read
both sides, because re-solving a lock costs a network round trip; the export
costs milliseconds and reads no network, so the file can simply be produced again
and compared. A second reader of a format is a thing that can disagree with the
first -- `tests/test_lock.py` shipped exactly that defect, its two readers having
diverged over environment markers -- and regenerating leaves nothing to diverge.

Both sides are read from the index. The conda half of `ci-floors` runs this suite
in a checkout whose `pyproject.toml` the floors generator has rewritten, and an
export from that manifest is a rendering of something this repository never
committed (:issue:`155`).

Recorded rather than guarded: the export's formatting belongs to pixi, so a pixi
upgrade that changes it fails here. That is a true finding -- the committed file
*is* stale against the new export -- and regenerating settles it, but the failure
names pixi rather than the manifest, and a reader meeting it should know that.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

REPO = Path(__file__).parents[1]

#: The published rendering, and the environment it renders. `default` carries the
#: newest supported Python and the whole package stack, which is what someone
#: reaching for a conda environment file wants; `--name` overrides the
#: environment's own name, so the file does not tell them to create an
#: environment called `default`.
RENDERED = "requirements/tephpy.yml"
ENVIRONMENT = "default"
NAME = "tephpy"


def committed(path: str) -> str:
    """Return ``path`` as the repository has it committed, not as it is on disk.

    Parameters
    ----------
    path : str
        A repository-relative path.

    Returns
    -------
    str
        The file's contents at ``HEAD``.

    Notes
    -----
    Carries its own index guard, as `tests/test_lock.py` does and for the reason
    `tests/test_floors.py::test_every_test_that_shells_out_to_git_is_guarded_on_
    the_index` gives: an unpacked sdist ships this suite and no repository, where
    `git` does not skip but raises.

    """
    if not (REPO / ".git").exists():
        pytest.skip("no index to read the committed files from")
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
        # the state anyone adding or regenerating it passes through.
        pytest.fail(f"{path} is not committed at HEAD: {found.stderr.strip()}")
    return found.stdout


def exported() -> str:
    """Return the environment file the committed manifest renders to.

    Returns
    -------
    str
        The export's output, in the form this repository stores a file in:
        exactly one trailing newline. The export itself ends in a blank line, and
        `end-of-file-fixer` takes that off every file the repository commits, so
        the raw output can never equal the committed one. Normalising here rather
        than loosening the comparison keeps the assertion exact -- every byte
        before the end still has to match.

    Notes
    -----
    Exported from a copy of the *committed* manifest in a scratch directory
    rather than from the working tree, so that what is compared is a rendering of
    what this repository declares. Verified to need nothing else beside it: the
    export reads the manifest, not the lock, and reaches no network.

    """
    if (pixi := shutil.which("pixi")) is None:
        pytest.skip("pixi is not on PATH to render the environment file with")
    with tempfile.TemporaryDirectory() as scratch:
        manifest = Path(scratch) / "pyproject.toml"
        manifest.write_text(committed("pyproject.toml"), encoding="utf-8")
        return (
            subprocess.run(  # noqa: S603
                [
                    pixi,
                    "workspace",
                    "export",
                    "conda-environment",
                    "--manifest-path",
                    str(manifest),
                    "--environment",
                    ENVIRONMENT,
                    "--name",
                    NAME,
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.rstrip("\n")
            + "\n"
        )


def test_the_export_renders_something():
    """The export produced a file, so the comparison below is about something.

    Two empty strings compare equal. This is what fails when `pixi workspace
    export` changes its interface, or the environment named here stops existing,
    rather than letting either pass as agreement.
    """
    rendered = exported()
    assert rendered.strip(), "the export rendered nothing"
    assert f"name: {NAME}" in rendered, (
        f"the export did not name the environment {NAME}"
    )


def test_the_environment_file_is_what_the_manifest_renders_to():
    """The committed file is exactly what the committed manifest exports.

    Regenerate `requirements/tephpy.yml` with the command in `ci-locks.yml` when
    this fails -- and note it fails for a manifest change *or* a pixi upgrade that
    reformats the export, the module docstring saying why the second is real too.
    """
    assert committed(RENDERED) == exported()
