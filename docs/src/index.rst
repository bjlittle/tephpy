tephpy
======

Plot and analyse :term:`tephigrams <tephigram>`.

.. The landing page carries the four Diataxis quadrants and nothing else. The
   gallery is not a fifth quadrant; it is a way into all four, so it is reached
   from the toctree below rather than from a card of its own.

.. Each card's icon is drawn in the brand mark's own vocabulary -- the 45
   degree lattice, a profile, an accent on the thing being pointed at -- rather
   than taken from a third-party icon set, because what tephpy plots reduces to
   an icon and a globe does not. What each one shows is the quadrant's subject:
   Tutorials, a path walked to a marked end; How-To Guides, one isopleth of a
   family drawn heavier, which is what the emphasis how-to teaches; Explanation,
   the axes turning through 45 degrees, which narrative spec §1 names as the
   question nothing answered; Reference, an index with one entry found.

   They are hand-authored and hand-maintained: ``docs/src/_static/cards/``, one
   file per quadrant per theme, small enough to edit in place. The light and
   dark pairing, and the layout, are ``docs/src/_static/tephpy.css``.

.. grid:: 2
    :gutter: 2

    .. grid-item-card:: Tutorials
        :link: tutorials/index
        :link-type: doc
        :class-card: teph-quadrant sd-rounded-3

        .. image:: _static/cards/tutorials-light.svg
            :class: only-light teph-quadrant-icon
            :alt: a path stepping up across the tephigram lattice to a marked end

        .. image:: _static/cards/tutorials-dark.svg
            :class: only-dark teph-quadrant-icon
            :alt: a path stepping up across the tephigram lattice to a marked end

        Learning-oriented lessons.

    .. grid-item-card:: How-To Guides
        :link: howtos/index
        :link-type: doc
        :class-card: teph-quadrant sd-rounded-3

        .. image:: _static/cards/howtos-light.svg
            :class: only-light teph-quadrant-icon
            :alt: one isopleth of a family drawn at a heavier weight

        .. image:: _static/cards/howtos-dark.svg
            :class: only-dark teph-quadrant-icon
            :alt: one isopleth of a family drawn at a heavier weight

        Goal-oriented recipes.

    .. grid-item-card:: Explanation
        :link: explanation/index
        :link-type: doc
        :class-card: teph-quadrant sd-rounded-3

        .. image:: _static/cards/explanation-light.svg
            :class: only-light teph-quadrant-icon
            :alt: a pair of axes turning through 45 degrees

        .. image:: _static/cards/explanation-dark.svg
            :class: only-dark teph-quadrant-icon
            :alt: a pair of axes turning through 45 degrees

        Understanding-oriented background.

    .. grid-item-card:: Reference
        :link: reference/index
        :link-type: doc
        :class-card: teph-quadrant sd-rounded-3

        .. image:: _static/cards/reference-light.svg
            :class: only-light teph-quadrant-icon
            :alt: an index of entries, one of them marked

        .. image:: _static/cards/reference-dark.svg
            :class: only-dark teph-quadrant-icon
            :alt: an index of entries, one of them marked

        Information-oriented API and glossary.

.. rst-class:: center

    :octicon:`mortar-board` Four quadrants, because learning, working and
    understanding are different needs (`Diátaxis <https://diataxis.fr/>`__)

.. toctree::
    :hidden:

    tutorials/index
    howtos/index
    explanation/index
    reference/index
    gallery/index
    developer/index
