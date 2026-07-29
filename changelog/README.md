# Changelog fragments

Every pull request adds a news fragment here named `<PR>.<type>.rst`, where
`<type>` is one of: `breaking`, `feature`, `enhancement`, `bugfix`,
`dependency`, `documentation`, `internal`, `misc`. The content is one short,
sentence-case line, ending with author attribution via the `:user:` extlink
role, e.g. ``(:user:`bjlittle`)``.

When the pull request closes one or more open issues, cite each issue in the
fragment with the `:issue:` extlink role — at the point where the fragment
describes what the issue reported, e.g. ``Fixed the fills pulling away from
the plotted profiles (:issue:`42`): …``.

When an entry names a documented API, cross-reference it with the matching
Sphinx domain role (`:class:`, `:func:`, `:meth:`, `:mod:`, `:obj:`) so the
reader can follow the link straight into the API docs, rather than quoting the
name as a plain double-backtick literal. For example, prefer ``Added
:func:`~tephpy.calc.parcel_path` and the :class:`~tephpy.calc.Profile`
dataclass.`` over spelling those names in double backticks. Third-party
objects (matplotlib, numpy, …) resolve the same way through intersphinx.
Reserve plain double-backtick literals for names with no documentation target
— private members, external tools, filenames, and config keys.

Fragments are assembled into `CHANGELOG.rst` at release time by towncrier.
