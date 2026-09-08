# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""`ci-linkcheck` scans what it claims to, and excludes only what cannot rot.

Nothing here reaches the network. The workflow does, once a week, and that run is
the wrong place to discover that a glob stopped naming `README.md` or that an
exclusion regex stopped matching the URL it was written for -- both of which fail
*quietly*, by checking less and reporting success.
"""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import quote

import pytest
import yaml

from tephpy._constants import WYOMING_URL

REPO = Path(__file__).parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci-linkcheck.yml"
IGNORE = REPO / ".lycheeignore"
SCRIPT = REPO / ".github" / "scripts" / "check_wyoming_endpoint.py"
FIXTURES = REPO / "tests" / "fixtures" / "io" / "README.md"


def workflow() -> dict:
    """Parse the workflow.

    Returns
    -------
    dict
        The parsed document.
    """
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def args(doc: dict) -> str:
    """Collect the arguments given to the lychee action.

    Parameters
    ----------
    doc : dict
        The parsed workflow.

    Returns
    -------
    str
        The `args` block, as written.
    """
    for step in doc["jobs"]["links"]["steps"]:
        if "lychee-action" in (step.get("uses") or ""):
            return step["with"]["args"]
    pytest.fail("no lychee step in the links job")


def patterns() -> list[str]:
    """Read the exclusion regexes, dropping comments and blank lines.

    Returns
    -------
    list of str
        One regex per entry.
    """
    lines = IGNORE.read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    ]


def excluded(url: str) -> bool:
    """Say whether any exclusion regex matches `url`.

    Parameters
    ----------
    url : str
        The URL to test.

    Returns
    -------
    bool
        Whether the URL would be skipped.
    """
    return any(re.search(pattern, url) for pattern in patterns())


def test_the_workflow_parses_as_yaml_and_the_schedule_is_weekly():
    doc = workflow()
    # PyYAML reads the bare key `on` as the boolean True under YAML 1.1, as
    # `test_topics_issue.py` records.
    schedule = doc[True]["schedule"]
    assert len(schedule) == 1
    _minute, _hour, day, month, weekday = schedule[0]["cron"].split()
    assert weekday != "*", "not pinned to a weekday, so it is not weekly"
    assert day == "*", "pinned to a day of the month, so it is not weekly"
    assert month == "*", "pinned to a month, so it is not weekly"


def test_both_jobs_declare_the_least_they_need_and_nothing_at_the_top():
    # Equality, not membership: declaring any permission sets every other to
    # `none`, so this block is the whole grant and a fourth entry appearing here
    # is a widening that should have to be argued for.
    #
    # `contents: read` is written out rather than left implicit. It is not what
    # makes `checkout` work today -- this repository is public, and `ci-topics`
    # runs the same shape without it, measured green -- but relying on that is a
    # dependency on the repository's visibility that nothing in the workflow
    # states (:pull:`285` review).
    doc = workflow()
    assert doc["permissions"] == {}
    for name in ("links", "endpoint"):
        assert doc["jobs"][name]["permissions"] == {
            "contents": "read",
            "issues": "write",
        }


def test_the_checkout_pin_matches_the_topics_workflow():
    # A stale pin here is a second copy that drifts from the ones already in the
    # tree; `test_topics_issue.py` holds the same rule against `ci-floors`.
    topics = yaml.safe_load(
        (REPO / ".github" / "workflows" / "ci-topics.yml").read_text(encoding="utf-8")
    )
    expected = topics["jobs"]["report"]["steps"][0]["uses"]
    doc = workflow()
    for name in ("links", "endpoint"):
        assert doc["jobs"][name]["steps"][0]["uses"] == expected


def test_every_third_party_action_is_pinned_to_a_full_sha():
    # An action named by tag is whatever that tag points at on the day it runs.
    doc = workflow()
    uses = [
        step["uses"]
        for job in doc["jobs"].values()
        for step in job["steps"]
        if step.get("uses")
    ]
    assert uses, "no actions found, so this test proves nothing"
    for entry in uses:
        _name, _, ref = entry.partition("@")
        assert re.fullmatch(r"[0-9a-f]{40}", ref), f"{entry} is not pinned to a SHA"


def test_the_readme_is_scanned():
    # The departure from geovista most likely to be lost in a later edit: its
    # globs do not name the README, and the README is the surface a reader meets
    # first on GitHub and on PyPI.
    assert "'./README.md'" in args(workflow())


def test_the_frozen_plans_are_not_scanned():
    # A plan is frozen once its implementation merges and is meant to go on
    # naming the URL it named; reporting those manufactures work on documents
    # nobody should edit.
    #
    # The path is asserted **bare**, without the `./` the input globs carry.
    # Measured with lychee 0.24.2 on 2026-09-08: `docs/src/developer/plans` drops
    # those files' 45 links, `./docs/src/developer/plans` is accepted and
    # silently ignored. This test first asserted the `./` form -- copied from
    # geovista, where the flag is not used -- and passed while every plan was
    # being scanned on every run.
    assert "--exclude-path 'docs/src/developer/plans'" in args(workflow())


def test_no_exclude_path_is_written_in_a_form_lychee_ignores():
    # The general rule behind the test above, so a second exclusion added later
    # cannot reintroduce the same silent no-op.
    for path in re.findall(r"--exclude-path '([^']+)'", args(workflow())):
        assert not path.startswith(("./", "/")), (
            f"--exclude-path {path!r} is silently ignored; write it bare"
        )
        assert (REPO / path).is_dir(), f"--exclude-path {path!r} is not a directory"


def test_the_docs_globs_would_otherwise_reach_the_plans():
    # Without which the exclusion above guards nothing, and would go on passing
    # after a glob change that had already stopped reaching them.
    plans = sorted((REPO / "docs" / "src" / "developer" / "plans").glob("*.md"))
    assert plans, "no plans on disk, so the exclusion has nothing to exclude"
    assert "'./docs/src/**/*.md'" in args(workflow())


def test_the_wyoming_template_is_excluded_as_it_is_actually_written():
    # The exclusion exists because the unformatted constant is answered 400 while
    # the archive is healthy. Matched against the constant itself rather than
    # against a copy of it: a regex that stopped matching would restore a
    # permanent false positive, and nothing else would say so.
    assert excluded(WYOMING_URL), (
        f"{WYOMING_URL} is scanned as text; it is a template, not a URL"
    )


def test_the_formatted_wyoming_url_is_not_excluded():
    # The exclusion must be narrow enough to leave the real request judgeable --
    # a pattern matching the whole host would silently cover the endpoint probe's
    # own URL too.

    formatted = WYOMING_URL.format(
        datetime=quote("2026-07-21 12:00:00"), station="03808"
    )
    assert not excluded(formatted)


def test_the_readme_clone_url_is_excluded_as_lychee_extracts_it():
    # Matched with the `git+` prefix, because that is the string lychee hands the
    # exclusion list -- measured with `lychee --dump`. This test first read the
    # URL from `^https` onward, which is a substring lychee never sees: it passed
    # while the URL was in fact being checked on every run.
    text = (REPO / "README.md").read_text(encoding="utf-8")
    found = re.findall(r"(?:git\+)?https://github\.com/bjlittle/tephpy\.git\S*", text)
    assert found, "the README no longer writes a clone URL for this to exclude"
    assert any(url.startswith("git+") for url in found), (
        "no `git+` form left in the README, which is the form this guards"
    )
    for url in found:
        assert excluded(url), f"{url} is a git transport, not a page"


def test_every_input_glob_matches_a_file():
    # An input that matches nothing is a check that checks nothing, and lychee
    # says so only as a WARN in a scheduled run's log. The `docs/src/**/*.txt`
    # glob carried over from geovista matched no file here and was dropped.
    globs = re.findall(r"'\./([^']+)'", args(workflow()))
    assert globs, "no input globs found, so this test proves nothing"
    for pattern in globs:
        assert list(REPO.glob(pattern)), f"{pattern} matches no file"


@pytest.mark.parametrize(
    "url",
    [
        "https://tephpy.example.invalid/thing.html",
        "http://example.invalid",
        "http://localhost:11000/",
        "https://tephpy--284.org.readthedocs.build/en/284/",
    ],
)
def test_the_unresolvable_placeholders_are_excluded(url):
    assert excluded(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://tephpy.readthedocs.io/en/latest/start/installation.html",
        "https://docs.conda.io/projects/conda/en/stable/",
        "https://pixi.sh",
        "https://docs.astral.sh/uv/",
        "https://github.com/bjlittle/tephpy",
    ],
)
def test_the_links_worth_checking_are_not_excluded(url):
    # The other half of the exclusion list's contract. A pattern loose enough to
    # swallow these would leave the check green over links nobody is watching --
    # the github.com one guards the clone-URL pattern in particular.
    assert not excluded(url)


def test_every_exclusion_is_a_valid_regex():
    for pattern in patterns():
        re.compile(pattern)


def test_the_exclusion_list_is_not_empty():
    # An empty file would exclude nothing and pass every test above that asserts
    # something is *not* excluded, while the two that assert something is
    # excluded would fail -- but only while they exist.
    assert patterns()


def test_the_endpoint_job_runs_the_script_by_path():
    # A workflow calling a script that has been renamed fails once a week, in a
    # run nobody is watching.
    doc = workflow()
    commands = " ".join(
        step.get("run") or "" for step in doc["jobs"]["endpoint"]["steps"]
    )
    assert f".github/scripts/{SCRIPT.name}" in commands


def test_the_probe_asks_for_the_ascent_the_fixtures_recorded():
    # The script's docstring claims a passing run also says the recorded captures
    # remain reproducible from the source their README names. That is only true
    # while it asks for the same station and time.
    source = SCRIPT.read_text(encoding="utf-8")
    station = re.search(r'^STATION = "(\d+)"', source, re.MULTILINE)
    assert station, "no STATION in the probe"
    provenance = FIXTURES.read_text(encoding="utf-8")
    assert f"id={station.group(1)}" in provenance, (
        "the probe asks for a station the fixtures did not record"
    )
    assert "datetime=2026-07-21%2012:00:00" in provenance
    assert "datetime(2026, 7, 21, 12, 0, tzinfo=UTC)" in source
