.. _developer-packaging:

Packaging and Support
=====================

.. readingtime::

What ``tephpy`` runs on, what holds it there, and what its distributions carry.

Supported Pythons
-----------------

``tephpy`` follows `Scientific Python SPEC 0
<https://scientific-python.org/specs/spec-0000/>`__. The supported window is
**Python 3.12, 3.13 and 3.14**, and it is revisited on each SPEC 0 rotation
(spec §8.3).

Five things enforce that window, and it is worth knowing which are which:

.. list-table::
    :header-rows: 1
    :widths: 40 15 45

    * - Where
      - Kind
      - What it does
    * - the SPEC 0 badge in ``README.md``
      - assertion
      - states the policy to a reader arriving at the repository
    * - this page
      - assertion
      - states the window, and this table
    * - the ``py312``/``py313``/``py314`` matrix in ``ci-tests``
      - mechanism
      - runs the whole suite on each supported Python
    * - the per-Python pixi solve-groups
      - mechanism
      - resolves a separate environment for each, so a dependency
        that has dropped one is a solve failure
    * - the ``sp-repo-review`` pre-commit hook
      - mechanism
      - reports a packaging declaration that has drifted from the
        Scientific Python conventions

The distinction matters. An assertion is a sentence someone has to keep true; a
mechanism fails on its own when it stops being true. ``requires-python`` and the
trove classifiers in ``pyproject.toml`` sit between the two — an installer
enforces them for a user, and nothing enforces them here — so treat them as
assertions when you change the window, and change all of them together.

Dependency Floors
-----------------

The support window fixes the Python versions. Every other lower bound is a
*dependency floor*, and floors are tested by a workflow of their own rather than
by the test matrix: ``ci-floors`` resolves an environment pinned at the declared
floors and runs the tier that depends on them, so a floor that no longer works
fails with a package name attached instead of surfacing as a mystery on somebody
else's machine.

Three tiers run — ``test``, ``docs`` and ``devs``. The machinery behind them is
specified in floors spec: the two declaration sites (floors spec §3.1), the pin
generator (floors spec §3.2), the attribution scan that names the culprit
(floors spec §3.4), and the issue contract that files one finding per tier and
package (floors spec §3.6). None of it is restated here, deliberately — a
developer guide that copied a specification would be a second copy to drift
from it.

Raise a floor when ``tephpy`` starts using something the older version does not
have, and say so in the changelog fragment. Lower one only with a reason.

What the Distributions Carry
----------------------------

**The sdist carries the package and what a build of it needs, and nothing
else.** Not the tests, not the documentation, not the changelog fragments, not
the CI. A release is tested before it ships — across every supported Python and
against the declared floors — so the packaging contract is that the artifact
works on the interpreters and dependencies it names. Tests inside every install
and every conda package buy the remaining case, which is a host where a tested
artifact does not work; the answer there is a development environment and a
checkout, not a copy of the suite the installer happened to carry. Shipping
them costs every downstream user size for a situation almost none of them will
meet.

That makes ``MANIFEST.in`` a list of exclusions. It once read as a list of
inclusions, which was inert: ``setuptools_scm``'s file finder already takes
every tracked file, so the ``include`` lines added nothing and the sdist carried
the repository — 450 files, of which the package was 55.

The direction matters for more than tidiness. An inclusion layered over a finder
that takes everything cannot fail visibly: a ``prune`` that stops matching
leaves the file tracked *and* shipped, which is what happened when
``docs/superpowers`` moved and nothing noticed. Written as exclusions, the same
mistake leaves files the manifest does not account for, and ``check-manifest``
says so.

One asymmetry is load-bearing beyond packaging. ``MANIFEST.in`` prunes ``docs``
entirely, and ``docs/src/conf.py`` separately excludes
``docs/src/developer/plans`` from the HTML build. So an implementation plan is
tracked in the repository and unpublished on the site: a specification is a
living document and a plan is a point-in-time record of what was intended before
implementation (docs spec §3.1). Sphinx compiles ``*`` to a pattern that does not
cross a solidus, so the ``exclude_patterns`` entry needs ``**`` to match what
``prune`` matches recursively, and the direction that asymmetry fails in is the
leaking one — which is why ``conf.py``'s comment spells both out.

The wheel is narrower still: the package, the sample soundings, the ``py.typed``
marker, and the logo masters under ``src/tephpy/plotting/_static``. Each
non-Python file it carries has a ``package-data`` entry.
``examples/GALLERY_HEADER.rst`` is not among them — it is sphinx-gallery's
landing page, read from the checkout a documentation build globs, and nothing
reads it from an installed ``tephpy``.

check-manifest
--------------

``pixi run manifest`` runs ``check-manifest``, and ``ci-wheels`` runs the same
task — in the job that builds the distributions, since that is what a manifest
no longer describing them would spoil.

The gap it closes was a real one rather than a theoretical one. ``MANIFEST.in``
has already gone stale once: a ``prune`` entry silently stopped matching when
the directory it named moved, and only a hand-run ``python -m build --sdist``
caught it before the affected files shipped (:issue:`77`).

The check is only meaningful because the manifest is written as exclusions.
Against the old inclusion-shaped manifest it reported 318 files "missing from
the sdist" that the real sdist carried — ``check-manifest`` copies the tracked
files to a temporary tree without ``.git``, where ``setuptools_scm``'s finder
enumerates nothing, so its trial sdist held only what ``MANIFEST.in`` named
outright. What it compares now is the manifest's own account of what ships
against what does, which is the question worth asking.
