# tephpy configuration value domains — design specification

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. `src/tephpy/_configfile.py` and `src/tephpy/_constants.py` cite it by section —
> `domain spec §3.2` and the like — so these sections *are* the reasoning behind what the
> code does, and where the two ever diverge it is the specification that gets corrected.
> Read it as current.

- **Date:** 2026-08-12 (originated; maintained since)
- **Status:** living design specification; the work it specifies is {issue}`116`
- **Citation prefix:** `domain spec §…` — not `config spec` or `validation spec`, either of
  which would read as a near-duplicate of configfile spec §5.2, the type check this sits
  behind
- **Scope:** checking a configuration-file value that has the right type and is still not a
  value the option can accept
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) — inherits
  its error-handling (spec §6), testing (spec §7) and engineering-standards (spec §8) rules
  unchanged
- **Sibling spec:** [`2026-08-07-config-file-design.md`](2026-08-07-config-file-design.md) —
  configfile spec §5.2 checks a value against the type its `Config` field declares and
  stops there; this specification is what happens next, and inherits that section's
  warn-and-skip rule rather than restating it

(domain-spec-1)=
## 1. Purpose

A configuration value can have exactly the right type and still be wrong. `color` is
`str | None`, so `color: notacolour` is a string and loads. `interval` is `float | None`, so
`interval: 0` is a number and loads. Neither is a value tephpy can draw.

**Measured** against the implementation as of {pull}`125`, one bad value per file:

| File | At load | At first draw |
|---|---|---|
| `isotherms: {linewidth: -1.0}` | silent | **draws** |
| `isotherms: {linewidth: .inf}` | silent | **draws** |
| `isotherms: {values: [.nan]}` | silent | **draws** |
| `moist_adiabats: {truncation: .nan}` | silent | **draws** |
| `isotherms: {color: notacolour}` | silent | `ValueError: 'notacolour' is not a valid color value.` |
| `isotherms: {color: 'b0b0b0'}` | silent | `ValueError: 'b0b0b0' is not a valid color value.` |
| `isotherms: {alpha: 5.0}` | silent | `ValueError: alpha (5.0) is outside 0-1 range` |
| `isotherms: {emphasis: {0.0: {color: notacolour}}}` | silent | `ValueError: Invalid RGBA argument: 'notacolour'` |
| `isotherms: {emphasis: {0.0: {linestyle: notaline}}}` | silent | `ValueError: Do not know how to convert ['solid', 'solid', 'solid', … ] to dashes` |
| `isotherms: {labels: [botom]}` | silent | `TypeError: unknown 'isotherms' label placement 'botom'; expected True, False, or edge name(s) from ['bottom', 'top', 'left', 'right']` |
| `isobars: {interval: 0.0}` | silent | `ValueError: 'isobars' interval must be a positive, finite number: 0.0` |
| `isobars: {interval: .inf}` | silent | `ValueError: 'isobars' interval must be a positive, finite number: inf` |
| `diagram: {extent: [[0.0, -80.0], [1050.0, 40.0]]}` | silent | `ValueError: extent corners must be physical (pressure > 0 hPa): ((0.0, -80.0), (1050.0, 40.0))` |
| `diagram: {extent: [[.inf, -80.0], [300.0, 40.0]]}` | silent | `ValueError: extent corners must be physical (pressure > 0 hPa): ((inf, -80.0), (300.0, 40.0))` |
| `isotherms: {emphasis: {0.0: {lw: 2.0}}}` | silent | `TypeError: unknown 'isotherms' emphasis style key(s) ['lw'] for member 0; expected ['color', 'linewidth', 'linestyle', 'alpha']` |
| `isotherms: {emphasis: {0.0: {linewidth: thick}}}` | silent | `TypeError: 'isotherms' emphasis 'linewidth' for member 0 must be a number: 'thick'` |
| `isotherms: {emphasis: {0.0: {alpha: 5.0}}}` | silent | `ValueError: 'isotherms' emphasis 'alpha' for member 0 must be between 0 and 1: 5.0` |
| `cursor: {fields: [nonsuch]}` | silent | `TypeError: unknown cursor field(s) ['nonsuch']; expected ['mixing_ratio', 'pressure', 'temperature', 'theta', 'theta_w']` |

