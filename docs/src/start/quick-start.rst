.. _start-quick-start:

Quick Start
===========

.. readingtime::

With ``tephpy`` installed, a real :term:`radiosonde` ascent on a real
:term:`tephigram` is a few lines. The :term:`sounding` ships with the package,
so there is nothing to download first.

.. plot::
    :context: reset
    :filename-prefix: quick-start-sounding

    import matplotlib.pyplot as plt

    from tephpy import samples

    snd = samples.sounding("norman-12z")

    fig, ax = plt.subplots(subplot_kw={"projection": "tephigram"})
    ax.plot_sounding(snd)
    ax.legend()

That is Norman, Oklahoma on the morning of 2013-05-20. The two traces are
temperature and :term:`dewpoint`; everything behind them is the diagram's own
grid.

You now have the thing this documentation is about. What you do not yet have is
a way to read it, which is what :ref:`tutorial-first-tephigram` is for — it
draws this same ascent and names every line on it.
