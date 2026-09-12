# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Every job that checks out says it may read the repository.

``actions/checkout`` clones with ``GITHUB_TOKEN``, so it wants a ``contents``
grant. Every workflow here opens with ``permissions: {}``, which sets every
scope to ``none`` for every job in the file: a job declaring no block of its
own inherits that, and a job declaring one replaces it outright rather than
merging into it. Either way ``contents`` has to be written out, or the job
holds no grant to read what it has just asked to clone.

Such a checkout works anyway, because tephpy is public and a public repository
is readable without a token at all. That is the reason this gate exists rather
than the reason it does not: the grant is what *states* the dependency, and
without it the whole of CI rests on a repository setting no file in the tree
mentions (:issue:`286`). Twelve jobs were resting on it, two thirds of them on
schedules nobody watches, which is where the failure would go unnoticed
longest.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    from collections.abc import Mapping

REPO = Path(__file__).parents[1]
GITHUB = REPO / ".github"
WORKFLOWS = GITHUB / "workflows"

# The suite runs from a checkout; a tree taken without its dotted directories
# has no workflows to hold to anything. As in `tests/test_stale.py`, the guard
# asks after the directory that would be absent rather than after the workflows
# themselves -- a checkout whose workflows had been deleted is a failure, not a
# reason to stand this module down.
pytestmark = pytest.mark.skipif(
    not GITHUB.is_dir(), reason="not a checkout of the repository"
)

#: The suffixes GitHub Actions reads from ``.github/workflows``. Both, because a
#: workflow declared in the other one runs like any other, and a scan globbing
#: only ``*.yml`` would wave its checkouts through -- the hole
#: `tests/test_stale.py` closed for the stale bot's exemptions (:pull:`290`).
SUFFIXES = ("*.yml", "*.yaml")

#: Absent, as distinct from present and empty. ``permissions: {}`` *is* a grant
#: -- the empty one -- and settles the question where an absent block lets it
#: fall through to the level above.
_ABSENT = object()

#: What GitHub's two whole-scope shorthands grant on ``contents``.
_SHORTHAND = {"read-all": "read", "write-all": "write"}


def contents(doc: Mapping[str, Any], job: Mapping[str, Any]) -> str | None:
    """Return the ``contents`` grant ``job`` runs with.

    Resolved the way GitHub resolves it: a job's own ``permissions`` block
    replaces the workflow's outright rather than merging into it, so the first
    block found is the whole grant and any scope it omits is ``none``.

    Parameters
    ----------
    doc : mapping
        The parsed workflow.
    job : mapping
        One job from it.

    Returns
    -------
    str or None
        ``"read"`` or ``"write"``, or ``None`` where the job holds no grant --
        which includes both levels staying silent, since what GitHub falls back
        on there is a repository setting rather than anything in the tree.

    """
    for block in (job.get("permissions", _ABSENT), doc.get("permissions", _ABSENT)):
        if block is _ABSENT:
            continue
        if isinstance(block, str):
            assert block in _SHORTHAND, f"unrecognised permissions shorthand: {block}"
            return _SHORTHAND[block]
        return block.get("contents")
    return None


def grants(directory: Path | None = None) -> dict[str, str | None]:
    """Return the ``contents`` grant held by each job that checks out.

    A job calling a reusable workflow carries no ``steps`` and so checks nothing
    out itself; the callee's jobs hold their own grants, and are collected here
    where they are declared, in their own file.

    Parameters
    ----------
    directory : Path, optional
        Where to look. Defaults to this repository's workflows; the parameter is
        what lets the tests below run the scan over a tree they control.

    Returns
    -------
    dict
        ``workflow / job`` against its grant, for the jobs that check out.

    """
    directory = directory or WORKFLOWS
    paths = sorted(path for suffix in SUFFIXES for path in directory.glob(suffix))
    assert paths, f"no workflows found under {directory}, so this gate proves nothing"
    found: dict[str, str | None] = {}
    for path in paths:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for name, job in (doc.get("jobs") or {}).items():
            steps = job.get("steps") or []
            if any("actions/checkout" in (step.get("uses") or "") for step in steps):
                found[f"{path.name} / {name}"] = contents(doc, job)
    return found


