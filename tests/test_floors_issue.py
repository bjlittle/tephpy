# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the floors issue contract (floors spec §3.6)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "floors_issue.py"

# `MANIFEST.in` prunes `.github`, so an sdist ships these tests without the
# script they exercise. Guarding the module rather than the test is deliberate:
# an unguarded import fails *collection* there, taking the rest of the suite
# with it (floors spec §5). As in `test_floors.py`, the guard asks after the
# script and not `.git`: the `test` tier is exercised in a copy of the checkout
# with `.git` stripped, and this module must stay live there.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="not a checkout of the repository"
)


def _load():
    """Import the issue composer by path."""
    spec = importlib.util.spec_from_file_location("floors_issue", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["floors_issue"] = module
    spec.loader.exec_module(module)
    return module


FINDING = {
    "tier": "core",
    "half": "conda",
    "package": "matplotlib-base",
    "declared": ">=3.10",
    "failure": "PyparsingDeprecationWarning: 'oneOf' deprecated",
    "lowest": "3.10.3",
    "scanned": ["3.10.0", "3.10.1", "3.10.3"],
}


def test_the_key_omits_the_half_so_one_floor_raises_one_issue():
    module = _load()
    conda = module.key(FINDING)
    pypi = module.key({**FINDING, "half": "pypi"})
    assert conda == pypi


def test_the_body_carries_the_caveat_and_both_declaration_sites():
    module = _load()
    text = module.body(FINDING, "https://example.invalid/run/1")
    assert "lowest version that passes what tephpy runs" in text
    assert "requirements/pypi-core.txt" in text
    assert "[tool.pixi.dependencies]" in text
    assert "https://example.invalid/run/1" in text


def test_the_scan_line_is_one_sentence_in_both_outcomes():
    # `outcome` is interpolated into a sentence here and into a list item under a
    # two-half heading, so a phrase fitting one shape and not the other reaches
    # the reader as a filed issue that does not parse. Both branches are asserted
    # because only one of them was wrong: a clause where the other returns a noun
    # phrase gave "The scan found no version at or above the floor passed".
    module = _load()
    found = module.body(FINDING, "url")
    assert "The scan found **3.10.3**, the lowest that passes, of 3 tried." in found
    none = module.body({**FINDING, "lowest": None}, "url")
    assert (
        "The scan found no version at or above the floor that passes, of 3 tried."
        in none
    )


def test_an_unattributed_finding_says_so_and_names_no_declaration_site():
    # The sites are read from the culprit's declaring table, so with no culprit
    # there is nothing to read them from -- and falling back to the tier's own
    # pair is a guess that reads as established, because the core table resolves
    # into every tier (floors spec §3.1). The `test` tier is expected to produce
    # a finding of exactly this shape on the first run, so this is the issue a
    # reader meets before any other.
    module = _load()
    finding = {**FINDING, "tier": "test", "package": None, "lowest": None}
    text = module.body(finding, "url")
    assert "no attribution was reached" in text
    assert "Both declaration sites need the same edit" not in text
    assert "pypi-optional-test.txt" not in text
    assert "[tool.pixi.feature.test.dependencies]" not in text


def test_the_declaration_sites_follow_the_declaring_table_not_the_tier():
    # The core table is resolved into every tier, so the `test` tier can fail on
    # a package declared in `[tool.pixi.dependencies]` -- which is exactly the
    # first finding expected of this job, `matplotlib-base`. Naming the tier's
    # sites would send the fix to two files that do not declare it.
    module = _load()
    text = module.body({**FINDING, "tier": "test", "site": "core"}, "url")
    assert "requirements/pypi-core.txt" in text
    assert "[tool.pixi.dependencies]" in text
    assert "pypi-optional-test.txt" not in text


def _stub(monkeypatch, module, existing=None):
    """Stub out `gh`; return the list that records each argv `main` runs."""
    calls = []

    def _run(command, **_):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module.subprocess, "run", _run)
    monkeypatch.setattr(module, "_open_issues", lambda: existing or {})
    monkeypatch.setattr(module, "_gh", lambda: "/usr/bin/gh")
    return calls


def _write(tmp_path, findings):
    """Write each finding as an artifact; return the paths as `main` takes them."""
    paths = []
    for finding in findings:
        path = tmp_path / f"finding-{finding['half']}-{finding['tier']}.json"
        path.write_text(json.dumps(finding), encoding="utf-8")
        paths.append(str(path))
    return paths


def test_an_unattributed_finding_comments_rather_than_refiling(monkeypatch, tmp_path):
    # `_open_issues` rebuilds each key from the issue title, so a key that does
    # not round-trip through `title` never matches an issue already open and the
    # weekly run files another. The unattributed finding is the one whose two can
    # differ, and it is not hypothetical: the `test` tier solves and fails its
    # exercise today, which is exactly the finding that carries no package.
    module = _load()
    finding = {**FINDING, "package": None, "lowest": None}
    titled = module.title(finding).removeprefix("Dependency floor: ")
    assert module.key(finding) == titled.replace(" / ", "/")
    calls = _stub(monkeypatch, module, existing={module.key(finding): "7"})
    paths = _write(tmp_path, [finding])
    monkeypatch.setattr(sys, "argv", ["floors_issue.py", *paths, "--run-url", "u"])
    assert module.main() == 0
    assert [call[1:3] for call in calls] == [["issue", "comment"]]


def test_both_halves_of_one_floor_file_one_issue(monkeypatch, tmp_path):
    # The key omits the half so that one floor is one issue, but the open-issue
    # map is read once, before anything is filed -- so without grouping the pypi
    # half cannot see the issue the conda half just created, and files a second
    # under the same title. The `key` equality above holds either way, which is
    # why telling the two apart takes filing two artifacts (floors spec §3.6).
    module = _load()
    calls = _stub(monkeypatch, module)
    paths = _write(tmp_path, [FINDING, {**FINDING, "half": "pypi"}])
    monkeypatch.setattr(sys, "argv", ["floors_issue.py", *paths, "--run-url", "u"])
    assert module.main() == 0
    assert [call[1:3] for call in calls] == [["issue", "create"]]
    # And the one issue reports each half, because a package can be at a
    # different version in the channel and the index (floors spec §3.5).
    body = calls[0][calls[0].index("--body") + 1]
    assert "conda" in body
    assert "pypi" in body


def test_no_artifacts_is_refused_rather_than_reported_as_nothing_wrong(
    monkeypatch, tmp_path
):
    # The filing job runs only when a tier failed, so reaching it with nothing to
    # read means the diagnosis did not produce its artifact. Exiting 0 there is
    # indistinguishable from a run that found nothing to file, which is the one
    # thing this job must never say while something is broken.
    module = _load()
    calls = _stub(monkeypatch, module)
    missing = str(tmp_path / "findings" / "*.json")
    monkeypatch.setattr(sys, "argv", ["floors_issue.py", missing, "--run-url", "u"])
    assert module.main() == 1
    assert calls == []
