.. _configure-from-a-file:

Configure tephpy From a File
============================

.. readingtime::

A house style is the same handful of lines at the top of every script — a
colour scheme, a preferred extent, a cursor readout. A configuration file
gives them a home on disk, and every later ``import tephpy`` picks them up.

Generate the Template
---------------------

.. code-block:: console

    $ tephpy config generate
    Wrote /home/you/.config/tephpy/tephpyrc.yaml

The template carries every option tephpy has, each commented out and showing
the default in force, with a line of prose above it. Nothing in it is active
until you uncomment something, so a freshly generated file changes nothing.
Every option is also listed in :ref:`tephpy-config-options`, with its type, its
default, and the longer prose the template has no room for.

Uncomment what you want and edit the value:

.. code-block:: yaml

    isotherms:
      # Matplotlib colour for the lines and their labels.
      color: purple
      # Line width in points.
      # linewidth: 0.5

Where tephpy Looks
------------------

The first file found wins; there is no merging across the three:

1. the file named by ``$TEPHPYRC``
2. ``tephpyrc.yaml`` in the current working directory
3. ``tephpyrc.yaml`` in your user configuration directory

``tephpy config path`` reports the whole search, not just the winner, which
is what you want when a file appears to be ignored:

.. code-block:: console

    $ tephpy config path
    /home/you/work/tephpyrc.yaml  [in force]
    /home/you/.config/tephpy/tephpyrc.yaml  [shadowed]

Being found is not the same as being used. A file tephpy could not read is
marked ``[rejected]``, and the defaults stay in force:

.. code-block:: console

    $ tephpy config path
    /home/you/work/tephpyrc.yaml  [rejected]
    /home/you/.config/tephpy/tephpyrc.yaml  [absent]

    /home/you/work/tephpyrc.yaml was rejected; tephpy is using its defaults. The warning it raised on import says why.

A directory that happens to be named ``tephpyrc.yaml`` is reported as
``[not a file]``, and passed over.

Setting ``$TEPHPYRC`` to a file that does not exist is never a fallthrough
to the next candidate — naming a file explicitly and not having it is a
mistake worth reporting. ``tephpy config path`` fails outright; ``import
tephpy`` warns and falls back to the defaults, so watch for that warning if
a script's styling is not what you expect.

Quote Hex Colours
-----------------

YAML reads an unquoted ``#`` as the start of a comment, so

.. code-block:: yaml

    isotherms:
      color: #b0b0b0

sets ``color`` to null, not to grey. Quote it:

.. code-block:: yaml

    isotherms:
      color: '#b0b0b0'

tephpy warns about a null value rather than passing it on, and names the
missing quotes as the likely cause. Named colours such as ``purple`` and
``tab:blue`` need no quoting.

When the File Takes Effect
--------------------------

The file is read once, at ``import tephpy``, and an :term:`isopleth` family
reads
``tephpy.config`` when it is created. A configuration file therefore sets the
starting values for axes you create afterwards; it does not restyle axes that
already exist. This is the ``rcParams`` behaviour matplotlib users already
expect.

After an Upgrade
----------------

A file written for one release of tephpy stays usable in the next, but the
two halves of that promise are not the same size. An option tephpy has since
renamed or dropped warns and is skipped — the rest of the file still applies.
An unknown *section*, though, is rejected outright, and rejecting a section
means rejecting the whole file: ``import tephpy`` warns and falls back to the
defaults entirely, and :meth:`tephpy.config.load` raises and leaves your
configuration as it found it. Nothing under that section is quietly lost,
because nothing in the file is applied at all.

So if a styling you have relied on for months disappears after an upgrade,
read the warning: one obsolete section name is enough to switch off every
other line in the file.

A value of the wrong type is treated the same way as an option tephpy no
longer recognises: ``linewidth: thick`` warns, that one option is skipped
and keeps its default, and every other line in the file still applies. The
warning names the file, the option, what was expected and what it found:

.. code-block:: text

    tephpyrc.yaml: ignoring isotherms.linewidth, which expects a number, not the string 'thick'

Two details of YAML are worth knowing before you read one of these.
``linewidth: 1`` is fine — an integer is accepted wherever a number is
wanted. But ``linewidth: true`` is not a number at all, and neither are
``yes``, ``no``, ``on`` and ``off``, which YAML also reads as true or
false. Quote them if you meant the words.

