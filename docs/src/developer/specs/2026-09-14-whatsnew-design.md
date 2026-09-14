# tephpy what's new — design specification

```{readingtime}
```

> **Living document.** This specification is maintained alongside the code, not archived
> behind it. The pages and gates it describes cite it by section — `whatsnew spec §3.2`
> and the like — so these sections *are* the reasoning behind what those pages do, and
> where the two ever diverge it is the specification that gets corrected. Read it as
> current.

- **Date:** 2026-09-14 (originated; maintained since)
- **Status:** living design specification
- **Citation prefix:** `whatsnew spec §…`
- **Scope:** a reference section carrying the highlights of each release in prose, the
  substitutions and changelog anchors it reads, and the release-time workflow that
  freezes one page and seeds the next
- **Parent spec:** [`2026-07-22-tephpy-design.md`](2026-07-22-tephpy-design.md) —
  `spec §10`'s release execution, of which this is the reader-facing half
- **Sibling specs:**
  [`2026-08-27-narrative-quadrants-design.md`](2026-08-27-narrative-quadrants-design.md) —
  the reference quadrant this section joins;
  [`2026-08-31-reading-time-design.md`](2026-08-31-reading-time-design.md) —
  `reading spec §3.6`'s banner rule, whose exemption list §3.1 below extends

(whatsnew-spec-1)=
## 1. Purpose

**The changelog answers "what changed"; nothing answers "what should I care about".**

`CHANGELOG.rst` is one entry per pull request, in the order towncrier assembles them.
That is the right record and the wrong introduction: a reader arriving at a new release
wants a handful of sentences about what is worth their attention, and gets 171 entries
about what was merged. The two documents have different jobs and only one of them
exists.

This section adds the other one. Each release gets a page of highlights in prose, which
links to that release's changelog entry for the full record. `geovista` has carried the
same section through several releases and is the model; what follows notes where tephpy
departs from it and why.

(whatsnew-spec-2)=
## 2. Decisions

1. **Per minor version, not per release.** `0.1.rst` covers `v0.1.0` and every patch
   after it. A patch release appends to §3.1's *Patches* section rather than opening a
   page of its own, because a reader asking what is new in 0.1 wants one page.
2. **The per-release changelog anchor is keyed on version, not date.** geovista's
   towncrier template emits `…-{{ versiondata.date }}`; tephpy emits
   `…-v{{ versiondata.version }}` (§3.3). Both are written by towncrier and both are
   known on release day, so this buys no ordering — it buys legibility. A frozen page
   links `changelog-v0.1.0`, which a reader can guess and a reviewer can check against
   the release it sits on; `changelog-2026-09-14` can only be looked up. The date is
   still in the rendered title either way.
3. **No icon roles.** geovista's pages use font-awesome (`:fa:`, `:fab:`). tephpy's
   idiom is `sphinx-iconify`, and `start spec §3.4` records a read-time network cost for
   it, so these pages carry emoji-free plain headings and no icon roles at all.
4. **A frozen page states its version literally.** §3.2 gives the reason; it is the one
   place this design cannot copy geovista, which has never frozen a page.
5. **The page's body is the newest *released* highlights, not the ones being accumulated.**
   geovista's index includes `latest.rst` always. Here the `include` follows the newest
   frozen page, so a reader arriving after 0.1.0 ships reads 0.1's highlights rather than
   `TBD prior to release` — which is what they would meet for most of a cycle otherwise,
   on the page a release announcement links to. `latest.rst` stays one entry away in the
   toctree.

(whatsnew-spec-3)=
## 3. Architecture

(whatsnew-spec-3-1)=
### 3.1 Where it lives, and the shape

`docs/src/reference/whatsnew/`, joining the reference quadrant — the factual material,
looked up rather than read through. `narrative spec §7` settled that this quadrant takes
a plain toctree rather than a landing table, so the section is one entry in
`reference/index.rst`, placed before `changelog` since the highlights are what a reader
meets first and the record is what they go on to.

Three files:

| file | what it is |
|---|---|
| `index.rst` | the *What's New* page itself: an introduction, an `include` of the newest frozen page, and a hidden toctree |
| `latest.rst` | the release being accumulated toward, and a real page in its own right |
| `A.B.rst` | one frozen release per minor version, newest first in the toctree |
| `latest.rst.template` | the seed §3.5 copies into place after a release |

**The `include` names the newest frozen page, and the toctree lists every page.** So the
*What's New* page opens with the highlights of the release a reader can actually install,
while `latest.rst` — the next one, still filling up — sits at the head of the toctree
beside it. The include moves exactly once per release, at §3.5 step 1.