Every row loads silently. What happens afterwards divides into three cases, and the
division is what this specification is built on.

**Four values never produce a message at all.** `linewidth: -1.0`, `linewidth: .inf`,
`values: [.nan]` and `truncation: .nan` draw a diagram that is simply not the one the file
asked for. This is the worst outcome available and it is the one the type check cannot
reach.

**Ten fail with tephpy's own message**, which already names the family, the option and
the legal set. Nothing is wrong with these messages. What is wrong is *when* they arrive:
under the auto-load cascade (configfile spec §3.2) `import tephpy` succeeds, and the
mistake surfaces at the first draw, in a traceback through tephpy rather than at the file
the user edited. `cursor.fields` is worse again — its check lives in `format_coord`, so it
fires on mouse motion and only ever reaches an interactive user.

**Four fail with matplotlib's message**, which names neither the option nor the file. The
`emphasis` `linestyle` case is the sharpest: the reader is shown a list of a dozen
`'solid'` strings they never wrote.

{issue}`116` describes the third of these classes as unchecked. It is not: `_normalize_emphasis`
validates the style values at draw. The gap is timing, plus the two style keys that
function deliberately leaves to matplotlib.

(domain-spec-2)=
## 2. Decisions

1. **A value whose domain its option rejects is reported and skipped**, the option keeps
   its default, and the rest of the file still applies. This is not a new rule — it is
   configfile spec §5.2's rule, which is in turn configfile spec §2's, reached by a stage
   behind the same `except`.
2. **The check is on the file, not on the object.** `config.isotherms.color = "notacolour"`
   in a user's own script is untouched, and still fails at the draw (§7).
3. **Rules are lifted, not invented.** Where a draw-time check already states a domain, the
   load-time check is that same rule read earlier. One rule in this specification has no
   draw-time counterpart, and it is named as such (§3.3).
4. **Where matplotlib owns the domain, matplotlib is asked.** A colour is a colour because
   `matplotlib.colors.is_color_like` says so, not because tephpy re-derived the rule.
5. **The vocabularies live in one place.** A legal set that the loader and the draw both
   consult is one object, not two that a test keeps in step (§3.2).

(domain-spec-3)=
## 3. Architecture

(domain-spec-3-1)=
### 3.1 A second stage in `coerce`

configfile spec §5.2 put the type check in `coerce`, which `apply` calls once per option
inside a `try`. That `except` clause is the whole of the warn-and-skip behaviour:

```python
try:
    setattr(section, option, coerce(name, option, value, hints[option]))
except TephpyConfigError as exc:
    _warn_from_caller(f"{prefix}ignoring {exc}")
```

The domain check is a second stage inside `coerce`, raising the same exception. **`apply`
does not change.** Nothing about the rule, the warning, the provenance
(configfile spec §5.1) or the message prefix has to be restated, because the new stage
enters through the door the old one already opened.

The stage runs on the *converted* value. YAML's four coercions (configfile spec §3.3)
happen in the type validators, so a domain rule sees a `tuple[float, ...]`, never a list of
`int` — which is what lets `values` express "every member finite" without re-deriving what
a member is.

`_DOMAIN_VALIDATORS` is keyed by **option name**, where `_TYPE_VALIDATORS` is keyed by
annotation. The two tables are shaped by different things: eight annotations cover all 42
options because a type is a coarse property, while a domain is a property of what the
option *means* — `color` and `linewidth` are both scalars and share no domain at all. Ten
names cover the 42 options bar the five `visible` flags.

Keying by name alone is sound only because no two sections give one option name different
domains: `values` is finite numbers whether the family measures °C or g/kg. That is a
property of the current `Config`, not a law, so §5 gates it rather than trusting it.

The exception carries both halves of the message, because for a compound option both vary
with the offending part:

```python
class _DomainError(Exception):
    """A value of the right type that its option still cannot accept."""

    def __init__(self, expects: str, found: str) -> None:
        ...
```

`coerce` formats it into the frame configfile spec §5.2 established, so a domain warning
and a type warning are the same sentence (§4).

(domain-spec-3-2)=
### 3.2 The vocabularies move below the arrow

