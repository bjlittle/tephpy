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

The Release Branch
-------------------

Every release is tagged from a dedicated branch named ``vA.B.x`` — a literal
``x``, with the major and minor version in place of ``A`` and ``B``, so
``v0.1.x`` carries ``v0.1.0`` and every patch release after it. ``main`` is
never tagged.

The branch is not ceremony. ``semver-pep440-release-branch``, the version scheme
:file:`pyproject.toml` configures, reads it: one commit past ``v0.1.0`` derives
``0.1.1.dev1`` on ``v0.1.x`` and ``0.2.0.dev1`` on ``main``. The branch is what
tells ``setuptools_scm`` that a patch line and the next minor line are different
lines, and it is where a fix for a released version is prepared without waiting
for whatever ``main`` has accumulated since.

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

- **The release branch is green.** Not "was green" — ``ci-tests``, ``ci-docs``
  and ``ci-wheels`` all run on a push to it, so a red one means the path the tag
  takes is already broken.
- **Every merged pull request left a fragment.** ``pixi run changelog --draft``
  renders what the release will say; a pull request missing from it is a
  fragment that was never written, and ``ci-changelog`` should have caught it.
- **The version you are about to tag does not exist on PyPI.** See
  `What Cannot Be Undone`_.

The Sequence
-------------

1. **Get on the release branch.** For a new minor version, cut it from ``main``:

   .. code-block:: console

      $ git switch main && git pull
      $ git switch -c vA.B.x && git push -u origin vA.B.x

   For a patch release the branch already exists and carries its own history —
   check it out and put the fix on it, rather than branching again.

2. **Assemble the changelog.** ``pixi run changelog --version X.Y.Z``. This
   writes ``CHANGELOG.rst`` and **deletes the fragments it consumed**, so it is
   a commit of its own and the diff is worth reading before you make it.

3. **Fill in the release metadata.** ``CITATION.cff`` takes ``version`` and
   ``date-released`` (``YYYY-MM-DD``). ``ci-citation`` validates the file, and
   it runs only when that file changes — so this step is the only thing that
   will ever check it.

4. **Open a pull request into the release branch, and label it**
   ``skip-changelog``. Then let it go green — this is the last point at which
   anything is reversible for free.

   The label is not optional here, and this is the one pull request where it is
   not a shortcut. ``ci-changelog`` asks every pull request for a fragment named
   after its own number, and this one has *deleted* every fragment there was:
   they are not missing, they have been consumed into ``CHANGELOG.rst`` in the
   same diff. Writing a fragment first does not help, because the gate reads the
   pull request's net change and step 2 removes it again.

   Nothing applies the label for you — ``ci-label`` adds it only for
   ``dependabot`` and ``pre-commit.ci`` — and without it the gate fails on the
   deleted paths rather than reporting a missing fragment, so the error will not
   tell you any of this.

5. **Merge it, and wait for the release branch.** ``ci-wheels`` runs again on
   the merge commit: ``manifest`` gates ``MANIFEST.in`` against what the sdist
   carries, and ``build`` builds and smoke-tests both distributions. Everything
   the tag will do except the upload itself, run on the exact commit you are
   about to tag.

   ``publish-testpypi`` does *not* run here — it is scoped to ``main``, which is
   where the code reached Test PyPI before the branch was cut. A patch release
   is the exception worth knowing: its fix is prepared on the release branch and
   never passes through ``main`` first, so nothing of it reaches Test PyPI ahead
   of PyPI. Dispatch ``ci-wheels`` by hand from the branch if you want that
   rehearsal for a patch.

6. **Tag it, and push the tag.**

   .. code-block:: console

      $ git switch vA.B.x && git pull
      $ git tag -a vX.Y.Z -m "vX.Y.Z"
      $ git push origin vX.Y.Z

   The tag is what derives the version: ``setuptools_scm`` reads it, and no file
   in the repository carries a version number to bump.

   `The releases page <https://github.com/bjlittle/tephpy/releases>`__ does the
   same thing through the browser, and will also draft the release notes and
   publish a GitHub release alongside the tag. Either way, make sure the target
   is the release branch and not ``main``.

