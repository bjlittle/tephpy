.. _explanation-rotated-axes:

Why the Axes Are Rotated
========================

A tephigram looks like a chart somebody turned forty-five degrees on the way to
the printer. It is not. The rotation is the last step of a construction that
starts by choosing two coordinates on physical grounds, and every awkward-looking
thing about the diagram — the diagonal grid, the curved pressure lines, the
absence of anything you could call a vertical axis — follows from that choice.

.. plot::
    :context: reset
    :filename-prefix: rotated-axes-grid

    import matplotlib.pyplot as plt

    import tephpy  # registers the "tephigram" projection

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.isotherms(
        emphasis={
            0.0: {},  # the shipped default, kept: an accessor emphasis replaces it
            -20.0: {"color": "tab:red", "linewidth": 2.0},
        }
    )
    ax.dry_adiabats(emphasis={20.0: {"color": "tab:blue", "linewidth": 2.0}})

One isotherm and one dry adiabat, picked out of the grid: they cross at a right
angle, and every other pair in those two families does the same. The rest of this
page is why.

Temperature Against Entropy
---------------------------

The two coordinates are temperature and :term:`entropy`. That pairing is the
whole design, and it is chosen for a property nothing else has: on a
temperature–entropy diagram, the area enclosed by a cyclic process is the energy
that process exchanges. A meteorologist reading energy off a chart by eye is
reading an area, and it is an area because of this choice.

Entropy is not plotted directly. For dry air the specific entropy is
:math:`c_p \ln \theta` plus a constant, where :math:`\theta` is
:term:`potential temperature` — so :math:`\ln \theta` *is* entropy, up to a
scale and an offset that no reader ever needs. The diagram plots
:math:`\ln \theta`, which is where the name T–ln θ comes from, and why
``tephpy``'s transforms take pressure and temperature in and give
:math:`\theta` back.

Why the Grid Is Square
----------------------

On those coordinates two of the five isopleth families are trivially straight,
and exactly perpendicular to each other.

An :term:`isotherm` is a line of constant temperature, so on a T–ln θ plane it
is a line of constant T: straight, and parallel to the entropy axis. A
:term:`dry adiabat` is a line of constant potential temperature — a parcel moved
without exchanging heat conserves :math:`\theta` — so it is a line of constant
:math:`\ln \theta`: straight, and parallel to the temperature axis.

Two families of straight lines, at right angles, covering the plane. That
squareness is the property the coordinates were chosen to produce, and it is what
makes a tephigram readable: any two of temperature, potential temperature and
their difference can be stepped off along a straight edge.

Why It Is Turned
----------------

The rotation is cosmetic in origin and structural in effect. ``tephpy`` performs
it in :func:`xy_from_temperature_theta
<tephpy.transforms.xy_from_temperature_theta>`:

.. math::

    x = M_A \ln \theta_K + T \qquad y = M_A \ln \theta_K - T

with :math:`M_A = 300` a scale that puts the two coordinates on comparable
ranges, and :math:`\theta_K` the potential temperature in kelvin. Adding and
subtracting the same pair is a forty-five degree rotation, and it has three
consequences worth naming.

**Isotherms run from bottom left to top right.** Along an isotherm :math:`T` is
fixed, so :math:`x - y = 2T` is fixed too: the line has slope one. The Met
Office's printed chart describes them exactly that way — "straight and parallel,
running at 45° across the diagram from bottom left to top right"
:cite:`metoffice_factsheet13`.

**Dry adiabats run perpendicular to them.** Along a dry adiabat
:math:`\ln \theta` is fixed, so :math:`x + y` is fixed: slope minus one. The
right angle survives the rotation, because rotations preserve angles. That is the
entire reason it is safe to turn the diagram at all.

**Pressure increases downward.** This is what the rotation buys. Cooling and
descending both move a parcel down and left, so the ground is at the bottom of
the page and the tropopause at the top, which is how anyone thinks about a
vertical profile. Unrotated, the same information reads sideways.

Where the Pressure Axis Went
----------------------------

There is not one. Pressure is *derived*, not plotted: given a temperature and a
potential temperature, Poisson's relation fixes the pressure, so every point on
the diagram already has one without an axis to carry it.

That is why an :term:`isobar` is a gently curved line rather than a horizontal
rule, and why ``tephpy`` computes the isobars rather than drawing a grid — see
:func:`pressure_from_temperature_theta
<tephpy.transforms.pressure_from_temperature_theta>`. It is also why a tephigram
cannot be read like a graph with two rulers. The diagram's own extent is stated
in pressure and temperature, because those are what a user thinks in, and
:meth:`ax.set_extent(...) <tephpy.plotting.axes.TephigramAxes.set_extent>`
converts.

What the Printed Chart Adds
---------------------------

Two conventions on the diagram are not consequences of the mathematics but
decisions somebody made and everybody kept. The isotherms are drawn every 10 °C,
and the 0 °C isotherm is distinguished from its neighbours — on the Met Office's
printed chart by colouring it red :cite:`metoffice_factsheet13`. ``tephpy``
follows both, drawing that one member heavier rather than red, because red is
already the temperature profile's colour. :ref:`howto-emphasis` shows how to
change or extend it.
