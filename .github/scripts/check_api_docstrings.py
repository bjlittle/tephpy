#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check the published API docstrings carry what policy requires (:issue:`227`).

numpydoc validates a great deal and this not at all: its ``ERROR_MSGS`` table
runs ``GL0x``, ``SS0x``, ``PR0x``, ``RT01``-``RT05``, ``YD01``, ``SA0x`` and
``EX01``, with no rule for ``Raises`` and none for ``versionadded``. A
docstring may therefore omit either and ``pixi run lint`` stays green, which
is how the public API came to carry no ``versionadded`` at all while thirteen
files under ``.github/scripts`` and ``docs/src/_ext`` already used the form.

The set this walks is the set sphinx-autoapi publishes: every module under
``src/tephpy`` with no underscore-prefixed path component, minus ``examples``,
together with the objects those modules define. ``tephpy.config`` is the case
that shapes the design -- a ``Config`` instance exported from the private
``tephpy._config``, which has no page of its own, yet whose methods are
published as ``tephpy.config.load`` and its neighbours because the singleton
is reachable from ``tephpy``. An enumerator built from the module list alone
would miss every one of them, so the walk reaches through the instance too.

Attributes and module data are deliberately outside the set. A dataclass
field is documented in its class's ``Attributes`` section and a ``#:`` comment
is not a docstring, so neither has anywhere to carry a directive; of the 207
``tephpy`` entries a build publishes, 104 are attributes and one is data.

``tests/test_docs_api_inventory.py`` is what earns the static shortcut: it
pins this enumeration against the ``objects.inv`` a real build wrote, so the
fast set is provably the set a reader meets.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import inspect
from pathlib import Path
import pkgutil
import re
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    import types

REPO = Path(__file__).parents[2]
PACKAGE = REPO / "src"

#: Roles that own a docstring of their own, and so can carry a directive.
STAMPED_ROLES = ("module", "class", "exception", "function", "method", "property")


@dataclasses.dataclass(frozen=True)
class PublicObject:
    """One published API object.

    Parameters
    ----------
    name : str
        The dotted name the API reference publishes it under.
    role : str
        One of :data:`STAMPED_ROLES`.
    obj : object
        The live object, read for its docstring.

    Attributes
    ----------
    name : str
        The dotted name the API reference publishes it under.
    role : str
        One of :data:`STAMPED_ROLES`.
    obj : object
        The live object, read for its docstring.
    """

    name: str
    role: str
    obj: object


def _import_package() -> types.ModuleType:
    """Import ``tephpy`` from the working tree.

    Returns
    -------
    types.ModuleType
        The imported package.
    """
    if str(PACKAGE) not in sys.path:
        sys.path.insert(0, str(PACKAGE))
    return importlib.import_module("tephpy")


