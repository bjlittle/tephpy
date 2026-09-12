.. _developer-release:

Cutting a Release
==================

.. readingtime::

A release is a short sequence of one-shot actions, two of which cannot be taken
back. This page is that sequence, in order, with what to check between the steps.

It does not carry the reasoning — the release-execution bullet of spec §10 holds
that, and the workflow files hold the mechanics. The split is the
one :doc:`ci` makes: a page that restated how ``ci-wheels`` publishes would drift
from the workflow, while the order you do things in is written down nowhere else.

Before You Tag
---------------

Four tasks, all of which CI runs anyway. Running them locally first means a
failure costs a minute rather than a tagged commit.

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Task
      - What it does
    * - ``tests``
      - The suite, with image comparison enforced (:doc:`testing`)
    * - ``lint``
      - Every pre-commit hook, over every file
    * - ``docs``
      - Builds the documentation and runs every gate over the result
    * - ``changelog``
      - Assembles ``changelog/`` into ``CHANGELOG.rst``. It takes the version
        the tag will carry: ``pixi run changelog --version 0.1.0``. Add
        ``--draft`` to render it without writing or removing anything

And three things that must be true:

- **``main`` is green.** Not "was green" — ``ci-wheels`` builds and publishes to
  Test PyPI on every push to ``main``, so a red one means the path the tag takes
  is already broken.
- **Every merged pull request left a fragment.** ``pixi run changelog --draft``
  renders what the release will say; a pull request missing from it is a
  fragment that was never written, and ``ci-changelog`` should have caught it.
- **The version you are about to tag does not exist on PyPI.** See
  `What Cannot Be Undone`_.

The Sequence
-------------

1. **Assemble the changelog.** ``pixi run changelog --version X.Y.Z``. This
   writes ``CHANGELOG.rst`` and **deletes the fragments it consumed**, so it is
   a commit of its own and the diff is worth reading before you make it.

2. **Fill in the release metadata.** ``CITATION.cff`` takes ``version`` and
   ``date-released`` (``YYYY-MM-DD``). ``ci-citation`` validates the file, and
   it runs only when that file changes — so this step is the only thing that
   will ever check it.

3. **Open a pull request with both, and label it** ``skip-changelog``. Then let
   it go green — this is the last point at which anything is reversible for
   free.

   The label is not optional here, and this is the one pull request where it is
   not a shortcut. ``ci-changelog`` asks every pull request for a fragment named
   after its own number, and this one has *deleted* every fragment there was:
   they are not missing, they have been consumed into ``CHANGELOG.rst`` in the
   same diff. Writing a fragment first does not help, because the gate reads the
   pull request's net change and step 1 removes it again.

   Nothing applies the label for you — ``ci-label`` adds it only for
   ``dependabot`` and ``pre-commit.ci`` — and without it the gate fails on the
   deleted paths rather than reporting a missing fragment, so the error will not
   tell you any of this.

4. **Merge it, and wait for ``main``.** ``ci-wheels`` runs again on the merge
   commit: ``manifest`` gates ``MANIFEST.in`` against what the sdist carries,
   ``build`` builds and smoke-tests both distributions, and ``publish-testpypi``
   publishes them to Test PyPI. That is the whole production path except its
   last step, exercised on the exact commit you are about to tag.

5. **Tag it, and push the tag.**

   .. code-block:: console

      $ git tag -a vX.Y.Z -m "vX.Y.Z"
      $ git push origin vX.Y.Z

   The tag is what derives the version: ``setuptools_scm`` reads it, and no file
   in the repository carries a version number to bump.

6. **Watch ``ci-wheels``.** The tag push runs it again, and this time
   ``publish-pypi`` runs instead of ``publish-testpypi``. It is gated on
   ``build`` succeeding, so a failure before that point publishes nothing.

7. **Check what arrived.** The project page on PyPI, and an install from it into
   a throwaway environment — ``ci-wheels`` smoke-tests the wheel it built, not
   the wheel PyPI served.

8. **Activate the version on Read the Docs.** Versioned hosting (``stable`` and
   ``vX.Y``) exists only once a tag does, so this step is possible only now.

9. **Announce it**, if it is a release worth announcing.

What Cannot Be Undone
----------------------

.. list-table::
    :header-rows: 1
    :widths: 30 70

    * - Action
      - What recovery there is
    * - Publishing to PyPI
      - **None.** A version number is consumed forever — yanking a release
        hides it from resolvers but never frees the number, and a file cannot
        be replaced. The recovery is to publish the next version
    * - Pushing a tag
      - The tag can be deleted, but anything it already published cannot.
        Delete a tag only when you are certain ``publish-pypi`` did not run
    * - Assembling the changelog
      - Free before the merge, since the fragments are still in git history.
        After it, restoring one means a new fragment

This is why the rehearsal below exists, and why steps 1 to 3 are a pull request
rather than a push.

The First Release
------------------

Everything below is one-time setup, and all of it must be done **before** the
first ``v*`` tag.

**The production publishing path has never run.** ``publish-pypi`` declares
``environment: pypi`` and the repository has no such environment, so the job
would fail at the point of publishing and nowhere earlier. Two things to create,
in this order:

1. A GitHub environment named exactly ``pypi``. The name is not a label — PyPI
   matches on it.
2. A PyPI Trusted Publisher for the project, naming this repository, the
   workflow file ``ci-wheels.yml``, and that environment. Because the project
   already exists on PyPI, it is configured against the project rather than as a
   *pending* publisher.

**Rehearse with a release candidate.** Tag ``vX.Y.Zrc1`` first and let it
publish. It exercises the whole production path for real, is throwaway in the
sense that nobody installs it by default, and turns every step above from
something never done into something done once. The alternative is finding out
whether the trusted publisher matches on the release itself, where
`What Cannot Be Undone`_ applies.

**Two gates will move at the first tag**, and neither is a defect:

- ``tests/test_api_docstrings.py::test_target_version_uses_the_project_version_scheme``
  asserts the derived version is ``0.1.0``. That stays right *at* the ``v0.1.0``
  tag and goes wrong on the next commit after it, when
  ``semver-pep440-release-branch`` derives ``0.2.0.dev…``. :issue:`227` records
  the snapshot rules that take over from the current equality rule.
- ``check_versionadded`` compares every published object against one target
  version, which is right only while nothing predates the first release.
