.. _developer-contributing:

Contributing to tephpy
=======================

.. readingtime::

``tephpy`` develops with `pixi <https://pixi.sh>`__, which reads its environments from
``pyproject.toml`` and needs no setup of its own:

.. code:: console

    $ git clone git@github.com:bjlittle/tephpy.git
    $ cd tephpy
    $ pixi run tests

The first run builds the environment it needs. ``pixi run <task>`` selects that
environment for you, so there is normally no ``--environment`` to remember.

What to Run
-----------

Three commands are what a pull request must pass:

.. code:: console

    $ pixi run tests
    $ pixi run lint
    $ pixi run docs

``pixi run docs`` builds the documentation and runs every gate over the result except one.
It is the one to reach for. ``pixi run docs-all`` adds the gate it leaves out — a smoke
test of the :doc:`browser demo </tutorials/browser-demo>` in
`Chromium <https://www.chromium.org/Home/>`__.

The Task Graph
---------------

Eighteen tasks are declared; about nine are worth knowing. The rest are steps these run
on your behalf:

.. code:: text

    docs-clean ─→ docs-html ─→ docs-check-api        ─┐
                            ─→ docs-check-citations   │
                            ─→ docs-check-figures     ├─→ docs ─┐
                            ─→ docs-check-links       │         ├─→ docs-all
                            ─→ docs-check-tooltips   ─┘         │
                            ─→ docs-browser-test ───────────────┘

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Task
      - What it does
    * - ``tests``
      - The suite, with image comparison enforced (:doc:`testing`)
    * - ``tests-clean``
      - Removes what a test run leaves behind
    * - ``baselines``
      - Regenerates the `pytest-mpl <https://pytest-mpl.readthedocs.io/>`__
        baselines
    * - ``lint``
      - Every pre-commit hook, over every file
    * - ``docs``
      - Builds the documentation and runs every gate over the result except the
        browser demo's smoke test
    * - ``docs-all``
      - ``docs``, plus the browser demo's smoke test
    * - ``docs-figures``
      - Regenerates the published figures' baselines
    * - ``serve-html``
      - Serves the built HTML locally
    * - ``manifest``
      - Checks ``MANIFEST.in`` against what the sdist carries

The Browser Demo Needs a Browser
----------------------------------

``pixi run docs-all`` runs `Playwright <https://playwright.dev/python/>`__, which
lives in the ``docs`` environment and is on no
other ``PATH``. Install a browser once:

.. code:: console

    $ pixi run -e docs playwright install chromium

On Linux the browser also needs system libraries pixi does not provide, which
``pixi run -e docs playwright install --with-deps chromium`` adds as root. Both go through
pixi for the same reason. If the browser will not start, the check says which of the two is
missing and names it the same way.

What a Pull Request Carries
-----------------------------

- A changelog fragment — see :doc:`changelog`.
- A passing ``pixi run docs``.
- Prose reviewed against *Reviewing Claims* in :doc:`docs-style`.

:doc:`ci` describes what runs once the pull request is open.
