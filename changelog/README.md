# Changelog fragments

Every pull request adds a news fragment here named `<PR>.<type>.rst`, where
`<type>` is one of: `breaking`, `feature`, `enhancement`, `bugfix`,
`dependency`, `documentation`, `internal`, `misc`. The content is one short,
sentence-case line, ending with author attribution via the `:user:` extlink
role, e.g. ``(:user:`bjlittle`)``. Fragments are assembled into
`CHANGELOG.rst` at release time by towncrier.
