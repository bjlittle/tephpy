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
# script and not `.git`: nothing here reads history, and a guard naming the index
# would stand the module down wherever history is absent.
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


def test_the_issue_quotes_what_the_highest_version_tried_failed_on():
    # The baseline failure is the failure of the floors as declared, which the
    # reader knows before opening the issue -- it is why the tier is red. Where
    # nothing passed, what the candidates failed on is the finding, and
    # :issue:`145` threw it away: it reported no passing `sphinx-design`,
    # when 0.6.1 passes and every candidate had been stopped by a second broken
    # floor. Naming the version the trace belongs to matters as much as the
    # trace: a reader who cannot see how far the scan got cannot tell an
    # unsolvable package from one blocked by something else (:issue:`149`).
    module = _load()
    finding = {**FINDING, "lowest": None, "blocked": "Unable to read file"}
    text = module.body(finding, "url")
    assert "3.10.3, the highest version tried, and what it failed on" in text
    assert "Unable to read file" in text
    assert "failure at the declared floors (conda)" in text


def test_the_issue_says_why_no_passing_version_is_not_a_contradiction():
    # "Attributed X, and no version of X passes" reads as "X has no good
    # version", which is how :issue:`145` was read. The two steps ask different
    # questions -- relaxation asks whether the tier resolves, the scan asks for
    # resolve *and* exercise -- and the gap is where the second broken floor
    # sits. Tied to a quoted trace, since the sentence ends by pointing at one.
    module = _load()
    stalled = module.body({**FINDING, "lowest": None, "blocked": "trace"}, "url")
    assert "ask different questions" in stalled
    found = module.body({**FINDING, "blocked": "trace"}, "url")
    assert "ask different questions" not in found
    dry = module.body({**FINDING, "lowest": None, "scanned": [], "blocked": ""}, "url")
    assert "ask different questions" not in dry
    assert "highest version tried" not in dry


def test_the_pixi_table_named_is_the_one_the_floor_is_declared_in():
    # A tier declares floors in two pixi tables, and both pair with the one
    # requirements file. Naming the dependency table by default would send the
    # reader to a table the package is not in, where the fix is to add a second
    # declaration of it -- the manifest then floors it twice (:issue:`151`).
    module = _load()
    finding = {**FINDING, "tier": "docs", "package": "playwright"}
    text = module.body({**finding, "table": "pypi-dependencies"}, "url")
    assert "[tool.pixi.feature.docs.pypi-dependencies]" in text
    assert "requirements/pypi-optional-docs.txt" in text
    conda = module.body(finding, "url")
    assert "[tool.pixi.feature.docs.dependencies]" in conda
    assert "pypi-dependencies" not in conda


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


def test_the_issue_names_the_package_as_the_file_it_sends_you_to_spells_it():
    # The issue is keyed and titled on the manifest's spelling, so that one floor
    # is one issue whichever half found it (floors spec §3.6) -- and a reader
    # sent to the requirements file with only that name finds no such line, the
    # package being `matplotlib` there. The body sends them to both files to make
    # the same edit, so it has to name both lines.
    module = _load()
    text = module.body({**FINDING, "alias": "matplotlib"}, "url")
    assert "`requirements/pypi-core.txt` — declared there as `matplotlib`" in text
    # And says nothing where the two sites agree, which is most of them: an
    # "also known as" reading back the name above it is noise on every issue.
    assert "declared there as" not in module.body(FINDING, "url")


def test_the_requirements_file_named_is_the_one_declaring_the_floor():
    # The two sites need not floor a package in the same tier: `setuptools_scm`
    # is a `test` requirement and a core declaration in the manifest, so reading
    # both files off one key names one of them wrongly -- and names it as a file
    # to make the same edit in, where there is no such line to edit.
    module = _load()
    text = module.body(
        {
            **FINDING,
            "tier": "test",
            "package": "setuptools-scm",
            "site": "core",
            "requirements": "requirements/pypi-optional-test.txt",
            "alias": "setuptools_scm",
        },
        "url",
    )
    assert "`pyproject.toml`, `[tool.pixi.dependencies]`" in text
    assert "requirements/pypi-optional-test.txt" in text
    assert "requirements/pypi-core.txt" not in text


def test_a_floor_declared_for_pixi_alone_names_one_line():
    # The manifest declares packages the pip requirements have no counterpart
    # for -- `make`, which drives the documentation build. Telling that reader
    # that "both declaration sites need the same edit" and naming a file with no
    # such line reads as a line they failed to find, so the body says instead
    # that this floor is declared once. An absent key is a finding from before
    # the diagnosis answered this, and keeps the pairing it was read with.
    module = _load()
    finding = {**FINDING, "tier": "docs", "package": "make", "site": "docs"}
    text = module.body({**finding, "requirements": ""}, "url")
    assert "Declared for pixi alone" in text
    assert "requirements/" not in text
    # The caveat of floors spec §3.5 is about the scanned version, not about the
    # declaration, so it is owed to this reader too.
    assert module.CAVEAT in text
    assert "requirements/pypi-optional-docs.txt" in module.body(finding, "url")
