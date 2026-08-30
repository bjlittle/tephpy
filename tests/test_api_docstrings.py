# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The published API docstring gate (:issue:`227`).

The gate's own definition of "the public API" is the thing under test here.
It reproduces sphinx-autoapi's selection without a build, so it can run in
pre-commit; ``tests/test_docs_api_inventory.py`` is what earns that shortcut
by pinning the result against a real build's ``objects.inv``.

The cases below pin the parts of that selection a reader cannot guess from
the module layout: that a private module's singleton contributes published
methods, and that a dataclass field does not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]


def test_published_objects_covers_the_documented_modules(gate):
    """The 15 module pages autoapi builds, and no private module."""
    names = {entry.name for entry in gate.published_objects() if entry.role == "module"}
    assert names == {
        "tephpy",
        "tephpy.calc",
        "tephpy.exceptions",
        "tephpy.io",
        "tephpy.io.igra",
        "tephpy.io.wyoming",
        "tephpy.plotting",
        "tephpy.plotting.axes",
        "tephpy.plotting.barbs",
        "tephpy.plotting.isopleths",
        "tephpy.plotting.logo",
        "tephpy.plotting.shading",
        "tephpy.samples",
        "tephpy.sounding",
        "tephpy.transforms",
    }


def test_published_objects_reaches_the_config_singleton(gate):
    """``tephpy.config`` is a private-module instance with published methods.

    ``tephpy._config`` has no API page, but the singleton is reachable from
    ``tephpy``, so autoapi documents ``tephpy.config.load`` and its
    neighbours. An enumerator built from the module list alone would miss
    every one of them.
    """
    names = {entry.name for entry in gate.published_objects()}
    assert "tephpy.config.load" in names
    assert "tephpy.config.reset" in names
    assert not any(name.startswith("tephpy._config") for name in names)


def test_published_objects_excludes_attributes_and_data(gate):
    """A dataclass field carries no docstring, so there is nothing to stamp."""
    names = {entry.name for entry in gate.published_objects()}
    assert "tephpy.calc.Profile" in names
    assert "tephpy.calc.Profile.lcl_pressure" not in names
    assert "tephpy.plotting.isopleths.EDGES" not in names


def test_published_objects_excludes_private_and_examples(gate):
    """The gallery is not API, and neither is anything underscored."""
    names = {entry.name for entry in gate.published_objects()}
    assert not any(".examples" in name for name in names)
    assert not any(part.startswith("_") for name in names for part in name.split("."))


def test_target_version_is_the_base_of_the_scm_version(gate, monkeypatch):
    """The next tag's version, with the development suffix removed."""
    monkeypatch.setattr(gate, "_scm_version", lambda: "0.2.0.dev3")
    assert gate.target_version() == "0.2.0"


@pytest.mark.parametrize(
    ("reported", "expected"),
    [
        ("0.1.0.dev149+dirty", "0.1.0"),  # no tags yet, working tree dirty
        ("0.2.0.dev3", "0.2.0"),  # mid-cycle, after v0.1.0
        ("0.2.0", "0.2.0"),  # exactly on a tag
        ("0.3.0.dev1+g36dd91c", "0.3.0"),  # a node-id local segment
    ],
)
def test_target_version_strips_dev_and_local_segments(
    gate, monkeypatch, reported, expected
):
    monkeypatch.setattr(gate, "_scm_version", lambda: reported)
    assert gate.target_version() == expected


def test_target_version_refuses_a_shallow_checkout(gate, monkeypatch):
    """A shallow clone derives the wrong target, so refuse rather than guess.

    Without tags ``setuptools_scm`` falls back to the first release, so once
    ``v0.1.0`` exists a shallow checkout derives ``0.1.0`` where the answer is
    ``0.2.0`` -- and comparing against a wrong-low target turns correctly
    stamped symbols into failures (:issue:`227`).
    """
    monkeypatch.setattr(gate, "_is_shallow", lambda: True)
    assert gate.target_version() is None


