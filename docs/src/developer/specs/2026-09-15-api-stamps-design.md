# tephpy API version stamps — design specification

```{readingtime}
```

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. The gate and the release runbook cite it by section — `stamps spec §3.2` and
> the like — so these sections *are* the reasoning behind what they do, and where the two
> ever diverge it is the specification that gets corrected. Read it as current.

- **Date:** 2026-09-15 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `stamps spec §…`
- **Scope:** the rule that every published API object records the version it arrived in,
  the committed snapshot that lets the rule survive a release, and the two release-runbook
  steps that keep the snapshot true
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) —
  `spec §10`'s release execution, which this makes safe to carry out
- **Sibling specs:**
  [`2026-08-03-published-specs-design.md`](2026-08-03-published-specs-design.md) —
  `docs spec §3.5`'s status vocabulary, which §8 below uses

(stamps-spec-1)=
## 1. Purpose

**The version gate turns `main` red the moment a release is merged back into it.**

{issue}`227` gave every published object a numpydoc `Notes` section carrying
`.. versionadded::`, and {pull}`229` built the gate that enforces it:
`.github/scripts/check_api_docstrings.py`, run by `tests/test_api_docstrings.py`. Its rule is
*phase 1*: every object must cite exactly the **target**, the base version the next tag
will carry, derived by `setuptools_scm` under `semver-pep440-release-branch`. That is exact
and total while nothing has been released, because nothing can predate the first release.
{issue}`227` recorded that it would stop being right once a tag existed, and deferred the
fix to a *phase 2* that could not start without one.

Measured on 2026-09-15, in a throwaway clone of `main` at `1ffb603`, the moment is the
**first merge-back of any tag, a release candidate included** — not the release itself:

| repository state | `setuptools_scm` | target | `tests/test_api_docstrings.py` |
|---|---|---|---|
| `main`, no tag | `0.1.0.dev223` | `0.1.0` | 52 passed |
| tag `v0.1.0rc1` on `v0.1.x` | `0.1.0rc1` | `0.1.0` | 52 passed |
| one commit past it on `v0.1.x` | `0.1.0rc2.dev1` | `0.1.0` | 52 passed |
| `main` after merging `v0.1.x` back | `0.2.0.dev2` | `0.2.0` | **3 failed** |
| tag `v0.1.0` on `v0.1.x` | `0.1.0` | `0.1.0` | 52 passed |
| `main` after merging that back, one commit on | `0.2.0.dev4` | `0.2.0` | **3 failed** |

The three failures are `test_target_version_uses_the_project_version_scheme`
(`'0.2.0' == '0.1.0'`), `test_every_published_docstring_is_stamped` (all 94 objects:
*versionadded cites 0.1.0, expected 0.2.0*), and `test_the_gate_reports_rather_than_raises`
(`main()` returns 1). Every one of the 94 stamps is correct; the rule is what stops being.
The release runbook's rehearsal merges a release candidate back, so without this
specification the first rehearsal of the first release would have left `main` red.

(stamps-spec-2)=
## 2. Decisions

1. **Released objects are recorded in a committed snapshot, written at the release
   freeze.** A plain-text file names every published object and the version it cites. An
   object the snapshot records keeps that version; an object it does not record cites the
   target. {issue}`227` proposed the shape; §3.2 settles the file.
2. **An object the snapshot records but the package no longer publishes is ignored** until
   the next freeze rewrites the file. The snapshot means *what the last release published*,
   and a later removal does not make that wrong. A renamed object is a new name to a
   reader, so it cites the target.
3. **A release branch is merged back through a dedicated branch named without a version.**
   §3.3 gives the reason: it is the only route by which a new object merged into `main`
   during a release can be re-stamped without turning `main` red.
4. **No snapshot file means phase 1.** Before the first freeze every published object is
   absent from a snapshot that does not exist, so every object cites the target — exactly
   the rule the gate enforces today. The change can therefore land before any tag, and the
   first release writes the first snapshot.

(stamps-spec-3)=
## 3. Architecture

(stamps-spec-3-1)=
### 3.1 The rule

For each published object, in the sense `docs-style.rst`'s *API Version Stamps* section
defines:

| the object | the rule |
|---|---|
| carries no `versionadded` in its `Notes` section | fails — unchanged from phase 1 |
| is recorded in the snapshot | must cite **exactly the version the snapshot records** |
| is not recorded in the snapshot | must cite **the target** |
| is recorded, but no longer published | ignored |

**The snapshot half needs no derived version.** It compares a docstring against a
committed file, so it keeps running where `target_version()` refuses to derive one — a
shallow clone, or a `git archive` export with no tag to measure from ({issue}`310`). There,
as in phase 1, an object absent from the snapshot is checked for presence only.

**Why this cannot deadlock the way {pull}`317`'s gate did.** That gate compared a
tag-derived value against file contents that could not change in the same commit, and so
had a window in which no tree satisfied it. Here, the snapshot half depends on a file and
never on a derived value. The target half applies only to objects absent from the
snapshot, whose stamps can be edited in the same change that moves the target — with the
one exception §3.3 exists to handle.

