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
