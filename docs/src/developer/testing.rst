.. _developer-testing:

Testing
=======

.. readingtime::

The tests tree mirrors the ``src/tephpy`` package layout: tests for top-level modules
live at the ``tests/`` root, and every subpackage has a matching directory —
``tests/plotting/`` for ``tephpy.plotting`` — however few modules it carries.
``tephpy.samples`` is a lone ``__init__.py`` and still has ``tests/samples/``.

``tests/test_layout.py`` holds the tree to that, so a subpackage arriving without its
directory fails a test rather than waiting to be noticed. Place a new test module at the
level of the module it exercises; the shared ``fixtures/`` and ``baseline/`` directories
stay at the root.

Running the Suite
-----------------

.. code:: console

    $ pixi run tests

pytest runs with a strict configuration and ``filterwarnings = ["error"]``, so a warning
is a failure. ``pixi run tests-clean`` removes the artifacts a run leaves behind.

Image Comparison
----------------

Plotting tests compare a rendered figure against a recorded baseline with pytest-mpl,
marked ``@pytest.mark.mpl_image_compare``. Both CI and ``pixi run tests`` pass ``--mpl``,
so the comparison is enforced rather than skipped.

.. code:: console

    $ pixi run baselines

regenerates ``tests/baseline``. Reach for it when a lockfile bump moves matplotlib or
freetype, and re-verify across all three test environments afterwards — the baselines are
shared, and a regeneration that satisfies one Python can fail another.

No Test Touches the Network
---------------------------

The ingest readers are tested against recorded captures under ``tests/fixtures/io/``,
byte-faithful and with their provenance recorded beside them. Nothing in the suite makes a
request.

The reason is worth stating, because the rule costs something. A suite that reached the
University of Wyoming would fail on their outage rather than on a defect here, and a red
tick that means "somebody else is down" teaches a reader to ignore red ticks. What the rule
gives up is knowing when the archive moves under us — every gate stays green while
``tephpy.io.wyoming`` stops working. :doc:`ci` describes the scheduled job that pays that
cost instead.