**What each half catches** — the two failure modes {issue}`227`'s phase-2 table named:

- an object recorded at `0.1.0` and re-stamped `0.2.0`: *retroactive rewriting of history*,
  caught by the snapshot half;
- a new function stamped `0.1.0` because the function above it says `0.1.0`: *the lazy
  copy*, and the likelier error, caught by the target half. A one-sided `cited <= target`
  would let it through (§5).

(stamps-spec-3-2)=
### 3.2 The snapshot

**`.github/api-surface.txt`.** One line per published object, sorted by dotted name, three
tab-separated fields — the dotted name, its role (`module`, `class`, `exception`,
`function`, `method` or `property`), and the version its docstring cites — under a header
comment saying that the gate writes the file and it is not edited by hand. Plain text so
that a public-API change reads as a diff in review; beside the gate, and so already outside
the sdist, because `MANIFEST.in` prunes `.github`.

**Written by the gate:** `python .github/scripts/check_api_docstrings.py --write-snapshot`.
It runs the rule first and **refuses to write**, leaving any existing file untouched, when
any published object fails, or when no target can be derived. A snapshot therefore never
records a stamp the rule did not accept.

**Read defensively.** A line the reader cannot parse fails the gate rather than being
skipped: a snapshot read as empty would silently return the rule to phase 1.

(stamps-spec-3-3)=
### 3.3 The release flow

Two steps of `docs/src/developer/release.rst` change.

**Step 4, *Fill in the release metadata*, writes the snapshot.** Beside `CITATION.cff`, the
release pull request runs `--write-snapshot` and commits `.github/api-surface.txt`, so the
snapshot is on the commit that gets tagged. Folding it into step 4 rather than adding a step
keeps the runbook's numbering, and the references to it, valid. A patch release re-enters at
the freeze and so rewrites the snapshot too; an object a patch adds keeps its patch version,
`0.1.1` say, on `main` after the merge-back.

**Step 10, the merge-back, goes through its own branch.** The problem is an object merged
into `main` after `vA.B.x` was cut and before its first tag comes back. Before the merge-back
`main`'s target is `0.1.0`, so the object must cite `0.1.0`; after it the target is `0.2.0`,
and the object — which did not ship in `0.1.0` — must cite `0.2.0`. The target moves in the
merge commit itself. A pull request from `vA.B.x` cannot re-stamp the object, because the
release branch does not contain it; re-stamping on `main` first turns `main` red until the
merge; and `main`'s protection requires the test, docs, build, pre-commit.ci, changelog and
Read the Docs checks to pass, so a red merge-back cannot land without an administrator's
bypass. The route that works:

1. create `merge-back` from `vA.B.x`, and merge `main` into it locally;
2. run the tests, and re-stamp any object the gate names with the version it asks for;
3. push, and open the pull request from `merge-back` into `main` — labelled
   `skip-changelog` and merged with a merge commit, as step 10 already requires;
4. once it merges, delete `merge-back` and keep `vA.B.x`.

The tag stays an ancestor of `main`, the release branch is not touched, and the failure
appears in a pull request's checks, where it can be fixed. The runbook's note *Two gates will
move at the first tag* is replaced: it named the hard-coded version assertion and the phase-1
rule, and this specification retires both.

(stamps-spec-3-4)=
### 3.4 Why the branch carries no version

`semver-pep440-release-branch` reads a branch name that contains a version as a release
branch. Measured 2026-09-15 in a throwaway clone — `v0.1.x` tagged `v0.1.0rc1` after a
commit of its own, then one new commit on `main`:

| where | `setuptools_scm` | target |
|---|---|---|
| `main` before the merge-back | `0.1.0.dev224` | `0.1.0` |
| branch `merge-back-v0.1.x`, `main` merged in | `0.1.0rc2.dev2` | `0.1.0` |
| branch `merge-back/0.1`, `main` merged in | `0.1.0rc2.dev2` | `0.1.0` |
| branch `merge-back`, `main` merged in | `0.2.0.dev2` | `0.2.0` |
| branch `merge-back-release`, `main` merged in | `0.2.0.dev2` | `0.2.0` |
| a detached merge commit — what pull-request CI checks out | `0.2.0.dev2` | `0.2.0` |
| `main` after the pull request's merge commit | `0.2.0.dev3` | `0.2.0` |

On a versioned name a local run targets the release line and **disagrees with the pull
request's CI**: a correct re-stamp to `0.2.0` fails locally and passes in CI. A versionless
name agrees with both. Pull-request CI is right either way, so a versioned name is not a
deadlock — it is a false failure on release day, which is reason enough.

**A trap for whoever measures this again.** Tagging `v0.1.x` and merging it straight back,
with no commit of its own on the branch, makes no merge commit at all: `main` is left on the
tagged commit, derives `0.1.0rc1`, and passes. Put a commit on the release branch first.

(stamps-spec-4)=
## 4. Companion changes