Before the first release there is no frozen page, so the include names `latest.rst`; that
is the state this section ships in, and `v0.1.0` is where it switches over for good.

The included page is therefore both inlined into `index.rst` **and** a document of its
own. Measured 2026-09-14: that builds clean under fail-on-warning — no duplicate label,
no orphan. A reader sees the current highlights without a second click, and the page still
has a URL to link.

Each page carries the three headings geovista uses, without its icons:
**Announcements**, **Highlights**, **Patches**.

`index.rst` joins `reading spec §3.6`'s `EXEMPT` list, alongside the section and quadrant
index pages it already holds. The banner belongs on the pages a reader reads, and an index whose body is
an include and a toctree is not one — and were it to carry a banner of its own it would
render two, its own and the included page's, which the reading-time gate refuses.
`latest.rst` and every frozen page carry theirs.

(whatsnew-spec-3-2)=
### 3.2 The version and date substitutions

`conf.py` defines two substitutions through `rst_epilog`:

```python
_built = datetime.now(tz=UTC).strftime("%Y-%m-%d")

rst_epilog = f"""
.. |tp_version| replace:: v{release}
.. |build_date| replace:: ({_built})
"""
```

`release` is the installed version, which `conf.py` already resolves. `latest.rst` opens
with `|tp_version| |build_date|`, so it reads `v0.1.0.dev213 (2026-09-14)` on a
development build and the release version on the tagged one, with no file to edit.
Measured 2026-09-14: the substitution expands inside the included copy as well as on
`latest.html`.

**A frozen page must not use them, and this is the departure from geovista.** A frozen
`0.1.rst` stays in the toctree for the life of the project. Left substituted, the 0.2.0
documentation build would render it titled `v0.2.0` with that day's date — a page about
0.1 announcing a version it has nothing to do with. So freezing a page replaces the two
substitutions with the literal text, and §4 gates it. geovista has not met this because
its `whatsnew/` has only ever held `index.rst`, `latest.rst` and the template: no page
has been frozen there yet, so the workflow's second half is designed here rather than
copied.

(whatsnew-spec-3-3)=
### 3.3 The changelog title and the per-release anchor

`changelog/template.rst` emits, before each release's entries:

```jinja
.. _changelog-v{{ versiondata.version }}:

{% if render_title %}
v{{ versiondata.version }} ({{ versiondata.date }})
{{ top_underline * ((versiondata.version + versiondata.date)|length + 4) }}
{% endif %}
```

`versiondata` is towncrier's, so both the title and the anchor are produced at assembly
time from the version the release manager passes — nothing is written by hand and nothing
can disagree with the release it describes.

**The title is not a refinement; it is a defect being fixed.** Before this, the template
carried no `render_title` block and `title_format` was unset, so the assembled
`CHANGELOG.rst` had *no version headings at all*. With one release nobody notices; from
the second, the file becomes an undivided run of entries with nothing to link to.
Measured 2026-09-14 by assembling a real changelog: the anchor survives
`sphinx_changelog`'s directive and reaches the rendered page as `id="changelog-v0-1-0"`.

(whatsnew-spec-3-4)=
### 3.4 The changelog preamble

`reference/changelog.rst` gains a short preamble stating the versioning scheme and
pointing at this section, and — immediately above the `changelog` directive — the label
`_changelog-latest`. `latest.rst` links *that* rather than a version anchor, because the
release it describes has no version anchor until it is assembled. A frozen page swaps the
link for its own release's anchor at the same moment §3.2's substitutions become literal.

(whatsnew-spec-3-5)=
### 3.5 The release-time workflow

Four steps, which `developer/release.rst` carries in its sequence:

1. **Before tagging, on the release branch.** Populate `latest.rst`'s Announcements and
   Highlights, replace `|tp_version|`/`|build_date|` with the literal version and release
   date, repoint the changelog link at `changelog-vX.Y.Z`, and rename the file to
   `A.B.rst`. Then edit `index.rst`: point its `include` at `A.B.rst`, and replace
   `latest` with `A.B` in the toctree.

   **Both index edits are obligatory, not tidying.** The rename takes `latest.rst` out of
   existence, so a toctree entry still naming it names nothing — on the one commit that
   gets tagged, built, and published. The `include` moves for the reason decision 5
   of §2 gives: the newest frozen page is now this one.

2. **Tag, publish, merge back** — `developer/release.rst`'s existing steps, unchanged.
   Through this window the section has no `latest.rst` at all, and that is the correct
   state: there is no next release being accumulated toward yet.

