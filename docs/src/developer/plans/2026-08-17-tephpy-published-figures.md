# Published Figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Point-in-time record.** This plan states what was intended *before* implementation and is not updated afterwards. The review loop routinely revises what it records, so its code blocks drift from what shipped. The code is authoritative, and the design specification in [`../specs/`](../specs/) is the living statement of intent — read this for how the work was approached, not for how tephpy behaves today.

**Goal:** Render the user documentation's own python snippets as figures on the page, so
the two how-to guides that teach a visual API show what they are describing, and pin what
they publish against approved baselines.

**Architecture:** `matplotlib.sphinxext.plot_directive` joins the extension list, configured
so a block is shown, executed, and rendered once per section. The page's `.. plot::` blocks
form one session — the first resets the context, every later one continues it — and each
figure-producing block names its image with `:filename-prefix:`. Those names are the
registry two gates read. `tests/test_docs_snippets.py`, which already executes every python
block in the user quadrants, learns the directive and asserts the page shape; it runs in the
test matrix, where Sphinx is absent. `.github/scripts/check_docs_figures.py` compares each
published image against `docs/baseline` with matplotlib's own comparator; it runs in the
documentation environment, against the build, because the artifact that ships exists only
there. `bless_docs_figures.py` regenerates the baselines from a build.

**Tech Stack:** Python 3.12–3.14, matplotlib (`plot_directive` and
`matplotlib.testing.compare`), Sphinx, pytest, pixi, pre-commit, towncrier.

**Spec:** [`../specs/2026-08-17-published-figures-design.md`](../specs/2026-08-17-published-figures-design.md)
— cited throughout as `plots spec §N`. Its siblings are cited as `docs spec §N`
([`../specs/2026-08-03-published-specs-design.md`](../specs/2026-08-03-published-specs-design.md))
and `spec §N` ([`../specs/2026-07-22-tephpy-design.md`](../specs/2026-07-22-tephpy-design.md)).
Read the plots spec alongside this plan; every task argues from a section of it.

## Global Constraints

- **Citation prefix is `plots spec §…`, never `figures spec`.** `figure` in this collection
  already means a number quoted in prose (docs spec §4), and a citation that reads as naming
  that rule while meaning a rendered diagram is worse than a longer prefix (plots spec, front
  matter). A pre-commit hook resolves anchors but cannot catch a citation that resolves to
  the wrong document.
- Every new file starts with the 4-line BSD copyright header (ruff `CPY001`) and
  `from __future__ import annotations`.
- Line length 88 (`ruff`, `line-length = 88`). Docstrings are numpydoc, validated by the
  `numpydoc-validation` pre-commit hook, **including private functions**.
- **A script in `.github/scripts/` with a shebang must be executable.** Every existing
  `check_*.py` there is `chmod +x`; ruff's `EXE001` (`shebang-not-executable`) fails
  otherwise, and `git add` preserves the mode.
- **Side-effect-only fixtures use `@pytest.mark.usefixtures("name")`**, not an unused
  parameter — ruff `ARG001` rejects the parameter form. `tests/test_citation_xrefs.py` is the
  existing example.
- Run a targeted test with `pixi run --frozen pytest <path> -k <expr> -v`. Run the full suite
  with `pixi run --frozen tests`. Run the lint gate with `pixi run --frozen lint`. Build and
  check the documentation with `pixi run --frozen docs` — `docs-html` depends on
  `docs-clean`, so that is always a clean build. `--frozen` is mandatory; never let pixi
  re-solve.
- **Sphinx is absent from the test environments.** Anything asserted about a page must be
  asserted by reading the page as text. Anything asserted about a built image belongs in a
  `.github/scripts/` gate wired into `pixi run docs`, not in `tests/`.
- Branch `docs-published-figures` off an updated `main`. The `doc` prefix earns the
  `type: documentation` label from `.github/workflows/ci-label.yml`; `labeler.yml` adds
  labels from the changed paths independently. Never commit to `main` (a
  `no-commit-to-branch` pre-commit hook enforces this).
- `pre-commit install` before the first commit — hooks are not installed in a fresh clone or
  worktree, and `pixi run --frozen lint` cannot see untracked files, so `git add` before
  linting.
- The changelog fragment is `changelog/<PR>.documentation.rst`, ending
  ``(:user:`claude`)``. **Open the pull request before choosing the number** — an issue filed
  in the interim takes the next number.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `docs/src/conf.py` | Sphinx configuration | Add the extension and its six settings |
| `docs/src/howtos/emphasis.rst` | The emphasis how-to | Convert its blocks; add a section |
| `docs/src/howtos/logo.rst` | The logo how-to | Convert its blocks |
| `tests/test_docs_snippets.py` | Executes user-page python | Learn `.. plot::`; assert page shape |
| `.github/scripts/check_docs_figures.py` | The figure gate | Create |
| `.github/scripts/bless_docs_figures.py` | Baseline regeneration | Create |
| `tests/test_docs_figures.py` | Tests for both scripts | Create |
| `docs/baseline/*.png` | Approved figures | Create (11 images) |
| `pyproject.toml` | pixi tasks | Add `docs-check-figures`, `docs-figures` |
| `.github/workflows/ci-docs.yml` | Documentation CI | Add the gate step |
| `tests/test_docs_workflow.py` | Asserts CI runs the gates | Extend `GATES` |
| `MANIFEST.in` | sdist contents | Prune `docs/baseline` |
| `docs/src/developer/docs-style.rst` | Authoring rules | Add "Published Figures" |
| `docs/src/developer/specs/2026-08-03-published-specs-design.md` | docs spec | Three edits to §3.9 |
| `docs/src/developer/specs/2026-07-22-tephpy-design.md` | parent spec | Extension list |
| `docs/src/developer/specs/2026-08-17-published-figures-design.md` | plots spec | Tense; §6 |
| `changelog/<PR>.documentation.rst` | News fragment | Create |

**Task order matters in one place.** Task 5's
`test_the_workflow_runs_the_documentation_gates_by_task_name` reads the *committed*
`pyproject.toml` (`git show HEAD:pyproject.toml`), so it stays red until Task 4's commit —
which adds the `docs-check-figures` pixi task — has landed. Do not diagnose that as a defect
in Task 5.

---

### Task 1: Configure the directive

