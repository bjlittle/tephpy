# tephpy design specifications — publication and conventions

> **Living document.** This specification is maintained alongside the documentation system
> it describes. It states the conventions every tephpy design specification follows —
> where they live, how their sections are addressed, and what a reader may assume about
> an unresolved item. Cite it as `docs spec §…`. Read it as current.

- **Date:** 2026-08-03 (originated; maintained since)
- **Status:** living design specification
- **Issue:** [#65](https://github.com/bjlittle/tephpy/issues/65)
- **Applies to:** every document under `docs/src/developer/specs/`

(docs-spec-1)=
## 1. Purpose

`src/` and `tests/` carry 333 `spec §…` citations. Until now the documents they cite never
entered the docs build, so a reader on Read the Docs met a reference to something that,
from where they were standing, did not exist — on twelve published API reference pages.

This specification closes that gap and states the conventions that keep it closed. It has
two halves, and only the first is a migration:

- **Publication.** Where the specifications live so that Sphinx builds them, and how the
  plans stay tracked but unpublished.
- **Conventions.** How sections are addressed, how the citation namespace works, and what
  status an unresolved item carries. These are ongoing contracts, not migration steps,
  which is why this document is itself a living specification rather than a plan.

The distinction between the two document classes is settled in
[#73](https://github.com/bjlittle/tephpy/pull/73): specifications are living documents
maintained alongside the code; plans are a point-in-time record of what was intended
before implementation, not updated afterwards. Everything below follows from that.

(docs-spec-2)=
## 2. Decisions

1. **Specifications are published; plans are not.** The reader-facing consequence of #73.
2. **Both live under the developer section, not a Diátaxis quadrant.** The quadrants are
   for users. Specification content — §7 testing, §8 engineering standards, §10 roadmap —
   is contributor material, and the developer guide is its dedicated home, following the
   [`bjlittle/geovista`](https://github.com/bjlittle/geovista) structure.
3. **Specifications and plans remain siblings** so that the relative links between them
   keep working, in a checkout and in GitHub's web UI.
4. **Sections are addressed by explicit anchors keyed to the section number,** never by
   the slug docutils derives from the heading text.
5. **Citations stay plain text for now.** Converting them into Sphinx cross-references is
   a separate change (§7).
6. **An unresolved item in a specification must cite a tracked issue** (§3.5).

(docs-spec-3)=
## 3. Architecture

(docs-spec-3-1)=
### 3.1 Layout

```
docs/src/developer/
├── docs-style.rst
├── index.rst
├── plans/          tracked, excluded from the build
└── specs/          published
    ├── index.rst
    ├── 2026-07-22-tephpy-design.md
    ├── 2026-08-01-add-logo-design.md
    └── 2026-08-03-published-specs-design.md
```

`docs/Makefile` sets `SOURCEDIR = src`, so both directories sit inside the source tree and
Sphinx reads the specifications natively. The plans are withheld by a single
`exclude_patterns` entry in `docs/src/conf.py`:

```python
exclude_patterns = ["brand/assets/*", "developer/plans/*"]
```

The two directories stay siblings. This is not cosmetic: the twelve plan banners added by
#73 link to [`../specs/`](../specs/), and the parent specification refers to the plans in
the other direction. Any layout that published the specifications while leaving the plans
elsewhere would break one direction and not the other, which is the confusing failure.

`docs/superpowers/` no longer exists. The superpowers skills default to writing
specifications and plans there, and their own instructions state that a user preference
overrides the default, so the preference is recorded once in the repository's `AGENTS.md`.

(docs-spec-3-2)=
### 3.2 Navigation and the citation namespace

`docs/src/developer/specs/index.rst` carries the toctree and introduces the collection. It
must state two things a reader cannot infer from any single document:

- **These are living documents.** The reader is entitled to treat what they read as
  current, and to report a divergence from the code as a specification defect.
- **The citation namespace has more than one member.** The prefix identifies the document:

  | citation | document | count |
  |---|---|---|
  | `spec §…` | `2026-07-22-tephpy-design.md` | 310 |
  | `logo spec §…` | `2026-08-01-add-logo-design.md` | 23 |
  | `docs spec §…` | this document | 0 |

  The prefix is load-bearing, not decorative: `logo spec §3.6` names a section that has no
  counterpart in the parent specification, so a reader who ignores the prefix lands in the
  wrong document with no signal that they have.

Each specification declares its own prefix in its header banner. A new specification
chooses a prefix that is unique across the collection and states it there.

(docs-spec-3-3)=
### 3.3 Section anchors

Every numbered heading carries an explicit MyST target immediately above it, keyed to the
section number with dots replaced by hyphens and prefixed by the document's slug:

```markdown
(spec-3-2)=
### 3.2 `plotting`
```

The target becomes the section's HTML `id`, so `…/2026-07-22-tephpy-design.html#spec-3-2`
addresses §3.2 directly.

Two reasons this is not optional. First, docutils derives its slug from the heading *text*
and discards the number, so `### 3.2 \`plotting\`` would otherwise be addressable only as
`#plotting` — and 149 citations point at that one section of a document that renders to
180 KB of HTML. A citation that resolves to the top of a page that long has not really
resolved. Second, prose-derived slugs collide silently: §7 *Testing* and §8.5 *Testing*
produced the same slug, and docutils disambiguated the second to `id1` — an anchor that
silently becomes `id2` the moment a heading is inserted above it. Anchors derived from
prose are unstable under exactly the edits a living document invites.

The prefixes are `spec-`, `logo-spec-` and `docs-spec-`, matching the citation prefixes in
§3.2 with spaces replaced by hyphens. Sphinx labels are global, so the prefix is what
keeps `spec-3-2` and `logo-spec-3-2` distinct.

(docs-spec-3-4)=
### 3.4 Pointer maintenance across the two document classes

#73 established that a plan is not updated after implementation. That contract governs
what a plan *says* — the intent it recorded, including where implementation later departed
from it. It does not govern the pointers a plan uses to name other documents.

So one carve-out, stated here so the boundary is not re-litigated: **a repository path or
link in a plan may be corrected when the thing it names moves; nothing else in a plan may
be edited.** A plan whose reference to its own specification no longer resolves is a worse
historical record, not a purer one — a reader who cannot reach the specification the plan
was derived from cannot evaluate the plan at all. Git history holds the original text
either way.

(docs-spec-3-5)=
### 3.5 Status vocabulary and the open-item contract

A living specification records not only what was decided but what remains undecided. Those
records are useful only if a reader can tell, at a glance, which is which and where the
trail continues. Every item in the parent specification's §10 *Assumptions and open
decisions* and §11 *Open questions* therefore carries a leading status tag from a fixed
vocabulary:

| status | meaning | must carry |
|---|---|---|
| **Resolved** | Settled and reflected in the code | date, and the PR or plan that settled it |
| **Refined** | Resolved earlier, revised by later work | date and the later PR or plan |
| **Rejected** | Considered and deliberately not done | date and one line of why |
| **Deferred** | Real, but not for this release | the release or issue it defers to |
| **Blocked** | Started, cannot proceed | what it is blocked on |
| **On hold** | Deliberately paused | why, and what would restart it |
| **Open** | Not yet addressed | — |

**The contract: any item not `Resolved` or `Rejected` must cite a tracked issue.** The
specification carries the pointer; the issue carries the discussion and the current state.
This is what stops a specification becoming a place where live work sits unseen — the
failure mode that a published document makes worse, because publication invites a reader
to trust it.

Those issues carry the `design: open` label, which makes the contract checkable in both
directions: every pointer in a specification must resolve to an issue, and every issue
carrying the label must be cited by a specification. A one-directional check lets an
issue be closed while the specification still claims the item is open.

(docs-spec-4)=
## 4. Canonical usage

A reader meets `(spec §3.2)` in the rendered documentation for `plot_barbs`, follows the
developer guide to *Design specifications*, and lands on §3.2 of the parent document by
its anchor. Reading it, they are entitled to assume it describes tephpy as it stands.

A contributor changing behaviour that a specification section describes updates that
section in the same pull request. A contributor who finds the code and the specification
disagreeing has found a specification defect, and reports it as one.

An item that cannot be settled now is written into §10 or §11 with a status tag, filed as
an issue labelled `design: open`, and cited from the item.

(docs-spec-5)=
## 5. Migration

One-off work, performed once and then finished:

1. `git mv` both directories under `docs/src/developer/`; add the `exclude_patterns`
   entry; record the superpowers path preference in `AGENTS.md`.
2. Add `docs/src/developer/specs/index.rst` and reference it from the developer guide
   toctree.
3. Add anchors to the 25 numbered headings in the parent specification and the 15 in the
   `add_logo` specification.
4. Repoint the parent specification's header link to the plans at an absolute GitHub URL.
   It is the build's only warning, and it fails precisely *because* the plans are
   deliberately unpublished: `../plans/` still resolves in a checkout and on GitHub, but
   Sphinx cannot resolve a link to a page it was told not to build. An absolute URL keeps
   the affordance for a reader of the published page, who has no checkout to fall back on.
5. Correct the stale repository paths (§3.4): §10 of the parent specification names
   `docs/superpowers/plans/`, `README.md` links to `docs/superpowers/specs` on GitHub, and
   twelve plans name their originating specification by its old path. The README link
   points at the published page instead, now that one exists.
6. Audit §10's sixteen items and §11's four questions, establish the true status of each,
   apply the §3.5 tags, and file `design: open` issues for whatever is genuinely open.

(docs-spec-6)=
## 6. Verification

The docs build runs with `--fail-on-warning --keep-going` and nitpicky cross-references,
so a clean `pixi run docs` exiting 0 is the primary gate. Beyond it:

- `_build/html/developer/plans/` does not exist, and no plan page is reachable.
- Both existing specification pages render, and this one alongside them.
- Every anchor named in §3.3 appears as a section `id` in the built HTML.
- Every distinct `spec §N` and `logo spec §N` citation in `src/` and `tests/` corresponds
  to an anchor that exists — a one-off check at implementation time.

A trial build of the moved specifications has already been run: 1,533 lines of Markdown
through myst produced exactly one warning, the `../plans/` link of item 4 above.

(docs-spec-7)=
## 7. Scope

Not in this change:

- **Converting citations into Sphinx cross-references.** 101 rendered citations across 60
  public objects would become `:ref:` targets. The anchors in §3.3 are its prerequisite,
  which is why it becomes cheap afterwards rather than never.
- **A citation-integrity pre-commit hook.** Nothing verifies that `spec §3.2` still names
  the right heading; renumbering would strand 149 citations silently. Every citation
  resolves correctly today, so the anchors make now the cheap moment to adopt one — as a
  follow-up, once the anchors are stable.
- **Editing the specifications' technical content.** They are published as they stand.
  The §3.5 pass adds status tags and issue pointers; it does not rewrite the reasoning.

(docs-spec-8)=
## 8. References

- [#65](https://github.com/bjlittle/tephpy/issues/65) — publish the design specifications
- [#73](https://github.com/bjlittle/tephpy/pull/73) — the living/point-in-time contract
- [`bjlittle/geovista`](https://github.com/bjlittle/geovista) — the developer-section precedent
- [MyST targets and cross-referencing](https://myst-parser.readthedocs.io/en/latest/syntax/cross-referencing.html)