Three of the legal sets this needs already exist, in `plotting`. `_configfile` cannot reach
them: `plotting.axes` imports `tephpy._config`, which imports `tephpy._configfile`, so an
import the other way is a cycle as well as a reversal of the configfile spec §3
dependency arrow.

They move to `_constants`, the floor both layers already import:

| Name | From | To |
|---|---|---|
| `EDGES` | `plotting.isopleths` | `_constants.EDGES` |
| `_EMPHASIS_STYLE_KEYS` | `plotting.isopleths` | `_constants.EMPHASIS_STYLE_KEYS` |
| the five cursor field names | `plotting.axes._CURSOR_FORMATTERS` keys | `_constants.CURSOR_FIELD_NAMES` |

`plotting` imports them back, so **no draw-time behaviour changes** — the move is a change
of address, and §5 gates that it is only that.

This tidies an existing split rather than creating one. `plotting.axes` already imports
`EDGE_AXIS_TITLES`, `EDGE_TICK_LENGTH`, `EDGE_TICK_PAD` and `EDGE_LABEL_GUTTER_PAD` from
`_constants`, and `EDGES` from `isopleths`, in two adjacent import blocks; afterwards the
edge constants are all in one of them.

The cursor formatter *functions* do not move. Two import MetPy function-locally so that
`import tephpy` stays light, and every one formats a value for display — presentation, not
the vocabulary this section moves below the arrow. So `_CURSOR_FORMATTERS` keeps its home in
`plotting.axes` and §5 asserts its keys are exactly `CURSOR_FIELD_NAMES` — two independently
written tables made to agree, the same self-check configfile spec §3.4 and
configfile spec §5.2 each already carry, for the same reason.

`CURSOR_FIELDS` stays: it is the three-field *default*, a different fact from the five-name
vocabulary, and §5 asserts it is a subset.

`_configfile` gains `matplotlib.colors` and `matplotlib.collections` as imports — the
colour oracle and the linestyle oracle of §3.3. Neither is a new dependency in any sense
that costs anything — **measured:** `from tephpy import _configfile` already leaves both in
`sys.modules`, because importing any tephpy submodule runs the package `__init__`, which
imports `plotting`. matplotlib is also absent from the layering the parent spec describes,
so nothing in configfile spec §3 is bent by naming it.

(domain-spec-3-3)=
### 3.3 The rules

| Option | Options covered | Rule | Lifted from |
|---|---|---|---|
| `color` | 5 | `mcolors.is_color_like` | matplotlib, the call the draw makes |
| `linewidth` | 5 | > 0 and finite | `isopleths._emphasis_number` |
| `alpha` | 5 | 0 ≤ *v* ≤ 1 | `isopleths._emphasis_number` |
| `labels` | 5 | edge names from `EDGES` | `isopleths._normalize_labels` |
| `emphasis` | 5 | see below | `isopleths._normalize_emphasis`, `isopleths._emphasis_number` |
| `values` | 5 | every member finite | `isopleths._normalize_emphasis`'s member rule |
| `interval` | 4 | > 0 and finite | `isopleths.IsoplethFamily._resolve` |
| `extent` | 1 | every corner number finite, both pressures > 0 | `axes.TephigramAxes.set_extent` |
| `fields` | 1 | names from `CURSOR_FIELD_NAMES` | `plotting.axes.format_coord` |
| `truncation` | 1 | finite | **nothing — see below** |
| `visible` | 5 | — | a bool needs no domain |

`emphasis` carries six rules, being the one option that nests a style mapping: each member
value finite; each style key from `EMPHASIS_STYLE_KEYS`; a `linewidth` override > 0 and
finite; an `alpha` override in [0, 1]; a `color` override `is_color_like`; and a
`linestyle` override accepted by `LineCollection.set_linestyle`.

A style *value* is annotated `object` and so reaches this stage unconverted
(configfile spec §5.2), where an option-level value has already been through its type
validator. **Measured:** that makes `emphasis: {850: {linewidth: 2}}` an `int` where
`linewidth: 2` is a `float`, so the numeric rules coerce with `float()` exactly as
`_emphasis_number` does rather than testing for `float` — a rule that tested the type
would refuse a value the draw accepts, which is §5's no-false-positives gate failing.

