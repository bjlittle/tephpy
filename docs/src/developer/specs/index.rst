Design Specifications
=====================

These are tephpy's design specifications. Each is a **living document**: maintained
alongside the code it describes, not archived behind it. Where the code and a
specification diverge, it is the specification that gets corrected — so read these as
current, and report a divergence as a specification defect.

tephpy's source cites them by section. You will meet ``spec §3.2`` and ``logo spec §3.5``
in comments and docstrings throughout ``src/`` and ``tests/``, and each names a section
on one of the pages below. The prefix identifies the document, and it is
load-bearing rather than decorative: ``logo spec §3.6`` names a section that has no
counterpart in the parent specification.

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Citation
      - Document
    * - ``spec §…``
      - :doc:`2026-07-22-tephpy-design`
    * - ``logo spec §…``
      - :doc:`2026-08-01-add-logo-design`
    * - ``docs spec §…``
      - :doc:`2026-08-03-published-specs-design`
    * - ``configfile spec §…``
      - :doc:`2026-08-07-config-file-design`
    * - ``domain spec §…``
      - :doc:`2026-08-12-config-domain-validation-design`
    * - ``floors spec §…``
      - :doc:`2026-08-13-dependency-floors-design`

A new specification chooses a prefix unique across this collection and declares it in its
own header banner.

The implementation plans derived from these specifications are tracked in the repository
under `docs/src/developer/plans/
<https://github.com/bjlittle/tephpy/tree/main/docs/src/developer/plans>`__, but are
deliberately not published here. Unlike a specification, a plan records what was intended
before implementation and is not updated afterwards.

.. toctree::
    :maxdepth: 1

    2026-07-22-tephpy-design
    2026-08-01-add-logo-design
    2026-08-03-published-specs-design
    2026-08-07-config-file-design
    2026-08-12-config-domain-validation-design
    2026-08-13-dependency-floors-design