def test_target_version_uses_the_project_version_scheme(gate):
    """The schemes come from ``pyproject.toml``, not from a copy of them.

    ``get_version`` with no configuration reports ``0.1``, not ``0.1.0``,
    because it does not read ``[tool.setuptools_scm]``. Restating
    ``release-branch-semver`` in the gate would work until someone changed it
    in one place, so the gate reads the file the build reads.
    """
    assert gate.target_version() == "0.1.0"


GOOD = """Summary line.

Notes
-----
.. versionadded:: 0.1.0
"""

NO_DIRECTIVE = "Summary line.\n"

WRONG_VERSION = """Summary line.

Notes
-----
.. versionadded:: 0.9.9
"""

ONE_COLON = """Summary line.

Notes
-----
.. versionadded: 0.1.0
"""


def _entry(gate, doc):
    """Build a PublicObject whose docstring is `doc`."""
    return gate.PublicObject(
        "tephpy.thing", "function", type("Stub", (), {"__doc__": doc})
    )


def test_cited_version_reads_the_directive(gate):
    assert gate.cited_version(GOOD) == "0.1.0"


def test_cited_version_is_none_without_a_directive(gate):
    assert gate.cited_version(NO_DIRECTIVE) is None


def test_cited_version_rejects_a_single_colon(gate):
    """A one-colon directive renders as nothing, so it does not count.

    numpydoc's ``GL10`` catches this for ``versionadded``, but the gate must
    not depend on another tool having run first -- and ``GL10`` never fires
    for Sphinx 9's ``version-added``, which is not in numpydoc's directive
    list at all (:issue:`227`).
    """
    assert gate.cited_version(ONE_COLON) is None


def test_check_reports_a_missing_directive(gate):
    problems = gate.check_versionadded([_entry(gate, NO_DIRECTIVE)], "0.1.0")
    assert len(problems) == 1
    assert "tephpy.thing" in problems[0]
    assert "no versionadded" in problems[0]


def test_check_reports_a_version_that_is_not_the_target(gate):
    problems = gate.check_versionadded([_entry(gate, WRONG_VERSION)], "0.1.0")
    assert len(problems) == 1
    assert "0.9.9" in problems[0]
    assert "0.1.0" in problems[0]


def test_check_accepts_the_target(gate):
    assert gate.check_versionadded([_entry(gate, GOOD)], "0.1.0") == []


def test_check_without_a_target_still_requires_presence(gate):
    """A shallow checkout drops the value comparison, not the rule.

    The presence half needs no version at all, so it keeps running where the
    derivation cannot be trusted.
    """
    assert gate.check_versionadded([_entry(gate, WRONG_VERSION)], None) == []
    assert len(gate.check_versionadded([_entry(gate, NO_DIRECTIVE)], None)) == 1


def test_main_reports_the_whole_surface(gate, capsys):
    """The gate runs over the real package and says how many it checked."""
    code = gate.main()
    out = capsys.readouterr().out
    assert code in (0, 1)
    assert "94" in out


def test_every_published_docstring_is_stamped(gate):
    """The rule, enforced over the real package.

    This is where the gate runs, rather than in pre-commit. The repository's
    other local hooks are pure-stdlib text scanners, so they work in the
    isolated environment pre-commit builds; this one imports ``tephpy``, and
    listing its runtime dependencies as ``additional_dependencies`` would
    duplicate ``requirements/pypi-core.txt`` and drift from it. The test suite
    already runs where the package is installed, and CI runs it on every pull
    request, so the rule is enforced without a second declaration of what
    tephpy needs to import.
    """
    problems = gate.check_versionadded(gate.published_objects(), gate.target_version())
    assert problems == []


def test_the_gate_reports_rather_than_raises(gate, capsys):
    """A contributor can run the script directly and read what to fix."""
    assert gate.main() == 0
    assert "versionadded ok" in capsys.readouterr().out


def test_the_policy_is_written_down():
    """docs-style is the living home for the rule the gate enforces.

    The gate says what is wrong; the style guide says what to write. Two
    developer plans already claim numpydoc validates `Raises`, which it does
    not (:issue:`225`), so the correction belongs somewhere maintained
    alongside the code rather than in a frozen plan.
    """
    style = (REPO / "docs" / "src" / "developer" / "docs-style.rst").read_text(
        encoding="utf-8"
    )
    assert "versionadded" in style
    assert "check_api_docstrings" in style