def test_every_job_that_checks_out_names_a_contents_grant():
    # Derived, not listed. :issue:`286` was written against three jobs -- the
    # three whose omission was *visible*, because they declare a `permissions`
    # block that names something else -- and there were twelve. The other nine
    # declare no block at all and hold no grant for the same reason, by the same
    # mechanism: `permissions: {}` at the top of the file. A gate keyed to
    # "declares a block and checks out", which is what the issue proposed, would
    # have cleared all nine.
    found = grants()
    assert found, "no job checks out, so this gate proves nothing"
    missing = sorted(label for label, grant in found.items() if grant is None)
    assert not missing, f"checks out with no `contents` grant: {missing}"


def test_no_job_that_checks_out_asks_to_write():
    # A set rather than a list, so nothing here has to be maintained as jobs
    # come and go, and a `write` arriving fails rather than blending in. Nothing
    # needs one: `ci-locks` is the one job that puts a commit on a branch, and
    # it does that through `TEPHPY_BOT_TOKEN` rather than through `GITHUB_TOKEN`
    # -- deliberately, since a bot commit made with `GITHUB_TOKEN` triggers no
    # CI, and the checks standing over what that bot wrote are the point of it.
    assert set(grants().values()) == {"read"}


@pytest.mark.parametrize(
    ("doc", "job", "expected"),
    [
        # The nine: nothing at the job level, `permissions: {}` above it.
        ({"permissions": {}}, {}, None),
        # The three the issue found: a block that names something else.
        ({"permissions": {}}, {"permissions": {"issues": "write"}}, None),
        # `ci-label`, which inherits a grant from the top of its file.
        ({"permissions": {"contents": "read", "issues": "write"}}, {}, "read"),
        # `ci-linkcheck`, and what the twelve become.
        (
            {"permissions": {}},
            {"permissions": {"contents": "read", "issues": "write"}},
            "read",
        ),
        # Replaced, not merged -- a reading of `permissions` that merged the two
        # levels would call this "read", and it is `none`. No job in the tree has
        # this shape, and the gate has to be right about it before one does.
        (
            {"permissions": {"contents": "read"}},
            {"permissions": {"issues": "write"}},
            None,
        ),
        # Silent at both levels: the grant is then whatever the repository's
        # Actions settings say, which is not something a file states.
        ({}, {}, None),
        # The whole-scope shorthands, which are strings rather than blocks.
        ({"permissions": "read-all"}, {}, "read"),
        ({"permissions": {}}, {"permissions": "write-all"}, "write"),
    ],
)
def test_a_grant_resolves_the_way_github_resolves_it(doc, job, expected):
    assert contents(doc, job) == expected


def test_a_scan_that_found_no_workflows_fails(tmp_path):
    # Every assertion above reads a dictionary this scan built. An empty one
    # satisfies `not missing` and would report a clean pass over nothing.
    with pytest.raises(AssertionError, match="no workflows found"):
        grants(tmp_path)


def test_a_workflow_declared_in_a_yaml_file_is_collected(tmp_path):
    # GitHub Actions reads both suffixes, so a checkout declared in the other
    # one is a checkout that runs -- and a scan globbing `*.yml` alone would
    # leave it ungoverned while reporting that every job it found was fine.
    (tmp_path / "ci-elsewhere.yaml").write_text(
        "permissions: {}\n"
        "jobs:\n"
        "  build:\n"
        "    steps:\n"
        "      - uses: actions/checkout@v7\n",
        encoding="utf-8",
    )
    assert grants(tmp_path) == {"ci-elsewhere.yaml / build": None}
