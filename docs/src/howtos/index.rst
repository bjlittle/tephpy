How-To Guides
=============

Recipes for a reader who already knows what they want. Each page answers one
question and stops there: getting data in from an archive, out of a format
``tephpy`` does not read, or straight out of a :class:`pandas.DataFrame` or an
:class:`xarray.Dataset`; framing the view on the region you care about; marking
a reference :term:`isopleth`; setting your own defaults from a configuration
file; branding a figure with the project logo; labelling its edges and setting
it beside another figure; and what units it takes and what it hands back.

They assume you can already draw a :term:`tephigram`. If you cannot yet, the
:doc:`tutorials <../tutorials/index>` are the shorter way in, and the
:doc:`gallery <../gallery/index>` shows finished examples to work backwards from.

Every python block on these pages is executed by the test suite, as one script per
page and on every supported Python version, so what you copy is what ran.

.. toctree::
    :maxdepth: 1

    build-a-sounding
    configuration
    emphasis
    framing
    label-and-compose
    logo
    read-a-sounding
    temp-and-bufr
    units
