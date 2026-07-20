
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click
from monty.json import jsanitize

if TYPE_CHECKING:
    from pathlib import Path

    from jobflow import Maker


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def dev() -> None:
    """Tools for atomate2 developers."""


@dev.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "test_dir",
)
@click.option(
    "--additional_file",
    "-a",
    multiple=True,
    help="list of additional files to copy from each completed VASP directory. "
    "Example: `--additional_file CHGCAR --additional_file LOCPOT`",
)
def vasp_test_data(test_dir: str | Path, additional_file: list[str]) -> None:
    pass


def _potcar_to_potcar_spec(potcar_filename: str | Path, output_filename: Path) -> None:
    pass


@dev.command(context_settings={"help_option_names": ["-h", "--help"]})
def abinit_script_maker() -> None:
    pass


@dev.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("structure_file", required=False)
@click.option("--make-kwargs", "-mk", required=False)
def abinit_generate_reference(structure_file: str, make_kwargs: dict) -> None:
    pass


@dev.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("test_name")
@click.option("--test-data-dir", required=False)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Whether to force overwrite of existing folders/files.",
)
def abinit_test_data(test_name: str, test_data_dir: str | None, force: bool) -> None:
    pass


def save_abinit_maker(maker: Maker) -> None:
    pass


