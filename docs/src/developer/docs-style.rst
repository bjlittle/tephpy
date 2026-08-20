Documentation Style
====================

Title Style
-----------

Hand-authored page and section titles use Chicago Manual of Style headline
style: capitalize the first and last words and all major words; lowercase
articles, coordinating conjunctions, prepositions, and the infinitive "to".

Preserve literal case for: code and API identifiers, filenames, config keys,
CLI commands, and paths; project and library names in their own casing
(matplotlib, numpy, pint, metpy, pixi, tephpy); and acronyms and scientific
symbols (CAPE, CIN, LCL, WMO, SPEC 0). The rule does not apply to
autoapi-generated API pages, numpydoc section headers, changelog entries, or
anything that is a full sentence (captions, admonition text, docstring
summaries), which use sentence case. Bibliography entries reproduce the
source's published title.

Glossary
--------

The glossary is written for software engineers, not meteorologists. Each entry
gives the concept in one plain sentence, then how it appears in ``tephpy`` (the
data, its units, the API type that carries it), and links deeper physics to the
Explanation quadrant.

Cross-reference the *first* mention of a glossary term per page with
``:term:``, in narrative prose only — never in titles, code blocks, API
signatures, or admonition labels. Within a definition, link related terms but
never the term itself. Keep one canonical spelling per concept.

When a definition names a documented API, cross-reference it with the matching
Sphinx domain role — ``:class:``, ``:func:``, ``:meth:``, ``:mod:``, or
``:obj:`` — so the reader can follow the link straight into the API
documentation, rather than quoting the name as a plain double-backtick literal.
Keep the accessor idiom the entry reads in as the link's display text, so
``calc.parcel_path`` and ``ax.shade_cape`` stay legible:

.. code-block:: rst

    avoid:   ``calc.parcel_path(...)`` computes a parcel's ascent
    prefer:  :func:`calc.parcel_path(...) <tephpy.calc.parcel_path>` computes a parcel's ascent

Third-party objects (matplotlib, metpy, numpy, pandas, pint, xarray) resolve
the same way through intersphinx — see :ref:`cross-references` below. Reserve
plain double-backtick literals for names with no documentation target: private
members, dataclass fields already reachable through their linked owner,
external tools without an intersphinx inventory (pixi), option strings, and
keyword arguments. This mirrors the changelog fragment convention documented in
``changelog/README.md``.

.. _cross-references:

Cross-References
----------------

Third-party APIs resolve through intersphinx. Every third-party package the
documentation names — matplotlib, metpy, numpy, pandas, pint, xarray — has its
inventory registered in ``intersphinx_mapping`` in ``docs/src/conf.py``, so a
domain role such as :func:`metpy.calc.moist_lapse` or :class:`pint.Quantity`
links straight into that project's documentation. When you first cite an API
from a package that is not yet mapped, add its ``objects.inv`` location there in
the same change, so the reference resolves rather than rendering as plain text.

Parameter and return *types* are cross-referenced automatically. With
``numpydoc_xref_param_type`` enabled, numpydoc turns each type in a
``Parameters``/``Returns`` block into a link: fully-qualified names
(``pint.Quantity``, ``numpy.ndarray``) resolve through intersphinx, tephpy's own
short type names (``Sounding``, ``Profile``, the ``Tephpy*Error`` exceptions) are
mapped to their targets in ``numpydoc_xref_aliases``, and descriptive connective
words (``optional``,
``of``) are listed in ``numpydoc_xref_ignore``. Write the type as its plain
qualified name — ``pint.Quantity``, not a hand-written role — and let the
configuration link it.

``nitpicky`` is enabled, so an unresolved cross-reference is a warning and — via
the docs Makefile's ``--fail-on-warning`` — fails the build. A reference that
does not resolve is therefore caught automatically; a clean build is proof the
links land. The only sanctioned exceptions live in ``nitpick_ignore`` in
``conf.py``: annotation types autoapi emits as ``py:class`` xrefs while numpy
publishes them as ``py:data``/``py:attribute`` (``numpy.typing.ArrayLike``,
``numpy.typing.NDArray``, ``numpy.float64``), the ``Ellipsis`` in variadic
tuples, and parameter defaults from the private ``_constants`` module. Do not
extend that list to silence a reference you can instead make resolve — add a
``numpydoc_xref_aliases`` entry or write the full dotted name.

