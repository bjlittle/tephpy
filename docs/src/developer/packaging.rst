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

The sdist and the wheel do not carry the same tree, and one asymmetry between
them is load-bearing.

``MANIFEST.in`` prunes ``docs/src/developer/plans``, and ``docs/src/conf.py``
excludes the same directory from the HTML build. So an implementation plan is
tracked in the repository, absent from the sdist, and unpublished on the site.
That is deliberate: a specification is a living document and a plan is a
point-in-time record of what was intended before implementation (docs spec §3.1).
The two exclusions are written differently — Sphinx compiles ``*`` to a
pattern that does not cross a solidus, so the ``exclude_patterns`` entry needs
``**`` to match what ``prune`` matches recursively — and the direction that
asymmetry would fail in is the leaking one, which is why both are spelled out
in ``conf.py``'s comment.

Beyond the code itself, the wheel carries the sample soundings and the gallery
header of gallery spec §3.7, the ``py.typed`` marker, and the logo masters under
``src/tephpy/plotting/_static``. Each has a line in ``MANIFEST.in``.

check-manifest
--------------

``check-manifest`` is declared in ``[tool.pixi.feature.devs.dependencies]`` and
run by nothing — no pixi task, no pre-commit hook, no workflow step. Adopting it
is :issue:`77`.

It is worth knowing that this is a real gap rather than a theoretical one.
``MANIFEST.in`` has already gone stale once: a ``prune`` entry silently stopped
matching when the directory it named moved, and only a hand-run ``python -m
build --sdist`` caught it before the affected files shipped. A declared
dependency that nothing runs looks from the outside exactly like a check that
passes.