**Files:**
- Modify: `docs/src/conf.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a Sphinx build that understands `.. plot::`, renders one `png` at dpi 100 per
  figure-producing block, shows the source, applies `figure.figsize` of `(8.0, 4.0)`, and
  executes every block in a scratch directory under `docs/_build/`. No page uses it yet.

- [ ] **Step 1: Add the extension**

In `docs/src/conf.py`, the `extensions` list is alphabetical after the first entry. Insert
one line:

```python
extensions = [
    "tephpy_citation_xrefs",
    "autoapi.extension",
    "matplotlib.sphinxext.plot_directive",
    "myst_nb",
    "numpydoc",
```

`tephpy_citation_xrefs` stays first — `check_rendered_citations.py` refuses a build in which
no citation became a link and says so by name.

- [ ] **Step 2: Add the configuration block**

Insert immediately after the `sphinx_gallery_conf = {...}` block and before the
`# -- myst-nb ---...` header. `Path` is already imported at the top of the file.

```python
# -- plot_directive ----------------------------------------------------------
# Renders the how-to snippets as figures (plots spec §3.1). Each setting below
# changes a default that is wrong for a page whose subject is the picture: the
# source is the point, so it is shown; and the source link and the format links
# both offer a download of something already on the page.
plot_include_source = True
plot_html_show_source_link = False
plot_html_show_formats = False
# One format, because the two settings above leave `hires.png` and `pdf`
# unlinked. The trailing dpi is the figure's, matching `tests/baseline`.
plot_formats = [("png", 100)]
# The recipe of plots spec §4. A tephigram's axes is a wide, short parallelogram,
# so at matplotlib's square default most of the canvas is empty and an emphasised
# member is lost in the five-family grid. Deliberately *not* `savefig.bbox:
# "tight"`: the margin it crops is where `add_logo(fig, ...)` puts a
# figure-anchored logo, and the logo how-to's first section teaches exactly that
# placement -- under `tight` that logo is cropped away entirely (plots spec §4).
plot_rcparams = {"figure.figsize": (8.0, 4.0)}
# Restores those rcParams between blocks, so a page that sets a matplotlib style
# cannot leak it into the next page built. It covers matplotlib state only --
# `tephpy.config` is module state and survives it, which is why a published block
# may not leave it mutated (plots spec §3.3).
plot_apply_rcparams = True
# Without this the directive runs each block from the *page's own source
# directory*, so a snippet that teaches `fig.savefig("sounding.png")` -- the logo
# how-to does -- writes that PNG into the checked-out documentation tree, where
# the next build then finds it. Redirect the writes to a scratch directory under
# the git-ignored build tree instead (plots spec §3.3). It is also prepended to
# `sys.path`; keeping it empty of modules is why it is a dedicated directory
# rather than `_build` itself.
_plot_scratch = Path(__file__).parent.parent / "_build" / "plot-scratch"
_plot_scratch.mkdir(parents=True, exist_ok=True)
plot_working_directory = str(_plot_scratch)
```

- [ ] **Step 3: Build, to prove the extension loads and changes nothing yet**

Run: `pixi run --frozen docs`
Expected: `build succeeded.` with no warnings — the build runs under `--fail-on-warning` —
and both existing gates green. No page carries a `.. plot::` yet, so no image is rendered.

- [ ] **Step 4: Prove `plot_working_directory` redirects a snippet's writes**

This is the setting whose absence costs a commit, and a build that renders nothing does not
exercise it. Add a throwaway block to the end of `docs/src/howtos/logo.rst`:

```rst
.. plot::
    :context: reset
    :nofigs:

    from pathlib import Path

    Path("probe-artifact.txt").write_text("written by a published block")
```

Run: `pixi run --frozen docs`
Then: `git status --short docs/src/howtos/` — expected: **no** `probe-artifact.txt`.
And: `ls docs/_build/plot-scratch/probe-artifact.txt` — expected: the file is there.

**If the probe file appears under `docs/src/howtos/`, stop.** The setting is not taking
effect, and every later task would be writing into the checked-out tree.

- [ ] **Step 5: Remove the probe block**

Revert `docs/src/howtos/logo.rst` to its committed state:

```bash
git checkout docs/src/howtos/logo.rst
```

- [ ] **Step 6: Lint and commit**

```bash
pre-commit install
git add docs/src/conf.py
pixi run --frozen lint
git commit -m "Configure matplotlib's plot_directive for the user documentation"
```

---

### Task 2: The snippet gate learns the directive, and the emphasis how-to converts

**Files:**
- Modify: `tests/test_docs_snippets.py`
- Modify: `docs/src/howtos/emphasis.rst`

**Interfaces:**
- Consumes: Task 1's configured directive.
- Produces: in `tests/test_docs_snippets.py` — `PUBLISHES_FIGURES: tuple[str, ...]`,
  `PLOT: re.Pattern`, `OPTION_VALUE: re.Pattern`,
  `plot_directives(text: str) -> list[tuple[int, str, dict[str, str]]]` and
  `figure_pages() -> list[Path]`; `literal_blocks` additionally yields `.. plot::` bodies as
  `python`. Task 3 extends `PUBLISHES_FIGURES` and adds no new name. Task 4's
  `check_docs_figures.py` parses `:filename-prefix:` independently and shares nothing with
  this module.

The two halves are one task because they are mutually dependent: the moment the page
converts, its blocks stop being found by `DIRECTIVE` and
`test_the_documented_pages_yield_blocks` fails by name — which is the gate working, and the
reason plots spec §3.4 puts the extension in the same change rather than after it.

- [ ] **Step 1: Add the two patterns and the page list**

`PUBLISHES_FIGURES` goes immediately after the existing `DOCUMENTED` tuple:

```python
#: The pages that publish figures (plots spec §3.2). Membership again, and for a
#: sharper reason than above: every page-shape check below iterates these pages,
#: so a converted page that stopped being recognised would not fail those checks
#: -- it would pass all of them, having been asked nothing.
PUBLISHES_FIGURES = ("howtos/emphasis.rst",)
```

`PLOT` goes immediately after the existing `DIRECTIVE` pattern:

```python
#: The directive that publishes a figure (plots spec §3.1). It is deliberately not
#: folded into :data:`DIRECTIVE`: that pattern reads a directive's argument as a
#: language, and ``.. plot::`` either takes none or takes a filename, so folding it
#: in would classify an unnamed plot as naming no language -- which
#: :func:`test_no_block_hides_the_language_this_gate_runs` reports -- and would read
#: ``script.py`` as a language nobody executes (plots spec §3.4). Its body is python
#: by definition, so it needs no language to be judged from.
PLOT = re.compile(r"^(?P<indent>[ ]*)\.\.[ ]+plot::[ ]*(?P<argument>\S*)[ ]*$")
```

`OPTION_VALUE` goes immediately after the existing `OPTION` pattern:

```python
#: A directive option with its value, for the options a ``.. plot::`` is judged by
#: (plots spec §3.2). The value is optional: ``:nofigs:`` is a flag and
#: ``:context: reset`` is not.
OPTION_VALUE = re.compile(r"^[ ]*:(?P<name>[\w-]+):[ ]*(?P<value>.*?)[ ]*$")
```

- [ ] **Step 2: Teach `literal_blocks` the directive**

Three edits inside the existing function. The scan head:

```python
        directive = DIRECTIVE.match(lines[index])
        plot = PLOT.match(lines[index]) if directive is None else None
        if directive is None and plot is None:
            index += 1
            continue
        opening = len((directive or plot)["indent"])
```

and, in the tuple the function appends, the language:

```python
        found.append(
            (
                start + 1,
                directive["language"] if directive else PYTHON,
                [line[body:] for line in lines[start:end]],
            )
        )
```

Everything between — the option run, the blank line, the body's indentation — is unchanged.
A `.. plot::` body is python by definition, which is why the language is supplied rather
than read.

- [ ] **Step 3: Add `plot_directives`**

After the existing `python_blocks`:

```python
def plot_directives(text: str) -> list[tuple[int, str, dict[str, str]]]:
    """Every ``.. plot::`` on a page, with its argument and its options.

    Separate from :func:`literal_blocks`, which reports what to *run*: the page
    shape of plots spec §3.2 is judged from what a directive declares, including
    a directive that renders no figure and one given a filename instead of a
    body, neither of which contributes a line of code.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    list of tuple
        ``(line, argument, options)`` per directive, in document order, ``line``
        1-based and naming the directive itself. ``argument`` is the empty string
        for the body form. ``options`` maps each option to its value, which is the
        empty string for a flag such as ``:nofigs:``.

    """
    lines = text.splitlines()
    # A ``.. plot::`` written *inside* another block's body is that block's
    # content -- the style guide quotes the directive it documents -- and is not
    # a directive this page declares.
    inside = block_lines(text)
    found: list[tuple[int, str, dict[str, str]]] = []
    for index, line in enumerate(lines):
        plot = PLOT.match(line)
        if plot is None or index + 1 in inside:
            continue
        options: dict[str, str] = {}
        cursor = index + 1
        while cursor < len(lines) and lines[cursor].strip():
            option = OPTION_VALUE.match(lines[cursor])
            if option is None:
                break
            options[option["name"]] = option["value"]
            cursor += 1
        found.append((index + 1, plot["argument"], options))
    return found
```

- [ ] **Step 4: Run the existing suite, and watch it stay green**

Run: `pixi run --frozen pytest tests/test_docs_snippets.py -q`
Expected: PASS, unchanged count. No page has converted yet, so `PLOT` matches nothing and
the extractor's behaviour on the existing corpus is identical. A failure here is a
regression in `literal_blocks`, not a missing conversion.

- [ ] **Step 5: Convert `docs/src/howtos/emphasis.rst`**

Five block conversions and one restructured section. Replace each `.. code-block:: python`
header with the directive and its options, leaving every body exactly as it is:

| Section | Replaces | With |
|---|---|---|
| The Freezing Level | `.. code-block:: python` | `.. plot::` / `:context: reset` / `:filename-prefix: emphasis-freezing-level` |
| Colour and Dashes | `.. code-block:: python` | `.. plot::` / `:context:` / `:filename-prefix: emphasis-colour-and-dashes` |
| Values the Interval Never Lands On | `.. code-block:: python` | `.. plot::` / `:context:` / `:filename-prefix: emphasis-off-interval` |
| Every Family, Every Tier | `.. code-block:: python` | `.. plot::` / `:context: close-figs` / `:filename-prefix: emphasis-every-family` |
| (final block) | `.. code-block:: python` | `.. plot::` / `:context:` / `:filename-prefix: emphasis-opt-out` |

The "Every Family, Every Tier" block gains a line, because `close-figs` closes the figure
the previous sections were drawing on:

```rst
.. plot::
    :context: close-figs
    :filename-prefix: emphasis-every-family

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.isobars(emphasis={500.0: {}})
```

- [ ] **Step 6: Rewrite the configuration passage**

The page's last prose passage demonstrates configuration by assigning to `tephpy.config`,
which plots spec §3.3 forbids in a published block: the setting would apply to every axes
created afterwards, on this page and on every page built after it. Replace from "and it
takes the usual precedence" through the final block's header with:

```rst
and it takes the usual precedence — the accessor keyword over
``tephpy.config`` over the convention default.

Configure It Once
-----------------

A family reads ``tephpy.config`` when the axes is created, and re-reads it on
``ax.clear()``, so the configuration has to be in force before the diagram it
should apply to exists. :meth:`tephpy.config.context` scopes it to exactly
that:

.. plot::
    :context: close-figs
    :filename-prefix: emphasis-from-config

    with tephpy.config.context(isotherms={"emphasis": {0.0: {"color": "tab:red"}}}):
        fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})

Setting ``tephpy.config.isotherms.emphasis`` directly does the same thing and
keeps doing it, for every axes created afterwards, until something puts it back.
Reach for that where a house style is the point — a configuration file
(:ref:`configure-from-a-file`) is the tidier home for one — and for a single
diagram prefer the accessor keyword the sections above use.

Passing an empty mapping at the accessor emphasises nothing, which is how one
diagram opts out of a configured emphasis:

.. plot::
    :context:
    :filename-prefix: emphasis-opt-out

    ax.isotherms(emphasis={})
```

The old block's `import matplotlib.pyplot as plt` and `import tephpy` lines go: the page is
one session and its first block already imports both. This is a better page as well as a
safe one — the ordering the prose is making is now visible in the indentation.

- [ ] **Step 7: Write the page-shape tests**

Append to `tests/test_docs_snippets.py`, after
`test_no_block_hides_the_language_this_gate_runs`:

```python
def figure_pages() -> list[Path]:
    """Select the user pages that publish figures.

    Returns
    -------
    list of Path
        The pages carrying at least one ``.. plot::`` (plots spec §3.2).

    """
    return [
        page
        for page in user_pages()
        if plot_directives(page.read_text(encoding="utf-8"))
    ]


def test_the_figure_pages_are_recognised():
    """Every check below iterates these pages; unrecognised, they are unasked."""
    found = {identify(page) for page in figure_pages()}
    assert set(PUBLISHES_FIGURES) <= found, (
        "these pages publish figures and yielded no `.. plot::`: "
        f"{sorted(set(PUBLISHES_FIGURES) - found)}. Every page-shape check in "
        "this module would pass them in silence (plots spec §3.2)"
    )


