.. _start-installation:

:iconify:`mdi:download-circle` Installation
===========================================

.. readingtime::

.. note::
    tephpy has not had its first release yet, so the commands in **Stable** do
    not work today. They are what installing will look like from ``v0.1.0``
    onward. To use ``tephpy`` now, take the **Latest** or **Developer** route.

:iconify:`mdi:check-circle` Stable
----------------------------------

The latest **stable release**, from `conda-forge <https://conda-forge.org/>`__
or `PyPI <https://pypi.org/project/tephpy/>`__:

.. tab-set::
    :sync-group: install

    .. tab-item:: :iconify:`vscode-icons:file-type-conda` conda
        :sync: conda

        .. code:: console

            $ conda create --name myenv --channel conda-forge tephpy
            $ conda activate myenv

        :iconify:`twemoji:information` Consult the ``conda``
        `installation <https://docs.conda.io/projects/conda/en/stable/>`__
        instructions.

    .. tab-item:: :iconify:`devicon:pypi` pip
        :sync: pip

        .. code:: console

            $ pip install tephpy

        :iconify:`twemoji:information` Consult the ``pip``
        `installation <https://pip.pypa.io/en/stable/installation/>`__
        instructions.

    .. tab-item:: :iconify:`fa6-solid:puzzle-piece` pixi
        :sync: pixi
        :selected:

        .. code:: console

            $ pixi init myenv
            $ cd myenv
            $ pixi add tephpy

        :iconify:`twemoji:information` Consult the ``pixi``
        `installation <https://pixi.sh/latest/installation/>`__
        instructions.

    .. tab-item:: :iconify:`material-icon-theme:uv` uv
        :sync: uv

        .. code:: console

            $ uv pip install tephpy

        :iconify:`twemoji:information` Consult the ``uv``
        `installation <https://docs.astral.sh/uv/getting-started/installation/>`__
        instructions.

:iconify:`mdi:rocket-launch` Latest
-----------------------------------

The **development version**, from the ``main`` branch:

.. tab-set::
    :sync-group: install

    .. tab-item:: :iconify:`vscode-icons:file-type-conda` conda
        :sync: conda

        .. code:: console

            $ conda create --name myenv --channel conda-forge pip
            $ conda activate myenv
            $ pip install git+https://github.com/bjlittle/tephpy.git@main

    .. tab-item:: :iconify:`devicon:pypi` pip
        :sync: pip

        .. code:: console

            $ pip install git+https://github.com/bjlittle/tephpy.git@main

    .. tab-item:: :iconify:`fa6-solid:puzzle-piece` pixi
        :sync: pixi
        :selected:

        .. code:: console

            $ pixi init myenv
            $ cd myenv
            $ pixi add python
            $ pixi add --pypi "tephpy @ git+https://github.com/bjlittle/tephpy.git@main"

    .. tab-item:: :iconify:`material-icon-theme:uv` uv
        :sync: uv

        .. code:: console

            $ uv pip install "tephpy @ git+https://github.com/bjlittle/tephpy.git@main"

:iconify:`mdi:tools` Developer
------------------------------

To work on ``tephpy`` itself, clone the repository:

.. code:: console

    $ git clone git@github.com:bjlittle/tephpy.git
    $ cd tephpy

``tephpy`` develops with `pixi <https://pixi.sh>`__, which reads its environments
from ``pyproject.toml`` and needs no setup of its own:

.. code:: console

    $ pixi run tests
    $ pixi run lint
    $ pixi run docs

Those three are the checks a pull request must pass, and each builds the
environment it needs the first time it runs. ``pixi run docs`` builds this
documentation and runs every gate over the result.

If you would rather not use ``pixi``, the same dependencies are declared as
extras:

.. tab-set::
    :sync-group: install

    .. tab-item:: :iconify:`vscode-icons:file-type-conda` conda
        :sync: conda

        .. code:: console

            $ conda create --name tephpy-dev --channel conda-forge python pip
            $ conda activate tephpy-dev
            $ pip install --editable ".[devs]"

    .. tab-item:: :iconify:`devicon:pypi` pip
        :sync: pip

        .. code:: console

            $ pip install --editable ".[devs]"

    .. tab-item:: :iconify:`fa6-solid:puzzle-piece` pixi
        :sync: pixi
        :selected:

        .. code:: console

            $ pixi shell --environment devs

    .. tab-item:: :iconify:`material-icon-theme:uv` uv
        :sync: uv

        .. code:: console

            $ uv pip install --editable ".[devs]"
