#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Approve the figures the documentation build just published.

The companion to ``check_docs_figures.py``: that gate compares each published
figure against ``docs/baseline``, and this is what puts a new or intended figure
there (plots spec §3.6). Re-blessing is one command and a diff to read rather
than a hand copy per file, which is what keeps a baseline update from being the
step someone does partially.

It approves *whatever was rendered*. That is the point and the hazard: a
regression is copied over its baseline exactly as willingly as a correction, and
the only thing standing between the two is the diff this prints. Read it before
committing, and commit the baselines with the change that caused them.

The declarations are read through ``check_docs_figures``, not re-parsed, so the
set blessed here is by construction the set that gate checks. A baseline no page
declares any longer is removed, which is the same orphan the gate reports -- and
is why the refusals that say the declarations could not be read are shared too,
and run before a file is touched. A declaration the scan cannot read leaves a
live baseline looking exactly like an orphan, so without them this command's
answer to a near miss the gate has just reported would be to delete the pin.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from pathlib import Path
import shutil
import sys

from check_docs_figures import IMAGES, SUFFIX, Figure, collect, unreadable
from matplotlib.image import imread
from matplotlib.testing.compare import compare_images
from matplotlib.testing.exceptions import ImageComparisonFailure


def _updated_suffix(figure: Figure) -> str:
    """Describe how a figure changed, for the 'updated' report line.

    Parameters
    ----------
    figure : Figure
        The figure being re-blessed. Both ``figure.baseline`` and
        ``figure.built`` must already exist and are known to differ.

    Returns
    -------
    str
        A parenthesised RMS or size-pair suffix, or an empty string if
        neither could be measured.

    """
    try:
        # A tolerance of 0 is what forces a measurement out of a pair of
        # files already known to differ, rather than the `None` the gate's
        # own tolerance would return for a change too small for it to report.
        # `git diff` on a PNG says only "Binary files differ", so without a
        # number here "read the diff" has nothing to read.
        result = compare_images(
            str(figure.baseline), str(figure.built), 0, in_decorator=True
        )
    except ImageComparisonFailure:
        # A pixel-size change is the ordinary reason to re-bless, and is
        # exactly what the gate's `CHANGED` advice sends a contributor here
        # to fix -- this path must be the most robust one in the script, not
        # the most fragile. Each image's own size, read independently, stands
        # in for the RMS there is no pixel-for-pixel comparison left to
        # produce.
        built_size = imread(figure.built).shape[:2]
        baseline_size = imread(figure.baseline).shape[:2]
        return f" (size {built_size} != baseline {baseline_size})"
    if not result:
        return ""
    # `compare_images` writes a '-failed-diff.png' beside the built image at
    # any tolerance, including the 0 used only to force this measurement.
    # Left behind, it would misname a successful blessing as one with an
    # unresolved diff.
    diff = result.get("diff")
    if diff:
        Path(diff).unlink(missing_ok=True)
    return f" (RMS {result['rms']:.2f})"


def main() -> int:
    """Copy the built figures over their baselines.

    Returns
    -------
    int
        ``0`` when every declared figure was built, ``1`` otherwise.

    """
    if len(sys.argv) < 2:
        print("usage: bless_docs_figures.py <html-root> [source-root] [baselines]")
        return 1
    root = Path(sys.argv[1])
    repo = Path(__file__).parents[2]
    source = Path(sys.argv[2]) if len(sys.argv) > 2 else repo / "docs" / "src"
    baselines = Path(sys.argv[3]) if len(sys.argv) > 3 else repo / "docs" / "baseline"
    for directory in (root, source):
        if not directory.is_dir():
            print(f"no such directory: {directory}")
            return 1

    figures = collect(source, root / IMAGES, baselines)
    if not figures:
        print("no page declares a figure -- nothing to bless")
        return 1

    # The sweep at the end of this function deletes every baseline no
    # declaration claims, so a declaration the scan cannot read is a live
    # baseline deleted -- reported as the rename it is indistinguishable from.
    # This runs before anything is copied or removed, because it is the gate's
    # advice for a near miss that sends a contributor here in the first place.
    if unreadable(source, figures):
        print("Nothing was blessed. Fix the declarations first.")
        return 1

    # A figure that was not built cannot be approved, and blessing the rest
    # silently would leave the gate red for a reason this command appears to
    # have addressed.
    missing = sorted(figure.name for figure in figures if not figure.built.is_file())
    if missing:
        print(f"these declared figures were not built: {missing}")
        print("Nothing was blessed. Fix the build first.")
        return 1

    baselines.mkdir(parents=True, exist_ok=True)
    added, updated = [], []
    for figure in sorted(figures):
        if not figure.baseline.is_file():
            added.append(figure.name)
        elif figure.baseline.read_bytes() != figure.built.read_bytes():
            updated.append(f"{figure.name}{_updated_suffix(figure)}")
        shutil.copyfile(figure.built, figure.baseline)

    claimed = {figure.baseline for figure in figures}
    removed = []
    for path in sorted(baselines.glob(f"*{SUFFIX}")):
        if path not in claimed:
            path.unlink()
            removed.append(path.stem)

    for label, names in (
        ("added", added),
        ("updated", updated),
        ("removed", removed),
    ):
        for name in names:
            print(f"{label:8} {name}")
    if not (added or updated or removed):
        print("baselines already match the build -- nothing changed")
    else:
        print(
            f"\n{len(added)} added, {len(updated)} updated, {len(removed)} removed. "
            "Read the diff before committing: this command approves a regression "
            "as readily as a fix (plots spec §3.6)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
