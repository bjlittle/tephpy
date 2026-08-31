# Configuration Value Validation Implementation Plan

> **Point-in-time record.** This plan captures what was intended before implementation. It
> is not updated afterwards — where the implementation departed from it, the departure is
> recorded in the pull request, and the living design specification in
> [`../specs/`](../specs/) is what describes tephpy as it stands.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Check every configuration file value against the type its `Config` field
declares, and on a mismatch warn, skip that option and keep applying the file — instead of
applying the value unchecked (today's silent wrongness) or rejecting the whole file
(today's escalation).

**Architecture:** Eight small converters, one per distinct annotation in `Config`, each of
which both checks a value and performs the §3.3 conversion. `_TYPE_VALIDATORS` maps the
evaluated annotation to its `(description, converter)` pair, so the expected types are read
from the declarations in `_config.py` rather than written out a second time.
`coerce` gains a fourth parameter — the annotation — and raises `TephpyConfigError` on a
mismatch; `apply` resolves the annotations for the section it already holds, catches that
error, warns and moves to the next option. That single `except` is what delivers the rule
and what ends the escalation.

**Tech Stack:** Python 3.12 stdlib (`typing.get_type_hints`, `types.MappingProxyType`);
pytest; `subprocess` for the import-time seam; `click.testing.CliRunner`; pixi; pre-commit.

**Spec:** `configfile spec §5.2`, in
[`../specs/2026-08-07-config-file-design.md`](../specs/2026-08-07-config-file-design.md).
Section 5 is the surrounding error-handling contract, §5.1 the warning provenance this
builds on, and §3.3 the coercions the converters absorb.

**Issue:** {issue}`105`, deferred from {pull}`112`.

## Global Constraints

- **Every pixi invocation carries `--frozen`.** `pixi run --frozen tests`,
  `pixi run --frozen lint`, `pixi run --frozen docs`. Never let pixi re-solve the
  environment.
- **Line length is 88 columns**, ruff-enforced and ruff-formatted. Every code block in this
  plan has been run through `ruff format` with the project configuration and is reproduced
  as it came out; paste it verbatim rather than re-wrapping it by hand.
- **Docstrings are numpydoc**, validated by the `numpydoc-validation` pre-commit hook over
  `^src/` with **no exclusions for private members** — so all nine new functions in
  `_configfile.py` need `Parameters` and `Returns` sections and an infinitive-verb summary
  ("Check a value is…", not "Checks…"). Test-file helpers follow the surrounding test style
  instead.
- **`pyproject.toml:67` sets `filterwarnings = ["error"]`.** Any test that triggers a
  configuration warning in-process must catch it with `pytest.warns`, or the suite fails.
- **No new files under `src/`**, so no new BSD copyright headers are needed. Every file
  this plan touches already carries one.
- **The type check must never be able to stop an import.** An annotation with no validator
  returns its value untouched; a test gate is what reports the gap. A `KeyError` or an
  unhandled exception from this code path would take out `import tephpy` itself.
- **Stage before mutating.** Every mutation check in this plan runs `git add` first, then
  edits, then restores with `git checkout -- <path>` — which reverts from the index. An
  unstaged mutate-and-revert cycle discards the real work along with the mutation.
- **The specifications are living documents; the plans are frozen** (docs spec §3.4).
  `configfile spec §5.2` is already written and committed (`4b53f3c`); Task 3 makes one
  correction to it and no other specification text is added. Nothing under
  `docs/src/developer/plans/` is edited by this work, including this file once its pull
  request merges.
- **Never write a bare `#N` or a `github.com/bjlittle/tephpy` issue URL in prose.** Use the
  `{issue}` and `{pull}` roles. The `check-github-references` gate enforces this over its
  corpus, which `check_citations.corpus` derives as every tracked text file **less
  `docs/src/developer/plans/`** — so it covers the changelog fragment, the how-to and the
  specification, and not this file. Commit messages are outside the corpus entirely; the
  role there is convention, not enforcement, and it is what the four merged bodies in
  `git log` use.
- **Always write the specification prefix**: `configfile spec §5.2`, never a bare
  `spec §5.2`, which resolves to a different document.

## Two departures from the specification, both measured

Record these in the pull request description. They are the only places where the
implementation below does not do what `configfile spec §5.2` says.

**1. There is no `_OPTION_TYPES` table.** §5.2 describes a module-level
`{(section, option): annotation}` mapping built once with `typing.get_type_hints`. It
cannot be built at import: `_configfile` may not import `_config` at runtime without
reversing the dependency arrow `(_cli, _config) → _configfile → _constants`
(`configfile spec §3`), and `_configfile` is imported *by* `_config`. A lazily-populated
global would work, but it would leave a direct `coerce` caller — the fixture tests —
consulting a table that is still empty, which is a gate that can pass by checking nothing.

Instead `coerce` takes the annotation as a fourth argument, and `apply` resolves it from
the section instance it already holds:

```python
hints = _option_hints(type(section))
...
setattr(section, option, coerce(name, option, value, hints[option]))
```

Every caller must therefore supply an annotation, so no caller can silently skip the check.
Task 3 Step 2 corrects the §5.2 bullet to match. Everything else in §5.2 —
`_TYPE_VALIDATORS`, the single `except` in `apply`, the completeness gate — stands as
written.

**2. `_option_hints` is not cached.** The design called for `functools.cache`. Two
measurements killed it:

- `mypy --strict` rejects it. Wrapping a function whose parameter is `type[object]` in
  `functools.cache` or `functools.lru_cache` fails with
  *Argument 1 to `__call__` of `_lru_cache_wrapper` has incompatible type `type[object]`;
  expected `Hashable`* — mypy does not accept `type[…]`'s inherited `__hash__` as
  satisfying the `Hashable` protocol. Binding the argument to a typed local first does not
  help.
- The cache buys 0.9 ms. `typing.get_type_hints` over all seven section dataclasses costs
  **909 µs**, once per `apply` call, against a **485 ms** `import tephpy`. That is 0.19% of
  the import it sits on.

So `_option_hints` is a plain function. If a caller ever loads configurations in a loop and
this shows up, the drop-in is a module-level `dict` cache, which type-checks cleanly;
`functools.cache` is not, and re-reaching for it will fail `pixi run --frozen lint`.

## File Structure

| File | Responsibility after this change |
|---|---|
| `src/tephpy/_configfile.py` | The whole behavioural change. Gains `_MismatchError`, eight converters plus the `_as_corner` helper, `_TYPE_VALIDATORS`, `_describe` and `_option_hints`; `coerce` is rewritten around them; `apply` resolves annotations, catches the mismatch and warns. Loses `_STRING_TUPLES` and `_FLOAT_TUPLES`, whose only readers were the old `coerce`. The module already "owns everything about the file", so owning what a valid value *is* belongs here. |
| `src/tephpy/_config.py` | Docstring only. `Config.load`'s `Warns` section names the wrong-typed case alongside the unknown option and the null value. |
| `tests/test_configfile.py` | Adds the accept/reject matrix over the eight annotation shapes, the validator completeness gate, the warn-and-skip realignment of `test_a_malformed_value_raises`, the one-bad-one-good file, and the path-prefix test. |
| `tests/test_configfile_fixture.py` | Two `coerce` call sites gain the annotation argument. |
| `tests/test_cli.py` | Adds the guard that a wrong-typed value leaves the file `[in force]`, not `[rejected]` — the user-visible end of the escalation. |
| `tests/test_config_autoload.py` | Adds the import-time survival case: a wrong-typed value under `PYTHONWARNINGS=error` warns, is skipped, and the rest of the file still applies. |
| `docs/src/howtos/configuration.rst` | "After an Upgrade" gains the wrong-typed value beside the renamed option (`configfile spec §8`). |
| `docs/src/developer/specs/2026-08-07-config-file-design.md` | The one-bullet `_OPTION_TYPES` correction described above. |
| `changelog/<PR>.bugfix.rst` | New fragment. |

## The vacuous-test traps

Three of them here, each of which would leave a test passing whatever the code does.

**`1 == 1.0` and `False == 0`.** The whole point of `_as_number` is that it returns a
`float` where YAML gave an `int`, and the whole point of the `bool` exclusion is that
`True` must *not* reach a numeric field. An accept matrix asserting only `coerced ==
expected` passes without any conversion happening at all. Every accept case therefore
asserts `type(coerced) is type(expected)` as well.

**`{0: …} == {0.0: …}`.** The same trap one level down, and it defeats a type assertion
too, because the dictionary object *is* a `dict` either way — it is the key that must
become a float. The existing `test_emphasis_keys_coerce_to_float`
(`tests/test_configfile.py:263`) is what guards that, by checking
`isinstance(keys[0], float)`; the matrix does not re-prove it.

**A gate that discovers nothing.** `test_every_option_has_a_validator` iterates the
sections it finds and asserts the annotations it found are all covered. An empty discovery
satisfies that trivially, so it asserts its own option set is non-empty *and* equal in size
to `CONFIG_DEFAULTS` — a count that updates itself when an option is added, unlike a
hard-coded 42.

---

### Task 1: The validators, and `coerce` around them

At the end of this task a wrong-typed value is *detected*: `coerce` raises, `apply` still
lets that raise propagate, and the file is rejected as it is today. That is deliberately
half the change — the detection is a large, separately reviewable unit, and the policy that
consumes it is Task 2. Note the intermediate state is briefly *worse* than today for the
silent cases (`linewidth: thick` now rejects the file rather than failing at draw time), so
Task 2 must follow before the branch is proposed for merge.

**Files:**
- Modify: `src/tephpy/_configfile.py` (delete `:126-131`; add to the imports at `:15`
  and `:20`; replace `coerce` at `:192-233`; one line inside `apply` at `:305-307` and one
  at `:325`)
- Test: `tests/test_configfile.py` (add after `test_a_non_mapping_document_raises` at
  `:209-212`)
- Test: `tests/test_configfile_fixture.py` (`:45`, `:55`)

**Interfaces:**
- Consumes: `Mapping`, `dataclasses`, `MappingProxyType`, `Final` and `TephpyConfigError`,
  all already imported by `_configfile.py` at `:15`, `:16`, `:19`, `:20`, `:27`.
- Produces, all module-private in `tephpy._configfile` except `coerce`:
  - `_MismatchError(Exception)` — carries no message.
  - `_as_string`, `_as_number`, `_as_flag`, `_as_string_tuple`, `_as_labels`,
    `_as_number_tuple`, `_as_corner`, `_as_extent`, `_as_emphasis`, each
    `(value: object) -> …`, each raising `_MismatchError`.
  - `_TYPE_VALIDATORS: Final[Mapping[object, tuple[str, Callable[[object], object]]]]`.
  - `_describe(value: object) -> str`.
  - `_option_hints(section_type: type[object]) -> Mapping[str, object]`.
  - `coerce(section: str, option: str, value: object, annotation: object) -> object` — the
    **fourth parameter is new and required**. Task 2 calls it with the same signature.
  Nothing new goes in `__all__`; `coerce` is already there and stays.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_configfile.py`, immediately after `test_a_non_mapping_document_raises`.
The module needs three new imports first — `import dataclasses` and `import re` beside the
existing `import warnings` at `:9`, and `from tephpy._constants import CONFIG_DEFAULTS`
beside the existing `from tephpy import _configfile` at `:14`:

```python
def _annotation(section, option):
    """The type ``_config`` declares for an option, for a direct ``coerce`` call."""
    return _configfile._option_hints(type(getattr(tephpy.config, section)))[option]


@pytest.mark.parametrize(
    ("section", "option", "value", "expected"),
    [
        ("isotherms", "color", "purple", "purple"),
        ("isotherms", "linewidth", 0.5, 0.5),
        ("isotherms", "linewidth", 1, 1.0),
        ("isotherms", "visible", False, False),
        ("isotherms", "labels", True, True),
        ("isotherms", "labels", "bottom", "bottom"),
        ("isotherms", "labels", ["bottom", "right"], ("bottom", "right")),
        ("isotherms", "values", [0, 10], (0.0, 10.0)),
        ("isotherms", "emphasis", {0: {"color": "red"}}, {0.0: {"color": "red"}}),
        ("cursor", "fields", ["pressure"], ("pressure",)),
        (
            "diagram",
            "extent",
            [[1000, -30], [300, 30]],
            ((1000.0, -30.0), (300.0, 30.0)),
        ),
        ("moist_adiabats", "truncation", -30.0, -30.0),
    ],
)
def test_a_well_typed_value_is_accepted(section, option, value, expected):
    """One accepted case per annotation shape, plus the two YAML forces.

    ``linewidth: 1`` is an ``int`` where a ``float`` is declared and must
    be accepted and converted; ``labels`` covers three of its four arms.
    The type assertion is not decoration: ``1 == 1.0`` and ``False == 0``
    in Python, so an equality-only test would pass with no conversion
    happening at all (configfile spec §5.2).
    """
    coerced = _configfile.coerce(section, option, value, _annotation(section, option))
    assert coerced == expected
    assert type(coerced) is type(expected)


@pytest.mark.parametrize(
    ("section", "option", "value", "match"),
    [
        ("isotherms", "linewidth", "thick", "expects a number, not the string 'thick'"),
        ("isotherms", "linewidth", True, "expects a number, not the boolean true"),
        ("isotherms", "color", 3, "expects a string, not the number 3"),
        ("isotherms", "visible", "maybe", "expects true or false"),
        ("isotherms", "values", "notalist", "expects a list of numbers"),
        ("isotherms", "values", [0, "ten"], "expects a list of numbers"),
        ("isotherms", "labels", 3, "expects true, false, an edge name"),
        ("isotherms", "emphasis", [0], "expects a mapping of member value"),
        ("cursor", "fields", "notalist", "expects a list of strings"),
        ("cursor", "fields", [1], "expects a list of strings"),
        ("diagram", "extent", 5, "expects two [pressure, temperature] corners"),
        ("diagram", "extent", [1, 2], "expects two [pressure, temperature] corners"),
        (
            "diagram",
            "extent",
            [[1000, -30], [300, "warm"]],
            "expects two [pressure, temperature] corners",
        ),
    ],
)
def test_a_wrong_typed_value_is_rejected(section, option, value, match):
    """Every measured case from the configfile spec §5.2 table, and then some.

    ``linewidth: true`` is the one that drove the design: it drew a 1 pt
    line, because ``isinstance(True, int)`` is ``True``. ``values:
    notalist`` and ``fields: notalist`` are the strings that would
    otherwise be iterated one character per member.
    """
    with pytest.raises(TephpyConfigError, match=re.escape(match)):
        _configfile.coerce(section, option, value, _annotation(section, option))


def test_every_option_has_a_validator():
    """An option whose type has no validator must fail here, not in silence.

    ``coerce`` returns an unrecognised annotation's value untouched, so
    that adding an option can never stop an import — which means nothing
    else in the suite would notice the gap. The option would simply go
    back to being applied unchecked, which is the defect configfile
    spec §5.2 exists to close.

    The first two assertions are what stop this gate passing by checking
    nothing, and the count is taken from ``CONFIG_DEFAULTS`` rather than
    written down, so adding an option updates it.
    """
    annotations = {}
    for field in dataclasses.fields(tephpy.config):
        section = getattr(tephpy.config, field.name)
        hints = _configfile._option_hints(type(section))
        for option in dataclasses.fields(section):
            annotations[field.name, option.name] = hints[option.name]
    assert annotations
    assert len(annotations) == sum(len(options) for options in CONFIG_DEFAULTS.values())
    missing = [
        key
        for key, annotation in sorted(annotations.items())
        if annotation not in _configfile._TYPE_VALIDATORS
    ]
    assert missing == []
    assert set(_configfile._TYPE_VALIDATORS) - set(annotations.values()) == set()
```

- [ ] **Step 2: Run the new tests and confirm they fail for the right reason**

```bash
pixi run --frozen tests tests/test_configfile.py -k "well_typed or wrong_typed or has_a_validator" -v
```

Expected: every one of them errors with `AttributeError: module 'tephpy._configfile' has
no attribute '_option_hints'`. That is the right failure — nothing exists yet. If any of
them *passes*, stop: the test is not reaching the code it claims to.

- [ ] **Step 3: Delete the two dead option groups**

In `src/tephpy/_configfile.py`, delete `:126-131` entirely — both `#:` comments, both
constants, and the blank line that separated them:

```python
#: Options whose YAML sequence becomes a tuple of strings.
_STRING_TUPLES: Final[frozenset[str]] = frozenset({"labels", "fields"})

#: Options whose YAML sequence becomes a tuple of floats.
_FLOAT_TUPLES: Final[frozenset[str]] = frozenset({"values"})
```

Their only readers are the two `option in …` branches of the old `coerce`, which Step 5
replaces. **Keep `_COLOR_OPTIONS`** at `:132-137` — it feeds the null-value quoting hint,
which this change does not touch.

- [ ] **Step 4: Extend the two import lines**

```python
from collections.abc import Callable, Mapping
```

and

```python
from typing import TYPE_CHECKING, Final, get_type_hints
```

Add nothing else. `force-sort-within-sections` is on, so an added `import` line would have
to be placed alphabetically; neither of these is a new line.

- [ ] **Step 5: Replace `coerce` with the validators**

Replace `src/tephpy/_configfile.py:192-233` — the whole of the existing `coerce`,
docstring included — with the following. It sits between `read_document` and
`_PACKAGE_ROOT`, which is where the old `coerce` was.

```python
class _MismatchError(Exception):
    """A configuration value does not match the type its option declares.

    Carries no message of its own. The section, the option and the expected
    type are known to :func:`coerce` and not to the converter that raises,
    so composing the text here would mean threading all three through every
    converter (configfile spec §5.2).
    """


def _as_string(value: object) -> str:
    """Check a value is a string.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    str
        The value, unchanged.

    Raises
    ------
    _MismatchError
        If the value is not a string.
    """
    if not isinstance(value, str):
        raise _MismatchError
    return value


def _as_number(value: object) -> float:
    """Check a value is a number, and convert it to a float.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    float
        The value as a float, so ``linewidth: 1`` and ``linewidth: 1.0``
        reach the configuration as the same thing.

    Raises
    ------
    _MismatchError
        If the value is not a number. ``bool`` is excluded explicitly:
        ``isinstance(True, int)`` is ``True`` in Python, which is how
        ``linewidth: true`` came to draw a 1 pt line (configfile spec §5.2).
    """
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _MismatchError
    return float(value)


def _as_flag(value: object) -> bool:
    """Check a value is a boolean.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    bool
        The value, unchanged.

    Raises
    ------
    _MismatchError
        If the value is not a boolean. YAML 1.1 spells more things
        ``bool`` than Python does: ``yes``, ``no``, ``on`` and ``off``
        all arrive here already converted.
    """
    if not isinstance(value, bool):
        raise _MismatchError
    return value


def _as_string_tuple(value: object) -> tuple[str, ...]:
    """Check a value is a list of strings, and convert it to a tuple.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    tuple of str
        The list as a tuple (configfile spec §3.3).

    Raises
    ------
    _MismatchError
        If the value is not a list, or any entry is not a string.
    """
    if not isinstance(value, list) or not all(
        isinstance(entry, str) for entry in value
    ):
        raise _MismatchError
    return tuple(value)


def _as_labels(value: object) -> bool | str | tuple[str, ...]:
    """Check a value is a labels setting, and convert any list to a tuple.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    bool or str or tuple of str
        The value, with a list of edge names as a tuple.

    Raises
    ------
    _MismatchError
        If the value is neither a boolean, nor a string, nor a list of
        strings.
    """
    if isinstance(value, bool | str):
        return value
    return _as_string_tuple(value)


def _as_number_tuple(value: object) -> tuple[float, ...]:
    """Check a value is a list of numbers, and convert it to a tuple of floats.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    tuple of float
        The list as a tuple of floats (configfile spec §3.3).

    Raises
    ------
    _MismatchError
        If the value is not a list, or any entry is not a number. A bare
        string is the case worth naming: iterating it would otherwise
        yield one member per character.
    """
    if not isinstance(value, list):
        raise _MismatchError
    return tuple(_as_number(entry) for entry in value)


def _as_corner(value: object) -> tuple[float, float]:
    """Check a value is one [pressure, temperature] corner.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    tuple of float
        The corner as a two-tuple of floats.

    Raises
    ------
    _MismatchError
        If the value is not a list of exactly two numbers.
    """
    if not isinstance(value, list) or len(value) != 2:
        raise _MismatchError
    first, second = value
    return (_as_number(first), _as_number(second))


def _as_extent(value: object) -> tuple[tuple[float, float], tuple[float, float]]:
    """Check a value is two [pressure, temperature] corners.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    tuple of tuple of float
        The extent as nested tuples of floats (configfile spec §3.3).

    Raises
    ------
    _MismatchError
        If the value is not a list of exactly two corners.
    """
    if not isinstance(value, list) or len(value) != 2:
        raise _MismatchError
    first, second = value
    return (_as_corner(first), _as_corner(second))


def _as_emphasis(value: object) -> dict[float, dict[str, object]]:
    """Check a value is an emphasis mapping, and convert its keys to floats.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    dict
        Member value to style overrides, keyed by float so ``850`` and
        ``850.0`` are not two different members (configfile spec §3.3).

    Raises
    ------
    _MismatchError
        If the value is not a mapping, or a member is not a number, or a
        style is not a mapping keyed by strings. The style *values* are
        annotated ``object`` and so are not checked at all
        (configfile spec §5.2).
    """
    if not isinstance(value, Mapping):
        raise _MismatchError
    emphasis: dict[float, dict[str, object]] = {}
    for member, style in value.items():
        if not isinstance(style, Mapping) or not all(
            isinstance(key, str) for key in style
        ):
            raise _MismatchError
        emphasis[_as_number(member)] = dict(style)
    return emphasis


#: One ``(description, converter)`` per distinct annotation in ``Config``:
#: eight entries covering all 42 options. The keys are evaluated
#: annotations, which compare equal to the ones ``typing.get_type_hints``
#: returns for ``_config``'s dataclasses — so the expected types are read
#: from the declarations rather than written out a second time. Each
#: converter both checks and converts, which makes it the natural home for
#: the §3.3 coercions rather than a second pass over the same value
#: (configfile spec §5.2).
_TYPE_VALIDATORS: Final[Mapping[object, tuple[str, Callable[[object], object]]]] = (
    MappingProxyType(
        {
            str | None: ("a string", _as_string),
            float | None: ("a number", _as_number),
            bool | None: ("true or false", _as_flag),
            bool | str | tuple[str, ...] | None: (
                "true, false, an edge name, or a list of edge names",
                _as_labels,
            ),
            tuple[float, ...] | None: ("a list of numbers", _as_number_tuple),
            tuple[str, ...] | None: ("a list of strings", _as_string_tuple),
            tuple[tuple[float, float], tuple[float, float]] | None: (
                "two [pressure, temperature] corners",
                _as_extent,
            ),
            Mapping[float, Mapping[str, object]] | None: (
                "a mapping of member value to style overrides",
                _as_emphasis,
            ),
        }
    )
)


def _describe(value: object) -> str:
    """Name a value as the reader of the file would.

    Parameters
    ----------
    value : object
        The value as ``yaml.safe_load`` produced it.

    Returns
    -------
    str
        The value described in the vocabulary of the YAML file being
        edited rather than of the annotation behind it — the reader has
        never seen ``float`` (configfile spec §5.2). ``bool`` is tested
        first because it is also an ``int``.
    """
    if isinstance(value, bool):
        return f"the boolean {str(value).lower()}"
    if isinstance(value, str):
        return f"the string {value!r}"
    if isinstance(value, int | float):
        return f"the number {value!r}"
    return repr(value)


def _option_hints(section_type: type[object]) -> Mapping[str, object]:
    """Return each option's declared type for a configuration section.

    Parameters
    ----------
    section_type : type
        A section dataclass, as ``type(config.isotherms)`` gives it.

    Returns
    -------
    mapping
        Option name to the annotation ``_config`` declares for it.
        ``get_type_hints`` evaluates the strings that ``from __future__
        import annotations`` leaves behind, in the namespace of the module
        that defined the class — which is how this module reads
        ``_config``'s types without importing it and reversing the
        dependency arrow (configfile spec §3).
    """
    return MappingProxyType(get_type_hints(section_type))


def coerce(section: str, option: str, value: object, annotation: object) -> object:
    """Check a parsed YAML value against its declared type, and convert it.

    Parameters
    ----------
    section : str
        The configuration section the option belongs to.
    option : str
        The option name.
    value : object
        The value as ``yaml.safe_load`` produced it.
    annotation : object
        The type ``_config`` declares for the option, as
        :func:`_option_hints` returns it.

    Returns
    -------
    object
        The value in the type ``tephpy.config`` holds (configfile
        spec §3.3). An annotation with no validator is returned untouched
        rather than rejected: adding an option must not be able to stop an
        import, and the completeness gate in ``tests/test_configfile.py``
        is what reports the gap instead (configfile spec §5.2).

    Raises
    ------
    TephpyConfigError
        If the value does not match the declared type. The message is a
        noun phrase — ``isotherms.linewidth, which expects a number, not
        the string 'thick'`` — so that :func:`apply` can lead with the
        file and the word "ignoring" and have the whole read as one
        sentence.
    """
    validator = _TYPE_VALIDATORS.get(annotation)
    if validator is None:
        return value
    description, convert = validator
    try:
        return convert(value)
    except _MismatchError:
        msg = f"{section}.{option}, which expects {description}, not {_describe(value)}"
        raise TephpyConfigError(msg) from None
```

- [ ] **Step 6: Pass the annotation from `apply`**

Two edits inside `apply`. After the `valid = {…}` line at `:306`, add the lookup — once per
section, outside the option loop:

```python
        section = getattr(config, name)
        valid = {field.name for field in dataclasses.fields(section)}
        hints = _option_hints(type(section))
```

and at `:325`, pass it:

```python
            setattr(section, option, coerce(name, option, value, hints[option]))
```

`hints[option]` is safe: the `option not in valid` branch above has already `continue`d on
any name the section does not declare, and `valid` and `hints` are built from the same
dataclass.

- [ ] **Step 7: Update the two fixture-test call sites**

In `tests/test_configfile_fixture.py`, add the same helper after `_document` at `:27-28`:

```python
def _annotation(section, option):
    """The type ``_config`` declares for an option, for a direct ``coerce`` call."""
    return _configfile._option_hints(type(getattr(tephpy.config, section)))[option]
```

then at `:45`:

```python
        coerced = _configfile.coerce(
            section, option, loaded[option], _annotation(section, option)
        )
```

and at `:55`:

```python
            expected = _configfile.coerce(
                section, option, document[section][option], _annotation(section, option)
            )
```

These two tests now also prove something they did not before: the complete fixture, which
sets **every** option to a non-default value, passes the type check for all 42.

- [ ] **Step 8: Run the tests**

```bash
pixi run --frozen tests tests/test_configfile.py tests/test_configfile_fixture.py -v
```

Expected: everything passes, including the pre-existing `test_a_malformed_value_raises` —
its three cases still raise `TephpyConfigError`, and the new messages still contain
`diagram.extent`, `isotherms.emphasis` and `isotherms.values`, which is what it matches on.
Task 2 is what changes that test.

Then the whole suite, because `coerce`'s signature changed:

```bash
pixi run --frozen tests
```

- [ ] **Step 9: Mutation-prove the two claims that are easiest to get wrong**

Stage first — `git checkout` reverts from the index:

```bash
git add src/tephpy/_configfile.py tests/test_configfile.py tests/test_configfile_fixture.py
```

**(a) The `bool` exclusion.** In `_as_number`, drop it:

```python
    if not isinstance(value, int | float):
```

```bash
pixi run --frozen tests tests/test_configfile.py -k "wrong_typed" -v
git checkout -- src/tephpy/_configfile.py
```

Expected: exactly one failure, the `linewidth`/`True` case. If any other case fails too,
the exclusion was load-bearing somewhere unintended.

**(b) The completeness gate.** Delete the `tuple[str, ...] | None` entry from
`_TYPE_VALIDATORS`:

```bash
pixi run --frozen tests tests/test_configfile.py -k "has_a_validator or wrong_typed" -v
git checkout -- src/tephpy/_configfile.py
```

Expected: `test_every_option_has_a_validator` fails on `missing == []`, naming
`('cursor', 'fields')` and `('isotherms', 'labels')`… — no: `labels` has its own shape, so
the report is `[('cursor', 'fields')]` alone. The two `cursor.fields` reject cases fail as
well, because an unvalidated annotation now passes through untouched. Both failures are the
point: the gate catches the gap, and the matrix shows what the gap costs.

Then the orphan half — add a validator no option uses:

```python
            complex | None: ("a complex number", _as_number),
```

```bash
pixi run --frozen tests tests/test_configfile.py -k "has_a_validator" -v
git checkout -- src/tephpy/_configfile.py
```

Expected: the final assertion fails. Without it, a validator left behind by a deleted
option would sit there unnoticed.

- [ ] **Step 10: Commit**

```bash
git add src/tephpy/_configfile.py tests/test_configfile.py tests/test_configfile_fixture.py
git commit -m "Check a configuration value against its declared type

Eight converters, one per distinct annotation in \`Config\`, each of which
both checks a value and performs the coercion the YAML format forces. The
expected types are read from the annotations \`_config\` already declares
rather than written out a second time, and a completeness gate fails if an
option's type has no validator.

\`coerce\` takes the annotation as a fourth argument rather than consulting
a module-level table: \`_configfile\` cannot import \`_config\` at runtime
without reversing the dependency arrow, and a lazily-built table would
leave a direct caller checking against an empty one.

Detection only. A mismatch still rejects the file, as it does today; the
warn-and-skip policy is the next commit (configfile spec §5.2).

Part of {issue}\`105\`."
```

---

### Task 2: Warn, skip the option, keep the file

**Files:**
- Modify: `src/tephpy/_configfile.py` (`apply` at `:265-326`)
- Modify: `src/tephpy/_config.py` (`Config.load` docstring, `Warns` section at `:218-223`)
- Test: `tests/test_configfile.py` (rewrite `test_a_malformed_value_raises` at `:241-260`;
  add two tests after it)
- Test: `tests/test_cli.py` (add after
  `test_path_marks_a_file_with_an_unknown_option_in_force` at `:106-125`)
- Test: `tests/test_config_autoload.py` (add after
  `test_warnings_as_errors_does_not_stop_the_import` at `:156-171`)

**Interfaces:**
- Consumes: `coerce(section, option, value, annotation)` and `_option_hints` from Task 1;
  `_warn_from_caller(message: str) -> None` at `_configfile.py:242`, unchanged.
- Produces: no new names. `apply`'s signature is unchanged; what changes is that a
  wrong-typed value now warns instead of raising, and all three option-level warnings gain
  a `f"{source}: "` prefix.

- [ ] **Step 1: Write the failing tests**

First **replace** `test_a_malformed_value_raises` (`tests/test_configfile.py:241-260`)
entirely — the three cases stay, what they assert inverts:

```python
@pytest.mark.parametrize(
    ("text", "section", "option", "match"),
    [
        (
            "diagram:\n  extent: [[1000, -30], [300, warm]]\n",
            "diagram",
            "extent",
            "diagram.extent",
        ),
        (
            "isotherms:\n  emphasis: [0]\n",
            "isotherms",
            "emphasis",
            "isotherms.emphasis",
        ),
        ("isotherms:\n  values: [0, ten]\n", "isotherms", "values", "isotherms.values"),
    ],
    ids=["extent", "emphasis", "values"],
)
def test_a_wrong_typed_value_warns_and_keeps_the_default(
    tmp_path, text, section, option, match
):
    """The three cases that used to cost the reader the whole file.

    Each is an option-level problem, so it warns and is skipped like an
    unknown option and a null value, and the option keeps its default
    (configfile spec §5.2). Before this change all three raised
    ``TephpyConfigError`` out of ``apply``, which under the auto-load left
    every other option in the file unapplied.
    """
    path = _write(tmp_path, text)
    with pytest.warns(TephpyConfigWarning, match=match):
        _configfile.apply(tephpy.config, _configfile.read_document(path), source=path)
    assert getattr(getattr(tephpy.config, section), option) is None
```

Then add, after it:

```python
def test_a_wrong_typed_value_does_not_cost_the_rest_of_the_file(tmp_path):
    """ "The rest of the file still applies" is otherwise a claim about nothing.

    One bad option beside a good one, in one file, reached through
    ``Config.load`` so the rollback is in play: the good option must
    survive, and ``source`` must be set — a rejected file leaves it
    ``None`` (configfile spec §5.2).
    """
    path = _write(tmp_path, "isotherms:\n  linewidth: thick\n  color: purple\n")
    with pytest.warns(TephpyConfigWarning, match="expects a number"):
        tephpy.config.load(path)
    assert tephpy.config.isotherms.linewidth is None
    assert tephpy.config.isotherms.color == "purple"
    assert tephpy.config.source == path


def test_every_option_level_warning_names_the_file(tmp_path):
    """With three cascade entries, a warning naming no file is half an answer.

    All three option-level warnings — unknown option, null value,
    wrong-typed value — lead with the path, as the file-level errors
    already do (configfile spec §5.2).
    """
    path = _write(
        tmp_path,
        "isotherms:\n  colour: purple\n  alpha:\n  linewidth: thick\n",
    )
    with pytest.warns(TephpyConfigWarning) as record:
        tephpy.config.load(path)
    assert len(record) == 3
    assert all(str(entry.message).startswith(f"{path}: ") for entry in record)
```

Add to `tests/test_cli.py`, after `test_path_marks_a_file_with_an_unknown_option_in_force`:

```python
def test_path_marks_a_file_with_a_wrong_typed_value_in_force(
    runner, monkeypatch, tmp_path, user_config
):
    """The user-visible end of the escalation.

    ``extent: 5`` used to raise out of ``apply``, which made ``_applies``
    return False and this command report ``[rejected]`` — an option-level
    problem presented as a whole-file one. It is now warned about and
    skipped, so the file is in force (configfile spec §5.2).
    """
    monkeypatch.delenv(_configfile.CONFIG_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tephpyrc.yaml").write_text("diagram:\n  extent: 5\n", encoding="utf-8")
    result = runner.invoke(_cli.main, ["config", "path"])
    assert result.exit_code == 0
    assert f"{tmp_path / 'tephpyrc.yaml'}  [in force]" in result.output
    assert "rejected" not in result.output
    assert not user_config.exists()
```

Add to `tests/test_config_autoload.py`, after
`test_warnings_as_errors_does_not_stop_the_import`:

```python
def test_a_wrong_typed_value_does_not_stop_the_import(tmp_path):
    """The whole rule, exercised on the path that has no user frame.

    ``PYTHONWARNINGS=error`` would turn the warning into an exception, and
    the auto-load's ``always`` filter is what stops it; ``check=True`` is
    half the assertion. The other half is ``purple``: the option beside
    the bad one still applies, which is what distinguishes warn-and-skip
    from the whole-file rejection this replaces (configfile spec §5.2).
    """
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "isotherms:\n  linewidth: thick\n  color: purple\n", encoding="utf-8"
    )
    result = _run(tmp_path, TEPHPYRC=str(bad), PYTHONWARNINGS="error")
    assert "TephpyConfigWarning" in result.stderr
    assert "expects a number" in result.stderr
    colour, source = result.stdout.splitlines()
    assert colour == "purple"
    assert source == str(bad)
```

- [ ] **Step 2: Run them and confirm they fail for the right reason**

```bash
pixi run --frozen tests tests/test_configfile.py -k "warns_and_keeps or rest_of_the_file or names_the_file" -v
pixi run --frozen tests tests/test_cli.py::test_path_marks_a_file_with_a_wrong_typed_value_in_force -v
pixi run --frozen tests tests/test_config_autoload.py::test_a_wrong_typed_value_does_not_stop_the_import -v
```

Expected, in order: `TephpyConfigError` raised where a warning was wanted (three cases,
then the one-bad-one-good case); `test_every_option_level_warning_names_the_file` failing
on the raise as well; `[rejected]` where `[in force]` was wanted; and `None` where `purple`
was wanted in the subprocess.

- [ ] **Step 3: Make `apply` warn instead**

Three edits in `src/tephpy/_configfile.py:265-326`.

Add the prefix as the first statement of the body, after the docstring:

```python
    prefix = f"{source}: " if source is not None else ""
```

`source` is `Path | None`, and `None` is reachable — the parameter is declared optional and
a caller with no file to name must not produce the string `"None: ignoring …"`.

Lead both existing warnings with it. Note the unknown-option message is re-split across
three implicitly-concatenated pieces rather than the current two, because `{prefix}` pushes
the first line past 88 columns — the message the reader sees is character-for-character
what it was, plus the path:

```python
if option not in valid:
    _warn_from_caller(
        f"{prefix}ignoring unknown option {option!r} in "
        f"configuration section {name!r}; expected one of "
        f"{sorted(valid)}"
    )
    continue
if value is None:
    hint = (
        "; an unquoted '#' colour is read as a comment, so quote "
        "it as '#b0b0b0' if that is what happened"
        if option in _COLOR_OPTIONS
        else ""
    )
    _warn_from_caller(f"{prefix}ignoring {name}.{option}, whose value is null{hint}")
    continue
```

and replace the bare `setattr` from Task 1 Step 6 with the catch:

```python
            try:
                setattr(section, option, coerce(name, option, value, hints[option]))
            except TephpyConfigError as exc:
                _warn_from_caller(f"{prefix}ignoring {exc}")
```

No `continue` is needed after the `except` — it is the last statement in the loop body.

Then update `apply`'s own `Warns` section, which currently reads "If an option is unknown,
or its value is an explicit null":

```python
    Warns
    -----
    TephpyConfigWarning
        If an option is unknown, its value is an explicit null, or its
        value does not match the type the option declares.
    """
```

- [ ] **Step 4: Update `Config.load`'s docstring**

`src/tephpy/_config.py:218-223`, the `Warns` section, same sentence:

```python
        Warns
        -----
        TephpyConfigWarning
            If an option is unknown, its value is an explicit null, or its
            value does not match the type the option declares. A caller who
            has filtered this category to an error gets that exception
            instead, and the same all-or-nothing restore.
```

That last sentence is already there and stays true, and it is worth reading twice: under
`warnings.simplefilter("error")` a wrong-typed value still rejects the whole file on an
explicit `load`, exactly as an unknown option does. The rule is about what tephpy does, not
about what a caller's own filters then do with it.

- [ ] **Step 5: Run the tests**

```bash
pixi run --frozen tests
```

Expected: the whole suite passes. Three pre-existing tests are worth watching, all of which
should still pass unchanged:

- `test_a_null_option_value_warns_and_names_the_quoting_trap` and
  `test_an_unknown_option_warns_and_is_skipped` match on `"quote"` and `"colour"`, both of
  which survive a path prefix.
- `test_a_rejected_file_leaves_the_configuration_as_it_was` uses an unknown *section*, and
  `test_a_rejected_file_rolls_back_under_warnings_as_errors` an unknown *option* under
  `simplefilter("error")`. Neither depended on `coerce` raising.
- `test_path_marks_a_rejected_file` uses malformed YAML, which `read_document` still
  rejects. Nothing about `[rejected]` has gone away; it now means what it says.

- [ ] **Step 6: Mutation-prove the two behaviours**

```bash
git add src/tephpy/_configfile.py src/tephpy/_config.py tests/
```

**(a) The `except` that ends the escalation.** Replace the try/except with the bare
`setattr` from Task 1:

```bash
pixi run --frozen tests tests/test_configfile.py tests/test_cli.py tests/test_config_autoload.py
git checkout -- src/tephpy/_configfile.py
```

Expected: the four new policy tests fail and the Task 1 matrix still passes — the matrix
tests `coerce`, this tests `apply`, and the split is what makes each failure precise.

**(b) The path prefix.** Delete the `prefix` from all three warnings:

```bash
pixi run --frozen tests tests/test_configfile.py -v
git checkout -- src/tephpy/_configfile.py
```

Expected: `test_every_option_level_warning_names_the_file` fails, and nothing else does. A
prose-only change is unguarded by default; this is what proves it is not.

- [ ] **Step 7: Commit**

```bash
git add src/tephpy/_configfile.py src/tephpy/_config.py tests/
git commit -m "Warn and skip a wrong-typed option, keeping the rest of the file

An option-level problem now behaves like every other option-level
problem: the option is skipped, keeps its default, and the rest of the
file still applies. Four measured cases changed behaviour -- three that
loaded silently and drew the wrong thing, and \`extent\`, which did the
opposite and rejected the whole file over one line.

All three option-level warnings now lead with the path. With three
cascade entries, naming \`isotherms.linewidth\` without naming a file does
not tell the reader which file to edit, and the file-level errors already
led with it.

Closes {issue}\`105\`."
```

---

### Task 3: The how-to, the specification correction, and the changelog

**Files:**
- Modify: `docs/src/howtos/configuration.rst` ("After an Upgrade", `:100-126`)
- Modify: `docs/src/developer/specs/2026-08-07-config-file-design.md` (the `_OPTION_TYPES`
  bullet, `:355-357`)
- Create: `changelog/<PR>.bugfix.rst`

**Interfaces:**
- Consumes: nothing new. This task adds no code.
- Produces: nothing later tasks rely on. It is the last task.

- [ ] **Step 1: Extend the how-to**

`configfile spec §8` requires the how-to to cover "what happens to a wrong-typed value
(§5.2)". "After an Upgrade" is where the option-level/section-level distinction already
lives, so it goes there. In `docs/src/howtos/configuration.rst`, after the paragraph ending
"…because nothing in the file is applied at all.", insert:

```rst
A value of the wrong type is treated the same way as an option tephpy no
longer recognises: ``linewidth: thick`` warns, that one option is skipped
and keeps its default, and every other line in the file still applies. The
warning names the file, the option, what was expected and what it found::

    tephpyrc.yaml: ignoring isotherms.linewidth, which expects a number, not the string 'thick'

Two details of YAML are worth knowing before you read one of these.
``linewidth: 1`` is fine — an integer is accepted wherever a number is
wanted. But ``linewidth: true`` is not a number at all, and neither are
``yes``, ``no``, ``on`` and ``off``, which YAML also reads as true or
false. Quote them if you meant the words.
```

- [ ] **Step 2: Correct the specification bullet**

In `docs/src/developer/specs/2026-08-07-config-file-design.md`, replace the `_OPTION_TYPES`
bullet at `:355-357` with:

```markdown
- The expected type reaches `coerce` as an argument. `apply` resolves it from the section
  it already holds, through `_option_hints`, a thin wrapper on `typing.get_type_hints`
  which resolves cleanly through the `from __future__ import annotations` in `_config.py`.
  A module-level `{(section, option): annotation}` table is not available: `_configfile`
  cannot import `_config` at runtime without reversing the §3 dependency arrow, and a
  lazily-built one would leave a direct `coerce` caller checking against an empty table.
  **Measured:** 42 options over 8 distinct annotation shapes.
```

This is the living-document correction the specification asks for when code and spec
diverge — the rest of §5.2 is unchanged, and it describes what was built.

- [ ] **Step 3: Open the pull request, and take its number**

The fragment is named for the pull request, so the pull request has to exist first. An
issue filed in between would otherwise take the number the fragment assumed.

```bash
git push -u origin fix/config-value-validation
gh pr create --draft --title "Warn and skip a wrong-typed configuration value" --body "$(cat <<'BODY'
Closes {issue}`105`.

Implements `configfile spec §5.2`. A configuration value must match the type its `Config`
field declares; a value that does not now warns, is skipped, and leaves the rest of the
file applying — instead of being applied unchecked, or costing the reader the whole file.

Two departures from the specification as committed, both recorded in
`docs/src/developer/plans/2026-08-10-tephpy-config-value-validation.md`:

- there is no `_OPTION_TYPES` table — the annotation is an argument to `coerce`, because
  `_configfile` cannot import `_config` at runtime; the §5.2 bullet is corrected here.
- `_option_hints` is not cached — `mypy --strict` rejects `functools.cache` over a
  `type[…]` parameter, and the cache would buy 0.9 ms against a 485 ms import.
BODY
)"
gh pr view --json number --jq .number
```

Use that number as `<PR>` below.

- [ ] **Step 4: Write the changelog fragment**

`changelog/<PR>.bugfix.rst`:

```rst
Fixed a configuration file value of the wrong type being applied unchecked
(:issue:`105`). ``linewidth: thick`` loaded silently and failed much later inside
Matplotlib, naming neither the file nor the option; ``linewidth: true`` and
``visible: maybe`` loaded and drew the wrong thing without any error at all; and
``extent: 5`` did the opposite, rejecting the whole file over one line. Every one
of these now warns, naming the file and the option, and skips just that option —
the rest of the file still applies. An integer is still accepted wherever a number
is wanted, so ``linewidth: 1`` is unaffected. (:user:`claude`)
```

Check it against the conventions before moving on: `:issue:` for the issue the problem is
described in, `:user:` attribution last, and no bare `#105` anywhere.

- [ ] **Step 5: File the deferred follow-up**

`configfile spec §9` now carries a non-goal — "Domain validation of a value that has the
right type" — with no issue behind it. File one, so the deferral survives this branch:

```bash
gh issue create --title "A configuration value of the right type is not checked for validity" --label "type: enhancement" --body "$(cat <<'BODY'
`configfile spec §5.2` checks a configuration value against the type its `Config` field
declares, and stops there. Three classes of mistake have the right type and are still
wrong:

- `color: notacolour` — a string, which Matplotlib rejects at the first draw.
- `fields: [nonsuch]` — a list of strings, which leaves the cursor readout quietly wrong.
- `emphasis: {0.0: {linewidth: thick}}` — the member and the style keys are typed, but the
  style *values* are annotated `object`, so nothing checks them.

Each needs knowledge the type check does not have: which colours Matplotlib accepts, which
cursor fields exist, and which style keys an emphasis entry may carry. `configfile spec §9`
records this as a non-goal of the type work, deliberately.

Deferred from {issue}`105`.
BODY
)"
```

- [ ] **Step 6: Build the documentation clean, and verify what rendered**

```bash
pixi run --frozen docs
```

Expected: `build succeeded`, no warnings. The `docs` task depends on `docs-clean`, which
matters here — an incremental build serves a stale draft of the changelog page.

Then confirm the three things that can render wrong rather than fail:

```bash
grep -c "which expects a number" docs/_build/html/howtos/configuration.html
grep -o "issues/105" docs/_build/html/reference/changelog.html | head -1
grep -o "_option_hints" docs/_build/html/developer/specs/2026-08-07-config-file-design.html | head -1
```

Expected: a non-zero count and both greps hitting. The literal block in Step 1 is longer
than the 88-column prose around it; check it has not been wrapped mid-message in the
rendered page, which would misquote the warning the reader is trying to match.

- [ ] **Step 7: Full verification**

```bash
pixi run --frozen tests
pixi run --frozen lint
```

Expected: the whole suite passes, and every pre-commit hook passes — including
`design specification citations resolve`, which checks that every new
`configfile spec §5.2` citation resolves to the `(configfile-spec-5-2)=` anchor (the gate
derives the slug by replacing the dot), and `check-github-references`, which rejects a bare
issue number in the changelog fragment or the how-to.

Both gates run over `check_citations.corpus`, which excludes
`docs/src/developer/plans/` — so a passing run says nothing about the citations in this
plan. The ones that matter are the ones in the code, the tests and the published docs,
which is what the corpus covers.

If `pre-commit` has never been installed in this worktree, install it first — a fresh
clone or worktree has no hooks, and `pixi run --frozen lint` is what runs them all:

```bash
pre-commit install
```

- [ ] **Step 8: Commit and mark the pull request ready**

```bash
git add docs/ changelog/
git commit -m "Document the wrong-typed value, and correct the specification

The how-to gains what happens to a wrong-typed value, as configfile spec
§8 requires, including the two YAML traps a reader will hit: an integer is
accepted where a number is wanted, and \`true\`, \`yes\`, \`no\`, \`on\` and
\`off\` are not numbers.

Corrects the configfile spec §5.2 implementation bullet, which described
an \`_OPTION_TYPES\` table that cannot be built without reversing the §3
dependency arrow. The specification is a living document; this is what it
asks for when the code and the spec diverge.

Part of {issue}\`105\`."
git push
gh pr ready
```

---

## Self-review

**Spec coverage.** `configfile spec §5.2` makes nine claims. Each has a task:

| §5.2 claim | Where |
|---|---|
| A value must match its field's declared type | Task 1 Steps 5-6 |
| Warn, skip the option, keep the rest of the file | Task 2 Steps 1, 3 |
| `int` accepted where `float` is declared | Task 1 Step 5 (`_as_number`), matrix case `linewidth: 1` |
| `bool` rejected there | Task 1 Step 5, matrix case `linewidth: true`, mutation-proved in Step 9(a) |
| Types read from the annotations, not written twice | Task 1 Steps 5-6 (`_option_hints`, `_TYPE_VALIDATORS` keyed by annotation) |
| `_TYPE_VALIDATORS`, one entry per shape | Task 1 Step 5 |
| One `except` in `apply` delivers the rule | Task 2 Step 3, mutation-proved in Step 6(a) |
| Completeness gate, non-empty and self-checking | Task 1 Step 1, mutation-proved in Step 9(b) |
| The message, and the path prefix on all three warnings | Task 2 Steps 1, 3; mutation-proved in Step 6(b) |

`configfile spec §6` adds three testing rows — the accept/reject matrix, the completeness
gate, and one wrong-typed option beside a good one — which are Task 1 Step 1 and Task 2
Step 1. `configfile spec §8` requires the how-to entry: Task 3 Step 1. `configfile spec §9`
records the domain-validity non-goal: Task 3 Step 5 gives it an issue to point at. The
`_OPTION_TYPES` bullet is the one claim the implementation does not satisfy, and Task 3
Step 2 corrects it rather than leaving the divergence unrecorded.

**Placeholders.** `<PR>` in Task 3 is a value the plan says exactly how to obtain (Step 3),
and the ordering — pull request before fragment — is deliberate. No other step defers
content.

**Type consistency.** `coerce(section: str, option: str, value: object, annotation: object)
-> object` is defined once (Task 1 Step 5) and called with four positional arguments at all
three call sites (Task 1 Step 6, Task 1 Step 7 twice). `_option_hints(section_type:
type[object]) -> Mapping[str, object]` is defined once and called with `type(section)` in
`apply` and in the three test helpers, all spelled
`_configfile._option_hints(type(getattr(tephpy.config, section)))[option]`. Every converter
is `(value: object) -> …` and raises only `_MismatchError`; `_as_labels` and
`_as_number_tuple` and `_as_extent` are the three that call another converter, and all
three call ones defined above them in the file. `_TYPE_VALIDATORS`' value type
`tuple[str, Callable[[object], object]]` is unpacked as `description, convert` in `coerce`
and nowhere else.

**Verified before writing, not after.** The implementation in Task 1 Step 5 was run against
the real `Config` before this plan was written: 42 options over 8 shapes with no missing
validator and no orphan, all 13 accept and 13 reject cases correct, the four messages
`configfile spec §5.2` publishes reproduced verbatim, and the complete fixture validating
throughout. It is `ruff format`-clean and `ruff check`-clean under the project
configuration, and `mypy --strict` clean with the repository's four extra error codes.