A value of the right type can still be refused. ``color: notacolour`` is a
string and ``interval: 0`` is a number, and neither is something tephpy can
draw; both warn and are skipped exactly as ``linewidth: thick`` is, and the
warning says what the option can accept:

.. code-block:: text

    tephpyrc.yaml: ignoring isotherms.color, which expects a colour matplotlib knows, not the string 'notacolour'
    tephpyrc.yaml: ignoring isobars.interval, which expects a positive, finite number, not the number 0.0

Where the set of legal values is closed, the warning lists it, because your
next move is to pick from it. Where it is open — no message can enumerate the
colours matplotlib knows — it is described instead. And ``color: b0b0b0``,
the mirror image of the ``#`` trap above, is told what it is probably missing:

.. code-block:: text

    tephpyrc.yaml: ignoring isotherms.color, which expects a colour matplotlib knows, not the string 'b0b0b0'; did you mean '#b0b0b0'?

One of these refusals will catch you out if you have relied on it.
``linewidth: 0`` is a working matplotlib instruction — a line of zero width
is a line you cannot see — but tephpy refuses it, because a line width is
expected to be a positive number and because hiding a family has an option
of its own:

.. code-block:: yaml

    isotherms:
      visible: false

That is the one to reach for. It says what you mean, it reads that way to
whoever opens the file next, and it costs you nothing: ``visible`` is
available on every isopleth family.

An option is skipped whole. ``emphasis`` holds a mapping of members to
styles, so one bad member costs you the whole ``emphasis`` option, not just
that member — the good members go back to being drawn like every other
member of the family. This is deliberate: told that ``emphasis`` was ignored
you can read your own file and see what you lost, where told it was partly
applied you could not tell what was in force.

These warnings arrive once, as the file is read, and no filter of yours can
turn them off: your own code has not started running yet, and the auto-load
puts tephpy's configuration warnings in front of every filter you set, so
they always reach you. They are shown rather than raised, so a typo cannot
take the import down with it either.

Loading the file again from Python warns again — an unknown section raises
there instead — and *those* warnings are ordinary ones. Once you have read
one and decided it is safe to live with — an unknown option you are not
using yet, say — filter it by category rather than by module: the warning
is attributed to your own code, not to ``tephpy``, so a filter keyed on the
module never matches it.
:class:`TephpyConfigWarning <tephpy.exceptions.TephpyConfigWarning>` is a
``UserWarning`` rather than a :class:`TephpyError
<tephpy.exceptions.TephpyError>`, because an unusable file degrades to the
shipped defaults instead of stopping the import; :mod:`tephpy.exceptions` sets
out that distinction and the rest of the hierarchy.

.. code-block:: python

    import warnings

    import tephpy

    warnings.filterwarnings("ignore", category=tephpy.exceptions.TephpyConfigWarning)
    tephpy.config.load()

Saving From Python
------------------

:meth:`tephpy.config.save` writes the options you actually set, and nothing else:

.. code-block:: python

    import tephpy

    tephpy.config.isotherms.color = "purple"
    tephpy.config.save()

It is a data dump: comments and key order in an existing file are not
preserved, because PyYAML cannot round-trip them. ``tephpy config generate``
is the command that produces the annotated file — reach for
:meth:`tephpy.config.save` to capture a configuration you arrived at
interactively, not to edit one you already have.

Which File Is in Force
----------------------

``tephpy.config.source`` names the file the configuration was last
*successfully* loaded from, as a :class:`pathlib.Path`, and is ``None`` until
one has been — so it answers "did my file take effect?" without your having to
guess from the options:

.. code-block:: python

    import tephpy

    tephpy.config.load()
    print(tephpy.config.source)

Back to the Defaults
--------------------

:meth:`tephpy.config.reset` puts every option in every section back to ``None``,
falling through to the shipped conventions, and clears
``tephpy.config.source`` with them:

.. code-block:: python

    tephpy.config.reset()

Reach for it in a notebook that has drifted, or between tests. Remember that a
family reads the configuration when its axes is created, so a ``reset`` applies
to diagrams you draw after it and not to one already on screen.

One thing to know before trusting ``source`` as a check. A load that fails
changes nothing: the options roll back, and so does ``source``. So a rejected
replacement leaves the *previous* file still named there, rather than ``None``
— which is the answer you want, but not the one you might expect.
