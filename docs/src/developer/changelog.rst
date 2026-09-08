.. _developer-changelog:

Changelog Fragments
====================

.. readingtime::

Every pull request adds a news fragment under ``changelog/``, named ``<PR>.<type>.rst``,
where ``<type>`` is one of ``breaking``, ``feature``, ``enhancement``, ``bugfix``,
``dependency``, ``documentation``, ``internal`` or ``misc``. towncrier assembles them into
``CHANGELOG.rst`` at release time, and the fragment is deleted then — so it is a pending
release note, not a permanent record.

The content is one short, sentence-case entry ending with author attribution through the
``:user:`` extlink role, for example ``(:user:`bjlittle`)``.

Citing an Issue
---------------

When the pull request closes an issue, cite it with the ``:issue:`` role at the point the
fragment describes what the issue reported, rather than trailing it at the end:

.. code:: rst

    Fixed the fills pulling away from the plotted profiles (:issue:`42`): …

Choosing a Role
---------------

When an entry names a documented API, cross-reference it with the matching Sphinx domain
role — ``:class:``, ``:func:``, ``:meth:``, ``:mod:``, ``:obj:`` — so a reader can follow
the link into the API documentation:

.. code:: rst

    Added :func:`~tephpy.calc.parcel_path` and the :class:`~tephpy.calc.Profile` dataclass.

rather than spelling those names in double backticks. Third-party objects resolve the same
way through intersphinx.

Reserve a plain double-backtick literal for a name with no documentation target: a private
member, an external tool, a filename, a configuration key.

``ci-changelog`` checks that a fragment is present and well formed; :doc:`ci` describes
what its failure means, and :doc:`contributing` describes the rest of what a pull request
carries.