7. **Watch the wheels workflow.** The tag push runs ``ci-wheels`` again, and
   this time ``publish-pypi`` runs instead of ``publish-testpypi``. It is gated
   on ``build`` succeeding, so a failure before that point publishes nothing.

8. **Check what arrived.** `The project page on PyPI
   <https://pypi.org/project/tephpy/>`__ should show the new version, and an
   install from it into a throwaway environment should work — ``ci-wheels``
   smoke-tests the wheel it *built*, not the wheel PyPI served.

   .. code-block:: console

      $ python -m venv /tmp/release-check
      $ /tmp/release-check/bin/pip install tephpy==X.Y.Z
      $ /tmp/release-check/bin/python -c "import tephpy; print(tephpy.__version__)"
      $ /tmp/release-check/bin/tephpy examples list

9. **Merge the release branch back into main** — with a **merge commit**, not
   a squash. The pull request carries ``CHANGELOG.rst``, the citation metadata,
   and any fix the release was made for.

   .. code-block:: console

      $ git fetch origin
      $ gh pr create --base main --head vA.B.x \
            --title "Merge back vA.B.x" --label skip-changelog

   ``skip-changelog`` for the reason step 4 needed it: this pull request carries
   the fragment deletions as well, and ``ci-changelog`` reads them the same way.

   **The merge method is the whole point of this step, and it is not the
   default.** ``main`` is configured for squash merges, and a squash would put
   the branch's *content* on ``main`` while leaving the tag off it — after which
   ``setuptools_scm`` goes on deriving a version *below* the one just released.
   A merge commit makes the tag an ancestor of ``main``, which moves ``main`` to
   the next minor line while the release branch stays on the patch line:
   ``0.2.0.dev…`` and ``0.1.1.dev…`` respectively, measured both ways.

   So the reviewer enables merge commits in the repository settings, merges with
   *Create a merge commit*, and turns the setting off again. ``main`` also
   requires linear history, which a merge commit is not; whether that needs
   relaxing for the same merge, or whether it is waived for administrators, is
   one of the things the rehearsal below is for.

   **Do not delete the release branch** when the pull request merges. The next
   patch release for this minor version is prepared on it.

10. **Activate the version on Read the Docs.** Versioned hosting (``stable`` and
    ``vX.Y``) exists only once a tag does, so this step is possible only now.

11. **Announce it**, if it is a release worth announcing.

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

This is why the rehearsal below exists, and why steps 2 to 4 are a pull request
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

**Rehearse with a release candidate.** Cut the release branch, then tag
``vX.Y.Zrc1`` on it and let it publish. It exercises the whole production path
for real, is throwaway in the sense that no resolver installs a pre-release by
default, and turns every step above from something never done into something
done once. The alternative is finding out whether the trusted publisher matches
on the release itself, where `What Cannot Be Undone`_ applies.

Rehearse the merge-back with it. That is the step with a setting to change and a
merge method to pick by hand, and it is the one whose failure is quiet: a squash
lands, everything looks merged, and ``main`` goes on deriving a version below the
release. Doing it once on a release candidate settles what the branch protection
actually permits, which is written above as an open question because nothing has
tried it.

**Two gates will move at the first tag**, and neither is a defect:

- ``tests/test_api_docstrings.py::test_target_version_uses_the_project_version_scheme``
  asserts the derived version is ``0.1.0``. That stays right *at* the ``v0.1.0``
  tag and goes wrong on the next commit after it, when
  ``semver-pep440-release-branch`` derives ``0.2.0.dev…``. :issue:`227` records
  the snapshot rules that take over from the current equality rule.
- ``check_versionadded`` compares every published object against one target
  version, which is right only while nothing predates the first release.
