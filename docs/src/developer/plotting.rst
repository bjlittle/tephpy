.. _developer-plotting:

A Tour of the Plotting Package
==============================

.. readingtime::

``tephpy.plotting`` is the matplotlib layer: what turns a sounding into a figure. It
publishes two names — ``TephigramAxes``, registered as the ``"tephigram"`` projection,
and ``add_logo`` — and keeps the rest private. Underneath it sits ``tephpy.transforms``,
which owns the temperature-entropy mathematics; beside it sit ``tephpy.sounding`` and
``tephpy.calc``, which it consumes and which never import it back. The thermodynamics is
MetPy's throughout.

**This page is a map, not an account.** Every mechanism it names is specified in a design
specification or documented on the object itself, and is cited here rather than restated.
Where this page and a specification disagree, the specification is right and this page is
the defect — so follow the citation whenever you need the argument rather than the rule.

The Modules
-----------

.. list-table::
    :header-rows: 1
    :widths: 16 54 30

    * - Module
      - What it owns
      - Where its rules live
    * - ``__init__.py``
      - the package's two public names, and nothing else
      - —
    * - ``axes.py``
      - the projection and its transforms, the plotting accessors, edge ownership, the
        cursor readout, and the side-panel layout
      - spec §3.2.1, §3.2.3, §3.2.5, §3.2.6, §3.2.7
    * - ``isopleths.py``
      - the five background families: their members, option resolution, the zoom ladder,
        and their labels
      - spec §3.2.1, §3.2.2, §3.2.4
    * - ``shading.py``
      - the CAPE and CIN region geometry
      - spec §3.2.5
    * - ``barbs.py``
      - the wind-barb gutter, its staff, and the thinning of levels
      - spec §3.2.5
    * - ``logo.py``
      - the branding artist, which has a specification of its own
      - logo spec §3.2, §3.3, §3.4, §3.5, §3.6
    * - ``_theme.py``
      - one answer to "what colour is the canvas", shared by the logo and the inline
        labels
      - logo spec §3.5, spec §3.2.2

``axes.py`` and ``isopleths.py`` carry roughly three quarters of the package between
them. The other five are small enough to read whole, and the table above is the only
place that has to change when a module arrives or leaves.

How the Isopleths Draw
----------------------

The five families — isotherms, isobars, dry adiabats, moist adiabats and humidity
mixing-ratio lines — are drawn by default, one ``IsoplethFamily`` artist each. Members
are built lazily on the first draw and cached; every ``draw`` then clips that cache to
the view rectangle, selects the members the zoom ladder calls for, and re-places the
labels (spec §3.2.1).

That is why pan, zoom, resize and ``set_extent`` need no special handling: matplotlib
calls ``draw`` on every render, and nothing caches a decision that depends on the view.
A change that moves work out of ``draw`` and into construction is a change that breaks
zoom, quietly.

Settings resolve in three tiers — accessor keywords, then ``tephpy.config``, then
``_constants`` — re-read on every resolve, so a configuration change can move a family
the call never mentions (spec §3.5). Passing ``values`` or ``interval`` explicitly fixes
the member set and turns the zoom ladder off.

Labels go inline or onto an edge, per family (spec §3.2.2). Which edges suit which family
is a measured question rather than a matter of taste: the per-family edge-crossing counts,
and the pairings they recommend, are in spec §3.2.7.

Clear Is the Constructor
------------------------

``TephigramAxes.clear`` is where every piece of projection-owned state is built — the
transform, the equal aspect, the hidden native axes, the five families, the edges they
claim, and the default extent. Matplotlib calls it twice over: once from ``Axes.__init__``
and again on every ``ax.clear()``. There is no separate constructor to read, and anything
that must survive a clear has to be built here.

The order matters in one place. All five families are constructed before the first edge
sync runs, because each arms its ``on_change`` as it is built and a sync running mid-loop
would see a partial set. The extent lands last.

A family's ``configure`` notifies ``on_change`` only when it succeeds, so a call that
raises leaves both the family and the diagram's edges as they were (spec §3.2.3).

