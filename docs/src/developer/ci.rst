.. _developer-ci:

Continuous Integration
=======================

.. readingtime::

Thirteen workflows run in this repository. Most of them you will meet on your own pull
request; six run on a schedule and will reach you without your having done anything, which
is the part worth reading before it happens.

This page says what each one is for and what its failure means. It does not describe how
they work — the workflow files say that, and cannot drift from themselves — and it does not
carry the reasoning behind a gate's design, which lives in the
:doc:`design specifications <specs/index>`.

On Your Pull Request
---------------------

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Workflow
      - What it is for
    * - ``ci-tests``
      - The suite, on every supported Python
    * - ``ci-docs``
      - Builds the documentation and runs every gate over it — the same set
        ``pixi run docs`` runs locally, named by task so the two cannot diverge
    * - ``ci-changelog``
      - Checks the news fragment: that there is one, and that it is well formed
    * - ``ci-citation``
      - Validates ``CITATION.cff``, the machine-readable record of how to cite this
        software. It runs only when that file changes
    * - ``ci-wheels``
      - Builds the sdist and wheel, and checks ``MANIFEST.in`` against what the
        sdist carries
    * - ``ci-label``
      - Labels the pull request from the paths it touches
    * - ``codeql``
      - Static security analysis

Every one of these except ``ci-citation`` runs on every pull request; ``ci-citation``
is the one workflow in this repository scoped to a path, so it stays quiet unless
``CITATION.cff`` itself changes.

On a Schedule
--------------

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Workflow
      - What it is for
    * - ``ci-locks``
      - Refreshes ``pixi.lock`` weekly and opens a pull request with what moved.
        Nothing else moves the lock, so without this the whole of CI goes on
        testing whichever day's resolution was last written
    * - ``ci-floors``
      - Resolves each declared minimum version and exercises what it resolves,
        so a floor that has become untrue is found rather than assumed
    * - ``ci-linkcheck``
      - Checks every external link, and separately that the University of Wyoming
        archive still answers ``tephpy.io`` — the one external URL this project
        calls rather than links, which no link checker can judge
    * - ``ci-topics``
      - Reports monthly on which glossary topics the documentation covers
    * - ``ci-stale``
      - Marks a long-quiet issue or pull request stale
    * - ``codeql``
      - The same analysis, weekly, against code that has not changed

On an Issue or a First Pull Request
-------------------------------------

``ci-first-contribution`` greets somebody's first issue or pull request and labels it.

When One of Them Finds Something
----------------------------------

Four cases are worth knowing in advance, because you meet them without having caused them,
or because the remedy is not guessable.

**A lock refresh turns the bot's pull request red on image comparison.** When
``ci-locks`` moves matplotlib or freetype, rendered figures shift by more than the
comparison tolerance. The remedy is to regenerate the baselines on that branch with
``pixi run baselines``, then re-verify across all three test environments (:doc:`testing`).
This is expected rather than a defect in the proposal.

**A scheduled job opens an issue.** ``ci-floors``, ``ci-linkcheck`` and ``ci-topics`` each
keep a single standing issue and edit it in place rather than filing a new one per run, so
the history stays in one place. An issue appearing under your name in a notification is
one of these, not something you broke.

**Something of yours was labelled stale.** ``ci-stale`` marks an issue or pull request
quiet for six months and closes it four weeks later. Any comment takes the label straight
back off. It never touches anything held deliberately — a blocked or paused item, a
tracked design question, or the standing reports above.

**The browser demo will not start.** ``pixi run docs-all`` needs a Chromium that pixi does
not install. The check names the command to run; :doc:`contributing` carries both forms.

Where the Detail Lives
------------------------

The workflow files under ``.github/workflows/`` are the authority on what runs. The
:doc:`design specifications <specs/index>` carry why each gate is shaped as it is —
``floors spec §…`` for the dependency floors, ``topics spec §…`` for the coverage report,
``docs spec §…`` for the documentation gates.
