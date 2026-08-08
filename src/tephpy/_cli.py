# Copyright (c) 2026, tephpy Contributors.
#
# This file is part of tephpy and is distributed under the 3-Clause BSD license.
# See the LICENSE file in the package root directory for licensing details.
"""The ``tephpy`` command line (configfile spec §4).

Argument parsing and output text only. Everything this module does is
reachable from Python through ``tephpy.config`` and ``tephpy._configfile``,
so the command line is never the only way to do something.
"""

from __future__ import annotations

from pathlib import Path

import click

from tephpy import _configfile
from tephpy.exceptions import TephpyConfigError

__all__ = ["main"]


@click.group()
@click.version_option(package_name="tephpy")
def main() -> None:
    """Plot and analyse tephigrams."""


@main.group(invoke_without_command=True)
@click.pass_context
def config(ctx: click.Context) -> None:
    """Inspect and generate the tephpy configuration file."""
    # ctx is Click's own plumbing (injected by @click.pass_context), not
    # part of the command's public surface: numpydoc ignore=PR01
    if ctx.invoked_subcommand is None:
        ctx.invoke(path)


@config.command()
def path() -> None:
    """Report the configuration file search, and which file is in force."""
    try:
        active = _configfile.discover()
    except TephpyConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    for candidate in _configfile.config_paths():
        if candidate == active:
            state = "in force"
        elif candidate.exists():
            state = "shadowed"
        else:
            state = "absent"
        click.echo(f"{candidate}  [{state}]")
    if active is None:
        click.echo("")
        click.echo("No configuration file found; tephpy is using its defaults.")


@config.command()
@click.option(
    "-o",
    "--output",
    "destination",
    default=None,
    help="Where to write. Use '-' for standard output.",
)
@click.option("--force", is_flag=True, help="Overwrite an existing file.")
def generate(destination: str | None, *, force: bool = False) -> None:
    """Write a fully-commented configuration template."""
    # destination and force are already explained by each option's help=
    # text above, which is what --help actually shows: numpydoc ignore=PR01
    if destination == "-":
        click.echo(_configfile.render_template(), nl=False)
        return
    target = (
        _configfile.user_config_path() if destination is None else Path(destination)
    )
    try:
        _configfile.write_template(target, force=force)
    except TephpyConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Wrote {target}")
