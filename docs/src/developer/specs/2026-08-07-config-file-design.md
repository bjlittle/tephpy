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
| Template defaults | A declarative `CONFIG_DEFAULTS` table in `_constants.py`, gated against `_resolve()` (§3.4) | Rendering the template must not re-enter the plotting path. A second table is only safe with a gate, so the gate is part of the design, not a follow-up |
| Option descriptions | A table in `_configfile.py`, gated for completeness (§3.4) | The `#:` comments in `_config.py` are invisible at runtime — they are not docstrings |
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
  extent: [[1050.0, -40.0], [200.0, 40.0]]

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
### 3.4 `CONFIG_DEFAULTS` and the two gates

`CONFIG_DEFAULTS` is a declarative `{section: {option: default}}` table in `_constants.py`,
read only by the template generator. It records *effective* defaults — what the user
actually gets — which for most options is the `_constants` convention `_resolve()` falls
back to (`ISOPLETH_LINEWIDTH`, `ISOPLETH_ALPHA`, the per-family `spec.color`,
`visible=True`), and for `interval`/`values` is the absence of one.

Being a second copy, it needs a gate, and so does the description table:

- **Defaults gate:** for every `(section, option)`, `CONFIG_DEFAULTS` matches what
  `_resolve()` returns with empty kwargs and an empty config.
- **Description gate:** every option in `CONFIG_DEFAULTS` has a description, and no
  description is an orphan.

Both gates assert their own parameter list is non-empty *and* that the section set equals
`{f.name for f in dataclasses.fields(Config)}` — a gate whose input silently emptied would
otherwise pass by checking nothing.

(configfile-spec-3-5)=
### 3.5 Public API

| Name | Behaviour |
|---|---|
| `config.source` | `Path` the active config came from, or `None`. Read-only property |
| `config.reset()` | Restore the pristine hardwired state; `source` becomes `None` |
| `config.load(path=None)` | Load `path`, or run discovery when omitted. **Raises** on a malformed file, an unknown section, or a missing `$TEPHPYRC`; an unknown *option* still warns and is skipped, as everywhere else (§2) |
| `config.save(path=None)` | Write the options the user actually set (non-`None`) to `path`, or to the user config dir |

`save()` writes values only. Comments and key order in an existing file are **not**
preserved — PyYAML cannot round-trip them. `generate` is the commented artefact; `save` is
a data dump, and the docs say so.

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
| `TephpyConfigWarning` | `UserWarning` | Auto-load failure; unknown option; an explicit null value |

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
| `pyyaml` | core | `>=6.0.1` | Present in the pixi environment only via pre-commit and sphinx-autoapi — **absent** from a core install today. Floored one patch above `6.0`, whose sdist has no cp312 wheel and fails to build |
| `click` | core | `>=8.1` | Present only via towncrier and jupyter-cache — **absent** from a core install today |
| `platformdirs` | core | `>=4.0` | Reachable today only as a transitive of pint; declared rather than inherited |
| `sphinx-click` | docs | `>=6.0` | Documents the CLI in the reference guide |

The first two matter more than a dependency table usually does. Because both are already in
the development environment, omitting the declaration leaves `pixi run tests` green and CI
green, while a user who runs `pip install tephpy` gets `ImportError: No module named 'yaml'`
at import. The failure is invisible to every check the repository runs.

The floors are chosen as "known to contain the APIs used", not verified — CI resolves
`--frozen` everywhere and would test 8.4.2 against a declared floor of 8.1. The
implementation plan carries an explicit one-off resolve of the declared minimums.

(configfile-spec-8)=
## 8. Documentation

- A Diátaxis **how-to** for configuring tephpy from a file, covering the cascade, the
  quoting trap (§5), and what `save()` does not preserve (§3.5).
- A **reference** page generated by `sphinx-click`.
- `TephpyConfigError` and `TephpyConfigWarning` picked up by autoapi with the rest of
  `exceptions`.
- `feature` and `dependency` changelog fragments from the implementing pull request — the
  new dependencies (§7) are user-visible and belong in the changelog in their own right.

(configfile-spec-9)=
## 9. Non-goals

- **Merging across cascade entries.** First hit wins (§2).
- **Per-figure or per-axes config files.** `tephpy.config` is process-wide; a file changes
  its starting values, not its scope.
- **Comment-preserving round trips.** Would mean `ruamel.yaml` in the core dependency tree
  to serve `save()` alone (§3.5).
- **Environment-variable overrides per option.** `$TEPHPYRC` selects a file; it does not
  become a parallel `TEPHPY_ISOTHERMS_COLOR` namespace.
- **Validating a config file without loading it.** `tephpy config path` reports discovery;
  a `--check` mode can follow if asked for.
