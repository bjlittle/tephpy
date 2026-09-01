# tephpy design specifications — publication and conventions

```{readingtime}
```

> **Living document.** This specification is maintained alongside the documentation system
> it describes. It states the conventions every tephpy design specification follows —
> where they live, how their sections are addressed, and what a reader may assume about
> an unresolved item. Cite it as `docs spec §…`. Read it as current.

- **Date:** 2026-08-03 (originated; maintained since)
- **Status:** living design specification
- **Issue:** {issue}`65`
- **Applies to:** every document under `docs/src/developer/specs/`

(docs-spec-1)=
## 1. Purpose

`src/` and `tests/` carry `spec §…` citations in the hundreds, and §3.2 says how to count
them. Until now the documents they cite never entered the docs build, so a reader on Read
the Docs met a reference to something that, from where they were standing, did not exist —
on twelve published API reference pages.

This specification closes that gap and states the conventions that keep it closed. It has
two halves, and only the first is a migration:

- **Publication.** Where the specifications live so that Sphinx builds them, and how the
  plans stay tracked but unpublished.
- **Conventions.** How sections are addressed, how the citation namespace works, and what
  status an unresolved item carries. These are ongoing contracts, not migration steps,
  which is why this document is itself a living specification rather than a plan.

The distinction between the two document classes is settled in
{pull}`73`: specifications are living documents
maintained alongside the code; plans are a point-in-time record of what was intended
before implementation, not updated afterwards. Everything below follows from that.

(docs-spec-2)=
## 2. Decisions

