# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""Tests for the shared-definition tooltip correction (tooltip spec §3.7)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
EXT = REPO / "docs" / "src" / "_ext"

# `sphinx_tippy` lives only in the `docs` feature (tooltip spec §3.1), so this
# module is unimportable in the `test-py3*` environments the CI matrix runs.
# Mirrors the guard `tests/test_readingtime_directive.py` carries for `sphinx`.
sphinx_tippy = pytest.importorskip(
    "sphinx_tippy", reason="the docs feature is not installed here"
)
bs4 = pytest.importorskip("bs4", reason="the docs feature is not installed here")

if str(EXT) not in sys.path:
    sys.path.insert(0, str(EXT))


def _load(name: str):
    """Import an extension module by path; ``_ext`` is not an importable package."""
    path = EXT / f"{name}.py"
    assert path.is_file(), f"the module is missing from {path}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tippy_terms = _load("tephpy_tippy_terms")


class _FakeConfig:
    """As much of ``TippyConfig`` as ``create_id_to_tip_html`` reads."""

    tip_selector = (
        "figure, table, img, p, aside, div.admonition, div.literal-block-wrapper"
    )


def _body(html: str):
    """Parse ``html`` the same way ``sphinx_tippy.collect_tips`` parses a page body."""
    return bs4.BeautifulSoup(html, "html.parser")


def _tips(body):
    """Run the real, unwrapped ``create_id_to_tip_html`` over ``body``."""
    return sphinx_tippy.create_id_to_tip_html(_FakeConfig(), body)


def test_a_two_term_group_gives_both_terms_the_definition():
    body = _body(
        "<dl>"
        '<dt id="term-alpha">alpha</dt>'
        '<dt id="term-beta">beta</dt>'
        "<dd><p>shared definition</p></dd>"
        "</dl>"
    )
    # The defect, reproduced: without the fix only the last `<dt>` of the
    # group is given the `<dd>`.
    assert "<dd" not in _tips(body).get("term-alpha", "")

    tippy_terms._duplicate_definitions(body)
    fixed = _tips(body)

    assert "<dd" in fixed["term-alpha"]
    assert "<dd" in fixed["term-beta"]
    assert "shared definition" in fixed["term-alpha"]
    assert "shared definition" in fixed["term-beta"]


def test_a_six_term_group_gives_all_six_the_definition():
    terms = [f"term-{letter}" for letter in "abcdef"]
    dts = "".join(f'<dt id="{term}">{term}</dt>' for term in terms)
    body = _body(f"<dl>{dts}<dd><p>one definition, six terms</p></dd></dl>")

    tippy_terms._duplicate_definitions(body)
    fixed = _tips(body)

    for term in terms:
        assert "<dd" in fixed[term], f"{term} was not given the definition"
        assert "one definition, six terms" in fixed[term]


def test_a_single_term_entry_is_untouched():
    body = _body(
        '<dl><dt id="term-solo">solo</dt><dd><p>its own definition</p></dd></dl>'
    )
    before = str(body)

    tippy_terms._duplicate_definitions(body)

    # Already adjacent: no `<dd>` was inserted, so the soup did not change.
    assert str(body) == before
    assert "<dd" in _tips(body)["term-solo"]


def test_a_term_already_adjacent_to_its_dd_is_not_doubled():
    body = _body(
        "<dl>"
        '<dt id="term-alpha">alpha</dt>'
        '<dt id="term-beta">beta</dt>'
        "<dd><p>shared definition</p></dd>"
        "</dl>"
    )

    tippy_terms._duplicate_definitions(body)

    # One `<dd>` was inserted (after alpha); the original, after beta, is not
    # itself duplicated -- three `<dd>` in the soup would mean it was.
    assert len(body.find_all("dd")) == 2
    fixed = _tips(body)
    assert fixed["term-beta"].count("<dd") == 1

    # Idempotent: running it again on the already-fixed soup inserts nothing
    # further -- every `<dt>` is now already adjacent to a `<dd>`.
    again = str(body)
    tippy_terms._duplicate_definitions(body)
    assert str(body) == again


def test_a_multi_signature_directive_gives_the_id_bearing_term_the_description():
    # The shape this module's donor-reuse predecessor could not fix: a second
    # `<dt>` carrying no `id` at all sits between the id-bearing `<dt>` and the
    # `<dd>`, so no `<dt>` is ever a donor -- reproducing
    # `tephpy.plotting.axes.TephigramAxes.plot_profile`'s own rendering, an
    # `@overload`-shaped method this documentation already has.
    body = _body(
        '<dl class="py function">'
        '<dt id="spam">spam(a)</dt>'
        "<dt>spam(a, b)</dt>"
        "<dd><p>The shared description.</p></dd>"
        "</dl>"
    )
    assert "<dd" not in _tips(body).get("spam", "")

    tippy_terms._duplicate_definitions(body)
    fixed = _tips(body)

    assert "<dd" in fixed["spam"]
    assert "The shared description." in fixed["spam"]


def test_a_dt_run_with_no_trailing_dd_is_left_alone_and_does_not_crash():
    # A definition list with no definition at all -- upstream gave none of
    # these a tip either, so there is nothing to fix and nothing to insert.
    body = _body('<dl><dt id="term-alpha">alpha</dt><dt id="term-beta">beta</dt></dl>')
    before = str(body)

    tippy_terms._duplicate_definitions(body)

    assert str(body) == before


def test_setup_wraps_create_id_to_tip_html(monkeypatch):
    sentinel_calls = []

    def fake_original(config, body):  # noqa: ARG001
        sentinel_calls.append(body)
        return {"term-alpha": '<dt id="term-alpha">alpha</dt>'}

    monkeypatch.setattr(sphinx_tippy, "create_id_to_tip_html", fake_original)

    class FakeApp:
        """As much of the application as ``setup`` reaches for: none of it."""

    metadata = tippy_terms.setup(FakeApp())

    assert sphinx_tippy.create_id_to_tip_html is not fake_original
    body = _body('<dl><dt id="term-alpha">alpha</dt></dl>')
    result = sphinx_tippy.create_id_to_tip_html(_FakeConfig(), body)
    assert sentinel_calls == [body]
    assert result == {"term-alpha": '<dt id="term-alpha">alpha</dt>'}
    assert metadata["parallel_read_safe"] is True
    assert metadata["parallel_write_safe"] is True