- `.github/scripts/check_api_docstrings.py` — `check_versionadded` takes the snapshot;
  `--write-snapshot`; a reader for the snapshot that fails on a line it cannot parse; a
  failure message that, for an object the snapshot records, names the recorded version
  rather than the target.
- `tests/test_api_docstrings.py` — §6's tests;
  `test_target_version_uses_the_project_version_scheme` stops asserting `"0.1.0"` and
  asserts a three-component release, which is what it exists to protect: without the
  scheme read from `pyproject.toml`, the target comes back `0.1`.
- `docs/src/developer/docs-style.rst` — *API Version Stamps* gains the contributor's half:
  a new object cites the version the gate names; an object from an earlier release keeps
  its stamp, and released API is never re-stamped; the release process writes the snapshot,
  a contributor does not.
- `docs/src/developer/release.rst` — steps 4 and 10 as §3.3 describes, and the note it
  replaces.

(stamps-spec-5)=
## 5. Alternatives considered

- **Read the previous release from its tag at check time.** No file to maintain, but it
  needs the tags present — a shallow clone and pre-commit.ci's checkout lack them — and
  enumerating the API as it stood at the tag means importing an old tree of the package.
  Rejected as fragile where the committed snapshot is not.
- **A one-sided rule, `cited <= target`, and no snapshot.** It can never deadlock, and it
  catches a stamp naming a future version. But it passes the lazy copy, which
  {issue}`227`'s phase-2 table identifies as the default mistake, from the first release
  onwards. Rejected for missing the likelier error.
- **Forbid new public API on `main` between cutting `vA.B.x` and merging its first tag
  back.** Nothing would enforce it, and when it is broken there is no clean fix — §3.3's
  reasons. Rejected for relying on memory.
- **Merge a red merge-back and re-stamp afterwards.** Possible only by bypassing required
  checks, and it leaves `main` red in between — the release-day surprise {pull}`317` was.
  Rejected.

(stamps-spec-6)=
## 6. Testing

| what lands | what holds it |
|---|---|
| each row of §3.1's table | a unit test per row, over fixture objects: recorded and matching with a different target passes; recorded and re-stamped fails naming the recorded version; absent and citing an old version fails naming the target; absent with no target checks presence; recorded with no target stays exact; recorded but unpublished is ignored |
| no snapshot means phase 1 | the existing phase-1 tests, unchanged |
| the snapshot file | a write-then-read round trip, sorted, with the header; `--write-snapshot` refusing on a violation and on an underived target, writing nothing; a malformed line failing the reader |
| §1's and §3.4's measured tables | one integration test building a git repository in a temporary directory from the project's committed `[tool.setuptools_scm]` settings: the rc tag and the release branch target `0.1.0`, `main` after the merge-back and a `merge-back` branch target `0.2.0`, a `merge-back-v0.1.x` branch targets `0.1.0`. Guarded on the checkout's `.git`, as `tests/test_floors.py` requires of every test that runs `git`, and passing identity and `commit.gpgsign=false` per command, so it runs on a machine with no git configuration |
| the policy is written down | `test_the_policy_is_written_down`, which today passes on any mention of `versionadded`, also requires `docs-style.rst` to name `.github/api-surface.txt` and `--write-snapshot` |
| the runbook's command exists | `release.rst` names `--write-snapshot` and the `merge-back` branch, and the gate's argument parser accepts `--write-snapshot` |

Each rule is proven by mutation in the plan: deleting the snapshot half fails the
re-stamp test; weakening the target half to `<=` fails the lazy-copy test; skipping a
malformed line fails its test; renaming the flag fails the runbook check.

(stamps-spec-7)=
## 7. Scope

**In scope.** The rule and the snapshot of §3.1 and §3.2, `--write-snapshot`, the tests of
§6, the style guide's policy, and the runbook's steps 4 and 10 with the note they replace.

**Out of scope.** Writing the first real snapshot, which happens at the release
candidate's step 4 on `v0.1.x` and is the first time the flow runs for real. {issue}`224`'s
`Raises` rule, which shares the script and is untouched. Migrating to Sphinx 9's
`version-added` spelling (§8).

(stamps-spec-8)=
## 8. Open items

Tagged per docs spec §3.5.

- **Deferred** ({issue}`227`) — migrating `versionadded` to `version-added` once the
  documentation's Sphinx floor passes 9.0, where the hyphenated spelling first exists, and
  suggesting upstream that numpydoc's `DIRECTIVES` list include it so `GL10` covers it.
  {issue}`227` carries both today and closes with this specification's implementation, so
  that pull request files one issue for them and repoints this item.

(stamps-spec-9)=
## 9. References

- {issue}`227` — the `versionadded` gate: phase 1's design, and phase 2's rules
- {pull}`229` — phase 1's implementation
- {pull}`317` — the gate that deadlocked a release, and the one-sided lesson §3.1 applies
- {issue}`310` — the underived version that `target_version()` refuses
- `docs/src/developer/docs-style.rst`, *API Version Stamps* — the contributor-facing policy
- `docs/src/developer/release.rst` — the runbook whose steps 4 and 10 §3.3 changes