`values` has no draw-time counterpart, but its rule is not invented either — it is
`_normalize_emphasis`'s member-value rule applied to the other place member values come
from, for the reason that function already records: *a non-finite key would build a full
NaN polyline that the view mask silently drops*.

**`truncation` is the one invented rule**, and it is deliberately the weakest available:
finiteness, no range. A temperature below which moist adiabats are truncated has no
defensible bound that is not a guess, and a validator that refuses a value the draw would
have accepted is a regression wearing a feature's clothes.

For `linestyle` the oracle is `LineCollection.set_linestyle`, because a `LineCollection` is
what the draw sets the style on. **Measured** on matplotlib 3.11.1: it and
`Line2D.set_linestyle` accept and reject the same ten probes and differ only in wording, and
`matplotlib.rcsetup._validate_linestyle` — the obvious third candidate — is private.

**Granularity is the option, not the part.** `emphasis: {850: {...}, 700: {...}}` with one
bad member skips the whole `emphasis` option back to its default. That follows from
configfile spec §5.2 operating per option, but it is not visible from outside, so it is
stated here and documented (§6).

(domain-spec-4)=
## 4. Error handling

One frame serves both stages, so a domain warning reads like a type warning and the
description does the work of locating the fault:

```text
tephpyrc.yaml: ignoring isotherms.color, which expects a colour matplotlib knows, not the string 'notacolour'
tephpyrc.yaml: ignoring isotherms.linewidth, which expects a positive, finite number, not the number -1.0
tephpyrc.yaml: ignoring isobars.interval, which expects a positive, finite number, not the number 0.0
tephpyrc.yaml: ignoring isotherms.values, which expects finite numbers, not the number nan
tephpyrc.yaml: ignoring isotherms.labels, which expects true, false, or edge name(s) from ['bottom', 'top', 'left', 'right'], not the string 'botom'
tephpyrc.yaml: ignoring cursor.fields, which expects field name(s) from ['mixing_ratio', 'pressure', 'temperature', 'theta', 'theta_w'], not the string 'nonsuch'
tephpyrc.yaml: ignoring isotherms.emphasis, which expects member 700 to use style key(s) from ['color', 'linewidth', 'linestyle', 'alpha'], not the string 'lw'
```

A closed vocabulary is listed, because the reader's next action is to pick from it. An open
one is described instead, since no message can enumerate the colours matplotlib knows.

For a compound option the *found* half names the offending part rather than the whole
value. Printing a forty-member `values` list back at someone who mistyped one entry helps
nobody, which is the reasoning configfile spec §5.2 already applied to the 401-digit
number it refuses to echo.

A number too large to convert is refused with the same frame rather than escaping as an
`OverflowError`. The type stage already guards this for a plain number
(configfile spec §5.2); an `emphasis` style value reaches the domain stage unconverted, so
the guard has to be repeated where the conversion actually happens.

**One hint earns its place.** configfile spec §5 warns that `color: #b0b0b0` parses to
null, because YAML consumes the unquoted `#` as a comment. The mirror-image typo is
`color: b0b0b0` — a perfectly good string that is not a colour — and it lands here instead.
The hint is *tested* rather than guessed: if prefixing `#` makes `is_color_like` true, the
warning says so.

```text
tephpyrc.yaml: ignoring isotherms.color, which expects a colour matplotlib knows, not the string 'b0b0b0'; did you mean '#b0b0b0'?
```

The two halves of one YAML trap now warn about each other.

(domain-spec-5)=
## 5. Testing

Extends spec §7 and configfile spec §6.

| Gate | Holds |
|---|---|
| One case per §1 row | The value warns, the option keeps its default, **and a sibling option in the same file still applies** |
| Completeness | Every `(section, option)` in `Config` bar the five `visible` has a domain rule |
| Unambiguous keys | No two sections give one option name a different domain — the §3.1 assumption |
| Vocabulary agreement | `set(_CURSOR_FORMATTERS) == set(CURSOR_FIELD_NAMES)`, and `CURSOR_FIELDS` is a subset |
| Address change only | `plotting` uses the `_constants` objects themselves, not copies of them |
| **No false positives** | Every rule accepts its legitimate lookalikes |
| **Load/draw agreement** | Every accepted value draws; every refused value raises at the draw bar the four that silently do not, and the two tables cover the same options |

