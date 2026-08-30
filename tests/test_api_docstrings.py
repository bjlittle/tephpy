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

import ast
from pathlib import Path
import textwrap

import pytest

import tephpy

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
    assert "api docstrings ok" in capsys.readouterr().out


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


MISPLACED = """Summary line.

.. versionadded:: 0.1.0

Parameters
----------
x : int
    A thing.
"""

WRONG_SECTION = """Summary line.

Parameters
----------
x : int
    A thing.

See Also
--------
.. versionadded:: 0.1.0
"""

NOTES_WITHOUT_DIRECTIVE = """Summary line.

Notes
-----
Something else entirely.
"""


def test_a_directive_outside_notes_does_not_count(gate):
    """Sphinx renders it anywhere; the house form is a ``Notes`` section.

    The policy, the failure message and the thirteen files already using the
    form all say ``Notes``. A gate that accepted the directive in the
    extended summary would leave that agreement to chance.
    """
    assert gate.cited_version(MISPLACED) is None
    problems = gate.check_versionadded([_entry(gate, MISPLACED)], "0.1.0")
    assert len(problems) == 1
    assert "no versionadded" in problems[0]


def test_a_directive_in_another_section_does_not_count(gate):
    assert gate.cited_version(WRONG_SECTION) is None


def test_a_notes_section_without_the_directive_does_not_count(gate):
    assert gate.cited_version(NOTES_WITHOUT_DIRECTIVE) is None


def test_notes_section_body_stops_at_the_next_section(gate):
    """A section ends at the *title* of the next, not at its rule."""
    doc = """Summary.

Notes
-----
The note.

References
----------
Not the note.
"""
    body = gate.notes_section(doc)
    assert "The note." in body
    assert "References" not in body
    assert "Not the note." not in body


def test_notes_section_is_empty_when_absent(gate):
    assert gate.notes_section("Summary only.\n") == ""
    assert gate.notes_section("") == ""


def test_notes_section_runs_to_the_end_when_last(gate):
    """The house form puts ``Notes`` last, which is the common case."""
    assert ".. versionadded:: 0.1.0" in gate.notes_section(GOOD)


# --- the Raises rule (:issue:`224`) ---------------------------------------


def test_raises_section_is_read_like_notes(gate):
    doc = """Summary.

Raises
------
TypeError
    If a thing.
ValueError
    If another.

Notes
-----
.. versionadded:: 0.1.0
"""
    assert gate.documented_raises(doc) == {"TypeError", "ValueError"}


def test_documented_raises_is_empty_without_the_section(gate):
    assert gate.documented_raises("Summary only.\n") == set()


def test_documented_raises_ignores_the_descriptions(gate):
    """Only the type lines count; an indented description is not a type."""
    doc = "Summary.\n\nRaises\n------\nTypeError\n    ValueError is not raised here.\n"
    assert gate.documented_raises(doc) == {"TypeError"}


def _fn(source):
    """Parse `source` into the ast.FunctionDef the rule reads."""
    return ast.parse(textwrap.dedent(source)).body[0]


def test_raised_directly_finds_an_uncaught_raise(gate):
    fn = _fn(
        '''
        def f():
            """Doc."""
            raise TypeError("no")
    ''',
    )
    assert gate.raised_directly(fn) == {"TypeError"}


def test_raised_directly_ignores_a_caught_raise(gate):
    """A raise the same function catches never reaches a caller."""
    fn = _fn(
        '''
        def f():
            """Doc."""
            try:
                raise ValueError("inner")
            except ValueError:
                return None
    ''',
    )
    assert gate.raised_directly(fn) == set()


def test_raised_directly_honours_the_exception_hierarchy(gate):
    """``except TephpyError`` catches a ``TephpyUnitsError`` raised under it."""
    fn = _fn(
        '''
        def f():
            """Doc."""
            try:
                raise TephpyUnitsError("inner")
            except TephpyError:
                return None
    ''',
    )
    assert gate.raised_directly(fn) == set()


def test_raised_directly_ignores_a_bare_re_raise(gate):
    """A bare ``raise`` re-raises whatever the handler caught."""
    fn = _fn(
        '''
        def f():
            """Doc."""
            try:
                g()
            except ValueError:
                raise
    ''',
    )
    assert gate.raised_directly(fn) == set()


def test_raised_directly_ignores_a_nested_function(gate):
    """A closure's raises are its own, and fire when it is called."""
    fn = _fn(
        '''
        def f():
            """Doc."""
            def inner():
                raise TypeError("not f's")
            return inner
    ''',
    )
    assert gate.raised_directly(fn) == set()


def test_raised_directly_sees_through_raise_from(gate):
    fn = _fn(
        '''
        def f():
            """Doc."""
            try:
                g()
            except OSError as err:
                raise TephpyIOError("wrapped") from err
    ''',
    )
    assert gate.raised_directly(fn) == {"TephpyIOError"}