1. **Specifications are published; plans are not.** The reader-facing consequence of {pull}`73`.
2. **Both live under the developer section, not a Diátaxis quadrant.** The quadrants are
   for users. Specification content — spec §7 testing, spec §8 engineering standards,
   spec §10 roadmap — is contributor material, and the developer guide is its dedicated
   home, following the [`bjlittle/geovista`](https://github.com/bjlittle/geovista)
   structure.
3. **Specifications and plans remain siblings** so that the relative links between them
   keep working, in a checkout and in GitHub's web UI.
4. **Sections are addressed by explicit anchors keyed to the section number,** never by
   the slug docutils derives from the heading text.
5. **Citations stay plain text in the source; the build makes them links.** The written
   form never changes — `spec §3.2` in a docstring is the characters it has always been —
   and a Sphinx transform resolves it against the §3.3 anchors while building the doctree
   (§3.7).
6. **An unresolved item in a specification must cite a tracked issue** (§3.5).
7. **A reference to an issue or pull request is written as a role, not as text or a URL.**
   The opposite of decision 5, and for the reason that decides both: an extlink's caption
   is generated from its value, so writing the role is what makes the text and the target
   inseparable, where writing a citation's role would let them come apart (§3.8).
8. **The code the user documentation tells a reader to type is executed** — every python
   block in the user quadrants, as one script per page, in document order, ending with a
   draw of every figure the page leaves open (§3.9). Whether a snippet does what the prose
   around it claims is a separate property, and an authoring rule rather than a gate; what
   its figure looks like is `pytest-mpl`'s, not this gate's.

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
    ├── 2026-08-03-published-specs-design.md
    ├── 2026-08-07-config-file-design.md
    ├── 2026-08-12-config-domain-validation-design.md
    └── 2026-08-13-dependency-floors-design.md
```

`docs/Makefile` sets `SOURCEDIR = src`, so both directories sit inside the source tree and
Sphinx reads the specifications natively. The plans are withheld by a single
`exclude_patterns` entry in `docs/src/conf.py`:

```python
exclude_patterns = ["brand/assets/*", "developer/plans/**"]
```

The two directories stay siblings. This is not cosmetic: the plan banners {pull}`73`
introduced link to `../specs/` — every plan carries one — and the parent specification refers
to the plans in the other direction. Any layout that published the specifications while
leaving the plans elsewhere would break one direction and not the other, which is the
confusing failure. Stating it as "every plan" rather than as a count is deliberate: the
number was twelve when this was written and grows with the repository, and §4 rules out a
figure that has to be re-measured to stay true.

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

  | citation | document |
  |---|---|
  | `spec §…` | `2026-07-22-tephpy-design.md` |
  | `logo spec §…` | `2026-08-01-add-logo-design.md` |
  | `docs spec §…` | this document |
  | `configfile spec §…` | `2026-08-07-config-file-design.md` |
  | `domain spec §…` | `2026-08-12-config-domain-validation-design.md` |
  | `floors spec §…` | `2026-08-13-dependency-floors-design.md` |

  The table names the members and counts nothing, per §4. How many citations name each
  document is a fact about the corpus on the day it is read, and there are two such facts
  rather than one: occurrences of the literal prefixed form, and citations *resolving* to
  the document once the bare and compound forms below are counted too. Either is obtained by
  tallying `tephpy_citations.scan` over `check_citations.corpus()` — for the second, keyed by
  the document each resolved anchor sits in — which is the gate of §3.6 counting rather than
  reporting.

  The prefix is load-bearing, not decorative: `logo spec §3.6` names a section that has no
  counterpart in the parent specification, so a reader who ignores the prefix lands in the
  wrong document with no signal that they have.

Each specification declares its own prefix in its header banner. A new specification
chooses a prefix that is unique across the collection and states it there.

Three details of the citation form, each of which a reader — or a checker — has to get
right. The word `spec` is matched without regard to case, so a sentence may open with
`Spec §3.2`. Where several sections are cited together the prefix carries across the whole
run, so `spec §3.3, §10` and `spec §3.1/§10` each name two sections of the parent; the
separators are a comma or a solidus. And a citation with no prefix at all — a bare `§N` —
means the *containing document's* §N:

> **A bare `§N` means this document. A reference to any other document names it.**

Inside a specification the bare form is the ordinary way to point at a neighbouring
section, and the parent uses it throughout. Outside the collection it is always an error:
`src/` and `tests/` own no sections, so a bare `§N` in a docstring has nothing to be
relative to and is read as the parent's only by habit. Stating the rule this way is what
makes the unqualified form *safe* — its meaning is fixed by where it is written rather
than by what the reader assumes, and the one case it cannot be is a silent reference to
somewhere else.

(docs-spec-3-3)=
### 3.3 Section anchors

Every numbered heading carries an explicit MyST target immediately above it, keyed to the
section number with dots replaced by hyphens and prefixed by the document's slug:

```markdown
(spec-3-2)=
### 3.2 `plotting`
```

The target becomes the section's HTML `id`, so `…/2026-07-22-tephpy-design.html#spec-3-2`
addresses spec §3.2 directly.

Two reasons this is not optional. First, docutils derives its slug from the heading *text*
and discards the number, so `### 3.2 \`plotting\`` would otherwise be addressable only as
`#plotting`. Each specification renders as one long page, so a citation landing at the top
of it rather than at the section it names has not really resolved. Second, prose-derived
slugs collide silently: spec §7 *Testing* and spec §8.5
*Testing* produced the same slug, and docutils disambiguated the second to `id1` — an
anchor that silently becomes `id2` the moment a heading is inserted above it. Anchors
derived from prose are unstable under exactly the edits a living document invites.

The prefixes are `spec-`, `logo-spec-`, `docs-spec-`, `configfile-spec-`, `domain-spec-` and
`floors-spec-`, matching the citation prefixes in §3.2 with spaces replaced by hyphens — one
per document in the table there, and a new specification adds its own. Sphinx labels are global, so the prefix is what
keeps `spec-3-2` and `logo-spec-3-2` distinct.

(docs-spec-3-4)=
### 3.4 Pointer maintenance across the two document classes

{pull}`73` established that a plan is not updated after implementation. That contract governs
what a plan *says* — the intent it recorded, including where implementation later departed
from it. It does not govern the pointers a plan uses to name other documents.

So one carve-out, stated here so the boundary is not re-litigated: **a repository path or
link in a plan may be corrected when the thing it names moves; nothing else in a frozen
plan may be edited.** A plan whose reference to its own specification no longer resolves is
a worse historical record, not a purer one — a reader who cannot reach the specification
the plan was derived from cannot evaluate the plan at all. Git history holds the original
text either way.

A plan is frozen when its implementation PR merges, not when the plan itself does. While a
plan is still being executed, a correction to what it asks for is a correction to work that
has not happened yet — the point-in-time record is of what was intended, and intent that
was wrong on the facts is worth fixing before it is acted on.

(docs-spec-3-5)=
### 3.5 Status vocabulary and the open-item contract

A living specification records not only what was decided but what remains undecided. Those
records are useful only if a reader can tell, at a glance, which is which and where the
trail continues. Every item in a specification's open-item sections — spec §10
*Assumptions and open decisions* and spec §11 *Open questions* — therefore carries a
leading status tag from a fixed vocabulary:

| status | meaning | must carry |
|---|---|---|
| **Resolved** | Settled and reflected in the code | date, and the PR or plan that settled it |
| **Refined** | Resolved earlier, revised by later work | date and the later PR or plan |
| **Rejected** | Considered and deliberately not done | date and one line of why |
| **Deferred** | Real, but not for this release | the release or issue it defers to |
| **Blocked** | Started, cannot proceed | what it is blocked on |
| **On hold** | Deliberately paused | why, and what would restart it |
| **Open** | Not yet addressed | — |

The date is the date the decision was taken, not the date the pull request merged; where an
item's prose carries no date for the *tagged* event — a **Refined** item whose refinement
is undated, say, though its earlier resolution is not — the last cited pull request's merge
date is used.

**The contract: any item not `Resolved`, `Refined`, or `Rejected` must cite a tracked
issue.** The specification carries the pointer; the issue carries the discussion and the
current state. This is what stops a specification becoming a place where live work sits
unseen — the failure mode that a published document makes worse, because publication
invites a reader to trust it.

Those issues carry the `design: open` label, which makes the contract checkable in both
directions: every pointer in a specification must resolve to an issue, and every issue
carrying the label must be cited by a specification. A one-directional check lets an
issue be closed while the specification still claims the item is open.

The parent specification is not the only document this governs. A specification with no
spec §10 or spec §11 records its unsettled items in whatever section it does carry —
**§Scope** in the `add_logo` specification and in this one, **§Non-goals** in the
`configfile` specification — and those entries carry the same tags and the same issue
pointers. The heading differs; the contract does not, and it binds by the section's role
rather than by its name, because a specification that named its ledger something new would
otherwise fall outside a rule written against a list of headings. Scoping it to the one
document that happens to have the right headings would leave live work sitting unseen in
exactly the published pages the contract exists to protect, and a reader has no way to
know that the absence of a tag means "not covered" rather than "nothing outstanding".

(docs-spec-3-6)=
### 3.6 Citation integrity

§3.2 and §3.3 are conventions, and a convention that nothing checks decays. Renumbering a
section, or inserting one, strands every citation that named the old number — and the
failure is invisible, because a stale citation is still a well-formed sentence in a
docstring that still renders. A pre-commit hook therefore asserts four properties:

1. **Resolution.** Every citation names an anchor that exists.
2. **Keying.** Every `(prefix-N)=` target sits immediately above the heading numbered N.
3. **Coverage.** Targets and numbered headings pair up one to one: every heading carries a
   target, and every target still has a heading beneath it.
4. **Separation.** No line break sits between a citation's prefix and its section number.

Resolution is the one that catches renumbering. Keying and coverage are what keep
resolution meaningful: an anchor that has drifted onto the wrong heading still resolves, a
heading with no anchor is unaddressable rather than wrongly addressed, and an anchor left
behind by a deleted section resolves to nothing at all — none of the three shows up as a
broken citation. Coverage is stated as a pairing rather than a one-way rule because the
two directions catch different faults, and reading only from the headings down misses the
orphan: there is no heading left to start from.

Separation is the one resolution cannot help with, because the wrapped citation resolves —
to the wrong document. A prefix ending a line never reaches a section sign opening the next:
the reader of §3.2's grammar is horizontal-only by design, so the citation is left with
whatever prefix shares its line, or falls back to the containing document. The transform of
§3.7 reads it the same way, the text node having kept the newline, so the two agree and the
page links somewhere nobody wrote. Both of the other properties hold throughout: the anchor
exists, and it is keyed and covered. Only the reader can tell, and only by following it.

Separation reads each file the way the other three do, and for the same reason: a notebook
as its cells rather than as the JSON it is stored in. A notebook's authored newlines are
escapes inside quoted strings, so a rule reading the raw text finds no line boundary to look
across and every wrap in the corpus's notebooks would pass unseen. What a wrap may join is
therefore bounded by what the reader yields — a fence in markdown and a cell boundary in a
notebook both end a run, the first blank and the second merely discontinuous.

The check asks the one question the other three cannot: **does undoing the wrap move the
anchor?** Nothing guesses what the author meant. A citation that reads the same wrapped and
unwrapped is never reported, which is what keeps the rule silent over the bare `§N` naming
the containing document — 61% of the citations in this corpus when the rule was written, and
the reason §3.2's fallback is not simply withdrawn. The measurement behind that figure, and
the two heuristics it ruled out, are recorded in {issue}`197`.

One class stays out of reach and is accepted rather than approximated. A section separated
from its prefix by something that is not a separator — `" and "` is the case {issue}`197`
found — resolves identically wrapped or not, so no comparison distinguishes it from a
citation meant that way. That one is a review question, and *Reviewing Claims* asks it.

The check derives its registry rather than declaring one. It reads the anchors out of
`docs/src/developer/specs/*.md`, and the set of valid prefixes falls out of them; a
citation then resolves by replacing the spaces in its prefix with hyphens and asking
whether that anchor exists. Because Sphinx labels are global (§3.3), resolution never
needs to know which file a citation targets, and no prefix-to-document map exists to fall
out of date. A new specification is governed from the day its first anchor lands, with
nothing to register — which is the whole point. A hand-maintained registry fails by
silently not covering something, and silent non-coverage is the failure this check exists
to remove.

Fenced code blocks are skipped. That is not a refinement: §3.3 illustrates the anchor rule
with a literal `(spec-3-2)=` and its heading *inside* a fence, so a checker that reads
fences finds a duplicate anchor and a heading in the wrong document, and fails on the very
passage documenting the rule it enforces. Skipping means matching the opening rail, not
counting delimiters — a block opened with four backticks may quote a three-backtick one,
and a reader that closes on any rail resumes inside the quotation.

A fence is a property of markdown rather than of a file extension, so the rule follows the
markdown wherever it is written. A notebook's markdown cells are read the same way, with
fences skipped; its code cells are read as Python is read, without; and its outputs are not
read at all, being generated rather than authored — and left plain by §3.7 for the same
reason. Keying the rule to the `.md` suffix instead would reintroduce, for the first
notebook that documents this convention, exactly the failure the paragraph above describes.

What a notebook costs is the line number. The file on disk is JSON, so a violation is
reported against the line the cell's source occupies there, located by searching forward
for the JSON-encoded form of the authored line. That rests on two properties of nbformat's
writer, neither of them this repository's to guarantee: one authored line is written to one
physical line, and the section sign is written literally rather than escaped. A writer that
stopped doing either would leave every citation-bearing line unlocatable and every violation
in a notebook reported against the line before it — still printed, still failing, pointing
an editor at the wrong place. So the fixture that exercises this path is written by nbformat
rather than in its likeness ({issue}`95`); one built by hand is the imitation being checked,
and cannot fail when the imitation stops being accurate.

The corpus is derived as well: every text file the repository tracks, less the plans,
which are point-in-time records (§3.4) whose citations are frozen with them, so a
renumbering is not a defect in a plan. Naming the corpus by glob would fail exactly the way a declared
prefix registry fails — by silently not covering something. It did: a corpus of
`src/**/*.py` and `tests/**/*.py` left `tests/fixtures/io/README.md` outside the check
while it carried two citations, along with those in `pyproject.toml` and this collection's
own `index.rst`. A tracked file is in scope from the moment it is added, whatever its
format.

**What this cannot catch.** A citation that is well formed and resolves, but names the
wrong section, is indistinguishable from a correct one. That is not hypothetical — it is
how the seven `design: open` issues failed, each footed `spec §3.5` where `docs spec §3.5`
was meant, sending readers to the parent's `_constants` section. This check is syntactic.
What narrows that class is the §3.2 rule giving the unqualified form a local, safe
meaning, together with review; it is not this hook, and nothing here should be read as
claiming otherwise.

(docs-spec-3-7)=
### 3.7 Rendering citations as cross-references

A citation that a reader cannot follow is a footnote to a document they must go and find.
The anchors of §3.3 make every section addressable, so the remaining work is to turn each
`spec §3.2` in the rendered documentation into a link to it.

**The conversion happens at build time, and no source file is edited.** A Sphinx transform
walks the doctree and replaces each citation in ordinary prose with a `std:ref`
cross-reference resolved against the §3.3 anchors. The written form is untouched: the
docstring on disk still reads `(spec §3.2)`, which is decision 5 of §2 — plain in the
source, linked in the output.

The alternative was to write the role by hand, once per citation. It is rejected for a
reason that follows directly from §3.6's closing paragraph. A hand-written
`` :ref:`spec §3.2 <logo-spec-3-2>` `` has the right display text and the wrong target,
and *both* halves are invisible: the citation checker reads the text and sees a
well-formed `spec §3.2`, and Sphinx resolves the target and finds an anchor that exists,
so the build stays clean. Hand-authoring the targets would therefore manufacture one fresh
opportunity per citation for exactly the wrong-but-resolving failure that §3.6 says it
cannot catch and that the `design: open` issues already demonstrated. Deriving the target
from the text removes the class outright: there is only one string, so the text and the
target cannot disagree. The mechanical cost pointed the same way — a role adds eighteen
characters, which when the decision was taken pushed 30 of the 96 affected lines past the
88-column limit, 13 of them docstring summary lines where wrapping trips numpydoc's
one-line-summary rule.

**One definition of what a citation is.** The transform and the §3.6 hook share a single
grammar module, rather than each carrying its own regular expression. Two definitions
would fail the way a declared registry fails: they would agree until one was amended, and
the disagreement would be silent in both directions — a form the hook accepts but the
transform does not recognise renders as dead text, and a form the transform links but the
hook does not check is unpoliced.

That module lives under `docs/src/_ext/`, not beside the hook in `.github/scripts/`.
`MANIFEST.in` prunes `.github` while the rest of `docs/` ships (§5 item 2), so an extension
importing from `.github` would build here and fail from an sdist. The dependency runs the
other way: the hook, which only ever runs in a checkout, reads the module out of `docs/`.

**What stays plain text.** Literals, code blocks, comments, raw blocks and API signatures
are left alone, so the `` `spec §3.2` `` that the style guide quotes as an example stays an
example, and viewcode's listings, which reproduce every docstring citation as verbatim
Python, are not rewritten. Existing references are skipped too: a citation inside link text
would otherwise nest one anchor inside another, which is invalid HTML that browsers silently
restructure. `[see spec §3.2](…)` is ordinary markdown, and one entry in the skip set rules
the nesting out whether or not a page is written that way. Skipping is not the same as
having nothing to say, though, and the paragraph on headings below is where the two part.

One exception is stated because it is not deducible: `autosummary_table` is a rendered
table that subclasses docutils' `comment` node, and the autoapi module summary sits inside
one, so a transform that skips comments silently skips every citation in it — and a reader
does see them.

**The source format does not matter.** The transform runs on the doctree, after parsing, so
it never sees markdown, reStructuredText or a notebook — only nodes. Citations therefore
link identically from every format the build accepts, including the `.md` and `.ipynb`
that myst-nb parses: in prose, tables, blockquotes, list items and emphasis, but not in a
notebook's code cells or their outputs, which are literal blocks like any other. This is
the reason to prefer a transform over a parser-level rule; a rule written against one
syntax would have to be rewritten for the next.

**The output is checked, not assumed.** §3.6 asserts that every citation in the *source*
resolves to an anchor. Its converse is asserted after `make html`: no citation-shaped text
survives outside a link, excluding only literal text and text already inside one. The two
gates fail in different ways, which is why both exist — the input gate cannot tell whether
the extension was loaded at all, and the output gate cannot tell a right target from a
wrong one. Together they pair the way §3.6's coverage property pairs anchors with headings.

The output gate is the one place that deliberately does *not* use the shared grammar. It
looks for a section sign followed by a number, which is looser than a citation, and that
is the point: a check that asked the grammar what to look for would go blind in the same
instant the grammar did, and pass by finding nothing. It has to be able to see a citation
the transform failed to recognise.

Its exemptions are therefore narrower than the transform's skip set, and deliberately so.
`<code>` and `<pre>` cover literals, code blocks and viewcode, but nothing in the output
marks a raw block or an API signature; a toctree `:caption:` is a directive option the
transform never sees as a node, and renders both where the toctree sits and in the sidebar;
and a citation in a page title loses its anchor twice over — Sphinx strips the markup
copying the title into `<title>`, and the theme repeats it in the breadcrumb without the
link. Each of those is reported as unlinked, which is the answer a reader would give: in
every one of them the citation does reach the page as plain text. Recognising them would
mean matching the transform's node classes in the rendered HTML, which is the coupling the
paragraph above rejects, so the residue is stated as an authoring rule instead — cite a
section in body prose — and the style guide carries it.

**What the failure says is separable from whether it fails.** The gate names the placement
of each unlinked citation, because the four have nothing in common but the symptom and an
author told only that a citation is unlinked has to rediscover which one they are in. It
reads the placement off element names — `<title>`, `<nav>`, `<dt>` — and off nothing else:
the classes that would tell a breadcrumb from any other navigation are one theme's private
presentation contract, where those three are HTML. That the labelling is advisory is what
makes the looser evidence admissible. A label decides only what the report says, never what
it returns, so a placement read wrongly costs a confusing message; the same class of guess
used to *exempt* would cost the gate its sight, which is why the exemptions stay narrow.

The listing is grouped by placement for the same reason, and not merely tidiness: advice is
given for a placement because a line naming that placement was just printed, so the two
cannot come apart on a page long enough for a rare placement to fall past a flat cut. Where
the listing does stop, it says how many it did not name. A report that bounds what it shows
without saying so reads as a smaller problem than it is, which is the failure mode of a
gate that is trying to be readable.

**Nesting is the one thing the transform's own precaution cannot prevent.** Skipping
`nodes.reference` declines to rewrite a citation that is *already* inside a link, which
rules out the case an author writes; it can do nothing about a link put around a citation
the transform has by then made. Docutils' `contents` transform is that case — it runs at
priority 720 against the citation transform's 400, and links every heading it lists both in
the list and in the heading itself — so a citation written in a heading is rewritten first
and enclosed second, and the page carries one anchor inside another. It is the failure an
author is least equipped to diagnose, because nothing in the source is wrong and nothing
else objects: the build succeeds under `--fail-on-warning`. Only reading the finished HTML
finds it, which is the case for the output gate that neither the transform nor §3.6 can
make. So it is reported as its own bucket, with its own advice, and the two directions are
described the way the scanner sees them: two anchors is the failure, one anchor is the
skipped case of the paragraph above, and that one passes.

**A citation in a section heading fails the other way, with everything downstream reporting
it as fine.** The theme rebuilds its "On this page" sidebar from the headings, keeping the
inline markup and dropping the anchor, and wraps the copy in the sidebar's own link; an
in-body toctree at `:maxdepth:` 2 or more does the same, as does an explicitly labelled
`:ref:` to that heading, which collapses the whole heading into one span inside the
reference's link. The output gate counts an enclosing `<a>`, finds one, and scores the
citation linked — it is written not to know one anchor from another, and teaching it to
recognise the transform's own is the coupling this section rejects. The reader is offered
citation text that links to the section it sits in rather than to the section it names, and
every gate is green. Only a page H1 escapes, by accident: it fails as unlinked through
`<title>` and the breadcrumb, as above.

So the transform reports it where the citation is written. A citation inside a section
heading logs a warning, which `--fail-on-warning` turns into a failed build ({issue}`96`),
and the citation is converted all the same — the page renders as it always did, and the
only change is that the build stops. A heading here is a `title` under a
`section` and nothing else: the caption of a table, a topic or an admonition is copied into
no navigation, so a citation in one is a link like any other and warning about it would
fail a build over a link that works. The message names the heading rather than relying on
the location printed beside it, because MyST gives a section title no usable line number —
a document title is located as `index.md::`, and a sub-heading was attributed four lines
early. No citation has ever been written in a heading; this is the authoring rule stated
above — cite a section in body prose — enforced before the first one is.

**What is reported is wider than what is converted.** A citation the author has already
wrapped in a link is not converted — nesting anchors is what that skip exists to prevent —
and from a heading it is reported anyway. Sphinx assembles the navigation with docutils'
`ContentsFilter`, which treats a `reference` and a `pending_xref` alike: both are dropped
and their text kept. A hand-written link is therefore stripped exactly where the transform's
is, and the reader meets the citation under the navigation's own anchor either way. Had the
report followed the conversion, the skip set would have doubled as a way of writing a
heading citation that no gate sees — the near miss made invisible instead of reported, which
is the failure the wider grammar of the output gate above is written to avoid. A literal is
the one skip that survives into the navigation intact, and `<code>` exempts it at both ends,
so a heading quoting `` `spec §3.2` `` as an example is silent and stays so.

(docs-spec-3-8)=
### 3.8 GitHub references

A specification cites the issues and pull requests that shaped it, and did so in two ways:
19 hand-written links, and 40 bare `#N` tokens linking to nothing. The bare form is a link
in an issue comment and plain text in a repository file, which is where these are written,
so it was never a link on Read the Docs either. A published page told a reader the barb
gutter was settled in PR {pull}`40` and left them to find it.

**Every reference to a tephpy issue or pull request is written as an extlink role.**

| context | form |
|---|---|
| MyST | `` {issue}`65` ``, `` {pull}`73` `` |
| reStructuredText, docstrings | `` :issue:`65` ``, `` :pull:`73` `` |

Both render as a linked `#65` and `#73`. The roles are configured once, in
`docs/src/conf.py`, so the URL is stated in one place and a reference costs an author the
number and nothing else. Two forms are therefore errors: a bare `#65`, and a hand-written
`https://github.com/bjlittle/tephpy/issues/65`.

The surrounding prose keeps its own label. ``PR {pull}`19` `` renders `PR #19`, and the
word earns its place: the caption is `#N` whichever role produced it, so without it a
reader cannot tell what they are about to open.

**Why the role is hand-written here, when §3.7 refuses to hand-write a citation role.** The
objection there was that `` :ref:`spec §3.2 <logo-spec-3-2>` `` carries two independent
strings — display text and target — so an author can get the second wrong while the first
still reads correctly, invisibly to both the checker and the build. An extlink carries one:
the caption is `#%s`, generated from the same value that builds the URL. Text and target
cannot disagree, which is §3.7's criterion met rather than waived.

What would remove the authoring step altogether is a build-time transform of the §3.7 kind,
and the token is too weak to carry one. `spec §3.2` is unmistakable in running prose; `#65`
is also a hex colour, a URL fragment, and a comment character followed by a number. §3.7
could derive its target from the text because the text named the document and the section.
`#65` names neither issue nor pull request, and those are different URLs.

**Three exemptions**, none of them a reference. Fenced blocks, for the reason §3.6 gives:
a passage documenting this rule quotes the bare form it forbids. Inline code spans and hex
colours — `` `#808080` `` in the `add_logo` specification and `"#101820"` in the logo tests
are colours whose six digits would otherwise read as an issue number. And the plans, frozen
with their references by §3.4.

The colour exemption is a colour and not, as it first was, any quoted string. A quote mark
is also an apostrophe, so a pair of them spans the words between: an ordinary sentence
about not regressing something would have had its reference blanked instead of judged, and
a one-line docstring holds a pair between its own delimiters. Docstrings are in scope here,
so the wider exemption cancelled the rule exactly where a regression cites its cause.

**The gate.** A pre-commit hook asserts both halves of the rule over the §3.6 corpus,
detecting wider than it validates: it looks for a `#` whether or not a space follows it,
and for any URL under this repository whatever path it names, then judges what it finds
against what a role produces. One pattern doing both jobs could not report a near-miss — a
form the detector failed to match would be neither judged nor mentioned, so a `# 65` with a
space, or a `pulls/65` typo, would read as compliance rather than as something to look at.
Both are reported, each with the reason it is not the form the rule asks for; a URL naming
neither kind, a discussion or a release, is not a reference and is left alone.

The wider first pattern costs something, and the cost is paid where a `#` means no
reference at all. One opening a line is a heading or a whole-line comment and is not
judged; one following something on the line is, so a trailing comment whose first word is a
number is reported as a near-miss it is not. Nothing tells them apart — `see # 65` and
`x = 1  # 3 files` put the same characters in the same places, and only the surrounding
sentence says which is which. A form nobody can see is worse than one somebody rewords.

The two assertions partition the failures rather than overlapping. A `#N` already inside
link text is exempt from the first and caught by the second when the link is ours, which
is what lets an issue in *another* project stay an ordinary link: the roles are scoped to
this repository, so `Unidata/MetPy#1234` is written with its URL, and neither assertion
matches it.

`extlinks_detect_hardcoded_links` is set alongside the hook. It is Sphinx's own matcher for
the second failure, reporting at build time with the exact role to write instead, and it is
deliberately a second implementation rather than a shared one — a bug in the hook's regular
expression is precisely what an independent check catches. Enabling it is safe only because
Sphinx declines to suggest a replacement when the captured value contains a solidus; without
that guard the `user` role's `https://github.com/%s` matches every link to another project's
repository, and the build, running under `--fail-on-warning`, would fail on
`https://github.com/SciTools/tephi`.

One reference on a published page is written by neither of these, and so is caught by
neither: the number towncrier appends to every changelog entry, taken from the fragment's
filename. Its default renders that as plain text, which is this section's first failure one
level up — the reader of a released changelog saw `#40` and could not follow it, exactly as
the reader of a specification did. `issue_format` in `[tool.towncrier]` is set to the same
role a fragment writes by hand, so the generated reference and the hand-written one are the
same form. A generator's output is not in the corpus, which is the general point: the gate
holds for what the repository says, and each generator has to be told separately.

**What this cannot catch**, in a shape §3.6 will recognise. A reference written with the
wrong role of the two — `` {issue}`73` `` where 73 is a pull request — is well formed,
renders identically, and resolves: GitHub redirects between the two paths, so the reader
still arrives where they should, and only the source misnames the kind. Settling it would
mean asking GitHub which each number is, and a hook that needs the network fails offline
and is rate-limited in CI. Review is what narrows this one.

(docs-spec-3-9)=
### 3.9 Snippet execution

The three gates above police how the documentation *refers* to things. None of them reads
what it *tells a reader to type*. The how-to guides are the shop window for the package,
and their code was correct only because it had been checked by hand — `ci-docs.yml` builds
the HTML and then checks citations and links, `sphinx.ext.doctest` is not among the
extensions, myst-nb executes nothing, and sphinx-gallery is configured with no example
directories.

**Every python code block in the user quadrants is executed, as one script per page, in
document order.**

The corpus is derived rather than declared, for the reason §3.6 gives: it is every `.rst`
under `docs/src/howtos/`, `docs/src/tutorials/` and `docs/src/explanation/` — the three
Diátaxis quadrants written for users — so a page is governed from the day it lands, and so
is a page in a subdirectory of one, which is the shape a tutorial series takes.
The reference quadrant is out of scope because it cannot drift — autoapi generates it from
the docstrings and `sphinx_click` from the live CLI — and the developer section is
contributor material whose specifications and plans quote code as illustration. A page with
no python block contributes nothing to run, which is the ordinary case in the explanation
quadrant.

**A python block takes one of two directives, and the extractor knows both.** `code-block`
(with its `code` and `sourcecode` spellings) is the plain form. `.. plot::` is the form that
also renders its block as a figure on the page, and its body is python by definition rather
than by a language argument — so it is matched by a pattern of its own, and contributes its
lines to the page's script exactly as a `code-block:: python` body does. The page shape that
directive brings with it — one form per page, the session options each block carries, the
name every published figure declares — is plots spec §3.2, and is asserted in this gate
rather than in the style guide because this is the gate that already reads every user page
as text.

**A page is a session, not a catalogue.** The second block of the `add_logo` how-to is
`add_logo()` with no argument, which brands the figure the first block bound; executed
alone it has nothing to brand. Running the blocks of a page as one script is therefore not
a convenience but the only reading under which the page is correct — and it binds the
author in return, so the style guide carries the consequence: a later block may rely on an
earlier one's names, and the blocks of a page cannot be reordered freely.

**A fresh interpreter, because that is what a reader pastes into.** Three of the properties
the configuration how-to describes exist only in one: the file is read once, at
`import tephpy`, and inside a test process that import has already happened, so a page
whose whole subject is import-time behaviour could not exercise its own subject. The
isolation is the same argument from the other side — that page calls `tephpy.config.save()`,
which writes to the user's configuration directory, and `tephpy.config.load()`, which
searches it. Run in place, the gate would write into the contributor's own configuration
and read back whatever they happened to have. The subprocess runs with `HOME` and
`XDG_CONFIG_HOME` relocated, `$TEPHPYRC` cleared and the working directory in a temporary
tree, so the cascade sees a controlled empty tree, the save lands in it, and a snippet that
writes a figure to a relative path writes it there. `-W error` mirrors the suite's own
`filterwarnings`, so a snippet that warns fails exactly as one that raises does.

**Reaching the end of the script is not the whole of running it.** Matplotlib defers most
of its validation to draw time: `emphasis={0.0: {"color": "notacolour"}}` is accepted
without complaint and raises `ValueError: Invalid RGBA argument` only when the canvas is
drawn — the class of defect {issue}`116` describes, where a value of the right type is
still not a value. A how-to whose figure cannot be rendered would pass a gate that stopped
at the last statement, and a page showing a plot is exactly the page where that matters.
Each page's script therefore ends by drawing every figure it leaves open. This is free to
adopt: the figures the how-tos build today draw clean under `-W error`.

**The generated script is line-aligned with its page.** Each block's code occupies the line
numbers it occupies in the `.rst`, the gaps padded with blank lines, so a traceback naming
line 80 names line 80 of the page. Blank padding is safe because a block's lines are
contiguous in the source too, so it only ever falls between blocks. The alternative —
marker comments to count back from — asks a reader of a failure to do arithmetic at the
moment they are least inclined to.

**There is no way to mark a block as not for execution.** A block a reader is invited to
copy, which cannot run, is a defect in the page rather than a case for the gate to
accommodate. An exemption with no reason attached is the form that cancels a rule quietly,
because the cheapest way to make a failing snippet pass is to reach for it; if one is ever
genuinely needed, the block that needs it will say what the reason is, which is not
knowable now. `:nofigs:` is not that exemption and does not become one: it suppresses the
*picture*, and the block it sits on runs here like any other.

**Refusing its own empty input.** A gate that derives its corpus can be made to check
nothing by an edit that has nothing to do with it — a renamed quadrant directory, or a
directive spelling the extractor stops recognising, after which every page passes by not
being found. Three assertions therefore stand apart from the per-page cases: the quadrant
directories exist, the discovered set is not empty, and the pages known to carry code are
among those yielding blocks. Membership names them, not a block count, because a count is a
figure that has to be re-measured to stay true. A fourth guards the near miss the other
three cannot see: a page of eight good blocks and one spelled `pycon` or `python3` satisfies
membership, and its odd block is passed over in silence. A block whose language means python
and is not `python` is therefore reported — every spelling Pygments resolves to the python
or the python-console lexer, both names of each, since `pycon` and `python-console` are one
lexer under two labels and only one of them looks like a near miss. So is a block that names
no language at all, in each of the three shapes that takes. A directive can omit it.
reStructuredText's other code-block form — a paragraph ending in `::`, a blank line, then an
indented body — is not a directive at all, and is invisible to an extractor that reads
directives; the blank line is part of the shape rather than a formality, because written
without one the same two lines are a definition list or a field, and docutils renders
neither as code. A doctest block — a paragraph opening `>>>` — needs neither a directive nor
a marker, and docutils renders it as a console session whatever the prose around it says.
Sphinx highlights the first two with whatever `highlight_language` is set to, and `conf.py`
leaves it at the default, which highlights as python; the third is a python console session
by construction. Any of them can be python on the page and invisible here. What the gate
looks for has to be wider than what it accepts, or a near miss reads as compliance.
They are separate test functions rather than parameters of the per-page one because pytest
reports an empty parametrisation as a skip, so an extractor returning nothing would leave
the summary line green.

The gate is an ordinary test module, so it runs in every test environment on every Python
the project supports — which is more than a docs-build gate could do, the docs build having
one environment.

**The extractor reads the source as text, so it owes docutils an exact answer.** Sphinx is
in the `docs` feature and not in `test`, and a gate that always-skips in the CI matrix is
not a gate — so the block boundaries are found by reading lines rather than by parsing. That
buys the environments back at the price of having to agree with docutils on where a block
starts and ends, and two of its rules are the ones a line reader gets wrong. A directive's
options end at the blank line reStructuredText requires before the content, not at the last
line that looks like an option: a wrapped `:caption:` continues onto a line matching nothing,
and stopping there reads the caption as the code and drops the block. And a block is
dedented by its least-indented line, not by its first: one that opens deeper than it ends
keeps that opening indentation, and measuring from the first line ends the block at the
outdent and silently drops every statement below. Both fail the same way, which is the
dangerous way — a short block that runs clean, standing in for a longer one that would not.

**Why not `sphinx.ext.doctest`.** It would mean rewriting every `code-block:: python` as
`testcode::`, adding per-page `testsetup::` blocks to carry the session a page's blocks
form, and maintaining a second execution path in the docs environment, for the same
coverage. Its one real advantage is output checking, and the only blocks with output
are the CLI transcripts, whose markers `tests/test_cli.py` already pins.

**What this cannot catch.** Execution proves that a snippet runs. It says nothing about
whether it does what the sentence above it says, and the two fail independently: {pull}`113`
fixed a passage whose snippet ran perfectly and whose surrounding prose was wrong, so this
gate would have passed it. That half is an authoring rule rather than a check — where a
snippet's surrounding prose makes a behavioural promise, a test pins the promise — and the
style guide carries it. Nor does this gate read the rendered page: a block Sphinx fails to
render is a docs-build failure, and a block that renders while saying something false is
review's.

Drawing a figure is likewise not the same as looking at it, and comparing the result
against a baseline image is deliberately out of scope. `pytest-mpl` is a decorator on an
in-process test function returning one figure, which is not the shape of a subprocess
running a page; its baselines are sensitive to the freetype and matplotlib versions, so
they are pinned in one environment while this gate runs in every one; and a page's figures
are anonymous and positional, so a baseline could only be keyed on figure order and would
break when an author inserts a snippet. What a how-to's figures should look like is already
pinned by `tests/plotting/test_images.py`, against the APIs the pages call.

Those three reasons are each a statement about where *this* gate runs, and none of them
rules out a comparison somewhere else. Plots spec §3.5 is that somewhere else: a
documentation-side gate over the images a build published, in the one environment that
builds them, keyed on the name each figure declares. It takes nothing from this section —
this gate gains no baselines — and the sentence above stays the reason it is narrow.
`tests/plotting/test_images.py` pins the constructions, in the test matrix, on every
supported Python; plots spec §3.5 pins the artifacts, once, where they are built.

What the terminating draw validates is each figure's *final* state, because there is one
draw and it is at the end. Where a later block replaces an earlier one's artists — three
blocks of `emphasis.rst` call `ax.isotherms(...)` on the same axes, and each supersedes the
one before it — the superseded artists are never drawn, and an undrawable value in the block
that made them raises nothing. Measured: `"color": "notacolour"` in the later block fails that
page, and the same mutation in the earlier one passes. Drawing after every block would close
it, and would cost the property that makes a failure readable: the draw would have to be
interleaved into the script at the line numbers the page's own prose occupies, so a
traceback would no longer name the page's lines. The end of the script is the only place a
statement can be added without disturbing the alignment above it.

Only `.rst` is read. myst-nb is among the extensions, so a Markdown page in a user quadrant
would build and publish like any other and this gate would not see it — the corpus is scoped
to `.rst` above because that is what the user quadrants are written in, and the first author
to reach for Markdown should meet that boundary here rather than discover it as a page the
gate silently exempts.

That sentence was an argument, and it is now a mechanism.
`test_no_user_page_is_written_in_a_format_this_gate_cannot_read` fails on any `.md` or
`.ipynb` under the three quadrants — the two suffixes myst-nb registers beside the `.rst`
Sphinx reads by default, `source_suffix` being unset. Plan 7c was the first delivery that
would have reached for one, spec §8.6 having called the tutorials notebooks until it was
corrected to match plots spec §3.1 and this section. `nb_execution_mode` is `off` in
`docs/src/conf.py`, and with no notebook source in a user quadrant that setting is a guard
rather than a policy: were one to appear, the build would render its stored outputs as
fact, which is a transcript nobody ran. Both halves of that — the format and the execution
— now fail loudly instead of passing quietly.

(docs-spec-4)=
## 4. Canonical usage

A reader meets `(spec §3.2)` in the rendered documentation for `plot_barbs`, follows the
developer guide to *Design specifications*, and lands on spec §3.2 of the parent document
by its anchor. Reading it, they are entitled to assume it describes tephpy as it stands.

A contributor changing behaviour that a specification section describes updates that
section in the same pull request. A contributor who finds the code and the specification
disagreeing has found a specification defect, and reports it as one.

A figure is held to that same contract, and most figures cannot keep it. A number measured
from content a pull request can change — how many citations resolve to a document, how many
links a build renders — is true when written and false soon afterwards, with nothing to
report that it has turned: the gates of §3.6 and §3.7 assert properties, not totals, and a
count nobody re-measures is a specification defect on a schedule nobody controls. So a
figure of that kind is not written here. What is written is the invariant and how to obtain
the number, leaving the counting to whichever gate is current by construction. The one
figure that stays is the one recording what was measured when a decision was taken: it is
stated in the past tense, anchored to that decision, and true permanently, because it is a
fact about the decision rather than about tephpy ({issue}`94`).

An item that cannot be settled now is written into the specification's open-item section —
spec §10 or spec §11 in the parent, §Scope elsewhere — with a status tag, filed as an
issue labelled `design: open`, and cited from the item.

(docs-spec-5)=
## 5. Migration

One-off work, performed once and then finished:

1. `git mv` both directories under `docs/src/developer/`; add the `exclude_patterns`
   entry; record the superpowers path preference in `AGENTS.md`.
2. Repoint `MANIFEST.in`. `prune docs/superpowers` is load-bearing — setuptools_scm puts
   every tracked file in the sdist, and the rest of `docs/` ships — so after the move that
   line silently stops matching and the plans start shipping. It becomes
   `prune docs/src/developer/plans`. The specifications ship from then on, which is right:
   they are published documentation like every other page under `docs/src/`.
3. Add `docs/src/developer/specs/index.rst` and reference it from the developer guide
   toctree.
4. Add anchors to the 25 numbered headings in the parent specification and the 15 in the
   `add_logo` specification.
5. Repoint the parent specification's header link to the plans at an absolute GitHub URL.
   It is the build's only warning, and it fails precisely *because* the plans are
   deliberately unpublished: `../plans/` still resolves in a checkout and on GitHub, but
   Sphinx cannot resolve a link to a page it was told not to build. An absolute URL keeps
   the affordance for a reader of the published page, who has no checkout to fall back on.
6. Correct the stale repository paths (§3.4): spec §10 of the parent specification names
   `docs/superpowers/plans/`, `README.md` links to `docs/superpowers/specs` on GitHub, and
   twelve plans name their originating specification by its old path. The README link
   becomes the *published* page rather than a second GitHub tree path: the Read the Docs
   project is live and builds `latest` from `main`, so once this change lands the rendered
   collection — toctree, namespace table and all — is what a reader following "the design"
   should land on. What is *not* corrected: the code blocks in three plans that reproduce
   a file's contents or a PR or issue body already published. Those record what was
   written, not where a document lives, and §3.4 does not reach them.
7. Audit spec §10's sixteen items and spec §11's four questions, establish the true status
   of each, apply the §3.5 tags, and file `design: open` issues for whatever is genuinely
   open.

(docs-spec-6)=
## 6. Verification

The docs build runs with `--fail-on-warning --keep-going` and nitpicky cross-references,
and `pixi run docs` runs the output gates of §3.7 and of the documentation-link check
after it, so a clean `pixi run docs` exiting 0 is the primary gate. Beyond it:

- `_build/html/developer/plans/` does not exist, and no plan page is reachable.
- The sdist carries the specifications and not the plans (item 2).
- Both existing specification pages render, and this one alongside them.
- Every anchor named in §3.3 appears as a section `id` in the built HTML.
- Every distinct `spec §N` and `logo spec §N` citation in `src/` and `tests/` corresponds
  to an anchor that exists. This began as a one-off check at implementation time; §3.6
  makes it continuous.
- No citation-shaped text survives outside a link in the built HTML, and none is nested
  inside a link the build itself made (§3.7). The gate prints what it counted on each run,
  which is where those numbers belong (§4); the property is not beyond the primary gate but
  part of it, checked on every `pixi run docs`. It passes more citations as literals than a
  reader would count from §3.7 above, because it does not read `_modules/`, where viewcode
  renders the same docstrings verbatim as Python: those are code rather than prose, and
  reading those pages too changes the count and not the verdict, every one of them already
  covered by `<pre>`.
- No citation is written in a section heading, which the transform reports as a warning and
  `--fail-on-warning` turns into a failed build (§3.7) — whether the build would link it or
  the author linked it by hand, the second being reported without being converted. It is the
  one placement the output gate scores as linked while the reader meets it unlinked.
  Mutation shows the pair is load-bearing in both directions: taking the report back to only
  what the transform converts fails the hand-linked case and no other, and widening it to
  every skipped citation fails the literal case and no other.
- No bare `#N` and no hand-written `bjlittle/tephpy` issue or pull-request URL survives in
  the corpus (§3.8), and every reference renders as a link on the built specification
  pages. At the time §3.8 landed that was 59 references converted — 40 that linked to
  nothing and 19 written as URLs.

- Every python block in the user quadrants executes clean, per page and in document order
  (§3.9), in every test environment, and every figure a page leaves open draws clean.
  Mutation is what shows the gate is load-bearing rather than merely green: renaming a
  keyword a snippet passes fails that page's case and no other; narrowing the directive the
  extractor recognises fails the membership assertion rather than passing every page
  vacuously; respelling one block's language as `pycon` or `python-console`, rewriting it as
  a bare `::` block, recasting it as a bare `>>>` transcript, or deleting its language
  altogether, fails that assertion while membership still passes; a block whose `:caption:`
  wraps onto a continuation line, and one whose first line is indented deeper than the lines
  below it, both execute in full — before the fixes the extractor truncated them to a caption
  fragment and to that opening line, and both truncations ran clean; a page added in a
  subdirectory of a quadrant is found and run like any other; and giving a
  snippet a typed-correct undrawable value — `color="notacolour"` — fails only while the
  terminating draw is there to catch it. That last one has a condition, or it is not
  reproducible: the mutated block must be the last on its page to draw the artist it styles,
  because only each figure's final state is drawn. Mutating an earlier block whose artists a
  later one replaces leaves the suite green, and says nothing about the draw.

A trial build of the moved specifications has already been run: 1,533 lines of Markdown
through myst produced exactly one warning, the `../plans/` link of item 4 above.

(docs-spec-7)=
## 7. Scope

Not in this change:

- **Rejected** (2026-08-03) — **editing the specifications' technical content.** They are
  published as they stand. The §3.5 pass adds status tags and issue pointers; it does not
  rewrite the reasoning.

Settled since:

- **Resolved** (2026-08-04, PR {pull}`89`) — **the citation-integrity hook of §3.6 is in place.**
  The 36 citations that did not meet the §3.2 rule were corrected with it: eleven in `src/`
  and `tests/` that carried a bare `§N` in a file owning no sections, and 25 in the two
  child specifications where a bare `§N` meant the *parent's* section and resolved
  silently to the child's own.
- **Resolved** (2026-08-04, PR {pull}`90`) — **citations render as cross-references** (§3.7).
  The item was deferred here as "101 rendered citations across 60 public objects"; both
  figures were wrong, and the count measured then was 95 across 54. Neither turned out to be
  the number that mattered, because the conversion happens in the doctree rather than in
  the sources: it reaches every citation the site renders and edits none.
- **Resolved** (2026-08-13, PR {pull}`132`) — **the counts this document recorded drifted
  silently.** Every figure measured from content a pull request can change — the §3.2 table
  and the resolving counts beside it, the citations naming one section in §3.3, the section
  signs and the link totals in §3.7 and §6, and the zero pages §3.7 counted as writing a
  citation inside a link — has been replaced by the invariant behind it
  and the way to obtain the number. What remains is stated in the past tense and anchored to
  the decision it was measured for. §4 carries the rule, so a figure added later is judged
  by it rather than by this entry.
- **Resolved** (2026-08-13, PR {pull}`132`) — **a citation in a section heading reached the
  reader unlinked with every gate green** (§3.7). The theme copies the heading into its page
  navigation without the anchor, and the output gate counts the navigation's own link and
  scores it linked. The transform warns instead, which fails the build where the citation is
  written; teaching the gate to tell its own cross-references from any other link was
  rejected as the coupling §3.7 exists to avoid. The report covers a citation the author
  linked by hand, which the transform skips rather than converts: the navigation strips that
  link the same way, so following the conversion would have left the skip set as a way of
  writing the defect unseen.

(docs-spec-8)=
## 8. References

- {issue}`65` — publish the design specifications
- {pull}`73` — the living/point-in-time contract
- {issue}`85` — render citations as cross-references
- {issue}`86` — the citation-integrity gate
- {issue}`94` — the citation counts recorded in this document drift silently
- {issue}`95` — the notebook citation path is verified only against hand-built fixtures
- {issue}`96` — a citation in a section heading fails silently
- {issue}`114` — nothing executes the code examples in the how-to guides
- {issue}`116` — a configuration value of the right type is not checked for validity
- [`bjlittle/geovista`](https://github.com/bjlittle/geovista) — the developer-section precedent
- [MyST targets and cross-referencing](https://myst-parser.readthedocs.io/en/latest/syntax/cross-referencing.html)