3. **After the merge-back lands on `main`**, and not before, copy `latest.rst.template`
   to `latest.rst`. It then accumulates highlights for the next minor version.

   The ordering here is the part worth stating. Seeding on the release branch would send
   the file back through the merge-back as a second empty page, and seeding on `main`
   before the merge-back would put `main` in a state where `latest.rst` and the frozen
   page both claim to be the newest.

4. **Reintroduce it to `index.rst`'s toctree**, in the same commit as step 3: `latest`
   goes back at the head, above the frozen pages. Step 1 removed it and nothing else puts
   it back, and a `latest.rst` in the directory but in no list is a page the section
   cannot reach — which is what §4's first gate exists to catch.

   The `include` is **not** touched here. It stays on the release just frozen, which is
   decision 5 of §2: the page a reader meets should be the newest release they can
   install, not the placeholder for the next one. The include therefore moves once per release, in step 1,
   and never in step 4.

A patch release re-enters at step 1 against the existing `A.B.rst`, appending to its
*Patches* section. It skips steps 3 and 4: `latest.rst` on `main` is already accumulating
for the next minor version and is not what a patch describes.

**What the *What's New* page shows is therefore stable across the cycle**: the newest
released highlights, from step 1 until the next release's step 1. It never shows the
template's placeholders, which is the whole of decision 5 in §2 — the alternative,
following
`latest.rst`, would put `TBD prior to release` in front of every reader for most of a
cycle, on the page a release announcement links to.

(whatsnew-spec-4)=
## 4. Testing

Three gates, each closing a way this goes wrong silently. The fail-on-warning build
already covers a broken reference, so none of these repeats it.

**The index lists every page in its directory.** The same rule
`narrative spec §3.9` gives the quadrant landing pages, for the same reason: a page the
toctree does not name builds clean and is unreachable from the section it belongs to. The
toctree is what the gate reads — the `include` is a convenience that always duplicates one
entry of it, never the only route to a page. Only the rule is borrowed — the *What's New* page is **not** a landing page in
that specification's sense, since `narrative spec §7` keeps the reference quadrant out of
the table-and-toctree shape those pages carry, and `tests/test_docs_landing_pages.py`
governs `TABLE_SECTIONS` alone. `latest.rst.template` is not a page and is excluded by name.

**No page but `latest.rst` carries the substitutions.** §3.2's freezing step is a manual
edit made once per release, and forgetting it produces a page that is wrong only from the
*next* release onward — long after anyone would connect the two. Reading the frozen pages
for `|tp_version|` and `|build_date|` catches it on the release pull request.

**No frozen page may carry the placeholder.** This was first written against `latest.rst`
instead, gated on the installed version reaching the first release — modelled on
`start spec §3.7`'s pre-release note, which earns exactly that shape by becoming one-sided
for the same kind of reason. But `start spec §3.7`'s note makes one transition and stays
retired; this state is cyclic, not one-way. §3.5 step 3 reseeds `latest.rst` from the
template — placeholder and all — after every release, so a rule keyed to the release
signal read a freshly reseeded file as a defect for the whole of the next cycle, and read
nothing at all through the frozen window between a release's tag and its merge-back, where
`latest.rst` does not exist (§3.5 step 2). The rule belongs to the page that is actually
wrong to carry the placeholder: the one just frozen, which needs no comparison against the
installed version to be wrong, and is vacuous before the first release because nothing is
frozen yet. Shipping `TBD` as the highlights of a release is still the one failure here
that reaches every reader; this catches it on the release pull request that does the
freezing, the same commit the gate above already reads.

(whatsnew-spec-5)=
## 5. Known defect, not caused here

Assembling `CHANGELOG.rst` fails `tests/test_citations.py::test_the_container_census_is_what_was_recorded`
({issue}`318`). The citation corpus is every tracked text file, so a non-empty
`CHANGELOG.rst` brings its fragments' container citations under a new key that the census
recorded by {pull}`297` does not have — and the count changes at every release, so
recording it is a treadmill.

It is stated here because building this section is what found it, and because it fires on
the same runbook step this design adds to. It is **not** this design's to fix: it would
fire at the first release with no whatsnew section at all.

(whatsnew-spec-6)=
## 6. Non-goals

- **Generating highlights from the changelog.** The value of a highlight is that a person
  decided it mattered; a summary derived from fragments would reproduce the changelog with
  fewer words.
- **A page per patch release.** §2 settled this. Revisit only if a patch ever carries
  more than its *Patches* bullets can hold.
- **Announcing releases anywhere else.** `developer/release.rst` step 13 leaves announcing
  to a person; this section is the material they would draw on, not a channel.
- **Backfilling releases before v0.1.0.** There are none.
