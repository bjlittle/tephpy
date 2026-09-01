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


def render(path: Path, colour: str, size: tuple[float, float] = (1.0, 1.0)) -> None:
    """Write a small PNG.

    Every image shares one size by default, which ``compare_images`` requires
    of the pair it is given; a caller wanting a size mismatch passes a
    different ``size``.
    """
    figure = plt.figure(figsize=size, dpi=50)
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


def test_a_directive_not_at_the_start_of_its_line_is_not_read():
    """The leading anchor: text before '.. plot::' on its own line hides it."""
    assert gate.declarations("see xx.. plot::\n    :filename-prefix: gamma\n") == []


def test_a_value_with_more_after_it_on_the_line_is_not_read():
    """The trailing anchor: a second token after the value hides it too."""
    assert gate.declarations(".. plot::\n    :filename-prefix: delta epsilon\n") == []


def test_the_declarations_are_in_document_order():
    assert gate.declarations(declare("alpha", "beta")) == ["alpha", "beta"]


def test_a_declaration_is_not_read_through_an_earlier_plot():
    """A declaration in a later block is found, past an earlier block with none."""
    text = (
        ".. plot::\n    :context:\n\n    value = 1\n\n"
        ".. plot::\n    :filename-prefix: beta\n\n    value = 2\n"
    )
    assert gate.declarations(text) == ["beta"]