.. _specification-citations:

Specification Citations
-----------------------

Cite a design specification as plain text — ``spec §3.2``, ``logo spec §1``,
``docs spec §3.6`` — and never as a hand-written role. The build turns each one
into a link to the section it names, so writing the role yourself is not an
improvement but a hazard: a role carries a second string that can disagree with
its display text, and

.. code-block:: rst

   :ref:`spec §3.2 <logo-spec-3-2>`

has the right text against the wrong document while resolving perfectly cleanly,
so neither the citation checker nor a nitpicky build has anything to object to.
Writing the citation once means the text and the target cannot disagree.

The prefix names the document and is load-bearing. A bare ``§N`` means *this*
document's §N, which makes it safe inside a specification and an error anywhere
else — a docstring owns no sections. Where several sections are cited together,
the prefix carries across the run, so ``spec §3.3, §10`` and ``spec §3.1/§10``
each name two sections of the parent specification. The run continues across a
comma or a solidus, and across nothing else: writing ``and`` in place of either
separator ends it, leaving the second citation bare. A bare ``§N`` opening the
next sentence falls back to the containing document rather than inheriting, for
the same reason.

A citation must also sit whole on one line, and so must a compound run — one
wrapping after its comma or solidus strands the continuation, which falls back
to the containing document instead of inheriting the prefix it was written
under. Only horizontal whitespace joins a prefix to its section number, and the
same holds of the gap after a separator, so a prefix stranded at the end of a
line with its number wrapped onto the next is no longer part of the citation:
what remains is a bare ``§N``, rejected outside a specification and read as a
local reference inside one — either way, not the citation that was written. The
rule is what keeps the displayed text and the link target from disagreeing,
because the hook reads one line at a time while the build reads a whole
paragraph, and a citation able to span the wrap is one they can read
differently.

Cite a section in body prose. Four other places will not carry a citation, and
each fails the documentation build rather than rendering wrongly. A page title is
linked like any other heading, but Sphinx copies the title into ``<title>`` with
the markup stripped, and the theme repeats it in the breadcrumb without the
anchor, so the citation reaches the reader as plain text in the browser tab and
above the page. A toctree ``:caption:`` is a directive option rather than text
the build can rewrite, and renders twice — once where the toctree sits and once
in the sidebar. A ``.. raw:: html`` block and an API signature — a parameter's
default value included — are left alone deliberately, because the build rewrites
neither raw output nor code. Name the section in the surrounding prose instead.

A section heading is worth avoiding for a second reason, and it is the one the
build names. The theme rebuilds its "On this page" navigation out of the headings,
keeping the text and dropping the anchor, and wraps the copy in the navigation's
own link — so the citation *is* a link, to the section it sits in rather than to
the section it names, and the check on the built HTML cannot tell one anchor from
another. The build therefore warns about a citation inside a heading, naming the
heading, and ``--fail-on-warning`` turns that into a failure. Writing the link
yourself does not avoid it: the navigation strips an author's link the same way,
so a heading citation is reported whether the build would link it or you already
have. Cite the section in the prose below the heading instead.

A heading is worth avoiding for a third reason, which fails differently again. A
``.. contents::`` directive links every heading it lists — in its own list and in
the heading itself — and it does so after the citation has already become a link,
so the page ends up with one anchor inside another. That is invalid HTML, which a
browser restructures silently, and Sphinx reports nothing: only the check on the
built HTML notices. Writing a citation inside a link yourself is the same
collision from the other side, and in body prose it is *not* an error — the build
leaves such a citation as plain text rather than nesting a link in a link, and
your own link is the one the reader follows. In a heading it is reported, for the
reason above.

A pre-commit hook checks that every citation names an anchor that exists, and the
documentation build checks that every rendered citation became a link. Both are
specified in the published specifications design: docs spec §3.6 covers the hook,
and docs spec §3.7 covers the build.

.. _github-references:

GitHub References
-----------------

Refer to a tephpy issue or pull request with the matching extlink role, never as
plain text and never by URL. Write ``:issue:`65``` and ``:pull:`73``` in
reStructuredText and in docstrings; write ``{issue}`65``` and ``{pull}`73``` in
the Markdown specifications. Each renders as a linked ``#65`` or ``#73``.