def test_a_page_publishes_figures_or_it_does_not():
    """The two block forms never mix on one page (plots spec §3.2)."""
    offenders: list[tuple[str, int]] = []
    for page in figure_pages():
        text = page.read_text(encoding="utf-8")
        inside = block_lines(text)
        offenders.extend(
            (identify(page), number)
            for number, line in enumerate(text.splitlines(), start=1)
            if number not in inside
            and (match := DIRECTIVE.match(line)) is not None
            and match["language"].lower() == PYTHON
        )
    assert offenders == [], (
        "these pages publish figures and still carry a plain python block: "
        f"{offenders}. Such a block runs in this gate and not in the "
        "documentation build, so the build's namespace silently loses whatever "
        "it bound; give it `.. plot::` with `:nofigs:` if its picture would add "
        "nothing (plots spec §3.2)"
    )


def test_the_first_plot_on_a_page_resets_the_context():
    """A page that opens without `reset` inherits the page built before it."""
    offenders: list[tuple[str, int, str]] = []
    for page in figure_pages():
        line, _, options = plot_directives(page.read_text(encoding="utf-8"))[0]
        if options.get("context") != "reset":
            offenders.append((identify(page), line, options.get("context", "")))
    assert offenders == [], (
        "these pages open with a plot that does not carry `:context: reset`: "
        f"{offenders}. Build order is not a property any page controls, so a "
        "page that builds only because of its neighbour breaks the moment "
        "someone rebuilds one file (plots spec §3.2)"
    )


def test_every_later_plot_continues_the_session():
    """A block with no `:context:` runs in a fresh namespace (plots spec §3.2)."""
    offenders: list[tuple[str, int]] = []
    for page in figure_pages():
        for line, _, options in plot_directives(page.read_text(encoding="utf-8"))[1:]:
            if options.get("context", None) not in ("", "close-figs"):
                offenders.append((identify(page), line))
    assert offenders == [], (
        "these plots neither continue the page's session nor open a figure of "
        f"their own: {offenders}. Each must carry `:context:` or `:context: "
        "close-figs` -- `reset` belongs to the first block alone, and a block "
        "with no `:context:` at all runs in a namespace where the page's "
        "imports never happened (plots spec §3.2)"
    )


def test_every_published_figure_is_named():
    """An unnamed image takes a counter, which renumbers on an insertion."""
    offenders: list[tuple[str, int]] = []
    for page in figure_pages():
        for line, _, options in plot_directives(page.read_text(encoding="utf-8")):
            if "nofigs" not in options and "filename-prefix" not in options:
                offenders.append((identify(page), line))
    assert offenders == [], (
        "these plots publish a figure under a per-document counter: "
        f"{offenders}. Inserting a section renumbers every image after it, and "
        "every baseline with it; give each one a `:filename-prefix:` "
        "(plots spec §3.2)"
    )


def test_a_suppressed_figure_is_not_also_named():
    """A name the build never produces is a baseline that can never match."""
    offenders: list[tuple[str, int]] = []
    for page in figure_pages():
        for line, _, options in plot_directives(page.read_text(encoding="utf-8")):
            if "nofigs" in options and "filename-prefix" in options:
                offenders.append((identify(page), line))
    assert offenders == [], (
        "these plots carry both `:nofigs:` and `:filename-prefix:`: "
        f"{offenders}. The name is a declaration that the figure gate then "
        "looks for, and Sphinx collects only the images a page references, so "
        "the pair can only ever fail as declared-but-not-built "
        "(plots spec §3.5)"
    )


def test_a_figure_name_is_unique_across_the_documentation():
    """Two sections sharing a prefix share one image, and one baseline."""
    seen: dict[str, tuple[str, int]] = {}
    collisions: list[tuple[str, str, str]] = []
    for page in figure_pages():
        for line, _, options in plot_directives(page.read_text(encoding="utf-8")):
            prefix = options.get("filename-prefix")
            if prefix is None:
                continue
            if prefix in seen:
                collisions.append(
                    (
                        prefix,
                        f"{seen[prefix][0]}:{seen[prefix][1]}",
                        f"{identify(page)}:{line}",
                    )
                )
            seen[prefix] = (identify(page), line)
    assert collisions == [], (
        f"these figure names are declared more than once: {collisions}. "
        "The images land in one flat directory, so a shared name is one image "
        "published under both sections (plots spec §3.2)"
    )


def test_no_plot_renders_from_a_file():
    """`.. plot:: script.py` puts the code a reader copies off the page."""
    offenders: list[tuple[str, int, str]] = []
    for page in figure_pages():
        offenders.extend(
            (identify(page), line, argument)
            for line, argument, _ in plot_directives(page.read_text(encoding="utf-8"))
            if argument
        )
    assert offenders == [], (
        "these plots render from a file rather than from a block on the page: "
        f"{offenders}. The page's own snippet is the figure's source -- a "
        "figure built from a script beside the page is a second construction "
        "that agrees with the prose until someone edits one of them "
        "(plots spec §2)"
    )
```

- [ ] **Step 8: Run the module**

Run: `pixi run --frozen pytest tests/test_docs_snippets.py -q`
Expected: PASS, 8 more tests than before. In particular
`test_the_documented_pages_yield_blocks` is green — the emphasis how-to's converted blocks
are found by the extended extractor — and `test_page_scripts_run` still executes the page.

- [ ] **Step 9: Prove the new assertions are not vacuous**

Each mutation is applied, the named test is watched to fail, and the mutation is reverted.
`git add -A` first: `git checkout <path>` reverts from the index, so an unstaged
mutate-verify-revert cycle would discard the task's real work along with the mutation.

1. In `emphasis.rst`, change the first block's `:context: reset` to `:context:` →
   `test_the_first_plot_on_a_page_resets_the_context` fails.
2. In `emphasis.rst`, delete the `:filename-prefix:` line from any block →
   `test_every_published_figure_is_named` fails.
3. In `emphasis.rst`, give two blocks the same `:filename-prefix:` →
   `test_a_figure_name_is_unique_across_the_documentation` fails.
4. In `emphasis.rst`, revert one block to `.. code-block:: python` →
   `test_a_page_publishes_figures_or_it_does_not` fails. This is the important one: it is
   the defect the page-form rule exists to stop.

Revert each with `git checkout docs/src/howtos/emphasis.rst`.

- [ ] **Step 10: Build, and look at the figures**

Run: `pixi run --frozen docs`
Expected: `build succeeded.`, and six PNGs under `docs/_build/html/_images/` named
`emphasis-*.png`. Open them. A gate cannot tell a correct diagram from a useless one, and
this is the only step in the plan where a human looks at what the page now publishes.

- [ ] **Step 11: Lint and commit**

```bash
git add tests/test_docs_snippets.py docs/src/howtos/emphasis.rst
pixi run --frozen lint
git commit -m "Publish the emphasis how-to's figures, and gate the page shape"
```

---

### Task 3: The logo how-to converts

**Files:**
- Modify: `docs/src/howtos/logo.rst`
- Modify: `tests/test_docs_snippets.py:45` (the `PUBLISHES_FIGURES` tuple)

**Interfaces:**
- Consumes: Task 2's `PUBLISHES_FIGURES`, `plot_directives`, and the extended
  `literal_blocks`.
- Produces: five more declared figure names — `logo-axes-and-figure`,
  `logo-current-figure`, `logo-size-and-form`, `logo-exact-placement`, `logo-restyled` —
  and three `:nofigs:` blocks. Task 4's baselines are these five plus Task 2's six.

A page of its own because it is the page that exercises the two rules the emphasis how-to
does not: a block that runs and publishes nothing, and a block that writes a file.

- [ ] **Step 1: Convert the five figure-producing blocks**

| Section | With |
|---|---|
| On the Plot or Around It | `.. plot::` / `:context: reset` / `:filename-prefix: logo-axes-and-figure` |
| (current figure) | `.. plot::` / `:context:` / `:filename-prefix: logo-current-figure` |
| Size and Form | `.. plot::` / `:context: close-figs` / `:filename-prefix: logo-size-and-form` |
| Exact Placement | `.. plot::` / `:context: close-figs` / `:filename-prefix: logo-exact-placement` |
| Restyling and Removal | `.. plot::` / `:context: close-figs` / `:filename-prefix: logo-restyled` |

The "Size and Form", "Exact Placement" and "Restyling and Removal" blocks each gain the line
that opens their own figure, because `close-figs` closed the previous one:

```rst
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
```

- [ ] **Step 2: Convert the three blocks that publish nothing**

Each carries `:nofigs:` and **no** `:filename-prefix:`. They still run, so the session is
unbroken and the snippet gate still covers them; a plain `code-block:: python` would run in
the test gate and not in the build, which is the defect the page-form rule exists to stop.

The dark-background block:

```rst
.. plot::
    :context: close-figs
    :nofigs:

    with plt.style.context("dark_background"):
        fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
        add_logo(ax)  # draws the dark-background variant
```

**Its figure is suppressed for a reason, not for tidiness.** Rendering a tephigram under a
dark matplotlib style exposes a pre-existing defect that is out of scope here:
`LABEL_BOX_COLOR` is the constant `"white"` at `LABEL_BOX_ALPHA` `0.6`, so every inline
isopleth label becomes an opaque pale blob on a black canvas and the diagram is unreadable.
`add_logo` itself is correct there — the dark-background variant is selected and drawn,
which is what the prose claims. Publishing the picture would advertise the defect on the
shop window; fixing it reaches into `src/tephpy/_constants.py` and re-blesses every image
baseline. This is plots spec §7's **Blocked** item, and this section's picture is the
acceptance test for that change. **Do not silently drop the `:nofigs:` later** — see Task 6,
step 6.

The `savefig` block, whose whole job is to be copied by a reader:

```rst
.. plot::
    :context:
    :nofigs:

    add_logo(ax, theme="dark")
    fig.savefig("sounding.png", transparent=True)
```

and the removal block:

```rst
.. plot::
    :context:
    :nofigs:

    logo.remove()  # changed your mind
