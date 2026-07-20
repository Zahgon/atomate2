
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from custodian.vasp.handlers import (
    FrozenJobErrorHandler,
    IncorrectSmearingHandler,
    LargeSigmaHandler,
    MeshSymmetryErrorHandler,
    PositiveEnergyErrorHandler,
    StdErrHandler,
    VaspErrorHandler,
)
from emmet.core.types.enums import StoreTrajectoryOption
from jobflow import Response, job

from atomate2.vasp.jobs.base import BaseVaspMaker
from atomate2.vasp.schemas.md import MultiMDOutput
from atomate2.vasp.sets.core import MDSetGenerator

if TYPE_CHECKING:
    from pathlib import Path

    from pymatgen.core import Structure

    from atomate2.vasp.sets.base import VaspInputGenerator


logger = logging.getLogger(__name__)


@dataclass
class MDMaker(BaseVaspMaker):

    name: str = "molecular dynamics"

    input_set_generator: VaspInputGenerator = field(default_factory=MDSetGenerator)

    run_vasp_kwargs: dict = field(
        default_factory=lambda: {
            "handlers": (
                VaspErrorHandler(),
                MeshSymmetryErrorHandler(),
                PositiveEnergyErrorHandler(),
                FrozenJobErrorHandler(),
                StdErrHandler(),
                LargeSigmaHandler(),
                IncorrectSmearingHandler(),
            )
        }
    )

    task_document_kwargs: dict = field(
        default_factory=lambda: {"store_trajectory": StoreTrajectoryOption.PARTIAL}
    )


@job(output_schema=MultiMDOutput)
def md_output(
    structure: Structure,
    vasp_dir: str | Path,
    traj_ids: list[str],
    prev_traj_ids: list[str] | None,
) -> Response:
    """
    Collect output references of a multistep MD flow.

    Parameters
    ----------
    structure: .Structure
        The final structure to be stored.
    vasp_dir: str or Path
        The path to the folder containing the last calculation of a MultiMDMaker.
    traj_ids: list of str
        List of the uuids of the jobs that will compose the trajectory.
    prev_traj_ids: list of str
        List of the uuids of the jobs coming from previous flow that will be
        added to the trajectory.

    Returns
    -------
    The output dictionary.
    """
    full_traj_ids = list(traj_ids)
    if prev_traj_ids:
        full_traj_ids = prev_traj_ids + full_traj_ids
    output = MultiMDOutput.from_structure(
        structure=structure,
        meta_structure=structure,
        vasp_dir=str(vasp_dir),
        traj_ids=traj_ids,
        full_traj_ids=full_traj_ids,
    )
    return Response(output=output)