This is the opposite instruction to the one above, and the same reasoning decides
both. An extlink generates its caption from its value, so there is one string and
the text cannot disagree with the target; a hand-written ``:ref:`` carries two.
Writing the role is what keeps them together here, and what would pull them apart
there.

Keep the word that says which kind it is. ``PR :pull:`19``` renders ``PR #19``,
and a reader who sees only ``#19`` cannot tell what the link opens, because the
caption is the same for both roles.

Two things follow. An issue in another project has no role — the two above are
scoped to this repository — so write it as an ordinary link with its own URL.
And a hexadecimal colour is not a reference: keep it in literal markup —
``#808080`` — or inside a string, which is where a colour belongs anyway.

A pre-commit hook rejects both a bare ``#65`` and a hand-written
``https://github.com/bjlittle/tephpy/issues/65``; the documentation build rejects
the second again through ``extlinks_detect_hardcoded_links``, naming the role to
write instead. Neither can tell ``:issue:`` from ``:pull:`` — GitHub redirects
between them, so the wrong one of the two still reaches the right page. The rule
is specified in docs spec §3.8.

.. _documentation-links:

Documentation Links
-------------------

A few tracked files link into the documentation by absolute URL, because they are
outside the Sphinx project and have no role to write instead: ``README.md``, the
repository's landing page, and a script that sends a contributor to the page
explaining why it failed them. Such a link is invisible to everything that checks
the rest — ``nitpicky`` sees only the references the build resolved.

Write the URL as ``https://tephpy.readthedocs.io/en/latest/<page>.html``,
optionally with a fragment. A per-pull-request preview host
(``tephpy--<pr>.org.readthedocs.build``) is where a documentation change is
verified rather than where a link belongs — Read the Docs deletes the preview when
the pull request closes — and ``latest`` is the only version published, so
``en/stable`` and a path that drops the version alike resolve nowhere. A URL whose
path never reaches ``.html`` names no page the gate can look up, so it is passed
over rather than judged — as the Read the Docs badge at the top of the README is,
pointing at the base with a query string and no path.

In ``README.md``, write the link as a Markdown reference — ``[CAPE][cape]`` in the
prose, with the target defined in the block at the foot of the file — so the prose
stays readable and each URL is stated once:

.. code-block:: markdown

    [cape]: https://tephpy.readthedocs.io/en/latest/reference/glossary.html#term-CAPE

Link the *first* mention of a glossary term in the README and no more, as on a
documentation page. Take the fragment from the built page rather than deriving it:
a glossary anchor is ``term-`` followed by the term with its case preserved and
each run of non-alphanumeric characters collapsed to a single hyphen, so ``CAPE``
gives ``term-CAPE`` and ``Normand's point`` gives ``term-Normand-s-point``. Label
the reference in lower case — Markdown labels are case-insensitive, and a lowercase
label is hard to mistake for the fragment, which is not.

The documentation build checks these links. ``check_documentation_links.py`` reads
each URL out of every file named in its ``SOURCES`` constant and looks it up in the
HTML just built, failing when a URL naming a page is written some other way, when
the page is absent, or when the fragment names no ``id``. Renaming a glossary term
or moving a page therefore fails the build, rather than leaving a link pointing
into a 404 that nobody notices.

A new file that writes such a URL is checked only once it is added to ``SOURCES``;
the gate reads that list and not the repository, so that a URL quoted in a test
fixture or frozen into an implementation plan is left alone. A file that stops
carrying a documentation link fails the gate rather than dropping out of it in
silence, so removing the last link means removing the entry too — and emptying
``SOURCES`` entirely fails the same way, rather than passing on a search of
nothing.

Code Examples
-------------

Every python block in the how-to, tutorial and explanation quadrants is executed
by ``tests/test_docs_snippets.py``, as one script per page and in document order,
ending with a draw of every figure the page leaves open. Four rules follow from
that, and the gate itself is specified in docs spec §3.9.

A page is a session, not a catalogue. A later block may rely on a name an earlier
one bound — ``add_logo()`` with no argument brands the figure the block above it
created — so the blocks of a page cannot be reordered freely, and a block that
would not run after the ones above it is a page defect rather than a gate problem.

There is no way to mark a block as not for execution. A block a reader is invited
to copy and which cannot run is the defect; the answer is to fix the snippet, or
to stop presenting it as one. A REPL transcript is code too — write it as a script
in a ``python`` block rather than as ``pycon``, which the gate reports rather than
skips.