```

- [ ] **Step 3: Extend the page list**

```python
PUBLISHES_FIGURES = ("howtos/emphasis.rst", "howtos/logo.rst")
```

- [ ] **Step 4: Run the module**

Run: `pixi run --frozen pytest tests/test_docs_snippets.py -q`
Expected: PASS, same count as Task 2 — these are the same assertions over one more page.

- [ ] **Step 5: Prove the `:nofigs:` rules are guarded**

Staged, as before. Two mutations:

1. Add `:filename-prefix: logo-dark` to the dark-background block →
   `test_a_suppressed_figure_is_not_also_named` fails. That pair is a figure declared and
   never built, because Sphinx collects into `_images/` only what a page references.
2. Change the removal block's `:context:` to nothing at all →
   `test_every_later_plot_continues_the_session` fails. Without the session, `logo` is
   unbound.

- [ ] **Step 6: Build, and confirm the suppressed renders never reach `_images/`**

Run: `pixi run --frozen docs`
Then: `ls docs/_build/html/_images/ | grep -c "^emphasis-\|^logo-"` — expected `11`.
And: `ls docs/_build/html/plot_directive/howtos/` — expected to contain the three
`:nofigs:` renders, which stay in the directive's own output directory and never arrive in
`_images/`. That asymmetry is what makes the declaration registry exact at both ends
(plots spec §3.5).

Open the five new images. As in Task 2, this is the step where a human looks.

- [ ] **Step 7: Confirm no snippet wrote into the source tree**

```bash
git status --short docs/src/
```

Expected: only `docs/src/howtos/logo.rst` and `tests/test_docs_snippets.py`. In particular
**no `docs/src/howtos/sounding.png`** — that is the file the `savefig` block deposits when
`plot_working_directory` is unset, and the next build then finds it as a new source file.

- [ ] **Step 8: Lint and commit**

```bash
git add tests/test_docs_snippets.py docs/src/howtos/logo.rst
pixi run --frozen lint
git commit -m "Publish the logo how-to's figures"
```

---

### Task 4: The figure gate, its blessing command, and the baselines

**Files:**
- Create: `.github/scripts/check_docs_figures.py`
- Create: `.github/scripts/bless_docs_figures.py`
- Create: `tests/test_docs_figures.py`
- Create: `docs/baseline/*.png` (11 images, blessed from the build)
- Modify: `pyproject.toml` (two pixi tasks; the `docs` task's `depends-on`)

**Interfaces:**
- Consumes: the `:filename-prefix:` declarations Tasks 2 and 3 put on the pages.
- Produces: `check_docs_figures.py` exporting `QUADRANTS`, `PUBLISHES`, `DECLARATION`,
  `IMAGES`, `SUFFIX`, `TOLERANCE`, `SHOWN`, `Figure(NamedTuple)` with fields
  `name/page/built/baseline`, `declarations(text) -> list[str]`,
  `collect(source, images, baselines) -> list[Figure]`,
  `offenders(title, lines, advice) -> bool` and `main() -> int`;
  `bless_docs_figures.py` importing `IMAGES`, `SUFFIX` and `collect` from it and exporting
  `main() -> int`. Task 5 wires the `docs-check-figures` pixi task into CI and asserts its
  name.

Both scripts and their tests are one task: the gate is not green until the baselines exist,
and the baselines are what the blessing command writes. A reviewer gates this on one
question — does the gate refuse the right things?

- [ ] **Step 1: Write the gate**

Create `.github/scripts/check_docs_figures.py`:

```python
#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Check that every figure the user documentation publishes is the approved one.

The how-to guides that teach a visual API render their own snippets as figures
through ``matplotlib.sphinxext.plot_directive`` (plots spec §3.1). The snippet
gate of docs spec §3.9 already runs that code on every supported Python, so a
snippet that stops working fails there. What it cannot see is the second failure
a rendered page adds: a snippet that still runs and no longer *shows* what its
prose claims. This gate is that check (plots spec §3.5).

It runs on the documentation side, against the images the build just produced,
because what is worth pinning is the artifact that ships and it exists only in
the build. Re-rendering the same code in the test environment and comparing that
would pin a second render whose agreement with the published one rests on
several settings staying aligned, with nothing checking the alignment.

The expected set is not a glob of the build's ``_images/``. That directory also
holds the browser demo's toolbar icons, and a glob cannot tell a plot from an
icon -- adding one non-plot image would turn this gate red for a file it was
never meant to judge, while a plot silently *not* built is the failure it exists
to catch. The names come instead from the ``:filename-prefix:`` each directive
declares on the page, which makes the page the registry and lets a declared
figure that was never built be reported as missing.

The page is parsed here rather than imported from ``tests/``: the sdist ships
the tests and prunes ``.github``, so this script cannot be a consumer of that
module, and a second implementation of a two-line pattern is the cheaper half of
that trade. It is also the half that catches a bug in the other one.

Three things are checked. Every declared figure was built. Every baseline is
claimed by a declaration, so a renamed section leaves no orphan behind. And each
declared/built pair matches its baseline within tolerance, by matplotlib's own
comparator -- the same RMS measure ``pytest-mpl`` applies to ``tests/baseline``.

An empty declared set fails. A gate that finds nothing to check and exits ``0``
reports a green tick over nothing, which is what docs spec §3.9's own corpus
refusals were written against.

What this does *not* do is judge whether a figure is a good illustration. It
pins what was published against what was approved; a diagram that draws
correctly and teaches nothing is review's to catch.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from pathlib import Path
import re
import sys
import textwrap
from typing import NamedTuple

from matplotlib.testing.compare import compare_images

#: The Diátaxis quadrants written for users, which are the pages that may publish
#: a figure (plots spec §3.2).
QUADRANTS = ("howtos", "tutorials", "explanation")
#: The pages known to publish figures. Membership, not a count: a count is a
#: figure that has to be re-measured to stay true. This is what fails when the
#: declaration pattern stops matching, instead of the gate finding nothing and
#: reporting that nothing was wrong.
PUBLISHES = ("howtos/emphasis.rst", "howtos/logo.rst")
#: A figure declaration: the ``:filename-prefix:`` option of a ``.. plot::``. The
#: directive line is matched too, so an option of that name under some other
#: directive is not read as a figure this project publishes.
DECLARATION = re.compile(
    r"^[ ]*\.\.[ ]+plot::.*$(?:\n^[ ]*:[\w-]+:.*$)*?"
    r"\n^[ ]*:filename-prefix:[ ]*(?P<prefix>[\w.-]+)[ ]*$",
    re.MULTILINE,
)
#: Where the build collects the images a page references. Sphinx puts only
#: referenced images here, so a ``:nofigs:`` block's render never arrives and
#: cannot be mistaken for a published figure.
IMAGES = "_images"
#: The extension the sole configured output format produces (plots spec §3.1).
SUFFIX = ".png"
#: The RMS difference tolerated between a published figure and its baseline,
#: which is ``pytest-mpl``'s default and so the figure the rest of this project's
#: image comparison already uses.
TOLERANCE = 2
#: How many offenders of one kind to name before counting the rest.
SHOWN = 6
#: What to do about a figure a page declares and the build did not produce.
MISSING = (
    "The page declares this figure and the build produced no such image. Sphinx "
    "collects into '_images' only what a page references, so the usual cause is "
    "a directive carrying both ':filename-prefix:' and ':nofigs:' -- it renders "
    "an image the page never shows, under a name this gate then looks for. "
    "Either drop the ':nofigs:' and publish the figure, or drop the name."
)
#: What to do about a baseline no page claims.
ORPHANED = (
    "No page declares this figure, so nothing compares against this baseline. A "
    "renamed ':filename-prefix:' leaves the old baseline behind, where it goes "
    "on being shipped and never again being read. Delete it, or restore the "
    "declaration that named it."
)
#: What to do about a figure with no baseline at all.
UNAPPROVED = (
    "The page declares this figure and no baseline exists to compare it "
    "against, so what it publishes has never been approved. Run 'pixi run "
    "docs-figures' to bless the build's output, then read the diff before "
    "committing it: that command approves whatever was rendered, including a "
    "regression."
)
#: What to do about a figure that no longer matches its baseline.
CHANGED = (
    "The published figure has drifted from the one that was approved. This is "
    "the failure this gate exists to catch: the snippet still runs, and no "
    "longer draws what the page's prose describes. Open the '-failed-diff.png' "
    "written beside the built image. If the change is wrong, fix the code or "
    "the snippet; if it is intended, run 'pixi run docs-figures' to re-bless it "
    "and commit the new baseline with the change that caused it."
)
#: What to do about a documentation tree that declares no figure anywhere.
EMPTY = (
    "No page declares a figure, so this gate has nothing to compare and a "
    "search of nothing finds nothing wrong. Either the pages stopped publishing "
    "figures -- in which case remove this gate rather than leaving it green -- "
    "or the declaration pattern has stopped matching them."
)
#: What to do about a page that is supposed to publish figures and does not.
UNRECOGNISED = (
    "This page is listed in PUBLISHES and declares no figure. The list names "
    "the pages whose figures are meant to be pinned; a page missing from the "
    "scan is not reported by any other check here, because every check reads "
    "the declarations. Restore the page's declarations, or remove it from "
    "PUBLISHES if it deliberately stopped publishing."
)


class Figure(NamedTuple):
    """One declared figure, and where its three files are."""

    #: The ``:filename-prefix:`` the page declared.
    name: str
    #: The page that declared it, relative to the documentation source root.
    page: str
    #: The image the build produced, which may not exist.
    built: Path
    #: The approved image, which may not exist.
    baseline: Path


def declarations(text: str) -> list[str]:
    """Read the figure names a page declares.

    Parameters
    ----------
    text : str
        The reStructuredText source of one page.

    Returns
    -------
    list of str
        The ``:filename-prefix:`` values, in document order.

    """
    return [match["prefix"] for match in DECLARATION.finditer(text)]


def collect(source: Path, images: Path, baselines: Path) -> list[Figure]:
    """Gather every figure the user documentation declares.

    Parameters
    ----------
    source : Path
        The documentation source root holding the quadrant directories.
    images : Path
        The built ``_images`` directory.
    baselines : Path
        The directory holding the approved images.

    Returns
    -------
    list of Figure
        One entry per declaration, quadrant by quadrant and sorted within each.

    """
    found: list[Figure] = []
    for quadrant in QUADRANTS:
        for page in sorted((source / quadrant).rglob("*.rst")):
            text = page.read_text(encoding="utf-8")
            found.extend(
                Figure(
                    name=name,
                    page=page.relative_to(source).as_posix(),
                    built=images / f"{name}{SUFFIX}",
                    baseline=baselines / f"{name}{SUFFIX}",
                )
                for name in declarations(text)
            )
    return found


def offenders(title: str, lines: list[str], advice: str) -> bool:
    """Report one kind of failure, truncated to :data:`SHOWN`.

    Parameters
    ----------
    title : str
        The headline, naming what went wrong.
    lines : list of str
        One line per offender, already formatted.
    advice : str
        What to do about it.

    Returns
    -------
    bool
        Whether anything was reported.

    """
    if not lines:
        return False
    print(f"{title}:")
    for line in lines[:SHOWN]:
        print(f"  {line}")
    if len(lines) > SHOWN:
        print(f"  ... and {len(lines) - SHOWN} more")
    print(f"\n{textwrap.fill(advice)}\n")
    return True


def main() -> int:
    """Check the built figures against their baselines.

    Returns
    -------
    int
        ``0`` when every published figure matches, ``1`` otherwise.

    """
    if len(sys.argv) < 2:
        print("usage: check_docs_figures.py <html-root> [source-root] [baselines]")
        return 1
    root = Path(sys.argv[1])
    repo = Path(__file__).parents[2]
    source = Path(sys.argv[2]) if len(sys.argv) > 2 else repo / "docs" / "src"
    baselines = Path(sys.argv[3]) if len(sys.argv) > 3 else repo / "docs" / "baseline"
    for directory in (root, source):
        if not directory.is_dir():
            print(f"no such directory: {directory}")
            return 1

    figures = collect(source, root / IMAGES, baselines)
    if not figures:
        print("no page declares a figure")
        print(f"\n{textwrap.fill(EMPTY)}")
        print("\nSee 'Published Figures' in docs/src/developer/docs-style.rst.")
        return 1

    declared_by = {figure.page for figure in figures}
    silent = sorted(set(PUBLISHES) - declared_by)
    if offenders("these pages declare no figure", silent, UNRECOGNISED):
        print("See 'Published Figures' in docs/src/developer/docs-style.rst.")
        return 1

    missing, unapproved, changed = [], [], []
    for figure in sorted(figures):
        if not figure.built.is_file():
            missing.append(f"{figure.name} ({figure.page})")
        elif not figure.baseline.is_file():
            unapproved.append(f"{figure.name} ({figure.page})")
        else:
            # `in_decorator=True` is what returns the measurement as a mapping;
            # the default returns a formatted string, whose RMS could only be
            # recovered by parsing prose matplotlib is free to reword.
            result = compare_images(
                str(figure.baseline),
                str(figure.built),
                TOLERANCE,
                in_decorator=True,
            )
            if result is not None:
                changed.append(
                    f"{figure.name} (RMS {result['rms']:.2f}, "
                    f"tolerance {result['tol']})"
                )

    claimed = {figure.baseline for figure in figures}
    orphaned = sorted(
        path.name for path in baselines.glob(f"*{SUFFIX}") if path not in claimed
    )

    failed = False
    failed |= offenders("these declared figures were not built", missing, MISSING)
    failed |= offenders("these figures have no baseline", unapproved, UNAPPROVED)
    failed |= offenders("these figures no longer match", changed, CHANGED)
    failed |= offenders("these baselines are claimed by no page", orphaned, ORPHANED)
    if failed:
        print("See 'Published Figures' in docs/src/developer/docs-style.rst.")
        return 1

    pages = len({figure.page for figure in figures})
    print(
        f"published figures ok: {len(figures)} compared within RMS {TOLERANCE}, "
        f"across {pages} page{'' if pages == 1 else 's'} (plots spec §3.5)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Two details that are easy to get wrong and expensive to debug:

- **`in_decorator=True` is not optional.** `compare_images` without it returns a formatted
  *string* on failure, and the RMS could then only be recovered by parsing prose matplotlib
  is free to reword. With it, the return is `None` on a match and a mapping with `rms` and
  `tol` on a failure.
- **The success line pluralises.** `across 1 pages` is a wart never visible on the real
  two-page documentation, and visible in the first synthetic test that builds a one-page
  tree.

- [ ] **Step 2: Make it executable**

```bash
chmod +x .github/scripts/check_docs_figures.py
```

Ruff's `EXE001` fails a file that has a shebang and is not executable, and every existing
`check_*.py` in that directory is `chmod +x`.

- [ ] **Step 3: Write the blessing command**

Create `.github/scripts/bless_docs_figures.py`:

```python
#!/usr/bin/env python3
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Approve the figures the documentation build just published.

The companion to ``check_docs_figures.py``: that gate compares each published
figure against ``docs/baseline``, and this is what puts a new or intended figure
there (plots spec §3.6). Re-blessing is one command and a diff to read rather
than a hand copy per file, which is what keeps a baseline update from being the
step someone does partially.

It approves *whatever was rendered*. That is the point and the hazard: a
regression is copied over its baseline exactly as willingly as a correction, and
the only thing standing between the two is the diff this prints. Read it before
committing, and commit the baselines with the change that caused them.

The declarations are read through ``check_docs_figures``, not re-parsed, so the
set blessed here is by construction the set that gate checks. A baseline no page
declares any longer is removed, which is the same orphan the gate reports.

Notes
-----
.. versionadded:: 0.1.0

"""

from __future__ import annotations

from pathlib import Path
import shutil
import sys

from check_docs_figures import IMAGES, SUFFIX, collect


def main() -> int:
    """Copy the built figures over their baselines.

    Returns
    -------
    int
        ``0`` when every declared figure was built, ``1`` otherwise.

    """
    if len(sys.argv) < 2:
        print("usage: bless_docs_figures.py <html-root> [source-root] [baselines]")
        return 1
    root = Path(sys.argv[1])
    repo = Path(__file__).parents[2]
    source = Path(sys.argv[2]) if len(sys.argv) > 2 else repo / "docs" / "src"
    baselines = Path(sys.argv[3]) if len(sys.argv) > 3 else repo / "docs" / "baseline"
    for directory in (root, source):
        if not directory.is_dir():
            print(f"no such directory: {directory}")
            return 1

    figures = collect(source, root / IMAGES, baselines)
    if not figures:
        print("no page declares a figure -- nothing to bless")
        return 1

    # A figure that was not built cannot be approved, and blessing the rest
    # silently would leave the gate red for a reason this command appears to
    # have addressed.
    missing = sorted(figure.name for figure in figures if not figure.built.is_file())
    if missing:
        print(f"these declared figures were not built: {missing}")
        print("Nothing was blessed. Fix the build first.")
        return 1

    baselines.mkdir(parents=True, exist_ok=True)
    added, updated = [], []
    for figure in sorted(figures):
        if not figure.baseline.is_file():
            added.append(figure.name)
        elif figure.baseline.read_bytes() != figure.built.read_bytes():
            updated.append(figure.name)
        shutil.copyfile(figure.built, figure.baseline)

    claimed = {figure.baseline for figure in figures}
    removed = []
    for path in sorted(baselines.glob(f"*{SUFFIX}")):
        if path not in claimed:
            path.unlink()
            removed.append(path.name)

    for label, names in (
        ("added", added),
        ("updated", updated),
        ("removed", removed),
    ):
        for name in names:
            print(f"{label:8} {name}")
    if not (added or updated or removed):
        print("baselines already match the build -- nothing changed")
    else:
        print(
            f"\n{len(added)} added, {len(updated)} updated, {len(removed)} removed. "
            "Read the diff before committing: this command approves a regression "
            "as readily as a fix (plots spec §3.6)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Then: `chmod +x .github/scripts/bless_docs_figures.py`.

`from check_docs_figures import ...` is a bare top-level import, which resolves because
Python puts a script's own directory on `sys.path[0]` when it runs it. That is true of
`pixi run docs-figures` and *not* true of a test module importing it, which is why the next
step's loader inserts the directory itself.

- [ ] **Step 4: Write the tests**

Create `tests/test_docs_figures.py`. Note where it lives: the tests tree mirrors the package,
and these scripts are not part of the package, so the module sits at the top level beside
`tests/test_rendered_citations.py`, which tests the neighbouring gate the same way.

```python
# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the published-figure gate and its blessing command (plots spec §3.5).

The gate itself runs in the documentation environment, against a build. These
run in the test matrix, against a synthetic tree of three or four small PNGs,
which is what lets every refusal be exercised: a real build produces a passing
tree, and a gate is only worth having if the shapes it rejects are known to be
rejected rather than assumed to be.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pytest

REPO = Path(__file__).parents[1]
SCRIPTS = REPO / ".github" / "scripts"
CHECK = SCRIPTS / "check_docs_figures.py"
BLESS = SCRIPTS / "bless_docs_figures.py"
BASELINE = REPO / "docs" / "baseline"

# As in `test_rendered_citations.py`: `MANIFEST.in` prunes `.github`, so an
# sdist ships these tests without the scripts they exercise. The guard sits on
# the module rather than inside each test, because an unconditional import
# would break collection there rather than skip it.
pytestmark = pytest.mark.skipif(
    not (CHECK.is_file() and BLESS.is_file()),
    reason="not a checkout of the repository",
)


def _load(path: Path):
    """Import a gate by path; ``.github`` is not an importable package."""
    # `bless_docs_figures` imports `check_docs_figures` by top-level name, which
    # resolves when Python runs the script -- the script's own directory becomes
    # `sys.path[0]` -- and not when it is loaded from here.
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load(CHECK) if CHECK.is_file() else None
bless = _load(BLESS) if BLESS.is_file() and gate is not None else None


def declare(*names: str) -> str:
    """Render a page whose sections declare each named figure, in order."""
    return "\n".join(
        f".. plot::\n"
        f"    :context: {'reset' if index == 0 else 'close-figs'}\n"
        f"    :filename-prefix: {name}\n"
        f"\n"
        f"    value = {index}\n"
        for index, name in enumerate(names)
    )


def render(path: Path, colour: str) -> None:
    """Write a small PNG.

    Every image here shares one size, which ``compare_images`` requires of the
    pair it is given.
    """
    figure = plt.figure(figsize=(1.0, 1.0), dpi=50)
    figure.add_subplot().plot([0, 1], [0, 1], color=colour)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path)
    plt.close(figure)


def build(tmp_path, pages, built, approved):
    """Write a synthetic tree: pages, the build's images, and the baselines.

    ``pages`` maps a path under the source root to its text; ``built`` and
    ``approved`` each map a figure name to the colour it is drawn in, so two
    tables differing in one colour are a figure that has drifted.
    """
    source = tmp_path / "src"
    for quadrant in gate.QUADRANTS:
        (source / quadrant).mkdir(parents=True, exist_ok=True)
    for relative, text in pages.items():
        page = source / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(text, encoding="utf-8")
    root = tmp_path / "html"
    (root / gate.IMAGES).mkdir(parents=True, exist_ok=True)
    for name, colour in built.items():
        render(root / gate.IMAGES / f"{name}{gate.SUFFIX}", colour)
    baselines = tmp_path / "baseline"
    baselines.mkdir(parents=True, exist_ok=True)
    for name, colour in approved.items():
        render(baselines / f"{name}{gate.SUFFIX}", colour)
    return root, source, baselines


def run(monkeypatch, capsys, module, tree):
    """Run one of the two commands over a synthetic tree; return code and output."""
    root, source, baselines = tree
    monkeypatch.setattr(
        module.sys,
        "argv",
        [module.__name__, str(root), str(source), str(baselines)],
    )
    code = module.main()
    return code, capsys.readouterr().out


def flat(out: str) -> str:
    """Undo the wrapping, so an assertion names a phrase and not a line."""
    return " ".join(out.split())


@pytest.fixture
def unlisted(monkeypatch):
    """Empty ``PUBLISHES``, which names real pages a synthetic tree has not got.

    Without this every case below would fail on the same refusal -- the one that
    reports a listed page declaring nothing -- and never reach the check it was
    written for.
    """
    monkeypatch.setattr(gate, "PUBLISHES", ())


def test_a_prefix_is_the_only_option():
    """The declaration is read whether or not other options accompany it."""
    assert gate.declarations(
        ".. plot::\n    :filename-prefix: alpha\n\n    value = 1\n"
    ) == ["alpha"]


def test_a_prefix_after_another_option_is_read():
    text = ".. plot::\n    :context: reset\n    :filename-prefix: alpha\n\n    x = 1\n"
    assert gate.declarations(text) == ["alpha"]


def test_a_prefix_before_another_option_is_read():
    text = ".. plot::\n    :filename-prefix: alpha\n    :context: reset\n\n    x = 1\n"
    assert gate.declarations(text) == ["alpha"]


def test_that_option_under_another_directive_is_not_a_declaration():
    """The directive line is matched too, so only a plot declares a figure."""
    assert gate.declarations(".. figure:: a.png\n    :filename-prefix: alpha\n") == []


def test_a_plot_with_no_prefix_declares_nothing():
    assert gate.declarations(".. plot::\n    :context:\n\n    value = 1\n") == []


def test_the_declarations_are_in_document_order():
    assert gate.declarations(declare("alpha", "beta")) == ["alpha", "beta"]


def test_a_declaration_is_not_read_through_an_earlier_plot():
    """The option run ends at the blank line, so the search cannot cross a block."""
    text = (
        ".. plot::\n    :context:\n\n    value = 1\n\n"
        ".. plot::\n    :filename-prefix: beta\n\n    value = 2\n"
    )
    assert gate.declarations(text) == ["beta"]


@pytest.mark.usefixtures("unlisted")
def test_a_matching_tree_passes(tmp_path, monkeypatch, capsys):
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha", "beta")},
        {"alpha": "red", "beta": "blue"},
        {"alpha": "red", "beta": "blue"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 0
    assert "2 compared within RMS 2, across 1 page" in out


@pytest.mark.usefixtures("unlisted")
def test_the_success_line_counts_the_pages_it_read(tmp_path, monkeypatch, capsys):
    """A count of figures alone would not show a page dropping out of the scan."""
    tree = build(
        tmp_path,
        {
            "howtos/guide.rst": declare("alpha"),
            "explanation/theory.rst": declare("beta"),
        },
        {"alpha": "red", "beta": "blue"},
        {"alpha": "red", "beta": "blue"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 0
    assert "2 compared within RMS 2, across 2 pages" in out


@pytest.mark.usefixtures("unlisted")
def test_a_declared_figure_that_was_not_built_fails(tmp_path, monkeypatch, capsys):
    """The shape a `:filename-prefix:` beside a `:nofigs:` takes."""
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha", "beta")},
        {"alpha": "red"},
        {"alpha": "red", "beta": "blue"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "these declared figures were not built" in out
    assert "beta (howtos/guide.rst)" in out
    assert "drop the ':nofigs:' and publish the figure" in flat(out)


@pytest.mark.usefixtures("unlisted")
def test_a_figure_with_no_baseline_fails(tmp_path, monkeypatch, capsys):
    """What is published has never been approved, which is not a pass."""
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha", "beta")},
        {"alpha": "red", "beta": "blue"},
        {"alpha": "red"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "these figures have no baseline" in out
    assert "beta (howtos/guide.rst)" in out


@pytest.mark.usefixtures("unlisted")
def test_a_changed_figure_fails(tmp_path, monkeypatch, capsys):
    """The failure the gate exists for: the snippet runs and draws something else."""
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha")},
        {"alpha": "red"},
        {"alpha": "blue"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "these figures no longer match" in out
    assert "alpha (RMS " in out
    assert "tolerance 2)" in out


@pytest.mark.usefixtures("unlisted")
def test_a_figure_within_tolerance_passes(tmp_path, monkeypatch, capsys):
    """The comparison is a tolerance and not an equality, as `pytest-mpl`'s is."""
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha")},
        {"alpha": "#ff0000"},
        {"alpha": "#fe0000"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 0, out


@pytest.mark.usefixtures("unlisted")
def test_an_orphaned_baseline_fails(tmp_path, monkeypatch, capsys):
    """A renamed section leaves a baseline that ships and is never read again."""
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha")},
        {"alpha": "red"},
        {"alpha": "red", "stale": "blue"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "these baselines are claimed by no page" in out
    assert "stale.png" in out


@pytest.mark.usefixtures("unlisted")
def test_a_tree_declaring_no_figure_fails(tmp_path, monkeypatch, capsys):
    """A gate that finds nothing to check reports a green tick over nothing."""
    tree = build(tmp_path, {"howtos/guide.rst": "Prose only.\n"}, {}, {})
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "no page declares a figure" in out
    assert "remove this gate rather than leaving it green" in flat(out)
    assert "'Published Figures' in docs/src/developer/docs-style.rst" in out


def test_a_listed_page_that_declares_nothing_fails(tmp_path, monkeypatch, capsys):
    """A page that stopped declaring is a page no other check here reports.

    Every other check reads the declarations, so an empty page is invisible to
    all of them.
    """
    monkeypatch.setattr(gate, "PUBLISHES", ("howtos/quiet.rst",))
    tree = build(
        tmp_path,
        {
            "howtos/guide.rst": declare("alpha"),
            "howtos/quiet.rst": "Prose only.\n",
        },
        {"alpha": "red"},
        {"alpha": "red"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "these pages declare no figure" in out
    assert "howtos/quiet.rst" in out
    assert "'Published Figures' in docs/src/developer/docs-style.rst" in out


@pytest.mark.usefixtures("unlisted")
def test_the_report_says_what_it_did_not_list(tmp_path, monkeypatch, capsys):
    """Truncation that does not say it truncated reads as the whole story."""
    names = [f"figure{index}" for index in range(gate.SHOWN + 2)]
    tree = build(tmp_path, {"howtos/guide.rst": declare(*names)}, {}, {})
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "... and 2 more" in out


@pytest.mark.usefixtures("unlisted")
def test_the_gate_names_the_style_guide_on_every_refusal(tmp_path, monkeypatch, capsys):
    """A refusal is only actionable if it says where the rule is written down.

    The section is named as well as the file, because the file is long and the
    rules live in one part of it.
    """
    tree = build(tmp_path, {"howtos/guide.rst": declare("alpha")}, {}, {})
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "'Published Figures' in docs/src/developer/docs-style.rst" in out


@pytest.mark.usefixtures("unlisted")
def test_blessing_refuses_a_figure_that_was_not_built(tmp_path, monkeypatch, capsys):
    """Blessing the rest would leave the gate red for a reason this appears to fix."""
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha", "beta")},
        {"alpha": "red"},
        {},
    )
    code, out = run(monkeypatch, capsys, bless, tree)
    assert code == 1
    assert "these declared figures were not built" in out
    assert "Nothing was blessed" in out
    assert not (tree[2] / "alpha.png").exists()


@pytest.mark.usefixtures("unlisted")
def test_blessing_refuses_a_tree_declaring_no_figure(tmp_path, monkeypatch, capsys):
    tree = build(tmp_path, {"howtos/guide.rst": "Prose only.\n"}, {}, {})
    code, out = run(monkeypatch, capsys, bless, tree)
    assert code == 1
    assert "nothing to bless" in out


@pytest.mark.usefixtures("unlisted")
def test_blessing_adds_updates_and_removes(tmp_path, monkeypatch, capsys):
    """One command and a diff to read, rather than a hand copy per file."""
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha", "beta")},
        {"alpha": "red", "beta": "blue"},
        {"alpha": "green", "stale": "black"},
    )
    code, out = run(monkeypatch, capsys, bless, tree)
    assert code == 0
    assert "added    beta" in out
    assert "updated  alpha" in out
    assert "removed  stale.png" in out
    assert "1 added, 1 updated, 1 removed" in out
    assert "approves a regression as readily as a fix" in flat(out)


@pytest.mark.usefixtures("unlisted")
def test_blessing_a_matching_tree_changes_nothing(tmp_path, monkeypatch, capsys):
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha")},
        {"alpha": "red"},
        {"alpha": "red"},
    )
    code, out = run(monkeypatch, capsys, bless, tree)
    assert code == 0
    assert "nothing changed" in out


@pytest.mark.usefixtures("unlisted")
def test_blessing_makes_the_gate_pass(tmp_path, monkeypatch, capsys):
    """The two commands compose, which is the loop a contributor runs."""
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha", "beta")},
        {"alpha": "red", "beta": "blue"},
        {"alpha": "green", "stale": "black"},
    )
    assert run(monkeypatch, capsys, bless, tree)[0] == 0
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 0, out


def test_every_page_that_publishes_a_figure_is_listed():
    """``PUBLISHES`` is what fails when the declaration pattern stops matching.

    A converted page missing from it leaves the gate reporting nothing wrong.
    """
    figures = gate.collect(REPO / "docs" / "src", Path("images"), BASELINE)
    assert {figure.page for figure in figures} == set(gate.PUBLISHES)


def test_every_committed_baseline_is_claimed_by_a_page():
    """The orphan check, run in the test matrix rather than only in a build."""
    figures = gate.collect(REPO / "docs" / "src", Path("images"), BASELINE)
    claimed = {figure.baseline.name for figure in figures}
    found = {path.name for path in BASELINE.glob(f"*{gate.SUFFIX}")}
    assert found == claimed
```

Three things about this module that are not obvious:

- **The `unlisted` fixture is load-bearing.** `PUBLISHES` names two real pages, and a
  synthetic tree has neither, so without it every case would fail on the same refusal — a
  listed page declaring nothing — and never reach the check it was written for. One test
  deliberately does *not* use it, and monkeypatches `PUBLISHES` to a synthetic page instead,
  which is what keeps that branch reachable.
- **The tolerance test is a real measurement.** `#ff0000` against `#fe0000` is RMS 0.12
  — non-zero, and inside the tolerance of 2. `red` against `blue` is RMS 25. Identical files
  return `None`. So the passing case is a tolerance and not an accident of equality.
- **The last two tests read the real tree**, not a synthetic one, and are the reason the
  orphan and registry checks are asserted in the test matrix rather than only in a
  documentation build.

- [ ] **Step 5: Run the module against a tree with no baselines yet**

Run: `pixi run --frozen pytest tests/test_docs_figures.py -q`
Expected: FAIL — 23 pass, and the two real-tree tests fail, because `docs/baseline` does not
exist yet. That is the correct failure and the next step is what fixes it.

- [ ] **Step 6: Add the pixi tasks**

In `pyproject.toml`, after the `docs-check-links` task and **before** the comment block that
belongs to the `docs` task:

```toml
[tool.pixi.feature.docs.tasks.docs-check-figures]
cmd = "python .github/scripts/check_docs_figures.py docs/_build/html"
depends-on = ["docs-html"]
description = "Check that every published figure matches its baseline"

# Blesses whatever the build just rendered, which is why it is a task a
# contributor runs deliberately and not something `docs` depends on: the diff it
# writes into `docs/baseline` is the thing to read before committing, and a
# regression approves just as quietly as an improvement (plots spec §3.6).
[tool.pixi.feature.docs.tasks.docs-figures]
cmd = "python .github/scripts/bless_docs_figures.py docs/_build/html"
depends-on = ["docs-html"]
description = "Re-bless the published figure baselines from the build"
```

The existing comment above the `docs` task describes the two gates it depended on. It has to
stay attached to `docs` — inserting the new tasks between the comment and the table it
introduces orphans it — and it needs the third gate:

```toml
# The gate of docs spec §3.7, the documentation-link check and the figure gate of
# plots spec §3.5 all read the build's output, and the first two ran only in
# `ci-docs.yml` until :issue:`91`. Each script has a test module of its own —
# `tests/test_rendered_citations.py`, `tests/test_documentation_links.py` and
# `tests/test_docs_figures.py` — so what `pixi run tests` and `pixi run lint`
# could not see is not the scripts but each gate's verdict over a real build, and
# a build that linked no citation at all exits 0. `docs` therefore depends on all
# three, and a contributor reproduces a `ci-docs` failure without pushing.
[tool.pixi.feature.docs.tasks.docs]
depends-on = ["docs-check-citations", "docs-check-links", "docs-check-figures"]
description = "Build the HTML documentation and check its output"
```

- [ ] **Step 7: Bless the baselines**

```bash
pixi run --frozen docs-figures
```

Expected: `11 added, 0 updated, 0 removed`, and the warning that this approves a regression
as readily as a fix. Then look at `docs/baseline/` — 11 PNGs, roughly 1.7 MB.

**Read what was blessed.** The images were inspected in Tasks 2 and 3, so this is a
confirmation rather than a first look, but the command is the one place in the workflow
where a wrong picture becomes an approved picture.

- [ ] **Step 8: Run everything**

Run: `pixi run --frozen pytest tests/test_docs_figures.py -q`
Expected: `25 passed`.

Run: `pixi run --frozen docs`
Expected: `published figures ok: 11 compared within RMS 2, across 2 pages (plots spec §3.5)`.

- [ ] **Step 9: Prove the gate's tests are not vacuous**

Staged first, as in Task 2. Four mutations, each isolating the right test:

1. `PUBLISHES = ("howtos/emphasis.rst",)` → exactly
   `test_every_page_that_publishes_a_figure_is_listed` fails.
2. Drop the `^` and `$` anchors from `DECLARATION` → exactly one test fails.
3. `touch docs/baseline/stray.png` → exactly
   `test_every_committed_baseline_is_claimed_by_a_page` fails.
4. `TOLERANCE = 1000` → three tests fail:
   `test_a_changed_figure_fails`, and the two whose success messages quote the number.

Each mutation is in the *tolerant* direction where possible: a mutation that breaks a shared
helper floods the suite and proves nothing about which assertion is load-bearing.

- [ ] **Step 10: Lint and commit**

```bash
git add .github/scripts/check_docs_figures.py .github/scripts/bless_docs_figures.py \
        tests/test_docs_figures.py docs/baseline pyproject.toml
pixi run --frozen lint
git commit -m "Pin the published figures against approved baselines"
```

Check the committed mode: `git ls-files -s .github/scripts/*_docs_figures.py` should show
`100755` for both.

---

### Task 5: Run the gate in CI, and keep the baselines out of the sdist

The gate now runs in `pixi run docs`, which a contributor runs locally. `ci-docs.yml` runs
its tasks one step at a time with `--skip-deps` rather than invoking `docs`, so a new gate
does not reach CI by being depended upon — it reaches CI by being named.

**Read the sequencing note in the File Structure table before running this task's tests.**

- [ ] **Step 1: Add the CI step**

In `.github/workflows/ci-docs.yml`, after the existing link-check step and before the
comment introducing the two network-reaching steps:

```yaml
      - name: Check the published figures
        run: pixi run --frozen --environment docs --skip-deps docs-check-figures
```

Placement matters in one respect only: it must come after `docs-html`, which the earlier
steps have already run. `--skip-deps` means the step does not rebuild.

- [ ] **Step 2: Extend the workflow's own gate**

`tests/test_docs_workflow.py` asserts the set of task names the job runs. It is an equality,
deliberately — its comment says a job that dropped `docs-check-links` would still be running
three tasks and still pass anything looser. So the new task is added to `GATES`:

```python
GATES = {
    "docs-html",
    "docs-check-citations",
    "docs-check-links",
    "docs-check-figures",
    "docs-browser-test",
}
```

- [ ] **Step 3: Keep the baselines out of the sdist**

In `MANIFEST.in`, beside the two existing prunes:

```
prune docs/baseline
```

1.7 MB of PNGs that only a documentation build and a repository checkout consume. `.github`
is already pruned, which is why `tests/test_docs_figures.py` carries the module-level skip.

- [ ] **Step 4: Verify**

Run: `pixi run --frozen pytest tests/test_docs_workflow.py -q`

Expected before Task 4's commit is in `HEAD`: **one failure**,
`test_the_workflow_runs_the_documentation_gates_by_task_name`, reporting
`Extra items in the right set: 'docs-check-figures'`. `_tasks()` reads
`git show HEAD:pyproject.toml`, so the task the workflow now names is not yet visible to it.
This is the sequencing note from the File Structure table. It is not a defect.

After committing Task 4 (or with this task's commit made first and the test re-run), the
module passes.

- [ ] **Step 5: Prove the workflow test is not vacuous**

Remove the new CI step, keep `GATES`, and run the module: exactly
`test_the_workflow_runs_the_documentation_gates_by_task_name` fails, this time reporting the
task missing from the *left* set. Restore it.

Then check the sdist:

```bash
pixi run --frozen python -m build --sdist --outdir /tmp/sdist-check
tar -tzf /tmp/sdist-check/*.tar.gz | grep -c 'docs/baseline' || echo "pruned"
```

Expected: `pruned`. And confirm `tests/test_docs_figures.py` *is* in the archive — it ships
without the scripts it tests, which is what the module-level skip is for.

- [ ] **Step 6: Lint and commit**

```bash
git add .github/workflows/ci-docs.yml tests/test_docs_workflow.py MANIFEST.in
pixi run --frozen lint
git commit -m "Run the published-figure gate in CI"
```

---

### Task 6: Write the rules down

The gate refuses; the style guide is where an author reads the rule before writing. Four
documents change, and one of them is the plots spec itself.

- [ ] **Step 1: Add "Published Figures" to the style guide**

In `docs/src/developer/docs-style.rst`, a new section immediately after "Code Examples" and
before "Attribute Documentation". It carries: the one-form-per-page rule, the
one-picture-per-section cadence, the five option rules of plots spec §3.2, the module-state
rule of §3.3, and how to re-bless.

```rst
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

One picture per section, not per block. A page is a session in which a later block
supersedes an earlier one — two blocks of :ref:`howto-emphasis` call
``ax.isotherms(...)`` on the same axes — so a picture after every block would
sometimes show a state the surrounding prose has stopped describing.

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
  figure gate reports.
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
```

Two things to check rather than assume:

- The citations are `plots spec §…`, unbackticked. A backticked citation is an inline
  literal and not a link, and the citation gate counts literals as legitimate.
- `:ref:` targets `howto-emphasis` and `configure-from-a-file` must exist. Grep for the
  label definitions before the build tells you.

- [ ] **Step 2: The gate's message must name the section that now exists**

`check_docs_figures.py` prints a style-guide pointer on every refusal. Confirm all three
trailers say `'Published Figures'` and not the name of a neighbouring section, and that
`tests/test_docs_figures.py` asserts the *whole* string:

```bash
grep -c "Published Figures" .github/scripts/check_docs_figures.py   # 3
grep -c "'Published Figures' in docs/src/developer/docs-style.rst" tests/test_docs_figures.py  # 3
```

A test asserting only `docs-style.rst` passes while the gate points at a section that does
not exist. This is worth a step of its own because it is exactly the failure the gate is
meant to prevent, one level up.

- [ ] **Step 3: Update the docs spec — §3.9, the snippet gate**

`docs/src/developer/specs/2026-08-03-published-specs-design.md` describes the gate Task 2
changed, and three of its passages are now incomplete. Add, after the paragraph ending "the
ordinary case in the explanation quadrant":

```markdown
**A python block takes one of two directives, and the extractor knows both.** `code-block`
(with its `code` and `sourcecode` spellings) is the plain form. `.. plot::` is the form that
also renders its block as a figure on the page, and its body is python by definition rather
than by a language argument — so it is matched by a pattern of its own, and contributes its
lines to the page's script exactly as a `code-block:: python` body does. The page shape that
directive brings with it — one form per page, the session options each block carries, the
name every published figure declares — is
[plots spec](2026-08-17-published-figures-design.md) §3.2, and is asserted in this gate
rather than in the style guide because this is the gate that already reads every user page
as text.
```

Extend the exemption paragraph, whose last sentence currently ends "which is not knowable
now":

```markdown
`:nofigs:` is not that exemption and does not become one: it suppresses the
*picture*, and the block it sits on runs here like any other.
```

And after the paragraph giving the three reasons this gate holds no baselines:

```markdown
Those three reasons are each a statement about where *this* gate runs, and none of them
rules out a comparison somewhere else.
[plots spec](2026-08-17-published-figures-design.md) §3.5 is that somewhere else: a
documentation-side gate over the images a build published, in the one environment that
builds them, keyed on the name each figure declares. It takes nothing from this section —
this gate gains no baselines — and the sentence above stays the reason it is narrow. This
pins the constructions, in the test matrix, on every supported Python; that pins the
artifacts, once, where they are built.
```

That third edit is the one that matters most. Without it the docs spec reads as ruling out
image comparison in the project, when what it rules out is image comparison *in that gate*.

- [ ] **Step 4: Update the parent spec — §8.6, the documentation extensions**

In `docs/src/developer/specs/2026-07-22-tephpy-design.md`, the extensions bullet gains
`plot_directive` with the sentence separating it from the gallery:

```markdown
  Plus `matplotlib.sphinxext.plot_directive`, which renders a user page's own snippets as
  figures — not from geovista, and not the gallery above: a gallery entry is a standalone
  worked example and a how-to figure is subordinate to a paragraph
  ([plots spec](2026-08-17-published-figures-design.md) §5).
```

"Not from geovista" earns its place: every other extension in that list is inherited from
geovista's documentation, and a reader who knows that would otherwise assume this one is
too.

- [ ] **Step 5: Sweep the plots spec for drift**

Editing a living spec means sweeping it, not only the section you came for. Two things in
`docs/src/developer/specs/2026-08-17-published-figures-design.md` are now stale:

- **§1 is written in the present tense** about a state this branch ends — "shows no
  picture", "has to build". Re-tense to the past: the specification describes the problem
  that was solved, and a living spec that describes a fixed problem in the present tense
  reads as an open defect.
- **Two §6 bullets are now wrong.** The style-guide bullet named a section that did not
  exist when the spec was written; it now names "Published Figures" and says what it
  carries. The extensions bullet said `plot_directive` "joins the list" — it has.

- [ ] **Step 6: Build and check the citations**

```bash
pixi run --frozen docs
```

Expected: `build succeeded`, and all three gates green. Check the citation gate's
linked/literal ratio in its output rather than only its exit code: it exits 0 on a
backticked citation, counting it as a legitimate literal.

- [ ] **Step 7: Lint and commit**

```bash
git add docs/src/developer/docs-style.rst docs/src/developer/specs
pixi run --frozen lint
git commit -m "Write down the published-figure rules"
```

---

### Task 7: The changelog fragment

- [ ] **Step 1: Open the pull request first**

The fragment is named for the pull request number, and issues filed before it steal numbers
from the sequence. So push the branch, open the PR, read the number it was given, and only
then write the file. Expect the fragment to land as a second commit rather than an amend.

```bash
git push -c credential.helper= -c credential.helper='!gh auth git-credential' \
    -u origin docs-published-figures
gh pr create --title "Publish figures in the how-to guides" --body-file -
```

The PR body takes bare `#N` references, not Sphinx roles — `{issue}` and `{pull}` render
literally on GitHub, and no gate scans a PR body.

- [ ] **Step 2: Write the fragment**

`changelog/<PR>.documentation.rst`. Cross-reference documented APIs with Sphinx roles rather
than quoting their names, cite the issue with `:issue:`, and end with the attribution:

```rst
The :ref:`howto-emphasis` and :ref:`howto-logo` how-to guides now show the figures
their snippets produce, rendered from those snippets by the build rather than
described in prose (:issue:`NN`). Each published image is compared against an
approved baseline whenever the documentation is built, so a change in what a
snippet draws fails the build rather than reaching the published page unnoticed.
Re-approve an intended change with ``pixi run docs-figures``. (:user:`claude`)
```

- [ ] **Step 3: Verify it renders**

The changelog is built into the documentation, so a broken cross-reference is a build
warning and `-W` makes it an error. Verify against a **clean** build — an incremental one
serves a stale draft:

```bash
pixi run --frozen docs
```

Then read the rendered page, not the source: a `:ref:` that resolves to the wrong target
renders as a link with the wrong text and warns about nothing.

---

## Verification

Run in order, from a clean tree, before the branch is ready:

- [ ] `pre-commit install` — hooks are not installed in a fresh worktree.
- [ ] `pixi run --frozen lint` — expected: clean. Both new scripts are mode `100755`;
      `EXE001` is what catches it if not.
- [ ] `pixi run --frozen tests` — expected: **1437 collected, 1437 passed**. The arithmetic:
      1404 before this branch, `+8` in `tests/test_docs_snippets.py`, `+25` in
      `tests/test_docs_figures.py`. A count that *falls* after adding tests means something
      was destroyed; check against `main` before pushing.
- [ ] `pixi run --frozen docs` — expected: `build succeeded`, no warnings, and three gate
      lines, the third reading
      `published figures ok: 11 compared within RMS 2, across 2 pages (plots spec §3.5)`.
- [ ] `ls docs/_build/html/_images/*.png | wc -l` — expected: 11. Sphinx copies only
      *referenced* images into `_images`, so this is the count of figures that actually
      reached the published pages, not the count that was rendered.
- [ ] `git status --short docs/src/` — expected: empty. `logo.rst` calls
      `fig.savefig("sounding.png")`, and this is what proves `plot_working_directory`
      redirected it out of the source tree.
- [ ] Open `docs/_build/html/howtos/emphasis.html` and `logo.html` in a browser and **look
      at every figure**. A gate compares an image to its baseline; nothing in this branch
      can tell you the baseline shows what the paragraph above it claims. This step is the
      only one that can.

## Constraints this work must not break

- **The snippet gate still refuses its own empty input.** Docs spec §3.9 makes that a
  property of the gate, and Task 2 adds two derived corpora — `plot_directives()` and
  `figure_pages()` — either of which could silently become empty. Both are pinned by
  membership, not by a count alone.
- **A page is a session.** The snippet gate concatenates a page's blocks into one script and
  runs it once. `.. plot::` bodies join that script; `:nofigs:` blocks join it too. A block
  that stops contributing its lines breaks a later block in a way that looks like a defect
  in the later block.
- **No page mutates module state.** `tephpy.config` assignment in any published block leaks
  across every page built afterwards, and the resulting baseline mismatch appears on a page
  nobody edited. `:context: reset` does not protect against this.
- **`pixi run docs` remains a clean build.** `docs-html` depends on `docs-clean`, which is
  why the figure gate can trust `_build/html/_images` to hold this build's output and
  nothing else. A change making the build incremental silently weakens the gate to "matches
  a baseline, or matched one once".
- **The baselines are 1.7 MB in the repository and not in the sdist.** `prune docs/baseline`
  is what keeps that true; the sdist is checked in Task 5.
- **`tests/test_docs_figures.py` must survive an unpacked sdist.** `.github` is pruned, so
  the module-level `pytest.mark.skipif` is load-bearing: an unconditional import of the
  scripts breaks collection rather than skipping it.
- **The gate names a section that exists.** Its refusals point at "Published Figures" in
  `docs/src/developer/docs-style.rst`. If that section is ever renamed, three strings and
  three assertions move with it.