Who Owns an Edge
----------------

An edge carries one family's labels, or none. Whichever way a family is reconfigured — an
accessor, a direct ``configure``, an ``Artist.set_visible`` — the same four steps run:

1. the family resolves its new options;
2. ``_check_label_edges`` rejects a claim another family already holds;
3. ``_sync_edge_labels`` compares what the five families now ask for against what is
   currently claimed; and
4. ``_claim_edge`` or ``_release_edge`` applies the difference.

Validation sits at step 2 rather than inside the family because the axes owns all five
families and is therefore the only object that can see a collision. Handing it to the
family as a hook puts the rejection inside that family's own rollback (spec §3.2.3).

Three properties are easy to break from inside any one of those steps.

**A claim installs identity, never presentation.** Locator, formatter, visibility, colour,
title. How the ticks *look* is stamped once, when the edge axis is created, and belongs to
the caller from the claim onwards — so ``ax.edge_axis("top").set_tick_params(labelsize=12)``
survives everything short of a release (spec §3.2.3).

**The tick-colour memory is keyed by owner as well as colour.** It outlives a release, so
comparing colour alone would suppress a new owner's claim whenever its colour happened to
match the previous owner's, leaving the ticks in a colour that ties them to nothing.

**The sync is re-entrancy guarded.** Nothing on the sync path resolves options, so a
nested call would have nothing new to apply. The guard makes that structural rather than a
standing bet on matplotlib's axis internals.

The Side Panels
---------------

Two panels can sit to the right of the diagram: the wind-barb gutter and the indices
panel, in that order, inside out (spec §3.2.7).

**One divider per axes**, created once and cached. A second ``make_axes_locatable`` call
would build a fresh divider and replace the parent locator, detaching the earlier panel so
that it draws over the newcomer.

**Relayout, not teardown.** ``_relayout_side_panels`` rebuilds the divider's horizontal
stack and reassigns every locator whenever a panel appears, so the inside-out order holds
whichever order ``plot_barbs`` and ``annotate_indices`` were called in. Removing and
re-appending would not do: ``append_axes`` only ever appends to the size stack, so the
removed panel's width slot stays behind as a phantom gap.

**The pad widens when the right edge carries ticks.** Isopleth tick labels are wider than
the gutter's own pad, so the panel nearest the diagram takes a wider one while the right
edge is claimed. That is why a right-edge claim relayouts the panels at all, and it is the
one place the two flows on this page meet.

**Who removes the panels on a clear depends on who called it.** They are the diagram's to
remove on a direct ``ax.clear()``, and the figure's on a figure clear, where the diagram's
teardown stands down rather than racing it: ``Figure.clear`` clears and deletes each entry
of a *snapshot* of ``figure.axes``, so an axes removing a sibling from inside its own
``clear`` orphans an entry the figure is still about to visit. The two cases are told apart
by the calling frame — ``_figure_is_clearing`` — because the figure's state is identical
either way (spec §3.2.7).

Where to Look
-------------

.. list-table::
    :header-rows: 1
    :widths: 45 55

    * - Changing
      - Read first
    * - a family's geometry, members or labels
      - the ``isopleths.py`` module docstring, then spec §3.2.1, §3.2.2
    * - which edge a family labels
      - spec §3.2.3, then ``_sync_edge_labels``
    * - emphasis styling of individual members
      - spec §3.2.4
    * - what an accessor accepts, or a new accessor
      - spec §3.2.5, then the accessor's own docstring
    * - the cursor readout
      - spec §3.2.6, then ``format_coord``
    * - the default view, or which edges a family can tick
      - spec §3.2.7 for the crossing counts, framing spec §3.1 for what an extent frames
    * - a side panel's width, order or pad
      - spec §3.2.7, then ``_relayout_side_panels``
    * - anything that must survive ``ax.clear()``
      - ``clear`` itself, and this page's *Clear Is the Constructor*
    * - the logo
      - logo spec, which is a specification of its own

The tests for all of this live in ``tests/plotting/``, mirroring the package
(:doc:`testing`).