def _is_shallow() -> bool:
    """Report whether this checkout is shallow.

    Returns
    -------
    bool
        ``True`` when git reports a shallow repository.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO,
    )
    return result.stdout.strip() == "true"


def _scm_version() -> str:
    """Return the version ``setuptools_scm`` derives for this checkout.

    The schemes are read from ``pyproject.toml`` rather than restated here.
    ``get_version`` with no configuration reports ``0.1``, not ``0.1.0``,
    because it never sees ``version_scheme = "release-branch-semver"`` -- and
    a gate comparing against ``0.1`` would fail every correctly stamped
    docstring in the package.

    Returns
    -------
    str
        A PEP 440 version, e.g. ``"0.1.0.dev149"``.
    """
    import warnings  # noqa: PLC0415

    from setuptools_scm import Configuration, get_version  # noqa: PLC0415

    config = Configuration.from_file(str(REPO / "pyproject.toml"))
    with warnings.catch_warnings():
        # `release-branch-semver` is deprecated upstream in favour of
        # `semver-pep440-release-branch` -- the same scheme under a new name,
        # verified to derive the same version. Renaming it is a deliberate
        # change to release-critical configuration and not this gate's to
        # make, and the gate cannot act on the warning either way, so it reads
        # the number and moves on.
        warnings.simplefilter("ignore", DeprecationWarning)
        return str(
            get_version(
                root=str(REPO),
                version_scheme=config.version_scheme,
                local_scheme=config.local_scheme,
            )
        )


def target_version() -> str | None:
    """Return the base version the next tag will carry.

    Returns
    -------
    str or None
        The base version, e.g. ``"0.1.0"``; ``None`` when the checkout is
        shallow, where the derivation cannot be trusted.
    """
    if _is_shallow():
        return None
    from packaging.version import Version  # noqa: PLC0415

    return Version(_scm_version()).base_version


def public_modules() -> list[str]:
    """Return the dotted names of the modules autoapi publishes.

    Returns
    -------
    list of str
        Sorted module names, private modules and the gallery excluded.
    """
    package = _import_package()
    names = ["tephpy"]
    for info in pkgutil.walk_packages(package.__path__, prefix="tephpy."):
        parts = info.name.split(".")
        if any(part.startswith("_") for part in parts) or "examples" in parts:
            continue
        names.append(info.name)
    return sorted(names)


def _members(owner: object, prefix: str, seen: set[str]) -> list[PublicObject]:
    """Collect the published members an owner defines.

    ``vars`` rather than ``dir`` throughout, because it answers the question
    autoapi asks: what does this thing *define*? For a module that excludes
    the names it imports -- ``tephpy.calc`` imports four exception classes and
    two unit helpers, and autoapi documents none of them under ``calc``, since
    they belong to the modules that define them. For a class it excludes
    inherited members, which is right because ``autoapi_options`` carries no
    ``inherited-members``: ``TephigramAxes`` documents what it overrides and
    adds, not the whole of ``matplotlib.axes.Axes``.

    A module needs the stricter test of the two. ``vars`` still holds every
    imported name, so membership is settled by ``__module__`` -- the module
    that defines an object is the one that publishes it.

    Parameters
    ----------
    owner : object
        The module, class, or singleton type to walk.
    prefix : str
        The dotted name `owner` is published under.
    seen : set of str
        Dotted names already emitted; mutated in place.

    Returns
    -------
    list of PublicObject
        The members, in name order.
    """
    is_module = inspect.ismodule(owner)
    found: list[PublicObject] = []
    for name in sorted(vars(owner)):
        if name.startswith("_"):
            continue
        try:
            child = getattr(owner, name)
        except AttributeError:  # pragma: no cover -- defensive
            continue
        target = child.fget if isinstance(child, property) else child
        defined_in = getattr(target, "__module__", None) or ""
        if is_module:
            if defined_in != owner.__name__:
                continue
        elif not defined_in.startswith("tephpy"):
            continue
        dotted = f"{prefix}.{name}"
        if dotted in seen:
            continue
        if inspect.isclass(child):
            role = "exception" if issubclass(child, BaseException) else "class"
            seen.add(dotted)
            found.append(PublicObject(dotted, role, child))
            found.extend(_members(child, dotted, seen))
        elif isinstance(child, property):
            seen.add(dotted)
            found.append(PublicObject(dotted, "property", target))
        elif inspect.isroutine(child):
            seen.add(dotted)
            found.append(
                PublicObject(dotted, "function" if is_module else "method", child)
            )
    return found


def published_objects() -> list[PublicObject]:
    """Enumerate every published API object that owns a docstring.

    Returns
    -------
    list of PublicObject
        Sorted by dotted name.
    """
    package = _import_package()
    seen: set[str] = set()
    found: list[PublicObject] = []
    for name in public_modules():
        module = importlib.import_module(name)
        found.append(PublicObject(name, "module", module))
        found.extend(_members(module, name, seen))
    found.extend(_singleton_methods(type(package.config), "tephpy.config", seen))
    return sorted(found, key=lambda entry: entry.name)


def _singleton_methods(owner: type, prefix: str, seen: set[str]) -> list[PublicObject]:
    """Collect the methods a reachable singleton publishes.

    ``tephpy.config`` is a ``Config`` instance exported from the private
    ``tephpy._config``. The module has no page, but the instance is reachable
    from ``tephpy``, so autoapi documents what you can *call* on it --
    ``context``, ``load``, ``reset`` and ``save`` -- and nothing else. Its
    properties are not published, and its dataclass sections arrive as
    ``py:attribute`` entries like ``tephpy.config.isotherms.alpha``, which own
    no docstring. Methods only, therefore, matching what a build emits rather
    than what the class happens to hold.

    Parameters
    ----------
    owner : type
        The singleton's class.
    prefix : str
        The dotted name the singleton is published under.
    seen : set of str
        Dotted names already emitted; mutated in place.

    Returns
    -------
    list of PublicObject
        The published methods, in name order.
    """
    found: list[PublicObject] = []
    for name in sorted(vars(owner)):
        if name.startswith("_"):
            continue
        child = getattr(owner, name)
        if not inspect.isroutine(child):
            continue
        dotted = f"{prefix}.{name}"
        if dotted in seen:
            continue
        seen.add(dotted)
        found.append(PublicObject(dotted, "method", child))
    return found


#: The house directive. Sphinx 9 added ``version-added`` and keeps this as a
#: registered alias, but the documentation floor is ``sphinx>=8.0``, where the
#: hyphenated spelling does not exist -- and numpydoc's ``GL10`` two-colon
#: check does not fire for it either, because it is not in numpydoc's
#: ``DIRECTIVES`` list (:issue:`227`). Two colons are required here: a
#: one-colon directive renders as nothing at all.
DIRECTIVE = re.compile(r"^\s*\.\.[ \t]+versionadded::[ \t]*(\S+)[ \t]*$", re.MULTILINE)


def notes_section(doc: str) -> str:
    """Return the body of a docstring's ``Notes`` section.

    Parameters
    ----------
    doc : str
        The docstring, already dedented by :func:`inspect.getdoc`.

    Returns
    -------
    str
        The section body, empty when there is no ``Notes`` section.
    """
    return section(doc, "Notes")


def section(doc: str, title: str) -> str:
    """Return the body of one numpydoc section.

    Hand-rolled rather than handed to ``numpydoc.docscrape``, because the
    ``test`` environment carries no numpydoc and this gate is enforced from
    the test suite. A section is a title line over a rule of dashes, and its
    body runs to the next such title or to the end.

    Parameters
    ----------
    doc : str
        The docstring, already dedented by :func:`inspect.getdoc`.
    title : str
        The section title, e.g. ``"Notes"`` or ``"Raises"``.

    Returns
    -------
    str
        The section body, empty when the docstring has no such section.
    """
    lines = (doc or "").splitlines()
    underlined = [
        index
        for index in range(len(lines) - 1)
        if lines[index].strip()
        and set(lines[index + 1].strip()) == {"-"}
        and len(lines[index + 1].strip()) >= len(lines[index].strip())
    ]
    for position, index in enumerate(underlined):
        if lines[index].strip() != title:
            continue
        following = underlined[position + 1 :]
        # A section ends at the *title* of the next one, which sits on the
        # line above its rule.
        end = following[0] - 1 if following else len(lines)
        return "\n".join(lines[index + 2 : end])
    return ""


def cited_version(doc: str) -> str | None:
    """Return the version a docstring's ``versionadded`` cites.

    The directive is only accepted inside the ``Notes`` section. Sphinx would
    render it anywhere, so this is the gate enforcing the house form rather
    than a limitation: the policy, the failure message and the thirteen files
    already using it all say ``Notes``, and a gate that accepted the directive
    in the summary would leave that agreement to chance.

    Parameters
    ----------
    doc : str
        The docstring, already dedented.

    Returns
    -------
    str or None
        The cited version, or ``None`` when the directive is absent from the
        ``Notes`` section, malformed, or placed outside it.
    """
    match = DIRECTIVE.search(notes_section(doc))
    return match.group(1) if match else None


def check_versionadded(
    entries: Iterable[PublicObject], target: str | None
) -> list[str]:
    """Check each entry carries the directive, citing `target`.

    While no tag exists nothing can predate the first release, so the rule is
    equality rather than a bound: every published object cites exactly the
    version the next tag will carry. Once a release exists that stops being
    right -- objects from earlier releases legitimately cite older versions --
    and :issue:`227` records the snapshot rules that take over.

    Parameters
    ----------
    entries : iterable of PublicObject
        The published objects to check.
    target : str or None
        The base version the next tag will carry, or ``None`` to check
        presence only (see :func:`target_version`).

    Returns
    -------
    list of str
        One line per violation, empty when the corpus is clean.
    """
    problems = []
    for entry in entries:
        cited = cited_version(inspect.getdoc(entry.obj) or "")
        if cited is None:
            problems.append(
                f"{entry.name} ({entry.role}): no versionadded directive in a "
                f"Notes section"
            )
        elif target is not None and cited != target:
            problems.append(
                f"{entry.name} ({entry.role}): versionadded cites {cited}, "
                f"expected {target}"
            )
    return problems


def main() -> int:
    """Run the gate over the published API.

    Returns
    -------
    int
        ``0`` when clean, ``1`` when any rule reports a violation.
    """
    entries = published_objects()
    target = target_version()
    # Two rules, reported separately: the versionadded rule is total and
    # exact, the raises rule is narrow by design (:issue:`224`). Folding them
    # into one verdict would let the narrower one argue for switching off the
    # other.
    stamps = check_versionadded(entries, target)
    raises = check_raises(entries)
    if stamps:
        print(
            f"{len(stamps)} of {len(entries)} published API objects fail the "
            f"versionadded rule (docs-style, :issue:`227`):\n"
        )
        for line in stamps:
            print(f"  {line}")
        print(
            "\nAdd a Notes section as the docstring's last section:\n\n"
            f"    Notes\n    -----\n    .. versionadded:: {target or '<version>'}\n"
        )
    if raises:
        print(
            f"\n{len(raises)} published API object(s) raise an exception their "
            f"Raises section does not document (docs-style, :issue:`224`):\n"
        )
        for line in raises:
            print(f"  {line}")
        print(
            "\nDocument it, or -- if the raise cannot reach a caller -- say so "
            "where it is raised.\n"
        )
    if stamps or raises:
        return 1
    print(
        f"api docstrings ok: {len(entries)} published objects carry a "
        f"versionadded and document what they raise"
    )
    return 0


def documented_raises(doc: str) -> set[str]:
    """Return the exception names a docstring's ``Raises`` section lists.

    Parameters
    ----------
    doc : str
        The docstring, already dedented.

    Returns
    -------
    set of str
        The listed type names, unqualified. Descriptions are indented under
        their type, so only unindented lines count.
    """
    names = set()
    for line in section(doc, "Raises").splitlines():
        if not line or line[:1].isspace() or not line.strip():
            continue
        for part in line.split(" or "):
            bare = part.strip().strip("`").split("(")[0].strip()
            if bare:
                names.add(bare.split(".")[-1])
    return names


def _exception_bases() -> dict[str, str]:
    """Map each known exception name to its immediate base.

    Returns
    -------
    dict of str to str
        Builtin exceptions plus tephpy's own hierarchy.
    """
    import builtins  # noqa: PLC0415

    bases = {}
    for name in dir(builtins):
        obj = getattr(builtins, name)
        if isinstance(obj, type) and issubclass(obj, BaseException):
            bases[name] = "" if obj is BaseException else obj.__mro__[1].__name__
    exceptions = importlib.import_module("tephpy.exceptions")
    for name in dir(exceptions):
        obj = getattr(exceptions, name)
        if isinstance(obj, type) and issubclass(obj, BaseException):
            bases[name] = obj.__mro__[1].__name__
    return bases


def _caught_by(name: str, handlers: Iterable[str]) -> bool:
    """Report whether a handler in `handlers` would catch `name`.

    Parameters
    ----------
    name : str
        The raised exception's unqualified name.
    handlers : iterable of str
        The unqualified names an enclosing ``except`` clause catches.

    Returns
    -------
    bool
        ``True`` when the raise never reaches a caller.
    """
    bases = _exception_bases()
    chain, current, seen = set(), name, set()
    while current and current not in seen:
        seen.add(current)
        chain.add(current)
        current = bases.get(current, "")
    return any(handler in chain for handler in handlers)


def _handlers_around(fn: ast.AST, node: ast.AST) -> list[str]:
    """Return what an enclosing ``try`` in `fn` catches at `node`.

    Parameters
    ----------
    fn : ast.AST
        The function being read.
    node : ast.AST
        The ``raise`` statement.

    Returns
    -------
    list of str
        Unqualified exception names, ``"BaseException"`` for a bare ``except``.
    """
    line = getattr(node, "lineno", -1)
    caught = []
    for block in ast.walk(fn):
        if not isinstance(block, ast.Try):
            continue
        if not any(
            stmt.lineno <= line <= (stmt.end_lineno or stmt.lineno)
            for stmt in block.body
        ):
            continue
        for handler in block.handlers:
            if handler.type is None:
                caught.append("BaseException")
            elif isinstance(handler.type, ast.Tuple):
                caught += [
                    ast.unparse(entry).split(".")[-1] for entry in handler.type.elts
                ]
            else:
                caught.append(ast.unparse(handler.type).split(".")[-1])
    return caught


def raised_directly(fn: ast.AST) -> set[str]:
    """Return the exceptions a function raises in its own body.

    Direct raises only, with no propagation through the calls it makes. That
    narrowness is deliberate (:issue:`224`): a propagating analysis cannot
    follow dynamic dispatch, cannot see an exception a third party raises --
    ``datetime.fromisoformat``'s ``ValueError`` is documented and invisible to
    it -- and reports internal guards that no caller can reach. Every one of
    those is a false positive, and a gate that cries wolf is switched off.

    A bare ``raise`` is excluded: it re-raises whatever the handler caught,
    which the ``except`` clause already names. So is anything inside a nested
    function, whose raises fire when *it* is called.

    Parameters
    ----------
    fn : ast.AST
        The parsed function definition.

    Returns
    -------
    set of str
        Unqualified exception names that can leave the body.
    """
    nested = [
        (node.lineno, node.end_lineno or node.lineno)
        for node in ast.walk(fn)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
        and node is not fn
    ]
    found = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        line = getattr(node, "lineno", None)
        if line is not None and any(lo <= line <= hi for lo, hi in nested):
            continue
        raised = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        name = ast.unparse(raised).split(".")[-1]
        if not _caught_by(name, _handlers_around(fn, node)):
            found.add(name)
    return found


def _definition(obj: object) -> ast.AST | None:
    """Parse the source of a callable into its definition node.

    Parameters
    ----------
    obj : object
        The callable to read.

    Returns
    -------
    ast.AST or None
        The parsed definition, or ``None`` when the source is unavailable.
    """
    import textwrap  # noqa: PLC0415

    try:
        source = textwrap.dedent(inspect.getsource(inspect.unwrap(obj)))
    except (OSError, TypeError):  # pragma: no cover -- builtins, C extensions
        return None
    return ast.parse(source).body[0]


def check_raises(entries: Iterable[PublicObject]) -> list[str]:
    """Check each entry documents the exceptions it raises itself.

    A class is read through its constructor hook rather than its own body,
    because that is where a dataclass validates and where the caller meets
    the failure: ``Sounding``, ``Profile`` and ``SoundingIndices`` all
    validate in ``__post_init__`` and document it on the class, which is the
    only docstring a reader of the API reference is shown.

    Parameters
    ----------
    entries : iterable of PublicObject
        The published objects to check.

    Returns
    -------
    list of str
        One line per violation, empty when the corpus is clean.
    """
    problems = []
    for entry in entries:
        if entry.role in ("function", "method", "property"):
            sources = [entry.obj]
        elif entry.role in ("class", "exception"):
            sources = [
                hook
                for name in ("__post_init__", "__init__")
                if (hook := vars(entry.obj).get(name)) is not None
            ]
        else:
            continue
        documented = documented_raises(inspect.getdoc(entry.obj) or "")
        for source in sources:
            node = _definition(source)
            if node is None:
                continue
            problems.extend(
                f"{entry.name} ({entry.role}): raises {name}, "
                f"which its Raises section does not document"
                for name in sorted(raised_directly(node) - documented)
            )
    return problems


if __name__ == "__main__":
    sys.exit(main())
