
import logging
import os
from pathlib import Path
from typing import Any, Union

from emmet.core.structure import MoleculeMetadata
from monty.dev import requires
from monty.json import jsanitize
from pydantic import Field
from pymatgen.core import Molecule
from pymatgen.core.periodic_table import Element
from typing_extensions import Self

from atomate2 import __version__
from atomate2.utils.datetime import datetime_str
from atomate2.utils.path import find_recent_logfile, get_uri

try:
    import cclib
except ImportError:
    cclib = None


logger = logging.getLogger(__name__)


class TaskDocument(MoleculeMetadata, extra="allow"):  # type: ignore[call-arg]

    molecule: Molecule | None = Field(
        None, description="Final output molecule from the task"
    )
    energy: float | None = Field(None, description="Final total energy")
    dir_name: str | None = Field(
        None, description="Directory where the output is parsed"
    )
    logfile: str | None = Field(
        None, description="Path to the log file used in the post-processing analysis"
    )
    attributes: dict | None = Field(
        None, description="Computed properties and calculation outputs"
    )
    metadata: dict | None = Field(
        None,
        description="Calculation metadata, including input parameters and runtime "
        "statistics",
    )
    task_label: str | None = Field(None, description="A description of the task")
    tags: list[str] | None = Field(
        None, description="Optional tags for this task document"
    )
    last_updated: str = Field(
        default_factory=datetime_str,
        description="Timestamp for this task document was last updated",
    )
    schema: str = Field(
        __version__, description="Version of atomate2 used to create the document"
    )

    @classmethod
    @requires(cclib, "The cclib TaskDocument requires cclib to be installed.")
    def from_logfile(
        cls,
        dir_name: Union[str, Path],
        logfile_extensions: Union[str, list[str]],
        store_trajectory: bool = False,
        additional_fields: dict[str, Any] | None = None,
        analysis: Union[str, list[str]] | None = None,
        proatom_dir: Union[Path, str] | None = None,
    ) -> Self:
        pass


@requires(cclib, "cclib_calculate requires cclib to be installed.")
def cclib_calculate(
    cclib_obj: Any,
    method: str,
    cube_file: Union[Path, str],
    proatom_dir: Union[Path, str],
) -> dict[str, Any] | None:
    pass


def _get_homos_lumos(
    mo_energies: list[list[float]], homo_indices: list[int]
) -> tuple[list[float], list[float] | None, list[float] | None]:
    pass