Snippets carry no linter directives. ``# noqa`` and ``# type: ignore`` suppress
nothing in a ``.rst`` file, and they ask a reader pasting the line to satisfy
tooling they are not running. Where an import looks unused, say why it is there
instead — ``import tephpy  # registers the "tephigram" projection``.

Where a snippet's surrounding prose makes a behavioural promise, a test pins the
promise. Execution and truth fail independently: :pull:`113` fixed a passage whose
snippet ran perfectly and whose prose was wrong, and the gate would have passed it.
Name the test in the pull request that adds the prose, so the connection is on the
record.

Published Figures
-----------------

A user page either publishes figures or it does not, and the two forms never mix.
On a page that does, every python block is a ``.. plot::``, which renders the block
and shows its source. Leaving one plain ``code-block:: python`` behind is the defect
the rule exists to stop: that block runs in the snippet gate and not in the
documentation build, so the build's namespace silently loses whatever it bound. The
rules below are specified in plots spec §3.2 and asserted by
``tests/test_docs_snippets.py``; the images themselves are pinned against
``docs/baseline`` by ``.github/scripts/check_docs_figures.py`` (plots spec §3.5).

One picture per point the prose makes, not one per block. A page is a session in
which a later block supersedes an earlier one — three blocks of :ref:`howto-emphasis`
call ``ax.isotherms(...)`` on the same axes — so a picture after every block would
sometimes show a state the surrounding prose has stopped describing. A section making
two distinct points publishes two: :ref:`howto-emphasis`'s "Configure It Once" section
shows the context-manager idiom and then a diagram opting out of it, and
:ref:`howto-logo`'s "On the Plot or Around It" section shows the axes-and-figure
targeting and then the no-argument call that brands whichever figure is current.

Each block carries its options by five rules:

- The first block on the page carries ``:context: reset``. Without it the page opens
  with whatever the previously built page left behind, and build order is not a
  property any page controls.
- Every later block carries ``:context:`` or ``:context: close-figs``. A block with
  no ``:context:`` at all runs in a fresh namespace, where the page's imports never
  happened; ``close-figs`` is what opens a section that starts its own figure. The
  two values do not combine — the directive takes exactly one of nothing, ``reset``
  or ``close-figs``.
- A block whose picture would add nothing, or should not be published, carries
  ``:nofigs:``. It still runs, so the session is unbroken and the snippet gate still
  covers it. That is why a plain ``code-block:: python`` is not the answer for such a
  block.
- Every figure-producing block carries a ``:filename-prefix:``, unique across the
  documentation. Unnamed, the image takes a per-document counter, so inserting a
  section renumbers every image after it and every baseline with them. A name and a
  ``:nofigs:`` on the same block is a figure declared and never built, which the
  figure gate reports. Spell the option in lowercase, indent it with spaces, and
  keep the value to one run of letters, digits, dots and dashes: Sphinx accepts
  more than that, and the gate reports anything else as a near miss rather than
  reading it as a declaration.
- No file-argument form. ``.. plot:: script.py`` renders the figure from a file, and
  the code a reader is invited to copy has to be on the page.

Nothing a published block does may outlive it. Every block on every page executes in
the Sphinx process, with ``sys.modules`` shared across the whole build, and
``:context: reset`` clears the namespace the blocks run in without touching module
state. So demonstrate configuration with :meth:`tephpy.config.context` rather than by
assigning to ``tephpy.config``: a bare assignment applies to every axes created
afterwards, on that page and on every page built after it. A page whose subject *is*
global, persistent configuration publishes no figures — :ref:`configure-from-a-file`
is that page (plots spec §3.3).

When a figure is meant to change, re-bless it in the same change that caused it:

.. code-block:: console

    $ pixi run docs-figures

Read the diff before committing. That command approves whatever was rendered,
a regression as readily as a correction.

It refuses outright, without touching a file, when the gate cannot read a
declaration — a near miss as above, or a page the gate expects to publish that has
stopped declaring anything. Fix the declaration and run it again. The baseline that
declaration named is a live pin, and to a scan that cannot read the declaration it
looks exactly like the orphan of a renamed section, which this command removes.

Gallery Examples
----------------

