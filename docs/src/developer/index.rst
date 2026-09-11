Developer Guide
===============

How ``tephpy`` is built, tested and documented, for anyone changing it — the
contributor arriving at a first pull request, and the maintainer returning to a
decision made months ago.

Every page here describes the repository as it is now, and is held to it wherever
a claim can be: the tasks these pages name are tasks that exist, the workflows
they name are workflows that run, and the modules the plotting tour maps are the
modules in the package. Where a page and a design specification disagree, the
specification is the one that is right.

If you are using ``tephpy`` rather than changing it, none of this is needed. The
:doc:`tutorials <../tutorials/index>`, :doc:`how-to guides <../howtos/index>` and
:doc:`reference <../reference/index>` stand on their own.

.. list-table::
    :widths: auto

    * - :doc:`contributing`
      - Getting an environment, the task graph, and what a pull request carries.
    * - :doc:`testing`
      - The tests tree, image comparison, and why nothing in the suite reaches the
        network.
    * - :doc:`plotting`
      - A map of the plotting package: which module owns what, and the order
        things happen in.
    * - :doc:`changelog`
      - The news fragment every pull request adds — its name, its type, and the
        roles its prose uses.
    * - :doc:`docs-style`
      - How to write a page here, and the four questions a reviewer asks of one.
    * - :doc:`packaging`
      - What ``tephpy`` runs on, and what its distributions carry.
    * - :doc:`ci`
      - What runs on a pull request and on a schedule, and what it means when one
        of them fails at you unbidden.
    * - :doc:`specs/index`
      - The design record: why each decision was made, cited by section from the
        source.

.. toctree::
    :hidden:

    contributing
    testing
    plotting
    changelog
    docs-style
    packaging
    ci
    specs/index
