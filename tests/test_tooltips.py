# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.

"""Tests for the tooltip gate of tooltip spec §3.6."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_tooltips.py"

# `MANIFEST.in` prunes `.github`, so an sdist ships this test without the gate it
# exercises. The gate is a contract about the repository, and that is not the
# repository, so skip there rather than fail collection -- the guard
# `tests/test_citations.py` and `tests/test_github_references.py` both carry.
pytestmark = pytest.mark.skipif(
    not SCRIPT.is_file(), reason="not a checkout of the repository"
)


def _load():
    """Load the gate from its path, which is not an importable package."""
    spec = importlib.util.spec_from_file_location("check_tooltips", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load() if SCRIPT.is_file() else None


PAGE = """<html><body><article class="bd-article">{body}</article>
{scripts}</body></html>"""
RUNTIME = (
    '<script defer="defer" src="{popper}"></script>'
    '<script defer="defer" src="{tippy}"></script>'
)
VENDORED = {
    "popper": "_static/js/popper.min.js?v=a8c9358f",
    "tippy": "_static/js/tippy-bundle.umd.min.js?v=37ef8ba7",
}
GUARDS = "placement: 'auto-start', maxWidth: 500, interactive: false,"
SKIPS = '["headerlink", "sd-stretched-link", "sd-sphinx-override"]'


def _prefixed(depth, srcs):
    """Rebase each relative src in ``srcs`` with the ``../`` depth needs.

    Mirrors what Sphinx itself does: a root page's script src is unprefixed, a
    page one directory down gets one ``../``, and so on. An absolute src is
    left alone.
    """
    prefix = "../" * depth
    return {
        key: src if gate.ABSOLUTE.match(src) else f"{prefix}{src}"
        for key, src in srcs.items()
    }


def build(  # noqa: PLR0913
    tmp_path,
    pages,
    payloads,
    *,
    runtime=None,
    guards=GUARDS,
    skips=SKIPS,
    no_runtime=frozenset(),
    vendor=True,
):
    """Write a minimal build tree and return its root.

    ``pages`` maps a docname to the HTML of its article body; ``payloads`` maps a
    docname to ``{href: tip html}``. Anything absent gets the passing default.
    ``no_runtime`` names docnames that get no runtime ``<script>`` tags at all --
    the stripped-tag regression check 3 now catches. ``vendor`` writes the two
    bundle files the default runtime names, so a relative ``src`` resolves by
    default; pass ``False`` for a page whose runtime file is not there.
    """
    srcs = runtime or VENDORED
    for docname, body in pages.items():
        page = tmp_path / f"{docname}.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        if docname in no_runtime:
            scripts = ""
        else:
            scripts = RUNTIME.format(**_prefixed(docname.count("/"), srcs))
        page.write_text(PAGE.format(body=body, scripts=scripts), encoding="utf-8")
    if vendor:
        for src in srcs.values():
            if gate.ABSOLUTE.match(src):
                continue
            clean = src.split("?", 1)[0]
            #: A root-relative src is written under `tmp_path` itself, the
            #: same build root the gate resolves it against -- joining with
            #: the leading `/` intact would discard `tmp_path` entirely.
            bundle = tmp_path / clean.lstrip("/")
            bundle.parent.mkdir(parents=True, exist_ok=True)
            bundle.write_text("/* stub */", encoding="utf-8")
    for docname, tips in payloads.items():
        js = (
            tmp_path
            / "_static"
            / "tippy"
            / f"{docname}.0123abcd-0123-4abc-8def-0123456789ab.js"
        )
        js.parent.mkdir(parents=True, exist_ok=True)
        entries = ", ".join(
            f'"a[href=\\"{href}\\"]": "{html}"' for href, html in tips.items()
        )
        js.write_text(
            f"selector_to_html = {{{entries}}}\n"
            f"skip_classes = {skips}\n"
            f"tippy(link, {{ content: tip_html, {guards} }});\n",
            encoding="utf-8",
        )
    return tmp_path


TERM = '<a href="reference/glossary.html#term-tephigram">tephigram</a>'
THUMB = '<a href="gallery/plot_sounding.html">A Sounding</a>'
EXTERNAL_TERM = (
    '<a href="https://docs.python.org/3/glossary.html#term-iterable">iterable</a>'
)


def test_a_glossary_link_with_a_tip_passes(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {"reference/glossary.html#term-tephigram": "<dd>a diagram</dd>"}},
    )
    assert gate.check_glossary(root) == []


def test_a_glossary_link_without_a_tip_is_reported(tmp_path):
    root = build(tmp_path, {"index": TERM}, {"index": {}})
    found = gate.check_glossary(root)
    assert found
    assert "term-tephigram" in found[0]


def test_a_glossary_tip_with_no_definition_is_reported(tmp_path):
    # A multi-term glossary entry's starved terms (tooltip spec §3.7): the
    # extension gave this term a tip, but it is only the hovered word, with no
    # `<dd>` -- the proxy this check used to accept.
    root = build(
        tmp_path,
        {"index": TERM},
        {
            "index": {
                "reference/glossary.html#term-tephigram": (
                    "<dt id='term-tephigram'>tephigram</dt>"
                )
            }
        },
    )
    found = gate.check_glossary(root)
    assert found
    assert "no definition" in found[0]
    assert "term-tephigram" in found[0]


def test_a_glossary_tip_with_a_definition_passes(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM},
        {
            "index": {
                "reference/glossary.html#term-tephigram": (
                    "<dt id='term-tephigram'>tephigram</dt><dd>a diagram</dd>"
                )
            }
        },
    )
    assert gate.check_glossary(root) == []


def test_a_build_with_no_glossary_link_at_all_is_reported(tmp_path):
    # The positive assertion of tooltip spec §3.6. A build in which the extension
    # silently produced nothing satisfies every other check most completely.
    root = build(tmp_path, {"index": "<p>no links here</p>"}, {"index": {}})
    found = gate.check_glossary(root)
    assert found
    assert "no glossary" in found[0].lower()


def test_an_untipped_glossary_link_on_genindex_is_not_reported(tmp_path):
    # genindex is generated by Sphinx's builder rather than rendered from a
    # source document; the extension writes it no payload, so an untipped
    # glossary link there is not a regression this check can see.
    root = build(
        tmp_path,
        {"index": TERM, "genindex": TERM},
        {"index": {"reference/glossary.html#term-tephigram": "<dd>a diagram</dd>"}},
    )
    assert gate.check_glossary(root) == []


def test_an_untipped_glossary_link_on_a_nested_search_page_is_reported(tmp_path):
    # GENERATED excludes "search" against the full posix docname, not a
    # basename -- a nested page that happens to share the name, such as a
    # `reference/search` this project wrote, is not that exclusion and stays
    # in scope.
    root = build(
        tmp_path,
        {"index": TERM, "reference/search": TERM},
        {"index": {"reference/glossary.html#term-tephigram": "<dd>a diagram</dd>"}},
    )
    found = gate.check_glossary(root)
    assert found
    assert any("reference/search" in line for line in found)


def test_an_untipped_external_glossary_link_is_not_reported(tmp_path):
    # tooltip spec §7: external and intersphinx links carry no tooltip by design.
    root = build(
        tmp_path,
        {"index": TERM + EXTERNAL_TERM},
        {"index": {"reference/glossary.html#term-tephigram": "<dd>a diagram</dd>"}},
    )
    assert gate.check_glossary(root) == []


def test_a_build_with_only_excluded_glossary_links_still_fails_the_empty_search_guard(
    tmp_path,
):
    # Excluding genindex and external links must not hollow out the positive
    # assertion: a build where every remaining glossary link is out of scope
    # looks, to this check, like a build where the extension produced nothing.
    root = build(tmp_path, {"index": EXTERNAL_TERM, "genindex": TERM}, {})
    found = gate.check_glossary(root)
    assert found
    assert "no glossary" in found[0].lower()


def test_a_tipped_gallery_link_is_reported(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM + THUMB},
        {
            "index": {
                "reference/glossary.html#term-tephigram": "<dd>a diagram</dd>",
                "gallery/plot_sounding.html": "<h1>A Sounding</h1>",
            }
        },
    )
    found = gate.check_gallery(root)
    assert found
    assert "plot_sounding" in found[0]


def test_an_untipped_gallery_link_passes(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM + THUMB},
        {"index": {"reference/glossary.html#term-tephigram": "<dd>a diagram</dd>"}},
    )
    assert gate.check_gallery(root) == []


def test_a_page_loading_the_runtime_from_a_cdn_is_reported(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {}},
        runtime={
            "popper": "https://unpkg.com/@popperjs/core@2",
            "tippy": "https://unpkg.com/tippy.js@6",
        },
    )
    found = gate.check_vendored(root)
    assert found
    assert "index.html" in found[0]


def test_a_page_loading_the_vendored_runtime_passes(tmp_path):
    root = build(tmp_path, {"index": TERM}, {"index": {}})
    assert gate.check_vendored(root) == []


def test_a_page_with_a_payload_and_no_runtime_script_is_reported(tmp_path):
    # The stripped-tag regression: the payload was generated, but the loader
    # that would fetch its dependency is gone -- the purely negative off-site
    # check is satisfied most completely by this build.
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {"reference/glossary.html#term-tephigram": "<dd>a diagram</dd>"}},
        no_runtime={"index"},
    )
    found = gate.check_vendored(root)
    assert found
    assert "references no vendored runtime script" in found[0]


def test_an_offsite_runtime_naming_the_payload_directory_is_reported(tmp_path):
    # The payload-loader exclusion must not be a substring test: an off-site
    # URL that merely *contains* `_static/tippy/` in its path is still the
    # vendoring reverted, and must be caught, not dropped for looking local.
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {}},
        runtime={
            "popper": "https://cdn.example/_static/tippy/popper.min.js",
            "tippy": "https://cdn.example/_static/tippy/tippy-bundle.umd.min.js",
        },
    )
    found = gate.check_vendored(root)
    offsite = [line for line in found if "off-site" in line]
    assert len(offsite) == len(VENDORED)
    assert all("index.html" in line for line in offsite)
    assert any("popper.min.js" in line for line in offsite)
    assert any("tippy-bundle.umd.min.js" in line for line in offsite)


def test_the_genuine_payload_loader_under_static_tippy_is_not_reported(tmp_path):
    # Regression guard for the exclusion the substring test above was
    # standing in for: a page's own generated payload loader, sitting under
    # `_static/tippy/` and matching `RUNTIME` on its filename, must still be
    # passed over -- it is Sphinx-emitted and not one of the two vendored
    # bundles this check is about.
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {"reference/glossary.html#term-tephigram": "<dd>a diagram</dd>"}},
        runtime={
            "popper": "_static/js/popper.min.js",
            "tippy": "_static/js/tippy-bundle.umd.min.js",
        },
    )
    # The loader referenced by the `<script>` tag is the same uuid-stamped
    # payload file `build` already wrote for "index" and `payloads()` reads
    # as the selector map -- there is no separate loader file in reality.
    loader = (
        root / "_static" / "tippy" / "index.0123abcd-0123-4abc-8def-0123456789ab.js"
    )
    assert loader.is_file()
    page = root / "index.html"
    page.write_text(
        page.read_text(encoding="utf-8").replace(
            "</body>",
            f'<script defer="defer" src="_static/tippy/{loader.name}"></script></body>',
        ),
        encoding="utf-8",
    )
    assert gate.check_vendored(root) == []


def test_a_local_runtime_file_outside_the_build_root_is_reported(tmp_path):
    # `resolve()` normalises but does not constrain: a traversal src that
    # resolves to a real file outside the build root must be reported, and
    # distinguished from a merely-missing file.
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "tippy.js").write_text("/* not vendored here */", encoding="utf-8")
    root = build(
        tmp_path / "build",
        {"index": TERM},
        {"index": {}},
        runtime={
            "popper": "_static/js/popper.min.js",
            "tippy": "../outside/tippy.js",
        },
    )
    found = gate.check_vendored(root)
    assert found
    assert any(
        "escapes the build root" in line and "tippy.js" in line for line in found
    )
    assert not any("does not exist" in line for line in found)


def test_a_root_relative_runtime_src_resolving_inside_the_build_passes(tmp_path):
    # A single leading `/` is root-relative, not off-site (`ABSOLUTE` does not
    # match it), and must resolve against the build root rather than the
    # page -- `Path.__truediv__` would otherwise discard the page side of the
    # join and walk the OS filesystem root.
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {}},
        runtime={
            "popper": "/_static/js/popper.min.js",
            "tippy": "/_static/js/tippy-bundle.umd.min.js",
        },
    )
    assert gate.check_vendored(root) == []


def test_a_root_relative_runtime_src_naming_a_missing_file_is_reported(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {}},
        runtime={
            "popper": "/_static/js/popper.min.js",
            "tippy": "/_static/js/tippy-bundle.umd.min.js",
        },
        vendor=False,
    )
    found = gate.check_vendored(root)
    assert len(found) == len(VENDORED)
    assert all("does not exist under the build root" in line for line in found)


def test_a_page_whose_runtime_file_does_not_exist_is_reported(tmp_path):
    # The renamed-or-deleted-bundle regression: the script tag is there and
    # local, but nothing was written to the path it names -- neither absent
    # nor off-site, so it passes both of the other rules.
    root = build(tmp_path, {"index": TERM}, {"index": {}}, vendor=False)
    found = gate.check_vendored(root)
    assert len(found) == len(VENDORED)
    assert all("does not exist under the build root" in line for line in found)


def test_a_runtime_file_with_a_cache_busting_query_still_resolves(tmp_path):
    # Guards the `?v=...` stripping: Sphinx appends one to every static asset,
    # and the file it names is written without it.
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {}},
        runtime={
            "popper": "_static/js/popper.min.js?v=deadbeef",
            "tippy": "_static/js/tippy-bundle.umd.min.js?v=deadbeef",
        },
    )
    assert gate.check_vendored(root) == []


def test_this_specification_naming_the_cdn_is_not_a_violation(tmp_path):
    # tooltip spec §6: check 3 must look for the runtime script, not for the
    # string. The specification is a published page and names `unpkg.com` in
    # prose, so a gate that swept the build for it would fail on the document
    # that told it to exist.
    root = build(
        tmp_path,
        {
            "developer/specs/tooltips": "<p>the default is https://unpkg.com/tippy.js@6</p>"
        },
        {},
    )
    assert gate.check_vendored(root) == []


def test_an_interactive_payload_is_reported(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {}},
        guards="placement: 'auto-start', maxWidth: 500, interactive: true,",
    )
    found = gate.check_guards(root)
    assert found
    assert "interactive" in found[0]


def test_a_payload_that_dropped_the_stretched_link_class_is_reported(tmp_path):
    root = build(
        tmp_path,
        {"index": TERM},
        {"index": {}},
        skips='["headerlink", "sd-sphinx-override"]',
    )
    found = gate.check_guards(root)
    assert found
    assert "sd-stretched-link" in found[0]


def test_a_payload_carrying_both_guards_passes(tmp_path):
    root = build(tmp_path, {"index": TERM}, {"index": {}})
    assert gate.check_guards(root) == []


def test_a_build_with_no_payloads_at_all_fails(tmp_path):
    # Every check but the first is satisfied by an empty build.
    root = build(tmp_path, {"index": TERM}, {})
    assert gate.check_guards(root)


@pytest.mark.parametrize("argv", [[], ["a", "b"]])
def test_the_gate_requires_exactly_one_argument(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["check_tooltips.py", *argv])
    assert gate.main() == 1
