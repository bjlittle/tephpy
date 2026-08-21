# tephpy configuration files — design specification

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. `src/tephpy/_configfile.py` and `src/tephpy/_cli.py` cite it by section —
> `configfile spec §3.2` and the like — so these sections *are* the reasoning behind what the
> code does, and where the two ever diverge it is the specification that gets corrected.
> Read it as current.

- **Date:** 2026-08-07 (originated; maintained since)
- **Status:** living design specification, implemented in {pull}`112`
- **Citation prefix:** `configfile spec §…` — deliberately not `config spec`, which would
  read as a near-duplicate of the parent's own spec §3.5 on `tephpy.config`; the prefix
  matches the module it governs
- **Scope:** a YAML configuration file for `tephpy.config`, its discovery cascade, and a
  `tephpy config` console script that generates and locates it
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) — this
  extends spec §3.5 with a persistence tier beneath `tephpy.config`, and inherits its
  error-handling (spec §6), testing (spec §7) and engineering-standards (spec §8) rules
  unchanged
- **Prior art:** matplotlib's `matplotlibrc` discovery cascade; the XDG Base Directory
  Specification, via [`platformdirs`](https://platformdirs.readthedocs.io/)

(configfile-spec-1)=
## 1. Purpose

`tephpy.config` already lets a user restyle every isopleth family, but only from Python and
only for the lifetime of the process. Anyone with a house style — a colour scheme, a
preferred extent, a cursor readout — retypes it at the top of every script:

```python
tephpy.config.isotherms.color = "purple"
tephpy.config.isobars.linewidth = 0.8
tephpy.config.diagram.extent = ((1000.0, -30.0), (250.0, 35.0))
```

This specification gives that boilerplate a home on disk:

```console
$ tephpy config generate
```

writes a fully-populated, fully-commented template; the user uncomments what they want;
every subsequent `import tephpy` picks it up. Nothing about the existing API changes —
the file is a new *bottom* tier, not a new front door.

(configfile-spec-2)=
## 2. Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Format | **YAML** | Comments are the requirement that decides it. A template whose value lines are commented out, each above its own prose description, is the entire user experience being asked for — and JSON has no comments at all. TOML has comments, but no clean spelling for the float-keyed mappings `emphasis` needs: TOML table keys are strings, so every member value would be quoted (§3.3) |
| Parser | `yaml.safe_load` | Never `yaml.load`: a config file is exactly the untrusted-input case full-loader tag construction is dangerous for |
| Discovery | matplotlibrc-style cascade, **first hit wins** (§3.2) | A convention users of the scientific Python stack already hold. First-hit-wins beats merging: with merge, a value you cannot see in the file you are editing can override the one you can |
| Location | `platformdirs.user_config_dir` | Correct on all three platforms without a per-platform branch. Hand-rolling `~/.config` is wrong on Windows and macOS |
| When loaded | At **`import tephpy`**, once | Matches the precedence contract in spec §3.5: config must already be in place before the first family is created, and families read config at creation |
| Auto-load failure | **Warns**, never raises (§5) | A YAML typo must not make `tephpy` unimportable — that would also take out `tephpy config path`, the tool for diagnosing it |
| Explicit load failure | **Raises** | A direct question deserves a direct answer |
| Unknown *option* | Warn, skip, continue | Forward compatibility: a file written for a later tephpy stays usable |
| Unknown *section* | Raise | A mistyped section silently discards every option under it — too much to lose to a warning |
| Wrong-typed *option value* | Warn, skip, continue (§5.2) | The same reasoning as an unknown option, and the same blast radius: one bad line must not cost the user the rest of the file. `int` is accepted where `float` is declared, because `linewidth: 1` is not a mistake; `bool` is not, because `linewidth: true` is |
| Template defaults | A declarative `CONFIG_DEFAULTS` table in `_constants.py`, gated against `_resolve()` (§3.4) | Rendering the template must not re-enter the plotting path. A second table is only safe with a gate, so the gate is part of the design, not a follow-up |
| Option descriptions | Two tables in `_configfile.py`, gated for completeness (§3.4) | The `#:` comments in `_config.py` are invisible at runtime — they are not docstrings — and unpublishable besides: `_config` is private and autoapi parses statically, so a `#:` comment there reaches no reader at all. `CONFIG_DESCRIPTIONS` carries the one-line summary both renderings show; `CONFIG_DETAILS` carries the longer prose only the reference page has room for (§3.6) |
| Options reference page | Generated from the same tables at build time (§3.6) | Prose can only cross-reference an option that has a target, and the options live in the private `_config`, which autoapi does not document. Generating the page from `CONFIG_DEFAULTS` makes it drift-proof by construction and keeps `_config` private. The alternatives — re-exporting the dataclasses from a public module, or adding a private module to the autoapi list — each publish an implementation detail to buy the same targets (§9) |
| Template line width | Wrapped to 88 columns; value lines never wrapped (§3.6) | 88 is the width ruff holds this repository's own sources to. A commented value line has to survive uncommenting as a single line, so wrapping one would hand a user who uncomments only its first line broken YAML |
| CLI framework | **click**, documented by `sphinx-click` | Zero runtime dependencies of its own. The alternative pairing (typer + sphinxcontrib-typer) adds five transitive runtime dependencies for a two-subcommand CLI |
| Default subcommand | `invoke_without_command=True` + `ctx.invoke(path)` | **Measured:** stock click covers the zero-argument default; `click-default-group` earns its place only for forwarding *arguments* to an unnamed default, which this CLI never needs. Defaulting to `path` rather than `generate` also means a bare `tephpy config` can never write a file |
| Test isolation | `Config.reset()` + a conftest hook (§6) | A shipped `tephpytestrc.yaml` pinning the defaults was considered and rejected: it would route every image baseline through the YAML path, add a third defaults table, and mask accidental default changes that baselines exist to catch |
| `save()` fidelity | Values only — **comments and ordering are lost** | PyYAML cannot round-trip comments. Stated as a limitation rather than designed around; `generate` is the commented artefact, `save` is a data dump |

(configfile-spec-3)=
## 3. Architecture

```
src/tephpy/
  _constants.py    conventions + CONFIG_DEFAULTS (new table)
  _config.py       shape: the dataclasses, context(); + source, reset(), load(), save()
  _configfile.py   NEW — discovery, parse, coerce, validate, render, write
  _cli.py          NEW — click group; argument parsing and output text only
  __init__.py      + the auto-load hook
```

Each module has one job, and the dependency arrows run one way:
(`_cli`, `_config`) → `_configfile` → `_constants`. `_config` depends on `_configfile`
inherently — `load()` and `save()` are methods on `Config` — and `_configfile` needs
`Config` only as an annotation, imported under `TYPE_CHECKING`, so the arrow between them
is one-way and there is no import cycle to work around. Nothing in `_configfile` imports
`plotting`, so loading a config file cannot drag in matplotlib figure machinery, and
`_cli` holds no logic that is unreachable from Python.

(configfile-spec-3-1)=
### 3.1 Two constraints from the existing code

**`source` must not be a dataclass field.** `Config.context()` enumerates its valid
sections with `dataclasses.fields(self)` and raises `TypeError` for anything else. Any
annotated class attribute becomes a field, so `_source: Path | None = None` at class level
would present `source` as an eighth configuration section and break `context()`. It is
therefore set in `__post_init__`, with no class-level annotation, and exposed through a
read-only property.

**The template must not re-enter `_resolve()`.** `_resolve()` is on the path every image
baseline covers. The template generator reads `CONFIG_DEFAULTS` instead, and a gate keeps
the two honest (§3.4).

(configfile-spec-3-2)=
### 3.2 Discovery cascade

First hit wins; discovery stops at the first path that exists.

1. `$TEPHPYRC`, if set
2. `./tephpyrc.yaml` in the current working directory
3. `platformdirs.user_config_dir("tephpy")/tephpyrc.yaml`

If none exists, tephpy runs on its hardwired conventions and `config.source` is `None` —
the no-config case is normal, not an error.

`$TEPHPYRC` is the one entry whose absence is an error: setting it names a specific file,
so pointing it at a missing path is reported rather than falling through to entry 2 —
falling through would silently ignore an explicit instruction. Whether that report is a
warning or an exception follows the one rule in §5, like every other config-file problem:
auto-load warns, explicit load raises.

That rule is expressed once, and the split between the two functions is not symmetric.
`config_paths()` reports the cascade *including* entries that do not exist — `tephpy config
path` marks a missing named file `[absent]`, which is how a user diagnoses a typo in the
variable — so the "absent is an error" half belongs to `discover()` alone. What both need
is the answer to "which path does `$TEPHPYRC` name", and they take it from one helper,
resolved once per call. `discover()` therefore validates and returns the same path: reading
the environment twice, as it once did, left a window in which the file checked for
existence and the file returned were two different files.

(configfile-spec-3-3)=
### 3.3 File format

One top-level mapping per configuration section, mirroring `Config` exactly — seven
sections, 42 options:

| Section | Type | Options |
|---|---|---|
| `isotherms`, `isobars`, `dry_adiabats` | `FamilyOptions` | `color`, `linewidth`, `alpha`, `labels`, `visible`, `emphasis`, `values`, `interval` |
| `moist_adiabats` | `MoistAdiabatOptions` | the above + `truncation` |
| `mixing_ratios` | `MixingRatioOptions` | `LineOptions` + `values` — a values ladder only, so **no** `interval` |
| `diagram` | `DiagramOptions` | `extent` |
| `cursor` | `CursorOptions` | `fields` |

```yaml
isotherms:
  color: dimgrey
  linewidth: 0.5
  alpha: 1.0
  labels: true
  visible: true
  # interval: omitted — the zoom-adaptive ladder selects members
  emphasis:
    0.0: {color: tab:cyan, linewidth: 1.5}

diagram:
  extent: [[900.0, -65.0], [200.0, 5.0]]

cursor:
  fields: [pressure, temperature, theta]
```

Four coercions are needed because YAML's type model does not match the dataclasses':

| YAML gives | Wanted | Note |
|---|---|---|
| `list` | `tuple` | `labels`, `values`, `fields`, `extent` |
| nested `list` | nested `tuple` | `extent` is `((p, T), (p, T))` |
| `int` mapping key | `float` | `emphasis` is keyed by member value; `850` and `850.0` must not be two members |
| scalar `str` | `str` | `labels` accepts a bare edge name as well as a tuple |

`interval` and `values` have **no** default value. Leaving them unset is what enables the
zoom-adaptive selection ladder, so the generated template carries them as commented
prose, never as a number — writing a plausible-looking default there would silently
disable adaptive selection for every user who uncommented it.

(configfile-spec-3-4)=
### 3.4 The declarative tables and their gates

`CONFIG_DEFAULTS` is a declarative `{section: {option: default}}` table in `_constants.py`,
read by the two renderings of §3.6 and by nothing else. It records *effective* defaults —
what the user actually gets — which for most options is the `_constants` convention
`_resolve()` falls back to (`ISOPLETH_LINEWIDTH`, `ISOPLETH_ALPHA`, the per-family
`spec.color`, `visible=True`), and for `interval`/`values` is the absence of one.

Two description tables sit beside it in `_configfile.py`, and they are two registers rather
than two copies. `CONFIG_DESCRIPTIONS` gives every option a one-line summary, keyed per
`(section, option)` so a family can name its own units — hPa for isobars, degrees Celsius
for the temperature families, g/kg for mixing ratios — with `_LINE_DESCRIPTIONS` supplying
once the five options that mean the same thing for every family. `CONFIG_DETAILS` is
sparse: an option earns an entry only where there is behaviour a summary cannot carry, and
the reference page is the only rendering with room to show it.

Being second copies of what the dataclasses declare, the tables need gates:

- **Defaults gate:** for every `(section, option)`, `CONFIG_DEFAULTS` matches what
  `_resolve()` returns with empty kwargs and an empty config.
- **Description gate:** every option in `CONFIG_DEFAULTS` has a description, and no
  description is an orphan.
- **Markup gate:** the descriptions are dual-register — a paragraph of reStructuredText on
  the reference page, a plain-text YAML comment in the template — so they carry exactly one
  construct, the double-backquoted literal, and no `*`, `|`, `--` or trailing underscore. A
  value the reader types is written as a literal, so that it stands out on the page instead
  of blending into the sentence around it; `_unmarked()` strips that one construct for the
  template, and the gate holds both ends — no backquote survives into the template, and the
  vocabulary itself does. Any other markup would reach the template as itself, which is why
  the escape is a single construct and not a general one.
- **Detail gate:** every `CONFIG_DETAILS` key names a real option, so a detail cannot
  outlive the option it describes. There is deliberately no converse: the table is sparse.
- **Coverage gate:** the targets `render_reference()` emits are exactly
  `tephpy.config.<section>.<option>` for every option in `CONFIG_DEFAULTS`. Generating the
  page from the table makes it drift-proof, but not non-empty — this is the gate a renderer
  that silently produced nothing would fail, and the docs build would not.
- **Type-text gate:** no rendered `:type:` carries a bare name that is neither a builtin nor
  dotted (§3.6).
- **Width gate:** no line `render_template()` produces exceeds 88 columns. The literal is
  written in the test rather than imported from the renderer, so raising one width does not
  silently move the other.

Every gate asserts its own parameter list is non-empty, and each gate that enumerates
sections asserts the section set equals `{f.name for f in dataclasses.fields(Config)}` — a
gate whose input silently emptied would otherwise pass by checking nothing. The detail gate
is the exception on the second count, and only there: a sparse table has no section set to
compare.

(configfile-spec-3-5)=
### 3.5 Public API

| Name | Behaviour |
|---|---|
| `config.source` | `Path` the active config came from, or `None`. Read-only property |
| `config.reset()` | Restore the pristine hardwired state; `source` becomes `None` |
| `config.load(path=None)` | Load `path`, or run discovery when omitted. **Raises** on a malformed file, an unknown section, or a missing `$TEPHPYRC`; an unknown *option*, a null value and a wrong-typed value each warn and are skipped, as everywhere else (§2, §5.2) |
| `config.save(path=None)` | Write the options the user actually set (non-`None`) to `path`, or to the user config dir |

`save()` writes values only. Comments and key order in an existing file are **not**
preserved — PyYAML cannot round-trip them. `generate` is the commented artefact; `save` is
a data dump, and the docs say so.

(configfile-spec-3-6)=
### 3.6 Two renderings of one table

The `CONFIG_DEFAULTS`, `CONFIG_DESCRIPTIONS` and `CONFIG_DETAILS` triple of §3.4 is
rendered twice, by two functions in `_configfile.py`:

| Rendering | Output | Shows |
|---|---|---|
| `render_template()` | the commented YAML `tephpy config generate` writes | summary, option, effective default |
| `render_reference()` | reStructuredText for the options reference page | summary, detail, type, effective default, method example |

**Wrapping.** `render_template()` wraps each summary with `textwrap.fill`, at width 88
counting the `  # ` prefix that `initial_indent` and `subsequent_indent` carry. Before this,
eleven lines ran over — the longest 117 columns — because a description that reads
comfortably in the source table overruns once it is commented and indented. Value lines are
deliberately *not* wrapped: `  # emphasis: {}` has to survive uncommenting as a single line,
and a wrapped flow-style value would leave a user who uncomments only its first line with
broken YAML. The widest value line is 44 columns, so the width gate has headroom; should a
future default ever cross 88, the answer is a judgement about that default's rendering, not
automatic wrapping.

**Why the renderer ships.** `render_reference()` lives in the package rather than in the
Sphinx extension that calls it. Its gates are then ordinary tests that import `tephpy`, with
no `sys.path` manipulation and no test that fails to collect from an unpacked sdist.
`docs/src/_ext/tephpy_config_reference.py` reduces to a directive,
`.. tephpy-config-options::`, which calls the function and parses what it returns. Nothing
Sphinx-side is imported by the package.

Its signature is `render_reference(config: Config) -> str`, taking the instance from its
caller exactly as `apply()` does. That is not a stylistic choice: `_config` imports
`_configfile` at module scope (§3), so `_configfile` may hold `Config` only as a
`TYPE_CHECKING` annotation. Passing the instance in is what keeps the arrow one-way; a
function-local import of `_config` would work at runtime and quietly reverse it.

**Targets.** Each option becomes

```rst
.. py:attribute:: tephpy.config.isobars.emphasis
   :type: collections.abc.Mapping[float, collections.abc.Mapping[str, object]] | None
```

so prose can write `` :attr:`tephpy.config.isobars.emphasis` ``. The page declares nothing at
`tephpy.config` itself: `config` is in the package `__all__` and autoapi's `undoc-members`
documents it as a data member of `tephpy`, so a second declaration would be a duplicate
object and, under `--fail-on-warning`, a failed build. The option targets cannot collide —
autoapi parses statically and cannot see the attributes of an instance.

**Types** come from the *evaluated* annotations `_option_hints()` already returns for §5.2's
validators — the same eight shapes §6's accept/reject matrix runs over. Because
`typing.get_type_hints` has resolved them, `str()` alone yields text carrying what a source
annotation would not: `Mapping` arrives as `collections.abc.Mapping[float,
collections.abc.Mapping[str, object]]`, and the private `Extent` alias arrives expanded to
`tuple[tuple[float, float], tuple[float, float]]`. No qualification table is needed, and one
should not be added — it would be a second spelling of what the annotations already say, of
exactly the kind §3.4's gates exist to catch.

What §3.4's type-text gate guards is instead the case `str()` cannot render: an annotation
naming a class stringifies as `<class 'tephpy._config.Thing'>`, which reaches the page as
neither valid type text nor a resolvable target. That gate lives in the test suite rather
than leaning on the build, because `pixi run tests` has no Sphinx and never runs one;
`nitpicky` is the backstop for a name that is well-formed and still unresolvable.
`tuple[float, ...]` needs nothing — `conf.py` already carries `("py:class", "Ellipsis")` for
the existing API pages.

**Defaults** print by one rule, with no per-option prose: the YAML form where there is one,
`{}` for the five `emphasis` mappings, which default to empty, and `unset` for the nine
`values` and `interval` options that have no default at all and whose summary already says
what selects their members instead (§3.3). `render_template()` blanks all fourteen, because
a template cannot show a value on a line meant to be uncommented; the page is under no such
constraint.

**Methods.** `load`, `save`, `reset` and `context` are emitted as `py:method` entries, with
signatures from `inspect.signature` and a summary from each docstring's first line, so the
how-to can cross-reference them instead of writing them as bare literals. They are
deliberately thinner than the docstrings behind them: numpydoc runs as an autodoc hook and
this build has no autodoc, so a full numpydoc body would render its `Parameters` heading as
a document section.

Each also carries one worked example, from `_REFERENCE_EXAMPLES` in `_configfile.py`, emitted
as a `code-block:: python` beneath the summary. A signature and a sentence say what a method
is; they do not say how it is called, and for `context` the difference is the whole point —
`context(**overrides)` gives no hint that the keyword arguments are section names mapped to
`{option: value}` mappings. The gap is widest exactly where the how-to cannot close it:
`context` and `reset` act on the configuration in memory, so `configure-from-a-file` covers
neither, and before this the reference page was the only place in the documentation either
one appeared at all.

The examples are the page's only hand-written content, and so its only content that can
drift. `tests/test_docs_snippets.py` does not reach them — it excludes the reference quadrant
on the grounds that a generated page cannot drift, which is true of everything else here and
not of these. `tests/test_configfile_reference.py` executes each one instead, reaching them
as string literals rather than as extracted page text, with membership pinned against
`_REFERENCE_METHODS` so that a method added without an example fails rather than passing by
absence (§6).

An example names its file. `save()` and `load()` both default to a path outside the working
directory — the user configuration directory — so an example that omitted the argument would,
when executed, read or write the developer's own configuration. The argument is in the prose
because it has to be in the test, and the defaults are left to the summary and the how-to.

(configfile-spec-4)=
## 4. Command-line interface

Console script `tephpy`, declared in `[project.scripts]`, with a `config` group so later
subcommands have somewhere to live.

```console
$ tephpy config                    # same as `tephpy config path`
$ tephpy config path               # print the cascade, marking the active file
$ tephpy config generate           # write the template to the user config dir
$ tephpy config generate -o FILE   # write to FILE ("-" for stdout)
$ tephpy config generate --force   # overwrite an existing file
```

`path` prints every cascade entry in order, marks the one in force, and shows which are
absent — it is the tool a user reaches for when a config file "isn't working", so it must
report the whole search, not just the winner.

`generate` refuses to overwrite without `--force`, exiting 1 and naming the file it would
have clobbered.

(configfile-spec-5)=
## 5. Error handling

Extends spec §6 with two names in `exceptions.py`:

| Name | Base | Raised/warned when |
|---|---|---|
| `TephpyConfigError` | `TephpyError` | Explicit load of a malformed file; unknown section; `$TEPHPYRC` missing |
| `TephpyConfigWarning` | `UserWarning` | Auto-load failure; unknown option; an explicit null value; a wrong-typed value (§5.2) |

The governing rule is **auto-load warns, explicit load raises** (§2). On auto-load failure
the config is left pristine and `source` stays `None`, so a broken file degrades to the
hardwired defaults rather than to a half-applied state.

Warning on an explicit null deserves its rationale, since it looks over-zealous. PyYAML
parses

```yaml
color: #b0b0b0
```

as `None` — the unquoted hex colour is consumed as a comment. **Measured:** `color: #b0b0b0`
→ `{'color': None}`, silently. A null in a config file is far more often this typo than a
deliberate value, and the two are indistinguishable after parsing, so the warning names the
missing quotes as the likely cause.

A file commented out in its entirety parses to `None`, not `{}` — that is the intended way
to start from the generated template, and it is an empty config, not an error.

A *section* whose options are all commented out parses the same way, to `{"isotherms": None}`,
and is likewise an empty section rather than an error. This is the one null that does not
warn, and the distinction is deliberate: the generated template leaves section headers
uncommented so that uncommenting a single option needs no second edit, which makes a null
section the expected state of every section the user has not touched. A null *option value*
stays a warning, because nothing in the template produces one.

(configfile-spec-5-1)=
### 5.1 Warning provenance

A `TephpyConfigWarning` reports a mistake in the *user's* file, so it must point at the
user's own code — the `config.load(...)` call, or the `import tephpy` that ran the
auto-load. A warning that names a file inside `src/tephpy/` reads as a tephpy bug and gives
the user nothing to edit. Every configuration warning therefore routes through one private
helper, `_configfile._warn_from_caller`, which passes `skip_file_prefixes` rather than
`stacklevel`: `warnings.warn` walks outwards to the first frame whose filename does not
start with the tephpy package directory, and blames that ({issue}`107`).

`stacklevel` is the wrong instrument here because it is a fixed count and the depth is not
fixed. `apply` is reached from `Config.load`, from the import-time auto-load, from the
CLI's `_applies`, and directly from the tests — four depths, one number, so any choice is
right for one caller and wrong for the rest. The import path is not merely a different
count: the user's `import tephpy` sits behind importlib's frozen bootstrap frames, so no
integer reaches it at all. `skip_file_prefixes` names the frames to *skip* instead, which
makes attribution follow from where tephpy ends rather than from how deep the call went.

**Measured** on Python 3.12.3 — the declared floor, and `skip_file_prefixes` is a 3.12
addition, so the mechanism is available across the whole supported range:

| Call path | `stacklevel=2` blames | `skip_file_prefixes` blames |
|---|---|---|
| `config.load(path)` → `apply` | `_config.py` | the caller's `load` line |
| `import tephpy` → auto-load → `apply` | `_config.py` | the caller's `import` line |
| `apply` called directly (tests) | the caller | the caller |

Two consequences follow from attribution being depth-independent. Routing all three warning
sites through a shared helper costs nothing — the frame the helper adds is inside the
package and skipped like any other, where the same refactor under `stacklevel` would have
meant re-counting every call site. And the prefix must carry a trailing `os.sep`: matching
is a plain string compare, so a bare package directory would also match a sibling
`tephpy_extras/`.

`_cli._applies` suppresses `TephpyConfigWarning` outright for the duration of its probe,
and that suppression is deliberate rather than incidental. There is no user frame worth
blaming: the call originates in tephpy's own CLI, against a file the user asked to *locate*
rather than to load (§4), and `import tephpy` has already warned over the same cascade.

One consequence for downstream code, which is why it is recorded here: a filter written as
`filterwarnings(..., module="tephpy")` no longer matches, because the warning now belongs
to the user's module. Filtering on `category=TephpyConfigWarning` is unaffected, and is the
axis the documentation points at — the category exists for exactly this.

The auto-load is the one place no filter reaches, and that is deliberate rather than a
limitation of the above. `_autoload_config` installs `filterwarnings("always",
category=TephpyConfigWarning)` for the duration of the load, which sits in front of
everything the user set, so the import-time notice is shown whatever their filters say —
the same mechanism that stops `-W error` turning a typo'd option into a failed import. User
code has not started running by then in any case. Only a later explicit `config.load(...)`
is the user's to filter, so that is the call the how-to shows alongside the filter.

(configfile-spec-5-2)=
### 5.2 Wrong-typed values

A configuration value must match the type its `Config` field declares. `linewidth` is
`float | None`, so `linewidth: thick` is a mistake in the user's file, and one the loader
is in a position to catch. It did not: `coerce` converted the four shapes YAML forces
(§3.3) and passed everything else through untouched ({issue}`105`).

**Measured** against the implementation as of {pull}`112` — one class of mistake, three
different behaviours, none of them the one §2 asks for:

| File | Outcome |
|---|---|
| `isotherms: {linewidth: thick}` | loads silently; `ValueError: could not convert string to float: 'thick'` at the first draw |
| `isotherms: {color: 3}` | loads silently; matplotlib rejects the colour at the first draw |
| `isotherms: {values: notalist}` | loads silently, then iterates the *string* — `could not convert string to float: 'n'` |
| `isotherms: {linewidth: true}` | loads silently and **draws**: matplotlib reads `True` as `1.0` |
| `isotherms: {visible: maybe}` | loads silently and **draws**: a non-empty string is truthy |
| `cursor: {fields: notalist}` | loads silently and **draws**: the cursor readout is quietly wrong |
| `diagram: {extent: 5}` | **raises**, discarding every other option in the file |

The last four rows are the ones that decide the design. Three of them are silent wrongness
— no warning, no traceback, a diagram that is simply not what the file asked for. The
fourth is the mirror image: `coerce` raising escalates an option-level problem into a
file-level one, which the table above never sanctioned. Under auto-load that escalation
means a single mistyped `extent` leaves every other option in the file unapplied.

**The rule.** A value whose type does not match its field is reported and skipped; the
option keeps its default, and the rest of the file still applies. This is not a new
principle — it is the existing one (§2: option-level problems warn and skip, section-level
problems reject the file) applied to a case §2 did not enumerate.

Two adjustments to "matches the declared type", both forced by YAML:

- **`int` is accepted where `float` is declared.** `linewidth: 1` is not a mistake, and
  nothing in the file format tells the user they were supposed to write `1.0`.
- **`bool` is not.** `isinstance(True, int)` is `True` in Python, so a boolean reaches a
  numeric field unless it is excluded explicitly — which is precisely how `linewidth: true`
  came to draw a 1 pt line. YAML 1.1 widens the exposure: PyYAML reads `yes`, `no`, `on`
  and `off` as booleans too.

**Implementation.** The expected types are not written out a second time; they are read
from the annotations that already exist:

- The expected type reaches `coerce` as an argument. `apply` resolves it from the section
  it already holds, through `_option_hints`, a thin wrapper on `typing.get_type_hints`
  which resolves cleanly through the `from __future__ import annotations` in `_config.py`.
  A module-level `{(section, option): annotation}` table is not available: `_configfile`
  cannot import `_config` at runtime without reversing the §3 dependency arrow, and a
  lazily-built one would leave a direct `coerce` caller checking against an empty table.
  **Measured:** 42 options over 8 distinct annotation shapes.
- `_TYPE_VALIDATORS` — one `(description, converter)` per distinct shape, so eight entries
  cover all 42 options. Each converter both checks and converts, which makes it the natural
  home for the §3.3 coercions rather than a second pass over the same value.
- `coerce` consults them and raises `TephpyConfigError` on a mismatch; `apply` catches it,
  warns through `_warn_from_caller` (§5.1), and moves to the next option. That single
  `except` is what delivers the rule and what ends the escalation.
- A completeness gate asserts every `(section, option)` in `Config` has a validator, and
  asserts its own option set, built from `dataclasses.fields`, is non-empty and the same
  size as the 42 that `CONFIG_DEFAULTS` holds — two independently written tables made to
  agree, which is the same self-check the two gates in §3.4 carry, for the same reason.

**The message** names the file, the option, what was expected and what was found, in the
vocabulary of the file the user is editing rather than of the annotation behind it — the
reader writes YAML and has never seen `float`:

```text
/home/you/work/tephpyrc.yaml: ignoring isotherms.linewidth, which expects a number, not the string 'thick'
/home/you/work/tephpyrc.yaml: ignoring isotherms.linewidth, which expects a number, not the boolean true
/home/you/work/tephpyrc.yaml: ignoring isotherms.values, which expects a list of numbers, not the string 'notalist'
/home/you/work/tephpyrc.yaml: ignoring diagram.extent, which expects two [pressure, temperature] corners, not [1, 2]
```

**One value fails at the conversion rather than at the check.** An integer of 309 or more
digits is a number, so it passes the check; `float()` then raises `OverflowError`, which is
neither `_MismatchError` nor `TephpyConfigError` and so is caught by nothing between there
and `import tephpy` (§2). `_as_number` turns it into the same warn-and-skip as any other
mismatch. It carries the one message that describes what was found instead of naming it —
printing 401 digits back at the reader helps nobody, and "not the number" would be a lie
about why it was refused:

```text
/home/you/work/tephpyrc.yaml: ignoring isotherms.linewidth, which expects a number, not a number that large; the largest tephpy can hold is about 1.8e308
```

The path prefix is new to option-level warnings, and is extended to the other two — the
unknown option and the null value — for one reason: with three cascade entries (§3.2), a
warning that names `isotherms.linewidth` but no file does not say which file to edit. The
file-level errors lead with the path too — `apply`'s two section-level raises gained it
here — so option-level and file-level messages read the same way.

**A limit, stated rather than designed around.** `emphasis` is
`Mapping[float, Mapping[str, object]]`: the member values and the style keys are typed, the
style *values* are `object`. So `emphasis: {0.0: {linewidth: thick}}` still reaches the
draw. Checking it needs to know which style keys exist and what each accepts, which is the
knowledge a domain check needs — and domain validity is out of scope here. This section
covers types only. Whether `notacolour` names a colour, or `nonsuch` a cursor field, is a
separate question, answered by domain spec §3: a second stage behind this one, which reads
the converted value and so reaches the `emphasis` style values this section cannot (§9).

**Rejected: pydantic.** A `TypeAdapter` per annotation — `Strict()` on the scalar leaves,
lax on the containers so YAML's lists still become tuples — was measured against the rule
above and agreed with it on all 27 cases, including `linewidth: 1` accepted,
`linewidth: true` rejected, and all four §3.3 coercions performed. It is rejected on cost
rather than on fit: a core runtime dependency and its compiled core, to replace eight small
functions, in a package whose dependency table (§7) is deliberately short. The measurement
is recorded because it sets the bar the hand-written validators are held to.

(configfile-spec-6)=
## 6. Testing

Extends spec §7.

**Isolation.** `pyproject.toml` sets `filterwarnings = ["error"]`, and the auto-load runs at
*import* — so a developer's own `~/.config/tephpy/tephpyrc.yaml` would feed every
pytest-mpl comparison, and one unknown key in it would become a collection error. The root
`tests/conftest.py` closes both:

```python
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import tephpy

tephpy.config.reset()
```

plus an autouse `reset()` per test, so a test that mutates config cannot leak into a later
baseline comparison. This depends on no new environment variable and on no assumption about
when pytest installs its warning filters.

**Coverage.** The genuinely new seam is `YAML → Config`; `Config → artists` is already
covered — `tests/plotting/test_isopleths.py` parametrises `config.context(...)` over
sections and options and asserts the resulting artist properties. Tests are placed
accordingly:

| Test | Proves |
|---|---|
| `tests/fixtures/tephpyrc-complete.yaml` + loader equality | Every option survives the YAML round trip |
| Fixture completeness gate | The fixture sets **every** option in `CONFIG_DEFAULTS`, each to a non-default value |
| Inline `tmp_path` documents | Each §3.3 coercion and each §5 trap, one case apiece |
| Subprocess import test | `$TEPHPYRC` → `import tephpy` → `config.source` and a loaded value |
| `CliRunner` cases | `path`, `generate`, clobber refusal, `-o -` |
| Accept/reject matrix over the eight annotation shapes | Each declared type accepts what it should and rejects what it should, `linewidth: 1` and `linewidth: true` among them (§5.2) |
| Validator completeness gate | Every option in `Config` has a validator; the gate's own option set is non-empty and equals `dataclasses.fields` |
| One wrong-typed option beside a good one, in one file | The warned option keeps its default **and** the good one applies — the case that makes "the rest of the file still applies" non-vacuous |
| `discover()` under a changing environment | The path validated is the path returned: a stub whose second read of `$TEPHPYRC` differs from its first (§3.2) |
| Detail, coverage, type-text and width gates (§3.4) | A detail cannot outlive its option; the reference page names every option and no others; no `:type:` reaches the docs unqualified; no generated template line exceeds 88 columns |
| Method examples executed, one per `_REFERENCE_METHODS` entry (§3.6) | Every example on the reference page runs, against the live API rather than a transcript of it, and a method cannot be listed without one |

Three notes on why these are shaped this way. The fixture is *complete* rather than
representative because only completeness proves a newly added option is expressible in
YAML; a representative fixture would let a new option with an unparsable type land
unnoticed. It carries **non-default** values throughout because a fixture pinned to the
defaults renders identically to loading nothing at all, and would pass whether or not the
loader ran. And the auto-load needs a *subprocess* because `tephpy` is already imported by
the time any in-process test runs — that seam is invisible from inside the suite.

No new image baseline. An end-to-end image test would re-prove the covered half of the
chain, and report a loader bug as dozens of differing comparisons rather than one precise
failure. It is also incompatible with the complete fixture, which necessarily sets
`visible: false` and renders almost nothing.

The fixture lives under `tests/`, which the sdist ships, so it is available when the suite
runs from an unpacked sdist.

Every new test is mutation-proved: revert the behaviour it guards and confirm that test,
and only that test, fails.

(configfile-spec-7)=
## 7. Dependencies

| Package | Tier | Floor | Note |
|---|---|---|---|
| `pyyaml` | core | `>=6.0.1` | Until declared here, in the pixi environment only via pre-commit and sphinx-autoapi, and **absent** from a core install. Floored one patch above `6.0`, whose sdist has no cp312 wheel and fails to build |
| `click` | core | `>=8.1` | Until declared here, present only via towncrier and jupyter-cache, and **absent** from a core install |
| `platformdirs` | core | `>=4.0` | Reachable only as a transitive of pint; declared rather than inherited |
| `sphinx-click` | docs | `>=6.0` | Documents the CLI in the reference guide |

The first two matter more than a dependency table usually does. Because both are already in
the development environment, omitting the declaration leaves `pixi run tests` green and CI
green, while a user who runs `pip install tephpy` gets `ImportError: No module named 'yaml'`
at import. The failure is invisible to every check the repository runs.

A floor is chosen as "known to contain the APIs used", and nothing the repository runs tests
that choice: every pixi task passes `--frozen`, so what CI resolves is the lockfile's pin —
click 8.4.2 against a declared floor of `>=8.1`, when this was written — and a floor set too
low fails for one person only, the user who happens to resolve that version. Each
floor above is therefore resolved by hand instead, once: `pyyaml`, `click` and
`platformdirs` as they were declared (PR {pull}`112`), `sphinx-click` afterwards
(2026-08-13, {issue}`109`). Standing rather than closed, then — a resolve by hand settles the
floors in front of it and nothing after. What would close it is specified in the dependency
floors specification, which takes this section's gap as its purpose (floors spec §1) and this
section's `sphinx-click` result as the reason its verdicts are reported as evidence rather
than as answers (floors spec §3.5).

`sphinx-click` was resolved as two scratch pixi environments carrying the rest of the
documentation dependencies and differing in that one package alone — one pinned to
`==6.0.0`, the other left to resolve. Both build the documentation under
`--fail-on-warning`, with the gates of docs spec §3.6 and docs spec §3.7 green, and their
output differs on a single page: from 6.2.0 each command's usage block carries a `Usage`
rubric, which 6.0.0 and 6.1.0 omit. The floor stands at `>=6.0`. What the reference page
asks of the directive — `:prog:` and `:nested: full` (§8) — is present there, the rubric is
presentation added upstream rather than an API tephpy calls, and the published site is
built from the lockfile rather than from the floor. The floor is declared twice — once for
pixi and once for pip — so the second was checked too: 6.0.0 ships a wheel on PyPI
declaring `requires-python >=3.8`, which covers every Python tephpy supports.

(configfile-spec-8)=
## 8. Documentation

- A Diátaxis **how-to** for configuring tephpy from a file, covering the cascade, the
  quoting trap (§5), what happens to a wrong-typed value (§5.2), and what `save()` does not
  preserve (§3.5).
- A **reference** page for the CLI, generated by `sphinx-click`.
- An **options reference** page generated from `CONFIG_DEFAULTS` at build time (§3.6),
  carrying a target per option so the how-to and any later prose can cross-reference them
  with a Sphinx role instead of a bare literal, and a worked example per method — the only
  documentation `reset` and `context` have.
- `TephpyConfigError` and `TephpyConfigWarning` picked up by autoapi with the rest of
  `exceptions`.
- `feature` and `dependency` changelog fragments from the implementing pull request — the
  new dependencies (§7) are user-visible and belong in the changelog in their own right.

(configfile-spec-9)=
## 9. Non-goals

This is the section that carries this specification's unsettled items, so its entries take
the status tags and issue pointers docs spec §3.5 requires. Most are settled against: a
non-goal is a decision, not an omission.

- **Rejected** (2026-08-07) — **merging across cascade entries.** First hit wins (§2).
- **Rejected** (2026-08-07) — **per-figure or per-axes config files.** `tephpy.config` is
  process-wide; a file changes its starting values, not its scope.
- **Rejected** (2026-08-07) — **comment-preserving round trips.** Would mean `ruamel.yaml`
  in the core dependency tree to serve `save()` alone (§3.5).
- **Rejected** (2026-08-07) — **environment-variable overrides per option.** `$TEPHPYRC`
  selects a file; it does not become a parallel `TEPHPY_ISOTHERMS_COLOR` namespace.
- **Rejected** (2026-08-07) — **validating a config file without loading it.**
  `tephpy config path` reports discovery; a `--check` mode can follow if asked for.
- **Rejected** (2026-08-11) — **making `Config` and its section dataclasses public.** It
  would buy the same cross-reference targets as §3.6 by publishing a shape §3.3 already
  documents as a file format, and would commit the project to that shape as API.
- **Rejected** (2026-08-11) — **full method documentation on the options reference page.**
  The `py:method` entries carry a signature, one sentence and one example (§3.6). Rendering
  the numpydoc bodies would mean enabling `sphinx.ext.autodoc` alongside autoapi purely to
  get the hook that processes them — a second API renderer in the build, for four methods.
  What this rejects is that hook and the `Parameters`, `Returns` and `Raises` sections it
  formats, not hand-written prose: the worked example §3.6 adds is a literal block in the
  generated reStructuredText and needs no autodoc, so it does not reopen this ({issue}`124`).
- **Rejected** (2026-08-12) — **a worked example for each of the 42 options.** Twenty-five are
  scalars, where the example restates the `Default:` line immediately above it. The seventeen
  that have a shape worth showing are served by `CONFIG_DETAILS` (§3.4), whose `emphasis`
  prose is unit-neutral by design — `LineOptions` backs isobars in hPa and mixing ratios in
  g/kg as well as the temperature families, so a concrete example would have to be written
  once per family or be wrong for four of them ({issue}`124`).
- **Rejected** (2026-08-11) — **a matching reference page for `_constants.py`.** The options
  page publishes the attributes of `tephpy.config`, an object already in `__all__`; it does
  not publish a private module, so it sets no precedent for the 135 `#:`-documented
  constants. Those are the conventions a configuration file exists to override, reachable by
  a user as the `tephpy.config` options that override them — not as names to import.
- **Resolved** (2026-08-12, PR {pull}`126`) — **domain validation of a value that has the
  right type.** §5.2 checks a value against the type its field declares and stops there:
  `color: notacolour` is a string, so it loaded, and matplotlib rejected it at the first
  draw. Answering it properly meant a per-option vocabulary — the colours, the edge names,
  the cursor fields, the `emphasis` style keys — which is why it was a larger piece of work
  than the type check it sits behind. Specified as domain spec §1–domain spec §7 and settled by that
  work ({issue}`116`). This was the one entry here that was not a decision against, and the
  only one the docs spec §3.5 contract required an issue for.
