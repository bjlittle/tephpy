.. _configure-from-a-file:

Configure tephpy From a File
============================

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

Setting ``$TEPHPYRC`` to a file that does not exist is an error rather than a
fallthrough — naming a file explicitly and not having it is a mistake worth
reporting.

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

The file is read once, at ``import tephpy``, and an isopleth family reads
``tephpy.config`` when it is created. A configuration file therefore sets the
starting values for axes you create afterwards; it does not restyle axes that
already exist. This is the ``rcParams`` behaviour matplotlib users already
expect.

Saving From Python
------------------

``tephpy.config.save`` writes the options you actually set, and nothing else:

.. code-block:: python

    import tephpy

    tephpy.config.isotherms.color = "purple"
    tephpy.config.save()

It is a data dump: comments and key order in an existing file are not
preserved, because PyYAML cannot round-trip them. ``tephpy config generate``
is the command that produces the annotated file — reach for
``tephpy.config.save`` to capture a configuration you arrived at
interactively, not to edit one you already have.