def test_every_published_raise_is_documented(gate):
    """The rule, over the real package.

    Green because :pull:`223` swept the public API by hand. This is what
    stops it drifting back.
    """
    assert gate.check_raises(gate.published_objects()) == []


def test_a_class_is_read_through_its_constructor_hook(gate):
    """Where a dataclass validates is not where a reader is told.

    ``Sounding``, ``Profile`` and ``SoundingIndices`` all validate in
    ``__post_init__``, which the API reference never renders, and document it
    on the class. A rule that read only the class body would have missed the
    largest defect :pull:`223` found by hand: three public classes that
    validated their arguments and documented none of it.
    """

    class Undocumented:
        """A class whose constructor raises, saying nothing about it."""

        def __post_init__(self) -> None:
            """Validate."""
            msg = "undocumented"
            raise TypeError(msg)

    entry = gate.PublicObject("tephpy.Thing", "class", Undocumented)
    problems = gate.check_raises([entry])
    assert len(problems) == 1
    assert "raises TypeError" in problems[0]


def test_a_documented_constructor_hook_passes(gate):
    class Documented:
        """A class that says what its constructor raises.

        Raises
        ------
        TypeError
            If the thing is wrong.
        """

        def __post_init__(self) -> None:
            """Validate."""
            msg = "documented"
            raise TypeError(msg)

    entry = gate.PublicObject("tephpy.Thing", "class", Documented)
    assert gate.check_raises([entry]) == []


def test_a_module_has_no_raises_of_its_own(gate):
    """Module-level code runs at import; the rule has nothing to read."""
    entry = gate.PublicObject("tephpy", "module", tephpy)
    assert gate.check_raises([entry]) == []


def test_raised_directly_follows_a_bare_re_raise_out(gate):
    """A raise its own handler catches and re-raises still reaches a caller.

    Reported by review on :pull:`230`: the named raise reads as caught and
    the bare ``raise`` was discarded, so the exception escaped the gate as
    well as the function.
    """
    fn = _fn('''
        def f():
            """Doc."""
            try:
                raise ValueError("escapes")
            except ValueError:
                cleanup()
                raise
    ''')
    assert gate.raised_directly(fn) == {"ValueError"}


def test_a_bare_re_raise_does_not_invent_a_raise(gate):
    """Rolling back and re-raising is propagation, not a direct raise.

    ``IsoplethFamily.configure`` is exactly this: the body only *calls*, and
    what leaves under ``except Exception`` belongs to the call. Crediting the
    bare ``raise`` with everything its handler catches would report
    ``Exception`` on a function that raises nothing itself.
    """
    fn = _fn('''
        def f():
            """Doc."""
            try:
                helper()
            except Exception:
                rollback()
                raise
    ''')
    assert gate.raised_directly(fn) == set()


def test_a_re_raise_can_still_be_caught_further_out(gate):
    """An outer handler that does not re-raise still swallows it."""
    fn = _fn('''
        def f():
            """Doc."""
            try:
                try:
                    raise ValueError("inner")
                except ValueError:
                    raise
            except ValueError:
                return None
    ''')
    assert gate.raised_directly(fn) == set()


def test_a_handler_raising_a_different_exception_swallows_the_first(gate):
    """``raise Y from err`` replaces X; only Y escapes."""
    fn = _fn('''
        def f():
            """Doc."""
            try:
                raise ValueError("inner")
            except ValueError as err:
                raise TephpyIOError("outer") from err
    ''')
    assert gate.raised_directly(fn) == {"TephpyIOError"}


ORDERED = """Summary.

Raises
------
TypeError
    If a thing.
ValueError
    If another.
"""

UNORDERED = """Summary.

Raises
------
ValueError
    If another.
TypeError
    If a thing.
"""


def test_raises_entries_are_read_in_document_order(gate):
    assert gate.raises_order(UNORDERED) == ["ValueError", "TypeError"]


def test_ordered_entries_pass(gate):
    assert gate.check_raises_order([_entry(gate, ORDERED)]) == []


def test_unordered_entries_are_reported(gate):
    """Thirteen docstrings restate the configuration-driven raise set.

    Nothing kept the copies in step, and they drifted -- one of them listed
    ``ValueError`` before ``TypeError`` while the other twelve did not
    (:issue:`226`). Alphabetical is what the corpus already followed.
    """
    problems = gate.check_raises_order([_entry(gate, UNORDERED)])
    assert len(problems) == 1
    assert "alphabetical" in problems[0]
    assert "ValueError" in problems[0]


def test_a_single_entry_is_trivially_ordered(gate):
    doc = "Summary.\n\nRaises\n------\nTypeError\n    If a thing.\n"
    assert gate.check_raises_order([_entry(gate, doc)]) == []


def test_every_published_raises_section_is_ordered(gate):
    assert gate.check_raises_order(gate.published_objects()) == []
