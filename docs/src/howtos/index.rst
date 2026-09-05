How-To Guides
=============

Recipes for a reader who already knows what they want. Each page answers one
question and stops there.

They assume you can already draw a :term:`tephigram`. If you cannot yet, the
:doc:`tutorials <../tutorials/index>` are the shorter way in, and the
:doc:`gallery <../gallery/index>` shows finished examples to work backwards from.

Every python block on these pages is executed by the test suite, as one script per
page and on every supported Python version, so what you copy is what ran.

.. list-table::
    :widths: auto

    * - :doc:`read-a-sounding`
      - An ascent out of the IGRA archive, or the Wyoming service.
    * - :doc:`temp-and-bufr`
      - A format ``tephpy`` does not read, decoded with ecCodes.
    * - :doc:`build-a-sounding`
      - Arrays, a :class:`pandas.DataFrame` or an :class:`xarray.Dataset` you already hold.
    * - :doc:`framing`
      - Fit the view to the data, or fix it so two figures compare.
    * - :doc:`emphasis`
      - Draw one member of a family heavier than the rest.
    * - :doc:`label-and-compose`
      - Label the edges, and set a tephigram beside another figure.
    * - :doc:`logo`
      - Brand a figure with the project mark.
    * - :doc:`configuration`
      - Set your own defaults once, in a file.
    * - :doc:`units`
      - What the API takes, and what it hands back.

.. toctree::
    :hidden:

    read-a-sounding
    temp-and-bufr
    build-a-sounding
    framing
    emphasis
    label-and-compose
    logo
    configuration
    units