The gallery is scraped from ``src/tephpy/examples``, which ships in the wheel:
every entry is a module a reader can download, and also one an installed tephpy
can run with ``tephpy examples run <name>``. The rules below are specified in
gallery spec §3.2, §3.3, §3.6, and asserted by
``tests/examples/test_examples.py``.

The gallery shows what the package draws. Everything else is a how-to. An
example whose subject is not a picture — getting data in, configuring the
package, installing it — belongs in the how-to quadrant, however much code it
carries (gallery spec §5). An example that happens to load data is fine; the
subject is what is tested, not the API surface touched.

Every module is named ``plot_*.py``, and the prefix is load-bearing.
sphinx-gallery's ``filename_pattern`` defaults to ``/plot``, and only a matching
file is *executed*: a file outside the pattern is still rendered, silently, with
no figure and no error.

Every module defines ``main()``, which builds the figure and returns it, and
closes with the guard that shows it:

.. code-block:: python

    def main() -> Figure:
        ...
        return fig


    if __name__ == "__main__":
        main()
        plt.show()

One construction then serves four consumers — sphinx-gallery, which executes the
file as ``__main__``; ``tephpy examples run``; ``pytest-mpl``, which decorates a
function returning a figure; and the reader running the downloaded script.
Showing inside ``main`` would cost the third of those, and the pinned figure
would then be a claim about the test rather than about what was published.

An example takes its data from :mod:`tephpy.samples`, reaches no network, and
writes no file. The documentation build executes it, so a ``savefig`` call would
leave an artefact in the generated tree on every build; the vector-output line
appears in an example's prose instead, shown and not run.

Add a new example to ``REGISTRY`` in ``src/tephpy/examples/__init__.py``, in the
position it should occupy. Registry order is gallery order is
``examples run --all`` order, and the tests read it: an unregistered
``plot_*.py`` fails them rather than disappearing quietly. Pass
``figsize=(8.0, 4.0)`` at the example's own ``subplots`` call — sphinx-gallery
calls ``plt.rcdefaults()`` before every example, so a configured default is
discarded before the first line runs.

Tags come from a closed vocabulary — ``analysis``, ``barbs``, ``diagram``,
``indices``, ``isopleths``, ``metpy``, ``overlay``, ``shading``, ``sounding`` —
two to four per example, declared in the flag sphinx-gallery reads:

.. code-block:: python

    # sphinx_gallery_tags = ["analysis", "shading", "indices", "sounding"]

They render on the page and drive the index's filter buttons, so a ``barb``
beside a ``barbs`` splits the very index the feature exists to build. Widening
the vocabulary means editing ``VOCABULARY`` in
``tests/examples/test_examples.py``, which is deliberate. Spell the flag exactly:
sphinx-gallery parses ``sphinx_gallery_tag`` into a differently-keyed entry and
discards it in silence, with no warning to fail the build on — which is why the
test reads the flag out of the source text rather than asking the parser.

Leave the flag visible. ``sphinx_gallery_start_ignore`` would hide it from the
page, but the source is the point on a page whose purpose is showing source.

Attribute Documentation
-----------------------

The API reference is generated by ``sphinx-autoapi``, which parses the source
*statically* and therefore never reads comments. A Sphinx ``#:`` doc-comment —
whether on the line above an assignment or trailing it inline — is silently
dropped from the rendered page; only ``sphinx.ext.autodoc`` (which imports the
module) honours ``#:``. Document a rendered attribute one of two ways instead:

- Prefer the numpydoc ``Attributes`` section of the owning class's docstring.
  This is the established pattern for tephpy's public dataclasses
  (:class:`~tephpy.sounding.Sounding`, :class:`~tephpy.calc.Profile`,
  :class:`~tephpy.calc.SoundingIndices`) and keeps every field's description in
  one place alongside its type.
- When an attribute must carry its documentation at the point of definition,
  use a PEP 224 *attribute docstring*: a triple-quoted string on the line
  *below* the assignment. autoapi renders it; a ``#:`` comment in the same spot
  renders nothing.

Reserve ``#:`` comments for annotations on private members — the private
``_constants`` and ``_config`` modules, and ``_``-prefixed module constants —
which autoapi excludes from the reference regardless of comment style. There the
choice is purely stylistic, and ``#:`` reads naturally above a constant.