The last two carry the weight.

**No false positives.** A validator that refuses a value the draw would have accepted is
worse than no validator, and no other gate here can see it: every test above passes just as
well against a rule that is too strict. So each rule is given values that must load —
`color: C0`, `color: 'xkcd:sky blue'` and `color: '0.5'`, all three of which are colours and
none of which looks like one; `alpha: 0` and `alpha: 1`, the inclusive bounds; `labels:
bottom` as a bare string and `[bottom, left]` as a list; `truncation: -40`; an `emphasis`
style with `linestyle: '--'`.

**Load/draw agreement** is what makes §2's "lifted, not invented" a checked property rather
than a claim in a comment. Each value is set through the Python API — which §2 leaves
unguarded — and the diagram is drawn. Every accepted value must draw. Two tables that agree
today drift apart silently otherwise, and the symptom is a configuration file that is
refused for a diagram that would have drawn.

The other direction is deliberately not symmetric, because §1 measured that it is not. The
gate's own table holds twenty refused values; sixteen raise at the draw and four do not.
Those four — `linewidth: -1.0`, `linewidth: .inf`, `values: [.nan]` and `truncation: .nan` —
are the rows §1 calls the worst outcome available, and they are the reason this work exists:
a rule with no draw-time counterpart on the option that carries it (§3.3). So the gate
asserts what each case actually does, and a further gate asserts that the two tables hold
the same `(section, option)` pairs, because both are hand-written and would otherwise drift.
Pinning the silence is the point. A later change that makes one of those four raise is a
change to the diagram a user already has, and this gate is where it surfaces.

The counts here are the gate's, not §1's. The two sets overlap without matching: the gate
drops `color: 'b0b0b0'`, which has its own named test for the `#` hint, and adds cases §1
does not tabulate.

Each new gate is proved by a mutation that fails it alone.

(domain-spec-6)=
## 6. Documentation

- The configuration how-to gains a paragraph: a value of the right *type* can still be
  refused, it warns and is skipped like any other option-level problem, and a compound
  option is skipped whole (§3.3).
- The options reference page (configfile spec §3.6) publishes the closed vocabularies
  from the same `_constants` objects that enforce them, so the page cannot document a legal
  set the loader rejects.
- configfile spec §5.2 closes by declaring domain validity out of scope and pointing at
  configfile spec §9; that paragraph now points here.
- configfile spec §9's entry for {issue}`116` — the only one there that was not a decision
  against — becomes **Resolved**, carrying the date and the settling pull request that
  docs spec §3.5 requires. The `design: open` label is checked in both directions, so
  removing it from the issue is part of the work.

(domain-spec-7)=
## 7. Non-goals

- **Rejected** (2026-08-12) — **checking values set through the Python API.** A
  `__setattr__` hook on the section dataclasses would catch `config.isotherms.color = "x"`
  and `config.context(...)` too. It is rejected on two counts: a file wants warn-and-skip
  (§2) where an assignment would have to raise, since silently ignoring an assignment is
  worse than the status quo, so one vocabulary would need two reactions; and it would make
  `Config` a class with behaviour where the published shape (configfile spec §3.3) is a
  record. The draw-time checks remain, and remain the answer for this path.
- **Rejected** (2026-08-12) — **improving matplotlib's anonymous draw-time messages.**
  `Invalid RGBA argument: 'notacolour'` and the `'solid'`-list linestyle message (§1) name
  neither option nor file. Wrapping them serves the Python path, which the entry above
  leaves to the draw; it does nothing for a configuration file, which never reaches them
  once §3 lands.
- **Rejected** (2026-08-12) — **applying the good parts of a compound option.** Keeping the
  valid members of an `emphasis` mapping and dropping only the bad one would make the unit
  of a warning smaller than the unit of an option, which is the granularity every other
  option-level rule in configfile spec §5.2 uses. A user who is told `emphasis` was
  ignored can read their own file; one told it was partly applied cannot tell what is in
  force.
- **Rejected** (2026-08-12) — **a range check on `truncation`.** Finiteness only (§3.3).
  Any bound would be invented here rather than lifted from a draw-time rule, and §5's
  no-false-positives gate exists precisely to make invented rules expensive.
