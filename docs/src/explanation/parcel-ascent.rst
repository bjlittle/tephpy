.. _explanation-parcel-ascent:

Parcel Ascent and Normand's Point
=================================

:ref:`explanation-rotated-axes` describes the grid. This page describes the one
thing meteorologists draw *on* it: the path a parcel of air takes when something
lifts it, and why the answer to "will this sounding produce a storm" is an area on
that path rather than a number in a table.

.. plot::
    :context: reset
    :filename-prefix: parcel-ascent-construction

    import matplotlib.pyplot as plt

    import tephpy
    from tephpy import samples

    snd = samples.sounding("norman-12z")
    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(snd)
    parcel = tephpy.calc.parcel_path(snd, label="surface parcel")
    ax.plot_profile(parcel, color="k", linestyle="--")
    ax.legend()

The dashed black line is the parcel. The red and green lines are the
:term:`sounding` — the atmosphere it is rising through. Everything below is what
the dashed line is doing.

Lifting a Parcel
----------------

Take a small volume of air at the surface and push it upward. It expands, because
the pressure around it falls, and expanding costs energy, so it cools. If it
exchanges no heat with its surroundings while this happens — a fair approximation
over the timescales that matter — the process is *adiabatic*, and the parcel
conserves its :term:`potential temperature`.

Conserving θ is exactly what a :term:`dry adiabat` is a line of. So the first
stage of the ascent needs no computation on this diagram: the parcel slides up the
dry adiabat it started on, and the diagram was built to make that a straight line.

Normand's Point
---------------

The parcel cools as it rises, but its moisture goes with it. Two quantities
therefore approach each other: the temperature, falling along the dry adiabat, and
the dewpoint, which falls much more slowly along a line of constant
:term:`humidity mixing ratio`. Where they meet, the parcel is saturated, and any
further lifting condenses water. That height is the
:term:`lifting condensation level` — cloud base — and the intersection is
**Normand's point**.

The construction is the whole reason this diagram is drawn: two straight lines
crossing, read off with a ruler.
:func:`calc.normand_point(...) <tephpy.calc.normand_point>` does exactly what a
forecaster does with a pencil — takes the dry adiabat through the parcel's
temperature and the mixing-ratio line through its dewpoint, and returns where they
meet. Nothing is iterated and nothing is fitted; the answer is geometric.

Above Normand's point the parcel is saturated, and condensation releases latent
heat. It still cools as it rises, but more slowly, so it follows a
:term:`moist adiabat` instead. That is the kink in the dashed line.

Where the Numbers Come From
---------------------------

``tephpy`` draws the construction; `MetPy <https://unidata.github.io/MetPy/latest/>`__
computes it. That division is deliberate — spec §3.3 delegates the thermodynamics
rather than reimplementing them — and it matters to anyone deciding whether to
trust a value: a CAPE figure from :func:`calc.indices(...) <tephpy.calc.indices>`
is MetPy's number, drawn here.

:func:`calc.parcel_path(...) <tephpy.calc.parcel_path>` assembles the path from
the pieces above. It lifts from the surface by default, or from a mixed layer if
asked, and returns a :class:`Profile <tephpy.calc.Profile>` carrying the LCL it
actually used.

One convention deserves naming rather than appearing as a magic number.
Operational practice often shifts cloud base about 25 mb below the computed LCL,
because the construction assumes a parcel that is not mixing with its surroundings
and real ones do. ``tephpy`` neither applies that silently nor hides it: it is
``cloud_base_correction``, applied only when asked, and the value lives in
``tephpy._constants.CLOUD_BASE_CORRECTION``.

Why CAPE Is an Area
-------------------

Above cloud base, compare the parcel with the air around it. Where the parcel is
warmer it is less dense, so it rises on its own — it is buoyant, and the
atmosphere is doing work on it. Where it is colder, lifting it costs work
instead.

The energy either way is the integral of the buoyancy over the ascent, and on a
diagram whose coordinates are temperature and :term:`entropy` an integral like
that *is* an area. That is the property :ref:`explanation-rotated-axes` says the
coordinates were chosen for, and this is where it pays: the two areas between the
dashed parcel line and the environment curve are
:term:`convective available potential energy` and
:term:`convective inhibition`, in joules per kilogram, readable by eye.

:meth:`ax.shade_cape(...) <tephpy.plotting.axes.TephigramAxes.shade_cape>` and
:meth:`ax.shade_cin(...) <tephpy.plotting.axes.TephigramAxes.shade_cin>` fill
them. On a diagram without this property — one whose axes were chosen for
something else — the same regions are still bounded, but their areas are not
energies, and shading them would be decoration.

Where to Go Next
----------------

:ref:`howto-emphasis` marks the reference lines a forecaster reads against, and
the :doc:`gallery <../gallery/index>` shows the finished analyses this
construction underlies.