def test_a_declaration_is_not_read_across_a_directive_boundary():
    r"""The option run must stay inside its own block.

    A widened run -- ``(?:\n.*)*?`` in place of the strict per-line pattern --
    would read a ':filename-prefix:' under a later, unrelated directive as if
    it belonged to an earlier '.. plot::', which is what this pins against.
    """
    text = (
        ".. plot::\n    :context:\n\n    v = 1\n\n"
        ".. figure:: a.png\n    :filename-prefix: alpha\n"
    )
    assert gate.declarations(text) == []


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
def test_a_size_mismatch_is_reported_as_changed(tmp_path, monkeypatch, capsys):
    """`compare_images` raises rather than returns when the sizes differ.

    `plot_rcparams`'s figure size is one config change away from breaking
    every baseline this way, so this is not a hypothetical shape: the gate
    must report it rather than abort on the first offender it meets.
    """
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha")},
        {"alpha": "red"},
        {"alpha": "red"},
    )
    root, _source, _baselines = tree
    render(root / gate.IMAGES / "alpha.png", "red", size=(2.0, 1.0))
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "these figures no longer match" in out
    assert "alpha (size" in out


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
def test_a_malformed_declaration_is_reported(tmp_path, monkeypatch, capsys):
    """A tab-indented option is invisible to `declarations()`.

    Left alone, this would leave the figure it names silently unpinned: the
    page still satisfies `PUBLISHES` through its other, well-formed figure.
    The other shape `MALFORMED` names -- a value with embedded whitespace -- is
    pinned separately by `test_a_spaced_value_is_reported_by_the_gate`.
    """
    text = (
        ".. plot::\n"
        "    :context: reset\n"
        "    :filename-prefix: alpha\n"
        "\n"
        "    value = 0\n"
        ".. plot::\n"
        "\t:filename-prefix: beta\n"
        "\n"
        "    value = 1\n"
    )
    tree = build(
        tmp_path,
        {"howtos/guide.rst": text},
        {"alpha": "red"},
        {"alpha": "red"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "these look like declarations and are not read" in out
    assert "'beta' (howtos/guide.rst)" in out


@pytest.mark.usefixtures("unlisted")
def test_a_case_variant_option_name_is_reported(tmp_path, monkeypatch, capsys):
    """Docutils lowercases directive option names, so this spelling is real input.

    Left alone, ``:Filename-Prefix:`` is invisible to both ``DECLARATION`` and
    the (case-sensitive) ``CANDIDATE`` alike: the figure is silently published
    and pinned by nothing, and neither ``declarations()`` nor ``malformed()``
    reports anything wrong. ``CANDIDATE``, widened with ``re.IGNORECASE``,
    turns this into a reported near miss instead -- while ``DECLARATION``
    stays case-sensitive, so the variant is reported rather than accepted.
    """
    text = (
        ".. plot::\n"
        "    :context: reset\n"
        "    :filename-prefix: alpha\n"
        "\n"
        "    value = 0\n"
        ".. plot::\n"
        "    :context: close-figs\n"
        "    :Filename-Prefix: probe-case\n"
        "\n"
        "    value = 1\n"
    )
    tree = build(
        tmp_path,
        {"howtos/guide.rst": text},
        {"alpha": "red"},
        {"alpha": "red"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "these look like declarations and are not read" in out
    assert "'probe-case' (howtos/guide.rst)" in out


@pytest.mark.usefixtures("unlisted")
def test_a_spaced_value_is_reported_by_the_gate(tmp_path, monkeypatch, capsys):
    """A value with embedded whitespace is reported end-to-end, not just refused.

    `test_a_value_with_more_after_it_on_the_line_is_not_read` pins the same
    shape at the pattern level: ``declarations()`` returns nothing for it. That
    proves only half of what `MALFORMED` promises -- that the strict pattern
    rejects the value. It does not prove the gate then *reports* the figure
    rather than losing it, which is what :data:`CANDIDATE` and `malformed()`
    exist for. This test exercises that second, separate path: the same
    defect class, caught by running the whole gate rather than by reading the
    pattern's return value.
    """
    text = (
        ".. plot::\n"
        "    :context: reset\n"
        "    :filename-prefix: alpha\n"
        "\n"
        "    value = 0\n"
        ".. plot::\n"
        "    :context: close-figs\n"
        "    :filename-prefix: delta epsilon\n"
        "\n"
        "    value = 1\n"
    )
    tree = build(
        tmp_path,
        {"howtos/guide.rst": text},
        {"alpha": "red"},
        {"alpha": "red"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 1
    assert "these look like declarations and are not read" in out
    assert "'delta epsilon' (howtos/guide.rst)" in out


@pytest.mark.usefixtures("unlisted")
def test_a_well_formed_page_reports_no_malformed_declaration(
    tmp_path, monkeypatch, capsys
):
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha", "beta")},
        {"alpha": "red", "beta": "blue"},
        {"alpha": "red", "beta": "blue"},
    )
    code, out = run(monkeypatch, capsys, gate, tree)
    assert code == 0
    assert "look like declarations" not in out


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


def test_the_gate_names_the_style_guide_on_every_refusal(tmp_path, monkeypatch, capsys):
    """A refusal is only actionable if it says where the rule is written down.

    The section is named as well as the file, because the file is long and the
    rules live in one part of it. All three sites that print the line are
    exercised, reusing the tree each already has a test of its own for: an
    empty declared set, a listed page that declares nothing, and a per-figure
    failure.
    """
    line = "'Published Figures' in docs/src/developer/docs-style.rst"

    monkeypatch.setattr(gate, "PUBLISHES", ())
    empty = build(tmp_path / "empty", {"howtos/guide.rst": "Prose only.\n"}, {}, {})
    code, out = run(monkeypatch, capsys, gate, empty)
    assert code == 1
    assert line in out

    monkeypatch.setattr(gate, "PUBLISHES", ("howtos/quiet.rst",))
    silent = build(
        tmp_path / "silent",
        {
            "howtos/guide.rst": declare("alpha"),
            "howtos/quiet.rst": "Prose only.\n",
        },
        {"alpha": "red"},
        {"alpha": "red"},
    )
    code, out = run(monkeypatch, capsys, gate, silent)
    assert code == 1
    assert line in out

    monkeypatch.setattr(gate, "PUBLISHES", ())
    pages = {"howtos/guide.rst": declare("alpha")}
    unbuilt = build(tmp_path / "unbuilt", pages, {}, {})
    code, out = run(monkeypatch, capsys, gate, unbuilt)
    assert code == 1
    assert line in out


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
def test_blessing_refuses_a_malformed_declaration(tmp_path, monkeypatch, capsys):
    """The remedy for a near miss must not be the thing that destroys the pin.

    ``:Filename-Prefix:`` is valid to Sphinx and refused by ``DECLARATION``, so
    the build publishes 'beta' under a name no declaration claims. The gate
    reports the near miss and, for the orphan it also sees, sends the
    contributor to this command -- which without this refusal ran its sweep over
    a set it had every means to know was short, deleted the live baseline, and
    exited 0 reporting it as 'removed', which is what a genuine rename prints.
    """
    text = (
        ".. plot::\n"
        "    :context: reset\n"
        "    :filename-prefix: alpha\n"
        "\n"
        "    value = 0\n"
        ".. plot::\n"
        "    :context: close-figs\n"
        "    :Filename-Prefix: beta\n"
        "\n"
        "    value = 1\n"
    )
    tree = build(
        tmp_path,
        {"howtos/guide.rst": text},
        {"alpha": "red", "beta": "blue"},
        {"alpha": "red", "beta": "blue"},
    )
    code, out = run(monkeypatch, capsys, bless, tree)
    assert code == 1
    assert "these look like declarations and are not read" in out
    assert "'beta' (howtos/guide.rst)" in out
    assert "Nothing was blessed" in out
    assert (tree[2] / "beta.png").is_file()


def test_blessing_refuses_a_listed_page_that_declares_nothing(
    tmp_path, monkeypatch, capsys
):
    """A page that stopped declaring is every one of its baselines, deleted.

    The same hazard as `test_blessing_refuses_a_malformed_declaration` reached
    the other way: here nothing on the page even looks like a declaration, so
    only ``PUBLISHES`` knows the page is meant to publish. That refusal is the
    gate's, and has to be this command's too -- 'beta' is the baseline the
    quiet page used to claim, and the sweep would take it.
    """
    monkeypatch.setattr(gate, "PUBLISHES", ("howtos/quiet.rst",))
    tree = build(
        tmp_path,
        {
            "howtos/guide.rst": declare("alpha"),
            "howtos/quiet.rst": "Prose only.\n",
        },
        {"alpha": "red"},
        {"alpha": "red", "beta": "blue"},
    )
    code, out = run(monkeypatch, capsys, bless, tree)
    assert code == 1
    assert "these pages declare no figure" in out
    assert "howtos/quiet.rst" in out
    assert "Nothing was blessed" in out
    assert (tree[2] / "beta.png").is_file()


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
    assert "updated  alpha (RMS " in out
    assert "removed  stale" in out
    assert "removed  stale.png" not in out
    assert "1 added, 1 updated, 1 removed" in out
    assert "approves a regression as readily as a fix" in flat(out)
    # Computing the RMS at tolerance 0 makes `compare_images` write a
    # '-failed-diff.png' beside the built image; left behind, it would
    # misname a successful blessing as one with an unresolved diff.
    assert not list((tree[0] / gate.IMAGES).glob("*-failed-diff.png"))


@pytest.mark.usefixtures("unlisted")
def test_blessing_a_size_mismatch_completes_and_copies_every_figure(
    tmp_path, monkeypatch, capsys
):
    """`compare_images` raises rather than returns when the sizes differ.

    Before this was caught, the raise crashed `bless` mid-loop: with the
    mismatch on a later-sorting figure, an earlier one is already copied when
    the exception lands, leaving the baselines half-updated with no summary
    and no exit code. A size change is the ordinary reason to re-bless, so
    this is exercised with the mismatch on 'beta', which sorts after 'alpha'
    -- the figure already blessed under the old, crashing behaviour -- and
    both must still be copied.
    """
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha", "beta")},
        {"alpha": "red", "beta": "blue"},
        {"alpha": "green", "beta": "blue"},
    )
    root, _source, baselines = tree
    render(root / gate.IMAGES / "beta.png", "blue", size=(2.0, 1.0))
    code, out = run(monkeypatch, capsys, bless, tree)
    assert code == 0
    assert "updated  alpha (RMS " in out
    assert "updated  beta (size " in out
    assert (baselines / "alpha.png").read_bytes() == (
        root / gate.IMAGES / "alpha.png"
    ).read_bytes()
    assert (baselines / "beta.png").read_bytes() == (
        root / gate.IMAGES / "beta.png"
    ).read_bytes()


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


def test_a_dotted_prefix_is_reported_rather_than_read():
    """A dot is refused by matplotlib, so a prefix carrying one is not a figure.

    `check_output_base_name` raises `PlotError` for a dot or a slash, so the
    class this pattern modelled was wider than the class that can exist. Reading
    one would have the gate looking for a built image the build never wrote;
    declining to read it hands the value to the near-miss detector, which
    reports it (:issue:`174`).
    """
    text = ".. plot::\n    :filename-prefix: alpha.beta\n\n    x = 1\n"
    assert gate.declarations(text) == []
    assert gate.malformed(text) == ["alpha.beta"]


@pytest.mark.usefixtures("unlisted")
def test_a_failing_comparison_writes_no_diff_into_the_published_tree(
    tmp_path, monkeypatch, capsys
):
    """`docs/_build/html/` is what Read the Docs publishes (:issue:`174`).

    `compare_images` writes its diff beside the built image, which puts it in
    the directory that gets deployed. The gate runs after Sphinx, so the build
    output is complete and publishable at the moment the diff appears -- "a red
    gate should not reach a deploy" is an argument, not a mechanism.
    """
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha")},
        {"alpha": "red"},
        {"alpha": "blue"},
    )
    root, _source, _baselines = tree

    code, _out = run(monkeypatch, capsys, gate, tree)

    assert code == 1
    strays = sorted(path.name for path in (root / gate.IMAGES).glob("*-failed-diff*"))
    assert strays == [], f"the published image directory holds {strays}"


@pytest.mark.usefixtures("unlisted")
def test_a_failing_comparison_keeps_the_diff_where_it_can_be_opened(
    tmp_path, monkeypatch, capsys
):
    """Moving the diff out of the deploy must not cost the contributor the file."""
    tree = build(
        tmp_path,
        {"howtos/guide.rst": declare("alpha")},
        {"alpha": "red"},
        {"alpha": "blue"},
    )
    root, _source, _baselines = tree

    code, out = run(monkeypatch, capsys, gate, tree)

    assert code == 1
    written = sorted((root.parent / gate.DIFFS).glob("*-failed-diff*"))
    assert [path.name for path in written] == ["alpha-failed-diff.png"]
    assert str(written[0]) in flat(out), "the advice does not name the diff it wrote"


def test_the_malformed_advice_does_not_recommend_the_character_that_fails():
    """The diagnostic and the pattern must agree on a dot (:issue:`174`).

    The advice is what a contributor acts on. Recommending the character the
    strict pattern now refuses would send them round the loop that produced the
    failure, so the pattern refusing it and the advice offering it cannot both
    stand.
    """
    dotted = ".. plot::\n    :filename-prefix: alpha.beta\n\n    x = 1\n"
    assert gate.declarations(dotted) == []
    assert "dots and dashes" not in gate.MALFORMED
    assert "digits and dashes" in gate.MALFORMED


def test_the_malformed_advice_counts_the_shapes_it_names():
    """`CANDIDATE` catches a fourth shape now, and the advice enumerates them."""
    shapes = {
        "whitespace": ".. plot::\n    :filename-prefix: alpha beta\n\n    x = 1\n",
        "tab": ".. plot::\n\t:filename-prefix: alpha\n\n\tx = 1\n",
        "case": ".. plot::\n    :Filename-Prefix: alpha\n\n    x = 1\n",
        "dot": ".. plot::\n    :filename-prefix: alpha.beta\n\n    x = 1\n",
    }
    for name, text in shapes.items():
        assert gate.malformed(text), f"the {name} shape is no longer detected"
    assert "four shapes" in gate.MALFORMED, (
        f"the advice names a count that is not {len(shapes)}"
    )


def test_a_diff_that_cannot_be_moved_is_reported_where_it_lies(tmp_path):
    """A gate with a drifted figure to report must still report it (:issue:`174`).

    Creating the destination can fail as readily as the move -- an unwritable
    build parent is the case -- and losing the drift report to an error about
    relocating its own attachment would replace a message a contributor can act
    on with one they cannot.
    """
    diff = tmp_path / "alpha-failed-diff.png"
    diff.write_bytes(b"not really a png")
    # A file where the destination's parent should be. Chosen over an unwritable
    # directory because permission bits are bypassed for uid 0, and a test that
    # goes vacuous in a root container is one that stops holding exactly where
    # nobody is watching.
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"not a directory")

    assert gate.relocate(diff, blocker / gate.DIFFS) == diff
    assert diff.is_file(), "the diff the advice names was lost"
